import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    objectName: "projectionProofPanel"

    property var proof: ({})
    property int hiddenEventCount: 0
    property int hiddenSnapshotCount: 0

    width: parent ? parent.width : 400
    height: column.height + 16
    radius: 4
    color: "#f5f5f5"
    border.color: "#e0e0e0"
    border.width: 1

    Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        spacing: 4

        Text {
            text: "Projection Proof"
            font.pixelSize: 14
            font.bold: true
            color: "#333"
        }

        Text {
            objectName: "projectionProofSource"
            text: "Source: " + (root.proof && root.proof.source ? root.proof.source : "Unknown")
            font.pixelSize: 12
            color: "#555"
        }

        Text {
            text: "Self: " + (root.proof && root.proof.self_role ? root.proof.self_role : "N/A") +
                  (root.proof && root.proof.self_team ? " (" + root.proof.self_team + ")" : "")
            font.pixelSize: 12
            color: "#555"
            visible: root.proof && root.proof.self_role !== undefined
        }

        Text {
            objectName: "projectionProofHiddenCounts"
            text: "Filtered: " + root.hiddenEventCount + " events, " + root.hiddenSnapshotCount + " snapshots"
            font.pixelSize: 12
            color: "#d32f2f"
            visible: root.hiddenEventCount > 0 || root.hiddenSnapshotCount > 0
        }

        Text {
            text: "Rules applied:"
            font.pixelSize: 12
            font.bold: true
            color: "#555"
            visible: root.proof && root.proof.rules && root.proof.rules.length > 0
            topPadding: 4
        }

        Repeater {
            objectName: "projectionProofRules"
            model: root.proof && root.proof.rules ? root.proof.rules : []
            delegate: Text {
                text: "• " + modelData
                font.pixelSize: 11
                color: "#666"
                wrapMode: Text.Wrap
                width: column.width
            }
        }
    }
}
