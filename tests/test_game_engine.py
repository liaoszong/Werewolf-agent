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
        self.assertNotIn("consensus_log", outputs.__dict__)
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
        self.assertEqual(first["target"], "p5")

    def test_g1c_split_wolf_vote_records_no_consensus_and_audit(self):
        result = run_mock_game_for_test(mode="g1c_split_wolf_vote")
        consensus_log = result["consensus_log"]
        audit = result["failure_audit"]

        self.assertTrue(any(item["status"] == "no_consensus" for item in consensus_log["consensuses"]))
        self.assertTrue(any(item["kind"] == "wolf_consensus_failure" for item in audit["failures"]))
        self.assertFalse(any(item.get("repaired_to_valid_action") for item in audit["failures"]))

    def test_g1c_invalid_wolf_action_is_rejected_not_repaired(self):
        result = run_mock_game_for_test(mode="g1c_invalid_wolf_action")
        audit = result["failure_audit"]
        decision_log = result["decision_log"]

        self.assertTrue(any(item["kind"] == "invalid_action" for item in audit["failures"]))
        invalid_targets = {item["target"] for item in audit["failures"] if item["kind"] == "invalid_action"}
        valid_decision_targets = {item.get("target") for item in decision_log["decisions"]}
        self.assertTrue(invalid_targets.isdisjoint(valid_decision_targets))

    def test_g1c_timeout_and_parse_failure_are_audited(self):
        result = run_mock_game_for_test(mode="g1c_timeout_parse_failure")
        kinds = {item["kind"] for item in result["failure_audit"]["failures"]}

        self.assertIn("timeout", kinds)
        self.assertIn("parse_failure", kinds)


if __name__ == "__main__":
    unittest.main()
