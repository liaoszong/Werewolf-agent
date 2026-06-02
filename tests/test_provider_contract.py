from __future__ import annotations

import json
import unittest

from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTrace,
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


if __name__ == "__main__":
    unittest.main()
