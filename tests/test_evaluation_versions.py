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
                self.assertEqual(
                    node.level, 0,
                    "forbidden relative import in evaluation_versions (would bypass the package-name check)",
                )


class PromptVersionTests(unittest.TestCase):
    def test_initial_prompt_version(self) -> None:
        from werewolf_eval.prompt_version import PROMPT_VERSION

        self.assertEqual(PROMPT_VERSION, "prompt_v1")

    def test_version_label_format(self) -> None:
        # Human-readable label, not a hash (review decision: hash is the lock,
        # the label is the product/leaderboard tag).
        from werewolf_eval.prompt_version import PROMPT_VERSION

        self.assertRegex(PROMPT_VERSION, r"^prompt_v\d+$")


class ProviderRuntimeKindTests(unittest.TestCase):
    def test_live_providers_declare_baseline_prompt_use(self) -> None:
        from werewolf_eval.llm_providers import BaseChatProvider

        self.assertEqual(BaseChatProvider.provider_runtime_kind, "live_model")
        self.assertTrue(BaseChatProvider.uses_baseline_prompt)

    def test_fake_provider_declares_no_prompt_use(self) -> None:
        from werewolf_eval.fake_provider import DeterministicFakeProvider

        self.assertEqual(
            DeterministicFakeProvider.provider_runtime_kind, "fake_deterministic"
        )
        self.assertFalse(DeterministicFakeProvider.uses_baseline_prompt)

    def test_deepseek_inherits_live_declaration(self) -> None:
        from werewolf_eval.deepseek_provider import DeepSeekProvider

        self.assertEqual(DeepSeekProvider.provider_runtime_kind, "live_model")
        self.assertTrue(DeepSeekProvider.uses_baseline_prompt)

    def test_g1h_private_fake_provider_also_declares(self) -> None:
        # run_g1h_fake_runtime has its OWN _DeterministicFakeProvider copy class
        # (no inheritance from the public one). Pin it so the g1h manifest can
        # never claim prompt_used_by_runtime=True (plan-review finding 3).
        from werewolf_eval.run_g1h_fake_runtime import _DeterministicFakeProvider

        self.assertEqual(
            _DeterministicFakeProvider.provider_runtime_kind, "fake_deterministic"
        )
        self.assertFalse(_DeterministicFakeProvider.uses_baseline_prompt)


class ReadManifestBucketTests(unittest.TestCase):
    def test_reads_bucket_from_stamped_manifest(self) -> None:
        import json
        import tempfile

        from werewolf_eval.evaluation_versions import read_manifest_bucket

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "prompt-manifest.json").write_text(
                json.dumps({"run_id": "r1", "evaluation_bucket": {
                    "rules_version": "rules_v1_1", "prompt_version": "prompt_v1",
                    "scoring_version": "scoring_v1",
                    "comparison_key": "rules_v1_1__prompt_v1__scoring_v1"}}),
                encoding="utf-8",
            )
            bucket = read_manifest_bucket(run_dir)
            self.assertEqual(bucket["comparison_key"], "rules_v1_1__prompt_v1__scoring_v1")

    def test_returns_none_for_legacy_or_missing_manifest(self) -> None:
        import tempfile

        from werewolf_eval.evaluation_versions import read_manifest_bucket

        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(read_manifest_bucket(Path(td)))


if __name__ == "__main__":
    unittest.main()
