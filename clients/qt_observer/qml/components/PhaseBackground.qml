import QtQuick
import qt_observer

// 圆桌房间背景:table-day/night 随 phase 交叉淡入。PreserveAspectFit 保住原图构图
// (桌子偏左 + 右留白不被裁掉)。暴露实际绘制矩形 painted*,供上层把头像环精确对到画里的桌沿。
// 资产缺失 → phase 暖渐变兜底。
Item {
    id: root
    objectName: "phaseBackground"
    property string phase: "day"
    readonly property bool _night: phase === "night"

    // 当前激活图实际绘制出的矩形(两图同尺寸,取 dayImg 即可),供头像落位对齐。
    readonly property real paintedW: dayImg.paintedWidth > 0 ? dayImg.paintedWidth : width
    readonly property real paintedH: dayImg.paintedHeight > 0 ? dayImg.paintedHeight : height
    readonly property real paintedX: (width - paintedW) / 2
    readonly property real paintedY: (height - paintedH) / 2

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root._night ? Theme.phase.night.sky : Theme.phase.day.bg }
            GradientStop { position: 1.0; color: root._night ? Theme.warm.surfaceDark : Theme.phase.day.ambient }
        }
    }
    Image {
        id: dayImg; anchors.fill: parent
        source: Illustrations.tableDay; fillMode: Image.PreserveAspectFit
        opacity: (!root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }
    Image {
        id: nightImg; anchors.fill: parent
        source: Illustrations.tableNight; fillMode: Image.PreserveAspectFit
        opacity: (root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }

    // Lighting pass — a real phase mood instead of a flat blue filter:
    //   warm centre glow (candle/window light focused on the table) +,
    //   at night, a peripheral vignette so the edges sink into shadow.
    // Both align to the painted table rect (not the letterboxed item).
    Image {
        id: warmGlow
        source: Illustrations.texWarmGlow
        readonly property real _cx: root.paintedX + root.paintedW * 0.40
        readonly property real _cy: root.paintedY + root.paintedH * 0.52
        width: root.paintedW * 0.98; height: width
        x: _cx - width / 2; y: _cy - height / 2
        opacity: root._night ? 0.85 : 0.20
        Behavior on opacity { NumberAnimation { duration: Theme.motion.slow } }
    }
    Image {
        id: nightVignette
        source: Illustrations.texNightVignette
        x: root.paintedX; y: root.paintedY
        width: root.paintedW; height: root.paintedH
        fillMode: Image.Stretch
        opacity: root._night ? 0.92 : 0.0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.slow } }
    }
}
