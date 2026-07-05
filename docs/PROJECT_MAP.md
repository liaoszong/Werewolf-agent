# PROJECT MAP — Werewolf-agent

> **本文件是项目的权威「产品全景地图」。** 它按**产品阶段**(而非工程层)组织,回答"我们最终要做成什么、现在在哪一格、下一格是什么"。
>
> - 规划深度原则:**锁上不锁下**。阶段 + 模块**全部锁定**(很少改,改动即大决策);**工作任务只细化当前模块**;子任务由实现者自动拆(superpowers / spec / writing-plans)。远期模块只画轮廓。
> - 命名:`P<阶段>-<模块>-<工作任务>`,例如 `P2-A-1`。旧 `G*` 编号的映射见文末「Reconcile」表。
> - 与其他文档的关系:`TASKS.md` 是压缩任务索引(任务名/状态/产物),不承载路线判断;本文件是唯一阶段权威。产品阶段冲突一律以本文件为准。
> - 除产品阶段外,文末另有「**系统视图(System View)**」:按工程子系统(SYS-xx 编号)组织的正式系统清单,用于讨论各系统的优化/改进/重构。阶段视图回答"做到哪了",系统视图回答"楼是怎么搭的"。

---

## 一句话产品愿景

一个**移动优先、可参与、可观战的狼人杀 Agent Theater**:每个座位不是一次 API 调用,而是有角色卡、记忆、私有目标、阵营协作、发言风格和博弈策略的 Agent。对局要先像真人狼人杀一样有拉踩、伪装、对跳、结盟、背刺、复盘价值;AI-vs-AI 是默认实验形态,但产品方向必须容纳真人在手机或桌面端扮演一个角色加入实时局。

> 2026-07-02 路线转向:旧路线把重心放在"可审计 AI-vs-AI + 评测/排行榜",工程地基成立,但 Agent 体验太薄,对局无聊。新路线把 **Agent 角色体验与真人参与** 放到 P3,评测/排行榜后移为 P4。SillyTavern 的角色卡/群聊/Lorebook/RAG/摘要/Prompt Inspector 是角色扮演参考;Claude Code / learn-claude-code 的 agent harness、记忆、上下文压缩、工具/权限、子智能体和 team protocol 是工程参考。详见 `docs/superpowers/specs/2026-07-02-agent-roleplay-human-game-pivot-design.md`。
>
> 2026-07-02 客户端路线转向:当前 Qt/QML 观战器保留为 legacy,直到新客户端达到基本 parity;新玩家端按 **Flutter-first client rewrite + backend protocol retained** 推进。旧 storybook/parchment/童话桌游视觉方向废弃,各页面 UI 重新讨论和设计。详见 `docs/superpowers/specs/2026-07-02-p3-e-client-platform-migration-design.md`。

---

## 阶段总览

| 阶段 | 名称 | 状态 | 一句话 |
|---|---|---|---|
| **P1** | 数据与事件地基 | ✅ 完成 | 后端原语:日志 schema/校验/评分/归因、引擎与 provider 契约、实时事件骨架、observer 协议+server。 |
| **P2** | 观战式 AI-vs-AI 对局客户端 | ✅ 完成 | 对局可自演化、可配置、可实时观战,并能进入结算与历史回看。 |
| **P3** | Agent 角色体验 · 真人参与 · 跨平台客户端 | 🚧 当前方向 | 把"座位=API 调用"升级为"座位=有角色卡、记忆、策略与行动工具的 Agent";同时把玩家端迁到移动优先的跨平台客户端,让真人座位加入同一实时局。 |
| **P4** | 评测 · 复盘 · 排行榜 | ⏳ 后移 | 在更有趣的 Agent/真人对局之上做复盘、归因、版本对战与排行榜。 |

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
| P2-D 结算画面 | 结算战报、剧场内结算覆盖层、历史回看/管理、中断局归档和删除语义。趣味性复盘入口归 P3-D,深度评测/复盘归 P4-A。 | ✅ 完成 |
| R0 Windows 桌面发行 | GitHub Releases 首次安装、Velopack 后台更新、Settings 内检查/下载/重启、active-run apply gate、用户数据隔离。 | ✅ 完成 |

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

## P3 · Agent 角色体验 · 真人参与 · 跨平台客户端 🚧(当前方向)

