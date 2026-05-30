# S5 Semantic Label Scoring Integration Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Integrate saved S5 semantic label outputs into deterministic `decision_quality_score` while preserving the no-provider-call boundary.

**Architecture:** Add a first-class Semantic Label Log runtime input, validate it against the existing Decision Log, and pass it into scoring as an optional third input. Scoring remains deterministic: saved semantic labels are converted to integer decision-quality scores through a fixed mapping, while missing labels and invalid labels never trigger model calls or repair logic.

**Tech Stack:** Python standard library only (`argparse`, `dataclasses`, `json`, `pathlib`, `unittest`, `subprocess`), existing `werewolf_eval` package, existing JSON gold fixtures, existing `scripts/dev/validate_brief.py`, existing tree refresh hook.

---

## Context

PR #29 completed the S5 semantic-label research harness. Main now has:

- `docs/semantic-labeling/s5-label-contract.md`
- `docs/gold-game/s5-semantic-label-eval-set.json`
- `docs/gold-game/s5-semantic-label-output.example.json`
- `scripts/research/evaluate_semantic_labels.py`
- `tests/test_semantic_label_research.py`

D2 currently connects Decision Log to scoring, but `_assess_decision()` still keeps positive `decision_quality_score` at 0 and explicitly says positive scoring waits for S5 semantic judgment. This plan turns the saved S5 label output into deterministic scoring input. It does not call a provider and does not implement live AI labeling.

## Research PR Decision

No new Research PR is needed.

Reasoning:

- The S5 research harness already exists and was merged in PR #29.
- The next task boundary is clear: consume a saved semantic-label JSON file and map its labels into deterministic scores.
- This is a single implementation unit across parser, scorer, CLI, demo, generated outputs, and tests.
- Provider selection, prompt experiments, and live model calls remain outside this task.

## Scoring Mapping

Use this fixed mapping for S5 `decision_quality_score`:

```text
supported_good      -> +2
supported_neutral   -> +1
random_or_default   ->  0
unsupported         -> -1
contradicted        -> -2
```

Additional rules:

- If no Semantic Label Log is supplied, current D2 behavior remains unchanged.
- If a Semantic Label Log is supplied and a scored decision has no semantic label, keep D2 score 0 and add `rubric:G.1.semantic_label_missing`.
- If deterministic D2 visibility checks find illegal visible info refs, keep `decision_quality_score = 0`, keep `rule_integrity_score = -3`, and do not apply semantic-label scoring to that record.
- `evidence_alignment` and `reasoning_consistency` are stored in rules / notes for traceability but do not directly add extra points in this PR.
- Semantic labels for non-score-relevant decisions may validate, but they do not create new Score Records.

## Global Forbidden Scope

Do not implement any of the following:

- No provider API calls.
- No SDK or dependency additions.
- No secrets or environment-variable requirements.
- No network calls.
- No prompt execution.
- No live semantic labeling.
- No Consensus Log scoring.
- No gameplay engine.
- No multi-game Leaderboard aggregation.
- No changes to existing Game Log, Decision Log, or Consensus Log canonical content.
- No automatic repair of invalid semantic-label output.

## Files Overview

Create:

- `src/werewolf_eval/semantic_labels.py`
  - Parser / validator / dataclasses for saved Semantic Label Log JSON.
- `src/werewolf_eval/validate_semantic_labels.py`
  - CLI validator for a Decision Log + Semantic Label Log pair.
- `tests/test_semantic_labels.py`
  - Unit tests for Semantic Label Log parsing, validation, and CLI behavior.
- `docs/gold-game/s5-score-log.json`
  - Canonical S5 Score Log generated with Game Log + Decision Log + saved Semantic Label Log.
- `docs/gold-game/s5-metrics-summary.json`
  - Canonical S5 Metrics Summary generated from `s5-score-log.json`.
- `docs/demo/phase2-s5-runtime-demo.html`
  - Single-file generated demo showing S5 saved-label scoring boundary.

Modify:

- `src/werewolf_eval/scoring.py`
  - Accept optional Semantic Label Log and apply deterministic label-to-score mapping.
- `src/werewolf_eval/score_game.py`
  - Add `--semantic-labels` CLI option.
- `src/werewolf_eval/render_demo.py`
  - Add optional semantic-label input and S5 boundary copy.
- `tests/test_scoring.py`
  - Add S5 scoring tests and CLI tests.
