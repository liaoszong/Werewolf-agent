# Phase 1 Closure and Phase 2 Boundary Alignment Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Close the Phase 1 deterministic MVP, align repository status documents with merged PR facts, defer S4/S5 to Phase 2, and prevent E1-E4 from being started under the Phase 1 no-business-code boundary.

**Architecture:** This is a documentation-only boundary-alignment task. It updates stable project status and task routing documents after S0/S1/S2/S3/S6 have produced the Phase 1 deterministic static demo artifacts. It does not create runtime code, parser/scorer/attribution implementation, app/server/web directories, dependencies, or new gold/demo data.

**Tech Stack:** Markdown only. Validation uses shell commands and Python standard library text checks. No runtime dependencies.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before executing this plan, progress must be checked through PR-first facts and main artifacts, not only `docs/TASKS.md` state fields.

Current expected facts:

- S0 implementation completed through PR #2, producing `docs/gold-game/s0-gold-game-seed.md`.
- S1 implementation completed through PR #4, producing `docs/gold-game/g001-game-log.json` and `docs/gold-game/s1-schema-validation.md`.
- S2 implementation completed through PR #6, producing `docs/gold-game/s2-score-log.json`, `docs/gold-game/s2-metrics-summary.json`, and `docs/gold-game/s2-scoring-validation.md`.
- S3 implementation completed through PR #7, producing `docs/gold-game/s3-rule-attribution.json` and `docs/gold-game/s3-attribution-validation.md`.
- S6 implementation completed through PR #9, producing `docs/demo/phase1-gold-demo.html`.
- S4 and S5 are intentionally deferred to Phase 2 and must not block Phase 1 deterministic MVP closure.
- E1-E4 are engineering implementation tasks and must not be started while the Phase 1 boundary remains documentation/spike-only.

## Scope Decision

This plan should be implemented as a single documentation-only Implementation PR.

No Research PR is needed because the decision boundary is clear:

- The repository facts already show the Phase 1 deterministic MVP outputs are present.
- The current docs are stale because M1, S2, S3, and S6 still show `pending` in `docs/TASKS.md`.
- S4/S5 and E1-E4 need explicit routing into Phase 2 so future agents do not start runtime implementation under Phase 1 rules.

## Files

- Create: none.
- Modify: `docs/TASKS.md`.
- Modify: `README.md`.
- Modify: `docs/PRODUCT_ONE_PAGER.md`.
- Modify: `AGENTS.md` only if needed to record stable Phase 1 closure / Phase 2 routing facts.
- Do not modify: `docs/EVALUATION_RUBRIC.md`.
- Do not modify: `docs/GOLD_DEMO.md`.
- Do not modify: `docs/SPIKES.md`.
- Do not modify: any `docs/gold-game/*` artifact.
- Do not modify: `docs/demo/phase1-gold-demo.html`.
- Test file: no committed test file for this documentation-only task. Each task includes explicit shell/Python validation commands.

## Hard Boundaries

