# Phase 2 · LiveCockpit 上帝视角圆桌重做 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把对局直播页(`TheaterView`)从冷炭灰审计面重做成「上帝视角俯视圆桌环」暖色插画客户端,并提供一个**首页静态预览入口**(烤死样例、不开真局)作为最早可截图验收点。

**Architecture:** 资产分层(空对称椭圆背景昼/夜 + 6 圆形角色头像)+ 一个**表现型组件 `CockpitSurface`**(数据/控件全经属性与插槽注入)+ 两个宿主(`DesignPreviewView` 喂烤死样例 + stub 控件 / `TheaterView` 绑真实 `ObserverClient` + 真控件)。数据绑定语义逐字保留;页面长相全新。

**Tech Stack:** Qt 6.10 QML(mingw,工具链在 F:)· QML 单例 `Theme`/`I18n`/`Illustrations` · Python `unittest` static contract 作结构门 · cmake 构建 + offscreen/真机截图自验。

**Spec:** `docs/superpowers/specs/2026-06-13-livecockpit-godseye-redesign-phase2-design.md`

---

## 关键约定(贯穿全计划)

### Shell:所有命令在 **Git Bash** 执行
qt 工具链 runbook(`verifying-qt-observer-ui`)本就是 bash,且 `/f/Qt/...` mount 路径是 **bash-only**(`F:/` 的冒号与 PATH 分隔符冲突)。**PowerShell 用户先开 Git Bash 再跑。** 唯一纯 Python 的结构门在 PS 下等价为 `$env:PYTHONPATH='src'; python -m unittest tests.test_qt_observer_static_contract`,但构建/截图必须 Git Bash。

### 构建(每次改 QML 后)
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
exit 0 = 已注册 QML 语法全有效。**新建 .qml 必须加进 `CMakeLists.txt` 的 `qt_add_qml_module(... QML_FILES ...)`,否则运行时白屏。**

### 结构门(每次改 QML/契约后)
```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract
```
必须绿。

### 暖色令牌口径(直接照抄,勿用冷色 `Theme.color.*`)
本页是**暖色页**,一律用 `Theme.warm.*` / `Theme.fontFamilies.*`。冷色 `Theme.color.*` 是旧 zinc 主题(`Theme.color.primary` 是**白色**,误用即翻车)。映射表:

| 用途 | 令牌 |
|---|---|
| 主文字 ink | `Theme.warm.ink` |
| 正文 | `Theme.warm.body` |
| 次要文字 | `Theme.warm.muted` |
| 最弱文字 | `Theme.warm.mutedSoft` |
| 画布 | `Theme.warm.canvas` |
| 卡片表面 | `Theme.warm.surfaceCard` |
| 浮起卡 | `Theme.warm.surfaceRaised` |
| 暗表面 | `Theme.warm.surfaceDark` |
| 发丝边 | `Theme.warm.hairline` |
| 主色珊瑚 | `Theme.warm.primary` |
| 珊瑚按下 | `Theme.warm.primaryActive` |
| 琥珀 | `Theme.warm.accentAmber` |
| 错误/出局 | `Theme.warm.error` |
| 标题字族 | `Theme.fontFamilies.serif` |
| 正文字族 | `Theme.fontFamilies.sans` |
| 等宽字族 | `Theme.fontFamilies.mono` |
| 标题字号 | `Theme.warmSize.titleLg/titleMd/bodyLg`(22/18/16) |
| 小字号(调色板无关) | `Theme.size.caption/micro`(12/11) |
| 字重/间距/圆角/动效/withAlpha/roleAccent | `Theme.weight.*`/`Theme.space.*`/`Theme.radius.*`/`Theme.motion.*`/`Theme.withAlpha()`/`Theme.roleAccent()`(均存在,调色板无关) |

**warm 文字规则**:每个承载中文的 `Text` 用 `font.family: Theme.fontFamilies.*` **并加** `font.contextFontMerging: true`(Inter 缺 CJK 字形时由系统字体合并,承袭 Phase 1)。

### 截图自验
在 `AppShell.qml` 临时加 `Timer` 导航到目标视图 → `root.grabToImage(r => r.saveToFile("G:/Werewolf-agent/.tmp/shot_X.png"))` → `Qt.quit()`;`QT_QPA_PLATFORM=offscreen` 跑;**MultiEffect/阴影 offscreen 不渲染,需真机**;跑完 `git checkout -- clients/qt_observer/qml/AppShell.qml`。残留进程锁 exe:`taskkill //F //IM appqt_observer.exe`。

### 提交纪律(共享 main)
每次 commit 前 `git branch --show-current` + `git status --short`(有非本任务 staged 就停)。实现**在隔离 worktree**(superpowers:using-git-worktrees)。

### 不碰
runtime/scoring/provider/模型可见 prompt/日志契约/observer 后端字段(`src/**`、`tests/**` 除 `test_qt_observer_static_contract.py`)。

---

## 文件结构

**新建:**
- `clients/qt_observer/assets/illustrations/scene/table-day.png` · `table-night.png`
- `clients/qt_observer/assets/illustrations/avatars/{werewolf,seer,witch,villager,guard,hunter}.png`
- `clients/qt_observer/qml/components/CharacterAvatar.qml`
- `clients/qt_observer/qml/components/PhaseBackground.qml`
- `clients/qt_observer/qml/components/PhaseIndicator.qml`
- `clients/qt_observer/qml/components/CockpitSurface.qml`
- `clients/qt_observer/qml/DesignPreviewView.qml`

**修改:**
- `clients/qt_observer/qml/Illustrations.qml`、`clients/qt_observer/qml/Theme.qml`(roleAccent 补 guard/hunter)、`clients/qt_observer/CMakeLists.txt`、`clients/qt_observer/qml/HomeView.qml`、`clients/qt_observer/qml/AppShell.qml`、`clients/qt_observer/qml/TheaterView.qml`、`clients/qt_observer/qml/EventPresentationQueue.qml`(加只读 `voteTally`/`currentRound`)、`clients/qt_observer/qml/components/EvidenceConsole.qml`(加 `showPerspectiveSwitcher`)、`tests/test_qt_observer_static_contract.py`

