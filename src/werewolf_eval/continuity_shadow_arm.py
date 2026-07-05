"""P3-A-3 continuity shadow arm assets.

The arm is explicit opt-in and offline-oriented. It seeds continuity records so
prompt_v6 can be audited without pretending that natural-language commitment
extraction or long-running memory authoring is implemented.
"""

from __future__ import annotations

import hashlib
import json
import copy
from typing import Any

from werewolf_eval.agent_assets import (
    PUBLIC_RUN_MANIFEST_SCHEMA_VERSION,
    RUNTIME_SEAT_STATE_SCHEMA_VERSION,
    RUNTIME_TEAM_STATE_SCHEMA_VERSION,
    validate_runtime_seat_state,
    validate_runtime_team_state,
)
from werewolf_eval.agent_context_packet import (
    AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
    validate_agent_context_packet,
)
from werewolf_eval.role_policy_registry import RolePolicyRegistry, build_default_role_policy_registry
from werewolf_eval.roleplay_shadow_arm import (
    ROLEPLAY_SHADOW_ROLE_POLICY_PACK_ID,
    build_starter_seat_character_cards,
)

CONTINUITY_SHADOW_ARM_ID = "p3a_continuity_shadow"
CONTINUITY_SHADOW_AUDIT_SCHEMA_VERSION = "p3a.continuity_shadow_audit.v1"


def build_continuity_shadow_bundle(
    *,
    run_id: str,
    seat_roles: dict[str, str],
    provider_profile_id: str = "runtime_provider_default",
    malicious_untrusted_text: str | None = None,
) -> dict[str, Any]:
    """Build explicit prompt_v6 shadow assets for one run."""
    registry = build_default_role_policy_registry()
    if malicious_untrusted_text:
        registry = _registry_with_untrusted_text(registry, malicious_untrusted_text)
    pack = registry.get_pack(ROLEPLAY_SHADOW_ROLE_POLICY_PACK_ID)
    cards_by_id = build_starter_seat_character_cards()
    if malicious_untrusted_text:
        cards_by_id = _cards_with_untrusted_text(cards_by_id, malicious_untrusted_text)
    seat_cards = _assign_cards_to_seats(sorted(seat_roles), cards_by_id)
    wolf_seats = sorted(
        seat_id for seat_id, role in seat_roles.items() if role == "werewolf"
    )
    packets = {
        seat_id: _build_continuity_packet(
            run_id=run_id,
            seat_id=seat_id,
            role=role,
            wolf_seats=wolf_seats,
            malicious_untrusted_text=malicious_untrusted_text,
        )
        for seat_id, role in sorted(seat_roles.items())
    }
    runtime_seat_states = [
        _runtime_seat_state(
            run_id=run_id,
            seat_id=seat_id,
            role=seat_roles[seat_id],
            policy_ref=pack["role_policy_refs"][seat_roles[seat_id]],
            card=seat_cards[seat_id],
            provider_profile_id=provider_profile_id,
            packet=packets[seat_id],
        )
        for seat_id in sorted(seat_roles)
    ]
    runtime_team_states = []
    if wolf_seats:
        team_state = {
            "schema_version": RUNTIME_TEAM_STATE_SCHEMA_VERSION,
            "run_id": run_id,
            "team_id": "werewolf",
            "visibility_scope": "faction_private",
            "authorized_seat_ids": wolf_seats,
            "active_plan": "keep pressure distributed while protecting one wolf vote line",
            "shared_commitments": [],
        }
        validate_runtime_team_state(team_state)
        runtime_team_states.append(team_state)
    public_manifest = _build_public_manifest(run_id=run_id, seat_cards=seat_cards)
    audit = {
        "schema_version": CONTINUITY_SHADOW_AUDIT_SCHEMA_VERSION,
        "roleplay_arm": CONTINUITY_SHADOW_ARM_ID,
        "run_id": run_id,
        "visibility_scope": "postgame_only",
        "release_condition": "game_end",
        "public_run_manifest_hash": f"sha256:{_sha256_json(public_manifest)}",
        "record_inventory": [
            {
                "seat_id": seat_id,
                "record_ids": [record["record_id"] for record in packet["records"]],
                "record_kinds": sorted({record["kind"] for record in packet["records"]}),
            }
            for seat_id, packet in sorted(packets.items())
        ],
        "seat_private_asset_snapshots": [
            _seat_private_snapshot(
                run_id=run_id,
                seat_id=state["seat_id"],
                role=seat_roles[state["seat_id"]],
                card=seat_cards[state["seat_id"]],
                policy_ref=pack["role_policy_refs"][seat_roles[state["seat_id"]]],
                runtime_state=state,
            )
            for state in runtime_seat_states
        ],
        "faction_private_asset_snapshots": [
            {
                "run_id": run_id,
                "team_id": state["team_id"],
                "visibility_scope": state["visibility_scope"],
                "authorized_seat_ids": list(state["authorized_seat_ids"]),
                "runtime_team_state_hash": f"sha256:{_sha256_json(state)}",
            }
            for state in runtime_team_states
        ],
        "postgame_audit_note": (
            "Continuity shadow records are deterministic seeds for offline "
            "prompt_v6 context compilation; they are not natural-language "
            "memory extraction and do not alter engine authority."
        ),
    }
    return {
        "roleplay_arm": CONTINUITY_SHADOW_ARM_ID,
        "role_policy_registry": registry,
        "role_policy_pack_id": ROLEPLAY_SHADOW_ROLE_POLICY_PACK_ID,
        "seat_character_cards": seat_cards,
        "runtime_seat_states": runtime_seat_states,
        "runtime_team_states": runtime_team_states,
        "agent_context_packets": packets,
        "public_run_manifest": public_manifest,
        "postgame_audit_artifact": audit,
    }