> 当前问题:项目已经能跑、能观战、能审计,但"好玩"不足。多数座位仍像同质化 API 调用:没有稳定人格、没有可持续记忆、没有局内目标管理、没有私密阵营协作,也没有真人坐进去参与博弈。P3 的目标是把狼人杀里真正有趣的点做出来:伪装、欺骗、试探、对跳、结盟、转票、遗言、私聊协作、记仇、复盘。
>
> 客户端问题同样阻塞 P3:当前 Qt/QML UI 过于桌面观战器,且 storybook/parchment/童话桌游方向已被废弃。P3 的玩家端必须移动优先,支持真人入座、实时发言/投票/夜间行动,并在桌面端保持同一套产品表面。新客户端路线见 P3-E。

### P3 设计参照

| 参考 | 对本项目的启发 |
|---|---|
| SillyTavern 角色卡 | 每个座位应有可编辑 Agent Card:身份策略、性格、说话风格、风险偏好、常用套路、禁用行为、示例发言。 |
| SillyTavern Group Chats | 白天讨论不应只有固定轮流发言;需要"被点名回应、话多/话少、强制发言、补充发言"等群聊调度思想。 |
| SillyTavern World Info / Lorebook / Data Bank / Summarize | Agent 需要分层记忆:局内工作记忆、情景记忆、跨局语义记忆、角色/人设知识库;注入必须可追溯、可预算、可见性安全。 |
| Claude Code / learn-claude-code agent harness | Agent = model + harness。循环可以稳定,但工具、记忆、权限、hooks、子智能体、team protocol 和上下文压缩决定能力上限。狼人杀 Agent 也应有 observe → remember → plan → speak/act → reflect 的 harness。 |

### 模块

| 模块 | 交付物(轮廓) | 状态 |
|---|---|---|
| **P3-A Agent Runtime Contract + Memory Spine** | 先锁四层 ownership:SeatCharacterCard / RolePolicy / RuntimeAgentState / ProviderProfile;再建单局 scoped memory、私有笔记、怀疑图、承诺/矛盾记录。所有记忆注入带 provenance、真相层级、status 与 visibility guard。 | 🚧 当前模块 |
| **P3-B 博弈脚手架与桌面发言** | 先建 P3-B0 Structured SpeechAct Contract,再把白天讨论从"顺序发言+投票"升级为可回应、可追问、可对跳、可转票的 table-talk;狼人私密频道、发言-投票一致性、轻量计划器进入 ActionEnvelope 上游。 | ⏳ 下一模块 |
| **P3-C 真人座位实时参与** | 首版后端支持本地单真人 seat,由 profile 的 seat provider=`human` 选择,可映射当前基础板任意 seat/角色;被选中的 seat 不构造 AI provider,所有真人动作由 server action_window 控制。多真人、账号/房间、完整玩家端 UX 仍后续。 | 🚧 当前切片 |
| **P3-D 趣味性复盘入口** | 结算先回答"这局哪里好看/哪里蠢/谁骗过了谁",再接评测指标;把 P4 的评测能力挂到玩家能理解的戏剧节点上。 | ⏳ 后续模块 |
| **P3-E 跨平台真人客户端迁移** | 新玩家端按 Flutter-first 重写,移动端优先、桌面端复用同一产品表面;Qt/QML 只作为 legacy 保留到 parity。保留 Python backend / observer REST+SSE / provider gateway / 日志与可见性边界。 | 🚧 当前设计 |

**P3 并行与前置关系:** P3-E-1/E-2 是 observer-first 客户端切片,可以与 P3-A/P3-B 并行推进;P3-E-3 真人 seat 客户端硬依赖 P3-C server action protocol 与 profile-driven single-human 后端。P3-C 的产品价值又依赖 P3-A/P3-B 让 AI 具备足够角色感和回应能力,否则真人只是进入一局无聊 AI 对局。

### P3-A 工作任务(当前模块,细化到工作任务粒度)

