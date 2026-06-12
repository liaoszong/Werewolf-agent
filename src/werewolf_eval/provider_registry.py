"""P2-B-3 provider registry — the SINGLE source of truth for which live
providers exist and their wire conventions (provider class, canonical base URL,
model-listing path, source label). The dynamic-model endpoint (B1), the credential
write gate (B1), and the per-seat live launcher (B3) all read from HERE so no
component re-guesses endpoint/auth/base-url rules.

Base-URL convention (explicit, not guessed): the chat suffix and the models path
are appended to ``base_url``. OpenAI's canonical root carries ``/v1`` while
DeepSeek's does not, so a single models_path of ``/models`` resolves to
``/v1/models`` for OpenAI and ``/models`` for DeepSeek. Anthropic keeps ``/v1`` in
its suffixes.
"""

from __future__ import annotations

import dataclasses
import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from werewolf_eval.deepseek_provider import DeepSeekProvider
from werewolf_eval.llm_providers import (
    AnthropicProvider,
    BaseChatProvider,
    ChatProviderConfig,
    OpenAICompatibleCustomProvider,
    OpenAIProvider,
    raise_sanitized_transport_error,
)
from werewolf_eval.provider_contract import (
    ANTHROPIC_PROVIDER_SOURCE_LABEL,
    DEEPSEEK_PROVIDER_SOURCE_LABEL,
    OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
    OPENAI_PROVIDER_SOURCE_LABEL,
)


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    label: str
    provider_cls: type[BaseChatProvider]
    default_base_url: str
    models_path: str
    source_label: str
    requires_base_url: bool = False
    # Offline UI fallback model ids (live fetch overrides). NOT a validation
    # allowlist — live providers trust the fetched/typed model id.
    default_models: tuple[str, ...] = ()
    # B5 closeout: optional pricing metadata for cost estimation.
    # Schema: {"input_per_mtok": float, "output_per_mtok": float, "currency": str}
    # No hardcoded prices here — pricing is provider-specific and drifts over time.
    # Consumers (settlement_bundle) use this to compute cost estimates; None means
    # "no pricing available, show token totals only". Prices can be populated by
    # external configuration or a future pricing registry.
    pricing: dict[str, object] | None = None


PROVIDER_REGISTRY: dict[str, ProviderSpec] = {
    "deepseek": ProviderSpec(
        provider_id="deepseek",
        label="DeepSeek",
        provider_cls=DeepSeekProvider,
        default_base_url="https://api.deepseek.com",
        models_path="/models",
        source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL,
        # Offline UI fallback so a deepseek seat has a VALID model before a live
        # fetch (these are DeepSeek's real chat models).
        default_models=("deepseek-chat", "deepseek-reasoner"),
    ),
    "openai": ProviderSpec(
        provider_id="openai",
        label="OpenAI",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.openai.com/v1",
        models_path="/models",
        source_label=OPENAI_PROVIDER_SOURCE_LABEL,
        default_models=("gpt-4o", "gpt-4o-mini"),
    ),
    "anthropic": ProviderSpec(
        provider_id="anthropic",
        label="Anthropic",
        provider_cls=AnthropicProvider,
        default_base_url="https://api.anthropic.com",
        models_path="/v1/models",
        source_label=ANTHROPIC_PROVIDER_SOURCE_LABEL,
        default_models=("claude-sonnet-4-6", "claude-haiku-4-5-20251001"),
    ),
    "openai_compatible": ProviderSpec(
        provider_id="openai_compatible",
        label="OpenAI-compatible (custom)",
        provider_cls=OpenAICompatibleCustomProvider,
        default_base_url="",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        requires_base_url=True,
    ),
    "zhipu": ProviderSpec(
        provider_id="zhipu",
        label="Zhipu GLM",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.z.ai/api/paas/v4",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("glm-4.7", "glm-4.6", "glm-4.5-air"),
    ),
    "moonshot": ProviderSpec(
        provider_id="moonshot",
        label="Moonshot Kimi",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.moonshot.ai/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("kimi-k2.6", "moonshot-v1-8k"),
    ),
    "qwen": ProviderSpec(
        provider_id="qwen",
        label="Alibaba Qwen",
        provider_cls=OpenAIProvider,
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("qwen3-max", "qwen-plus", "qwen-flash"),
    ),
    "minimax": ProviderSpec(
        provider_id="minimax",
        label="MiniMax",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.minimax.io/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("MiniMax-M3", "MiniMax-Text-01"),
    ),
    "siliconflow": ProviderSpec(
        provider_id="siliconflow",
        label="SiliconFlow",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.siliconflow.cn/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"),
    ),
    "xai": ProviderSpec(
        provider_id="xai",
        label="xAI Grok",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.x.ai/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("grok-4.3", "grok-4"),
    ),
    "gemini": ProviderSpec(
        provider_id="gemini",
        label="Google Gemini",
        provider_cls=OpenAIProvider,
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"),
    ),
    "modelscope": ProviderSpec(
        provider_id="modelscope",
        label="ModelScope",
        provider_cls=OpenAIProvider,
        default_base_url="https://api-inference.modelscope.cn/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"),
    ),
    "openrouter": ProviderSpec(
        provider_id="openrouter",
        label="OpenRouter",
        provider_cls=OpenAIProvider,
        default_base_url="https://openrouter.ai/api/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("~openai/gpt-latest", "~anthropic/claude-sonnet-latest", "openrouter/auto"),
    ),
}


