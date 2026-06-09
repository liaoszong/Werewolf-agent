"""G3-1 live DeepSeek launcher.

A thin wiring layer: builds one shared ``DeepSeekProvider`` (server-side env
key) and delegates a profile launch to the existing spine consensus runner
verbatim.  It adds zero engine logic; its only post-run work is to read the
``failure-audit.json`` it caused and classify the run-failure exit code so the
observer can map it to a key-free run-status reason (A7):

* runner exit 0                                   -> 0
* runner nonzero + budget exhaustion              -> 3 (budget_exhausted)
* runner nonzero otherwise                        -> 2 (provider_failure)

Budget exhaustion is detected by a single shared predicate
(``_failure_is_budget_exhausted``): the structured ``kind == "budget_exhausted"``
field OR either reason wording ("budget exhausted" / "budget exceeded"), so the
legacy and emergent exit-code paths agree.

The API key lives only inside the provider config + Authorization header; it is
never logged, traced, or written to any artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Mapping

from werewolf_eval.deepseek_provider import DeepSeekProvider, DeepSeekProviderConfig
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.run_deepseek_consensus_game import (
    ProviderFactory,
    run_deepseek_consensus_game_with_provider_factory,
)
from werewolf_eval.run_emergent_deepseek_game import (
    _deepseek_factory as _emergent_deepseek_factory,
    run_emergent_deepseek_game,
)
from werewolf_eval.seat_agents import ProviderCredential, build_seat_agents

RunLauncher = Callable[[str, Path], int]

DEFAULT_MAX_LIVE_REQUESTS = 32
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_DAY_ROUNDS = 3


def build_deepseek_provider_config(
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int,
    max_requests: int = DEFAULT_MAX_LIVE_REQUESTS,
) -> DeepSeekProviderConfig:
    """Build the shared provider config.  ``max_requests`` defaults to 32 — the
    server-override-only live budget (A7); an explicit value overrides it."""
    return DeepSeekProviderConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        max_requests=max_requests,
    )


def _default_provider_factory(config: DeepSeekProviderConfig) -> ProviderFactory:
    """One shared ``DeepSeekProvider`` across all seats so ``max_requests`` is a
    true global budget for the whole game (mirrors ``_build_deepseek_agent``)."""
    shared_provider = DeepSeekProvider(config)

    def factory(player_id: str) -> ProviderAgent:
        return ProviderAgent(player_id, shared_provider)

    return factory


def _failure_is_budget_exhausted(failure: Any) -> bool:
    """Single source of truth for "this failure is a request-budget exhaustion".

    Detects it three ways so the two live exit-code paths (legacy single-provider
    and emergent/multi-provider) agree on the observer-facing 0/2/3 contract:
    - the STRUCTURED field ``kind == "budget_exhausted"`` (emergent engine,
      ``emergent_engine.py``); this is the authoritative signal.
    - the legacy reason wording ``"budget exceeded"`` (``llm_providers`` raises
      ``"request budget exceeded"``, which ``provider_agent`` wraps as a
      ``kind="timeout"`` failure — so the budget signal survives only in the
      reason string, not the kind).
    - the emergent reason wording ``"budget exhausted"`` (note: *exhausted*, not
      *exceeded*) — guards against any path that records the wording without the
      structured kind. A substring-only detector keyed on "budget exceeded" alone
      silently misclassified every emergent budget failure as a generic failure.
    """
    if not isinstance(failure, dict):
        return False
    if failure.get("kind") == "budget_exhausted":
        return True
    reason = str(failure.get("reason", ""))
    return "budget exhausted" in reason or "budget exceeded" in reason


def _classify_failure(run_dir: Path) -> int:
    """Read the launcher's own ``failure-audit.json`` and return 3 when the run
    failed because the request budget was exhausted, else 2."""
    audit_path = run_dir / "failure-audit.json"
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 2
    if not isinstance(audit, dict):
        return 2
    if any(_failure_is_budget_exhausted(f) for f in audit.get("failures", [])):
        return 3
    return 2


def build_deepseek_launcher(
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int,
    max_requests: int = DEFAULT_MAX_LIVE_REQUESTS,
    provider_factory: ProviderFactory | None = None,
) -> RunLauncher:
    """Return a ``RunLauncher`` that runs one live consensus game with the full
    runtime spine.  ``provider_factory`` is injectable so tests pass a fake (no
    real transport); when ``None`` a default one-shared-``DeepSeekProvider``
    factory is built from the config."""
    if provider_factory is None:
        config = build_deepseek_provider_config(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            max_requests=max_requests,
        )
        provider_factory = _default_provider_factory(config)

    factory = provider_factory

    def _launcher(run_id: str, run_dir: Path) -> int:
        rdir = Path(run_dir)
        code = run_deepseek_consensus_game_with_provider_factory(
            game_id=run_id,
            out_dir=rdir,
            provider_factory=factory,
            write_runtime_spine=True,
            model=model,  # G3-3: record the real deepseek model in the manifest
        )
        if code == 0:
            return 0
        return _classify_failure(rdir)

    return _launcher


# ---------------------------------------------------------------------------
# P2 observer bridge — emergent live launcher (Adapter B)
# ---------------------------------------------------------------------------


def _audit_is_budget_exhausted(audit_path: Path) -> bool:
    """Return True when the emergent failure audit records a budget-exhausted run.

    The emergent engine serializes budget exhaustion as a STRUCTURED failure with
    ``kind == "budget_exhausted"`` (the reason string reads "budget exhausted:
    N/M requests"). Detection is shared with ``_classify_failure`` via
    ``_failure_is_budget_exhausted`` so both exit-code paths agree. Any read/parse
    error is treated as not-budget (conservative → exit 2), never raised."""
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(audit, dict):
        return False
    return any(_failure_is_budget_exhausted(f) for f in audit.get("failures", []))


def build_emergent_deepseek_launcher(
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int,
    max_requests: int = DEFAULT_MAX_LIVE_REQUESTS,
    max_day_rounds: int = DEFAULT_MAX_DAY_ROUNDS,
    provider_factory: ProviderFactory | None = None,
) -> RunLauncher:
    """Return a ``RunLauncher`` that drives the EmergentGameEngine over live
    DeepSeek with the full observer spine + provider-turns evidence.

    Mirrors ``build_deepseek_launcher`` but for the emergent runtime. The runner
    fails closed with exit 2 on ANY error, so the closure re-reads the
    ``failure-audit.json`` it caused and translates a budget-exhausted run to
    exit 3 — the only code the observer maps to ``budget_exhausted`` (others →
    ``provider_failure``). ``provider_factory`` is injectable so offline tests
    pass a fake-transport factory (no network); the old scripted launcher above
    is retained for fallback."""
    if provider_factory is None:
        provider_factory = _emergent_deepseek_factory(
            api_key, base_url, model, timeout_seconds, max_tokens, max_requests
        )

    factory = provider_factory

    def _launcher(run_id: str, run_dir: Path) -> int:
        rdir = Path(run_dir)
        code = run_emergent_deepseek_game(
            game_id=run_id,
            out_dir=rdir,
            provider_factory=factory,
            model=model,
            max_requests_per_game=max_requests,
            max_day_rounds=max_day_rounds,
        )
        if code == 0:
            return 0
        if _audit_is_budget_exhausted(rdir / "failure-audit.json"):
            return 3
        return 2

    return _launcher


def build_multi_provider_launcher(
    *,
    resolved_seats: list[dict],
    credentials: Mapping[str, ProviderCredential],
    max_requests: int = DEFAULT_MAX_LIVE_REQUESTS,
    max_day_rounds: int = DEFAULT_MAX_DAY_ROUNDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    default_max_tokens: int = 256,
    transport=None,
    runner: Callable[..., int] = run_emergent_deepseek_game,
) -> RunLauncher:
    """P2-B-3: a ``RunLauncher`` that drives the emergent engine with PER-SEAT
    providers — each seat uses its own provider/model/persona/temperature, so a
    single game can mix DeepSeek + OpenAI + Anthropic.

    Seat agents are built fresh inside the closure (the launcher is reusable). A
    missing per-seat credential raises ``ValueError`` (no silent fallback; the
    server gate in P2-B-4 rejects with 403 before reaching here). ``runner`` is
    injectable for offline tests; the budget-exhausted → exit 3 mapping mirrors
    the single-provider launcher."""
    def _launcher(run_id: str, run_dir: Path) -> int:
        rdir = Path(run_dir)
        agents = build_seat_agents(
            resolved_seats,
            credentials,
            max_requests=max_requests,
            timeout_seconds=timeout_seconds,
            default_max_tokens=default_max_tokens,
            transport=transport,
        )
        code = runner(
            game_id=run_id,
            out_dir=rdir,
            provider_factory=lambda pid: agents[pid],
            model="",  # per-seat models live on each provider; no single model
            max_requests_per_game=max_requests,
            max_day_rounds=max_day_rounds,
        )
        if code == 0:
            return 0
        if _audit_is_budget_exhausted(rdir / "failure-audit.json"):
            return 3
        return 2

    return _launcher
