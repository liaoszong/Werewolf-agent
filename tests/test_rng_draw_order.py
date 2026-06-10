# tests/test_rng_draw_order.py
"""Counting-Random per-round draw-count parity (OLD vs NEW). The differential gate
compares OUTPUT bytes; this asserts the engines consume self._rng in the same NUMBER
of draws — a direct guard on RNG-order drift independent of the resolved targets."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_engine import (
    EmergentGameEngine as LiveEngine,
    build_emergent_config,
    build_emergent_hunter_config,
)
from tests._oracle.emergent_engine_oracle import EmergentGameEngine as OracleEngine
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents
from tests.parity_scripts import DEFAULT_MATRIX, HUNTER_MATRIX, SEEDS  # shared, NOT the (deletable) diff gate


class _CountingRandom(random.Random):
    def __init__(self, seed):
        super().__init__(seed)
        self.draws = 0
    def choice(self, seq):
        self.draws += 1
        return super().choice(seq)
    def randrange(self, *a, **k):
        self.draws += 1
        return super().randrange(*a, **k)


def _draws(engine_cls, config_builder, script, seed):
    eng = engine_cls(config=config_builder(game_id="rng"),
                     agents=build_emergent_fake_agents(script), seed=seed)
    eng._rng = _CountingRandom(seed)   # swap in the counter (same seed)
    eng.run()
    return eng._rng.draws


class DrawCountParityTests(unittest.TestCase):
    def test_same_total_draws(self):
        for name, sb in DEFAULT_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self.assertEqual(_draws(OracleEngine, build_emergent_config, sb(), seed),
                                     _draws(LiveEngine, build_emergent_config, sb(), seed),
                                     f"draw count differs: {name} seed={seed}")

    def test_same_total_draws_hunter(self):
        for name, sb in HUNTER_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self.assertEqual(_draws(OracleEngine, build_emergent_hunter_config, sb(), seed),
                                     _draws(LiveEngine, build_emergent_hunter_config, sb(), seed),
                                     f"draw count differs: {name} seed={seed}")


if __name__ == "__main__":
    unittest.main()
