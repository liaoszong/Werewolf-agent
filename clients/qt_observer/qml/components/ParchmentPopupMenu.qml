import QtQuick
import QtQuick.Controls
import qt_observer

Popup {
    id: root

    property var actions: []
    property int itemHeight: 46
    property int edgeMargin: 22
    signal triggered(string key)

    width: 198
    padding: 7
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
    parent: Overlay.overlay

    function popup(anchorItem, dx, dy) {
        if (visible) {
            close()
            return
        }

        var overlay = Overlay.overlay
        var p = anchorItem.mapToItem(overlay, dx || 0, dy || 0)
        var targetX = p.x + anchorItem.width - width
        var maxX = overlay ? overlay.width - width - edgeMargin : targetX
        x = Math.max(edgeMargin, Math.min(targetX, maxX))
        y = p.y + 7
        open()
    }

    background: Item {
        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 8
            anchors.leftMargin: 3
            anchors.rightMargin: -3
            anchors.bottomMargin: -6
            radius: 16
            color: Theme.withAlpha(Theme.parchment.woodShadow, 0.64)
        }

        Rectangle {
            anchors.fill: parent
            radius: 16
            color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.98)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.54)

            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: Illustrations.texParchment
                fillMode: Image.Tile
                opacity: 0.18
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: 15
                color: "transparent"
                border.width: 1
                border.color: Theme.withAlpha(Theme.parchment.highlightLine, 0.40)
            }
        }
    }

    contentItem: Column {
        id: menuColumn
        spacing: 4

        Repeater {
            model: root.actions

            delegate: ItemDelegate {
                id: menuItem
                width: root.availableWidth
                height: root.itemHeight
                hoverEnabled: true
                objectName: modelData.objectName || ""

                contentItem: Text {
                    text: modelData.text || ""
                    color: menuItem.hovered ? Theme.warm.primaryActive : Theme.parchment.ink
                    font.family: Theme.fontFamilies.cjkSans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    font.weight: Theme.weight.semibold
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 12
                    elide: Text.ElideRight
                }

                background: Rectangle {
                    radius: 11
                    color: menuItem.hovered
                           ? Theme.withAlpha(Theme.parchment.terracottaWash, 0.58)
                           : "transparent"
                    border.width: menuItem.hovered ? 1 : 0
                    border.color: Theme.withAlpha(Theme.warm.primary, 0.20)
                }

                onClicked: {
                    root.close()
                    root.triggered(modelData.key || "")
                }
            }
        }
    }
}
