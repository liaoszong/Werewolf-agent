from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.decision_log import DecisionLogValidationError, load_decision_log, parse_decision_log
from werewolf_eval.game_log import load_game_log


class DecisionLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.path = ROOT / "docs/gold-game/g001-decision-log.json"

    def test_load_decision_log_accepts_gold_sample(self) -> None:
        decision_log = load_decision_log(self.path, self.game)

        self.assertEqual(decision_log.decision_log_id, "d1_g001_decision_log")
        self.assertEqual(decision_log.game_id, "g001")
        self.assertEqual(decision_log.source_label, "[人工 gold sample]")
        self.assertEqual(len(decision_log.decisions), 10)
        self.assertEqual(decision_log.decisions[0].decision_id, "g001_d001")
        self.assertEqual(decision_log.decisions[0].actor, "wolf_team")
        self.assertEqual(decision_log.decisions[0].decision_scope, "team")
        self.assertEqual(decision_log.decisions[-1].decision_type, "inference_based")

    def test_rejects_game_id_mismatch(self) -> None:
        raw = {
            "decision_log_id": "bad",
            "game_id": "other_game",
            "source_label": "[人工 gold sample]",
            "decisions": [],
        }

        with self.assertRaisesRegex(DecisionLogValidationError, "game_id mismatch"):
            parse_decision_log(raw, self.game)

    def test_rejects_unknown_actor(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["actor"] = "p99"

        with self.assertRaisesRegex(DecisionLogValidationError, "unknown actor"):
            parse_decision_log(raw, self.game)

    def test_rejects_unknown_visible_info_ref(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["visible_info_refs"] = ["g001_e999"]

        with self.assertRaisesRegex(DecisionLogValidationError, "unknown visible_info_refs"):
            parse_decision_log(raw, self.game)

    def test_rejects_invalid_decision_type(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["decision_type"] = "mind_reading"

        with self.assertRaisesRegex(DecisionLogValidationError, "invalid decision_type"):
            parse_decision_log(raw, self.game)

    def test_rejects_long_reason_summary(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["reason_summary"] = "x" * 201

        with self.assertRaisesRegex(DecisionLogValidationError, "reason_summary"):
            parse_decision_log(raw, self.game)

    def test_rejects_confidence_out_of_range(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["confidence"] = 1.5

        with self.assertRaisesRegex(DecisionLogValidationError, "confidence"):
            parse_decision_log(raw, self.game)

    def _minimal_raw(self) -> dict[str, object]:
        return {
            "decision_log_id": "test_decision_log",
            "game_id": "g001",
            "source_label": "[人工 gold sample]",
            "decisions": [
                {
                    "decision_id": "test_d001",
                    "actor": "p4",
                    "decision_scope": "single",
                    "consensus_id": None,
                    "phase": "day",
                    "action": "player_vote",
                    "target": "p1",
                    "visible_info_refs": ["g001_e010"],
                    "reason_summary": "p4 votes based on visible public pressure.",
                    "decision_type": "inference_based",
                    "confidence": 0.75,
                    "strategy_tag": "vote_suspicious_pair",
                }
            ],
        }

    def test_validate_decision_log_cli_outputs_summary(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.validate_decision_log",
                str(self.path),
                str(ROOT / "docs/gold-game/g001-game-log.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("validated decision_log_id=d1_g001_decision_log", result.stdout)
        self.assertIn("game_id=g001", result.stdout)
        self.assertIn("decisions=10", result.stdout)
        self.assertIn("source_label=[人工 gold sample]", result.stdout)


    def test_accepts_scripted_deterministic_source_label(self) -> None:
        raw = self._minimal_raw()
        raw["source_label"] = "[scripted deterministic output]"
        decision_log = parse_decision_log(raw, self.game)
        self.assertEqual(decision_log.source_label, "[scripted deterministic output]")


if __name__ == "__main__":
    unittest.main()