- Do not create `src/`, `apps/`, `server/`, `web/`, `tools/`, or `tests/`.
- Do not create `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, or any dependency manifest.
- Do not implement E1 Game Log parser.
- Do not implement E2 deterministic scorer.
- Do not implement E3 attribution engine.
- Do not implement E4 production visualization app.
- Do not create or modify business/runtime code.
- Do not change `docs/EVALUATION_RUBRIC.md` scoring rules.
- Do not change accepted S0/S1/S2/S3/S6 outputs.
- Do not claim real AI Agent gameplay exists.
- Do not claim real Consensus Log or real Decision Log collection exists.
- Do not claim `decision_quality_score` is genuinely available in Phase 1.
- Do not claim the Leaderboard is real; it remains a UI demo with one deterministic row plus mock rows.

---

### Task 1: Preflight current progress and documentation boundary

**Files:**

- Create: none.
- Modify: none.
- Test file: none; use repository and document inspection commands.

- [ ] **Step 1: Verify PR-first progress facts**

Run:

```bash
gh pr list --state merged --limit 10
```

Expected result must include these merged PRs or equivalent newer merged PRs that preserve the same facts:

```text
#9 Add S6 Leaderboard UI Demo Validation
#8 Plan S6 Leaderboard UI Demo Validation
#7 Add S3 Rule Attribution Validation
#6 Add S2 Deterministic Scorer Validation
#5 Plan S2 Deterministic Scorer Validation
#4 Add S1 Game Log Schema Validation
#3 Plan S1 Game Log Schema Validation
#2 Add S0 Gold Game Seed
#1 Plan S0 Gold Game Seed
```

- [ ] **Step 2: Verify recent main history**

Run:

```bash
git log --oneline -10
```

Expected result must include the latest S6 merge near the top:

```text
b4d165e Merge pull request #9 from liaoszong/task/s6-leaderboard-ui-demo-validation
```

If the hash differs because main has advanced, continue only if the latest history still contains the S6 merge and no newer PR has already completed this Phase 1 closure task.

- [ ] **Step 3: Verify Phase 1 artifact files exist**

Run:

```bash
test -f docs/gold-game/s0-gold-game-seed.md
test -f docs/gold-game/g001-game-log.json
test -f docs/gold-game/s1-schema-validation.md
test -f docs/gold-game/s2-score-log.json
test -f docs/gold-game/s2-metrics-summary.json
test -f docs/gold-game/s2-scoring-validation.md
test -f docs/gold-game/s3-rule-attribution.json
test -f docs/gold-game/s3-attribution-validation.md
test -f docs/demo/phase1-gold-demo.html
printf 'Phase 1 completed artifacts exist\n'
```

Expected result:

```text
Phase 1 completed artifacts exist
```

- [ ] **Step 4: Verify the repository still has no runtime implementation directories**

Run:

```bash
test ! -d src
test ! -d apps
test ! -d server
test ! -d web
test ! -d tools
test ! -d tests
test ! -f package.json
test ! -f package-lock.json
test ! -f pnpm-lock.yaml
test ! -f yarn.lock
printf 'No runtime implementation boundary drift detected\n'
```

Expected result:

```text
No runtime implementation boundary drift detected
```

No commit is required for Task 1 because no files are modified.

---

### Task 2: Update `docs/TASKS.md` to close M1 and defer S4/S5

**Files:**

- Create: none.
- Modify: `docs/TASKS.md`.
- Test file: none; use Python text validation.

- [ ] **Step 1: Update Product Milestone status**

In `docs/TASKS.md`, update M1 from `pending` to `completed` and add a completion note that cites the fixed artifact chain.

Replace the M1 status block with content equivalent to:

```md
- 状态：`completed`（deterministic MVP closure：S0/S1/S2/S3/S6 已完成；S4/S5 延后到 Phase 2）
- 完成产物：
  - `docs/gold-game/g001-game-log.json`
  - `docs/gold-game/s2-score-log.json`
  - `docs/gold-game/s2-metrics-summary.json`
  - `docs/gold-game/s3-rule-attribution.json`
  - `docs/demo/phase1-gold-demo.html`
