"""CI-safe fake G1h runtime CLI.

Runs a deterministic game with fake providers and writes the full G1h
event-spine artifact bundle.  No network, no API keys, no secrets.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from werewolf_eval.game_engine import GameEngine, build_default_config
from werewolf_eval.provider_agent import ProviderActionError, ProviderAgent
from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTrace,
    provider_failure_to_dict,
    provider_trace_to_dict,
)
from werewolf_eval.evaluation_versions import SCORING_VERSION, UNKNOWN_VERSION, evaluation_bucket
from werewolf_eval.prompt_version import PROMPT_VERSION
from werewolf_eval.runtime_events import (
    RuntimeEventWriter,
    build_prompt_manifest,
    read_events_jsonl,
)


class _DeterministicFakeProvider:
    """A fake provider that returns deterministic valid-action JSON."""

    # Scripted by (actor, phase, round) keys — never reads the rendered prompt.
    provider_runtime_kind = "fake_deterministic"
    uses_baseline_prompt = False

    def __init__(self) -> None:
        self._provider_name = "fake_deterministic"
        self._source_label = FAKE_PROVIDER_SOURCE_LABEL
        self.requests: list[ProviderRequest] = []
        self.responses: list[ProviderResponse] = []

    def respond(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        allowed = request.allowed_actions
        action = allowed[0] if allowed else "player_vote"
        targets = request.allowed_targets
        target = targets[0] if targets else "p1"
        payload = {
            "action": action,
            "target": target,
            "reason_summary": "deterministic fake decision",
            "decision_type": "inference_based",
            "confidence": 1.0,
        }
        raw = json.dumps(payload, ensure_ascii=False)
        response = ProviderResponse(
            request_id=request.request_id,
            provider_name=self._provider_name,
            source_label=self._source_label,
            raw_content=raw,
            latency_ms=0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
        self.responses.append(response)
        return response


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _collect_trace(
    game_id: str,
    agents: dict[str, Any],
    failures: list[ProviderFailure],
) -> ProviderTrace:
    seen_req: set[str] = set()
    seen_resp: set[str] = set()
    all_requests: list[ProviderRequest] = []
    all_responses: list[ProviderResponse] = []

    for agent in agents.values():
        if isinstance(agent, ProviderAgent):
            provider = agent.provider
            if hasattr(provider, "requests"):
                for req in provider.requests:
                    if req.request_id not in seen_req:
                        seen_req.add(req.request_id)
                        all_requests.append(req)
            if hasattr(provider, "responses"):
                for resp in provider.responses:
                    if resp.request_id not in seen_resp:
                        seen_resp.add(resp.request_id)
                        all_responses.append(resp)

    return ProviderTrace(
        game_id=game_id,
        provider_name="fake_deterministic",
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        requests=all_requests,
        responses=all_responses,
        failures=failures,
    )


def run_fake_runtime(*, game_id: str, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    writer = RuntimeEventWriter(run_id=game_id, out_dir=out_dir)

    shared_provider = _DeterministicFakeProvider()

    def factory(player_id: str) -> ProviderAgent:
        return ProviderAgent(player_id, shared_provider, runtime_events=writer)

    player_ids = ["p1", "p2", "p3", "p4", "p5", "p6"]
    agents = {pid: factory(pid) for pid in player_ids}

    engine = GameEngine.from_config(
        build_default_config(game_id=game_id),
        agents=agents,
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        runtime_events=writer,
    )

    failures: list[ProviderFailure] = []

    try:
        outputs = engine.run(mode="g1f_provider_consensus")
    except ProviderActionError as exc:
        failures.append(exc.failure)
        trace = _collect_trace(game_id, agents, failures)
        _write_json(out_dir / "provider-trace.json", provider_trace_to_dict(trace))
        failure_audit = {
            "game_id": game_id,
            "source_label": FAKE_PROVIDER_SOURCE_LABEL,
            "failures": [provider_failure_to_dict(f) for f in failures],
        }
        _write_json(out_dir / "failure-audit.json", failure_audit)
        print(f"g1h_fake_runtime_game_id={game_id}")
        print(f"source_label={FAKE_PROVIDER_SOURCE_LABEL}")
        print("events_jsonl=written")
        print("provider_trace=written")
        print("failure_audit=written")
        print("live_api=not_used")
        return 2

    _write_json(out_dir / "game-log.json", outputs.game_log)
    _write_json(out_dir / "decision-log.json", outputs.decision_log)

    if outputs.consensus_log is not None:
        _write_json(out_dir / "consensus-log.json", outputs.consensus_log)

    trace = _collect_trace(game_id, agents, [])
    _write_json(out_dir / "provider-trace.json", provider_trace_to_dict(trace))

    failure_audit = {
        "game_id": game_id,
        "source_label": FAKE_PROVIDER_SOURCE_LABEL,
        "failures": [],
    }
    _write_json(out_dir / "failure-audit.json", failure_audit)

    providers = [a.provider for a in agents.values()]
    manifest = build_prompt_manifest(
        run_id=game_id,
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        agents=[
            {
                "player_id": pid,
                "role": engine._players_by_id[pid].role,
                "provider": "fake_deterministic",
                "model": "none",
            }
            for pid in player_ids
        ],
        evaluation_bucket=evaluation_bucket(
            rules_version=UNKNOWN_VERSION,  # G1h GameEngine predates RulesVariant; honest unknown
            prompt_version=PROMPT_VERSION,
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
    writer.write_prompt_manifest(manifest)

    events = read_events_jsonl(writer.events_path)
    snapshot_files = sorted(writer.snapshots_dir.glob("*.json"))

    print(f"g1h_fake_runtime_game_id={game_id}")
    print(f"source_label={FAKE_PROVIDER_SOURCE_LABEL}")
    print("events_jsonl=written")
    print("snapshots=written")
    print("prompt_manifest=written")
    print("game_log=written")
    print("decision_log=written")
    print(f"consensus_log={'written' if outputs.consensus_log is not None else 'not_written'}")
    print("provider_trace=written")
    print("failure_audit=written")
    print("live_api=not_used")
    print(f"runtime_events={len(events)}")
    print(f"runtime_snapshots={len(snapshot_files)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run G1h fake runtime CLI.")
    parser.add_argument("--game-id", default="g1h_fake_runtime")
    parser.add_argument("--out-dir", default=".tmp/g1h-fake-runtime")
    args = parser.parse_args()

    return run_fake_runtime(game_id=args.game_id, out_dir=Path(args.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
