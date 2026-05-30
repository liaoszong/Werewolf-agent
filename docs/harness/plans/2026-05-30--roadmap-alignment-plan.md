# Roadmap Alignment Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a canonical roadmap alignment document and minimally update project entry documents so Werewolf-agent has a visible Phase 2 / Phase 3 route before D2 implementation begins.

**Architecture:** This is a documentation-only alignment PR. `docs/ROADMAP.md` becomes the route source for phase boundaries and dependency order, while `README.md`, `docs/TASKS.md`, and `docs/PRODUCT_ONE_PAGER.md` receive small references or conflict-resolution edits. No runtime, test, scoring, attribution, demo, or gold artifact files are changed.

**Tech Stack:** Markdown only. Validation uses shell commands, `grep`, `git diff --name-only`, and the existing tree refresh hook.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Research PR Decision

No new Research PR is needed.

Reasoning:

- PR #19 has already provided the route decision research.
- The task is not to rediscover the route; it is to codify the route in canonical project docs.
- The implementation boundary is clear and documentation-only.
- This plan prepares one Roadmap Alignment Implementation PR.

## Source Decisions To Preserve

The Roadmap Alignment PR must preserve these decisions from the repository and R1 research:

- Final product vision: an AI Werewolf Agent evaluation + review + leaderboard system, not merely a static demo.
- Current minimum MVP route: `Game Log + Decision Log -> Score Log / Metrics Summary / Rule Attribution / Runtime HTML Demo`.
- Current next implementation direction: D2 Decision Log scoring integration.
- S4 Consensus Log and S5 AI semantic labeling are after D2.
- Real AI Agent gameplay is not Phase 2A; it belongs to Phase 3 / G-track.
- Real multi-game leaderboard is after real gameplay produces enough data; it belongs to L-track / Phase 3+.
- `docs/TASKS.md` is a task status file, not the canonical roadmap.
- `docs/ROADMAP.md` is route alignment, not an Implementation Plan and not a replacement for `docs/TASKS.md`.

## Grill-with-docs Classification

These items must be explicitly reflected in `docs/ROADMAP.md` or linked entry documents:

- `[confirmed by docs]` README and PRODUCT_ONE_PAGER define the project as an evaluation + review + leaderboard system.
- `[confirmed by docs]` E1-E4 and D1 are completed runtime entries; D1 does not connect `decision_quality_score` to scoring.
- `[confirmed by docs]` EVALUATION_RUBRIC defines `decision_quality_score` as a core dimension and Leaderboard default sort key.
- `[confirmed by docs]` R1 recommends D2 next, then S4 and S5, then G1 and L1.
- `[conflict resolved]` PRODUCT_ONE_PAGER previously described Phase 2 as real AI Agent output, while TASKS marks AI Agent autonomous gameplay as Phase 2 non-goal. This PR resolves the conflict by splitting Phase 2A/2B evaluator runtime from Phase 3/G-track real AI gameplay.
- `[inferred]` ROADMAP should become the canonical route source; this follows the need to keep future agents from narrowing into local task fragments.

## Scope Decision

This Implementation PR creates:

- `docs/ROADMAP.md`

It modifies:

- `README.md`
- `docs/TASKS.md`
- `docs/PRODUCT_ONE_PAGER.md`
- `AGENTS.md`
- `.oh-my-harness/tree.md`

It does not modify:

- `src/`
- `tests/`
- `docs/EVALUATION_RUBRIC.md`
- `docs/SPIKES.md`
- `docs/prs/2026-05-30--phase2-next-step-research.md`
- `docs/gold-game/`
- `docs/demo/`
- any runtime, scorer, attribution, parser, validator, or generated artifact file

## Roadmap Content Boundary

`docs/ROADMAP.md` must be concise and directional. It must not become a backlog dump.

It must include:

- final product vision
- current main facts
- phase boundary
- dependency graph
- current priority
- explicit non-goals
- document responsibility map

It must not include:

- provider selection
- prompt design
- full Agent gameplay implementation details
- exact future task plan for every subfeature
- D2 implementation algorithm beyond the route-level statement
- scoring rule changes

---

### Task 1: Preflight current roadmap facts

**Files:**

