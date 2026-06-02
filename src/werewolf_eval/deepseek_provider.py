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

    def _build_request_payload(self, request: ProviderRequest) -> dict[str, Any]:
        allowed_actions_str = ", ".join(request.allowed_actions)
        allowed_targets_str = ", ".join(request.allowed_targets)
        system_prompt = (
            f"You are {request.actor} in a Werewolf game (round {request.round}, "
            f"phase {request.phase}). "
            f"Respond with valid JSON containing exactly: action, target, reason_summary, "
            f"decision_type, confidence. "
            f"You MUST select action from [{allowed_actions_str}] "
            f"and target from [{allowed_targets_str}]. "
            f"No other action or target value is acceptable. "
            f"Example response format:\n"
            f'{{"action":"{request.allowed_actions[0]}","target":"{request.allowed_targets[0]}",'
            f'"reason_summary":"your reasoning here","decision_type":"inference_based",'
            f'"confidence":0.9}}'
        )
        return {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(request.observation)},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "thinking": {"type": "disabled"},
            "max_tokens": self._config.max_tokens,
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
