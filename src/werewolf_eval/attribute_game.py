"""LEGACY (R-35): standalone attribution CLI, reachable only from its own tests. The
canonical attribution entry is `attribution.attribute_game()` (used by render_demo /
settlement_bundle); this thin CLI is not on the product path. Kept for its tests; do
not extend. See `docs/PROJECT_MAP.md`."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.attribution import attribute_game, attribution_to_dict
from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics


def _write_json(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute deterministic Werewolf-agent rule attribution.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--attribution-out", help="Optional path for generated attribution JSON")
    args = parser.parse_args()

    game = load_game_log(args.path)
    score_log = score_game(game)
    metrics = summarize_metrics(game, score_log)
    attribution = attribute_game(game, score_log, metrics)
    payload = attribution_to_dict(attribution)

    if args.attribution_out:
        _write_json(args.attribution_out, payload)

    top = attribution.top_attribution
    print(f"attributed game_id={game.game_id}")
    print(f"turn_points={len(attribution.turn_points)}")
    print(f"top_rule={top.rule_id}")
    print(f"top_turn_point={top.turn_point_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
