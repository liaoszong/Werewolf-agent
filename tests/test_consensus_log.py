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

    def test_rejects_decision_type_mismatch_with_dissenters(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["status"] = "consensus"
        raw["consensuses"][0]["final_decision"]["decision_type"] = "consensus"
        raw["consensuses"][0]["final_decision"]["dissenters"] = ["p2"]
        raw["consensuses"][0]["final_decision"]["supporters"] = ["p1"]

        with self.assertRaisesRegex(ConsensusLogValidationError, "consensus decision_type requires 0 dissenters"):
            parse_consensus_log(raw, self.game)

    def test_rejects_coordinator_tie_break_without_dissenters(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][1]["status"] = "coordinator_tie_break"
        raw["consensuses"][1]["final_decision"]["decision_type"] = "coordinator_tie_break"
        raw["consensuses"][1]["final_decision"]["dissenters"] = []

        with self.assertRaisesRegex(ConsensusLogValidationError, "coordinator_tie_break decision_type requires at least 1 dissenter"):
            parse_consensus_log(raw, self.game)

    def test_rejects_participant_not_covered_in_final_decision(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][1]["final_decision"]["supporters"] = ["p1"]
        raw["consensuses"][1]["final_decision"]["dissenters"] = []
        raw["consensuses"][1]["status"] = "consensus"
        raw["consensuses"][1]["final_decision"]["decision_type"] = "consensus"

        with self.assertRaisesRegex(ConsensusLogValidationError, "all participants must appear as supporter or dissenter"):
            parse_consensus_log(raw, self.game)

    def test_rejects_two_actions_in_same_action_round(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["actual_rounds"] = 2
        raw["consensuses"][0]["proposals"][0]["action_round"] = 1
        raw["consensuses"][0]["proposals"].append({
            "proposal_id": 3,
            "proposer": "p1",
            "proposed_target": "p4",
            "visible_info_refs": ["g001_e001"],
            "reason_summary": "alternative target.",
            "confidence": 0.5,
            "action_round": 1,
        })

        with self.assertRaisesRegex(ConsensusLogValidationError, "max 1 per action_round"):
            parse_consensus_log(raw, self.game)

    def test_rejects_missing_consensus_for_werewolf_kill(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"] = [raw["consensuses"][0]]

        with self.assertRaisesRegex(ConsensusLogValidationError, "no matching consensus entry"):
            parse_consensus_log(raw, self.game)

    def test_rejects_duplicate_consensus_for_same_kill(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        clone = dict(raw["consensuses"][0])
        clone["consensus_id"] = "g001_c003"
        raw["consensuses"].append(clone)

        with self.assertRaisesRegex(ConsensusLogValidationError, "multiple consensus entries"):
            parse_consensus_log(raw, self.game)


    def test_accepts_scripted_deterministic_source_label(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["source_label"] = "[scripted deterministic output]"
        consensus_log = parse_consensus_log(raw, self.game)
        self.assertEqual(consensus_log.source_label, "[scripted deterministic output]")


if __name__ == "__main__":
    unittest.main()
