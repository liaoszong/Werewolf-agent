from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.consensus_log import parse_consensus_log
from werewolf_eval.decision_log import parse_decision_log
from werewolf_eval.emergent_engine import (
    EmergentBudget,
    EmergentGameEngine,
    SPEECH_EMPTY_PLACEHOLDER,
    build_emergent_config,
)
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
    build_werewolf_win_script,
)
from werewolf_eval.fake_provider import DeterministicFakeProvider
from werewolf_eval.game_log import parse_game_log
from werewolf_eval.provider_agent import ProviderAgent


def _run(script, *, seed=0, budget=None, game_id="p2a1_test"):
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=game_id),
        agents=build_emergent_fake_agents(script),
        seed=seed,
        budget=budget,
    )
    return engine.run()


class VillagerWinTests(unittest.TestCase):
    def test_completes_with_villager_win(self) -> None:
        outcome = _run(build_villager_win_script())
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(outcome.game_log["result"]["winner"], "villager")
        self.assertEqual(outcome.game_log["result"]["end_condition"], "all_werewolves_eliminated")
        self.assertEqual(outcome.game_log["result"]["end_round"], 2)
        self.assertEqual(sorted(outcome.game_log["result"]["survivors"]), ["p4", "p5", "p6"])

    def test_all_four_logs_validate(self) -> None:
        outcome = _run(build_villager_win_script())
        game = parse_game_log(outcome.game_log)
        parse_decision_log(outcome.decision_log, game)
        parse_consensus_log(outcome.consensus_log, game)
        # failure audit is a plain dict; assert shape
        self.assertEqual(outcome.failure_audit["game_id"], "p2a1_test")
        self.assertIsInstance(outcome.failure_audit["failures"], list)

    def test_deterministic_same_seed_byte_identical(self) -> None:
        a = _run(build_villager_win_script())
        b = _run(build_villager_win_script())
        self.assertEqual(
            json.dumps(a.game_log, ensure_ascii=False, sort_keys=True),
            json.dumps(b.game_log, ensure_ascii=False, sort_keys=True),
        )
        self.assertEqual(
            json.dumps(a.decision_log, ensure_ascii=False, sort_keys=True),
            json.dumps(b.decision_log, ensure_ascii=False, sort_keys=True),
        )

    def test_speeches_emitted_for_each_alive_player_round1(self) -> None:
        outcome = _run(build_villager_win_script())
        speeches = [e for e in outcome.game_log["events"] if e["type"] == "player_speech" and e["round"] == 1]
        self.assertEqual(sorted(e["actor"] for e in speeches), ["p1", "p2", "p3", "p4", "p5", "p6"])
        # speeches are public natural text in data.summary
        self.assertTrue(all(e["visibility"] == "public" for e in speeches))
        self.assertTrue(all(e["data"]["summary"] for e in speeches))

    def test_witch_save_prevents_night1_death(self) -> None:
        outcome = _run(build_villager_win_script())
        deaths_n1 = [e for e in outcome.game_log["events"] if e["type"] == "player_died" and e["round"] == 1]
        self.assertEqual(deaths_n1, [])  # p5 was saved

    def test_seer_result_is_private_and_truthful(self) -> None:
        outcome = _run(build_villager_win_script())
        seer_events = [e for e in outcome.game_log["events"] if e["type"] == "seer_check"]
        self.assertTrue(seer_events)
        for e in seer_events:
            self.assertEqual(e["visibility"], "seer")
        # p3 checked p1 (a werewolf) round 1
        e1 = next(e for e in seer_events if e["round"] == 1)
        self.assertIn("werewolf", e1["data"]["summary"])


class WerewolfWinTests(unittest.TestCase):
    def test_completes_with_werewolf_win_by_parity(self) -> None:
        outcome = _run(build_werewolf_win_script())
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(outcome.game_log["result"]["winner"], "werewolf")
        self.assertEqual(outcome.game_log["result"]["end_condition"], "werewolves_reach_parity")
        self.assertEqual(outcome.game_log["result"]["end_round"], 1)

    def test_logs_validate(self) -> None:
        outcome = _run(build_werewolf_win_script())
        game = parse_game_log(outcome.game_log)
        parse_decision_log(outcome.decision_log, game)
        parse_consensus_log(outcome.consensus_log, game)


