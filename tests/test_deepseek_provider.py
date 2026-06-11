from __future__ import annotations

import json
import unittest
from typing import Any

from werewolf_eval.deepseek_provider import DeepSeekProvider, DeepSeekProviderConfig
from werewolf_eval.provider_contract import ProviderRequest


def fake_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "content": '{"action":"seer_check","target":"p1","reason_summary":"check p1","decision_type":"inference_based","confidence":1.0}',
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


_CAPTURE: dict[str, Any] = {}


def capturing_fake_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    _CAPTURE.clear()
    _CAPTURE["url"] = url
    _CAPTURE["headers"] = dict(headers)
    _CAPTURE["payload"] = dict(payload)
    return fake_transport(url, headers, payload, timeout_seconds)


class DeepSeekProviderTests(unittest.TestCase):
    def _make_request(self, **overrides: Any) -> ProviderRequest:
        kwargs = dict(
            request_id="g1e_r01_p3",
            game_id="g1e",
            actor="p3",
            phase="night",
            round=1,
            observation={"role": "seer", "alive": ["p1", "p2", "p3"]},
            allowed_actions=["seer_check"],
            allowed_targets=["p1", "p2", "p3"],
        )
        kwargs.update(overrides)
        return ProviderRequest(**kwargs)

    def test_missing_api_key_refuses_before_transport_call(self) -> None:
        config = DeepSeekProviderConfig(api_key="")
        provider = DeepSeekProvider(config, transport=fake_transport)
        with self.assertRaises(RuntimeError):
            provider.respond(self._make_request())

    def test_builds_openai_compatible_json_request(self) -> None:
        config = DeepSeekProviderConfig(
            api_key="sk-test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
        )
        provider = DeepSeekProvider(config, transport=capturing_fake_transport)
        provider.respond(self._make_request())
        self.assertEqual(
            _CAPTURE["payload"]["model"], "deepseek-v4-flash"
        )
        self.assertEqual(
            _CAPTURE["payload"]["response_format"], {"type": "json_object"}
        )
        self.assertEqual(_CAPTURE["payload"]["stream"], False)
        self.assertEqual(
            _CAPTURE["payload"]["thinking"], {"type": "disabled"}
        )
        self.assertIn("Authorization", _CAPTURE["headers"])
        self.assertIn("Bearer ", _CAPTURE["headers"]["Authorization"])

    def test_success_response_becomes_provider_response(self) -> None:
        config = DeepSeekProviderConfig(api_key="sk-test-key")
        provider = DeepSeekProvider(config, transport=fake_transport)
        response = provider.respond(self._make_request())
        self.assertEqual(response.provider_name, "deepseek")
        self.assertEqual(response.source_label, "[DeepSeek API output]")
        expected_content = '{"action":"seer_check","target":"p1","reason_summary":"check p1","decision_type":"inference_based","confidence":1.0}'
        self.assertEqual(response.raw_content, expected_content)
        self.assertEqual(response.token_usage["total_tokens"], 30)
        self.assertEqual(response.token_usage["prompt_tokens"], 10)
        self.assertEqual(response.token_usage["completion_tokens"], 20)

    def test_empty_content_is_provider_error(self) -> None:
        def empty_transport(
            url: str,
            headers: dict[str, str],
            payload: dict[str, Any],
            timeout_seconds: int,
        ) -> dict[str, Any]:
            return {
                "choices": [{"message": {"content": ""}}],
                "usage": {},
            }

        config = DeepSeekProviderConfig(api_key="sk-test-key")
        provider = DeepSeekProvider(config, transport=empty_transport)
        with self.assertRaises(RuntimeError) as ctx:
            provider.respond(self._make_request())
        self.assertNotIn("sk-test-key", str(ctx.exception))

    def test_http_error_does_not_expose_api_key(self) -> None:
        # Worst case: the transport raises an exception whose OWN message carries the
        # Bearer key (as if it had formatted the headers). The provider must neither
        # surface it in the wrapped message NOR keep it reachable via the exception
        # chain (BYO-key invariant: keys never reach crash logs).
        def error_transport(
            url: str,
            headers: dict[str, str],
            payload: dict[str, Any],
            timeout_seconds: int,
        ) -> dict[str, Any]:
            raise RuntimeError(f"HTTP 500 with header {headers['Authorization']}")

        config = DeepSeekProviderConfig(api_key="sk-test-secret-key")
        provider = DeepSeekProvider(config, transport=error_transport)
        with self.assertRaises(RuntimeError) as ctx:
            provider.respond(self._make_request())
        self.assertNotIn("sk-test-secret-key", str(ctx.exception))
        self.assertNotIn("sk-test", str(ctx.exception))
        # the chain must be broken so traversal/traceback-with-locals can't reach the key
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)

    def test_request_budget_is_enforced(self) -> None:
        config = DeepSeekProviderConfig(
            api_key="sk-test-key", max_requests=2
        )
        provider = DeepSeekProvider(config, transport=fake_transport)
        provider.respond(self._make_request())
        provider.respond(self._make_request())
        with self.assertRaises(RuntimeError) as ctx:
            provider.respond(self._make_request())
        self.assertIn("request budget exceeded", str(ctx.exception))
        self.assertNotIn("sk-test-key", str(ctx.exception))

    def test_response_trace_contains_no_authorization_value(self) -> None:
        config = DeepSeekProviderConfig(api_key="sk-test-key")
        provider = DeepSeekProvider(config, transport=capturing_fake_transport)
        provider.respond(self._make_request())
        auth_value = _CAPTURE["headers"].get("Authorization", "")
        self.assertNotEqual(auth_value, "")
        self.assertFalse(any(
            auth_value in str(r) for r in provider.responses
        ))
        self.assertFalse(any(
            auth_value in str(r) for r in provider.requests
        ))


class DeepSeekConfigShapeTest(unittest.TestCase):
    """D-3: DeepSeekProviderConfig is the shared ChatProviderConfig shape with
    deepseek defaults — no second 8-field clone to keep in sync."""

    def test_is_chat_provider_config_with_deepseek_defaults(self):
        import dataclasses
        from werewolf_eval.llm_providers import ChatProviderConfig

        cfg = DeepSeekProviderConfig(api_key="sk-test-key")
        self.assertIsInstance(cfg, ChatProviderConfig)
        self.assertEqual(cfg.base_url, "https://api.deepseek.com")
        self.assertEqual(cfg.model, "deepseek-v4-flash")
        self.assertEqual(cfg.timeout_seconds, 30)
        self.assertEqual(cfg.max_tokens, 256)
        self.assertEqual(cfg.max_requests, 11)
        self.assertEqual(cfg.persona_prompt, "")
        self.assertIsNone(cfg.temperature)
        self.assertEqual(
            [f.name for f in dataclasses.fields(cfg)],
            [f.name for f in dataclasses.fields(ChatProviderConfig)],
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cfg.api_key = "x"
