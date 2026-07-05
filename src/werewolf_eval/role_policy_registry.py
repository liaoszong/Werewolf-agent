"""P3-A RolePolicyPack registry helpers.

This module is deliberately asset-only. It stores and versions RolePolicyPack
and RolePolicy objects without changing runtime prompt rendering, providers, or
observer protocols.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from werewolf_eval.agent_assets import (
    AgentAssetValidationError,
    ROLE_POLICY_SCHEMA_VERSION,
    validate_role_policy,
)

ROLE_POLICY_PACK_SCHEMA_VERSION = "p3a.role_policy_pack.v1"
ROLE_POLICY_REGISTRY_SCHEMA_VERSION = "p3a.role_policy_registry.v1"
ROLE_POLICY_DRAFT_SCHEMA_VERSION = "p3a.role_policy_draft.v1"

_DEFAULT_PACK_ID = "standard_six_player_balanced"
_DEFAULT_PACK_VERSION = "1.0.0"
_FORBIDDEN_POLICY_FIELDS = frozenset(
    {
        "seat_character_card_ref",
        "provider_profile_ref",
        "execution_contract_ref",
        "runtime_state",
        "runtime_state_ref",
        "team_plan",
        "team_plan_ref",
        "extra_call_budget",
        "history_tool_budget",
        "visibility_entitlement",
        "legal_action_window",
    }
)
_FORBIDDEN_POLICY_KEY_FRAGMENTS = (
    "providerprofile",
    "executioncontract",
    "runtimestate",
    "teamplan",
    "modelcall",
    "toolround",
    "callbudget",
    "tokenbudget",
    "timeoutbudget",
    "visibilityentitlement",
    "legalactionwindow",
)
_ALLOWED_NORMALIZED_POLICY_KEYS = frozenset({"usesteamplan"})
_POLICY_SECTION_FIELDS = {
    "ability_use_policy": frozenset(
        {
            "werewolf_kill",
            "seer_check",
            "witch_save",
            "witch_poison",
            "player_vote",
            "guard_protect",
            "hunter_shoot",
        }
    ),
    "claim_policy": frozenset({"identity_claims"}),
    "deception_policy": frozenset({"allowed", "style"}),
    "team_policy": frozenset({"uses_team_plan", "protect_teammates"}),
}
_POLICY_STR_LIST_FIELDS = frozenset(
    {
        "goals",
        "information_priorities",
        "playbook_refs",
        "forbidden_behavior",
    }
)
_POLICY_APPLICABILITY_FIELDS = frozenset(
    {
        "ruleset_id",
        "seat_count",
        "required_roles",
        "optional_roles",
        "phase_protocol_version",
        "team_channel_policy",
    }
)
_NORMALIZED_FORBIDDEN_POLICY_FIELDS = frozenset(
    re.sub(r"[^a-z0-9]", "", field.lower()) for field in _FORBIDDEN_POLICY_FIELDS
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
_SECRET_VALUE_MARKERS = (
    "sk-",
    "bearer ",
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "access_key",
)


class RolePolicyRegistryError(ValueError):
    """Raised when RolePolicyPack registry data violates P3-A ownership rules."""


class RolePolicyRegistry:
    """In-memory RolePolicyPack registry with optional JSON persistence."""

    def __init__(
        self,
        *,
        packs: dict[str, dict[str, Any]],
        policies: dict[str, dict[str, Any]],
        drafts: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._packs = copy.deepcopy(packs)
        self._policies = {
            _policy_ref(policy): copy.deepcopy(policy)
            for policy in copy.deepcopy(policies).values()
        }
        self._drafts = copy.deepcopy(drafts or {})
        self._validate_all()

    def get_pack(self, pack_id: str) -> dict[str, Any]:
        try:
            return copy.deepcopy(self._packs[pack_id])
        except KeyError as exc:
            raise RolePolicyRegistryError(f"unknown RolePolicyPack {pack_id!r}") from exc

    def resolve_policy_ref(self, policy_ref: str) -> dict[str, Any]:
        _split_policy_ref(policy_ref)
        try:
            policy = self._policies[policy_ref]
        except KeyError as exc:
            raise RolePolicyRegistryError(f"unknown RolePolicy ref {policy_ref!r}") from exc
        return copy.deepcopy(policy)

    def create_draft(
        self,
        *,
        pack_id: str,
        role: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        _check_policy_patch(changes)
        pack = self.get_pack(pack_id)
        try:
            current_ref = pack["role_policy_refs"][role]
        except KeyError as exc:
            raise RolePolicyRegistryError(
                f"pack {pack_id!r} has no policy for role {role!r}"
            ) from exc
        base_policy = self.resolve_policy_ref(current_ref)
        policy = copy.deepcopy(base_policy)
        policy.update(copy.deepcopy(changes))
        policy["role"] = role
        _validate_policy(policy)
        draft_id = _next_draft_id(self._drafts, pack_id, role)
        draft = {
            "schema_version": ROLE_POLICY_DRAFT_SCHEMA_VERSION,
            "draft_id": draft_id,
            "pack_id": pack_id,
            "role": role,
            "base_policy_ref": current_ref,
            "status": "draft",
            "policy": policy,
        }
        self._drafts[draft_id] = copy.deepcopy(draft)
        return copy.deepcopy(draft)

    def publish_draft(
        self,
        draft_id: str,
        *,
        referenced_policy_refs: set[str],
    ) -> dict[str, Any]:
        try:
            draft = self._drafts[draft_id]
        except KeyError as exc:
            raise RolePolicyRegistryError(f"unknown RolePolicy draft {draft_id!r}") from exc
        if draft["status"] != "draft":
            raise RolePolicyRegistryError(f"RolePolicy draft {draft_id!r} is not draft")
        pack_id = draft["pack_id"]
        role = draft["role"]
        pack = self._packs[pack_id]
        base_ref = draft["base_policy_ref"]
        current_ref = pack["role_policy_refs"][role]
        registry_referenced_refs = self._policy_refs_used_outside(
            pack_id=pack_id,
            role=role,
        )
        if current_ref != base_ref:
            raise RolePolicyRegistryError(
                f"RolePolicy draft {draft_id!r} is stale for role {role!r}"
            )
        policy = copy.deepcopy(draft["policy"])
        draft_ref = _policy_ref(policy)
        would_mutate_base_ref = (
            draft_ref == base_ref and self._policies.get(base_ref) != policy
        )
        if (
            base_ref in referenced_policy_refs
            or base_ref in registry_referenced_refs
            or would_mutate_base_ref
        ):
            base_policy_id, base_version = _split_policy_ref(base_ref)
            policy["policy_id"] = base_policy_id
            policy["version"] = _next_unused_patch_version(
                policy_id=base_policy_id,
                base_version=base_version,
                existing_refs=(
                    set(self._policies)
                    | referenced_policy_refs
                    | registry_referenced_refs
                ),
            )
        _validate_policy(policy)
        policy_ref = _policy_ref(policy)
        if policy_ref in self._policies and policy_ref != base_ref:
            raise RolePolicyRegistryError(
                f"RolePolicy ref collision would overwrite {policy_ref!r}"
            )
        self._policies[policy_ref] = copy.deepcopy(policy)
        pack["role_policy_refs"][role] = policy_ref
        draft["status"] = "published"
        draft["published_policy_ref"] = policy_ref
        return copy.deepcopy(policy)

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": ROLE_POLICY_REGISTRY_SCHEMA_VERSION,
            "packs": copy.deepcopy(self._packs),
            "policies": copy.deepcopy(self._policies),
            "drafts": copy.deepcopy(self._drafts),
        }

    def _policy_refs_used_outside(self, *, pack_id: str, role: str) -> set[str]:
        refs: set[str] = set()
        for other_pack_id, pack in self._packs.items():
            for other_role, policy_ref in pack["role_policy_refs"].items():
                if other_pack_id == pack_id and other_role == role:
                    continue
                refs.add(policy_ref)
        return refs

    def save(self, path: str | Path) -> None:
        data = self.export()
        text = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)
        Path(path).write_text(f"{text}\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "RolePolicyRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != ROLE_POLICY_REGISTRY_SCHEMA_VERSION:
            raise RolePolicyRegistryError("invalid role policy registry schema_version")
        return cls(
            packs=data.get("packs", {}),
            policies=data.get("policies", {}),
            drafts=data.get("drafts", {}),
        )

    def _validate_all(self) -> None:
        for pack in self._packs.values():
            _validate_pack(pack)
            for role, policy_ref in pack["role_policy_refs"].items():
                policy = self.resolve_policy_ref(policy_ref)
                if policy["role"] != role:
                    raise RolePolicyRegistryError(
                        f"RolePolicyPack role {role!r} points to {policy['role']!r}"
                    )
        for policy in self._policies.values():
            _validate_policy(policy)
        for draft in self._drafts.values():
            _validate_draft(draft)


def build_default_role_policy_registry() -> RolePolicyRegistry:
    policies = {
        role: _default_role_policy(role)
        for role in ("werewolf", "seer", "witch", "villager", "guard", "hunter")
    }
    pack = {
        "schema_version": ROLE_POLICY_PACK_SCHEMA_VERSION,
        "pack_id": _DEFAULT_PACK_ID,
        "version": _DEFAULT_PACK_VERSION,
        "display_name": "Standard Six Player Balanced",
        "applicability": {
            "ruleset_id": "rules_v1_2",
            "seat_count": [6],
            "required_roles": ["werewolf", "seer", "witch", "villager"],
            "optional_roles": ["guard", "hunter"],
        },
        "role_policy_refs": {
            role: _policy_ref(policy) for role, policy in policies.items()
        },
    }
    return RolePolicyRegistry(
        packs={_DEFAULT_PACK_ID: pack},
        policies={policy["policy_id"]: policy for policy in policies.values()},
    )


def _default_role_policy(role: str) -> dict[str, Any]:
    summaries = {
        "werewolf": {
            "policy_id": "standard_werewolf_balanced",
            "goals": ["hide team identity", "misdirect daytime votes"],
            "information_priorities": ["public claims", "vote shifts", "teammate pressure"],
            "ability_use_policy": {
                "werewolf_kill": "prefer high-threat non-wolf targets"
            },
            "claim_policy": {"identity_claims": "claim under pressure only"},
            "team_policy": {
                "uses_team_plan": True,
                "protect_teammates": "conditional distancing",
            },
        },
        "seer": {
            "policy_id": "standard_seer_steady_checks",
            "goals": ["maximize check information", "release evidence at useful timing"],
            "information_priorities": ["claim conflicts", "high-impact suspects"],
            "ability_use_policy": {"seer_check": "check high-impact low-trust players"},
            "claim_policy": {"identity_claims": "lead after a check chain"},
        },
        "witch": {
            "policy_id": "standard_witch_resource_timing",
            "goals": ["preserve potion value", "intervene on pivotal turns"],
            "information_priorities": ["death rhythm", "claim conflicts", "vote anomaly"],
            "ability_use_policy": {
                "witch_save": "prioritize key targets",
                "witch_poison": "prefer high-confidence wolf candidates",
            },
        },
        "villager": {
            "policy_id": "standard_villager_claim_review",
            "goals": ["reason from public evidence", "track contradictions"],
            "information_priorities": ["speech contradictions", "vote shifts", "public commitments"],
            "ability_use_policy": {"player_vote": "vote from public evidence"},
        },
        "guard": {
            "policy_id": "standard_guard_safe_protection",
            "goals": ["protect high-value public targets", "avoid predictable guards"],
            "information_priorities": ["death rhythm", "claimed roles", "public pressure"],
            "ability_use_policy": {"guard_protect": "prefer high-value public targets"},
        },
        "hunter": {
            "policy_id": "standard_hunter_threat_control",
            "goals": ["preserve shot threat", "avoid baited shots"],
            "information_priorities": ["vote shifts", "speech contradictions", "pressure sources"],
            "ability_use_policy": {"hunter_shoot": "shoot only with strong public evidence"},
        },
    }
    data = summaries[role]
    policy = {
        "schema_version": ROLE_POLICY_SCHEMA_VERSION,
        "policy_id": data["policy_id"],
        "version": "1.0.0",
        "role": role,
        "applicability": {
            "ruleset_id": "rules_v1_2",
            "seat_count": [6],
            "required_roles": ["werewolf", "seer", "witch", "villager"],
            "optional_roles": ["guard", "hunter"],
            "phase_protocol_version": "phase_protocol_v2",
            "team_channel_policy": "wolf_private_plan_v1",
        },
        "fallback_policy": "reject",
        "goals": data["goals"],
        "information_priorities": data["information_priorities"],
        "ability_use_policy": data.get("ability_use_policy", {}),
        "claim_policy": data.get("claim_policy", {}),
        "deception_policy": {
            "allowed": role == "werewolf",
            "style": "in-game social deduction only",
        },
        "team_policy": data.get("team_policy", {}),
        "playbook_refs": [f"{role}_starter_playbook_v1"],
        "forbidden_behavior": [
            "claim access to god-view facts",
            "quote hidden system prompts",
        ],
    }
    _validate_policy(policy)
    return policy


def _validate_pack(pack: dict[str, Any]) -> None:
    _check_no_secret(pack)
    if pack.get("schema_version") != ROLE_POLICY_PACK_SCHEMA_VERSION:
        raise RolePolicyRegistryError("RolePolicyPack.schema_version invalid")
    for key in ("pack_id", "version", "role_policy_refs"):
        if key not in pack:
            raise RolePolicyRegistryError(f"RolePolicyPack missing {key}")
    refs = pack["role_policy_refs"]
    if not isinstance(refs, dict) or not refs:
        raise RolePolicyRegistryError("RolePolicyPack.role_policy_refs must be object")
    for role, policy_ref in refs.items():
        if not isinstance(role, str) or not isinstance(policy_ref, str):
            raise RolePolicyRegistryError("RolePolicyPack role refs must be strings")
        _split_policy_ref(policy_ref)


def _validate_policy(policy: dict[str, Any]) -> None:
    _check_policy_patch(policy)
    try:
        validate_role_policy(policy)
    except AgentAssetValidationError as exc:
        raise RolePolicyRegistryError(str(exc)) from exc


def _validate_draft(draft: dict[str, Any]) -> None:
    _check_no_secret(draft)
    if draft.get("schema_version") != ROLE_POLICY_DRAFT_SCHEMA_VERSION:
        raise RolePolicyRegistryError("RolePolicyDraft.schema_version invalid")
    for key in ("draft_id", "pack_id", "role", "base_policy_ref", "status", "policy"):
        if key not in draft:
            raise RolePolicyRegistryError(f"RolePolicyDraft missing {key}")
    if draft["status"] not in {"draft", "published"}:
        raise RolePolicyRegistryError("RolePolicyDraft.status invalid")
    _split_policy_ref(draft["base_policy_ref"])
    _validate_policy(draft["policy"])
    if draft["policy"]["role"] != draft["role"]:
        raise RolePolicyRegistryError(
            f"RolePolicyDraft role {draft['role']!r} contains {draft['policy']['role']!r} policy"
        )


def _check_policy_patch(obj: dict[str, Any]) -> None:
    if not isinstance(obj, dict):
        raise RolePolicyRegistryError("RolePolicy patch must be object")
    forbidden = sorted(set(obj) & _FORBIDDEN_POLICY_FIELDS)
    if forbidden:
        raise RolePolicyRegistryError(f"RolePolicy contains forbidden fields: {forbidden}")
    _check_no_forbidden_policy_fields(obj)
    _check_no_secret(obj)
    _check_policy_applicability_fields(obj)
    _check_policy_section_fields(obj)
    _check_policy_str_list_fields(obj)


def _check_no_forbidden_policy_fields(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)
            normalized_key = _normalize_policy_key(key_text)
            if normalized_key not in _ALLOWED_NORMALIZED_POLICY_KEYS and (
                normalized_key in _NORMALIZED_FORBIDDEN_POLICY_FIELDS
                or any(
                    fragment in normalized_key
                    for fragment in _FORBIDDEN_POLICY_KEY_FRAGMENTS
                )
            ):
                raise RolePolicyRegistryError(
                    f"RolePolicy contains forbidden field: {path}{key_text}"
                )
            _check_no_forbidden_policy_fields(value, f"{path}{key_text}.")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            _check_no_forbidden_policy_fields(value, f"{path}{index}.")


def _check_policy_section_fields(obj: dict[str, Any]) -> None:
    for section, allowed_fields in _POLICY_SECTION_FIELDS.items():
        if section not in obj:
            continue
        section_obj = obj[section]
        if not isinstance(section_obj, dict):
            raise RolePolicyRegistryError(f"RolePolicy.{section} must be object")
        extra = sorted(set(section_obj) - allowed_fields)
        if extra:
            raise RolePolicyRegistryError(
                f"RolePolicy.{section} has unsupported fields: {extra}"
            )
        for key, value in section_obj.items():
            if key in {"allowed", "uses_team_plan"}:
                if not isinstance(value, bool):
                    raise RolePolicyRegistryError(
                        f"RolePolicy.{section}.{key} must be boolean"
                    )
            elif not isinstance(value, str):
                raise RolePolicyRegistryError(
                    f"RolePolicy.{section}.{key} must be strategy text"
                )


def _check_policy_applicability_fields(obj: dict[str, Any]) -> None:
    if "applicability" not in obj:
        return
    applicability = obj["applicability"]
    if not isinstance(applicability, dict):
        raise RolePolicyRegistryError("RolePolicy.applicability must be object")
    extra = sorted(set(applicability) - _POLICY_APPLICABILITY_FIELDS)
    if extra:
        raise RolePolicyRegistryError(
            f"RolePolicy.applicability has unsupported fields: {extra}"
    )
    for key in ("ruleset_id", "phase_protocol_version", "team_channel_policy"):
        if key in applicability and not isinstance(applicability[key], str):
            raise RolePolicyRegistryError(
                f"RolePolicy.applicability.{key} must be string"
            )
    if "seat_count" in applicability and (
        not isinstance(applicability["seat_count"], list)
        or not all(
            isinstance(item, int) and item > 0 for item in applicability["seat_count"]
        )
    ):
        raise RolePolicyRegistryError(
            "RolePolicy.applicability.seat_count must be positive integers"
        )
    for key in ("required_roles", "optional_roles"):
        if key in applicability and (
            not isinstance(applicability[key], list)
            or not all(isinstance(item, str) for item in applicability[key])
        ):
            raise RolePolicyRegistryError(
                f"RolePolicy.applicability.{key} must be list[str]"
            )


def _check_policy_str_list_fields(obj: dict[str, Any]) -> None:
    for field in _POLICY_STR_LIST_FIELDS:
        if field not in obj:
            continue
        value = obj[field]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise RolePolicyRegistryError(f"RolePolicy.{field} must be list[str]")


def _check_no_secret(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key).lower()
            if any(fragment in key_text for fragment in _SECRET_KEY_FRAGMENTS):
                raise RolePolicyRegistryError(f"secret-like key not allowed: {path}{key}")
            _check_no_secret(value, f"{path}{key}.")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            _check_no_secret(value, f"{path}{index}.")
    elif isinstance(obj, str):
        lowered = obj.lower()
        if any(marker in lowered for marker in _SECRET_VALUE_MARKERS):
            raise RolePolicyRegistryError(
                f"secret-like value not allowed at {path.rstrip('.')}"
            )


def _policy_ref(policy: dict[str, Any]) -> str:
    return f"{policy['policy_id']}@{policy['version']}"


def _normalize_policy_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _split_policy_ref(policy_ref: str) -> tuple[str, str]:
    if not isinstance(policy_ref, str) or "@" not in policy_ref:
        raise RolePolicyRegistryError(f"invalid RolePolicy ref {policy_ref!r}")
    policy_id, version = policy_ref.rsplit("@", 1)
    if not policy_id or not version:
        raise RolePolicyRegistryError(f"invalid RolePolicy ref {policy_ref!r}")
    return policy_id, version


def _increment_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise RolePolicyRegistryError(f"cannot increment non-semver version {version!r}")
    major, minor, patch = (int(part) for part in parts)
    return f"{major}.{minor}.{patch + 1}"


def _next_unused_patch_version(
    *,
    policy_id: str,
    base_version: str,
    existing_refs: set[str],
) -> str:
    version = _increment_patch_version(base_version)
    while f"{policy_id}@{version}" in existing_refs:
        version = _increment_patch_version(version)
    return version


def _next_draft_id(
    drafts: dict[str, dict[str, Any]],
    pack_id: str,
    role: str,
) -> str:
    prefix = f"{pack_id}_{role}_draft_"
    next_index = 1
    for draft_id in drafts:
        if draft_id.startswith(prefix):
            suffix = draft_id.removeprefix(prefix)
            if suffix.isdigit():
                next_index = max(next_index, int(suffix) + 1)
    return f"{prefix}{next_index}"
