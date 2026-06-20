# 狼人杀观察席 · 游戏客户端视觉重做 — 设计方案

- 状态：草案（待用户复核）
- 日期：2026-06-13
- 范围：`clients/qt_observer/**`（QML 客户端的视觉/交互层）
- 不在范围：runtime / scoring / provider / 模型可见 prompt / 日志契约 / 引擎逻辑

---

## 1. 背景与定位转变

当前 qt_observer 被当作**严肃工程控制台**来做：冷炭灰（zinc）背景、扁平无质感组件、过细过淡的字体、突兀的底栏。用户的真实不满是三点：配色不高级且冷、组件扁平没质感、字体太细太淡太小。

更根本的发现：**项目的实际性质已经从"实验工程台"偏向"游戏"**。因此本次不是换肤，而是一次**定位转变**——

> 从「严肃工程控制台」→「插画驱动的狼人杀观战**游戏客户端**」。

狼人杀源自桌游卡牌，"精美卡片"与"角色"是天然加分项。视觉锚点由 GPT 生成的参考图确立（见 `.superpowers/brainstorm/` 与用户提供的昼/夜首页插画），最终选定：

- **首页**：动物角色围桌场景（左栏导航 + 中央场景 + 底部塔罗身份卡排 + 右侧信息卡）。
- **昼夜分割**作为全局阶段母题。
- **塔罗身份卡**作为身份系统与收藏页母题。
- **圆桌坐席环**作为对局直播页母题。

## 2. 设计原则（铁律）

1. **暖色编辑感**：沿用 `DESIGN.md`（Claude.com 分析）的暖奶油 / 珊瑚 / 暖海军蓝三位一体，作为 UI chrome 层。禁止冷灰、纯白、蓝紫科技渐变。
2. **插画承载灵魂，UI 克制托底**：氛围与角色由插画表达；界面元素保持安静、editorial。
3. **质感 = 柔和扩散投影 + 发丝边框**，扁平填色。**永不使用 glossy 渐变 / 玻璃高光 / 短硬黑影 / 霓虹辉光**。
4. **插画上必有可读性托底**：插画区上的任何文字必须坐在 scrim（渐变遮罩）或半透明卡片上，保证对比度 ≥ 4.5:1。
5. **阵营色只做小面积强调**：圆点 / 卡框 / 标签，绝不做卡片或大面积底色（守 Claude "不引入第四种表面色" 的克制）。
6. **双语**：中 / EN 始终对等；中文为默认。
7. **信息优先于装饰**：实时对局页信息优先级高于插画。LiveCockpit 中当前阶段、当前发言者、存活/出局、投票目标、夜晚结果、LIVE/SIMULATION 真相**必须始终一眼可见**；插画不得压过这些状态。本质仍是可审计观战平台，不是纯视觉 demo。

## 3. 设计令牌（Theme.qml 重写）

保留现有 `Theme.qml` 的单源 QtObject 结构与 helper，但令牌值与分组按下表重定。

### 3.1 颜色 — UI chrome 层（取自 DESIGN.md）

| 角色 | 令牌 | 值 |
|---|---|---|
| 主画布（白天/游戏外） | `color.canvas` | `#faf9f5` |
| 卡片表面 | `color.surfaceCard` | `#efe9de` |
| 浮起卡（near-white 暖白） | `color.surfaceRaised` | `#fffefb` |
| 暗表面（夜/对比） | `color.surfaceDark` | `#181715` |
| 发丝边 | `color.hairline` | `#e6dfd8` |
| 主文字 ink | `color.text` | `#141413` |
| 正文 | `color.textBody` | `#3d3d3a` |
| 次要 | `color.textMuted` | `#6c6a64` |
| 最弱 | `color.textSoft` | `#8e8b82` |
| 主色珊瑚 | `color.primary` | `#cc785c` |
| 珊瑚按下 | `color.primaryActive` | `#a9583e` |
| 珊瑚禁用 | `color.primaryDisabled` | `#e6dfd8` |
| 暖琥珀强调 | `color.accentAmber` | `#e8a55a` |
| 成功 | `color.success` | `#5db872` |
| 警告 | `color.warning` | `#d4a017` |
| 错误 | `color.error` | `#c64545` |

