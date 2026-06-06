# P2-D 结算/战报画面(一镜到底 morph + 中轴脊椎联动)— Design Spec

**Status:** draft — pending user review(brainstorm 2026-06-06 完成,含可视化伴侣 5 屏迭代);approve 后转 writing-plans,尚未实现。
**Route:** `docs/PROJECT_MAP.md` → P2(观战式 AI-vs-AI 对局客户端)/ 模块 D(结算画面)。
**Date:** 2026-06-06
**Depends on(复用,不推倒):** P1-A 评分/归因原语(`scoring.py`/`attribution.py`)、P1-D observer 协议 + 本地 server(`observer_server.py`/`observer_protocol.py`/`observer_visibility.py`)、P2-C-1 剧场 Qt 座舱(`TheaterView.qml`、`SeatRing.qml`、`Theme.qml`/`I18n.qml`、C++ `ObserverApiClient`)。

> 一句话:**对局结束不切页面,而是一镜到底地把剧场舞台 Z 轴拉远停靠成左侧"活指示器",右侧展开会随滚动联动 scrub 的深度战报。** 结算画面**就是** P3 评测/复盘的入口外壳;P2-D 只建到「战报」深度,但把**评测就绪的数据契约**与**可向内加深的 UI 骨架**定死,使 P3 = 加字段/加区块,而非重写。

---

## 0. Goal

把对局结束那一刻从"剧场安静下来亮个药丸"(P2-C-1 现状)升级为**有仪式感的结算 + 有内核的战报**:胜负揭晓、全员翻牌、关键转折点、核心指标,并以**一镜到底的空间形变**(定格高光 → Z 轴拉远停靠 → 推演台展开)登场;右侧长复盘与左侧"残局沙盘"经**单一 cursor 真值源**联动 scrub。

**Success criteria**

- 对局到达终态(`status==completed|failed` 且事件队列放完)→ 自动进入结算的「定格高光」拍;点「查看深度战报」→ morph 到「推演台展开」态。**全程同一视图内的状态机过渡,绝非 StackView 整页切换。**
- 右侧战报随滚动驱动单一 `cursorIndex`;左侧停靠沙盘 + 中轴脊椎是纯 Observer(property binding),cursor 一变即联动到对应 round-phase 的盘面/节点。
- 结算数据 = **server 端按 run 产出的 `game-log.json` + `decision-log.json` 跑 `score_game` + `attribute_game` 生成的"评测就绪 settlement bundle"**;懒计算 + 落盘缓存(`settlement-bundle.json`),对刚跑完与历史 run 一致可用。
- **优雅降级:** 谢幕层(胜负/翻牌/存活/残局沙盘)只依赖 `game-log.json`,恒可用;战报层(转折点/核心分)若评分失败 → `degraded` 标记 + 战报面板显"数据不可用",**绝不阻断、绝不报错**。
- 结算 = 上帝全揭(game over → 全部真相),bundle 仍 secret-free(无 prompt/provider 文本/路径)。
- P2-D 只建到战报深度;逐人记分卡全表、过程指标全表、逐人行为/理由长分析、胜率曲线、AI 复盘侧栏 = **P3 在同一 bundle 加字段、同一滚动联动加锚点段**(§11)。
- Qt 静态契约测试更新且绿;Qt 构建 exit 0;`ctest` 绿;视觉抓图确认三拍 morph + 滚动联动 + 历史直入。

---

## 1. Product framing(locked,brainstorm 2026-06-06)

- **结算 ≠ 独立于评测/复盘的另一块。** 按 PROJECT_MAP,「结算画面**就是** P3 评测/复盘的入口」。三者是**同一张会生长的画面的不同深度**:
  - **结算/战报(P2-D)** = 最外层外壳:胜负、翻牌、转折点、核心分。每局必看的收尾屏。
  - **评测/复盘(P3-A)** = 在同一张画面**向内展开**:逐人记分卡、全过程指标、逐人行为/理由分析。读**同一 bundle 的更多字段**。
  - **历史(P3-B)/榜(P3-C)** = 围绕同一份 bundle 做保存/跳转/聚合。
- **因此 P2-D 的活有一半是"把契约定对"**:`settlement-bundle.json` 的形状 = P3 防返工的核心资产(§5)。
- **深度选型(brainstorm 三方向):** 选 **B·战报**(胜负+翻牌+转折点+核心指标),否 **A·谢幕**(太薄,无评测内核)、否 **C·复盘台**(把 P3 的逐人记分卡全表/全指标提前做 = 越界,且 `decision_quality_score` 正向评分尚未真接,见 §15)。
- **登场形态(brainstorm 进阶 + 4 屏迭代):** **一镜到底 Z 轴景深 morph**,否「StackView 整页切换」(那是 morph 的返工陷阱,§4 D4)。
- **空间(brainstorm 终态 v2):** **28% sticky 左(拍扁的状态指示器)+ 中轴竖向脊椎时间轴 + 72% 滚动战报**。否「左 44%」(喧宾夺主)、否「时间轴底部横置」(与右侧垂直瀑布认知割裂)、否「沙盘顶部横置」(拍扁了上帝视角空间感)。

---

## 2. Current state(已逐一核对源码 / 探查报告 2026-06-06)

### 2.1 评分链原语(P1-A,可被 server 程序化调用)