- `tests/test_render_demo.py`
  - Add S5 demo boundary tests.
- `README.md`
  - Update current status to mention saved semantic labels can now feed deterministic scoring.
- `docs/TASKS.md`
  - Mark S5 scoring integration as complete after implementation and record outputs.
- `.oh-my-harness/tree.md`
  - Refresh after adding files.

No other files should be modified.

---

### 任务 1：Add Semantic Label Log runtime input

**文件：**
- 创建：`src/werewolf_eval/semantic_labels.py`
- 创建：`src/werewolf_eval/validate_semantic_labels.py`
- 创建：`tests/test_semantic_labels.py`
- 测试：`tests/test_semantic_labels.py`

- [ ] **步骤 1：编写 failing tests**

Create `tests/test_semantic_labels.py` with this initial content:

```python
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
```

- [ ] **步骤 2：运行测试确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_semantic_labels -v
```

Expected result before implementation:

```text
ModuleNotFoundError: No module named 'werewolf_eval.semantic_labels'
```

- [ ] **步骤 3：实现 `semantic_labels.py`**

Create `src/werewolf_eval/semantic_labels.py` with these public objects:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.decision_log import DecisionLog

VALID_QUALITY_LABELS = {"supported_good", "supported_neutral", "unsupported", "contradicted", "random_or_default"}
VALID_EVIDENCE_ALIGNMENTS = {"aligned", "weak", "missing", "contradicted"}
VALID_REASONING_CONSISTENCIES = {"consistent", "thin", "inconsistent"}
VALID_SOURCE_LABELS = {"[semantic research output]"}
VALID_PROMPT_CANDIDATES = {"candidate_a_minimal_json", "candidate_b_evidence_first_json"}
MAX_RATIONALE_CHARS = 180

@dataclass(frozen=True)
class SemanticLabel:
    decision_id: str
    quality_label: str
    evidence_alignment: str
    reasoning_consistency: str
    confidence: float
    short_rationale: str

@dataclass(frozen=True)
class SemanticLabelLog:
    label_log_id: str
    game_id: str
    source_label: str
    prompt_candidate: str
    labels: list[SemanticLabel]

    @property
    def label_by_decision_id(self) -> dict[str, SemanticLabel]:
        return {label.decision_id: label for label in self.labels}

class SemanticLabelValidationError(ValueError):
    """Raised when a Semantic Label Log cannot be accepted as saved S5 input."""
```

Implement `load_semantic_label_log(path: str | Path, decision_log: DecisionLog) -> SemanticLabelLog` and `parse_semantic_label_log(raw: dict[str, Any], decision_log: DecisionLog) -> SemanticLabelLog` with these checks:

- root is an object;
- top-level fields are exactly sufficient: `label_log_id`, `game_id`, `source_label`, `prompt_candidate`, `labels`;
- `game_id` equals `decision_log.game_id`;
- `source_label` is `[semantic research output]`;
- `prompt_candidate` is one of the two known candidates;
- `labels` is a list;
- each label has all fields from the S5 contract;
- each `decision_id` exists in `decision_log.decision_ids`;
- no duplicate `decision_id` values;
- enum fields are known;
- `confidence` is numeric, not boolean, and in `[0.0, 1.0]`;
- `short_rationale` is non-empty and at most 180 characters.

- [ ] **步骤 4：实现 validator CLI**

Create `src/werewolf_eval/validate_semantic_labels.py`:

