# tests/test_guard_resolver.py
"""GuardResolver (pure) — L4 guard arm Task 4. Mirrors SeerResolver EXCEPT
candidates: self-protect is legal, the previous guard night's target is not."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1_2
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.turn import DecisionWindow, GuardResolver
from werewolf_eval.action_runtime.validator import ActionValidator
from werewolf_eval.game_engine import AgentAction


def _window(live_action, alive=("p1", "p2", "p3", "p5"), last=None):
    state = RuntimeState(
        alive=frozenset(alive),
        roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p5": "guard"},
        last_guarded_target=last,
    )
    return DecisionWindow(
        rnd=2, actor="p5", role="guard", emit_phase="night", registry_phase="night",
        alive_seat_order=tuple(alive), roles=dict(state.roles), public_refs=(),
        live_action=live_action,
        validator=ActionValidator(RoleAbilityRegistry(rules_v1_2())),
        runtime_state=state,
    )


def _act(target):
    return AgentAction(actor="p5", action="guard_protect", target=target, phase="night",
                       round=2, reason_summary="t", decision_type="inference_based",
                       confidence=0.9)


class GuardResolverTests(unittest.TestCase):
    def test_legal_protect_accepted(self):
        adj = GuardResolver().adjudicate(_window(_act("p3"), last="p1"))
        self.assertEqual(adj.accepted_target, "p3")
        self.assertEqual(adj.decision_type, "inference_based")
        self.assertIsNone(adj.failure)

    def test_self_protect_accepted(self):
        adj = GuardResolver().adjudicate(_window(_act("p5"), last="p1"))
        self.assertEqual(adj.accepted_target, "p5")

    def test_consecutive_repeat_rejected_with_fallback(self):
        adj = GuardResolver().adjudicate(_window(_act("p3"), last="p3"))
        self.assertIsNone(adj.accepted_target)
        self.assertEqual(adj.failure.kind, "invalid_action")
        self.assertEqual(adj.decision_type, "default")
        # 兜底候选 = 存活含自己、剔上夜所守
        self.assertEqual(adj.rng_pick.over, ("p1", "p2", "p5"))
        self.assertIsNotNone(adj.downgrade_reason)

    def test_provider_error_falls_back_without_failure_row(self):
        adj = GuardResolver().adjudicate(_window(None, last="p3"))
        self.assertIsNone(adj.failure)          # err-path 由引擎记录
        self.assertEqual(adj.rng_pick.over, ("p1", "p2", "p5"))

    def test_render_event_shape(self):
        w = _window(_act("p3"), last="p1")
        plan = GuardResolver().render(w, "p3", "inference_based")
        self.assertEqual(plan.event.etype, "guard_protect")
        self.assertEqual(plan.event.visibility, "guard")
        self.assertEqual(plan.event.summary, "Guard p5 protects p3.")
        self.assertEqual(plan.decision.action, "guard_protect")
        self.assertEqual(plan.decision.phase, "night")


if __name__ == "__main__":
    unittest.main()
