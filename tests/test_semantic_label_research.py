from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SemanticLabelDocsTests(unittest.TestCase):
    def test_required_docs_exist(self) -> None:
        for path in [
            ROOT / "docs/prs/2026-05-30--s5-semantic-label-research.md",
            ROOT / "docs/semantic-labeling/s5-label-contract.md",
            ROOT / "docs/semantic-labeling/s5-label-prompts.md",
        ]:
            self.assertTrue(path.exists(), path.as_posix())


import json


class SemanticLabelFixtureTests(unittest.TestCase):
    def test_eval_set_has_unique_decisions(self) -> None:
        payload = json.loads((ROOT / "docs/gold-game/s5-semantic-label-eval-set.json").read_text(encoding="utf-8"))
        decision_ids = [item["decision_id"] for item in payload["items"]]
        self.assertEqual(len(decision_ids), len(set(decision_ids)))
        self.assertEqual(len(decision_ids), 5)
        self.assertIn("g001_d008", decision_ids)
        self.assertNotIn("g001_d006", decision_ids)

    def test_example_output_covers_eval_set(self) -> None:
        eval_set = json.loads((ROOT / "docs/gold-game/s5-semantic-label-eval-set.json").read_text(encoding="utf-8"))
        output = json.loads((ROOT / "docs/gold-game/s5-semantic-label-output.example.json").read_text(encoding="utf-8"))
        expected = {item["decision_id"] for item in eval_set["items"]}
        actual = {item["decision_id"] for item in output["labels"]}
        self.assertEqual(actual, expected)


class SemanticLabelEvaluatorTests(unittest.TestCase):
    def test_evaluator_reports_exact_accuracy(self) -> None:
        from scripts.research.evaluate_semantic_labels import evaluate_files

        result = evaluate_files(
            ROOT / "docs/gold-game/s5-semantic-label-eval-set.json",
            ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["decision_count"], 5)
        self.assertEqual(result["quality_label_accuracy"], 1.0)
        self.assertEqual(result["evidence_alignment_accuracy"], 1.0)
        self.assertEqual(result["reasoning_consistency_accuracy"], 1.0)


    def test_evaluator_rejects_duplicate_decision_id(self) -> None:
        from scripts.research.evaluate_semantic_labels import evaluate_files

        output = json.loads((ROOT / "docs/gold-game/s5-semantic-label-output.example.json").read_text(encoding="utf-8"))
        output["labels"].append(output["labels"][0])
        dup_path = ROOT / "docs/gold-game/_dup_output.json"
        dup_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
        try:
            with self.assertRaisesRegex(ValueError, "duplicate decision_id"):
                evaluate_files(ROOT / "docs/gold-game/s5-semantic-label-eval-set.json", dup_path)
        finally:
            dup_path.unlink(missing_ok=True)

    def test_evaluator_rejects_missing_confidence(self) -> None:
        from scripts.research.evaluate_semantic_labels import evaluate_files

        output = json.loads((ROOT / "docs/gold-game/s5-semantic-label-output.example.json").read_text(encoding="utf-8"))
        del output["labels"][0]["confidence"]
        bad_path = ROOT / "docs/gold-game/_bad_output.json"
        bad_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
        try:
            with self.assertRaisesRegex(ValueError, "label missing fields"):
                evaluate_files(ROOT / "docs/gold-game/s5-semantic-label-eval-set.json", bad_path)
        finally:
            bad_path.unlink(missing_ok=True)

    def test_evaluator_accepts_80_percent_threshold(self) -> None:
        from scripts.research.evaluate_semantic_labels import evaluate_files

        output = json.loads((ROOT / "docs/gold-game/s5-semantic-label-output.example.json").read_text(encoding="utf-8"))
        output["labels"][0]["quality_label"] = "contradicted"
        bad_path = ROOT / "docs/gold-game/_bad_output.json"
        bad_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
        try:
            result = evaluate_files(ROOT / "docs/gold-game/s5-semantic-label-eval-set.json", bad_path)
            self.assertEqual(result["decision_count"], 5)
            self.assertEqual(result["quality_label_accuracy"], 0.8)
            self.assertTrue(result["valid"])
        finally:
            bad_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
