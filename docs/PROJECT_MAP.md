# PROJECT MAP — Werewolf-agent

> **本文件是项目的权威「产品全景地图」。** 它按**产品阶段**(而非工程层)组织,回答"我们最终要做成什么、现在在哪一格、下一格是什么"。
>
> - 规划深度原则:**锁上不锁下**。阶段 + 模块**全部锁定**(很少改,改动即大决策);**工作任务只细化当前模块**;子任务由实现者自动拆(superpowers / spec / writing-plans)。远期模块只画轮廓。
> - 命名:`P<阶段>-<模块>-<工作任务>`,例如 `P2-A-1`。旧 `G*` 编号的映射见文末「Reconcile」表。
> - 与其他文档的关系:`TASKS.md` 是压缩任务索引(任务名/状态/产物),不承载路线判断;本文件是唯一阶段权威。产品阶段冲突一律以本文件为准。
> - 除产品阶段外,文末另有「**系统视图(System View)**」:按工程子系统(SYS-xx 编号)组织的正式系统清单,用于讨论各系统的优化/改进/重构。阶段视图回答"做到哪了",系统视图回答"楼是怎么搭的"。

---

## 一句话产品愿景

一个**可观战的 AI-vs-AI 狼人杀**:开局前可配置每个角色由哪个 AI 扮演、改其 agent prompt(增加可玩性)→ 进入对局,**实时上帝视角观战**(看每个 AI 的决策、发言、投票、夜晚揭示)→ 结算画面;结算即评测/复盘,历史对战可回看,并据此形成**每角色 AI 胜率排行榜**。

---

## 阶段总览

| 阶段 | 名称 | 状态 | 一句话 |
|---|---|---|---|
| **P1** | 数据与事件地基 | ✅ 完成 | 后端原语:日志 schema/校验/评分/归因、引擎与 provider 契约、实时事件骨架、observer 协议+server。 |
| **P2** | 观战式 AI-vs-AI 对局客户端 | ✅ 完成 | 对局可自演化、可配置、可实时观战,并能进入结算与历史回看。 |
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

## P2 · 观战式 AI-vs-AI 对局客户端 ✅(已完成)

> 本阶段已把写死剧本替换为**真正自演化的对局**,并形成完整的**配置 → 观战 → 结算 → 历史管理**闭环。

### 模块

| 模块 | 交付物(轮廓) | 状态 |
|---|---|---|
| **P2-A 涌现式游戏引擎** | 全角色 AI 驱动的真实对局:刀/查/救毒/发言/投票/胜负/动态回合。离线 fake 默认可测,真实 DeepSeek 可走 live 开关。 | ✅ 完成(P2-A-1/A-2;后续引擎演进走系统视图 SYS-A2 action runtime 线) |
| P2-B 开局配置 | BYO-key、本地凭证存储与中继、供应商中心、多供应商预设、per-seat provider/prompt/参数配置、调度沙盘、配置保存/导入/导出。 | ✅ 完成 |
| P2-C 实时观战上帝视角 UI | 实时上帝视角剧场、事件跟随、SSE/live 状态、玩家环/发言/投票/夜晚揭示、证据控制台、AI 推理轨迹、导航生命周期。 | ✅ 完成 |
| P2-D 结算画面 | 结算战报、剧场内结算覆盖层、历史回看/管理、中断局归档和删除语义。逐人深度复盘仍归 P3-A。 | ✅ 完成 |

### P2-A 工作任务(当前模块,细化到工作任务粒度)

| 工作任务 | 描述 | 状态 |
|---|---|---|
| **P2-A-1 完整自演化的一局** | 新建 `EmergentGameEngine`(复用 P1 全部原语,不动旧剧本模式)。全角色 AI、夜→昼→唱票→出局→胜负、动态回合;非法输出复用 `ProviderAgent` 校验 + 确定性兜底;离线 fake 默认 + 全测试(18 个)为验收门槛。 | ✅ 完成(commit f287722) |
| **P2-A-2 真实 DeepSeek 涌现对局(live 集成冒烟)** | 让 P2-A-1 引擎走真实 live 路径并跑通 1 次冒烟。**定位:集成冒烟,非内容调优**。两个前置已修:发言 prompt 路径 + 观察文本化(引擎侧 role-safe)。 | ✅ 完成 — 两局真实 DeepSeek 冒烟 PASS(村民胜 22/19、狼人胜 14/13,rate 0.86/0.93,全门槛过) |

> P2-A-1 收口于已批准 DoD 门槛(离线确定性整局 + 全测试绿);真实 live 因非"薄接线"而拆为 P2-A-2(owner 决定 2026-06-05)。其余 P2-A 工作任务(多轮对辩、可配板子)继续锁上不锁下。