```python
from __future__ import annotations

import argparse

from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.game_log import load_game_log
from werewolf_eval.semantic_labels import load_semantic_label_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate saved S5 Semantic Label Log JSON.")
    parser.add_argument("game_log_path")
    parser.add_argument("decision_log_path")
    parser.add_argument("semantic_label_path")
    args = parser.parse_args()

    game = load_game_log(args.game_log_path)
    decision_log = load_decision_log(args.decision_log_path, game)
    label_log = load_semantic_label_log(args.semantic_label_path, decision_log)

    print(f"validated semantic_label_log_id={label_log.label_log_id}")
    print(f"game_id={label_log.game_id}")
    print(f"labels={len(label_log.labels)}")
    print(f"source_label={label_log.source_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 5：运行测试确认通过**

```bash
PYTHONPATH=src python -m unittest tests.test_semantic_labels -v
```

Expected result:

```text
Ran 4 tests
OK
```

- [ ] **步骤 6：提交 task 1**

```bash
git add src/werewolf_eval/semantic_labels.py src/werewolf_eval/validate_semantic_labels.py tests/test_semantic_labels.py
git commit -m "feat: add semantic label log input"
```

---

### 任务 2：Integrate semantic labels into scoring

**文件：**
- 修改：`src/werewolf_eval/scoring.py`
- 修改：`tests/test_scoring.py`
- 创建：`docs/gold-game/s5-score-log.json`
- 创建：`docs/gold-game/s5-metrics-summary.json`
- 测试：`tests/test_scoring.py`

- [ ] **步骤 1：编写 failing scoring tests**

Modify `tests/test_scoring.py` imports:

```python
from werewolf_eval.semantic_labels import load_semantic_label_log
```

Extend `setUp()`:

```python
self.semantic_label_log = load_semantic_label_log(
    ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
    self.decision_log,
)
self.s5_score_log = score_game(
    self.game,
    decision_log=self.decision_log,
    semantic_label_log=self.semantic_label_log,
)
self.s5_metrics = summarize_metrics(self.game, self.s5_score_log)
```

Add these tests:

```python
def test_s5_semantic_labels_assign_decision_quality_scores(self) -> None:
    records = {record.event_id: record for record in self.s5_score_log.records}

    self.assertEqual(records["g001_e007"].decision_id, "g001_d001")
    self.assertEqual(records["g001_e007"].decision_quality_score, 1)
    self.assertIn("rubric:G.1.semantic.supported_neutral", records["g001_e007"].rules_triggered)

    self.assertEqual(records["g001_e008"].decision_id, "g001_d002")
    self.assertEqual(records["g001_e008"].decision_quality_score, -1)
    self.assertIn("rubric:G.1.semantic.unsupported", records["g001_e008"].rules_triggered)

    self.assertEqual(records["g001_e009"].decision_id, "g001_d003")
    self.assertEqual(records["g001_e009"].decision_quality_score, -1)
    self.assertIn("rubric:G.1.semantic.unsupported", records["g001_e009"].rules_triggered)

    self.assertEqual(records["g001_e020"].decision_id, "g001_d008")
    self.assertEqual(records["g001_e020"].decision_quality_score, 0)
    self.assertIn("rubric:G.1.semantic.random_or_default", records["g001_e020"].rules_triggered)

    self.assertEqual(records["g001_e035"].decision_id, "g001_d010")
    self.assertEqual(records["g001_e035"].decision_quality_score, 2)
    self.assertIn("rubric:G.1.semantic.supported_good", records["g001_e035"].rules_triggered)


def test_s5_missing_label_keeps_score_zero_and_records_rule(self) -> None:
    records = {record.event_id: record for record in self.s5_score_log.records}

    self.assertEqual(records["g001_e019"].decision_id, "g001_d007")
    self.assertEqual(records["g001_e019"].decision_quality_score, 0)
    self.assertIn("rubric:G.1.semantic_label_missing", records["g001_e019"].rules_triggered)


def test_s5_metrics_summary_reflects_semantic_scores(self) -> None:
    payload = metrics_summary_to_dict(self.s5_metrics)
    decision_scores = payload["score_summary"]["player_decision_quality_scores"]
    self.assertEqual(decision_scores["p3"], -1)
    self.assertEqual(decision_scores["p4"], -1)
    self.assertEqual(decision_scores["p6"], 2)
    self.assertEqual(sum(decision_scores.values()), 0)
    self.assertEqual(payload["score_summary"]["team_outcome_scores"]["wolf_team"], 3)
```

Also add a canonical output test:

```python
def test_s5_score_outputs_match_expected_files(self) -> None:
    score_payload = score_log_to_dict(self.s5_score_log)
    metrics_payload = metrics_summary_to_dict(self.s5_metrics)
    self.assertEqual(score_payload, load_json("docs/gold-game/s5-score-log.json"))
    self.assertEqual(metrics_payload, load_json("docs/gold-game/s5-metrics-summary.json"))
```

- [ ] **步骤 2：运行测试确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring.DeterministicScorerTests -v
```

Expected result before implementation:

```text
TypeError: score_game() got an unexpected keyword argument 'semantic_label_log'
```

- [ ] **步骤 3：修改 `scoring.py` data flow**

Modify imports:

```python
from werewolf_eval.semantic_labels import SemanticLabel, SemanticLabelLog
```

