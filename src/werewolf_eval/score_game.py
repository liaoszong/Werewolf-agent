from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)


def _write_json(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute deterministic Werewolf-agent Score Log and Metrics Summary.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--score-log-out", help="Optional path for generated Score Log JSON")
    parser.add_argument("--metrics-out", help="Optional path for generated Metrics Summary JSON")
    args = parser.parse_args()

    game = load_game_log(args.path)
    score_log = score_game(game)
    metrics = summarize_metrics(game, score_log)

    score_payload = score_log_to_dict(score_log)
    metrics_payload = metrics_summary_to_dict(metrics)

    if args.score_log_out:
        _write_json(args.score_log_out, score_payload)
    if args.metrics_out:
        _write_json(args.metrics_out, metrics_payload)

    print(f"scored game_id={game.game_id}")
    print(f"score_records={len(score_log.records)}")
    print(f"winner={metrics.result_metrics.winner}")
    print(f"game_length={metrics.result_metrics.game_length}")
    print(f"wolf_team_outcome_score={metrics.score_summary.team_outcome_scores.get('wolf_team', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
