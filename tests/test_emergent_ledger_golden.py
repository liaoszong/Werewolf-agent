# tests/test_emergent_ledger_golden.py
"""Permanent full-ledger regression guard. The golden was captured from the ②a-swapped
engine, PROVEN byte-equal to the dceac69 oracle by test_emergent_parity_diff before that
oracle was deleted. Regenerate ONLY on an intentional, reviewed behavior change."""
from __future__ import annotations
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "emergent_ledger_golden.json"

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config, build_emergent_hunter_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents, build_villager_win_script, build_werewolf_win_script,
    build_hunter_night_kill_script,
)
from tests.parity_scripts import _wolf_split_tie  # shared module survives the Task-7 oracle deletion

CASES = [
    ("villager_win", build_emergent_config, build_villager_win_script, 0),
    ("werewolf_win", build_emergent_config, build_werewolf_win_script, 7),
    ("wolf_split_tie", build_emergent_config, _wolf_split_tie, 42),
    ("hunter_night_kill", build_emergent_hunter_config, build_hunter_night_kill_script, 0),
]

def _ledger(o):
    return {k: getattr(o, k) for k in ("game_log", "decision_log", "consensus_log", "failure_audit", "provider_turns")}

def _run(cfg, sb, seed):
    return EmergentGameEngine(config=cfg(game_id="gold"), agents=build_emergent_fake_agents(sb()), seed=seed).run()

class GoldenLedgerTests(unittest.TestCase):
    def test_matches_golden(self):
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        for name, cfg, sb, seed in CASES:
            with self.subTest(name=name):
                got = json.dumps(_ledger(_run(cfg, sb, seed)), ensure_ascii=False, sort_keys=True)
                self.assertEqual(got, golden[name], f"{name} drifted from golden")

# one-off generator (run manually, never in CI). Use a module alias, NOT `import *` —
# `_ledger`/`_run` are underscore-private and `import *` would skip them (NameError):
#   PYTHONPATH=src python -c "import json, tests.test_emergent_ledger_golden as g; \
#     d={n: json.dumps(g._ledger(g._run(c,s,seed)),ensure_ascii=False,sort_keys=True) for n,c,s,seed in g.CASES}; \
#     g.GOLDEN.parent.mkdir(exist_ok=True); g.GOLDEN.write_text(json.dumps(d,ensure_ascii=False,indent=1),encoding='utf-8')"
