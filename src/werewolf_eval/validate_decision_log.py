from __future__ import annotations

import argparse

from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.game_log import load_game_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Decision Log JSON file.")
    parser.add_argument("decision_log_path", help="Path to Decision Log JSON")
    parser.add_argument("game_log_path", help="Path to matching Game Log JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        decision_log = load_decision_log(args.decision_log_path, game)
    except (OSError, ValueError) as exc:
        print(f"invalid decision log: {exc}")
        return 1

    print(f"validated decision_log_id={decision_log.decision_log_id}")
    print(f"game_id={decision_log.game_id}")
    print(f"decisions={len(decision_log.decisions)}")
    print(f"source_label={decision_log.source_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
