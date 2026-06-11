"""CLI runner for the P2-A-1 emergent Werewolf engine.

LEGACY/log-only: this CLI deliberately does NOT wire the observer runtime spine
(no events.jsonl/snapshots) — the canonical product path is
``run_emergent_fake_runtime`` (used by the observer launcher). Kept for quick
log-only runs and its own regression test (health-check E-5).

Fake-deterministic by default (offline, free, reproducible). Writes the four
standard logs on a completed game; on a fail-closed outcome (round cap / budget
exhausted) it writes ONLY the failure audit and exits non-zero — mirroring the
existing run_fake_provider_game.py fail-closed contract.

Live DeepSeek wiring is intentionally gated and NOT the default; see
--provider and the design spec §5/§11 for the known live-path limitations.
"""

from __future__ import annotations

import argparse
import sys

from werewolf_eval.artifacts import write_json
from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
    build_werewolf_win_script,
)
from werewolf_eval.provider_contract import FAKE_PROVIDER_SOURCE_LABEL

SCRIPTS = {
    "villager_win": build_villager_win_script,
    "werewolf_win": build_werewolf_win_script,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an emergent fake-deterministic Werewolf game.")
    parser.add_argument("--game-id", default="p2a1_emergent")
    parser.add_argument("--script", choices=sorted(SCRIPTS), default="villager_win")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-requests", type=int, default=80)
    parser.add_argument("--max-day-rounds", type=int, default=3)
    parser.add_argument("--game-log-out", default=None)
    parser.add_argument("--decision-log-out", default=None)
    parser.add_argument("--consensus-log-out", default=None)
    parser.add_argument("--failure-audit-out", default=None)
    args = parser.parse_args(argv)

    script = SCRIPTS[args.script]()
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=args.game_id),
        agents=build_emergent_fake_agents(script),
        seed=args.seed,
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        budget=EmergentBudget(max_requests=args.max_requests, max_day_rounds=args.max_day_rounds),
    )
    outcome = engine.run()

    print(f"emergent_game_id={args.game_id}")
    print(f"source_label={FAKE_PROVIDER_SOURCE_LABEL}")
    print(f"status={outcome.status}")
    print(f"end_condition={outcome.end_condition}")

    if not outcome.completed:
        # fail-closed: never write a complete game/decision/consensus log
        if args.failure_audit_out:
            write_json(args.failure_audit_out, outcome.failure_audit)
            print("failure_audit=written")
        print("game_log=not_written")
        print("decision_log=not_written")
        print("consensus_log=not_written")
        return 2

    print(f"winner={outcome.game_log['result']['winner']}")
    print(f"end_round={outcome.game_log['result']['end_round']}")
    print(f"events={len(outcome.game_log['events'])}")
    print(f"decisions={len(outcome.decision_log['decisions'])}")
    print(f"consensuses={len(outcome.consensus_log['consensuses'])}")
    print(f"failures={len(outcome.failure_audit['failures'])}")
    if args.game_log_out:
        write_json(args.game_log_out, outcome.game_log)
        print("game_log=written")
    if args.decision_log_out:
        write_json(args.decision_log_out, outcome.decision_log)
        print("decision_log=written")
    if args.consensus_log_out:
        write_json(args.consensus_log_out, outcome.consensus_log)
        print("consensus_log=written")
    if args.failure_audit_out:
        write_json(args.failure_audit_out, outcome.failure_audit)
        print("failure_audit=written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
