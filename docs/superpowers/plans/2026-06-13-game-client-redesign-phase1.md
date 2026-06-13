# 狼人杀观察席 · 游戏客户端重做 Phase 1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 配套 spec：`docs/superpowers/specs/2026-06-13-werewolf-game-client-redesign-design.md`
> QML 构建/截图：执行前读 skill `verifying-qt-observer-ui`（Qt 工具链路径以 skill/记忆为准）。
> 共享 main 检出，提交走 skill `committing-in-shared-worktrees`，实现工作在隔离 worktree。

**Goal:** 把暖色"Claude"游戏化设计系统的地基落地（增量 Theme 令牌 + 插画资产管线 + SceneBackground/NavRail），并用它把 **HomeView 重做成样板页**，其余页面零回归。

**Architecture:**
- **增量 Theme**：现有暗色 token 的**值一律不动**（其它页面继续用，避免近白文字落奶油上消失）。新增 `Theme.warm.*` / `Theme.phase.*` / `Theme.fontFamilies.*` / `Theme.warmSize.*` / `Theme.elevation.*` 五组暖色/阶段/字体/字号/投影令牌，HomeView 与新组件只读新令牌。
- **共享组件加 `onLight` 开关**：`AppButton/AppCard/StatusBadge/SectionHeader/EmptyState` 各加 `property bool onLight: false`，默认走原暗色路径（所有现有调用点行为不变），`onLight: true` 时切暖色。
- **新组件**：`Illustrations`（singleton 资产注册表）、`SceneBackground`（插画 + scrim + 缺图 fallback）、`NavRail`（安静左栏导航，v1 只做 选中/禁用/窄屏收起/tooltip）。
- **AppShell 外科级改动**：仅当 `currentView === "home"` 时隐藏顶栏、StackView 顶部贴到 `parent.top`；其它页面顶栏与锚点完全不变 → 零回归。HomeView 在 home 上自带 NavRail + 暖色 chrome。
- **资产**：8 张 PNG 已在 `clients/qt_observer/assets/illustrations/`，通过 `qt_add_qml_module(... RESOURCES ...)` 进 qrc，`Illustrations` 单源解析 URL，缺图 fallback 强制。
- **HomeView 契约**：`homeView/startNewMatchButton/historyButton/serverStatusBadge/recentRunsList` 这些 objectName 与 `navigateSetup()/navigateHistory()` 调用一字不动保留。
- **字体（契约）**：`Theme.fontFamilies.serif/sans/mono` 为**单个字符串**（`"Source Han Serif SC"` / `"Inter"` / `"JetBrains Mono"`）。新增暖色文本统一 `font.family: Theme.fontFamilies.X` + `font.contextFontMerging: true`；**禁用 `font.families` 与未验证的 `font.features`**。不打包字体、不做 CJK 子集化（打包是后续可选增强，非 Phase 1 门槛）。run_id 用 mono。
- **排版行高（契约）**：暖色页面的 display/title/body 文本显式 `lineHeightMode: Text.ProportionalHeight` + `lineHeight`（display/title 1.10–1.18；body 1.45–1.55），不靠默认行高导致标题松散或正文发飘。
- **动效（克制阻尼）**：统一走 `Theme.anim`——颜色/hover 140ms `Easing.OutCubic`，press/scale 100ms `Easing.OutQuad`，按压 scale 0.98 回弹 1.0。NavRail 不做花哨 hover / icon 动画 / 发光。
- **Phase 1 不做毛玻璃**：无全屏 FastBlur / 大面积 backdrop blur / frosted glass；`MultiEffect` 只用于卡片柔和投影。
- **Phase 1 不做纸张噪点**：不加 noise/grain/PaperGrainOverlay；若截图偏平，仅在 review 结论建议 Phase 1.5 单独小任务。
- **发丝线收敛**：卡片层级靠 surface + soft shadow，不靠重边框；onLight 卡片 1px 边 alpha 0.06–0.10；NavRail 右 seam、输入/badge/列表分割可保留低对比 hairline。

**Tech Stack:** Qt 6.8+ / QtQuick / QtQuick.Controls / QtQuick.Effects(MultiEffect) / CMake `qt_add_qml_module` / Python `unittest`（静态契约门）。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `tests/test_qt_observer_static_contract.py` | 新增 Phase 1 契约门（资产存在、CMake 注册、Theme 暖令牌、组件 fallback、Home 用新系统） | Modify |
| `clients/qt_observer/qml/Theme.qml` | 增量暖色/阶段/字体/字号/投影令牌 | Modify |
| `clients/qt_observer/qml/Illustrations.qml` | 插画资产单源注册表（singleton） | Create |
| `clients/qt_observer/qml/components/SceneBackground.qml` | 插画背景 + scrim + 缺图 fallback | Create |
| `clients/qt_observer/qml/components/NavRail.qml` | 安静左栏导航（v1 四态） | Create |
| `clients/qt_observer/qml/components/AppButton.qml` | 加 `onLight` 暖色路径 | Modify |
| `clients/qt_observer/qml/components/AppCard.qml` | 加 `onLight` 暖色路径 + 柔和投影 | Modify |
| `clients/qt_observer/qml/components/StatusBadge.qml` | 加 `onLight` 暖色路径 | Modify |
| `clients/qt_observer/qml/components/SectionHeader.qml` | 加 `onLight` 暖色路径 | Modify |
| `clients/qt_observer/qml/components/EmptyState.qml` | 加 `onLight` 暖色路径 | Modify |
| `clients/qt_observer/qml/AppShell.qml` | home 上隐藏顶栏并重锚 StackView | Modify |
| `clients/qt_observer/qml/HomeView.qml` | 用新系统重做（NavRail + Scene + 暖 hero + tarot 条 + 最近对局） | Modify |
| `clients/qt_observer/CMakeLists.txt` | 注册新 QML 文件、Illustrations singleton、8 张图 RESOURCES | Modify |

---

## Task 1: Phase 1 静态契约门（先红）