- 注意：Phase 1 的 decision_quality_score 恒为 0（无真实 Decision Log），不宣称已真实可用。Consensus Log 和 Decision Log 的真实数据采集转入 Phase 2。
```

- [ ] **Step 2: Update S2, S3, and S6 statuses**

In `docs/TASKS.md`, update:

```md
### S2：确定性评分器验证
```

so its status and output lines state:

```md
- 状态：`completed`（PR #5 plan, PR #6 impl）
- 产出：`docs/gold-game/s2-score-log.json` + `docs/gold-game/s2-metrics-summary.json` + `docs/gold-game/s2-scoring-validation.md`。
```

Update:

```md
### S3：规则归因验证
```

so its status and output lines state:

```md
- 状态：`completed`（PR #7 impl）
- 产出：`docs/gold-game/s3-rule-attribution.json` + `docs/gold-game/s3-attribution-validation.md`。
```

Update:

```md
### S6：Leaderboard UI demo 验证
```

so its status and output lines state:

```md
- 状态：`completed`（PR #8 plan, PR #9 impl）
- 产出：`docs/demo/phase1-gold-demo.html`。
```

- [ ] **Step 3: Defer S4 and S5 to Phase 2**

In `docs/TASKS.md`, update:

```md
### S4：狼人 Consensus Log schema 验证
```

so its status line states:

```md
- 状态：`deferred_to_phase_2`（真实 Consensus Log 为 Phase 2 启用；Phase 1 deterministic MVP 不再阻塞于人工 consensus sample）
```

Update:

```md
### S5：AI 语义标注可行性验证
```

so its status line states:

```md
- 状态：`deferred_to_phase_2`（AI 标注与真实 Agent 输出、Decision Log 启用一起验证；Phase 1 demo 不依赖 AI 标注）
```

Keep their original spike descriptions and pass/fail criteria in place as Phase 2 references. Do not delete S4/S5 sections.

- [ ] **Step 4: Move E1-E4 to Phase 2 candidate engineering tasks**

In `docs/TASKS.md`, rename the engineering section heading to:

```md
## Phase 2 Candidate Engineering Tasks
```

Replace the current sentence:

```md
**仅在对应 spike 通过后创建。** 此处只列出预期工程任务类型，不展开细节步骤。
```

with:

```md
**Phase 1 不启动 E1-E4。** 这些任务是 Phase 2 候选工程任务，只有在 Phase 2 charter / Implementation Plan 明确允许业务代码后才能展开。此处只保留任务路由，不代表已开始实现。
```

Update statuses:

```md
- E1：`phase_2_candidate`（S0/S1 已满足；等待 Phase 2 实现边界打开）
- E2：`phase_2_candidate`（S2 已满足；等待 E1 与 Phase 2 实现边界）
- E3：`phase_2_candidate`（S3 已满足；等待 E1/E2 与 Phase 2 实现边界）
- E4：`phase_2_candidate`（S6 已满足；Phase 1 已有静态 HTML demo，Phase 2 是否重做由后续 plan 决定）
```

- [ ] **Step 5: Update Demo Acceptance**

In `docs/TASKS.md`, update Demo Acceptance so it no longer says the complete Gold Demo requires S4 and E1-E4 for Phase 1 closure.

Use content equivalent to:

```md
**Demo 1：Phase 1 deterministic Gold Demo**

- 触发条件：S0/S1/S2/S3/S6 完成后。
- 演示内容：固定 Game Log → 确定性评分摘要 → 规则归因 → 静态 Leaderboard UI demo。
- 验收：同一 Game Log 的 deterministic 指标可复现；非技术用户 3 分钟内能复述谁赢了、关键转折点是什么、评测系统如何打分。
- 状态：`completed`（`docs/demo/phase1-gold-demo.html`）

**Demo 2：Phase 2 runtime pipeline demo**

- 触发条件：Phase 2 charter 明确允许业务代码，并完成 E1-E4 或替代实现路径。
- 演示内容：运行时读取 Game Log → 计算 Score Log → 计算 Attribution → 输出或刷新 UI。
- 验收：后续 Phase 2 plan 定义。
```

- [ ] **Step 6: Validate `docs/TASKS.md` text**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/TASKS.md').read_text(encoding='utf-8')
required = [
    'M1：评测系统概念验证完成',
    '状态：`completed`（deterministic MVP closure：S0/S1/S2/S3/S6 已完成；S4/S5 延后到 Phase 2）',
    'S2：确定性评分器验证',
    '状态：`completed`（PR #5 plan, PR #6 impl）',
    'S3：规则归因验证',
    '状态：`completed`（PR #7 impl）',
    'S6：Leaderboard UI demo 验证',
    '状态：`completed`（PR #8 plan, PR #9 impl）',
    'S4：狼人 Consensus Log schema 验证',
    '状态：`deferred_to_phase_2`',
    'S5：AI 语义标注可行性验证',
    '## Phase 2 Candidate Engineering Tasks',
    'Phase 1 不启动 E1-E4',
    'Demo 1：Phase 1 deterministic Gold Demo',
    'Demo 2：Phase 2 runtime pipeline demo',
]
missing = [item for item in required if item not in text]
assert not missing, missing
print('TASKS phase closure text validated')
PY
```

