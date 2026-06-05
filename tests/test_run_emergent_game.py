from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class RunEmergentGameCliTests(unittest.TestCase):
    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "werewolf_eval.run_emergent_game", *args],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
        )

    def test_villager_win_writes_four_logs_that_validate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = self._run_cli(
                "--game-id", "p2a1_cli",
                "--script", "villager_win",
                "--game-log-out", str(out / "game.json"),
                "--decision-log-out", str(out / "decision.json"),
                "--consensus-log-out", str(out / "consensus.json"),
                "--failure-audit-out", str(out / "failure.json"),
            )
            self.assertEqual(result.returncode, 0, f"stderr={result.stderr}")
            self.assertIn("status=completed", result.stdout)
            self.assertIn("winner=villager", result.stdout)
            for name in ("game.json", "decision.json", "consensus.json", "failure.json"):
                self.assertTrue((out / name).exists(), name)

            from werewolf_eval.consensus_log import parse_consensus_log
            from werewolf_eval.decision_log import parse_decision_log
            from werewolf_eval.game_log import parse_game_log

            game = parse_game_log(json.loads((out / "game.json").read_text(encoding="utf-8")))
            parse_decision_log(json.loads((out / "decision.json").read_text(encoding="utf-8")), game)
            parse_consensus_log(json.loads((out / "consensus.json").read_text(encoding="utf-8")), game)
            self.assertEqual(game.game_id, "p2a1_cli")
            self.assertEqual(game.result.winner, "villager")

    def test_werewolf_win_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = self._run_cli(
                "--script", "werewolf_win",
                "--game-log-out", str(out / "game.json"),
            )
            self.assertEqual(result.returncode, 0, f"stderr={result.stderr}")
            self.assertIn("winner=werewolf", result.stdout)

    def test_budget_failclosed_exits_nonzero_and_writes_only_failure_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = self._run_cli(
                "--script", "villager_win",
                "--max-requests", "3",
                "--game-log-out", str(out / "game.json"),
                "--decision-log-out", str(out / "decision.json"),
                "--failure-audit-out", str(out / "failure.json"),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("status=failed", result.stdout)
            self.assertIn("end_condition=budget_exhausted", result.stdout)
            self.assertIn("game_log=not_written", result.stdout)
            self.assertFalse((out / "game.json").exists())
            self.assertFalse((out / "decision.json").exists())
            self.assertTrue((out / "failure.json").exists())

    def test_no_secrets_or_urls_in_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self._run_cli(
                "--game-log-out", str(out / "game.json"),
                "--decision-log-out", str(out / "decision.json"),
                "--consensus-log-out", str(out / "consensus.json"),
            )
            for name in ("game.json", "decision.json", "consensus.json"):
                text = (out / name).read_text(encoding="utf-8").lower()
                for forbidden in ["api_key", "authorization", "http://", "https://", "bearer", "sk-"]:
                    self.assertNotIn(forbidden, text, f"{forbidden} in {name}")


if __name__ == "__main__":
    unittest.main()