def _assign_cards_to_seats(
    seat_ids: list[str],
    cards_by_id: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    card_ids = ("calm_logician", "pressure_tester", "quiet_tracker")
    return {
        seat_id: dict(cards_by_id[card_ids[index % len(card_ids)]])
        for index, seat_id in enumerate(seat_ids)
    }


def _runtime_seat_state(
    *,
    run_id: str,
    seat_id: str,
    role: str,
    policy_ref: str,
    card: dict[str, Any],
    provider_profile_id: str,
    packet: dict[str, Any],
) -> dict[str, Any]:
    policy_id, _ = policy_ref.rsplit("@", 1)
    state = {
        "schema_version": RUNTIME_SEAT_STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "seat_id": seat_id,
        "initialized_from": {
            "seat_character_card_id": card["card_id"],
            "role_policy_id": policy_id,
            "provider_profile_id": provider_profile_id,
        },
        "status": "active",
        "memory_records": [record["record_id"] for record in packet["records"]],
        "commitments": [
            record["record_id"]
            for record in packet["records"]
            if record["kind"] == "CommitmentRecord"
        ],
        "context_budget": {"max_records": 8},
    }
    validate_runtime_seat_state(state)
    return state


def _build_continuity_packet(
    *,
    run_id: str,
    seat_id: str,
    role: str,
    wolf_seats: list[str],
    malicious_untrusted_text: str | None = None,
) -> dict[str, Any]:
    untrusted_suffix = (
        f" | untrusted text: {malicious_untrusted_text}"
        if malicious_untrusted_text
        else ""
    )
    records: list[dict[str, Any]] = [
        _record(
            f"{seat_id}_public_claim_day1",
            kind="ClaimRecord",
            section="public_timeline",
            writer="public_event",
            visibility_scope="public",
            audience_scope={"seat_ids": []},
            render_mode="quoted_evidence",
            source_event_ids=["synthetic_e_day1_claim"],
            status="active",
            summary="p3 publicly claimed a check result on p1" + untrusted_suffix,
        ),
        _record(
            f"{seat_id}_commitment_active",
            kind="CommitmentRecord",
            section="commitments",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["synthetic_e_day1_commitment"],
            status="active",
            summary=f"{seat_id} committed to revisit p3's claim before the next vote{untrusted_suffix}",
            owner_seat_id=seat_id,
            proposition="revisit p3 claim before next vote",
            created_round=1,
            created_phase="day",
        ),
        _record(
            f"{seat_id}_belief_weakened",
            kind="BeliefRecord",
            section="episodic_notes",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["synthetic_e_day1_vote", "synthetic_e_day2_claim"],
            status="weakened",
            summary=f"{seat_id} suspected p3, but the later claim evidence reduced confidence{untrusted_suffix}",
            owner_seat_id=seat_id,
            target_seat_id="p3",
            proposition="p3 is suspicious",
            confidence=0.35,
            evidence_refs=["synthetic_e_day1_vote", "synthetic_e_day2_claim"],
            created_round=1,
            created_phase="day",
            status_reason="later public claim evidence reduced confidence",
        ),
    ]
    ability = _ability_record_for_role(run_id=run_id, seat_id=seat_id, role=role)
    if ability is not None:
        records.append(ability)
    if seat_id in wolf_seats:
        records.append(
            _record(
                "werewolf_team_plan_continuity",
                kind="TeamPlanRecord",
                section="team_memory",
                writer="team_scaffold",
                visibility_scope="faction_private",
                audience_scope={
                    "team_ids": ["werewolf"],
                    "authorized_seat_ids": wolf_seats,
                },
                source_event_ids=["synthetic_e_wolf_channel"],
                status="active",
                summary="keep pressure distributed while protecting one wolf vote line"
                + untrusted_suffix,
            )
        )
    packet = {
        "schema_version": AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
        "run_id": run_id,
        "seat_id": seat_id,
        "decision_id": f"{run_id}_{seat_id}_continuity_seed",
        "records": records,
        "context_budget": {
            "included_blocks": [],
            "compacted_blocks": [],
            "dropped_blocks": [],
        },
    }
    validate_agent_context_packet(packet)
    return packet


def _ability_record_for_role(
    *,
    run_id: str,
    seat_id: str,
    role: str,
) -> dict[str, Any] | None:
    if role == "witch":
        return _record(
            f"ability_{seat_id}_witch_potions",
            kind="AbilityHistoryRecord",
            section="ability_history",
            writer="runtime",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["synthetic_e_witch_save_r1"],
            status="active",
            summary="Night1 antidote used=True; poison_used=False; visible victim was p5",
            ability_name="witch_potions",
            ability_state="antidote_used_true_poison_unused",
            owner_seat_id=seat_id,
            created_round=2,
            created_phase="day",
        )
    if role == "seer":
        return _record(
            f"ability_{seat_id}_seer_checks",
            kind="AbilityHistoryRecord",
            section="ability_history",
            writer="runtime",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["synthetic_e_seer_check_r1"],
            status="active",
            summary="Night1 check target=p1 result=werewolf",
            ability_name="seer_check",
            ability_state="night1_p1_werewolf",
            owner_seat_id=seat_id,
            target_seat_id="p1",
            created_round=2,
            created_phase="day",
        )
    if role == "guard":
        return _record(
            f"ability_{seat_id}_guard_history",
            kind="AbilityHistoryRecord",
            section="ability_history",
            writer="runtime",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["synthetic_e_guard_protect_r1"],
            status="active",
            summary="Night1 protected p3; Night2 cannot repeat p3",
            ability_name="guard_protect",
            ability_state="last_guarded_target_p3",
            owner_seat_id=seat_id,
            target_seat_id="p3",
            created_round=2,
            created_phase="night",
        )
    if role == "hunter":
        return _record(
            f"ability_{seat_id}_hunter_trigger",
            kind="AbilityHistoryRecord",
            section="ability_history",
            writer="runtime",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["synthetic_e_hunter_state"],
            status="active",
            summary="Hunter trigger remains available unless death cause is witch_poison",
            ability_name="hunter_shoot",
            ability_state="trigger_available",
            owner_seat_id=seat_id,
            created_round=2,
            created_phase="day",
        )
    return None


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
    render_mode: str = "state_summary",
    trust_class: str = "run_derived",
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
            "generated_by": CONTINUITY_SHADOW_ARM_ID,
        },
        "status": status,
        "summary": summary,
    }
    record.update(extra)
    return record


