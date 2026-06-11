"""SYS-B1 acceptance: a full fake game on the prompt_v2 rendering chain must pass
ALL invariants (I1..I7 incl. the I4b visibility oracle) over its persisted
artifacts. The runtime guard assert_prompt_entitled already runs in-engine; this
locks the artifact-level oracle too."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.invariants.checker import check_run
from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game


class PromptV2InvariantsTests(unittest.TestCase):
    def _fake_factory(self):
        agents = build_emergent_fake_agents(build_villager_win_script())
        return lambda pid: agents[pid]

    def test_v2_fake_game_passes_all_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            run_emergent_deepseek_game(
                game_id="v2_inv_smoke", out_dir=out_dir, provider_factory=self._fake_factory(),
                model="none", seed=11, max_requests_per_game=80, max_day_rounds=3,
                prompt_version="prompt_v2",
            )
            violations = check_run(out_dir)
            self.assertEqual(violations, [], f"invariant violations on prompt_v2 artifacts: {violations}")

    def test_v1_fake_game_still_passes_all_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            run_emergent_deepseek_game(
                game_id="v1_inv_smoke", out_dir=out_dir, provider_factory=self._fake_factory(),
                model="none", seed=11, max_requests_per_game=80, max_day_rounds=3,
            )
            violations = check_run(out_dir)
            self.assertEqual(violations, [], f"invariant violations on prompt_v1 artifacts: {violations}")


if __name__ == "__main__":
    unittest.main()