Add mapping helpers:

```python
SEMANTIC_QUALITY_SCORE_BY_LABEL = {
    "supported_good": 2,
    "supported_neutral": 1,
    "random_or_default": 0,
    "unsupported": -1,
    "contradicted": -2,
}


def _semantic_rule(label: SemanticLabel) -> str:
    return f"rubric:G.1.semantic.{label.quality_label}"
```

Extend `DecisionAssessment` to keep existing fields and continue returning one object per record. Modify `_assess_decision()` signature to:

```python
def _assess_decision(game: GameLog, decision: Decision | None, semantic_label: SemanticLabel | None = None) -> DecisionAssessment:
```

Required behavior:

- no decision: unchanged;
- illegal refs: unchanged except notes may say S5 skipped because deterministic integrity failed;
- semantic label missing while label log is enabled: score 0 and add `rubric:G.1.semantic_label_missing`;
- semantic label present: set `decision_quality_score` from `SEMANTIC_QUALITY_SCORE_BY_LABEL`, append `_semantic_rule(label)`, include existing visible-info evidence ids, and add a note containing `label.evidence_alignment`, `label.reasoning_consistency`, and `label.short_rationale`.

Modify `score_game()` signature:

```python
def score_game(game: GameLog, decision_log: DecisionLog | None = None, semantic_label_log: SemanticLabelLog | None = None) -> ScoreLog:
```

Inside `score_game()`, build:

```python
labels_by_decision = semantic_label_log.label_by_decision_id if semantic_label_log else {}
```

Pass the matching label to `_assess_decision()`:

```python
decision = decisions_by_event.get(event.event_id)
semantic_label = labels_by_decision.get(decision.decision_id) if decision else None
assessment = _assess_decision(game, decision, semantic_label)
```

Update `ScoreLog.source_label`, `phase`, and `scoring_boundary`:

- no Decision Log: existing Phase 1 behavior;
- Decision Log only: existing D2 behavior;
- Decision Log + Semantic Label Log: `source_label = "[deterministic][decision-log][semantic-labels]"`, `phase = "Phase 2B-S5"`.

- [ ] **步骤 4：generate canonical S5 outputs**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --semantic-labels docs/gold-game/s5-semantic-label-output.example.json --score-log-out docs/gold-game/s5-score-log.json --metrics-out docs/gold-game/s5-metrics-summary.json
```

Expected result:

```text
scored game_id=g001
score_records=14
winner=villager
game_length=3
wolf_team_outcome_score=3
decision_log=enabled
semantic_labels=enabled
decision_quality_total=1
```

- [ ] **步骤 5：运行 scoring tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring.DeterministicScorerTests -v
```

Expected result:

```text
OK
```

- [ ] **步骤 6：提交 task 2**

```bash
git add src/werewolf_eval/scoring.py tests/test_scoring.py docs/gold-game/s5-score-log.json docs/gold-game/s5-metrics-summary.json
git commit -m "feat: apply semantic labels to decision scoring"
```

---

### 任务 3：Add CLI support for saved semantic labels

**文件：**
- 修改：`src/werewolf_eval/score_game.py`
- 修改：`tests/test_scoring.py`
- 测试：`tests/test_scoring.py`

- [ ] **步骤 1：add failing CLI test**

Append to `tests/test_scoring.py`:

```python
def test_score_game_cli_accepts_semantic_labels(self) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "werewolf_eval.score_game",
            str(ROOT / "docs/gold-game/g001-game-log.json"),
            "--decision-log",
            str(ROOT / "docs/gold-game/g001-decision-log.json"),
            "--semantic-labels",
            str(ROOT / "docs/gold-game/s5-semantic-label-output.example.json"),
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=True,
    )

    self.assertIn("decision_log=enabled", result.stdout)
    self.assertIn("semantic_labels=enabled", result.stdout)
    self.assertIn("decision_quality_total=1", result.stdout)
```

Also add:

```python
def test_score_game_cli_rejects_semantic_labels_without_decision_log(self) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "werewolf_eval.score_game",
            str(ROOT / "docs/gold-game/g001-game-log.json"),
            "--semantic-labels",
            str(ROOT / "docs/gold-game/s5-semantic-label-output.example.json"),
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
    )

    self.assertNotEqual(result.returncode, 0)
    self.assertIn("--semantic-labels requires --decision-log", result.stderr)
```

