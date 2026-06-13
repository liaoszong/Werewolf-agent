# Phase 2 · LiveCockpit 上帝视角圆桌重做 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把对局直播页(`TheaterView`)从冷炭灰审计面重做成「上帝视角俯视圆桌环」暖色插画客户端,并提供一个**首页静态预览入口**(烤死样例、不开真局)作为最早可截图验收点。

**Architecture:** 资产分层(空对称椭圆背景昼/夜 + 6 圆形角色头像)+ 一个**表现型组件 `CockpitSurface`**(数据全经属性注入,内含椭圆落位、悬浮件、左栏)+ 两个宿主(`DesignPreviewView` 喂烤死样例 / `TheaterView` 绑真实 `ObserverClient`)。数据绑定语义逐字保留;页面长相全新。

**Tech Stack:** Qt 6.10 QML(mingw,工具链在 F:)· QML 单例 `Theme`/`I18n`/`Illustrations` · Python `unittest` static contract 作结构门 · cmake 构建 + offscreen/真机截图自验。

**Spec:** `docs/superpowers/specs/2026-06-13-livecockpit-godseye-redesign-phase2-design.md`

---

## 关键约定(贯穿全计划)

- **构建命令**(每次改 QML 后):
  ```bash
  export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
  "F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
  ```
  exit 0 = 已注册 QML 语法全有效。**新建 .qml 必须加进 `CMakeLists.txt` 的 `qt_add_qml_module(... QML_FILES ...)`,否则运行时白屏。**
- **结构门**(每次改 QML/契约后):
  ```bash
  NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract
  ```
  必须绿。
- **截图自验**:在 `AppShell.qml` 临时加 `Timer` 导航到目标视图 → `root.grabToImage(r => r.saveToFile("G:/Werewolf-agent/.tmp/shot_X.png"))` → `Qt.quit()`;`QT_QPA_PLATFORM=offscreen` 跑;**MultiEffect/阴影 offscreen 不渲染,需真机**;跑完 `git checkout -- qml/AppShell.qml` 撤临时 harness。残留进程锁 exe:`taskkill //F //IM appqt_observer.exe`。
- **提交纪律**(共享 main):每次 commit 前 `git branch --show-current` + `git status --short`(有非本任务 staged 就停)。实现**在隔离 worktree**(superpowers:using-git-worktrees)。
- **不碰**:runtime/scoring/provider/模型可见 prompt/日志契约/observer 后端字段(`src/**`、`tests/**` 除 `test_qt_observer_static_contract.py`)。

---

## 文件结构

**新建:**
- `clients/qt_observer/assets/illustrations/scene/table-day.png` · `table-night.png` — 空圆桌背景昼/夜
- `clients/qt_observer/assets/illustrations/avatars/{werewolf,seer,witch,villager,guard,hunter}.png` — 6 圆形角色头像
- `clients/qt_observer/qml/components/CharacterAvatar.qml` — 单座头像(圆肖像+色环+名牌+存活/发言/出局)
- `clients/qt_observer/qml/components/PhaseBackground.qml` — table 昼/夜交叉淡入
- `clients/qt_observer/qml/components/PhaseIndicator.qml` — 桌心阶段徽记(太阳/月亮+轮次)
- `clients/qt_observer/qml/components/CockpitSurface.qml` — 表现型直播面(椭圆环+悬浮件+左栏),数据全经属性
- `clients/qt_observer/qml/DesignPreviewView.qml` — 静态宿主(烤死样例)

**修改:**
- `clients/qt_observer/qml/Illustrations.qml` — 加 tableDay/tableNight + `avatar(roleKey)`
- `clients/qt_observer/CMakeLists.txt` — 注册新 QML + RESOURCES
- `clients/qt_observer/qml/HomeView.qml` — 加 `designPreviewButton`
- `clients/qt_observer/qml/AppShell.qml` — 加 `navigateDesignPreview` + 路由
- `clients/qt_observer/qml/TheaterView.qml` — 重写为 `CockpitSurface` 的 live 宿主
- `clients/qt_observer/qml/components/EvidenceConsole.qml` — 加 `showPerspectiveSwitcher` 开关
- `tests/test_qt_observer_static_contract.py` — Phase2 契约 + 删除 LiveCockpitView 相关断言

**删除:**
- `clients/qt_observer/qml/LiveCockpitView.qml`(死代码,Task 8 处理)

> **SeatRing.qml 不动**:它的 docked 模式承载结算棋盘(`SettlementView` 关键路径)。新椭圆环在 `CockpitSurface` 内用 `CharacterAvatar` 重建,避免destabilize 结算。(偏离 spec §6「改造 SeatRing」的工程取舍,降风险。)

---

## Task 1: 资产入库 + Illustrations 注册 + CMake RESOURCES

**Files:**
- Create: `clients/qt_observer/assets/illustrations/scene/table-day.png`, `scene/table-night.png`, `avatars/{werewolf,seer,witch,villager,guard,hunter}.png`
- Modify: `clients/qt_observer/qml/Illustrations.qml`, `clients/qt_observer/CMakeLists.txt`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: 拷贝资产到仓库(已生成的 8 张在 `.superpowers/brainstorm/862-1781342388/content/`)**

```bash
cd "G:/Werewolf-agent/clients/qt_observer/assets/illustrations"
mkdir -p avatars
SRC="G:/Werewolf-agent/.superpowers/brainstorm/862-1781342388/content"
cp "$SRC/bg-day.png"      scene/table-day.png
cp "$SRC/bg-night.png"    scene/table-night.png
cp "$SRC/av-werewolf.png" avatars/werewolf.png
cp "$SRC/av-seer.png"     avatars/seer.png
cp "$SRC/av-witch.png"    avatars/witch.png
cp "$SRC/av-villager.png" avatars/villager.png
cp "$SRC/av-guard.png"    avatars/guard.png
cp "$SRC/av-hunter.png"   avatars/hunter.png
ls -la scene/table-*.png avatars/*.png
```

- [ ] **Step 2: 压缩(母版另存;pngquant 有则压,无则跳过并记 TODO)**

```bash
# 母版备份到 .tmp(不入仓),应用内用压缩版
cd "G:/Werewolf-agent/clients/qt_observer/assets/illustrations"
command -v pngquant >/dev/null && \
  pngquant --force --quality=70-92 --ext .png scene/table-day.png scene/table-night.png avatars/*.png \
  || echo "pngquant 不可用:先用母版,压缩留作收尾(打包优化)"
```

