# Review Packet Gate v1 Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a lightweight Review Packet Gate v1 so Codex reviews evidence packets first instead of performing default full-repository context discovery.

**Architecture:** This is a workflow hardening slice. The implementation adds a stable review-packet specification, wires the requirement into the cloud/local agent workflow, and provides a minimal local Python generator that produces `.logs/review/latest/review-packet.md` from objective Git evidence. It does not change evaluator runtime behavior, gameplay logic, scoring logic, generated gold artifacts, or provider/runtime integration.

**Tech Stack:** Markdown specs, Python standard library, `git` CLI, `unittest`, existing `.oh-my-harness/tree.md` refresh hook.

---

## Research PR Decision

No Research PR is needed.

The task boundary is clear and implementation-oriented:

- document the Review Packet Gate workflow;
- define the Review Packet v1 contract;
- add a minimal generator script under `scripts/dev/`;
- add tests for generator output shape and limits;
- ensure `.logs/review/` artifacts are not tracked;
- avoid all business logic and runtime behavior changes.

## Bound Implementation PR

Future Implementation PR title:

```text
docs/dev: add Review Packet Gate v1
```

Bound plan path:

```text
docs/harness/plans/2026-05-31--review-packet-gate-v1-plan.md
```

## Global Allowed Scope

The Implementation PR may create or modify only these paths unless the implementer records a concrete reason in the Review Packet risk notes:

```text
docs/specs/agent-workflow.md
docs/specs/review-packet-gate.md
.github/codex-review-comment.md
.gitignore
scripts/dev/build_review_packet.py
tests/test_build_review_packet.py
.oh-my-harness/tree.md
```

## Global Forbidden Scope

The Implementation PR must not modify:

```text
src/werewolf_eval/**
docs/gold-game/**
docs/demo/**
docs/semantic-labeling/**
docs/TASKS.md
docs/ROADMAP.md
docs/PRODUCT_ONE_PAGER.md
docs/EVALUATION_RUBRIC.md
README.md
```

The Implementation PR must not introduce:

```text
provider API calls
network calls
SDK additions
runtime dependency additions
secrets or environment-variable requirements
live AI execution
scoring behavior changes
parser behavior changes
generated demo or gold-game artifact changes
```

## Review Packet v1 Contract

The generated file must be:

```text
.logs/review/latest/review-packet.md
```

It must include these sections in this order:

```text
# Review Packet

## Metadata
## Changed Files
## Diff Stat
## Diff Check
## Allowed Files Check
## Forbidden Patterns Check
## Dependency / Import Diff
## Test Summary
## Key Hunks
## Evidence Map
## Acceptance Checklist
## Implementer Risk Notes
## Review Trigger Result
```

Minimum evidence requirements:

```text
1. git diff --name-only
2. git diff --stat
3. git diff --check result
4. changed files allowlist check
5. forbidden patterns check
6. dependency/import diff check
7. test command + exact pass/fail summary
8. key hunk excerpts
9. Evidence Map
10. acceptance checklist with evidence pointer
11. implementer risk notes
12. review trigger result
```

Length limits:

```text
review-packet.md <= 300 lines
Key Hunks <= 120 lines
Test output summary only; do not include full logs
Each changed file gets at most one key hunk unless a risk trigger is hit
```

If the packet exceeds a limit, the generator must write:

```text
PACKET_TOO_LARGE = YES
Suggested action: NEED_DEEP_REVIEW with explicit line ranges
```

If the packet stays within limits, the generator must write:

```text
PACKET_TOO_LARGE = NO
```

Codex A档 gate semantics:

```text
PASS: stop review; no repository search is needed
BLOCK: return only blocking findings and the minimal fix prompt
NEED_DEEP_REVIEW: return only explicit file paths and line ranges for B档
```

A档 must not automatically deep-review only because the changed area is high-risk. The packet must mark `risk=true` when a trigger appears, and Codex decides whether the provided evidence is sufficient.

## Risk Triggers

The generator must mark risk when evidence shows any of these conditions:

```text
Changed file count > 8
Diff stat indicates more than 500 changed lines
PACKET_TOO_LARGE = YES
forbidden pattern scan hits provider / network / env / dependency / live AI
changed files include src/werewolf_eval/scoring.py
changed files include src/werewolf_eval/*parser*.py
changed files include src/werewolf_eval/*log*.py
changed files include docs/gold-game/**
changed files include docs/demo/**
changed files include dependency manifests
key hunks were truncated
allowlist check is not PASS
```

