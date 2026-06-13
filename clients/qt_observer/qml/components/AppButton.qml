import QtQuick
import qt_observer

// Branded button built from scratch (no native style dependency).
// variant: "primary" | "secondary" | "ghost" | "danger"
// onLight: false (default) -> dark theme path (existing pages, unchanged).
//          true            -> warm "Claude" path (cream surfaces).
// Set `width` explicitly to make it fill / fixed; otherwise it hugs its label.
Item {
    id: root

    property string text: ""
    property string variant: "primary"
    property bool onLight: false
    signal clicked

    implicitHeight: 40
    implicitWidth: Math.max(104, label.implicitWidth + Theme.space.xxl * 2)
    opacity: enabled ? 1.0 : 0.45

    readonly property color _bg: {
        if (onLight) {
            if (variant === "primary") return Theme.warm.primary;
            if (variant === "danger")  return Theme.warm.error;
            if (variant === "secondary") return Theme.warm.surfaceRaised;
            return "transparent";  // ghost
        }
        if (variant === "primary") return Theme.color.primary;
        if (variant === "danger") return Theme.color.danger;
        if (variant === "secondary") return Theme.color.surfaceAlt;
        return "transparent";
    }
    readonly property color _bgHover: {
        if (onLight) {
            if (variant === "primary") return Theme.warm.primaryActive;
            if (variant === "danger")  return Qt.darker(Theme.warm.error, 1.1);
            if (variant === "secondary") return Theme.warm.surfaceSoft;
            return Theme.withAlpha(Theme.warm.ink, 0.05);
        }
        if (variant === "primary") return Theme.color.primaryHover;
        if (variant === "danger") return Qt.lighter(Theme.color.danger, 1.12);
        if (variant === "secondary") return Qt.lighter(Theme.color.surfaceAlt, 1.18);
        return Theme.withAlpha(Theme.color.text, 0.06);
    }
    readonly property color _fg: {
        if (onLight) {
            if (variant === "primary" || variant === "danger") return Theme.warm.onPrimary;
            if (variant === "secondary") return Theme.warm.ink;
            return Theme.warm.body;  // ghost
        }
        if (variant === "primary") return Theme.color.primaryText;
        if (variant === "danger") return "#FFFFFF";
        if (variant === "secondary") return Theme.color.text;
        return Theme.color.textSecondary;
    }
    readonly property bool _outlined: variant === "ghost" || variant === "secondary"
    readonly property color _border: onLight ? Theme.warm.hairline : Theme.color.border
    readonly property color _borderHover: onLight ? Theme.warm.mutedSoft : Theme.color.borderStrong

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: Theme.radius.md
        color: hover.hovered ? root._bgHover : root._bg
        border.width: root._outlined ? 1 : 0
        border.color: hover.hovered ? root._borderHover : root._border
        scale: tap.pressed ? Theme.anim.pressScale : 1.0

        Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutQuad } }

        Text {
            id: label
            anchors.centerIn: parent
            text: root.text
            color: root._fg
            font.family: root.onLight ? Theme.fontFamilies.sans : Theme.font.family
            font.contextFontMerging: root.onLight
            font.pixelSize: root.onLight ? Theme.warmSize.bodyLg : Theme.size.body
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
