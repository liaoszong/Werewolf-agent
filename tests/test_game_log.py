from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.game_log import GameLogValidationError, load_game_log, parse_game_log


def load_raw_gold_game() -> dict:
    return json.loads((ROOT / "docs/gold-game/g001-game-log.json").read_text(encoding="utf-8"))


class GameLogParserTests(unittest.TestCase):
    def test_loads_gold_game(self) -> None:
        game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")

        self.assertEqual(game.game_id, "g001")
        self.assertEqual(game.source_label, "[人工 gold sample]")
        self.assertEqual(len(game.players), 6)
        self.assertEqual(len(game.events), 38)
        self.assertEqual(game.events[0].event_id, "g001_e001")
        self.assertEqual(game.events[-1].type, "game_over")
        self.assertEqual(game.result.winner, "villager")
        self.assertEqual(game.result.survivors, ["p4", "p6"])

    def test_rejects_missing_source_label(self) -> None:
        raw = load_raw_gold_game()
        del raw["source_label"]

        with self.assertRaisesRegex(GameLogValidationError, "missing top-level fields"):
            parse_game_log(raw)

    def test_rejects_unknown_source_label(self) -> None:
        raw = load_raw_gold_game()
        raw["source_label"] = "[unknown mystery label]"

        with self.assertRaisesRegex(GameLogValidationError, "invalid source_label"):
            parse_game_log(raw)

    def test_rejects_duplicate_event_id(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][1] = copy.deepcopy(raw["events"][1])
        raw["events"][1]["event_id"] = raw["events"][0]["event_id"]

        with self.assertRaisesRegex(GameLogValidationError, "event_id values must be unique"):
            parse_game_log(raw)

    def test_rejects_non_continuous_sequence(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][1] = copy.deepcopy(raw["events"][1])
        raw["events"][1]["sequence"] = 99

        with self.assertRaisesRegex(GameLogValidationError, "event sequence must be continuous"):
            parse_game_log(raw)

    def test_rejects_unknown_survivor(self) -> None:
        raw = load_raw_gold_game()
        raw["result"] = copy.deepcopy(raw["result"])
        raw["result"]["survivors"] = ["p999"]

        with self.assertRaisesRegex(GameLogValidationError, "unknown players"):
            parse_game_log(raw)

    def test_rejects_invalid_visibility(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][0] = copy.deepcopy(raw["events"][0])
        raw["events"][0]["visibility"] = "secret_table"

        with self.assertRaisesRegex(GameLogValidationError, "invalid visibility"):
            parse_game_log(raw)

    def test_rejects_unknown_visible_info_ref(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][24] = copy.deepcopy(raw["events"][24])
        raw["events"][24]["data"] = copy.deepcopy(raw["events"][24]["data"])
        raw["events"][24]["data"]["visible_info_refs"] = ["g001_e999"]

        with self.assertRaisesRegex(GameLogValidationError, "unknown refs"):
            parse_game_log(raw)


if __name__ == "__main__":
    unittest.main()