- `scoring.py` `score_game(game: GameLog, decision_log: DecisionLog | None = None, ...) -> ScoreLog`(`scoring.py:651`):纯函数,无 CLI 壁垒。`ScoreRecord` 含 `outcome_score`[-3,3] / `rule_integrity_score`{-3,0} / `decision_quality_score`[-2,2] / `rules_triggered` / `evidence_event_ids`(`scoring.py:50-58`)。
- `MetricsSummary`(`scoring.py:91-102`):`result_metrics{winner, game_length, margin, *_survival_rate}` + `process_metrics{vote_accuracy_by_player, survival_rounds, seer_metrics, witch_metrics, team_metrics, contradiction/info_leak counts}` + `score_summary{player_outcome_scores, team_outcome_scores, player_rule_integrity_scores, player_decision_quality_scores}`。
- `attribution.py` `attribute_game(game: GameLog, score_log: ScoreLog, metrics: MetricsSummary) -> AttributionResult`(`attribution.py:266`):产 `turn_points[]`(每条 `{turn_point_id, rule_id, round, subject, description_template(中文), impact_score{1.0|2.0}, impact_sign, evidence_event_ids}`,`attribution.py:19-78`)+ `top_attribution{turn_point_id, description_template, selection_policy}`。
- **关键:** 三者都是纯函数,`observer_server` 同包可直接 import 调用(`src/werewolf_eval`)。**结算 bundle = 这三步的输出裁剪。**
- **`decision_quality_score` 现状(诚实标注):** 正向评分需 saved S5 语义标签;live 涌现 run **无** saved 标签 → `decision_quality_score` 恒 0。bundle 仍带此字段(契约位),但 **P2-D UI 不 headline 它**(§15)。

### 2.2 对局结果与终局状态(恒可用,谢幕层数据源)

- `GameLog.result`(`game_log.py:42-56`):`{winner: "villager"|"werewolf", end_round, survivors[], end_condition}`。
- `MetricsSummary.result_metrics.margin`:胜方存活 − 负方存活。
- `final_god_view.json` 快照(game_end 态):`players[]{player_id, role, team, alive}` + `alive_players[]` —— 全员真实身份揭晓。
- **这些只依赖 `game-log.json`(+ 终局快照),恒存在 ⇒ 谢幕层永不降级。**

### 2.3 Observer server 已暴露 / 缺口(决定后端 delta)

- 终态:`status ∈ {completed, failed}`;failed 带 `reason`(`budget_exhausted|provider_failure`)(`observer_protocol.py:54-60,275-303`)。run-detail(`observer_server.py:392-395`)、artifacts 列表(`:398-401`)、artifact 原文(`:404-417`,**不做 perspective 过滤**)、snapshots(`:353-373`)。
- `ALLOWED_ARTIFACTS`(`observer_protocol.py:31-40`):`events.jsonl / game-log.json / decision-log.json / consensus-log.json / prompt-manifest.json / provider-trace.json / failure-audit.json / resolved-profile.json`。**当前不含 `score-log` / `metrics-summary` / `attribution` / `settlement-bundle`** ⇒ 涌现 run 跑完**无人算分**,这是 P2-D 后端 delta 的根因。
- **server 启动的是什么(已核实):** 默认 `default_fake_launcher`(`observer_server.py:66-67`)→ G1h `run_fake_runtime`(产 `game-log.json` + `decision-log.json`);live 走 `deepseek_launcher.py`→ G1c consensus runner(同样产 game-log + decision-log)。**两条现役 launcher 都产出评分链所需的 game-log + decision-log ⇒ bundle 计算可行。**
- **⚠️ 预存在缺口(不属本切片):** observer **尚未接 P2-A 涌现引擎**(`emergent_engine.py` 的 `run_emergent_game.py` 是独立 CLI,server 不 import)。结算只消费"这一局产出的 artifact",无论它来自 fake / G1c / 将来的涌现接线 ⇒ **「涌现→observer」接线 = 另一任务,见 §11 out-of-scope。**

### 2.4 P2-C-1 剧场 Qt 座舱(复用 / 薄扩展)

