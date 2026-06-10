from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.evaluation_versions import (
    SCORING_VERSION,
    UNKNOWN_VERSION,
    evaluation_bucket,
)


class EvaluationVersionsTests(unittest.TestCase):
    def test_scoring_version_initial_value(self) -> None:
        self.assertEqual(SCORING_VERSION, "scoring_v1")

    def test_unknown_version_sentinel(self) -> None:
        self.assertEqual(UNKNOWN_VERSION, "unknown")

    def test_bucket_shape_and_key_format(self) -> None:
        b = evaluation_bucket(
            rules_version="rules_v1_1",
            prompt_version="prompt_v1",
            scoring_version=SCORING_VERSION,
        )
        self.assertEqual(
            b,
            {
                "rules_version": "rules_v1_1",
                "prompt_version": "prompt_v1",
                "scoring_version": "scoring_v1",
                "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
            },
        )

    def test_bucket_requires_keyword_args(self) -> None:
        with self.assertRaises(TypeError):
            evaluation_bucket("rules_v1_1", "prompt_v1", "scoring_v1")  # type: ignore[misc]

    def test_unknown_components_form_browsable_key(self) -> None:
        b = evaluation_bucket(
            rules_version=UNKNOWN_VERSION,
            prompt_version=UNKNOWN_VERSION,
            scoring_version=SCORING_VERSION,
        )
        self.assertEqual(b["comparison_key"], "unknown__unknown__scoring_v1")

    def test_module_has_no_werewolf_eval_imports(self) -> None:
        # Anti-circular-import contract (spec §4.1): callers of the tuple must not
        # transitively import scoring or any other werewolf_eval module.
        # AST-based on purpose: a substring check would be tripped by the module's
        # own docstring mentioning the package name (plan-review finding 4).
        import ast

        import werewolf_eval.evaluation_versions as ev

        tree = ast.parse(Path(ev.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                bad = [a.name for a in node.names if a.name.startswith("werewolf_eval")]
                self.assertFalse(bad, f"forbidden import: {bad}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                self.assertFalse(mod.startswith("werewolf_eval"), f"forbidden import from: {mod}")


class PromptVersionTests(unittest.TestCase):
    def test_initial_prompt_version(self) -> None:
        from werewolf_eval.prompt_version import PROMPT_VERSION

        self.assertEqual(PROMPT_VERSION, "prompt_v1")

    def test_version_label_format(self) -> None:
        # Human-readable label, not a hash (review decision: hash is the lock,
        # the label is the product/leaderboard tag).
        from werewolf_eval.prompt_version import PROMPT_VERSION

        self.assertRegex(PROMPT_VERSION, r"^prompt_v\d+$")


if __name__ == "__main__":
    unittest.main()
