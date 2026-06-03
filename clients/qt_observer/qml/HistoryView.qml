import QtQuick
import QtQuick.Controls
import qt_observer

Item {
    id: root
    objectName: "historyView"
    anchors.fill: parent

    Component.onCompleted: ObserverClient.refreshRuns()

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8

        Text {
            text: qsTr("History")
            font.pixelSize: 24
        }

        Row {
            spacing: 8

            Button {
                id: historyRefreshButton
                objectName: "historyRefreshButton"
                text: qsTr("Refresh")
                onClicked: ObserverClient.refreshRuns()
            }
        }

        ListView {
            id: historyRunsList
            objectName: "historyRunsList"
            width: 600
            height: 400
            model: ObserverClient.runItems
            clip: true

            delegate: ItemDelegate {
                id: runDelegate
                width: ListView.view.width

                Row {
                    spacing: 12
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        text: modelData.run_id || ""
                        width: 200
                        font.pixelSize: 13
                    }

                    StatusBadge {
                        status: modelData.status || ""
                    }

                    Button {
                        id: openReplayButton
                        objectName: "openReplayButton"
                        text: qsTr("Open")
                        onClicked: {
                            ObserverClient.openRun(modelData.run_id)
                            root.StackView.view.parent.navigateCockpit()
                        }
                    }
                }
            }
        }

        Button {
            text: qsTr("Back to Home")
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.StackView.view.parent.navigateHome()
        }
    }
}
