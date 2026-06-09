from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.abilities import TARGET_RULES
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.provider_agent import ALLOWED_ACTIONS_BY_ROLE_PHASE


class RuntimeStateTests(unittest.TestCase):
    def test_state_holds_alive_roles_victim(self) -> None:
        s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer"},
            night_victim="p3",
        )
        self.assertIn("p1", s.alive)
        self.assertEqual(s.roles["p3"], "seer")
        self.assertEqual(s.night_victim, "p3")
        self.assertFalse(s.is_wolf("p3"))
        self.assertTrue(s.is_wolf("p1"))


class TargetRuleTests(unittest.TestCase):
    def _state(self) -> RuntimeState:
        return RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p4", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager"},
            night_victim="p5",
        )

    def test_alive_non_wolf_excludes_wolves_and_dead(self) -> None:
        s = self._state()
        rule = TARGET_RULES["alive_non_wolf"]
        self.assertTrue(rule(s, "p1", "p5"))    # villager alive -> ok
        self.assertFalse(rule(s, "p1", "p2"))   # wolf -> rejected
        self.assertFalse(rule(s, "p1", "p9"))   # dead/unknown -> rejected

    def test_exclude_self(self) -> None:
        s = self._state()
        rule = TARGET_RULES["exclude_self"]
        self.assertFalse(rule(s, "p3", "p3"))   # self -> rejected
        self.assertTrue(rule(s, "p3", "p1"))

    def test_is_night_victim(self) -> None:
        s = self._state()
        rule = TARGET_RULES["is_night_victim"]
        self.assertTrue(rule(s, "p4", "p5"))    # p5 is tonight's victim
        self.assertFalse(rule(s, "p4", "p1"))

    def test_alive_only(self) -> None:
        s = self._state()
        rule = TARGET_RULES["alive_only"]
        self.assertTrue(rule(s, "p4", "p1"))
        self.assertFalse(rule(s, "p4", "p9"))


class RulesV1Tests(unittest.TestCase):
    def test_rules_v1_has_versioned_id_and_roles(self) -> None:
        rs = rules_v1()
        self.assertEqual(rs.rules_version, "rules_v1")
        roles = {r.role for r in rs.roles}
        self.assertEqual(roles, {"werewolf", "seer", "witch", "villager"})

    def test_abilities_present(self) -> None:
        rs = rules_v1()
        ids = {a.action_id for a in rs.abilities}
        self.assertIn("werewolf_kill", ids)
        self.assertIn("seer_check", ids)
        self.assertIn("witch_save", ids)
        self.assertIn("witch_poison", ids)
        self.assertIn("player_vote", ids)

    def test_naide_chuan_is_a_settlement_rule_not_global(self) -> None:
        # 奶穿 lives in the ruleset's night interaction table, not a constant.
        rs = rules_v1()
        self.assertEqual(rs.night_settlement_rule("guard+save_same_target"), "death")

    def test_witch_poison_target_rule_is_exclude_self(self) -> None:
        # Parity: the engine rejects the witch poisoning herself (emergent_engine.py:702).
        rs = rules_v1()
        self.assertEqual(rs.ability("witch_poison").target_rule, "exclude_self")


class RegistryParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reg = RoleAbilityRegistry(rules_v1())

    def test_allowed_actions_match_static_map_exactly(self) -> None:
        # runtime "night" -> static "night"; runtime "day_vote" -> static "day".
        phase_map = {"night": "night", "day_vote": "day"}
        for (role, static_phase), expected in ALLOWED_ACTIONS_BY_ROLE_PHASE.items():
            rt_phase = next(rt for rt, st in phase_map.items() if st == static_phase)
            got = self.reg.allowed_actions(role, rt_phase)
            # witch night has save+poison+pass in the registry; the static map lists
            # only the adjudicating [witch_save, witch_poison]. Compare the
            # adjudicating subset for parity (pass is a no-target engine path).
            adjudicating = [a for a in got if a != "witch_pass"]
            self.assertEqual(
                sorted(adjudicating), sorted(expected),
                f"{role}/{static_phase}: {adjudicating} != {expected}",
            )

    def test_allowed_targets_wolf_kill_excludes_wolves(self) -> None:
        s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p5": "villager"},
        )
        targets = self.reg.allowed_targets("werewolf_kill", "p1", s)
        self.assertEqual(sorted(targets), ["p3", "p5"])  # no wolves, no dead


if __name__ == "__main__":
    unittest.main()
