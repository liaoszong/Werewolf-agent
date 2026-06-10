# tests/test_emergent_parity_diff.py
"""OLD-vs-NEW full-ledger differential gate for the ②a resolver-deletion swap.

Runs the FROZEN dceac69 oracle (tests/_oracle/emergent_engine_oracle.py) and the LIVE
engine on the SAME (script, board, seed) and asserts byte-equality on every output
artifact + provider_turns (index-by-index). This is the real differential the
determinism canary (NEW-vs-NEW) and the settler-only parity test cannot provide.

The adversarial scripts + (matrix, seeds) live in tests/parity_scripts.py (a non-test helper)
so test_rng_draw_order.py and test_emergent_ledger_golden.py share them and they SURVIVE this
file's deletion in Task 7.
"""
from __future__ import annotations

import json
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
from tests.parity_scripts import DEFAULT_MATRIX, HUNTER_MATRIX, SEEDS


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _run(engine_cls, config_builder, script, seed):
    eng = engine_cls(config=config_builder(game_id="diff"),
                     agents=build_emergent_fake_agents(script), seed=seed)
    return eng.run()


class ParityDiffTests(unittest.TestCase):
    def _assert_identical(self, name, config_builder, script_builder, seed):
        old = _run(OracleEngine, config_builder, script_builder(), seed)
        new = _run(LiveEngine, config_builder, script_builder(), seed)
        ctx = f"{name} seed={seed}"
        self.assertEqual(old.status, new.status, ctx)
        self.assertEqual(old.end_condition, new.end_condition, ctx)
        for attr in ("game_log", "decision_log", "consensus_log", "failure_audit"):
            self.assertEqual(_j(getattr(old, attr)), _j(getattr(new, attr)), f"{attr} differs: {ctx}")
        # provider_turns: index-by-index (catches append-order drift)
        self.assertEqual(len(old.provider_turns), len(new.provider_turns), f"provider_turns len: {ctx}")
        for i, (o, n) in enumerate(zip(old.provider_turns, new.provider_turns)):
            self.assertEqual(_j(o), _j(n), f"provider_turns[{i}] differs: {ctx}")

    def test_default_board_matrix(self):
        for name, sb in DEFAULT_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self._assert_identical(name, build_emergent_config, sb, seed)

    def test_hunter_board_matrix(self):
        for name, sb in HUNTER_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self._assert_identical(name, build_emergent_hunter_config, sb, seed)


if __name__ == "__main__":
    unittest.main()