The v1 script is allowed to implement conservative filename/pattern-based risk detection. It must record exactly which trigger fired.

## Evidence Map Shape

The packet must include an Evidence Map with one row per acceptance item:

```text
| Acceptance | Evidence | Status |
|---|---|---|
| A1: review packet contains required machine evidence | `tests/test_build_review_packet.py::test_packet_contains_required_sections`; `.logs/review/latest/review-packet.md` sections | PASS |
| A2: packet length is bounded | `tests/test_build_review_packet.py::test_packet_marks_size_limits`; `PACKET_TOO_LARGE` field | PASS |
```

When the script cannot infer an acceptance item automatically, it must provide a scaffold row with `MANUAL_REVIEW_REQUIRED`, not a fake PASS.

## Extension Points Outside v1

These are explicit extension points, not implementation requirements for this PR:

```text
Plan allowlist parsing from Implementation Plan front matter
Automatic acceptance extraction from plan checkboxes
Exact source line pointer generation for Evidence Map rows
Deep Review Packet generator for Codex B档
CI enforcement that rejects implementation PRs without review-packet.md evidence
```

The v1 Implementation PR should keep these as documented extension points and should not build the full system at once.

---

## Task 1: Add Review Packet Gate workflow specification

**Files:**

- Create: `docs/specs/review-packet-gate.md`
- Modify: `docs/specs/agent-workflow.md`
- Test: inline documentation shape check command shown below

- [ ] **Step 1: Create `docs/specs/review-packet-gate.md`**

Create a spec with these exact headings:

```markdown
# Review Packet Gate v1

## Purpose

Review Packet Gate v1 changes Codex review from repository-wide context discovery to evidence-packet review.

## Roles

| Actor | Responsibility |
|---|---|
| Claude Code / local implementer | Implement scoped changes, run validation, generate review packet |
| Review Packet script | Produce objective Git/test evidence |
| Codex A档 | Review only `review-packet.md` and return PASS / BLOCK / NEED_DEEP_REVIEW |
| Codex B档 | Read only requested file ranges after NEED_DEEP_REVIEW |

## Required Gate

No `review-packet.md`, no Codex implementation review.

## A档 Rules

- Codex A档 reviews only `.logs/review/latest/review-packet.md`.
- A档 has exactly three verdicts: PASS, BLOCK, NEED_DEEP_REVIEW.
- A档 outputs one conclusion only.
- If evidence is insufficient, A档 lists Minimal Next Reads with explicit file paths and line ranges.
- A档 must not request broad repository material.

## Review Packet v1 Required Sections

[List the required sections from this plan.]

## Length Limits

[List the 300-line and 120-line limits from this plan.]

## Evidence Map

[Describe the Evidence Map table shape from this plan.]

## B档 Escalation

B档 starts only after NEED_DEEP_REVIEW and reads only the requested file ranges.

## Out-of-Scope Extension Points

[List the extension points from this plan.]
```

- [ ] **Step 2: Update `docs/specs/agent-workflow.md`**

Add a concise subsection under `## 审查与交付` after the existing review comment rules. The subsection should say:

```markdown
### Review Packet Gate v1

- Implementation PRs should provide `.logs/review/latest/review-packet.md` before Codex review.
- Codex A档 reviews only the Review Packet first.
- Without a Review Packet, the reviewer should request packet generation instead of starting full-repository review.
- A档 verdicts are limited to `PASS`, `BLOCK`, and `NEED_DEEP_REVIEW`.
- `NEED_DEEP_REVIEW` must list explicit file paths and line ranges for B档.
- Review Packet requirements are defined in `docs/specs/review-packet-gate.md`.
```

- [ ] **Step 3: Validate docs contain the gate language**

Run:

```bash
python - <<'PY'
from pathlib import Path
spec = Path('docs/specs/review-packet-gate.md').read_text(encoding='utf-8')
workflow = Path('docs/specs/agent-workflow.md').read_text(encoding='utf-8')
required_spec = [
    'No `review-packet.md`, no Codex implementation review.',
    'PASS / BLOCK / NEED_DEEP_REVIEW',
    'review-packet.md <= 300 lines',
    'Key Hunks <= 120 lines',
    'Evidence Map',
]
required_workflow = [
    '### Review Packet Gate v1',
    'Codex A档 reviews only the Review Packet first.',
    'NEED_DEEP_REVIEW',
    'docs/specs/review-packet-gate.md',
]
for item in required_spec:
    assert item in spec, item
for item in required_workflow:
    assert item in workflow, item
print('review packet gate docs shape: PASS')
PY
```