**Files:**
- Modify: `tests/test_qt_observer_static_contract.py`（文件末尾、`if __name__` 之前追加新类）

- [ ] **Step 1: 追加契约测试类**

在 `tests/test_qt_observer_static_contract.py` 末尾 `if __name__ == "__main__":` 之前插入：

```python
class QtObserverGameRedesignPhase1Tests(unittest.TestCase):
    """游戏客户端重做 Phase 1：暖色地基 + 插画管线 + HomeView 样板页。"""

    ILLUSTRATIONS = [
        "assets/illustrations/scene/home-day.png",
        "assets/illustrations/scene/home-night.png",
        "assets/illustrations/tarot/werewolf.png",
        "assets/illustrations/tarot/seer.png",
        "assets/illustrations/tarot/witch.png",
        "assets/illustrations/tarot/villager.png",
        "assets/illustrations/tarot/guard.png",
        "assets/illustrations/tarot/hunter.png",
    ]

    def test_illustration_assets_exist(self) -> None:
        for rel in self.ILLUSTRATIONS:
            self.assertTrue((QT / rel).exists(), f"missing illustration asset: {rel}")

    def test_cmake_registers_new_qml_and_singleton_and_resources(self) -> None:
        cmake = (QT / "CMakeLists.txt").read_text(encoding="utf-8")
        for qml in ["qml/Illustrations.qml",
                    "qml/components/SceneBackground.qml",
                    "qml/components/NavRail.qml"]:
            self.assertIn(qml, cmake, f"CMakeLists must register {qml}")
        # Illustrations is a QML singleton
        self.assertRegex(cmake, r"qml/Illustrations\.qml\s+PROPERTIES\s+QT_QML_SINGLETON_TYPE\s+TRUE")
        # all 8 assets are bundled as RESOURCES
        for rel in self.ILLUSTRATIONS:
            self.assertIn(rel, cmake, f"CMakeLists must bundle resource {rel}")
        self.assertIn("RESOURCES", cmake)

    def test_theme_has_warm_phase_font_tokens(self) -> None:
        theme = (QT / "qml/Theme.qml").read_text(encoding="utf-8")
        for token in ["property QtObject warm", "canvas", "surfaceCard", "surfaceRaised",
                      "property QtObject phase", "property QtObject fontFamilies",
                      "property QtObject warmSize", "property QtObject elevation",
                      "property QtObject anim",
                      '"#cc785c"', '"#faf9f5"']:
            self.assertIn(token, theme, f"Theme.qml missing warm token: {token}")
        # fontFamilies must be single strings, not arrays (no font.families usage).
        self.assertRegex(theme, r'property string serif:\s*"Source Han Serif SC"')
        self.assertNotIn("font.families", theme)

    def test_scene_background_has_no_asset_fallback(self) -> None:
        c = (QT / "qml/components/SceneBackground.qml").read_text(encoding="utf-8")
        self.assertIn("Image.Ready", c)          # only show art when loaded
        self.assertIn("Gradient", c)              # phase-gradient fallback underneath
        self.assertIn("Illustrations", c)         # sourced via the registry

    def test_navrail_contract(self) -> None:
        c = (QT / "qml/components/NavRail.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "navRail"', c)
        self.assertIn("currentKey", c)            # selected state
        self.assertIn("collapsed", c)             # narrow collapse state
        self.assertIn("signal activated", c)      # emits navigation intent

    def test_home_uses_new_design_system(self) -> None:
        c = (QT / "qml/HomeView.qml").read_text(encoding="utf-8")
        self.assertIn("SceneBackground", c)
        self.assertIn("NavRail", c)
        self.assertIn("onLight", c)               # warm component path is used
        # navigation + required objectNames preserved (also covered by REQUIRED_OBJECT_NAMES)
        self.assertIn("navigateSetup()", c)
        self.assertIn("navigateHistory()", c)
        # typography contract: explicit proportional line height; no font.families
        self.assertIn("lineHeightMode", c)
        self.assertIn("contextFontMerging", c)
        self.assertNotIn("font.families", c)
        # tarot strip falls back on Image.status (not only on empty url)
        self.assertIn("tarotArt.status !== Image.Ready", c)

    def test_no_phase1_glass_or_grain(self) -> None:
        # Phase 1 forbids frosted glass and paper-grain overlays.
        for rel in ["qml/components/SceneBackground.qml", "qml/HomeView.qml",
                    "qml/components/AppCard.qml"]:
            c = (QT / rel).read_text(encoding="utf-8")
            for forbidden in ["FastBlur", "GaussianBlur", "blurEnabled",
                              "PaperGrainOverlay", "noise.png", "grain.png"]:
                self.assertNotIn(forbidden, c, f"{forbidden} forbidden in {rel} (Phase 1)")

    def test_appshell_hides_topbar_only_on_home(self) -> None:
        c = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        # topBar visibility gated on home; chip/objectNames preserved
        self.assertRegex(c, r'currentView\s*!==\s*"home"')
        self.assertIn('objectName: "dataSourceChip"', c)
        self.assertIn('objectName: "appShellStack"', c)
```

- [ ] **Step 2: 运行新测试，确认大部分红（资产那条应已绿）**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase1Tests -v`
Expected: `test_illustration_assets_exist` PASS（图已就位）；其余 FAIL（CMake/Theme/组件尚未实现）。

- [ ] **Step 3: Commit**

```bash
git add tests/test_qt_observer_static_contract.py
git commit -m "test(qt-redesign): Phase 1 static contract for warm tokens + illustration pipeline + Home"
```

---

## Task 2: Theme 增量暖色令牌

**Files:**
- Modify: `clients/qt_observer/qml/Theme.qml`

- [ ] **Step 1: 在 `report` QtObject 之后、`// ---- Spacing` 之前插入新令牌块**

定位 `Theme.qml` 中 `report` 对象的结束 `}`（约 L83）与 `// -------- Spacing`（约 L85）之间，插入：

