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

        Grid {
            id: playerPanelGrid
            objectName: "playerPanelGrid"
            columns: 6
            spacing: 4

            Repeater {
                model: [
                    { seatId: "p1", role: "Werewolf" },
                    { seatId: "p2", role: "Werewolf" },
                    { seatId: "p3", role: "Seer" },
                    { seatId: "p4", role: "Witch" },
                    { seatId: "p5", role: "Villager" },
                    { seatId: "p6", role: "Villager" },
                ]
                delegate: RoleCard {
                    seatId: modelData.seatId
                    roleName: modelData.role
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
