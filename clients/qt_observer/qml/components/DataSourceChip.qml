import QtQuick
import qt_observer

// G3-2 global HUD chip — EXECUTED TRUTH, not intent.
//
// `mode` is driven by run-detail execution_mode (ObserverClient.currentExecutionMode):
// the chip reads "SYS: LIVE_API" iff mode === "live", otherwise the conservative
// "SYS: SIMULATION" (the default until run detail returns a mode — never optimistic).
// Nominalized HUD register, monochrome luminance (not chromatic).
Rectangle {
    id: root

    property string mode: ""

    readonly property bool _live: ("" + root.mode).toLowerCase() === "live"

    implicitWidth: row.implicitWidth + Theme.space.md * 2
    implicitHeight: 22
    radius: Theme.radius.sm
    color: root._live ? Theme.withAlpha(Theme.color.text, 0.14) : Theme.color.surfaceInset
    border.width: 1
    border.color: root._live ? Theme.color.borderStrong : Theme.color.border

    Behavior on color { ColorAnimation { duration: Theme.motion.base } }
    Behavior on border.color { ColorAnimation { duration: Theme.motion.base } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: Theme.space.xs

        GlowDot {
            anchors.verticalCenter: parent.verticalCenter
            diameter: 7
            color: root._live ? Theme.color.text : Theme.color.textMuted
            pulse: root._live
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root._live
                  ? I18n.t("环境: 真实AI", "SYS: LIVE_API")
                  : I18n.t("环境: 模拟", "SYS: SIMULATION")
            color: root._live ? Theme.color.text : Theme.color.textMuted
            font.family: Theme.font.mono
            font.pixelSize: Theme.size.micro
            font.weight: Theme.weight.semibold
            font.letterSpacing: 1
        }
    }
}
