# P2-C-1 剧场化观战主界面 + 底部取证控制台 — Design Spec

**Status:** approved with 4 minor edits applied (2026-06-06 user review) — proceeding to writing-plans, not yet implementing
**Route:** `docs/PROJECT_MAP.md` → P2(观战式 AI-vs-AI 对局客户端)/ 模块 C(实时观战上帝视角 UI)/ 工作任务 1。
**Date:** 2026-06-06
**Supersedes:** `docs/superpowers/specs/2026-06-05-p2-c-1-theater-view-NOTES.md`(brainstorm 工作笔记;本 spec 落地后删除该 NOTES)。
**Depends on(复用,不推倒):** P1-D observer 协议 + 本地 server(`observer_server.py`/`observer_protocol.py`/`observer_visibility.py`)、P2-A 涌现式引擎事件流(`emergent_engine.py`)、G2b/G2c/G3 已建 Qt 座舱外壳(`AppShell.qml`、C++ `ObserverApiClient` + `ObserverSseParser`、`Theme.qml`/`I18n.qml` 设计系统、诚实链组件)。

> 一句话:**主舞台按日夜呼吸,底部控制台负责取证,Event Queue 统一展示节奏,播放器按钮只是队列的遥控器。** 现有数据仪表盘(`LiveCockpitView`)不被废弃,而是**降级**为剧场视角内的取证层。

---

## 0. Goal

把现有的"数据仪表盘式"观战主界面(`LiveCockpitView`)换成**剧场化的默认观战体验**:6 座玩家环按 `phase` 呼吸式重组,发言剧场打字机式逐字呈现,夜晚以聚光 + 发光连线揭示狼刀/查验/用药,底部三档取证控制台承载全部诚实链证据。观众享受**全知实时**的戏剧性反讽(看着村民投错人)。

**Success criteria**

- `AppShell.navigateCockpit()` 进入新的 `TheaterView`;老 `LiveCockpitView` 退役为顶层视图,其诚实链组件复用进底部 `EvidenceConsole`。
- 同一 `TheaterView` 随 `phase` 在 night / day-discussion / voting 三态间**呼吸式**重组布局,过渡走 ≤1.5s 的 QML Transition。
- **QML 侧 Event Presentation Queue** 按事件类型分配展示时长,逐条消费驱动舞台状态;**phase 过渡动画 = 队列消费的硬性 gate**(consumer 必须等过渡 `onStopped` 才弹下一条)。
- 全知上帝视角(`perspective="god"`)实时看到所有真实身份 + 夜晚动作;底部 **Seat Lens** 切到 `role:pN` 重新投影,演示视角差。
- 发言/动作文本经**视角安全的后端 enrichment**(post-visibility-filter)从 projection back-fill —— 不喂漏、不碰 prompt/provider 秘密。
- **Live in-progress 口径(降调):** live 进行中只保证 thin-event 舞台更新(phase / active seat / board / waiting);**有向连线(`actor→target`)与完整 `data.summary` 文本需 projection 富化 → 仅对 `game-log.json` 已存在的 just-finished run 保证;live 无 target 时连线降级为 active-seat spotlight/占位**;instant live summary 显式推迟(§7)。
- 薄播放器(Play/Pause · 1x/2x/4x/Instant · 跳到下一阶段 · 跳到队列末尾),**不做时间轴拖动**。
- Qt 静态契约测试更新且绿;Qt 构建 exit 0;`ctest` 绿;视觉抓图确认三态布局。

---

## 1. Product framing(locked,brainstorm 2026-06-05)

- **P2-C = 默认观战体验 = Theater / Spectator View(上帝全知)。** 现有 `LiveCockpitView`(诚实链数据仪表盘)**不被废弃**,但**从主界面降级**为剧场视角里的「取证层」(底部 `EvidenceConsole`)。
- **剧透程度 = 全知实时(纯上帝):** 观众实时看到所有真实身份 + 夜晚动作(狼刀谁、预言家查谁、女巫救/毒)。符合产品愿景「看每个 AI 的决策…夜晚揭示」。
- **PerspectiveSwitcher(按座位视角)不再是主观看模式**,重生为底部控制台里的 **Seat Lens / View as Seat**(切 `role:pN` 重新投影,演示"那个 AI 当时看到了什么")。

---

## 2. Current state(已逐一核对源码)

### 2.1 Qt 外壳与导航(复用)

- `AppShell.qml:159` `StackView`(objectName `appShellStack`);`navigateCockpit()`(`:198`)`replace` 进 `cockpitComponent`(`:180`,当前 = `LiveCockpitView{ objectName:"liveCockpitView" }`)。其余导航:`navigateHome/Setup/Preflight/History`。
- `LiveCockpitView.qml`(objectName `liveCockpitView`):`Component.onCompleted` 调 `ObserverClient.connectStream()` + `refreshProjection()`;组合 `StatusBadge`(`runStatusBadge`)、`PerspectiveSwitcher`(`perspectiveSwitcher`)、`ViewBoundaryBadge`、`ProjectionProofPanel`、`RoleCard` 网格(`playerPanelGrid`)、`EventTimeline`(`eventTimeline`)、`AuditLinksPanel`(`auditLinksPanel`)、失败摘要(`providerFailureSummary`)。
- **诚实链组件(复用不重写)** `clients/qt_observer/qml/components/`:`ViewBoundaryBadge`(props `perspective/contractVersion/hiddenEventCount/hiddenSnapshotCount`)、`ProjectionProofPanel`(prop `proof` + hidden counts)、`AuditLinksPanel`(读 `currentRunId/currentPerspective/baseUrl`,6 个审计链 chip)、`EventTimeline`(读 `eventItems`,滚动事件行)、`PerspectiveSwitcher`(`ComboBox`,9 视角 `god/public/role:p1–p6/team:werewolf`,读写 `currentPerspective`)。另有可复用:`RoleCard`、`StatusBadge`、`AppCard`、`AppButton`、`SectionHeader`、`EmptyState`、`GlowDot`、`AppBackground`。

### 2.2 C++ 数据层(复用,薄扩展)

