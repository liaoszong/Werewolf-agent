from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.attribution import attribute_game, attribution_to_dict
from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class RuleAttributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.result = attribute_game(self.game, self.score_log, self.metrics)

    def test_attribution_matches_s3_expected(self) -> None:
        actual = attribution_to_dict(self.result)
        expected = load_json("docs/gold-game/s3-rule-attribution.json")
        self.assertEqual(actual, expected)

    def test_top_attribution_selected_from_turn_points(self) -> None:
        turn_point_ids = {turn_point.turn_point_id for turn_point in self.result.turn_points}
        self.assertIn(self.result.top_attribution.turn_point_id, turn_point_ids)

    def test_all_turn_point_evidence_refs_existing_events(self) -> None:
        event_ids = self.game.event_ids
        for turn_point in self.result.turn_points:
            self.assertTrue(turn_point.evidence_event_ids)
            for evidence_event_id in turn_point.evidence_event_ids:
                self.assertIn(evidence_event_id, event_ids)

    def test_rule_evaluation_summary_contains_all_f_rules(self) -> None:
        self.assertEqual(
            set(self.result.rule_evaluation_summary),
            {
                "attribution:F.1.critical_vote",
                "attribution:F.2.information_gap",
                "attribution:F.3.witch_misfire",
                "attribution:F.4.vote_deviation",
                "attribution:F.5.successful_disguise",
            },
        )

    def test_no_ai_annotation_or_free_text_reasoning(self) -> None:
        boundary = self.result.attribution_boundary
        self.assertEqual(boundary.ai_annotations, "none")
        self.assertEqual(boundary.free_text_reasoning, "not_used")
        self.assertEqual(boundary.decision_quality_score, 0)

    def test_validation_note_preserves_round1_possible_false_negative(self) -> None:
        notes = self.result.validation_notes
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].type, "possible_false_negative")
        self.assertEqual(
            notes[0].event_ids,
            ["g001_e016", "g001_e017", "g001_e020", "g001_e021", "g001_e022", "g001_e023"],
        )


if __name__ == "__main__":
    unittest.main()
