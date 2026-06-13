import QtQuick
import QtQuick.Controls
import qt_observer

// Quiet left navigation rail (game client). v1: selected / disabled / collapsed /
// tooltip only — no hover flourishes or icon animation. Now with a brand badge
// at the top and an observer-profile footer (mirrors the reference layout).
Item {
    id: root
    objectName: "navRail"

    // items: [{ key, label, glyph, enabled }]
    property var items: []
    property string currentKey: "home"
    property bool collapsed: width < 96
    // observer profile (footer)
    property string observerName: "观察者"
    property int observerLevel: 12
    property real observerProgress: 0.64
    signal activated(string key)

    implicitWidth: 220

    Rectangle {
        anchors.fill: parent
        color: Theme.warm.surfaceCard
        Rectangle {                       // right hairline seam
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.warm.hairline
        }
    }

    // ------------------------------------------------------------- Brand badge
    Row {
        id: brand
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.xl
        anchors.leftMargin: Theme.space.lg
        anchors.rightMargin: Theme.space.lg
        spacing: Theme.space.md

        Rectangle {
            width: 34; height: 34; radius: 17
            anchors.verticalCenter: parent.verticalCenter
            color: Theme.warm.surfaceDark
            border.width: 1
            border.color: Theme.withAlpha(Theme.warm.primary, 0.5)
            Text {
                anchors.centerIn: parent
                text: "🐺"
                font.pixelSize: 17
            }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            visible: !root.collapsed
            spacing: 1
            Text {
                text: "狼人杀 · 观察席"
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.serif
                font.contextFontMerging: true
                font.pixelSize: Theme.size.small
                font.weight: Theme.weight.semibold
            }
            Text {
                text: "WEREWOLF OBSERVER"
                color: Theme.warm.mutedSoft
                font.family: Theme.fontFamilies.sans
                font.contextFontMerging: true
                font.pixelSize: 9
                font.letterSpacing: 1
            }
        }
    }

    // ------------------------------------------------------------------- Items
    Column {
        id: list
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: brand.bottom
        anchors.topMargin: Theme.space.xxl
        spacing: Theme.space.xs

        Repeater {
            model: root.items
            delegate: Item {
                id: rowItem
                required property var modelData
                width: list.width
                height: 46
                enabled: modelData.enabled === undefined ? true : modelData.enabled
                opacity: enabled ? 1.0 : 0.4

                readonly property bool _selected: root.currentKey === modelData.key

                Rectangle {
                    id: pill
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space.sm
                    anchors.rightMargin: Theme.space.sm
                    radius: Theme.radius.md
                    color: rowItem._selected ? Theme.warm.primary
                           : (hov.hovered && rowItem.enabled ? Theme.withAlpha(Theme.warm.ink, 0.04) : "transparent")
                    Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }

                    // Diamond end-accents (selected only).
                    Rectangle {
                        visible: rowItem._selected
                        width: 5; height: 5; radius: 1; rotation: 45
                        color: Theme.withAlpha(Theme.warm.textOnPrimary, 0.7)
                        anchors.left: parent.left; anchors.leftMargin: 7
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        visible: rowItem._selected
                        width: 5; height: 5; radius: 1; rotation: 45
                        color: Theme.withAlpha(Theme.warm.textOnPrimary, 0.7)
                        anchors.right: parent.right; anchors.rightMargin: 7
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.space.md
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Theme.space.md

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: rowItem.modelData.glyph || "•"
                            color: rowItem._selected ? Theme.warm.textOnPrimary : Theme.warm.muted
                            font.pixelSize: 17
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: !root.collapsed
                            text: rowItem.modelData.label || ""
                            color: rowItem._selected ? Theme.warm.textOnPrimary : Theme.warm.body
                            font.family: Theme.fontFamilies.sans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.warmSize.bodyLg
                            font.weight: rowItem._selected ? Theme.weight.semibold : Theme.weight.medium
                        }
                    }
                }

                HoverHandler {
                    id: hov
                    enabled: rowItem.enabled
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    enabled: rowItem.enabled
                    onTapped: root.activated(rowItem.modelData.key)
                }

                ToolTip.visible: root.collapsed && hov.hovered
                ToolTip.text: rowItem.modelData.label || ""
                ToolTip.delay: 300
            }
        }
    }

    // ----------------------------------------------------------------- Footer
    Item {
        id: footer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.space.lg
        height: 48

        Rectangle {                       // hairline divider above the footer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: -Theme.space.md
            height: 1
            color: Theme.warm.hairline
        }

        Row {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            spacing: Theme.space.md

            Rectangle {
                width: 36; height: 36; radius: 18
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.warm.surfaceCreamStrong
                border.width: 1
                border.color: Theme.warm.hairline
                Text { anchors.centerIn: parent; text: "🦉"; font.pixelSize: 17 }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                visible: !root.collapsed
                spacing: 3
                Text {
                    text: root.observerName + " · Lv." + root.observerLevel
                    color: Theme.warm.body
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    font.weight: Theme.weight.medium
                }
                Rectangle {                 // level progress track
                    width: 120; height: 4; radius: 2
                    color: Theme.withAlpha(Theme.warm.ink, 0.08)
                    Rectangle {
                        width: parent.width * Math.max(0, Math.min(1, root.observerProgress))
                        height: parent.height; radius: 2
                        color: Theme.warm.primary
                    }
                }
            }
        }
    }
}
