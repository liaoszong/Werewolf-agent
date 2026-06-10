from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.deepseek_launcher import build_multi_provider_launcher
from werewolf_eval.deepseek_provider import DeepSeekProvider
from werewolf_eval.llm_providers import AnthropicProvider
from werewolf_eval.provider_contract import MIXED_PROVIDER_SOURCE_LABEL
from werewolf_eval.run_emergent_deepseek_game import _provider_identity, _seat_manifest_agents
from werewolf_eval.seat_agents import ProviderCredential, build_seat_agents


def _multi_shape_transport(url, headers, payload, timeout):
    body = '{"action":"player_vote","target":"p1","reason_summary":"r","decision_type":"inference_based","confidence":1.0}'
    if url.endswith("/v1/messages"):
        return {"content": [{"type": "text", "text": body}], "usage": {"input_tokens": 1, "output_tokens": 1}}
    return {"choices": [{"message": {"content": body}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


def _seat(pid, provider, model, prompt=""):
    return {"player_id": pid, "provider": provider, "model": model, "role": "villager",
            "team": "villager", "strategy": "default", "prompt": prompt,
            "temperature": None, "max_tokens": None}


def _mixed_seats():
    return [
        _seat("p1", "deepseek", "deepseek-v4-flash", prompt="激进"),
        _seat("p2", "anthropic", "claude-haiku-4-5", prompt="保守"),
        _seat("p3", "deepseek", "deepseek-v4-pro"),
        _seat("p4", "anthropic", "claude-haiku-4-5"),
        _seat("p5", "deepseek", "deepseek-v4-flash"),
        _seat("p6", "deepseek", "deepseek-v4-flash"),
    ]


def _creds():
    return {"deepseek": ProviderCredential(key="sk-ds"), "anthropic": ProviderCredential(key="sk-ant")}


class RunnerPerSeatHelpersTests(unittest.TestCase):
    """Verify the runner's per-seat manifest/trace logic with REAL providers
    (no full game needed)."""

    def test_identity_is_mixed_for_heterogeneous_seats(self):
        agents = build_seat_agents(_mixed_seats(), _creds(), max_requests=64, transport=_multi_shape_transport)
        name, label = _provider_identity(agents)
        self.assertEqual(name, "mixed")
        self.assertEqual(label, MIXED_PROVIDER_SOURCE_LABEL)

    def test_identity_is_uniform_for_single_provider(self):
        seats = [_seat(f"p{i}", "deepseek", "deepseek-v4-flash") for i in range(1, 7)]
        agents = build_seat_agents(seats, _creds(), max_requests=64, transport=_multi_shape_transport)
        name, label = _provider_identity(agents)
        self.assertEqual(name, "deepseek")
        self.assertEqual(label, "[DeepSeek API output]")

    def test_seat_manifest_has_per_seat_provider_model_persona(self):
        agents = build_seat_agents(_mixed_seats(), _creds(), max_requests=64, transport=_multi_shape_transport)
        rows = {r["player_id"]: r for r in _seat_manifest_agents(agents, fallback_model="")}
        self.assertEqual(rows["p1"]["provider"], "deepseek")
        self.assertEqual(rows["p1"]["model"], "deepseek-v4-flash")
        self.assertEqual(rows["p1"]["prompt"], "激进")
        self.assertEqual(rows["p2"]["provider"], "anthropic")
        self.assertEqual(rows["p2"]["model"], "claude-haiku-4-5")
        self.assertEqual(rows["p2"]["prompt"], "保守")
        self.assertEqual(rows["p3"]["model"], "deepseek-v4-pro")


class MultiProviderLauncherTests(unittest.TestCase):
    def test_launcher_builds_per_seat_agents_and_returns_runner_code(self):
        captured: dict[str, Any] = {}

        def fake_runner(*, game_id, out_dir, provider_factory, model, max_requests_per_game,
                        max_day_rounds, seat_roles=None):
            captured["p1_provider"] = provider_factory("p1").provider
            captured["p2_provider"] = provider_factory("p2").provider
            captured["seat_roles"] = seat_roles
            return 0

        launcher = build_multi_provider_launcher(
            resolved_seats=_mixed_seats(), credentials=_creds(),
            transport=_multi_shape_transport, runner=fake_runner,
        )
        with tempfile.TemporaryDirectory() as tmp:
            rc = launcher("run1", Path(tmp))
        self.assertEqual(rc, 0)
        self.assertIsInstance(captured["p1_provider"], DeepSeekProvider)
        self.assertIsInstance(captured["p2_provider"], AnthropicProvider)

    def test_launcher_raises_on_missing_credential(self):
        launcher = build_multi_provider_launcher(
            resolved_seats=_mixed_seats(),
            credentials={"deepseek": ProviderCredential(key="sk-ds")},  # no anthropic
            transport=_multi_shape_transport, runner=lambda **k: 0,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                launcher("run1", Path(tmp))

    def test_launcher_maps_budget_exhausted_to_exit_3(self):
        def fake_runner(*, out_dir, **kwargs):
            (Path(out_dir) / "failure-audit.json").write_text(
                json.dumps({"failures": [{"kind": "budget_exhausted", "reason": "budget exhausted: 5/5"}]}),
                encoding="utf-8",
            )
            return 2

        launcher = build_multi_provider_launcher(
            resolved_seats=_mixed_seats(), credentials=_creds(),
            transport=_multi_shape_transport, runner=fake_runner,
        )
        with tempfile.TemporaryDirectory() as tmp:
            rc = launcher("run1", Path(tmp))
        self.assertEqual(rc, 3)

    def test_launcher_maps_generic_failure_to_exit_2(self):
        def fake_runner(*, out_dir, **kwargs):
            return 2

        launcher = build_multi_provider_launcher(
            resolved_seats=_mixed_seats(), credentials=_creds(),
            transport=_multi_shape_transport, runner=fake_runner,
        )
        with tempfile.TemporaryDirectory() as tmp:
            rc = launcher("run1", Path(tmp))
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
