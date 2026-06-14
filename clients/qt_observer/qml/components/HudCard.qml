import QtQuick
import qt_observer

// Parchment HUD card — the engraved double-line frame shared by every right-side
// HUD module (phase card, current votes, live status). Pure presentation:
//   parchment fill + ink/gold outer line + inset gold hairline = "engraved" look.
// Sizes to its content: put a top/left/right-anchored child (usually a Column);
// implicitHeight derives from that child's bounding box plus padding.
Item {
    id: root

    property color fill: Theme.parchment.parchment
    property color line: Theme.parchment.goldLineSoft
    property real frameRadius: Theme.radius.lg
    property real pad: Theme.space.lg
    // When true the card uses the darker elevated parchment (selected / emphasis).
    property bool emphasized: false

    default property alias content: holder.data

    implicitWidth: 240
    implicitHeight: 2 * pad + holder.childrenRect.height

    // Soft drop to lift the card off the wooden table (very low alpha, warm).
    Rectangle {
        anchors.fill: frame
        anchors.topMargin: 2
        radius: frame.radius
        color: Qt.rgba(0, 0, 0, 0.14)
        z: -1
    }

    Rectangle {
        id: frame
        anchors.fill: parent
        radius: root.frameRadius
        color: root.emphasized ? Theme.parchment.parchmentStrong : root.fill
        border.width: 1
        border.color: root.line

        // Inset gold hairline = the engraved inner rule.
        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: Math.max(0, parent.radius - 3)
            color: "transparent"
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.45)
        }
    }

    Item {
        id: holder
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: root.pad
    }
}