Expected result:

```text
review packet gate docs shape: PASS
```

- [ ] **Step 4: Commit Task 1**

```bash
git add docs/specs/review-packet-gate.md docs/specs/agent-workflow.md
git commit -m "docs: define review packet gate v1"
```

Expected result:

```text
[branch] docs: define review packet gate v1
```

---

## Task 2: Add the minimal Review Packet generator

**Files:**

- Create: `scripts/dev/build_review_packet.py`
- Modify: `.gitignore`
- Test: `tests/test_build_review_packet.py`

- [ ] **Step 1: Add failing tests for generator output shape**

Create `tests/test_build_review_packet.py` with tests that initialize a temporary Git repository, create a base commit, modify a file, run the script, and assert required sections exist.

Test skeleton:

```python
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'dev' / 'build_review_packet.py'


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


class BuildReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(['git', 'init'], self.repo)
        run(['git', 'config', 'user.email', 'test@example.com'], self.repo)
        run(['git', 'config', 'user.name', 'Test User'], self.repo)
        (self.repo / 'sample.py').write_text('print("base")\n', encoding='utf-8')
        run(['git', 'add', 'sample.py'], self.repo)
        run(['git', 'commit', '-m', 'base'], self.repo)
        run(['git', 'branch', '-M', 'main'], self.repo)
        (self.repo / 'sample.py').write_text('import os\nprint("changed")\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_packet_contains_required_sections(self):
        out = self.repo / '.logs' / 'review' / 'latest' / 'review-packet.md'
        run([sys.executable, str(SCRIPT), '--base', 'main', '--out', str(out)], self.repo)
        packet = out.read_text(encoding='utf-8')
        for heading in [
            '# Review Packet',
            '## Metadata',
            '## Changed Files',
            '## Diff Stat',
            '## Diff Check',
            '## Allowed Files Check',
            '## Forbidden Patterns Check',
            '## Dependency / Import Diff',
            '## Test Summary',
            '## Key Hunks',
            '## Evidence Map',
            '## Acceptance Checklist',
            '## Implementer Risk Notes',
            '## Review Trigger Result',
        ]:
            self.assertIn(heading, packet)
        self.assertIn('PACKET_TOO_LARGE = NO', packet)

    def test_packet_records_manual_allowlist_when_no_allowlist_is_provided(self):
        out = self.repo / '.logs' / 'review' / 'latest' / 'review-packet.md'
        run([sys.executable, str(SCRIPT), '--base', 'main', '--out', str(out)], self.repo)
        packet = out.read_text(encoding='utf-8')
        self.assertIn('ALLOWLIST_CHECK = MANUAL_REVIEW_REQUIRED', packet)

    def test_packet_marks_forbidden_pattern_hits(self):
        out = self.repo / '.logs' / 'review' / 'latest' / 'review-packet.md'
        (self.repo / 'sample.py').write_text('provider = "demo"\nprint(provider)\n', encoding='utf-8')
        run([sys.executable, str(SCRIPT), '--base', 'main', '--out', str(out)], self.repo)
        packet = out.read_text(encoding='utf-8')
        self.assertIn('FORBIDDEN_PATTERN_SCAN = WARN', packet)
        self.assertIn('provider', packet)


if __name__ == '__main__':
    unittest.main()
```

Run:

```bash
python -m unittest tests.test_build_review_packet -v
```

Expected result before script implementation:

```text
FAILED
```

The failure should be caused by the missing `scripts/dev/build_review_packet.py` file.

- [ ] **Step 2: Implement `scripts/dev/build_review_packet.py`**

Implement a standard-library script with this CLI:

```text
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md
```

Required options:

```text
--base <ref>               default: main
--out <path>               default: .logs/review/latest/review-packet.md
--allowlist <glob>         may be repeated
--test-command <command>   may be repeated; records summary text only
--acceptance <text>        may be repeated; creates Evidence Map scaffold rows
```

Implementation outline:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

