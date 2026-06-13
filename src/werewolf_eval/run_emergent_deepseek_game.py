"""P2-A-2 live runner: drive the emergent engine via the real DeepSeek provider.

Opt-in (`--allow-live-api`), dev-key/server-side. Writes the four standard logs
PLUS the MANDATORY runtime spine (events.jsonl, snapshots/, prompt-manifest.json
with the REAL model) PLUS a provider-turns summary (provider_result_kind stats +
token usage) that the smoke uses for the live-success gate. Fail-closed: a
round-cap / budget-exhausted outcome writes only the failure audit + spine and
exits non-zero — never a complete game log.

The provider call is server-side only; the key lives only in the process env and
is never written to any artifact. A `provider_factory` seam lets offline tests
inject a fake-transport DeepSeek provider (no network).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

from werewolf_eval.artifacts import collect_provider_trace, write_json
from werewolf_eval.deepseek_provider import DeepSeekProviderConfig
from werewolf_eval.provider_registry import build_provider
from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.prompt_renderers import get_renderer
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.provider_contract import (
    DEEPSEEK_PROVIDER_SOURCE_LABEL,
    MIXED_PROVIDER_SOURCE_LABEL,
    provider_trace_to_dict,
)
from werewolf_eval.evaluation_versions import SCORING_VERSION, evaluation_bucket
from werewolf_eval.runtime_events import RuntimeEventWriter, build_prompt_manifest, redact_secret_values

ProviderFactory = Callable[[str], ProviderAgent]
PLAYER_IDS = ["p1", "p2", "p3", "p4", "p5", "p6"]


def _provider_identity(agents: dict[str, ProviderAgent]) -> tuple[str, str]:
    """Derive the run-level provider_name + source_label from the seat providers.
    Uniform → that provider's name/label; heterogeneous → "mixed" / the mixed
    label. ``getattr`` fallbacks keep legacy/fake providers (which lack the
    class attrs) reporting exactly as before ("deepseek" / DeepSeek label)."""
    names = {getattr(a.provider, "PROVIDER_NAME", "deepseek") for a in agents.values()}
    labels = {
        getattr(a.provider, "SOURCE_LABEL", DEEPSEEK_PROVIDER_SOURCE_LABEL)
        for a in agents.values()
    }
    name = next(iter(names)) if len(names) == 1 else "mixed"
    # Heterogeneous EITHER by name (e.g. moonshot+qwen, which share the compatible
    # label) or by label → the run-level label is the mixed label. Honest.
    if len(names) == 1 and len(labels) == 1:
        label = next(iter(labels))
    else:
        label = MIXED_PROVIDER_SOURCE_LABEL
    return name, label


def _seat_manifest_agents(agents: dict[str, ProviderAgent], fallback_model: str) -> list[dict]:
    """Per-seat manifest rows. ``provider.model or fallback_model`` preserves the
    legacy single-model manifest (the fake provider's model is None) while giving
    real per-seat models under multi-provider; persona → per-seat prompt_hash."""
    rows: list[dict] = []
    for pid in PLAYER_IDS:
        if pid not in agents:
            continue
        provider = agents[pid].provider
        rows.append({
            "player_id": pid,
            "provider": getattr(provider, "PROVIDER_NAME", "deepseek"),
            "model": getattr(provider, "model", None) or fallback_model,
            "prompt": getattr(provider, "persona", "") or "",
        })
    return rows


def _collect_trace(
    game_id: str,
    agents: dict[str, ProviderAgent],
    *,
    provider_name: str,
    source_label: str,
) -> dict:
    return provider_trace_to_dict(
        collect_provider_trace(
            game_id,
            agents.values(),
            provider_name=provider_name,
            source_label=source_label,
        )
    )


def _provider_turns_summary(turns: list[dict]) -> dict:
    by_kind: dict[str, int] = {}
    # B5 closeout (B34-03): honest token naming. Each turn's token_usage carries
    # prompt_tokens, completion_tokens, total_tokens. We sum them separately so
    # cost calculations use the correct口径 (completion_tokens for output pricing,
    # prompt_tokens for input pricing). Scribe turns (scaffold, not a seat) are
    # tracked separately so per-seat cost is not inflated by scaffold spend.
    player_prompt_tokens = 0
    player_completion_tokens = 0
    player_total_tokens = 0
    scaffold_prompt_tokens = 0
    scaffold_completion_tokens = 0
    scaffold_total_tokens = 0
    for t in turns:
        by_kind[t["kind"]] = by_kind.get(t["kind"], 0) + 1
        usage = t.get("token_usage")
        if not isinstance(usage, dict):
            continue
        prompt = int(usage.get("prompt_tokens", 0))
        completion = int(usage.get("completion_tokens", 0))
        total = int(usage.get("total_tokens", 0))
        if t.get("actor") == "scribe":
            scaffold_prompt_tokens += prompt
            scaffold_completion_tokens += completion
            scaffold_total_tokens += total
        else:
            player_prompt_tokens += prompt
            player_completion_tokens += completion
            player_total_tokens += total
    live_requested = sum(1 for t in turns if t.get("live_requested"))
    live_success = by_kind.get("live_success", 0)
    return {
        "live_requested_actions": live_requested,
        "live_success_actions": live_success,
        "live_success_rate": (live_success / live_requested) if live_requested else 1.0,
        "by_provider_result_kind": by_kind,
        # Player (seat) token sums — exclude scribe (scaffold).
        "player_prompt_tokens": player_prompt_tokens,
        "player_completion_tokens": player_completion_tokens,
        "player_total_tokens": player_total_tokens,
        # Scaffold (scribe) token sums — separate so per-seat cost is honest.
        "scaffold_prompt_tokens": scaffold_prompt_tokens,
        "scaffold_completion_tokens": scaffold_completion_tokens,
        "scaffold_total_tokens": scaffold_total_tokens,
        # Legacy alias for backward compat (sum of player + scaffold total).
        "total_tokens": player_total_tokens + scaffold_total_tokens,
        "player_requests": live_requested,
        "scaffold_requests": sum(1 for t in turns if t.get("response_kind") == "scaffold"),
        "turns": turns,
    }


def run_emergent_deepseek_game(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory: ProviderFactory,
    model: str,
    seed: int = 0,
    max_requests_per_game: int = 64,
    max_day_rounds: int = 3,
    source_label: str | None = None,
    seat_roles: dict[str, str] | None = None,
    prompt_version: str = "prompt_v1",
    scaffold_provider_factory=None,
) -> int:
    # Fail-loud before any side effects (writer/engine construction).
    renderer = get_renderer(prompt_version)
    config = build_emergent_config(game_id=game_id, seat_roles=seat_roles)
    board_roles = {p.role for p in config.players}
    if "guard" in board_roles and not renderer.requires_scaffold:
        raise ValueError(
            f"guard board requires a scaffold-based renderer (prompt_v3+) that carries "
            f"the guard rules card; prompt_version={prompt_version!r} has none — no rules "
            f"card / empty guard persona would degrade the live game into invalid-action "
            f"fallback (B12-04). Set prompt_version to prompt_v3."
        )
    scaffold_agent = None
    if renderer.requires_scaffold:
        if scaffold_provider_factory is None:
            raise ValueError(f"{prompt_version} requires scaffold_provider_factory (scribe provider)")
        scaffold_agent = scaffold_provider_factory()
    writer = RuntimeEventWriter(run_id=game_id, out_dir=out_dir)
    agents = {pid: provider_factory(pid) for pid in PLAYER_IDS}
    # P2-B-3: run-level identity derived from the seat providers (uniform or mixed);
    # an explicit source_label overrides. Legacy/fake paths derive "deepseek".
    provider_name, derived_label = _provider_identity(agents)
    effective_label = source_label or derived_label
    engine = EmergentGameEngine(
        config=config,
        agents=agents,
        seed=seed,
        source_label=effective_label,
        budget=EmergentBudget(max_requests=max_requests_per_game, max_day_rounds=max_day_rounds),
        runtime_events=writer,
        prompt_version=prompt_version,
        scaffold_agent=scaffold_agent,
    )
    outcome = engine.run()

    # provider trace + turns summary are written in BOTH outcomes (live evidence).
    # Include scribe agent in trace collection so actor="scribe" rows are captured;
    # _provider_identity keeps using the original player-only agents (identity unaffected).
    trace_agents = {**agents, "scribe": scaffold_agent} if scaffold_agent is not None else agents
    write_json(
        out_dir / "provider-trace.json",
        redact_secret_values(
            _collect_trace(game_id, trace_agents, provider_name=provider_name, source_label=effective_label)
        ),
    )
    write_json(out_dir / "provider-turns.json", _provider_turns_summary(outcome.provider_turns))

    # MANDATORY spine: prompt-manifest with the REAL per-seat provider/model/persona.
    providers = [a.provider for a in agents.values()]
    manifest = build_prompt_manifest(
        run_id=game_id,
        source_label=effective_label,
        agents=_seat_manifest_agents(agents, model),
        evaluation_bucket=evaluation_bucket(
            rules_version=engine.rules_version,
            prompt_version=engine.prompt_version,
            scoring_version=SCORING_VERSION,
        ),
        # getattr default True is the SAFE-for-live direction but LIES for an
        # undeclared fake provider — every fake provider class MUST declare
        # uses_baseline_prompt=False (pinned in test_evaluation_versions.py).
        prompt_used_by_runtime=any(
            getattr(p, "uses_baseline_prompt", True) for p in providers
        ),
    )
    manifest["secrets_redacted"] = True
    if scaffold_agent is not None:
        manifest["scaffold_model"] = getattr(scaffold_agent.provider, "model", None)
    writer.write_prompt_manifest(manifest)

    if outcome.completed:
        write_json(out_dir / "game-log.json", outcome.game_log)
        write_json(out_dir / "decision-log.json", outcome.decision_log)
        write_json(out_dir / "consensus-log.json", outcome.consensus_log)
        write_json(out_dir / "failure-audit.json", outcome.failure_audit)
        print(f"emergent_deepseek_game_id={game_id}")
        print(f"status=completed")
        print(f"winner={outcome.game_log['result']['winner']}")
        print(f"live_requested_actions={outcome.live_requested_actions}")
        print(f"live_success_actions={outcome.live_success_actions}")
        print(f"live_success_rate={outcome.live_success_rate:.3f}")
        print("game_log=written")
        return 0

    # fail-closed: no complete game log
    write_json(out_dir / "failure-audit.json", outcome.failure_audit)
    print(f"emergent_deepseek_game_id={game_id}")
    print(f"status=failed")
    print(f"end_condition={outcome.end_condition}")
    print(f"live_requested_actions={outcome.live_requested_actions}")
    print(f"live_success_actions={outcome.live_success_actions}")
    print("game_log=not_written")
    return 2


def _deepseek_factory(api_key: str, base_url: str, model: str, timeout_seconds: int, max_tokens: int, max_requests: int) -> ProviderFactory:
    config = DeepSeekProviderConfig(
        api_key=api_key, base_url=base_url, model=model,
        timeout_seconds=timeout_seconds, max_tokens=max_tokens, max_requests=max_requests,
    )
    shared = build_provider("deepseek", config)

    def factory(pid: str) -> ProviderAgent:
        return ProviderAgent(pid, shared)

    return factory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an emergent DeepSeek live game (opt-in).")
    parser.add_argument("--game-id", default="p2a2_emergent_live")
    parser.add_argument("--out-dir", default=".tmp/p2a2-emergent-live")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--max-tokens-per-request", type=int, default=256)
    parser.add_argument("--max-requests-per-game", type=int, default=64)
    parser.add_argument("--max-day-rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--allow-live-api", action="store_true", default=False)
    args = parser.parse_args(argv)

    if not args.allow_live_api:
        print("live_api=disabled")
        print("game_log=not_written")
        return 1

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        print(f"missing {args.api_key_env}", file=sys.stderr)
        print("game_log=not_written")
        return 1

    factory = _deepseek_factory(
        api_key=api_key, base_url=args.base_url, model=args.model,
        timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens_per_request,
        max_requests=args.max_requests_per_game,
    )
    return run_emergent_deepseek_game(
        game_id=args.game_id, out_dir=Path(args.out_dir), provider_factory=factory,
        model=args.model, seed=args.seed,
        max_requests_per_game=args.max_requests_per_game, max_day_rounds=args.max_day_rounds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
