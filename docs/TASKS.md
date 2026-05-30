# TASKS — Werewolf-agent Task Status

> **Progress note:** 本文件描述 Phase 1 任务依赖关系和计划状态，但任务完成状态可能滞后于实际进度。判断当前进度时，必须以已合入 PR 和 main 上实际存在的产物文件为准。如果本文件状态与 PR / main 文件冲突，以 PR / main 文件为准。

> **Roadmap note:** Phase 2 / Phase 3 route boundaries are defined in `docs/ROADMAP.md`. This file tracks task status and candidate engineering work; it does not replace the roadmap.

任务按类型组织。每个 spike 通过前不展开对应的 engineering task。

---

## Product Milestone

**M1：评测系统概念验证完成**

- 输入：一局 6 人狼人杀结构化 Game Log（Spike 0 产出。优先路径：人工编写虚拟对局）。
- 输出：确定性的 outcome_score + rule_integrity_score + 过程指标 + 规则归因 + 单局评分卡 + Leaderboard UI demo（静态 HTML）。
- 验收：两次运行同一 Game Log 所有指标一致；非技术用户 3 分钟能理解评测系统工作方式。
- 状态：`completed`（deterministic MVP closure：S0/S1/S2/S3/S6 已完成；S4/S5 延后到 Phase 2）
- 完成产物：
  - `docs/gold-game/g001-game-log.json`
  - `docs/gold-game/s2-score-log.json`
  - `docs/gold-game/s2-metrics-summary.json`
  - `docs/gold-game/s3-rule-attribution.json`
  - `docs/demo/phase1-gold-demo.html`
- 注意：Phase 1 的 decision_quality_score 恒为 0（无真实 Decision Log），不宣称已真实可用。Consensus Log 和 Decision Log 的真实数据采集转入 Phase 2。

---

## Spike Tasks

### S0：名局筛选 + 资料完整性 + 版权风险

- 状态：`completed`（人工构造虚拟对局，PR #2）
- 产出：`docs/gold-game/s0-gold-game-seed.md`。
- 依赖：无。
- 通过标准：见 `@docs/SPIKES.md` Spike 0。

### S1：Game Log schema 验证

- 状态：`completed`（PR #3 plan, PR #4 impl）
- 产出：`docs/gold-game/g001-game-log.json` + `docs/gold-game/s1-schema-validation.md`。
- 依赖：S0。
- 通过标准：见 `@docs/SPIKES.md` Spike 1。

### S2：确定性评分器验证

- 状态：`completed`（PR #5 plan, PR #6 impl）
- 产出：`docs/gold-game/s2-score-log.json` + `docs/gold-game/s2-metrics-summary.json` + `docs/gold-game/s2-scoring-validation.md`。
- 依赖：S1。
- 通过标准：见 `@docs/SPIKES.md` Spike 2。

### S3：规则归因验证

- 状态：`completed`（PR #7 impl）
- 产出：`docs/gold-game/s3-rule-attribution.json` + `docs/gold-game/s3-attribution-validation.md`。
- 依赖：S2。
- 通过标准：见 `@docs/SPIKES.md` Spike 3。

### S4：狼人 Consensus Log schema 验证

- 状态：`deferred_to_phase_2`（真实 Consensus Log 为 Phase 2 启用；Phase 1 deterministic MVP 不再阻塞于人工 consensus sample）
- 产出：人工 gold consensus sample + schema 可用性评估。
- 依赖：S1（可与 S2、S3 并行）。
- 通过标准：见 `@docs/SPIKES.md` Spike 4。

### S5：AI 语义标注可行性验证

- 状态：`deferred_to_phase_2`（AI 标注与真实 Agent 输出、Decision Log 启用一起验证；Phase 1 demo 不依赖 AI 标注）
- 产出：标注准确率报告 + 一致性报告 + token 统计。
- 依赖：无（使用独立构造的样例，不依赖前面 spike）。
- 通过标准：见 `@docs/SPIKES.md` Spike 5。

