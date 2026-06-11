from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

from werewolf_eval.artifacts import collect_provider_trace, write_json
from werewolf_eval.deepseek_provider import DeepSeekProvider, DeepSeekProviderConfig
from werewolf_eval.game_engine import GameEngine, build_default_config
from werewolf_eval.provider_agent import ProviderActionError, ProviderAgent
from werewolf_eval.provider_contract import (
    DEEPSEEK_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    provider_failure_to_dict,
    provider_trace_to_dict,
    ProviderTrace,
)
from werewolf_eval.runtime_events import redact_secret_values


def _collect_trace(
    game_id: str,
    agents: dict[str, object],
    wolf_agent: object,
    failures: list[ProviderFailure],
) -> ProviderTrace:
    # All agents share one provider instance (global max_requests budget), so
    # request_id de-dup is load-bearing here, not just belt-and-suspenders.
    return collect_provider_trace(
        game_id,
        list(agents.values()) + [wolf_agent],
        provider_name="deepseek",
        source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL,
        failures=failures,
    )


ProviderFactory = Callable[[str], ProviderAgent]


def run_deepseek_game_with_provider_factory(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory: ProviderFactory,
) -> int:
    agents = {pid: provider_factory(pid) for pid in ["p3", "p4", "p5", "p6"]}
    wolf_agent = provider_factory("wolf_team")

    engine = GameEngine.from_config(
        build_default_config(game_id=game_id),
        agents=agents,
        wolf_agent=wolf_agent,
        source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL,
    )

    failures: list[ProviderFailure] = []

    try:
        outputs = engine.run(mode="g1b_default")
    except ProviderActionError as exc:
        failures.append(exc.failure)
        trace = _collect_trace(game_id, agents, wolf_agent, failures)
        trace_payload = redact_secret_values(provider_trace_to_dict(trace))
        write_json(str(out_dir / "provider-trace.json"), trace_payload)

        failure_audit = {
            "game_id": game_id,
            "source_label": DEEPSEEK_PROVIDER_SOURCE_LABEL,
            "failures": [provider_failure_to_dict(f) for f in failures],
        }
        write_json(str(out_dir / "failure-audit.json"), failure_audit)

        print(f"deepseek_provider_game_id={game_id}")
        print(f"source_label={DEEPSEEK_PROVIDER_SOURCE_LABEL}")
        print(f"provider_requests={len(trace.requests)}")
        print(f"provider_responses={len(trace.responses)}")
        print(f"provider_failures={len(failures)}")
        print(f"game_log=not_written")
        print(f"decision_log=not_written")
        print(f"provider_trace=written")
        print(f"failure_audit=written")
        return 2

    write_json(str(out_dir / "game-log.json"), outputs.game_log)
    write_json(str(out_dir / "decision-log.json"), outputs.decision_log)

    trace = _collect_trace(game_id, agents, wolf_agent, [])
    trace_payload = redact_secret_values(provider_trace_to_dict(trace))
    write_json(str(out_dir / "provider-trace.json"), trace_payload)

    failure_audit = {
        "game_id": game_id,
        "source_label": DEEPSEEK_PROVIDER_SOURCE_LABEL,
        "failures": [],
    }
    write_json(str(out_dir / "failure-audit.json"), failure_audit)

    print(f"deepseek_provider_game_id={game_id}")
    print(f"source_label={DEEPSEEK_PROVIDER_SOURCE_LABEL}")
    print(f"provider_requests={len(trace.requests)}")
    print(f"provider_responses={len(trace.responses)}")
    print(f"provider_failures=0")
    print(f"game_log=written")
    print(f"decision_log=written")
    print(f"provider_trace=written")
    print(f"failure_audit=written")
    return 0


def _build_deepseek_agent(api_key: str, base_url: str, model: str, timeout_seconds: int, max_tokens: int, max_requests: int) -> ProviderFactory:
    config = DeepSeekProviderConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        max_requests=max_requests,
    )
    # Share one provider instance across all agents so max_requests is a
    # true global budget for the entire game run, not a per-instance cap.
    shared_provider = DeepSeekProvider(config)

    def factory(player_id: str) -> ProviderAgent:
        return ProviderAgent(player_id, shared_provider)

    return factory


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DeepSeek single-game smoke.")
    parser.add_argument("--game-id", default="g1e_deepseek_smoke")
    parser.add_argument("--out-dir", default=".tmp/g1e-deepseek-provider-smoke")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--max-tokens-per-request", type=int, default=256)
    parser.add_argument("--max-provider-requests", type=int, default=11)
    parser.add_argument("--allow-live-api", action="store_true", default=False)
    args = parser.parse_args()

    if not args.allow_live_api:
        print("live_api=disabled")
        print("game_log=not_written")
        print("decision_log=not_written")
        return 1

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        print(f"missing {args.api_key_env}", file=sys.stderr)
        print("game_log=not_written")
        print("decision_log=not_written")
        return 1

    factory = _build_deepseek_agent(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        max_tokens=args.max_tokens_per_request,
        max_requests=args.max_provider_requests,
    )

    return run_deepseek_game_with_provider_factory(
        game_id=args.game_id,
        out_dir=Path(args.out_dir),
        provider_factory=factory,
    )


if __name__ == "__main__":
    raise SystemExit(main())
