from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

FAKE_PROVIDER_SOURCE_LABEL = "[deterministic fake provider output]"
DEEPSEEK_PROVIDER_SOURCE_LABEL = "[DeepSeek API output]"


@dataclass(frozen=True)
class ProviderRequest:
    request_id: str
    game_id: str
    actor: str
    phase: str
    round: int
    observation: dict[str, Any]
    allowed_actions: list[str]
    allowed_targets: list[str]
    response_format_version: str = "g1d-action-v1"
    # P2-A-2 (additive, back-compat): role-safe readable observation text the
    # engine renders; "action" (JSON) vs "speech" (free text) response mode; an
    # optional per-request output-token cap (speech needs more than vote/action).
    observation_text: str = ""
    response_kind: str = "action"
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class ProviderResponse:
    request_id: str
    provider_name: str
    source_label: str
    raw_content: str
    latency_ms: int
    token_usage: dict[str, int]


@dataclass(frozen=True)
class ProviderFailure:
    request_id: str
    game_id: str
    round: int
    phase: str
    actor: str
    kind: str
    reason: str
    target: str | None = None
    repaired_to_valid_action: bool = False


@dataclass(frozen=True)
class ProviderTrace:
    game_id: str
    provider_name: str
    source_label: str
    requests: list[ProviderRequest]
    responses: list[ProviderResponse]
    failures: list[ProviderFailure]


def provider_request_to_dict(request: ProviderRequest) -> dict[str, Any]:
    return asdict(request)


def provider_response_to_dict(response: ProviderResponse) -> dict[str, Any]:
    return asdict(response)


def provider_failure_to_dict(failure: ProviderFailure) -> dict[str, Any]:
    return asdict(failure)


def provider_trace_to_dict(trace: ProviderTrace) -> dict[str, Any]:
    return {
        "game_id": trace.game_id,
        "provider_name": trace.provider_name,
        "source_label": trace.source_label,
        "requests": [provider_request_to_dict(r) for r in trace.requests],
        "responses": [provider_response_to_dict(r) for r in trace.responses],
        "failures": [provider_failure_to_dict(f) for f in trace.failures],
    }
