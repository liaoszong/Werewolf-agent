import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    objectName: "viewBoundaryBadge"

    property string perspective: ""
    property string contractVersion: ""
    property int hiddenEventCount: 0
    property int hiddenSnapshotCount: 0

    width: row.width + 16
    height: row.height + 8
    radius: 4
    color: "#e8f5e9"
    border.color: "#81c784"
    border.width: 1

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8

        Text {
            objectName: "viewBoundaryPerspective"
            text: {
                if (root.perspective === "god") return "God View"
                if (root.perspective === "public") return "Public View"
                if (root.perspective.startsWith("role:")) return "Role View (" + root.perspective.substring(5) + ")"
                if (root.perspective.startsWith("team:")) return "Team View (" + root.perspective.substring(5) + ")"
                return root.perspective
            }
            font.pixelSize: 12
            font.bold: true
            color: "#2e7d32"
        }

        Text {
            text: "v" + root.contractVersion
            font.pixelSize: 11
            color: "#388e3c"
        }

        Text {
            objectName: "viewBoundaryHiddenCounts"
            text: "Hidden: " + root.hiddenEventCount + " events, " + root.hiddenSnapshotCount + " snaps"
            font.pixelSize: 11
            color: "#d32f2f"
            visible: root.hiddenEventCount > 0 || root.hiddenSnapshotCount > 0
        }
    }
}
