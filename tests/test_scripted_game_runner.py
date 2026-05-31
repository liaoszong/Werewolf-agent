from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ScriptedGameFixtureTests(unittest.TestCase):
    def test_script_fixture_exists_and_has_contract_shape(self) -> None:
        path = ROOT / "docs/game-scripts/g1-scripted-game.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["script_id"], "g1_scripted_001")
        self.assertEqual(payload["game_id"], "g1_scripted_001")
        self.assertEqual(payload["source_label"], "[scripted deterministic output]")
        self.assertEqual(len(payload["players"]), 6)
        self.assertEqual(len(payload["steps"]), 15)
        self.assertEqual(payload["result"]["winner"], "villager")

        decision_steps = [step for step in payload["steps"] if "decision_actor" in step]
        self.assertEqual(len(decision_steps), 7)
        self.assertTrue(
            all(
                step["decision_source_label"] == "[scripted deterministic output]"
                for step in decision_steps
            )
        )

        wolf_kills = [step for step in payload["steps"] if step["type"] == "werewolf_kill"]
        self.assertEqual(len(wolf_kills), 2)
        self.assertTrue(
            all(
                step["consensus_source_label"] == "[scripted deterministic output]"
                for step in wolf_kills
            )
        )


class ScriptedGameRunnerTests(unittest.TestCase):
    def test_runner_emits_valid_log_dicts(self) -> None:
        from werewolf_eval.consensus_log import parse_consensus_log
        from werewolf_eval.decision_log import parse_decision_log
        from werewolf_eval.game_log import parse_game_log
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        outputs = run_scripted_game(script)

        game = parse_game_log(outputs.game_log)
        decision_log = parse_decision_log(outputs.decision_log, game)
        consensus_log = parse_consensus_log(outputs.consensus_log, game)

        self.assertEqual(game.game_id, "g1_scripted_001")
        self.assertEqual(outputs.game_log["source_label"], "[scripted deterministic output]")
        self.assertEqual(decision_log.source_label, "[scripted deterministic output]")
        self.assertEqual(consensus_log.source_label, "[scripted deterministic output]")
        self.assertEqual(len(game.events), 15)
        self.assertEqual(len(decision_log.decisions), 7)
        self.assertEqual(len(consensus_log.consensuses), 2)

    def test_runner_is_deterministic(self) -> None:
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        first = run_scripted_game(script)
        second = run_scripted_game(script)

        self.assertEqual(first.game_log, second.game_log)
        self.assertEqual(first.decision_log, second.decision_log)
        self.assertEqual(first.consensus_log, second.consensus_log)


class ScriptedGameCliTests(unittest.TestCase):
    def test_run_scripted_game_cli_writes_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_scripted_game",
                    str(ROOT / "docs/game-scripts/g1-scripted-game.json"),
                    "--game-log-out",
                    str(out / "game.json"),
                    "--decision-log-out",
                    str(out / "decision.json"),
                    "--consensus-log-out",
                    str(out / "consensus.json"),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("scripted_game_id=g1_scripted_001", result.stdout)
            self.assertIn("events=15", result.stdout)
            self.assertIn("decisions=7", result.stdout)
            self.assertIn("consensuses=2", result.stdout)
            self.assertEqual(
                json.loads(
                    (out / "decision.json").read_text(encoding="utf-8")
                )["source_label"],
                "[scripted deterministic output]",
            )
            self.assertEqual(
                json.loads(
                    (out / "consensus.json").read_text(encoding="utf-8")
                )["source_label"],
                "[scripted deterministic output]",
            )


class ScriptedGameArtifactProvenanceTests(unittest.TestCase):
    def test_generated_score_and_metrics_use_g1_ids(self) -> None:
        score_path = ROOT / "docs/generated-games/g1-scripted-score-log.json"
        metrics_path = ROOT / "docs/generated-games/g1-scripted-metrics-summary.json"
        score = json.loads(score_path.read_text(encoding="utf-8"))
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        combined = json.dumps({"score": score, "metrics": metrics}, ensure_ascii=False)
        self.assertEqual(score["game_id"], "g1_scripted_001")
        self.assertEqual(metrics["game_id"], "g1_scripted_001")
        self.assertNotIn("s2_g001", combined)
        self.assertNotIn("s5_g001", combined)
        self.assertIn("[scripted deterministic output]", combined)
        self.assertNotIn("[人工 gold sample]", combined)
        self.assertNotIn("[AI 生成]", combined)

    def test_generated_artifacts_are_not_written_to_gold_game(self) -> None:
        generated = sorted(
            (ROOT / "docs/generated-games").glob("g1-scripted-*.json")
        )
        self.assertGreaterEqual(len(generated), 5)
        gold_names = {
            path.name for path in (ROOT / "docs/gold-game").glob("g1-scripted-*.json")
        }
        self.assertEqual(gold_names, set())


class ScriptedGameEvaluatorPipelineTests(unittest.TestCase):
    def test_generated_logs_can_be_scored_and_rendered(self) -> None:
        from werewolf_eval.attribution import attribute_game
        from werewolf_eval.decision_log import load_decision_log
        from werewolf_eval.game_log import load_game_log
        from werewolf_eval.render_demo import build_demo_context, render_html
        from werewolf_eval.scoring import (
            score_game,
            score_log_to_dict,
            summarize_metrics,
            metrics_summary_to_dict,
        )

        game = load_game_log(
            ROOT / "docs/generated-games/g1-scripted-game-log.json"
        )
        decision_log = load_decision_log(
            ROOT / "docs/generated-games/g1-scripted-decision-log.json", game
        )
        score_log = score_game(game, decision_log=decision_log)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
        html = render_html(build_demo_context(game, score_log, metrics, attribution))

        score_payload = score_log_to_dict(score_log)
        metrics_payload = metrics_summary_to_dict(metrics)
        self.assertEqual(score_payload["game_id"], "g1_scripted_001")
        self.assertEqual(metrics_payload["game_id"], "g1_scripted_001")
        self.assertNotIn(
            "s2_g001", json.dumps(score_payload, ensure_ascii=False)
        )
        self.assertNotIn(
            "s2_g001", json.dumps(metrics_payload, ensure_ascii=False)
        )
        self.assertIn("G1a scripted deterministic fresh-log runner", html)
        self.assertIn("not live AI Agent gameplay", html)
        self.assertNotIn("https://", html)


if __name__ == "__main__":
    unittest.main()
