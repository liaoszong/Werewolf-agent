from __future__ import annotations

import unittest

from werewolf_eval.source_labels import VALID_SOURCE_LABELS


class SourceLabelsTests(unittest.TestCase):
    def test_expected_labels_present(self) -> None:
        expected = {
            "[人工 gold sample]",
            "[AI 生成]",
            "[scripted deterministic output]",
            "[deterministic mock agent output]",
        }
        self.assertEqual(VALID_SOURCE_LABELS, expected)

    def test_rejects_unknown_label(self) -> None:
        self.assertNotIn("[freeform mock output]", VALID_SOURCE_LABELS)
        self.assertNotIn("[unknown label]", VALID_SOURCE_LABELS)


if __name__ == "__main__":
    unittest.main()
