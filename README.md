# Werewolf-agent

AI 狼人杀 client-agnostic live experiment platform。项目目标是让 AI 狼人杀对局可以被实时运行、观察、配置、审计和复盘；评测、回放、报告和 Leaderboard 是建立在同一套结构化运行日志之上的后续能力。

## 项目背景

基于多 Agent 协作框架，构建能够自主完成信息不对称博弈的狼人杀 Agent Team 系统。核心在于多智能体的协作/对抗与交互机制设计：每个 Agent 根据其扮演角色（狼人、预言家、女巫等）拥有独立的目标、策略与行动空间，在严格信息隔离的约束下进行推理、发言与决策。系统需搭建完整的对局引擎，驱动回合流转与胜负裁决，并输出结构化日志以实现全程可观测。加分项为前端观战 UI，支持纯 AI 对战或人机混战，直观呈现多 Agent 的实时博弈过程。

### 进阶方向

本项目从方向 **② 评测+复盘** 出发，当前路线已升级为 **client-agnostic live AI Werewolf experiment platform**：先建立可审计、可回放、可实时观察的对局运行基础，再在其上发展多维评测、复盘归因和多模型 Leaderboard。

| 方向 | 描述 |
|------|------|
| ① 通用 Agent | 探索"读懂自己→修改自己→运行自己"的自演化系统，从「通用 Agent」演化为「狼人杀多角色 Agent」 |
| ② 评测+复盘 | 构建多维可量化评测体系 + 复盘归因 + Leaderboard（本项目的评测基础） |
| ③ 自进化 Agent | 实现"对局→分析→优化→再对局"自进化循环，使各角色 Agent 在多局迭代中持续提升胜率 |

## Phase 1 目标

构建结构化 Game Log + 确定性评测 + 规则归因 + Leaderboard UI demo。

基于一局已有 6 人狼人杀对局的结构化日志，验证"可量化、可复现、可排序"的评测体系是否成立。

## 当前状态

**Phase 1 deterministic MVP、Phase 2 evaluator runtime、G1a-G1g provider-backed audit/replay foundation 已完成。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer、E3 rule attribution engine、E4 runtime demo HTML exporter、D1 Decision Log runtime input、D2 Decision Log deterministic scoring integration、S4 Consensus Log runtime input、S5 saved semantic-label research harness and scoring integration、G1a scripted deterministic fresh-log runner、G1b deterministic game engine + mock agent contract、G1c wolf consensus + failure recovery、G1d fake-provider contract、G1e DeepSeek provider smoke、G1f DeepSeek consensus smoke、G1g provider replay HTML。

G1a-G1g 的当前价值是 audit foundation、replay foundation、log bundle / provider trace / failure audit foundation。G1g 的 HTML replay/report 只是 offline audit artifact，用于审查和复盘 provider-backed 游戏包；它不是 primary UX，也不代表 live observer、prompt editor、Qt/Web client、人机 UI、multi-provider arena 或 real multi-game Leaderboard 已完成。

G-track 后续路线已在 `docs/ROADMAP.md` 固化：G1h 重新定义为 Live Runtime Event Spine，目标是把真实/假 provider 单局运行升级为可订阅、可回放、可审计的 runtime event stream。Qt/QML 是推荐的后续 rich client 方向，但必须通过 client-agnostic protocol 消费 Python runtime/server 输出，不直接绑定 Python 内部对象。

Phase 1 不代表真实 AI Agent 对局、真实 Decision Log / Consensus Log 采集、真实多模型 Leaderboard 或真实 `decision_quality_score` 可用。

## 文档索引

| 文档 | 作用 |
|------|------|
| [ROADMAP](docs/ROADMAP.md) | 总路线：Phase 2 / Phase 3 边界、G1h / G2 / G3 / G4 live platform route、当前优先级 |
| [PRODUCT_ONE_PAGER](docs/PRODUCT_ONE_PAGER.md) | 产品定义：用户、输入、输出、核心价值、Phase 1 做什么不做什么 |
| [ADR 0001](docs/adr/0001-client-agnostic-live-observer-protocol.md) | 架构决策：先 event protocol / runtime spine，再 observer server，再 Qt/Web client |
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
