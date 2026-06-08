"""DeepSeek provider — now a thin DeepSeek-dialect subclass of the shared
``OpenAICompatibleProvider`` (P2-B-3). Public API is unchanged:
``DeepSeekProviderConfig`` and ``DeepSeekProvider(config, transport=None)`` keep
their names, fields, and behavior (existing tests are the refactor's safety net).
The DeepSeek dialect = OpenAI-compatible ``/chat/completions`` PLUS the two
DeepSeek-only payload keys (``thinking``, ``response_format``)."""

from __future__ import annotations

from dataclasses import dataclass

from werewolf_eval.llm_providers import (  # re-exported for back-compat
    OpenAICompatibleProvider,
    Transport,
    _default_transport,
)
from werewolf_eval.provider_contract import DEEPSEEK_PROVIDER_SOURCE_LABEL

__all__ = [
    "DeepSeekProvider",
    "DeepSeekProviderConfig",
    "Transport",
    "_default_transport",
]


@dataclass(frozen=True)
class DeepSeekProviderConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: int = 30
    max_tokens: int = 256
    max_requests: int = 11
    # P2-B-3 per-seat knobs (additive, no-op defaults).
    persona_prompt: str = ""
    temperature: float | None = None


class DeepSeekProvider(OpenAICompatibleProvider):
    PROVIDER_NAME = "deepseek"
    SOURCE_LABEL = DEEPSEEK_PROVIDER_SOURCE_LABEL
    INCLUDE_THINKING = True
    INCLUDE_RESPONSE_FORMAT = True

    def __init__(
        self,
        config: DeepSeekProviderConfig,
        transport: Transport | None = None,
    ) -> None:
        super().__init__(config, transport=transport)
