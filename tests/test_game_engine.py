from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class GameEngineContractTests(unittest.TestCase):
    def test_private_observation_hides_non_visible_roles(self) -> None:
        from werewolf_eval.game_engine import build_default_config, GameEngine

        engine = GameEngine.from_config(build_default_config(game_id="g1b_mock_001"))

        seer_observation = engine.observation_for("p3")
        self.assertEqual(seer_observation.player_id, "p3")
        self.assertEqual(seer_observation.role, "seer")
        self.assertEqual(seer_observation.team, "villager")
        self.assertEqual(seer_observation.known_roles, {"p3": "seer"})
        self.assertNotIn("p1", seer_observation.known_roles)
        self.assertNotIn("p2", seer_observation.known_roles)

        wolf_observation = engine.observation_for("p1")
        self.assertEqual(wolf_observation.role, "werewolf")
        self.assertEqual(wolf_observation.team, "werewolf")
        self.assertEqual(
            wolf_observation.known_roles,
            {"p1": "werewolf", "p2": "werewolf"},
        )

    def test_mock_agent_returns_structured_action(self) -> None:
        from werewolf_eval.game_engine import AgentAction, MockAgent

        agent = MockAgent(player_id="p3")
        action = agent.decide(
            observation={
                "game_id": "g1b_mock_001",
                "player_id": "p3",
                "role": "seer",
                "team": "villager",
                "phase": "night",
                "round": 1,
                "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
                "public_event_ids": [],
                "private_event_ids": [],
                "known_roles": {"p3": "seer"},
            }
        )

        self.assertIsInstance(action, AgentAction)
        self.assertEqual(action.actor, "p3")
        self.assertEqual(action.action, "seer_check")
        self.assertEqual(action.target, "p1")
        self.assertEqual(action.decision_type, "inference_based")
        self.assertEqual(action.source_label, "[deterministic mock agent output]")


class GameEngineOutputTests(unittest.TestCase):
    def test_engine_emits_valid_game_and_decision_logs(self) -> None:
        from werewolf_eval.decision_log import parse_decision_log
        from werewolf_eval.game_engine import build_default_config, GameEngine
        from werewolf_eval.game_log import parse_game_log

        outputs = GameEngine.from_config(build_default_config()).run()
        game = parse_game_log(outputs.game_log)
        decision_log = parse_decision_log(outputs.decision_log, game)

        self.assertEqual(game.game_id, "g1b_mock_001")
        self.assertEqual(outputs.game_log["source_label"], "[deterministic mock agent output]")
        self.assertEqual(decision_log.source_label, "[deterministic mock agent output]")
        self.assertEqual(len(game.events), 18)
        self.assertEqual(len(decision_log.decisions), 11)
        self.assertIsNone(outputs.consensus_log)
        self.assertEqual(game.result.winner, "villager")

    def test_engine_is_deterministic(self) -> None:
        from werewolf_eval.game_engine import build_default_config, GameEngine

        first = GameEngine.from_config(build_default_config()).run()
        second = GameEngine.from_config(build_default_config()).run()

        self.assertEqual(first.game_log, second.game_log)
        self.assertEqual(first.decision_log, second.decision_log)


class GameEngineCliTests(unittest.TestCase):
    def test_run_mock_game_cli_writes_game_and_decision_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_mock_game",
                    "--game-id",
                    "g1b_mock_001",
                    "--game-log-out",
                    str(out / "game.json"),
                    "--decision-log-out",
                    str(out / "decision.json"),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("mock_game_id=g1b_mock_001", result.stdout)
            self.assertIn("events=18", result.stdout)
            self.assertIn("decisions=11", result.stdout)
            self.assertIn("consensus=not_generated", result.stdout)

            game = json.loads((out / "game.json").read_text(encoding="utf-8"))
            decision = json.loads((out / "decision.json").read_text(encoding="utf-8"))
            self.assertEqual(game["game_id"], "g1b_mock_001")
            self.assertEqual(game["source_label"], "[deterministic mock agent output]")
            self.assertEqual(decision["source_label"], "[deterministic mock agent output]")