Expected result:

```text
TASKS phase closure text validated
```

- [ ] **Step 7: Commit `docs/TASKS.md` update**

Run:

```bash
git add docs/TASKS.md
git commit -m "docs: close phase1 task status"
```

Expected result:

```text
[task/phase1-closure-phase2-boundary ...] docs: close phase1 task status
```

The exact commit hash may differ.

---

### Task 3: Update `README.md` current status

**Files:**

- Create: none.
- Modify: `README.md`.
- Test file: none; use Python text validation.

- [ ] **Step 1: Replace stale current status**

In `README.md`, replace the current `## 当前状态` section content:

```md
**Phase 1 文档启动阶段。** 评测体系设计已完成审查（2026-05），正在建立产品文档和 spike 计划。暂无业务代码。
```

with:

```md
**Phase 1 deterministic MVP 已完成。** 当前 main 已包含一局人工构造的 6 人 Gold Game、结构化 Game Log、确定性评分产物、规则归因产物和单文件静态 Leaderboard UI demo。仓库仍无业务代码；E1-E4 运行时实现任务转入 Phase 2 候选范围。

Phase 1 不代表真实 AI Agent 对局、真实 Decision Log / Consensus Log 采集、真实多模型 Leaderboard 或真实 `decision_quality_score` 可用。
```

- [ ] **Step 2: Keep document index accurate**

In the README document index, keep existing rows and ensure `TASKS` still describes execution/routing. If the current row says:

```md
| [TASKS](docs/TASKS.md) | 工程执行清单：承接已验证工作，不替代产品探索 |
```

it may remain unchanged.

- [ ] **Step 3: Validate `README.md` text**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('README.md').read_text(encoding='utf-8')
required = [
    'Phase 1 deterministic MVP 已完成',
    '结构化 Game Log',
    '确定性评分产物',
    '规则归因产物',
    '单文件静态 Leaderboard UI demo',
    '仓库仍无业务代码',
    'E1-E4 运行时实现任务转入 Phase 2 候选范围',
    '不代表真实 AI Agent 对局',
    '真实 `decision_quality_score` 可用',
]
missing = [item for item in required if item not in text]
assert not missing, missing
assert 'Phase 1 文档启动阶段' not in text
print('README phase closure text validated')
PY
```

Expected result:

```text
README phase closure text validated
```

- [ ] **Step 4: Commit `README.md` update**

Run:

```bash
git add README.md
git commit -m "docs: update readme phase1 status"
```

Expected result:

```text
[task/phase1-closure-phase2-boundary ...] docs: update readme phase1 status
```

The exact commit hash may differ.

---

### Task 4: Update `docs/PRODUCT_ONE_PAGER.md` Phase 1 / Phase 2 boundary

**Files:**

- Create: none.
- Modify: `docs/PRODUCT_ONE_PAGER.md`.
- Test file: none; use Python text validation.

- [ ] **Step 1: Update `## Phase 1 做什么`**

In `docs/PRODUCT_ONE_PAGER.md`, replace the current Phase 1 list that says `7 个 spike 验证所有关键不确定性` with a closure-oriented list equivalent to:

```md
## Phase 1 做什么

Phase 1 deterministic MVP 已完成以下闭环：

- 选定一局 6 人狼人杀人工 Gold Game → 整理结构化 Game Log。
- 产出确定性的 outcome_score + rule_integrity_score + 过程指标 + 结果指标。
- 产出确定性规则归因：turn_points + top_attribution。
- 构建最小可视化页面：时间线、状态表、投票表、指标表、单局评分卡、Leaderboard UI demo。
- 保持所有数据来源标注：`[结构化事件]`、`[deterministic]`、`[mock]`、`[人工 gold sample]`。

Phase 1 closure 使用 S0/S1/S2/S3/S6。S4 Consensus Log schema 验证和 S5 AI 语义标注可行性验证延后到 Phase 2，与真实 Agent 输出、真实 Decision Log / Consensus Log 启用一起验证。
```

