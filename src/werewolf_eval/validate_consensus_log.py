from __future__ import annotations

import argparse

from werewolf_eval.consensus_log import load_consensus_log
from werewolf_eval.game_log import load_game_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Consensus Log JSON file.")
    parser.add_argument("path", help="Path to Consensus Log JSON")
    parser.add_argument("game_log_path", help="Path to Game Log JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        consensus_log = load_consensus_log(args.path, game)
    except (OSError, ValueError) as exc:
        print(f"invalid consensus log: {exc}")
        return 1

    print(
        "validated "
        f"consensus_log_id={consensus_log.consensus_log_id} "
        f"game_id={consensus_log.game_id} "
        f"consensuses={len(consensus_log.consensuses)} "
        f"source_label={consensus_log.source_label}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
