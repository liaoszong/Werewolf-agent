from __future__ import annotations

import argparse

from werewolf_eval.consensus_log import load_consensus_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.game_log import load_game_log
from werewolf_eval.log_bundle import validate_log_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cross-log Werewolf-agent bundle invariants.")
    parser.add_argument("game_log_path", help="Path to Game Log JSON")
    parser.add_argument("--decision-log", help="Path to Decision Log JSON")
    parser.add_argument("--consensus-log", help="Path to Consensus Log JSON")
    parser.add_argument("--failure-audit", help="Path to Failure Audit JSON")
    args = parser.parse_args()

    game = load_game_log(args.game_log_path)
    decision_log = load_decision_log(args.decision_log, game) if args.decision_log else None
    consensus_log = load_consensus_log(args.consensus_log, game) if args.consensus_log else None
    failure_audit = load_failure_audit(args.failure_audit, game) if args.failure_audit else None

    result = validate_log_bundle(
        game,
        decision_log=decision_log,
        consensus_log=consensus_log,
        failure_audit=failure_audit,
    )

    print(f"validated log_bundle game_id={result.game_id}")
    print(f"decision_log={'enabled' if result.decision_log_enabled else 'disabled'}")
    print(f"consensus_log={'enabled' if result.consensus_log_enabled else 'disabled'}")
    print(f"failure_audit={'enabled' if result.failure_audit_enabled else 'disabled'}")
    print(f"team_consensus_links={result.team_consensus_links}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
