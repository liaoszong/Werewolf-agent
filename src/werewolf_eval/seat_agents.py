"""P2-B-3 keystone: build per-seat ProviderAgents from a resolved profile.

Each seat gets its OWN provider instance, built from that seat's provider/model
and the session credential for that provider, with the seat's prompt threaded in
as the persona and its temperature/max_tokens applied. Because the per-seat config
lives on the provider instance, ALL three engine call paths — action (decide),
speech (decide), and the witch direct ``agent.provider.respond`` — automatically
use the right per-seat persona/temperature without any engine change.

This is what makes "wolf-1 aggressive on DeepSeek, wolf-2 conservative on OpenAI"
real. The returned dict plugs straight into the runner's existing seam via a
``pid -> agent`` factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from werewolf_eval.llm_providers import ChatProviderConfig
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.provider_registry import build_provider

DEFAULT_MAX_TOKENS = 256
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ProviderCredential:
    """A session credential for one provider. ``base_url`` empty → the registry
    default is used (custom providers must supply one)."""

    key: str
    base_url: str = ""


def build_seat_agents(
    resolved_seats: list[dict],
    credentials: Mapping[str, ProviderCredential],
    *,
    max_requests: int,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    default_max_tokens: int = DEFAULT_MAX_TOKENS,
    transport=None,
) -> dict[str, ProviderAgent]:
    """Return ``{player_id: ProviderAgent}`` — one independent provider per seat.

    Raises ``ValueError`` for any seat whose provider has no credential (no silent
    fallback). ``max_requests`` is applied to EVERY per-seat provider as a safe
    ceiling; the real global cap is the engine's EmergentBudget, so a per-seat cap
    never trips first."""
    agents: dict[str, ProviderAgent] = {}
    for seat in resolved_seats:
        pid = seat["player_id"]
        provider_id = seat["provider"]
        cred = credentials.get(provider_id)
        if cred is None or not cred.key:
            raise ValueError(
                f"no credential for provider {provider_id!r} (seat {pid})"
            )
        seat_max_tokens = seat.get("max_tokens")
        config = ChatProviderConfig(
            api_key=cred.key,
            base_url=cred.base_url,
            model=seat["model"],
            timeout_seconds=timeout_seconds,
            max_tokens=seat_max_tokens if seat_max_tokens is not None else default_max_tokens,
            max_requests=max_requests,
            persona_prompt=seat.get("prompt") or "",
            temperature=seat.get("temperature"),
        )
        provider = build_provider(provider_id, config, transport=transport)
        agents[pid] = ProviderAgent(pid, provider)
    return agents