FORBIDDEN_PATTERNS = [
    'provider', 'network', 'env', 'dependency', 'live AI',
    'fallback', 'compatibility', 'default', 'silently ignore', 'optional',
]
DEPENDENCY_FILES = {
    'requirements.txt', 'requirements-dev.txt', 'pyproject.toml',
    'poetry.lock', 'package.json', 'package-lock.json', 'pnpm-lock.yaml',
}
MAX_PACKET_LINES = 300
MAX_KEY_HUNK_LINES = 120
MAX_FILES_BEFORE_RISK = 8
MAX_CHANGED_LINES_BEFORE_RISK = 500


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', *args], text=True, capture_output=True, check=False)


def split_lines(text: str) -> list[str]:
    return text.splitlines()


def main() -> int:
    parser = argparse.ArgumentParser(description='Build a bounded Review Packet for Codex A档 review.')
    parser.add_argument('--base', default='main')
    parser.add_argument('--out', default='.logs/review/latest/review-packet.md')
    parser.add_argument('--allowlist', action='append', default=[])
    parser.add_argument('--test-command', action='append', default=[])
    parser.add_argument('--acceptance', action='append', default=[])
    args = parser.parse_args()
    # Generate required sections, enforce limits, write packet, return 0.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

The final implementation must not leave the body as a stub. It must generate the sections required by this plan.

Key behavior requirements:

```text
- Use `git diff --name-only {base}...HEAD` for Changed Files.
- Use `git diff --stat {base}...HEAD` for Diff Stat.
- Use `git diff --check {base}...HEAD` for Diff Check.
- Use `git diff --unified=3 {base}...HEAD` for Key Hunks.
- Include at most one hunk per changed file unless a risk trigger is hit.
- Cap Key Hunks at 120 lines.
- If `--allowlist` is omitted, write `ALLOWLIST_CHECK = MANUAL_REVIEW_REQUIRED`.
- If all changed files match at least one allowlist glob, write `ALLOWLIST_CHECK = PASS`.
- If any changed file misses the allowlist, write `ALLOWLIST_CHECK = FAIL` and list the missed files.
- Scan added diff lines for forbidden patterns and write PASS or WARN.
- Summarize dependency manifest changes and added Python imports.
- Write Evidence Map scaffold rows for `--acceptance` entries.
- Write `PACKET_TOO_LARGE = YES` if the packet exceeds 300 lines after generation.
```

- [ ] **Step 3: Ignore generated review logs**

Modify `.gitignore` and add:

```gitignore
.logs/review/
```

Keep the existing `.logs/validate/` ignore entry.

- [ ] **Step 4: Run generator tests**

Run:

```bash
python -m unittest tests.test_build_review_packet -v
```

Expected result:

```text
OK
```

- [ ] **Step 5: Run the generator on the implementation branch**

Run:

```bash
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md --allowlist 'docs/specs/*' --allowlist '.github/*' --allowlist '.gitignore' --allowlist 'scripts/dev/build_review_packet.py' --allowlist 'tests/test_build_review_packet.py' --allowlist '.oh-my-harness/tree.md' --test-command 'python -m unittest tests.test_build_review_packet -v' --acceptance 'A1: Review Packet Gate workflow is documented' --acceptance 'A2: review-packet.md contains required machine evidence' --acceptance 'A3: packet length and Key Hunks limits are enforced'
```

Expected result:

```text
wrote .logs/review/latest/review-packet.md
PACKET_TOO_LARGE = NO
```

- [ ] **Step 6: Commit Task 2**

```bash
git add scripts/dev/build_review_packet.py tests/test_build_review_packet.py .gitignore
git commit -m "chore: add review packet generator"
```

Expected result:

```text
[branch] chore: add review packet generator
```

---

## Task 3: Add Codex A档 prompt guidance

**Files:**

- Modify: `.github/codex-review-comment.md`
- Test: inline documentation shape check command shown below

- [ ] **Step 1: Update `.github/codex-review-comment.md`**

Add a short Review Packet A档 section that instructs reviewers to start from the packet before requesting broader context.

Add content equivalent to:

```markdown
## Review Packet Gate v1

For Implementation PRs, start with `.logs/review/latest/review-packet.md` when available.

A档 review output must use one verdict:

- `PASS`
- `BLOCK`
- `NEED_DEEP_REVIEW`

A档 should not perform repository-wide context discovery by default. If evidence is insufficient, output `Minimal Next Reads` with explicit file paths and line ranges.
```

