from __future__ import annotations

from werewolf_eval.action_runtime.abilities import AbilityDefinition, TARGET_RULES
from werewolf_eval.action_runtime.ruleset import BoardRuleset
from werewolf_eval.action_runtime.state import RuntimeState

# runtime phase -> the trigger string used in AbilityDefinition.trigger
_PHASE_TRIGGER = {"night": "phase:night", "day_vote": "phase:day_vote"}


class RoleAbilityRegistry:
    """Projects the active ruleset: which actions a (role, phase) may take, and
    which targets are legal in a given state. Single source for allowed_actions /
    allowed_targets / ability cards (cards land in Phase 2)."""

    def __init__(self, ruleset: BoardRuleset) -> None:
        self._rs = ruleset
        self._by_role = {r.role: r for r in ruleset.roles}

    def ability(self, action_id: str) -> AbilityDefinition:
        return self._rs.ability(action_id)

    def abilities_for(self, role: str, phase: str) -> list[AbilityDefinition]:
        # Unknown role/phase -> [] (degrades to a clean invalid_action), matching the
        # engine's never-raise contract. Defensive for callers passing a role/phase not in
        # this ruleset (e.g. a future role before its RulesVariant lands).
        trig = _PHASE_TRIGGER.get(phase)
        role_def = self._by_role.get(role)
        if trig is None or role_def is None:
            return []
        return [
            self._rs.ability(aid)
            for aid in role_def.ability_ids
            if self._rs.ability(aid).trigger == trig
        ]

    def allowed_actions(self, role: str, phase: str) -> list[str]:
        return [a.action_id for a in self.abilities_for(role, phase)]

    def on_death_abilities(self, role: str) -> list[AbilityDefinition]:
        """Abilities a role's death triggers (trigger == 'event:on_death'). [] for an
        unknown role or a role with no death trigger (so the engine hook is a no-op)."""
        role_def = self._by_role.get(role)
        if role_def is None:
            return []
        return [
            self._rs.ability(aid)
            for aid in role_def.ability_ids
            if self._rs.ability(aid).trigger == "event:on_death"
        ]

    def death_trigger_suppressing_causes(self, role: str) -> frozenset[str]:
        """Death causes under which a role's on_death trigger is SUPPRESSED (ruling
        A-2). Union of ``suppressed_by_cause`` over the role's on_death abilities.
        Empty for a role with no death trigger or no suppression -> the engine hook
        fires normally. For the hunter this is {"witch_poison"}."""
        causes: set[str] = set()
        for ability in self.on_death_abilities(role):
            causes |= ability.suppressed_by_cause
        return frozenset(causes)

    def shown_targets(self, action_id: str, state: RuntimeState) -> list[str]:
        """The BROAD target list the model is SHOWN in the prompt — the full alive
        set, matching the engine's ``observation.alive_players``
        (provider_agent.py:109, rendered verbatim at llm_providers.py:98/91).
        Legality is a SEPARATE concern (see ``legal_targets`` / the validator):
        the engine shows the broad list and adjudicates narrowly. Routing the
        narrow list into the prompt would change prompt bytes + the model's
        instruction → parity break, so the two are kept distinct here."""
        return sorted(state.alive)

    def legal_targets(self, action_id: str, actor: str, state: RuntimeState) -> list[str]:
        """The NARROW set of legal targets (the ``target_rule`` predicate) — for
        validation / adjudication ONLY, never for the prompt."""
        ability = self._rs.ability(action_id)
        if not ability.target_rule:
            return []
        pred = TARGET_RULES[ability.target_rule]
        return [pid for pid in sorted(state.alive) if pred(state, actor, pid)]
