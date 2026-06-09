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

    def test_allowed_actions_pinned(self) -> None:
        # The registry IS the source of truth now (the static ALLOWED_ACTIONS_BY_ROLE_PHASE
        # map was deleted); pin its full contract explicitly. Order matters — the prompt
        # joins this list and uses [0] as the example action.
        expected = {
            ("werewolf", "night"): ["werewolf_kill"],
            ("seer", "night"): ["seer_check"],
            ("witch", "night"): ["witch_save", "witch_poison", "witch_pass"],
            ("werewolf", "day_vote"): ["player_vote"],
            ("seer", "day_vote"): ["player_vote"],
            ("witch", "day_vote"): ["player_vote"],
            ("villager", "day_vote"): ["player_vote"],
        }
        for (role, phase), want in expected.items():
            self.assertEqual(self.reg.allowed_actions(role, phase), want, f"{role}/{phase}")

    def test_legal_targets_wolf_kill_excludes_wolves(self) -> None:
        s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p5": "villager"},
        )
        legal = self.reg.legal_targets("werewolf_kill", "p1", s)
        self.assertEqual(sorted(legal), ["p3", "p5"])  # narrow: no wolves, no dead

    def test_shown_targets_is_broad_alive_list_for_prompt_parity(self) -> None:
        # The model is SHOWN the full alive list (incl. self + teammates), exactly
        # like the engine's observation.alive_players (provider_agent.py:109) — the
        # narrow legal_targets must NOT drive the prompt (Phase-3 parity).
        s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p5": "villager"},
        )
        self.assertEqual(self.reg.shown_targets("werewolf_kill", s), ["p1", "p2", "p3", "p5"])

    def test_unknown_role_or_phase_returns_empty_not_keyerror(self) -> None:
        # Hardening: degrade to [] (clean invalid_action) instead of KeyError, matching the
        # pre-swap never-raise contract + guarding lockstep drift with the static map.
        self.assertEqual(self.reg.allowed_actions("hunter", "day_vote"), [])
        self.assertEqual(self.reg.allowed_actions("seer", "dusk"), [])

    def test_witch_night_actions_exact_order_including_pass(self) -> None:
        # B5-5: pin witch_pass's presence + position (the static-map parity test filters it out).
        self.assertEqual(
            self.reg.allowed_actions("witch", "night"),
            ["witch_save", "witch_poison", "witch_pass"],
        )


if __name__ == "__main__":
    unittest.main()
