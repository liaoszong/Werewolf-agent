from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.fake_provider import build_default_fake_provider_agent
from werewolf_eval.game_engine import GameEngine, build_default_config
from werewolf_eval.provider_agent import ProviderActionError
from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    provider_failure_to_dict,
    provider_trace_to_dict,
    ProviderTrace,
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
    wolf_agent: object,
    failures: list[ProviderFailure],
) -> ProviderTrace:
    from werewolf_eval.provider_agent import ProviderAgent

    all_requests: list = []
    all_responses: list = []

    for agent in list(agents.values()) + [wolf_agent]:
        if isinstance(agent, ProviderAgent):
            all_requests.extend(agent.provider.requests)
            all_responses.extend(agent.provider.responses)

    return ProviderTrace(
        game_id=game_id,
        provider_name="deterministic_fake_provider",
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        requests=all_requests,
        responses=all_responses,
        failures=failures,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic fake-provider game.")
    parser.add_argument("--game-id", default="g1d_fake_provider")
    parser.add_argument("--game-log-out", required=True)
    parser.add_argument("--decision-log-out", required=True)
    parser.add_argument("--provider-trace-out", required=True)
    parser.add_argument("--failure-audit-out", default=None)
    parser.add_argument("--failure-mode", default=None)
    args = parser.parse_args()

    agents = {
        pid: build_default_fake_provider_agent(pid)
        for pid in ["p3", "p4", "p5", "p6"]
    }
    wolf_agent = build_default_fake_provider_agent("wolf_team")

    if args.failure_mode == "parse_failure":
        agents["p3"] = build_default_fake_provider_agent(
            "p3", override_raw_content="not valid json {{{",
        )
    elif args.failure_mode == "timeout":
        agents["p3"] = build_default_fake_provider_agent(
            "p3", failure_mode="timeout",
        )

    engine = GameEngine.from_config(
        build_default_config(game_id=args.game_id),
        agents=agents,
        wolf_agent=wolf_agent,
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
    )

    failures: list[ProviderFailure] = []

    try:
        outputs = engine.run(mode="g1b_default")
    except ProviderActionError as exc:
        failures.append(exc.failure)
        trace = _collect_trace(args.game_id, agents, wolf_agent, failures)
        trace_payload = provider_trace_to_dict(trace)
        _write_json(args.provider_trace_out, trace_payload)

        if args.failure_audit_out:
            failure_audit = {
                "game_id": args.game_id,
                "source_label": FAKE_PROVIDER_SOURCE_LABEL,
                "failures": [provider_failure_to_dict(f) for f in failures],
            }
            _write_json(args.failure_audit_out, failure_audit)

        print(f"fake_provider_game_id={args.game_id}")
        print(f"source_label={FAKE_PROVIDER_SOURCE_LABEL}")
        print(f"provider_requests={len(trace.requests)}")
        print(f"provider_responses={len(trace.responses)}")
        print(f"provider_failures={len(failures)}")
        if failures:
            print(f"failure_kind={failures[0].kind}")
        print("game_log=not_written")
        print("decision_log=not_written")
        if args.failure_audit_out:
            print("failure_audit=written")
        return 2

    # Success path
    _write_json(args.game_log_out, outputs.game_log)
    _write_json(args.decision_log_out, outputs.decision_log)

    trace = _collect_trace(args.game_id, agents, wolf_agent, [])
    trace_payload = provider_trace_to_dict(trace)
    _write_json(args.provider_trace_out, trace_payload)

    if args.failure_audit_out:
        failure_audit = {
            "game_id": args.game_id,
            "source_label": FAKE_PROVIDER_SOURCE_LABEL,
            "failures": [],
        }
        _write_json(args.failure_audit_out, failure_audit)

    print(f"fake_provider_game_id={args.game_id}")
    print(f"source_label={FAKE_PROVIDER_SOURCE_LABEL}")
    print(f"events={len(outputs.game_log['events'])}")
    print(f"decisions={len(outputs.decision_log['decisions'])}")
    print(f"provider_requests={len(trace.requests)}")
    print(f"provider_responses={len(trace.responses)}")
    print(f"provider_failures=0")
    print("game_log=written")
    print("decision_log=written")
    print("provider_trace=written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