- Create: none
- Modify: none
- Test: existing docs only

- [ ] **Step 1: Confirm current route-source files exist**

Run:

```bash
test -f README.md
test -f docs/PRODUCT_ONE_PAGER.md
test -f docs/TASKS.md
test -f docs/EVALUATION_RUBRIC.md
test -f docs/prs/2026-05-30--phase2-next-step-research.md
test -f AGENTS.md
test -f .oh-my-harness/tree.md
printf 'roadmap source docs exist\n'
```

Expected result:

```text
roadmap source docs exist
```

- [ ] **Step 2: Confirm R1 route decision is available**

Run:

```bash
grep -R "D2（Decision Log scoring integration）" docs/prs/2026-05-30--phase2-next-step-research.md
grep -R "G1（Agent gameplay engine）" docs/prs/2026-05-30--phase2-next-step-research.md
grep -R "Real multi-game Leaderboard" docs/prs/2026-05-30--phase2-next-step-research.md
```

Expected result:

- The first command prints the R1 next-step recommendation.
- The second command prints the G1 route reference.
- The third command prints the L1 route reference.

- [ ] **Step 3: Confirm current code baseline still passes before documentation changes**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected Game Log output includes:

```text
validated game_id=g001
players=6
events=38
winner=villager
end_round=2
```

Expected Decision Log output:

```text
validated decision_log_id=d1_g001_decision_log
game_id=g001
decisions=10
source_label=[人工 gold sample]
```

Expected unittest output includes:

```text
OK
```

No commit is required for Task 1 because it only verifies the starting state.

---

### Task 2: Add canonical ROADMAP.md

**Files:**

- Create: `docs/ROADMAP.md`
- Modify: none
- Test: grep checks against `docs/ROADMAP.md`

- [ ] **Step 1: Create `docs/ROADMAP.md`**

Create this exact file content:

```markdown
# ROADMAP — Werewolf-agent

## Purpose

`ROADMAP.md` is the canonical route alignment document for Phase 2 / Phase 3 planning. It explains what the project is ultimately trying to become, where the current main branch stands, and why the next task order is D2 before S4/S5/G1.

This document does not replace `docs/TASKS.md`. `TASKS.md` tracks task status and implementation candidates. Implementation details still live in bound plans under `docs/harness/plans/`.

## Final Product Vision

Werewolf-agent aims to become an AI Werewolf Agent evaluation, review, and leaderboard system.

The final product route is:

```text
real or replayed Werewolf games
-> structured Game Log / Decision Log / Consensus Log
-> reproducible Score Log / Metrics Summary
-> deterministic and AI-assisted attribution
-> role-separated scorecards and real multi-game Leaderboard
```

The project is not trying to become only a static HTML demo. The static demos exist to prove that the evaluation loop is visible and understandable before real Agent gameplay is introduced.

## Current Main Facts

The current main branch has completed:

- Phase 1 deterministic MVP.
- E1 Game Log parser / validator.
- E2 deterministic scorer.
- E3 rule attribution engine.
- E4 runtime demo HTML exporter.
- D1 Decision Log runtime input skeleton.
- R1 Phase 2 next-step research.

The current main branch has not completed:

- D2 Decision Log scoring integration.
- S4 Consensus Log runtime/input.
- S5 AI semantic labeling research or integration.
- G1 real AI Agent gameplay engine.
- L1 real multi-game Leaderboard.

## Phase Boundaries

### Phase 1: deterministic MVP closure

Goal: prove that a structured Game Log can produce reproducible deterministic scoring, attribution, and a visible demo.

Status: completed.

Completed route:

```text
Game Log -> deterministic Score Log / Metrics Summary -> Rule Attribution -> static and runtime HTML demo
```

Boundary: Phase 1 does not claim real AI Agent gameplay, real Decision Log / Consensus Log collection, real multi-model Leaderboard, or real `decision_quality_score` availability.

### Phase 2A: evaluator runtime closure

Goal: close the evaluation runtime loop before adding real gameplay.

Minimum closure route:

```text
Game Log + Decision Log -> Score Log / Metrics Summary -> Rule Attribution -> Runtime HTML Demo
```

Current priority: D2 Decision Log scoring integration.

D2 must connect D1 Decision Log input to scoring so `decision_quality_score` is no longer globally fixed at 0. D2 is deterministic and does not call AI.

### Phase 2B: collaboration and semantic inputs

Goal: add the next runtime inputs needed for stronger evaluation.

Candidate tasks:

- S4 Consensus Log runtime/input: validate wolf-team coordination logs.
- S5 AI semantic labeling research: evaluate provider, prompt, accuracy, consistency, token cost, and fallback behavior.

Boundary: S5 integration should not happen before D2 because AI labels need a scoring consumer.

### Phase 3 / G-track: real AI Agent gameplay

Goal: introduce real AI Agent automatic gameplay after evaluator and log contracts are stable.

G1 requires:

- game engine or round driver
- Agent runtime
- provider adapter boundary
- structured Game Log generation
- structured Decision Log generation
- Consensus Log generation for wolf-team nights
- failure recovery and invalid-output handling

Boundary: G1 is not Phase 2A. It is a later gameplay track.

### Phase 3+ / L-track: real multi-game Leaderboard

Goal: aggregate many real games across models, versions, and roles.

L1 requires:

- enough games to make role-separated ranking meaningful
- `games_played` and `role_distribution`
- sample-size warnings
- role tabs
- stable aggregation for `avg_outcome_score`, `avg_decision_quality_score`, and `avg_rule_integrity_score`

Boundary: L1 depends on G1 producing enough multi-game data.

## Dependency Graph

```text
E1 Game Log parser
  -> E2 deterministic scorer
  -> E3 rule attribution
  -> E4 runtime demo

