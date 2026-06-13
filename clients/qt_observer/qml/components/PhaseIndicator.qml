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
