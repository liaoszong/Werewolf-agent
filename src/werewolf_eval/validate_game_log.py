from __future__ import annotations

import argparse

from werewolf_eval.game_log import load_game_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Game Log JSON file.")
    parser.add_argument("path", help="Path to Game Log JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.path)
    except (OSError, ValueError) as exc:
        print(f"invalid game log: {exc}")
        return 1

    print(f"validated game_id={game.game_id}")
    print(f"source_label={game.source_label}")
    print(f"players={len(game.players)}")
    print(f"events={len(game.events)}")
    print(f"winner={game.result.winner}")
    print(f"end_round={game.result.end_round}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
