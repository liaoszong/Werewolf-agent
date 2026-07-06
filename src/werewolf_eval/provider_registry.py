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

WIRE_OPENAI_CHAT_COMPLETIONS = "openai_chat_completions"
WIRE_ANTHROPIC_MESSAGES = "anthropic_messages"
CHAT_PROVIDER_CONFIG_DEFAULT_TIMEOUT_SECONDS = ChatProviderConfig.__dataclass_fields__[
    "timeout_seconds"
].default
OPENAI_CHAT_CAPABILITIES = (
    "chat_completions",
    "json_object_response",
    "model_list",
    "bearer_auth",
)
DEEPSEEK_CHAT_CAPABILITIES = (
    "chat_completions",
    "json_object_response",
    "disable_thinking",
    "model_list",
    "bearer_auth",
)
ANTHROPIC_MESSAGES_CAPABILITIES = (
    "messages",
    "model_list",
    "x_api_key_auth",
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
    # Non-secret live-call contract metadata for UI/pilot planning. Adapter code
    # still owns the actual HTTP dialect; these fields describe it for callers.
    wire_protocol: str = WIRE_OPENAI_CHAT_COMPLETIONS
    capabilities: tuple[str, ...] = ()
    default_timeout_seconds: int = 30


def _openai_compatible_spec(
    provider_id: str,
    label: str,
    default_base_url: str,
    default_models: tuple[str, ...],
) -> ProviderSpec:
    return ProviderSpec(
        provider_id=provider_id,
        label=label,
        provider_cls=OpenAIProvider,
        default_base_url=default_base_url,
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=default_models,
        wire_protocol=WIRE_OPENAI_CHAT_COMPLETIONS,
        capabilities=OPENAI_CHAT_CAPABILITIES,
    )


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
        default_models=("deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash", "deepseek-v4-pro"),
        wire_protocol=WIRE_OPENAI_CHAT_COMPLETIONS,
        capabilities=DEEPSEEK_CHAT_CAPABILITIES,
    ),
    "openai": ProviderSpec(
        provider_id="openai",
        label="OpenAI",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.openai.com/v1",
        models_path="/models",
        source_label=OPENAI_PROVIDER_SOURCE_LABEL,
        default_models=("gpt-4o", "gpt-4o-mini"),
        wire_protocol=WIRE_OPENAI_CHAT_COMPLETIONS,
        capabilities=OPENAI_CHAT_CAPABILITIES,
    ),
    "anthropic": ProviderSpec(
        provider_id="anthropic",
        label="Anthropic",
        provider_cls=AnthropicProvider,
        default_base_url="https://api.anthropic.com",
        models_path="/v1/models",
        source_label=ANTHROPIC_PROVIDER_SOURCE_LABEL,
        default_models=("claude-sonnet-4-6", "claude-haiku-4-5-20251001"),
        wire_protocol=WIRE_ANTHROPIC_MESSAGES,
        capabilities=ANTHROPIC_MESSAGES_CAPABILITIES,
    ),
    "openai_compatible": ProviderSpec(
        provider_id="openai_compatible",
        label="OpenAI-compatible (custom)",
        provider_cls=OpenAICompatibleCustomProvider,
        default_base_url="",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        requires_base_url=True,
        wire_protocol=WIRE_OPENAI_CHAT_COMPLETIONS,
        capabilities=OPENAI_CHAT_CAPABILITIES,
    ),
    "zhipu": _openai_compatible_spec(
        "zhipu",
        "Zhipu GLM",
        "https://api.z.ai/api/paas/v4",
        ("glm-4.7", "glm-4.6", "glm-4.5-air"),
    ),
    "moonshot": _openai_compatible_spec(
        "moonshot",
        "Moonshot Kimi",
        "https://api.moonshot.ai/v1",
        ("kimi-k2.6", "moonshot-v1-8k"),
    ),
    "qwen": _openai_compatible_spec(
        "qwen",
        "Alibaba Qwen",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ("qwen3-max", "qwen-plus", "qwen-flash", "qwen3-coder-plus"),
    ),
    "minimax": _openai_compatible_spec(
        "minimax",
        "MiniMax",
        "https://api.minimax.io/v1",
        ("MiniMax-M3", "MiniMax-Text-01"),
    ),
    "siliconflow": _openai_compatible_spec(
        "siliconflow",
        "SiliconFlow",
        "https://api.siliconflow.cn/v1",
        ("deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct", "Pro/MiniMaxAI/MiniMax-M2.7"),
    ),
    "xai": _openai_compatible_spec(
        "xai",
        "xAI Grok",
        "https://api.x.ai/v1",
        ("grok-4.3", "grok-4"),
    ),
    "gemini": _openai_compatible_spec(
        "gemini",
        "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        ("gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"),
    ),
    "modelscope": _openai_compatible_spec(
        "modelscope",
        "ModelScope",
        "https://api-inference.modelscope.cn/v1",
        ("Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3", "ZhipuAI/GLM-5.1"),
    ),
    "openrouter": _openai_compatible_spec(
        "openrouter",
        "OpenRouter",
        "https://openrouter.ai/api/v1",
        ("~openai/gpt-latest", "~anthropic/claude-sonnet-latest", "openrouter/auto"),
    ),
    # cc-switch e606adf Codex presets explicitly marked apiFormat="openai_chat".
    # Responses-only, Anthropic, Gemini-native, OAuth, and subscription-routing
    # presets are intentionally not enabled until matching adapters exist here.
    "volcengine_ark": _openai_compatible_spec(
        "volcengine_ark",
        "Volcengine Ark Agent Plan",
        "https://ark.cn-beijing.volces.com/api/coding/v3",
        ("ark-code-latest",),
    ),
    "byteplus_ark": _openai_compatible_spec(
        "byteplus_ark",
        "BytePlus ModelArk",
        "https://ark.ap-southeast.bytepluses.com/api/coding/v3",
        ("ark-code-latest",),
    ),
    "zhipu_coding": _openai_compatible_spec(
        "zhipu_coding",
        "Zhipu GLM Coding",
        "https://open.bigmodel.cn/api/coding/paas/v4",
        ("glm-5.2",),
    ),
    "zhipu_global_coding": _openai_compatible_spec(
        "zhipu_global_coding",
        "Zhipu GLM Global Coding",
        "https://api.z.ai/api/coding/paas/v4",
        ("glm-5.2",),
    ),
    "qianfan_coding": _openai_compatible_spec(
        "qianfan_coding",
        "Baidu Qianfan Coding Plan",
        "https://qianfan.baidubce.com/v2/coding",
        ("qianfan-code-latest",),
    ),
    "moonshot_cn": _openai_compatible_spec(
        "moonshot_cn",
        "Moonshot Kimi China",
        "https://api.moonshot.cn/v1",
        ("kimi-k2.7-code",),
    ),
    "kimi_coding": _openai_compatible_spec(
        "kimi_coding",
        "Kimi For Coding",
        "https://api.kimi.com/coding/v1",
        ("kimi-for-coding",),
    ),
    "stepfun": _openai_compatible_spec(
        "stepfun",
        "StepFun",
        "https://api.stepfun.com/step_plan/v1",
        ("step-3.7-flash", "step-3.5-flash-2603", "step-3.5-flash"),
    ),
    "stepfun_global": _openai_compatible_spec(
        "stepfun_global",
        "StepFun Global",
        "https://api.stepfun.ai/step_plan/v1",
        ("step-3.7-flash", "step-3.5-flash-2603", "step-3.5-flash"),
    ),
    "bailing": _openai_compatible_spec(
        "bailing",
        "BaiLing",
        "https://api.tbox.cn/api/llm/v1",
        ("Ling-2.6-1T",),
    ),
    "siliconflow_global": _openai_compatible_spec(
        "siliconflow_global",
        "SiliconFlow Global",
        "https://api.siliconflow.com/v1",
        ("MiniMaxAI/MiniMax-M2.7",),
    ),
    "novita": _openai_compatible_spec(
        "novita",
        "Novita AI",
        "https://api.novita.ai/openai/v1",
        ("zai-org/glm-5.1",),
    ),
    "nvidia_nim": _openai_compatible_spec(
        "nvidia_nim",
        "NVIDIA NIM",
        "https://integrate.api.nvidia.com/v1",
        ("moonshotai/kimi-k2.5",),
    ),
    "opencode_go": _openai_compatible_spec(
        "opencode_go",
        "OpenCode Go",
        "https://opencode.ai/zen/go/v1",
        ("glm-5.2", "glm-5.1", "kimi-k2.7-code", "deepseek-v4-pro", "deepseek-v4-flash", "mimo-v2.5-pro"),
    ),
    "atlascloud": _openai_compatible_spec(
        "atlascloud",
        "AtlasCloud",
        "https://api.atlascloud.ai/v1",
        ("zai-org/glm-5.1",),
    ),
}


def _effective_base_url(spec: ProviderSpec, base_url: str) -> str:
    return (base_url or spec.default_base_url).rstrip("/")


def _config_with_registry_defaults(
    spec: ProviderSpec,
    config: ChatProviderConfig,
) -> ChatProviderConfig:
    base_url = config.base_url or spec.default_base_url
    timeout_seconds = config.timeout_seconds
    if timeout_seconds == CHAT_PROVIDER_CONFIG_DEFAULT_TIMEOUT_SECONDS:
        timeout_seconds = spec.default_timeout_seconds
    if base_url == config.base_url and timeout_seconds == config.timeout_seconds:
        return config
    return dataclasses.replace(
        config,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )


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
    config = _config_with_registry_defaults(spec, config)
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
    config = _config_with_registry_defaults(spec, config)
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
            "models_path": spec.models_path,
            "requires_base_url": spec.requires_base_url,
            "default_models": list(spec.default_models),
            "wire_protocol": spec.wire_protocol,
            "capabilities": list(spec.capabilities),
            "default_timeout_seconds": spec.default_timeout_seconds,
        }
        for spec in PROVIDER_REGISTRY.values()
    ]
