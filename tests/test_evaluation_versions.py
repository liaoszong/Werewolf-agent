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
    rebase_bucket_to_current_scoring,
)


class EvaluationVersionsTests(unittest.TestCase):
    def test_scoring_version_current_value(self) -> None:
        # scoring_v2: default/random votes are filtered from model-vote process
        # metrics when a Decision Log is supplied. Bumping the formula splits the
        # comparison bucket so old/new results are never ranked together.
        self.assertEqual(SCORING_VERSION, "scoring_v2")

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
                "scoring_version": "scoring_v2",
                "comparison_key": "rules_v1_1__prompt_v1__scoring_v2",
            },
        )

    def test_bucket_requires_keyword_args(self) -> None:
        with self.assertRaises(TypeError):
            evaluation_bucket("rules_v1_1", "prompt_v1", "scoring_v2")  # type: ignore[misc]

    def test_unknown_components_form_browsable_key(self) -> None:
        b = evaluation_bucket(
            rules_version=UNKNOWN_VERSION,
            prompt_version=UNKNOWN_VERSION,
            scoring_version=SCORING_VERSION,
        )
        self.assertEqual(b["comparison_key"], "unknown__unknown__scoring_v2")

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


class RebaseBucketToCurrentScoringTests(unittest.TestCase):
    """scoring_v2: re-scoring a historical run MUST stamp today's formula, never
    the manifest's historical scoring_version. rules/prompt are run-input history
    and are preserved; only scoring_version is forced current."""

    def test_v1_manifest_bucket_is_rebased_to_current_scoring(self) -> None:
        historical = {
            "rules_version": "rules_v1_2",
            "prompt_version": "prompt_v4",
            "scoring_version": "scoring_v1",
            "comparison_key": "rules_v1_2__prompt_v4__scoring_v1",
        }
        rebased = rebase_bucket_to_current_scoring(historical)
        # rules + prompt preserved as legitimate run-input history.
        self.assertEqual(rebased["rules_version"], "rules_v1_2")
        self.assertEqual(rebased["prompt_version"], "prompt_v4")
        # scoring forced to the current formula; key rebuilt by evaluation_bucket().
        self.assertEqual(rebased["scoring_version"], "scoring_v2")
        self.assertEqual(rebased["comparison_key"], "rules_v1_2__prompt_v4__scoring_v2")

    def test_none_yields_unknown_unknown_current_bucket(self) -> None:
        rebased = rebase_bucket_to_current_scoring(None)
        self.assertEqual(rebased["scoring_version"], "scoring_v2")
        self.assertEqual(rebased["comparison_key"], "unknown__unknown__scoring_v2")

    def test_current_scoring_bucket_is_idempotent(self) -> None:
        current = evaluation_bucket(
            rules_version="rules_v1_1",
            prompt_version="prompt_v1",
            scoring_version="scoring_v2",
        )
        rebased = rebase_bucket_to_current_scoring(current)
        self.assertEqual(rebased, current)
        self.assertEqual(rebased["comparison_key"], "rules_v1_1__prompt_v1__scoring_v2")

    def test_missing_or_non_str_components_fall_back_to_unknown(self) -> None:
        rebased = rebase_bucket_to_current_scoring(
            {"rules_version": "", "prompt_version": None, "scoring_version": "scoring_v1"}
        )
        self.assertEqual(rebased["rules_version"], "unknown")
        self.assertEqual(rebased["prompt_version"], "unknown")
        self.assertEqual(rebased["scoring_version"], "scoring_v2")


if __name__ == "__main__":
    unittest.main()