### 3.2 颜色 — 昼夜阶段（取自首页插画提取，与 chrome 协调）

```
phase.day.bg      ~#F3E8D2   阳光暖奶油
phase.day.ambient ~#E8C078   阳光琥珀
phase.day.sky     ~#AFC9E0   天空蓝
phase.night.bg    ~#2A3A55   深暖海军蓝
phase.night.sky   ~#20304F   月光夜空
phase.night.glow  ~#E8A85A   烛光琥珀（共享暖光，呼应珊瑚）
```

阶段背景驱动：游戏外/白天阶段 = `canvas`；黑夜阶段 = `surfaceDark` 配 `night.*`。

### 3.3 颜色 — 阵营（仅小面积强调）

```
faction.werewolf #c0392b   faction.seer #d4a017
faction.witch    #8e5bb5   faction.villager #3e6fb0
faction.guard    #4a8c6f   faction.hunter #b5683a
faction.unknown  #8e8b82   (隐藏 → "Hidden")
```
保留 helper：`roleAccent / roleTint(≤0.16) / roleBorder(≤0.30)`，但全部走"点/边/标签"，不做填充。`roleTint` **仅允许极小面积背景**（badge 内部、头像状态晕圈、投票箭头尾迹），**禁止用于整张卡片/大面积背景**（堵死"≤0.16 tint 也铺满卡"的空子）。

### 3.4 排版（治"太细太淡太小"）

字号阶：display 48/36/28、title 22/18/16、body 16/14、caption 13/12。行高正文 1.55、标题 1.05–1.2。正文基准 **16px**、字重 Medium，是消除"太细太淡太小"的主力。显示标题权重 Medium(500)、负字距（-0.5 ~ -1px）。

**字体策略（实现口径——打包不作为第一阶段硬门槛）**：

- **P0 默认：系统字体栈优先，不阻塞构建与分发。**
  - 标题：`Noto Serif SC` / `Source Han Serif SC` / 系统宋体 fallback
  - 正文：`Inter` / `Noto Sans SC` / `Source Han Sans SC` / 系统黑体 fallback
  - 等宽：`JetBrains Mono` / 系统等宽 fallback
- **可选增强**：若要跨平台视觉完全一致，再单独立小任务打包字体（不与 Theme 重写绑死）。
- **CJK 第一阶段不强制子集化**；若做子集化，只对子系统**固定 UI 文案**负责，**动态 AI 文本（发言/日志/provider 名/错误/战报）必须保留系统 fallback**，避免缺字。
- 第一阶段先把 font family / weight / size **token 定死**，视觉已能改善 ~80%。

### 3.5 间距 / 圆角 / 投影 / 动效

- 间距 4px 基：4/8/12/16/24/32/48；卡内 padding 32（大卡）/24（小卡）。
- 圆角：按钮/输入 8、卡片 12、大件 16、pill 9999。
- **elevation（新，柔和暖调投影三档）**：
  - `e1` `0 1px 2px rgba(50,38,24,.05)`（输入/次按钮）
  - `e2` `0 1px 2px rgba(50,38,24,.04), 0 10px 30px rgba(50,38,24,.07)`（卡片浮起）
  - `e3` 更大扩散（弹层/对话框）
- **scrim（新）**：插画上文字托底，`linear-gradient` 从 `rgba(canvas/dark, .0→.85)`。
- 动效：fast 120 / base 180 / slow 260；阶段切换用 base 交叉淡入。

## 4. 插画资产体系

### 4.1 管线

- GPT 生成 PNG → 放 `clients/qt_observer/assets/illustrations/` → 走 Qt 资源系统打包。
- **单源注册表**（如 `Illustrations.qml` 或 manifest）：禁止散落硬编码路径；新增/替换图改一处。
- 大图将来在 2K/4K 需更清晰时统一**放大到 ~2560×1440**。

