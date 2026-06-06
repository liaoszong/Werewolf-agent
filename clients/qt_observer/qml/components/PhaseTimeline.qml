import QtQuick
import QtQuick.Effects
import qt_observer

// P2-C-1 top phase progress axis — a real data-cockpit rail (no text-character mock-ups).
// Upper tier: a solid track with a bright progress fill connecting geometric, glowing phase
// nodes (day/night), labels set below in spaced caps. Lower tier: a borderless pill that
// glides (Behavior on x) along a slot track to the acting role/step, tinted by faction color.
Item {
    id: root
    objectName: "phaseTimeline"

    property var phases: []          // queue.phaseTimeline — [{round, phase}]
    property string phase: "day"     // fallback only (see _curPhase)
    property string action: ""       // queue.currentAction (wolf|seer|witch|speech|vote)

    implicitHeight: 66

    // Current major phase from the cursor-based timeline (NOT layoutPhase, which the gate
    // pre-advances while the night event is still on stage).
    readonly property string _curPhase: phases.length > 0 ? phases[phases.length - 1].phase : phase

    // ----- node geometry -----
    readonly property int _nodePitch: 104
    readonly property int _nodeN: phases.length
    readonly property real _groupW: _nodeN > 1 ? (_nodeN - 1) * _nodePitch : 0
    function _nodeCX(i) { return (width - _groupW) / 2 + i * _nodePitch }

    // ----- sub-step (action) geometry -----
    readonly property int _slotW: 74
    readonly property int _slotH: 24
    readonly property int _gap: Theme.space.sm
    readonly property int _pitch: _slotW + _gap
    readonly property var _subs: _curPhase === "night"
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
    function _nodeAccent(ph) { return ph === "night" ? Theme.color.info : Theme.color.seer }

    // ============================ Upper tier: track + fill + nodes ============================
    Item {
        id: majorTier
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.sm
        height: 32
        readonly property real railY: 7   // node centre line

        // Solid base track (recessed groove).
        Rectangle {
            visible: root._nodeN > 1
            x: root._nodeCX(0)
            y: majorTier.railY - 1
            width: root._groupW
            height: 3
            radius: 1.5
            color: Theme.color.surfaceInset
        }
        // Bright progress fill — reaches the current (last) node; animates as the track grows.
        Rectangle {
            id: fill
            visible: root._nodeN > 1
            x: root._nodeCX(0)
            y: majorTier.railY - 1
            width: root._groupW
            height: 3
            radius: 1.5
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Theme.withAlpha(Theme.color.text, 0.35) }
                GradientStop { position: 1.0; color: Theme.color.text }
            }
            Behavior on width { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutCubic } }
        }

        Repeater {
            model: root.phases
            delegate: Item {
                id: nodeItem
                required property int index
                required property var modelData
                readonly property bool isCurrent: index === root._nodeN - 1
                readonly property color accent: root._nodeAccent(modelData.phase)
                width: 44
                height: majorTier.height
                x: root._nodeCX(index) - width / 2

                // Geometric node — glowing when current.
                Rectangle {
                    id: dot
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: majorTier.railY - height / 2
                    width: nodeItem.isCurrent ? 13 : 7
                    height: width
                    radius: width / 2
                    color: nodeItem.isCurrent ? nodeItem.accent : Theme.color.borderStrong
                    Behavior on width { NumberAnimation { duration: Theme.motion.base } }
                    layer.enabled: nodeItem.isCurrent
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: nodeItem.accent
                        shadowBlur: 1.0
                        shadowScale: 1.5
                        autoPaddingEnabled: true
                    }
                }
                // Label set below the node, spaced caps, de-emphasized.
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: majorTier.railY + 11
                    text: (nodeItem.modelData.phase === "night" ? I18n.t("夜", "N") : I18n.t("日", "D"))
                          + nodeItem.modelData.round
                    color: nodeItem.isCurrent ? Theme.color.textSecondary : Theme.color.textMuted
                    font.family: Theme.font.mono
                    font.pixelSize: Theme.size.micro
                    font.weight: nodeItem.isCurrent ? Theme.weight.semibold : Theme.weight.regular
                    font.letterSpacing: 2
                    renderType: Text.NativeRendering
                }
            }
        }
    }

    // ============================ Lower tier: gliding pill slider ============================
    Item {
        id: subTier
        anchors.top: majorTier.bottom
        anchors.topMargin: Theme.space.xs
        anchors.horizontalCenter: parent.horizontalCenter
        width: root._subs.length * root._slotW + (root._subs.length - 1) * root._gap
        height: root._slotH

        // Borderless filled capsule that glides to the active step (soft faction glow under it).
        Rectangle {
            id: capsule
            visible: root._activeSub >= 0
            width: root._slotW
            height: root._slotH
            radius: height / 2
            x: root._activeSub >= 0 ? root._activeSub * root._pitch : 0
            color: Theme.withAlpha(root._actionAccent(root.action), 0.24)
            Behavior on x { NumberAnimation { duration: 520; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: Theme.motion.base } }
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root._actionAccent(root.action)
                shadowBlur: 0.7
                shadowScale: 1.05
                autoPaddingEnabled: true
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
                    height: subTier.height
                    readonly property bool isActive: index === root._activeSub
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: parent.isActive ? Theme.color.text : Theme.color.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.micro
                        font.weight: parent.isActive ? Theme.weight.semibold : Theme.weight.regular
                        font.letterSpacing: 0.5
                        renderType: Text.NativeRendering
                    }
                }
            }
        }
    }
}
