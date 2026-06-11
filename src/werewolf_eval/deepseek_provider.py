"""DeepSeek provider — now a thin DeepSeek-dialect subclass of the shared
``OpenAICompatibleProvider`` (P2-B-3). Public API is unchanged:
``DeepSeekProviderConfig`` and ``DeepSeekProvider(config, transport=None)`` keep
their names, fields, and behavior (existing tests are the refactor's safety net).
The DeepSeek dialect = OpenAI-compatible ``/chat/completions`` PLUS the two
DeepSeek-only payload keys (``thinking``, ``response_format``)."""

from __future__ import annotations

from dataclasses import dataclass

from werewolf_eval.llm_providers import (  # re-exported for back-compat
    ChatProviderConfig,
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
class DeepSeekProviderConfig(ChatProviderConfig):
    """DeepSeek defaults over the shared ``ChatProviderConfig`` shape (health-check
    D-3). Field names/order/behavior unchanged — existing tests are the safety net;
    being a subclass lets ``provider_registry.build_provider`` accept it directly."""

    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"


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