- `ObserverApiClient`(Q_PROPERTY)`currentRunId/currentStatus/currentPerspective/connected/lastError/eventItems/playerItems/projectionProof/hiddenEventCount/hiddenSnapshotCount/visibilityContractVersion/…`;invokables `connectStream/disconnectStream/refreshProjection/openRun/startDefaultMatch/launchFromProfile/refreshCapabilities`。
- **SSE:** `ObserverSseParser.feed()` 按 `\n\n` 切帧,只认 `event: runtime_event` / `run_status`;每条转 `QVariantMap` + 注入 `_eventType`,append 进 `eventItems`。
- **projection:** `refreshProjection()` → `GET /api/runs/{id}/projection?perspective={p}`,**latest-wins serial guard**(serial + runId + perspective 三重校验弃旧响应);当前只消费 `players[]/proof/hidden_*counts`,**未消费 envelope 里的 `events[]`**。

### 2.3 后端事件 / 可见性 / enrichment(关键发现,决定本 spec 是否含后端改动)

- **引擎事件双轨(`emergent_engine.py:249-269`):** `_emit()` 把**富事件** `{event_id, sequence, round, phase, type, actor, target, visibility, data:{summary, visible_info_refs}}` append 进内存 `self._events`(→ 收口写 `game-log.json`);但写运行时主线(`runtime_events.emit`)时 **payload 只带 `{event_id, type}`**。
- **⇒ 已核实:SSE 与 `/projection` 都源自 `events.jsonl` 的运行时事件,只有 `payload:{event_id,type}`,不带 `summary`/`target`。** `project_events()`(`observer_visibility.py:519-533`)对可见事件只做 `dict(event)` 拷贝 + `_visibility_reason`,**不富化**。`build_projection_envelope()`(`:725-736`)输出含 `events[]`,但仍是 thin。三条取事件路径(`/events`→`filter_events_for_perspective`、`/projection`→`project_events`、SSE→`event_visible_to_perspective`)一律 thin。
- **summary 的真源 = `game-log.json`**(`events[].data.summary` + `target`),是 `ALLOWED_ARTIFACTS`(`observer_protocol.py:34`)里可经 `GET /api/runs/{id}/artifacts/game-log.json` 取的工件,但**该 artifact 路由不做 perspective 过滤**(`observer_server.py:404-417` 直接送原文)——即 game-log.json 是**未投影的上帝全文**,直接喂 Seat Lens 会**漏**隐藏摘要。
- **写入时机:** `game-log.json` 在**收口一次性写**(`run_emergent_deepseek_game.py:117`),非增量。⇒ live 进行中该工件尚不存在;**已完成的局(刚跑完的 fake / 已结束的 live)才有完整 summary 源**。
- **安全边界(已验证):** `observer_visibility.py:114-127` 投影源规则明文「Do not return prompt text, provider secrets, local absolute paths, or secret-like fields」;decision_log 的 `reason_summary`/`visible_info_refs`(`emergent_engine.py:286-301`)是**审计工件**,不进投影。

> **结论(本 spec 据此定 §7 后端 delta):** projection 当前不带 summary;NOTES §10-2 预案「薄后端加字段」成立。enrichment 走**视角安全的 projection 富化**(post-filter join game-log.json),而非客户端直读未投影的 game-log.json——后者无法安全服务 Seat Lens。

---

## 3. Architecture

### 3.1 组件拓扑(新建 vs 复用)

```
AppShell.navigateCockpit() ──► TheaterView.qml  (新, objectName "theaterView")   ← 默认观战面
  │
  ├─ SeatRing.qml          (新)  呼吸式 6 座环:真角色 / alive-dead / active 高亮 / 连线层
  ├─ SpeechTheater.qml     (新)  发言·事件流:打字机 + 内联三层 AI Trace
  ├─ PlaybackControls.qml  (新)  薄遥控器(Play/Pause·1x-4x-Instant·next-phase·queue-end)
  ├─ EventPresentationQueue.qml (新, 非视觉控制器)  Timer + JS ring buffer,展示节奏内核
  └─ EvidenceConsole.qml   (新)  底部三档取证控制台(Closed/Peek/Expanded)
        └─ 复用诚实链(re-home,不重写):
             PerspectiveSwitcher(→ Seat Lens 重命名)· ProjectionProofPanel
             · ViewBoundaryBadge · EventTimeline · AuditLinksPanel · 失败摘要

数据管线不动:C++ ObserverApiClient(SSE/REST)+ ObserverSseParser 继续承载。
新增 1 个 Q_PROPERTY(projectionEvents)+ 1 处后端 projection 富化(§7)。
```

### 3.2 数据流

```
后端 server ──SSE thin notify──► ObserverSseParser ──► eventItems(thin: payload.event_id/type, actor, round, phase, visibility)
                                                            │
                                                            ▼
                                              EventPresentationQueue  ──逐条消费、按 type 计时──► 舞台状态(SeatRing/SpeechTheater)
                                                            ▲
refreshProjection(perspective) ──► projection.events[](§7 富化: 可见事件带 data.summary + target) ──► projectionEvents(新属性)
                                                            │  按 payload.event_id 关联,back-fill 文本(打字机"追上"时浮现)
```

- **Live 进行中:** SSE 增量喂队列(立即驱动 board);随新 seq `refreshProjection()` 重拉富化文本(局未收口前 game-log.json 不存在 → 文本在收口后补齐,见 §7 live 延迟说明)。
- **刚跑完的 fake / 已结束 live:** `connectStream()` 时 server 一次性回放全部历史事件(`observer_server.py:661` 先发 existing,再 tail);队列**不一次性渲染**,按剧场节奏慢慢演;`refreshProjection()` 一次拿全富化文本。

### 3.3 呼吸式布局(核心)——同一 View,重心随 `phase` 改变

| 态 | SeatRing | SpeechTheater | 焦点 |
|---|---|---|---|
| **Night** | center-stage 主导 | 退场/压暗 | 聚光(压暗非活跃座位)+ 发光连线(红线 狼→猎物)+ kill/check/witch spotlight |
| **Day discussion** | 缩到左/左上 | 展开为主阅读面(打字机) | 当前发言者在环上高亮;长句横向阅读优先 |
| **Voting** | 重获视觉优先 | 显示投票理由 / 最后陈述 | vote 连线 + 计票条(tally) |