### S6：Leaderboard UI demo 验证

- 状态：`completed`（PR #8 plan, PR #9 impl）
- 产出：`docs/demo/phase1-gold-demo.html`。
- 依赖：S2（可使用真实评分 + mock 数据，不需要 S3 归因先完成）。
- 通过标准：见 `@docs/SPIKES.md` Spike 6。

---

## Phase 2 Candidate Engineering Tasks

**E1-E4 与 D1 已作为 Phase 2 runtime entries 完成。** 当前 Phase 2A 优先级是 D2 Decision Log scoring integration。S4/S5 在 D2 后推进；G1/L1 属于 Phase 3 / Phase 3+ 路线。以下记录各工程任务的完成状态与产物路径，阶段边界以 `docs/ROADMAP.md` 为准。

### E1：Game Log 解析器

- 状态：`completed`（Phase 2 E1 runtime entry；Game Log parser / validator 已实现）
- 产出：`src/werewolf_eval/game_log.py` + `src/werewolf_eval/validate_game_log.py` + `tests/test_game_log.py`。
- 说明：读取结构化 Game Log JSON，验证 schema，转换为内部数据结构。

### E2：确定性评分器

- 状态：`completed`（Phase 2 E2 deterministic scorer；Score Log / Metrics Summary runtime 已实现）
- 产出：`src/werewolf_eval/scoring.py` + `src/werewolf_eval/score_game.py` + `tests/test_scoring.py`。
- 说明：实现 EVALUATION_RUBRIC.md 中所有确定性评分规则。输出 Score Log。

### E3：规则归因引擎

- 状态：`completed`（Phase 2 E3 rule attribution engine；turn_points / top_attribution runtime 已实现）
- 产出：`src/werewolf_eval/attribution.py` + `src/werewolf_eval/attribute_game.py` + `tests/test_attribution.py`。
- 说明：实现归因规则匹配引擎。输出 turn_points + top_attribution。

### E4：可视化页面

- 状态：`completed`（Phase 2 runtime demo HTML exporter）
- 产出：`src/werewolf_eval/render_demo.py` + `tests/test_render_demo.py` + `docs/demo/phase2-runtime-demo.html`。
- 说明：构建可双击打开的单文件静态 HTML，不依赖后端、不依赖构建工具、不引入 React/Vite。该页面从 E1/E2/E3 runtime pipeline 生成，包含时间线、状态表、投票表、指标表、评分卡、Leaderboard，并保留 Phase 2 边界声明。

### D1：Decision Log runtime skeleton

- 状态：`completed`（Phase 2 Decision Log runtime input；Decision Log parser / validator 已实现）
- 产出：`docs/gold-game/g001-decision-log.json` + `src/werewolf_eval/decision_log.py` + `src/werewolf_eval/validate_decision_log.py` + `tests/test_decision_log.py`。
- 说明：读取人工 gold Decision Log JSON，验证其 `game_id` 与 Game Log 一致，验证 actor / target / visible_info_refs / decision_type / confidence 等字段。D1 不调用 AI，不启用 S5，不修改 scoring，`decision_quality_score` 仍未接入评分链。

### D2：Decision Log scoring integration

- 状态：`completed`（Phase 2A evaluator runtime closure；Decision Log 已接入 deterministic scoring）
- 产出：`src/werewolf_eval/scoring.py` + `src/werewolf_eval/score_game.py` + `src/werewolf_eval/render_demo.py` + `docs/gold-game/s2-score-log.json` + `docs/gold-game/s2-metrics-summary.json` + `docs/demo/phase2-runtime-demo.html`。
- 依赖：D1 + E2。
- 目标：将 Decision Log 接入 scoring，完成 deterministic visibility 检查和 decision_id 追溯。`decision_quality_score` 正向评分仍等待 S5 AI 语义判断。
- 边界：只实现 Rubric G.1 Step 1-2 deterministic visibility 检查和 decision_id 追溯；不调用 AI，不启用 S5，不做 Consensus Log，不宣称 `decision_quality_score` 完整可用（正向评分等待 S5 AI 语义判断）。
- 路线依据：`docs/prs/2026-05-30--phase2-next-step-research.md` + `docs/ROADMAP.md`。

