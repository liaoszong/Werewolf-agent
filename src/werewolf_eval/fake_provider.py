from __future__ import annotations

import json
from typing import Any

from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    ProviderRequest,
    ProviderResponse,
)
from werewolf_eval.provider_agent import ProviderAgent


class DeterministicFakeProvider:
    def __init__(self, script: dict[tuple, str], provider_name: str = "deterministic_fake_provider") -> None:
        self._script = dict(script)
        self._provider_name = provider_name
        self._requests: list[ProviderRequest] = []
        self._responses: list[ProviderResponse] = []

    @property
    def requests(self) -> list[ProviderRequest]:
        return list(self._requests)

    @property
    def responses(self) -> list[ProviderResponse]:
        return list(self._responses)

    def respond(self, request: ProviderRequest) -> ProviderResponse:
        self._requests.append(request)
        key = (request.actor, request.phase, request.round)
        raw_content = self._script.get(key)
        if raw_content is None:
            raise KeyError(f"no script entry for {key}")
        response = ProviderResponse(
            request_id=request.request_id,
            provider_name=self._provider_name,
            source_label=FAKE_PROVIDER_SOURCE_LABEL,
            raw_content=raw_content,
            latency_ms=0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
        self._responses.append(response)
        return response


def build_default_fake_provider_script() -> dict[tuple, str]:
    return {
        ("p3", "night", 1): json.dumps({
            "action": "seer_check", "target": "p1",
            "reason_summary": "p3 seer checks p1",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p4", "night", 1): json.dumps({
            "action": "witch_save", "target": "p5",
            "reason_summary": "p4 witch saves p5",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p3", "day", 1): json.dumps({
            "action": "player_vote", "target": "p1",
            "reason_summary": "p3 votes p1 based on seer result",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p4", "day", 1): json.dumps({
            "action": "player_vote", "target": "p1",
            "reason_summary": "p4 follows vote on p1",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p5", "day", 1): json.dumps({
            "action": "player_vote", "target": "p1",
            "reason_summary": "p5 follows vote on p1",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p6", "day", 1): json.dumps({
            "action": "player_vote", "target": "p1",
            "reason_summary": "p6 follows vote on p1",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p4", "day", 2): json.dumps({
            "action": "player_vote", "target": "p2",
            "reason_summary": "p4 votes p2",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p5", "day", 2): json.dumps({
            "action": "player_vote", "target": "p2",
            "reason_summary": "p5 follows vote on p2",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("p6", "day", 2): json.dumps({
            "action": "player_vote", "target": "p2",
            "reason_summary": "p6 follows vote on p2",
            "decision_type": "inference_based", "confidence": 1.0,
        }, ensure_ascii=False),
        ("wolf_team", "night", 1): json.dumps({
            "action": "werewolf_kill", "target": "p5",
            "reason_summary": "wolf team kills p5",
            "decision_type": "team_coordinated", "confidence": 1.0,
        }, ensure_ascii=False),
        ("wolf_team", "night", 2): json.dumps({
            "action": "werewolf_kill", "target": "p3",
            "reason_summary": "wolf team kills seer p3",
            "decision_type": "team_coordinated", "confidence": 1.0,
        }, ensure_ascii=False),
    }


def build_default_fake_provider_agent(
    actor: str,
    override_raw_content: str | None = None,
    failure_mode: str | None = None,
) -> ProviderAgent:
    script = build_default_fake_provider_script()
    provider = DeterministicFakeProvider(script)
    return ProviderAgent(
        player_id=actor,
        provider=provider,
        override_raw_content=override_raw_content,
        failure_mode=failure_mode,
    )