**删除:** `clients/qt_observer/qml/LiveCockpitView.qml`(死代码,Task 8)

> **SeatRing.qml 不动**:其 docked 模式承载结算棋盘(`SettlementView` 关键路径)。新椭圆环在 `CockpitSurface` 内用 `CharacterAvatar` 重建。(spec §6 写「改造 SeatRing」,此处工程取舍=不动它、新建环,降结算回归风险。)

---

## Task 1: 资产入库 + Illustrations 注册 + Theme.roleAccent 补全 + CMake

**Files:**
- Create: `assets/illustrations/scene/table-{day,night}.png`、`assets/illustrations/avatars/{werewolf,seer,witch,villager,guard,hunter}.png`
- Modify: `qml/Illustrations.qml`、`qml/Theme.qml`、`CMakeLists.txt`、`tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: 拷贝资产(已生成在 brainstorm content 目录)**

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

- [ ] **Step 2: 压缩(母版另存;pngquant 有则压,无则跳过记 TODO)**

```bash
cd "G:/Werewolf-agent/clients/qt_observer/assets/illustrations"
if command -v pngquant >/dev/null; then
  pngquant --force --quality=70-92 --ext .png scene/table-day.png scene/table-night.png avatars/*.png
else
  echo "pngquant 不可用:先用母版,压缩留 Task 9 收尾"
fi
```

- [ ] **Step 3: Illustrations.qml 加 table + avatar 注册**

`qml/Illustrations.qml`,`homeSceneNight` 行后加:
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
`function tarot` 后加:
```qml
    function table(phaseName) {
        return ("" + phaseName).toLowerCase() === "night" ? tableNight : tableDay;
    }
    function avatar(roleKey) {
        var k = ("" + roleKey).toLowerCase();
        return _avatar[k] !== undefined ? _avatar[k] : "";
    }
```

- [ ] **Step 4: Theme.roleAccent 补 guard/hunter(现仅覆盖 werewolf/seer/witch/villager,守卫猎人会落到 unknown 灰)**

`qml/Theme.qml` 的 `function roleAccent`,在 `case "villager":` 分支后、`default:` 前加:
```qml
        case "guard":
            return "#4a8c6f";
        case "hunter":
            return "#b5683a";
```

- [ ] **Step 5: CMake 注册 8 个 RESOURCES**

`CMakeLists.txt` 的 `RESOURCES` 段(`tarot/hunter.png` 后、`)` 前)加:
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

- [ ] **Step 6: Phase2 契约类(资产 + CMake + 注册 + roleAccent)**

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

    def test_role_accent_covers_guard_and_hunter(self) -> None:
        c = (QT / "qml/Theme.qml").read_text(encoding="utf-8")
        self.assertRegex(c, r'case\s*"guard":')
        self.assertRegex(c, r'case\s*"hunter":')
```

- [ ] **Step 7: 结构门 + 构建**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase2Tests -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: 4 tests OK;构建 exit 0。

- [ ] **Step 8: Commit**

```bash
git add clients/qt_observer/assets/illustrations clients/qt_observer/qml/Illustrations.qml clients/qt_observer/qml/Theme.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): Phase2 assets (table day/night + 6 role avatars) + Illustrations registry + roleAccent guard/hunter"
```

---

## Task 2: CharacterAvatar 组件(单座头像)

**Files:** Create `qml/components/CharacterAvatar.qml`;Modify `CMakeLists.txt`、契约。

- [ ] **Step 1: 写 CharacterAvatar.qml**

```qml
import QtQuick
import qt_observer

// 单座动物头像:圆形肖像(Illustrations.avatar)+ 阵营色环 + 名牌 + 存活/发言/出局态。
// 纯表现,状态经属性。资产缺失 → 角色名首字 + 色环 fallback(永不白屏)。
Item {
    id: root
    objectName: "characterAvatar"

    property string roleKey: ""          // "" → fallback
    property string seatLabel: ""
    property string roleLabel: ""
    property color accent: Theme.warm.hairline
    property bool alive: true
    property bool speaking: false
    property real diameter: 84

    readonly property url _art: Illustrations.avatar(roleKey)
    readonly property bool _hasArt: _art != "" && portrait.status === Image.Ready

    implicitWidth: diameter
    implicitHeight: diameter + 22

    Rectangle {                          // 发言光晕(珊瑚)
        anchors.horizontalCenter: medallion.horizontalCenter
        anchors.verticalCenter: medallion.verticalCenter
        visible: root.speaking && root.alive
        width: root.diameter + 14; height: width; radius: width / 2
        color: "transparent"; border.width: 4
        border.color: Theme.withAlpha(Theme.warm.primary, 0.45)
    }

    Rectangle {                          // 圆形徽章
        id: medallion
        width: root.diameter; height: root.diameter; radius: width / 2
        anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter
        color: Theme.warm.surfaceCard
        border.width: root.speaking ? 4 : 3
        border.color: root.speaking ? Theme.warm.primary : root.accent
        clip: true
        opacity: root.alive ? 1.0 : 0.55

        Image {
            id: portrait
            anchors.fill: parent
            source: root._art
            fillMode: Image.PreserveAspectCrop
            verticalAlignment: Image.AlignTop
            visible: root._hasArt
            // 出局去色需 MultiEffect(真机);offscreen 不渲染,截图按彩色判读 alive 态
        }
        Text {                           // fallback:角色名首字
            anchors.centerIn: parent
            visible: !root._hasArt
            text: (root.roleLabel || root.seatLabel || "?").substring(0, 1)
            color: Theme.warm.ink
            font.family: Theme.fontFamilies.serif
            font.contextFontMerging: true
            font.pixelSize: root.diameter * 0.42
            font.weight: Theme.weight.bold
        }
        Rectangle {                      // 出局斜杠
            visible: !root.alive
            anchors.centerIn: parent
            width: parent.width * 1.1; height: 3; radius: 1.5; rotation: -45
            color: Theme.warm.error; opacity: 0.85
        }
    }

    Rectangle {                          // 出局 / OUT 角标
        visible: !root.alive
        anchors.horizontalCenter: medallion.horizontalCenter
        anchors.verticalCenter: medallion.bottom
        width: outText.implicitWidth + Theme.space.sm; height: outText.implicitHeight + 3
        radius: Theme.radius.sm; color: Theme.withAlpha(Theme.warm.error, 0.92)
        Text {
            id: outText; anchors.centerIn: parent
            text: I18n.t("出局", "OUT")
            color: "#ffffff"
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
        }
    }

    Rectangle {                          // 名牌
        anchors.top: medallion.bottom
        anchors.topMargin: root.alive ? 4 : 13
        anchors.horizontalCenter: medallion.horizontalCenter
        width: plate.implicitWidth + Theme.space.sm; height: plate.implicitHeight + 2
        radius: Theme.radius.sm; color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.82)
        Text {
            id: plate; anchors.centerIn: parent
            text: root.seatLabel + (root.roleLabel ? " · " + root.roleLabel : "")
            color: root.alive ? Theme.warm.ink : Theme.warm.muted
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro
        }
    }
}
```

- [ ] **Step 2: CMake 注册** `        qml/components/CharacterAvatar.qml`

- [ ] **Step 3: 契约**

`QtObserverGameRedesignPhase2Tests` 加:
```python
    def test_character_avatar_contract(self) -> None:
        c = (QT / "qml/components/CharacterAvatar.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "characterAvatar"', c)
        self.assertIn("Illustrations.avatar(", c)
        for prop in ["roleKey", "alive", "speaking", "accent"]:
            self.assertIn(prop, c)
        self.assertIn("CharacterAvatar.qml", (QT / "CMakeLists.txt").read_text(encoding="utf-8"))
```

- [ ] **Step 4: 结构门 + 构建 + Commit**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract.QtObserverGameRedesignPhase2Tests -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
git add clients/qt_observer/qml/components/CharacterAvatar.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): CharacterAvatar (circular role bust + faction ring + alive/speaking/out + fallback)"
```

---

## Task 3: PhaseBackground + PhaseIndicator

**Files:** Create 两个组件;Modify `CMakeLists.txt`、契约。

- [ ] **Step 1: PhaseBackground.qml**

```qml
import QtQuick
import qt_observer

// 圆桌房间背景:table-day/night 随 phase 交叉淡入。资产缺失 → phase 暖渐变兜底。
Item {
    id: root
    objectName: "phaseBackground"
    property string phase: "day"
    readonly property bool _night: phase === "night"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root._night ? Theme.phase.night.sky : Theme.phase.day.bg }
            GradientStop { position: 1.0; color: root._night ? Theme.warm.surfaceDark : Theme.phase.day.ambient }
        }
    }
    Image {
        id: dayImg; anchors.fill: parent
        source: Illustrations.tableDay; fillMode: Image.PreserveAspectCrop
        opacity: (!root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }
    Image {
        id: nightImg; anchors.fill: parent
        source: Illustrations.tableNight; fillMode: Image.PreserveAspectCrop
        opacity: (root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }
}
```

- [ ] **Step 2: PhaseIndicator.qml**

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
        color: root._night ? Theme.warm.accentAmber : Theme.warm.primary
        font.pixelSize: 28
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: (root._night ? I18n.t("黑夜", "Night") : I18n.t("白天", "Day"))
              + " · " + I18n.t("第 ", "R") + root.round
        color: Theme.warm.ink
        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
        font.pixelSize: Theme.size.caption; font.weight: Theme.weight.medium
    }
}
```

- [ ] **Step 3: CMake 注册两行**:`        qml/components/PhaseBackground.qml`、`        qml/components/PhaseIndicator.qml`

- [ ] **Step 4: 契约**
```python
    def test_phase_components_contract(self) -> None:
        bg = (QT / "qml/components/PhaseBackground.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "phaseBackground"', bg)
        self.assertIn("Illustrations.tableDay", bg)
        self.assertIn("Illustrations.tableNight", bg)
        self.assertIn("Gradient", bg)
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

**Files:** Create `qml/components/CockpitSurface.qml`;Modify `CMakeLists.txt`、契约。

**接口(全经属性/插槽,无 ObserverClient):**
- 数据:`players`(`[{player_id,display_role,display_team,visibility,alive}]`)、`deadIds`、`speakingId`、`phase`("day"/"night"/"voting")、`round`、`votes`(`[{target,count}]` 已截断)、`majority`、`dataSourceText`、`perspectiveText`
- 插槽(`Component`,宿主注入,预览/真宿主各给不同实现):`perspectiveSlot`(左上视角切换)、`eventLogSlot`(左中事件流)、`auditSlot`(左下证据/审计折叠条)、`playbackSlot`(右下倍速)
- 信号:`backRequested()`
- 椭圆常量(待真机标定):`cx/cy/ringRx/ringRy/depthK`

- [ ] **Step 1: 写 CockpitSurface.qml**

```qml
import QtQuick
import QtQuick.Controls
import qt_observer
import "."

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
    property string dataSourceText: ""
    property string perspectiveText: ""
    property Component perspectiveSlot: null
    property Component eventLogSlot: null
    property Component auditSlot: null
    property Component playbackSlot: null
    signal backRequested()

    // 椭圆落位(右区比例,待真机按 table-day.png 桌沿标定)
    property real cx: 0.40
    property real cy: 0.54
    property real ringRx: 0.32
    property real ringRy: 0.21       // ≈ Rx·cos(俯角)
    property real depthK: 0.16

    function _angle(i, n) { return (-90 + i * 360 / Math.max(1, n)) * Math.PI / 180 }
    function _roleName(role) {
        var m = ({
            werewolf: I18n.t("狼人","Werewolf"), seer: I18n.t("预言家","Seer"),
            witch: I18n.t("女巫","Witch"), villager: I18n.t("村民","Villager"),
            guard: I18n.t("守卫","Guard"), hunter: I18n.t("猎人","Hunter")
        })
        return m[role] || role
    }

    Rectangle { anchors.fill: parent; color: Theme.warm.canvas }

    // ===== 左区 20% =====
    Rectangle {
        id: leftCol
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Math.max(340, parent.width * 0.20)
        color: Theme.warm.surfaceCard
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.warm.hairline }

        Column {
            id: leftStack
            anchors.fill: parent
            anchors.margins: Theme.space.lg
            spacing: Theme.space.md

            Text {
                text: I18n.t("上帝视角观察", "God's-Eye Observer")
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.titleMd; font.weight: Theme.weight.bold
            }
            AppButton {
                objectName: "cockpitBackButton"
                text: I18n.t("← 返回", "← Back"); variant: "ghost"; onLight: true
                onClicked: root.backRequested()
            }
            Text {
                visible: root.dataSourceText !== ""
                text: root.dataSourceText
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.mono; font.pixelSize: Theme.size.micro
            }
            Text {
                visible: root.perspectiveText !== ""
                text: root.perspectiveText
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.micro
            }
            // 视角切换插槽(左上)
            Loader { width: parent.width; sourceComponent: root.perspectiveSlot }
            // 事件流(占满中部)
            Loader {
                id: eventLogLoader
                width: parent.width
                height: leftStack.height - y - auditLoader.height - leftStack.spacing
                sourceComponent: root.eventLogSlot
            }
            // 证据/审计折叠条(左下)
            Loader { id: auditLoader; width: parent.width; sourceComponent: root.auditSlot }
        }
    }

    // ===== 右区 80% =====
    Item {
        id: stage
        anchors { left: leftCol.right; top: parent.top; right: parent.right; bottom: parent.bottom }
        clip: true

        PhaseBackground { anchors.fill: parent; phase: root.phase }

        PhaseIndicator {
            phase: root.phase; round: root.round
            x: stage.width * root.cx - width / 2
            y: stage.height * root.cy - height / 2
        }

        // 投票/行动箭头(座位间珊瑚虚线;Task 7 细化箭头朝向)
        Canvas {
            id: arrows
            anchors.fill: parent
            property var v: root.votes
            onVChanged: requestPaint(); onWidthChanged: requestPaint(); onHeightChanged: requestPaint()
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
                ctx.strokeStyle = Theme.warm.primary; ctx.lineWidth = 2
                ctx.setLineDash([6, 5]); ctx.globalAlpha = 0.7
                for (var k = 0; k < root.votes.length; k++) {
                    var pt = _seatPt(root.votes[k].target)
                    if (pt) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 5, 0, 2 * Math.PI); ctx.stroke() }
                }
            }
        }

        // 椭圆头像环
        Repeater {
            model: root.players
            delegate: CharacterAvatar {
                required property var modelData
                required property int index
                readonly property real _th: root._angle(index, root.players.length)
                readonly property real _sin: Math.sin(_th)
                diameter: Math.min(stage.width, stage.height) * 0.13 * (1 + root.depthK * _sin)
                x: stage.width * root.cx + stage.width * root.ringRx * Math.cos(_th) - width / 2
                y: stage.height * root.cy + stage.height * root.ringRy * _sin - diameter / 2
                z: 10 + _sin
                roleKey: (modelData.display_role && modelData.display_role !== "unknown") ? modelData.display_role : ""
                roleLabel: roleKey ? root._roleName(modelData.display_role) : ""
                seatLabel: modelData.player_id
                accent: roleKey ? Theme.roleAccent(modelData.display_role) : Theme.warm.hairline
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
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.9)
            border.width: 1; border.color: Theme.warm.hairline
            Text {
                id: phaseChipText; anchors.centerIn: parent
                text: (root.phase === "night" ? "☾ " + I18n.t("黑夜","Night") : "☀ " + I18n.t("白天","Day"))
                      + " · " + I18n.t("第 ","R") + root.round
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.caption
            }
        }

        // 悬浮:当前票数(右)
        Rectangle {
            id: votesPanel
            anchors { right: parent.right; top: phaseChip.bottom; topMargin: Theme.space.sm; rightMargin: Theme.space.lg }
            width: stage.width * 0.28
            implicitHeight: votesCol.implicitHeight + Theme.space.lg
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.9)
            border.width: 1; border.color: Theme.warm.hairline
            visible: root.votes && root.votes.length > 0
            Column {
                id: votesCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.space.md }
                spacing: 2
                Text {
                    text: I18n.t("当前票数", "Current Votes")
                    color: Theme.warm.primary
                    font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                    font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
                }
                Repeater {
                    model: root.votes
                    delegate: Text {
                        required property var modelData
                        text: modelData.target + "  ●×" + modelData.count
                        color: Theme.warm.body
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
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
            implicitWidth: majText.implicitWidth + Theme.space.xxxl
            implicitHeight: majText.implicitHeight + Theme.space.sm
            radius: Theme.radius.pill
            color: Theme.withAlpha(Theme.warm.surfaceDark, 0.55)
            Text {
                id: majText; anchors.centerIn: parent
                text: "──  " + I18n.t("多数线 ", "Majority ") + root.majority + "  ──"
                color: Theme.warm.canvas
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.caption
            }
        }
    }
}
```

> `required property var modelData` / `required property int index`:`CockpitSurface.qml` 顶部需 `pragma ComponentBehavior: Bound`?——否。`Repeater` delegate 用 `required property` 是 Qt6 推荐写法,无需 pragma。若构建报 `modelData` 未定义,改回隐式 `modelData`/`index`(去掉 required 行)。`onLight` 是 Phase 1 `AppButton` 暖色开关。

- [ ] **Step 2: CMake 注册** `        qml/components/CockpitSurface.qml`

- [ ] **Step 3: 契约**
```python
    def test_cockpit_surface_contract(self) -> None:
        c = (QT / "qml/components/CockpitSurface.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "cockpitSurface"', c)
        for comp in ["PhaseBackground", "CharacterAvatar", "PhaseIndicator"]:
            self.assertIn(comp, c)
        self.assertNotIn("ObserverClient", c)        # 表现型:数据经属性
        for slot in ["perspectiveSlot", "eventLogSlot", "auditSlot", "playbackSlot"]:
            self.assertIn(slot, c)
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
git commit -m "feat(qt-redesign): CockpitSurface presentational live page (ellipse avatar ring + 4 host slots + floating panels)"
```

---

## Task 5: DesignPreviewView + 首页入口 + 烤死样例 + stub 控件 ← 最早可截图验收点

**Files:** Create `qml/DesignPreviewView.qml`;Modify `HomeView.qml`、`AppShell.qml`、`CMakeLists.txt`、契约。

> 预览页**自带 stub 视角切换 / 倍速 / 审计折叠条**(静态、不接 ObserverClient),让首张截图就能验全部 5 个验收要点(阶段/票数/多数线/数据源真相/审计+倍速位置)。

- [ ] **Step 1: DesignPreviewView.qml**

```qml
import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// 静态宿主:烤死样例 + stub 控件驱动 CockpitSurface,不接 ObserverClient、不开 run。
// 真相标记固定「设计样例」,绝不读 ObserverClient.currentExecutionMode。
Item {
    id: root
    objectName: "designPreviewView"

    property string previewPhase: "day"      // day / night / voting
    property bool eightSeat: false           // synthetic 8 座 smoke(验环 N-可变,纯前端)

    readonly property var _six: [
        { player_id: "1", display_role: "werewolf", display_team: "werewolf", visibility: "visible", alive: true },
        { player_id: "2", display_role: "seer",     display_team: "village",  visibility: "visible", alive: true },
        { player_id: "3", display_role: "witch",    display_team: "village",  visibility: "visible", alive: true },
        { player_id: "4", display_role: "villager", display_team: "village",  visibility: "visible", alive: true },
        { player_id: "5", display_role: "guard",    display_team: "village",  visibility: "visible", alive: true },
        { player_id: "6", display_role: "hunter",   display_team: "village",  visibility: "visible", alive: false }
    ]
    readonly property var _eight: _six.concat([
        { player_id: "7", display_role: "villager", display_team: "village", visibility: "visible", alive: true },
        { player_id: "8", display_role: "werewolf", display_team: "werewolf", visibility: "visible", alive: true }
    ])
    readonly property var _events: [
        { t: "00:01", text: I18n.t("第二天开始", "Day 2 begins") },
        { t: "00:07", text: I18n.t("4 号发言", "Seat 4 speaks") },
        { t: "00:09", text: I18n.t("4 号 → 5 号", "4 → 5") },
        { t: "00:21", text: I18n.t("2 号附议", "2 seconds it") }
    ]

    Rectangle { anchors.fill: parent; color: Theme.warm.canvas }

    CockpitSurface {
        id: surface
        anchors.fill: parent
        players: root.eightSeat ? root._eight : root._six
        deadIds: ["6"]
        speakingId: "4"
        phase: root.previewPhase
        round: 2
        votes: root.previewPhase === "voting" ? [ { target: "5", count: 3 }, { target: "1", count: 2 } ] : []
        majority: root.previewPhase === "voting" ? 4 : 0
        dataSourceText: I18n.t("设计样例", "Design Sample")
        perspectiveText: I18n.t("上帝视角", "God's-Eye")
        perspectiveSlot: stubPerspective
        eventLogSlot: stubEventLog
        auditSlot: stubAudit
        playbackSlot: stubPlayback
        onBackRequested: root.StackView.view.parent.navigateHome()
    }

    // stub 视角切换(静态 pill)
    Component {
        id: stubPerspective
        Rectangle {
            height: 28; radius: Theme.radius.pill
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.9); border.width: 1; border.color: Theme.warm.hairline
            Text {
                anchors.centerIn: parent
                text: I18n.t("视角:上帝视角 ▾", "View: God's-Eye ▾")
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.micro
            }
        }
    }
    // stub 事件流
    Component {
        id: stubEventLog
        ListView {
            model: root._events; spacing: Theme.space.xs; clip: true
            delegate: Row {
                required property var modelData
                spacing: Theme.space.sm
                Text { text: modelData.t; color: Theme.warm.muted; font.family: Theme.fontFamilies.mono; font.pixelSize: Theme.size.micro }
                Text {
                    text: modelData.text; color: Theme.warm.body
                    font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.caption
                }
            }
        }
    }
    // stub 证据/审计折叠条
    Component {
        id: stubAudit
        Rectangle {
            height: 30; radius: Theme.radius.sm
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.7); border.width: 1; border.color: Theme.warm.hairline
            Text {
                anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: Theme.space.sm
                text: I18n.t("▸ 证据 / 审计", "▸ Evidence / Audit")
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.micro
            }
        }
    }
    // stub 倍速/播放
    Component {
        id: stubPlayback
        Rectangle {
            implicitHeight: 36; radius: Theme.radius.md
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.92); border.width: 1; border.color: Theme.warm.primary
            Text {
                anchors.centerIn: parent
                text: "▶   ⏸   1x  2x  4x"
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.caption
            }
        }
    }

    // 昼/夜/投票/(8座)切换(预览专用)
    Row {
        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: Theme.space.lg }
        spacing: Theme.space.sm
        Repeater {
            model: [ { k: "day", t: I18n.t("白天","Day") }, { k: "night", t: I18n.t("黑夜","Night") }, { k: "voting", t: I18n.t("投票","Voting") } ]
            delegate: AppButton {
                required property var modelData
                objectName: "previewPhase_" + modelData.k
                text: modelData.t; onLight: true
                variant: root.previewPhase === modelData.k ? "primary" : "ghost"
                onClicked: root.previewPhase = modelData.k
            }
        }
        AppButton {
            objectName: "previewSeatToggle"
            text: root.eightSeat ? I18n.t("6 座","6") : I18n.t("8 座","8")
            variant: "ghost"; onLight: true
            onClicked: root.eightSeat = !root.eightSeat
        }
    }
}
```

> `onBackRequested:` 是绑信号的**正确**写法(`signal backRequested()` → `onBackRequested`);不要写 `backRequested: function(){}`(QML 不支持给信号赋函数)。

- [ ] **Step 2: HomeView 加入口**

`qml/HomeView.qml` hero 按钮区(`startNewMatchButton` 附近)加:
```qml
                AppButton {
                    objectName: "designPreviewButton"
                    text: I18n.t("🎴 设计预览", "🎴 Design Preview")
                    variant: "ghost"; onLight: true
                    onClicked: root.StackView.view.parent.navigateDesignPreview()
                }
```

- [ ] **Step 3: AppShell 加路由**

仿现有 `cockpitComponent` + `navigate*`:
```qml
    Component { id: designPreviewComponent; DesignPreviewView { } }
```
```qml
    function navigateDesignPreview() {
        currentView = "designPreview"
        stackView.replace(designPreviewComponent)
    }
```
> `currentView !== "home"` → 显示顶栏,预览页显示顶栏即可,不影响 home 顶栏隐藏逻辑。

- [ ] **Step 4: CMake 注册** `        qml/DesignPreviewView.qml`

- [ ] **Step 5: 契约更新**

`REQUIRED_QML_VIEWS` 加 `"qml/DesignPreviewView.qml"`;`REQUIRED_OBJECT_NAMES` 加 `"qml/DesignPreviewView.qml": ["designPreviewView"]`;`REQUIRED_OBJECT_NAMES["qml/HomeView.qml"]` 追加 `"designPreviewButton"`。`QtObserverGameRedesignPhase2Tests` 加:
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
        self.assertNotIn("currentExecutionMode", c)
        self.assertNotIn("ObserverClient", c)
        self.assertIn('objectName: "designPreviewView"', c)
        # stub 控件齐(验收要看审计/倍速/视角位置)
        for slot in ["perspectiveSlot:", "auditSlot:", "playbackSlot:", "eventLogSlot:"]:
            self.assertIn(slot, c)
```

- [ ] **Step 6: 结构门 + 构建**
```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: 全绿 + exit 0。

- [ ] **Step 7: 截图自验(首个视觉验收 — 昼/夜/投票/8座)**

`AppShell.qml` 临时 harness(跑完撤):
```qml
    Timer {
        running: true; interval: 600; property int n: 0
        property var modes: ["day","night","voting"]
        onTriggered: {
            navigateDesignPreview()
            var v = appShellStack.currentItem
            if (n < 3) v.previewPhase = modes[n]
            else if (n === 3) { v.previewPhase = "day"; v.eightSeat = true }
            else { Qt.quit(); return }
            root.grabToImage(function(res){ res.saveToFile("G:/Werewolf-agent/.tmp/preview_" + n + ".png") })
            n++; interval = 900
        }
    }
```
```bash
QT_QPA_PLATFORM=offscreen .tmp/qt-observer-build/appqt_observer.exe
```
Read `.tmp/preview_0..3.png` 核对:头像贴桌沿椭圆、偏左留空使悬浮件不盖头像、昼/夜背景、投票面板+多数线、左下审计条+右下倍速、8 座仍均分。**据此微调 CockpitSurface 的 `cx/cy/ringRx/ringRy/depthK`**(改→重构建→重截)。撤:`git checkout -- clients/qt_observer/qml/AppShell.qml`。

- [ ] **Step 8: Commit**
```bash
git add clients/qt_observer/qml/DesignPreviewView.qml clients/qt_observer/qml/HomeView.qml clients/qt_observer/qml/AppShell.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): HomeView Design Preview entry + DesignPreviewView (static sample + stub controls; day/night/voting/8-seat)"
```

---

## Task 6: TheaterView 重写为 live 宿主 + 票数派生 + 视角左上

**Files:** Modify `qml/TheaterView.qml`、`qml/EventPresentationQueue.qml`、`qml/components/EvidenceConsole.qml`、契约。

> **保留逐字**:`objectName: "theaterView"`、`EventPresentationQueue { id: eventQueue }`、`state: eventQueue.layoutPhase`、`resumeAfterTransition` 接线、`navigateHome` 退出、`SettlementView` overlay(`currentStatus === "completed"`)、**不得出现 `ring.perspective =`**。这些被 `QtObserverTheaterViewTests` 钉死。

- [ ] **Step 1: EventPresentationQueue 加只读 `currentRound` + `voteTally`(按游标截断,镜像 `deadPlayers` 的扫描法,绝不用全量 `enriched`/`projectionEvents` 算最终票)**

`qml/EventPresentationQueue.qml`,在 `deadPlayers` 属性后加:
```qml
    // 当前 round = phaseTimeline 末项(已按游标截断)。
    readonly property int currentRound: phaseTimeline.length ? phaseTimeline[phaseTimeline.length - 1].round : 0

    // 当前 round 的票数聚合,仅统计「已消费到游标(0.._cursor)」的 player_vote。
    // 与 deadPlayers 同法扫描 _ordered[0.._cursor);target 优先取 enrichment,缺则 raw.target。
    // 绝不扫完整 enriched/source(会显示未来票)。
    readonly property var voteTally: {
        var counts = ({})
        var n = Math.min(_cursor, _ordered.length)
        var cr = currentRound
        for (var i = 0; i < n; i++) {
            var raw = _ordered[i]
            var t = (raw && raw.payload) ? raw.payload.type : (raw ? raw.type : "")
            if (t !== "player_vote") continue
            var rr = (raw && raw.round !== undefined && raw.round !== null) ? raw.round : 0
            if (rr !== cr) continue
            var gid = (raw && raw.payload) ? raw.payload.event_id : (raw ? raw.event_id : "")
            var enr = (gid && _enrichedById[gid]) ? _enrichedById[gid] : null
            var tgt = (enr && enr.target && enr.target !== "none") ? enr.target : ((raw && raw.target) ? raw.target : "")
            if (!tgt) continue
            counts[tgt] = (counts[tgt] || 0) + 1
        }
        var out = []
        for (var k in counts) out.push({ target: k, count: counts[k] })
        out.sort(function(a, b) { return b.count - a.count })
        return out
    }
```

- [ ] **Step 2: EvidenceConsole 加 `showPerspectiveSwitcher` 开关**

`qml/components/EvidenceConsole.qml`:加 `property bool showPerspectiveSwitcher: true`;把含 `PerspectiveSwitcher` 的 `lensRow` 的 `visible` 与之 AND:
```qml
        Row {
            id: lensRow
            visible: root.showPerspectiveSwitcher && (root.mode === 1 || root.mode === 2)
            ...
```
> `test_evidence_console_rehomes_honesty_chain` 仍要求 EvidenceConsole **包含** `PerspectiveSwitcher` 字样(组件在即可)。

- [ ] **Step 3: 重写 TheaterView 主体为 CockpitSurface 宿主**

保留顶部 `Component.onCompleted`/`Connections`/`projRefreshTimer`/`EventPresentationQueue`/状态机/`SettlementView` Loader 不变;把 `topBar + PhaseTimeline + stage + EvidenceConsole` 替换为:
```qml
    CockpitSurface {
        id: surface
        anchors.fill: parent
        players: ObserverClient.playerItems
        deadIds: eventQueue.deadPlayers
        speakingId: eventQueue.current ? (eventQueue.current.actor || "") : ""
        phase: eventQueue.layoutPhase
        round: eventQueue.currentRound
        votes: eventQueue.voteTally
        majority: theaterRoot._majority
        dataSourceText: ObserverClient.currentExecutionMode === "live" ? I18n.t("真实 LIVE","LIVE") : I18n.t("模拟","SIMULATION")
        perspectiveText: I18n.t("视角:","View: ") + ObserverClient.currentPerspective
        perspectiveSlot: livePerspective
        eventLogSlot: liveEventLog
        auditSlot: liveAudit
        playbackSlot: livePlayback
        onBackRequested: { ObserverClient.disconnectStream(); theaterRoot.StackView.view.parent.navigateHome() }
    }

    // 视角切换在左上(spec §5);EvidenceConsole 内的重复 switcher 关掉(单实例铁律)
    Component { id: livePerspective; PerspectiveSwitcher { } }
    Component { id: liveEventLog;   EventTimeline { } }
    Component { id: livePlayback;   PlaybackControls { queue: eventQueue } }
    Component { id: liveAudit;      EvidenceConsole { perspective: ObserverClient.currentPerspective; showPerspectiveSwitcher: false } }
```
并加多数线派生:
```qml
    readonly property int _deadCount: eventQueue.deadPlayers ? eventQueue.deadPlayers.length : 0
    readonly property int _majority: Math.floor((ObserverClient.playerItems.length - theaterRoot._deadCount) / 2) + 1
```

- [ ] **Step 4: 契约同步**

`QtObserverTheaterViewTests` 既有断言应仍绿。加(并入该类或 Phase2 类):
```python
    def test_event_queue_exposes_cursor_truncated_votes(self) -> None:
        c = (QT / "qml/EventPresentationQueue.qml").read_text(encoding="utf-8")
        self.assertIn("readonly property var voteTally", c)
        self.assertIn("readonly property int currentRound", c)
        self.assertIn("Math.min(_cursor, _ordered.length)", c)   # 按游标截断
    def test_theater_hosts_cockpit_surface(self) -> None:
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("CockpitSurface", t)
        self.assertIn("ObserverClient.playerItems", t)
        self.assertIn("eventQueue.voteTally", t)              # 票数来自截断派生
        self.assertNotIn("ObserverClient.projectionEvents", t.split("votes:")[1].split("\n")[0] if "votes:" in t else "")
        self.assertIn("showPerspectiveSwitcher: false", t)    # 单实例:EvidenceConsole 关 switcher
        self.assertIn("PerspectiveSwitcher", t)               # 视角切换在左上 slot
    def test_evidence_console_perspective_toggle(self) -> None:
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

- [ ] **Step 6: 截图自验(真 server,含结算)** — 见「关键约定」截图段;跑 `default_6p_fake` 一局,截直播页昼/夜 + 结算,核对与预览一致。

- [ ] **Step 7: Commit**
```bash
git add clients/qt_observer/qml/TheaterView.qml clients/qt_observer/qml/EventPresentationQueue.qml clients/qt_observer/qml/components/EvidenceConsole.qml tests/test_qt_observer_static_contract.py
git commit -m "feat(qt-redesign): TheaterView hosts CockpitSurface (live bindings preserved; cursor-truncated voteTally/currentRound; perspective top-left, single instance)"
```

---

## Task 7: 昼夜/投票呼吸 + 投票箭头 + 结算 overlay 重皮

**Files:** Modify `qml/components/CockpitSurface.qml`、`qml/TheaterView.qml`、`qml/SettlementView.qml`(仅暖色令牌,不动结算逻辑/cursor 契约)。

- [ ] **Step 1: CockpitSurface 昼夜呼吸**:phase 变化时环整体缩放 / 事件流淡入,用 `states`+`Behavior`(只动尺寸/透明度,不动容器位置)。
- [ ] **Step 2: 箭头升级**:`arrows` Canvas 从「目标圈」升级为「投票者→目标」珊瑚虚线 + 箭头;夜间用 `Theme.roleAccent` 阵营色(狼刀/查验/守护)。坐标用 `_seatPt`。
- [ ] **Step 3: SettlementView overlay 重皮**:只改暖色令牌/onLight,**不动** `cursorIndex`/`fetchSettlement`/`boardState`/morph states 契约(`QtObserverSettlementViewTests` 钉死)。
- [ ] **Step 4: 结构门 + 构建 + 截图矩阵**(昼/夜/投票/结算,至少含 1280×720)。
- [ ] **Step 5: Commit**
```bash
git add clients/qt_observer/qml/components/CockpitSurface.qml clients/qt_observer/qml/TheaterView.qml clients/qt_observer/qml/SettlementView.qml
git commit -m "feat(qt-redesign): cockpit day/night/voting breathing + vote/action arrows + settlement overlay reskin"
```

---

## Task 8: 删除 LiveCockpitView + 迁移其契约不变量

**Files:** Delete `qml/LiveCockpitView.qml`;Modify `CMakeLists.txt`、契约。

> 删前其不变量须已由新面承载:无硬编码角色 / 用 projection → `CockpitSurface`(`players` 经投影,不硬编码);边界+证明 → `EvidenceConsole`(`test_evidence_console_rehomes_honesty_chain` 已覆盖)。

- [ ] **Step 1: 删文件 + CMake 去注册**
```bash
git rm clients/qt_observer/qml/LiveCockpitView.qml
```
`CMakeLists.txt` 删 `        qml/LiveCockpitView.qml` 行。

- [ ] **Step 2: 契约删除/改写 LiveCockpitView 相关断言**

`tests/test_qt_observer_static_contract.py`:
- `REQUIRED_QML_VIEWS`:删 `"qml/LiveCockpitView.qml"`。
- `REQUIRED_OBJECT_NAMES`:删 `"qml/LiveCockpitView.qml": [...]` 整条。
- `QtObserverCockpitContractTests.test_cockpit_contains_required_object_names`:**删除**(其 objectName 已被 EvidenceConsole 在 REQUIRED_OBJECT_NAMES 覆盖)。
- `QtObserverHiddenInfoBoundaryTests`:`test_live_cockpit_does_not_embed_static_role_assignments` / `test_qml_boundary_copy_mentions_server_projection` → **改读** `qml/components/CockpitSurface.qml`(见下);`test_qt_client_does_not_use_local_snapshot_or_event_paths` 与 LiveCockpit 无关,保留。
- `QtObserverVisibilityUiTests`:`test_live_cockpit_uses_projection_player_items` → 改读 `TheaterView`;`test_live_cockpit_contains_boundary_badge_and_proof_panel` → **删除**(已被 `test_evidence_console_rehomes_honesty_chain` 覆盖);`test_cockpit_does_not_hardcode_god_roles_as_live_player_source` → 改读 `CockpitSurface`。

改写后的替代断言(加进 `QtObserverGameRedesignPhase2Tests` 或就地改):
```python
    def test_cockpit_surface_no_hardcoded_roles(self) -> None:
        c = (QT / "qml/components/CockpitSurface.qml").read_text(encoding="utf-8")
        self.assertNotRegex(c, r'(display_role|role):\s*"(?:Werewolf|Seer|Witch|Villager)"')
        self.assertIn("players", c)
    def test_theater_uses_projection_player_items(self) -> None:
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("ObserverClient.playerItems", t)
```

- [ ] **Step 3: 全量结构门 + 构建(零残留)**
```bash
grep -rn "LiveCockpitView\|liveCockpitView" clients/qt_observer tests | grep -v ".tmp"   # 期望:空
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: grep 空;测试全绿;exit 0。

- [ ] **Step 4: Commit**
```bash
git add -A clients/qt_observer tests/test_qt_observer_static_contract.py
git commit -m "chore(qt-redesign): delete dead LiveCockpitView + re-home its contract invariants to CockpitSurface/TheaterView/EvidenceConsole"
```

---

## Task 9: 截图矩阵复核 + 压缩收尾 + 清理

- [ ] **Step 1: 截图矩阵**:经 `DesignPreviewView` 截 白天/黑夜/投票/8座;经真 server 截 结算(胜/负)。分辨率 1280×720(小屏)+ 1920×1080。逐张 Read 核对验收(下「验收」)。
- [ ] **Step 2: 资产最终压缩**(Task 1 若跳过):pngquant 压 8 张,重构建确认体积降、显示无明显劣化。
- [ ] **Step 3: 三件门全跑**:`unittest` 结构门 + `ctest --test-dir .tmp/qt-observer-build` + `qmllint -I .tmp/qt-observer-build qml/*.qml qml/components/*.qml`(只看 `Error:`)。
- [ ] **Step 4: 清理**:`git status` 干净(无残留临时 harness、无 `.tmp` 截图入仓)。
- [ ] **Step 5: Commit(若有压缩)**
```bash
git add clients/qt_observer/assets/illustrations
git commit -m "perf(qt-redesign): compress Phase2 illustration assets (pngquant)"
```

---

## 验收(spec §11)

- 暖色 + 质感 + 字体舒适三点消解。
- 一眼可见:阶段/轮次、当前发言者、存活/出局、投票目标与票数、多数线、LIVE/SIMULATION(预览=设计样例)真相、左下证据/审计与右下倍速的位置。
- 头像按椭圆贴合背景桌沿;偏左留空使悬浮件不盖头像。
- 座位 N-可变:**当前 backend perspective=p1–p6(6 座)**为真实验收;椭圆环 N-可变以 `DesignPreviewView` 的 **synthetic 8 座纯前端 smoke** 佐证(不接 backend、不改 perspective 契约)。
- 截图矩阵:白天/黑夜/投票/结算 × {1280×720, 1920×1080};经 `DesignPreviewView`(无需真局)+ 真 server(结算)。
- 三件门绿;`LiveCockpitView` 残留为零。