### S4：Consensus Log runtime/input

- 状态：`completed`（Phase 2B collaboration input；Consensus Log parser / validator / fixture / CLI 已实现）
- 产出：`docs/gold-game/g001-consensus-log.json` + `src/werewolf_eval/consensus_log.py` + `src/werewolf_eval/validate_consensus_log.py` + `tests/test_consensus_log.py`。
- 依赖：E1 / S1；产品优先级上放在 D2 后。
- 目标：验证狼人夜间协商层 Consensus Log 的 parser / validator / fixture / CLI。
- 边界：不做 AI gameplay，不做 S5 语义标注，不接 scoring，不宣称 team coordination scoring 完整可用。

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

---

## UX Acceptance

每个 engineering task 完成后必须提供：

| Task | UX 验收物 | 验收口径 |
|------|----------|---------|
| E1 | 无独立 UX（被 E2 消费） | schema 验证通过 |
| E2 | Score Log 可读摘要 | 每个评分能追溯到 rule_id 和 event_id |
| E3 | 归因面板 | 每个 turn_point 可展开查看触发的规则 |
| E4 | 页面截图（`docs/demo/phase2-runtime-demo.html`） | 非技术用户 3 分钟能查看该页面，复述谁赢了、关键转折点是什么、评测系统如何打分，并能看到明确的 `[deterministic]` / `[mock]` 标签和 Phase 2 边界声明 |
| D1 | Decision Log CLI 校验摘要 | 同一 Game Log + Decision Log 能稳定输出 `decision_log_id`、`game_id`、`decisions`、`source_label`，并拒绝非法 actor / refs / decision_type |
| D2 | Decision Log scoring 摘要 + runtime demo D2 边界声明 | 传入同一 Game Log + Decision Log 后，Score Log 中部分记录带 `decision_id`，gold game 的 canonical Score Log 所有 `rule_integrity_score` 均为 0（无违规 refs）；非法 refs 扣 -3 由 synthetic unit test 覆盖；页面明确标注 D2 只含 deterministic Step 1-2，`decision_quality_score` 仍为 0（正向评分等待 S5） |
| S4 | Consensus Log CLI 校验摘要 | 同一 Game Log + Consensus Log 能稳定输出 `consensus_log_id`、`game_id`、`consensuses`、`source_label`，并拒绝非法 participant / refs / status / final target |

---

## Demo Acceptance

**Demo 1：Phase 1 deterministic Gold Demo**

- 触发条件：S0/S1/S2/S3/S6 完成后。
- 演示内容：固定 Game Log → 确定性评分摘要 → 规则归因 → 静态 Leaderboard UI demo。
- 验收：同一 Game Log 的 deterministic 指标可复现；非技术用户 3 分钟内能复述谁赢了、关键转折点是什么、评测系统如何打分。
- 状态：`completed`（`docs/demo/phase1-gold-demo.html`）

**Demo 2：Phase 2 runtime pipeline demo**

- 状态：`completed`（`docs/demo/phase2-runtime-demo.html`；仅表示 E1/E2/E3 runtime pipeline 可生成可视化 demo，不表示真实 AI Agent / Decision Log / Consensus Log 已启用）
- 触发条件：Phase 2 charter 明确允许业务代码，并完成 E1-E4 或替代实现路径。
- 演示内容：运行时读取 Game Log → 计算 Score Log → 计算 Attribution → 输出或刷新 UI。
- 验收：同一 Game Log 可重新生成 `docs/demo/phase2-runtime-demo.html`，页面展示 Score / Metrics / Attribution / Leaderboard，并保留边界声明。

**Demo 3：Phase 2 Decision Log input validation**