### 4.2 资产清单与规格

| # | 资产 | 规格 | 状态 |
|---|---|---|---|
| 1 | 首页主场景 · 白天 | 1536×1024，无 UI，主体居中偏上，左~30%/右~28%/底部安静区 | ✅ `scene/home-day.png` |
| 2 | 首页主场景 · 黑夜 | 1536×1024，构图与白天**完全一致**，仅换光 | ✅ `scene/home-night.png` |
| 3 | 塔罗身份卡 ×6 | 1024×1536，统一暖金边框+奶油名牌；动物形象+象征符号+烤入中文名 | ✅ `tarot/{werewolf,seer,witch,villager,guard,hunter}.png` |
| 4 | 角色头像 ×9–12 | 座位用动物头像；正方/可裁圆；与场景同画风 | ⏳ 待生成 |
| 5 | 对局页昼/夜背景 | 16:9，可与圆桌环叠加 | ⏳ 待生成 |
| 6 | 空状态插画 ×1 | "暂无对局" 小幅插画 | ⏳ 待生成 |

资产根目录：`clients/qt_observer/assets/illustrations/`（`scene/` + `tarot/`）。已落 8 张 PNG，共 ~24MB（母版）。⚠️ **打包优化必做**：pngquant 压缩 + 应用内显示按需降采样（塔罗在席位/牌库多为缩略展示）；原始母版保留。塔罗名已烤入图内，QML 不再叠中文名（EN 态另议）。

### 4.3 可读性规则

首页插画为满构图，左右有家具细节、夜版有烛火亮点。故：**左栏导航 / hero 标题 / 右侧信息卡一律坐在半透明卡片或 scrim 上**，不得让裸文字压在繁忙插画区。底部安置塔罗卡排。

塔罗卡的中文角色名**烤入图内、恒为中文**（卡是收藏品/艺术品）；EN 模式下界面另给英文标签，不改卡面。

### 4.4 资产失败降级（强制）

所有插画组件**必须有无资产 fallback**，不允许因图缺失/路径错/未进 qrc/加载失败导致白屏、布局塌陷或 QML runtime error：

- `SceneBackground` 缺图 → 退回 phase 渐变 + subtle pattern；
- `TarotCard` 缺图 → 退回 vector / card placeholder；
- `CharacterAvatar` 缺图 → 退回 role initials + `roleAccent` 描边环。

## 5. 组件库（QML）

### 5.1 沿用并重做（chrome）

- `AppButton`：珊瑚主 / 发丝描边次 / 暗表面次；e1–e2 投影；按下 darken，无 hover 花活。
- `AppCard`：浮起卡（e2 + hairline + surfaceRaised）。
- `StatusBadge` / `SectionHeader`（衬线）/ `EmptyState`（配空状态插画）。
- 顶栏 → **`NavRail`（新，左侧图标导航）**：今夜对局/席位/实时事件/复盘/收藏牌库/设置 + 观察者等级。**v1 只做四件事：选中态、禁用态、窄屏收起态、tooltip/label**；不做 hover 花活/图标动效。它是安静的入口，不是抢主视觉的装饰条。

### 5.2 新增游戏组件

- `TarotCard`：身份卡（用资产 #3），含正/背/翻面态、可缩放。
- `CharacterAvatar`：动物头像座位（用资产 #4），含存活/出局/发言态。
- `SceneBackground`：插画图层 + scrim（用资产 #1/#2/#5）。
- `PhaseBackground`：昼夜阶段背景，随 game phase 交叉淡入切换。
- `PhaseIndicator`：当前白天/黑夜与轮次标识。

## 6. 页面母题分工

