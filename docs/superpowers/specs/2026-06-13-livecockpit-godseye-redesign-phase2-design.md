# Phase 2 · LiveCockpit 上帝视角圆桌重做 — 设计方案

- 状态:草案(待用户复核)
- 日期:2026-06-13
- 父 spec:`docs/superpowers/specs/2026-06-13-werewolf-game-client-redesign-design.md`(本方案是其 §7.1 **Phase 2** 的细化与落地蓝本)
- 范围:`clients/qt_observer/**`(对局直播页的视觉/交互层 + 一个首页静态预览入口)+ `tests/test_qt_observer_static_contract.py`(契约同步 only)
- 不在范围:runtime / scoring / provider / 模型可见 prompt / 日志契约 / 引擎逻辑 / observer 后端字段

---

## 1. 定位与目标(两处关键澄清)

**(a) 真正要重做的页是 `TheaterView`,不是 `LiveCockpitView`。**
`clients/qt_observer/qml/LiveCockpitView.qml` **未接入 `AppShell` runtime 路由**(接入 `StackView` 的对局直播页是 `TheaterView.qml` —— `AppShell.qml:226` 的 `cockpitComponent`,objectName `theaterView`,已带真实 `ObserverClient` 绑定 + SSE 流 + 结算 overlay),**但仍被 CMake 与 static contract 注册**(`CMakeLists.txt:47` 的 `qml_module` 文件列表 + `tests/test_qt_observer_static_contract.py:76` 钉了它的 7 个 objectName)。本次重做的对象是 **TheaterView**;`LiveCockpitView.qml` 在本阶段**删除**,**删除时必须同步移除 CMake 注册与该 static contract 条目**(否则构建/契约测试会失败)。

**(b) 当前产品阶段 = 人类玩家是「上帝视角」观看 AI vs AI。**
人类是**全知观众**,不是局内玩家。因此中央动物头像**编码角色是优点**(一眼读懂谁狼谁神),不构成可见性泄漏——可见性契约约束的是「切换到某座位视角时事件/身份的投影」,而默认上帝视角本就应可见全部 `display_role`。**「角色中性头像」是未来「玩家 vs AI」阶段才需要的东西**,届时另设一组与任何角色无关的头像随机分配即可,不在本阶段。

> 重做的本质:**整棵可视化树照 ③ 蓝本推倒重写**(新布局/新组件/新资产),**只保留看不见的数据绑定语义**(座位/事件/票数/可见性投影)。保留数据 ≠ 保留长相。

## 2. 视觉蓝本:GOD'S-EYE 俯视圆桌环

经 GPT 多版生图比选,选定「上帝视角俯视圆桌环」(参考图 ③):羊皮纸圆桌居中偏左,座位 = 围桌的独立动物肖像徽章,投票/夜间行动 = 座位间珊瑚虚线箭头;左栏事件流、右侧票数与控制悬浮、底部多数线。暖奶油 + 珊瑚 + 烛光的水彩绘本质感(沿用 `DESIGN.md` 与首页/塔罗画风)。

## 3. 资产分层模型(灵魂所在)

**不画「一整张画死的场景」**(壁纸无法反映 6 座实时变化的存活/发言/票),也**不画透视房间**(透视下平面头像贴上去会错位、座位数一变即废)。改为**可拼图层**:

1. **背景层**:一张「空的、对称的、俯角椭圆」圆桌房间——**无动物、无固定椅子**,桌心留空、外圈留干净环形空带、桌子**刻意偏左**(中心约在右区 44%),右 ~30% 与底部留暗作悬浮面板区。昼/夜两张,构图一致只换光。
2. **头像层**:6 张角色动物**圆形透明肖像**(正脸广告牌式),由 QML 按公式落位。
3. **驱动层(QML)**:座位位置/数量/存活/发言/出局/投票箭头全部由真实数据驱动,背景一张通吃任意人数。

### 3.1 资产清单与 repo 落点