```qml
    // ---------------------------------------------- Warm "Claude" palette (game client)
    // ADDITIVE — the dark tokens above keep their values so un-migrated pages do
    // not regress. Warm-surfaced pages (Home first) read from `warm` / `phase`.
    readonly property QtObject warm: QtObject {
        readonly property color canvas: "#faf9f5"
        readonly property color surfaceSoft: "#f5f0e8"
        readonly property color surfaceCard: "#efe9de"
        readonly property color surfaceCreamStrong: "#e8e0d2"
        readonly property color surfaceRaised: "#fffefb"
        readonly property color surfaceDark: "#181715"
        readonly property color surfaceDarkElevated: "#252320"
        readonly property color hairline: "#e6dfd8"
        readonly property color hairlineSoft: "#ebe6df"
        readonly property color ink: "#141413"
        readonly property color body: "#3d3d3a"
        readonly property color bodyStrong: "#252523"
        readonly property color muted: "#6c6a64"
        readonly property color mutedSoft: "#8e8b82"
        readonly property color primary: "#cc785c"
        readonly property color primaryActive: "#a9583e"
        readonly property color primaryDisabled: "#e6dfd8"
        readonly property color onPrimary: "#ffffff"
        readonly property color onDark: "#faf9f5"
        readonly property color onDarkSoft: "#a09d96"
        readonly property color accentAmber: "#e8a55a"
        readonly property color accentTeal: "#5db8a6"
        readonly property color success: "#5db872"
        readonly property color warning: "#d4a017"
        readonly property color error: "#c64545"
    }

    // Day / night phase surfaces (extracted from the home-scene illustrations).
    readonly property QtObject phase: QtObject {
        readonly property QtObject day: QtObject {
            readonly property color bg: "#f3e8d2"
            readonly property color ambient: "#e8c078"
            readonly property color sky: "#afc9e0"
        }
        readonly property QtObject night: QtObject {
            readonly property color bg: "#2a3a55"
            readonly property color sky: "#20304f"
            readonly property color glow: "#e8a85a"
        }
    }

    // System-stack-first font families (NO bundled fonts in Phase 1; see spec §3.4).
    // Single string per role; warm Text uses `font.family` + `font.contextFontMerging:
    // true` so a missing CJK glyph in (e.g.) "Inter" is merged from the system CJK
    // font at render time. No `font.families`, no `font.features`, no subsetting.
    readonly property QtObject fontFamilies: QtObject {
        readonly property string serif: "Source Han Serif SC"
        readonly property string sans:  "Inter"
        readonly property string mono:  "JetBrains Mono"
    }

    // Larger warm type scale (additive; existing `size` untouched).
    readonly property QtObject warmSize: QtObject {
        readonly property int displayXl: 48
        readonly property int displayLg: 36
        readonly property int displayMd: 28
        readonly property int titleLg: 22
        readonly property int titleMd: 18
        readonly property int bodyLg: 16
    }

    // Restrained damped motion for warm UI (Phase 1). Components reference these
    // instead of literal durations/easing so the feel stays consistent.
    //   color/hover -> Easing.OutCubic ; press/scale -> Easing.OutQuad
    readonly property QtObject anim: QtObject {
        readonly property int color: 140        // hover / colour cross-fade (120–160)
        readonly property int press: 100        // press / scale (80–120)
        readonly property real pressScale: 0.98
    }

    // Soft warm elevation (consumed by AppCard onLight via QtQuick.Effects MultiEffect).
    readonly property QtObject elevation: QtObject {
        readonly property color shadowColor: Qt.rgba(50 / 255, 38 / 255, 24 / 255, 0.18)
        readonly property real blur: 0.9
        readonly property real verticalOffset: 10
    }
```

- [ ] **Step 2: 运行 Theme 契约**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase1Tests.test_theme_has_warm_phase_font_tokens -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add clients/qt_observer/qml/Theme.qml
git commit -m "feat(qt-redesign): additive warm/phase/font/elevation Theme tokens (Phase 1)"
```

---

## Task 3: Illustrations 资产注册表 + CMake 资源/注册

**Files:**
- Create: `clients/qt_observer/qml/Illustrations.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`

- [ ] **Step 1: 创建 `qml/Illustrations.qml`**

```qml
pragma Singleton
import QtQuick

// Single-source registry of bundled illustration assets (game client redesign).
// Logical name -> resource URL, resolved relative to this module file so callers
// never hardcode qrc paths. A missing file surfaces as Image.Error at load time;
// every consumer MUST provide a no-asset fallback (see SceneBackground et al.).
QtObject {
    id: assets

    readonly property url homeSceneDay: Qt.resolvedUrl("../assets/illustrations/scene/home-day.png")
    readonly property url homeSceneNight: Qt.resolvedUrl("../assets/illustrations/scene/home-night.png")

    readonly property var _tarot: ({
        "werewolf": Qt.resolvedUrl("../assets/illustrations/tarot/werewolf.png"),
        "seer":     Qt.resolvedUrl("../assets/illustrations/tarot/seer.png"),
        "witch":    Qt.resolvedUrl("../assets/illustrations/tarot/witch.png"),
        "villager": Qt.resolvedUrl("../assets/illustrations/tarot/villager.png"),
        "guard":    Qt.resolvedUrl("../assets/illustrations/tarot/guard.png"),
        "hunter":   Qt.resolvedUrl("../assets/illustrations/tarot/hunter.png")
    })

    // Returns "" for an unknown role so the caller renders its fallback.
    function tarot(roleKey) {
        var k = ("" + roleKey).toLowerCase();
        return _tarot[k] !== undefined ? _tarot[k] : "";
    }

    function homeScene(phaseName) {
        return ("" + phaseName).toLowerCase() === "night" ? homeSceneNight : homeSceneDay;
    }
}
```

- [ ] **Step 2: 在 CMakeLists.txt 注册 singleton 属性**

在现有两行 singleton 声明后追加（约 L31 之后）：

```cmake
set_source_files_properties(qml/Illustrations.qml PROPERTIES QT_QML_SINGLETON_TYPE TRUE)
```

- [ ] **Step 3: 在 `qt_add_qml_module` 的 `QML_FILES` 段加入 Illustrations（仅它）**

