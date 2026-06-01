# Pre-G1d Evaluation Trust Hardening Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** 在启动 G1d fake-provider contract 之前，把 Game / Decision / Consensus / Failure Audit 的关键评测信任缺口提升为可执行校验器和可审查证据。

**Architecture:** 本计划优先补强评测入口的 trust contract，而不是直接进入 live provider。实现方式是抽出统一 source label 分类、让 Game Log 顶层溯源成为必填校验项、增加 Failure Audit parser/validator、增加跨日志 bundle validator，并让 score/render CLI 在提供协作日志时记录 bundle validation 状态。最后修复 plan indexer 对英文 task heading 的识别，避免后续 Claude Code 违反 Context Budget Gate。

**Tech Stack:** Python stdlib, dataclasses, argparse, json, unittest, existing Werewolf-agent validators, existing review-packet generator.

---

## Decision

The next development point is **Pre-G1d Evaluation Trust Hardening**.

Reasoning:

- `docs/ROADMAP.md` and `docs/TASKS.md` identify G1d provider adapter research / fake-provider contract as the next G-track candidate.
- The 2026-06-01 project-wide healthcheck found that G1d can start only with strict provider/fake-provider boundaries, while several trust contracts are still weak:
  - Game Log top-level `source_label` is present in newer generated logs but is not required by `parse_game_log`.
  - Team Decision Log entries can still parse with `consensus_id = null` when Consensus Log is available.
  - Failure Audit has generated artifacts but no independent parser/validator.
  - Score/render can run without recording whether Consensus Log and Failure Audit were cross-validated.
  - G1b/G1c Implementation Plan indexes can return `task_count=0`, which weakens the Context Budget Gate.

This plan intentionally does **not** implement real provider calls. It creates the validator and review evidence surface that G1d should depend on.

## Context Budget Gate for Claude Code

Do not read this full plan during implementation. Use the context workflow below.

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-06-01--pre-g1d-evaluation-trust-hardening-plan.md
```

```bash
python - <<'PY'
import json
from pathlib import Path

plan = Path("docs/harness/plans/2026-06-01--pre-g1d-evaluation-trust-hardening-plan.md")
index_path = Path("docs/generated-context") / f"{plan.stem}.index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))

for task in index["tasks"]:
    print(f"{task['id']}: {task['title']} lines={task['line_start']}-{task['line_end']}")
PY
```

For each task, generate a minimal task context before editing:

```bash
python scripts/context/build_task_context.py docs/generated-context/2026-06-01--pre-g1d-evaluation-trust-hardening-plan.index.json <TASK_ID>
```

Read only:

```text
docs/generated-context/current-task.ctx.md
```

If that context is insufficient, read only the exact `Original plan lines` listed inside `current-task.ctx.md`.

## File Structure

### Create

- `src/werewolf_eval/source_labels.py`
  - Centralizes accepted source labels for Game / Decision / Consensus / Failure Audit.
- `src/werewolf_eval/failure_audit.py`
  - Parses and validates G1c/G1d failure audit artifacts.
- `src/werewolf_eval/validate_failure_audit.py`
  - CLI wrapper for failure audit validation.
- `src/werewolf_eval/log_bundle.py`
  - Cross-log validation for Game Log, Decision Log, Consensus Log, and Failure Audit.
- `src/werewolf_eval/validate_log_bundle.py`
  - CLI wrapper for bundle validation.
- `tests/test_source_labels.py`
  - Unit tests for shared source label validation.
- `tests/test_failure_audit.py`
  - Unit tests for failure audit parser/validator.
- `tests/test_log_bundle.py`
  - Unit tests for Decision/Consensus/Failure Audit cross-log invariants.

### Modify

- `src/werewolf_eval/game_log.py`
  - Add `source_label` to `GameLog`, require top-level `source_label`, and validate it through `source_labels.py`.
- `src/werewolf_eval/decision_log.py`
  - Import source labels from `source_labels.py` instead of maintaining a separate local set.
- `src/werewolf_eval/consensus_log.py`
  - Import source labels from `source_labels.py` instead of maintaining a separate local set.
- `src/werewolf_eval/score_game.py`
  - Add `--consensus-log` and `--failure-audit` arguments. When either is supplied, run bundle validation and write `bundle_validation` metadata into output JSON.
- `src/werewolf_eval/render_demo.py`
  - Add `--consensus-log` and `--failure-audit` arguments. When either is supplied, run bundle validation and render a small provenance row.
- `scripts/context/build_plan_index.py`
  - Support both Chinese `### 任务 N：...` and English `### Task N: ...` headings.
- `tests/test_game_log.py`
  - Add negative tests for missing and unknown Game Log top-level `source_label`.
- `tests/test_decision_log.py`
  - Update assertions to use shared source-label contract where relevant.
- `tests/test_consensus_log.py`
  - Update assertions to use shared source-label contract where relevant.
- `tests/test_scoring.py`
  - Assert score output still works after Game Log `source_label` becomes part of `GameLog`.
- `tests/test_render_demo.py`
  - Assert bundle validation status appears when render CLI receives consensus/failure-audit inputs.
- `tests/test_context_budget.py`
  - Add actual heading-format regression tests for `Task` and `任务` headings.
- `docs/gold-game/g001-game-log.json`
  - Add top-level `"source_label": "[人工 gold sample]"` while keeping the existing `source` object.
- `docs/generated-games/g1-scripted-game-log.json`
  - Ensure top-level `"source_label": "[scripted deterministic output]"`.
- `docs/generated-games/g1b-mock-agent-game-log.json`
  - Ensure top-level `"source_label": "[deterministic mock agent output]"`.
- `docs/generated-games/g1c-wolf-consensus-game-log.json`
  - Ensure top-level `"source_label": "[deterministic mock agent output]"`.
- `docs/generated-games/g1c-wolf-consensus-score-log.json`
  - Regenerate only if `score_game.py` output metadata changes.
- `docs/generated-games/g1c-wolf-consensus-metrics-summary.json`
  - Regenerate only if `score_game.py` output metadata changes.
- `docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`
  - Regenerate only if `render_demo.py` output changes.
- `.oh-my-harness/tree.md`
  - Refresh via hook after creating new files.
- `.logs/review/latest/review-packet.md`
  - Generate after implementation for Codex A档 review.

## Allowlist

The implementation branch may modify only these paths:

```text
src/werewolf_eval/source_labels.py
src/werewolf_eval/game_log.py
src/werewolf_eval/decision_log.py
src/werewolf_eval/consensus_log.py
src/werewolf_eval/failure_audit.py
src/werewolf_eval/validate_failure_audit.py
src/werewolf_eval/log_bundle.py
src/werewolf_eval/validate_log_bundle.py
src/werewolf_eval/score_game.py
src/werewolf_eval/render_demo.py
scripts/context/build_plan_index.py
tests/test_source_labels.py
tests/test_game_log.py
tests/test_decision_log.py
tests/test_consensus_log.py
tests/test_failure_audit.py
tests/test_log_bundle.py
tests/test_scoring.py
tests/test_render_demo.py
tests/test_context_budget.py
docs/gold-game/g001-game-log.json
docs/generated-games/g1-scripted-game-log.json
docs/generated-games/g1b-mock-agent-game-log.json
docs/generated-games/g1c-wolf-consensus-game-log.json
docs/generated-games/g1c-wolf-consensus-score-log.json
docs/generated-games/g1c-wolf-consensus-metrics-summary.json
docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

## Forbidden Scope

Do not modify:

```text
docs/ai-worklog/**
README.md
docs/ROADMAP.md
docs/TASKS.md
docs/PRODUCT_ONE_PAGER.md
docs/EVALUATION_RUBRIC.md
docs/harness/plans/**
docs/prs/**
docs/specs/**
docs/generated-context/**
docs/gold-game/g001-decision-log.json
docs/gold-game/g001-consensus-log.json
docs/gold-game/s5-semantic-label-output.example.json
docs/demo/phase1-gold-demo.html
docs/demo/phase2-runtime-demo.html
docs/demo/phase2-s5-runtime-demo.html
docs/demo/phase3-g1-scripted-runtime-demo.html
docs/demo/phase3-g1b-mock-agent-runtime-demo.html
src/werewolf_eval/game_engine.py
src/werewolf_eval/run_mock_game.py
src/werewolf_eval/scripted_game.py
src/werewolf_eval/run_scripted_game.py
src/werewolf_eval/scoring.py
src/werewolf_eval/semantic_labels.py
scripts/dev/build_review_packet.py
package.json
package-lock.json
pyproject.toml
requirements.txt
requirements-dev.txt
```

Do not add:

- live provider calls
- HTTP client code
- API key or secret handling
- CI live-call behavior
- new dependencies
- real multi-game leaderboard logic
- human-vs-AI UI
- repair behavior that converts invalid, timeout, or parse-failure actions into valid Decision Log / Consensus Log actions
- broad refactors unrelated to this plan

## Verification Commands

Run these commands from the repository root.

### Core validation

```bash
python scripts/dev/validate_brief.py
```

Expected result:

```text
ok: true
next_read: []
```

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result:

```text
OK
```

The exact test count may increase from the current baseline because this plan adds new tests.

```bash
python -m compileall src tests -q
```

Expected result:

```text
exit code 0 with no Python syntax errors
```

### Runtime validators

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
```

Expected result:

```text
validated game_id=g001
source_label=[人工 gold sample]
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated game_id=g1c_wolf_consensus
source_label=[deterministic mock agent output]
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated decision_log_id=g1c_wolf_consensus_decisions
game_id=g1c_wolf_consensus
decisions=11
source_label=[deterministic mock agent output]
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1c-wolf-consensus-consensus-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated consensus_log_id=g1c_wolf_consensus_consensus
game_id=g1c_wolf_consensus
consensuses=2
source_label=[deterministic mock agent output]
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_failure_audit docs/generated-games/g1c-wolf-consensus-failure-audit.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated failure_audit game_id=g1c_wolf_consensus
failures=0
source_label=[deterministic mock agent output]
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json
```

Expected result:

```text
validated log_bundle game_id=g1c_wolf_consensus
decision_log=enabled
consensus_log=enabled
failure_audit=enabled
team_consensus_links=2
```

### Score/render provenance checks

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --score-log-out docs/generated-games/g1c-wolf-consensus-score-log.json --metrics-out docs/generated-games/g1c-wolf-consensus-metrics-summary.json
```

Expected result:

```text
scored game_id=g1c_wolf_consensus
score_records=11
decision_log=enabled
semantic_labels=disabled
bundle_validation=enabled
decision_quality_total=0
```

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --html-out docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
```

Expected result:

```text
wrote docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
bundle_validation=enabled
```

### Context-budget regression

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md --out /tmp/g1c-plan.index.json
```

Expected result:

```text
wrote /tmp/g1c-plan.index.json tasks>0
```

On Windows PowerShell, use:

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md --out C:\tmp\g1c-plan.index.json
```

Expected result:

```text
wrote C:\tmp\g1c-plan.index.json tasks>0
```

### Tree and diff checks

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
tree refreshed successfully or equivalent hook success output
```

```bash
git diff --check
```

Expected result:

```text
exit code 0
```

Existing LF/CRLF warnings are acceptable only when `git diff --check` exits 0 and the review packet classifies them as pre-existing or non-blocking.

## Acceptance Criteria

A-1. Game Log top-level `source_label` is required and validated.

Evidence pointer: `tests/test_game_log.py::test_game_log_requires_top_level_source_label`, `tests/test_game_log.py::test_game_log_rejects_unknown_source_label`, `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json`.

A-2. Source label taxonomy is shared by Game Log, Decision Log, Consensus Log, and Failure Audit validators.

Evidence pointer: `src/werewolf_eval/source_labels.py`, `tests/test_source_labels.py`, `tests/test_decision_log.py`, `tests/test_consensus_log.py`, `tests/test_failure_audit.py`.

A-3. Failure Audit has an independent parser, validator, CLI, and negative tests.

Evidence pointer: `src/werewolf_eval/failure_audit.py`, `src/werewolf_eval/validate_failure_audit.py`, `tests/test_failure_audit.py`, validator command output.

A-4. Bundle validation rejects team Decision Log entries that lack a valid Consensus Log link when Consensus Log is supplied.

Evidence pointer: `src/werewolf_eval/log_bundle.py`, `tests/test_log_bundle.py::test_team_decision_requires_consensus_id_when_consensus_log_is_supplied`, `tests/test_log_bundle.py::test_team_decision_rejects_unknown_consensus_id`.

A-5. Bundle validation rejects mismatch between Decision Log `consensus_id` target and Consensus Log final target.

Evidence pointer: `tests/test_log_bundle.py::test_team_decision_rejects_consensus_target_mismatch`.

A-6. Score and render commands record bundle validation status when consensus/failure audit paths are supplied.

Evidence pointer: `tests/test_scoring.py` or CLI-level assertion in `tests/test_log_bundle.py`, `tests/test_render_demo.py`, score/render command output.

A-7. Existing G1c valid path still validates, scores, and renders.

Evidence pointer: runtime validator commands, score command, render command.

A-8. Context Budget Gate indexer no longer returns `task_count=0` for actual G1b/G1c-style English task headings.

Evidence pointer: `tests/test_context_budget.py::test_plan_index_accepts_english_task_heading`, G1c plan index command output.

A-9. No provider, network, secret, dependency, or live AI capability is introduced.

Evidence pointer: Review Packet Forbidden Patterns Check, Dependency / Import Diff, changed files allowlist.

A-10. Review Packet is generated and contains machine evidence instead of a plain-language implementer summary.

Evidence pointer: `.logs/review/latest/review-packet.md`.

## Codex B档 Deep Review Risk Points

This implementation is expected to trigger or nearly trigger B档 review because it touches trust-boundary files.

Classify these risks in the review packet:

- `src/werewolf_eval/game_log.py` changes parser behavior and fixture compatibility.
- `src/werewolf_eval/decision_log.py` and `src/werewolf_eval/consensus_log.py` share source-label validation.
- New `src/werewolf_eval/failure_audit.py` defines a new input contract.
- New `src/werewolf_eval/log_bundle.py` creates cross-log invariants.
- `src/werewolf_eval/score_game.py` and `src/werewolf_eval/render_demo.py` affect user-visible runtime output.
- `scripts/context/build_plan_index.py` affects Claude/Codex context-budget safety.
- `docs/gold-game/g001-game-log.json`, `docs/generated-games/**`, and `docs/demo/**` are generated or fixture artifacts and should be reviewed for scope containment.
- Review packet forbidden pattern scan will likely see terms such as provider or network in docs/tests. These WARN items must be categorized as boundary text, not new runtime capability, unless the changed runtime code actually imports network/client/env/dependency behavior.
- Changed file count may exceed the v1 threshold of 8. If so, the Review Trigger Result should explicitly classify why B档 may be warranted and give exact file ranges.

## Review Packet Requirements

After implementation, generate:

```text
.logs/review/latest/review-packet.md
```

Prefer the project script:

```bash
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md --allowlist "src/werewolf_eval/source_labels.py" --allowlist "src/werewolf_eval/game_log.py" --allowlist "src/werewolf_eval/decision_log.py" --allowlist "src/werewolf_eval/consensus_log.py" --allowlist "src/werewolf_eval/failure_audit.py" --allowlist "src/werewolf_eval/validate_failure_audit.py" --allowlist "src/werewolf_eval/log_bundle.py" --allowlist "src/werewolf_eval/validate_log_bundle.py" --allowlist "src/werewolf_eval/score_game.py" --allowlist "src/werewolf_eval/render_demo.py" --allowlist "scripts/context/build_plan_index.py" --allowlist "tests/test_source_labels.py" --allowlist "tests/test_game_log.py" --allowlist "tests/test_decision_log.py" --allowlist "tests/test_consensus_log.py" --allowlist "tests/test_failure_audit.py" --allowlist "tests/test_log_bundle.py" --allowlist "tests/test_scoring.py" --allowlist "tests/test_render_demo.py" --allowlist "tests/test_context_budget.py" --allowlist "docs/gold-game/g001-game-log.json" --allowlist "docs/generated-games/g1-scripted-game-log.json" --allowlist "docs/generated-games/g1b-mock-agent-game-log.json" --allowlist "docs/generated-games/g1c-wolf-consensus-game-log.json" --allowlist "docs/generated-games/g1c-wolf-consensus-score-log.json" --allowlist "docs/generated-games/g1c-wolf-consensus-metrics-summary.json" --allowlist "docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html" --allowlist ".oh-my-harness/tree.md" --allowlist ".logs/review/latest/review-packet.md" --test-command "python scripts/dev/validate_brief.py" --test-command "PYTHONPATH=src python -m unittest discover -s tests -p \"test_*.py\"" --test-command "python -m compileall src tests -q" --test-command "git diff --check" --acceptance "A-1 Game Log source_label required and validated | tests/test_game_log.py + validate_game_log output | PASS" --acceptance "A-2 shared source label taxonomy | tests/test_source_labels.py + log validators | PASS" --acceptance "A-3 Failure Audit parser validator CLI | tests/test_failure_audit.py + validate_failure_audit output | PASS" --acceptance "A-4 team decisions require valid consensus_id | tests/test_log_bundle.py | PASS" --acceptance "A-5 consensus target mismatch rejected | tests/test_log_bundle.py | PASS" --acceptance "A-6 score/render record bundle validation | tests/test_render_demo.py + score/render command output | PASS" --acceptance "A-7 G1c valid path still works | validator/score/render commands | PASS" --acceptance "A-8 plan indexer accepts English headings | tests/test_context_budget.py + build_plan_index command | PASS" --acceptance "A-9 no live provider/network/dependency capability | packet forbidden/dependency checks | PASS" --acceptance "A-10 packet includes machine evidence | .logs/review/latest/review-packet.md | PASS"
```

If the script option names differ from the command above, run:

```bash
python scripts/dev/build_review_packet.py --help
```

Then use the supported equivalents while preserving the same evidence content.

The review packet must include at least:

1. `git diff --name-only`
2. `git diff --stat`
3. `git diff --check` result
4. changed files allowlist check
5. forbidden patterns check
6. dependency/import diff check
7. test command + exact pass/fail summary
8. key hunk excerpts
9. acceptance checklist with evidence pointer
10. implementer risk notes
11. Evidence Map
12. review trigger result
13. packet length check with `PACKET_TOO_LARGE = NO` or `PACKET_TOO_LARGE = YES`

Length limits:

- `review-packet.md <= 300 lines`
- Key Hunks <= 120 lines
- Test output contains summaries only
- Each changed file gets at most 1 key hunk unless a risk trigger is hit
- If over the limit, write `PACKET_TOO_LARGE = YES`
- If within the limit, write `PACKET_TOO_LARGE = NO`

The packet must not leave any acceptance item as `MANUAL_REVIEW_REQUIRED`. If the generator cannot infer one acceptance item automatically, add the acceptance evidence with the script-supported mechanism, then regenerate the packet.

## Implementation PR Description Draft

Title:

```text
feat: harden pre-G1d evaluation trust contracts
```

Body:

```markdown
## Summary

Implements the Pre-G1d Evaluation Trust Hardening plan:

- require and validate Game Log top-level source_label
- centralize source label taxonomy
- add Failure Audit parser / validator / CLI
- add cross-log bundle validator for Game + Decision + Consensus + Failure Audit
- record bundle validation status in score/render paths when consensus/failure-audit inputs are supplied
- fix plan indexer so English and Chinese task headings both produce context-budget task indexes

Bound plan:

`docs/harness/plans/2026-06-01--pre-g1d-evaluation-trust-hardening-plan.md`

## Boundaries

This PR does not add live provider calls, network code, secret handling, dependencies, G1e smoke, real multi-game Leaderboard, or human-vs-AI UI.

## Validation

- `python scripts/dev/validate_brief.py`
- `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
- `python -m compileall src tests -q`
- `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1c-wolf-consensus-consensus-log.json docs/generated-games/g1c-wolf-consensus-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.validate_failure_audit docs/generated-games/g1c-wolf-consensus-failure-audit.json docs/generated-games/g1c-wolf-consensus-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json`
- `PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --score-log-out docs/generated-games/g1c-wolf-consensus-score-log.json --metrics-out docs/generated-games/g1c-wolf-consensus-metrics-summary.json`
- `PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --html-out docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`
- `python scripts/context/build_plan_index.py docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md --out /tmp/g1c-plan.index.json`
- `node .codex/hooks/tree.mjs --force`
- `git diff --check`

## Review Packet

Generated at:

`.logs/review/latest/review-packet.md`

A档 review should start from the packet. B档 should read only the packet-requested file ranges.
```

---

### 任务 1：Source label taxonomy and Game Log top-level provenance

**文件：**
- 创建：`src/werewolf_eval/source_labels.py`
- 修改：`src/werewolf_eval/game_log.py`
- 修改：`src/werewolf_eval/decision_log.py`
- 修改：`src/werewolf_eval/consensus_log.py`
- 修改：`docs/gold-game/g001-game-log.json`
- 测试：`tests/test_source_labels.py`
- 测试：`tests/test_game_log.py`
- 测试：`tests/test_decision_log.py`
- 测试：`tests/test_consensus_log.py`

- [ ] **步骤 1：编写 shared source label tests**

Create `tests/test_source_labels.py` with these test cases:

```python
import unittest

from werewolf_eval.source_labels import (
    SourceLabelValidationError,
    validate_source_label,
)


class SourceLabelTests(unittest.TestCase):
    def test_accepts_known_runtime_labels(self):
        self.assertEqual(
            validate_source_label("[deterministic mock agent output]", artifact_name="Game Log"),
            "[deterministic mock agent output]",
        )
        self.assertEqual(
            validate_source_label("[scripted deterministic output]", artifact_name="Decision Log"),
            "[scripted deterministic output]",
        )
        self.assertEqual(
            validate_source_label("[人工 gold sample]", artifact_name="Consensus Log"),
            "[人工 gold sample]",
        )

    def test_rejects_unknown_label(self):
        with self.assertRaisesRegex(SourceLabelValidationError, "invalid source_label"):
            validate_source_label("[forged provider output]", artifact_name="Game Log")

    def test_rejects_non_string_label(self):
        with self.assertRaisesRegex(SourceLabelValidationError, "source_label must be a string"):
            validate_source_label(None, artifact_name="Game Log")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：Add failing Game Log source label tests**

Add these methods to the existing `GameLogParserTests` class in `tests/test_game_log.py`:

```python
    def test_game_log_requires_top_level_source_label(self) -> None:
        raw = load_raw_gold_game()
        raw.pop("source_label", None)

        with self.assertRaisesRegex(GameLogValidationError, "missing top-level fields"):
            parse_game_log(raw)

    def test_game_log_rejects_unknown_source_label(self) -> None:
        raw = load_raw_gold_game()
        raw["source_label"] = "[forged provider output]"

        with self.assertRaisesRegex(GameLogValidationError, "invalid source_label"):
            parse_game_log(raw)

    def test_game_log_exposes_source_label(self) -> None:
        raw = load_raw_gold_game()
        raw["source_label"] = "[人工 gold sample]"

        game = parse_game_log(raw)

        self.assertEqual(game.source_label, "[人工 gold sample]")
```

Keep the existing `unittest` style and do not introduce pytest.

- [ ] **步骤 3：Run tests and confirm expected failure**

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_game_log -v
```

Expected result:

```text
FAIL or ERROR
```

Expected reason:

```text
No module named werewolf_eval.source_labels
```

or:

```text
GameLog has no attribute source_label
```

- [ ] **步骤 4：Create source label module**

Create `src/werewolf_eval/source_labels.py`:

```python
from __future__ import annotations

from typing import Any


VALID_SOURCE_LABELS = {
    "[人工 gold sample]",
    "[AI 生成]",
    "[scripted deterministic output]",
    "[deterministic mock agent output]",
    "[semantic research output]",
}


class SourceLabelValidationError(ValueError):
    """Raised when an artifact source label is missing or outside the approved taxonomy."""


def validate_source_label(value: Any, *, artifact_name: str) -> str:
    if not isinstance(value, str):
        raise SourceLabelValidationError(f"{artifact_name}: source_label must be a string")
    if value not in VALID_SOURCE_LABELS:
        raise SourceLabelValidationError(f"{artifact_name}: invalid source_label: {value!r}")
    return value
```

- [ ] **步骤 5：Update Game Log parser**

Modify `src/werewolf_eval/game_log.py`:

```python
from werewolf_eval.source_labels import SourceLabelValidationError, validate_source_label
```

Add `source_label` to `GameLog`:

```python
@dataclass(frozen=True)
class GameLog:
    game_id: str
    source_label: str
    players: list[Player]
    events: list[Event]
    result: GameResult
```

Update `parse_game_log`:

```python
def parse_game_log(raw: dict[str, Any]) -> GameLog:
    required_top_level = {"game_id", "source_label", "players", "events", "result"}
    missing = required_top_level - set(raw)
    if missing:
        raise GameLogValidationError(f"missing top-level fields: {sorted(missing)}")

    try:
        source_label = validate_source_label(raw["source_label"], artifact_name="Game Log")
    except SourceLabelValidationError as exc:
        raise GameLogValidationError(str(exc)) from exc

    players = [_parse_player(player) for player in raw["players"]]
    events = [_parse_event(event) for event in raw["events"]]
    result = _parse_result(raw["result"])

    game = GameLog(
        game_id=str(raw["game_id"]),
        source_label=source_label,
        players=players,
        events=events,
        result=result,
    )
    validate_game_log(game)
    return game
```

Update `validate_game_log.py` to print the source label:

```python
print(f"source_label={game.source_label}")
```

- [ ] **步骤 6：Update Decision and Consensus Log validators to import shared labels**

In `src/werewolf_eval/decision_log.py`, replace the local `VALID_SOURCE_LABELS` set with:

```python
from werewolf_eval.source_labels import SourceLabelValidationError, validate_source_label
```

Then replace the source-label check with:

```python
try:
    validate_source_label(decision_log.source_label, artifact_name="Decision Log")
except SourceLabelValidationError as exc:
    raise DecisionLogValidationError(str(exc)) from exc
```

In `src/werewolf_eval/consensus_log.py`, apply the same pattern with `artifact_name="Consensus Log"`.

- [ ] **步骤 7：Update gold Game Log fixture**

Add this top-level field to `docs/gold-game/g001-game-log.json` immediately after `game_id`:

```json
"source_label": "[人工 gold sample]",
```

Keep the existing `source` object unchanged.

- [ ] **步骤 8：Run task tests**

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_game_log tests.test_decision_log tests.test_consensus_log -v
```

Expected result:

```text
OK
```

- [ ] **步骤 9：Run Game Log validators**

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result includes:

```text
source_label=[人工 gold sample]
source_label=[deterministic mock agent output]
```

- [ ] **步骤 10：Commit task 1**

```bash
git add src/werewolf_eval/source_labels.py src/werewolf_eval/game_log.py src/werewolf_eval/decision_log.py src/werewolf_eval/consensus_log.py src/werewolf_eval/validate_game_log.py docs/gold-game/g001-game-log.json tests/test_source_labels.py tests/test_game_log.py tests/test_decision_log.py tests/test_consensus_log.py
git commit -m "feat: require validated game log source labels"
```

Expected result:

```text
commit created
```

Acceptance for task 1:

- Missing Game Log top-level `source_label` fails validation.
- Unknown Game Log top-level `source_label` fails validation.
- Existing valid gold and G1c Game Logs validate.
- Decision/Consensus Log source labels use the shared taxonomy.

### 任务 2：Failure Audit parser validator and CLI

**文件：**
- 创建：`src/werewolf_eval/failure_audit.py`
- 创建：`src/werewolf_eval/validate_failure_audit.py`
- 测试：`tests/test_failure_audit.py`

- [ ] **步骤 1：Write failing tests**

Create `tests/test_failure_audit.py`:

```python
import copy
import json
import unittest
from pathlib import Path

from werewolf_eval.failure_audit import (
    FailureAuditValidationError,
    parse_failure_audit,
)
from werewolf_eval.game_log import load_game_log


def _game():
    return load_game_log("docs/generated-games/g1c-wolf-consensus-game-log.json")


def _valid_raw():
    return json.loads(
        Path("docs/generated-games/g1c-wolf-consensus-failure-audit.json").read_text(
            encoding="utf-8"
        )
    )


class FailureAuditTests(unittest.TestCase):
    def test_accepts_empty_valid_audit(self):
        audit = parse_failure_audit(_valid_raw(), _game())

        self.assertEqual(audit.game_id, "g1c_wolf_consensus")
        self.assertEqual(audit.source_label, "[deterministic mock agent output]")
        self.assertEqual(audit.failures, [])

    def test_rejects_missing_kind(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p1",
                "target": "p99",
                "reason": "invalid target",
                "repaired_to_valid_action": False,
            }
        ]

        with self.assertRaisesRegex(FailureAuditValidationError, "failure missing fields"):
            parse_failure_audit(raw, _game())

    def test_rejects_repaired_to_valid_action_true(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p1",
                "kind": "invalid_action",
                "target": "p99",
                "reason": "invalid target",
                "repaired_to_valid_action": True,
            }
        ]

        with self.assertRaisesRegex(FailureAuditValidationError, "must be false"):
            parse_failure_audit(raw, _game())

    def test_rejects_unknown_failure_actor(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p99",
                "kind": "timeout",
                "target": None,
                "reason": "unknown actor timed out",
                "repaired_to_valid_action": False,
            }
        ]

        with self.assertRaisesRegex(FailureAuditValidationError, "unknown actor"):
            parse_failure_audit(raw, _game())

    def test_rejects_unknown_valid_target_for_invalid_action(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p1",
                "kind": "invalid_action",
                "target": "p99",
                "reason": "invalid target",
                "repaired_to_valid_action": False,
            }
        ]

        audit = parse_failure_audit(raw, _game())
        self.assertEqual(audit.failures[0].target, "p99")


if __name__ == "__main__":
    unittest.main()
```

The invalid-action target may be outside `game.player_ids` because the audit must preserve rejected target text instead of repairing it.

- [ ] **步骤 2：Run tests and confirm expected failure**

```bash
PYTHONPATH=src python -m unittest tests.test_failure_audit -v
```

Expected result:

```text
ERROR
```

Expected reason:

```text
No module named werewolf_eval.failure_audit
```

- [ ] **步骤 3：Create parser and validator**

Create `src/werewolf_eval/failure_audit.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.game_log import GameLog
from werewolf_eval.source_labels import SourceLabelValidationError, validate_source_label


VALID_FAILURE_KINDS = {
    "timeout",
    "parse_failure",
    "invalid_action",
    "wolf_consensus_failure",
}
VALID_FAILURE_PHASES = {"night", "day"}


@dataclass(frozen=True)
class FailureRecord:
    game_id: str
    round: int
    phase: str
    actor: str
    kind: str
    target: str | None
    reason: str
    repaired_to_valid_action: bool


@dataclass(frozen=True)
class FailureAudit:
    game_id: str
    source_label: str
    failures: list[FailureRecord]


class FailureAuditValidationError(ValueError):
    """Raised when a Failure Audit cannot be accepted as runtime evidence."""


def load_failure_audit(path: str | Path, game: GameLog) -> FailureAudit:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise FailureAuditValidationError("Failure Audit root must be an object")
    return parse_failure_audit(raw, game)


def parse_failure_audit(raw: dict[str, Any], game: GameLog) -> FailureAudit:
    required_top_level = {"game_id", "source_label", "failures"}
    missing = required_top_level - set(raw)
    if missing:
        raise FailureAuditValidationError(f"missing top-level fields: {sorted(missing)}")

    if not isinstance(raw["failures"], list):
        raise FailureAuditValidationError("failures must be a list")

    try:
        source_label = validate_source_label(raw["source_label"], artifact_name="Failure Audit")
    except SourceLabelValidationError as exc:
        raise FailureAuditValidationError(str(exc)) from exc

    audit = FailureAudit(
        game_id=str(raw["game_id"]),
        source_label=source_label,
        failures=[_parse_failure(item) for item in raw["failures"]],
    )
    validate_failure_audit(audit, game)
    return audit


def validate_failure_audit(audit: FailureAudit, game: GameLog) -> None:
    if audit.game_id != game.game_id:
        raise FailureAuditValidationError(
            f"game_id mismatch: failure audit {audit.game_id!r} != game {game.game_id!r}"
        )

    known_actors = game.player_ids | {"wolf_team"}
    for failure in audit.failures:
        _validate_failure(failure, game, known_actors)


def _parse_failure(raw: Any) -> FailureRecord:
    if not isinstance(raw, dict):
        raise FailureAuditValidationError("failure entries must be objects")

    required_fields = {
        "game_id",
        "round",
        "phase",
        "actor",
        "kind",
        "target",
        "reason",
        "repaired_to_valid_action",
    }
    missing = required_fields - set(raw)
    if missing:
        raise FailureAuditValidationError(f"failure missing fields: {sorted(missing)}")

    target = raw["target"]
    return FailureRecord(
        game_id=str(raw["game_id"]),
        round=int(raw["round"]),
        phase=str(raw["phase"]),
        actor=str(raw["actor"]),
        kind=str(raw["kind"]),
        target=None if target is None else str(target),
        reason=str(raw["reason"]),
        repaired_to_valid_action=bool(raw["repaired_to_valid_action"]),
    )


def _validate_failure(failure: FailureRecord, game: GameLog, known_actors: set[str]) -> None:
    if failure.game_id != game.game_id:
        raise FailureAuditValidationError(
            f"failure game_id mismatch: {failure.game_id!r} != {game.game_id!r}"
        )
    if failure.round < 1:
        raise FailureAuditValidationError("failure round must be >= 1")
    if failure.phase not in VALID_FAILURE_PHASES:
        raise FailureAuditValidationError(f"invalid failure phase: {failure.phase!r}")
    if failure.actor not in known_actors:
        raise FailureAuditValidationError(f"unknown actor in failure audit: {failure.actor!r}")
    if failure.kind not in VALID_FAILURE_KINDS:
        raise FailureAuditValidationError(f"invalid failure kind: {failure.kind!r}")
    if not failure.reason:
        raise FailureAuditValidationError("failure reason must not be empty")
    if failure.repaired_to_valid_action is not False:
        raise FailureAuditValidationError("repaired_to_valid_action must be false")
```

- [ ] **步骤 4：Create CLI**

Create `src/werewolf_eval/validate_failure_audit.py`:

```python
from __future__ import annotations

import argparse

from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.game_log import load_game_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Failure Audit JSON file.")
    parser.add_argument("failure_audit_path", help="Path to Failure Audit JSON")
    parser.add_argument("game_log_path", help="Path to matching Game Log JSON")
    args = parser.parse_args()

    game = load_game_log(args.game_log_path)
    audit = load_failure_audit(args.failure_audit_path, game)

    print(f"validated failure_audit game_id={audit.game_id}")
    print(f"failures={len(audit.failures)}")
    print(f"source_label={audit.source_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 5：Run tests**

```bash
PYTHONPATH=src python -m unittest tests.test_failure_audit -v
```

Expected result:

```text
OK
```

- [ ] **步骤 6：Run CLI**

```bash
PYTHONPATH=src python -m werewolf_eval.validate_failure_audit docs/generated-games/g1c-wolf-consensus-failure-audit.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated failure_audit game_id=g1c_wolf_consensus
failures=0
source_label=[deterministic mock agent output]
```

- [ ] **步骤 7：Commit task 2**

```bash
git add src/werewolf_eval/failure_audit.py src/werewolf_eval/validate_failure_audit.py tests/test_failure_audit.py
git commit -m "feat: validate failure audit artifacts"
```

Expected result:

```text
commit created
```

Acceptance for task 2:

- Valid empty G1c failure audit passes.
- Missing failure `kind` fails.
- `repaired_to_valid_action=true` fails.
- Unknown failure actor fails.
- Invalid rejected target text is preserved in audit and not repaired.

### 任务 3：Cross-log bundle validator

**文件：**
- 创建：`src/werewolf_eval/log_bundle.py`
- 创建：`src/werewolf_eval/validate_log_bundle.py`
- 测试：`tests/test_log_bundle.py`

- [ ] **步骤 1：Write failing bundle tests**

Create `tests/test_log_bundle.py`:

```python
import copy
import json
import unittest
from pathlib import Path

from werewolf_eval.consensus_log import load_consensus_log, parse_consensus_log
from werewolf_eval.decision_log import parse_decision_log
from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.game_log import load_game_log
from werewolf_eval.log_bundle import LogBundleValidationError, validate_log_bundle


GAME_PATH = "docs/generated-games/g1c-wolf-consensus-game-log.json"
DECISION_PATH = "docs/generated-games/g1c-wolf-consensus-decision-log.json"
CONSENSUS_PATH = "docs/generated-games/g1c-wolf-consensus-consensus-log.json"
FAILURE_AUDIT_PATH = "docs/generated-games/g1c-wolf-consensus-failure-audit.json"


def _raw(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LogBundleTests(unittest.TestCase):
    def test_valid_g1c_bundle_passes(self):
        game = load_game_log(GAME_PATH)
        decision_log = parse_decision_log(_raw(DECISION_PATH), game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)
        failure_audit = load_failure_audit(FAILURE_AUDIT_PATH, game)

        result = validate_log_bundle(
            game,
            decision_log=decision_log,
            consensus_log=consensus_log,
            failure_audit=failure_audit,
        )

        self.assertEqual(result.team_consensus_links, 2)

    def test_team_decision_requires_consensus_id_when_consensus_log_is_supplied(self):
        game = load_game_log(GAME_PATH)
        raw_decision = _raw(DECISION_PATH)
        raw_decision["decisions"][0]["consensus_id"] = None
        decision_log = parse_decision_log(raw_decision, game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)

        with self.assertRaisesRegex(LogBundleValidationError, "missing consensus_id"):
            validate_log_bundle(game, decision_log=decision_log, consensus_log=consensus_log)

    def test_team_decision_rejects_unknown_consensus_id(self):
        game = load_game_log(GAME_PATH)
        raw_decision = _raw(DECISION_PATH)
        raw_decision["decisions"][0]["consensus_id"] = "missing_consensus"
        decision_log = parse_decision_log(raw_decision, game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)

        with self.assertRaisesRegex(LogBundleValidationError, "unknown consensus_id"):
            validate_log_bundle(game, decision_log=decision_log, consensus_log=consensus_log)

    def test_team_decision_rejects_consensus_target_mismatch(self):
        game = load_game_log(GAME_PATH)
        raw_decision = _raw(DECISION_PATH)
        raw_decision["decisions"][0]["target"] = "p6"
        decision_log = parse_decision_log(raw_decision, game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)

        with self.assertRaisesRegex(LogBundleValidationError, "target mismatch"):
            validate_log_bundle(game, decision_log=decision_log, consensus_log=consensus_log)

    def test_failure_audit_source_label_must_match_game_source_label(self):
        game = load_game_log(GAME_PATH)
        raw_audit = _raw(FAILURE_AUDIT_PATH)
        raw_audit["source_label"] = "[scripted deterministic output]"

        with self.assertRaisesRegex(LogBundleValidationError, "source_label mismatch"):
            validate_log_bundle(
                game,
                failure_audit=parse_failure_audit(raw_audit, game),
            )


if __name__ == "__main__":
    unittest.main()
```

Import `parse_failure_audit` in the test when adding the last case.

- [ ] **步骤 2：Run tests and confirm expected failure**

```bash
PYTHONPATH=src python -m unittest tests.test_log_bundle -v
```

Expected result:

```text
ERROR
```

Expected reason:

```text
No module named werewolf_eval.log_bundle
```

- [ ] **步骤 3：Create bundle validator**

Create `src/werewolf_eval/log_bundle.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from werewolf_eval.consensus_log import Consensus, ConsensusLog
from werewolf_eval.decision_log import Decision, DecisionLog
from werewolf_eval.failure_audit import FailureAudit
from werewolf_eval.game_log import GameLog


class LogBundleValidationError(ValueError):
    """Raised when separately valid logs do not satisfy cross-log invariants."""


@dataclass(frozen=True)
class LogBundleValidationResult:
    game_id: str
    decision_log_enabled: bool
    consensus_log_enabled: bool
    failure_audit_enabled: bool
    team_consensus_links: int


def validate_log_bundle(
    game: GameLog,
    *,
    decision_log: DecisionLog | None = None,
    consensus_log: ConsensusLog | None = None,
    failure_audit: FailureAudit | None = None,
) -> LogBundleValidationResult:
    if decision_log is not None and decision_log.game_id != game.game_id:
        raise LogBundleValidationError("decision_log game_id mismatch")
    if consensus_log is not None and consensus_log.game_id != game.game_id:
        raise LogBundleValidationError("consensus_log game_id mismatch")
    if failure_audit is not None and failure_audit.game_id != game.game_id:
        raise LogBundleValidationError("failure_audit game_id mismatch")

    _validate_source_labels_match(game, decision_log, consensus_log, failure_audit)

    team_links = 0
    if decision_log is not None and consensus_log is not None:
        team_links = _validate_team_decision_consensus_links(decision_log, consensus_log)

    return LogBundleValidationResult(
        game_id=game.game_id,
        decision_log_enabled=decision_log is not None,
        consensus_log_enabled=consensus_log is not None,
        failure_audit_enabled=failure_audit is not None,
        team_consensus_links=team_links,
    )


def _validate_source_labels_match(
    game: GameLog,
    decision_log: DecisionLog | None,
    consensus_log: ConsensusLog | None,
    failure_audit: FailureAudit | None,
) -> None:
    for name, artifact in [
        ("decision_log", decision_log),
        ("consensus_log", consensus_log),
        ("failure_audit", failure_audit),
    ]:
        if artifact is not None and artifact.source_label != game.source_label:
            raise LogBundleValidationError(
                f"source_label mismatch: {name} {artifact.source_label!r} != game {game.source_label!r}"
            )


def _is_team_decision(decision: Decision) -> bool:
    return (
        decision.decision_scope == "team"
        or decision.actor == "wolf_team"
        or decision.action == "werewolf_kill"
        or decision.decision_type == "team_coordinated"
    )


def _validate_team_decision_consensus_links(
    decision_log: DecisionLog,
    consensus_log: ConsensusLog,
) -> int:
    consensuses = {item.consensus_id: item for item in consensus_log.consensuses}
    links = 0

    for decision in decision_log.decisions:
        if not _is_team_decision(decision):
            continue

        if not decision.consensus_id:
            raise LogBundleValidationError(
                f"{decision.decision_id}: missing consensus_id for team decision"
            )
        if decision.consensus_id not in consensuses:
            raise LogBundleValidationError(
                f"{decision.decision_id}: unknown consensus_id {decision.consensus_id!r}"
            )

        consensus = consensuses[decision.consensus_id]
        _validate_decision_matches_consensus(decision, consensus)
        links += 1

    return links


def _validate_decision_matches_consensus(decision: Decision, consensus: Consensus) -> None:
    if decision.target != consensus.final_decision.target:
        raise LogBundleValidationError(
            f"{decision.decision_id}: target mismatch with {consensus.consensus_id}: "
            f"{decision.target!r} != {consensus.final_decision.target!r}"
        )
    if decision.phase != consensus.phase:
        raise LogBundleValidationError(
            f"{decision.decision_id}: phase mismatch with {consensus.consensus_id}: "
            f"{decision.phase!r} != {consensus.phase!r}"
        )
```

- [ ] **步骤 4：Create CLI**

Create `src/werewolf_eval/validate_log_bundle.py`:

```python
from __future__ import annotations

import argparse

from werewolf_eval.consensus_log import load_consensus_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.game_log import load_game_log
from werewolf_eval.log_bundle import validate_log_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cross-log Werewolf-agent bundle invariants.")
    parser.add_argument("game_log_path", help="Path to Game Log JSON")
    parser.add_argument("--decision-log", help="Path to Decision Log JSON")
    parser.add_argument("--consensus-log", help="Path to Consensus Log JSON")
    parser.add_argument("--failure-audit", help="Path to Failure Audit JSON")
    args = parser.parse_args()

    game = load_game_log(args.game_log_path)
    decision_log = load_decision_log(args.decision_log, game) if args.decision_log else None
    consensus_log = load_consensus_log(args.consensus_log, game) if args.consensus_log else None
    failure_audit = load_failure_audit(args.failure_audit, game) if args.failure_audit else None

    result = validate_log_bundle(
        game,
        decision_log=decision_log,
        consensus_log=consensus_log,
        failure_audit=failure_audit,
    )

    print(f"validated log_bundle game_id={result.game_id}")
    print(f"decision_log={'enabled' if result.decision_log_enabled else 'disabled'}")
    print(f"consensus_log={'enabled' if result.consensus_log_enabled else 'disabled'}")
    print(f"failure_audit={'enabled' if result.failure_audit_enabled else 'disabled'}")
    print(f"team_consensus_links={result.team_consensus_links}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 5：Run tests**

```bash
PYTHONPATH=src python -m unittest tests.test_log_bundle -v
```

Expected result:

```text
OK
```

- [ ] **步骤 6：Run bundle CLI**

```bash
PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json
```

Expected result:

```text
validated log_bundle game_id=g1c_wolf_consensus
decision_log=enabled
consensus_log=enabled
failure_audit=enabled
team_consensus_links=2
```

- [ ] **步骤 7：Commit task 3**

```bash
git add src/werewolf_eval/log_bundle.py src/werewolf_eval/validate_log_bundle.py tests/test_log_bundle.py
git commit -m "feat: validate cross-log trust bundle"
```

Expected result:

```text
commit created
```

Acceptance for task 3:

- Valid G1c bundle passes.
- Team decision without consensus link fails when Consensus Log is supplied.
- Unknown consensus link fails.
- Consensus target mismatch fails.
- Source label mismatch across supplied artifacts fails.

### 任务 4：Score and render provenance recording

**文件：**
- 修改：`src/werewolf_eval/score_game.py`
- 修改：`src/werewolf_eval/render_demo.py`
- 修改：`docs/generated-games/g1c-wolf-consensus-score-log.json`
- 修改：`docs/generated-games/g1c-wolf-consensus-metrics-summary.json`
- 修改：`docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`
- 测试：`tests/test_scoring.py`
- 测试：`tests/test_render_demo.py`

- [ ] **步骤 1：Add failing score/render tests**

Add test coverage that exercises CLI helper behavior or direct functions already used in these test files.

For `score_game.py`, assert that when both `--consensus-log` and `--failure-audit` are supplied:

```text
bundle_validation=enabled
```

appears in command output and the written score JSON contains:

```json
"bundle_validation": {
  "enabled": true,
  "decision_log": true,
  "consensus_log": true,
  "failure_audit": true,
  "team_consensus_links": 2
}
```

For `render_demo.py`, assert that when both `--consensus-log` and `--failure-audit` are supplied, the HTML contains:

```html
Bundle validation: enabled
```

and:

```html
team_consensus_links=2
```

Use the existing test style in `tests/test_scoring.py` and `tests/test_render_demo.py`. Do not introduce subprocess-only tests when the current files already use direct Python functions.

- [ ] **步骤 2：Run targeted tests and confirm expected failure**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring tests.test_render_demo -v
```

Expected result:

```text
FAIL
```

Expected reason:

```text
bundle_validation not found
```

or:

```text
unrecognized arguments: --consensus-log --failure-audit
```

- [ ] **步骤 3：Modify score CLI**

In `src/werewolf_eval/score_game.py`, import:

```python
from werewolf_eval.consensus_log import load_consensus_log
from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.log_bundle import validate_log_bundle
```

Add parser arguments:

```python
parser.add_argument("--consensus-log", help="Optional path to Consensus Log JSON for bundle validation")
parser.add_argument("--failure-audit", help="Optional path to Failure Audit JSON for bundle validation")
```

After loading `decision_log`, load the new artifacts:

```python
consensus_log = load_consensus_log(args.consensus_log, game) if args.consensus_log else None
failure_audit = load_failure_audit(args.failure_audit, game) if args.failure_audit else None
bundle_result = None
if decision_log or consensus_log or failure_audit:
    bundle_result = validate_log_bundle(
        game,
        decision_log=decision_log,
        consensus_log=consensus_log,
        failure_audit=failure_audit,
    )
```

After building output dictionaries, add:

```python
if bundle_result is not None:
    bundle_payload = {
        "enabled": True,
        "decision_log": bundle_result.decision_log_enabled,
        "consensus_log": bundle_result.consensus_log_enabled,
        "failure_audit": bundle_result.failure_audit_enabled,
        "team_consensus_links": bundle_result.team_consensus_links,
    }
    score_payload["bundle_validation"] = bundle_payload
    metrics_payload["bundle_validation"] = bundle_payload
```

Add print:

```python
print(f"bundle_validation={'enabled' if bundle_result else 'disabled'}")
if bundle_result is not None:
    print(f"team_consensus_links={bundle_result.team_consensus_links}")
```

- [ ] **步骤 4：Modify render CLI**

In `src/werewolf_eval/render_demo.py`, add the same parser arguments and validation call at the CLI boundary. Pass a small dict into the existing demo context or append it to the rendering context.

The rendered HTML must include a compact provenance line:

```text
Bundle validation: enabled
```

and:

```text
team_consensus_links=2
```

If no bundle artifacts are supplied, the HTML should keep existing behavior and must not claim bundle validation occurred.

- [ ] **步骤 5：Run targeted tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring tests.test_render_demo -v
```

Expected result:

```text
OK
```

- [ ] **步骤 6：Regenerate G1c score and demo artifacts**

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --score-log-out docs/generated-games/g1c-wolf-consensus-score-log.json --metrics-out docs/generated-games/g1c-wolf-consensus-metrics-summary.json
```

Expected result includes:

```text
bundle_validation=enabled
team_consensus_links=2
```

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --html-out docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
```

Expected result includes:

```text
wrote docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
bundle_validation=enabled
```

- [ ] **步骤 7：Commit task 4**

```bash
git add src/werewolf_eval/score_game.py src/werewolf_eval/render_demo.py docs/generated-games/g1c-wolf-consensus-score-log.json docs/generated-games/g1c-wolf-consensus-metrics-summary.json docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html tests/test_scoring.py tests/test_render_demo.py
git commit -m "feat: record bundle validation in outputs"
```

Expected result:

```text
commit created
```

Acceptance for task 4:

- Score command can record bundle validation.
- Render command can show bundle validation.
- Existing calls without bundle artifacts remain valid and do not claim bundle validation.
- G1c generated artifacts are updated only where output schema changed.

### 任务 5：Context Budget Gate plan index regression

**文件：**
- 修改：`scripts/context/build_plan_index.py`
- 测试：`tests/test_context_budget.py`

- [ ] **步骤 1：Add failing regression tests**

In `tests/test_context_budget.py`, add these methods to `PlanIndexBuilderTests`:

```python
    def test_plan_index_accepts_english_task_heading(self) -> None:
        from scripts.context.build_plan_index import build_plan_index

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "docs/harness/plans/english-plan.md"
            plan.parent.mkdir(parents=True)
            plan.write_text(
                "# Example Plan\n\n"
                "### Task 1: English heading\n\n"
                "**文件：**\n"
                "- 修改：`src/werewolf_eval/game_log.py`\n\n"
                "```bash\n"
                "PYTHONPATH=src python -m unittest tests.test_game_log -v\n"
                "```\n",
                encoding="utf-8",
            )

            index = build_plan_index(plan, repo_root=root)

        self.assertEqual(index["task_count"], 1)
        self.assertEqual(index["tasks"][0]["id"], "1")
        self.assertEqual(index["tasks"][0]["title"], "English heading")

    def test_plan_index_still_accepts_chinese_task_heading(self) -> None:
        from scripts.context.build_plan_index import build_plan_index

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "docs/harness/plans/chinese-plan.md"
            plan.parent.mkdir(parents=True)
            plan.write_text(
                "# Example Plan\n\n"
                "### 任务 2：中文标题\n\n"
                "**文件：**\n"
                "- 修改：`src/werewolf_eval/game_log.py`\n\n"
                "```bash\n"
                "PYTHONPATH=src python -m unittest tests.test_game_log -v\n"
                "```\n",
                encoding="utf-8",
            )

            index = build_plan_index(plan, repo_root=root)

        self.assertEqual(index["task_count"], 1)
        self.assertEqual(index["tasks"][0]["id"], "2")
        self.assertEqual(index["tasks"][0]["title"], "中文标题")
```

- [ ] **步骤 2：Run regression tests and confirm expected failure**

```bash
PYTHONPATH=src python -m unittest tests.test_context_budget -v
```

Expected result:

```text
FAIL
```

Expected reason:

```text
task_count 0 != 1
```

for the English heading case.

- [ ] **步骤 3：Update heading parser**

Modify `scripts/context/build_plan_index.py`.

Replace:

```python
TASK_HEADING_RE = re.compile(r"^###\s+任务\s+([^：:]+)[：:]\s*(.+?)\s*$")
```

with:

```python
TASK_HEADING_RE = re.compile(
    r"^###\s+(?:任务|Task)\s+([^：:]+)[：:]\s*(.+?)\s*$",
    re.IGNORECASE,
)
```

This preserves current Chinese heading support and adds English `Task` support.

- [ ] **步骤 4：Run regression tests**

```bash
PYTHONPATH=src python -m unittest tests.test_context_budget -v
```

Expected result:

```text
OK
```

- [ ] **步骤 5：Run actual G1c index command**

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md --out /tmp/g1c-plan.index.json
```

Expected result:

```text
wrote /tmp/g1c-plan.index.json tasks>0
```

If running on Windows PowerShell:

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md --out C:\tmp\g1c-plan.index.json
```

Expected result:

```text
wrote C:\tmp\g1c-plan.index.json tasks>0
```

- [ ] **步骤 6：Commit task 5**

```bash
git add scripts/context/build_plan_index.py tests/test_context_budget.py
git commit -m "fix: index english implementation plan tasks"
```

Expected result:

```text
commit created
```

Acceptance for task 5:

- English `### Task N: ...` headings index correctly.
- Chinese `### 任务 N：...` headings still index correctly.
- Actual G1c plan no longer produces `tasks=0`.

### 任务 6：Final validation review packet and handoff

**文件：**
- 修改：`.oh-my-harness/tree.md`
- 创建或修改：`.logs/review/latest/review-packet.md`

- [ ] **步骤 1：Refresh tree after new files**

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
tree refreshed successfully or equivalent hook success output
```

- [ ] **步骤 2：Run full verification**

```bash
python scripts/dev/validate_brief.py
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests -q
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1c-wolf-consensus-consensus-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_failure_audit docs/generated-games/g1c-wolf-consensus-failure-audit.json docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --score-log-out docs/generated-games/g1c-wolf-consensus-score-log.json --metrics-out docs/generated-games/g1c-wolf-consensus-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --consensus-log docs/generated-games/g1c-wolf-consensus-consensus-log.json --failure-audit docs/generated-games/g1c-wolf-consensus-failure-audit.json --html-out docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
python scripts/context/build_plan_index.py docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md --out /tmp/g1c-plan.index.json
git diff --check
```

Expected result:

```text
all commands exit 0
unittest summary ends with OK
compileall exits 0
validate_brief reports ok: true
bundle validator reports team_consensus_links=2
score/render commands report bundle_validation=enabled
build_plan_index reports tasks>0
git diff --check exits 0
```

- [ ] **步骤 3：Generate review packet**

Run the command in the Review Packet Requirements section. If the script interface differs, inspect:

```bash
python scripts/dev/build_review_packet.py --help
```

Then run the supported equivalent.

Expected result:

```text
.logs/review/latest/review-packet.md exists
PACKET_TOO_LARGE = NO
Evidence Map has no MANUAL_REVIEW_REQUIRED rows
Acceptance Checklist is all PASS
Forbidden WARN entries are classified
```

If `PACKET_TOO_LARGE = YES`, keep the packet but mark Codex review as B档 required and list exact file ranges. Do not delete evidence to hide the trigger.

- [ ] **步骤 4：Commit final packet/tree**

```bash
git add .oh-my-harness/tree.md .logs/review/latest/review-packet.md
git commit -m "chore: add review packet for trust hardening"
```

Expected result:

```text
commit created
```

- [ ] **步骤 5：Final implementer output**

The implementer final response must include only:

```text
是否完整读取过 plan: NO
使用的 current-task.ctx.md: docs/generated-context/current-task.ctx.md
changed files: <git diff --name-only summary>
commit 列表: <git log --oneline main..HEAD>
验证命令与 PASS/FAIL 摘要: <summary only>
review-packet.md 路径: .logs/review/latest/review-packet.md
PACKET_TOO_LARGE: NO or YES
Evidence Map 是否仍有 MANUAL_REVIEW_REQUIRED: NO
Acceptance Checklist 是否全部完成: YES
Forbidden WARN 是否已分类说明: YES
是否触发 Codex B 档深审: YES or NO with reason
是否需要继续修复: YES or NO
```

Acceptance for task 6:

- Review packet exists and satisfies the required evidence sections.
- Packet length status is explicit.
- Implementer output is bounded and does not include full diff, full test log, full review packet, or full plan content.
