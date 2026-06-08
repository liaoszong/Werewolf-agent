from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.deepseek_provider import DeepSeekProvider
from werewolf_eval.llm_providers import AnthropicProvider
from werewolf_eval.provider_contract import ProviderRequest
from werewolf_eval.seat_agents import ProviderCredential, build_seat_agents


_CALLS: list[dict[str, Any]] = []


def _multi_shape_transport(url, headers, payload, timeout):
    """One transport that serves both wire shapes (DeepSeek/OpenAI vs Anthropic),
    branching on the endpoint, and records each call for assertions."""
    _CALLS.append({"url": url, "headers": dict(headers), "payload": dict(payload)})
    body = '{"action":"player_vote","target":"p1","reason_summary":"r","decision_type":"inference_based","confidence":1.0}'
    if url.endswith("/v1/messages"):  # Anthropic
        return {"content": [{"type": "text", "text": body}], "usage": {"input_tokens": 1, "output_tokens": 1}}
    return {  # OpenAI-compatible
        "choices": [{"message": {"content": body}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _seat(pid, provider, model, prompt="", temperature=None, max_tokens=None):
    return {
        "player_id": pid, "provider": provider, "model": model,
        "role": "villager", "team": "villager", "strategy": "default",
        "prompt": prompt, "temperature": temperature, "max_tokens": max_tokens,
    }


def _request(pid):
    return ProviderRequest(
        request_id=f"g_{pid}", game_id="g", actor=pid, phase="day", round=1,
        observation={"role": "villager"}, allowed_actions=["player_vote"],
        allowed_targets=["p1", "p2"], observation_text="obs",
    )


class BuildSeatAgentsTests(unittest.TestCase):
    def setUp(self):
        _CALLS.clear()

    def _creds(self):
        return {
            "deepseek": ProviderCredential(key="sk-ds"),
            "anthropic": ProviderCredential(key="sk-ant"),
        }

    def test_each_seat_gets_its_own_provider_class_and_model(self):
        seats = [
            _seat("p1", "deepseek", "deepseek-v4-flash"),
            _seat("p2", "anthropic", "claude-haiku-4-5"),
        ]
        agents = build_seat_agents(seats, self._creds(), max_requests=64, transport=_multi_shape_transport)
        self.assertIsInstance(agents["p1"].provider, DeepSeekProvider)
        self.assertIsInstance(agents["p2"].provider, AnthropicProvider)
        self.assertEqual(agents["p1"].provider.model, "deepseek-v4-flash")
        self.assertEqual(agents["p2"].provider.model, "claude-haiku-4-5")

    def test_per_seat_persona_reaches_each_payload(self):
        seats = [
            _seat("p1", "deepseek", "deepseek-v4-flash", prompt="你非常激进。"),
            _seat("p2", "anthropic", "claude-haiku-4-5", prompt="你非常保守。"),
        ]
        agents = build_seat_agents(seats, self._creds(), max_requests=64, transport=_multi_shape_transport)
        agents["p1"].provider.respond(_request("p1"))
        agents["p2"].provider.respond(_request("p2"))
        ds_call = next(c for c in _CALLS if c["url"].endswith("/chat/completions"))
        an_call = next(c for c in _CALLS if c["url"].endswith("/v1/messages"))
        self.assertTrue(ds_call["payload"]["messages"][0]["content"].startswith("你非常激进。"))
        self.assertTrue(an_call["payload"]["system"].startswith("你非常保守。"))
        # contract preserved in both
        self.assertIn("reason_summary", ds_call["payload"]["messages"][0]["content"])
        self.assertIn("reason_summary", an_call["payload"]["system"])

    def test_per_seat_temperature_and_max_tokens(self):
        seats = [
            _seat("p1", "deepseek", "deepseek-v4-flash", temperature=0.9, max_tokens=300),
            _seat("p2", "anthropic", "claude-haiku-4-5", temperature=0.0),  # None max_tokens -> default
        ]
        agents = build_seat_agents(seats, self._creds(), max_requests=64, default_max_tokens=256, transport=_multi_shape_transport)
        agents["p1"].provider.respond(_request("p1"))
        agents["p2"].provider.respond(_request("p2"))
        ds_call = next(c for c in _CALLS if c["url"].endswith("/chat/completions"))
        an_call = next(c for c in _CALLS if c["url"].endswith("/v1/messages"))
        self.assertEqual(ds_call["payload"]["temperature"], 0.9)
        self.assertEqual(ds_call["payload"]["max_tokens"], 300)
        self.assertEqual(an_call["payload"]["temperature"], 0.0)  # 0.0 must survive
        self.assertEqual(an_call["payload"]["max_tokens"], 256)   # default applied

    def test_distinct_keys_per_provider(self):
        seats = [
            _seat("p1", "deepseek", "deepseek-v4-flash"),
            _seat("p2", "anthropic", "claude-haiku-4-5"),
        ]
        agents = build_seat_agents(seats, self._creds(), max_requests=64, transport=_multi_shape_transport)
        agents["p1"].provider.respond(_request("p1"))
        agents["p2"].provider.respond(_request("p2"))
        ds_call = next(c for c in _CALLS if c["url"].endswith("/chat/completions"))
        an_call = next(c for c in _CALLS if c["url"].endswith("/v1/messages"))
        self.assertEqual(ds_call["headers"]["Authorization"], "Bearer sk-ds")
        self.assertEqual(an_call["headers"]["x-api-key"], "sk-ant")

    def test_persona_property_exposed(self):
        seats = [_seat("p1", "deepseek", "deepseek-v4-flash", prompt="人格X")]
        agents = build_seat_agents(seats, {"deepseek": ProviderCredential(key="sk-ds")}, max_requests=64, transport=_multi_shape_transport)
        self.assertEqual(agents["p1"].provider.persona, "人格X")

    def test_missing_credential_raises(self):
        seats = [_seat("p1", "anthropic", "claude-haiku-4-5")]
        with self.assertRaises(ValueError):
            build_seat_agents(seats, {"deepseek": ProviderCredential(key="sk-ds")}, max_requests=64, transport=_multi_shape_transport)

    def test_two_deepseek_seats_get_independent_providers(self):
        # Same provider, different per-seat persona -> must be DIFFERENT instances
        # (so persona/temperature don't bleed across seats).
        seats = [
            _seat("p1", "deepseek", "deepseek-v4-flash", prompt="A"),
            _seat("p2", "deepseek", "deepseek-v4-flash", prompt="B"),
        ]
        agents = build_seat_agents(seats, {"deepseek": ProviderCredential(key="sk-ds")}, max_requests=64, transport=_multi_shape_transport)
        self.assertIsNot(agents["p1"].provider, agents["p2"].provider)
        self.assertEqual(agents["p1"].provider.persona, "A")
        self.assertEqual(agents["p2"].provider.persona, "B")


if __name__ == "__main__":
    unittest.main()
