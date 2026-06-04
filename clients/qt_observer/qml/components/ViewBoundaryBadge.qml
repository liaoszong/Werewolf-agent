import QtQuick
import qt_observer

// Trust-boundary pill: surfaces the active visibility perspective, the
// contract version it was rendered under, and how much was withheld.
// Presentation only — perspective derivation and counts are unchanged.
Rectangle {
    id: root
    objectName: "viewBoundaryBadge"

    property string perspective: ""
    property string contractVersion: ""
    property int hiddenEventCount: 0
    property int hiddenSnapshotCount: 0

    implicitWidth: row.implicitWidth + Theme.space.md * 2
    implicitHeight: row.implicitHeight + Theme.space.sm * 2
    width: implicitWidth
    height: implicitHeight

    radius: Theme.radius.md
    color: Theme.color.surfaceInset
    border.width: 1
    border.color: Theme.withAlpha(Theme.color.info, 0.4)

    Row {
        id: row
        anchors.centerIn: parent
        spacing: Theme.space.sm

        // Drawn eye/shield glyph — a watchful boundary mark (no emoji)
        Item {
            id: glyph
            width: 14
            height: 14
            anchors.verticalCenter: parent.verticalCenter

            // Outer lens / shield contour
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "transparent"
                border.width: 1.5
                border.color: Theme.color.info
            }
            // Iris
            Rectangle {
                anchors.centerIn: parent
                width: 5
                height: 5
                radius: width / 2
                color: Theme.color.info
            }
        }

        Text {
            objectName: "viewBoundaryPerspective"
            anchors.verticalCenter: parent.verticalCenter
            text: {
                if (root.perspective === "god") return I18n.t("上帝视角", "God View")
                if (root.perspective === "public") return I18n.t("公开视角", "Public View")
                if (root.perspective.startsWith("role:")) return I18n.t("座位视角 (", "Role View (") + root.perspective.substring(5) + ")"
                if (root.perspective.startsWith("team:")) return I18n.t("阵营视角 (", "Team View (") + root.perspective.substring(5) + ")"
                return root.perspective
            }
            color: Theme.color.text
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
            font.weight: Theme.weight.semibold
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "v" + root.contractVersion
            color: Theme.color.textMuted
            font.family: Theme.font.mono
            font.pixelSize: Theme.size.micro
        }

        Text {
            objectName: "viewBoundaryHiddenCounts"
            anchors.verticalCenter: parent.verticalCenter
            visible: root.hiddenEventCount > 0 || root.hiddenSnapshotCount > 0
            text: I18n.t("已隐藏：", "Hidden: ") + root.hiddenEventCount + I18n.t(" 个事件，", " events, ") + root.hiddenSnapshotCount + I18n.t(" 个快照", " snaps")
            color: Theme.color.danger
            font.family: Theme.font.family
            font.pixelSize: Theme.size.micro
        }
    }
}
