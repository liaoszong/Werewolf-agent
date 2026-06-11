from __future__ import annotations

import argparse

from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.game_log import load_game_log
from werewolf_eval.semantic_labels import load_semantic_label_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate saved S5 Semantic Label Log JSON.")
    parser.add_argument("game_log_path")
    parser.add_argument("decision_log_path")
    parser.add_argument("semantic_label_path")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        decision_log = load_decision_log(args.decision_log_path, game)
        label_log = load_semantic_label_log(args.semantic_label_path, decision_log)
    except (OSError, ValueError) as exc:
        print(f"invalid semantic label log: {exc}")
        return 1

    print(f"validated semantic_label_log_id={label_log.label_log_id}")
    print(f"game_id={label_log.game_id}")
    print(f"labels={len(label_log.labels)}")
    print(f"source_label={label_log.source_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
