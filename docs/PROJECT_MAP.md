# PROJECT MAP — Werewolf-agent

> **本文件是项目的权威「产品全景地图」。** 它按**产品阶段**(而非工程层)组织,回答"我们最终要做成什么、现在在哪一格、下一格是什么"。
>
> - 规划深度原则:**锁上不锁下**。阶段 + 模块**全部锁定**(很少改,改动即大决策);**工作任务只细化当前模块**;子任务由实现者自动拆(superpowers / spec / writing-plans)。远期模块只画轮廓。
> - 命名:`P<阶段>-<模块>-<工作任务>`,例如 `P2-A-1`。旧 `G*` 编号的映射见文末「Reconcile」表。
> - 与其他文档的关系:`ROADMAP.md` 保留工程依赖图与历史记录;`TASKS.md` 跟踪**当前工作任务**的状态与产物;本文件是它们之上的产品框架。三者冲突时,产品阶段以本文件为准。

---

## 一句话产品愿景

一个**可观战的 AI-vs-AI 狼人杀**:开局前可配置每个角色由哪个 AI 扮演、改其 agent prompt(增加可玩性)→ 进入对局,**实时上帝视角观战**(看每个 AI 的决策、发言、投票、夜晚揭示)→ 结算画面;结算即评测/复盘,历史对战可回看,并据此形成**每角色 AI 胜率排行榜**。

---

## 阶段总览

| 阶段 | 名称 | 状态 | 一句话 |
|---|---|---|---|
| **P1** | 数据与事件地基 | ✅ 完成 | 后端原语:日志 schema/校验/评分/归因、引擎与 provider 契约、实时事件骨架、observer 协议+server。 |
| **P2** | 观战式 AI-vs-AI 对局客户端 | 🚧 **当前** | 让对局真能自演化并好看地观战:**引擎 → 配置 → 观战 UI → 结算**。 |
| **P3** | 评测 · 复盘 · 排行榜 | ⏳ 未开始(仅轮廓) | 结算画面深化为评测/复盘;历史对战回看;每角色 AI 胜率动态榜。 |

---

## P1 · 数据与事件地基 ✅(已完成,仅留映射)

> 用户视角:这是"原始的后端数据处理",不直接面向玩家。已全部落地,作为上层一切的地基保留。

| 模块 | 交付物 | 旧编号 |
|---|---|---|
| P1-A 评测原语 | Game/Decision/Consensus Log schema + validators、确定性评分、规则归因、saved 语义标注接入 | E1–E4, D1, D2, S4, S5 |
| P1-B 引擎与 provider 契约地基 | 确定性 6 人状态机、private observation、`AgentAction` 契约、mock/fake/DeepSeek provider、狼人共识 + 失败恢复、provider replay | G1a–G1g |
| P1-C 实时事件骨架 | `events.jsonl`、runtime snapshots、prompt manifest、provider 生命周期事件、log bundle 兼容 | G1h |
| P1-D observer 协议与本地 server | client-agnostic REST/SSE、run/status/artifact/snapshot/event、visibility projection | G2a |

---

## P2 · 观战式 AI-vs-AI 对局客户端 🚧(当前阶段)

> 这是当前阶段。目标:把写死的剧本换成**真正自演化的对局**,并让玩家能**配置 → 观战 → 看结算**。
> 已有的 Qt 座舱(G2b/c/d)、实时执行开关(G3-1/2/3)是本阶段已建好的**外壳/管线**,P2-B/P2-C 在其上长出真正的可玩与观感。

### 模块

| 模块 | 交付物(轮廓) | 状态 |
|---|---|---|
| **P2-A 涌现式游戏引擎** | 全角色 AI 驱动的真实对局:刀/查/救毒/发言/投票/胜负/动态回合。离线 fake 默认可测,真实 DeepSeek 走 G3 开关。 | 🚧 **当前模块** |
| P2-B 开局配置 | 每角色选哪个 AI、改 agent prompt/参数(在已有 server-side profile 之上做到真正可玩)。**架构转向(grill 2026-06-05 定):BYO-key — 用户自带 key,见下「P2-B 架构方向」。** | 轮廓 |
| P2-C 实时观战上帝视角 UI | 玩家环+真角色、阶段/回合、发言流、投票箭头、夜晚揭示;娱乐导向,而非数据仪表盘。 | 轮廓 |
| P2-D 结算画面 | 对局结束的结算视图。**注意:这就是 P3 评测/复盘的入口**,数据结构需"评测就绪"以免 P3 返工。 | 轮廓 |

### P2-A 工作任务(当前模块,细化到工作任务粒度)

| 工作任务 | 描述 | 状态 |
|---|---|---|
| **P2-A-1 完整自演化的一局** | 新建 `EmergentGameEngine`(复用 P1 全部原语,不动旧剧本模式)。全角色 AI、夜→昼→唱票→出局→胜负、动态回合;非法输出复用 `ProviderAgent` 校验 + 确定性兜底;离线 fake 默认 + 全测试(18 个)为验收门槛。 | ✅ 完成(commit f287722) |
| **P2-A-2 真实 DeepSeek 涌现对局(live 集成冒烟)** | 让 P2-A-1 引擎走真实 live 路径并跑通 1 次冒烟。**定位:集成冒烟,非内容调优**。两个前置已修:发言 prompt 路径 + 观察文本化(引擎侧 role-safe)。 | 🔬 离线实现完成(commit facaa8e,22 新测试绿);**待用户跑真实冒烟** |

> P2-A-1 收口于已批准 DoD 门槛(离线确定性整局 + 全测试绿);真实 live 因非"薄接线"而拆为 P2-A-2(owner 决定 2026-06-05)。其余 P2-A 工作任务(多轮对辩、可配板子)继续锁上不锁下。

