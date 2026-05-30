# S5 Semantic Label Research Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Build a reproducible research harness for S5 semantic labels before any scoring integration.

**Architecture:** The PR adds research documentation, a strict saved-output label contract, a small manual eval set, a complete example output file, an offline evaluator, and unit tests. The evaluator reads JSON from disk and computes agreement metrics for the three contract axes. It does not call external services and does not change scoring.

**Tech Stack:** Python standard library only (`argparse`, `json`, `pathlib`, `unittest`), Markdown, JSON fixtures, existing `unittest` commands, existing tree refresh hook.

---

## Context

Current main has D2 and S4 complete. D2 connects Decision Log to deterministic scoring, but positive `decision_quality_score` is still intentionally held at 0 until semantic judgment is researched and reviewed. S4 adds Consensus Log input validation, which closes the collaboration input side. The next best step is S5 research, not gameplay and not scoring integration.

This revision also resolves three non-blocking review observations from PR #28:

- The random/default eval item now uses `g001_d008`, whose `decision_type` is `default`, instead of `g001_d006`, whose fields indicate a coordinated wolf speech.
- The eval set now includes `expected_reasoning_consistency`, matching the three-axis contract.
- The example output fixture is specified in full, so implementers do not need to infer the five label objects.

## Research PR Decision

Research PR is required.

Reasons:

- S5 requires evidence about output validity, label agreement, consistency, and cost before integration.
- The label contract must be reviewed before labels can become scoring input.
- Direct scoring integration would make `decision_quality_score` depend on unreviewed semantic output.

This plan is therefore for a research-harness PR. It prepares the artifacts needed to run and review S5 research. It does not implement S5 scoring.

## Global Forbidden Scope

Do not implement any of the following:

- No external service calls.
- No SDK or dependency additions.
- No secrets or environment-variable requirements.
- No changes to `src/werewolf_eval/scoring.py`.
- No generated Score Log changes.
- No generated demo HTML changes.
- No real gameplay engine.
- No Leaderboard aggregation.
- No modification to existing canonical Game Log, Decision Log, or Consensus Log contents.

## Files Overview

Create:

- `docs/prs/2026-05-30--s5-semantic-label-research.md`
- `docs/semantic-labeling/s5-label-contract.md`
- `docs/semantic-labeling/s5-label-prompts.md`
- `docs/gold-game/s5-semantic-label-eval-set.json`
- `docs/gold-game/s5-semantic-label-output.example.json`
- `scripts/research/evaluate_semantic_labels.py`
- `tests/test_semantic_label_research.py`

Modify:

- `.oh-my-harness/tree.md`

No other files should be changed.

---

### 任务 1：Add S5 research documentation

**文件：**
- 创建：`docs/prs/2026-05-30--s5-semantic-label-research.md`
- 创建：`docs/semantic-labeling/s5-label-contract.md`
- 创建：`docs/semantic-labeling/s5-label-prompts.md`
- 创建：`tests/test_semantic_label_research.py`
- 测试：`tests/test_semantic_label_research.py`

- [ ] **步骤 1：创建 research report**

Create `docs/prs/2026-05-30--s5-semantic-label-research.md` with this content:

```markdown
# S5 Semantic Label Research

## Decision

This PR prepares offline S5 research artifacts. It does not integrate semantic labels into scoring.

## Research Questions

1. Can saved semantic-label output follow the strict JSON contract?
2. Can every eval-set decision be covered exactly once?
3. Can semantic labels match the manual eval set at the required threshold?
4. Which label prompt is more stable on repeated saved-output runs?
5. Which invalid output shape should block scoring integration?

## Acceptance Thresholds

- Contract validity: 100%.
- Decision coverage: 100%.
- `quality_label` agreement: at least 80%.
- `evidence_alignment` agreement: at least 80%.
- `reasoning_consistency` agreement: at least 80%.
- Duplicate decisions, missing decisions, unknown labels, or out-of-range confidence values block integration.

## Required Validation Command

```bash
PYTHONPATH=. python scripts/research/evaluate_semantic_labels.py docs/gold-game/s5-semantic-label-eval-set.json docs/gold-game/s5-semantic-label-output.example.json
```

Expected output:

```text
s5_semantic_label_accuracy quality_label=1.000 evidence_alignment=1.000 reasoning_consistency=1.000 valid=true decisions=5
```
```

- [ ] **步骤 2：创建 label contract**

Create `docs/semantic-labeling/s5-label-contract.md` defining this saved-output JSON shape:

```json
{
  "label_log_id": "s5_g001_example",
  "game_id": "g001",
  "source_label": "[semantic research output]",
  "prompt_candidate": "candidate_a_minimal_json",
  "labels": [
    {
      "decision_id": "g001_d001",
      "quality_label": "supported_neutral",
      "evidence_alignment": "aligned",
      "reasoning_consistency": "consistent",
      "confidence": 0.8,
      "short_rationale": "The decision cites visible evidence and has a plausible target."
    }
  ]
}
```

Allowed `quality_label` values:

- `supported_good`
- `supported_neutral`
- `unsupported`
- `contradicted`
- `random_or_default`

