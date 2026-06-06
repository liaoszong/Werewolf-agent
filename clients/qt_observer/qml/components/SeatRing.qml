import QtQuick
import qt_observer

// P2-C-1 breathing player ring. Six seats on a circle; faction accents; alive/dead;
// active-seat spotlight driven by the queue's PresentationEvent (current.actor). A Canvas
// connector layer draws actor->target lines ONLY when current.target resolves to a seat
// (P1-B: live has no target -> spotlight only, no directional line). Non-god perspectives
// fog unknown identities (████). Reads PresentationEvent fields only (current.type/actor/target).
Item {
    id: root
    objectName: "seatRing"

    property var players: []            // ObserverClient.playerItems
    property var current: ({})          // eventQueue.current (PresentationEvent)
    property string layoutPhase: "day"
    property string perspective: "god"

    property real seatSize: 58
    readonly property real ringRadius: Math.max(40, Math.min(width, height) * 0.36)

    function _angle(i) { return (-90 + i * 60) * Math.PI / 180 }
    function seatX(i) { return width / 2 + ringRadius * Math.cos(_angle(i)) }
    function seatY(i) { return height / 2 + ringRadius * Math.sin(_angle(i)) }
    function _indexOf(pid) {
        for (var i = 0; i < players.length; i++)
            if (players[i] && players[i].player_id === pid)
                return i
        return -1
    }
    function _roleLabel(role) {
        var m = ({
            werewolf: I18n.t("狼人", "Werewolf"),
            seer: I18n.t("预言家", "Seer"),
            witch: I18n.t("女巫", "Witch"),
            villager: I18n.t("村民", "Villager"),
            unknown: I18n.t("未知", "Unknown")
        })
        return m[role] || role
    }

    // Faint stage ring guide.
    Rectangle {
        anchors.centerIn: parent
        width: root.ringRadius * 2
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 1
        border.color: Theme.withAlpha(Theme.color.border, 0.5)
    }

    // Connector layer (actor -> target). Repaints when the current event or size changes.
    Canvas {
        id: connectors
        anchors.fill: parent
        property var ev: root.current
        onEvChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var ev = root.current
            if (!ev)
                return
            var t = ev.type || ""
            if (t !== "werewolf_kill" && t !== "seer_check" && t !== "player_vote")
                return
            var ai = root._indexOf(ev.actor)
            var ti = root._indexOf(ev.target)
            if (ai < 0 || ti < 0)        // P1-B: no resolvable target (e.g. live) -> no line
                return
            var color = t === "werewolf_kill" ? Theme.color.werewolf
                      : t === "seer_check" ? Theme.color.seer
                      : Theme.color.textMuted
            ctx.strokeStyle = color
            ctx.globalAlpha = 0.75
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.moveTo(root.seatX(ai), root.seatY(ai))
            ctx.lineTo(root.seatX(ti), root.seatY(ti))
            ctx.stroke()
            // arrowhead at target
            var a = Math.atan2(root.seatY(ti) - root.seatY(ai), root.seatX(ti) - root.seatX(ai))
            var hx = root.seatX(ti) - Math.cos(a) * (root.seatSize / 2 + 6)
            var hy = root.seatY(ti) - Math.sin(a) * (root.seatSize / 2 + 6)
            ctx.globalAlpha = 0.9
            ctx.beginPath()
            ctx.moveTo(hx, hy)
            ctx.lineTo(hx - Math.cos(a - 0.4) * 10, hy - Math.sin(a - 0.4) * 10)
            ctx.lineTo(hx - Math.cos(a + 0.4) * 10, hy - Math.sin(a + 0.4) * 10)
            ctx.closePath()
            ctx.fillStyle = color
            ctx.fill()
        }
    }

    Repeater {
        model: root.players
        delegate: Item {
            id: seat
            width: root.seatSize
            height: root.seatSize + 22
            x: root.seatX(index) - width / 2
            y: root.seatY(index) - root.seatSize / 2

            property bool isUnknown: !modelData.display_role || modelData.display_role === "unknown"
            property bool isDead: modelData.alive === false
            property bool isActive: root.current && root.current.actor === modelData.player_id
            property color accent: isUnknown ? Theme.color.border : Theme.roleAccent(modelData.display_role)

            GlowDot {
                anchors.horizontalCenter: avatar.horizontalCenter
                anchors.verticalCenter: avatar.verticalCenter
                visible: seat.isActive && !seat.isDead
                pulse: visible
                diameter: root.seatSize + 8
                color: seat.accent
            }

            Rectangle {
                id: avatar
                width: root.seatSize
                height: root.seatSize
                radius: width / 2
                color: seat.isUnknown ? Theme.color.surfaceInset : Theme.roleTint(modelData.display_role)
                border.width: seat.isActive ? 2 : 1
                border.color: seat.accent
                opacity: seat.isDead ? 0.4 : 1.0

                Text {
                    anchors.centerIn: parent
                    text: modelData.player_id
                    color: Theme.color.text
                    font.family: Theme.font.display
                    font.pixelSize: Theme.size.h2
                    font.weight: Theme.weight.bold
                }

                // Dead strike-through.
                Rectangle {
                    visible: seat.isDead
                    anchors.centerIn: parent
                    width: parent.width * 1.1
                    height: 2
                    rotation: -45
                    color: Theme.color.textMuted
                }
            }

            Text {
                anchors.top: avatar.bottom
                anchors.topMargin: 4
                anchors.horizontalCenter: avatar.horizontalCenter
                text: seat.isUnknown ? "████" : root._roleLabel(modelData.display_role)
                color: seat.isUnknown ? Theme.color.textMuted : seat.accent
                font.family: seat.isUnknown ? Theme.font.mono : Theme.font.family
                font.pixelSize: Theme.size.micro
            }
        }
    }
}
