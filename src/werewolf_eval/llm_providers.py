"""P2-B-3 multi-provider abstraction.

A single ``respond(ProviderRequest) -> ProviderResponse`` seam (provider_contract)
generalized across provider dialects:

  - OpenAI-compatible (OpenAI, DeepSeek, generic custom): POST {base}/chat/completions,
    ``Authorization: Bearer``, ``messages=[system,user]``, ``choices[0].message.content``.
  - Anthropic: POST {base}/v1/messages, ``x-api-key`` + ``anthropic-version``, ``system``
    as a TOP-LEVEL string, ``content[0].text``, ``usage.{input,output}_tokens``.

The MACHINE CONTRACT system prompts (the exact JSON field list the engine's
``ProviderAgent`` parser depends on) live here as shared builders so EVERY provider
emits the identical contract. A per-seat ``persona_prompt`` is only ever PREPENDED to
that contract (``compose_system``) — it can flavor behavior but can never replace the
contract. The BYO-key invariant (keys never reach crash logs) is enforced once, in the
base ``respond`` transport-error guard.

``DeepSeekProvider`` lives in ``deepseek_provider`` as a thin subclass of
``OpenAICompatibleProvider`` (back-compat: its public API is unchanged). The wired
registry of all providers lives in ``provider_registry``.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from werewolf_eval.prompt_renderers import get_renderer
from werewolf_eval.prompt_v1 import build_speech_system_prompt
from werewolf_eval.prompt_v2 import build_speech_system_prompt_v2
from werewolf_eval.prompt_v3 import build_speech_system_prompt_v3
from werewolf_eval.provider_contract import (
    ANTHROPIC_PROVIDER_SOURCE_LABEL,
    OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
    OPENAI_PROVIDER_SOURCE_LABEL,
    ProviderRequest,
    ProviderResponse,
)

Transport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]


@dataclass(frozen=True)
class ChatProviderConfig:
    """Per-provider (and, in P2-B-3, per-seat) provider configuration.

    ``persona_prompt`` / ``temperature`` are the per-seat knobs; both default to a
    no-op so a provider built without them behaves exactly as before."""

    api_key: str
    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 30
    max_tokens: int = 256
    max_requests: int = 11
    persona_prompt: str = ""
    temperature: float | None = None


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


def raise_sanitized_transport_error(label: str, exc: BaseException):
    """Single source of the BYO-key transport-error guard, used by every provider
    ``respond`` and by the model-listing fetch. The original exception's traceback
    frames hold the ``headers`` local (auth header with the key); ``from None``
    breaks that chain and we surface only the exception CLASS name (never its str,
    which can carry the URL). Hardening applied here covers all callers at once."""
    raise RuntimeError(f"{label} transport error: {type(exc).__name__}") from None


# --------------------------------------------------------------- system prompts
# These are the SHARED machine-contract system prompts. They are provider-agnostic
# so OpenAI / DeepSeek / Anthropic all bind the ProviderAgent JSON parser to the
# SAME contract. The action prompt's exact text is byte-preserved from the original
# DeepSeek implementation so existing parsing/tests stay green.


def build_action_system_prompt(request: ProviderRequest) -> str:
    allowed_actions_str = ", ".join(request.allowed_actions)
    allowed_targets_str = ", ".join(request.allowed_targets)
    example_action = request.allowed_actions[0] if request.allowed_actions else "player_vote"
    example_target = request.allowed_targets[0] if request.allowed_targets else "p1"
    return (
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


def build_scribe_system_prompt(request: ProviderRequest) -> str:
    # SYS-B4 §3 scheme C: the scribe is an EXTRACTION artifact, not a judge.
    # Strict JSON (the scaffold request rides response_format=json_object on
    # OpenAI-compatible dialects; Anthropic has no such switch — coverage gate
    # absorbs any parse-failure delta there).
    return (
        "你是狼人杀对局的书记员。你只负责提取,不要判断真假、不要推理谁是狼。"
        "从下面带编号的发言记录中提取所有身份声称、查验报告与反驳,输出 JSON:"
        '{"claims":[{"claimant":"pX","claim_type":"identity_claim|check_report|refutation",'
        '"target":"pX或null","result":"身份或查验结果或null","refutes":"pX或null",'
        '"source":发言编号,"source_quote":"原文片段","uncertain":true或false}]}。'
        "规则:claimant 必须是发言者本人;source_quote 必须是该发言的原文片段;"
        "提取不到明确声称就输出 {\"claims\":[]};语义含糊时照常提取但把 uncertain 设为 true。"
        "不要输出 JSON 以外的任何内容。"
    )


def compose_system(persona_prompt: str, contract: str) -> str:
    """Prepend the per-seat persona to the machine contract. The contract is kept
    verbatim and is never removed/altered — an empty persona returns it unchanged
    (byte-identical to the no-persona path)."""
    persona = (persona_prompt or "").strip()
    if not persona:
        return contract
    return f"{persona}\n\n{contract}"


# ----------------------------------------------------------------- base provider


class BaseChatProvider:
    """Shared respond() skeleton, budget/history, and the BYO-key transport-error
    guard. Dialect specifics live in the hooks below."""

    # Spec 2026-06-10-prompt-versioning §4.4: declared mechanism, NOT name-sniffing.
    # prompt_used_by_runtime is derived from these declarations by runners.
    provider_runtime_kind = "live_model"
    uses_baseline_prompt = True

    PROVIDER_NAME: str = "base"
    SOURCE_LABEL: str = ""

    def __init__(
        self,
        config: ChatProviderConfig,
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

    @property
    def persona(self) -> str:
        """The per-seat persona seed baked into this provider's config (used by the
        runner to record a per-seat prompt_hash in the manifest). Empty string when
        no persona was set."""
        return self._config.persona_prompt

    # -- per-seat effective knobs (request overrides config) -------------------
    def _effective_persona(self, request: ProviderRequest) -> str:
        return request.persona_prompt or self._config.persona_prompt

    def _effective_temperature(self, request: ProviderRequest) -> float | None:
        if request.temperature is not None:
            return request.temperature
        return self._config.temperature

    def _effective_max_tokens(self, request: ProviderRequest) -> int:
        """The per-call output cap. The engine sets a per-response-kind cap on the
        request (action vs speech); a per-seat ``max_tokens`` acts as a CEILING on
        top of it (``min``), so it can tighten a seat's budget but never exceed the
        engine's safety cap. With the default seat budget this is a no-op
        (min(120, 256) == 120), preserving legacy behavior exactly."""
        req = request.max_output_tokens
        cfg = self._config.max_tokens
        if req is None:
            return cfg
        if cfg is None:
            return req
        return min(req, cfg)

    def _system_for(self, request: ProviderRequest) -> str:
        # defense in depth: engine/harness already gate this; never silently
        # render an unknown version as v1 (get_renderer fail-louds for EVERY
        # response_kind, matching the old up-front check).
        renderer = get_renderer(request.prompt_version)
        if request.response_kind == "scaffold":
            contract = build_scribe_system_prompt(request)
        elif request.response_kind == "speech":
            contract = renderer.speech_contract(request)
        else:
            contract = build_action_system_prompt(request)
        composed = compose_system(self._effective_persona(request), contract)
        if request.board_card:
            # board rules card tops the system prompt; empty card (all v1
            # requests) keeps the composed bytes identical to legacy.
            return f"{request.board_card}\n\n{composed}"
        return composed

    def _user_content(self, request: ProviderRequest) -> str:
        """Readable observation text when the engine provides it (P2-A-2);
        legacy raw-observation dump only as a back-compat fallback."""
        if request.observation_text:
            return request.observation_text
        return json.dumps(request.observation)

    def respond(self, request: ProviderRequest) -> ProviderResponse:
        if not self._config.api_key:
            raise RuntimeError(f"{self.PROVIDER_NAME} API key is not configured")

        if len(self._response_history) >= self._config.max_requests:
            msg = f"request budget exceeded: {self._config.max_requests}"
            raise RuntimeError(msg)

        url = self._build_url()
        headers = self._build_headers()
        payload = self._build_payload(request)

        self._request_history.append(request)

        try:
            raw = self._transport(url, headers, payload, self._config.timeout_seconds)
        except Exception as exc:
            raise_sanitized_transport_error(self.PROVIDER_NAME, exc)

        raw_content = self._extract_content(raw)
        token_usage = self._extract_usage(raw)

        response = ProviderResponse(
            request_id=request.request_id,
            provider_name=self.PROVIDER_NAME,
            source_label=self.SOURCE_LABEL,
            raw_content=raw_content,
            latency_ms=0,
            token_usage=token_usage,
        )

        self._response_history.append(response)
        return response

    # -- dialect hooks --------------------------------------------------------
    def _build_url(self) -> str:
        raise NotImplementedError

    def _build_headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        raise NotImplementedError

    def _extract_content(self, raw: dict[str, Any]) -> str:
        raise NotImplementedError

    def _extract_usage(self, raw: dict[str, Any]) -> dict[str, int]:
        raise NotImplementedError


# --------------------------------------------------------- OpenAI-compatible family


class OpenAICompatibleProvider(BaseChatProvider):
    """OpenAI-style ``/chat/completions`` providers (OpenAI, DeepSeek, generic
    custom). Subclasses toggle the few dialect keys via class flags."""

    PROVIDER_NAME = "openai_compatible"
    SOURCE_LABEL = OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL
    CHAT_SUFFIX = "/chat/completions"
    # DeepSeek-only key; OpenAI/custom leave it off.
    INCLUDE_THINKING = False
    # JSON mode for the action path (speech is free text). OpenAI & DeepSeek
    # both support response_format={"type":"json_object"}.
    INCLUDE_RESPONSE_FORMAT = True

    def _build_url(self) -> str:
        base_url = self._config.base_url.rstrip("/")
        return f"{base_url}{self.CHAT_SUFFIX}"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }

    def _build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": self._system_for(request)},
                {"role": "user", "content": self._user_content(request)},
            ],
            "stream": False,
            "max_tokens": self._effective_max_tokens(request),
        }
        if self.INCLUDE_THINKING:
            payload["thinking"] = {"type": "disabled"}
        if request.response_kind != "speech" and self.INCLUDE_RESPONSE_FORMAT:
            payload["response_format"] = {"type": "json_object"}
        temperature = self._effective_temperature(request)
        if temperature is not None:
            payload["temperature"] = temperature
        return payload

    def _extract_content(self, raw: dict[str, Any]) -> str:
        choices = raw.get("choices", [])
        if not choices:
            raise RuntimeError(f"{self.PROVIDER_NAME} returned empty choices")
        raw_content = choices[0].get("message", {}).get("content", "").strip()
        if not raw_content:
            raise RuntimeError(f"{self.PROVIDER_NAME} returned empty content")
        return raw_content

    def _extract_usage(self, raw: dict[str, Any]) -> dict[str, int]:
        usage_raw = raw.get("usage", {})
        return {
            "prompt_tokens": usage_raw.get("prompt_tokens", 0),
            "completion_tokens": usage_raw.get("completion_tokens", 0),
            "total_tokens": usage_raw.get("total_tokens", 0),
        }


class OpenAIProvider(OpenAICompatibleProvider):
    PROVIDER_NAME = "openai"
    SOURCE_LABEL = OPENAI_PROVIDER_SOURCE_LABEL
    INCLUDE_THINKING = False
    INCLUDE_RESPONSE_FORMAT = True


class OpenAICompatibleCustomProvider(OpenAICompatibleProvider):
    """A user-supplied OpenAI-compatible endpoint (BYO base_url)."""

    PROVIDER_NAME = "openai_compatible"
    SOURCE_LABEL = OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL
    INCLUDE_THINKING = False
    INCLUDE_RESPONSE_FORMAT = True


# ------------------------------------------------------------------ Anthropic


class AnthropicProvider(BaseChatProvider):
    """Anthropic Messages API: distinct endpoint, auth header, top-level system,
    and content/usage shapes. JSON mode is enforced via the contract prompt
    (Anthropic has no response_format=json_object)."""

    PROVIDER_NAME = "anthropic"
    SOURCE_LABEL = ANTHROPIC_PROVIDER_SOURCE_LABEL
    CHAT_SUFFIX = "/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"

    def _build_url(self) -> str:
        base_url = self._config.base_url.rstrip("/")
        return f"{base_url}{self.CHAT_SUFFIX}"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self._config.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
        }

    def _build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "system": self._system_for(request),
            "messages": [
                {"role": "user", "content": self._user_content(request)},
            ],
            "max_tokens": self._effective_max_tokens(request),
        }
        temperature = self._effective_temperature(request)
        if temperature is not None:
            payload["temperature"] = temperature
        return payload

    def _extract_content(self, raw: dict[str, Any]) -> str:
        # Anthropic may return a leading non-text block (thinking / tool_use) with
        # the answer in a later block — scan for the first non-empty text block
        # rather than blindly indexing [0].
        blocks = raw.get("content", [])
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text:
                    return text
        raise RuntimeError(f"{self.PROVIDER_NAME} returned empty content")

    def _extract_usage(self, raw: dict[str, Any]) -> dict[str, int]:
        usage_raw = raw.get("usage", {})
        prompt_tokens = usage_raw.get("input_tokens", 0)
        completion_tokens = usage_raw.get("output_tokens", 0)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