- [ ] **步骤 2：run tests and confirm CLI failure**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring.DeterministicScorerTests.test_score_game_cli_accepts_semantic_labels tests.test_scoring.DeterministicScorerTests.test_score_game_cli_rejects_semantic_labels_without_decision_log -v
```

Expected result before implementation:

```text
error: unrecognized arguments: --semantic-labels
```

- [ ] **步骤 3：modify `score_game.py`**

Update imports:

```python
from werewolf_eval.semantic_labels import load_semantic_label_log
```

Add parser option:

```python
parser.add_argument("--semantic-labels", help="Optional path to saved S5 Semantic Label Log JSON. Requires --decision-log.")
```

After loading `decision_log`, add:

```python
if args.semantic_labels and decision_log is None:
    parser.error("--semantic-labels requires --decision-log")
semantic_label_log = load_semantic_label_log(args.semantic_labels, decision_log) if args.semantic_labels else None
score_log = score_game(game, decision_log=decision_log, semantic_label_log=semantic_label_log)
```

Print semantic-label status:

```python
print(f"semantic_labels={'enabled' if semantic_label_log else 'disabled'}")
```

- [ ] **步骤 4：run CLI tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring.DeterministicScorerTests.test_score_game_cli_accepts_semantic_labels tests.test_scoring.DeterministicScorerTests.test_score_game_cli_rejects_semantic_labels_without_decision_log -v
```

Expected result:

```text
Ran 2 tests
OK
```

- [ ] **步骤 5：提交 task 3**

```bash
git add src/werewolf_eval/score_game.py tests/test_scoring.py
git commit -m "feat: add semantic label scoring CLI"
```

---

### 任务 4：Add S5 runtime demo output

**文件：**
- 修改：`src/werewolf_eval/render_demo.py`
- 修改：`tests/test_render_demo.py`
- 创建：`docs/demo/phase2-s5-runtime-demo.html`
- 测试：`tests/test_render_demo.py`

- [ ] **步骤 1：add failing render tests**

Modify imports in `tests/test_render_demo.py`:

```python
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.semantic_labels import load_semantic_label_log
```

Extend `setUp()`:

```python
self.decision_log = load_decision_log(ROOT / "docs/gold-game/g001-decision-log.json", self.game)
self.semantic_label_log = load_semantic_label_log(
    ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
    self.decision_log,
)
self.s5_score_log = score_game(
    self.game,
    decision_log=self.decision_log,
    semantic_label_log=self.semantic_label_log,
)
self.s5_metrics = summarize_metrics(self.game, self.s5_score_log)
self.s5_attribution = attribute_game(self.game, self.s5_score_log, self.s5_metrics)
```

Add:

```python
def test_render_html_with_semantic_labels_shows_s5_boundary(self) -> None:
    context = build_demo_context(self.game, self.s5_score_log, self.s5_metrics, self.s5_attribution)
    html = render_html(context)

    self.assertIn("S5 saved semantic labels", html)
    self.assertIn("decision_quality_total", html)
    self.assertIn("not live AI labeling", html)
    self.assertIn("[semantic-labels]", html)
    self.assertNotIn("https://", html)


def test_write_demo_html_accepts_semantic_labels(self) -> None:
    output = ROOT / "docs/demo/test-phase2-s5-runtime-demo.html"
    try:
        write_demo_html(
            ROOT / "docs/gold-game/g001-game-log.json",
            output,
            ROOT / "docs/gold-game/g001-decision-log.json",
            ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
        )
        html = output.read_text(encoding="utf-8")
        self.assertIn("S5 saved semantic labels", html)
        self.assertIn("decision_quality_total", html)
    finally:
        output.unlink(missing_ok=True)
```

- [ ] **步骤 2：run render tests and confirm failure**

```bash
PYTHONPATH=src python -m unittest tests.test_render_demo.RuntimeDemoRenderTests -v
```

Expected result before implementation:

```text
TypeError: write_demo_html() takes from 2 to 3 positional arguments but 4 were given
```

- [ ] **步骤 3：modify `render_demo.py`**

Update imports:

```python
from werewolf_eval.semantic_labels import load_semantic_label_log
```

Update `build_demo_context()` to detect S5:

```python
semantic_labels_enabled = score_payload["phase"] == "Phase 2B-S5"
```

Use S5 copy when enabled:

