from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from werewolf_eval.provider_contract import (
    DEEPSEEK_PROVIDER_SOURCE_LABEL,
    ProviderRequest,
    ProviderResponse,
)

Transport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]


@dataclass(frozen=True)
class DeepSeekProviderConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: int = 30
    max_tokens: int = 256
    max_requests: int = 11


def _default_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=timeout_seconds)
    body = resp.read().decode("utf-8")
    return json.loads(body)


class DeepSeekProvider:
    def __init__(
        self,
        config: DeepSeekProviderConfig,
        transport: Transport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport if transport is not None else _default_transport
        self._request_history: list[ProviderRequest] = []
        self._response_history: list[ProviderResponse] = []

    @property
    def requests(self) -> list[ProviderRequest]:
        return list(self._request_history)

    @property
    def responses(self) -> list[ProviderResponse]:
        return list(self._response_history)

    @property
    def model(self) -> str:
        return self._config.model

    def _user_content(self, request: ProviderRequest) -> str:
        """Readable observation text when the engine provides it (P2-A-2);
        legacy raw-observation dump only as a back-compat fallback."""
        if request.observation_text:
            return request.observation_text
        return json.dumps(request.observation)

    def _build_speech_payload(self, request: ProviderRequest) -> dict[str, Any]:
        # P2-A-2 speech path: free text, NO JSON, NO allowed_actions[0] (which
        # would IndexError for a speech request with empty allowed_actions).
        system_prompt = (
            f"你是狼人杀里的 {request.actor}(第 {request.round} 轮,白天发言)。"
            f"请用自然口吻发言,3-5 句或 120-180 字。"
            f"发言应尽量包含:当前局势判断、你怀疑或相信的对象、一个具体理由、本轮投票倾向。"
            f"不要使用固定小标题,不要输出 JSON,直接说话。"
        )
        return {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._user_content(request)},
            ],
            "stream": False,
            "thinking": {"type": "disabled"},
            "max_tokens": request.max_output_tokens or self._config.max_tokens,
        }

    def _build_request_payload(self, request: ProviderRequest) -> dict[str, Any]:
        if request.response_kind == "speech":
            return self._build_speech_payload(request)
        allowed_actions_str = ", ".join(request.allowed_actions)
        allowed_targets_str = ", ".join(request.allowed_targets)
        example_action = request.allowed_actions[0] if request.allowed_actions else "player_vote"
        example_target = request.allowed_targets[0] if request.allowed_targets else "p1"
        system_prompt = (
            f"You are {request.actor} in a Werewolf game (round {request.round}, "
            f"phase {request.phase}). "
            f"Respond with valid JSON containing exactly: action, target, reason_summary, "
            f"decision_type, confidence. "
            f"You MUST select action from [{allowed_actions_str}] "
            f"and target from [{allowed_targets_str}]. "
            f"No other action or target value is acceptable. "
            f"decision_type must be exactly one of: inference_based, random, retaliatory. "
            f"Do not invent other decision_type values. "
            f"Example response format:\n"
            f'{{"action":"{example_action}","target":"{example_target}",'
            f'"reason_summary":"your reasoning here","decision_type":"inference_based",'
            f'"confidence":0.9}}'
        )
        return {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._user_content(request)},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "thinking": {"type": "disabled"},
            "max_tokens": request.max_output_tokens or self._config.max_tokens,
        }

    def respond(self, request: ProviderRequest) -> ProviderResponse:
        if not self._config.api_key:
            raise RuntimeError("DeepSeek API key is not configured")

        if len(self._response_history) >= self._config.max_requests:
            msg = f"request budget exceeded: {self._config.max_requests}"
            raise RuntimeError(msg)

        base_url = self._config.base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }

        payload = self._build_request_payload(request)

        self._request_history.append(request)

        try:
            raw = self._transport(url, headers, payload, self._config.timeout_seconds)
        except Exception as exc:
            msg = str(exc)
            raise RuntimeError(f"DeepSeek transport error") from exc

        choices = raw.get("choices", [])
        if not choices:
            raise RuntimeError("DeepSeek returned empty choices")

        raw_content = choices[0].get("message", {}).get("content", "").strip()
        if not raw_content:
            raise RuntimeError("DeepSeek returned empty content")

        usage_raw = raw.get("usage", {})
        token_usage = {
            "prompt_tokens": usage_raw.get("prompt_tokens", 0),
            "completion_tokens": usage_raw.get("completion_tokens", 0),
            "total_tokens": usage_raw.get("total_tokens", 0),
        }

        response = ProviderResponse(
            request_id=request.request_id,
            provider_name="deepseek",
            source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL,
            raw_content=raw_content,
            latency_ms=0,
            token_usage=token_usage,
        )

        self._response_history.append(response)
        return response