- [ ] **Step 3: Illustrations.qml 加 table 背景 + avatar 注册表**

`clients/qt_observer/qml/Illustrations.qml`,在 `homeSceneNight` 行后加:

```qml
    readonly property url tableDay: Qt.resolvedUrl("../assets/illustrations/scene/table-day.png")
    readonly property url tableNight: Qt.resolvedUrl("../assets/illustrations/scene/table-night.png")

    readonly property var _avatar: ({
        "werewolf": Qt.resolvedUrl("../assets/illustrations/avatars/werewolf.png"),
        "seer":     Qt.resolvedUrl("../assets/illustrations/avatars/seer.png"),
        "witch":    Qt.resolvedUrl("../assets/illustrations/avatars/witch.png"),
        "villager": Qt.resolvedUrl("../assets/illustrations/avatars/villager.png"),
        "guard":    Qt.resolvedUrl("../assets/illustrations/avatars/guard.png"),
        "hunter":   Qt.resolvedUrl("../assets/illustrations/avatars/hunter.png")
    })
```

并在 `function tarot` 后加(`table` 选择器 + `avatar` 查询):

```qml
    function table(phaseName) {
        return ("" + phaseName).toLowerCase() === "night" ? tableNight : tableDay;
    }

    // Returns "" for an unknown role so the caller renders its fallback.
    function avatar(roleKey) {
        var k = ("" + roleKey).toLowerCase();
        return _avatar[k] !== undefined ? _avatar[k] : "";
    }
```

- [ ] **Step 4: CMakeLists 注册 8 个 RESOURCES**

`clients/qt_observer/CMakeLists.txt` 的 `RESOURCES` 段(现以 `tarot/hunter.png` 结尾),在 `)` 前加:

```cmake
        assets/illustrations/scene/table-day.png
        assets/illustrations/scene/table-night.png
        assets/illustrations/avatars/werewolf.png
        assets/illustrations/avatars/seer.png
        assets/illustrations/avatars/witch.png
        assets/illustrations/avatars/villager.png
        assets/illustrations/avatars/guard.png
        assets/illustrations/avatars/hunter.png
```

- [ ] **Step 5: 加 Phase2 契约测试类(先只测资产+CMake,写成会失败)**

`tests/test_qt_observer_static_contract.py` 末尾(`if __name__` 前)加:

```python
class QtObserverGameRedesignPhase2Tests(unittest.TestCase):
    """游戏客户端重做 Phase 2:上帝视角圆桌 LiveCockpit + 首页静态预览。"""

    PHASE2_ASSETS = [
        "assets/illustrations/scene/table-day.png",
        "assets/illustrations/scene/table-night.png",
        "assets/illustrations/avatars/werewolf.png",
        "assets/illustrations/avatars/seer.png",
        "assets/illustrations/avatars/witch.png",
        "assets/illustrations/avatars/villager.png",
        "assets/illustrations/avatars/guard.png",
        "assets/illustrations/avatars/hunter.png",
    ]

    def test_phase2_assets_exist(self) -> None:
        for rel in self.PHASE2_ASSETS:
            self.assertTrue((QT / rel).exists(), f"missing Phase 2 asset: {rel}")

    def test_phase2_assets_registered_in_cmake(self) -> None:
        cmake = (QT / "CMakeLists.txt").read_text(encoding="utf-8")
        for rel in self.PHASE2_ASSETS:
            self.assertIn(rel, cmake, f"CMakeLists must bundle resource {rel}")

    def test_illustrations_registers_table_and_avatar(self) -> None:
        c = (QT / "qml/Illustrations.qml").read_text(encoding="utf-8")
        for tok in ["tableDay", "tableNight", "function table(", "function avatar("]:
            self.assertIn(tok, c, f"Illustrations.qml missing {tok}")
```

- [ ] **Step 6: 跑结构门(应通过)+ 构建**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase2Tests -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: 3 tests OK;构建 exit 0。

- [ ] **Step 7: Commit**

```bash
git add clients/qt_observer/assets/illustrations clients/qt_observer/qml/Illustrations.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): Phase2 LiveCockpit assets (table day/night + 6 role avatars) + Illustrations registry"
```

---

## Task 2: CharacterAvatar 组件(单座头像)

**Files:**
- Create: `clients/qt_observer/qml/components/CharacterAvatar.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: 写 CharacterAvatar.qml**

```qml
import QtQuick
import qt_observer

