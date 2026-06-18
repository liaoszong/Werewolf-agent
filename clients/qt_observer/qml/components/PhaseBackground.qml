import QtQuick
import qt_observer

// 圆桌房间背景:table-day/night 随 phase 交叉淡入。PreserveAspectCrop 满幅铺盘面(无
// letterbox 空带),新水彩图四边自带奶油晕染,裁到的边仍是奶油纸,无突兀硬边。暴露实际
// 绘制矩形 painted*(Crop 下为覆盖缩放尺寸,offset 可为负),供上层把头像环对到画里的桌沿。
// 资产缺失 → 奶油兜底。
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

    // The new table art is a soft watercolor vignette that dissolves into warm cream
    // paper at its edges; this fallback fill matches that cream so that, while the art
    // loads (or if it is missing), the PreserveAspectCrop board blends seamlessly into
    // one continuous storybook page — no visible seams.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#f6e6c6" }
            GradientStop { position: 1.0; color: "#f1ddb6" }
        }
    }
    Image {
        id: dayImg; anchors.fill: parent
        source: Illustrations.tableDay; fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        sourceSize.width: Math.max(1, Math.ceil(width * 2))
        sourceSize.height: Math.max(1, Math.ceil(height * 2))
        opacity: (!root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }
    Image {
        id: nightImg; anchors.fill: parent
        source: Illustrations.tableNight; fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        sourceSize.width: Math.max(1, Math.ceil(width * 2))
        sourceSize.height: Math.max(1, Math.ceil(height * 2))
        opacity: (root._night && status === Image.Ready) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }
    }

    // (Lighting is baked into the new day/night watercolor art — no extra glow /
    // vignette overlays needed; they would fight the painting's own cream edges.)
}
