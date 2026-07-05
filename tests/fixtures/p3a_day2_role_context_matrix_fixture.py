"""Synthetic P3-A-3 context compiler fixture.

This fixture is not a GameState, not a runnable match, and not a product board.
It exists only to compile prompt_v6 contexts for six role perspectives against
one shared Day2 public timeline. The private snapshots below are independent
role-safe examples and must never be fed into the normal game loop, win-rate
tests, or generated game artifacts.
"""

from __future__ import annotations

from typing import Any

from werewolf_eval.agent_context_packet import (
    AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
    validate_agent_context_packet,
)
from werewolf_eval.prompt_v6 import render_continuity_context_suffix
from werewolf_eval.role_policy_registry import build_default_role_policy_registry
from werewolf_eval.roleplay_shadow_arm import build_starter_seat_character_cards

PUBLIC_TIMELINE = [
    {
        "event_id": "matrix_e1",
        "round": 1,
        "phase": "day",
        "type": "player_speech",
        "summary": "p2 claimed a seer result on p1.",
    },
    {
        "event_id": "matrix_e2",
        "round": 1,
        "phase": "day",
        "type": "player_vote",
        "summary": "Votes split between p1 and p2.",
    },
    {
        "event_id": "matrix_e3",
        "round": 2,
        "phase": "day",
        "type": "day_announcement",
        "summary": "Day2 begins after one night result.",
    },
]

ROLE_SNAPSHOTS = {
    "Werewolf": ("p1", "werewolf", "werewolf"),
    "Seer": ("p2", "seer", "villager"),
    "Witch": ("p3", "witch", "villager"),
    "Villager": ("p4", "villager", "villager"),
    "Guard": ("p5", "guard", "villager"),
    "Hunter": ("p6", "hunter", "villager"),
}


def compile_synthetic_day2_role_context_matrix() -> dict[str, dict[str, Any]]:
    registry = build_default_role_policy_registry()
    pack = registry.get_pack("standard_six_player_balanced")
    cards = build_starter_seat_character_cards()
    card_ids = ("calm_logician", "pressure_tester", "quiet_tracker")
    compiled: dict[str, dict[str, Any]] = {}
    wolf_seats = ["p1"]
    for index, (label, (seat_id, role, team)) in enumerate(ROLE_SNAPSHOTS.items()):
        packet = _packet_for_role(seat_id=seat_id, role=role, team=team, wolf_seats=wolf_seats)
        policy = registry.resolve_policy_ref(pack["role_policy_refs"][role])
        rendered = render_continuity_context_suffix(
            role_policy=policy,
            agent_context_packet=packet,
            seat_character_card=cards[card_ids[index % len(card_ids)]],
            seat_id=seat_id,
            team_ids={team},
            action_contract=_action_contract(role),
            public_timeline=PUBLIC_TIMELINE,
        )
        compiled[label] = {
            "seat_id": seat_id,
            "role": role,
            "team": team,
            "rendered": rendered,
            "packet": packet,
        }
    return compiled


def _action_contract(role: str) -> dict[str, Any]:
    if role == "guard":
        return {
            "phase": "night",
            "round": 2,
            "allowed_actions": ["guard_protect"],
            "allowed_targets": ["p1", "p2", "p3", "p4", "p6"],
        }
    if role == "hunter":
        return {
            "phase": "hunter_shot",
            "round": 2,
            "allowed_actions": ["hunter_shoot", "hunter_pass"],
            "allowed_targets": ["p1", "p2", "p3", "p4", "p5"],
        }
    return {
        "phase": "day",
        "round": 2,
        "allowed_actions": ["player_speech"],
        "allowed_targets": [],
    }