| 资产 | 文件 | 规格 | 状态 |
|---|---|---|---|
| 圆桌背景·白天 | `assets/illustrations/scene/table-day.png` | ~1536×1024,俯角椭圆,偏左,右/底留空 | ✅ 已生成 |
| 圆桌背景·黑夜 | `assets/illustrations/scene/table-night.png` | 同构图换月光烛火深海军蓝 | ✅ 已生成 |
| 角色头像 ×6 | `assets/illustrations/avatars/{werewolf,seer,witch,villager,guard,hunter}.png` | 1024² 透明圆形肖像,正脸,统一画风 | ✅ 已生成 |

物种映射:狼人=深袍狼 · 预言家=枭 · 女巫=猫 · 村民=兔 · 守卫=金甲狼 · 猎人=狐。

- **单源注册**:全部经 `Illustrations.qml` 注册,禁散落硬编码路径。
- **压缩必做**:原始母版 2–3MB/张(共 ~18MB),实现时 pngquant 压缩 + 应用内按需降采样;母版另存。
- **fallback 强制**:头像缺失→角色名首字 + `roleAccent` 描边环;背景缺失→phase 暖渐变兜底。

## 4. 落位几何(圆 → 椭圆 + 景深)

`SeatRing` 从「正圆」升级为「椭圆 + 近大远小 + z 序」:

```
θᵢ = −90° + i·360/N                      # 0 号在最里(上),顺时针
xᵢ = cx + Rx·cos θᵢ
yᵢ = cy + Ry·sin θᵢ        Ry = Rx·cos(俯角)   # 竖轴压扁 = 俯角
scaleᵢ = 1 + k·sin θᵢ      k≈0.12–0.18         # 前排略大、后排略小
z 序:按 sin θᵢ 升序绘制(后排先画,前排压上)
```

- `cx/cy/Rx/Ry` 为**标定常量**,**待真机按 `table-day.png` 实际桌沿椭圆量取**;形如 cx≈右区 38%、cy≈54%、Rx≈31%、`Ry = Rx·cos(俯角)`(俯角约 45–50° → Ry/Rx≈0.65–0.70)。两张背景构图一致,常量共享。
- 头像是**正脸广告牌,不做透视拉伸**;立体感来自椭圆排布 + 缩放 + 遮挡。
- 桌心(cx,cy)留给 `PhaseIndicator` 阶段徽记(太阳/月亮 + 轮次)。
- 投票/夜间行动箭头 = QML 在两座位坐标间连珊瑚虚线(Shape/Canvas)。

## 5. 页面布局 v2

```
┌──────────────┬────────────────────────────────────────────┐
│ 上帝视角观察   │                         [阶段 白天·R2/5]  ◄悬浮右上
│ ← 返回 · 数据源│        〔右区 = 背景图 + 头像环〕            │
│ [视角切换]     │           圆桌(俯角椭圆,中心偏左~44%)       │
├──────────────┤                              [当前票数]    ◄悬浮右
│  事件流        │              🐺                            │
│  (信息量大,    │          🐰      🦉            [▶⏸ 1x2x4x]◄悬浮右
│   独占纵向)    │              🐱                            │
│              │                                              │
│ [证据/审计 ▸] │            ──── 多数线 5 ────              ◄底部居中
└──────────────┴────────────────────────────────────────────┘
  左区 ~20%(实体UI列)        右区 ~80%(背景铺满,悬浮件只压氛围空白)
```

- **左区 ~20%**(360–420px,不透明 UI 列,坐 `canvas/surfaceCard`):
  - 顶:品牌「上帝视角观察」+ `← 返回` + **数据源真相**(`DataSourceChip`,LIVE/SIMULATION **始终可见**)+ **视角切换**(`PerspectiveSwitcher`)。
  - 中:**事件流**(`EventTimeline`,接 `eventItems`,onLight 重做)——独占纵向空间。
  - 底:**证据/审计可折叠条**(`EvidenceConsole` + `ViewBoundaryBadge` + `ProjectionProofPanel` 收纳于此,默认折叠,展开看可见性边界/投影证明)。
  - ⚠️ **`PerspectiveSwitcher` 全页只能有一个实例**:现有 `EvidenceConsole.qml:203` 内部已自带 `PerspectiveSwitcher` + 审计件。把视角切换提到左区顶部时,**必须**给 `EvidenceConsole` 加 `showPerspectiveSwitcher: false`(或拆出 audit-only 模式),避免左上与折叠条里**两个控件重复写同一个 `ObserverClient.currentPerspective`**。
