import QtQuick
import qt_observer

// P2-D §7.4 — the page's vertical spine: a full-height round-phase timeline
// scrubber between the docked sandbox (left) and the scrolling report (right).
// PURE Observer of the cursor: `activeIndex` is bound from SettlementView's single
// writable cursorIndex; a node tap emits `nodeClicked(index)` for the parent to
// handle (it NEVER writes the cursor itself — no feedback paths originate here).
Item {
    id: root
    objectName: "settlementSpine"

    property var nodes: []          // bundle.board_timeline (round-phase nodes)
    property int activeIndex: 0     // bound to SettlementView.cursorIndex (read-only here)
    signal nodeClicked(int index)

    readonly property int _count: nodes ? nodes.length : 0
    // Even vertical distribution of node centers along the spine track.
    function _nodeY(i) {
        if (_count <= 1)
            return height / 2
        var pad = Theme.space.xl
        return pad + (height - pad * 2) * (i / (_count - 1))
    }

    // The spine track (thin vertical rail behind the nodes).
    Rectangle {
        id: track
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: Theme.space.xl
        anchors.bottomMargin: Theme.space.xl
        width: 2
        radius: 1
        color: Theme.withAlpha(Theme.color.border, 0.7)
    }

    // Round-phase nodes (dots + labels).
    Repeater {
        model: root.nodes
        delegate: Item {
            id: node
            width: root.width
            height: 1
            y: root._nodeY(index)

            readonly property bool isActive: index === root.activeIndex

            // Node dot on the track.
            Rectangle {
                id: dot
                anchors.horizontalCenter: track.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                width: node.isActive ? 12 : 8
                height: width
                radius: width / 2
                color: node.isActive ? Theme.color.completed : Theme.color.surfaceAlt
                border.width: 1
                border.color: node.isActive ? Theme.color.completed : Theme.color.border
                Behavior on width { NumberAnimation { duration: Theme.motion.fast } }
            }

            // Round-phase label (to the right of the rail).
            Text {
                anchors.left: track.right
                anchors.leftMargin: Theme.space.sm
                anchors.verticalCenter: parent.verticalCenter
                text: (modelData && modelData.label) ? modelData.label : ""
                color: node.isActive ? Theme.color.text : Theme.color.textMuted
                font.family: Theme.font.family
                font.pixelSize: Theme.size.micro
                font.weight: node.isActive ? Theme.weight.semibold : Theme.weight.regular
                elide: Text.ElideRight
                width: Math.max(0, root.width - dot.width - Theme.space.md)
            }

            TapHandler {
                onTapped: root.nodeClicked(index)
            }
            HoverHandler {
                cursorShape: Qt.PointingHandCursor
            }
        }
    }

    // Sliding cursor indicator — a glow ring that animates to the active node (D6).
    GlowDot {
        id: cursorMark
        x: track.x + track.width / 2 - diameter / 2
        y: root._nodeY(root.activeIndex) - diameter / 2
        diameter: 18
        pulse: true
        color: Theme.color.completed
        visible: root._count > 0
        Behavior on y { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.InOutCubic } }
    }
}
