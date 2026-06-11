"""LEGACY (R-35): scripted-game CLI, reachable only from its own tests — NOT on the
canonical product path (`run_observer_server` → `run_g1h_fake_runtime` for fake /
`deepseek_launcher` for live). Kept for its passing tests; do not extend. See
`docs/PROJECT_MAP.md`."""
from __future__ import annotations

import argparse

from werewolf_eval.artifacts import write_json
from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic logs from a scripted Werewolf game."
    )
    parser.add_argument("script_path")
    parser.add_argument("--game-log-out", required=True)
    parser.add_argument("--decision-log-out", required=True)
    parser.add_argument("--consensus-log-out", required=True)
    args = parser.parse_args()

    script = load_scripted_game(args.script_path)
    outputs = run_scripted_game(script)

    write_json(args.game_log_out, outputs.game_log)
    write_json(args.decision_log_out, outputs.decision_log)
    write_json(args.consensus_log_out, outputs.consensus_log)

    print(f"scripted_game_id={outputs.game_log['game_id']}")
    print(f"source_label={outputs.game_log['source_label']}")
    print(f"events={len(outputs.game_log['events'])}")
    print(f"decisions={len(outputs.decision_log['decisions'])}")
    print(f"consensuses={len(outputs.consensus_log['consensuses'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
