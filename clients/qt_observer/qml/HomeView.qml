import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "homeView"
    anchors.fill: parent

    Component.onCompleted: ObserverClient.checkHealth()

    Column {
        anchors.centerIn: parent
        spacing: 20

        Text {
            text: qsTr("Werewolf Observer")
            font.pixelSize: 32
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

            Text { text: qsTr("Server:") }
            StatusBadge {
                id: serverStatusBadge
                objectName: "serverStatusBadge"
                status: ObserverClient.connected ? "connected" : "disconnected"
            }
        }

        Button {
            id: startNewMatchButton
            objectName: "startNewMatchButton"
            text: qsTr("Start New Match")
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.StackView.view.parent.navigateSetup()
        }

        Button {
            id: historyButton
            objectName: "historyButton"
            text: qsTr("History")
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: {
                ObserverClient.refreshRuns()
                root.StackView.view.parent.navigateHistory()
            }
        }

        Text {
            text: qsTr("Recent Runs:")
            font.pixelSize: 14
            anchors.horizontalCenter: parent.horizontalCenter
        }

        ListView {
            id: recentRunsList
            objectName: "recentRunsList"
            width: 400
            height: 150
            model: ObserverClient.runItems
            clip: true

            delegate: ItemDelegate {
                width: ListView.view.width
                text: (modelData.run_id || "") + " [" + (modelData.status || "") + "]"
                onClicked: {
                    ObserverClient.openRun(modelData.run_id)
                    root.StackView.view.parent.navigateCockpit()
                }
            }
        }
    }
}