**P2-A-2 验收口径(grill 2026-06-05 锁定):**
- **硬门槛①(visibility 不喂漏):** live prompt 只能由该 seat 的 `public_event_ids ∪ private_event_ids` 渲染(引擎侧文本化,provider 只收已过滤的 `observation_text`,绝不碰全局事件存)。机检:渲染来源 event_ids ⊆ obs 可见集;非狼视角 prompt 不含狼队私有/队友身份/他人私有结果。**喂漏=阻断性 bug。**
- **硬门槛②(真的是 live,非 fallback 糊过):** `max_requests_per_game=64`、`live_success_rate ≥ 0.80`、正常 6 人局 `live_success_actions ≥ 20`、`budget_exhausted` 一律 hard fail;兜底可救场不可过关,须按 `provider_result_kind`(live_success / invalid_then_fallback / timeout_then_fallback / error_then_fallback / budget_exhausted)统计并在 review packet 暴露。早终局致调用数低需在 packet 解释。
- **硬门槛③(诚实链,复用 G3-3):** `source_label=="[DeepSeek API output]"`、manifest 记真实 model、`token_usage>0`(fake 恒 0)。
- **软门槛(嘴漏=内容警告):** 模型幻觉自称拥有不可见系统事实 → 记 content warning,不阻断(除非破坏 action 契约/崩);狼人伪装/诈身份是正常玩法。
- **运行(spec-review 2026-06-05 supersede grill Q4):** **user-run / agent-offline-review** —— 用户本地用 dev key 跑 gated live smoke,agent 不接触 key,只对 raw artifacts 离线机检;`fake-deterministic` 仍是无条件默认。
- **隔离:** P2-A-2 **不**实现用户 key 存储 / 模型下拉 / BYO-key 配置——那些属于 P2-B。

### P2-B 架构方向:BYO-key(grill 2026-06-05 定)

> **口号:Client-owned secret, server-executed provider call.**
> 从 dev/server 自带凭证,转向**用户自带本地凭证**作为可玩配置。Qt 客户端可收集/本地保存/选择用户自己的 API key,并按供应商下拉选模型(自动拉取);但 **provider 网络调用仍只由本地 Python observer/server 执行,客户端绝不直连各家供应商**。这保住"Python owns engine/provider,Qt 只是配置+观战客户端"地基——G3-1/2 的活是进化不是推倒。`fake-deterministic` 仍是无 key 默认。

**修订后的三层安全不变量(取代旧"客户端完全不碰 key"):**
- **Hard invariants:** key 不写死进源码;不提交/打日志/导出进 review packet、prompt manifest、runtime events、客户端崩溃日志;fake-deterministic 模式永不需要 key。
- **Architecture invariant:** Qt 可收集并本地保存用户自有 key;provider 网络调用只由本地 Python server/provider 执行;Qt 不直连各家 API。
- **Storage invariant:** 优先 OS keychain / 凭证库;若有本地回退存储,须明确标 dev-only 或尽量加密;UI 只显示打码 key。

> 落到 P2-B 进场时再单独 brainstorm/spec(存储细节、`/api/providers/{name}/models` 端点、多厂商抽象)。此处只锁方向,不锁实现(锁上不锁下)。

---

## P3 · 评测 · 复盘 · 排行榜 ⏳(仅轮廓)

> 远期阶段,只画轮廓,不预先拆工作任务。关键设计约束已知:**用户看到的结算画面就是评测/复盘**,历史对战即保存的结算数据。

| 模块 | 交付物(轮廓) |
|---|---|
| P3-A 评测 · 复盘 | 把结算画面的数据深化为评测+复盘(谁赢、关键转折、各角色表现)。 |
| P3-B 历史对战 | 保存每局结算数据;点开跳到那局的评测/复盘。 |
| P3-C 动态排行榜 | 基于评测/复盘聚合,形成**每角色**的 AI 胜率排行榜(因可换 AI 才有榜)。 |

> 旧 ROADMAP 的 "Phase 4 / G4 评测平台 / L1 真实排行榜" 即并入本阶段并被重构——评测不再是独立平台,而是结算画面的自然延伸。

---

## Reconcile:旧 G/E/S 编号 → 新产品阶段

| 旧 | 新归属 | 状态 |
|---|---|---|
| E1–E4, D1, D2, S4, S5 | P1-A 评测原语 | ✅ |
| G1a–G1g | P1-B 引擎与 provider 契约地基 | ✅ |
| G1h | P1-C 实时事件骨架 | ✅ |
| G2a | P1-D observer 协议+server | ✅ |
| G2b / G2c / G2d(+G2d-2) | P2 客户端外壳(座舱 / 视角 / 配置入口)→ 喂给 P2-B、P2-C | ✅(管线) |
| G3-1 / G3-2 / G3-3 | P2 实时执行通道(live/fake 开关、HUD、manifest 诚实)→ 喂给 P2-A 真实路径 | ✅(管线) |
| (新) 涌现式引擎 | **P2-A-1**(原临时名 "G4-1") | 🚧 当前 |
| 旧 "Phase 4 / G4 评测平台"、L1 真实排行榜 | **P3**(拆为 P3-A/B/C),重构 | ⏳ 已 supersede |

---

## 维护约定

- 改**阶段或模块** = 大决策,需明确确认后才动本文件。
- 当前工作任务推进/完成 → 更新 `TASKS.md` 与本文件对应行状态。
- 新工作任务只在"当前模块"内细化;进入新模块时再细化该模块的工作任务。
