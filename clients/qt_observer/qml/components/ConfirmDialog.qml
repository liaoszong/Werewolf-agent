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
    anchors.centerIn: parent
    width: Math.min(420, parent ? parent.width - Theme.space.xl * 2 : 420)
    padding: Theme.space.lg
    background: Rectangle {
        color: Theme.color.surface
        radius: Theme.radius.md
        border.width: 1
        border.color: Theme.color.border
    }

    contentItem: Column {
        spacing: Theme.space.md
        Text {
            width: root.availableWidth
            text: root.title
            color: Theme.color.text
            font.pixelSize: Theme.size.body
            font.weight: Theme.weight.semibold
            wrapMode: Text.Wrap
        }
        Text {
            width: root.availableWidth
            text: root.message
            color: Theme.color.textMuted
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
                onClicked: root.close()
            }
            AppButton {
                objectName: "confirmAcceptButton"
                text: root.confirmText
                variant: "danger"
                onClicked: { root.close(); root.confirmed() }
            }
        }
    }
}