Allowed `evidence_alignment` values:

- `aligned`
- `weak`
- `missing`
- `contradicted`

Allowed `reasoning_consistency` values:

- `consistent`
- `thin`
- `inconsistent`

`confidence` must be a number from `0.0` to `1.0`. `short_rationale` must be non-empty and at most 180 characters.

- [ ] **步骤 3：创建 prompt notes**

Create `docs/semantic-labeling/s5-label-prompts.md` with two candidates:

- `candidate_a_minimal_json`: shortest strict JSON instruction.
- `candidate_b_evidence_first_json`: evidence-first instruction that asks for label assignment from visible evidence and reason summary.

Both candidates must require output matching `s5-label-contract.md`. Both candidates must state that labels are research output only and must not assign numeric score values.

- [ ] **步骤 4：创建 docs existence test**

Create `tests/test_semantic_label_research.py`:

```python
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
```

Run:

```bash
PYTHONPATH=. python -m unittest tests.test_semantic_label_research.SemanticLabelDocsTests -v
```

Expected result after docs are created:

```text
Ran 1 test
OK
```

- [ ] **步骤 5：提交 task 1**

```bash
git add docs/prs/2026-05-30--s5-semantic-label-research.md docs/semantic-labeling/s5-label-contract.md docs/semantic-labeling/s5-label-prompts.md tests/test_semantic_label_research.py
git commit -m "research: add S5 semantic label contract"
```

---

### 任务 2：Add manual eval fixtures

**文件：**
- 创建：`docs/gold-game/s5-semantic-label-eval-set.json`
- 创建：`docs/gold-game/s5-semantic-label-output.example.json`
- 修改：`tests/test_semantic_label_research.py`
- 测试：`tests/test_semantic_label_research.py`

- [ ] **步骤 1：创建 eval set fixture**

Create `docs/gold-game/s5-semantic-label-eval-set.json`:

```json
{
  "eval_set_id": "s5_g001_manual_eval_set",
  "game_id": "g001",
  "source_decision_log": "docs/gold-game/g001-decision-log.json",
  "items": [
    {
      "decision_id": "g001_d001",
      "expected_quality_label": "supported_neutral",
      "expected_evidence_alignment": "aligned",
      "expected_reasoning_consistency": "consistent"
    },
    {
      "decision_id": "g001_d002",
      "expected_quality_label": "unsupported",
      "expected_evidence_alignment": "missing",
      "expected_reasoning_consistency": "thin"
    },
    {
      "decision_id": "g001_d003",
      "expected_quality_label": "unsupported",
      "expected_evidence_alignment": "missing",
      "expected_reasoning_consistency": "consistent"
    },
    {
      "decision_id": "g001_d008",
      "expected_quality_label": "random_or_default",
      "expected_evidence_alignment": "weak",
      "expected_reasoning_consistency": "thin"
    },
    {
      "decision_id": "g001_d010",
      "expected_quality_label": "supported_good",
      "expected_evidence_alignment": "aligned",
      "expected_reasoning_consistency": "consistent"
    }
  ],
  "notes": {
    "g001_d008": "This is the random/default eval example because its Decision Log decision_type is default. g001_d006 is not used for this label because it is team_coordinated and cites visible speech evidence."
  }
}
```

- [ ] **步骤 2：创建 complete example output fixture**

Create `docs/gold-game/s5-semantic-label-output.example.json` with this complete content:

```json
{
  "label_log_id": "s5_g001_example_output",
  "game_id": "g001",
  "source_label": "[semantic research output]",
  "prompt_candidate": "candidate_a_minimal_json",
  "labels": [
    {
      "decision_id": "g001_d001",
      "quality_label": "supported_neutral",
      "evidence_alignment": "aligned",
      "reasoning_consistency": "consistent",
      "confidence": 0.72,
      "short_rationale": "The wolf-team kill has visible setup evidence but the quality remains neutral until S5 scoring is designed."
    },
    {
      "decision_id": "g001_d002",
      "quality_label": "unsupported",
      "evidence_alignment": "missing",
      "reasoning_consistency": "thin",
      "confidence": 0.66,
      "short_rationale": "The seer check has no visible refs, so the stated inference is not evidence-supported in this contract."
    },
    {
      "decision_id": "g001_d003",
      "quality_label": "unsupported",
      "evidence_alignment": "missing",
      "reasoning_consistency": "consistent",
      "confidence": 0.7,
      "short_rationale": "The save rationale is coherent, but the Decision Log entry intentionally has no visible refs."
    },
    {
      "decision_id": "g001_d008",
      "quality_label": "random_or_default",
      "evidence_alignment": "weak",
      "reasoning_consistency": "thin",
      "confidence": 0.63,
      "short_rationale": "The decision_type is default, and the visible evidence gives only weak support for the vote."
    },
    {
      "decision_id": "g001_d010",
      "quality_label": "supported_good",
      "evidence_alignment": "aligned",
      "reasoning_consistency": "consistent",
      "confidence": 0.82,
      "short_rationale": "The final vote cites visible late-game evidence and targets a plausible wolf."
    }
  ]
}
```

