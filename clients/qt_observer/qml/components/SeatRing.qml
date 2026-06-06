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

    // Hover-replay overlay (set by the waterfall when a history row is hovered): re-arms a
    // past actor->target line on the ring even though it is no longer the current event.
    property string hoverActor: ""
    property string hoverTarget: ""
    property string hoverType: ""

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
        property string hActor: root.hoverActor
        property string hTarget: root.hoverTarget
        onEvChanged: requestPaint()
        onHActorChanged: requestPaint()
        onHTargetChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        function _lineColor(t) {
            return t === "werewolf_kill" ? Theme.color.werewolf
                 : t === "seer_check" ? Theme.color.seer
                 : t === "player_vote" ? Theme.color.textSecondary
                 : Theme.color.textMuted
        }
        // Draw one actor->target arrow at the given alpha. ai/ti must already resolve to seats.
        function _arrow(ctx, t, ai, ti, alpha) {
            if (ai < 0 || ti < 0)        // P1-B: no resolvable target (e.g. live) -> no line
                return
            var color = _lineColor(t)
            ctx.strokeStyle = color
            ctx.globalAlpha = alpha
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.moveTo(root.seatX(ai), root.seatY(ai))
            ctx.lineTo(root.seatX(ti), root.seatY(ti))
            ctx.stroke()
            var a = Math.atan2(root.seatY(ti) - root.seatY(ai), root.seatX(ti) - root.seatX(ai))
            var hx = root.seatX(ti) - Math.cos(a) * (root.seatSize / 2 + 6)
            var hy = root.seatY(ti) - Math.sin(a) * (root.seatSize / 2 + 6)
            ctx.globalAlpha = Math.min(1, alpha + 0.15)
            ctx.beginPath()
            ctx.moveTo(hx, hy)
            ctx.lineTo(hx - Math.cos(a - 0.4) * 10, hy - Math.sin(a - 0.4) * 10)
            ctx.lineTo(hx - Math.cos(a + 0.4) * 10, hy - Math.sin(a + 0.4) * 10)
            ctx.closePath()
            ctx.fillStyle = color
            ctx.fill()
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (width <= 0 || height <= 0 || root.players.length === 0)
                return
            // Live line for the current event (directional only when target resolves).
            var ev = root.current
            if (ev) {
                var t = ev.type || ""
                if (t === "werewolf_kill" || t === "seer_check" || t === "player_vote")
                    _arrow(ctx, t, root._indexOf(ev.actor), root._indexOf(ev.target), 0.75)
            }
            // Hover-replay line from the waterfall (brighter, drawn on top).
            if (root.hoverActor !== "" && root.hoverTarget !== "")
                _arrow(ctx, root.hoverType,
                       root._indexOf(root.hoverActor), root._indexOf(root.hoverTarget), 0.95)
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

            // Dead seats recede: smaller (退场 depth) + dimmed + desaturated (gray, faction color dropped).
            scale: isDead ? 0.82 : 1.0
            Behavior on scale { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutCubic } }

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
                color: seat.isDead ? Theme.color.surfaceInset
                     : (seat.isUnknown ? Theme.color.surfaceInset : Theme.roleTint(modelData.display_role))
                border.width: seat.isActive && !seat.isDead ? 2 : 1
                border.color: seat.isDead ? Theme.color.borderStrong : seat.accent
                opacity: seat.isDead ? 0.5 : 1.0
                Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }

                Text {
                    anchors.centerIn: parent
                    text: modelData.player_id
                    color: seat.isDead ? Theme.color.textMuted : Theme.color.text
                    font.family: Theme.font.display
                    font.pixelSize: Theme.size.h2
                    font.weight: Theme.weight.bold
                }

                // Dead strike-through (dark red, bold).
                Rectangle {
                    visible: seat.isDead
                    anchors.centerIn: parent
                    width: parent.width * 1.15
                    height: 3
                    radius: 1.5
                    rotation: -45
                    color: Theme.color.danger
                    opacity: 0.9
                }
            }

            // 出局 / OUT badge — crisp (full opacity even though the avatar is dimmed).
            Rectangle {
                visible: seat.isDead
                anchors.horizontalCenter: avatar.horizontalCenter
                anchors.verticalCenter: avatar.bottom
                width: outText.implicitWidth + Theme.space.sm
                height: outText.implicitHeight + 3
                radius: Theme.radius.sm
                color: Theme.withAlpha(Theme.color.danger, 0.92)
                Text {
                    id: outText
                    anchors.centerIn: parent
                    text: I18n.t("出局", "OUT")
                    color: Theme.color.text
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro
                    font.weight: Theme.weight.bold
                }
            }

            Text {
                anchors.top: avatar.bottom
                anchors.topMargin: seat.isDead ? 13 : 4
                anchors.horizontalCenter: avatar.horizontalCenter
                text: seat.isUnknown ? "████" : root._roleLabel(modelData.display_role)
                color: seat.isDead ? Theme.color.textMuted
                     : (seat.isUnknown ? Theme.color.textMuted : seat.accent)
                font.family: seat.isUnknown ? Theme.font.mono : Theme.font.family
                font.pixelSize: Theme.size.micro
            }
        }
    }
}