D1 Decision Log input
  + E2 deterministic scorer
  -> D2 Decision Log scoring integration

E1 Game Log parser
  -> S4 Consensus Log runtime/input

D1 + D2
  -> S5 AI semantic labeling research/integration

E1 + D1 + D2 + S4 contracts
  -> G1 real AI Agent gameplay

G1 multi-game outputs
  -> L1 real multi-game Leaderboard
```

## Current Priority

The next implementation priority is D2 Decision Log scoring integration.

Why D2 before S4/S5/G1:

- D2 closes the most important current scoring gap: `decision_quality_score` is still not connected to scoring.
- S4 is valuable but only covers wolf-team coordination.
- S5 needs D2 because semantic labels need a scoring consumer.
- G1 real gameplay should wait until evaluator and log contracts are stable enough to score generated games.

## Explicit Non-goals

Current Phase 2A does not do:

- real AI Agent autonomous gameplay
- game engine implementation
- provider adapter implementation
- real multi-model Leaderboard
- S5 AI semantic scoring integration
- full natural-language review reports
- human-vs-AI UI

D2 specifically must not claim full `decision_quality_score` quality. It only starts the deterministic scoring path. AI-assisted semantic checks remain S5.

## Document Responsibility Map

- `README.md`: short project entry, current status, and links.
- `docs/PRODUCT_ONE_PAGER.md`: product users, value, and high-level product constraints.
- `docs/ROADMAP.md`: phase route, dependency graph, and route conflict resolution.
- `docs/TASKS.md`: task status, candidate tasks, and UX/demo acceptance.
- `docs/EVALUATION_RUBRIC.md`: scoring dimensions, formulas, log schemas, and AI judge boundary.
- `docs/prs/`: research records and route decisions that may later be promoted into stable docs.
- `docs/harness/plans/`: executable implementation protocols.
```

- [ ] **Step 2: Check roadmap content**

Run:

```bash
grep -R "Final Product Vision" docs/ROADMAP.md
grep -R "Phase 2A: evaluator runtime closure" docs/ROADMAP.md
grep -R "D2 Decision Log scoring integration" docs/ROADMAP.md
grep -R "Phase 3 / G-track" docs/ROADMAP.md
grep -R "Phase 3+ / L-track" docs/ROADMAP.md
grep -R "Document Responsibility Map" docs/ROADMAP.md
```

Expected result:

- Each command prints one or more matching lines from `docs/ROADMAP.md`.

- [ ] **Step 3: Commit ROADMAP**

Run:

```bash
git add docs/ROADMAP.md
git commit -m "docs: add project roadmap"
```

