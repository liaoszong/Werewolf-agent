import QtQuick
import qt_observer

// Branded button built from scratch (no native style dependency).
// variant: "primary" | "secondary" | "ghost" | "danger"
// Set `width` explicitly to make it fill / fixed; otherwise it hugs its label.
Item {
    id: root

    property string text: ""
    property string variant: "primary"
    signal clicked

    implicitHeight: 40
    implicitWidth: Math.max(104, label.implicitWidth + Theme.space.xxl * 2)
    opacity: enabled ? 1.0 : 0.45

    readonly property color _bg: {
        if (variant === "primary") return Theme.color.primary;
        if (variant === "danger") return Theme.color.danger;
        if (variant === "secondary") return Theme.color.surfaceAlt;
        return "transparent";
    }
    readonly property color _bgHover: {
        if (variant === "primary") return Theme.color.primaryHover;
        if (variant === "danger") return Qt.lighter(Theme.color.danger, 1.12);
        if (variant === "secondary") return Qt.lighter(Theme.color.surfaceAlt, 1.18);
        return Theme.withAlpha(Theme.color.text, 0.06);
    }
    readonly property color _fg: {
        if (variant === "primary") return Theme.color.primaryText;
        if (variant === "danger") return "#FFFFFF";
        if (variant === "secondary") return Theme.color.text;
        return Theme.color.textSecondary;
    }
    readonly property bool _outlined: variant === "ghost" || variant === "secondary"

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: Theme.radius.sm
        color: hover.hovered ? root._bgHover : root._bg
        border.width: root._outlined ? 1 : 0
        border.color: hover.hovered ? Theme.color.borderStrong : Theme.color.border
        scale: tap.pressed ? 0.97 : 1.0

        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        Behavior on scale { NumberAnimation { duration: Theme.motion.fast; easing.type: Easing.OutCubic } }

        Text {
            id: label
            anchors.centerIn: parent
            text: root.text
            color: root._fg
            font.family: Theme.font.family
            font.pixelSize: Theme.size.body
            font.weight: Theme.weight.semibold
        }
    }

    HoverHandler {
        id: hover
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        id: tap
        enabled: root.enabled
        onTapped: root.clicked()
    }

    Accessible.role: Accessible.Button
    Accessible.name: root.text
    Accessible.onPressAction: root.clicked()
}
