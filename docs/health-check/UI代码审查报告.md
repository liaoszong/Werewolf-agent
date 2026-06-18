# Qt/QML UI 全页面代码审查报告

> **Closeout 状态更新（2026-06-18）**：本报告现在兼作下一轮 UI 债务路由。当前结论不是“所有审查项逐条清零”，而是 **UI 冻结所需的 Critical / High 可用性与信任感问题已经收口；Medium / Low 中的结构债、可靠性债、视觉债保留为后续计划项**。

## 0. Closeout 状态表

### 已修复 / 冻结可收口

| 项 | 状态 | 说明 |
|---|---|---|
| H1 History `timeFilter` 死 UI | 已修 | 已接入时间过滤，近期提交包含 `fix(qt): wire history time filter`。 |
| H2 perf harness 残留 | 已处理 | 后续报告确认无 instrumentation / harness 残留；不再作为 UI 冻结阻断项。 |
| H3 `replace()` 导航重建卡顿 | 已修 | 已改为 push/pop 方向并补 stale-data 风险处理；近期提交包含 `perf(qt): preserve navigation state and reduce image decode cost`。 |
| H4 i18n 硬编码 | 已修主要项 | i18n/debug/dead-code 清理已完成，按 UI 冻结口径视为收口；若后续发现零散边角字符串，另按低风险 polish 处理。 |
| M3 `ModeControl` 死三元 | 已修 | 已并入小 polish。 |
| L1 `console.log` 残留 | 已修 | 已并入小 polish。 |

### 暂缓 / 下一轮候选

| 项 | 状态 | 为什么没修 |
|---|---|---|
| M1 硬编码颜色 token 清洗 | 暂缓 | 量大，容易造成视觉回归，不阻断当前 UI 冻结。 |
| M2 `ProviderSettingsView` 预览假数据混真实页 | 暂缓 | 属于产品信息架构问题，不是小 bug。 |
| M4 SSE 自动重连 | 暂缓 | 属于可靠性 plan，需要先设计重连策略。 |
| M5 History 批量删除串行 | 暂缓 | 大批量才明显，且需要并发/接口策略。 |
| L2 `ConfirmDialog` 风格割裂 | 暂缓 | 纯视觉一致性问题。 |
| L3 Theme 四套 palette 并存 | 暂缓 | 文档/设计债，不影响当前使用。 |
| L4 `EventPresentationQueue` 全表重扫 | 暂缓 | 需要 profiler 证据，不能凭感觉改。 |

> 下文保留原始审查证据和修复方向，便于追溯问题来源；各项当前状态以上方表格和标题状态标记为准。

## 1. 总评

**当前 UI 代码整体风险等级:中等。核心架构(竞态防护、安全边界、objectName 契约)扎实,无阻断性 bug,不建议立即停工修;但有一批 High 级维护性债务和一处中英/死 UI 问题建议尽快收口。**

值得肯定的设计(本轮未发现问题的部分,先记正面):
- **竞态防护是教科书级**:`ObserverApiClient` 对 projection/settlement/profile/validate 各有独立 `requestSerial` 单调递增 + 回调内 `if (serial != m_xxxSerial) return;`(latest-wins),`m_pendingOpenRunId` 防 openRun 竞态,SSE `stopStream()` 有 re-entrancy 注释(先 null 再 abort,防 SIGSEGV)。
- **安全边界完全合规**:BYO-key 走 `CredentialStore`(QSettings 本地存),QML 拿不到 raw key 只有 `maskedCredential()`,sync 经 POST body(不放 URL/header),错误信息只派生 HTTP status / network error enum,不含 key/response body;`hasSecretLikeContent()` 还对导出配置做 secret 扫描。
- **objectName 静态契约全部完好**:`tests/test_qt_observer_static_contract.py` 断言的所有 objectName 在当前 QML 中全部存在,UI 重构**未破坏任何契约或导航边界**。
- **client-agnostic 边界严格**:Qt 仅经 `ObserverApiClient`(REST/SSE)拿数据,无任何直接读 `.runs`/Python 内部/artifact path 的旁路。
- **EventPresentationQueue 不变量严谨**:presentation-only、de-dup by event_id、不 reorder/sort、票数/死亡按游标截断(绝不显示未来票),有 sequence regression 检测和 source truncation 检测自动 reset。

