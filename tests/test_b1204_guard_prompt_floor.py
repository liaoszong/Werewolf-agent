"""B12-04: a guard board on a non-scaffold renderer (prompt_v1/v2) must fail loud
before any side effects — v1/v2 carry no guard rules card, so the live game would
silently degrade into mass invalid-action fallback."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game

GUARD_BOARD = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
               "p4": "witch", "p5": "guard", "p6": "villager"}


def _factory(_pid):
    raise AssertionError("provider factory must not be called: fail-loud precedes side effects")


class GuardPromptFloorTests(unittest.TestCase):
    def test_guard_board_v1_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_emergent_deepseek_game(
                game_id="b1204_v1", out_dir=ROOT / ".tmp_should_not_exist",
                provider_factory=_factory, model="m", seat_roles=GUARD_BOARD,
                prompt_version="prompt_v1",
            )
        self.assertIn("guard", str(ctx.exception).lower())
        self.assertIn("prompt_v1", str(ctx.exception))

    def test_guard_board_v2_raises(self):
        with self.assertRaises(ValueError):
            run_emergent_deepseek_game(
                game_id="b1204_v2", out_dir=ROOT / ".tmp_should_not_exist",
                provider_factory=_factory, model="m", seat_roles=GUARD_BOARD,
                prompt_version="prompt_v2",
            )

    def test_non_guard_board_v1_does_not_raise_on_floor(self):
        # No guard on the board: the floor must not fire. (It may still fail later
        # on the fake factory, but NOT with the guard-floor message.)
        with tempfile.TemporaryDirectory() as td:
            try:
                run_emergent_deepseek_game(
                    game_id="b1204_ok", out_dir=Path(td),
                    provider_factory=_factory, model="m", seat_roles=None,
                    prompt_version="prompt_v1",
                )
            except ValueError as e:
                self.assertNotIn("rules card", str(e).lower())
            except AssertionError:
                pass  # reached the provider factory => floor correctly did not fire


if __name__ == "__main__":
    unittest.main()
