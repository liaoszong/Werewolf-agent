# PRODUCT_ONE_PAGER — Werewolf-agent

## 产品定义

Werewolf-agent 是一个 **client-agnostic live AI Werewolf experiment platform**。平台目标是让 AI 狼人杀对局可以被**实时运行、观察、配置、审计和复盘**。

平台核心是一个 Python runtime game engine + agent/provider loop。每次对局产出结构化运行日志（Game Log / Decision Log / Consensus Log / Score Log）、`events.jsonl` 事件流、runtime snapshots、prompt manifest 和 provider lifecycle 记录。这些运行产物通过 client-agnostic observer protocol 对外暴露，由 Qt/Web observer client 消费。

评测评分、回放报告、Leaderboard 和跨模型对比是建立在同一套结构化运行日志之上的 **G4 downstream capabilities**，不是平台的 primary UX。

## 用户是谁

**主要用户：** AI Agent 开发者、模型评测者、狼人杀 AI 研究者。他们需要通过配置 agent profile（prompt / model / temperature / strategy）来运行可控实验，实时观察 AI 对局行为，审计运行日志，并对比不同配置下的 Agent 表现。

**间接用户：** 非技术用户通过 observer client（Qt/QML 或 Web）观看对局过程，通过 G4 阶段的 Leaderboard 和评分面板理解 Agent 能力差异。

## 输入是什么

通过 YAML profile 配置的 AI Werewolf 运行参数：
- 角色分配、对局配置（几狼几神几民）
- 每个座位绑定的 provider / model / prompt / strategy
- Prompt manifest 和 temperature / tool-use 参数
- Runtime snapshot 间隔、event stream 开关

## 输出是什么

**G1h-G3 运行平台层（分阶段能力）：**
1. Runtime event spine：`events.jsonl` 事件流 + runtime snapshots + prompt manifest + provider lifecycle events
2. 标准结构化日志包：Game Log / Decision Log / Consensus Log / Score Log
3. Provider trace + failure audit（可审计的 provider 调用链和故障记录）
4. Client-agnostic observer protocol（REST/WebSocket）
5. Qt/QML 或 Web observer client（God View + Role View）
6. Prompt configuration surface（profile 编辑）
7. Experiment profiles + replay/live dual mode + multi-provider arena（G3）

**G4 评测层（后期能力）：**
- 结果评测指标 + 过程评测指标
- 确定性规则归因（turn_points + top_attribution）
- 单局评分卡 + 跨局聚合
- 多模型、多版本、按角色区分的真实 Leaderboard
- 评分规则定义见 `docs/EVALUATION_RUBRIC.md`（G4 later-stage reference）

## 核心价值

**可审计、可实时观察、可配置复现的 AI 狼人杀实验平台。**

- 不看谁"说得好"，只看运行时实际产出的结构化事件和日志。
- 对局过程不是黑盒——`events.jsonl`、prompt manifest、provider trace 提供完整审计链。
- 同一 profile 可复现运行，不同配置可对比实验。
- 评测和 Leaderboard 建立在真实运行数据之上，不是人工 gold sample。
- Client-agnostic protocol 确保 observer client 不与 Python runtime 内部实现绑定。

## G1h：Live Runtime Event Spine（已完成基础设施）

G1h 是已完成的平台 runtime 基础设施层：
- 把 real/fake provider 单局运行升级为可订阅、可回放、可审计的 runtime event stream。
- 产出 `events.jsonl`、runtime snapshots、prompt manifest、provider lifecycle events、标准 log bundle compatibility。
- G1h 不做 Qt/QML client、Web observer、prompt editor UI、multi-provider arena、leaderboard 或 scoring formula 变更。

G1a-G1h 已完成，当前价值是 audit/replay/log bundle/provider trace/failure audit/event spine foundation。G1g 的 HTML replay/report 是 offline audit artifact，不是 primary UX。G2 Observer Route 是下一阶段，observer server、Qt/Web client、prompt/profile editor、experiment orchestration 和 leaderboard 尚未完成。

## G2：Observer Route（下一阶段）

- G2a：Local Observer Server（REST/WebSocket protocol）
- G2b：Qt Observer MVP（God View + Role View）
- G2c：Prompt Configuration MVP

G2b 的本地 Qt/QML 起点目录是 `clients/qt_observer`。当前它只是 Qt Creator 自动生成的 Qt6 Quick scaffold；observer protocol integration、match cockpit、God/Role View、run control、history/replay UI 仍未完成。

## G3：Experiment Route

- Experiment profiles + replay/live dual mode
- Multi-provider arena
- Batch run metadata 和 comparison-ready exports

## G4：Evaluation Platform（后期）

- Real multi-game Leaderboard（多模型、多版本、角色分离）
- 评分聚合与样本量警告
- 跨模型/跨版本对比
- 导出式评测报告

## 路径演进说明

项目从 Phase 1 deterministic MVP（单局人工 gold sample → 确定性评分 → 规则归因 → UI demo）出发，经由 Phase 2 evaluator runtime closure 和 G1a-G1g gameplay foundation，已 pivot 到 client-agnostic live experiment platform。

详细路线以 `docs/ROADMAP.md` 为准。Phase A 产品路线与系统架构宪章见 `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md`。Phase 1 和 Phase 2 的具体实现记录见 `docs/GOLD_DEMO.md`（Phase 1 legacy）和 `docs/TASKS.md`（任务状态）。

## 数据标注规范

所有输出必须标注数据来源层级：

| 标注 | 含义 |
|------|------|
| `[原始资料]` | 来自原始记录 |
| `[结构化事件]` | 人工从原始资料整理的事件 |
| `[deterministic]` | 确定性规则计算产出 |
| `[AI 生成]` | 真实 AI 产出 |
| `[人工 gold sample]` | 人工编写的理想输出样例 |
| `[mock]` | 占位假数据，仅用于 UI demo |
