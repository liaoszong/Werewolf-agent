import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "liveCockpitView"
    anchors.fill: parent

    Component.onCompleted: {
        if (ObserverClient.currentRunId !== "") {
            ObserverClient.connectStream()
            ObserverClient.refreshProjection()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8

        Row {
            spacing: 16

            Text {
                text: qsTr("Live Cockpit")
                font.pixelSize: 24
            }

            Text {
                text: qsTr("Run: ") + ObserverClient.currentRunId
                font.pixelSize: 16
            }

            StatusBadge {
                id: runStatusBadge
                objectName: "runStatusBadge"
                status: ObserverClient.currentStatus
            }

            PerspectiveSwitcher {
                id: perspectiveSwitcher
                objectName: "perspectiveSwitcher"
            }
        }

        ViewBoundaryBadge {
            id: viewBoundaryBadge
            perspective: ObserverClient.currentPerspective
            contractVersion: ObserverClient.visibilityContractVersion
            hiddenEventCount: ObserverClient.hiddenEventCount
            hiddenSnapshotCount: ObserverClient.hiddenSnapshotCount
        }

        ProjectionProofPanel {
            id: projectionProofPanel
            proof: ObserverClient.projectionProof
            hiddenEventCount: ObserverClient.hiddenEventCount
            hiddenSnapshotCount: ObserverClient.hiddenSnapshotCount
        }

        Grid {
            id: playerPanelGrid
            objectName: "playerPanelGrid"
            columns: 6
            spacing: 4

            Repeater {
                model: ObserverClient.playerItems
                delegate: RoleCard {
                    seatId: modelData.player_id
                    roleName: modelData.display_role
                    displayRole: modelData.display_role
                    displayTeam: modelData.display_team
                    visibilityLabel: modelData.visibility
                    statusText: modelData.alive ? "Alive" : "Dead"
                    width: 120
                    height: 140
                }
            }
        }

        Text {
            id: providerFailureSummary
            objectName: "providerFailureSummary"
            text: qsTr("Provider failures: check audit links for details.")
            font.pixelSize: 12
            color: "#888"
        }

        Text {
            text: qsTr("Events:")
            font.pixelSize: 18
        }

        EventTimeline {
            id: eventTimeline
            objectName: "eventTimeline"
            width: parent.width
            height: 200
        }

        Text {
            text: qsTr("Audit Links:")
            font.pixelSize: 18
        }

        AuditLinksPanel {
            id: auditLinksPanel
            objectName: "auditLinksPanel"
            width: parent.width
            height: 100
        }

        Row {
            spacing: 8
            Button {
                text: qsTr("Disconnect")
                onClicked: ObserverClient.disconnectStream()
            }
            Button {
                text: qsTr("Back to Home")
                onClicked: {
                    ObserverClient.disconnectStream()
                    root.StackView.view.parent.navigateHome()
                }
            }
        }
    }
}
