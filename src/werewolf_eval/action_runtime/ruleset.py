from __future__ import annotations

from dataclasses import dataclass

from werewolf_eval.action_runtime.abilities import (
    ARITY_NONE,
    ARITY_ONE,
    AbilityDefinition,
    RoleDefinition,
)


@dataclass(frozen=True)
class BoardRuleset:
    rules_version: str
    roles: tuple[RoleDefinition, ...]
    abilities: tuple[AbilityDefinition, ...]
    # night interaction rule table (奶穿 etc.) — data, not a global constant.
    _night_rules: dict[str, str]
    # death-trigger ordering key components (Phase 2/3 uses this).
    death_order_key: tuple[str, ...] = ("phase_priority", "cause_priority", "seat_index")

    def night_settlement_rule(self, key: str) -> str:
        return self._night_rules[key]

    def ability(self, action_id: str) -> AbilityDefinition:
        for a in self.abilities:
            if a.action_id == action_id:
                return a
        raise KeyError(action_id)


def rules_v1() -> BoardRuleset:
    """The current standard 6-player board, encoded as data. The single source of
    allowed actions (it replaced provider_agent's static ALLOWED_ACTIONS_BY_ROLE_PHASE
    map) + the engine target rules.

    NOTE: witch_poison's target rule is ``exclude_self`` (alive AND != witch), the
    real engine guard at emergent_engine.py:702 (``target == witch`` is rejected) —
    NOT the broad ``alive`` target *list* shown to the model at :662.
    """
    abilities = (
        AbilityDefinition("werewolf_kill", "phase:night", "alive_non_wolf", ARITY_ONE, "werewolf_team"),
        AbilityDefinition("seer_check",    "phase:night", "exclude_self",   ARITY_ONE, "seer"),
        AbilityDefinition("witch_save",    "phase:night", "is_night_victim", ARITY_ONE, "witch"),
        AbilityDefinition("witch_poison",  "phase:night", "exclude_self",   ARITY_ONE, "witch"),
        AbilityDefinition("witch_pass",    "phase:night", "",               ARITY_NONE, "witch"),
        AbilityDefinition("player_vote",   "phase:day_vote", "exclude_self", ARITY_ONE, "public"),
    )
    roles = (
        RoleDefinition("werewolf", "werewolf", ("werewolf_kill", "player_vote")),
        RoleDefinition("seer",     "villager", ("seer_check", "player_vote")),
        RoleDefinition("witch",    "villager", ("witch_save", "witch_poison", "witch_pass", "player_vote")),
        RoleDefinition("villager", "villager", ("player_vote",)),
    )
    night_rules = {
        # 奶穿: guard-protect AND witch-save on the same target -> still dies.
        # Only rules the settler actually consults live here — a key in this table
        # is authoritative (§4.0), so we do NOT list save_cancels_kill/poison_stacks
        # (the settler hardcodes those rules_v1 semantics; a future RulesVariant that
        # wants them configurable must add them here AND have the settler read them).
        "guard+save_same_target": "death",
    }
    return BoardRuleset("rules_v1", roles, abilities, night_rules)


def rules_v1_1() -> BoardRuleset:
    """rules_v1 + the hunter (a versioned superset — does NOT edit rules_v1, per audit
    contract C). Backward-compatible: the 4 original roles' abilities/target-rules are
    byte-identical, so a 4-role game under rules_v1_1 behaves exactly as under rules_v1
    (pinned by test_allowed_actions_pinned + the determinism canary)."""
    base = rules_v1()
    hunter_abilities = (
        # on_death shot: a model decision fired when the hunter dies (night kill or vote-out).
        # Ruling A-2 (audit 2026-06-12): a POISON death suppresses the shot; wolf-kill,
        # vote-out and being-shot all still trigger it.
        AbilityDefinition("hunter_shoot", "event:on_death", "exclude_self", ARITY_ONE, "public",
                          suppressed_by_cause=frozenset({"witch_poison"})),
        AbilityDefinition("hunter_pass", "event:on_death", "", ARITY_NONE, "public"),
    )
    hunter = RoleDefinition("hunter", "villager", ("player_vote", "hunter_shoot", "hunter_pass"))
    return BoardRuleset(
        "rules_v1_1",
        base.roles + (hunter,),
        base.abilities + hunter_abilities,
        dict(base._night_rules),
        base.death_order_key,
    )


def rules_v1_2() -> BoardRuleset:
    """rules_v1_1 + the guard (L4 protective-structure arm, spec 2026-06-11).
    Versioned superset — does NOT edit rules_v1_1. Boards without a guard behave
    byte-identically under v1_2 (pinned by test_allowed_actions_pinned + the
    determinism canary). The guard's no-consecutive-protect rule lives in the
    exclude_last_guarded target rule, fed by RuntimeState.last_guarded_target —
    minimal inline state (witch one-shot precedent), NOT a CapabilityLedger."""
    base = rules_v1_1()
    guard_abilities = (
        AbilityDefinition("guard_protect", "phase:night", "exclude_last_guarded", ARITY_ONE, "guard"),
    )
    guard = RoleDefinition("guard", "villager", ("guard_protect", "player_vote"))
    return BoardRuleset(
        "rules_v1_2",
        base.roles + (guard,),
        base.abilities + guard_abilities,
        dict(base._night_rules),
        base.death_order_key,
    )


def all_rulesets() -> tuple[BoardRuleset, ...]:
    """Every ruleset this codebase has ever shipped. APPEND-ONLY: observer-side
    consumers derive role->team knowledge from this union, and must keep
    recognizing roles from logs written under ANY rules version."""
    return (rules_v1(), rules_v1_1(), rules_v1_2())


def known_role_teams() -> dict[str, str]:
    """role -> team, union over all_rulesets(), in declaration order.

    THE single source of role->team facts (ADR 2026-06-11): observer_protocol
    re-exports this for observer-side modules; profile_config derives its gated
    ROLE_TEAMS projection from it. A role may not change team across rulesets —
    fail loud instead of silently picking one."""
    teams: dict[str, str] = {}
    for rs in all_rulesets():
        for role_def in rs.roles:
            existing = teams.get(role_def.role)
            if existing is not None and existing != role_def.team:
                raise ValueError(
                    f"role {role_def.role!r} maps to both {existing!r} and "
                    f"{role_def.team!r} across rulesets"
                )
            teams[role_def.role] = role_def.team
    return teams
