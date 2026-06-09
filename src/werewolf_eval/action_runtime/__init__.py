"""Agent Action Runtime (P-AAR). Data-driven action resolution; see
docs/superpowers/specs/2026-06-09-agent-action-runtime-architecture-design.md."""

from werewolf_eval.action_runtime.abilities import (
    AbilityDefinition,
    RoleDefinition,
    TARGET_RULES,
)
from werewolf_eval.action_runtime.envelope import ActionEnvelope
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import BoardRuleset, rules_v1
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.validator import ActionValidator, ValidationResult

__all__ = [
    "AbilityDefinition",
    "RoleDefinition",
    "TARGET_RULES",
    "ActionEnvelope",
    "RoleAbilityRegistry",
    "BoardRuleset",
    "rules_v1",
    "RuntimeState",
    "ActionValidator",
    "ValidationResult",
]