在 `qml/I18n.qml` 行后加入（**本任务只注册 Illustrations**；SceneBackground/NavRail 留到它们各自被创建的 Task 4/5 再注册，确保每个 commit 都可 configure）：

```cmake
        qml/Illustrations.qml
```

- [ ] **Step 4: 在 `qt_add_qml_module(...)` 内、`QML_FILES` 段之后追加 `RESOURCES` 段**

在 `QML_FILES` 闭合的 `)` **之前**（仍在 `qt_add_qml_module(...)` 调用内）追加：

```cmake
    RESOURCES
        assets/illustrations/scene/home-day.png
        assets/illustrations/scene/home-night.png
        assets/illustrations/tarot/werewolf.png
        assets/illustrations/tarot/seer.png
        assets/illustrations/tarot/witch.png
        assets/illustrations/tarot/villager.png
        assets/illustrations/tarot/guard.png
        assets/illustrations/tarot/hunter.png
```

> 中间可构建性：本 commit 后 Illustrations + 8 资源已注册且 configure/build 仍可通过（不引用尚未创建的文件）。SceneBackground/NavRail 在 Task 4/5 创建后立即注册。

- [ ] **Step 5: 部分验证（完整 CMake 契约在 Task 5 转绿）**

`test_cmake_registers_new_qml_and_singleton_and_resources` 同时检查 SceneBackground/NavRail，故**本步仍会 FAIL**（预期）。这里只确认 Illustrations + 资源已加入：
Run: `$env:PYTHONPATH='src'; python -c "import pathlib; t=pathlib.Path('clients/qt_observer/CMakeLists.txt').read_text(encoding='utf-8'); assert 'qml/Illustrations.qml' in t and 'QT_QML_SINGLETON_TYPE' in t and 'assets/illustrations/scene/home-day.png' in t and 'RESOURCES' in t; print('illustrations+resources OK')"`
Expected: `illustrations+resources OK`

- [ ] **Step 6: Commit**

```bash
git add clients/qt_observer/qml/Illustrations.qml clients/qt_observer/CMakeLists.txt
git commit -m "feat(qt-redesign): Illustrations asset registry + bundle 8 PNGs via RESOURCES"
```

---

## Task 4: SceneBackground 组件（插画 + scrim + fallback）

**Files:**
- Create: `clients/qt_observer/qml/components/SceneBackground.qml`

- [ ] **Step 1: 创建组件**

```qml
import QtQuick
import qt_observer

// Full-bleed illustration background with readability scrims. Falls back to a
// phase gradient when the asset is missing or still loading (never a white gap).
Item {
    id: root
    anchors.fill: parent

    property string phase: "day"            // "day" | "night"
    readonly property bool _night: phase === "night"

    // (1) Phase-gradient floor — also shown while the image loads or on error.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root._night ? Theme.phase.night.sky : Theme.phase.day.sky }
            GradientStop { position: 1.0; color: root._night ? Theme.phase.night.bg  : Theme.phase.day.bg }
        }
    }

    // (2) The illustration itself — only painted once fully loaded.
    Image {
        id: art
        anchors.fill: parent
        source: Illustrations.homeScene(root.phase)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        visible: status === Image.Ready
    }

    // (3) Readability scrims — lift the left rail/hero and the right cards off the
    // busy illustration so overlaid text stays legible (spec §4.3).
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: Theme.withAlpha(root._night ? Theme.phase.night.bg : Theme.warm.canvas, root._night ? 0.72 : 0.62) }
            GradientStop { position: 0.40; color: "transparent" }
            GradientStop { position: 0.70; color: "transparent" }
            GradientStop { position: 1.00; color: Theme.withAlpha(root._night ? Theme.phase.night.bg : Theme.warm.canvas, root._night ? 0.66 : 0.52) }
        }
    }
}
```

- [ ] **Step 2: 在 CMakeLists.txt 的 components 区注册它**

```cmake
        qml/components/SceneBackground.qml
```
（commit 后仍可 configure：文件已存在。）

- [ ] **Step 3: 运行 SceneBackground 契约**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase1Tests.test_scene_background_has_no_asset_fallback -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add clients/qt_observer/qml/components/SceneBackground.qml clients/qt_observer/CMakeLists.txt
git commit -m "feat(qt-redesign): SceneBackground (illustration + scrim + phase-gradient fallback)"
```

---

## Task 5: NavRail 组件（安静左栏，v1 四态）

**Files:**
- Create: `clients/qt_observer/qml/components/NavRail.qml`

- [ ] **Step 1: 创建组件**

```qml
import QtQuick
import QtQuick.Controls
import qt_observer

// Quiet left navigation rail (game client). v1 does FOUR things only: selected
// state, disabled state, narrow/collapsed state, tooltip label. No hover
// flourishes, no icon animation. It is an entry, not a decorative strip.
Item {
    id: root
    objectName: "navRail"

    // items: [{ key, label, glyph, enabled }]
    property var items: []
    property string currentKey: "home"
    property bool collapsed: width < 96
    signal activated(string key)

    implicitWidth: 220

    Rectangle {
        anchors.fill: parent
        color: Theme.warm.surfaceCard

        Rectangle {                       // right hairline seam
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.warm.hairline
        }
    }

    Column {
        id: list
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Theme.space.xl
        spacing: Theme.space.xs

        Repeater {
            model: root.items
            delegate: Item {
                id: rowItem
                required property var modelData
                width: list.width
                height: 46
                enabled: modelData.enabled === undefined ? true : modelData.enabled
                opacity: enabled ? 1.0 : 0.4

                readonly property bool _selected: root.currentKey === modelData.key

                Rectangle {
                    id: pill
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space.sm
                    anchors.rightMargin: Theme.space.sm
                    radius: Theme.radius.md
                    color: rowItem._selected ? Theme.warm.surfaceCreamStrong : "transparent"

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.space.md
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Theme.space.md

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: rowItem.modelData.glyph || "•"
                            color: rowItem._selected ? Theme.warm.primary : Theme.warm.muted
                            font.pixelSize: 18
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: !root.collapsed
                            text: rowItem.modelData.label || ""
                            color: rowItem._selected ? Theme.warm.ink : Theme.warm.body
                            font.family: Theme.fontFamilies.sans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.warmSize.bodyLg
                            font.weight: rowItem._selected ? Theme.weight.semibold : Theme.weight.medium
                        }
                    }
                }

                HoverHandler {
                    id: hov
                    enabled: rowItem.enabled
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    enabled: rowItem.enabled
                    onTapped: root.activated(rowItem.modelData.key)
                }

                // Tooltip label when collapsed — attached property only, no hover
                // animation (the single v1 "extra").
                ToolTip.visible: root.collapsed && hov.hovered
                ToolTip.text: rowItem.modelData.label || ""
                ToolTip.delay: 300
            }
        }
    }
}
```

- [ ] **Step 2: 在 CMakeLists.txt 的 components 区注册它**

```cmake
        qml/components/NavRail.qml