**P2-A-2 验收口径(grill 2026-06-05 锁定):**
- **硬门槛①(visibility 不喂漏):** live prompt 只能由该 seat 的 `public_event_ids ∪ private_event_ids` 渲染(引擎侧文本化,provider 只收已过滤的 `observation_text`,绝不碰全局事件存)。机检:渲染来源 event_ids ⊆ obs 可见集;非狼视角 prompt 不含狼队私有/队友身份/他人私有结果。**喂漏=阻断性 bug。**
- **硬门槛②(真的是 live,非 fallback 糊过):** `max_requests_per_game=64`、`live_success_rate ≥ 0.80`、`live_success_actions ≥ 12`(2026-06-05 两局真实数据校准:6 人局 1-2 轮分胜负、~14-22 回合,原 20 误杀合法早终局)、`budget_exhausted` 一律 hard fail;兜底可救场不可过关,须按 `provider_result_kind`(live_success / invalid_then_fallback / timeout_then_fallback / error_then_fallback / budget_exhausted)统计并在验收摘要中暴露。更短早终局 → `--allow-short-game` + artifact 解释。
- **硬门槛③(诚实链,复用 G3-3):** `source_label=="[DeepSeek API output]"`、manifest 记真实 model、`token_usage>0`(fake 恒 0)。
- **软门槛(嘴漏=内容警告):** 模型幻觉自称拥有不可见系统事实 → 记 content warning,不阻断(除非破坏 action 契约/崩);狼人伪装/诈身份是正常玩法。
- **运行(spec-review 2026-06-05 supersede grill Q4):** **user-run / agent-offline-review** —— 用户本地用 dev key 跑 gated live smoke,agent 不接触 key,只对 raw artifacts 离线机检;`fake-deterministic` 仍是无条件默认。
- **隔离:** P2-A-2 **不**实现用户 key 存储 / 模型下拉 / BYO-key 配置——那些属于 P2-B。

### P2-B 架构方向:BYO-key(grill 2026-06-05 定)

> **口号:Client-owned secret, server-executed provider call.**
> 从 dev/server 自带凭证,转向**用户自带本地凭证**作为可玩配置。Qt 客户端可收集/本地保存/选择用户自己的 API key,并按供应商下拉选模型(自动拉取);但 **provider 网络调用仍只由本地 Python observer/server 执行,客户端绝不直连各家供应商**。这保住"Python owns engine/provider,Qt 只是配置+观战客户端"地基——G3-1/2 的活是进化不是推倒。`fake-deterministic` 仍是无 key 默认。

**修订后的三层安全不变量(取代旧"客户端完全不碰 key"):**
- **Hard invariants:** key 不写死进源码;不提交/打日志/导出进共享产物、prompt manifest、runtime events、客户端崩溃日志;fake-deterministic 模式永不需要 key。
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

## 系统视图(System View)— 正式系统清单

> **与阶段视图正交的第二维度**(2026-06-10 加入)。按业界标准分法:架构(Architecture)→ 子系统(System)→ 模块(Module)。每个系统给稳定编号 **SYS-xx**,讨论优化/改进/重构时以此为统一词汇。每行给出:业界专业名称(便于检索行业最佳实践)、代码落点、现状与已知债务。
>
> 状态图例:✅ 成熟 · 🚧 在建 · 🌱 雏形(有最小实现,待长大)· ⏳ 仅图纸(spec/讨论有,代码无)

### A 组 · 对局核心(Game Core)

| ID | 系统 | 业界专业名称 | 代码落点 | 现状与已知债务 |
|---|---|---|---|---|
| **SYS-A1** | 游戏循环与阶段调度 | Game Loop / Phase State Machine;回合制的 Turn Order System | `emergent_engine.py` `_run_inner` | 🌱 夜→昼序列仍写死在主循环;**NightPlan**(夜序数据化 + 狼→女巫信息管道显式化)= 本系统的收口件,⏳ 等第一个夜间新角色(守卫)再落地 |
| **SYS-A2** | 能力系统 | **Ability System**(对标 Unreal GAS:Ability/Cost/Effect/Activation) | `action_runtime/`(registry·ruleset·validator·envelope·settler)+ 引擎 dispatch | 🌱 主体完成(2026-06-10):registry/validator/settler/猎人 + ②a 注册表派发(=Activation 窗口 v1,字节恒等收口)。⏳ 待建:**CapabilityLedger**(②b,=GAS 的 Cost/Charges,女巫迁移的前提)、**EffectQueue**(=Effects 管线,等狼王/情侣)、DecisionWindow 完整版。小尾巴:加角色还要碰 `profile_config.ALLOWED_ROLES` + `observer_visibility._KNOWN_ROLE_TEAMS` 两处名单 |
| **SYS-A3** | 夜晚联合结算 | Simultaneous Action Resolution(对标 Diplomacy adjudicator) | `action_runtime/settler.py`(JointSettler) | ✅ 已含奶穿规则表 + guard 钩子(v1.5 守卫即插) |
| **SYS-A4** | 信息可见性 | Information Visibility / Fog of War;博弈论:Information Set | 引擎 visibility tag + `_build_obs`;observer 侧 `observer_visibility.py`(独立第二实现) | ✅ 双实现互为见证(不变量 I4b 的反循环基础)。债务:observer 私有 tag 只认 seer/witch,新角色专属视野需加分支 |
| **SYS-A5** | 对局事件日志 | **Event Sourcing**(事件溯源:只追加事件流 + 快照 + 状态可重放) | game-log / decision-log / consensus-log / failure-audit / snapshots / provider-turns | ✅ 教科书式落地。安全网 I7(重放一致性)即本系统的完整性检查 |

