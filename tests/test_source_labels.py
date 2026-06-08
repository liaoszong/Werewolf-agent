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
            "[deterministic fake provider output]",
            "[DeepSeek API output]",
            "[OpenAI API output]",
            "[Anthropic API output]",
            "[OpenAI-compatible API output]",
        }
        self.assertEqual(VALID_SOURCE_LABELS, expected)

    def test_rejects_unknown_label(self) -> None:
        self.assertNotIn("[freeform mock output]", VALID_SOURCE_LABELS)
        self.assertNotIn("[unknown label]", VALID_SOURCE_LABELS)

    def test_rejects_generic_provider_labels(self) -> None:
        self.assertNotIn("[provider output]", VALID_SOURCE_LABELS)
        self.assertNotIn("[live provider output]", VALID_SOURCE_LABELS)


if __name__ == "__main__":
    unittest.main()