| 工作任务 | 描述 | 状态 |
|---|---|---|
| **P3-A-0 路线转向 spec** | 正式记录从"评测/排行榜优先"转向"Agent 角色体验 + 真人参与优先";把 SillyTavern 与 Claude Code/learn-claude-code 参考转译成 Werewolf-agent 架构。 | ✅ 文档中 |
| **P3-A-1 Agent asset ownership/schema** | 定义 SeatCharacterCard(角色无关人格)、RolePolicy(按真实身份加载)、RuntimeAgentState(每局新建)、ProviderProfile(模型/温度/预算)四层。用户可打包成预设,但 runtime 内部必须拆开。 | ⏳ 待 plan |
| **P3-A-2 Agent memory packet** | 在现有 observation_text 之上建立 `AgentContextPacket`:Fact/Claim/Belief/Commitment/TeamPlan/StaticPlaybook 分层,包含 source ids、audience_scope、confidence、status、supersedes、prompt block hash 与调用成本记录。 | ⏳ 待 plan |
| **P3-A-3 First playable roleplay arm(shadow-safe)** | 先做 6 人基础板的最小 Agent 化闭环:卡片差异可见、记忆引用可追溯、belief 与 fact 不混淆、狼人共享计划不泄漏、旧 baseline 在 shadow mode 下保持可比、调用成本可审计。追问/转票/戏剧节点归 P3-B/P3-D。 | ⏳ 待 plan |

### P3-C 工作任务(真人参与通道,细化到工作任务粒度)

| 工作任务 | 描述 | 状态 |
|---|---|---|
| **P3-C-0 Server action protocol spec + minimal server skeleton** | 已定义真人动作的 observer/server 协议,并落地最小代码切片:协议类型/校验器/错误 envelope、join/state/events/actions 路由骨架、本地开发 join code、session token、idempotency、role projection、安全拒绝语义。仍不接真实 game loop。 | ✅ 已实现 |
| **P3-C-1 Single human seat game-loop integration** | 把 P3-C-0 action window 接入真实 game loop。P3-C-1a 先接通模板本地真人村民发言/投票;P3-C-1b 改为 profile-driven single human seat,seat provider=`human` 时该 seat 不接 AI provider,夜间角色动作与白天发言/投票都走 participant action window。P3-C-1c 补真人遗言、可选窗口超时不阻塞、session/reconnect cursor smoke。P3-C-1d 收紧 SSE cursor、过期/撤销 session 和 role-selectable spec 口径。`response` 依赖 P3-B table-talk,不在 P3-C 单独硬造。 | ✅ 已实现 |
| **P3-C-1a Human villager speech/vote game-loop slice** | 新增 in-memory participant action controller,让 observer participant routes 与 `EmergentGameEngine` 共享 action window/idempotency;模板 launch 显式 `participant.seat_id` 时,本地单真人村民可通过 server action_window 提交白天发言和投票。provider 统计不把真人动作计为 live provider 请求。 | ✅ 已实现 |
| **P3-C-1b Profile-driven single human seat backend** | profile schema/provider 下拉新增 `human`;只允许 seat_overrides 中最多一个 human seat;fake/live profile launch 都配置 participant controller;live credential gate 跳过 human provider 但仍要求其它 AI provider key;engine 对真人狼人/预言家/女巫/村民的当前动作不访问 `_agents[seat]`,改由 action window 驱动。 | ✅ 已实现 |
| **P3-C-1c Final words + reconnect/timeout backend smoke** | 真人 seat 死亡/出局后打开可选 `final_words` action window;提交后进入 public game-log,超时/`pass` 不阻塞对局且不当作 AI provider failure。participant session 在提交后推进 `last_seen_cursor`,state payload 在窗口超时后也返回最新 reconnect cursor。 | ✅ 已实现 |
| **P3-C-1d Participant route hardening + spec alignment** | Participant SSE 显式校验 `cursor=event:<n>`;过期/撤销 session 在 HTTP state 路径返回 `missing_or_invalid_session` 且不泄漏 token;P3-C-0 spec 从 villager-only 口径改为 profile-driven single human seat 可映射当前角色动作。 | ✅ 已实现 |

### P3-E 工作任务(客户端路线,细化到工作任务粒度)

