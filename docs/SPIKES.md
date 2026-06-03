# SPIKES — Werewolf-agent

> **Archived.** All 7 Phase 1 spikes completed (S0-S6). Current new spikes are not tracked here. This document is retained as a historical record of Phase 1 uncertainty validation.

不确定性验证清单。每个 spike 必须在 engineering task 之前完成并通过验收。

---

## Spike 0：名局筛选 + 资料完整性 + 版权风险

**输入：** 搜索公开可用的 6 人狼人杀对局资料（视频平台、文字战报、论坛），或直接准备编写虚拟对局的事件摘要。Phase 1 固定角色配置：2 狼人 + 1 预言家 + 1 女巫 + 2 平民。不包含猎人。

**输出：**
- 1-2 个候选对局的完整事件摘要。
- 资料完整性评估表（哪些事件确认、哪些合理推断、哪些缺失）。
- 版权风险评估（来源、使用范围、是否需要授权）。

**通过标准：**
- 事件链连续无断裂（每夜行动、每天发言关键点、投票、死亡、身份揭示均可追溯）。
- 版权风险可接受（只引用公开可查的游戏事实，不复制原视频/音频/台词）或确认使用人工构造对局。

**失败决策：**
- 名局版权不清晰或资料不完整 → 使用手工编写的虚拟对局（逻辑自洽、事件链完整）。这是 owner 确认的优先路径，不违反 Gold Demo 原则——关键是对局逻辑完整，不是"真实"。
- 资料完整性不足 → 标记哪些事件是推断，Phase 1 演示中只使用确认事件。

**不代表什么：**
- 不代表名局选择会限制后续 Agent 行为多样性。
- 不代表 Phase 2 只能复现这一局。
- 不代表虚拟对局比真实对局差——对于评测系统校准，逻辑完整即可。

---

## Spike 1：Game Log schema 验证

**输入：** Spike 0 产出的事件摘要 + `@docs/EVALUATION_RUBRIC.md` 中定义的 Game Log schema。角色配置固定为：2 狼人 + 1 预言家 + 1 女巫 + 2 平民。

**输出：**
- 用候选对局数据填一份完整 Game Log JSON。
- schema 缺失字段清单（如有）。
- 修正后的 schema 建议（如有）。

**通过标准：**
- Game Log 能无歧义地描述该局所有关键事件。
- 每条事件的 `type`、`visibility`、`actor`、`target` 均可确定。
- 事件序列能覆盖完整游戏流程（role_assignment → 每轮 night/day → game_over）。

**失败决策：**
- schema 缺字段 → 补字段，重填。
- 某些事件无法用现有 type 表达 → 调整事件类型枚举。
- 对局本身事件链不完整 → 回溯 Spike 0，补充或换对局。

**不代表什么：**
- 不代表 schema 已覆盖所有狼人杀变体（只覆盖 6 人标准局）。
- 不代表 Phase 2 AI Agent 产生的 Game Log 不需要调整。

---

## Spike 2：确定性评分器验证

**输入：** Spike 1 产出的完整 Game Log + `@docs/EVALUATION_RUBRIC.md` 中定义的评分规则。

**输出：**
- 每角色每轮的 `outcome_score` 和 `rule_integrity_score`。
- 过程指标（vote_accuracy、survival_rounds、技能使用统计等）。
- 结果指标（winner、game_length、survival_rate、margin）。

**通过标准：**
- 所有评分可追溯到具体规则和 event_id。
- 两次运行同一 Game Log，所有指标完全一致。
- 人工审查 3 个评分案例，确认评分逻辑符合 Rubric 的意图。

**失败决策：**
- 规则有歧义 → 修 `EVALUATION_RUBRIC.md`，明确边界条件。
- 规则无法计算（依赖缺失字段）→ 回溯 Spike 1 补字段。
- 评分结果与人工直觉严重冲突 → 审查规则合理性，修正 rubric。

**不代表什么：**
- 不代表规则已覆盖所有边缘情况（只覆盖 6 人标准局的主要分支）。
- 不代表 `decision_quality_score` 已验证（Phase 2 才启用）。

---

## Spike 3：规则归因验证

**输入：** Spike 2 产出的评分结果 + Game Log + `@docs/EVALUATION_RUBRIC.md` 中定义的归因规则。

**输出：**
- turn_points 列表（每项含 rule_id、round、actor、description_template、impact_score、evidence event_ids）。
- top_attribution（模板化结论）。

**通过标准：**
- 每个 turn_point 有明确的 rule_id 和 evidence。
- 人工判断标记的"关键转折点"中至少有 2/3 是合理的。
- 两次运行同一 Game Log，归因结果完全一致。