```

- [ ] **Step 3: 运行 NavRail 契约 + 完整 CMake 契约（此时应转绿）**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase1Tests.test_navrail_contract tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase1Tests.test_cmake_registers_new_qml_and_singleton_and_resources -v`
Expected: 两条均 PASS（Illustrations + SceneBackground + NavRail 全部注册）。

- [ ] **Step 4: Commit**

```bash
git add clients/qt_observer/qml/components/NavRail.qml clients/qt_observer/CMakeLists.txt
git commit -m "feat(qt-redesign): NavRail quiet left navigation (selected/disabled/collapsed/tooltip)"
```

---

## Task 6: 共享组件加 `onLight` 暖色路径

> 默认 `onLight: false` → 原暗色行为不变（现有页面零回归）。`onLight: true` → 暖色路径。

**Files:**
- Modify: `clients/qt_observer/qml/components/AppButton.qml`
- Modify: `clients/qt_observer/qml/components/AppCard.qml`
- Modify: `clients/qt_observer/qml/components/StatusBadge.qml`
- Modify: `clients/qt_observer/qml/components/SectionHeader.qml`
- Modify: `clients/qt_observer/qml/components/EmptyState.qml`

- [ ] **Step 1: AppButton — 加 `onLight` + 暖色解析**

把 `AppButton.qml` 的属性与三个 `readonly property color` 解析块替换为下列（保留 `implicitHeight/implicitWidth/opacity` 等其余不变）：

```qml
    property string text: ""
    property string variant: "primary"
    property bool onLight: false
    signal clicked

    implicitHeight: 40
    implicitWidth: Math.max(104, label.implicitWidth + Theme.space.xxl * 2)
    opacity: enabled ? 1.0 : 0.45

    readonly property color _bg: {
        if (onLight) {
            if (variant === "primary") return Theme.warm.primary;
            if (variant === "danger")  return Theme.warm.error;
            if (variant === "secondary") return Theme.warm.surfaceRaised;
            return "transparent";  // ghost
        }
        if (variant === "primary") return Theme.color.primary;
        if (variant === "danger") return Theme.color.danger;
        if (variant === "secondary") return Theme.color.surfaceAlt;
        return "transparent";
    }
    readonly property color _bgHover: {
        if (onLight) {
            if (variant === "primary") return Theme.warm.primaryActive;
            if (variant === "danger")  return Qt.darker(Theme.warm.error, 1.1);
            if (variant === "secondary") return Theme.warm.surfaceSoft;
            return Theme.withAlpha(Theme.warm.ink, 0.05);
        }
        if (variant === "primary") return Theme.color.primaryHover;
        if (variant === "danger") return Qt.lighter(Theme.color.danger, 1.12);
        if (variant === "secondary") return Qt.lighter(Theme.color.surfaceAlt, 1.18);
        return Theme.withAlpha(Theme.color.text, 0.06);
    }
    readonly property color _fg: {
        if (onLight) {
            if (variant === "primary" || variant === "danger") return Theme.warm.onPrimary;
            if (variant === "secondary") return Theme.warm.ink;
            return Theme.warm.body;  // ghost
        }
        if (variant === "primary") return Theme.color.primaryText;
        if (variant === "danger") return "#FFFFFF";
        if (variant === "secondary") return Theme.color.text;
        return Theme.color.textSecondary;
    }
    readonly property bool _outlined: variant === "ghost" || variant === "secondary"
    readonly property color _border: onLight ? Theme.warm.hairline : Theme.color.border
    readonly property color _borderHover: onLight ? Theme.warm.mutedSoft : Theme.color.borderStrong
```

并把内部 `Rectangle` 的 `radius`/`color`/`border`/`scale`/`Behavior` 与 `label` 字体替换为（统一走 `Theme.anim` 阻尼，按压 scale 0.98）：

```qml
        radius: Theme.radius.md
        color: hover.hovered ? root._bgHover : root._bg
        border.width: root._outlined ? 1 : 0
        border.color: hover.hovered ? root._borderHover : root._border
        scale: tap.pressed ? Theme.anim.pressScale : 1.0

        Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutQuad } }
```
```qml
        Text {
            id: label
            anchors.centerIn: parent
            text: root.text
            color: root._fg
            font.family: root.onLight ? Theme.fontFamilies.sans : Theme.font.family
            font.contextFontMerging: root.onLight
            font.pixelSize: root.onLight ? Theme.warmSize.bodyLg : Theme.size.body
            font.weight: Theme.weight.semibold
        }
```

- [ ] **Step 2: AppCard — 加 `onLight` + 柔和投影**

把 `AppCard.qml` 整体替换为：