def _effective_base_url(spec: ProviderSpec, base_url: str) -> str:
    return (base_url or spec.default_base_url).rstrip("/")


def model_list_url(provider_id: str, base_url: str) -> str:
    """The GET URL for a provider's model list. Empty ``base_url`` falls back to the
    spec default (custom providers have no default and must supply one)."""
    spec = PROVIDER_REGISTRY[provider_id]
    return f"{_effective_base_url(spec, base_url)}{spec.models_path}"


def build_provider(
    provider_id: str,
    config: ChatProviderConfig,
    transport=None,
) -> BaseChatProvider:
    """Instantiate the provider class for ``provider_id``, filling a blank
    ``base_url`` with the registry default. Raises KeyError for unknown providers."""
    spec = PROVIDER_REGISTRY[provider_id]
    effective_base_url = config.base_url or spec.default_base_url
    if spec.requires_base_url and not effective_base_url:
        raise ValueError(f"provider {provider_id!r} requires a base_url")
    if not config.base_url:
        config = dataclasses.replace(config, base_url=spec.default_base_url)
    provider = spec.provider_cls(config, transport=transport)
    # Stamp the registry identity so per-seat artifacts (manifest, provider trace,
    # ProviderResponse.provider_name/source_label) name the REAL vendor, not the
    # shared class default ("openai"). Instance attrs shadow the class attrs that
    # respond() reads. No-op for the existing 4 (class defaults already match).
    provider.PROVIDER_NAME = spec.provider_id
    provider.SOURCE_LABEL = spec.source_label
    return provider


# --------------------------------------------------------------- model discovery
# A GET transport mirrors the providers' POST transport seam so model listing is
# unit-testable without network. Signature: (url, headers, timeout) -> dict.
ModelsTransport = Callable[[str, dict[str, str], int], dict[str, Any]]


def _default_models_transport(
    url: str, headers: dict[str, str], timeout_seconds: int
) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    resp = urllib.request.urlopen(req, timeout=timeout_seconds)
    return json.loads(resp.read().decode("utf-8"))


def list_models(
    provider_id: str,
    config: ChatProviderConfig,
    transport: ModelsTransport | None = None,
) -> list[str]:
    """Fetch the provider's model ids (OpenAI/DeepSeek/Anthropic all return
    ``{"data":[{"id":...}]}``). Reuses the provider's own auth headers so the
    BYO-key handling is single-sourced. Never leaks the key on error."""
    spec = PROVIDER_REGISTRY[provider_id]
    url = model_list_url(provider_id, config.base_url)  # applies default fallback
    # Reuse the provider's exact auth header builder (single source of truth).
    # This instantiates the class directly (NOT via build_provider) on purpose:
    # model listing only needs config-driven auth headers, never the stamped
    # PROVIDER_NAME/SOURCE_LABEL identity, so the un-stamped instance is correct.
    headers = spec.provider_cls(config)._build_headers()
    fetch = transport if transport is not None else _default_models_transport
    try:
        raw = fetch(url, headers, config.timeout_seconds)
    except Exception as exc:
        raise_sanitized_transport_error(f"{provider_id} models", exc)
    data = raw.get("data", []) if isinstance(raw, dict) else []
    return [str(m["id"]) for m in data if isinstance(m, dict) and m.get("id")]


def provider_specs_payload() -> list[dict[str, object]]:
    """Read-only UI metadata for every registered provider. The observer server
    merges this into the profile-schema response so the Qt client can data-drive
    its provider list and per-provider model dropdowns. Never carries a secret."""
    return [
        {
            "id": spec.provider_id,
            "label": spec.label,
            "default_base_url": spec.default_base_url,
            "requires_base_url": spec.requires_base_url,
            "default_models": list(spec.default_models),
        }
        for spec in PROVIDER_REGISTRY.values()
    ]