**失败决策：**
- 归因太多（标记了 >5 个"关键"转折点）→ 收紧触发条件。
- 归因太少（<1 个）→ 放宽触发条件或检查 Game Log 是否过于简单。
- 归因不合理 → 修正归因规则定义。

**不代表什么：**
- 不代表归因是正确的"为什么输/赢"的唯一解释。
- 不代表归因能覆盖策略层面的微妙博弈（只覆盖结构化的可计算事实）。

---

## Spike 4：狼人 Consensus Log schema 验证

**输入：** Spike 1 的 Game Log 中狼人夜间行动 + `@docs/EVALUATION_RUBRIC.md` 中定义的 Consensus Log schema。

**输出：**
- 用候选对局的狼人夜间行动填写人工 gold consensus sample（每夜一份）。
- schema 可用性评估：proposal/response 结构是否覆盖协商场景。

**通过标准：**
- Consensus Log schema 能完整描述该局的狼人协商过程（提案、回应、说服、最终决策）。
- 3 轮上限对 6 人局足够（人工模拟最坏情况验证）。
- decision_type 枚举（consensus / accepted_consensus / coordinator_tie_break / forced_random）能找到对应的实际场景。

**失败决策：**
- schema 无法充分描述协商 → 调整字段结构。
- 3 轮不够 → 调整为 4 轮或增加每轮消息长度限制。
- 某些决策类型在 6 人局中无对应场景 → 保留定义但标注 Phase 2 再验证。

**不代表什么：**
- 不代表 2 狼人之外（如 3 狼人局）的协商模式已覆盖。
- 不代表 AI Agent 在实际协商中的行为方式已验证。
- Consensus Log schema 在 Phase 1 仅用于人工 gold sample 验证，非实现能力。真实 Consensus Log 为 Phase 2 启用，schema 可能根据真实 AI 交互调整。

---

## Spike 5：AI 语义标注可行性验证

**输入：** 5-10 条人工编写的发言/决策样例（含正例和反例：正常发言、信息泄漏、逻辑矛盾、逻辑自洽）。

**输出：**
- AI 对每条样例的标注结果（结构化 JSON）。
- 一致性报告：同一输入跑 3 次，判断结果是否一致。
- token 消耗统计。

**通过标准：**
- 信息泄漏检测准确率 ≥ 80%（与人工标注对比）。
- 矛盾检测准确率 ≥ 80%。
- 逻辑支撑判断与人工判断一致率 ≥ 70%。
- 同一输入跑 3 次，结果一致率 ≥ 90%（temperature=0 条件下）。
- 单条标注 token 消耗 ≤ 500。

**失败决策：**
- 准确率不够 → 调整 prompt、简化检测维度、或降级为关键词+模式匹配。
- token 消耗过高 → 换轻量模型（如 haiku）。
- 一致性不够 → 标记为不稳定能力，Phase 2 再做，Phase 1 demo 中不依赖 AI 标注。
- 完全不通过 → Phase 1 demo 全部使用 deterministic 规则，AI 标注全部延后到 Phase 2。

**不代表什么：**
- 不代表 AI 标注可以替代确定性规则。
- 不代表 AI 标注在真实 Agent 对局中表现相同（真实 Agent 的输出可能有更多模式外行为）。
- AI 标注只辅助，不给分——分数永远是确定性规则计算的。

---

## Spike 6：Leaderboard UI demo 验证

**输入：** Spike 2 的名局评分结果 + mock 数据（5-10 行不同 agent 的评分）。

**输出：**
- 一个可双击打开的单文件静态 HTML 页面（建议路径：`docs/demo/phase1-gold-demo.html`），包含：时间线、状态表、投票表、指标表、单局评分卡、Leaderboard 表格。
- 不依赖后端、不依赖构建工具、不引入 React/Vite。
- 排序切换功能（按不同维度排序）。
- 样本量不足警告（games_played < 5 标灰，< 10 显示低置信度）。

**通过标准：**
- 非技术用户能在 3 分钟内找到关键信息（谁赢了、最高分角色、最低分角色）。
- 排序切换正常工作。
- 所有 mock / gold / deterministic 数据有视觉区分。
- 样本量不足的行有警告标识。

**失败决策：**
- 页面信息过载 → 减少同时展示的信息量，优先时间线 + Leaderboard。
- 用户找不到关键信息 → 增加引导标注、调整信息架构。
- 页面实现复杂度超预期 → 降级为纯 HTML 无交互，但必须包含所有信息。

**不代表什么：**
- 不代表最终前端技术选型。Phase 1 使用可双击打开的单文件静态 HTML（owner 决策，建议路径：`docs/demo/phase1-gold-demo.html`），Phase 2+ 根据需要再评估技术栈。
- 不代表 Leaderboard 已就绪（真实排名需要 Phase 3 的足够样本）。