```python
boundary_copy = "This is not real AI Agent gameplay, not live AI labeling, and not a real multi-model Leaderboard. S5 saved semantic labels are connected to deterministic scoring; no provider call is made during rendering."
decision_copy = f"decision_quality_score: S5 saved semantic labels enabled; decision_quality_total={decision_quality_total}."
```

Update leaderboard deterministic row:

```python
avg_decision_quality_score = decision_quality_total / max(len(score_payload["records"]), 1)
source_label = "[deterministic][semantic-labels]" if semantic_labels_enabled else "[deterministic]"
```

Update `write_demo_html()` signature:

```python
def write_demo_html(game_log_path, output_path, decision_log_path=None, semantic_label_path=None) -> None:
```

Inside it:

```python
decision_log = load_decision_log(decision_log_path, game) if decision_log_path else None
if semantic_label_path and decision_log is None:
    raise ValueError("semantic_label_path requires decision_log_path")
semantic_label_log = load_semantic_label_log(semantic_label_path, decision_log) if semantic_label_path else None
score_log = score_game(game, decision_log=decision_log, semantic_label_log=semantic_label_log)
```

Add CLI option:

```python
parser.add_argument("--semantic-labels", help="Optional saved S5 Semantic Label Log JSON. Requires --decision-log.")
```

Pass it to `write_demo_html()`.

- [ ] **步骤 4：generate S5 runtime demo**

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --semantic-labels docs/gold-game/s5-semantic-label-output.example.json --html-out docs/demo/phase2-s5-runtime-demo.html
```

Expected result:

```text
rendered_demo_html=docs/demo/phase2-s5-runtime-demo.html
```

- [ ] **步骤 5：run render tests**

```bash
PYTHONPATH=src python -m unittest tests.test_render_demo.RuntimeDemoRenderTests -v
```

Expected result:

```text
OK
```

- [ ] **步骤 6：提交 task 4**

```bash
git add src/werewolf_eval/render_demo.py tests/test_render_demo.py docs/demo/phase2-s5-runtime-demo.html
git commit -m "feat: render S5 semantic label demo"
```

---

### 任务 5：Update status docs and run full validation

**文件：**
- 修改：`README.md`
- 修改：`docs/TASKS.md`
- 修改：`.oh-my-harness/tree.md`
- 测试：`tests/test_semantic_labels.py`、`tests/test_scoring.py`、`tests/test_render_demo.py`

- [ ] **步骤 1：update README status**

Modify `README.md` current status to say:

```markdown
**Phase 1 deterministic MVP 已完成，Phase 2 evaluator runtime 已接入 saved S5 semantic labels。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer、E3 rule attribution engine、E4 runtime demo HTML exporter、D1 Decision Log runtime input、D2 Decision Log deterministic scoring integration、S4 Consensus Log runtime input、S5 saved semantic-label research harness and scoring integration。当前仍不代表真实 AI Agent 对局、live AI semantic labeling、真实多模型 Leaderboard 或 provider integration 已完成；S5 只消费已保存的 semantic-label JSON，不在运行时调用模型。
```

- [ ] **步骤 2：update TASKS status**

In `docs/TASKS.md`, update the S5 section to:

```markdown
### S5：AI semantic labeling research and saved-label scoring integration

- 状态：`completed`（Phase 2B semantic input；saved semantic labels can feed deterministic `decision_quality_score`）
- 产出：`docs/semantic-labeling/s5-label-contract.md` + `docs/gold-game/s5-semantic-label-output.example.json` + `src/werewolf_eval/semantic_labels.py` + `src/werewolf_eval/validate_semantic_labels.py` + `scripts/research/evaluate_semantic_labels.py` + `tests/test_semantic_labels.py` + `tests/test_semantic_label_research.py`。
- 依赖：D1 + D2。
- 目标：用已保存的 Semantic Label Log 为 Decision Log 对应 Score Records 赋 deterministic `decision_quality_score`。
- 边界：不做 provider integration，不做 live AI labeling，不做 gameplay，不做 multi-game Leaderboard。
```

Add a Demo Acceptance entry:

```markdown
**Demo 6：Phase 2 S5 saved semantic-label scoring**