---

### Task 3: Update README entry points

**Files:**

- Create: none
- Modify: `README.md`
- Test: grep checks against `README.md`

- [ ] **Step 1: Update current status paragraph**

In `README.md`, replace the current `## 当前状态` paragraph with:

```markdown
**Phase 1 deterministic MVP 已完成，Phase 2 evaluator runtime 正在收口。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer、E3 rule attribution engine、E4 runtime demo HTML exporter；D1 以 `docs/gold-game/g001-decision-log.json` + `src/werewolf_eval/decision_log.py` 提供 Phase 2 Decision Log runtime input skeleton。下一步路线以 `docs/ROADMAP.md` 为准，当前优先级是 D2 Decision Log scoring integration。当前仍不代表真实 AI Agent 对局、真实 Consensus Log、AI 语义标注或真实多模型 Leaderboard 已完成，`decision_quality_score` 仍未接入评分链。
```

- [ ] **Step 2: Add ROADMAP to document index**

In the `## 文档索引` table, add this row before `PRODUCT_ONE_PAGER`:

```markdown
| [ROADMAP](docs/ROADMAP.md) | 总路线：Phase 2 / Phase 3 边界、D2/S4/S5/G1/L1 依赖关系、当前优先级 |
```

- [ ] **Step 3: Check README references**

Run:

```bash
grep -R "Phase 2 evaluator runtime 正在收口" README.md
grep -R "docs/ROADMAP.md" README.md
grep -R "D2 Decision Log scoring integration" README.md
```

Expected result:

- The first command prints the updated current status paragraph.
- The second command prints the ROADMAP reference.
- The third command prints the D2 current priority reference.

- [ ] **Step 4: Commit README update**

Run:

```bash
git add README.md
git commit -m "docs: point README to roadmap"
```

---

### Task 4: Align PRODUCT_ONE_PAGER phase summary

**Files:**

- Create: none
- Modify: `docs/PRODUCT_ONE_PAGER.md`
- Test: grep checks against `docs/PRODUCT_ONE_PAGER.md`

- [ ] **Step 1: Update the input phase sentence**

In `docs/PRODUCT_ONE_PAGER.md`, replace this sentence:

```markdown
Phase 1 使用一局 6 人狼人杀对局的 Game Log。优先使用人工编写的虚拟但逻辑自洽的 6 人对局；如能找到版权合适的公开名局，可使用名局。Phase 2 起由真实 AI Agent 对局产生。
```

with:

```markdown
Phase 1 使用一局 6 人狼人杀对局的 Game Log。优先使用人工编写的虚拟但逻辑自洽的 6 人对局；如能找到版权合适的公开名局，可使用名局。Phase 2A 先完成 evaluator runtime 闭环，仍可使用人工 gold sample / replay log；真实 AI Agent 对局进入 Phase 3 / G-track。
```

- [ ] **Step 2: Replace Phase 2 / Phase 3 overview**

Replace the existing `## Phase 2 / Phase 3 概述` section with:

```markdown
## Phase 2 / Phase 3 概述

详细路线以 `docs/ROADMAP.md` 为准。

- **Phase 2A**：evaluator runtime closure。目标是 `Game Log + Decision Log -> Score Log / Metrics Summary -> Rule Attribution -> Runtime HTML Demo`，优先完成 D2 Decision Log scoring integration。
- **Phase 2B**：collaboration and semantic inputs。目标是补 S4 Consensus Log runtime/input，并对 S5 AI semantic labeling 做 research / spike。
- **Phase 3 / G-track**：real AI Agent gameplay。目标是 game engine + Agent runtime + provider adapter + structured log generation。
- **Phase 3+ / L-track**：real multi-game Leaderboard。目标是多模型、多角色轮换、多局统计与样本量警告。
```

- [ ] **Step 3: Check product phase alignment**

Run:

```bash
grep -R "Phase 2A 先完成 evaluator runtime 闭环" docs/PRODUCT_ONE_PAGER.md
grep -R "真实 AI Agent 对局进入 Phase 3 / G-track" docs/PRODUCT_ONE_PAGER.md
grep -R "详细路线以 `docs/ROADMAP.md` 为准" docs/PRODUCT_ONE_PAGER.md
grep -R "D2 Decision Log scoring integration" docs/PRODUCT_ONE_PAGER.md
```