- `AppShell.qml` `StackView`(`navigateCockpit()` replace 进 `TheaterView`);`HistoryView` 已有历史/回放。
- `TheaterView.qml:30-35`:`_runOver = currentStatus==="completed"||"failed"`;`_statusText` 在 run over + `eventQueue.atEnd` 时显"对局结束"。**当前无任何结算 UI —— 舞台原地安静。** ⇒ 结算挂在这个 hook 点。
- `SeatRing.qml`:呼吸式 6 座环,每座真角色(`Theme.roleAccent`)/alive-dead/active 高亮/连线层;读 `playerItems` + `eventQueue.current`。**P2-D 给它加 `layoutMode`(§5.3)实现 ring↔docked 无缝形变。**
- `EventPresentationQueue.qml`:`atEnd` = cursor 到尾;已有 seek 能力(`seek respects the phase gate` 提交、HistoryView 回放)。**结算不复用 live 队列**(队列是 live 播放节奏器);结算是 post-game 静态、滚动驱动,board 状态走 bundle 的 `board_timeline`(§5,D10),与队列解耦。
- `Theme.qml`:faction tokens(狼 #EF4444 / 预言家 #FBBF24 / 女巫 #A855F7 / 村民 #60A5FA / 猎人 #34D399)、`statusColor("completed")` #60A5FA、`space/radius/font/motion/layout` token、`AppCard/StatusBadge/AppButton/GlowDot/AppBackground` 等可复用组件。
- C++ `ObserverApiClient`:`currentRunId/currentStatus/currentPerspective/playerItems/...` + invokables `openRun/connectStream/refreshProjection/...`。**P2-D 加 1 属性 `settlementBundle` + 1 invokable `fetchSettlement`(§5.7)。**

---

## 3. Architecture

### 3.1 组件拓扑(新建 vs 复用)

```
TheaterView.qml(P2-C-1,MODIFY:加结算 overlay 层 + SeatRing.layoutMode 驱动)
  │  run terminal + eventQueue.atEnd  ──触发──►  SettlementView 激活(同视图内 overlay,非 StackView 切页)
  │
  └─ SettlementView.qml(新, objectName "settlementView")  ── morph 三拍状态机 + 单一 cursorIndex 真值源
       ├─ (复用)SeatRing.qml(MODIFY:+ layoutMode = theater | docked,座位位置可动画)  ← 左 28% 停靠"活指示器"
       ├─ SettlementSpine.qml(新)   中轴竖向时间轴:round-phase 节点 + 随滚动滑的 cursor 指示器
       ├─ SettlementReport.qml(新)  右 72% Flickable 长战报:胜负头 + 转折点段(锚点)+ 核心指标 + P3 加挂位
       └─ WinnerBanner.qml(新)      第一拍"定格高光"横幅(谢幕仪式)

数据层(复用,薄扩展):C++ ObserverApiClient + 新 Q_PROPERTY settlementBundle / invokable fetchSettlement。
后端:observer_server 加 GET /api/runs/{id}/settlement(懒算-或-缓存)+ settlement bundle builder(纯函数)。
```

### 3.2 数据流(单一 cursor 真值源)

```
run terminal(completed/failed)+ eventQueue.atEnd
   │
   ▼  SettlementView 激活
ObserverClient.fetchSettlement(runId) ──► GET /api/runs/{id}/settlement
                                              │ server: 有缓存→读 settlement-bundle.json;无→ score_game+attribute_game 算→落盘→返回(懒、幂等)
                                              ▼
                                       settlementBundle(新 Q_PROPERTY)
                                              │  result / players[] / turning_points[] / top_attribution / core_metrics / board_timeline[]
        ┌──────────────────────────────────────┼──────────────────────────────────────┐
        ▼                                       ▼                                      ▼
SettlementReport(右滚动)              SettlementSpine(中轴)                SeatRing layoutMode=docked(左)
  各段挂 cursor_index 锚点              节点 = board_timeline round-phase         渲染 board_timeline[cursorIndex]
  Flickable.contentY → 命中可见段       cursor 指示器 obs cursorIndex            (alive/dead/highlight)
  ──写──► cursorIndex                  点节点 ──写──► cursorIndex                 ── obs cursorIndex(纯 binding)
        └──────────────► cursorIndex(SettlementView 唯一可写 state)◄──────────────┘
```

- **单一真值源 `SettlementView.cursorIndex`(int,board_timeline 索引)。** 写者只有两个:右侧 scroll-spy、脊椎点选。读者:SeatRing(docked)、Spine 指示器、Report 高亮 —— 全是 property binding 的 Observer,无回环。
- **防反馈环:** 脊椎点选 = 设 `cursorIndex` + 程序化 `positionViewAtIndex` 滚动;该程序化滚动用 `_programmaticScroll` 闸防止 scroll-spy 反向再写 `cursorIndex`(标准 scroll-sync guard)。
- **结算是 post-game 静态:** bundle 一次拿全;无 SSE 增量、无 live 队列、无富化时序问题(对照 P2-C-1 §7 的 live 延迟)。

### 3.3 一镜到底 morph 三拍(D4/D7)

| 拍 | 状态 | 舞台 | 战报区 | 说明 |
|---|---|---|---|---|
| **第一拍 定格高光** | `freeze` | 剧场环压暗,聚光打在胜方座位,`WinnerBanner` 砸下 | 隐 | 保住谢幕仪式感;自动触发(run over) |
| **第二拍 Z 轴拉远** | `docking` | `SeatRing.layoutMode: ring→docked`,座位从环位**飞向** 28% 左列紧凑排布(`morphProgress` 0→1 插值),整体 scale 缩小 | 淡入开始 | 点「查看深度战报」触发;一镜到底 |
| **第三拍 推演台展开** | `report` | docked 沙盘钉死满高(状态指示器) | 脊椎 + 长战报滑出,scroll-sync 全激活 | 终态;可滚动/点节点/回看/去历史 |

- 过渡走 `Theme.motion` 预算的 `SequentialAnimation`/`ParallelAnimation`。
- **历史直入(无第一拍):** 从 History 打开已结束 run → `SettlementView` 初始 `state="report"`,直接落到展开态(沙盘 docked、无 freeze 仪式)。
- **morph 机制(D7):** SeatRing 的座位是 `Repeater` 项,其 `x/y` 绑定 `layoutMode` + 可动画 `morphProgress`(环坐标 ↔ docked 网格坐标插值)。**同一组座位元件位置插值 = 真·一镜到底**,非"环淡出/网格淡入"的 cross-fade。景深虚化(`MultiEffect` blur)/ 聚光辉光 shader = **二期 polish 叠加层,本切片不做**。

---

## 4. Locked decisions

| # | 决策 | 选择 | 理由 |
|---|---|---|---|
| D1 | 结算深度 | **B·战报**(胜负+翻牌+转折点+核心分);**否 C 复盘台全表** | B 有评测内核又不越界;C 是 P3 的活,且 `decision_quality` 未真接。P2-D 定契约,P3 加深同一面。 |
| D2 | 结算数据谁算/何时 | **server 端懒算-或-缓存** `settlement-bundle.json`,由 `game-log + decision-log` 跑 `score_game`+`attribute_game` | Python owns engine/eval 地基;单一数据源;懒算幂等 → 刚跑完与历史 run 一致可用;Qt 只读。 |
| D3 | 失败处理 | **优雅降级**:谢幕层只靠 game-log 恒可用;战报层评分失败 → `degraded` 标记,面板显"不可用",不阻断 | live/涌现 mismatch(§15)不能让整屏炸;谢幕仪式永远在。 |
| D4 | 登场形态 | **一镜到底 morph**(三拍,同视图状态机);**否 StackView 整页切换** | 整页切换是 morph 的返工陷阱(必须同面状态过渡才能形变);原生客户端渲染优势,上下文不丢失。 |
| D5 | 空间切分 | **28% sticky 左指示器 + 中轴竖脊椎 + 72% 滚动战报** | 左侧只是状态指示器,认知重心在右;sticky 满高消灭"短侧栏塌陷";脊椎与右侧瀑布同轴。 |
| D6 | 联动机制 | **单一 `cursorIndex` 真值源**;scroll-spy + 脊椎点选写,沙盘/脊椎/高亮纯 binding 读;程序化滚动闸防环 | 地道 QML 响应式;三者解耦无回环。 |
| D7 | morph 实现 | **SeatRing `layoutMode` ring↔docked,座位位置插值**(真形变);blur/glow polish 推迟 | 一镜到底用同元件位置插值,非 cross-fade;polish 是叠加层,防过度工程。 |
| D8 | 结算视角 | **上帝全揭**(game over → 全部真相),无 per-seat 伪迷雾;bundle 仍 secret-free | 谢幕的意义就是全翻牌;无 prompt/provider 文本进 bundle(守 secret 边界)。 |
| D9 | 时间轴形态 | **中轴竖向脊椎(Solution 2)**;否顶部横置(Solution 1) | 竖脊椎与右侧垂直瀑布同轴、零认知割裂;顶部横置拍扁上帝视角空间感。 |
| D10 | cursor 锚定数据 | **server 计算 `board_timeline[]`**(每 round-phase 一项)放进 bundle;结算与 live `EventPresentationQueue` 解耦 | 结算是静态 post-game,预算 board 状态比挂 live 队列更稳更简单;cursor = board_timeline 索引,单真值源。 |
| D11 | 设计系统 | 沿用 `Theme.*` token / faction 色 / 复用 P2-C 组件;charcoal 剧场;`I18n.t(zh,en)` | 与剧场一致;不改共享 token 波及 setup;中文默认。 |

---

## 5. Settlement Bundle 契约(P2-D 核心交付物 · P3 防返工资产)

> **`settlement-bundle.json`(`bundle_version:"p2d.settlement.v1"`)= server 端从 `game-log.json` + `decision-log.json` 裁剪自 `score_game`+`attribute_game`+`game.result`。P3 = 在此**加字段**(逐人行为/理由、全过程指标、胜率曲线…),**不改既有键**。

```jsonc
{
  "bundle_version": "p2d.settlement.v1",
  "run_id": "...", "game_id": "...",
  "degraded": false, "degraded_reason": null,   // 评分失败时 true + 原因;此时下面 scoring 派生字段为空/null

  // —— 谢幕层(只靠 game-log,恒可用,degraded 时仍齐全)——
  "result": {
    "winner": "villager",                        // game.result.winner
    "end_round": 3, "end_condition": "all_werewolves_eliminated",
    "survivors": ["p1","p4","p6"],
    "margin": 2,                                  // metrics.result_metrics.margin(degraded 时可由 game-log 重算或 null)
    "source_label": "[DeepSeek API output]"       // 诚实链:live vs deterministic
  },
  "players": [                                   // 翻牌 + 逐人核心分(P3 在每项加 behavior/reasoning)
    { "player_id": "p1", "role": "seer", "team": "villager", "alive": true,
      "outcome_score": 5, "rule_integrity_score": 0, "decision_quality_score": 0 }   // decision_quality 现状恒 0(§2.1)
    // ...
  ],

  // —— 战报层(靠评分链;degraded 时为空/null,UI 显"不可用")——
  "core_metrics": {                              // P2-D 精选小集;P3 读 metrics-summary 全量
    "game_length": 3, "margin": 2, "mvp_player_id": "p1",   // mvp = 最高 outcome_score
    "villager_survival_rate": 0.66, "werewolf_survival_rate": 0.0
  },
  "top_attribution": {                           // attribution.top_attribution
    "turn_point_id": "...", "description": "第 2 轮 2-1 处决 p1 是本局村民获胜的直接关键转折点。"
  },
  "turning_points": [                            // attribution.turn_points → 右侧战报的"段"
    { "turn_point_id": "...", "round": 2, "phase": "day",
      "title": "2-1 处决 p1(狼)", "description": "...",      // description ← description_template
      "impact_score": 2.0, "impact_sign": "positive_for_villager",
      "evidence_event_ids": ["..."],
      "cursor_index": 3 }                        // 指向 board_timeline 项 → scroll-sync 锚点
    // ...
  ],

  // —— cursor 锚定层(server 从 game-log 预算,sticky 左沙盘按 index 渲染)——
  "board_timeline": [                            // 每 round-phase 节点一项;脊椎节点 = 这些
    { "cursor_index": 0, "round": 1, "phase": "night", "label": "第1夜",
      "alive_player_ids": ["p1","p2","p3","p4","p5","p6"],
      "changed": [ { "player_id": "p3", "change": "died" } ],
      "highlight": { "actor": "p2", "target": "p3", "kind": "werewolf_kill" } }
    // ...一直到 game_end
  ]
}
```

- **`board_timeline` 构建(纯函数,从 game-log 事件):** 顺序遍历 `game-log.events`,按 `(round, phase)` 分组,逐组结算 `alive_player_ids` / `changed`(本组死亡/出局)/ `highlight`(代表性 actor→target 动作)。**只用 game-log,恒可算 ⇒ 即使 `degraded` 也有 board_timeline + 谢幕层。**
- **P3 加深契约(锁):** P3 仅**新增**键 —— `players[].behavior_analysis` / `players[].reasoning_chain`、`process_metrics`(全表)、`win_rate_curve`、更多 `turning_points`。既有键语义冻结。
- **Secret 边界:** bundle **不含** prompt 文本、provider 秘密、本地绝对路径、`reason_summary`(那是 decision-log 审计工件)。只有结果/分数/中文叙述。

---

## 6. 后端 delta(observer_server,薄)

### 6.1 settlement bundle builder(纯函数,新)

- 新 `src/werewolf_eval/settlement_bundle.py`:`build_settlement_bundle(game: GameLog, decision_log: DecisionLog | None) -> dict`。
  1. 恒先建谢幕层(`result` + `players` 翻牌 + `board_timeline`)—— 只用 `game`。
  2. `try`: `score_log = score_game(game, decision_log)` → metrics → `attribute_game(...)` → 填 `core_metrics` / `top_attribution` / `turning_points` / `players[].*_score`。
  3. `except`(评分/归因抛错,如 decision-log 缺失、事件词汇 mismatch §15):`degraded=true` + `degraded_reason`,战报层留空,**返回仍有效的谢幕 bundle**。
- **纯函数 ⇒ 本环境可单测**(对照 server 路由的 localhost 限制,memory `werewolf-env-network-test-limits`)。

### 6.2 端点 + 缓存(observer_server / observer_protocol)

- `GET /api/runs/{run_id}/settlement`:run 终态时,有 `settlement-bundle.json` 缓存 → 读返回;无 → 读 `game-log.json`(+`decision-log.json`)→ `build_settlement_bundle` → **落盘 `settlement-bundle.json`** → 返回。**懒、幂等、确定性。** 非终态 run → 409/`{pending:true}`(client 不渲染战报)。
- `settlement-bundle.json` 加入 `ALLOWED_ARTIFACTS`(`observer_protocol.py:31-40`)⇒ 也可经 artifact 路由取/审计。
- **不改 SSE / `/events` / `/projection` / 引擎 / scoring 公式 / validators。** 唯一新增 = 1 路由 + 1 builder 模块 + 1 artifact 名。

---

## 7. Qt 组件清单

> 命名遵循既有 camelCase objectName;字符串走 `I18n.t(zh, en)`;只用 `Theme.*` token;charcoal 剧场;视图根 `Item` 不 `anchors.fill`(由父定尺寸)。

### 7.1 `qml/SettlementView.qml`(NEW)— objectName `settlementView`

- morph 三拍状态机宿主;持有 `cursorIndex`(唯一可写真值源)、`state ∈ {freeze, docking, report}`。
- `Component.onCompleted` / 激活:`ObserverClient.fetchSettlement(currentRunId)`;`settlementBundle` 到达后构建 spine 节点 / report 段 / docked 沙盘数据。
- live 入口:由 `TheaterView` 在 `_runOver && eventQueue.atEnd` 时挂起激活,初始 `state="freeze"`。历史入口:初始 `state="report"`(§3.3)。
- 三拍过渡 `Transition`/`SequentialAnimation`(`Theme.motion` 预算)。
- `degraded` 时:谢幕层(banner/沙盘/存活)正常;战报面板(转折点/核心指标)渲染 `EmptyState`「战报数据生成失败 · 仅显示对局结果」。

### 7.2 `qml/components/WinnerBanner.qml`(NEW)— objectName `winnerBanner`

- 第一拍横幅:`result.winner` 阵营色大字 + `end_round` + `margin` + `source_label`(诚实链)。`Theme.statusColor`/`roleAccent`。docking 后缩为战报头(或交给 `SettlementReport` 头部,二选一由 writing-plans 定)。

### 7.3 `qml/components/SeatRing.qml`(MODIFY,P2-C-1 既有)— + `layoutMode`

- 新增 `property string layoutMode: "theater"`(`theater` | `docked`)+ 可动画 `property real morphProgress`。座位 `Repeater` 项 `x/y` = `layoutMode/morphProgress` 插值(环坐标 ↔ docked 紧凑网格坐标);整体 `scale` 随 morph 缩小。
- **docked 模式数据源切换:** `layoutMode==="docked"` 时,座位 alive/dead/highlight **读 `settlementBundle.board_timeline[cursorIndex]`**(纯 binding,Observer),**不读** live `eventQueue.current`。`theater` 模式行为不变(P2-C-1 回归保护)。
- 复用既有 `Theme.roleAccent` / alive-dead 压暗 / active 高亮。docked 紧凑排布(3×2 量级,6 座);**有向连线(vote line / 中毒特效)= 二期 polish**,本切片 docked 只显 alive/dead + cursor 命中座位高亮。

### 7.4 `qml/components/SettlementSpine.qml`(NEW)— objectName `settlementSpine`

- 中轴竖向时间轴:`Repeater` over `board_timeline`(round-phase 节点,`label`)。
- `cursor` 指示器位置 = `cursorIndex` 的纯 binding(Observer);节点点击 → `settlementView.setCursor(index)`(写真值源 + 触发程序化滚动)。
- 脊椎固定满高,变的是滑动的 cursor 指示器(D6)。

### 7.5 `qml/components/SettlementReport.qml`(NEW)— objectName `settlementReport`

- 右 72% `Flickable`/`ListView`:胜负头 + `turning_points` 段(每段挂 `cursor_index`)+ `core_metrics` 面板 + **P3 加挂占位段**。
- **scroll-spy:** `contentY`/当前可见 item index → 命中段的 `cursor_index` → `settlementView.cursorIndex = ...`(唯一写路径之一)。
- **程序化滚动闸:** 脊椎点选触发的 `positionViewAtIndex` 期间置 `_programmaticScroll`,scroll-spy 跳过回写(D6 防环)。
- 长文本横向充足(72% 不折行);`core_metrics` 用 `AppCard` 小卡(margin / MVP / 天数 / 存活率)。

### 7.6 C++ `ObserverApiClient`(MODIFY — 1 属性 + 1 invokable,薄)

- 新增 `Q_PROPERTY(QVariantMap settlementBundle ... NOTIFY)`。
- 新增 `Q_INVOKABLE void fetchSettlement(QString runId)`:`GET /api/runs/{id}/settlement` → 解析进 `settlementBundle`(递归保留嵌套 `result/players/turning_points/board_timeline`)→ notify。沿用既有 latest-wins serial guard 思路;`pending` 响应 → 保持空 + 可重试。
- **run 切换清空:** `setCurrentRunId` / 离开结算 → 清 `m_settlementBundle` 并 notify(防 stale)。
- 无本地文件 I/O;无 secret;无新依赖。

### 7.7 `qml/TheaterView.qml`(MODIFY)/ `AppShell.qml` / `HistoryView.qml`

- `TheaterView`:`_runOver && eventQueue.atEnd` → 激活 `SettlementView` overlay(同视图内,**非 navigateXxx 切页**);SeatRing 交给 SettlementView 驱动 `layoutMode`。
- `HistoryView`:已结束 run 加「查看战报」affordance → 打开 `SettlementView`(初始 `report` 态)。**薄**:复用同一 `fetchSettlement`,不做历史列表深化(P3-B)。
- `AppShell`:若 `SettlementView` 作为独立可导航视图(vs TheaterView 内 overlay)由 writing-plans 定;**默认 overlay-in-theater 以保 morph 同面**(§17)。

### 7.8 `CMakeLists.txt` / `README.md`(MODIFY)

- 注册新 QML(`SettlementView`、`WinnerBanner`、`SettlementSpine`、`SettlementReport`)。
- README 非目标更新:结算 = 一镜到底战报;仍 no Web client / no Python binding / no local artifact reads / no provider secrets。

---

## 8. 视觉北极星 & 设计系统遵循(D11)

- **延续剧场 charcoal 美学**:碳黑底、faction 色克制高亮、1px 边、克制辉光。
- **左指示器拍扁不抢戏**:28% sticky;座位小、信息只到 alive/dead/cursor 高亮;底部一行胜负小结。
- **中轴脊椎 = 整页脊柱**:与右侧瀑布同轴;cursor 圆环滑动用 `Theme.motion` 缓动。
- **右战报深呼吸**:72% 横向充足;转折点段 `AppCard`,关键转折用 `statusColor`/`roleAccent` 高亮;核心指标小卡。
- **token 纪律**:只用 `Theme.color/space/radius/font/size/weight/motion/layout.*` + `roleAccent/roleTint/roleBorder`;`I18n.t(zh,en)` 默认中文。
- **morph 缓动**:三拍走 `Theme.motion` 预算;blur 景深 / 聚光辉光 = 二期。

---

## 9. Scope fence

**In scope(P2-D):**
- 后端:`build_settlement_bundle` 纯函数 + `GET /api/runs/{id}/settlement`(懒算-或-缓存)+ `settlement-bundle.json` artifact;优雅降级。
- Settlement bundle 契约 v1(result / players-core / core_metrics / top_attribution / turning_points / board_timeline)。
- Qt:`SettlementView`(三拍 morph + 单一 cursor)、`SeatRing` docked layoutMode(无缝形变 + board_timeline 渲染)、`SettlementSpine`(竖脊椎 scrubber)、`SettlementReport`(滚动 + scroll-sync)、`WinnerBanner`。
- C++ `settlementBundle` 属性 + `fetchSettlement` invokable。
- 入口:剧场 run-over 自动激活 + 历史「查看战报」薄入口。
- 测试 + 视觉抓图。

**Out of scope(→ P3 / 后续 / polish):**
- 逐人记分卡全表、过程指标全表、`decision_quality` 正向评分接入(C·复盘台 / P3-A;bundle 带核心分作契约,UI 不建全表)。
- 逐人行为/理由长分析段、胜率波动曲线、AI 智能复盘侧栏(P3-A,同 bundle 加字段 + 同 scroll-sync 加锚点段)。
- 历史 run 列表深化 / run library / 真实排行榜(P3-B/C)。
- **接「P2-A 涌现引擎 → observer」**(预存在缺口 §2.3,另任务)。
- **修 `emergent_engine` 的 `witch_kill` vs scorer `witch_poison` 事件词汇 mismatch**(§15;属 P2-A,结算遇评分失败已 `degraded` 兜底)。
- morph 重型 polish:景深虚化(`MultiEffect` blur)、聚光辉光 shader、vote-line / 中毒特效微动画。
- P2-B key/model 配置。

---

## 10. Allowlist(本切片可触文件)

```
src/werewolf_eval/settlement_bundle.py              (new: build_settlement_bundle 纯函数)
src/werewolf_eval/observer_server.py                (+ GET /api/runs/{id}/settlement 懒算-或-缓存)
src/werewolf_eval/observer_protocol.py              (+ settlement-bundle.json 入 ALLOWED_ARTIFACTS)
clients/qt_observer/src/ObserverApiClient.h          (+ settlementBundle Q_PROPERTY + fetchSettlement)
clients/qt_observer/src/ObserverApiClient.cpp        (fetchSettlement 实现 + run 切换清空)
clients/qt_observer/qml/SettlementView.qml           (new)
clients/qt_observer/qml/components/WinnerBanner.qml   (new)
clients/qt_observer/qml/components/SettlementSpine.qml (new)
clients/qt_observer/qml/components/SettlementReport.qml (new)
clients/qt_observer/qml/components/SeatRing.qml       (MODIFY: + layoutMode/morphProgress + docked board_timeline 渲染)
clients/qt_observer/qml/TheaterView.qml              (MODIFY: run-over 激活 SettlementView overlay)
clients/qt_observer/qml/HistoryView.qml              (MODIFY: 「查看战报」薄入口)
clients/qt_observer/qml/AppShell.qml                 (按 §17 决定:overlay vs 可导航)
clients/qt_observer/CMakeLists.txt                   (注册新 QML)
clients/qt_observer/README.md                        (非目标更新)
tests/test_settlement_bundle.py                      (new: builder 纯单元 + 降级 + secret-free)
tests/test_qt_observer_static_contract.py            (新文件/objectName/契约)
docs/superpowers/specs/2026-06-06-p2-d-settlement-screen-design.md
docs/harness/plans/2026-06-06--p2-d-settlement-screen-plan.md
```

---

## 11. Testing & verification

**后端(纯单元,本环境可跑;对照 server 路由 localhost 限制):**
- `tests/test_settlement_bundle.py`(NEW),断言:
  - (a) 正常 run(game-log + decision-log)→ bundle 含 `result/players(翻牌+核心分)/core_metrics/top_attribution/turning_points/board_timeline`;`mvp_player_id` = 最高 `outcome_score`;`turning_points[*].cursor_index` 命中合法 `board_timeline` 项。
  - (b) **降级**:decision-log 缺失 / 评分抛错 → `degraded=true` + `degraded_reason`,但 `result/players(翻牌)/board_timeline` 仍齐(谢幕层不塌)。
  - (c) **board_timeline 只靠 game-log 可算**:无 decision-log 也产出完整 round-phase 序列 + alive/dead。
  - (d) **确定性**:同输入两次产出逐字节一致。
  - (e) **secret-free**:bundle 不含 prompt / provider 秘密 / 绝对路径 / `reason_summary`。
- **不新增 server-route 测试**(localhost HTTP env-blocked,memory `werewolf-env-network-test-limits`):路由是 builder 的薄包装,由 builder 纯单测覆盖。

**Qt 静态契约(`tests/test_qt_observer_static_contract.py`,MODIFY):**
- `REQUIRED_QML_VIEWS` / 注册:加 `SettlementView`、`WinnerBanner`、`SettlementSpine`、`SettlementReport`;`SeatRing` 仍在。
- `REQUIRED_OBJECT_NAMES`:`settlementView` / `winnerBanner` / `settlementSpine` / `settlementReport`(+ `seatRing` 保留)。
- **单一 cursor 真值源契约:** 断言 `cursorIndex` 的可写定义只在 `SettlementView.qml`;`SettlementSpine`/`SeatRing`(docked)/`SettlementReport` 对 cursor 的渲染**经 binding 读**;`SettlementReport` 含 scroll-spy 写路径 + `_programmaticScroll` 闸标识(防环)。
- **SeatRing 回归 + 模式契约:** 断言 `SeatRing.qml` 含 `layoutMode`;`theater` 路径仍读 `eventQueue.current`、`docked` 路径读 `settlementBundle.board_timeline`。
- **client 契约:** `ObserverApiClient` 暴露 `settlementBundle` + `fetchSettlement`;`setCurrentRunId` 清空 `m_settlementBundle` 并 notify。
- 禁词扫描绿:新组件**不得**含 `events.jsonl`/`snapshots/`/`QFile`/`QDir`/`file://`/`werewolf_eval`/secret 标记;无本地文件 I/O。
- README 断言随非目标更新同步。

**Qt 构建 / 运行时 / 视觉(本环境可跑,memory `qt-observer-build-verify`):**
- `cmake --build .tmp/qt-observer-build --target appqt_observer` exit 0(qmlcachegen AOT = 语法门)。
- `ctest` 绿;`qmllint` 只看 `Error:`。
- **视觉:** 临时喂一份 fake `settlementBundle`(真实契约形状,含多 round-phase `board_timeline` + 多 `turning_points`)→ `grabToImage` → PNG → Read 确认:
  - (i) 三拍 morph:freeze 横幅 → docking 座位飞向左列 → report 展开;
  - (ii) **scroll-sync**:程序滚 `SettlementReport` 到某转折段 → docked 沙盘 alive/dead 切到对应 `cursor_index`、脊椎 cursor 滑到该节点;
  - (iii) **历史直入**:初始 `report` 态、无 freeze 仪式、沙盘 docked;
  - (iv) **degraded**:bundle `degraded=true` → 谢幕层正常 + 战报面板 `EmptyState`。
  - 事后移除 harness。

---

## 12. Acceptance criteria

- **A1.** run 终态 + `eventQueue.atEnd` → 自动入 `freeze` 拍(`WinnerBanner` + 聚光);点「查看深度战报」→ `docking`→`report`,**全程同视图状态机,无 StackView 切页**(harness 断言无 `navigateXxx` 调用)。
- **A2.** `SeatRing.layoutMode` ring↔docked 座位位置插值形变;`theater` 模式行为不变(P2-C-1 回归);`docked` 模式座位渲染 `board_timeline[cursorIndex]`。
- **A3.** 单一 `cursorIndex` 真值源:右侧 scroll-spy 与脊椎点选写;沙盘/脊椎/高亮纯 binding 读;程序化滚动不引发回环(harness:点脊椎节点后无抖动二次跳)。
- **A4.** settlement bundle 契约 v1 完整(`result/players/core_metrics/top_attribution/turning_points/board_timeline`);`turning_points[*].cursor_index` 合法;`mvp_player_id` = 最高 outcome_score。
- **A5.** **优雅降级**:评分失败 → `degraded` + 谢幕层(胜负/翻牌/存活/沙盘/board_timeline)齐全、战报面板显"不可用",**不报错不阻断**(`tests/test_settlement_bundle.py` 覆盖)。
- **A6.** 后端懒算-或-缓存:首次 GET 算并落 `settlement-bundle.json`,二次读缓存;同输入确定性一致;非终态 run 返回 pending(client 不渲染战报)。
- **A7.** 历史入口:已结束 run「查看战报」→ `SettlementView` 初始 `report` 态、沙盘 docked、无 freeze。
- **A8.** 结算 = 上帝全揭,无 per-seat 伪迷雾;bundle secret-free(无 prompt/provider/路径/`reason_summary`)。
- **A9.** C++ `settlementBundle` 暴露 + `fetchSettlement`;run 切换清空并 notify(无 stale)。
- **A10.** 静态契约测试更新且绿;Qt 构建 exit 0;`ctest` 绿;视觉抓图确认 §11 四场景(morph / scroll-sync / 历史直入 / degraded)。
- **A11.** 无本地文件 I/O、无 secret、无新依赖;**引擎(P2-A)一行不改、scoring 公式/validators 不改、SSE/`/events`/`/projection` 语义不变**;唯一后端新增 = 1 builder + 1 路由 + 1 artifact 名。
- **A12.** P3 加深契约:bundle 既有键语义冻结,P3 仅新增键(spec §5 记录,作为 P3 入场依据)。

---

## 13. 引擎事件词汇(board_timeline / turning_points 渲染依据,核对自 `emergent_engine.py` / G1h)

| phase | event type | board_timeline 渲染 |
|---|---|---|
| setup | `role_assignment` | 初始全员 alive |
| night | `werewolf_kill` | highlight 狼→猎物;changed 猎物 died |
| night | `seer_check` | highlight 预言家→目标(查验) |
| night | `witch_save`/`witch_kill`/`witch_pass` | highlight 女巫动作(§15 词汇注意) |
| night | `player_died` | changed died |
| day | `player_vote` / `day_announcement` | highlight 票型 / 公布 |
| day | `player_eliminated` | changed eliminated |
| day | `role_revealed` | 翻牌 |
| game_end | `game_over` | 终局 + 全员翻牌(谢幕) |

---

## 14. Decisions surfaced during spec-writing(请 user review)

1. **morph 同面要求 → 结算挂 `TheaterView` overlay(非独立 StackView 视图)。** 一镜到底需同视图状态过渡;若作独立可导航视图则无法形变。默认 overlay-in-theater;`AppShell` 是否另给独立入口由 writing-plans 定(§17)。**待 user 确认默认 overlay 取向。**
2. **`SeatRing` 增 `layoutMode` = 给 live 组件加结算职责。** 为真·一镜到底(座位位置插值)选择扩展既有 SeatRing 而非新建沙盘 cross-fade。代价:SeatRing 责任变重。回退:若插值形变成本高,降级为 docked 独立 `SettlementSandbox` + cross-fade(§17 风险)。**待 user 认可"扩 SeatRing"取向。**
3. **`decision_quality_score` 现状恒 0(无 S5 saved 标签)。** bundle 带此契约字段,但 P2-D UI 不 headline。P3 接入 live 语义标注才有正向分。**记录,无需拍板。**
4. **结算独立于 live `EventPresentationQueue`(D10):** board 状态走 bundle `board_timeline`(server 预算),不挂 live 队列 cursor。更稳更简单,但意味着"两套 board 状态来源"(live=队列、结算=board_timeline)。两者都最终源自 game-log 事件,语义一致。**记录。**
5. **历史入口深度:** P2-D 只给「查看战报」薄 affordance 复用 `fetchSettlement`;历史列表深化属 P3-B。**记录。**

---

## 15. Open risks / writing-plans 细化项

- **`witch_kill` vs `witch_poison` 词汇 mismatch(探查报告):** `emergent_engine.py` 发 `witch_kill`,`scoring.py` 期望 `witch_poison`。**当前 observer 未接涌现引擎**(§2.3),现役 G1h/G1c launcher 的事件词汇需 writing-plans 核对;若 mismatch 触发评分失败 → §6.1 降级兜底已覆盖(不炸),但战报层会空。修词汇属 P2-A,不在本切片。**writing-plans 核对现役 launcher 实际事件词汇 vs scorer 期望。**
- **`metrics-summary` builder 入口:** §2.1 经探查为 `score_game` 流程内构建;`build_settlement_bundle` 需确认调用面(直接函数 vs 经 `score_game` 返回)。**writing-plans 核对 `scoring.py` 实际导出面。**
- **座位 ring→docked 位置插值:** `Repeater` 项坐标如何同时支持环排布与紧凑网格并平滑插值;`morphProgress` 驱动两套坐标 lerp。可能需 `Behavior on x/y` + 显式坐标函数。**writing-plans 定状态机。**
- **scroll-spy 防环细节:** `positionViewAtIndex` 触发的 `contentY` 变化与用户滚动区分;`_programmaticScroll` 闸的清除时机(动画 `onStopped`)。
- **board_timeline 粒度:** round-phase 节点是否够细(一个 night 多个动作合一节点 vs 拆细)?默认每 (round,phase) 一节点,`highlight` 取代表性动作;若需逐动作 scrub 留 P3。**writing-plans 定粒度。**
- **bundle 缓存失效:** run artifact 理论不变(终态),`settlement-bundle.json` 落盘后恒缓存;若 builder 逻辑迭代,旧缓存需带 `bundle_version` 校验/重算。

---

## 16. Next steps

1. **Spec self-review**(placeholder / 一致性 / scope / 歧义已扫,见 §14/§15)→ 提交 user review。
2. user approve → 调 **writing-plans** 出实现计划 `docs/harness/plans/2026-06-06--p2-d-settlement-screen-plan.md`(严格 TDD:后端 `build_settlement_bundle` 纯单测先行 + 降级路径;Qt 组件逐个建 + 静态契约同步 + 视觉门四场景)。
3. 同步 `docs/PROJECT_MAP.md` P2-D 行状态(轮廓 → 进行中)与 `docs/TASKS.md`。
