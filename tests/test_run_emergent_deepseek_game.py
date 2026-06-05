"""Offline structural test of the P2-A-2 live runner: inject script-driven fake
agents through the provider_factory seam (no network) and assert the mandatory
spine + four logs + provider-turns summary + fail-closed behavior."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.consensus_log import parse_consensus_log
from werewolf_eval.decision_log import parse_decision_log
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.game_log import parse_game_log
from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game


class EmergentDeepSeekRunnerTests(unittest.TestCase):
    def _factory(self):
        agents = build_emergent_fake_agents(build_villager_win_script())
        return lambda pid: agents[pid]

    def test_completed_run_writes_logs_and_mandatory_spine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rc = run_emergent_deepseek_game(
                game_id="p2a2_off", out_dir=out, provider_factory=self._factory(),
                model="deepseek-v4-flash", seed=0,
            )
            self.assertEqual(rc, 0)
            # four logs
            for name in ("game-log.json", "decision-log.json", "consensus-log.json", "failure-audit.json"):
                self.assertTrue((out / name).exists(), name)
            # mandatory spine
            self.assertTrue((out / "events.jsonl").exists())
            self.assertTrue((out / "prompt-manifest.json").exists())
            self.assertTrue((out / "snapshots").is_dir() and any((out / "snapshots").glob("*.json")), "snapshots empty")
            self.assertTrue((out / "provider-trace.json").exists())
            self.assertTrue((out / "provider-turns.json").exists())

            # logs validate
            game = parse_game_log(json.loads((out / "game-log.json").read_text(encoding="utf-8")))
            parse_decision_log(json.loads((out / "decision-log.json").read_text(encoding="utf-8")), game)
            parse_consensus_log(json.loads((out / "consensus-log.json").read_text(encoding="utf-8")), game)

            # manifest records the real model
            manifest = json.loads((out / "prompt-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(all(a["model"] == "deepseek-v4-flash" for a in manifest["agents"]))

            # provider-turns summary shape
            summary = json.loads((out / "provider-turns.json").read_text(encoding="utf-8"))
            self.assertIn("live_success_rate", summary)
            self.assertIn("by_provider_result_kind", summary)
            self.assertEqual(summary["live_requested_actions"], len(summary["turns"]))

    def test_fail_closed_writes_no_game_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rc = run_emergent_deepseek_game(
                game_id="p2a2_fc", out_dir=out, provider_factory=self._factory(),
                model="deepseek-v4-flash", seed=0, max_requests_per_game=3,
            )
            self.assertEqual(rc, 2)
            self.assertFalse((out / "game-log.json").exists())
            self.assertTrue((out / "failure-audit.json").exists())
            # spine still present for evidence
            self.assertTrue((out / "prompt-manifest.json").exists())
            self.assertTrue((out / "provider-turns.json").exists())


if __name__ == "__main__":
    unittest.main()