### B 组 · 智能体层(Agent Layer)

| ID | 系统 | 业界专业名称 | 代码落点 | 现状与已知债务 |
|---|---|---|---|---|
| **SYS-B1** | 记忆与上下文构建 | **Agent Memory / Context Engineering**;分层:工作记忆 → 情景记忆(episodic)→ 语义记忆(semantic) | `render_observation_text` + `augment_witch_observation`(每轮 prompt 组装) | 🌱 现在 = 工作记忆层的最小实现(每轮由可见事件重建上下文)。情景/语义记忆 ⏳ 属增强层,接缝 AgentContextPacket 已留;**任何记忆注入必须带 source ids 过 I4b 可见性检查**(防隐形喂漏,已写进安全网 spec)。**prompt 版本化机制已落地**(prompt_v1 字节锁 + ledger + 三元组戳,spec 2026-06-10):baseline prompt 修订有合法出口 |
| **SYS-B2** | 决策协议 | Action Protocol / Structured Output | `action_runtime/envelope.py`(ActionEnvelope)+ strict-JSON;tool-calling 仅作消融轴 | ✅ baseline 统一 strict-JSON 已锁定(评测公平性不变量) |
| **SYS-B3** | 模型接入网关 | Model Gateway / LLM Provider Abstraction | provider registry + BYO-key + 9 家 OpenAI 兼容预设 | ✅ 主体完成;剩 B5 收尾(per-seat token/成本汇总、退役 deepseek-only env 兜底) |
| **SYS-B4** | 增强脚手架 | **Agent Scaffolding**(persona / 反思 / 狼频道 / 发言-投票一致性) | 现有接缝 = 渲染器 `requires_scaffold` 标志 + `scaffold_model`(scribe provider);**注意:并不存在 manifest `enabled_scaffolds` 字段——B4 真正进场时需新增,勿按此名找** | ⏳ 仅图纸(另立 spec);边界已锁:脚手架在 ActionEnvelope 上游,baseline 永远裁判 |

### C 组 · 平台与质量面(Platform & Quality)

| ID | 系统 | 业界专业名称 | 代码落点 | 现状与已知债务 |
|---|---|---|---|---|
| **SYS-C1** | 评测 | Evaluation Harness;baseline vs ablation(消融) | scoring / attribution / score_records | ✅ P1 原语完整;P3 深化为复盘/排行榜 |
| **SYS-C2** | 观战与回放 | Replay / Spectator System | observer server(REST/SSE)+ Qt 剧场/结算 | ✅ 主体完成;P3-A 逐人复盘待做 |
| **SYS-C3** | 质量防线 | 三件套:Differential Testing(差分测试)· **Runtime Verification / Semantic Oracle**(不变量安全网)· Deterministic Simulation Testing(fake 脚本+固定种子,对标 FoundationDB DST) | 差分:②a 的 OLD-oracle gate;安全网:`docs/superpowers/specs/2026-06-09-p2a-invariant-safety-net-design.md`(PLAN-READY);DST:`emergent_fake_script.py` + seed 体系 | ✅ 三件套全部就位(2026-06-10):安全网已合并(`src/werewolf_eval/invariants/`,7 不变量 + B1 防泄漏×4站点 + B4 防双死×3站点 + 50-seed fuzz,字节中立);剩 engine-level fuzz、B2/B3 守卫跟 ledger/EffectQueue |

> **系统间的关键依赖**(讨论重构顺序时用):SYS-A2 的 ledger 是女巫迁移前提;SYS-C3 安全网是 A2 后续所有大刀(ledger/EffectQueue/NightPlan)的护栏,先网后刀;SYS-B1 的情景记忆依赖 SYS-A4 可见性检查(I4b)防泄漏;SYS-A1 的 NightPlan 与 SYS-A2 的 EffectQueue 都等真实角色需求触发,不预建。

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
| (新) 涌现式引擎 | **P2-A-1**(原临时名 "G4-1") | ✅ |
| 旧 "Phase 4 / G4 评测平台"、L1 真实排行榜 | **P3**(拆为 P3-A/B/C),重构 | ⏳ 已 supersede |

---

## 维护约定

- 改**阶段或模块** = 大决策,需明确确认后才动本文件。
- 当前工作任务推进/完成 → 更新 `TASKS.md` 与本文件对应行状态。
- 新工作任务只在"当前模块"内细化;进入新模块时再细化该模块的工作任务。