```qml
import QtQuick
import QtQuick.Effects
import qt_observer

// Surface container. Dark (default): bordered + top hairline (existing pages).
// onLight: warm raised card — cream surface, hairline, soft diffuse shadow.
Rectangle {
    id: root

    property bool interactive: false
    property bool onLight: false
    readonly property bool hovered: hoverHandler.hovered

    radius: Theme.radius.lg
    color: onLight
           ? ((hovered && interactive) ? Theme.warm.surfaceSoft : Theme.warm.surfaceRaised)
           : ((hovered && interactive) ? Theme.color.surfaceAlt : Theme.color.surface)
    border.width: 1
    // onLight: very faint ink hairline (alpha 0.08) — depth comes from the soft
    // shadow + surface, not a heavy border.
    border.color: onLight
                  ? Theme.withAlpha(Theme.warm.ink, 0.08)
                  : ((hovered && interactive) ? Theme.color.borderStrong : Theme.color.border)

    Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
    Behavior on border.color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }

    // Soft warm elevation (onLight only).
    layer.enabled: root.onLight
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: Theme.elevation.shadowColor
        shadowBlur: Theme.elevation.blur
        shadowVerticalOffset: Theme.elevation.verticalOffset
        shadowHorizontalOffset: 0
    }

    // Top hairline highlight — dark theme only (warm uses the soft shadow).
    Rectangle {
        visible: !root.onLight
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 1
        height: 1
        color: Theme.color.hairline
    }

    HoverHandler {
        id: hoverHandler
        enabled: root.interactive
    }
}
```

- [ ] **Step 3: StatusBadge — 加 `onLight`**

在 `StatusBadge.qml` 加属性 `property bool onLight: false`，并把 dot 与 label 的颜色改为按 `onLight` 在暖底上加深（保证对比度）。把内部 `GlowDot.color` 与 `Text.color` 替换为：

```qml
        GlowDot {
            anchors.verticalCenter: parent.verticalCenter
            diameter: 7
            color: root.onLight ? Qt.darker(Theme.statusColor(root.status), 1.15) : Theme.statusColor(root.status)
            pulse: root.status === "running" || root.status === "connected"
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root._label
            color: root.onLight ? Qt.darker(Theme.statusColor(root.status), 1.25) : Theme.statusColor(root.status)
            font.family: Theme.font.family
            font.pixelSize: Theme.size.micro
            font.weight: Theme.weight.semibold
        }
```
（`color`/`border.color` 用的 `statusTint`/`statusColor` 在暖底上仍可读，保持不变。）

- [ ] **Step 4: SectionHeader — 加 `onLight`**

```qml
    property string title: ""
    property string caption: ""
    property bool onLight: false
```
标题 `Text` 改为：

```qml
        text: root.title
        color: root.onLight ? Theme.warm.ink : Theme.color.text
        font.family: root.onLight ? Theme.fontFamilies.serif : Theme.font.family
        font.contextFontMerging: root.onLight
        font.pixelSize: root.onLight ? Theme.warmSize.titleLg : Theme.size.h2
        font.weight: Theme.weight.semibold
        lineHeightMode: Text.ProportionalHeight
        lineHeight: 1.15
```
caption `Text.color` 改 `root.onLight ? Theme.warm.muted : Theme.color.textMuted`（字体不变）。

- [ ] **Step 5: EmptyState — 加 `onLight`**

```qml
    property string title: "Nothing here yet"
    property string subtitle: ""
    property bool onLight: false
```
`wolfMark` 的 `ctx.fillStyle` 改为：`ctx.fillStyle = root.onLight ? "rgba(20,20,19,0.10)" : "rgba(245,245,245,0.12)"`（并在 `onPaint` 中 `requestPaint` 依赖 `onLight` 变化：加 `onOnLightChanged: wolfMark.requestPaint()`）。title `Text.color` 改 `root.onLight ? Theme.warm.body : Theme.color.textSecondary`；subtitle `Text.color` 改 `root.onLight ? Theme.warm.muted : Theme.color.textMuted`。

- [ ] **Step 6: 跑全量静态契约（确认现有契约零回归）**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract -v`
Expected：**现有所有契约类全部 PASS（零回归）**；`QtObserverGameRedesignPhase1Tests` 中 `test_home_uses_new_design_system` 与 `test_appshell_hides_topbar_only_on_home` 此时**仍 FAIL（预期）**——它们在 Task 7/8 完成后才转绿。**本步不得宣称全量全绿。** 全量全绿的硬门槛在 Task 8 之后。

- [ ] **Step 7: Commit**

```bash
git add clients/qt_observer/qml/components/AppButton.qml clients/qt_observer/qml/components/AppCard.qml clients/qt_observer/qml/components/StatusBadge.qml clients/qt_observer/qml/components/SectionHeader.qml clients/qt_observer/qml/components/EmptyState.qml
git commit -m "feat(qt-redesign): add onLight warm path to shared components (default dark unchanged)"
```

---

## Task 7: AppShell — home 上隐藏顶栏并重锚

**Files:**
- Modify: `clients/qt_observer/qml/AppShell.qml`

- [ ] **Step 1: 顶栏按 home 隐藏（替换那一行 `height: 52`，不要新增第二个 height）**

把 `topBar` 的 `Item { id: topBar ... }` 里现有的 `height: 52`（约 L48）**替换**为下面两行（`visible` + 单个 `height` 三元）：

```qml
        visible: root.currentView !== "home"
        height: root.currentView !== "home" ? 52 : 0
```
> ⚠️ 必须是**替换** `height: 52`，不能在它后面再加一行 `height:` —— 同一 `Item` 两个 `height` 属性是 QML 重复属性错误。

- [ ] **Step 2: StackView 顶部锚改为条件**

把 StackView 的 `anchors.top: topBar.bottom` 改为：

```qml
        anchors.top: topBar.visible ? topBar.bottom : parent.top
```

> 其它页面 `currentView !== "home"` → 顶栏照常显示、锚点照旧 → 零回归。`dataSourceChip`/`appShellStack` objectName 与绑定均保留。

- [ ] **Step 3: AppShell 契约**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase1Tests.test_appshell_hides_topbar_only_on_home -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add clients/qt_observer/qml/AppShell.qml
git commit -m "feat(qt-redesign): hide AppShell top bar on home, full-bleed for the warm hub"
```

---

## Task 8: HomeView 重做为样板页

