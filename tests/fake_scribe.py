"""Shared fake scribe provider for prompt_v3 tests (NOT a test module).
Mimics the BaseChatProvider surface the engine/_collect_trace touch
(respond / model / requests / responses)."""
from werewolf_eval.provider_contract import ProviderResponse


class _FakeScribeProvider:
    uses_baseline_prompt = False
    provider_runtime_kind = "deterministic_fake"

    def __init__(self, broken=False):
        self.broken = broken
        self.requests = []
        self.responses = []
        self.model = "none"

    def respond(self, request):
        self.requests.append(request)
        content = "GARBAGE" if self.broken else (
            '{"claims":[{"claimant":"p3","claim_type":"identity_claim","target":null,'
            '"result":"seer","refutes":null,"source":1,"source_quote":"测试声称","uncertain":false}]}'
        )
        resp = ProviderResponse(request_id=request.request_id, provider_name="fake_scribe",
                                source_label="[deterministic fake provider output]",
                                raw_content=content, latency_ms=0,
                                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        self.responses.append(resp)
        return resp