**不立即修也能用**,但下列 Critical/High 项应在下一个 polish plan 里收口。此处为原始审查结论，当前 closeout 状态见第 0 节。

---

## 2. 发现列表(分级)

### Critical
> 无。未发现阻断性 bug、安全泄露、契约破坏或会导致崩溃/数据错误的缺陷。

---

### High

#### H1 — HistoryView `timeFilter` 是死 UI(下拉框改属性,但过滤器从不读它)【已修】
- **文件/位置**:`qml/HistoryView.qml` — `timeFilter` 声明(L29)、`timeCombo` 下拉框(L1026-1039)、`_matchFilters()`(L423-433)、`_filteredRuns()`(L435-461)
- **问题**:用户切换"全部时间/最近创建/较早档案"下拉框,`onActivated` 写入 `root.timeFilter`,但 `_matchFilters()` 只读 `searchText/activeFilter/executionFilter/resultFilter`,**从不读 `timeFilter`**。整个文件只有声明和赋值两处引用,无任何过滤逻辑消费它。
- **证据**:`_matchFilters` 函数体(L423-433)无 `timeFilter` 分支;L29 注释自承 `// placeholder until API exposes dates`。
- **影响**:功能欺骗——用户以为在按时间范围筛选,实际无任何效果,降低信任;且数据其实已具备(`_extractRunTimestamp` 已用于排序)。
- **修复方向**:要么在 `_matchFilters` 加 `timeFilter` 分支(用已算出的 timestamp 做 recent/older 阈值),要么删掉这个下拉框。
- **是否本轮小修**:需另开 plan(涉及筛选语义定义:recent/older 的阈值口径)。

#### H2 — 工作树有一套常驻 perf harness 未提交,与 DESIGN.md「临时 harness 必须 diff 前删除」冲突【已处理】
- **文件/位置**:`qml/AppShell.qml`(`_perfNav`/`_perfNextStep`/`perfStepTimer`/`perfStartTimer`/`perfSettleTimer`/`Qt.quit()`,L15-321)、`src/ObserverApiClient.cpp/h`(`perfNavEnabled`/`perfLog`/`WW_QT_PERF` HTTP 日志,未提交 diff)、`main.cpp`(`--perf-nav` flag,未提交 diff)
- **问题**:工作树存在 12 个未提交改动,核心是一套**性能测量 harness**:`--perf-nav` CLI 启动后,AppShell 自动跑 16 步导航序列并 `perfLog` 每步耗时,跑完 `Qt.quit()`;同时 C++ 在每个 HTTP get/post 写 `PERF_HTTP` 日志。DESIGN.md 明确写「Temporary screenshot harnesses may use local Timer + grabToImage(), but they must be removed before final diff」——这套 harness 虽由 flag/env 门控(正常用户流程不触发),但它**常驻在 AppShell 导航壳层和 C++ 请求路径里**,不是临时截图 harness 那种用完即删。
- **证据**:`git diff --stat` 显示 main.cpp/+6、ObserverApiClient.cpp/+20、AppShell.qml/+177 等未提交;AppShell L312-316 `Qt.quit()` 在 perf 模式跑完 16 步后触发。
- **影响**:(a) 给审查和后续维护者制造困惑(壳层里混入自动导航+退出逻辑);(b) 每个 HTTP 请求都多一次 env 查询 + 条件日志判断(虽轻);(c) 未提交状态本身是流程债——这套改动应要么提交、要么剥离。
- **修复方向**:确认这套 perf harness 的归宿——若作为长期可测量性能基线保留,应正式提交 + 文档化(写进 skill/README,说明 `--perf-nav` 用法);若只是一次性体检,应从 AppShell/C++ 剥离,改为外部脚本驱动。
- **是否本轮小修**:需另开 plan(归属决策 + 提交或剥离)。

