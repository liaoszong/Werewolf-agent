from __future__ import annotations

from dataclasses import dataclass

from werewolf_eval.action_runtime.abilities import ARITY_NONE, TARGET_RULES
from werewolf_eval.action_runtime.envelope import ActionEnvelope
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.state import RuntimeState


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    # "" | "invalid_action" | "invalid_target" | "bad_arity" | "needs_state"
    # ("needs_state" = a well-formed single-target action whose legality can only
    # be decided with the live state — see validate_in_state.)
    reason_kind: str = ""


class ActionValidator:
    """Validates an ActionEnvelope against the active ruleset. Mirrors the
    accept/reject decisions today split across ProviderAgent.decide + the
    per-resolver inline checks. Does NOT perform fallback — the caller keeps the
    existing seeded R-29 fallback on rejection (Phase 2)."""

    def __init__(self, registry: RoleAbilityRegistry) -> None:
        self._reg = registry

    def validate(self, env: ActionEnvelope) -> ValidationResult:
        """Stateless verdict: is the action allowed for (role, phase) and is the
        target ARITY correct? Target *legality* needs state -> validate_in_state."""
        allowed = self._reg.allowed_actions(env.role, env.phase)
        if env.action not in allowed:
            return ValidationResult(False, "invalid_action")
        ability = self._reg.ability(env.action)
        if ability.target_arity == ARITY_NONE:
            return ValidationResult(True) if not env.targets else ValidationResult(False, "bad_arity")
        if len(env.targets) != 1:
            return ValidationResult(False, "bad_arity")
        # A well-formed single-target action: legality is undecidable without state.
        return ValidationResult(False, "needs_state")

    def validate_in_state(self, env: ActionEnvelope, state: RuntimeState) -> ValidationResult:
        """Full verdict: action-allowed + arity (stateless) PLUS target legality
        under the live state."""
        base = self.validate(env)
        if not base.ok and base.reason_kind in ("invalid_action", "bad_arity"):
            return base
        ability = self._reg.ability(env.action)
        if ability.target_arity == ARITY_NONE:
            return ValidationResult(True)
        # .get mirrors registry.legal_targets' guard: a malformed ability (arity != none
        # but empty/unknown target_rule) rejects rather than KeyError-ing.
        pred = TARGET_RULES.get(ability.target_rule)
        if pred is not None and env.targets and all(pred(state, env.actor, t) for t in env.targets):
            return ValidationResult(True)
        return ValidationResult(False, "invalid_target")
