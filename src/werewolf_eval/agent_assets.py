"""P3-A agent asset schema helpers.

This module is deliberately pure and runtime-neutral. It validates and projects
the P3-A asset ownership model without changing provider calls, prompt bytes, or
engine adjudication.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from werewolf_eval.action_runtime.ruleset import known_role_teams
from werewolf_eval.profile_config import resolve_profile_for_run

SEAT_CHARACTER_CARD_SCHEMA_VERSION = "p3a.seat_character_card.v1"
ROLE_POLICY_SCHEMA_VERSION = "p3a.role_policy.v1"
RUNTIME_SEAT_STATE_SCHEMA_VERSION = "p3a.runtime_seat_state.v1"
RUNTIME_TEAM_STATE_SCHEMA_VERSION = "p3a.runtime_team_state.v1"
PROVIDER_PROFILE_SCHEMA_VERSION = "p3a.provider_profile.v1"
EXECUTION_CONTRACT_SCHEMA_VERSION = "p3a.execution_contract.v1"
AGENT_PRESET_SCHEMA_VERSION = "p3a.agent_preset.v1"
PUBLIC_RUN_MANIFEST_SCHEMA_VERSION = "p3a.public_run_manifest.v1"
SEAT_PRIVATE_ASSET_SNAPSHOT_SCHEMA_VERSION = "p3a.seat_private_asset_snapshot.v1"
FACTION_PRIVATE_ASSET_SNAPSHOT_SCHEMA_VERSION = "p3a.faction_private_asset_snapshot.v1"
POSTGAME_AUDIT_ASSET_SNAPSHOT_SCHEMA_VERSION = "p3a.postgame_audit_asset_snapshot.v1"

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")
_SEAT_RE = re.compile(r"^p[1-9][0-9]*$")
_CERTIFICATION_STATUSES = frozenset(
    {"built_in_vetted", "user_unreviewed", "legacy_opaque"}
)
_VISIBILITY_SCOPES = frozenset(
    {"public", "seat_private", "faction_private", "engine_only", "postgame_only"}
)
_RELEASE_CONDITIONS = frozenset({"immediate", "game_end", "audit_authorized"})
_PROVIDER_PROFILE_FORBIDDEN_KEYS = frozenset(
    {
        "prompt_template_version",
        "prompt_renderer_version",
        "action_schema_version",
        "tool_capability_manifest_version",
        "context_selector_version",
        "response_parser_version",
        "fallback_behavior_version",
        "visibility_oracle_version",
        "agent_session_version",
        "decision_loop_policy_version",
    }
)
_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "secret",
    "token",
    "bearer",
    "password",
    "credential",
    "access_key",
)
_VALUE_SECRET_MARKERS = (
    "sk-",
    "bearer ",
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "access_key",
    "deepseek_api_key",
)
_SECRET_KEY_EXEMPTIONS = frozenset({"credential_slot", "max_tokens"})


class AgentAssetValidationError(ValueError):
    """Raised when a P3-A asset object violates schema ownership rules."""


def _sha256_json(obj: object) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _check_object(obj: object, *, where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise AgentAssetValidationError(f"{where} must be an object")
    _reject_secret_like_keys(obj)
    _reject_secret_like_values(obj)
    return obj


def _check_schema(obj: dict[str, Any], expected: str, *, where: str) -> None:
    if obj.get("schema_version") != expected:
        raise AgentAssetValidationError(
            f"{where}.schema_version must be {expected!r}"
        )


def _check_required(obj: dict[str, Any], required: set[str], *, where: str) -> None:
    missing = sorted(required - set(obj))
    if missing:
        raise AgentAssetValidationError(f"{where} missing required keys: {missing}")


def _check_no_extra(
    obj: dict[str, Any],
    allowed: set[str],
    *,
    where: str,
) -> None:
    extra = sorted(set(obj) - allowed)
    if extra:
        raise AgentAssetValidationError(f"{where} has unexpected keys: {extra}")


def _check_id(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_RE.match(value):
        raise AgentAssetValidationError(f"{where} must be a safe id string")
    return value


def _check_optional_str_list(value: object, *, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise AgentAssetValidationError(f"{where} must be a list of strings")


def _check_seat_id(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SEAT_RE.match(value):
        raise AgentAssetValidationError(f"{where} must be a seat id like p1")
    return value


def _check_visibility_scope(value: object, *, where: str) -> str:
    if value not in _VISIBILITY_SCOPES:
        raise AgentAssetValidationError(f"{where} has invalid visibility_scope")
    return str(value)


def _reject_secret_like_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key).lower()
            if key_text not in _SECRET_KEY_EXEMPTIONS and any(
                frag in key_text for frag in _SECRET_KEY_FRAGMENTS
            ):
                raise AgentAssetValidationError(
                    f"secret-like key not allowed: {path}{key}"
                )
            _reject_secret_like_keys(value, f"{path}{key}.")
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _reject_secret_like_keys(item, f"{path}{index}.")


def _reject_secret_like_values(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            _reject_secret_like_values(value, f"{path}{key}.")
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _reject_secret_like_values(item, f"{path}{index}.")
    elif isinstance(obj, str):
        lowered = obj.lower()
        if any(marker in lowered for marker in _VALUE_SECRET_MARKERS):
            raise AgentAssetValidationError(
                f"secret-like value not allowed at {path.rstrip('.')}"
            )


def validate_seat_character_card(card: object) -> None:
    card = _check_object(card, where="SeatCharacterCard")
    allowed = {
        "schema_version",
        "card_id",
        "version",
        "display_name",
        "summary",
        "personality",
        "speech_style",
        "social_tendencies",
        "example_dialogue",
        "role_scope",
        "asset_certification",
        "metadata",
    }
    _check_no_extra(card, allowed, where="SeatCharacterCard")
    _check_schema(card, SEAT_CHARACTER_CARD_SCHEMA_VERSION, where="SeatCharacterCard")
    _check_required(
        card,
        {"schema_version", "card_id", "version", "display_name", "summary", "role_scope", "asset_certification"},
        where="SeatCharacterCard",
    )
    _check_id(card["card_id"], where="SeatCharacterCard.card_id")
    _check_id(card["version"], where="SeatCharacterCard.version")
    if card["role_scope"] != "role_agnostic":
        raise AgentAssetValidationError("SeatCharacterCard.role_scope must be role_agnostic")
    cert = _check_object(card["asset_certification"], where="SeatCharacterCard.asset_certification")
    if cert.get("status") not in _CERTIFICATION_STATUSES:
        raise AgentAssetValidationError("SeatCharacterCard.asset_certification.status invalid")
    if "attribution_eligible" in cert and not isinstance(cert["attribution_eligible"], bool):
        raise AgentAssetValidationError("SeatCharacterCard.asset_certification.attribution_eligible must be boolean")
    if "personality" in card:
        _check_optional_str_list(card["personality"], where="SeatCharacterCard.personality")


def validate_role_policy(policy: object) -> None:
    policy = _check_object(policy, where="RolePolicy")
    allowed = {
        "schema_version",
        "policy_id",
        "version",
        "role",
        "applicability",
        "fallback_policy",
        "goals",
        "information_priorities",
        "ability_use_policy",
        "claim_policy",
        "deception_policy",
        "team_policy",
        "playbook_refs",
        "forbidden_behavior",
    }
    _check_no_extra(policy, allowed, where="RolePolicy")
    _check_schema(policy, ROLE_POLICY_SCHEMA_VERSION, where="RolePolicy")
    _check_required(
        policy,
        {"schema_version", "policy_id", "version", "role", "applicability", "fallback_policy", "goals"},
        where="RolePolicy",
    )
    _check_id(policy["policy_id"], where="RolePolicy.policy_id")
    _check_id(policy["version"], where="RolePolicy.version")
    if policy["role"] not in known_role_teams():
        raise AgentAssetValidationError(f"RolePolicy.role unknown: {policy['role']!r}")
    applicability = _check_object(policy["applicability"], where="RolePolicy.applicability")
    _check_required(
        applicability,
        {"ruleset_id", "seat_count", "required_roles", "phase_protocol_version"},
        where="RolePolicy.applicability",
    )
    if not isinstance(applicability["seat_count"], list) or not all(
        isinstance(x, int) and x > 0 for x in applicability["seat_count"]
    ):
        raise AgentAssetValidationError("RolePolicy.applicability.seat_count must be positive integers")
    _check_optional_str_list(applicability["required_roles"], where="RolePolicy.applicability.required_roles")
    if policy["fallback_policy"] not in {"reject", "explicit_compatibility"}:
        raise AgentAssetValidationError("RolePolicy.fallback_policy invalid")
    _check_optional_str_list(policy["goals"], where="RolePolicy.goals")


def validate_runtime_seat_state(state: object) -> None:
    state = _check_object(state, where="RuntimeSeatState")
    allowed = {
        "schema_version",
        "run_id",
        "seat_id",
        "initialized_from",
        "status",
        "seen_event_cursor",
        "public_speech_summary",
        "memory_records",
        "suspicion_graph",
        "commitments",
        "active_intent",
        "private_notes",
        "decision_history",
        "last_decision_result",
        "context_budget",
        "last_updated_event_id",
    }
    _check_no_extra(state, allowed, where="RuntimeSeatState")
    _check_schema(state, RUNTIME_SEAT_STATE_SCHEMA_VERSION, where="RuntimeSeatState")
    _check_required(
        state,
        {"schema_version", "run_id", "seat_id", "initialized_from", "status"},
        where="RuntimeSeatState",
    )
    _check_id(state["run_id"], where="RuntimeSeatState.run_id")
    _check_seat_id(state["seat_id"], where="RuntimeSeatState.seat_id")
    if state["status"] not in {"active", "dead", "left", "human_controlled"}:
        raise AgentAssetValidationError("RuntimeSeatState.status invalid")
    init = _check_object(state["initialized_from"], where="RuntimeSeatState.initialized_from")
    _check_required(
        init,
        {"seat_character_card_id", "role_policy_id", "provider_profile_id"},
        where="RuntimeSeatState.initialized_from",
    )


def validate_runtime_team_state(state: object) -> None:
    state = _check_object(state, where="RuntimeTeamState")
    allowed = {
        "schema_version",
        "run_id",
        "team_id",
        "visibility_scope",
        "authorized_seat_ids",
        "active_plan",
        "teammate_public_risk",
        "night_target_candidates",
        "shared_commitments",
        "team_message_history",
        "revision_history",
    }
    _check_no_extra(state, allowed, where="RuntimeTeamState")
    _check_schema(state, RUNTIME_TEAM_STATE_SCHEMA_VERSION, where="RuntimeTeamState")
    _check_required(
        state,
        {"schema_version", "run_id", "team_id", "visibility_scope", "authorized_seat_ids"},
        where="RuntimeTeamState",
    )
    _check_id(state["run_id"], where="RuntimeTeamState.run_id")
    if state["team_id"] not in {"werewolf", "villager"}:
        raise AgentAssetValidationError("RuntimeTeamState.team_id invalid")
    if state["visibility_scope"] != "faction_private":
        raise AgentAssetValidationError("RuntimeTeamState.visibility_scope must be faction_private")
    if not isinstance(state["authorized_seat_ids"], list) or not state["authorized_seat_ids"]:
        raise AgentAssetValidationError("RuntimeTeamState.authorized_seat_ids must be non-empty")
    for seat_id in state["authorized_seat_ids"]:
        _check_seat_id(seat_id, where="RuntimeTeamState.authorized_seat_ids")


def require_runtime_team_state_authorized(
    state: dict[str, Any],
    seat_id: str,
) -> dict[str, Any]:
    """Return ``state`` only when ``seat_id`` is authorized for this team state."""
    validate_runtime_team_state(state)
    _check_seat_id(seat_id, where="seat_id")
    if seat_id not in state["authorized_seat_ids"]:
        raise AgentAssetValidationError(
            f"seat {seat_id!r} is not authorized for team state {state['team_id']!r}"
        )
    return state


def validate_provider_profile(profile: object) -> None:
    profile = _check_object(profile, where="ProviderProfile")
    if _PROVIDER_PROFILE_FORBIDDEN_KEYS & set(profile):
        raise AgentAssetValidationError("ProviderProfile must not contain prompt/action/tool/parser contract versions")
    allowed = {
        "schema_version",
        "provider_profile_id",
        "provider",
        "model",
        "temperature",
        "max_tokens",
        "request_budget",
        "timeout_policy",
        "credential_slot",
    }
    _check_no_extra(profile, allowed, where="ProviderProfile")
    _check_schema(profile, PROVIDER_PROFILE_SCHEMA_VERSION, where="ProviderProfile")
    _check_required(
        profile,
        {"schema_version", "provider_profile_id", "provider", "model", "credential_slot"},
        where="ProviderProfile",
    )
    _check_id(profile["provider_profile_id"], where="ProviderProfile.provider_profile_id")
    _check_id(profile["provider"], where="ProviderProfile.provider")
    if not isinstance(profile["model"], str) or not profile["model"]:
        raise AgentAssetValidationError("ProviderProfile.model must be non-empty string")
    if "temperature" in profile and (
        isinstance(profile["temperature"], bool)
        or not isinstance(profile["temperature"], (int, float))
        or not (0.0 <= float(profile["temperature"]) <= 2.0)
    ):
        raise AgentAssetValidationError("ProviderProfile.temperature invalid")
    if "max_tokens" in profile and (
        isinstance(profile["max_tokens"], bool)
        or not isinstance(profile["max_tokens"], int)
        or profile["max_tokens"] <= 0
    ):
        raise AgentAssetValidationError("ProviderProfile.max_tokens invalid")


def validate_execution_contract(contract: object) -> None:
    contract = _check_object(contract, where="ExecutionContract")
    allowed = {
        "schema_version",
        "execution_contract_id",
        "prompt_template_version",
        "prompt_renderer_version",
        "action_schema_version",
        "agent_session_version",
        "decision_loop_policy_version",
        "tool_capability_manifest_version",
        "context_selector_version",
        "response_parser_version",
        "fallback_behavior_version",
        "visibility_oracle_version",
    }
    _check_no_extra(contract, allowed, where="ExecutionContract")
    _check_schema(contract, EXECUTION_CONTRACT_SCHEMA_VERSION, where="ExecutionContract")
    _check_required(
        contract,
        {
            "schema_version",
            "execution_contract_id",
            "prompt_template_version",
            "prompt_renderer_version",
            "action_schema_version",
            "tool_capability_manifest_version",
            "context_selector_version",
            "response_parser_version",
            "visibility_oracle_version",
        },
        where="ExecutionContract",
    )
    _check_id(contract["execution_contract_id"], where="ExecutionContract.execution_contract_id")


def validate_agent_preset(preset: object) -> None:
    preset = _check_object(preset, where="AgentPreset")
    allowed = {
        "schema_version",
        "preset_id",
        "display_name",
        "seat_character_card_ref",
        "role_policy_pack_refs",
        "provider_profile_ref",
    }
    _check_no_extra(preset, allowed, where="AgentPreset")
    _check_schema(preset, AGENT_PRESET_SCHEMA_VERSION, where="AgentPreset")
    _check_required(
        preset,
        {
            "schema_version",
            "preset_id",
            "display_name",
            "seat_character_card_ref",
            "role_policy_pack_refs",
            "provider_profile_ref",
        },
        where="AgentPreset",
    )
    _check_id(preset["preset_id"], where="AgentPreset.preset_id")
    if not isinstance(preset["role_policy_pack_refs"], dict) or not preset["role_policy_pack_refs"]:
        raise AgentAssetValidationError("AgentPreset.role_policy_pack_refs must be non-empty object")
    for role in preset["role_policy_pack_refs"]:
        if role not in known_role_teams():
            raise AgentAssetValidationError(f"AgentPreset.role_policy_pack_refs unknown role {role!r}")


def build_legacy_agent_asset_artifacts(
    profile: dict[str, Any],
    *,
    run_id: str,
    execution_contract_id: str = "baseline_prompt_v1_action_runtime_v1_2",
) -> dict[str, Any]:
    """Project the legacy profile into P3-A-1 audience-scoped asset artifacts.

    This is a compatibility projection only. It does not alter the legacy
    profile resolver or feed any new text into model prompts.
    """
    seats = resolve_profile_for_run(profile, run_id=run_id)
    public_seats: list[dict[str, Any]] = []
    seat_private: list[dict[str, Any]] = []
    wolves: list[str] = []
    profile_name = str(profile.get("name", "legacy_profile"))

    for seat in seats:
        seat_id = seat["player_id"]
        role = seat["role"]
        team = seat["team"]
        if team == "werewolf":
            wolves.append(seat_id)
        controller = "human" if seat["provider"] == "human" else "ai"
        persona_text = str(profile.get("seat_personas", {}).get(seat_id, ""))
        role_default_prompt = str(
            profile.get("role_defaults", {}).get(role, {}).get("prompt", "")
        )
        seat_override_prompt = profile.get("seat_overrides", {}).get(seat_id, {}).get("prompt")
        card_id = f"legacy_seat_card_{seat_id}"
        policy_id = f"legacy_role_policy_{role}"
        provider_profile_id = f"legacy_provider_{seat['provider']}_{seat_id}"

        public_seat = {
            "seat_id": seat_id,
            "controller": controller,
            "public_card": {
                "display_name": f"Seat {seat_id}",
                "card_hash_public": f"sha256:{_sha256_json({'seat_id': seat_id, 'persona': persona_text})}",
            },
        }
        if controller != "human":
            public_seat["provider_profile_summary"] = {
                "provider": seat["provider"],
                "model": seat["model"],
                "temperature": seat.get("temperature"),
            }
        public_seats.append(public_seat)

        private_seat = {
                "schema_version": SEAT_PRIVATE_ASSET_SNAPSHOT_SCHEMA_VERSION,
                "run_id": run_id,
                "seat_id": seat_id,
                "visibility_scope": "seat_private",
                "release_condition": "audit_authorized",
                "controller": controller,
                "true_role": role,
                "team": team,
                "seat_character_card_ref": {
                    "id": card_id,
                    "version": "legacy",
                    "hash": f"sha256:{_sha256_json({'card_id': card_id, 'persona': persona_text})}",
                },
                "role_policy_ref": {
                    "id": policy_id,
                    "version": "legacy",
                    "hash": f"sha256:{_sha256_json({'role': role, 'prompt': role_default_prompt})}",
                    "policy_selection_reason": "legacy_role_defaults_prompt",
                    "compatibility_mode": True,
                },
                "execution_contract_ref": {
                    "id": execution_contract_id,
                    "hash": f"sha256:{_sha256_json({'execution_contract_id': execution_contract_id})}",
                },
                "runtime_seat_state_ref": {
                    "run_id": run_id,
                    "seat_id": seat_id,
                },
                "legacy_bridge": {
                    "used_role_defaults_prompt": True,
                    "used_seat_persona": bool(persona_text),
                    "used_legacy_prompt_overlay": bool(seat_override_prompt),
                    "legacy_projection_byte_exact": True,
                },
            }
        if seat_override_prompt:
            private_seat["legacy_prompt_overlay"] = {
                "schema_version": "p3a.legacy_prompt_overlay.v1",
                "origin_path": f"seat_overrides.{seat_id}.prompt",
                "raw_text_hash": f"sha256:{hashlib.sha256(str(seat_override_prompt).encode('utf-8')).hexdigest()}",
                "classification": "legacy_opaque",
                "insertion_order": 3,
                "migration_status": "not_semantically_split",
            }
        if controller != "human":
            private_seat["provider_profile_ref"] = {
                "id": provider_profile_id,
                "hash": f"sha256:{_sha256_json({'provider': seat['provider'], 'model': seat['model'], 'seat': seat_id})}",
            }
        seat_private.append(private_seat)

    faction_private: list[dict[str, Any]] = []
    if wolves:
        faction_private.append(
            {
                "schema_version": FACTION_PRIVATE_ASSET_SNAPSHOT_SCHEMA_VERSION,
                "run_id": run_id,
                "team_id": "werewolf",
                "visibility_scope": "faction_private",
                "release_condition": "audit_authorized",
                "authorized_seat_ids": sorted(wolves),
                "team_policy_ref": {
                    "id": "wolf_private_plan_v1",
                    "hash": f"sha256:{_sha256_json({'team_policy': 'wolf_private_plan_v1'})}",
                },
                "runtime_team_state_ref": {
                    "run_id": run_id,
                    "team_id": "werewolf",
                },
            }
        )

    public_manifest = {
        "schema_version": PUBLIC_RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_name": profile_name,
        "visibility_scope": "public",
        "release_condition": "immediate",
        "seats": public_seats,
        "execution_contract_summary": {
            "prompt_template_version": "prompt_v1",
            "action_schema_version": "g1d-action-v1",
        },
    }
    postgame = {
        "schema_version": POSTGAME_AUDIT_ASSET_SNAPSHOT_SCHEMA_VERSION,
        "run_id": run_id,
        "visibility_scope": "postgame_only",
        "release_condition": "game_end",
        "asset_snapshot_manifest": {
            "snapshot_store_version": "v1",
            "seat_private_snapshot_hash": f"sha256:{_sha256_json(seat_private)}",
            "faction_private_snapshot_hash": f"sha256:{_sha256_json(faction_private)}",
            "execution_contract_hash": f"sha256:{_sha256_json({'execution_contract_id': execution_contract_id})}",
        },
        "sealed_blobs": [],
    }
    return {
        "public_run_manifest": public_manifest,
        "seat_private_asset_snapshots": seat_private,
        "faction_private_asset_snapshots": faction_private,
        "postgame_audit_asset_snapshot": postgame,
    }
