# tests/test_rules_v1_2.py
"""rules_v1_2 (guard) data-layer pins — L4 guard arm Task 1/2.

Append-only superset contract (spec §3): rules_v1_1 is untouched and is a
field-equal prefix of rules_v1_2; the guard's no-consecutive-protect rule is the
exclude_last_guarded target rule fed by RuntimeState.last_guarded_target."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.abilities import ARITY_ONE, TARGET_RULES
from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.runtime_events import RUNTIME_EVENT_VISIBILITIES


class RulesV12Tests(unittest.TestCase):
    def test_guard_role_and_ability(self):
        rs = rules_v1_2()
        self.assertEqual(rs.rules_version, "rules_v1_2")
        guard = next(r for r in rs.roles if r.role == "guard")
        self.assertEqual(guard.team, "villager")
        self.assertEqual(guard.ability_ids, ("guard_protect", "player_vote"))
        ab = rs.ability("guard_protect")
        self.assertEqual(
            (ab.trigger, ab.target_rule, ab.target_arity, ab.visibility),
            ("phase:night", "exclude_last_guarded", ARITY_ONE, "guard"),
        )

    def test_v1_1_untouched_superset(self):
        # append-only:v1_1 的角色/能力是 v1_2 的前缀,逐字段相等(spec §3 硬边界)
        self.assertEqual(rules_v1_1().roles, rules_v1_2().roles[:-1])
        self.assertEqual(rules_v1_1().abilities, rules_v1_2().abilities[:-1])

    def test_night_rules_inherited_no_new_keys(self):
        self.assertEqual(rules_v1_2().night_settlement_rule("guard+save_same_target"), "death")

    def test_guard_visibility_registered(self):
        self.assertIn("guard", RUNTIME_EVENT_VISIBILITIES)


class ExcludeLastGuardedPredicateTests(unittest.TestCase):
    def test_predicate(self):
        pred = TARGET_RULES["exclude_last_guarded"]
        s = RuntimeState(alive=frozenset({"p1", "p2", "p5"}), roles={}, last_guarded_target="p2")
        self.assertTrue(pred(s, "p5", "p5"))   # 可自守
        self.assertTrue(pred(s, "p5", "p1"))
        self.assertFalse(pred(s, "p5", "p2"))  # 不可连守
        self.assertFalse(pred(s, "p5", "p6"))  # 非存活
        night1 = RuntimeState(alive=frozenset({"p1", "p2", "p5"}), roles={})
        self.assertTrue(pred(night1, "p5", "p2"))  # 夜1 无上夜目标:全存活合法


if __name__ == "__main__":
    unittest.main()