class GameEngineEvaluatorPipelineTests(unittest.TestCase):
    def test_g1b_generated_logs_can_be_scored_and_rendered(self) -> None:
        from werewolf_eval.attribution import attribute_game
        from werewolf_eval.decision_log import load_decision_log
        from werewolf_eval.game_log import load_game_log
        from werewolf_eval.render_demo import build_demo_context, render_html
        from werewolf_eval.scoring import score_game, summarize_metrics

        game_log_path = ROOT / "docs/generated-games/g1b-mock-agent-game-log.json"
        raw = json.loads(game_log_path.read_text(encoding="utf-8"))
        game_source_label = raw["source_label"]

        game = load_game_log(game_log_path)
        decision_log = load_decision_log(
            ROOT / "docs/generated-games/g1b-mock-agent-decision-log.json",
            game,
        )
        score_log = score_game(game, decision_log=decision_log)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
        html = render_html(build_demo_context(game, score_log, metrics, attribution, game_source_label=game_source_label))

        self.assertEqual(score_log.game_id, "g1b_mock_001")
        self.assertEqual(metrics.game_id, "g1b_mock_001")
        self.assertIn("g1b_mock_001", html)
        self.assertNotIn("https://", html)
        self.assertIn("[deterministic mock agent output]", html)
        self.assertNotIn("[人工 gold sample]", html)

    def test_g1b_artifacts_do_not_claim_provider_or_consensus(self) -> None:
        paths = [
            ROOT / "docs/generated-games/g1b-mock-agent-game-log.json",
            ROOT / "docs/generated-games/g1b-mock-agent-decision-log.json",
            ROOT / "docs/generated-games/g1b-mock-agent-score-log.json",
            ROOT / "docs/generated-games/g1b-mock-agent-metrics-summary.json",
            ROOT / "docs/demo/phase3-g1b-mock-agent-runtime-demo.html",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

        self.assertIn("[deterministic mock agent output]", combined)
        for forbidden in [
            "provider-backed",
            "live AI Agent gameplay",
            "human-vs-AI UI",
            "real multi-game Leaderboard",
            "consensus_log_id",
            "g001_",
            "g1_scripted_001",
            "[人工 gold sample]",
        ]:
            self.assertNotIn(forbidden, combined)

        demo_html = (ROOT / "docs/demo/phase3-g1b-mock-agent-runtime-demo.html").read_text(encoding="utf-8")
        self.assertIn("[deterministic mock agent output]", demo_html)
        self.assertNotIn("[人工 gold sample]", demo_html)

        self.assertFalse((ROOT / "docs/generated-games/g1b-mock-agent-consensus-log.json").exists())


def run_mock_game_for_test(mode: str = "g1c_consensus") -> dict:
    from werewolf_eval.game_engine import GameEngine, build_default_config

    game_id_map = {
        "g1c_consensus": "g1c_wolf_consensus",
        "g1c_split_wolf_vote": "g1c_split_wolf_vote",
        "g1c_invalid_wolf_action": "g1c_invalid_wolf_action",
        "g1c_timeout_parse_failure": "g1c_timeout_parse_failure",
    }
    game_id = game_id_map.get(mode, "g1c_wolf_consensus")
    outputs = GameEngine.from_config(build_default_config(game_id=game_id)).run(mode=mode)

    return {
        "game_log": outputs.game_log,
        "decision_log": outputs.decision_log,
        "consensus_log": getattr(outputs, "consensus_log", {}),
        "failure_audit": getattr(outputs, "failure_audit", {}),
    }


class GameEngineConsensusCliTests(unittest.TestCase):
    def test_run_mock_game_g1c_cli_writes_all_four_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            game_log_path = out / "game.json"
            decision_log_path = out / "decision.json"
            consensus_log_path = out / "consensus.json"
            failure_audit_path = out / "failure.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_mock_game",
                    "--game-id", "g1c_wolf_consensus",
                    "--mode", "g1c_consensus",
                    "--game-log-out", str(game_log_path),
                    "--decision-log-out", str(decision_log_path),
                    "--consensus-log-out", str(consensus_log_path),
                    "--failure-audit-out", str(failure_audit_path),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("consensus_entries=2", result.stdout)
            self.assertTrue(game_log_path.exists())
            self.assertTrue(decision_log_path.exists())
            self.assertTrue(consensus_log_path.exists())
            self.assertTrue(failure_audit_path.exists())

            consensus_log = json.loads(consensus_log_path.read_text(encoding="utf-8"))
            failure_audit = json.loads(failure_audit_path.read_text(encoding="utf-8"))
            self.assertEqual(consensus_log["source_label"], "[deterministic mock agent output]")
            self.assertEqual(failure_audit["source_label"], "[deterministic mock agent output]")


class GameEngineConsensusTests(unittest.TestCase):
    def test_g1c_wolf_consensus_log_is_emitted_for_valid_night_kill(self):
        result = run_mock_game_for_test(mode="g1c_consensus")
        consensus_log = result["consensus_log"]

        self.assertEqual(consensus_log["game_id"], result["game_log"]["game_id"])
        self.assertEqual(consensus_log["source_label"], "[deterministic mock agent output]")
        self.assertGreaterEqual(len(consensus_log["consensuses"]), 1)

        first = consensus_log["consensuses"][0]
        self.assertEqual(first["phase"], "night")
        self.assertEqual(first["status"], "consensus")
        self.assertIn("p1", first["participants"])
        self.assertIn("p2", first["participants"])
        self.assertEqual(first["final_decision"]["target"], "p5")

        # wolf_team Decision Log entries carry matching consensus_id
        wolf_team_decisions = [
            d for d in result["decision_log"]["decisions"]
            if d["actor"] == "wolf_team" and d["action"] == "werewolf_kill"
        ]
        self.assertGreaterEqual(len(wolf_team_decisions), 1)
        for wtd in wolf_team_decisions:
            self.assertIsNotNone(wtd["consensus_id"],
                                 f"wolf_team decision {wtd['decision_id']} has null consensus_id")
            self.assertIn(
                wtd["consensus_id"],
                {c["consensus_id"] for c in consensus_log["consensuses"]},
                f"wolf_team decision consensus_id {wtd['consensus_id']!r} not found in Consensus Log",
            )

    def test_g1c_split_wolf_vote_records_no_consensus_and_audit(self):
        from werewolf_eval.game_log import parse_game_log

        result = run_mock_game_for_test(mode="g1c_split_wolf_vote")
        consensus_log = result["consensus_log"]
        audit = result["failure_audit"]

        self.assertTrue(any(item["status"] == "coordinator_tie_break" for item in consensus_log["consensuses"]))
        self.assertTrue(any(item["kind"] == "wolf_consensus_failure" for item in audit["failures"]))
        self.assertFalse(any(item.get("repaired_to_valid_action") for item in audit["failures"]))

        # Game Log must validate
        game = parse_game_log(result["game_log"])
        self.assertEqual(game.game_id, "g1c_split_wolf_vote")

        # where both werewolf_kill and player_died exist for the same round, targets must match
        kill_by_round: dict[int, str] = {}
        died_by_round: dict[int, str] = {}
        for e in game.events:
            if e.type == "werewolf_kill":
                kill_by_round[e.round] = e.target
            elif e.type == "player_died":
                died_by_round[e.round] = e.target
        for rnd in sorted(set(kill_by_round) & set(died_by_round)):
            self.assertEqual(kill_by_round[rnd], died_by_round[rnd],
                             f"round {rnd}: kill target={kill_by_round[rnd]} != died target={died_by_round[rnd]}")

    def test_g1c_invalid_wolf_action_is_rejected_not_repaired(self):
        from werewolf_eval.consensus_log import parse_consensus_log
        from werewolf_eval.game_log import parse_game_log

        result = run_mock_game_for_test(mode="g1c_invalid_wolf_action")
        audit = result["failure_audit"]
        decision_log = result["decision_log"]
        consensus_log = result["consensus_log"]

        self.assertTrue(any(item["kind"] == "invalid_action" for item in audit["failures"]))
        invalid_actions = [item for item in audit["failures"] if item["kind"] == "invalid_action"]
        invalid_targets = {item["target"] for item in invalid_actions}
        valid_decision_targets = {item.get("target") for item in decision_log["decisions"]}
        self.assertTrue(invalid_targets.isdisjoint(valid_decision_targets))

        # p1 invalid p99 is audited
        p1_invalid = [item for item in invalid_actions if item["actor"] == "p1" and item.get("target") == "p99"]
        self.assertTrue(len(p1_invalid) > 0, "p1 invalid p99 must be audited")

        # p99 does not appear as a valid Decision Log target
        self.assertNotIn("p99", valid_decision_targets)

        # Consensus Log validates
        game = parse_game_log(result["game_log"])
        parsed_cl = parse_consensus_log(consensus_log, game)
        self.assertIsNotNone(parsed_cl)

        # p1 is covered by supporters or dissenters
        r1_consensus = consensus_log["consensuses"][0]
        fd = r1_consensus["final_decision"]
        self.assertIn("p1", r1_consensus["participants"])
        covered = set(fd["supporters"]) | set(fd["dissenters"])
        self.assertIn("p1", covered)

    def test_g1c_timeout_and_parse_failure_are_audited(self):
        from werewolf_eval.game_log import parse_game_log

        result = run_mock_game_for_test(mode="g1c_timeout_parse_failure")

        # Failure-mode Game Log must validate (continuous sequence even when events are skipped)
        game = parse_game_log(result["game_log"])
        self.assertEqual(game.game_id, "g1c_timeout_parse_failure")

        kinds = {item["kind"] for item in result["failure_audit"]["failures"]}

        self.assertIn("timeout", kinds)
        self.assertIn("parse_failure", kinds)

        # No wolf_team werewolf_kill Decision Log entry is produced from the failed round 1 actions
        wolf_kill_decisions = [
            item for item in result["decision_log"]["decisions"]
            if item["actor"] == "wolf_team" and item["action"] == "werewolf_kill"
        ]
        # Round 2 produces a valid kill; ensure none have forced_random decision_type
        self.assertFalse(
            any(item.get("decision_type") == "forced_random" for item in wolf_kill_decisions),
            "no forced_random kill decision from timeout/parse_failure")
        # The failed round 1 must not produce a kill targeting p5 via forced_random
        forced_p5 = [
            item for item in wolf_kill_decisions
            if item.get("target") == "p5" and item.get("decision_type") == "forced_random"
        ]
        self.assertEqual(len(forced_p5), 0,
                         "no forced_random p5 target from timeout/parse_failure")

        # No werewolf_kill events in game log from the failed round 1 consensus
        kill_events = [
            e for e in result["game_log"]["events"]
            if e["type"] == "werewolf_kill"
        ]
        # Round 2 produces a valid kill event (target p3); verify none are forced_random-derived
        forced_kill_events = [
            e for e in kill_events
            if e["target"] == "p5" and e["round"] == 1
        ]
        self.assertEqual(len(forced_kill_events), 0,
                         "no werewolf_kill event from failed round 1 actions")

        # timeout/parse_failure entries have repaired_to_valid_action=false
        for item in result["failure_audit"]["failures"]:
            self.assertFalse(item.get("repaired_to_valid_action"),
                             f"{item['kind']} must not be marked repaired_to_valid_action")


if __name__ == "__main__":
    unittest.main()
