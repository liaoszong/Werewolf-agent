from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.game_log import load_game_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.semantic_labels import load_semantic_label_log
from werewolf_eval.scoring import score_game, summarize_metrics
from werewolf_eval.attribution import attribute_game
from werewolf_eval.render_demo import build_demo_context, render_html, write_demo_html


class RuntimeDemoRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.attribution = attribute_game(self.game, self.score_log, self.metrics)
        self.decision_log = load_decision_log(ROOT / "docs/gold-game/g001-decision-log.json", self.game)
        self.semantic_label_log = load_semantic_label_log(
            ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
            self.decision_log,
        )
        self.s5_score_log = score_game(
            self.game,
            decision_log=self.decision_log,
            semantic_label_log=self.semantic_label_log,
        )
        self.s5_metrics = summarize_metrics(self.game, self.s5_score_log)
        self.s5_attribution = attribute_game(self.game, self.s5_score_log, self.s5_metrics)

    def test_build_demo_context_uses_runtime_outputs(self) -> None:
        context = build_demo_context(self.game, self.score_log, self.metrics, self.attribution)

        self.assertEqual(context["game"]["game_id"], "g001")
        self.assertEqual(context["game"]["winner"], "villager")
        self.assertEqual(context["game"]["winner_label"], "村民阵营")
        self.assertEqual(context["game"]["players"], 6)
        self.assertEqual(context["game"]["events"], 38)
        self.assertEqual(context["score"]["records"], 14)
        self.assertEqual(context["attribution"]["turn_points"], 1)
        self.assertEqual(context["attribution"]["top_turn_point"], "s3_g001_tp001")
        self.assertGreaterEqual(len(context["timeline"]), 38)
        self.assertTrue(any(row["source_label"] == "[deterministic]" for row in context["leaderboard"]))
        self.assertTrue(any(row["source_label"] == "[mock]" for row in context["leaderboard"]))
        deterministic_row = next(row for row in context["leaderboard"] if row["source_label"] == "[deterministic]")
        self.assertEqual(deterministic_row["games_played"], 1)
        self.assertEqual(
            deterministic_row["avg_outcome_score"],
            sum(context["score"]["summary"]["player_outcome_scores"].values())
            + sum(context["score"]["summary"]["team_outcome_scores"].values()),
        )

    def test_render_html_contains_required_demo_sections_and_boundaries(self) -> None:
        context = build_demo_context(self.game, self.score_log, self.metrics, self.attribution)
        html = render_html(context)

        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("Werewolf-agent Phase 2 Runtime Demo", html)
        self.assertIn("运行时生成", html)
        self.assertIn("时间线", html)
        self.assertIn("玩家状态", html)
        self.assertIn("投票表", html)
        self.assertIn("确定性指标", html)
        self.assertIn("规则归因", html)
        self.assertIn("Leaderboard", html)
        self.assertIn("[deterministic]", html)
        self.assertIn("[mock]", html)
        self.assertIn("decision_quality_score", html)
        self.assertIn("fixed at 0", html)
        self.assertIn("not real AI Agent gameplay", html)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("https://", html)

    def test_write_demo_html_with_decision_log_shows_d2_boundary(self) -> None:
        output = ROOT / "docs/demo/test-phase2-d2-runtime-demo.html"
        try:
            write_demo_html(
                ROOT / "docs/gold-game/g001-game-log.json",
                output,
                ROOT / "docs/gold-game/g001-decision-log.json",
            )
            html = output.read_text(encoding="utf-8")
            self.assertIn("D2 deterministic Step 1-2", html)
            self.assertIn("D2 visibility check", html)
            self.assertIn("waiting for S5", html)
        finally:
            output.unlink(missing_ok=True)

    def test_write_demo_html_creates_single_file_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "phase2-runtime-demo.html"
            write_demo_html(ROOT / "docs/gold-game/g001-game-log.json", output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertIn("Werewolf-agent Phase 2 Runtime Demo", html)
            self.assertIn("g001", html)
            self.assertIn("s3_g001_tp001", html)

    def test_render_html_with_semantic_labels_shows_s5_boundary(self) -> None:
        context = build_demo_context(self.game, self.s5_score_log, self.s5_metrics, self.s5_attribution)
        html = render_html(context)

        self.assertIn("S5 saved semantic labels", html)
        self.assertIn("decision_quality_total", html)
        self.assertIn("not live AI labeling", html)
        self.assertIn("[semantic-labels]", html)
        self.assertNotIn("https://", html)

    def test_write_demo_html_accepts_semantic_labels(self) -> None:
        output = ROOT / "docs/demo/test-phase2-s5-runtime-demo.html"
        try:
            write_demo_html(
                ROOT / "docs/gold-game/g001-game-log.json",
                output,
                ROOT / "docs/gold-game/g001-decision-log.json",
                ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
            )
            html = output.read_text(encoding="utf-8")
            self.assertIn("S5 saved semantic labels", html)
            self.assertIn("decision_quality_total", html)
        finally:
            output.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