Expected result:

- Each command prints one matching line from `docs/PRODUCT_ONE_PAGER.md`.

- [ ] **Step 4: Commit PRODUCT_ONE_PAGER update**

Run:

```bash
git add docs/PRODUCT_ONE_PAGER.md
git commit -m "docs: align product phase boundaries"
```

---

### Task 5: Update TASKS role and candidate roadmap tasks

**Files:**

- Create: none
- Modify: `docs/TASKS.md`
- Test: grep checks against `docs/TASKS.md`

- [ ] **Step 1: Update TASKS title**

Replace the first heading:

```markdown
# TASKS — Werewolf-agent Phase 1
```

with:

```markdown
# TASKS — Werewolf-agent Task Status
```

- [ ] **Step 2: Add roadmap note after the progress note**

After the existing progress note, add:

```markdown
> **Roadmap note:** Phase 2 / Phase 3 route boundaries are defined in `docs/ROADMAP.md`. This file tracks task status and candidate engineering work; it does not replace the roadmap.
```

- [ ] **Step 3: Update Phase 2 candidate heading paragraph**

Replace the paragraph under `## Phase 2 Candidate Engineering Tasks` with:

```markdown
**E1-E4 与 D1 已作为 Phase 2 runtime entries 完成。** 当前 Phase 2A 优先级是 D2 Decision Log scoring integration。S4/S5 在 D2 后推进；G1/L1 属于 Phase 3 / Phase 3+ 路线。以下记录各工程任务的完成状态与产物路径，阶段边界以 `docs/ROADMAP.md` 为准。
```

- [ ] **Step 4: Add D2/S4/S5/G1/L1 candidate sections**

After the D1 section, add:

```markdown
### D2：Decision Log scoring integration

- 状态：`candidate_next`（Phase 2A evaluator runtime closure；下一步推荐任务）
- 依赖：D1 + E2。
- 目标：将 Decision Log 接入 scoring，让 `decision_quality_score` 不再全局固定为 0。
- 边界：不调用 AI，不启用 S5，不做 Consensus Log，不宣称 `decision_quality_score` 完整可用。
- 路线依据：`docs/prs/2026-05-30--phase2-next-step-research.md` + `docs/ROADMAP.md`。

### S4：Consensus Log runtime/input

- 状态：`candidate_after_D2`（Phase 2B collaboration input）
- 依赖：E1 / S1；产品优先级上放在 D2 后。
- 目标：验证狼人夜间协商层 Consensus Log 的 parser / validator / fixture / CLI。
- 边界：不做 AI gameplay，不做 S5 语义标注。

### S5：AI semantic labeling research

- 状态：`candidate_after_D2_research_first`（Phase 2B semantic input）
- 依赖：D1；integration 依赖 D2。
- 目标：研究 provider、prompt、准确率、一致性、token 成本和失败降级。
- 边界：先做 Research PR / spike，不直接进入 Implementation Plan。

### G1：Real AI Agent gameplay engine

- 状态：`phase_3_candidate`
- 依赖：稳定的 Game Log / Decision Log / scoring contracts；S4 合同稳定后更安全。
- 目标：实现真实 AI Agent 自动对局，产出结构化 Game Log / Decision Log / Consensus Log。
- 边界：不属于 Phase 2A evaluator runtime closure。

### L1：Real multi-game Leaderboard

- 状态：`phase_3_plus_candidate`
- 依赖：G1 产生足够多局、多角色、多模型数据。
- 目标：形成真实多模型、多版本、按角色区分的 Leaderboard。
- 边界：不在没有多局数据时宣称真实排行榜完成。
```

- [ ] **Step 5: Check TASKS route status**

Run:

```bash
grep -R "TASKS — Werewolf-agent Task Status" docs/TASKS.md
grep -R "Roadmap note" docs/TASKS.md
grep -R "D2：Decision Log scoring integration" docs/TASKS.md
grep -R "G1：Real AI Agent gameplay engine" docs/TASKS.md
grep -R "L1：Real multi-game Leaderboard" docs/TASKS.md
grep -R "phase_3_candidate" docs/TASKS.md
```

