import QtQuick
import qt_observer

// P2-C-1 top phase progress axis ("糖葫芦"). Upper tier: the major day/night nodes that have
// elapsed (past = dim, current = bright). Lower tier: the current phase's action slots
// (night = wolf/seer/witch, day = speech/vote) with a glowing capsule that slides — Behavior
// on x — to whichever step is acting now. Reads presentation fields only; never mutates state.
Item {
    id: root
    objectName: "phaseTimeline"

    property var phases: []          // queue.phaseTimeline — [{round, phase}]
    property string phase: "day"     // current major phase (night|day)
    property string action: ""       // queue.currentAction (wolf|seer|witch|speech|vote)

    implicitHeight: 54

    // Fixed-width slots make the sliding capsule trivial (x = index * pitch).
    readonly property int _slotW: 78
    readonly property int _slotH: 24
    readonly property int _gap: Theme.space.sm
    readonly property int _pitch: _slotW + _gap

    readonly property var _subs: phase === "night"
        ? [{ key: "wolf", label: I18n.t("狼人", "Wolves") },
           { key: "seer", label: I18n.t("预言家", "Seer") },
           { key: "witch", label: I18n.t("女巫", "Witch") }]
        : [{ key: "speech", label: I18n.t("发言", "Speech") },
           { key: "vote", label: I18n.t("投票", "Vote") }]
    readonly property int _activeSub: {
        for (var i = 0; i < _subs.length; i++)
            if (_subs[i].key === action)
                return i
        return -1
    }
    function _actionAccent(key) {
        switch (key) {
        case "wolf":   return Theme.color.werewolf
        case "seer":   return Theme.color.seer
        case "witch":  return Theme.color.witch
        case "vote":   return Theme.color.textSecondary
        default:       return Theme.color.info
        }
    }

    Column {
        anchors.fill: parent
        spacing: Theme.space.xs

        // ---- Upper tier: elapsed major day/night nodes ----
        Row {
            id: majorRow
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 0
            Repeater {
                model: root.phases
                delegate: Row {
                    id: node
                    required property int index
                    required property var modelData
                    spacing: 0
                    readonly property bool isCurrent: index === root.phases.length - 1

                    // Connector from the previous node.
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: node.index > 0
                        width: Theme.space.lg
                        height: 1
                        color: Theme.color.border
                    }
                    Row {
                        spacing: Theme.space.xs
                        leftPadding: node.index > 0 ? Theme.space.xs : 0
                        rightPadding: Theme.space.xs
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: node.isCurrent ? 9 : 6
                            height: width
                            radius: width / 2
                            color: node.isCurrent
                                   ? (root.phase === "night" ? Theme.color.info : Theme.color.seer)
                                   : Theme.color.borderStrong
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: (node.modelData.phase === "night" ? I18n.t("夜", "N") : I18n.t("日", "D"))
                                  + node.modelData.round
                            color: node.isCurrent ? Theme.color.text : Theme.color.textMuted
                            font.family: Theme.font.mono
                            font.pixelSize: Theme.size.micro
                            font.weight: node.isCurrent ? Theme.weight.bold : Theme.weight.medium
                            renderType: Text.NativeRendering
                        }
                    }
                }
            }
        }

        // ---- Lower tier: current phase's action slots + sliding glow capsule ----
        Item {
            id: subTrack
            anchors.horizontalCenter: parent.horizontalCenter
            width: root._subs.length * root._slotW + (root._subs.length - 1) * root._gap
            height: root._slotH

            // The breathing highlight capsule — slides to the active step.
            Rectangle {
                id: capsule
                visible: root._activeSub >= 0
                width: root._slotW
                height: root._slotH
                radius: Theme.radius.pill
                x: root._activeSub >= 0 ? root._activeSub * root._pitch : 0
                color: Theme.withAlpha(root._actionAccent(root.action), 0.18)
                border.width: 1
                border.color: Theme.withAlpha(root._actionAccent(root.action), 0.9)
                Behavior on x { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }
                Behavior on color { ColorAnimation { duration: Theme.motion.base } }
                SequentialAnimation on opacity {
                    running: capsule.visible
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.55; duration: 900; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 0.55; to: 1.0; duration: 900; easing.type: Easing.InOutSine }
                }
            }

            Row {
                spacing: root._gap
                Repeater {
                    model: root._subs
                    delegate: Item {
                        required property int index
                        required property var modelData
                        width: root._slotW
                        height: root._slotH
                        readonly property bool isActive: index === root._activeSub
                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent.isActive ? Theme.color.text : Theme.color.textMuted
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.micro
                            font.weight: parent.isActive ? Theme.weight.semibold : Theme.weight.regular
                            renderType: Text.NativeRendering
                        }
                    }
                }
            }
        }
    }
}
