from __future__ import annotations

import unittest
from typing import Any

from werewolf_eval.llm_providers import AnthropicProvider, ChatProviderConfig
from werewolf_eval.provider_contract import ProviderRequest


def _ok_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": '{"action":"seer_check","target":"p1","reason_summary":"r","decision_type":"inference_based","confidence":1.0}',
            }
        ],
        "usage": {"input_tokens": 40, "output_tokens": 9},
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


class AnthropicProviderTests(unittest.TestCase):
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
            api_key="sk-ant-key",
            base_url="https://api.anthropic.com",
            model="claude-haiku-4-5",
        )
        kwargs.update(overrides)
        return ChatProviderConfig(**kwargs)

    def test_posts_to_messages_endpoint(self) -> None:
        provider = AnthropicProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request())
        self.assertEqual(_CAPTURE["url"], "https://api.anthropic.com/v1/messages")

    def test_uses_x_api_key_and_version_header_not_bearer(self) -> None:
        provider = AnthropicProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request())
        self.assertEqual(_CAPTURE["headers"]["x-api-key"], "sk-ant-key")
        self.assertIn("anthropic-version", _CAPTURE["headers"])
        self.assertNotIn("Authorization", _CAPTURE["headers"])

    def test_system_is_top_level_string_not_a_message(self) -> None:
        provider = AnthropicProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request())
        payload = _CAPTURE["payload"]
        self.assertIsInstance(payload["system"], str)
        self.assertIn("reason_summary", payload["system"])
        # messages contains only the user turn; no system role inside messages
        roles = [m["role"] for m in payload["messages"]]
        self.assertEqual(roles, ["user"])

    def test_content_blocks_parsed_to_raw_content(self) -> None:
        provider = AnthropicProvider(self._config(), transport=_ok_transport)
        response = provider.respond(self._request())
        self.assertEqual(response.provider_name, "anthropic")
        self.assertEqual(response.source_label, "[Anthropic API output]")
        self.assertIn("seer_check", response.raw_content)

    def test_usage_maps_input_output_to_prompt_completion_total(self) -> None:
        provider = AnthropicProvider(self._config(), transport=_ok_transport)
        response = provider.respond(self._request())
        self.assertEqual(response.token_usage["prompt_tokens"], 40)
        self.assertEqual(response.token_usage["completion_tokens"], 9)
        self.assertEqual(response.token_usage["total_tokens"], 49)

    def test_persona_prepended_contract_preserved(self) -> None:
        persona = "你是一个谨慎的村民。"
        provider = AnthropicProvider(self._config(), transport=_capturing_transport)
        provider.respond(self._request(persona_prompt=persona))
        system = _CAPTURE["payload"]["system"]
        self.assertTrue(system.startswith(persona))
        self.assertIn(
            "action, target, reason_summary, decision_type, confidence", system
        )

    def test_skips_leading_non_text_block(self) -> None:
        # Anthropic can return a leading non-text block (thinking / tool_use) with
        # the actual text in a later block; the parser must find the first text
        # block, not blindly index [0].
        def transport(url, headers, payload, timeout):
            return {
                "content": [
                    {"type": "thinking", "thinking": "hmm"},
                    {"type": "text", "text": '{"action":"seer_check"}'},
                ],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }

        provider = AnthropicProvider(self._config(), transport=transport)
        response = provider.respond(self._request())
        self.assertIn("seer_check", response.raw_content)

    def test_truly_empty_content_still_errors(self) -> None:
        def transport(url, headers, payload, timeout):
            return {"content": [], "usage": {"input_tokens": 1, "output_tokens": 0}}

        provider = AnthropicProvider(self._config(), transport=transport)
        with self.assertRaises(RuntimeError):
            provider.respond(self._request())

    def test_temperature_passed_through(self) -> None:
        provider = AnthropicProvider(
            self._config(temperature=0.5), transport=_capturing_transport
        )
        provider.respond(self._request())
        self.assertEqual(_CAPTURE["payload"]["temperature"], 0.5)

    def test_max_tokens_is_min_of_request_and_config(self) -> None:
        provider = AnthropicProvider(self._config(max_tokens=300), transport=_capturing_transport)
        provider.respond(self._request(max_output_tokens=120))
        self.assertEqual(_CAPTURE["payload"]["max_tokens"], 120)
        provider2 = AnthropicProvider(self._config(max_tokens=50), transport=_capturing_transport)
        provider2.respond(self._request(max_output_tokens=120))
        self.assertEqual(_CAPTURE["payload"]["max_tokens"], 50)

    def test_transport_error_does_not_leak_key(self) -> None:
        def boom(
            url: str,
            headers: dict[str, str],
            payload: dict[str, Any],
            timeout_seconds: int,
        ) -> dict[str, Any]:
            raise RuntimeError(f"HTTP 401 {headers['x-api-key']}")

        provider = AnthropicProvider(
            self._config(api_key="sk-ant-secret"), transport=boom
        )
        with self.assertRaises(RuntimeError) as ctx:
            provider.respond(self._request())
        self.assertNotIn("sk-ant-secret", str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main()
