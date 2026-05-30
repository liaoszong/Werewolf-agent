# PRODUCT_ONE_PAGER — Werewolf-agent

## 用户是谁

Agent 开发者、模型评测者、狼人杀 AI 研究者。他们需要回答："哪个 Agent 更擅长狼人杀？为什么？"

非技术用户是间接用户——他们通过 Leaderboard 和评分面板理解 Agent 能力差异，不需要阅读代码。

## 输入是什么

一局狼人杀的结构化 Game Log（JSON）。包含每夜行动、每天发言摘要、投票、死亡顺序、身份揭示、胜负结果。每条事件标注 `visibility`（对谁可见）。

Phase 1 使用一局 6 人狼人杀对局的 Game Log。优先使用人工编写的虚拟但逻辑自洽的 6 人对局；如能找到版权合适的公开名局，可使用名局。Phase 2A 先完成 evaluator runtime 闭环，仍可使用人工 gold sample / replay log；真实 AI Agent 对局进入 Phase 3 / G-track。

## 输出是什么

1. **结果评测指标**：胜负方、回合数、存活率、分差。
2. **过程评测指标**：每个角色每轮的 outcome_score 和 rule_integrity_score（Phase 1 无真实 Decision Log，decision_quality_score 恒为 0 不宣称可用），投票准确率，信息传递率，技能使用率。
3. **规则归因**：基于确定性规则的关键转折点识别和因果归因（非自然语言分析）。
4. **单局评分卡**：6 个角色的评分汇总。
5. **Leaderboard UI demo**：一行真实数据 + 多行 mock 数据，展示排序和筛选能力。

## 核心价值

**可量化、角色分离、区分运气与实力的多 Agent 评测排行榜。**

- 不看谁"说得好"，只看数据说了什么。
- 不按单一胜率排序，按多维评分排序（默认按 avg_decision_quality_score）。
- 区分"结果贡献"和"决策质量"——狼人随机刀中预言家拿 outcome 分但不拿 decision_quality 分。
- 信息泄漏、规则违规、前后矛盾被显式扣分。

## Phase 1 做什么

Phase 1 deterministic MVP 已完成以下闭环：

- 选定一局 6 人狼人杀人工 Gold Game → 整理结构化 Game Log。
- 产出确定性的 outcome_score + rule_integrity_score + 过程指标 + 结果指标。
- 产出确定性规则归因：turn_points + top_attribution。
- 构建最小可视化页面：时间线、状态表、投票表、指标表、单局评分卡、Leaderboard UI demo。
- 保持所有数据来源标注：`[结构化事件]`、`[deterministic]`、`[mock]`、`[人工 gold sample]`。

Phase 1 closure 使用 S0/S1/S2/S3/S6。S4 Consensus Log schema 验证和 S5 AI 语义标注可行性验证延后到 Phase 2，与真实 Agent 输出、真实 Decision Log / Consensus Log 启用一起验证。

## Phase 1 不做什么

- 不做对局引擎（无规则校验、无回合驱动）。
- 不做 AI Agent 自主对局（无 Decision Log、无 Consensus Log 真实数据）。
- 不做 AI 角色推理说明（不生成"他为什么这样说"的解释文本）。
- 不做四格视角并行分析/观战解说。
- 不做长篇自然语言复盘报告。
- 不做多模型 Provider 适配。
- 不做人机混战 UI。
- 不做多局对比 / 真实 Leaderboard。
- 不宣称 decision_quality_score 已真实可用（Phase 1 无真实 Decision Log，该维度恒为 0，仅用于评分链演示）。

## 为什么选择进阶方向 ②"评测+复盘"

① 通用 Agent 和 ③ 自进化 Agent 的共同前提是：**你能客观衡量 Agent 玩得好不好**。没有评测体系，自演化没有方向，通用 Agent 没有校准基准。

方向 ② 是最小可验证闭环：
- 输入确定（Game Log）→ 输出确定（指标 + 归因 + 榜单）。
- 每个工程产出都是用户可见的（指标面板、归因摘要、评分卡）。
- 不会出现"写了三周 schema 没有截图"的问题（ViralMorph 教训）。

## 为什么暂不做通用 Agent / 自进化 Agent

- 通用 Agent：等价于先建框架再填内容，连续多个 checkpoint 没有用户可见变化。
- 自进化 Agent：需要多局迭代才能显现效果，单局不可观测时胜率提升无法被用户感知。
- 两者都是 Phase 3+ 的事，前提是本评测系统已验证可工作。

## Leaderboard 设计原则

- 默认**不按 win_rate 排**。默认按 `avg_decision_quality_score` 降序排列。
- 多维切换：可按 win_rate、avg_outcome_score、avg_total_score、avg_rule_integrity_score、info_leak_rate 排序。
- 按角色分 tab：总览 / 狼人 / 预言家 / 女巫 / 平民。不跨角色混合排名。
- 必须展示 `games_played` 和 `role_distribution`。样本不足时显著警告。
- **Phase 1 只做 Leaderboard UI demo**（一行真实数据 + mock 数据），不宣称真实排行榜完成。

## 日志四层结构

| 层 | 内容 | Phase 1 | Phase 2 |
|----|------|---------|---------|
| Game Log | 事实事件（不可变） | 人工整理名局 | AI Agent 对局产生 |
| Consensus Log | 狼人夜间协商过程（Phase 2 启用） | 不作为 Phase 1 closure 阻塞项 | AI Agent 产生 |
| Decision Log | 行动前结构化理由（Phase 2 启用） | 不作为 Phase 1 closure 阻塞项；decision_quality_score 恒为 0 | AI Agent 产生 |
| Score Log | 评分器输出（可重算） | 确定性规则计算 | 完整三维评分 |

## Phase 2 / Phase 3 概述

详细路线以 `docs/ROADMAP.md` 为准。

- **Phase 2A**：evaluator runtime closure。目标是 `Game Log + Decision Log -> Score Log / Metrics Summary -> Rule Attribution -> Runtime HTML Demo`，优先完成 D2 Decision Log scoring integration。
- **Phase 2B**：collaboration and semantic inputs。目标是补 S4 Consensus Log runtime/input，并对 S5 AI semantic labeling 做 research / spike。
- **Phase 3 / G-track**：real AI Agent gameplay。目标是 game engine + Agent runtime + provider adapter + structured log generation。
- **Phase 3+ / L-track**：real multi-game Leaderboard。目标是多模型、多角色轮换、多局统计与样本量警告。

## 数据标注规范

所有输出必须标注数据来源层级：

| 标注 | 含义 |
|------|------|
| `[原始资料]` | 来自名局原始记录 |
| `[结构化事件]` | 人工从原始资料整理的事件 |
| `[deterministic]` | 确定性规则计算产出 |
| `[AI 生成]` | 真实 AI 产出 |
| `[人工 gold sample]` | 人工编写的理想输出样例 |
| `[mock]` | 占位假数据，仅用于 UI demo |