- **右区 ~80%**:`PhaseBackground`(table-day/night 交叉淡入)+ 头像环。悬浮件**只压背景氛围空白,绝不盖头像**:
  - 右上:**阶段**(白天/黑夜 + 轮次;**去掉原 LIVE 观战人数标记**)。
  - 右(阶段下):**当前票数**实时聚合。
  - 右(票数下):**倍速/暂停**独立悬浮件(`PlaybackControls`,即原 ③ 的 JUMP TO LATEST 位)。
  - 底部居中:**多数线**。
- **结算**:沿用现有同页 `SettlementView` overlay(对局结束自动浮出),视觉随新系统重做。

## 6. 组件清单

| 组件 | 处置 |
|---|---|
| `LiveCockpitView.qml` | **删除**(死代码) |
| `TheaterView.qml` | **重写**为新布局宿主;保留全部 `ObserverClient` 绑定/调用与 objectName `theaterView` |
| `SeatRing.qml` | 改造:椭圆 + 景深 + z 序;座位委托换 `CharacterAvatar` |
| `CharacterAvatar.qml` | **新增**:圆形动物肖像 + 阵营色环 + 名牌 + 存活/发言/出局态 + 接触阴影 + fallback |
| `PhaseBackground.qml` | **新增**:table-day/night 按 phase 交叉淡入 |
| `PhaseIndicator.qml` | **新增**:桌心阶段徽记(太阳/月亮 + 轮次)+ 右上悬浮阶段条 |
| `EventTimeline` / `PlaybackControls` / `EvidenceConsole` / `ViewBoundaryBadge` / `ProjectionProofPanel` / `PerspectiveSwitcher` / `DataSourceChip` / `StatusBadge` | 复用,迁入新布局并按暖色系统(onLight)重做样式 |
| 当前票数面板 | QML 侧派生,**不新增后端字段**。派生口径**写死**:从**当前可见投票事件**统计,且**按 `EventPresentationQueue` 的播放游标 / 当前 round 截断**(`EventPresentationQueue.qml:19` 已分层接入 `eventItems` 与 `projectionEvents`)。**禁止**从完整 `projectionEvents` 一次性算最终票数——否则回放中会**提前显示未来票**。 |
| `SettlementView` overlay | 保留接线,视觉随新系统 |

## 7. 数据绑定不变 + 表现层参数化

把「直播页视觉」做成**表现型组件**,数据经属性注入,而非组件内部直接抓 `ObserverClient`:

- 新增表现型 cockpit(承载头像环 + 悬浮件 + 事件流),输入 = `players / events / phase / round / votes / perspective / dataSource / deadIds / current …`(均为现有可见数据的形状)。
- **两个宿主**绑同一套表现组件:
  - **`TheaterView`(live 宿主)**:把 `ObserverClient.*` 绑到表现组件属性(现有绑定语义逐字保留)。
  - **`DesignPreviewView`(静态宿主,见 §9)**:把**烤死样例数据**绑到同样属性。
- 收益:同一视觉两处复用、可截图验收、不触碰后端;符合「页面可重排,数据绑定语义不变」铁律。

## 8. 昼夜 / 投票呼吸

沿用 `TheaterView` 现有 `EventPresentationQueue` 驱动的 `layoutPhase` 状态机与过渡门控(night/day/voting),但表现重做:
- **night**:`PhaseBackground` 切 table-night;环略放大居中;事件流面板可淡;夜间行动(狼刀/查验/守护)以箭头在环上呈现(上帝视角可见)。
- **day**:table-day;环常态;事件流亮。
- **voting**:票数悬浮 + 环上投票箭头汇聚 + 底部多数线。
- 过渡用 base(~180–700ms)交叉淡入,**不动容器位置,只动尺寸/透明度**(承袭现有「呼吸」实现,避免瀑布流乱飞)。

## 9. 首页静态预览入口(验收骨架)

**目标:不开真局也能逐版检查重做页。**

