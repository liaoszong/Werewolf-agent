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


if __name__ == "__main__":
    unittest.main()
