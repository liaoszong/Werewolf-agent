from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class DeterministicScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)

    def test_score_log_matches_s2_expected_records(self) -> None:
        actual = score_log_to_dict(self.score_log)
        expected = load_json("docs/gold-game/s2-score-log.json")
        self.assertEqual(actual, expected)

    def test_metrics_summary_matches_s2_expected(self) -> None:
        actual = metrics_summary_to_dict(self.metrics)
        expected = load_json("docs/gold-game/s2-metrics-summary.json")
        self.assertEqual(actual, expected)

    def test_decision_quality_is_zero_without_decision_log(self) -> None:
        self.assertTrue(self.score_log.records)
        for record in self.score_log.records:
            self.assertEqual(record.decision_quality_score, 0)

    def test_rule_integrity_defaults_to_zero_without_flag_events(self) -> None:
        self.assertTrue(self.score_log.records)
        for record in self.score_log.records:
            self.assertEqual(record.rule_integrity_score, 0)

    def test_score_records_reference_existing_events(self) -> None:
        event_ids = self.game.event_ids
        for record in self.score_log.records:
            self.assertIn(record.event_id, event_ids)
            for evidence_event_id in record.evidence_event_ids:
                self.assertIn(evidence_event_id, event_ids)

    def test_known_rubric_gaps_are_preserved(self) -> None:
        score_payload = score_log_to_dict(self.score_log)
        metrics_payload = metrics_summary_to_dict(self.metrics)
        score_rules = {
            rule
            for record in score_payload["records"]
            for rule in record["rules_triggered"]
        }
        self.assertIn("rubric-gap:werewolf_day_vote_without_elimination", score_rules)
        self.assertIn("rubric-gap:witch_day_vote_outcome_not_explicit", score_rules)

        gaps = {item["gap"] for item in metrics_payload["known_rubric_gaps_recorded_not_fixed"]}
        self.assertEqual(
            gaps,
            {"werewolf_day_vote_without_elimination", "witch_day_vote_outcome_not_explicit"},
        )


if __name__ == "__main__":
    unittest.main()
