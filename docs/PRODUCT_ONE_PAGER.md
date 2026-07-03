# PRODUCT_ONE_PAGER — Werewolf-agent

> 产品阶段与模块状态以 `docs/PROJECT_MAP.md` 为准;本文回答"这是什么产品、给谁用、输入输出是什么"。

## 产品定义

Werewolf-agent 是一个 **mobile-first, client-agnostic live Werewolf Agent Theater**。平台目标是让狼人杀 Agent 对局可以被**实时运行、参与、观察、配置、审计和复盘**。AI-vs-AI 是默认实验形态;真人作为角色加入实时局是 P3 一等能力。

平台核心是一个 Python runtime game engine + agent/provider loop。每次对局产出结构化运行日志（Game Log / Decision Log / Consensus Log / Score Log）、`events.jsonl` 事件流、runtime snapshots、prompt manifest 和 provider lifecycle 记录。这些运行产物通过 client-agnostic observer protocol 对外暴露:当前由 Qt observer client 消费;P3-E 后续由 Flutter-first 跨平台客户端消费,Qt 保留为 legacy 直到 parity。Web client 不是当前路线目标。

Agent 角色体验、单局记忆、桌面发言、真人参与和跨平台玩家端是当前 **P3 direction**。评测评分、复盘归因、Leaderboard 和跨模型对比是建立在同一套结构化运行日志之上的 **P4 downstream capabilities**，结算画面既是趣味性复盘入口,也是后续评测/复盘入口。

## 用户是谁

**主要用户：** AI Agent 开发者、模型评测者、狼人杀 AI 研究者。他们需要通过配置 agent profile、Agent Card、RolePolicy、provider/model/temperature 来运行可控实验，实时观察 AI 对局行为，审计运行日志，并对比不同配置下的 Agent 表现。

**直接玩家/观众：** 非技术用户当前可以通过 Qt observer client 观看对局过程;P3-E 目标是提供移动优先的 Flutter 跨平台客户端,让真人以受限角色座位参战。P4 阶段再通过 Leaderboard 和评分面板理解 Agent 能力差异。

## 输入是什么

通过 YAML profile 配置的 AI Werewolf 运行参数：

- 角色分配、对局配置（几狼几神几民）、可选角色洗牌（role_shuffle）
- 每个座位绑定的 provider / model / prompt / persona / temperature（BYO-key：用户自带 API key，仅存本地，provider 调用只由本地 Python server 执行）
- Prompt manifest 与 prompt 版本（字节锁定 + 修订台账）
- Runtime snapshot 间隔、event stream 开关、live / fake 执行模式

## 输出是什么

**运行平台层（P1 + P2，已交付）：**

1. Runtime event spine：`events.jsonl` 事件流 + runtime snapshots + prompt manifest + provider lifecycle events
2. 标准结构化日志包：Game Log / Decision Log / Consensus Log / Score Log
3. Provider trace + failure audit（可审计的 provider 调用链和故障记录）
4. Client-agnostic observer protocol（REST/SSE）
5. Qt/QML 剧场客户端：实时上帝视角观战（座位环、发言剧场、证据控制台）+ God/Public/Role 视角投影
6. 对局配置面：每座位 provider/model/prompt 选择、live/fake 双模、多供应商预设（DeepSeek / OpenAI / Anthropic / 9 家 OpenAI 兼容 / 自定义端点）
7. 结算战报（settlement bundle + 剧场内战报覆盖层）与历史对局回看/管理

**Agent 角色体验层（P3，当前方向）：**

- Agent asset ownership：SeatCharacterCard / RolePolicy / RuntimeAgentState / ProviderProfile 分层
- 单局 scoped memory：Fact / Claim / Belief / Commitment / TeamPlan 等有真相层级的记录
- AgentContextPacket：带 provenance、visibility guard、prompt block hash、预算裁剪的上下文编译
- Structured SpeechAct / table-talk：最小回应、质询、对跳、转票接口
- Human participant seat：先从本地单真人村民开始,复用 observer protocol 与 action contract
- Flutter-first cross-platform client：移动端优先的真人参与与观战客户端;桌面端是同一产品表面的响应式扩展

**评测层（P4，下游能力）：**

- 结果评测指标 + 过程评测指标（确定性评分已在 P1 落地，作为 P4 的原语）
- 确定性规则归因（turn_points + top_attribution）
- 单局评分卡 + 跨局聚合 + 消融实验台（prompt/脚手架对比）
- 多模型、多版本、按角色、Agent Card、记忆策略区分的真实 Leaderboard
- 评分规则定义见 `docs/EVALUATION_RUBRIC.md`（P4 reference）

## 核心价值

**可审计、可实时观察、可配置复现的 AI 狼人杀实验平台,也是可参与的社交推理剧场。**

- 不看谁"说得好"，只看运行时实际产出的结构化事件和日志。
- 对局过程不是黑盒——`events.jsonl`、prompt manifest、provider trace 提供完整审计链；HUD 始终显示执行真相（LIVE_API vs SIMULATION）。
- 严格信息隔离可被机检：每个座位的 prompt 只能由其可见事件渲染，运行时不变量在泄漏时立刻报错。
- 同一 profile 可复现运行，不同配置可对比实验；prompt 字节锁保证 baseline 不被静默漂移。
- 角色体验优先于排行榜:只有对局本身有记忆、有拉扯、有戏剧节点,评测和 Leaderboard 才有产品价值。
- 真人参与优先于纯观战:移动端玩家需要能入座、发言、投票、承担隐藏信息压力,而不是只看日志或上帝视角。
- 评测和 Leaderboard 建立在真实运行数据之上，不是人工 gold sample。
- Client-agnostic protocol 确保 Qt legacy client 与 Flutter-first 客户端都不与 Python runtime 内部实现绑定。

## 阶段演进

| 阶段 | 内容 | 状态 |
|------|------|------|
| P1 数据与事件地基 | 日志 schema/校验/评分/归因、引擎与 provider 契约、实时事件骨架、observer 协议 + server | ✅ 完成 |
| P2 观战式 AI-vs-AI 对局客户端 | 涌现式引擎、BYO-key 配置、剧场观战、结算战报 | ✅ 完成 |
| P3 Agent 角色体验 · 真人参与 · 跨平台客户端 | 角色卡、单局记忆、roleplay harness、桌面发言、真人座位、Flutter-first 移动/桌面客户端 | 🚧 当前方向 |
| P4 评测 · 复盘 · 排行榜 | 结算深化为复盘/归因、历史聚合、按模型/角色/Agent Card/记忆策略排行 | ⏳ 后移 |

项目从 Phase 1 deterministic MVP（单局人工 gold sample → 确定性评分 → 规则归因 → UI demo）出发，经由 provider-backed gameplay foundation（旧 G-track），pivot 到 client-agnostic live experiment platform。旧 G/E/S 编号到 P 阶段的映射见 `docs/PROJECT_MAP.md` 的「Reconcile」表。

## 数据标注规范

所有输出必须标注数据来源层级：

| 标注 | 含义 |
|------|------|
| `[原始资料]` | 来自原始记录 |
| `[结构化事件]` | 人工从原始资料整理的事件 |
| `[deterministic]` | 确定性规则计算产出 |
| `[AI 生成]` | 真实 AI 产出（live 路径标注真实 provider，如 `[DeepSeek API output]`） |
| `[人工 gold sample]` | 人工编写的理想输出样例 |
| `[mock]` | 占位假数据，仅用于 UI demo |