#### H3 — 导航全用 `stackView.replace()`,每次切换销毁重建页面,状态全丢 + 重复请求【已修】
- **文件/位置**:`qml/AppShell.qml` — 所有 `navigateXxx()` → `_replaceView()` → `stackView.replace(component)`(L323-367);各页 `Component.onCompleted`
- **问题**:7 个页面全用 `replace`(非 push/pop)。每次导航(含「返回」)都销毁当前页、重建目标页,导致:
  - HistoryView 每次进入重跑 `ObserverClient.refreshRuns()`(L13),`selectedRunId`/`activeFilter`/`_selected`/`searchText` 全部回到默认——用户在历史页选了筛选+选中某局,切到设置页再返回,**筛选和选中全丢**。
  - MatchSetupView 每次进入重跑 `refreshProfileSchema`/`refreshProfiles`/`refreshCapabilities` + 遍历 `syncCredentialToServer`(L89-97),`editedProfile`/`selectedSeatId`/`currentConfigId` 全丢——用户排了一半的座位配置,切走再回全部清空。
  - ProviderSettingsView 每次进入 `loadProviderIntoForm()`(L411 onSelectedProviderChanged 触发),`selectedSection` 回到 `"ai"`、`selectedProvider` 回到 `"deepseek"`。
- **证据**:AppShell L325 `stackView.replace(component)`;HistoryView L13 `Component.onCompleted: ObserverClient.refreshRuns()`;MatchSetupView L89-97 onCompleted 三连请求;ProviderSettingsView L411 `onSelectedProviderChanged: loadProviderIntoForm()`。
- **影响**:UX 退化(返回后状态错乱/选中丢失/旧数据闪现后重新加载);重复 API 请求;返回卡顿感(重建整页)。这是「页面返回状态恢复」问题的根因。
- **修复方向**:三选一——(a) 关键页面状态(筛选/选中/编辑中的 profile)上提到 AppShell 或单例 store,replace 后恢复;(b) 高频往返页(设置↔配置)改用 `StackView.push/pop` 保留实例;(c) Loader + `active` 缓存实例而非销毁。
- **是否本轮小修**:需另开 plan(导航架构调整,影响多页)。

#### H4 — i18n 大量硬编码残留,中英切换不彻底【已修主要项】
- **文件/位置**(按严重度):
  - `qml/HistoryView.qml`:L1388/L1677 `text: "Run ID: " + ...`(英文前缀不切换)、L1546/L1627 `text: "档"`(硬编码中文占位)、以及 `_statusLabel`/`_templateLabel`/`_timeLabel`/`_endTimeLabel`/`_durationLabel`/`_resultLabel`/`_versionLabel`/`_shortRunId` 等helper 中约 10 处 `return "Unknown"` 未走 I18n(这些值会喂给用户可见 Text)。
  - `qml/ProviderSettingsView.qml`:L563 `text: "Werewolf"`、L1200 `text: "API Key"`、L1251 `text: "Base URL"`(标签不切换)、L311 `modelCountText` EN 分支 `count + " models"` 不走 I18n.t。
  - `qml/components/SeatEditorPanel.qml`:L604 `text: "Temperature"`、L682 `text: "Max Tokens"`。
  - `qml/components/NavRail.qml`:L64 `text: "狼人杀 · 观察席"`(中英都写死中文,不随 lang 变)、L72 `text: "WEREWOLF OBSERVER"`。
  - `qml/AppShell.qml`:L96 `text: "WEREWOLF OBSERVER"`。
  - `qml/components/EvidenceConsole.qml`:L277 `text: "R" + ...`、L310 `text: "AI · " + reason`。
- **问题**:项目有统一 `I18n.t(zh, en)` 路径,但重写后多处漏接。切到英文后这些位置仍显示中文/英文固定值。
- **证据**:上述行号;NavRail L64 在中英模式下都显示「狼人杀 · 观察席」。
- **影响**:中英切换不彻底,英文模式出现中文残留/反之,专业度下降;helper 的 `"Unknown"` 在英文模式显示英文、中文模式也显示英文(未本地化)。
- **修复方向**:逐一改走 `I18n.t()`;helper 的回退值统一用 `I18n.t("未知","Unknown")`。
- **是否本轮小修**:H4 中「单文件零散字符串补 I18n.t」部分**可本轮小修**(低风险,不改逻辑);但 HistoryView helper 局部化需测试验证,建议并入小 plan。

---

### Medium