| 工作任务 | 描述 | 状态 |
|---|---|---|
| **P3-E-0 客户端迁移路线 spec** | 正式记录 Flutter-first client rewrite、Qt legacy until parity、backend protocol retained;同步废弃 storybook/parchment/童话桌游 UI 方向。 | ✅ 文档中 |
| **P3-E-1 Flutter protocol spike** | 新 Flutter 客户端连接现有 observer/participant server:配置 base URL、join/resume profile-bound single human seat、读取 participant state、渲染 role-safe live room 与底部 Composer Rail,并提交 speech/final_words + vote/角色结构化动作;不读本地 artifact,不碰 provider。 | ✅ 完成 |
| **P3-E-2 Mobile-first live room slice** | 以手机竖屏为主布局,完成可替代 Qt 基础观战的实时对局房间:移动端入口/导航、昼夜外观、角色库与历史壳、role-safe projection 解析、发言流、座位/阶段/私有信息结构、房间身份提醒弹窗、行动窗口截止/提交/服务器拒绝反馈、候选目标选择与多动作 Composer。桌面端保留响应式扩展口径。 | ✅ 完成 |
| **P3-E-3 Human seat client slice** | 接 P3-C 的 single human seat 后端:合法视野、发言、角色动作、投票、遗言、超时、重连,全部由 server action_window 控制。前置:P3-C-0 protocol + P3-C-1b profile-driven backend。 | ⏳ 待 plan |
| **P3-E-4 Desktop parity / Qt retirement gate** | 先达 player parity(启动/接入、观战、常用配置、真人入座、结算回看);Qt 归档/移除还要求 developer parity(证据/推理轨迹/provider/发行更新等工具链)或另行决策。 | ⏳ 后续 |

### P3 成功口径

- **有趣优先:**发言不再大面积同质化;同一局中能看到稳定人格、记忆引用、对跳/反驳/拉票/转票。
- **博弈优先:**狼人会围绕伪装目标协作,好人会围绕公开/私有信息形成推理链,不同角色行动不只是"合法 JSON"。
- **真人可玩:**真人 seat 不需要上帝视角也能完整参与;AI 能回应真人发言,不是把真人当旁白。
- **移动优先:**默认假设玩家在手机上参与;桌面端是更宽的同一套客户端,不是唯一入口。
- **可证伪的好玩门槛:** P3 不能只证明"合法/安全";至少要有轻量趣味性验收,例如盲评能高于随机地区分不同 AgentCard,且样例局出现可标注的对跳、反驳、拉票或转票节点。
- **安全不退:**所有 Agent 记忆、摘要、RAG、playbook 注入都必须过 SYS-A4 可见性边界;不能把私有事实包装成"记忆"泄漏给不该知道的 seat。
- **成本可控:**默认一名玩家一次行动最多一次玩家模型调用;确定性 harness 负责 context selection、source entitlement、claim ledger 和预算裁剪。反思/记忆更新首版不得扩成多轮 planner。

---

## P4 · 评测 · 复盘 · 排行榜 ⏳(后移)

> P4 不取消,但必须建立在 P3 的"好玩对局"之上。评测指标只评价无聊局没有产品价值。P4 的核心是把结算画面深化为复盘/归因,再形成 Agent 版本、模型、角色卡、记忆策略的排行榜。

| 模块 | 交付物(轮廓) |
|---|---|
| P4-A 评测 · 复盘 | 把结算画面的数据深化为评测+复盘(谁赢、关键转折、谁骗过谁、谁忽略了自己可见信息)。 |
| P4-B 历史对战 | 保存每局结算数据;点开跳到那局的评测/复盘。 |
| P4-C 动态排行榜 | 基于评测/复盘聚合,形成按角色、模型、Agent Card、记忆策略维度切分的动态榜。 |

> 旧 ROADMAP 的 "Phase 4 / G4 评测平台 / L1 真实排行榜" 后移到 P4;旧 P3 的评测/复盘口径不再是当前前线。

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
| **SYS-B4** | 增强脚手架 | **Agent Scaffolding / Agent Harness**(计划、反思、工具、hooks、狼频道、发言-投票一致性) | 现有接缝 = 渲染器 `requires_scaffold` 标志 + `scaffold_model`(scribe provider);未来接 `AgentContextPacket` / roleplay harness | 🚧 P3 核心方向。边界已锁:脚手架在 ActionEnvelope 上游,baseline 永远裁判;不得把中间推理混入 action JSON。默认一玩家行动一次模型调用,额外 team/scaffold 调用必须单独记账。 |
| **SYS-B5** | 角色卡与剧本资产 | Character Card / Persona Card / Playbook Library | 现有 `profile_config` 的 role prompt + seat persona;未来新增四层资产模型与本地资产库 | ⏳ P3-A 待建。对标 SillyTavern 的 Character Card/World Info,但 runtime 必须拆成 SeatCharacterCard / RolePolicy / RuntimeAgentState / ProviderProfile;本局状态永不回写角色卡本体。 |

### C 组 · 平台与质量面(Platform & Quality)

