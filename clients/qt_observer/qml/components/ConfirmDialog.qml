import QtQuick
import QtQuick.Controls
import qt_observer

Popup {
    id: root
    objectName: "confirmDialog"

    property string title: ""
    property string message: ""
    property string confirmText: I18n.t("删除", "Delete")
    signal confirmed()

    modal: true
    focus: true
    anchors.centerIn: parent
    width: Math.min(420, parent ? parent.width - Theme.space.xl * 2 : 420)
    padding: Theme.space.lg
    Overlay.modal: Rectangle {
        color: Theme.withAlpha(Theme.warm.ink, 0.38)
    }
    background: Rectangle {
        color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.98)
        radius: Theme.radius.md
        border.width: 1
        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.62)
        clip: true

        Image {
            anchors.fill: parent
            anchors.margins: 1
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.16
        }
    }

    contentItem: Column {
        spacing: Theme.space.md
        Text {
            width: root.availableWidth
            text: root.title
            color: Theme.parchment.ink
            font.family: Theme.fontFamilies.serif
            font.contextFontMerging: true
            font.pixelSize: Theme.warmSize.titleMd
            font.weight: Theme.weight.semibold
            wrapMode: Text.Wrap
        }
        Text {
            width: root.availableWidth
            text: root.message
            color: Theme.parchment.inkSoft
            font.family: Theme.fontFamilies.sans
            font.contextFontMerging: true
            font.pixelSize: Theme.size.caption
            wrapMode: Text.Wrap
        }
        Row {
            anchors.right: parent.right
            spacing: Theme.space.sm
            AppButton {
                objectName: "confirmCancelButton"
                text: I18n.t("取消", "Cancel")
                variant: "ghost"
                onLight: true
                onClicked: root.close()
            }
            AppButton {
                objectName: "confirmAcceptButton"
                text: root.confirmText
                variant: "danger"
                onLight: true
                onClicked: { root.close(); root.confirmed() }
            }
        }
    }
}
