from __future__ import annotations

import json
import sys
import tempfile
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
    SPEECH_REQUEST_PHASE,
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
from werewolf_eval.runtime_events import RuntimeEventWriter


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

    def test_witch_poison_uses_eval_vocabulary_and_is_scored(self) -> None:
        # Regression (P2-A): the witch's poison must use the eval-contract vocabulary
        # "witch_poison" (the string scoring/attribution and gold-game g001 expect),
        # NOT "witch_kill". A mismatch makes score_game silently SKIP the poison event
        # AND its decision (scoring.py filters both on SCORE_RELEVANT_*), under-scoring
        # the witch. Mirror the witch_save pattern: one string across action/decision/event.
        from werewolf_eval.scoring import score_game

        outcome = _run(build_villager_win_script())
        game = parse_game_log(outcome.game_log)
        # 1) game-log event vocabulary
        poison_events = [e for e in game.events if e.type == "witch_poison"]
        self.assertEqual(len(poison_events), 1)
        self.assertEqual((poison_events[0].actor, poison_events[0].target), ("p4", "p2"))
        self.assertNotIn("witch_kill", [e.type for e in game.events])
        # 2) decision-log action vocabulary
        decision_log = parse_decision_log(outcome.decision_log, game)
        self.assertEqual(len([d for d in decision_log.decisions if d.action == "witch_poison"]), 1)
        self.assertNotIn("witch_kill", [d.action for d in decision_log.decisions])
        # 3) end-to-end: the poison is now actually scored (was silently dropped before)
        score_log = score_game(game, decision_log)
        witch_poison_records = [r for r in score_log.records if r.actor == "p4" and r.action_type == "witch_poison"]
        self.assertEqual(len(witch_poison_records), 1)

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

    def test_bad_wolf_kill_targets_teammate_falls_back(self) -> None:
        # Phase-3 validator swap reject path: p1 tries to kill wolf teammate p2 ->
        # invalid -> failure recorded; game still completes (p2's valid proposal wins).
        s = build_villager_win_script()
        s[("p1", "night", 1)] = json.dumps({"action": "werewolf_kill", "target": "p2", "reason_summary": "x", "decision_type": "team_coordinated", "confidence": 1.0}, ensure_ascii=False)
        outcome = _run(s)
        self.assertEqual(outcome.status, "completed")
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])
        parse_game_log(outcome.game_log)

    def test_bad_seer_check_self_falls_back(self) -> None:
        # Phase-3 validator swap reject path: p3 (seer) checks itself -> invalid -> fallback.
        s = build_villager_win_script()
        s[("p3", "night", 1)] = json.dumps({"action": "seer_check", "target": "p3", "reason_summary": "x", "decision_type": "inference_based", "confidence": 1.0}, ensure_ascii=False)
        outcome = _run(s)
        self.assertEqual(outcome.status, "completed")
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])
        parse_game_log(outcome.game_log)

    def test_voter_votes_self_falls_back(self) -> None:
        # Audit B5-3: the ONLY validator-discriminated vote reject is a self-vote (dead/unknown
        # targets are caught upstream by ProviderAgent.decide). p6 votes itself -> invalid -> fallback.
        s = build_villager_win_script()
        s[("p6", "day", 1)] = json.dumps({"action": "player_vote", "target": "p6", "reason_summary": "x", "decision_type": "inference_based", "confidence": 1.0}, ensure_ascii=False)
        outcome = _run(s)
        self.assertEqual(outcome.status, "completed")
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])
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
        # poison already used, a witch_poison must be rejected and apply no poison.
        s = build_villager_win_script()
        s[("p4", "night", 1)] = json.dumps({"action": "witch_poison", "target": "p6", "reason_summary": "x", "decision_type": "retaliatory", "confidence": 1.0}, ensure_ascii=False)
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


class _DiskSnoopProvider:
    """Wraps a provider and, at the FIRST round-1 day speech (by which point all
    night-1 events have already been emitted), snapshots ``game-log.json`` from
    disk into *captured*. Proves the partial game-log is readable mid-run — the
    exact thing the live theater's projection needs to draw night-1 pointing
    lines and speech bodies BEFORE the game ends."""

    def __init__(self, inner, out_dir: Path, captured: dict) -> None:
        self._inner = inner
        self._out_dir = Path(out_dir)
        self._captured = captured

    def respond(self, request):
        if (
            request.phase == SPEECH_REQUEST_PHASE
            and request.round == 1
            and not self._captured.get("_taken")
        ):
            self._captured["_taken"] = True
            try:
                self._captured["log"] = json.loads(
                    (self._out_dir / "game-log.json").read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                self._captured["log"] = None   # absent/torn -> pre-fix behaviour
        return self._inner.respond(request)


class LivePartialLogTests(unittest.TestCase):
    """Option A: the emergent engine mirrors the in-progress game-log/decision-log
    to the spine dir as events are emitted, so the live projection can enrich
    events (summary/target/reason_summary) WHILE the game runs — not only at end."""

    def test_game_log_readable_mid_run_for_projection(self) -> None:
        script = build_villager_win_script()
        captured: dict = {}
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            writer = RuntimeEventWriter(run_id="g_mid", out_dir=out_dir)
            agents = {
                pid: ProviderAgent(
                    player_id=pid,
                    provider=_DiskSnoopProvider(
                        DeterministicFakeProvider(dict(script)), out_dir, captured
                    ),
                )
                for pid in ("p1", "p2", "p3", "p4", "p5", "p6")
            }
            engine = EmergentGameEngine(
                config=build_emergent_config(game_id="g_mid"),
                agents=agents,
                seed=0,
                runtime_events=writer,
            )
            outcome = engine.run()

        self.assertEqual(outcome.status, "completed")
        log = captured.get("log")
        self.assertIsNotNone(
            log, "game-log.json must exist on disk during day-1 speeches (mid-run)"
        )
        events = log.get("events", [])
        kills = [e for e in events if e.get("type") == "werewolf_kill"]
        self.assertTrue(kills, "night-1 werewolf_kill must be on disk before day-1 speeches")
        # The two fields the theater needs: target (pointing line) + data.summary (body).
        self.assertEqual(kills[0].get("target"), "p5")
        self.assertEqual(kills[0]["data"]["summary"], "Wolf team kills p5.")

    def test_failed_run_leaves_no_partial_logs(self) -> None:
        # fail-closed invariant: a failed run must leave NO game log on disk, even
        # though setup events were emitted (and a partial was written) before the
        # round-cap failure. The cleanup in _failed_outcome must remove them.
        script = build_villager_win_script()
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            writer = RuntimeEventWriter(run_id="g_fail", out_dir=out_dir)
            engine = EmergentGameEngine(
                config=build_emergent_config(game_id="g_fail"),
                agents=build_emergent_fake_agents(script),
                seed=0,
                budget=EmergentBudget(max_requests=80, max_day_rounds=0),
                runtime_events=writer,
            )
            outcome = engine.run()
            self.assertEqual(outcome.status, "failed")
            self.assertFalse((out_dir / "game-log.json").exists())
            self.assertFalse((out_dir / "decision-log.json").exists())


if __name__ == "__main__":
    unittest.main()