Expected result:

- Each command prints one matching line from `docs/TASKS.md`.

- [ ] **Step 6: Commit TASKS update**

Run:

```bash
git add docs/TASKS.md
git commit -m "docs: align tasks with roadmap"
```

---

### Task 6: Update agent docs and tree index

**Files:**

- Create: none
- Modify: `AGENTS.md`
- Modify: `.oh-my-harness/tree.md`
- Test: grep checks against `AGENTS.md` and `.oh-my-harness/tree.md`

- [ ] **Step 1: Add ROADMAP to AGENTS project routing text**

In `AGENTS.md`, add this bullet near the project documentation / routing guidance:

```markdown
- Phase 2 / Phase 3 总路线以 `docs/ROADMAP.md` 为准；`docs/TASKS.md` 只记录任务状态和候选工程任务。
```

If `AGENTS.md` has a MAP/tree section, add `ROADMAP.md` under `docs/` using the existing tree style.

- [ ] **Step 2: Refresh tree**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result: `.oh-my-harness/tree.md` is regenerated and contains `ROADMAP.md`.

- [ ] **Step 3: Check AGENTS and tree references**

Run:

```bash
grep -R "docs/ROADMAP.md" AGENTS.md
grep -R "TASKS.md.*任务状态" AGENTS.md
grep -R "ROADMAP.md" .oh-my-harness/tree.md
```

Expected result:

- The first command prints the roadmap routing rule in `AGENTS.md`.
- The second command prints the TASKS boundary sentence in `AGENTS.md`.
- The third command prints `ROADMAP.md` from `.oh-my-harness/tree.md`.

- [ ] **Step 4: Commit AGENTS and tree updates**

Run:

```bash
git add AGENTS.md .oh-my-harness/tree.md
git commit -m "docs: register roadmap in agent docs"
```

---

### Task 7: Final verification and PR preparation

**Files:**

- Create: none
- Modify: none
- Test: documentation and no-code-change checks

- [ ] **Step 1: Run full documentation checks**

Run:

```bash
grep -R "Final Product Vision" docs/ROADMAP.md
grep -R "Phase 2A: evaluator runtime closure" docs/ROADMAP.md
grep -R "D2 Decision Log scoring integration" README.md docs/ROADMAP.md docs/TASKS.md docs/PRODUCT_ONE_PAGER.md
grep -R "Phase 3 / G-track" docs/ROADMAP.md docs/PRODUCT_ONE_PAGER.md
grep -R "Real AI Agent gameplay" docs/ROADMAP.md docs/TASKS.md
grep -R "docs/ROADMAP.md" README.md docs/TASKS.md docs/PRODUCT_ONE_PAGER.md AGENTS.md
grep -R "ROADMAP.md" .oh-my-harness/tree.md
```

Expected result:

- Every command prints at least one matching line.
- D2 appears in README, ROADMAP, TASKS, and PRODUCT_ONE_PAGER.
- `docs/ROADMAP.md` appears in README, TASKS, PRODUCT_ONE_PAGER, and AGENTS.
- `ROADMAP.md` appears in `.oh-my-harness/tree.md`.

- [ ] **Step 2: Run baseline runtime tests to prove docs-only PR did not break code**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected Game Log output includes:

```text
validated game_id=g001
players=6
events=38
winner=villager
end_round=2
```

Expected Decision Log output:

```text
validated decision_log_id=d1_g001_decision_log
game_id=g001
decisions=10
source_label=[人工 gold sample]
```

Expected unittest output includes:

```text
OK
```

- [ ] **Step 3: Confirm only intended files changed**

Run:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
.oh-my-harness/tree.md
AGENTS.md
README.md
docs/PRODUCT_ONE_PAGER.md
docs/ROADMAP.md
docs/TASKS.md
```

- [ ] **Step 4: Confirm forbidden files did not change**

Run:

```bash
git diff --name-only main...HEAD -- src tests docs/EVALUATION_RUBRIC.md docs/SPIKES.md docs/gold-game docs/demo docs/prs/2026-05-30--phase2-next-step-research.md
```

Expected result: no output.

- [ ] **Step 5: Run whitespace check**

Run:

```bash
git diff --check
```

Expected result: no output.

- [ ] **Step 6: Prepare Implementation PR**

Use this PR title:

```text
docs: align project roadmap
```

Use this PR body:

```markdown
## Summary

