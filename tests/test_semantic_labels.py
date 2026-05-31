from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.game_log import load_game_log
from werewolf_eval.semantic_labels import (
    SemanticLabelValidationError,
    load_semantic_label_log,
)


class SemanticLabelLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.decision_log = load_decision_log(ROOT / "docs/gold-game/g001-decision-log.json", self.game)

    def test_load_example_semantic_label_log(self) -> None:
        label_log = load_semantic_label_log(
            ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
            self.decision_log,
        )

        self.assertEqual(label_log.label_log_id, "s5_g001_example_output")
        self.assertEqual(label_log.game_id, "g001")
        self.assertEqual(label_log.source_label, "[semantic research output]")
        self.assertEqual(label_log.prompt_candidate, "candidate_a_minimal_json")
        self.assertEqual(len(label_log.labels), 5)
        self.assertIn("g001_d010", label_log.label_by_decision_id)

    def test_rejects_duplicate_decision_label(self) -> None:
        path = ROOT / "docs/gold-game/s5-semantic-label-output.example.json"
        import json
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["labels"].append(dict(raw["labels"][0]))

        with self.assertRaisesRegex(SemanticLabelValidationError, "duplicate decision_id"):
            from werewolf_eval.semantic_labels import parse_semantic_label_log
            parse_semantic_label_log(raw, self.decision_log)

    def test_rejects_unknown_decision_id(self) -> None:
        path = ROOT / "docs/gold-game/s5-semantic-label-output.example.json"
        import json
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["labels"][0]["decision_id"] = "missing_decision"

        with self.assertRaisesRegex(SemanticLabelValidationError, "unknown decision_id"):
            from werewolf_eval.semantic_labels import parse_semantic_label_log
            parse_semantic_label_log(raw, self.decision_log)

    def test_validate_semantic_labels_cli(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.validate_semantic_labels",
                str(ROOT / "docs/gold-game/g001-game-log.json"),
                str(ROOT / "docs/gold-game/g001-decision-log.json"),
                str(ROOT / "docs/gold-game/s5-semantic-label-output.example.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("validated semantic_label_log_id=s5_g001_example_output", result.stdout)
        self.assertIn("game_id=g001", result.stdout)
        self.assertIn("labels=5", result.stdout)


if __name__ == "__main__":
    unittest.main()
