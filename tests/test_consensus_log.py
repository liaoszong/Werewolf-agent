from __future__ import annotations

import json
from pathlib import Path
import unittest

from werewolf_eval.game_log import load_game_log
from werewolf_eval.consensus_log import (
    ConsensusLogValidationError,
    load_consensus_log,
    parse_consensus_log,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ConsensusLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.raw = load_json("docs/gold-game/g001-consensus-log.json")

    def test_load_consensus_log_accepts_gold_fixture(self) -> None:
        consensus_log = load_consensus_log(ROOT / "docs/gold-game/g001-consensus-log.json", self.game)

        self.assertEqual(consensus_log.consensus_log_id, "s4_g001_consensus_log")
        self.assertEqual(consensus_log.game_id, "g001")
        self.assertEqual(consensus_log.source_label, "[人工 gold sample]")
        self.assertEqual(len(consensus_log.consensuses), 2)
        self.assertEqual(consensus_log.consensus_ids, {"g001_c001", "g001_c002"})
        self.assertEqual(consensus_log.consensuses[0].final_decision.target, "p5")

    def test_rejects_game_id_mismatch(self) -> None:
        raw = dict(self.raw)
        raw["game_id"] = "other_game"

        with self.assertRaisesRegex(ConsensusLogValidationError, "game_id mismatch"):
            parse_consensus_log(raw, self.game)

    def test_rejects_unknown_participant(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["participants"] = ["p1", "p9"]

        with self.assertRaisesRegex(ConsensusLogValidationError, "unknown participant"):
            parse_consensus_log(raw, self.game)

    def test_rejects_non_werewolf_participant(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["participants"] = ["p1", "p3"]

        with self.assertRaisesRegex(ConsensusLogValidationError, "participant must be werewolf"):
            parse_consensus_log(raw, self.game)

    def test_rejects_unknown_visible_info_ref(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["proposals"][0]["visible_info_refs"] = ["missing_event"]

        with self.assertRaisesRegex(ConsensusLogValidationError, "unknown visible_info_refs"):
            parse_consensus_log(raw, self.game)

    def test_rejects_too_many_discussion_rounds(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["actual_rounds"] = 4

        with self.assertRaisesRegex(ConsensusLogValidationError, "actual_rounds must be between 1 and max_rounds"):
            parse_consensus_log(raw, self.game)

    def test_rejects_reason_summary_over_150_chars(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["proposals"][0]["reason_summary"] = "x" * 151

        with self.assertRaisesRegex(ConsensusLogValidationError, "reason_summary exceeds 150 chars"):
            parse_consensus_log(raw, self.game)

    def test_rejects_response_to_unknown_proposal(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["responses"][0]["to_proposal_id"] = 99

        with self.assertRaisesRegex(ConsensusLogValidationError, "unknown to_proposal_id"):
            parse_consensus_log(raw, self.game)

    def test_rejects_final_target_that_does_not_match_werewolf_kill_event(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["final_decision"]["target"] = "p4"

        with self.assertRaisesRegex(ConsensusLogValidationError, "final target does not match werewolf_kill"):
            parse_consensus_log(raw, self.game)

    def test_rejects_invalid_status(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["status"] = "majority"

        with self.assertRaisesRegex(ConsensusLogValidationError, "invalid status"):
            parse_consensus_log(raw, self.game)


if __name__ == "__main__":
    unittest.main()