def _build_public_manifest(
    *,
    run_id: str,
    seat_cards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "roleplay_arm": CONTINUITY_SHADOW_ARM_ID,
        "visibility_scope": "public",
        "release_condition": "immediate",
        "seats": [
            {
                "seat_id": seat_id,
                "controller": "ai",
                "public_card": {
                    "display_name": card["display_name"],
                    "summary": card["summary"],
                    "card_hash_public": f"sha256:{_sha256_json(_public_card_body(card))}",
                },
            }
            for seat_id, card in sorted(seat_cards.items())
        ],
        "execution_contract_summary": {
            "prompt_template_version": "prompt_v6",
            "action_schema_version": "g1d-action-v1",
            "roleplay_context_schema_version": "prompt_v6.continuity_context.v1",
            "context_selector_version": "p3a.context_selector.v1",
        },
    }


def _seat_private_snapshot(
    *,
    run_id: str,
    seat_id: str,
    role: str,
    card: dict[str, Any],
    policy_ref: str,
    runtime_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "seat_id": seat_id,
        "visibility_scope": "seat_private",
        "release_condition": "audit_authorized",
        "true_role": role,
        "team": "werewolf" if role == "werewolf" else "villager",
        "seat_character_card_hash": f"sha256:{_sha256_json(card)}",
        "role_policy_ref": {
            "hash": f"sha256:{hashlib.sha256(policy_ref.encode('utf-8')).hexdigest()}",
            "policy_selection_reason": "engine_true_role_after_assignment",
        },
        "runtime_seat_state_hash": f"sha256:{_sha256_json(runtime_state)}",
    }


def _public_card_body(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "display_name": card["display_name"],
        "summary": card["summary"],
    }


def _registry_with_untrusted_text(
    registry: RolePolicyRegistry,
    malicious_untrusted_text: str,
) -> RolePolicyRegistry:
    data = registry.export()
    for policy in data["policies"].values():
        goals = list(policy.get("goals", []))
        goals.append(malicious_untrusted_text)
        policy["goals"] = goals
    return RolePolicyRegistry(
        packs=data["packs"],
        policies=data["policies"],
        drafts=data.get("drafts", {}),
    )


def _cards_with_untrusted_text(
    cards_by_id: dict[str, dict[str, Any]],
    malicious_untrusted_text: str,
) -> dict[str, dict[str, Any]]:
    cards = copy.deepcopy(cards_by_id)
    for card in cards.values():
        personality = list(card.get("personality", []))
        personality.append(malicious_untrusted_text)
        card["personality"] = personality
    return cards


def _sha256_json(obj: object) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
