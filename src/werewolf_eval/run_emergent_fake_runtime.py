"""Fake-deterministic emergent runtime launcher (P2 observer bridge, Adapter A).

The keystone of wiring the observer server to the EmergentGameEngine: it drives
the SAME emergent engine the live runner uses, but with offline fake-script
agents, AND it wires the `RuntimeEventWriter` so a fake run produces the full
observer spine (events.jsonl, snapshots/, prompt-manifest.json) plus the four
logs + provider trace. `run_emergent_game.py` (the bare CLI) deliberately does
NOT wire the writer; this module is the observer-shaped fake path.

`default_emergent_fake_launcher` conforms to the observer's
`RunLauncher = Callable[[run_id, run_dir], int]` contract and is swapped in for
the old scripted `default_fake_launcher` behind the existing default_6p_fake
template — `observer_server.py`/`observer_protocol.py`/Qt are untouched.

No network, no API keys, no secrets: the manifest records `model="none"` and the
fake source label, and `secrets_redacted=True`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from werewolf_eval.artifacts import collect_provider_trace, write_json
from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
    build_werewolf_win_script,
)
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    provider_trace_to_dict,
)
from werewolf_eval.evaluation_versions import SCORING_VERSION, evaluation_bucket
from werewolf_eval.prompt_version import PROMPT_VERSION
from werewolf_eval.run_emergent_deepseek_game import _provider_turns_summary
from werewolf_eval.runtime_events import RuntimeEventWriter, build_prompt_manifest, read_events_jsonl

SCRIPTS = {
    "villager_win": build_villager_win_script,
    "werewolf_win": build_werewolf_win_script,
}

_FAKE_PROVIDER_NAME = "deterministic_fake_provider"


def _collect_trace(game_id: str, agents: dict[str, ProviderAgent]) -> dict:
    """Roll up the per-seat fake provider requests/responses into one trace.

    Each fake agent wraps its own DeterministicFakeProvider, so request_ids never
    collide across seats; the de-dup is belt-and-suspenders. Fake token usage is
    always zero (honesty marker vs the live path)."""
    return provider_trace_to_dict(
        collect_provider_trace(
            game_id,
            agents.values(),
            provider_name=_FAKE_PROVIDER_NAME,
            source_label=FAKE_PROVIDER_SOURCE_LABEL,
        )
    )


def run_emergent_fake_runtime(
    *,
    game_id: str,
    out_dir: Path,
    script: str = "villager_win",
    seed: int = 0,
    max_requests: int = 80,
    max_day_rounds: int = 3,
    participant_controller: object | None = None,
    human_seat_id: str | None = None,
    participant_action_timeout_seconds: float = 60.0,
) -> int:
    """Run one fake-deterministic emergent game writing the full observer spine.

    Returns 0 on a completed game (full logs + spine present), 2 on a fail-closed
    outcome (round cap / budget) where only the failure audit is written — the
    streamed spine (events.jsonl + setup snapshot) stays as evidence."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    writer = RuntimeEventWriter(run_id=game_id, out_dir=out_dir)

    config = build_emergent_config(game_id=game_id)
    agents = build_emergent_fake_agents(SCRIPTS[script]())
    engine = EmergentGameEngine(
        config=config,
        agents=agents,
        seed=seed,
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        budget=EmergentBudget(max_requests=max_requests, max_day_rounds=max_day_rounds),
        runtime_events=writer,
        participant_controller=participant_controller,
        human_seat_ids={human_seat_id} if human_seat_id is not None else (),
        participant_action_timeout_seconds=participant_action_timeout_seconds,
    )
    outcome = engine.run()

    if not outcome.completed:
        # fail-closed: never write a complete game/decision/consensus log.
        write_json(out_dir / "failure-audit.json", outcome.failure_audit)
        print(f"emergent_fake_runtime_game_id={game_id}")
        print(f"source_label={FAKE_PROVIDER_SOURCE_LABEL}")
        print(f"status={outcome.status}")
        print(f"end_condition={outcome.end_condition}")
        print("failure_audit=written")
        print("game_log=not_written")
        print("live_api=not_used")
        return 2

    write_json(out_dir / "game-log.json", outcome.game_log)
    write_json(out_dir / "decision-log.json", outcome.decision_log)
    write_json(out_dir / "consensus-log.json", outcome.consensus_log)
    write_json(out_dir / "failure-audit.json", outcome.failure_audit)
    write_json(out_dir / "provider-trace.json", _collect_trace(game_id, agents))
    write_json(out_dir / "provider-turns.json", _provider_turns_summary(outcome.provider_turns))

    providers = [a.provider for a in agents.values()]
    manifest = build_prompt_manifest(
        run_id=game_id,
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        agents=[
            {
                "player_id": p.player_id,
                "role": p.role,
                "provider": "fake_deterministic",
                "model": "none",
            }
            for p in config.players
        ],
        evaluation_bucket=evaluation_bucket(
            rules_version=engine.rules_version,
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

    print(f"emergent_fake_runtime_game_id={game_id}")
    print(f"source_label={FAKE_PROVIDER_SOURCE_LABEL}")
    print("status=completed")
    print(f"winner={outcome.game_log['result']['winner']}")
    print("events_jsonl=written")
    print("snapshots=written")
    print("prompt_manifest=written")
    print("game_log=written")
    print("decision_log=written")
    print("consensus_log=written")
    print("provider_trace=written")
    print("failure_audit=written")
    print("live_api=not_used")
    print(f"runtime_events={len(events)}")
    print(f"runtime_snapshots={len(snapshot_files)}")
    return 0


def default_emergent_fake_launcher(run_id: str, run_dir: Path) -> int:
    """`RunLauncher`-shaped entry the observer server wires as the fake default."""
    return run_emergent_fake_runtime(game_id=run_id, out_dir=Path(run_dir))


def build_participant_emergent_fake_launcher(
    participant_controller: object,
    *,
    human_seat_id: str,
    script: str = "villager_win",
    seed: int = 0,
    max_requests: int = 80,
    max_day_rounds: int = 3,
    participant_action_timeout_seconds: float = 60.0,
):
    """Build a fake launcher that gives one villager seat to a participant.

    P3-C-1 first slice keeps this template-only and in-memory. The controller is
    injected from observer state so HTTP submissions and the engine thread share
    one action-window store.
    """

    def _launcher(run_id: str, run_dir: Path) -> int:
        participant_controller.configure_human_seat(run_id, human_seat_id)
        return run_emergent_fake_runtime(
            game_id=run_id,
            out_dir=Path(run_dir),
            script=script,
            seed=seed,
            max_requests=max_requests,
            max_day_rounds=max_day_rounds,
            participant_controller=participant_controller,
            human_seat_id=human_seat_id,
            participant_action_timeout_seconds=participant_action_timeout_seconds,
        )

    return _launcher


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an emergent fake game with the full observer spine.")
    parser.add_argument("--game-id", default="p2_emergent_fake_runtime")
    parser.add_argument("--out-dir", default=".tmp/p2-emergent-fake-runtime")
    parser.add_argument("--script", choices=sorted(SCRIPTS), default="villager_win")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-requests", type=int, default=80)
    parser.add_argument("--max-day-rounds", type=int, default=3)
    args = parser.parse_args(argv)
    return run_emergent_fake_runtime(
        game_id=args.game_id,
        out_dir=Path(args.out_dir),
        script=args.script,
        seed=args.seed,
        max_requests=args.max_requests,
        max_day_rounds=args.max_day_rounds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