过渡走 `phase_change` ≤1.5s 预算的 QML `Transition`/`PropertyAnimation`;**过渡进行中队列暂停消费**(§6 yield 不变量)。

---

## 4. Locked decisions

| # | 决策 | 选择 | 理由 |
|---|---|---|---|
| D1 | 默认观战面 | **新 `TheaterView`** 成为 `navigateCockpit` 目标;`LiveCockpitView` 退役 | 剧场化娱乐导向 > 数据仪表盘(PROJECT_MAP P2-C 定义)。 |
| D2 | 诚实链去向 | **re-home 进 `EvidenceConsole`,复用不重写** | 诚实链是项目核心资产;降级为取证层而非废弃(brainstorm)。 |
| D3 | 取证控制台位置 | **底部三档**(Closed/Peek/Expanded),非右抽屉 | 白天核心是发言剧场,大模型长句最怕被压缩宽度折行;底部保留横向阅读结构。 |
| D4 | 展示节奏内核 | **QML 侧 Event Presentation Queue**(Timer + ring buffer) | 纯展示节奏关注点;SSE/REST I/O 留 C++ 不碰。 |
| D5 | 队列 ↔ 动画 | **phase 过渡 `onStopped` = 队列硬 gate**(consumer 必须 yield) | 防止 UI 变形/过渡半途就渲染后续文本。 |
| D6 | 文本 enrichment | **视角安全的 projection 富化**(post-filter join game-log.json),client 按 `event_id` back-fill | projection 已逐视角过滤;join 在过滤后做,god 全见 / Seat Lens 只见该座可见,**不漏**。 |
| D7 | 伪迷雾深度 | **轻量**(`Unknown`/`████`/`[ENCRYPTED]` + opacity);重型毛玻璃/shader **推迟** | P2-C-1 求"能看 + 诚实",polish 留 P2-C 后续。 |
| D8 | 播放器 | **薄遥控器**,无时间轴拖动 | 队列 replay-ready,但历史回看产品功能属 P3-B。 |
| D9 | 视角默认 | **`god`**(全知);Seat Lens 切 `role:pN` | 产品愿景 = 上帝视角看 AI 决策。 |
| D10 | 配色 | **沿用现有 faction tokens**(`Theme.roleAccent`:狼 #EF4444 / 预言家 #FBBF24 / 女巫 #A855F7 / 村民 #60A5FA);夜晚聚光+连线为"深化" | "沿用并深化"既有设计系统,避免改共享 token 波及 setup 视图。brainstorm 的 indigo-seer/fluo-green-witch 见 §18 待确认。 |

---

## 5. Component inventory

> 命名遵循既有 camelCase objectName 约定;所有字符串走 `I18n.t(zh, en)`(English 第 2 参);只用 `Theme.*` token,无字面色值/尺寸;charcoal/silver 暗黑剧场。视图根 `Item` 不 `anchors.fill`(StackView 定尺寸)。

### 5.1 `qml/TheaterView.qml`(NEW)— objectName `theaterView`

- `navigateCockpit()` 的新目标。`Component.onCompleted`:`if (currentRunId) { connectStream(); refreshProjection() }`(沿用 `LiveCockpitView` 入场逻辑)。
- 持有 `EventPresentationQueue`(id `eventQueue`)、`SeatRing`、`SpeechTheater`、`PlaybackControls`、`EvidenceConsole`。
- `state` **绑定** `eventQueue.layoutPhase`(非命令式 `onPhaseBoundary` 赋值,P2-D 保证 reset 时布局同步);state 切换驱动三态 `Transition`/`PropertyAnimation`,其(单一终态)`onStopped` 调 `eventQueue.resumeAfterTransition()`(D5 yield-gate)。
- 暗黑剧场背景(碳黑 / 极暗深空蓝,复用/深化 `AppBackground`)。

### 5.2 `qml/components/SeatRing.qml`(NEW)— objectName `seatRing`

- 呼吸式 6 座环:每座真角色(`Theme.roleAccent`)、alive/dead(dead 压暗 + 划除)、active 高亮(发光环 `GlowDot` 风格)。
- **连线层(Canvas/Shape):** 狼→猎物红线、预言家→目标线、投票连线 —— **有向连线需 `current.target`(来自 projection 富化);live 未收口无 target 时只画 active-seat spotlight/占位,不画有向线(P1-B)**;夜晚瞬间扩散光环;**不用弹窗 Dialog**。
- 读 `playerItems`(座位/角色/alive,来自 projection);active seat / 连线由 `eventQueue.current`(**规范化 PresentationEvent**,§6)驱动:`current.type/actor/target` —— **不直接读 raw runtime 字段(`payload.type` 等)**。
- 轻量伪迷雾(D7):Seat Lens 下不可见身份 → `Unknown`/`████`,不可见连线 → 隐藏/降透明。

### 5.3 `qml/components/SpeechTheater.qml`(NEW)— objectName `speechTheater`

- 发言/事件叙事流:游戏叙事动作用大号优雅 Sans(`Theme.font.display`);AI 推理/日志用小号 Monospace(`Theme.font.mono` Consolas),打字机、半透明、局部浮现。
- **打字机**:按字数推进(队列分配时长,最长 6–8s);文本来自 `eventQueue.current.summary`(**规范化 PresentationEvent**,§6;其 `summary` = 匹配 projection 事件的 `data.summary`)—— **组件读 PresentationEvent,不碰 raw runtime**。**just-finished run 文本完整;live 进行中 `game-log.json` 未收口时 `current.summary===""` → 持续占位/淡入(§0/§7 口径)。**
- **内联三层 AI Trace**(§8):L1 状态、L2 `data.summary`、L3 点击展开 = `reason_summary`(若暴露)+「open in console」跳 `EvidenceConsole`。

### 5.4 `qml/components/PlaybackControls.qml`(NEW)— objectName `playbackControls`

- 控件:Play/Pause、1x/2x/4x/Instant、跳到下一阶段(队列 phase boundary marker)、跳到当前队列末尾。**无时间轴拖动。**
- 调 `eventQueue` 的 `play/pause/setSpeed/seekNextPhase/seekQueueEnd`;任何当前事件展示读 `eventQueue.current`(**PresentationEvent**),不碰 raw runtime 字段。
- **Live 语义:** pause 只停 UI 展示,**不停后端对局**;2x/4x/instant 只能消费已收到事件,**不能快进未生成的未来**;队列空 → 显示「AI thinking / waiting」。

### 5.5 `qml/EventPresentationQueue.qml`(NEW,非视觉控制器)— objectName `eventQueue`

见 §6。(singleton vs instance 见 §18;默认 instance,生命周期绑 View,避免跨 run 状态残留。)

### 5.6 `qml/components/EvidenceConsole.qml`(NEW)— objectName `evidenceConsole`

见 §9。re-home 复用:`PerspectiveSwitcher`(`perspectiveSwitcher`,标签→ Seat Lens)、`ProjectionProofPanel`、`ViewBoundaryBadge`、`EventTimeline`(`eventTimeline`)、`AuditLinksPanel`(`auditLinksPanel`)、失败摘要(`providerFailureSummary`)。

### 5.7 C++ `ObserverApiClient`(MODIFY — 1 属性,薄)

- 新增 Q_PROPERTY `QVariantList projectionEvents`(NOTIFY)。`refreshProjection()` 回调里在现有 `players/proof/counts` 解析旁,把 envelope 的 `events[]`(§7 富化,递归保留嵌套 `data`)读入 `projectionEvents`;沿用同一 latest-wins serial guard。**不新增任何端点调用**(仍是 `/projection?perspective=`)。
- **Stale-data 守卫(Edit, user 2026-06-06 — Seat Lens 无残留):** `setCurrentPerspective` / `setCurrentRunId`(及任何 run 切换路径)必须**先**清空 `m_projectionEvents` 并**立即** `emit projectionEventsChanged()`,**再**触发新的 `refreshProjection()`。保证 perspective/run 切换瞬间旧 god projection 立即消失,新投影到达前 UI 取空/占位(绝不显示 stale god 数据)。
- 无新 invokable;无本地文件 I/O;无 secret。

### 5.8 后端 `observer_visibility.py`(MODIFY — projection 富化)

见 §7。`project_events()` / `build_projection_envelope()` 加法式富化可见事件的 `data.summary` + `target`,post-visibility-filter。**不改 SSE / `/events` thin 语义**(队列 board state 仍由 thin SSE 驱动;富文本只来自 projection)。

### 5.9 `qml/LiveCockpitView.qml`(RETIRE)

- 从 `navigateCockpit` **顶层导航退役**;诚实链能力 re-home 进 `EvidenceConsole`(其"数据仪表盘"能力以取证层形式存续于 Expanded 档,满足 brainstorm「不被废弃」)。**删除该文件仅允许在 `EvidenceConsole` re-home 完成且静态契约通过之后**;否则保留为**未被引用的临时 raw cockpit fallback**(不进顶层导航,仍注册于 CMake)。契约测试随之处理(§13);最终去留由 writing-plans 收口。

### 5.10 `CMakeLists.txt` / `README.md`(MODIFY)

- `qt_add_qml_module(... QML_FILES ...)` 注册 6 个新 QML(`TheaterView`、`SeatRing`、`SpeechTheater`、`PlaybackControls`、`EventPresentationQueue`、`EvidenceConsole`);`LiveCockpitView` 退役期间仍注册(retire-not-delete),仅删文件时移除其行。
- README 非目标更新:主观战面 = Theater View;仍 no Web client / no Python binding / no local artifact reads / no provider secrets。

---

## 6. Event Presentation Queue(内核,D4/D5)

**形态:** QML 非视觉控制器,`Timer` + JS ring buffer。**职责:** 接收 SSE/snapshot/一次性回放事件 → 按 `type` 分配展示时长 → 逐条消费更新舞台状态 → 支持 pause/resume/speed/instant → 发 phase boundary marker 供 seek。

**键:** 每条以 `payload.event_id`(= game-log `event_id`)/`sequence` 为键;与 `projectionEvents` 同键关联,back-fill `data.summary`/`target`。

**展示层不变量(user review 2026-06-06 锁 + Edit 强化):** 队列**可**按 `event_id`/`sequence` 去重,但**必须按 `ObserverClient.eventItems` 的 append 顺序消费 —— 不排序(no `.sort`)、不重排权威事件顺序、不合成业务事件**。若 `sequence` 回退或 source generation 改变 → **reset 或 warn,绝不 reorder**(见下 Reset 协议)。presentation-only 的 phase boundary markers 仅作 UI 标记,**不是 runtime event**,不回写后端。队列是展示节奏器,**不是第二套 game engine**。

**规范化输出 PresentationEvent(Edit, user 2026-06-06):** runtime 事件是 thin,仅作 `rawRuntime`。队列消费 `rawRuntime` 时产出**规范化 `PresentationEvent`**:`type = rawRuntime.payload.type`、`target = 匹配 projection 事件的 target`、`summary = 匹配 projection 事件的 data.summary`(并带 `event_id/sequence/round/phase/actor/visibility`)。匹配键 = `rawRuntime.payload.event_id` == projection 事件 `payload.event_id`(= game-log `event_id`)。**`eventQueue.current` 即 PresentationEvent;`SeatRing`/`SpeechTheater`/`PlaybackControls` 一律读 PresentationEvent(`current.type/target/summary`),绝不直接碰 raw runtime 字段(`payload.type` 等)。** 静态契约断言这三个组件文件不含 `.payload`。

**响应式 back-fill(P1-A,复审2):** `current` 是**计算绑定** `_present(_currentRaw)` —— 当 `enriched`(projectionEvents)**后到**时,正在展示的同 `event_id` 事件**自动重算**补上 `summary`/`target`(打字机/连线"追上"),**不靠再次 pump**。实现:队列存 `_currentRaw`(当前 raw 事件),`current` 随 `_currentRaw` 或 `_enrichedById` 变化重算;`SpeechTheater` 以 `current.event_id` 为键(summary 由空补全时显示新文本而非从头重启)。

**Reset 协议(Edit, user 2026-06-06):** run / perspective / source-generation 改变时,队列 `reset()`:清 `cursor / current(_currentRaw) / gate / waiting / consumedSeq`、`layoutPhase` 复位。配合 §5.7 的 C++ 清空 `projectionEvents`,**Seat Lens 切换期间绝无 stale current 或 stale god projection 可见**(空/占位优先于旧数据)。source-generation 改变 = `eventItems` 被换代/截断(如 perspective 切换重连后重填)或 `sequence` 回退。**TheaterView `state` 绑定 `eventQueue.layoutPhase`(非 `onPhaseBoundary` 命令式赋值,P2-D),故 reset 复位 `layoutPhase=day` 时布局立即同步,不残留 night/voting 旧态。**

**⚠️ 关键不变量(D5,user 2026-06-05 补充):** 队列弹出 `phase_change`(布局态切换)后,**必须暂停弹下一条,直到日夜布局的 QML `Transition`/`PropertyAnimation` 触发 `onStopped`**。即:phase 过渡动画 = 队列消费的硬性 gate。实现:队列暴露 `resumeAfterTransition()`,`TheaterView` 的过渡 `onStopped` 调它。

**事件展示时长预算(粗定,writing-plans 微调):**

| event type | 时长 |
|---|---|
| `role_assignment` | 1.0s(setup 揭示) |
| `werewolf_kill` / `seer_check` / `witch_*` | 1.5–2.0s(夜晚 spotlight + 连线) |
| `player_speech` | 起手 0.5s + 打字机按字数,最长 6–8s |
| `player_vote` | 1.0–1.5s(连线 + tally 累加) |
| `player_died` / `player_eliminated` / `role_revealed` | 2.0s(death/reveal) |
| `day_announcement` | 1.0s |
| `game_over` | 3.0s |
| (布局)`phase` 切换 | ≤1.5s + **gate 到 onStopped** |

**Live 防快进未来:** instant/4x 只压缩**已入队**事件的间隔;队列尾部触达「已收到的最后一条」即停,显示 waiting 态,不伪造未来。

---

## 7. Enrichment —— 视角安全的 projection 富化(后端 delta,D6)

**问题(§2.3 已核实):** SSE 与 projection 的事件只有 `payload:{event_id,type}`,无发言文本/动作摘要/target。

**方案:** 在 **projection 富化层**(已逐视角过滤)做加法式 join:

1. `build_projection_envelope()` 读取同 run 目录的 `game-log.json`(存在时),构建 `{game_log_event_id → (summary, target)}` 查找表。
2. `project_events()` 对**每条已通过可见性过滤的**事件,按 `event["payload"]["event_id"]` 命中查找表,附加 `data.summary` 与 `target`(加法式,不改既有键)。
3. **不漏保证:** join 在 `event_visible_in_projection` 过滤**之后**执行 —— god 视角得全部摘要;`role:p3`(预言家)只得它可见事件的摘要;不可见事件整条被滤掉(`hidden_event_count++`),其摘要永不进 envelope。摘要是公共/角色可见的游戏叙事文本,**非** prompt/provider 秘密(符合 `observer_visibility.py:126` 规则)。
4. `game-log.json` 缺失(live 未收口)→ 该步 no-op,事件保持 thin;**绝不抛错、绝不阻断 projection**。

**Client 消费(规范形状 = `event.data.summary` + `event.target`):** 富化后每条 projection 事件带 `data.summary`(嵌套)+ `target`(顶层)。`ObserverApiClient.refreshProjection()` 读 envelope `events[]` → `projectionEvents`(QVariantMap 递归保留嵌套 `data`);`EventPresentationQueue` 按 `payload.event_id` 关联,产出 PresentationEvent(§6),打字机"追上"时文本浮现。**spec / plan / 测试 / C++ / QML 一律以 `data.summary` + `target` 为准,不用顶层 `summary`。**

**Live 延迟边界(显式,user review 2026-06-06 降调):** `game-log.json` 收口一次性写(`run_emergent_deepseek_game.py:117`)。**故 live 进行中 P2-C-1 只保证 thin-event 驱动的舞台更新 —— phase、active seat、board/座位存活、waiting 态、连线占位;完整 `data.summary` 文本仅对 `game-log.json` 已存在的 just-finished run 保证。** 进行中 board 由 thin SSE 即时驱动(`type`+`actor` —— 高亮 active 座位/spotlight)。**有向连线 `actor→target` 需 `target`,而 target 只来自 projection 富化(game-log)—— live 未收口无 target,故 live 连线降级为 active-seat spotlight/占位,有向连线仅对 game-log 已存在的 just-finished run 保证(P1-B)。****主 P2-C-1 演示路径 = 刚跑完的 fake / 已结束 live。** 让 live 文本"即时"需引擎把 summary 写进运行时 payload 或增量 flush game-log(= P2-A 引擎改动)→ **本切片不做(§11 Scope / §16)。**

**视角安全测试(纯 `observer_visibility`,本环境可跑;P2-C-1 不新增 server-route 测试):** 断言:(a) god projection 事件带 `data.summary`(嵌套)+ `target`;(b) `role:pN` projection 只对该座可见事件带摘要,隐藏事件整条不出现(摘要不泄漏);(c) 无 `game-log.json` 时 projection 不报错且事件保持 thin;(d) envelope 仍不含 `reason_summary`/prompt/secret。

---

## 8. 三层 AI Trace

- **L1(stage):** 极简状态 + 关键动作(event `type`,如 "checks" / "votes")。
- **L2(active surface):** `data.summary`(发言文本 / "Seer p3 checks p1 → werewolf")—— 来自 §7 富化。
- **L3(点击/悬停展开):** 决策 `reason_summary`(**若**后端将来暴露;当前不在 projection)+「open in console」跳 `EvidenceConsole` Expanded → 审计工件链接(`prompt-manifest.json`/`provider-trace.json`,god/审计门控,**绝不进主舞台**)。
- **P2-C-1 默认(brainstorm 已定):** L3 内联 = `data.summary` + 审计 artifact 链接;**inline live `reason_summary` 推迟**(可选小后端字段,flag 不阻断本切片)。
- **安全边界:** `observer_visibility.py:126` —— 投影故意不返回 prompt 文本/provider 秘密;`reason_summary` 仅在 decision-log 审计工件。

---

## 9. 底部取证控制台 `EvidenceConsole`(D2/D3/D7)

**三档(按钮切换,不做自由拖拽/吸附/全屏 DevTools):**

| 档 | 高度 | 内容 |
|---|---|---|
| **Closed** | 底部细条 | `Evidence` · PASS / warning count · 当前 Seat Lens |
| **Peek** | ~28–32% 屏高 | projection summary / provider status / 最近事件(`EventTimeline`) |
| **Expanded** | ~60–70% 屏高 | Seat Lens · Projection Proof · Visible Observation · Redacted/`[ENCRYPTED]` hidden facts · raw event table · Prompt Preview / Provider Evidence 审计链 |

- **Seat Lens = 旧 `PerspectiveSwitcher`:** 切 seat 调 `currentPerspective = "role:pN"` → C++ setter 自动重 `connectStream` + `refreshProjection`(已有行为);舞台与控制台一起按新视角重投影,演示视角差。
- **Seat Lens 可逆(user review 2026-06-06 锁):** Seat Lens 重投影只影响 evidence console 与(可选)轻量伪迷雾 overlay;**退出 Seat Lens 必须把 `god` 恢复为剧场 canonical 模式**(不长期停在玩家视角,守住 D9 纯上帝默认)。**切换瞬间 C++ 清空 `projectionEvents` + 队列 `reset()`(§5.7/§6),优先空/占位,绝不显示 stale god 数据。** **`SeatRing.perspective` 单一绑定 `ObserverClient.currentPerspective` —— 绝不用 signal handler 赋值打断绑定(P1-C:否则 Back-to-God/重置失同步,伤可逆性);切 seat = 设 `currentPerspective`,ring/console 经各自绑定自动跟随。**
- **轻量伪迷雾(D7,in scope):** 不可见身份→`Unknown`/`████`;不可见夜晚动作→`[ENCRYPTED]`;不可见连线→降透明/隐藏;可见事件正常高亮。
- **重型毛玻璃/shader/噪点遮罩 = 推迟到 P2-C polish。**
- 复用诚实链组件全部 re-home 至此(§5.6);`ViewBoundaryBadge` 显示当前视角 + 合约版本 + hidden counts,持续可见的信任边界。

---

## 10. 视觉北极星 & 设计系统遵循(D10)

- **"系统运行 / 实验观察" 隐喻** —— geeky、高端。视觉解耦:游戏叙事动作(大号优雅 Sans `Theme.font.display`,极简动效)vs AI 推理/日志(小号 Monospace `Theme.font.mono` Consolas,打字机,半透明,局部浮现)。
- **暗黑剧场优先** —— 碳黑 / 极暗深空蓝(`Theme.color.bgBase`/深化);高亮极克制,只用关键阵营/动作。
- **夜晚 = 聚光 + 连线** —— 压暗非活跃座位,高亮活跃 AI + 目标;头像间细发光连线(红线 狼→猎物);瞬间扩散光环;不用弹窗。
- **token 纪律:** 只用 `Theme.color/space/radius/font/size/weight/motion/layout.*`;阵营色用 `Theme.roleAccent/roleTint/roleBorder`;`I18n.t(zh,en)` 默认中文。1px 边、克制辉光。

---

## 11. Scope fence

**In scope(P2-C-1):**
- 当前 / 刚结束 run 的剧场化观战(live 进行中,或刚跑完 fake —— SSE 一次性推完被队列慢慢演)。
- State-driven 呼吸式 theater(night/day/voting 三态 + ≤1.5s 过渡 + 队列 yield gate)。
- 底部取证控制台(诚实链 re-home + Seat Lens 重投影 + 轻量伪迷雾 + 三层 Trace 内联)。
- QML Event Presentation Queue(replay-ready 架构)+ 薄 Playback Controls。
- 视角安全的 projection 富化(后端薄 delta)+ C++ `projectionEvents` 属性。

**Out of scope(→ P3 / 后续 / polish):**
- 历史 run 列表 / 打开任意旧 run / run library / archive browser(P3-B)。
- 完整时间轴拖动 / 任意 seek / snapshot 重建。
- 从结算页跳历史复盘(P2-D / P3)。
- 重型毛玻璃 / shader / 复杂噪点遮罩(P2-C polish)。
- 让 live 动作文本"即时"的引擎改动(summary 进运行时 payload / 增量 game-log flush)。
- inline live `reason_summary`(可选小后端字段)。
- P2-B key/model 配置。

---

## 12. Allowlist(本切片可触文件)

```
src/werewolf_eval/observer_visibility.py          (projection 富化: join game-log summary, post-filter)
clients/qt_observer/src/ObserverApiClient.h       (+ projectionEvents Q_PROPERTY)
clients/qt_observer/src/ObserverApiClient.cpp      (refreshProjection 读 envelope events[])
clients/qt_observer/qml/TheaterView.qml            (new)
clients/qt_observer/qml/components/SeatRing.qml    (new)
clients/qt_observer/qml/components/SpeechTheater.qml (new)
clients/qt_observer/qml/components/PlaybackControls.qml (new)
clients/qt_observer/qml/EventPresentationQueue.qml (new)
clients/qt_observer/qml/components/EvidenceConsole.qml (new)
clients/qt_observer/qml/AppShell.qml               (navigateCockpit → TheaterView)
clients/qt_observer/qml/LiveCockpitView.qml         (retire from nav; delete only after re-home + tests green, else keep unreferenced)
clients/qt_observer/CMakeLists.txt                  (注册新 QML)
clients/qt_observer/README.md                       (非目标更新)
tests/test_observer_visibility.py                   (富化 + 视角安全断言)
tests/test_qt_observer_static_contract.py           (新文件/objectName/re-home/CMake)
docs/superpowers/specs/2026-06-06-p2-c-1-theater-view-design.md
historical harness plan 2026-06-06--p2-c-1-theater-view-plan.md
```

---

## 13. Testing & verification

**后端(可在本环境跑的纯单元):**
- `tests/test_observer_visibility.py`(MODIFY)—— §7 富化的 4 条断言(god 带 summary / role:pN 不漏 / 缺 game-log 不报错 / 仍无 reason_summary·secret)。`project_events`/`build_projection_envelope` 是纯函数,**可在本环境跑**(对照 server 路由的 localhost 限制)。
- **P2-C-1 不新增 server-route 测试**(避免 allowlist/env 冲突):projection 富化全部由纯 `observer_visibility` 单元测试覆盖(本环境可跑)。既有 server-route 测试不在本切片范围,仍 env-blocked,**不声称由本切片 authored**。

**Qt 静态契约(`tests/test_qt_observer_static_contract.py`,MODIFY):**
- `REQUIRED_QML_VIEWS` 加 6 新 QML(`TheaterView`、`SeatRing`、`SpeechTheater`、`PlaybackControls`、`EventPresentationQueue`、`EvidenceConsole`)。**`LiveCockpitView.qml` 条目在文件仍存在时保留**(retire-not-delete);仅当 re-home 完成 + 契约绿后删文件时,才移除其条目。
- `REQUIRED_OBJECT_NAMES`:**新增**键 —— TheaterView→`theaterView`、SeatRing→`seatRing`、SpeechTheater→`speechTheater`、EvidenceConsole→`evidenceConsole` + re-home 的 `eventTimeline/perspectiveSwitcher/auditLinksPanel/providerFailureSummary`、PlaybackControls→`playbackControls`、EventPresentationQueue→`eventQueue`。**`LiveCockpitView.qml` 键随文件保留**(其 objectName 仍在该未引用文件内 → 契约自然绿);删文件时一并移除该键。玩家显示由 SeatRing 的 `seatRing` 承接(`playerPanelGrid` 不再要求于顶层导航)。
- 独立诚实链组件文件(`PerspectiveSwitcher.qml`/`AuditLinksPanel.qml`/`ViewBoundaryBadge.qml`/`ProjectionProofPanel.qml`)**自身 objectName 与注册不变**,仅被 `EvidenceConsole` 复用;`QtObserverCockpitContractTests` 里键于这些**组件文件**的断言(`PerspectiveSwitcher` 9 视角值、`AuditLinksPanel` 审计 chip)**保持绿不动**。
- **EvidenceConsole re-home 强校验(Edit, user 2026-06-06):** 断言 `EvidenceConsole.qml` **自身文本**实例化 `ViewBoundaryBadge`/`ProjectionProofPanel`/`PerspectiveSwitcher`/`EventTimeline`/`AuditLinksPanel` 且含 `objectName:"providerFailureSummary"`。**不得**由保留的 `LiveCockpitView.qml` 顶替满足 re-home —— 断言键定在 `EvidenceConsole.qml` 文件上。
- CMake 注册测试覆盖新文件。
- 禁词扫描保持绿(新组件**不得**含 `events.jsonl`/`snapshots/`/`QFile`/`QDir`/local-file URL scheme/`werewolf_eval`/secret 标记);新组件无本地文件 I/O。
- `QtObserverProjectionClientTests`:加断言 client 暴露 `projectionEvents`,且 `setCurrentPerspective`/`setCurrentRunId` **清空 `m_projectionEvents` 并 notify**(stale 守卫,§5.7)。
- **队列契约(Edit):** 断言 `EventPresentationQueue.qml` 含 `function reset`(Reset 协议)、含 `_present`(PresentationEvent 规范化)、**不含 `.sort(`**(append-order 消费,§6);断言 `SeatRing/SpeechTheater/PlaybackControls` 三文件**不含 `.payload`**(只读 PresentationEvent)。
- README 断言随非目标更新同步。

**Qt 构建 / 运行时 / 视觉(本环境可跑,见 memory `qt-observer-build-verify`):**
- `cmake --build .tmp/qt-observer-build --target appqt_observer` exit 0(qmlcachegen AOT = 语法门)。
- `ctest`(SSE 解析等)绿;`qmllint` 只看 `Error:`。
- **视觉:** 临时 `Timer` 驱动 `TheaterView` 走 night→day→voting 三态 → `grabToImage` → PNG → Read 确认:夜晚环聚光+连线、白天发言剧场打字机、唱票 tally、底部三档控制台。**视觉 harness 必须喂真实 runtime 形状的 thin 事件(`payload:{event_id,type}`)+ 独立 `projectionEvents`(带 `data.summary`/`target`),不得用预合并的 rich fake 事件 —— 以真实数据契约驱动 PresentationEvent 规范化(Edit)。** **并覆盖两个场景:(i) source 先到、projection 后到 → 占位先现、文本/连线随后"追上"(验响应式 back-fill,P1-A);(ii) night→reset→day → 布局随 `layoutPhase` 绑定即时复位(验 P2-D)。** 事后移除 harness。

---

## 14. Acceptance criteria

- **A1.** `navigateCockpit()` 进入 `TheaterView`(objectName `theaterView`);`LiveCockpitView` 退役;诚实链在 `EvidenceConsole` 内可见。
- **A2.** `TheaterView` 随 `phase` 在 night/day/voting 三态呼吸式重组,过渡 ≤1.5s;**过渡进行中队列不弹下一条**(D5 可观测:harness 断言过渡未停时无新事件渲染)。
- **A3.** `EventPresentationQueue` 按 §6 时长逐条消费;Pause/1x-4x/Instant/next-phase/queue-end 生效;live 不快进未来,队列空显示 waiting。
- **A4.** god 视角下 `SeatRing` 显示全部真角色 + 夜晚连线;Seat Lens 切 `role:pN` 后舞台 + 控制台一致重投影,轻量伪迷雾生效(`Unknown`/`████`/`[ENCRYPTED]`)。
- **A5.** `SpeechTheater` 打字机呈现 `data.summary`(**just-finished run 保证完整;live 进行中按 §0/§7 口径仅占位/淡入,不算失败**);三层 Trace 内联 L1/L2 + L3 跳控制台审计链。
- **A6.** projection 富化(规范形状 `event.data.summary` + `event.target`):god `events[]` 带摘要;`role:pN` 不漏隐藏摘要;缺 `game-log.json` 不报错;仍不含 prompt/`reason_summary`/secret(`tests/test_observer_visibility.py` 绿;**P2-C-1 不新增 server-route 测试**)。
- **A7.** C++ `projectionEvents` 暴露且 latest-wins;`setCurrentPerspective`/`setCurrentRunId` 立即清空并 notify(stale 守卫);`EventPresentationQueue` 按 `payload.event_id` 关联产出 PresentationEvent。
- **A8.** 静态契约测试更新且绿;Qt 构建 exit 0;`ctest` 绿;视觉抓图确认三态。
- **A9.** 无本地文件 I/O、无 secret、无新端点、无新依赖;引擎(P2-A)一行不改;SSE/`/events` thin 语义不变。
- **A10.** 队列产出规范化 **PresentationEvent**(`type`=raw `payload.type`、`target`/`summary`=匹配 projection 的 `target`/`data.summary`);`SeatRing/SpeechTheater/PlaybackControls` 只读 PresentationEvent(三文件无 `.payload`);队列**按 append 顺序消费、无 `.sort(`**。
- **A11.** run/perspective 切换:C++ 清空 `projectionEvents` + 队列 `reset()`;Seat Lens 切换期间无 stale god projection / stale current(空/占位优先)。
- **A12.** 响应式 back-fill(P1-A):`current` 是计算绑定,projection 后到时正在展示事件自动补 `summary`/`target`(不 re-pump);live 有向连线需 target → 仅 just-finished,live = active-seat spotlight(P1-B)。
- **A13.** reset 同步布局:`TheaterView.state` 绑定 `eventQueue.layoutPhase`(P2-D);`SeatRing.perspective` 单一绑定 `currentPerspective`,绝不 handler 赋值(P1-C)。

---

## 15. 引擎事件词汇(P2-C 渲染依据,核对自 `emergent_engine.py`)

| phase | event type | visibility | 渲染 |
|---|---|---|---|
| setup | `role_assignment` | public | 环揭示真角色 |
| night | `werewolf_kill` | werewolf_team | 红线 狼→猎物 + spotlight |
| night | `seer_check` | seer | 预言家→目标连线 + 结果 |
| night | `witch_save`/`witch_kill`/`witch_pass` | witch | 救/毒/弃权 spotlight |
| night | `player_died` | all | 座位压暗+划除 |
| day | `player_speech` | public | 打字机发言(`data.summary`) |
| day | `player_vote` | public | 投票连线 + tally |
| day | `day_announcement` | public | 公布 |
| day | `player_eliminated` | all | 出局 |
| day | `role_revealed` | all | 揭示角色 |
| game_end | `game_over` | all(actor=winner team) | 终局 |

- 每事件:`{event_id, sequence, round, phase, type, actor, target, visibility, data:{summary, visible_info_refs}}`(富事件,内存→game-log)/ 运行时 payload 仅 `{event_id, type}`(SSE/projection 源)。
- 决策:`decision_log` 含 `reason_summary`(`reason[:200]`)、`visible_info_refs` —— **审计工件,非投影**。
- 审计 artifacts:`prompt-manifest.json`、`provider-trace.json`(god 门控,经 `AuditLinksPanel` 链接)。

---

## 16. Decisions surfaced during spec-writing(请 user review)

> 以下是 brainstorm 后、写 spec 时基于源码核实**新浮现**或需 user 拍板的点。**全部已在 2026-06-06 user review 拍板(见下);本节保留作决策记录。**

1. **Enrichment 需后端薄改动(已确认,非"无改动")。** NOTES §10-2 的"待确认"已核实:projection/SSE **不带** summary,故 §7 后端 join **进入 P2-C-1 scope**(加法式、视角安全、缺 game-log 不报错)。这是唯一后端改动,不碰引擎。**✅ user 同意。**
2. **Live 动作文本有延迟(收口后补齐),非即时。** 因 `game-log.json` 收口一次性写。主演示路径(刚跑完 fake)不受影响。让 live 即时 = 引擎改动,已划出 scope(§11/§16)。**✅ user 接受延迟,并要求在 §0/§7/A5 显式降调(已落)。**
3. **`LiveCockpitView.qml`:从导航退役,不强制删文件(✅ user 拍板,改 §5.9)。** 删除仅在 `EvidenceConsole` re-home 完成 + 静态契约绿后允许;否则留作未引用的临时 raw cockpit fallback。
4. **配色沿用既有 token(D10)**:现有 seer=amber #FBBF24 / witch=purple #A855F7,与 brainstorm 北极星措辞(预言家 indigo、女巫 fluo-green)**不一致**。默认沿用既有(改共享 token 会波及 setup 视图 RoleCard)。若要 brainstorm 那套,作为**全局 Theme token 调整**单独确认(可放 P2-C polish)。
5. **`EventPresentationQueue` = instance(默认)vs singleton。** NOTES 提"单例/控制器";本 spec 默认 instance(生命周期绑 View,防跨 run 残留)。最终 writing-plans 定。

---

## 17. Open risks / writing-plans 细化项

- **打字机 vs 队列计时的协调:** `speech_text` 时长按字数,需与 back-fill 文本到达时机解耦(文本未到 → 占位/淡入,到达 → 续打)。writing-plans 定状态机。
- **富化 join 的 event_id 一致性:** 运行时 `payload.event_id` 必须 == game-log `event_id`(已核实 `_emit` 同源 `evt["event_id"]`);加测试钉住。
- **三态过渡的 yield gate 实现细节:** 队列 `resumeAfterTransition()` 与多个并发 `PropertyAnimation` 的 `onStopped` 协调(取最后一个/用 `ParallelAnimation` 单 `onStopped`)。
- **Live 重拉 projection 的频率:** 每新 seq 重拉 vs 节流;latest-wins guard 已防错序,但需防抖避免请求风暴。
- **伪迷雾与 god 默认的交互:** god 视角无迷雾;仅 Seat Lens 启用;确保切换即时且无闪烁。

---

## 18. Next steps

1. **Spec self-review**(本节已并入 §16/§17:placeholder/一致性/scope/歧义已扫)→ 提交 user review。
2. user approve → 调 **writing-plans** 出实现计划 `historical harness plan 2026-06-06--p2-c-1-theater-view-plan.md`(严格 TDD:后端富化先行 + 视角安全测试;Qt 组件逐个建 + 静态契约同步 + 视觉门)。
3. 删除 `docs/superpowers/specs/2026-06-05-p2-c-1-theater-view-NOTES.md`(已被本 spec supersede)。

