from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.game_engine import GameEngine, build_default_config


def _write_json(path: str, payload: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic G1b mock-agent game.")
    parser.add_argument("--game-id", default="g1b_mock_001")
    parser.add_argument("--game-log-out", required=True)
    parser.add_argument("--decision-log-out", required=True)
    args = parser.parse_args()

    outputs = GameEngine.from_config(build_default_config(game_id=args.game_id)).run()
    _write_json(args.game_log_out, outputs.game_log)
    _write_json(args.decision_log_out, outputs.decision_log)

    print(f"mock_game_id={args.game_id}")
    print(f"events={len(outputs.game_log['events'])}")
    print(f"decisions={len(outputs.decision_log['decisions'])}")
    print("consensus=not_generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
