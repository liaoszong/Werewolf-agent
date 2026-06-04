import QtQuick
import qt_observer

// Surface container: rounded, bordered, with a faint top hairline for depth.
// Set `interactive: true` to get a hover state (border + surface brighten).
// Place child content directly inside; lay it out with anchors/Column/etc.
Rectangle {
    id: root

    property bool interactive: false
    readonly property bool hovered: hoverHandler.hovered

    radius: Theme.radius.lg
    color: (hovered && interactive) ? Theme.color.surfaceAlt : Theme.color.surface
    border.width: 1
    border.color: (hovered && interactive) ? Theme.color.borderStrong : Theme.color.border

    Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
    Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }

    // Top hairline highlight
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 1
        height: 1
        color: Theme.color.hairline
    }

    HoverHandler {
        id: hoverHandler
        enabled: root.interactive
    }
}
