# Phase 2 Next Step Research

> 研究性质：路线决策。不修改业务代码、测试代码、运行时代码。
> 输出：1 个研究文档。不更新 README / TASKS / PRODUCT_ONE_PAGER。

## 研究问题

E1-E4 + D1 已合入 main。当前 runtime pipeline 能从 Game Log 生成 score、attribution、HTML demo，但 `decision_quality_score` 仍然固定为 0。S4（Consensus Log）和 S5（AI 语义标注）仍为延后状态。本研究的目的是回答三个问题。

---

## 问题 1：最终 MVP 的最小闭环是什么？

**结论：Game Log + Decision Log → Score Log / Metrics Summary / Rule Attribution / Runtime HTML Demo。**

理由：

- 当前 E1→E2→E3→E4 已经实现了这个闭环的 Game Log 单腿。D1 补齐了 Decision Log 输入层。下一步只需要把 Decision Log 接入 scoring（D2），就能让 `decision_quality_score` 从固定 0 变成基于结构化输入计算。
- 真实 AI Agent 对局需要 game engine、Agent runtime、provider 适配、failure recovery——这是一条独立路线，不属于 Phase 2 的最小闭环。把它放在 Phase 3 或独立的 G（Gameplay）任务线。
- 这个闭环已经能 double-click `phase2-runtime-demo.html` 看到完整评测结果，非技术用户 3 分钟可理解。

---

## 问题 2：D2 是否是下一步？

**结论：是。D2 应优先于 S4 和 S5。**

理由：

- `decision_quality_score` 是 EVALUATION_RUBRIC 定义的三个评分维度之一，也是 Leaderboard 默认排序维度。它当前永远为 0，是项目最核心的能力缺口。
- D1 已经建立了 Decision Log runtime 输入层（parser + validator + fixture + CLI），D2 只需要做一件事：把 Decision Log 读进 scoring 链，用 `visible_info_refs` / `reason_summary` / `decision_type` 字段计算最小 deterministic `decision_quality_score`。
- D2 不需要 AI。Rubric G.1 的 Step 1-2 是纯确定性的（检查 visibility 合法性、检查 refs 是否为空 / decision_type 是否 random），D2 可以先实现这两个步骤，让有依据的决策得分、随机决策不得分。Step 3-4（AI 语义检查）留给 S5。
- 相比之下，S4（Consensus Log）只覆盖狼人夜间协商，不能直接让全角色的 `decision_quality_score` 可用。S5（AI 标注）需要 provider、prompt、token 成本、准确率验证，前置条件更多。

---

## 问题 3：S4/S5 应该在 D2 之前还是之后？

**结论：D2 之后。S4 和 S5 各自独立，可并行评估。**

S4（Consensus Log）分析：

- S4 是狼人夜间协商层，输入是 Consensus Log JSON（人工 gold sample 或 runtime 采集），结构已在 Rubric B.2 定义。
- 前置依赖：只有 E1（Game Log parser）。不需要等 D2 或 S5。
- 风险低：可以走 E1/D1 复刻模式（parser + validator + fixture + CLI）。
- 建议：D2 完成后，S4 可以独立开 Implementation Plan。

S5（AI 语义标注）分析：

- S5 需要调 AI 模型，输入是 Decision Log 的 `visible_info_refs` + `reason_summary`，输出是 `{logically_supported: bool, confidence: float}`。
- 前置依赖：D1（Decision Log schema）+ D2（scoring 接入，否则标注结果无处消费）。
- 风险中高：需要选择 provider、设计 prompt、验证准确率、评估 token 成本、处理模型不可用降级。
- 建议：D2 完成后，S5 先做 Research PR（或 spike），不要直接开 Implementation Plan。

---

## 推荐路线

```text
已完成: E1 → E2 → E3 → E4 → D1
下一步: D2（Decision Log scoring integration）
之后:   S4（Consensus Log runtime）与 S5（AI 语义标注 research）可并行
远期:   G1（Agent gameplay engine）→ L1（Real multi-game Leaderboard）
```

## 下一步 Implementation Plan 方向

**推荐：D2 Decision Log Scoring Integration。**

目标描述：

```text
将 D1 Decision Log 接入 E2 deterministic scorer，实现最小 deterministic decision_quality_score 计算。
不调用 AI，不启用 S5。只实现 Rubric G.1 的 Step 1（visibility 合法性检查）和 Step 2（refs 为空 / decision_type 为 random 时 decision_quality_score = 0）。
有依据的决策（inference_based / team_coordinated / retaliatory）获得最小基准分 +1，无依据或随机的决策保持 0。
更新 Score Log 的 decision_quality_score 字段，更新 S2 相关 golden test 期望值，更新 E4 render_demo 的边界声明。
```

边界：

- 不调用 AI。
- 不做 S5 AI 语义标注。
- 不做 Consensus Log。
- 不改 attribution / render_demo 的核心逻辑（只更新字符串常量）。
- decision_quality_score 的 AI 标注通道留给 S5。
- 不宣称 decision_quality_score 已完整可用。

---

## 不做的事

- 不修改 `docs/EVALUATION_RUBRIC.md`。
- 不修改业务代码。
- 不修改测试代码。
- 不更新 README / TASKS / PRODUCT_ONE_PAGER（状态文档更新留给后续 Implementation Plan）。
- 不写 Implementation Plan（本 Research PR 只输出结论）。
- 不做 Consensus Log / AI 标注 / Agent 对局。