#### M1 — 硬编码颜色字面量绕过 Theme token(46 处,集中在重写页)【暂缓】
- **文件/位置**:`MatchSetupView.qml`(15 处,最严重)、`SeatEditorPanel.qml`(8)、`ProviderSettingsView.qml`(7)、`SeatCard.qml`(4)、`HistoryView.qml`(3,Qt.rgba 渐变 L622-624)、`ParchmentComboBox.qml`(2,含 `Qt.rgba(1, 248/255, 234/255, ...)` 反复出现)、`PlaybackBar.qml`(2)、`HomeView.qml`(2,含 tarot 卡 `#3a2a16` L403)
- **问题**:DESIGN.md 明确「Add one-off color literals when a Theme token exists → Don't」。重写页大量用 `Qt.rgba(1, 248/255, 234/255, 0.32)`(高光描边)、`Qt.rgba(48/255,32/255,18/255,0.18)`(木影)、`#c6785f`/`#c8735b`(赤陶 hover,与 `Theme.parchment.terracotta` 重复)等裸值,而非 `Theme.parchment.*`/`Theme.warm.*`。`ProviderSettingsView.qml` L242-248 的 `providerAccent()` switch 里 `#5db8a6`=`Theme.warm.accentTeal`、`#a9583e`=`Theme.warm.primaryActive` 是重复定义。
- **证据**:Explore agent 统计:Theme.qml 外共 ~46 处;MatchSetupView L472/567/640/653/663/672/741/863/870/877/883/894/903。
- **影响**:维护性——改配色要全文搜替换;视觉一致性风险(同类色微漂移);与 DESIGN.md 冲突。
- **修复方向**:抽 token。高光描边 `Qt.rgba(1,248/255,...)` 建议加 `Theme.parchment.highlightLine`;木影已有 `Theme.parchment.woodShadow`;赤陶 hover 用 `Theme.parchment.terracotta`/`terracottaDeep`。
- **是否本轮小修**:需另开 plan(量大,且每处需视觉核对防回归)。

#### M2 — ProviderSettingsView 大量「预览/即将推出」假数据混在真实凭证页里【暂缓】
- **文件/位置**:`qml/ProviderSettingsView.qml` — `usageLedgerData`(L58-66,假 "182K"/"$3.42")、`usageChartBars`(L68,假柱状图)、`providerPreviewStats`(L70-84,假价格表)、`modelPreviewRows`(L86-111)、`sectionPreviewCards`(L113-142)、`previewProviderCatalog`(L53-56,Bedrock/Cohere)、`settingsSections` 里 7/8 标了 `preview: true`(L27-34)
- **问题**:设置页把**真实凭证管理**(deepseek/openai 等 BYO-key)和**纯预览假数据**(用量账本、预算护栏、per-provider 价格、Bedrock/Cohere 预览连接器)混在同一页。8 个设置分区里 7 个是 preview,只有 "ai" 是真实功能。假数据虽标了 "Preview" pill,但用量账本的 "$3.42"/"182K" 等具体数字可能被用户误读为真实账单。
- **证据**:L58-66 静态假数据;L1871 文案自承 `此页面已完成样式与导航接线;未标明真实功能的控件暂不调用后端 API`;previewNotice L2053-2072。
- **影响**:认知混淆(假数字混真实功能);维护负担(假数据散落文件头部,未来接真实字段时要逐处替换);页面臃肿(2146 行)。
- **修复方向**:预览分区单独抽到 `PreviewSettingsView` 或折叠隐藏,只保留真实凭证页;假数据移到独立 data 模块便于未来替换。
- **是否本轮小修**:需另开 plan(信息架构调整)。

#### M3 — ModeControl Live 段 label 是死代码三元【已修】
- **文件/位置**:`qml/components/ModeControl.qml` L58-59
- **问题**:`label: root.liveAvailable ? I18n.t("实战", "Live") : I18n.t("实战", "Live")` —— 三元运算两边完全相同,永远显示「实战/Live」。看似本想 liveAvailable 时换文案,但两分支一样。
- **证据**:L58-59 逐字相同。
- **影响**:无功能 bug(显示正常),但是死代码,误导维护者以为有分支逻辑。
- **修复方向**:直接改为 `label: I18n.t("实战", "Live")`;若原意是 liveAvailable=false 时显示别的(如「锁定」),补回差异化。
- **是否本轮小修**:**可本轮小修**(一行)。

