# tests/test_rng_draw_order.py
"""Draw-count regression guard (self-contained, oracle retired).

The golden draw-counts below were captured from the ②a-swapped live engine, which
was proven byte-equal to the dceac69 oracle by test_emergent_parity_diff before that
oracle was deleted. These values are therefore oracle-verified. Regenerate ONLY on an
intentional, reviewed behavior change that affects RNG consumption order."""
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
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents
from tests.parity_scripts import DEFAULT_MATRIX, HUNTER_MATRIX, SEEDS  # shared, survives oracle deletion

# Golden draw-counts captured from the ②a live engine (== oracle-verified).
# Keys: (scenario_name, seed). Values: total RNG draws consumed during that run.
GOLDEN_DRAWS = {
    ('bad_vote', 0): 1,
    ('bad_vote', 1): 1,
    ('bad_vote', 2): 1,
    ('bad_vote', 7): 2,
    ('bad_vote', 13): 6,
    ('bad_vote', 42): 1,
    ('bad_vote', 99): 1,
    ('hunter_night_kill', 0): 0,
    ('hunter_night_kill', 1): 0,
    ('hunter_night_kill', 2): 0,
    ('hunter_night_kill', 7): 0,
    ('hunter_night_kill', 13): 0,
    ('hunter_night_kill', 42): 0,
    ('hunter_night_kill', 99): 0,
    ('hunter_voteout', 0): 0,
    ('hunter_voteout', 1): 0,
    ('hunter_voteout', 2): 0,
    ('hunter_voteout', 7): 0,
    ('hunter_voteout', 13): 0,
    ('hunter_voteout', 42): 0,
    ('hunter_voteout', 99): 0,
    ('seer_checks_self', 0): 1,
    ('seer_checks_self', 1): 1,
    ('seer_checks_self', 2): 1,
    ('seer_checks_self', 7): 1,
    ('seer_checks_self', 13): 1,
    ('seer_checks_self', 42): 1,
    ('seer_checks_self', 99): 1,
    ('self_vote', 0): 1,
    ('self_vote', 1): 1,
    ('self_vote', 2): 1,
    ('self_vote', 7): 2,
    ('self_vote', 13): 6,
    ('self_vote', 42): 1,
    ('self_vote', 99): 1,
    ('villager_win', 0): 0,
    ('villager_win', 1): 0,
    ('villager_win', 2): 0,
    ('villager_win', 7): 0,
    ('villager_win', 13): 0,
    ('villager_win', 42): 0,
    ('villager_win', 99): 0,
    ('vote_tie', 0): 8,
    ('vote_tie', 1): 1,
    ('vote_tie', 2): 1,
    ('vote_tie', 7): 7,
    ('vote_tie', 13): 8,
    ('vote_tie', 42): 1,
    ('vote_tie', 99): 7,
    ('werewolf_win', 0): 0,
    ('werewolf_win', 1): 0,
    ('werewolf_win', 2): 0,
    ('werewolf_win', 7): 0,
    ('werewolf_win', 13): 0,
    ('werewolf_win', 42): 0,
    ('werewolf_win', 99): 0,
    ('wolf_both_invalid', 0): 1,
    ('wolf_both_invalid', 1): 5,
    ('wolf_both_invalid', 2): 4,
    ('wolf_both_invalid', 7): 1,
    ('wolf_both_invalid', 13): 1,
    ('wolf_both_invalid', 42): 4,
    ('wolf_both_invalid', 99): 1,
    ('wolf_kills_teammate', 0): 0,
    ('wolf_kills_teammate', 1): 0,
    ('wolf_kills_teammate', 2): 0,
    ('wolf_kills_teammate', 7): 0,
    ('wolf_kills_teammate', 13): 0,
    ('wolf_kills_teammate', 42): 0,
    ('wolf_kills_teammate', 99): 0,
    ('wolf_split_tie', 0): 1,
    ('wolf_split_tie', 1): 1,
    ('wolf_split_tie', 2): 1,
    ('wolf_split_tie', 7): 1,
    ('wolf_split_tie', 13): 1,
    ('wolf_split_tie', 42): 1,
    ('wolf_split_tie', 99): 1,
}


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
                    self.assertEqual(_draws(LiveEngine, build_emergent_config, sb(), seed),
                                     GOLDEN_DRAWS[(name, seed)],
                                     f"draw count differs from golden: {name} seed={seed}")

    def test_same_total_draws_hunter(self):
        for name, sb in HUNTER_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self.assertEqual(_draws(LiveEngine, build_emergent_hunter_config, sb(), seed),
                                     GOLDEN_DRAWS[(name, seed)],
                                     f"draw count differs from golden: {name} seed={seed}")


if __name__ == "__main__":
    unittest.main()
