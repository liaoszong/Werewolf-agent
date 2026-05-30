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


if __name__ == "__main__":
    unittest.main()