**Files:**
- Modify: `clients/qt_observer/qml/HomeView.qml`

- [ ] **Step 1: 整体替换 HomeView.qml**

```qml
import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Warm game-client home (Phase 1 sample page). Layout: NavRail (left) +
// SceneBackground (warm illustration) + editorial hero + tarot strip + recent
// runs. ObserverClient bindings, navigation calls and objectNames preserved.
Item {
    id: root
    objectName: "homeView"

    // Day/night phase for the home backdrop (screenshot matrix toggles this).
    property string phase: "day"

    Component.onCompleted: ObserverClient.checkHealth()

    SceneBackground {
        id: scene
        phase: root.phase
    }

    // ----------------------------------------------------------- Left NavRail
    NavRail {
        id: rail
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 220
        currentKey: "home"
        items: [
            { key: "home",    label: I18n.t("今夜对局", "Tonight"),    glyph: "☾", enabled: true },
            { key: "setup",   label: I18n.t("开始对局", "New Match"),  glyph: "✦", enabled: true },
            { key: "seats",   label: I18n.t("席位一览", "Seats"),      glyph: "◍", enabled: false },
            { key: "events",  label: I18n.t("实时事件", "Events"),     glyph: "≋", enabled: false },
            { key: "history", label: I18n.t("历史对局", "History"),    glyph: "❡", enabled: true },
            { key: "deck",    label: I18n.t("收藏牌库", "Card Deck"),  glyph: "🂠", enabled: false },
            { key: "settings",label: I18n.t("设置", "Settings"),       glyph: "⚙", enabled: true }
        ]
        onActivated: function(key) {
            if (key === "setup")    root.StackView.view.parent.navigateSetup()
            else if (key === "history") {
                ObserverClient.refreshRuns()
                root.StackView.view.parent.navigateHistory()
            }
            else if (key === "settings") root.StackView.view.parent.navigateProviderSettings()
        }
    }

    // --------------------------------------------------------- Content column
    Flickable {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        contentHeight: content.implicitHeight + Theme.space.huge * 2
        clip: true

        Column {
            id: content
            x: Theme.space.huge
            y: Theme.space.huge
            width: Math.min(parent.width - Theme.space.huge * 2, 760)
            spacing: Theme.space.xxl

            // ----------------------------------------------------- (A) HERO
            Column {
                width: parent.width
                spacing: Theme.space.md

                Text {
                    text: I18n.t("观 战 席", "OBSERVER COCKPIT")
                    color: Theme.warm.primary
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    font.weight: Theme.weight.bold
                    font.letterSpacing: 2
                }

                Text {
                    text: I18n.t("狼人杀 · 观察席", "Werewolf Observer")
                    color: Theme.warm.ink
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.displayXl
                    font.weight: Theme.weight.medium
                    font.letterSpacing: -1
                    lineHeightMode: Text.ProportionalHeight
                    lineHeight: 1.12
                }

                Text {
                    width: parent.width
                    text: I18n.t("观察 AI 玩家如何欺骗、推理与投票 —— 一夜一局。",
                                 "Watch AI agents deceive, deduce, and vote — one night at a time.")
                    color: Theme.warm.body
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.bodyLg
                    wrapMode: Text.WordWrap
                    lineHeightMode: Text.ProportionalHeight
                    lineHeight: 1.5
                }

                Row {
                    spacing: Theme.space.sm
                    topPadding: Theme.space.xs
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: I18n.t("服务器", "Server")
                        color: Theme.warm.muted
                        font.family: Theme.fontFamilies.sans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                    }
                    StatusBadge {
                        id: serverStatusBadge
                        objectName: "serverStatusBadge"
                        onLight: true
                        anchors.verticalCenter: parent.verticalCenter
                        status: ObserverClient.connected ? "connected" : "disconnected"
                    }
                }

                Row {
                    spacing: Theme.space.md
                    topPadding: Theme.space.sm
                    AppButton {
                        id: startNewMatchButton
                        objectName: "startNewMatchButton"
                        onLight: true
                        text: I18n.t("开始新对局", "Start New Match")
                        variant: "primary"
                        onClicked: root.StackView.view.parent.navigateSetup()
                    }
                    AppButton {
                        id: historyButton
                        objectName: "historyButton"
                        onLight: true
                        text: I18n.t("历史对局", "History")
                        variant: "secondary"
                        onClicked: {
                            ObserverClient.refreshRuns()
                            root.StackView.view.parent.navigateHistory()
                        }
                    }
                }
            }

            // ------------------------------------------ (B) TAROT IDENTITY STRIP
            Row {
                width: parent.width
                spacing: Theme.space.md
                Repeater {
                    model: ["werewolf", "seer", "witch", "villager", "guard", "hunter"]
                    delegate: Rectangle {
                        required property var modelData
                        width: (content.width - Theme.space.md * 5) / 6
                        height: width * 1.5
                        radius: Theme.radius.md
                        color: Theme.warm.surfaceCreamStrong
                        border.width: 1
                        border.color: Theme.warm.hairline
                        clip: true

                        Image {
                            id: tarotArt
                            anchors.fill: parent
                            source: Illustrations.tarot(modelData)
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            cache: true
                            visible: status === Image.Ready
                        }
                        // fallback: role name whenever the art is not loaded —
                        // missing url OR a real load error (Image.Error), never blank.
                        Text {
                            anchors.centerIn: parent
                            visible: tarotArt.status !== Image.Ready
                            text: Theme.humanizeRole(modelData)
                            color: Theme.warm.muted
                            font.family: Theme.fontFamilies.serif
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                        }
                    }
                }
            }

            // ------------------------------------------------ (C) RECENT RUNS
            AppCard {
                width: parent.width
                onLight: true
                implicitHeight: runsBody.implicitHeight + Theme.space.xxl * 2

                Column {
                    id: runsBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.xxl
                    spacing: Theme.space.lg

                    SectionHeader {
                        onLight: true
                        title: I18n.t("最近对局", "Recent Runs")
                    }

                    EmptyState {
                        width: parent.width
                        onLight: true
                        visible: ObserverClient.runItems.length === 0
                        title: I18n.t("暂无对局", "No matches yet")
                        subtitle: I18n.t("开始一局，在此实时观战。", "Start a new match to watch it unfold here.")
                    }

                    ListView {
                        id: recentRunsList
                        objectName: "recentRunsList"
                        width: parent.width
                        height: 180
                        clip: true
                        visible: ObserverClient.runItems.length > 0
                        model: ObserverClient.runItems
                        spacing: Theme.space.xs
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: Item {
                            required property var modelData
                            width: ListView.view.width
                            height: 44

                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.radius.md
                                color: hover.hovered ? Theme.warm.surfaceSoft : "transparent"
                                Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }

                                // Fixed two columns: run_id (mono, elide middle) | status badge (fixed width).
                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: Theme.space.md
                                    anchors.right: badgeCol.left
                                    anchors.rightMargin: Theme.space.md
                                    anchors.verticalCenter: parent.verticalCenter
                                    elide: Text.ElideMiddle
                                    text: modelData.run_id || ""
                                    color: Theme.warm.body
                                    font.family: Theme.fontFamilies.mono
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.size.small
                                }
                                Item {
                                    id: badgeCol
                                    width: 112
                                    anchors.right: parent.right
                                    anchors.rightMargin: Theme.space.md
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    StatusBadge {
                                        onLight: true
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        status: modelData.status || ""
                                    }
                                }
                            }

                            HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                            TapHandler {
                                onTapped: {
                                    ObserverClient.openRun(modelData.run_id)
                                    root.StackView.view.parent.navigateCockpit()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 2: HomeView 契约 + 全量静态契约**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract -v`
