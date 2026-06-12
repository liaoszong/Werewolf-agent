"""End-to-end acceptance test: fake deterministic games must pass the invariant checker.

Criterion 1 (offline checker) + Criterion 2 (persisted artifacts): for each
available fake script, run the fake runner to a temp dir and assert zero
error-severity violations. No API keys, no network.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.invariants import check_run
from werewolf_eval.run_emergent_fake_runtime import run_emergent_fake_runtime


class TestEndToEndOffline(unittest.TestCase):
    def _run_and_check(self, script: str) -> None:
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d) / "run"
            run_emergent_fake_runtime(game_id=f"e2e_{script}", out_dir=out_dir, script=script)
            violations = [v for v in check_run(out_dir) if v.severity == "error"]
            self.assertEqual(
                violations, [],
                f"[{script}] clean fake game tripped invariants: {violations}",
            )

    def test_villager_win_passes_checker(self) -> None:
        self._run_and_check("villager_win")

    def test_werewolf_win_passes_checker(self) -> None:
        self._run_and_check("werewolf_win")


class TestZeroArtifactGap(unittest.TestCase):
    """C3-7: e2e 对 artifact_gap 零容忍 — 任何严重级别(含 artifact_gap)的违例都不得出现。"""

    _scripts = ("villager_win", "werewolf_win")

    def _run_and_check_all(self, script: str) -> None:
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d) / "run"
            run_emergent_fake_runtime(game_id=f"c3_7_{script}", out_dir=out_dir, script=script)
            violations = check_run(out_dir)
            self.assertEqual(
                violations, [],
                f"[C3-7][{script}] zero-tolerance violated: {violations}",
            )

    def test_villager_win_zero_gap(self) -> None:
        self._run_and_check_all("villager_win")

    def test_werewolf_win_zero_gap(self) -> None:
        self._run_and_check_all("werewolf_win")


if __name__ == "__main__":
    unittest.main()
