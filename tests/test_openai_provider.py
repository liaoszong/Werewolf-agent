from __future__ import annotations

import unittest
from typing import Any

from werewolf_eval.llm_providers import ChatProviderConfig, OpenAIProvider
from werewolf_eval.provider_contract import ProviderRequest


def _ok_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "content": '{"action":"seer_check","target":"p1","reason_summary":"r","decision_type":"inference_based","confidence":1.0}',
                }
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
    }


_CAPTURE: dict[str, Any] = {}


def _capturing_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    _CAPTURE.clear()
    _CAPTURE["url"] = url
    _CAPTURE["headers"] = dict(headers)
    _CAPTURE["payload"] = dict(payload)
    return _ok_transport(url, headers, payload, timeout_seconds)


class OpenAIProviderTests(unittest.TestCase):
    def _request(self, **overrides: Any) -> ProviderRequest:
        kwargs = dict(
            request_id="g_r01_p3",
            game_id="g",
            actor="p3",
            phase="night",
            round=1,
            observation={"role": "seer"},
            allowed_actions=["seer_check"],
            allowed_targets=["p1", "p2", "p3"],
        )
        kwargs.update(overrides)
        return ProviderRequest(**kwargs)

    def _config(self, **overrides: Any) -> ChatProviderConfig:
        kwargs = dict(
            api_key="sk-openai-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        kwargs.update(overrides)
        return ChatProviderConfig(**kwargs)

    def test_posts_to_chat_completions_with_bearer_auth(self) -> None:
        provider = OpenAIProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request())
        self.assertEqual(_CAPTURE["url"], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(
            _CAPTURE["headers"]["Authorization"], "Bearer sk-openai-key"
        )

    def test_action_payload_has_json_response_format_but_no_thinking(self) -> None:
        # OpenAI supports response_format=json_object but has NO DeepSeek `thinking` key.
        provider = OpenAIProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request())
        self.assertEqual(_CAPTURE["payload"]["model"], "gpt-4o-mini")
        self.assertEqual(
            _CAPTURE["payload"]["response_format"], {"type": "json_object"}
        )
        self.assertNotIn("thinking", _CAPTURE["payload"])

    def test_speech_payload_has_no_response_format(self) -> None:
        provider = OpenAIProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request(response_kind="speech", allowed_actions=[]))
        self.assertNotIn("response_format", _CAPTURE["payload"])

    def test_response_carries_openai_identity_and_usage(self) -> None:
        provider = OpenAIProvider(self._config(), transport=_ok_transport)
        response = provider.respond(self._request())
        self.assertEqual(response.provider_name, "openai")
        self.assertEqual(response.source_label, "[OpenAI API output]")
        self.assertEqual(response.token_usage["total_tokens"], 33)

    def test_persona_is_prepended_but_contract_is_preserved(self) -> None:
        # The per-seat persona must appear BEFORE the machine contract, and the
        # contract's required JSON field list must remain verbatim (the parser
        # depends on it). Persona can flavor, never replace.
        persona = "你是一个极度激进的玩家,优先发起进攻。"
        provider = OpenAIProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request(persona_prompt=persona))
        system = _CAPTURE["payload"]["messages"][0]["content"]
        self.assertTrue(system.startswith(persona))
        # contract field list preserved verbatim
        self.assertIn(
            "action, target, reason_summary, decision_type, confidence", system
        )
        self.assertLess(system.index(persona), system.index("reason_summary"))

    def test_no_persona_leaves_contract_unchanged(self) -> None:
        provider = OpenAIProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request())
        system = _CAPTURE["payload"]["messages"][0]["content"]
        self.assertTrue(system.startswith("You are p3"))

    def test_persona_from_config_applies_when_request_has_none(self) -> None:
        # B3 wires per-seat persona onto the provider config; the witch direct-call
        # path builds its own request without persona, so config-level persona must
        # still take effect.
        persona = "保守稳健,先观望。"
        provider = OpenAIProvider(
            self._config(persona_prompt=persona), transport=_capturing_transport
        )
        provider.respond(self._request())
        system = _CAPTURE["payload"]["messages"][0]["content"]
        self.assertTrue(system.startswith(persona))

    def test_temperature_passed_through_when_set(self) -> None:
        provider = OpenAIProvider(
            self._config(temperature=0.7), transport=_capturing_transport
        )
        provider.respond(self._request())
        self.assertEqual(_CAPTURE["payload"]["temperature"], 0.7)

    def test_temperature_omitted_when_none(self) -> None:
        provider = OpenAIProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request())
        self.assertNotIn("temperature", _CAPTURE["payload"])

    def test_request_temperature_overrides_config(self) -> None:
        provider = OpenAIProvider(
            self._config(temperature=0.1), transport=_capturing_transport
        )
        provider.respond(self._request(temperature=0.9))
        self.assertEqual(_CAPTURE["payload"]["temperature"], 0.9)

    def test_missing_api_key_refuses_before_transport(self) -> None:
        provider = OpenAIProvider(self._config(api_key=""), transport=_ok_transport)
        with self.assertRaises(RuntimeError):
            provider.respond(self._request())

    def test_transport_error_does_not_leak_key(self) -> None:
        def boom(
            url: str,
            headers: dict[str, str],
            payload: dict[str, Any],
            timeout_seconds: int,
        ) -> dict[str, Any]:
            raise RuntimeError(f"HTTP 500 {headers['Authorization']}")

        provider = OpenAIProvider(
            self._config(api_key="sk-secret-openai"), transport=boom
        )
        with self.assertRaises(RuntimeError) as ctx:
            provider.respond(self._request())
        self.assertNotIn("sk-secret-openai", str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)

    def test_budget_enforced(self) -> None:
        provider = OpenAIProvider(
            self._config(max_requests=1), transport=_ok_transport
        )
        provider.respond(self._request())
        with self.assertRaises(RuntimeError) as ctx:
            provider.respond(self._request())
        self.assertIn("request budget exceeded", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
