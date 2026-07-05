"""Shadow-only runtime continuity recorder for prompt_v6 evidence.

This module does not implement model memory extraction. It records
engine-derived ability facts and fixture-authored runtime continuity signals so
the p3a_continuity_shadow arm can produce request-level evidence through the
real runner/provider path.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from werewolf_eval.agent_assets import validate_runtime_seat_state
from werewolf_eval.agent_context_packet import (
    AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
    validate_agent_context_packet,
    validate_memory_record,
)

RUNTIME_EVIDENCE_SCENARIO_ID = "p3a_runtime_evidence_closure_v1"
FIXTURE_SIGNAL_SOURCE = "fixture-authored runtime continuity signal"
FIXTURE_SIGNAL_NOTE = (
    "fixture-authored runtime continuity signal; not model-extracted; not a "
    "public game event unless explicitly represented as one"
)


class RuntimeContinuityStore:
    """Mutable per-run continuity store used only by explicit shadow scenarios."""

    def __init__(
        self,
        *,
        run_id: str,
        seat_roles: dict[str, str],
        agent_context_packets: dict[str, dict[str, Any]],
        runtime_seat_states: list[dict[str, Any]] | None = None,
        runtime_team_states: list[dict[str, Any]] | None = None,
        scenario_id: str | None = None,
        malicious_untrusted_text: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.scenario_id = scenario_id
        self.malicious_untrusted_text = malicious_untrusted_text
        self._seat_roles = dict(seat_roles)
        self._packets = copy.deepcopy(agent_context_packets)
        self._runtime_seat_states = {
            state["seat_id"]: copy.deepcopy(state)
            for state in (runtime_seat_states or [])
        }
        self._runtime_team_states = copy.deepcopy(runtime_team_states or [])
        self._game_events: list[dict[str, Any]] = []
        self._signals: list[dict[str, Any]] = []
        self._applied_fixture_signals: set[str] = set()
        self._witch_state: dict[str, dict[str, bool]] = {}
        self._seer_checks: dict[str, list[str]] = {}

        for seat_id in sorted(seat_roles):
            self._packets.setdefault(seat_id, _empty_packet(run_id, seat_id))
            validate_agent_context_packet(self._packets[seat_id])

    @property
    def context_packets(self) -> dict[str, dict[str, Any]]:
        return self._packets

    def on_game_event(self, event: dict[str, Any]) -> None:
        """Observe a trusted engine game event and derive role-private facts."""
        self._game_events.append(copy.deepcopy(event))
        etype = str(event.get("type", ""))
        actor = str(event.get("actor", ""))
        if etype == "seer_check" and actor in self._seat_roles:
            self._record_seer_check(event)
        elif etype in {"witch_save", "witch_poison", "witch_pass"} and actor in self._seat_roles:
            self._record_witch_potion(event)

    def before_provider_request(
        self,
        *,
        observation: dict[str, Any],
        response_kind: str,
        action_contract: dict[str, Any] | None = None,
    ) -> None:
        """Apply deterministic fixture signals at real request boundaries."""
        if self.scenario_id != RUNTIME_EVIDENCE_SCENARIO_ID:
            return
        seat_id = str(observation["player_id"])
        phase = str(observation["phase"])
        rnd = int(observation["round"])

        if seat_id == "p4" and phase == "day_speech" and rnd == 1 and response_kind == "speech":
            self._apply_p4_memory_create(observation)
        if seat_id == "p4" and phase == "day" and rnd == 1 and response_kind == "action":
            self._apply_p4_memory_transition(observation)

    def audit_artifact(self) -> dict[str, Any]:
        return {
            "schema_version": "p3a.runtime_continuity.v1",
            "scenario_id": self.scenario_id,
            "signal_note": FIXTURE_SIGNAL_NOTE,
            "signals": copy.deepcopy(self._signals),
            "runtime_seat_states": copy.deepcopy(
                [self._runtime_seat_states[seat] for seat in sorted(self._runtime_seat_states)]
            ),
            "runtime_team_states": copy.deepcopy(self._runtime_team_states),
            "agent_context_packets": copy.deepcopy(
                {seat: self._packets[seat] for seat in sorted(self._packets)}
            ),
        }

    def _record_seer_check(self, event: dict[str, Any]) -> None:
        seat_id = str(event["actor"])
        target = str(event.get("target", "none"))
        event_id = str(event["event_id"])
        checks = self._seer_checks.setdefault(seat_id, [])
        if event_id not in checks:
            checks.append(event_id)
        summary = (
            f"runtime-trusted seer check: {seat_id} checked {target}; "
            f"engine summary={event.get('data', {}).get('summary', '')}"
        )
        record = _record(
            f"runtime_ability_{seat_id}_seer_check",
            kind="AbilityHistoryRecord",
            section="ability_history",
            writer="engine",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=list(checks),
            status="active",
            summary=summary,
            ability_name="seer_check",
            ability_state=f"checks_recorded={len(checks)}",
            owner_seat_id=seat_id,
            target_seat_id=target if target != "none" else None,
            created_round=int(event["round"]),
            created_phase=str(event["phase"]),
            generated_by="EmergentGameEngine.runtime_continuity",
        )
        self._upsert_record(seat_id, record, signal_source="engine_event", source_event_id=event_id)

    def _record_witch_potion(self, event: dict[str, Any]) -> None:
        seat_id = str(event["actor"])
        event_id = str(event["event_id"])
        state = self._witch_state.setdefault(
            seat_id,
            {"antidote_used": False, "poison_used": False},
        )
        etype = str(event["type"])
        if etype == "witch_save":
            state["antidote_used"] = True
        elif etype == "witch_poison":
            state["poison_used"] = True
        source_ids = _existing_source_ids(
            self._packets.get(seat_id), f"runtime_ability_{seat_id}_witch_potions"
        )
        if event_id not in source_ids:
            source_ids.append(event_id)
        summary = (
            "runtime-trusted witch potion state: "
            f"antidote_used={state['antidote_used']}; "
            f"poison_used={state['poison_used']}; latest_event={etype}; "
            f"target={event.get('target')}"
        )
        record = _record(
            f"runtime_ability_{seat_id}_witch_potions",
            kind="AbilityHistoryRecord",
            section="ability_history",
            writer="engine",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=source_ids,
            status="active",
            summary=summary,
            ability_name="witch_potions",
            ability_state=(
                f"antidote_used={state['antidote_used']};"
                f"poison_used={state['poison_used']}"
            ),
            owner_seat_id=seat_id,
            target_seat_id=(
                str(event.get("target")) if str(event.get("target")) != "none" else None
            ),
            created_round=int(event["round"]),
            created_phase=str(event["phase"]),
            generated_by="EmergentGameEngine.runtime_continuity",
        )
        self._upsert_record(seat_id, record, signal_source="engine_event", source_event_id=event_id)

    def _apply_p4_memory_create(self, observation: dict[str, Any]) -> None:
        key = "p4_memory_create"
        if key in self._applied_fixture_signals:
            return
        self._applied_fixture_signals.add(key)
        source_ids = _visible_source_ids(
            observation, self._game_events, event_type="player_speech", actors={"p3"}
        )
        extra = _malicious_suffix(self.malicious_untrusted_text)
        commitment = _record(
            "runtime_commitment_p4_revisit_claim",
            kind="CommitmentRecord",
            section="commitments",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": ["p4"]},
            source_event_ids=source_ids,
            status="active",
            summary=(
                "runtime p4 commitment: revisit p3's public claim before voting"
                + extra
            ),
            owner_seat_id="p4",
            proposition="revisit p3 public claim before voting",
            created_round=1,
            created_phase="day",
            generated_by=RUNTIME_EVIDENCE_SCENARIO_ID,
        )
        belief = _record(
            "runtime_belief_p4_p3_claim",
            kind="BeliefRecord",
            section="episodic_notes",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": ["p4"]},
            source_event_ids=source_ids,
            status="active",
            summary="runtime p4 belief: p3's claim currently looks credible" + extra,
            owner_seat_id="p4",
            target_seat_id="p3",
            proposition="p3 claim looks credible",
            confidence=0.72,
            created_round=1,
            created_phase="day",
            generated_by=RUNTIME_EVIDENCE_SCENARIO_ID,
        )
        self._upsert_record("p4", commitment, signal_source=FIXTURE_SIGNAL_SOURCE)
        self._upsert_record("p4", belief, signal_source=FIXTURE_SIGNAL_SOURCE)

    def _apply_p4_memory_transition(self, observation: dict[str, Any]) -> None:
        key = "p4_memory_transition"
        if key in self._applied_fixture_signals:
            return
        self._applied_fixture_signals.add(key)
        source_ids = _visible_source_ids(
            observation,
            self._game_events,
            event_type="player_speech",
            actors={"p1", "p2", "p3"},
        )
        extra = _malicious_suffix(self.malicious_untrusted_text)
        commitment = _record(
            "runtime_commitment_p4_revisit_claim",
            kind="CommitmentRecord",
            section="commitments",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": ["p4"]},
            source_event_ids=source_ids,
            status="satisfied",
            summary=(
                "runtime p4 commitment: revisited p3's public claim before voting"
                + extra
            ),
            owner_seat_id="p4",
            proposition="revisit p3 public claim before voting",
            created_round=1,
            created_phase="day",
            status_reason="p4 reached the vote window after reviewing public claim evidence",
            generated_by=RUNTIME_EVIDENCE_SCENARIO_ID,
        )
        belief = _record(
            "runtime_belief_p4_p3_claim",
            kind="BeliefRecord",
            section="episodic_notes",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": ["p4"]},
            source_event_ids=source_ids,
            status="weakened",
            summary=(
                "runtime p4 belief: p3's claim remains useful but needs vote-proof support"
                + extra
            ),
            owner_seat_id="p4",
            target_seat_id="p3",
            proposition="p3 claim looks credible",
            confidence=0.48,
            created_round=1,
            created_phase="day",
            status_reason="public counterpressure reduced confidence before vote",
            generated_by=RUNTIME_EVIDENCE_SCENARIO_ID,
        )
        self._upsert_record("p4", commitment, signal_source=FIXTURE_SIGNAL_SOURCE)
        self._upsert_record("p4", belief, signal_source=FIXTURE_SIGNAL_SOURCE)

    def _upsert_record(
        self,
        seat_id: str,
        record: dict[str, Any],
        *,
        signal_source: str,
        source_event_id: str | None = None,
    ) -> None:
        record = {k: v for k, v in record.items() if v is not None}
        validate_memory_record(record)
        packet = self._packets.setdefault(seat_id, _empty_packet(self.run_id, seat_id))
        records = [
            existing
            for existing in packet["records"]
            if existing["record_id"] != record["record_id"]
        ]
        records.append(record)
        packet["records"] = records
        validate_agent_context_packet(packet)
        self._update_runtime_seat_state(seat_id, record)
        self._signals.append(
            {
                "scenario_id": self.scenario_id,
                "signal_source": signal_source,
                "not_model_extracted": True,
                "record_id": record["record_id"],
                "record_kind": record["kind"],
                "seat_id": seat_id,
                "status": record["status"],
                "visibility_scope": record["visibility_scope"],
                "source_event_ids": list(record["source_provenance"].get("source_event_ids", [])),
                "source_event_id": source_event_id,
                "record_hash": f"sha256:{_sha256_json(record)}",
                "note": (
                    FIXTURE_SIGNAL_NOTE
                    if signal_source == FIXTURE_SIGNAL_SOURCE
                    else "engine-derived runtime continuity fact; not model-extracted"
                ),
            }
        )

    def _update_runtime_seat_state(self, seat_id: str, record: dict[str, Any]) -> None:
        state = self._runtime_seat_states.get(seat_id)
        if state is None:
            return
        memory_records = list(state.get("memory_records", []))
        if record["record_id"] not in memory_records:
            memory_records.append(record["record_id"])
        state["memory_records"] = memory_records
        if record["kind"] == "CommitmentRecord":
            commitments = list(state.get("commitments", []))
            if record["record_id"] not in commitments:
                commitments.append(record["record_id"])
            state["commitments"] = commitments
        validate_runtime_seat_state(state)


def _record(
    record_id: str,
    *,
    kind: str,
    section: str,
    writer: str,
    visibility_scope: str,
    audience_scope: dict[str, list[str]],
    source_event_ids: list[str],
    status: str,
    summary: str,
    generated_by: str,
    trust_class: str = "run_derived",
    render_mode: str = "state_summary",
    **extra: Any,
) -> dict[str, Any]:
    record = {
        "record_id": record_id,
        "kind": kind,
        "section": section,
        "writer": writer,
        "visibility_scope": visibility_scope,
        "audience_scope": audience_scope,
        "trust_class": trust_class,
        "render_mode": render_mode,
        "source_provenance": {
            "source_event_ids": source_event_ids,
            "generated_by": generated_by,
        },
        "status": status,
        "summary": summary,
    }
    record.update(extra)
    return record


def _empty_packet(run_id: str, seat_id: str) -> dict[str, Any]:
    return {
        "schema_version": AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
        "run_id": run_id,
        "seat_id": seat_id,
        "decision_id": f"{run_id}_{seat_id}_runtime_continuity",
        "records": [],
        "context_budget": {"max_records": 8},
    }


def _existing_source_ids(packet: dict[str, Any] | None, record_id: str) -> list[str]:
    if packet is None:
        return []
    for record in packet.get("records", []):
        if record.get("record_id") == record_id:
            return list(record.get("source_provenance", {}).get("source_event_ids", []))
    return []


def _visible_source_ids(
    observation: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    event_type: str,
    actors: set[str],
) -> list[str]:
    visible = set(observation.get("public_event_ids", [])) | set(
        observation.get("private_event_ids", [])
    )
    ids: list[str] = []
    for event in events:
        if event.get("type") != event_type:
            continue
        if str(event.get("actor")) not in actors:
            continue
        event_id = str(event.get("event_id"))
        if event_id in visible:
            ids.append(event_id)
    return ids


def _malicious_suffix(text: str | None) -> str:
    return f" | untrusted text: {text}" if text else ""


def _sha256_json(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
