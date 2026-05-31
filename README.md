# Werewolf-agent

AI 狼人杀多智能体协作与博弈评测系统。

## 项目背景

基于多 Agent 协作框架，构建能够自主完成信息不对称博弈的狼人杀 Agent Team 系统。核心在于多智能体的协作/对抗与交互机制设计：每个 Agent 根据其扮演角色（狼人、预言家、女巫等）拥有独立的目标、策略与行动空间，在严格信息隔离的约束下进行推理、发言与决策。系统需搭建完整的对局引擎，驱动回合流转与胜负裁决，并输出结构化日志以实现全程可观测。加分项为前端观战 UI，支持纯 AI 对战或人机混战，直观呈现多 Agent 的实时博弈过程。

### 进阶方向

本项目选择方向 **② 评测+复盘**：构建结果评测、过程评测等多维可量化评测体系，基于此完成任意游戏的复盘归因，并产出不同版本、不同模型 Agent 同台竞技的 Leaderboard。

| 方向 | 描述 |
|------|------|
| ① 通用 Agent | 探索"读懂自己→修改自己→运行自己"的自演化系统，从「通用 Agent」演化为「狼人杀多角色 Agent」 |
| ② 评测+复盘 | 构建多维可量化评测体系 + 复盘归因 + Leaderboard（**本项目方向**） |
| ③ 自进化 Agent | 实现"对局→分析→优化→再对局"自进化循环，使各角色 Agent 在多局迭代中持续提升胜率 |

## Phase 1 目标

构建结构化 Game Log + 确定性评测 + 规则归因 + Leaderboard UI demo。

基于一局已有 6 人狼人杀对局的结构化日志，验证"可量化、可复现、可排序"的评测体系是否成立。

## 当前状态

**Phase 1 deterministic MVP 已完成，Phase 2 evaluator runtime 已接入 saved S5 semantic labels。G1a scripted deterministic fresh-log runner 已完成。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer、E3 rule attribution engine、E4 runtime demo HTML exporter、D1 Decision Log runtime input、D2 Decision Log deterministic scoring integration、S4 Consensus Log runtime input、S5 saved semantic-label research harness and scoring integration、G1a scripted deterministic fresh-log runner（`docs/game-scripts/g1-scripted-game.json` → `src/werewolf_eval/scripted_game.py` + `src/werewolf_eval/run_scripted_game.py` → `docs/generated-games/g1-scripted-*.json` → evaluator pipeline → `docs/demo/phase3-g1-scripted-runtime-demo.html`）。

G1a 已提供 scripted deterministic fresh-log runner，可从 `docs/game-scripts/g1-scripted-game.json` 生成新的 scripted deterministic Game Log / Decision Log / Consensus Log，并通过现有 evaluator pipeline 生成 `docs/demo/phase3-g1-scripted-runtime-demo.html`。这不是 Agent runtime output，不代表 real AI Agent gameplay、provider integration、Web live observer、human-vs-AI UI 或 multi-game Leaderboard 已完成。

G-track 后续路线已在 `docs/ROADMAP.md` 固化：G1b 是 deterministic game engine + mock agent contract；G1c 才处理 wolf consensus + failure recovery；G1d 先做 provider adapter research / fake-provider contract；G1e 才允许本地预算受控的 provider-backed single-game smoke。完整 G1 real AI Agent gameplay 仍未完成。

Phase 1 不代表真实 AI Agent 对局、真实 Decision Log / Consensus Log 采集、真实多模型 Leaderboard 或真实 `decision_quality_score` 可用。

## 文档索引

| 文档 | 作用 |
|------|------|
| [ROADMAP](docs/ROADMAP.md) | 总路线：Phase 2 / Phase 3 边界、G1a-G1e / L1 依赖关系、当前优先级 |
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
