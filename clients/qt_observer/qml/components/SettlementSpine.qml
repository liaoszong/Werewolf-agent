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
    // The rail sits near the RIGHT of the column; labels fill the left of it. ONE
    // shared x for the rail/dots/glow so they all line up (the dots used to be
    // mis-anchored cross-hierarchy and fell to x=0, overlapping the labels).
    readonly property real railCenterX: width - Theme.space.lg
    // Even vertical distribution of node centers along the spine track.
    function _nodeY(i) {
        if (_count <= 1)
            return height / 2
        var pad = Theme.space.xl
        return pad + (height - pad * 2) * (i / (_count - 1))
    }

    // The spine track — a soft-but-present dark hairline that anchors the eye as the
    // page's central axis. On the warm-beige canvas it reads as a thin warm-gray rail.
    Rectangle {
        id: track
        x: root.railCenterX - width / 2
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: Theme.space.xl
        anchors.bottomMargin: Theme.space.xl
        width: 2
        radius: 1
        color: Theme.withAlpha(Theme.report.text, 0.22)
    }

    // Round-phase nodes (dots + labels). Labels fill the column LEFT of the rail
    // (breathing space from the report); the dot sits ON the rail. Both positioned
    // by root.railCenterX (no cross-hierarchy anchors) so they never collide.
    Repeater {
        model: root.nodes
        delegate: Item {
            id: node
            width: root.width
            height: 1
            y: root._nodeY(index)

            readonly property bool isActive: index === root.activeIndex

            // Round-phase label — left of the rail, right-aligned, ending before the dot.
            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: root.railCenterX - Theme.space.md * 2
                text: (modelData && modelData.label) ? modelData.label : ""
                color: node.isActive ? Theme.report.accent : Theme.report.textMuted
                font.family: Theme.font.family
                font.pixelSize: Theme.size.caption
                font.weight: node.isActive ? Theme.weight.semibold : Theme.weight.regular
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideLeft
            }

            // Node dot — ON the rail.
            Rectangle {
                id: dot
                x: root.railCenterX - width / 2
                anchors.verticalCenter: parent.verticalCenter
                width: node.isActive ? 11 : 7
                height: width
                radius: width / 2
                color: node.isActive ? Theme.report.accent : Theme.report.card
                border.width: node.isActive ? 0 : 1.5
                border.color: Theme.withAlpha(Theme.report.text, 0.35)
                Behavior on width { NumberAnimation { duration: Theme.motion.fast } }
            }

            TapHandler {
                onTapped: root.nodeClicked(index)
            }
            HoverHandler {
                cursorShape: Qt.PointingHandCursor
            }
        }
    }

    // Sliding cursor indicator — a coral glow ring that breathes on the active node
    // and animates between nodes (D6). Centered ON the rail, haloing the active dot.
    GlowDot {
        id: cursorMark
        x: root.railCenterX - diameter / 2
        y: root._nodeY(root.activeIndex) - diameter / 2
        diameter: 20
        pulse: true
        color: Theme.report.accentGlow
        visible: root._count > 0
        Behavior on y { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.InOutCubic } }
    }
}