Adds a canonical ROADMAP and aligns project entry docs so future work stays tied to the final Werewolf-agent direction instead of narrowing into local task fragments.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--roadmap-alignment-plan.md`

## Scope

- Adds `docs/ROADMAP.md`.
- Updates README.md to point to ROADMAP and current D2 priority.
- Updates docs/PRODUCT_ONE_PAGER.md to resolve Phase 2 / Phase 3 boundary conflict.
- Updates docs/TASKS.md title, roadmap note, and D2/S4/S5/G1/L1 candidate status.
- Updates AGENTS.md and .oh-my-harness/tree.md so future agents can find the roadmap.

## Boundary

- Documentation-only PR.
- No runtime code changes.
- No test code changes.
- No scoring rule changes.
- No changes to docs/EVALUATION_RUBRIC.md.
- No changes to gold-game or demo artifacts.
- Does not implement D2, S4, S5, G1, or L1.

## Validation

```bash
grep -R "Final Product Vision" docs/ROADMAP.md
grep -R "Phase 2A: evaluator runtime closure" docs/ROADMAP.md
grep -R "D2 Decision Log scoring integration" README.md docs/ROADMAP.md docs/TASKS.md docs/PRODUCT_ONE_PAGER.md
grep -R "Phase 3 / G-track" docs/ROADMAP.md docs/PRODUCT_ONE_PAGER.md
grep -R "Real AI Agent gameplay" docs/ROADMAP.md docs/TASKS.md
grep -R "docs/ROADMAP.md" README.md docs/TASKS.md docs/PRODUCT_ONE_PAGER.md AGENTS.md
grep -R "ROADMAP.md" .oh-my-harness/tree.md
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
git diff --check
```

Expected key outputs:

```text
Final Product Vision
Phase 2A: evaluator runtime closure
D2 Decision Log scoring integration
Phase 3 / G-track
ROADMAP.md
validated game_id=g001
validated decision_log_id=d1_g001_decision_log
OK
```
```

- [ ] **Step 7: Stop for review**

Do not merge automatically. Report changed files, validation outputs, and whether the Phase 2 / Phase 3 conflict is resolved in the checkpoint summary.

---

## Checkpoint summary template for this PR

Use `docs/CHECKPOINT_TEMPLATE.md` and include:

```markdown
## Checkpoint Summary

Task: Roadmap Alignment
Branch: `task/roadmap-alignment`
Bound plan: `docs/harness/plans/2026-05-30--roadmap-alignment-plan.md`

Changed files:
- `.oh-my-harness/tree.md`
- `AGENTS.md`
- `README.md`
- `docs/PRODUCT_ONE_PAGER.md`
- `docs/ROADMAP.md`
- `docs/TASKS.md`

Validation:
- `grep -R "Final Product Vision" docs/ROADMAP.md`
- `grep -R "Phase 2A: evaluator runtime closure" docs/ROADMAP.md`
- `grep -R "D2 Decision Log scoring integration" README.md docs/ROADMAP.md docs/TASKS.md docs/PRODUCT_ONE_PAGER.md`
- `grep -R "Phase 3 / G-track" docs/ROADMAP.md docs/PRODUCT_ONE_PAGER.md`
- `grep -R "Real AI Agent gameplay" docs/ROADMAP.md docs/TASKS.md`
- `grep -R "docs/ROADMAP.md" README.md docs/TASKS.md docs/PRODUCT_ONE_PAGER.md AGENTS.md`
- `grep -R "ROADMAP.md" .oh-my-harness/tree.md`
- `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
- `git diff --check`

Boundary confirmation:
- No runtime code changes.
- No test code changes.
- No scoring rule changes.
- No gold-game or demo artifact changes.
- No D2 / S4 / S5 / G1 / L1 implementation.
- Phase 2 evaluator runtime and Phase 3 real gameplay route conflict is resolved through ROADMAP.
```