- HomeView 新增「🎴 设计预览 / Design Preview」入口(新 objectName,如 `designPreviewButton`),`AppShell` 加 `navigateDesignPreview` → 路由到 `DesignPreviewView`。
- `DesignPreviewView` 用 §3 的 8 张真资产 + **一份 QML 侧烤死样例**(6 座 = 6 角色、1 座发言、1 座出局、若干票、当前阶段)渲染重做后的 cockpit 表现组件;**不接 `ObserverClient`、不开 run**。
- 内置「白天/黑夜/投票」切换,供截图矩阵。
- ⚠️ **预览页的真相标记必须是固定的「设计样例 / Design Sample」**,**禁止读 `ObserverClient.currentExecutionMode`**(`AppShell.qml:121` 的全局 `DataSourceChip` 绑的是当前 run 的 execution mode)——否则预览页会误显示上一局残留的 LIVE/SIMULATION 状态。
- 既是设计验收入口,也是 `verifying-qt-observer-ui` 的截图靶子(真机渲染,companion HTML 无法替代:MultiEffect/阴影/遮罩须真机验)。

## 10. 约束

- ⚠️ 大改 QML 会撞 `tests/test_qt_observer_static_contract.py`(钉文案/结构/objectName):**plan 必含同步更新**(新增 `designPreviewButton`/`navigateDesignPreview`;TheaterView 重写后 objectName 维持 `theaterView`)。
- 不触碰 runtime/scoring/provider/模型可见 prompt/日志契约/observer 后端字段。
- 中 / EN 双语对等,中文默认;塔罗/头像画面中文已烤入或无字。
- 每阶段:Qt 构建 0 error + 截图复核(skill `verifying-qt-observer-ui`)。
- 单人本地执行;提交前按根 `AGENTS.md` 的本地验证纪律自检。
- 增量 `Theme`(暖色令牌已于 Phase 1 落地),共享组件 `onLight` 开关,避免暗色页回归。

## 11. 验收口径

- 三点原不满消解:暖色(奶油+昼夜插画)、有质感(柔和投影+水彩头像+圆桌)、字体舒适(宋体标题 + 16px 正文)。
- **信息一眼可见(铁律)**:当前阶段/轮次、当前发言者、存活/出局、投票目标与票数、多数线、LIVE/SIMULATION 真相——插画不得压过这些。
- 头像按椭圆公式贴合背景桌沿;偏左留空使悬浮件不盖头像;6/8 人皆正确排布。
- 截图矩阵(经 `DesignPreviewView`,无需真局):白天 / 黑夜 / 投票中 / 结算;分辨率 1280×720、1440×900、1920×1080 至少覆盖一档小屏。

## 12. 暂留项(parked,不阻塞本 spec)

- **守卫=金甲狼 与 狼人=深袍狼 同为狼**:小尺寸辨识稍弱(靠红/绿色环 + 名牌区分)。先用;若要最干净辨识,守卫可换物种(熊/獾/牛)重生一张,纯换图不动结构。
- 审计/证据三件套(`EvidenceConsole`/`ViewBoundaryBadge`/`ProjectionProofPanel`)与 `PerspectiveSwitcher` 的**最终落位**(本 spec 暂定左区底部折叠条 + 左区顶部),实现时按真机观感微调。
- 夜间行动箭头(狼刀/查验/守护)的具体样式与上帝视角呈现细节。
- 字体打包(可选增强),不绑本阶段硬门槛。

## 13. Phase 2 内部分步建议(供 plan 细化)

1. **资产入库 + 注册 + 压缩**(table-day/night、6 头像、`Illustrations.qml`、fallback)。
2. **CharacterAvatar + SeatRing 椭圆化 + PhaseBackground/PhaseIndicator**(组件级)。
3. **DesignPreviewView + HomeView 入口 + 烤死样例**(先让「静态首页预览」可见可截图 = 最早验收点)。
4. **TheaterView 重写**为新布局宿主(绑真实 `ObserverClient`,保留语义),悬浮件/左栏/审计件 rehome。
5. **昼夜/投票呼吸 + 结算 overlay 重皮**。
6. 契约测试同步 + 截图矩阵复核。

> 每一步都落到「DesignPreviewView 或 TheaterView 的真实页面」截图,不交纯 token/组件。
