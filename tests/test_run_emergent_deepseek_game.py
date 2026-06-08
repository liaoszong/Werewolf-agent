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


class ProviderIdentityTests(unittest.TestCase):
    def _agent(self, name, label):
        from werewolf_eval.provider_contract import OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL
        class _P:
            PROVIDER_NAME = name
            SOURCE_LABEL = label
            requests = []
            responses = []
            model = "m"
            persona = ""
        class _A:
            provider = _P()
        return _A()

    def test_same_label_different_vendors_is_mixed(self) -> None:
        from werewolf_eval.run_emergent_deepseek_game import _provider_identity
        from werewolf_eval.provider_contract import (
            OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL, MIXED_PROVIDER_SOURCE_LABEL,
        )
        agents = {
            "p1": self._agent("moonshot", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
            "p2": self._agent("qwen", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
        }
        name, label = _provider_identity(agents)
        self.assertEqual(name, "mixed")
        self.assertEqual(label, MIXED_PROVIDER_SOURCE_LABEL)

    def test_uniform_vendor_keeps_its_label(self) -> None:
        from werewolf_eval.run_emergent_deepseek_game import _provider_identity
        from werewolf_eval.provider_contract import OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL
        agents = {
            "p1": self._agent("moonshot", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
            "p2": self._agent("moonshot", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
        }
        name, label = _provider_identity(agents)
        self.assertEqual(name, "moonshot")
        self.assertEqual(label, OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL)


class SeatManifestHonestyTests(unittest.TestCase):
    def _agent(self, name, model):
        class _P:
            PROVIDER_NAME = name
            SOURCE_LABEL = "[OpenAI-compatible API output]"
            requests = []
            responses = []
            persona = ""
            def __init__(self, m): self._m = m
            @property
            def model(self): return self._m
        class _A:
            def __init__(self, p): self.provider = p
        return _A(_P(model))

    def test_manifest_keeps_each_vendor_id(self) -> None:
        from werewolf_eval.run_emergent_deepseek_game import _seat_manifest_agents, PLAYER_IDS
        agents = {
            PLAYER_IDS[0]: self._agent("moonshot", "kimi-k2.6"),
            PLAYER_IDS[1]: self._agent("qwen", "qwen3-max"),
        }
        rows = _seat_manifest_agents(agents, fallback_model="fallback")
        by_pid = {r["player_id"]: r for r in rows}
        self.assertEqual(by_pid[PLAYER_IDS[0]]["provider"], "moonshot")
        self.assertEqual(by_pid[PLAYER_IDS[0]]["model"], "kimi-k2.6")
        self.assertEqual(by_pid[PLAYER_IDS[1]]["provider"], "qwen")
        self.assertEqual(by_pid[PLAYER_IDS[1]]["model"], "qwen3-max")


if __name__ == "__main__":
    unittest.main()
