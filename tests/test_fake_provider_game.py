from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class FakeProviderGameCliTests(unittest.TestCase):
    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "werewolf_eval.run_fake_provider_game", *args],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
        )

    def test_valid_game_writes_all_three_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = self._run_cli(
                "--game-id", "g1d_fake_provider",
                "--game-log-out", str(out / "game.json"),
                "--decision-log-out", str(out / "decision.json"),
                "--provider-trace-out", str(out / "provider-trace.json"),
            )
            self.assertEqual(result.returncode, 0, f"stderr={result.stderr}")
            self.assertIn("fake_provider_game_id=g1d_fake_provider", result.stdout)
            self.assertIn("source_label=[deterministic fake provider output]", result.stdout)
            self.assertIn("events=18", result.stdout)
            self.assertIn("decisions=11", result.stdout)
            self.assertIn("provider_requests=11", result.stdout)
            self.assertIn("provider_responses=11", result.stdout)
            self.assertIn("provider_failures=0", result.stdout)
            self.assertIn("game_log=written", result.stdout)
            self.assertIn("decision_log=written", result.stdout)
            self.assertIn("provider_trace=written", result.stdout)
            self.assertTrue((out / "game.json").exists())
            self.assertTrue((out / "decision.json").exists())
            self.assertTrue((out / "provider-trace.json").exists())

    def test_valid_artifacts_validate_through_parsers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = self._run_cli(
                "--game-id", "g1d_fake_provider",
                "--game-log-out", str(out / "game.json"),
                "--decision-log-out", str(out / "decision.json"),
                "--provider-trace-out", str(out / "provider-trace.json"),
            )
            self.assertEqual(result.returncode, 0)

            from werewolf_eval.decision_log import parse_decision_log
            from werewolf_eval.game_log import parse_game_log

            game = parse_game_log(json.loads((out / "game.json").read_text(encoding="utf-8")))
            decision_log = parse_decision_log(
                json.loads((out / "decision.json").read_text(encoding="utf-8")), game,
            )
            self.assertEqual(game.game_id, "g1d_fake_provider")
            self.assertEqual(decision_log.source_label, "[deterministic fake provider output]")

    def test_provider_trace_contains_no_secrets_or_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = self._run_cli(
                "--game-id", "g1d_fake_provider",
                "--game-log-out", str(out / "game.json"),
                "--decision-log-out", str(out / "decision.json"),
                "--provider-trace-out", str(out / "provider-trace.json"),
            )
            self.assertEqual(result.returncode, 0)
            trace_text = (out / "provider-trace.json").read_text(encoding="utf-8").lower()
            for forbidden in ["api_key", "authorization", "http://", "https://", "bearer"]:
                self.assertNotIn(forbidden, trace_text, f"found forbidden '{forbidden}' in provider trace")

    def test_parse_failure_mode_exits_nonzero_and_writes_failure_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = self._run_cli(
                "--game-id", "g1d_fake_provider_parse_failure",
                "--game-log-out", str(out / "game.json"),
                "--decision-log-out", str(out / "decision.json"),
                "--provider-trace-out", str(out / "provider-trace.json"),
                "--failure-audit-out", str(out / "failure-audit.json"),
                "--failure-mode", "parse_failure",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fake_provider_game_id=g1d_fake_provider_parse_failure", result.stdout)
            self.assertIn("provider_failures=1", result.stdout)
            self.assertIn("failure_kind=parse_failure", result.stdout)
            self.assertIn("game_log=not_written", result.stdout)
            self.assertIn("decision_log=not_written", result.stdout)
            self.assertIn("failure_audit=written", result.stdout)
            self.assertTrue((out / "failure-audit.json").exists())
            self.assertTrue((out / "provider-trace.json").exists())
            # Game log and decision log must NOT exist
            self.assertFalse((out / "game.json").exists())
            self.assertFalse((out / "decision.json").exists())


class FakeProviderGameArtifactTests(unittest.TestCase):
    def test_generated_html_includes_fake_provider_label(self) -> None:
        html_path = ROOT / "docs/demo/phase3-g1d-fake-provider-runtime-demo.html"
        if not html_path.exists():
            self.skipTest("demo HTML not yet generated")
        html = html_path.read_text(encoding="utf-8")
        self.assertIn("[deterministic fake provider output]", html)
        for forbidden in [
            "provider-backed",
            "live AI Agent gameplay",
            "human-vs-AI UI",
            "real multi-game Leaderboard",
        ]:
            self.assertNotIn(forbidden, html)

    def test_generated_game_log_validates(self) -> None:
        game_log_path = ROOT / "docs/generated-games/g1d-fake-provider-game-log.json"
        if not game_log_path.exists():
            self.skipTest("game log not yet generated")
        from werewolf_eval.game_log import parse_game_log
        game = parse_game_log(json.loads(game_log_path.read_text(encoding="utf-8")))
        self.assertEqual(game.game_id, "g1d_fake_provider")
        self.assertEqual(len(game.events), 18)

    def test_generated_decision_log_validates(self) -> None:
        game_log_path = ROOT / "docs/generated-games/g1d-fake-provider-game-log.json"
        decision_log_path = ROOT / "docs/generated-games/g1d-fake-provider-decision-log.json"
        if not decision_log_path.exists():
            self.skipTest("decision log not yet generated")
        from werewolf_eval.decision_log import parse_decision_log
        from werewolf_eval.game_log import parse_game_log
        game = parse_game_log(json.loads(game_log_path.read_text(encoding="utf-8")))
        decision_log = parse_decision_log(
            json.loads(decision_log_path.read_text(encoding="utf-8")), game,
        )
        self.assertEqual(decision_log.source_label, "[deterministic fake provider output]")
        self.assertEqual(len(decision_log.decisions), 11)


if __name__ == "__main__":
    unittest.main()
