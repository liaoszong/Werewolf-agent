from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1, rules_v1_1


class RulesV11Tests(unittest.TestCase):
    def test_is_a_superset_versioned_variant(self) -> None:
        rs = rules_v1_1()
        self.assertEqual(rs.rules_version, "rules_v1_1")
        roles = {r.role for r in rs.roles}
        self.assertEqual(roles, {"werewolf", "seer", "witch", "villager", "hunter"})
        # backward-compatible: the 4 original roles' abilities are unchanged vs rules_v1.
        v1 = {r.role: r.ability_ids for r in rules_v1().roles}
        for r in rules_v1_1().roles:
            if r.role in v1:
                self.assertEqual(r.ability_ids, v1[r.role], f"{r.role} drifted")

    def test_four_role_allowed_actions_identical_to_rules_v1(self) -> None:
        # The byte-safety claim: rules_v1_1 yields the same allowed_actions as rules_v1 for
        # every (original role, phase) reached by decide().
        a, b = RoleAbilityRegistry(rules_v1()), RoleAbilityRegistry(rules_v1_1())
        for role in ("werewolf", "seer", "witch", "villager"):
            for phase in ("night", "day_vote"):
                self.assertEqual(a.allowed_actions(role, phase), b.allowed_actions(role, phase),
                                 f"{role}/{phase} drifted")

    def test_hunter_has_day_vote_and_on_death_shot(self) -> None:
        reg = RoleAbilityRegistry(rules_v1_1())
        self.assertEqual(reg.allowed_actions("hunter", "day_vote"), ["player_vote"])
        on_death = [a.action_id for a in reg.on_death_abilities("hunter")]
        self.assertEqual(on_death, ["hunter_shoot", "hunter_pass"])
        self.assertEqual(reg.ability("hunter_shoot").target_rule, "exclude_self")
        # the hunter's on_death abilities are NOT reachable via the phase-keyed allowed_actions
        # (they have trigger event:on_death) — the engine must validate the shot via the predicate.
        self.assertEqual(reg.allowed_actions("hunter", "night"), [])

    def test_base_roles_have_no_on_death_trigger(self) -> None:
        # the engine death-hook must be a no-op for a 4-role game (determinism).
        reg = RoleAbilityRegistry(rules_v1_1())
        for role in ("werewolf", "seer", "witch", "villager"):
            self.assertEqual(reg.on_death_abilities(role), [], f"{role} unexpectedly triggers on death")


if __name__ == "__main__":
    unittest.main()
