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