- [ ] **Step 2: Validate Codex guidance wording**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('.github/codex-review-comment.md').read_text(encoding='utf-8')
for item in [
    'Review Packet Gate v1',
    '.logs/review/latest/review-packet.md',
    'PASS',
    'BLOCK',
    'NEED_DEEP_REVIEW',
    'Minimal Next Reads',
]:
    assert item in text, item
print('codex review packet guidance: PASS')
PY
```

Expected result:

```text
codex review packet guidance: PASS
```

- [ ] **Step 3: Commit Task 3**

```bash
git add .github/codex-review-comment.md
git commit -m "docs: add codex review packet guidance"
```

Expected result:

```text
[branch] docs: add codex review packet guidance
```

---

## Task 4: Refresh tree and run final validation

**Files:**

- Modify: `.oh-my-harness/tree.md`
- Test: repository validation commands listed below

- [ ] **Step 1: Refresh the tree file**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md updated
```

If the hook prints a different success message but updates `.oh-my-harness/tree.md`, record the exact message in the Implementation PR validation section.

- [ ] **Step 2: Run full unittest discovery**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result:

```text
OK
```

- [ ] **Step 3: Run Review Packet docs checks**

Run the Task 1 and Task 3 inline documentation checks again.

Expected result:

```text
review packet gate docs shape: PASS
codex review packet guidance: PASS
```

- [ ] **Step 4: Run the Review Packet generator for this PR**

Run:

```bash
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md --allowlist 'docs/specs/*' --allowlist '.github/*' --allowlist '.gitignore' --allowlist 'scripts/dev/build_review_packet.py' --allowlist 'tests/test_build_review_packet.py' --allowlist '.oh-my-harness/tree.md' --test-command 'PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"' --test-command 'python -m unittest tests.test_build_review_packet -v' --acceptance 'A1: Review Packet Gate workflow is documented' --acceptance 'A2: review-packet.md contains required machine evidence' --acceptance 'A3: packet length and Key Hunks limits are enforced' --acceptance 'A4: Codex A档 starts from review-packet.md'
```

Expected result:

```text
wrote .logs/review/latest/review-packet.md
PACKET_TOO_LARGE = NO
```

- [ ] **Step 5: Check diff cleanliness**

Run:

```bash
git diff --check
```

Expected result:

```text
(no output)
```

- [ ] **Step 6: Commit final tree update**

```bash
git add .oh-my-harness/tree.md
git commit -m "chore: refresh tree for review packet gate"
```

Expected result:

```text
[branch] chore: refresh tree for review packet gate
```

If `.oh-my-harness/tree.md` has no changes after hook refresh, skip this commit and record `tree already current` in the PR description.

---

## Acceptance Criteria

- [ ] `docs/specs/review-packet-gate.md` exists and defines Review Packet Gate v1.
- [ ] `docs/specs/agent-workflow.md` states that Codex A档 starts from `.logs/review/latest/review-packet.md`.
- [ ] `.github/codex-review-comment.md` includes A档 verdict guidance.
- [ ] `scripts/dev/build_review_packet.py` exists and runs with `--base main --out .logs/review/latest/review-packet.md`.
- [ ] Generated packet includes all required v1 sections.
- [ ] Packet length check writes `PACKET_TOO_LARGE = YES` or `PACKET_TOO_LARGE = NO`.
- [ ] Key Hunks section is capped at 120 lines.
- [ ] `.gitignore` ignores `.logs/review/`.
- [ ] `python -m unittest tests.test_build_review_packet -v` passes.
- [ ] `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` passes.
- [ ] `git diff --check` passes.
- [ ] Business runtime files under `src/werewolf_eval/**` remain unchanged.

## Review Packet Requirements for This Implementation PR

The Implementation PR must provide `.logs/review/latest/review-packet.md` before asking Codex for review.

The Review Packet for this PR must include this Evidence Map:

```text
| Acceptance | Evidence | Status |
|---|---|---|
| A1: workflow documented | `docs/specs/review-packet-gate.md`; `docs/specs/agent-workflow.md`; docs shape check | PASS |
| A2: generator produces required machine evidence | `tests/test_build_review_packet.py::test_packet_contains_required_sections`; generated packet | PASS |
| A3: packet limit behavior exists | `tests/test_build_review_packet.py`; `PACKET_TOO_LARGE` output | PASS |
| A4: Codex A档 guidance exists | `.github/codex-review-comment.md`; guidance wording check | PASS |
| A5: no business runtime changes | `git diff --name-only main...HEAD`; allowed files check | PASS |
```

