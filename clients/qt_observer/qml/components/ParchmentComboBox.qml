import QtQuick
import QtQuick.Controls
import qt_observer

ComboBox {
    id: control

    property real controlRadius: 13
    property real surfaceOpacity: 0.72
    property real insetOpacity: 0.30
    property int popupMaxHeight: 282
    property bool compact: false

    hoverEnabled: true
    implicitHeight: compact ? 36 : 42
    leftPadding: compact ? 12 : 14
    rightPadding: compact ? 36 : 40

    function optionLabel(data) {
        if (control.textRole && data && data[control.textRole] !== undefined)
            return data[control.textRole]
        if (data === undefined || data === null)
            return ""
        return String(data)
    }

    background: Rectangle {
        radius: control.controlRadius
        color: {
            if (!control.enabled)
                return Theme.withAlpha(Theme.parchment.parchmentStrong, 0.34)
            if (control.pressed || control.popup.visible)
                return Theme.withAlpha(Theme.parchment.parchmentStrong, control.surfaceOpacity + 0.10)
            if (control.hovered)
                return Theme.withAlpha(Theme.parchment.parchmentSoft, control.surfaceOpacity + 0.08)
            return Theme.withAlpha(Theme.parchment.parchmentStrong, control.surfaceOpacity)
        }
        border.width: 1
        border.color: control.pressed || control.popup.visible
                      ? Theme.withAlpha(Theme.warm.primaryActive, 0.58)
                      : (control.hovered
                         ? Theme.withAlpha(Theme.parchment.goldLine, 0.52)
                         : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.42))

        Image {
            anchors.fill: parent
            anchors.margins: 1
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: control.enabled ? 0.12 : 0.07
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: control.controlRadius
            anchors.rightMargin: control.controlRadius
            height: 1
            color: Qt.rgba(1, 248 / 255, 234 / 255, control.enabled ? 0.45 : 0.20)
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: control.controlRadius
            anchors.rightMargin: control.controlRadius
            height: 1
            color: Theme.withAlpha(Theme.parchment.goldLineSoft, control.insetOpacity)
        }

        Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
    }

    indicator: Item {}

    contentItem: Item {
        Text {
            anchors.left: parent.left
            anchors.leftMargin: control.leftPadding
            anchors.right: chevronPlate.left
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            text: control.displayText
            color: control.enabled ? Theme.parchment.ink : Theme.parchment.mutedInk
            font: control.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }

        Rectangle {
            id: chevronPlate
            anchors.right: parent.right
            anchors.rightMargin: control.compact ? 9 : 11
            anchors.verticalCenter: parent.verticalCenter
            width: control.compact ? 18 : 20
            height: control.compact ? 18 : 20
            radius: 7
            color: control.enabled
                   ? Theme.withAlpha(Theme.parchment.goldLine, control.popup.visible ? 0.66 : 0.48)
                   : Theme.withAlpha(Theme.parchment.goldLine, 0.22)
            border.width: 1
            border.color: Qt.rgba(1, 246 / 255, 220 / 255, control.enabled ? 0.42 : 0.18)

            Text {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -1
                text: "▾"
                color: control.enabled ? Theme.parchment.ink : Theme.parchment.mutedInk
                font.family: Theme.fontFamilies.cjkSans
                font.contextFontMerging: true
                font.pixelSize: control.compact ? 12 : 13
                font.weight: Theme.weight.bold
            }
        }
    }

    delegate: ItemDelegate {
        id: option
        width: ListView.view ? ListView.view.width : control.width
        height: control.compact ? 38 : 42
        hoverEnabled: true
        highlighted: control.highlightedIndex === index

        contentItem: Text {
            text: control.optionLabel(modelData)
            color: option.highlighted || option.hovered
                   ? Theme.warm.primaryActive
                   : Theme.parchment.ink
            font: control.font
            verticalAlignment: Text.AlignVCenter
            leftPadding: 12
            rightPadding: 10
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 10
            color: option.highlighted
                   ? Theme.withAlpha(Theme.parchment.terracottaWash, 0.64)
                   : (option.hovered
                      ? Theme.withAlpha(Theme.parchment.goldLine, 0.13)
                      : "transparent")
            border.width: option.highlighted ? 1 : 0
            border.color: Theme.withAlpha(Theme.warm.primary, 0.22)
        }
    }

    popup: Popup {
        id: popup
        y: control.height + 7
        width: control.width
        implicitHeight: Math.min(control.popupMaxHeight, optionList.contentHeight + 14)
        padding: 7
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

        background: Item {
            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 8
                anchors.leftMargin: 3
                anchors.rightMargin: -3
                anchors.bottomMargin: -6
                radius: 15
                color: Theme.withAlpha(Theme.parchment.woodShadow, 0.62)
            }

            Rectangle {
                anchors.fill: parent
                radius: 15
                color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.98)
                border.width: 1
                border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.52)

                Image {
                    anchors.fill: parent
                    anchors.margins: 2
                    source: Illustrations.texParchment
                    fillMode: Image.Tile
                    opacity: 0.17
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: 14
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.rgba(1, 248 / 255, 234 / 255, 0.36)
                }
            }
        }

        contentItem: ListView {
            id: optionList
            clip: true
            implicitHeight: contentHeight
            boundsBehavior: Flickable.StopAtBounds
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            spacing: 3
        }
    }
}