#### M4 — SSE 流断开后无自动重连【暂缓】
- **文件/位置**:`src/ObserverApiClient.cpp` — `onStreamFinished`(L595-603)、`onStreamError`(L605-615)
- **问题**:SSE 流结束/出错时只置 `m_connected=false` + emit,无重连逻辑。若观战中服务端临时断流(网络抖动、server 重启),UI 静默停止更新,显示「离线」但不恢复;只有用户手动返回再进入对局(TheaterView onCompleted 重新 connectStream)才能恢复。
- **证据**:`onStreamFinished` 无 reconnect;TheaterView L20-24 仅在 onCompleted 且 `!ObserverClient.connected` 时 connectStream。
- **影响**:长时间观战的鲁棒性——直播对局中途断流后需手动操作恢复。
- **修复方向**:加退避重连(指数退避,限次),或在 `connected` 变 false 时由 TheaterView 触发定时重连;注意要与 perspective/run 变化的 reset 协调,避免重连风暴。
- **是否本轮小修**:需另开 plan(重连策略 + 与现有竞态防护协调)。

#### M5 — HistoryView 批量删除串行执行,无并发,大批量慢【暂缓】
- **文件/位置**:`qml/HistoryView.qml` — `_startBatchDelete`(L530)、`_pumpBatch`(L541-557)
- **问题**:批量删除逐个串行(`_pumpBatch` 删一个 → 等 `deleteRunFinished` → 删下一个)。删 50 局要 50 次往返。
- **证据**:L541 `if (_batchQueue.length === 0)` 收尾;L556 `ObserverClient.deleteRun(next)` 单个;onDeleteRunFinished L561-569 串行 pump。
- **影响**:大批量删除慢(非阻断,有进度反馈);小批量无感。
- **修复方向**:有限并发(如 4-8 路)或服务端批量删除端点。
- **是否本轮小修**:需另开 plan(并发控制)。

---

### Low

#### L1 — AuditLinksPanel 残留 console.log,用户点击审计链接时触发【已修】
- **文件/位置**:`qml/components/AuditLinksPanel.qml` L80 `console.log("Audit link:", ObserverClient.baseUrl + path)`
- **问题**:dev 日志残留在用户点击路径,把 observer base URL 打到 stdout。
- **影响**:轻微信息泄露(base URL 非密,但不应在生产点击路径打印);日志噪音。
- **修复方向**:删除该行。
- **是否本轮小修**:**可本轮小修**(删一行)。

#### L2 — ConfirmDialog 用深色 token 背景,在浅色页面上作 modal 弹出【暂缓】
- **文件/位置**:`qml/components/ConfirmDialog.qml` L20-24(`Theme.color.surface`/`border` 深色)、L31/L41(`Theme.color.text`/`textMuted`)
- **问题**:ConfirmDialog 用 dark theme token,但宿主(HistoryView)是 warm 浅色页。modal 遮罩盖住背景后深色 dialog 本身可读,但与浅色应用风格割裂。
- **影响**:视觉一致性(非 bug)。
- **修复方向**:加 `onLight` 开关或统一用 warm token。
- **是否本轮小修**:可本轮小修,但建议并入视觉收口 plan。

#### L3 — Theme 四套调色板并存,易混用【暂缓】
- **文件/位置**:`qml/Theme.qml` — `color`(dark zinc)/`report`(warm beige)/`warm`(Claude)/`parchment`(god-view)四套
- **问题**:四套 palette 都活跃,页面混用(ConfirmDialog 用 `color`、HistoryView 用 `warm`+`parchment`、SettlementView 用 `report`)。M1 的硬编码色部分源于「找不到合适 token 就地写」。
- **影响**:维护性、一致性。
- **修复方向**:文档化每套 palette 的适用场景(Theme.qml 注释已有,但可在 DESIGN.md 补决策表)。
- **是否本轮小修**:文档项,非代码,可本轮。

#### L4 — EventPresentationQueue 多个 readonly 计算属性每次重扫全表【暂缓】
- **文件/位置**:`qml/EventPresentationQueue.qml` — `phaseTimeline`(L36-51)、`deadPlayers`(L68-84)、`voteTally`(L95-119)、`presentedEvents`(L126-146)每次重算都遍历 `_ordered[0.._cursor]`
- **问题**:这些 readonly 属性被多处绑定;cursor 推进 / enriched 变化时全部重算 O(_cursor)。长对局(几十回合)下,每个 90ms tick 推进都可能触发多次全表扫。
- **影响**:性能嫌疑(详见第 4 节),非 bug。
- **修复方向**(若性能体检证实为瓶颈):增量维护死亡集合/票数字典,而非每次重扫。
- **是否本轮小修**:需先测量(见第 5 节),证实后再开 plan。

