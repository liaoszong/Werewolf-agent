"""Shared artifact-write + provider-trace assembly for run_*.py entrypoints.

Single source of truth for two contracts previously copy-pasted across the
run_* launchers (health check 2026-06-08, E-2/E-3):

- write_json: the artifact-write contract (mkdir parents, UTF-8,
  ensure_ascii=False, indent=2, trailing newline) — the natural enforcement
  point for the R-08 write discipline.
- collect_provider_trace: roll up per-seat provider requests/responses into
  one ProviderTrace, de-duplicated by request_id. Each seat wraps its own
  provider instance, so ids never collide across seats and the de-dup is
  belt-and-suspenders; dedup=False preserves the historical
  run_fake_provider_game no-dedup behavior verbatim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.provider_contract import (
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTrace,
)


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def collect_provider_trace(
    game_id: str,
    agents: Iterable[Any],
    *,
    provider_name: str,
    source_label: str,
    failures: list[ProviderFailure] | None = None,
    dedup: bool = True,
) -> ProviderTrace:
    seen_req: set[str] = set()
    seen_resp: set[str] = set()
    requests: list[ProviderRequest] = []
    responses: list[ProviderResponse] = []
    for agent in agents:
        if not isinstance(agent, ProviderAgent):
            continue
        provider = agent.provider
        for req in getattr(provider, "requests", []):
            if dedup and req.request_id in seen_req:
                continue
            seen_req.add(req.request_id)
            requests.append(req)
        for resp in getattr(provider, "responses", []):
            if dedup and resp.request_id in seen_resp:
                continue
            seen_resp.add(resp.request_id)
            responses.append(resp)
    return ProviderTrace(
        game_id=game_id,
        provider_name=provider_name,
        source_label=source_label,
        requests=requests,
        responses=responses,
        failures=failures if failures is not None else [],
    )
