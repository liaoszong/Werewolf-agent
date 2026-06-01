from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.consensus_log import load_consensus_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.game_log import load_game_log
from werewolf_eval.log_bundle import validate_log_bundle
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)
from werewolf_eval.semantic_labels import load_semantic_label_log


def _write_json(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute deterministic Werewolf-agent Score Log and Metrics Summary.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--decision-log", help="Optional path to Decision Log JSON for D2 deterministic decision-quality scoring")
    parser.add_argument("--semantic-labels", help="Optional path to saved S5 Semantic Label Log JSON. Requires --decision-log.")
    parser.add_argument("--consensus-log", help="Optional path to Consensus Log JSON for bundle validation")
    parser.add_argument("--failure-audit", help="Optional path to Failure Audit JSON for bundle validation")
    parser.add_argument("--score-log-out", help="Optional path for generated Score Log JSON")
    parser.add_argument("--metrics-out", help="Optional path for generated Metrics Summary JSON")
    args = parser.parse_args()

    game = load_game_log(args.path)
    decision_log = load_decision_log(args.decision_log, game) if args.decision_log else None

    if args.semantic_labels and decision_log is None:
        parser.error("--semantic-labels requires --decision-log")
    semantic_label_log = load_semantic_label_log(args.semantic_labels, decision_log) if args.semantic_labels else None

    consensus_log = load_consensus_log(args.consensus_log, game) if args.consensus_log else None
    failure_audit = load_failure_audit(args.failure_audit, game) if args.failure_audit else None
    bundle_result = None
    if decision_log or consensus_log or failure_audit:
        bundle_result = validate_log_bundle(
            game,
            decision_log=decision_log,
            consensus_log=consensus_log,
            failure_audit=failure_audit,
        )

    score_log = score_game(game, decision_log=decision_log, semantic_label_log=semantic_label_log)
    metrics = summarize_metrics(game, score_log)

    score_payload = score_log_to_dict(score_log)
    metrics_payload = metrics_summary_to_dict(metrics)

    if bundle_result is not None:
        bundle_payload = {
            "enabled": True,
            "decision_log": bundle_result.decision_log_enabled,
            "consensus_log": bundle_result.consensus_log_enabled,
            "failure_audit": bundle_result.failure_audit_enabled,
            "team_consensus_links": bundle_result.team_consensus_links,
        }
        score_payload["bundle_validation"] = bundle_payload
        metrics_payload["bundle_validation"] = bundle_payload

    if args.score_log_out:
        _write_json(args.score_log_out, score_payload)
    if args.metrics_out:
        _write_json(args.metrics_out, metrics_payload)

    print(f"scored game_id={game.game_id}")
    print(f"score_records={len(score_log.records)}")
    print(f"winner={metrics.result_metrics.winner}")
    print(f"game_length={metrics.result_metrics.game_length}")
    print(f"wolf_team_outcome_score={metrics.score_summary.team_outcome_scores.get('wolf_team', 0)}")
    print(f"decision_log={'enabled' if decision_log else 'disabled'}")
    print(f"semantic_labels={'enabled' if semantic_label_log else 'disabled'}")
    print(f"bundle_validation={'enabled' if bundle_result else 'disabled'}")
    if bundle_result is not None:
        print(f"team_consensus_links={bundle_result.team_consensus_links}")
    print(f"decision_quality_total={sum(record.decision_quality_score for record in score_log.records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
