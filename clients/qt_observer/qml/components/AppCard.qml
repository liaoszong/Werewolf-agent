import QtQuick
import QtQuick.Effects
import qt_observer

// Surface container. Dark (default): bordered + top hairline (existing pages).
// onLight: warm raised card — cream surface, very faint hairline, soft diffuse
// shadow. Depth comes from the shadow + surface, not a heavy border.
Rectangle {
    id: root

    property bool interactive: false
    property bool onLight: false
    readonly property bool hovered: hoverHandler.hovered

    radius: Theme.radius.lg
    color: onLight
           ? ((hovered && interactive) ? Theme.warm.surfaceSoft : Theme.warm.surfaceRaised)
           : ((hovered && interactive) ? Theme.color.surfaceAlt : Theme.color.surface)
    border.width: 1
    // onLight: very faint ink hairline (alpha 0.08) — depth comes from the soft
    // shadow + surface, not a heavy border.
    border.color: onLight
                  ? Theme.withAlpha(Theme.warm.ink, 0.08)
                  : ((hovered && interactive) ? Theme.color.borderStrong : Theme.color.border)

    Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
    Behavior on border.color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }

    // Soft warm elevation (onLight only).
    layer.enabled: root.onLight
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: Theme.elevation.shadowColor
        shadowBlur: Theme.elevation.blur
        shadowVerticalOffset: Theme.elevation.verticalOffset
        shadowHorizontalOffset: 0
    }

    // Top hairline highlight — dark theme only (warm uses the soft shadow).
    Rectangle {
        visible: !root.onLight
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
