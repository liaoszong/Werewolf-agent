from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1, rules_v1_1
from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_hunter_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_hunter_night_kill_script,
    build_hunter_voteout_script,
)


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


class HunterGameTests(unittest.TestCase):
    """End-to-end: a hunter board runs and the hunter takes a model-driven shot on death
    (proving 'add role = add data' — the only new code is the trigger + shot resolver)."""

    def _run(self, script):
        engine = EmergentGameEngine(
            config=build_emergent_hunter_config(),
            agents=build_emergent_fake_agents(script), seed=0,
        )
        return engine.run()

    @staticmethod
    def _events(outcome):
        return outcome.game_log["events"]

    def test_hunter_shoots_on_night_death(self) -> None:
        outcome = self._run(build_hunter_night_kill_script())
        self.assertEqual(outcome.status, "completed")
        shots = [e for e in self._events(outcome) if e["type"] == "hunter_shoot"]
        self.assertEqual(len(shots), 1)
        self.assertEqual((shots[0]["actor"], shots[0]["target"]), ("p6", "p1"))
        # the shot target actually died
        self.assertTrue([e for e in self._events(outcome) if e["type"] == "player_died" and e.get("target") == "p1"])
        # both wolves gone (p1 shot, p2 voted) -> villager win
        self.assertEqual(outcome.game_log["result"]["winner"], "villager")

    def test_hunter_shoots_on_voteout_day_path(self) -> None:
        # Exercises the DAY death hook + the distinct shot key (fix #3): the shot must read
        # (p6,"hunter_shot",1), NOT p6's own day-vote entry (p6,"day",1).
        outcome = self._run(build_hunter_voteout_script())
        self.assertEqual(outcome.status, "completed")
        shots = [e for e in self._events(outcome) if e["type"] == "hunter_shoot"]
        self.assertEqual(len(shots), 1)
        self.assertEqual((shots[0]["actor"], shots[0]["target"]), ("p6", "p1"))
        # p6 ALSO cast a real day vote (its vote key wasn't swallowed by the shot)
        p6_votes = [e for e in self._events(outcome) if e["type"] == "player_vote" and e["actor"] == "p6"]
        self.assertEqual(len(p6_votes), 1)
        self.assertEqual(outcome.game_log["result"]["winner"], "villager")

    def test_hunter_pass_fires_no_shot(self) -> None:
        s = build_hunter_night_kill_script()
        # witch poisons wolf p1 so the game still ends day-1; the hunter PASSES (no shot).
        s[("p4", "night", 1)] = json.dumps(
            {"action": "witch_poison", "target": "p1", "reason_summary": "x", "decision_type": "retaliatory", "confidence": 1.0},
            ensure_ascii=False)
        s[("p6", "hunter_shot", 1)] = json.dumps(
            {"action": "hunter_pass", "target": "none", "reason_summary": "no shot", "decision_type": "default", "confidence": 1.0},
            ensure_ascii=False)
        outcome = self._run(s)
        self.assertEqual(outcome.status, "completed")
        self.assertTrue([e for e in self._events(outcome) if e["type"] == "hunter_pass"])
        self.assertFalse([e for e in self._events(outcome) if e["type"] == "hunter_shoot"])

    def test_4role_game_unaffected_no_hunter_events(self) -> None:
        # The hunter machinery is inert on a 4-role board (add-role = add-data, not a global change).
        from werewolf_eval.emergent_engine import build_emergent_config
        from werewolf_eval.emergent_fake_script import build_villager_win_script
        engine = EmergentGameEngine(config=build_emergent_config(game_id="plain"),
                                    agents=build_emergent_fake_agents(build_villager_win_script()), seed=0)
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        self.assertFalse([e for e in outcome.game_log["events"] if e["type"] in ("hunter_shoot", "hunter_pass")])


if __name__ == "__main__":
    unittest.main()
