"""P3-A-4 starter roleplay arm assets.

This module builds the first shadow-safe roleplay arm without changing engine
authority. All assets are run-scoped projections: public output gets only
role-agnostic card summaries, while true-role policy refs and team state stay
seat/faction private or postgame-only audit data.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from werewolf_eval.agent_assets import (
    PUBLIC_RUN_MANIFEST_SCHEMA_VERSION,
    RUNTIME_SEAT_STATE_SCHEMA_VERSION,
    RUNTIME_TEAM_STATE_SCHEMA_VERSION,
    SEAT_CHARACTER_CARD_SCHEMA_VERSION,
    validate_runtime_seat_state,
    validate_runtime_team_state,
    validate_seat_character_card,
)
from werewolf_eval.agent_context_packet import (
    AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
    validate_agent_context_packet,
)
from werewolf_eval.role_policy_registry import build_default_role_policy_registry

ROLEPLAY_SHADOW_ARM_ID = "p3a_roleplay_shadow"
ROLEPLAY_SHADOW_AUDIT_SCHEMA_VERSION = "p3a.roleplay_shadow_audit.v1"
ROLEPLAY_SHADOW_ROLE_POLICY_PACK_ID = "standard_six_player_balanced"


def build_starter_seat_character_cards() -> dict[str, dict[str, Any]]:
    """Return built-in, role-agnostic starter cards for P3-A-4."""
    cards = {
        "calm_logician": {
            "display_name": "Calm Logician",
            "summary": "Careful evidence tracker; speaks with explicit uncertainty.",
            "personality": ["calm", "evidence-driven", "reluctant to overclaim"],
            "speech_style": ["short claims", "names concrete observations"],
            "social_tendencies": ["asks for reasons before joining pressure"],
        },
        "pressure_tester": {
            "display_name": "Pressure Tester",
            "summary": "Probes weak stories and invites others to commit publicly.",
            "personality": ["direct", "skeptical", "comfortable applying pressure"],
            "speech_style": ["pointed questions", "clear vote intent"],
            "social_tendencies": ["tests reactions before hard commitment"],
        },
        "quiet_tracker": {
            "display_name": "Quiet Tracker",
            "summary": "Low-volume observer who remembers promises and vote shifts.",
            "personality": ["reserved", "patient", "detail-oriented"],
            "speech_style": ["concise notes", "timeline references"],
            "social_tendencies": ["waits for contradictions before speaking strongly"],
        },
    }
    built: dict[str, dict[str, Any]] = {}
    for card_id, body in cards.items():
        card = {
            "schema_version": SEAT_CHARACTER_CARD_SCHEMA_VERSION,
            "card_id": card_id,
            "version": "1.0.0",
            "display_name": body["display_name"],
            "summary": body["summary"],
            "personality": body["personality"],
            "speech_style": body["speech_style"],
            "social_tendencies": body["social_tendencies"],
            "role_scope": "role_agnostic",
            "asset_certification": {
                "status": "built_in_vetted",
                "attribution_eligible": True,
            },
        }
        validate_seat_character_card(card)
        built[card_id] = card
    return built


def build_roleplay_shadow_bundle(
    *,
    run_id: str,
    seat_roles: dict[str, str],
    provider_profile_id: str = "runtime_provider_default",
) -> dict[str, Any]:
    """Build run-scoped assets for the explicit P3-A-4 shadow arm."""
    registry = build_default_role_policy_registry()
    pack = registry.get_pack(ROLEPLAY_SHADOW_ROLE_POLICY_PACK_ID)
    cards_by_id = build_starter_seat_character_cards()
    seat_cards = _assign_cards_to_seats(sorted(seat_roles), cards_by_id)
    wolf_seats = sorted(
        seat_id for seat_id, role in seat_roles.items() if role == "werewolf"
    )

    runtime_seat_states = []
    for seat_id in sorted(seat_roles):
        role = seat_roles[seat_id]
        policy_ref = pack["role_policy_refs"][role]
        policy_id, _ = policy_ref.rsplit("@", 1)
        state = {
            "schema_version": RUNTIME_SEAT_STATE_SCHEMA_VERSION,
            "run_id": run_id,
            "seat_id": seat_id,
            "initialized_from": {
                "seat_character_card_id": seat_cards[seat_id]["card_id"],
                "role_policy_id": policy_id,
                "provider_profile_id": provider_profile_id,
            },
            "status": "active",
            "memory_records": [],
            "context_budget": {"max_records": 6},
        }
        validate_runtime_seat_state(state)
        runtime_seat_states.append(state)

    runtime_team_states = []
    if wolf_seats:
        team_state = {
            "schema_version": RUNTIME_TEAM_STATE_SCHEMA_VERSION,
            "run_id": run_id,
            "team_id": "werewolf",
            "visibility_scope": "faction_private",
            "authorized_seat_ids": wolf_seats,
            "active_plan": "maintain flexible pressure without synchronized exposure",
        }
        validate_runtime_team_state(team_state)
        runtime_team_states.append(team_state)

    packets = {
        seat_id: _build_agent_context_packet(
            run_id=run_id,
            seat_id=seat_id,
            is_wolf=seat_id in wolf_seats,
            wolf_seats=wolf_seats,
        )
        for seat_id in sorted(seat_roles)
    }

    public_manifest = _build_public_manifest(
        run_id=run_id,
        seat_cards=seat_cards,
    )
    audit = {
        "schema_version": ROLEPLAY_SHADOW_AUDIT_SCHEMA_VERSION,
        "roleplay_arm": ROLEPLAY_SHADOW_ARM_ID,
        "run_id": run_id,
        "visibility_scope": "postgame_only",
        "release_condition": "game_end",
        "public_run_manifest_hash": f"sha256:{_sha256_json(public_manifest)}",
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
            "Roleplay arm assets are shadow-scoped; public live manifest omits "
            "true roles, teams, and RolePolicy refs."
        ),
    }

    return {
        "roleplay_arm": ROLEPLAY_SHADOW_ARM_ID,
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


def _build_agent_context_packet(
    *,
    run_id: str,
    seat_id: str,
    is_wolf: bool,
    wolf_seats: list[str],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = [
        {
            "record_id": f"{seat_id}_belief_seed",
            "kind": "BeliefRecord",
            "section": "episodic_notes",
            "writer": "seat_agent",
            "visibility_scope": "seat_private",
            "audience_scope": {"seat_ids": [seat_id]},
            "trust_class": "run_derived",
            "render_mode": "state_summary",
            "source_provenance": {
                "static_source": ROLEPLAY_SHADOW_ARM_ID,
                "generated_by": "roleplay_shadow_arm",
            },
            "status": "active",
            "summary": "early suspicions must remain revisable until public evidence accumulates",
        }
    ]
    if is_wolf:
        records.append(
            {
                "record_id": "werewolf_team_plan_seed",
                "kind": "TeamPlanRecord",
                "section": "team_memory",
                "writer": "team_scaffold",
                "visibility_scope": "faction_private",
                "audience_scope": {
                    "team_ids": ["werewolf"],
                    "authorized_seat_ids": wolf_seats,
                },
                "trust_class": "run_derived",
                "render_mode": "state_summary",
                "source_provenance": {
                    "static_source": ROLEPLAY_SHADOW_ARM_ID,
                    "generated_by": "roleplay_shadow_arm",
                },
                "status": "active",
                "summary": "maintain flexible pressure without synchronized exposure",
            }
        )
    packet = {
        "schema_version": AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
        "run_id": run_id,
        "seat_id": seat_id,
        "decision_id": f"{run_id}_{seat_id}_shadow_seed",
        "records": records,
        "context_budget": {
            "included_blocks": [],
            "compacted_blocks": [],
            "dropped_blocks": [],
        },
    }
    validate_agent_context_packet(packet)
    return packet


def _build_public_manifest(
    *,
    run_id: str,
    seat_cards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "roleplay_arm": ROLEPLAY_SHADOW_ARM_ID,
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
            "prompt_template_version": "prompt_v5",
            "action_schema_version": "g1d-action-v1",
            "roleplay_context_schema_version": "prompt_v5.roleplay_context.v1",
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


def _sha256_json(obj: object) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