| 页面 | 蓝本 / 母题 |
|---|---|
| 首页 HomeView | 图1：NavRail + 围桌 SceneBackground + 底部 TarotCard 排 + 右侧"今夜对局/实时事件"卡 + 珊瑚主 CTA「进入今晚对局」 |
| 对局直播 LiveCockpit | 圆桌坐席环（CharacterAvatar 环绕）+ PhaseBackground 昼夜 |
| 身份牌库 / 收藏 | 放大 TarotCard 卡墙 |
| 结算 / 复盘 Settlement | 沿用暖色"明室"，融入 TarotCard 复盘 |
| 配置 MatchSetup | 卡片化座位配置；返回/启动底栏只用发丝线分隔、**不变底色** |
| 历史 / 设置 | chrome 组件标准化 |

### 6.1 首页布局蓝本（图1）

```
┌──┬───────────────────────────────────────┬───────────────┐
│N │  观战席(eyebrow)                       │  今夜对局卡    │
│a │  狼人杀 · 观察席   (衬线大标题)         │  [进入观战席]  │
│v │  一行 lede                             │               │
│R │  [进入今晚对局] [查看昨夜复盘]          │  实时事件列表  │
│a │        〔围桌 SceneBackground〕         │               │
│i │  ── 底部：6 张 TarotCard 排 ──          │               │
└──┴───────────────────────────────────────┴───────────────┘
        左~30% 安静区              右~28% 安静区（卡片托底）
```

## 7. 范围 / 分阶段 / 约束

### 7.1 分阶段（每阶段独立 PR，各绑一个 implementation plan）

**原则：每个阶段都必须落到一个真实页面验收，不止交 token 和组件**（UI 项目最怕"地基 PR 单看都对，拼到页面全错"）。

1. **Phase 1 — Theme + 资产管线 + HomeView 样板页**：`Theme.qml` 重写（含字体 token，系统栈优先、不打包）+ scrim/elevation 令牌 + 插画资产管线与注册表 + 该阶段所需组件（SceneBackground / NavRail / AppButton / AppCard）+ **HomeView 落地为样板页**。
2. **Phase 2 — 组件库系统化 + LiveCockpit 样板页**：补齐游戏组件（TarotCard / CharacterAvatar / PhaseBackground / PhaseIndicator）+ chrome 组件系统化 + **LiveCockpit 落地**（昼夜 + 投票 + 结算前）。
3. **Phase 3 — 全量迁移**：Settlement / MatchSetup / History（含牌库）全部迁移到新系统。

字体打包（可选增强）单独成小任务，不绑入任何阶段硬门槛。

### 7.2 已知约束（落地现实）

- ⚠️ 大改 QML 会撞 `tests/test_qt_observer_static_contract.py` 等静态契约测试（钉了文案/结构）；**每个 plan 必须含同步更新这些契约测试**。
- 保持中 / EN 双语对等。
- 每阶段改完走 **Qt 构建 + 截图验证**（skill `verifying-qt-observer-ui`）。
- 单人本地执行；提交前按根 `AGENTS.md` 的本地验证纪律自检。
- 本次不触碰 runtime/scoring/provider/模型可见 prompt/日志契约。
- **QML 数据绑定语义不变**：不改现有路由、API 字段、状态机、SSE 订阅、profile schema、运行日志结构。**页面可重排，数据绑定语义保持不变**。

## 8. 验收口径

- 三点原不满全部消解：暖色（奶油+昼夜）、有质感（柔和投影+插画）、字体舒适（宋体标题+16px 正文）。
- 首页与图1蓝本一致、插画上文字可读、阵营色仅小强调。
- 每阶段：构建 0 error + 截图复核 + 契约测试更新通过。

### 8.1 截图验收矩阵（每阶段按覆盖到的页面截）

- HomeView：白天 / 黑夜
- MatchSetup：fake / live armed
- LiveCockpit：白天 / 黑夜 / 投票中 / 结算前
- Settlement：胜 / 负两种
- History：空状态 / 有历史
- 分辨率：1280×720、1440×900、1920×1080 三档，**至少覆盖一档小屏**