- [ ] **Step 2: Update four-layer log table if needed**

In the `日志四层结构` table, keep the existing Phase 1/Phase 2 distinction, but ensure it does not imply real Consensus Log or real Decision Log exist in Phase 1.

The intended rows are:

```md
| Game Log | 事实事件（不可变） | 人工整理 Gold Game | AI Agent 对局产生 |
| Consensus Log | 狼人夜间协商过程（Phase 2 启用） | 不作为 Phase 1 closure 阻塞项 | AI Agent 产生 |
| Decision Log | 行动前结构化理由（Phase 2 启用） | 不作为 Phase 1 closure 阻塞项；decision_quality_score 恒为 0 | AI Agent 产生 |
| Score Log | 评分器输出（可重算） | 确定性规则计算产物 | 完整三维评分 |
```

- [ ] **Step 3: Update `Phase 2 / Phase 3 概述`**

Replace the Phase 2 line with content equivalent to:

```md
- **Phase 2**：打开运行时实现边界，启动 E1-E4 或替代工程路径；接入真实 AI Agent，启用真实 Decision Log / Consensus Log，并重新验证 S4/S5。
```

Keep the Phase 3 line focused on multi-model, role rotation, and statistically meaningful Leaderboard.

- [ ] **Step 4: Validate `PRODUCT_ONE_PAGER.md` text**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/PRODUCT_ONE_PAGER.md').read_text(encoding='utf-8')
required = [
    'Phase 1 deterministic MVP 已完成以下闭环',
    'Phase 1 closure 使用 S0/S1/S2/S3/S6',
    'S4 Consensus Log schema 验证和 S5 AI 语义标注可行性验证延后到 Phase 2',
    '不作为 Phase 1 closure 阻塞项',
    'decision_quality_score 恒为 0',
    '打开运行时实现边界，启动 E1-E4 或替代工程路径',
]
missing = [item for item in required if item not in text]
assert not missing, missing
assert '7 个 spike 验证所有关键不确定性' not in text
print('PRODUCT_ONE_PAGER phase boundary text validated')
PY
```

Expected result:

```text
PRODUCT_ONE_PAGER phase boundary text validated
```

- [ ] **Step 5: Commit product one-pager update**

Run:

```bash
git add docs/PRODUCT_ONE_PAGER.md
git commit -m "docs: align product phases after phase1 closure"
```

Expected result:

```text
[task/phase1-closure-phase2-boundary ...] docs: align product phases after phase1 closure
```

The exact commit hash may differ.

---

### Task 5: Minimally update `AGENTS.md` stable routing facts

**Files:**

- Create: none.
- Modify: `AGENTS.md`.
- Test file: none; use Python text validation.

- [ ] **Step 1: Update project status without copying volatile detail**

In `AGENTS.md`, keep it short. Do not copy score formulas, role rubric, or artifact details.

Change the project positioning bullet from:

```md
- 项目定位：AI 狼人杀多智能体协作与博弈评测系统。Phase 1 构建"结构化 Game Log + 确定性评测 + 规则归因 + Leaderboard UI demo"。
```

To:

```md
- 项目定位：AI 狼人杀多智能体协作与博弈评测系统。Phase 1 deterministic MVP 已闭合为"结构化 Game Log + 确定性评测 + 规则归因 + Leaderboard UI demo"；Phase 2 才打开运行时实现边界。
```

- [ ] **Step 2: Update architecture boundary with stable routing**

In `AGENTS.md` under `## 架构边界`, keep the existing Phase 1 boundary, but append one stable routing bullet:

```md
- S4/S5 和 E1-E4 已转入 Phase 2 路由：Phase 1 closure 不再阻塞于人工 Consensus Log sample 或 AI 语义标注；E1-E4 只有在 Phase 2 Implementation Plan 明确允许业务代码后才能启动。
```

- [ ] **Step 3: Update code boundary without allowing immediate code**

In `AGENTS.md` under `## 代码边界`, keep the no-runtime-code rule and replace:

```md
- Phase 2 开始前必须通过所有 Phase 1 spike 验收。
```

