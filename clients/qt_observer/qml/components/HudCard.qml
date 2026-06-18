import QtQuick
import qt_observer

// Material-system parchment card — the shared "paper" surface for the right info
// tower (and any HUD card). Not a flat block: a faint top-lit gradient fill + a
// tiled paper-grain texture overlay + an engraved double rule (soft gold outer +
// inner gold hairline) + a warm layered shadow that lifts it off the table.
// Sizes to its content: put a top/left/right-anchored child (usually a Column).
Item {
    id: root

    property color fill: Theme.parchment.parchment
    property color line: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.9)
    property real frameRadius: Theme.radius.lg
    property real pad: Theme.space.lg
    property bool emphasized: false
    property bool tactile: true                 // paper-grain overlay
    readonly property color _fillBase: emphasized ? Theme.parchment.parchmentStrong : fill

    default property alias content: holder.data

    implicitWidth: 240
    implicitHeight: 2 * pad + holder.childrenRect.height

    // ---- warm layered shadow (low-alpha rects -> visible in screenshots) ----
    Rectangle {
        anchors.fill: frame; anchors.topMargin: 6; anchors.bottomMargin: -6
        radius: frame.radius; color: Theme.parchment.woodShadowSoft; z: -2
    }
    Rectangle {
        anchors.fill: frame; anchors.topMargin: 2; anchors.bottomMargin: -2
        radius: frame.radius; color: Theme.parchment.woodShadow; z: -1
    }

    Rectangle {
        id: frame
        anchors.fill: parent
        radius: root.frameRadius
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(root._fillBase, 1.04) }
            GradientStop { position: 1.0; color: Qt.darker(root._fillBase, 1.03) }
        }
        border.width: 1
        border.color: root.line
        clip: true

        // paper grain (already low-alpha in the asset)
        Image {
            anchors.fill: parent
            source: root.tactile ? Illustrations.texParchment : ""
            fillMode: Image.Tile
            visible: root.tactile
        }
        // top inner sheen (very faint) — paper catching light
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: parent.height * 0.4
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.withAlpha(Theme.warm.textOnPrimary, 0.10) }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }
        // engraved inner gold rule
        Rectangle {
            anchors.fill: parent; anchors.margins: 3
            radius: Math.max(0, parent.radius - 2)
            color: "transparent"
            border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.4)
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
