# Werewolf-agent

AI 狼人杀多智能体协作与博弈评测系统。

## Phase 1 目标

构建结构化 Game Log + 确定性评测 + 规则归因 + Leaderboard UI demo。

基于一局已有 6 人狼人杀对局的结构化日志，验证"可量化、可复现、可排序"的评测体系是否成立。

## 当前状态

**Phase 1 文档启动阶段。** 评测体系设计已完成审查（2026-05），正在建立产品文档和 spike 计划。暂无业务代码。

## 文档索引

| 文档 | 作用 |
|------|------|
| [PRODUCT_ONE_PAGER](docs/PRODUCT_ONE_PAGER.md) | 产品定义：用户、输入、输出、核心价值、Phase 1 做什么不做什么 |
| [GOLD_DEMO](docs/GOLD_DEMO.md) | 黄金演示路径：固定输入输出、3 分钟演示脚本、验收要求 |
| [SPIKES](docs/SPIKES.md) | 不确定性验证清单：7 个 spike 的输入/输出/通过标准/失败决策 |
| [TASKS](docs/TASKS.md) | 工程执行清单：承接已验证工作，不替代产品探索 |
| [EVALUATION_RUBRIC](docs/EVALUATION_RUBRIC.md) | 评分体系唯一事实来源：三分结构、角色 rubric、AI 裁判边界 |
| [CHECKPOINT_TEMPLATE](docs/CHECKPOINT_TEMPLATE.md) | 每轮 checkpoint 必须填写的验收报告模板 |

## Phase 1 不是

- 真实 AI Agent 对局（无 Decision Log / Consensus Log 真实数据）
- 叙事型观战系统
- AI 心理分析系统
- 完整对局引擎
- 真实多模型 Leaderboard（只做 UI demo）
- AI 自进化系统
- 人机混战系统
- decision_quality_score 真实可用（Phase 1 无真实 Decision Log，该维度恒为 0）