with:

```md
- Phase 1 closure 以 S0/S1/S2/S3/S6 为 deterministic MVP 验收链；S4/S5 延后到 Phase 2。
- Phase 2 引入代码前必须有明确的 Phase 2 Implementation Plan，并更新对应测试约束。
```

- [ ] **Step 4: Validate `AGENTS.md` text**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('AGENTS.md').read_text(encoding='utf-8')
required = [
    'Phase 1 deterministic MVP 已闭合',
    'Phase 2 才打开运行时实现边界',
    'S4/S5 和 E1-E4 已转入 Phase 2 路由',
    'E1-E4 只有在 Phase 2 Implementation Plan 明确允许业务代码后才能启动',
    'Phase 1 closure 以 S0/S1/S2/S3/S6 为 deterministic MVP 验收链',
    'Phase 2 引入代码前必须有明确的 Phase 2 Implementation Plan',
]
missing = [item for item in required if item not in text]
assert not missing, missing
assert '评分公式' in text
print('AGENTS phase routing text validated')
PY
```

Expected result:

```text
AGENTS phase routing text validated
```

- [ ] **Step 5: Commit AGENTS update**

Run:

```bash
git add AGENTS.md
git commit -m "docs: route phase2 implementation boundary"
```

Expected result:

```text
[task/phase1-closure-phase2-boundary ...] docs: route phase2 implementation boundary
```

The exact commit hash may differ.

---

### Task 6: Final validation and PR preparation

**Files:**

- Create: none.
- Modify: none by default after previous tasks.
- Test file: none; use full-document validation commands.

- [ ] **Step 1: Run JSON artifact parse checks to ensure accepted outputs were not broken**

Run:

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
printf 'Accepted JSON artifacts still parse\n'
```

Expected result:

```text
Accepted JSON artifacts still parse
```

- [ ] **Step 2: Run final cross-document consistency validation**

Run:

```bash
python - <<'PY'
from pathlib import Path

files = {
    'AGENTS.md': Path('AGENTS.md').read_text(encoding='utf-8'),
    'README.md': Path('README.md').read_text(encoding='utf-8'),
    'docs/TASKS.md': Path('docs/TASKS.md').read_text(encoding='utf-8'),
    'docs/PRODUCT_ONE_PAGER.md': Path('docs/PRODUCT_ONE_PAGER.md').read_text(encoding='utf-8'),
}

required_by_file = {
    'AGENTS.md': [
        'Phase 1 deterministic MVP 已闭合',
        'S4/S5 和 E1-E4 已转入 Phase 2 路由',
    ],
    'README.md': [
        'Phase 1 deterministic MVP 已完成',
        '仓库仍无业务代码',
        'E1-E4 运行时实现任务转入 Phase 2 候选范围',
    ],
    'docs/TASKS.md': [
        '状态：`completed`（deterministic MVP closure：S0/S1/S2/S3/S6 已完成；S4/S5 延后到 Phase 2）',
        '状态：`deferred_to_phase_2`',
        '## Phase 2 Candidate Engineering Tasks',
    ],
    'docs/PRODUCT_ONE_PAGER.md': [
        'Phase 1 deterministic MVP 已完成以下闭环',
        'Phase 1 closure 使用 S0/S1/S2/S3/S6',
        '打开运行时实现边界，启动 E1-E4 或替代工程路径',
    ],
}

for path, required in required_by_file.items():
    missing = [item for item in required if item not in files[path]]
    assert not missing, f'{path} missing: {missing}'

for path, text in files.items():
    assert 'decision_quality_score 已真实可用' not in text, path
    assert '真实 Leaderboard 已完成' not in text, path

print('Phase closure cross-document validation passed')
PY
```

Expected result:

```text
Phase closure cross-document validation passed
```

- [ ] **Step 3: Verify no forbidden files changed**