| ID | 系统 | 业界专业名称 | 代码落点 | 现状与已知债务 |
|---|---|---|---|---|
| **SYS-C1** | 评测 | Evaluation Harness;baseline vs ablation(消融) | scoring / attribution / score_records | ✅ P1 原语完整;P4 深化为复盘/排行榜;P3 只取趣味性复盘入口 |
| **SYS-C2** | 观战与回放 | Replay / Spectator System | observer server(REST/SSE)+ Qt 剧场/结算 | ✅ 主体完成;P3-D 趣味性节点展示与 P4-A 逐人深度复盘待做 |
| **SYS-C3** | 质量防线 | 三件套:Differential Testing(差分测试)· **Runtime Verification / Semantic Oracle**(不变量安全网)· Deterministic Simulation Testing(fake 脚本+固定种子,对标 FoundationDB DST) | 差分:②a 的 OLD-oracle gate;安全网:`docs/superpowers/specs/2026-06-09-p2a-invariant-safety-net-design.md`(PLAN-READY);DST:`emergent_fake_script.py` + seed 体系 | ✅ 三件套全部就位(2026-06-10):安全网已合并(`src/werewolf_eval/invariants/`,7 不变量 + B1 防泄漏×4站点 + B4 防双死×3站点 + 50-seed fuzz,字节中立);剩 engine-level fuzz、B2/B3 守卫跟 ledger/EffectQueue |
| **SYS-C4** | 桌面发行与更新 | Desktop Distribution / In-App Update | `scripts/release/`, `src/werewolf_eval/release_host/`, `clients/qt_observer/qml/ProviderSettingsView.qml` | ✅ R0 完成:PyInstaller onedir bootstrapper、frozen observer server、Qt deployment tree、Velopack package、GitHub Releases source、host-owned update RPC、Settings 内更新 UI、安装态本地 E2E 与数据保留验证 |
| **SYS-C5** | 真人参与通道 | Human-in-the-loop Game Client / Participant Seat Gateway | observer REST/SSE + participant action endpoints;未来新增 human seat UI | 🚧 P3-C-0 协议与 route skeleton 已建;P3-C-1 已支持 profile-driven single human seat,被选 seat 不构造 AI provider,当前基础板角色动作、白天发言/投票、遗言、超时与 reconnect cursor smoke 接入 `EmergentGameEngine` action windows。后续仍需 P3-B `response`/table-talk、多真人、账号/房间和完整玩家端 UX。真人 seat 必须走 server-controlled `action_window_id` / session token / idempotency key / reconnect cursor;客户端不得读取本地 artifact 或 god snapshot 伪造参战视角。 |
| **SYS-C6** | 跨平台玩家客户端与设计系统 | Cross-platform Client Platform / Design System | 当前:`clients/qt_observer/` legacy;`clients/flutter_app/` P3-E-1 spike | 🌱 Flutter-first 客户端雏形已建:移动优先 join/身份确认、role-safe live room、语义高亮发言流、可收起 Composer Rail、participant REST/SSE client 与 action submit。Android 侧已接入 Internal/Production 远程更新通道;移动端早期冒烟默认使用 PaleInk 公网 observer,并保留本机开发 server preset。Qt/QML 保留到 parity。旧 storybook/parchment/童话视觉只属于 legacy,不得作为新页面默认方向。客户端边界仍是 observer/participant protocol,不直连 provider、不读本地 artifact。 |

> **系统间的关键依赖**(讨论重构顺序时用):SYS-A2 的 ledger 是女巫迁移前提;SYS-C3 安全网是 A2 后续所有大刀(ledger/EffectQueue/NightPlan)的护栏,先网后刀;P3-A 先建 SYS-B5 Agent Card 与 SYS-B1 AgentContextPacket,再让 SYS-B4 harness 消费它;SYS-B1 的情景/语义记忆依赖 SYS-A4 可见性检查(I4b)防泄漏;SYS-C5 真人参与必须复用 SYS-A4/SYS-B2/SYS-C2,不能绕过 observer 协议;SYS-C6 新客户端必须复用 SYS-C2/SYS-C5 协议边界,不能变成另一个 runtime。

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
| 旧 "Phase 4 / G4 评测平台"、L1 真实排行榜 | **P4**(评测/复盘/排行榜),后移 | ⏳ 已 supersede |

---

## 维护约定

- 改**阶段或模块** = 大决策,需明确确认后才动本文件。
- 当前工作任务推进/完成 → 更新 `TASKS.md` 与本文件对应行状态。
- 新工作任务只在"当前模块"内细化;进入新模块时再细化该模块的工作任务。