If any row cannot be supported by machine evidence, mark it `MANUAL_REVIEW_REQUIRED` and explain why in Implementer Risk Notes.

## Implementation PR Description Draft

```markdown
## Summary

Add Review Packet Gate v1 so implementation reviews start from a bounded evidence packet rather than default full-repository context discovery.

Bound plan: `docs/harness/plans/2026-05-31--review-packet-gate-v1-plan.md`

## What changed

- Added `docs/specs/review-packet-gate.md` with Review Packet v1 rules.
- Updated `docs/specs/agent-workflow.md` to require Review Packet-first Codex A档 review.
- Updated `.github/codex-review-comment.md` with PASS / BLOCK / NEED_DEEP_REVIEW guidance.
- Added `scripts/dev/build_review_packet.py`.
- Added `tests/test_build_review_packet.py`.
- Ignored `.logs/review/` generated artifacts.
- Refreshed `.oh-my-harness/tree.md` if needed.

## Review Packet

Generated packet:

```text
.logs/review/latest/review-packet.md
```

A档 reviewer should start from the packet and should not perform full-repository context discovery unless the verdict is `NEED_DEEP_REVIEW`.

## Validation

```text
python -m unittest tests.test_build_review_packet -v
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md ...
git diff --check
```

## Risk notes

- This PR changes workflow documentation and developer tooling only.
- No business runtime files under `src/werewolf_eval/**` should change.
- v1 allowlist support is glob-based and explicit; plan parsing is an extension point outside this PR.
- Generated `.logs/review/` files are ignored and should not be committed.
```

## Handoff Prompt for Claude Code

```text
接手当前 Implementation Plan，完成 Review Packet Gate v1 实现 PR。

要求：

- 先阅读 AGENTS.md、docs/specs/agent-workflow.md、docs/harness/plans/2026-05-31--review-packet-gate-v1-plan.md 和 .oh-my-harness/tree.md。
- 不要读取 docs/ai-worklog。
- 不要修改业务逻辑代码。
- 不要修改运行时业务行为。
- 修改范围优先限制在 plan 的 Global Allowed Scope。
- 如果必须修改范围外文件，先说明原因，并在 review-packet.md 中标记为 WARN。
- 每完成一个任务就运行对应验证。
- 最后必须生成 .logs/review/latest/review-packet.md。

完成后输出：

- changed files
- validation result
- review-packet.md 路径
- 是否触发 Codex B档深审
- 是否需要继续修复
```

## Handoff Prompt for Codex A档 Review

```text
你现在进入省余额审查模式，只做 Codex A档高风险 gate。

只审查我提供的 review-packet.md。

严格限制：

- 除非发现明确 blocker 或明确缺证据，否则不要读取任何本地文件。
- 不要读取完整 plan。
- 不要读取完整 README / TASKS / AGENTS。
- 不要运行宽泛 rg。
- 不要打印完整 diff。
- 不要自行扩大搜索范围。
- 不要基于 Claude Code 自述直接下结论，优先看机器生成证据。
- A档只能输出一次结论。若信息不足，只列 Minimal Next Reads，不要继续推理或请求宽泛材料。

请基于 review-packet.md 输出：

1. Verdict: PASS / BLOCK / NEED_DEEP_REVIEW
2. Blockers
3. Evidence Gaps
4. Suspicious Areas
5. Minimal Next Reads
6. Minimal Fix Prompt

判定规则：

- 如果 PACKET_TOO_LARGE = YES，默认 NEED_DEEP_REVIEW，并要求明确行段。
- 如果测试失败，BLOCK。
- 如果验收标准没有 Evidence Map 支撑，NEED_DEEP_REVIEW。
- 如果 forbidden scan 命中 provider / network / env / dependency / live AI，默认 NEED_DEEP_REVIEW，除非 packet 已证明无风险。
- 如果没有明确 blocker，也没有关键证据缺口，输出 PASS 后停止。

不要做风格建议。
不要重复总结任务背景。
没有证据的问题不要当 blocker。
```