- 状态：`completed`（`docs/demo/phase2-s5-runtime-demo.html`）
- 触发条件：S5 saved-label scoring integration 完成。
- 演示内容：运行时读取 Game Log + Decision Log + saved Semantic Label Log → 计算 Score Log / Metrics Summary → 输出带 S5 边界声明的 HTML demo。
- 验收：页面明确说明 semantic labels 来自 saved JSON，不是 live AI labeling；Score Log 中部分 `decision_quality_score` 不再全为 0；`decision_quality_total=1` 可追溯到 label rules。
```

- [ ] **步骤 3：run targeted tests**

```bash
PYTHONPATH=src python -m unittest tests.test_semantic_labels tests.test_scoring tests.test_render_demo -v
```

Expected result:

```text
OK
```

- [ ] **步骤 4：run full validation summary**

```bash
PYTHONPATH=src python scripts/dev/validate_brief.py
```

Expected result:

```json
{"ok": true}
```

The JSON may include more fields. `ok` must be `true` and failed commands must be empty.

- [ ] **步骤 5：check whitespace**

```bash
git diff --check
```

Expected result:

```text
```

No output means success.

- [ ] **步骤 6：refresh tree**

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md updated
```

If the hook prints a different success line but updates `.oh-my-harness/tree.md`, record that exact output in the PR body.

- [ ] **步骤 7：提交 task 5**

```bash
git add README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: update S5 scoring integration status"
```

---

## Final Validation Commands

Run all of these before review:

```bash
PYTHONPATH=src python -m unittest tests.test_semantic_label_research tests.test_semantic_labels tests.test_scoring tests.test_render_demo -v
PYTHONPATH=src python -m werewolf_eval.validate_semantic_labels docs/gold-game/g001-game-log.json docs/gold-game/g001-decision-log.json docs/gold-game/s5-semantic-label-output.example.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --semantic-labels docs/gold-game/s5-semantic-label-output.example.json --score-log-out docs/gold-game/s5-score-log.json --metrics-out docs/gold-game/s5-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --semantic-labels docs/gold-game/s5-semantic-label-output.example.json --html-out docs/demo/phase2-s5-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
```

Expected results:

```text
unittest: OK
validate_semantic_labels: validated semantic_label_log_id=s5_g001_example_output
score_game: decision_quality_total=1 and semantic_labels=enabled
render_demo: rendered_demo_html=docs/demo/phase2-s5-runtime-demo.html
validate_brief: ok=true
git diff --check: no output
```

## Self-review Checklist

- No provider calls are introduced.
- No new dependencies are introduced.
- Semantic labels are loaded from saved JSON only.
- Invalid labels fail closed through parser / validator errors.
- Existing D2 behavior is unchanged when `semantic_label_log` is not supplied.
- S5 score changes are visible in `s5-score-log.json` and `s5-metrics-summary.json`, not forced into existing D2 fixture names.
- Runtime demo states that labels are saved JSON, not live AI labeling.
- README and TASKS boundaries do not claim real Agent gameplay or provider integration.

## Implementation PR Description Draft

Title:

```text
feat: integrate saved S5 semantic labels into scoring
```

Body:

```markdown
## Summary

Integrate saved S5 Semantic Label Log output into deterministic `decision_quality_score`.

Bound plan: `docs/harness/plans/2026-05-31--s5-semantic-label-scoring-integration-plan.md`

## Changes

- Add Semantic Label Log parser / validator and CLI.
- Add deterministic label-to-score mapping for saved S5 labels.
- Add `--semantic-labels` support to scoring CLI and runtime demo CLI.
- Add S5 canonical Score Log / Metrics Summary outputs.
- Add `docs/demo/phase2-s5-runtime-demo.html` with explicit saved-label boundary.
- Update README / TASKS status.
- Refresh `.oh-my-harness/tree.md`.

## Validation

```bash
PYTHONPATH=src python -m unittest tests.test_semantic_label_research tests.test_semantic_labels tests.test_scoring tests.test_render_demo -v
PYTHONPATH=src python -m werewolf_eval.validate_semantic_labels docs/gold-game/g001-game-log.json docs/gold-game/g001-decision-log.json docs/gold-game/s5-semantic-label-output.example.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --semantic-labels docs/gold-game/s5-semantic-label-output.example.json --score-log-out docs/gold-game/s5-score-log.json --metrics-out docs/gold-game/s5-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --semantic-labels docs/gold-game/s5-semantic-label-output.example.json --html-out docs/demo/phase2-s5-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
```

## Boundaries

- No provider API calls.
- No network calls.
- No new dependencies.
- No live semantic labeling.
- No gameplay engine.
- No multi-game Leaderboard aggregation.
```