---

## 3. 维度小结

- **A 页面状态与导航生命周期**:H3 是根因(replace 销毁重建→状态丢失+重复请求);无隐藏页面继续运行问题(destroy 即停);Timer 都 repeat:false 或由业务门控,无泄漏。Connections 每文件 ≤2,合理。
- **B 绑定与状态一致性**:未见明显 binding loop;`I18n.lang` 单向数据流清晰;EventQueue 的 cursor 单源设计好。`historyExecutionModeCombo`/`historyResultCombo`/`historyTimeCombo` 用 index→枚举映射,currentIndex 与 filter 是单向写入(下拉改 filter,filter 不反写 currentIndex),中英切换时 ParchmentComboBox 的 model 文本变化但 currentIndex 不变,行为正确。
- **C 数据请求与协议边界**:竞态防护扎实(见总评);空态(EmptyState)、loading(`fetching`)、错误(reasonText)完整。**唯一缺口是 SSE 无重连(M4)和 timeFilter 死 UI(H1)**。
- **D 组件复用与视觉一致性**:ParchmentComboBox/AppButton/AppCard/HudCard 复用好;但 M1 硬编码色、M2 假数据混入真实页、ConfirmDialog 风格割裂(L2)。无 debug/preview 入口残留在用户导航(designPreview 仅 AppShell 持有且无用户页链接)。
- **E i18n/文案/可读性**:H4 是主要问题;HistoryView 命名规则「N人对局 - 时间」(L205-217)实现正确且默认按时间降序排序(L442-458),符合要求;文案长度用 elide 处理,溢出可控。
- **F 可维护性**:HistoryView 1968 行、ProviderSettingsView 2146 行偏大(M2 建议拆分);重复 delegate/卡片样式多但已抽组件;无写死坐标导致缩放问题(都用 anchors/比例)。
- **G 安全**:CredentialStore 边界完全合规(见总评);live/fake 真相由 `currentExecutionMode`(run-detail execution_mode,非 intent)驱动,DataSourceChip 保守默认 SIMULATION;错误信息不泄露 secret。**无安全问题**。

---

## 4. 最可能导致「页面返回卡顿」的代码嫌疑清单

> 仅列嫌疑,本轮不做性能结论(未跑 profiler)。

1. **`AppShell._replaceView` → `stackView.replace`**(L323-336):每次返回都销毁+重建整页 + 180ms 淡入过渡。重建本身(实例化所有子组件、重跑 onCompleted、重发 API 请求)是返回延迟的主嫌疑。
2. **HistoryView `Component.onCompleted` → `refreshRuns()`**(L13):每次进入历史页都全量拉 `/api/runs`,返回历史页必触发。
3. **MatchSetupView `Component.onCompleted`**(L89-97):三连请求(refreshProfileSchema/refreshProfiles/refreshCapabilities)+ 遍历 `syncCredentialToServer` 逐个 POST,返回配置页必全跑。
4. **EventPresentationQueue readonly 属性全表重扫**(L4):观战页停留时每个 tick 触发 phaseTimeline/deadPlayers/voteTally/presentedEvents 多次 O(_cursor) 扫描。
5. **ProviderSettingsView `onSelectedProviderChanged` → `loadProviderIntoForm`**(L411):切供应商时清空/重填表单 + 触发 `providerGroupRows`/`modelRowsFor` 重算(L825 model 绑定含 `(root.credRev, ObserverClient.providerModels, root.providerGroupRows(modelData))` 逗号表达式强制重算)。
6. **ParchmentComboBox `Behavior on color/border.color` + popup 切换**(L74-75):下拉框频繁 state 切换时颜色动画叠加。
7. **HistoryView `filteredRuns` 每次重算遍历全部 runItems + 排序**(L435-461):runItems 变化或任一 filter 变化都全量重扫+排序。

---

## 5. 建议后续性能体检的测量点

利用工作树中已有的 perf harness(`--perf-nav` + `WW_QT_PERF`/`WW_QT_PERF_LOG`),建议测量:

