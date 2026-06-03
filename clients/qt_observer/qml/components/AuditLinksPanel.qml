import QtQuick
import QtQuick.Controls
import qt_observer

Column {
    id: root
    objectName: "auditLinksPanel"

    property var linkMap: ({
        "/manifest": "Prompt Manifest",
        "/provider-trace": "Provider Trace",
        "/failure-audit": "Failure Audit",
        "/snapshots": "Snapshots",
        "/artifacts": "Artifacts",
    })

    Repeater {
        model: [
            { label: "Prompt Manifest", tag: "manifest" },
            { label: "Provider Trace", tag: "provider-trace" },
            { label: "Failure Audit", tag: "failure-audit" },
            { label: "Snapshots", tag: "snapshots" },
            { label: "Artifacts", tag: "artifacts" },
        ]

        delegate: Text {
            text: modelData.label
            font.pixelSize: 13
            color: "#1976d2"
            font.underline: true

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    var path = "/api/runs/" + ObserverClient.currentRunId + "/" + modelData.tag
                    console.log("Audit link:", ObserverClient.baseUrl + path)
                }
            }
        }

        objectName: ""
    }
}
