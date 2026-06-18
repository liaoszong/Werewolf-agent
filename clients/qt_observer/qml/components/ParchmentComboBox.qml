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
    property int arrowAreaWidth: compact ? 34 : 38

    hoverEnabled: true
    implicitHeight: compact ? 36 : 42
    leftPadding: compact ? 12 : 14
    rightPadding: arrowAreaWidth + (compact ? 10 : 12)

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
            color: Theme.withAlpha(Theme.parchment.highlightLine, control.enabled ? 0.45 : 0.20)
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
            anchors.right: arrowArea.left
            anchors.rightMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            text: control.displayText
            color: control.enabled ? Theme.parchment.ink : Theme.parchment.mutedInk
            font: control.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }

        Item {
            id: arrowArea
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: control.arrowAreaWidth

            Rectangle {
                anchors.centerIn: parent
                width: control.compact ? 21 : 23
                height: control.compact ? 21 : 23
                radius: control.compact ? 8 : 9
                color: control.enabled
                       ? Theme.withAlpha(Theme.parchment.goldLine, control.popup.visible ? 0.34 : 0.20)
                       : Theme.withAlpha(Theme.parchment.goldLine, 0.13)
                border.width: 1
                border.color: control.enabled
                              ? Theme.withAlpha(Theme.parchment.goldLine, control.popup.visible ? 0.58 : 0.38)
                              : Theme.withAlpha(Theme.parchment.goldLine, 0.20)

                Canvas {
                    id: chevronGlyph
                    anchors.centerIn: parent
                    width: control.compact ? 10 : 11
                    height: control.compact ? 7 : 8
                    antialiasing: true
                    rotation: control.popup.visible ? 180 : 0

                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        ctx.lineWidth = control.compact ? 1.35 : 1.45
                        ctx.lineCap = "round"
                        ctx.lineJoin = "round"
                        ctx.strokeStyle = control.enabled
                                ? Theme.withAlpha(Theme.parchment.ink, 0.82)
                                : Theme.withAlpha(Theme.parchment.mutedInk, 0.62)
                        ctx.beginPath()
                        ctx.moveTo(1.2, 1.5)
                        ctx.lineTo(width / 2, height - 1.4)
                        ctx.lineTo(width - 1.2, 1.5)
                        ctx.stroke()
                    }

                    Behavior on rotation {
                        NumberAnimation { duration: Theme.motion.fast; easing.type: Easing.OutCubic }
                    }

                    Connections {
                        target: control.popup
                        function onVisibleChanged() { chevronGlyph.requestPaint() }
                    }

                    Connections {
                        target: control
                        function onEnabledChanged() { chevronGlyph.requestPaint() }
                    }
                }
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
                    border.color: Theme.withAlpha(Theme.parchment.highlightLine, 0.36)
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
