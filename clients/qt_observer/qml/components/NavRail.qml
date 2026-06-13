import QtQuick
import QtQuick.Controls
import qt_observer

// Quiet left navigation rail (game client). v1 does FOUR things only: selected
// state, disabled state, narrow/collapsed state, tooltip label. No hover
// flourishes, no icon animation. It is an entry, not a decorative strip.
Item {
    id: root
    objectName: "navRail"

    // items: [{ key, label, glyph, enabled }]
    property var items: []
    property string currentKey: "home"
    property bool collapsed: width < 96
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

    Column {
        id: list
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Theme.space.xl
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
                    color: rowItem._selected ? Theme.warm.surfaceCreamStrong : "transparent"

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.space.md
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Theme.space.md

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: rowItem.modelData.glyph || "•"
                            color: rowItem._selected ? Theme.warm.primary : Theme.warm.muted
                            font.pixelSize: 18
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: !root.collapsed
                            text: rowItem.modelData.label || ""
                            color: rowItem._selected ? Theme.warm.ink : Theme.warm.body
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

                // Tooltip label when collapsed — attached property only, no hover
                // animation (the single v1 "extra").
                ToolTip.visible: root.collapsed && hov.hovered
                ToolTip.text: rowItem.modelData.label || ""
                ToolTip.delay: 300
            }
        }
    }
}
