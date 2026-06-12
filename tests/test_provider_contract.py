from __future__ import annotations

import json
import unittest

from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTrace,
    classify_provider_failure_kind,
    provider_failure_to_dict,
    provider_request_to_dict,
    provider_response_to_dict,
    provider_trace_to_dict,
)
from werewolf_eval.source_labels import VALID_SOURCE_LABELS


class ProviderContractTests(unittest.TestCase):
    def test_fake_provider_source_label_is_registered(self) -> None:
        self.assertEqual(FAKE_PROVIDER_SOURCE_LABEL, "[deterministic fake provider output]")
        self.assertIn(FAKE_PROVIDER_SOURCE_LABEL, VALID_SOURCE_LABELS)

    def test_request_response_failure_trace_are_json_safe(self) -> None:
        request = ProviderRequest(
            request_id="g1d_fake_provider_r01_p3",
            game_id="g1d_fake_provider",
            actor="p3",
            phase="night",
            round=1,
            observation={"player_id": "p3", "private_event_ids": []},
            allowed_actions=["seer_check"],
            allowed_targets=["p1", "p2"],
        )
        response = ProviderResponse(
            request_id=request.request_id,
            provider_name="deterministic_fake_provider",
            source_label=FAKE_PROVIDER_SOURCE_LABEL,
            raw_content='{"action":"seer_check","target":"p1","reason_summary":"p3 checks p1","decision_type":"inference_based","confidence":1.0}',
            latency_ms=0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
        failure = ProviderFailure(
            request_id="g1d_fake_provider_r01_p4",
            game_id="g1d_fake_provider",
            round=1,
            phase="night",
            actor="p4",
            kind="parse_failure",
            reason="provider response was not valid JSON",
        )
        trace = ProviderTrace(
            game_id="g1d_fake_provider",
            provider_name="deterministic_fake_provider",
            source_label=FAKE_PROVIDER_SOURCE_LABEL,
            requests=[request],
            responses=[response],
            failures=[failure],
        )

        payload = provider_trace_to_dict(trace)
        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertIn("g1d_fake_provider", encoded)
        self.assertNotIn("api_key", encoded.lower())
        self.assertNotIn("authorization", encoded.lower())
        self.assertNotIn("http://", encoded.lower())
        self.assertNotIn("https://", encoded.lower())
        self.assertFalse(provider_failure_to_dict(failure)["repaired_to_valid_action"])
        self.assertEqual(provider_request_to_dict(request)["response_format_version"], "g1d-action-v1")
        self.assertEqual(provider_response_to_dict(response)["source_label"], FAKE_PROVIDER_SOURCE_LABEL)


class ClassifyProviderFailureKindTests(unittest.TestCase):
    """B34-10: single source of truth mapping a provider transport/respond
    exception to a structured failure kind. Matches llm_providers wording."""

    def test_budget_exhausted_from_either_wording(self) -> None:
        # llm_providers raises "request budget exceeded: N"; emergent reason reads
        # "budget exhausted"; both must classify structurally.
        self.assertEqual(
            classify_provider_failure_kind(RuntimeError("request budget exceeded: 32")),
            "budget_exhausted",
        )
        self.assertEqual(
            classify_provider_failure_kind(RuntimeError("budget exhausted: 30/30 requests")),
            "budget_exhausted",
        )

    def test_transport_error(self) -> None:
        self.assertEqual(
            classify_provider_failure_kind(RuntimeError("[DeepSeek API output] transport error: ConnectionError")),
            "transport_error",
        )

    def test_auth_failed(self) -> None:
        self.assertEqual(
            classify_provider_failure_kind(RuntimeError("DeepSeek API key is not configured")),
            "auth_failed",
        )

    def test_unknown_defaults_to_provider_error(self) -> None:
        self.assertEqual(
            classify_provider_failure_kind(RuntimeError("DeepSeek returned empty content")),
            "provider_error",
        )
        self.assertEqual(
            classify_provider_failure_kind(ValueError("something weird")),
            "provider_error",
        )


if __name__ == "__main__":
    unittest.main()
