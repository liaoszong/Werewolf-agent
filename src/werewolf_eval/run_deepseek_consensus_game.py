"""Run DeepSeek consensus smoke for G1f milestone.

Requires a DeepSeek API key. See docs/secrets/api-keys.md for setup."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from werewolf_eval.deepseek_provider import DeepSeekProvider, DeepSeekProviderConfig
from werewolf_eval.game_engine import GameEngine, build_default_config
from werewolf_eval.provider_agent import ProviderActionError, ProviderAgent
from werewolf_eval.provider_contract import (
    DEEPSEEK_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    ProviderRequest,
    provider_failure_to_dict,
    provider_trace_to_dict,
    ProviderTrace,
)
from werewolf_eval.runtime_events import (
    RuntimeEventWriter,
    build_prompt_manifest,
)


def _write_json(path: str, payload: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _collect_trace(
    game_id: str,
    agents: dict[str, object],
    failures: list[ProviderFailure],
) -> ProviderTrace:
    seen_req: set[str] = set()
    seen_resp: set[str] = set()
    all_requests: list[ProviderRequest] = []
    all_responses: list = []

    for agent in list(agents.values()):
        if isinstance(agent, ProviderAgent):
            for req in agent.provider.requests:
                if req.request_id not in seen_req:
                    seen_req.add(req.request_id)
                    all_requests.append(req)
            for resp in agent.provider.responses:
                if resp.request_id not in seen_resp:
                    seen_resp.add(resp.request_id)
                    all_responses.append(resp)

    return ProviderTrace(
        game_id=game_id,
        provider_name="deepseek",
        source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL,
        requests=all_requests,
        responses=all_responses,
        failures=failures,
    )


ProviderFactory = Callable[[str], ProviderAgent]


def run_deepseek_consensus_game_with_provider_factory(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory: ProviderFactory,
    write_runtime_spine: bool = False,
    runtime_source_label: str | None = None,
) -> int:
    writer: RuntimeEventWriter | None = None
    if write_runtime_spine:
        writer = RuntimeEventWriter(run_id=game_id, out_dir=out_dir)

    source_label = runtime_source_label or DEEPSEEK_PROVIDER_SOURCE_LABEL

    def _wrap_factory(pid: str) -> ProviderAgent:
        agent = provider_factory(pid)
        if writer is not None and not hasattr(agent, "_runtime_events"):
            agent = ProviderAgent(
                pid, agent.provider, runtime_events=writer
            )
        elif writer is not None:
            agent._runtime_events = writer
        return agent

    agents = {pid: _wrap_factory(pid) for pid in ["p1", "p2", "p3", "p4", "p5", "p6"]}

    engine = GameEngine.from_config(
        build_default_config(game_id=game_id),
        agents=agents,
        source_label=source_label,
        runtime_events=writer,
    )

    failures: list[ProviderFailure] = []

    try:
        outputs = engine.run(mode="g1f_provider_consensus")
    except ProviderActionError as exc:
        failures.append(exc.failure)
        trace = _collect_trace(game_id, agents, failures)
        trace_payload = provider_trace_to_dict(trace)
        _write_json(str(out_dir / "provider-trace.json"), trace_payload)

        failure_audit = {
            "game_id": game_id,
            "source_label": source_label,
            "failures": [provider_failure_to_dict(f) for f in failures],
        }
        _write_json(str(out_dir / "failure-audit.json"), failure_audit)

        if writer is not None:
            writer.emit(
                "artifact_written",
                round=0, phase="final", actor="system",
                visibility="internal",
                payload={"artifact": "provider-trace.json"},
            )
            writer.emit(
                "artifact_written",
                round=0, phase="final", actor="system",
                visibility="internal",
                payload={"artifact": "failure-audit.json"},
            )
            manifest = build_prompt_manifest(
                run_id=game_id,
                source_label=source_label,
                agents=[
                    {"player_id": pid, "provider": "deepseek", "model": "unknown"}
                    for pid in ["p1", "p2", "p3", "p4", "p5", "p6"]
                ],
            )
            manifest["secrets_redacted"] = True
            writer.write_prompt_manifest(manifest)
            writer.emit(
                "artifact_written",
                round=0, phase="final", actor="system",
                visibility="internal",
                payload={"artifact": "prompt-manifest.json"},
            )
            writer.emit(
                "run_finalized",
                round=0, phase="final", actor="system",
                visibility="internal",
                payload={"status": "failure"},
            )

        print(f"deepseek_consensus_game_id={game_id}")
        print(f"source_label={source_label}")
        print(f"provider_requests={len(trace.requests)}")
        print(f"provider_responses={len(trace.responses)}")
        print(f"provider_failures={len(failures)}")
        print(f"game_log=not_written")
        print(f"decision_log=not_written")
        print(f"consensus_log=not_written")
        print(f"provider_trace=written")
        print(f"failure_audit=written")
        return 2

    _write_json(str(out_dir / "game-log.json"), outputs.game_log)
    _write_json(str(out_dir / "decision-log.json"), outputs.decision_log)

    if outputs.consensus_log is not None:
        _write_json(str(out_dir / "consensus-log.json"), outputs.consensus_log)

    trace = _collect_trace(game_id, agents, [])
    trace_payload = provider_trace_to_dict(trace)
    _write_json(str(out_dir / "provider-trace.json"), trace_payload)

    failure_audit = {
        "game_id": game_id,
        "source_label": source_label,
        "failures": [],
    }
    _write_json(str(out_dir / "failure-audit.json"), failure_audit)

    if writer is not None:
        for artifact in ["game-log.json", "decision-log.json", "provider-trace.json", "failure-audit.json"]:
            writer.emit(
                "artifact_written",
                round=0, phase="final", actor="system",
                visibility="internal",
                payload={"artifact": artifact},
            )
        if outputs.consensus_log is not None:
            writer.emit(
                "artifact_written",
                round=0, phase="final", actor="system",
                visibility="internal",
                payload={"artifact": "consensus-log.json"},
            )
        manifest = build_prompt_manifest(
            run_id=game_id,
            source_label=source_label,
            agents=[
                {"player_id": pid, "provider": "deepseek", "model": "unknown"}
                for pid in ["p1", "p2", "p3", "p4", "p5", "p6"]
            ],
        )
        manifest["secrets_redacted"] = True
        writer.write_prompt_manifest(manifest)
        writer.emit(
            "artifact_written",
            round=0, phase="final", actor="system",
            visibility="internal",
            payload={"artifact": "prompt-manifest.json"},
        )
        writer.emit(
            "run_finalized",
            round=0, phase="final", actor="system",
            visibility="internal",
            payload={"status": "success"},
        )

    print(f"deepseek_consensus_game_id={game_id}")
    print(f"source_label={source_label}")
    print(f"provider_failures=0")
    print(f"game_log=written")
    print(f"decision_log=written")
    print(f"consensus_log={ 'written' if outputs.consensus_log is not None else 'not_written' }")
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
    shared_provider = DeepSeekProvider(config)

    def factory(player_id: str) -> ProviderAgent:
        return ProviderAgent(player_id, shared_provider)

    return factory


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DeepSeek consensus smoke.")
    parser.add_argument("--game-id", default="g1f_deepseek_consensus_smoke")
    parser.add_argument("--out-dir", default=".tmp/g1f-deepseek-consensus-smoke")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--max-tokens-per-request", type=int, default=256)
    parser.add_argument("--max-provider-requests", type=int, default=12)
    parser.add_argument("--allow-live-api", action="store_true", default=False)
    parser.add_argument("--write-runtime-spine", action="store_true", default=False)
    args = parser.parse_args()

    if not args.allow_live_api:
        print("live_api=disabled")
        print("game_log=not_written")
        print("decision_log=not_written")
        print("consensus_log=not_written")
        return 1

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        print(f"missing {args.api_key_env}", file=sys.stderr)
        print("game_log=not_written")
        print("decision_log=not_written")
        print("consensus_log=not_written")
        return 1

    factory = _build_deepseek_agent(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        max_tokens=args.max_tokens_per_request,
        max_requests=args.max_provider_requests,
    )

    return run_deepseek_consensus_game_with_provider_factory(
        game_id=args.game_id,
        out_dir=Path(args.out_dir),
        provider_factory=factory,
        write_runtime_spine=args.write_runtime_spine,
    )


if __name__ == "__main__":
    raise SystemExit(main())