// 单座动物头像:圆形肖像(Illustrations.avatar(roleKey))+ 阵营色环 + 名牌 + 存活/发言/出局态。
// 纯表现:全部状态经属性注入。资产缺失 → 角色名首字 + 色环 fallback(永不白屏)。
Item {
    id: root
    objectName: "characterAvatar"

    property string roleKey: ""          // werewolf/seer/witch/villager/guard/hunter("" → fallback)
    property string seatLabel: ""        // 名牌:座位号/座位名
    property string roleLabel: ""        // 角色中文名(上帝视角可见时)
    property color accent: Theme.color.border
    property bool alive: true
    property bool speaking: false
    property real diameter: 84

    readonly property url _art: Illustrations.avatar(roleKey)
    readonly property bool _hasArt: _art != "" && portrait.status === Image.Ready

    implicitWidth: diameter
    implicitHeight: diameter + 22

    // 发言光晕(珊瑚)
    Rectangle {
        anchors.horizontalCenter: medallion.horizontalCenter
        anchors.verticalCenter: medallion.verticalCenter
        visible: root.speaking && root.alive
        width: root.diameter + 14; height: width; radius: width / 2
        color: "transparent"
        border.width: 4
        border.color: Theme.withAlpha(Theme.color.primary, 0.45)
    }

    // 圆形徽章
    Rectangle {
        id: medallion
        width: root.diameter; height: root.diameter; radius: width / 2
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        color: Theme.color.surfaceCard
        border.width: root.speaking ? 4 : 3
        border.color: root.speaking ? Theme.color.primary : root.accent
        clip: true
        opacity: root.alive ? 1.0 : 0.55

        Image {
            id: portrait
            anchors.fill: parent
            source: root._art
            fillMode: Image.PreserveAspectCrop
            // 头肩像:略偏上裁出脸
            verticalAlignment: Image.AlignTop
            visible: root._hasArt
            // 出局去色
            layer.enabled: !root.alive
            // 注:灰度需 MultiEffect(真机);offscreen 不渲染,截图按彩色判读
        }

        // fallback:角色名首字
        Text {
            anchors.centerIn: parent
            visible: !root._hasArt
            text: (root.roleLabel || root.seatLabel || "?").substring(0, 1)
            color: Theme.color.text
            font.family: Theme.font.display
            font.pixelSize: root.diameter * 0.42
            font.weight: Theme.weight.bold
        }

        // 出局斜杠
        Rectangle {
            visible: !root.alive
            anchors.centerIn: parent
            width: parent.width * 1.1; height: 3; radius: 1.5; rotation: -45
            color: Theme.color.error; opacity: 0.85
        }
    }

    // 出局 / OUT 角标
    Rectangle {
        visible: !root.alive
        anchors.horizontalCenter: medallion.horizontalCenter
        anchors.verticalCenter: medallion.bottom
        width: outText.implicitWidth + Theme.space.sm
        height: outText.implicitHeight + 3
        radius: Theme.radius.sm
        color: Theme.withAlpha(Theme.color.error, 0.92)
        Text {
            id: outText; anchors.centerIn: parent
            text: I18n.t("出局", "OUT")
            color: "#ffffff"
            font.family: Theme.font.family; font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
        }
    }

    // 名牌
    Rectangle {
        anchors.top: medallion.bottom
        anchors.topMargin: root.alive ? 4 : 13
        anchors.horizontalCenter: medallion.horizontalCenter
        width: plate.implicitWidth + Theme.space.sm; height: plate.implicitHeight + 2
        radius: Theme.radius.sm
        color: Theme.withAlpha(Theme.color.surfaceRaised, 0.82)
        Text {
            id: plate; anchors.centerIn: parent
            text: root.seatLabel + (root.roleLabel ? " · " + root.roleLabel : "")
            color: root.alive ? Theme.color.text : Theme.color.textMuted
            font.family: Theme.font.family; font.pixelSize: Theme.size.micro
        }
    }
}
```

> 注:`Theme.color.surfaceCard/surfaceRaised/primary/error`、`Theme.size.micro`、`Theme.font.display/family`、`Theme.withAlpha`、`Theme.radius.sm`、`Theme.space.sm` 均为 Phase 1 已落地令牌(`test_theme_has_warm_phase_font_tokens`)。若某 token 名不符,实现时按 `Theme.qml` 实际名校正(构建会报 unqualified)。

- [ ] **Step 2: CMake 注册**

`CMakeLists.txt` 的 `QML_FILES` 段加一行:`        qml/components/CharacterAvatar.qml`

- [ ] **Step 3: 契约加断言**

在 `QtObserverGameRedesignPhase2Tests` 加:

```python
    def test_character_avatar_contract(self) -> None:
        c = (QT / "qml/components/CharacterAvatar.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "characterAvatar"', c)
        self.assertIn("Illustrations.avatar(", c)   # 走注册表
        for prop in ["roleKey", "alive", "speaking", "accent"]:
            self.assertIn(prop, c)
        self.assertIn("CharacterAvatar.qml", (QT / "CMakeLists.txt").read_text(encoding="utf-8"))
```

- [ ] **Step 4: 结构门 + 构建**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase2Tests -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: OK + exit 0。

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/qml/components/CharacterAvatar.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): CharacterAvatar (circular role bust + faction ring + alive/speaking/out states + fallback)"
```

---

## Task 3: PhaseBackground + PhaseIndicator

**Files:**
- Create: `clients/qt_observer/qml/components/PhaseBackground.qml`, `clients/qt_observer/qml/components/PhaseIndicator.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: PhaseBackground.qml**

```qml
import QtQuick
import qt_observer

// 圆桌房间背景:table-day/night 随 phase 交叉淡入。资产缺失 → phase 暖渐变兜底。
Item {
    id: root
    objectName: "phaseBackground"
    property string phase: "day"    // "night" → 夜图;其余 → 昼图

    readonly property bool _night: phase === "night"

    // 兜底渐变(图未就绪时可见)
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root._night ? "#20304F" : "#F3E8D2" }
            GradientStop { position: 1.0; color: root._night ? "#181715" : "#E8C078" }
        }
    }

    Image {
        id: dayImg
        anchors.fill: parent
        source: Illustrations.tableDay
        fillMode: Image.PreserveAspectCrop
        opacity: (!root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }
    Image {
        id: nightImg
        anchors.fill: parent
        source: Illustrations.tableNight
        fillMode: Image.PreserveAspectCrop
        opacity: (root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }
}
```

> `Theme.motion.base` 是 Phase 1 anim 令牌(`property QtObject anim`/motion)。若名为 `Theme.anim.base`,按实际校正。

- [ ] **Step 2: PhaseIndicator.qml(桌心徽记 + 可复用悬浮阶段条)**

```qml
import QtQuick
import qt_observer

// 桌心阶段徽记:太阳/月亮 + 轮次。纯表现。
Column {
    id: root
    objectName: "phaseIndicator"
    property string phase: "day"
    property int round: 1
    spacing: 2

    readonly property bool _night: phase === "night"

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root._night ? "☾" : "☀"
        color: root._night ? Theme.color.accentAmber : Theme.color.primary
        font.pixelSize: 28
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: (root._night ? I18n.t("黑夜", "Night") : I18n.t("白天", "Day"))
              + " · " + I18n.t("第 ", "R") + root.round
        color: Theme.color.text
        font.family: Theme.font.family
        font.pixelSize: Theme.size.caption
        font.weight: Theme.weight.medium
    }
}
```

- [ ] **Step 3: CMake 注册两行**

`        qml/components/PhaseBackground.qml`、`        qml/components/PhaseIndicator.qml`

- [ ] **Step 4: 契约加断言**

```python
    def test_phase_components_contract(self) -> None:
        bg = (QT / "qml/components/PhaseBackground.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "phaseBackground"', bg)
        self.assertIn("Illustrations.tableDay", bg)
        self.assertIn("Illustrations.tableNight", bg)
        self.assertIn("Gradient", bg)               # 兜底
        ind = (QT / "qml/components/PhaseIndicator.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "phaseIndicator"', ind)
        cmake = (QT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("PhaseBackground.qml", cmake)
        self.assertIn("PhaseIndicator.qml", cmake)
```

- [ ] **Step 5: 结构门 + 构建 + Commit**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase2Tests -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
git add clients/qt_observer/qml/components/PhaseBackground.qml clients/qt_observer/qml/components/PhaseIndicator.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): PhaseBackground (table day/night crossfade + gradient fallback) + PhaseIndicator"
```

---

## Task 4: CockpitSurface 表现型直播面(核心)

**Files:**
- Create: `clients/qt_observer/qml/components/CockpitSurface.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`

**数据接口(全部经属性注入,无 ObserverClient):**
- `players: var` — 形如 `ObserverClient.playerItems` 的数组:每项 `{player_id, display_role, display_team, visibility, alive}`
- `deadIds: var` · `speakingId: string` · `phase: string`("day"/"night"/"voting") · `round: int`
- `votes: var` — 形如 `[{target, count}]`(已按播放游标截断,见 Task 6) · `majority: int`
- `events: var` — 事件流模型(左栏列表)
- `dataSourceText: string` · `perspectiveText: string`
- 信号:`backRequested()`

- [ ] **Step 1: 写 CockpitSurface.qml**

```qml
import QtQuick
import QtQuick.Controls
import qt_observer
import "."

// 表现型直播面:左 20% 实体列(品牌/数据源/视角/事件流) + 右 80%(PhaseBackground +
// 椭圆头像环 + 悬浮 阶段/票数/倍速 + 多数线)。数据全经属性注入;无 ObserverClient。
Item {
    id: root
    objectName: "cockpitSurface"

    property var players: []
    property var deadIds: []
    property string speakingId: ""
    property string phase: "day"
    property int round: 1
    property var votes: []
    property int majority: 0
    property var events: []
    property string dataSourceText: ""
    property string perspectiveText: ""
    // 可选插槽:宿主把真实的 PlaybackControls / EventTimeline / 审计折叠条塞进来
    property Component playbackSlot: null
    property Component eventLogSlot: null
    property Component auditSlot: null
    signal backRequested()

    // ---- 椭圆落位常量(待真机按 table-day.png 桌沿标定)----
    property real cx: 0.40       // 右区比例:桌心偏左
    property real cy: 0.54
    property real ringRx: 0.32
    property real ringRy: 0.21   // ≈ Rx·cos(俯角)
    property real depthK: 0.16

    function _angle(i, n) { return (-90 + i * 360 / Math.max(1, n)) * Math.PI / 180 }

    Rectangle { anchors.fill: parent; color: Theme.color.canvas }

    // ===== 左区 20% =====
    Rectangle {
        id: leftCol
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Math.max(340, parent.width * 0.20)
        color: Theme.color.surfaceCard
        border.width: 0
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.color.hairline }

        Column {
            anchors.fill: parent
            anchors.margins: Theme.space.lg
            spacing: Theme.space.md

            Text {
                text: I18n.t("上帝视角观察", "God's-Eye Observer")
                color: Theme.color.text; font.family: Theme.font.display
                font.pixelSize: Theme.size.h2; font.weight: Theme.weight.bold
            }
            Row {
                spacing: Theme.space.sm
                AppButton {
                    objectName: "cockpitBackButton"
                    text: I18n.t("← 返回", "← Back"); variant: "ghost"; onLight: true
                    onClicked: root.backRequested()
                }
            }
            // 数据源真相(始终可见)+ 视角文本
            Text {
                visible: root.dataSourceText !== ""
                text: root.dataSourceText
                color: Theme.color.textMuted; font.family: Theme.font.mono; font.pixelSize: Theme.size.micro
            }
            Text {
                visible: root.perspectiveText !== ""
                text: root.perspectiveText
                color: Theme.color.textMuted; font.family: Theme.font.family; font.pixelSize: Theme.size.micro
            }
            // 视角切换插槽(宿主注入,见 Task 6;预览页可不注入)
            // 事件流(占满中部)
            Loader {
                width: parent.width
                height: parent.height - y - auditLoader.height - Theme.space.lg
                sourceComponent: root.eventLogSlot
            }
            Loader { id: auditLoader; width: parent.width; sourceComponent: root.auditSlot }
        }
    }

    // ===== 右区 80% =====
    Item {
        id: stage
        anchors { left: leftCol.right; top: parent.top; right: parent.right; bottom: parent.bottom }
        clip: true

        PhaseBackground { anchors.fill: parent; phase: root.phase }

        // 桌心徽记
        PhaseIndicator {
            phase: root.phase; round: root.round
            x: stage.width * root.cx - width / 2
            y: stage.height * root.cy - height / 2
        }

        // 投票/行动箭头(座位间珊瑚虚线)
        Canvas {
            id: arrows
            anchors.fill: parent
            property var v: root.votes
            onVChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            function _seatPt(pid) {
                for (var i = 0; i < root.players.length; i++)
                    if (root.players[i] && root.players[i].player_id === pid) {
                        var th = root._angle(i, root.players.length)
                        return Qt.point(width * root.cx + width * root.ringRx * Math.cos(th),
                                        height * root.cy + height * root.ringRy * Math.sin(th))
                    }
                return null
            }
            onPaint: {
                var ctx = getContext("2d"); ctx.reset()
                if (!root.votes) return
                ctx.strokeStyle = Theme.color.primary; ctx.lineWidth = 2
                ctx.setLineDash([6, 5]); ctx.globalAlpha = 0.7
                for (var k = 0; k < root.votes.length; k++) {
                    var pt = _seatPt(root.votes[k].target)
                    // 票箭头细节(从投票者指向目标)在 Task 8 细化;此处先画目标圈
                    if (pt) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 4, 0, 2*Math.PI); ctx.stroke() }
                }
            }
        }

        // 椭圆头像环
        Repeater {
            model: root.players
            delegate: CharacterAvatar {
                readonly property real _th: root._angle(index, root.players.length)
                readonly property real _sin: Math.sin(_th)
                diameter: Math.min(stage.width, stage.height) * 0.13 * (1 + root.depthK * _sin)
                x: stage.width * root.cx + stage.width * root.ringRx * Math.cos(_th) - width / 2
                y: stage.height * root.cy + stage.height * root.ringRy * _sin - diameter / 2
                z: 10 + _sin                 // 后排(sin 小)在下,前排压上
                roleKey: modelData.display_role && modelData.display_role !== "unknown" ? modelData.display_role : ""
                roleLabel: roleKey ? _roleName(modelData.display_role) : ""
                seatLabel: modelData.player_id
                accent: roleKey ? Theme.roleAccent(modelData.display_role) : Theme.color.border
                alive: root.deadIds.indexOf(modelData.player_id) < 0
                speaking: root.speakingId === modelData.player_id
            }
        }

        // 悬浮:阶段(右上)
        Rectangle {
            id: phaseChip
            anchors { right: parent.right; top: parent.top; margins: Theme.space.lg }
            width: stage.width * 0.28
            implicitHeight: phaseChipText.implicitHeight + Theme.space.md
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.color.surfaceRaised, 0.9)
            border.width: 1; border.color: Theme.color.hairline
            Text {
                id: phaseChipText; anchors.centerIn: parent
                text: (root.phase === "night" ? "☾ " + I18n.t("黑夜","Night") : "☀ " + I18n.t("白天","Day"))
                      + " · " + I18n.t("第 ","R") + root.round
                color: Theme.color.text; font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
        }

        // 悬浮:当前票数(右)
        Rectangle {
            id: votesPanel
            anchors { right: parent.right; top: phaseChip.bottom; topMargin: Theme.space.sm; rightMargin: Theme.space.lg }
            width: stage.width * 0.28
            implicitHeight: votesCol.implicitHeight + Theme.space.lg
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.color.surfaceRaised, 0.9)
            border.width: 1; border.color: Theme.color.hairline
            visible: root.votes && root.votes.length > 0
            Column {
                id: votesCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.space.md }
                spacing: 2
                Text {
                    text: I18n.t("当前票数", "Current Votes")
                    color: Theme.color.primary; font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
                }
                Repeater {
                    model: root.votes
                    delegate: Text {
                        text: modelData.target + "  ●×" + modelData.count
                        color: Theme.color.textBody; font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                    }
                }
            }
        }

        // 悬浮:倍速/播放(右,票数下)— 宿主插槽
        Loader {
            anchors { right: parent.right; top: votesPanel.bottom; topMargin: Theme.space.sm; rightMargin: Theme.space.lg }
            width: stage.width * 0.28
            sourceComponent: root.playbackSlot
        }

        // 底部居中:多数线
        Rectangle {
            visible: root.majority > 0
            anchors { bottom: parent.bottom; bottomMargin: Theme.space.lg }
            x: stage.width * root.cx - width / 2
            implicitWidth: majText.implicitWidth + Theme.space.xl
            implicitHeight: majText.implicitHeight + Theme.space.sm
            radius: Theme.radius.pill
            color: Theme.withAlpha(Theme.color.surfaceDark, 0.55)
            Text {
                id: majText; anchors.centerIn: parent
                text: "──  " + I18n.t("多数线 ", "Majority ") + root.majority + "  ──"
                color: Theme.color.canvas; font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
        }
    }

    // 角色中文名(上帝视角可见时)
    function _roleName(role) {
        var m = ({
            werewolf: I18n.t("狼人","Werewolf"), seer: I18n.t("预言家","Seer"),
            witch: I18n.t("女巫","Witch"), villager: I18n.t("村民","Villager"),
            guard: I18n.t("守卫","Guard"), hunter: I18n.t("猎人","Hunter")
        })
        return m[role] || role
    }
}
```

> `onLight` 是 Phase 1 共享组件的暖色开关(`test_home_uses_new_design_system` 锁了 `onLight`)。`AppButton` 已支持。`Theme.color.surfaceDark/canvas/textBody/accentAmber` 等若名不符按 `Theme.qml` 校正。椭圆常量初值待 Task 5 真机标定。

- [ ] **Step 2: CMake 注册** `        qml/components/CockpitSurface.qml`

- [ ] **Step 3: 契约加断言**

```python
    def test_cockpit_surface_contract(self) -> None:
        c = (QT / "qml/components/CockpitSurface.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "cockpitSurface"', c)
        self.assertIn("PhaseBackground", c)
        self.assertIn("CharacterAvatar", c)
        self.assertIn("PhaseIndicator", c)
        # 表现型:不抓 ObserverClient(数据经属性)
        self.assertNotIn("ObserverClient", c)
        for prop in ["property var players", "property var votes", "property int majority", "property string phase"]:
            self.assertIn(prop, c)
        self.assertIn("CockpitSurface.qml", (QT / "CMakeLists.txt").read_text(encoding="utf-8"))
```

- [ ] **Step 4: 结构门 + 构建 + Commit**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase2Tests -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
git add clients/qt_observer/qml/components/CockpitSurface.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): CockpitSurface presentational live page (ellipse avatar ring + floating panels, data via props)"
```

---

## Task 5: DesignPreviewView + 首页入口 + 烤死样例 ← 最早可截图验收点

**Files:**
- Create: `clients/qt_observer/qml/DesignPreviewView.qml`
- Modify: `clients/qt_observer/qml/HomeView.qml`, `clients/qt_observer/qml/AppShell.qml`, `clients/qt_observer/CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: DesignPreviewView.qml(烤死样例 + 昼/夜/投票切换 + 固定「设计样例」标记)**

```qml
import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// 静态宿主:用烤死样例驱动 CockpitSurface,不接 ObserverClient、不开 run。
// 真相标记固定「设计样例」,绝不读 ObserverClient.currentExecutionMode。
Item {
    id: root
    objectName: "designPreviewView"

    property string previewPhase: "day"     // day / night / voting

    // 6 座 = 6 角色(上帝视角:display_role 全可见)
    readonly property var _players: [
        { player_id: "1", display_role: "werewolf", display_team: "werewolf", visibility: "visible", alive: true },
        { player_id: "2", display_role: "seer",     display_team: "village",  visibility: "visible", alive: true },
        { player_id: "3", display_role: "witch",    display_team: "village",  visibility: "visible", alive: true },
        { player_id: "4", display_role: "villager", display_team: "village",  visibility: "visible", alive: true },
        { player_id: "5", display_role: "guard",    display_team: "village",  visibility: "visible", alive: true },
        { player_id: "6", display_role: "hunter",   display_team: "village",  visibility: "visible", alive: false }
    ]
    readonly property var _events: [
        { t: "00:01", text: I18n.t("第二天开始", "Day 2 begins") },
        { t: "00:07", text: I18n.t("4 号发言", "Seat 4 speaks") },
        { t: "00:09", text: I18n.t("4 号 → 5 号", "4 → 5") },
        { t: "00:21", text: I18n.t("2 号附议", "2 seconds it") }
    ]

    Rectangle { anchors.fill: parent; color: Theme.color.canvas }

    CockpitSurface {
        id: surface
        anchors.fill: parent
        players: root._players
        deadIds: ["6"]
        speakingId: "4"
        phase: root.previewPhase
        round: 2
        votes: root.previewPhase === "voting"
               ? [ { target: "5", count: 3 }, { target: "1", count: 2 } ]
               : []
        majority: root.previewPhase === "voting" ? 4 : 0
        dataSourceText: I18n.t("设计样例", "Design Sample")
        perspectiveText: I18n.t("上帝视角", "God's-Eye")
        eventLogSlot: eventLogComp
        backRequested: function() { root.StackView.view.parent.navigateHome() }
    }

    Component {
        id: eventLogComp
        ListView {
            model: root._events
            spacing: Theme.space.xs
            delegate: Row {
                spacing: Theme.space.sm
                Text { text: modelData.t; color: Theme.color.textMuted; font.family: Theme.font.mono; font.pixelSize: Theme.size.micro }
                Text { text: modelData.text; color: Theme.color.textBody; font.family: Theme.font.family; font.pixelSize: Theme.size.caption }
            }
        }
    }

    // 昼/夜/投票切换(预览专用)
    Row {
        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: Theme.space.lg }
        spacing: Theme.space.sm
        Repeater {
            model: [ { k: "day", t: I18n.t("白天","Day") }, { k: "night", t: I18n.t("黑夜","Night") }, { k: "voting", t: I18n.t("投票","Voting") } ]
            delegate: AppButton {
                objectName: "previewPhase_" + modelData.k
                text: modelData.t; onLight: true
                variant: root.previewPhase === modelData.k ? "primary" : "ghost"
                onClicked: root.previewPhase = modelData.k
            }
        }
    }
}
```

> `backRequested: function(){...}` 形式绑信号;若 QML 版本要求 `onBackRequested:`,改用 `Connections` 或 `surface.onBackRequested`. 实现时若报错改 `onBackRequested`。

- [ ] **Step 2: HomeView 加入口按钮**

`qml/HomeView.qml`,在 hero 双按钮区(`startNewMatchButton` 附近)加一个 onLight 按钮:

```qml
                AppButton {
                    objectName: "designPreviewButton"
                    text: I18n.t("🎴 设计预览", "🎴 Design Preview")
                    variant: "ghost"
                    onLight: true
                    onClicked: root.StackView.view.parent.navigateDesignPreview()
                }
```

- [ ] **Step 3: AppShell 加路由**

`qml/AppShell.qml`:仿现有 `cockpitComponent` + `navigate*` 模式加:

```qml
    Component { id: designPreviewComponent; DesignPreviewView { } }
```
并加导航函数(与 `navigateHistory` 等并列):
```qml
    function navigateDesignPreview() {
        currentView = "designPreview"
        stackView.replace(designPreviewComponent)
    }
```
> `currentView` 取值不影响 home 顶栏隐藏逻辑(`currentView !== "home"` → 显示顶栏,预览页显示顶栏即可)。

- [ ] **Step 4: CMake 注册** `        qml/DesignPreviewView.qml`

- [ ] **Step 5: 契约更新(REQUIRED_QML_VIEWS / OBJECT_NAMES / HomeView 入口 / AppShell 路由 / Phase2)**

`REQUIRED_QML_VIEWS` 加 `"qml/DesignPreviewView.qml"`;`REQUIRED_OBJECT_NAMES` 加:
```python
    "qml/DesignPreviewView.qml": ["designPreviewView"],
```
`REQUIRED_OBJECT_NAMES["qml/HomeView.qml"]` 追加 `"designPreviewButton"`。
在 `QtObserverGameRedesignPhase2Tests` 加:
```python
    def test_home_has_design_preview_entry(self) -> None:
        c = (QT / "qml/HomeView.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "designPreviewButton"', c)
        self.assertIn("navigateDesignPreview()", c)
        a = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        self.assertIn("function navigateDesignPreview", a)
        self.assertIn("DesignPreviewView", a)

    def test_preview_uses_static_sample_not_execution_mode(self) -> None:
        c = (QT / "qml/DesignPreviewView.qml").read_text(encoding="utf-8")
        self.assertIn("CockpitSurface", c)
        self.assertNotIn("currentExecutionMode", c)      # 不读真 run 模式
        self.assertNotIn("ObserverClient", c)            # 纯静态样例
        self.assertIn('objectName: "designPreviewView"', c)
```

- [ ] **Step 6: 结构门 + 构建**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: 全绿 + exit 0。

- [ ] **Step 7: 截图自验(首个视觉验收 — 昼/夜/投票)**

在 `AppShell.qml` 临时加 harness(跑完撤):
```qml
    Timer {
        running: true; interval: 600; property int n: 0
        onTriggered: {
            navigateDesignPreview()
            var v = appShellStack.currentItem
            if (n === 0) { v.previewPhase = "day" }
            else if (n === 1) { v.previewPhase = "night" }
            else if (n === 2) { v.previewPhase = "voting" }
            else { Qt.quit(); return }
            root.grabToImage(function(res){ res.saveToFile("G:/Werewolf-agent/.tmp/preview_" + n + ".png") })
            n++; interval = 900; running = true
        }
    }
```
```bash
QT_QPA_PLATFORM=offscreen .tmp/qt-observer-build/appqt_observer.exe
```
用 Read 读 `.tmp/preview_0/1/2.png` 核对:头像贴合桌沿椭圆、偏左留空使悬浮件不盖头像、昼/夜背景切换、投票面板+多数线。**据此微调 CockpitSurface 的 `cx/cy/ringRx/ringRy/depthK` 常量**(改完重构建重截)。撤 harness:`git checkout -- clients/qt_observer/qml/AppShell.qml`。

- [ ] **Step 8: Commit**

```bash
git add clients/qt_observer/qml/DesignPreviewView.qml clients/qt_observer/qml/HomeView.qml clients/qt_observer/qml/AppShell.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): HomeView Design Preview entry + DesignPreviewView (static sample, day/night/voting) hosting CockpitSurface"
```

---

## Task 6: TheaterView 重写为 CockpitSurface 的 live 宿主

**Files:**
- Modify: `clients/qt_observer/qml/TheaterView.qml`, `clients/qt_observer/qml/components/EvidenceConsole.qml`, `tests/test_qt_observer_static_contract.py`

> **保留逐字**:`objectName: "theaterView"`、`EventPresentationQueue { id: eventQueue }`、`state: eventQueue.layoutPhase`、`resumeAfterTransition` 接线、`navigateHome` 退出、`SettlementView` overlay(`currentStatus === "completed"`)、`SeatRing.perspective` 单向绑(本页不再用 SeatRing,但**不得出现 `ring.perspective =` 写法**)。这些被 `QtObserverTheaterViewTests` 钉死。

- [ ] **Step 1: EvidenceConsole 加 `showPerspectiveSwitcher` 开关**

`qml/components/EvidenceConsole.qml`:加 `property bool showPerspectiveSwitcher: true`,把内部 `lensRow`(含 `PerspectiveSwitcher`)的 `visible` 与之 AND:
```qml
        Row {
            id: lensRow
            visible: root.showPerspectiveSwitcher && (root.mode === 1 || root.mode === 2)
            ...
```
> `test_evidence_console_rehomes_honesty_chain` 仍要求 EvidenceConsole **包含** `PerspectiveSwitcher` 字样(组件存在即可,visible 受控不影响断言)。

- [ ] **Step 2: 重写 TheaterView 主体为 CockpitSurface 宿主**

保留顶部 `Component.onCompleted`/`Connections`/`projRefreshTimer`/`EventPresentationQueue`/状态机/`SettlementView` Loader 不变;把原 `topBar + PhaseTimeline + stage(ringStage/feedPanel) + EvidenceConsole` 替换为:

```qml
    CockpitSurface {
        id: surface
        anchors.fill: parent
        players: ObserverClient.playerItems
        deadIds: eventQueue.deadPlayers
        speakingId: eventQueue.current ? (eventQueue.current.actor || "") : ""
        phase: eventQueue.layoutPhase
        round: eventQueue.currentRound       // 若无此属性,用 phaseTimeline 末项的 round;见 Step 3
        votes: theaterRoot._derivedVotes
        majority: theaterRoot._majority
        dataSourceText: ObserverClient.currentExecutionMode === "live" ? I18n.t("真实 LIVE","LIVE") : I18n.t("模拟","SIMULATION")
        perspectiveText: I18n.t("视角:","View: ") + ObserverClient.currentPerspective
        eventLogSlot: liveEventLog
        playbackSlot: livePlayback
        auditSlot: liveAudit
        backRequested: function() { ObserverClient.disconnectStream(); theaterRoot.StackView.view.parent.navigateHome() }
    }

    Component { id: liveEventLog; EventTimeline { } }
    Component { id: livePlayback; PlaybackControls { queue: eventQueue } }
    Component { id: liveAudit; EvidenceConsole { perspective: ObserverClient.currentPerspective; showPerspectiveSwitcher: true } }
```

> 视角切换在 EvidenceConsole(auditSlot)内,因此 `showPerspectiveSwitcher: true`;**不要**在 CockpitSurface 左区顶部再放一个(单实例铁律,spec §5)。`perspectiveText` 仅文本展示,不是控件。

- [ ] **Step 3: 票数派生(按播放游标截断,禁用未来票)**

在 TheaterView 加(从**当前可见、且 ≤ 播放游标**的投票事件统计;**不**从完整 `projectionEvents` 算最终票):

```qml
    // 票数 = eventQueue 已呈现到游标的 player_vote 事件聚合(当前 round)。
    // EventPresentationQueue 已分层 eventItems(瘦)/projectionEvents(富),这里只数已播放的票。
    readonly property var _derivedVotes: {
        var counts = ({})
        var played = eventQueue.playedEvents || []     // 若 API 名不同,见下注
        for (var i = 0; i < played.length; i++) {
            var e = played[i]
            if ((e.type || "") === "player_vote" && e.target)
                counts[e.target] = (counts[e.target] || 0) + 1
        }
        var out = []
        for (var k in counts) out.push({ target: k, count: counts[k] })
        out.sort(function(a,b){ return b.count - a.count })
        return out
    }
    readonly property int _majority: Math.floor((ObserverClient.playerItems.length - theaterRoot._deadCount) / 2) + 1
    readonly property int _deadCount: eventQueue.deadPlayers ? eventQueue.deadPlayers.length : 0
```

> ⚠️ **实现前先在 `EventPresentationQueue.qml` 确认「已播放到游标的事件列表」的真实属性名**(可能是 `queuedConsumed`/`history`/`playedEvents` 等)。若无现成游标内已播放列表,在 queue 暴露一个**只读派生**(不新增后端字段)。**绝不**用 `ObserverClient.projectionEvents` 全量(会显示未来票)。`round` 同理:用 queue 的当前 round 派生。

- [ ] **Step 4: 契约同步(TheaterView 仍满足既有断言 + EvidenceConsole 开关)**

`QtObserverTheaterViewTests` 既有断言应仍绿(theaterView/EventPresentationQueue/eventQueue/resumeAfterTransition/state binding/navigateHome/无 `ring.perspective =`)。加:
```python
    def test_theater_hosts_cockpit_surface(self) -> None:
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("CockpitSurface", t)
        self.assertIn("ObserverClient.playerItems", t)
        # 票数不得直接来自完整 projectionEvents 全量
        self.assertNotRegex(t, r"votes:\s*ObserverClient\.projectionEvents")
    def test_evidence_console_perspective_switch_toggle(self) -> None:
        e = (QT / "qml/components/EvidenceConsole.qml").read_text(encoding="utf-8")
        self.assertIn("showPerspectiveSwitcher", e)
```

- [ ] **Step 5: 结构门 + 构建**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: 全绿 + exit 0。

- [ ] **Step 6: 截图自验(真 server,含结算)— 见「关键约定」截图自验第 2 段命令**,跑 `default_6p_fake` 一局,截直播页昼/夜 + 结算。核对真实数据下与预览一致。

- [ ] **Step 7: Commit**

```bash
git add clients/qt_observer/qml/TheaterView.qml clients/qt_observer/qml/components/EvidenceConsole.qml tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): TheaterView hosts CockpitSurface (live ObserverClient bindings preserved; cursor-truncated votes; perspective single-instance in EvidenceConsole)"
```

---

## Task 7: 昼夜/投票呼吸 + 投票箭头 + 结算 overlay 重皮

**Files:**
- Modify: `clients/qt_observer/qml/components/CockpitSurface.qml`, `clients/qt_observer/qml/TheaterView.qml`, `clients/qt_observer/qml/SettlementView.qml`(仅视觉令牌,不动结算逻辑/cursor 契约)

- [ ] **Step 1: CockpitSurface 昼夜呼吸**:phase 变化时环整体缩放/事件流淡入,用 `states`/`Behavior`(只动尺寸/透明度,不动容器位置)。night 环略放大;voting 票面板+箭头亮。
- [ ] **Step 2: 投票/夜间行动箭头**:Task 4 的 `arrows` Canvas 从「目标圈」升级为「投票者→目标」珊瑚虚线+箭头;夜间用阵营色(狼刀/查验/守护)。坐标用 `_seatPt`。
- [ ] **Step 3: SettlementView overlay 重皮**:只改暖色令牌/onLight,**不动** `cursorIndex`/`fetchSettlement`/`boardState`/morph states 契约(`QtObserverSettlementViewTests` 钉死)。
- [ ] **Step 4: 结构门 + 构建 + 截图矩阵**(昼/夜/投票/结算 × 至少含一档小屏 1280×720)。
- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/qml/components/CockpitSurface.qml clients/qt_observer/qml/TheaterView.qml clients/qt_observer/qml/SettlementView.qml
git commit -m "feat(qt-redesign): cockpit day/night/voting breathing + vote/action arrows + settlement overlay reskin"
```

---

## Task 8: 删除 LiveCockpitView + 迁移其契约不变量

**Files:**
- Delete: `clients/qt_observer/qml/LiveCockpitView.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`

> LiveCockpitView 被 contract 多处绑定。删除前其「不变量」必须已由新面承载:无硬编码角色 / 用 projection / 有边界+证明 → 现由 `CockpitSurface`(用 `players`/projection 形状,不硬编码)+ `EvidenceConsole`(已 re-home 证明面,`test_evidence_console_rehomes_honesty_chain` 已覆盖)承载。

- [ ] **Step 1: 删文件 + CMake 去注册**

```bash
git rm clients/qt_observer/qml/LiveCockpitView.qml
```
`CMakeLists.txt` 删 `        qml/LiveCockpitView.qml` 行。

- [ ] **Step 2: 契约删除/改写 LiveCockpitView 相关断言**

在 `tests/test_qt_observer_static_contract.py`:
- `REQUIRED_QML_VIEWS`:删 `"qml/LiveCockpitView.qml"`。
- `REQUIRED_OBJECT_NAMES`:删 `"qml/LiveCockpitView.qml": [...]` 整条。
- `QtObserverCockpitContractTests.test_cockpit_contains_required_object_names`:改为读 `qml/components/EvidenceConsole.qml`(它已含这些 objectName,见第 89 行),或删除此方法(EvidenceConsole 的 objectName 已在 REQUIRED_OBJECT_NAMES 覆盖)→ **删除该方法**。
- `QtObserverHiddenInfoBoundaryTests`:`test_live_cockpit_does_not_embed_static_role_assignments` / `test_qml_boundary_copy_mentions_server_projection` → 改为针对 `qml/components/CockpitSurface.qml`(断言不含 `role: "Werewolf"` 等硬编码、含 `players`)。`test_qt_client_does_not_use_local_snapshot_or_event_paths` 与 LiveCockpit 无关,保留。
- `QtObserverVisibilityUiTests`:`test_live_cockpit_uses_projection_player_items`(改读 TheaterView,断言 `ObserverClient.playerItems`)、`test_live_cockpit_contains_boundary_badge_and_proof_panel`(边界+证明已在 EvidenceConsole;改读 EvidenceConsole 或删,因 `test_evidence_console_rehomes_honesty_chain` 已覆盖 → **删除**)、`test_cockpit_does_not_hardcode_god_roles_as_live_player_source`(改读 CockpitSurface)。

具体改写示例(把三处「读 LiveCockpitView」改成读新面):
```python
    def test_cockpit_surface_no_hardcoded_roles(self) -> None:
        c = (QT / "qml/components/CockpitSurface.qml").read_text(encoding="utf-8")
        self.assertNotRegex(c, r'(display_role|role):\s*"(?:Werewolf|Seer|Witch|Villager)"')
        self.assertIn("players", c)                  # 经投影属性,非硬编码
    def test_theater_uses_projection_player_items(self) -> None:
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("ObserverClient.playerItems", t)
```

- [ ] **Step 3: 全量结构门 + 构建(确认无残留引用 LiveCockpitView)**

```bash
grep -rn "LiveCockpitView\|liveCockpitView" clients/qt_observer tests | grep -v ".tmp"   # 期望:空
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: grep 空;测试全绿;构建 exit 0。

- [ ] **Step 4: Commit**

```bash
git add -A clients/qt_observer tests/test_qt_observer_static_contract.py
git commit -m "chore(qt-redesign): delete dead LiveCockpitView + re-home its contract invariants onto CockpitSurface/TheaterView/EvidenceConsole"
```

---

## Task 9: 截图矩阵复核 + 压缩收尾 + 清理

**Files:** 无源改动(验证 + 资产压缩)

- [ ] **Step 1: 截图矩阵**:经 `DesignPreviewView` 截 白天/黑夜/投票;经真 server 截 结算(胜/负各一)。分辨率 1280×720(小屏必覆盖)+ 1920×1080。逐张 Read 核对验收口径(spec §11):阶段/发言者/存活出局/票数/多数线/数据源真相一眼可见,头像不被悬浮件挡,阵营色仅小强调。
- [ ] **Step 2: 资产最终压缩**(Task 1 若跳过):pngquant 压 8 张,重构建确认体积下降、显示无明显劣化。
- [ ] **Step 3: 三件门全跑**:`unittest` 结构门 + `ctest --test-dir .tmp/qt-observer-build` + `qmllint -I .tmp/qt-observer-build qml/*.qml qml/components/*.qml`(只看 `Error:`)。
- [ ] **Step 4: 清理**:确认无残留临时 harness(`git status` 干净)、无 `.tmp` 截图入仓。
- [ ] **Step 5: Commit(若有压缩)**

```bash
git add clients/qt_observer/assets/illustrations
git commit -m "perf(qt-redesign): compress Phase2 illustration assets (pngquant)"
```

---

## 验收(spec §11)

- 暖色 + 质感 + 字体舒适三点消解。
- 一眼可见:阶段/轮次、当前发言者、存活/出局、投票目标与票数、多数线、LIVE/SIMULATION 真相。
- 头像按椭圆贴合背景桌沿;偏左留空使悬浮件不盖头像;6/8 人皆正确排布。
- 截图矩阵:白天/黑夜/投票/结算 × {1280×720, 1920×1080};经 `DesignPreviewView`(无需真局)+ 真 server(结算)。
- 三件门绿;`LiveCockpitView` 残留为零。