Expected: 全绿（含 `QtObserverGameRedesignPhase1Tests` 全 PASS、`REQUIRED_OBJECT_NAMES["qml/HomeView.qml"]` 仍 PASS）。

- [ ] **Step 3: Commit**

```bash
git add clients/qt_observer/qml/HomeView.qml
git commit -m "feat(qt-redesign): rebuild HomeView on warm system (NavRail + scene + tarot strip)"
```

---

## Task 9: 构建 + 截图验收

> 读 skill `verifying-qt-observer-ui` 取准确的 Qt 工具链/构建/截图命令；下列为形态参考。

- [ ] **Step 1: 构建（exit 0）**

Run（PowerShell，路径以 skill 为准）:
```powershell
cmake -S clients/qt_observer -B .tmp/qt-observer-build -G "MinGW Makefiles" -DCMAKE_PREFIX_PATH=<Qt6-mingw>
cmake --build .tmp/qt-observer-build
```
Expected: 配置 + 编译 exit 0，资源 8 张 PNG 进 qrc，无 QML 编译错误。

- [ ] **Step 2: 运行 + 截图矩阵（按 spec §8.1，Phase 1 覆盖 Home）**

启动 app，截图：
- HomeView **白天**（默认 `phase: "day"`）
- HomeView **黑夜**（临时把 HomeView 根 `property string phase: "night"` 或运行期切换后截）
- 至少一档小屏：窗口 1280×720（验证 NavRail/hero/最近对局不溢出、scrim 下文字可读）

逐项肉眼复核：① 暖奶油 + 插画背景，文字坐在 scrim 上清晰；② 衬线大标题足够重、正文 16px 不再细淡、行高不松不飘；③ 珊瑚主按钮 + 描边次按钮 + 卡片柔和投影有质感不廉价（无 glossy 渐变/毛玻璃/纸张噪点）；④ 左栏 NavRail 安静（选中态/禁用态正确、无花哨动效/发光）；⑤ 塔罗条 6 张正常显示（缺图或加载失败均退角色名，不空白）；⑥ Recent Runs 双列对齐稳定（run_id 中段省略 + 固定宽 badge 列）。

> 若截图后整体仍显得"太平"：**不要**在 Phase 1 加纸张噪点/毛玻璃；在本任务的 review 结论里建议一个 **Phase 1.5 单独小任务**（仅补一个低强度 paper-grain overlay）再单独评估。

- [ ] **Step 3: 冒烟——其它页面零回归**

切到 MatchSetup / History / 一个 cockpit，确认顶栏正常显示、布局未塌陷、暗色未变（仅证明无回归，不要求美化）。

- [ ] **Step 4: 截图归档 + Commit**

把截图存入 `.tmp/` 或 review 目录（不入库），在 commit 说明里记录验收结论：

```bash
git commit --allow-empty -m "test(qt-redesign): Phase 1 build green + Home day/night + small-screen + no-regression screenshots verified"
```

---

## 自检（Spec 覆盖）

- spec §2 铁律 #4 scrim → Task 4 SceneBackground scrim 层 ✓
- spec §2 #5 阵营色仅小强调 → Phase 1 未引入阵营填充；tarot 条用资产非色块 ✓（roleTint 规则在后续含阵营 UI 的页面落地）
- spec §3.2 阶段色 / §3.4 系统字体栈优先（不打包）→ Task 2 `phase`/`fontFamilies` ✓
- spec §4 资产管线 + §4.4 fallback → Task 3 Illustrations + Task 4/8 fallback（Scene/Image/tarot 角色名兜底）✓
- spec §5 NavRail v1 四态 / onLight 组件 → Task 5 / Task 6 ✓
- spec §6 首页蓝本（NavRail + 场景 + 塔罗条 + 最近对局）→ Task 8 ✓
- spec §7.1 阶段落到真实页面（HomeView）→ Task 8/9 ✓
- spec §7.2 数据绑定语义不变（objectName/navigate*/ObserverClient 绑定保留）→ Task 8 ✓
- spec §8.1 截图矩阵（Home 昼/夜 + 小屏）→ Task 9 ✓
- 未覆盖（按设计留给后续阶段，非缺口）：完整 `TarotCard`/`CharacterAvatar`/`PhaseBackground` 组件（Phase 2）、字体打包增强（可选小任务）、其它页面迁移（Phase 3）。
