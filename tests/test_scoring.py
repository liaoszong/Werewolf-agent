from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.decision_log import load_decision_log, parse_decision_log
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
        self.decision_log = load_decision_log(ROOT / "docs/gold-game/g001-decision-log.json", self.game)
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.d2_score_log = score_game(self.game, decision_log=self.decision_log)
        self.d2_metrics = summarize_metrics(self.game, self.d2_score_log)

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
            self.assertIsNone(record.decision_id)
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

    def test_d2_decision_log_attaches_decision_id_and_preserves_quality_zero(self) -> None:
        records = {record.event_id: record for record in self.d2_score_log.records}

        self.assertEqual(records["g001_e019"].decision_id, "g001_d007")
        self.assertEqual(records["g001_e019"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e019"].rules_triggered)

        self.assertEqual(records["g001_e025"].decision_id, "g001_d009")
        self.assertEqual(records["g001_e025"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e025"].rules_triggered)

        self.assertEqual(records["g001_e035"].decision_id, "g001_d010")
        self.assertEqual(records["g001_e035"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e035"].rules_triggered)

    def test_d2_default_or_empty_ref_decisions_keep_quality_zero(self) -> None:
        records = {record.event_id: record for record in self.d2_score_log.records}

        self.assertEqual(records["g001_e020"].decision_id, "g001_d008")
        self.assertEqual(records["g001_e020"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.no_decision_quality_for_default", records["g001_e020"].rules_triggered)

    def test_d2_illegal_visible_info_ref_penalizes_rule_integrity(self) -> None:
        raw = load_json("docs/gold-game/g001-decision-log.json")
        raw["decisions"] = [
            {
                "decision_id": "bad_d001",
                "actor": "p5",
                "decision_scope": "single",
                "consensus_id": None,
                "phase": "day",
                "action": "player_vote",
                "target": "p3",
                "visible_info_refs": ["g001_e008"],
                "reason_summary": "p5 illegally relies on the seer-only check result.",
                "decision_type": "inference_based",
                "confidence": 0.5,
                "strategy_tag": "illegal_ref_test",
            }
        ]
        decision_log = parse_decision_log(raw, self.game)

        score_log = score_game(self.game, decision_log=decision_log)
        records = {record.event_id: record for record in score_log.records}

        self.assertEqual(records["g001_e020"].decision_id, "bad_d001")
        self.assertEqual(records["g001_e020"].decision_quality_score, 0)
        self.assertEqual(records["g001_e020"].rule_integrity_score, -3)
        self.assertIn("rubric:G.1.illegal_visible_info_ref", records["g001_e020"].rules_triggered)

    def test_d2_metrics_summary_reflects_decision_log_input(self) -> None:
        payload = metrics_summary_to_dict(self.d2_metrics)
        decision_scores = payload["score_summary"]["player_decision_quality_scores"]

        # D2 does not assign positive decision_quality_score.
        # All scores remain 0; the value is in decision_id traceability and rule_integrity checks.
        self.assertEqual(decision_scores["p4"], 0)
        self.assertEqual(decision_scores["p6"], 0)
        self.assertEqual(decision_scores["p5"], 0)

    def test_score_game_cli_accepts_decision_log(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.score_game",
                str(ROOT / "docs/gold-game/g001-game-log.json"),
                "--decision-log",
                str(ROOT / "docs/gold-game/g001-decision-log.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("decision_log=enabled", result.stdout)
        self.assertIn("decision_quality_total=", result.stdout)


if __name__ == "__main__":
    unittest.main()