1. **导航步耗时**:AppShell `_perfNextStep` 已记录 `PERF_NAV sync` / `settled` 的 `syncMs`/`elapsedMs` —— 直接量化 H3 的返回卡顿(Home↔Setup、Home↔Settings、Home↔History 各往返耗时)。
2. **HTTP 请求瀑布**:`PERF_HTTP GET/POST <path>` 已记录每次请求 —— 分析返回某页时触发了哪些请求、是否重复(refreshRuns/refreshProfiles 是否每次必发)。
3. **EventQueue tick 负载**:在长对局(>20 回合)下,测量 90ms tick 内 `phaseTimeline`/`voteTally`/`presentedEvents` 重算耗时占比(用 QML profiler 或在 `_pump` 打点)。
4. **页面实例化耗时**:`stackView.replace` 后 `currentItem` 出现的延迟 —— 区分「重建实例」vs「API 往返」各占多少。
5. **批量删除吞吐**:删 N 局(N=10/50)的总耗时,量化 M5。
6. **内存**:多次 Home↔History 往返后内存是否单调增长(replace 是否真正释放旧页实例 + JS 闭包)。

---

## 6. 最后报告

### `git status --short`
```
 M clients/qt_observer/main.cpp
 M clients/qt_observer/qml/AppShell.qml
 M clients/qt_observer/qml/HistoryView.qml
 M clients/qt_observer/qml/HomeView.qml
 M clients/qt_observer/qml/MatchSetupView.qml
 M clients/qt_observer/qml/ProviderSettingsView.qml
 M clients/qt_observer/qml/TheaterView.qml
 M clients/qt_observer/qml/components/PhaseBackground.qml
 M clients/qt_observer/qml/components/SceneBackground.qml
 M clients/qt_observer/qml/components/SetupRoleCard.qml
 M clients/qt_observer/src/ObserverApiClient.cpp
 M clients/qt_observer/src/ObserverApiClient.h
```
**说明**:工作树存在 12 个未提交改动。经 `git diff` 核实,这是一套**性能测量 harness 的接入**(`--perf-nav` flag、`perfLog`、`WW_QT_PERF`/`WW_QT_PERF_LOG` env、HTTP 请求日志),与本审查报告 H2 直接相关——它既是审查发现,也是工作树未提交状态的成因。

### 本轮是否修改文件
**否。** 本轮纯审查,全程仅用 Read / Bash(grep、wc、git diff、git status),**从未调用 Edit 或 Write 工具**,未对任何文件做任何改动。上述 12 个 M 状态文件是会话开始前已存在的未提交改动(初始快照标注 clean 是更早时点的快照),非本轮造成。

### 本轮运行的命令及结果
| 命令 | 用途 | 结果 |
|---|---|---|
| `git status --short` | 工作树状态 | 12 个 M(perf harness 改动) |
| `git ls-files clients/qt_observer` | 目录结构 | 列出全部 QML/C++/资源 |
| `git log --oneline -20 -- clients/qt_observer` | 提交历史 | 最近 UI 重做提交 |
| `wc -l qml/*.qml ...` | 文件规模 | TheaterView 165 / HistoryView 1968 / ProviderSettingsView 2146 行 |
| `grep -rn "_perfNav\|Qt.quit\|grabToImage..."` | harness 残留 | 确认 perf harness 在 AppShell + C++ |
| `grep -rn "console\.\(log\|debug...\)"` | 日志残留 | 仅 AuditLinksPanel.qml:80 一处 |
| `grep -rc "Connections {\|Component.onCompleted\|Timer {"` | 生命周期指标 | Connections ≤2/文件,onCompleted/Timer 分布合理 |
| `git diff clients/qt_observer/src/...` | 核实未提交改动性质 | 确认为 perf harness,非本轮所致 |
| 各文件 Read | 逐文件审查 | 见报告引用的行号 |

**未运行测试/构建**:本轮纯静态审查,按 skill 要求构建+ctest+截图自验属于「修复后」动作,本轮不修改代码故未触发验证门。

---

**审查结论**:UI 重做整体质量良好(竞态、安全、契约三块过硬),无 Critical。建议下一个 polish plan 优先处理 **H1(死 UI)→ H4(i18n 零散补,可本轮小修部分)→ H3(导航状态恢复,需架构决策)→ H2(perf harness 归宿决策)**;M1/L1 可作为收尾清扫。性能方面先用已有 perf harness 跑一轮测量(第 5 节)再决定是否优化 L4。