- [ ] **步骤 3：追加 fixture tests**

Append to `tests/test_semantic_label_research.py`:

```python
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
```

Run:

```bash
PYTHONPATH=. python -m unittest tests.test_semantic_label_research.SemanticLabelFixtureTests -v
```

Expected result:

```text
Ran 2 tests
OK
```

- [ ] **步骤 4：提交 task 2**

```bash
git add docs/gold-game/s5-semantic-label-eval-set.json docs/gold-game/s5-semantic-label-output.example.json tests/test_semantic_label_research.py
git commit -m "research: add S5 semantic label eval fixtures"
```

---

### 任务 3：Add offline evaluator

**文件：**
- 创建：`scripts/research/evaluate_semantic_labels.py`
- 修改：`tests/test_semantic_label_research.py`
- 测试：`tests/test_semantic_label_research.py`

- [ ] **步骤 1：追加 evaluator test**

Append to `tests/test_semantic_label_research.py`:

```python
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
```

Run before implementation:

```bash
PYTHONPATH=. python -m unittest tests.test_semantic_label_research.SemanticLabelEvaluatorTests -v
```

Expected result before implementation:

```text
ModuleNotFoundError
```

- [ ] **步骤 2：实现 evaluator script**

Create `scripts/research/evaluate_semantic_labels.py` with a public function:

```python
def evaluate_files(eval_set_path, output_path):
    ...
```

Required behavior:

- Load both JSON files.
- Require matching `game_id`.
- Require every eval-set decision to appear exactly once in output labels.
- Reject unknown label values for all three axes.
- Reject confidence outside `[0.0, 1.0]`.
- Return `valid`, `decision_count`, `quality_label_accuracy`, `evidence_alignment_accuracy`, and `reasoning_consistency_accuracy`.
- CLI prints one line:

```text
s5_semantic_label_accuracy quality_label=1.000 evidence_alignment=1.000 reasoning_consistency=1.000 valid=true decisions=5
```

- [ ] **步骤 3：运行 evaluator test and CLI**

```bash
PYTHONPATH=. python -m unittest tests.test_semantic_label_research.SemanticLabelEvaluatorTests -v
PYTHONPATH=. python scripts/research/evaluate_semantic_labels.py docs/gold-game/s5-semantic-label-eval-set.json docs/gold-game/s5-semantic-label-output.example.json
```

Expected result:

```text
Ran 1 test
OK
s5_semantic_label_accuracy quality_label=1.000 evidence_alignment=1.000 reasoning_consistency=1.000 valid=true decisions=5
```

- [ ] **步骤 4：提交 task 3**

```bash
git add scripts/research/evaluate_semantic_labels.py tests/test_semantic_label_research.py
git commit -m "research: add S5 semantic label evaluator"
```

---

### 任务 4：Validate and refresh tree

**文件：**
- 修改：`.oh-my-harness/tree.md`
- 测试：`tests/test_semantic_label_research.py`

- [ ] **步骤 1：运行 S5 tests**

```bash
PYTHONPATH=. python -m unittest tests.test_semantic_label_research -v
```

Expected result:

```text
OK
```

- [ ] **步骤 2：运行 repository brief validation**

```bash
PYTHONPATH=. python scripts/dev/validate_brief.py
```

Expected result:

```json
{"ok": true}
```

The summary JSON may contain more fields, but `ok` must be true.

- [ ] **步骤 3：刷新 tree**

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md updated
```

- [ ] **步骤 4：提交 task 4**

```bash
git add .oh-my-harness/tree.md
git commit -m "chore: refresh tree for S5 semantic label research"
```

---

## Self-review Checklist

- Research PR requirement is explicit.
- No scoring or generated demo changes are included.
- Every task has exact files, commands, and expected results.
- The evaluator is offline and deterministic.
- Invalid saved-output behavior is rejected before scoring integration.
- The eval set covers all three semantic-label axes.
- `g001_d008`, not `g001_d006`, is the random/default eval example.

## PR Description Draft

Title:

```text
research: S5 semantic label harness
```

Body:

```markdown
## Summary

Prepare S5 semantic-label research artifacts without scoring integration.

Bound plan: `docs/harness/plans/2026-05-30--s5-semantic-label-research-plan.md`

## Changes

- Add S5 research report.
- Add semantic label contract and prompt notes.
- Add manual eval set and complete example saved output.
- Add offline evaluator and tests for all three contract axes.
- Refresh `.oh-my-harness/tree.md`.

## Validation

```bash
PYTHONPATH=. python -m unittest tests.test_semantic_label_research -v
PYTHONPATH=. python scripts/research/evaluate_semantic_labels.py docs/gold-game/s5-semantic-label-eval-set.json docs/gold-game/s5-semantic-label-output.example.json
PYTHONPATH=. python scripts/dev/validate_brief.py
node .codex/hooks/tree.mjs --force
```

## Boundaries

- No external service calls.
- No scoring changes.
- No generated demo changes.
- No gameplay engine.
```