def _packet_for_role(
    *,
    seat_id: str,
    role: str,
    team: str,
    wolf_seats: list[str],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = [
        _record(
            f"{seat_id}_claim_public",
            kind="ClaimRecord",
            section="public_timeline",
            writer="public_event",
            visibility_scope="public",
            audience_scope={"seat_ids": []},
            render_mode="quoted_evidence",
            source_event_ids=["matrix_e1"],
            status="active",
            summary="p2 claimed p1 is werewolf",
        ),
        _record(
            f"{seat_id}_commitment_active",
            kind="CommitmentRecord",
            section="commitments",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["matrix_e1"],
            status="active",
            summary=f"{seat_id} promised to re-evaluate the p2 claim on Day2",
            owner_seat_id=seat_id,
            proposition="re-evaluate p2 claim on Day2",
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
            source_event_ids=["matrix_e1", "matrix_e2"],
            status="weakened",
            summary=f"{seat_id} suspected p2, but the vote split weakened that read",
            owner_seat_id=seat_id,
            target_seat_id="p2",
            proposition="p2 is suspicious",
            confidence=0.4,
            evidence_refs=["matrix_e1", "matrix_e2"],
            created_round=1,
            created_phase="day",
            status_reason="vote split conflicts with the first read",
        ),
        _record(
            f"{seat_id}_belief_replacement",
            kind="BeliefRecord",
            section="episodic_notes",
            writer="seat_agent",
            visibility_scope="seat_private",
            audience_scope={"seat_ids": [seat_id]},
            source_event_ids=["matrix_e2", "matrix_e3"],
            status="active",
            summary=f"{seat_id} now tracks p1 and p2 as a linked conflict",
            owner_seat_id=seat_id,
            proposition="p1/p2 conflict should be resolved before side votes",
            confidence=0.7,
            evidence_refs=["matrix_e2", "matrix_e3"],
            created_round=2,
            created_phase="day",
            supersedes=[f"{seat_id}_belief_weakened"],
        ),
    ]
    ability = _ability_for_role(seat_id=seat_id, role=role)
    if ability is not None:
        records.append(ability)
    if team == "werewolf":
        records.append(
            _record(
                "matrix_wolf_team_plan",
                kind="TeamPlanRecord",
                section="team_memory",
                writer="team_scaffold",
                visibility_scope="faction_private",
                audience_scope={
                    "team_ids": ["werewolf"],
                    "authorized_seat_ids": wolf_seats,
                },
                source_event_ids=["matrix_wolf_private"],
                status="active",
                summary="push the p1/p2 conflict without exposing the remaining wolf",
            )
        )
    packet = {
        "schema_version": AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
        "run_id": "synthetic_context_matrix",
        "seat_id": seat_id,
        "decision_id": f"matrix_day2_{seat_id}",
        "records": records,
        "context_budget": {
            "included_blocks": [],
            "compacted_blocks": [],
            "dropped_blocks": [],
        },
    }
    validate_agent_context_packet(packet)
    return packet


def _ability_for_role(seat_id: str, role: str) -> dict[str, Any] | None:
    by_role = {
        "seer": ("seer_check", "Night1 check target=p1 result=werewolf", "matrix_e_seer"),
        "witch": (
            "witch_potions",
            "Night1 antidote used=True; poison_used=False; visible victim was p4",
            "matrix_e_witch",
        ),
        "guard": (
            "guard_protect",
            "Night1 protected p3; Night2 cannot repeat p3",
            "matrix_e_guard",
        ),
        "hunter": (
            "hunter_shoot",
            "Trigger available if death cause is not witch_poison",
            "matrix_e_hunter",
        ),
    }
    if role not in by_role:
        return None
    ability_name, summary, event_id = by_role[role]
    return _record(
        f"ability_{seat_id}_{ability_name}",
        kind="AbilityHistoryRecord",
        section="ability_history",
        writer="runtime",
        visibility_scope="seat_private",
        audience_scope={"seat_ids": [seat_id]},
        source_event_ids=[event_id],
        status="active",
        summary=summary,
        ability_name=ability_name,
        ability_state=summary,
        owner_seat_id=seat_id,
        created_round=2,
        created_phase="day",
    )


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
            "generated_by": "p3a_day2_role_context_matrix_fixture",
        },
        "status": status,
        "summary": summary,
    }
    record.update(extra)
    return record