Run:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
AGENTS.md
README.md
docs/PRODUCT_ONE_PAGER.md
docs/TASKS.md
```

If `.oh-my-harness/tree.md` changes because a local hook refreshes it, include it in the same commit only if the tree file accurately reflects the current repository. Do not manually edit `.oh-my-harness/tree.md`.

- [ ] **Step 4: Verify no runtime directories or dependency manifests exist**

Run:

```bash
test ! -d src
test ! -d apps
test ! -d server
test ! -d web
test ! -d tools
test ! -d tests
test ! -f package.json
test ! -f package-lock.json
test ! -f pnpm-lock.yaml
test ! -f yarn.lock
printf 'No business-code or dependency files introduced\n'
```

Expected result:

```text
No business-code or dependency files introduced
```

- [ ] **Step 5: Check whitespace**

Run:

```bash
git diff --check main...HEAD
```

Expected result:

```text
```

No output means no whitespace errors.

- [ ] **Step 6: Prepare Implementation PR description**

Use this PR description:

```md
## Summary

Closes the Phase 1 deterministic MVP and aligns Phase 2 routing across repository docs.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--phase1-closure-phase2-boundary-alignment-plan.md`

## Scope

- Marks M1 as completed through S0/S1/S2/S3/S6.
- Marks S2, S3, and S6 as completed based on merged PR facts.
- Defers S4 and S5 to Phase 2.
- Moves E1-E4 into Phase 2 candidate engineering routing.
- Updates README current status so it no longer says Phase 1 is only at the documentation-start stage.
- Updates PRODUCT_ONE_PAGER phase boundaries to reflect deterministic MVP closure and Phase 2 runtime implementation boundary.
- Minimally updates AGENTS.md with stable routing facts so future agents do not start E1-E4 under the Phase 1 no-business-code boundary.

## Out of Scope

- No business code.
- No parser, scorer, attribution engine, runtime UI, backend, frontend app, or Agent gameplay.
- No dependency files.
- No changes to `docs/EVALUATION_RUBRIC.md`.
- No changes to accepted `docs/gold-game/*` artifacts.
- No changes to `docs/demo/phase1-gold-demo.html`.
- No S4/S5 implementation.
- No claim that real `decision_quality_score`, real Consensus Log, real Decision Log, or real Leaderboard exists.

## Validation

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
python - <<'PY'
from pathlib import Path

files = {
    'AGENTS.md': Path('AGENTS.md').read_text(encoding='utf-8'),
    'README.md': Path('README.md').read_text(encoding='utf-8'),
    'docs/TASKS.md': Path('docs/TASKS.md').read_text(encoding='utf-8'),
    'docs/PRODUCT_ONE_PAGER.md': Path('docs/PRODUCT_ONE_PAGER.md').read_text(encoding='utf-8'),
}

required_by_file = {
    'AGENTS.md': ['Phase 1 deterministic MVP 已闭合', 'S4/S5 和 E1-E4 已转入 Phase 2 路由'],
    'README.md': ['Phase 1 deterministic MVP 已完成', '仓库仍无业务代码', 'E1-E4 运行时实现任务转入 Phase 2 候选范围'],
    'docs/TASKS.md': ['M1：评测系统概念验证完成', '## Phase 2 Candidate Engineering Tasks', '状态：`deferred_to_phase_2`'],
    'docs/PRODUCT_ONE_PAGER.md': ['Phase 1 deterministic MVP 已完成以下闭环', 'Phase 1 closure 使用 S0/S1/S2/S3/S6'],
}

for path, required in required_by_file.items():
    missing = [item for item in required if item not in files[path]]
    assert not missing, f'{path} missing: {missing}'

print('Phase closure cross-document validation passed')
PY
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected changed files:

```text
AGENTS.md
README.md
docs/PRODUCT_ONE_PAGER.md
docs/TASKS.md
```

## Risk

The main risk is over-updating long-lived rules. This PR should keep AGENTS.md minimal and avoid copying volatile task details or scoring formulas. It should only record the stable routing fact: Phase 1 deterministic MVP is closed, S4/S5 are deferred to Phase 2, and E1-E4 require a Phase 2 Implementation Plan before business code starts.
```

- [ ] **Step 7: Final status check**

Run:

```bash
git status --short
```

Expected result after all commits:

```text
```

No output means the working tree is clean.
