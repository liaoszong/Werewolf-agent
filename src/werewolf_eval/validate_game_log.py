from __future__ import annotations

import argparse

from werewolf_eval.game_log import load_game_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Game Log JSON file.")
    parser.add_argument("path", help="Path to Game Log JSON")
    args = parser.parse_args()

    game = load_game_log(args.path)

    print(f"validated game_id={game.game_id}")
    print(f"players={len(game.players)}")
    print(f"events={len(game.events)}")
    print(f"winner={game.result.winner}")
    print(f"end_round={game.result.end_round}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