- 状态：`completed`（`docs/gold-game/g001-decision-log.json`；仅表示 Decision Log runtime input 可被验证，不表示 `decision_quality_score` 已接入评分链）
- 触发条件：D1 完成。
- 演示内容：运行时读取 Game Log + Decision Log → 校验结构化决策输入。
- 验收：同一输入稳定输出 `validated decision_log_id=d1_g001_decision_log`、`game_id=g001`、`decisions=10`、`source_label=[人工 gold sample]`。

**Demo 4：Phase 2 Decision Log scoring integration**

- 状态：`completed`（`docs/demo/phase2-runtime-demo.html` 使用 Decision Log 生成 D2 deterministic decision score）
- 触发条件：D2 完成。
- 演示内容：运行时读取 Game Log + Decision Log → 计算 Score Log / Metrics Summary → 输出带 D2 边界声明的 HTML demo。
- 验收：同一输入稳定输出 `decision_id` 追溯到 Score Record，synthetic unit test 覆盖非法 refs → `rule_integrity_score = -3` 惩罚路径（canonical gold game 无违规 refs，所有 `rule_integrity_score` 均为 0）；页面明确说明 Decision Log 已接入但 `decision_quality_score` 仍为 0（正向评分等待 S5）。

**Demo 5：Phase 2 Consensus Log input validation**

- 状态：`completed`（`docs/gold-game/g001-consensus-log.json`；仅表示 Consensus Log runtime input 可被验证，不表示真实 AI 狼人协商、team coordination scoring 或 Consensus Log scoring 已启用）
- 触发条件：S4 完成。
- 演示内容：运行时读取 Game Log + Consensus Log → 校验狼人夜间协商结构化输入。
- 验收：同一输入稳定输出 `validated consensus_log_id=s4_g001_consensus_log`、`game_id=g001`、`consensuses=2`、`source_label=[人工 gold sample]`；invalid participant / refs / status / final target 由 unit tests 覆盖并拒绝。

---

## Stop / Review Gate

每个 spike 完成后必须复盘，不连续推进 engineering。检查清单：

- [ ] 本轮有用户可见变化？（截图、输出、页面）
- [ ] 确定性指标可复现？
- [ ] 所有 mock / gold / deterministic / real AI 标注清晰？
- [ ] 本轮不代表什么已明确？
- [ ] 下一步最大风险已识别？
- [ ] 是否连续两个任务没有用户可见变化？（如果是 → 停止，做 UX demo 或重排任务）
- [ ] 是否需要修改 EVALUATION_RUBRIC.md 的 stable 规则？
- [ ] 是否应该砍范围？（已发现某方向不可行 → 执行失败决策，不扩文档）

---

## 明确不做（持续更新）

| 条目 | 类型 | 状态 |
|------|------|------|
| 对局引擎 | 真正不做（Phase 2） | active |
| AI Agent 自主对局 | 真正不做（Phase 2） | active |
| AI 角色推理/心理分析 | 真正不做（Phase 2+） | active |
| 多模型适配 | 真正不做（Phase 3） | active |
| 人机混战 UI | 真正不做（Phase 2+） | active |
| 多局对比 / 真实 Leaderboard | 真正不做（Phase 3） | active |
| 完整前端观战 UI | 真正不做（Phase 2+） | active |
| 前端技术栈预选（React/Vite 等） | 真正不做（owner 决策：Phase 1 静态 HTML） | active |
| Consensus Log 真实数据 | 暂不工程化，Phase 1 仅人工 gold sample 演示 | active |
| Decision Log 真实数据 | 暂不工程化，Phase 1 仅人工 gold sample 演示 | active |
| decision_quality_score 真实可用 | 暂不工程化，Phase 1 恒为 0 | active |
| team_coordination_score 权重公式 | 暂不工程化，Phase 1 仅展示子指标，权重为 Phase 2 draft | active |
| 狼队协作综合权重 | 暂不确认（owner 决策：先展示子指标） | active |