class TieBreakTests(unittest.TestCase):
    def _tie_script(self):
        # p3/p4 vote p1 ; p5/p6 vote p2 ; p1->p3 p2->p4  => p1,p2 tie at 2 each
        s = build_villager_win_script()
        s[("p5", "day", 1)] = json.dumps({"action": "player_vote", "target": "p2", "reason_summary": "x", "decision_type": "inference_based", "confidence": 1.0}, ensure_ascii=False)
        s[("p6", "day", 1)] = json.dumps({"action": "player_vote", "target": "p2", "reason_summary": "x", "decision_type": "inference_based", "confidence": 1.0}, ensure_ascii=False)
        s[("p1", "day", 1)] = json.dumps({"action": "player_vote", "target": "p3", "reason_summary": "x", "decision_type": "inference_based", "confidence": 1.0}, ensure_ascii=False)
        s[("p2", "day", 1)] = json.dumps({"action": "player_vote", "target": "p4", "reason_summary": "x", "decision_type": "inference_based", "confidence": 1.0}, ensure_ascii=False)
        return s

    def test_seeded_tiebreak_is_deterministic_per_seed(self) -> None:
        a = _run(self._tie_script(), seed=7, game_id="tie")
        b = _run(self._tie_script(), seed=7, game_id="tie")
        elim_a = [e["target"] for e in a.game_log["events"] if e["type"] == "player_eliminated" and e["round"] == 1]
        elim_b = [e["target"] for e in b.game_log["events"] if e["type"] == "player_eliminated" and e["round"] == 1]
        self.assertEqual(elim_a, elim_b)
        self.assertIn(elim_a[0], ("p1", "p2"))


class RobustnessTests(unittest.TestCase):
    def test_bad_vote_target_falls_back_and_game_finishes(self) -> None:
        s = build_villager_win_script()
        # p6 votes an invalid target -> failure + fallback, game still completes
        s[("p6", "day", 1)] = json.dumps({"action": "player_vote", "target": "p99", "reason_summary": "x", "decision_type": "inference_based", "confidence": 1.0}, ensure_ascii=False)
        outcome = _run(s)
        self.assertEqual(outcome.status, "completed")
        kinds = [f["kind"] for f in outcome.failure_audit["failures"]]
        self.assertIn("invalid_action", kinds)
        # log still validates
        parse_game_log(outcome.game_log)

    def test_malformed_speech_uses_placeholder(self) -> None:
        from werewolf_eval.emergent_engine import SPEECH_REQUEST_PHASE
        s = build_villager_win_script()
        s[("p2", SPEECH_REQUEST_PHASE, 1)] = "   "  # whitespace only
        outcome = _run(s)
        p2_speech = next(e for e in outcome.game_log["events"] if e["type"] == "player_speech" and e["actor"] == "p2" and e["round"] == 1)
        self.assertEqual(p2_speech["data"]["summary"], SPEECH_EMPTY_PLACEHOLDER)

    def test_witch_cannot_poison_twice(self) -> None:
        # Focused unit test of the resolver's once-only poison constraint: with
        # poison already used, a witch_kill must be rejected and apply no poison.
        s = build_villager_win_script()
        s[("p4", "night", 1)] = json.dumps({"action": "witch_kill", "target": "p6", "reason_summary": "x", "decision_type": "retaliatory", "confidence": 1.0}, ensure_ascii=False)
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="witch"),
            agents=build_emergent_fake_agents(s),
            seed=0,
        )
        # emit a setup event so any refs are valid, then call the resolver directly
        engine._emit("setup", 0, "role_assignment", "system", "none", "public", "setup")
        saved, poison_target, save_used, poison_used = engine._resolve_witch(
            rnd=1, victim="p5", save_used=False, poison_used=True
        )
        self.assertFalse(saved)
        self.assertIsNone(poison_target)  # poison rejected -> no target applied
        self.assertTrue(poison_used)  # stays consumed (unchanged from input)
        kinds = [f["kind"] for f in engine._failures]
        self.assertIn("invalid_action", kinds)


class BudgetTests(unittest.TestCase):
    def test_budget_exhaustion_is_fail_closed(self) -> None:
        outcome = _run(build_villager_win_script(), budget=EmergentBudget(max_requests=3, max_day_rounds=3))
        self.assertEqual(outcome.status, "failed")
        self.assertIsNone(outcome.game_log)
        self.assertEqual(outcome.end_condition, "budget_exhausted")
        kinds = [f["kind"] for f in outcome.failure_audit["failures"]]
        self.assertIn("budget_exhausted", kinds)

    def test_round_cap_is_fail_closed(self) -> None:
        # A script that never resolves a winner within the cap: nobody ever dies.
        # Wolves "kill" but witch saves every round; votes all abstain-equivalent.
        # Simplest: max_day_rounds=0 forces immediate round-cap failure.
        outcome = _run(build_villager_win_script(), budget=EmergentBudget(max_requests=80, max_day_rounds=0))
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(outcome.end_condition, "round_cap")


if __name__ == "__main__":
    unittest.main()
