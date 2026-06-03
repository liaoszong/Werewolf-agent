import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "preflightView"
    anchors.fill: parent

    Timer {
        id: runIdPoller
        interval: 200
        repeat: true
        running: false
        onTriggered: {
            if (ObserverClient.currentRunId !== "") {
                stop()
                root.StackView.view.parent.navigateCockpit()
            }
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 16

        Text {
            text: qsTr("Preflight Check")
            font.pixelSize: 24
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

            Text { text: qsTr("Server Status:") }
            StatusBadge {
                id: preflightServerStatus
                objectName: "preflightServerStatus"
                status: ObserverClient.connected ? "connected" : "disconnected"
            }
        }

        Text {
            id: preflightTemplateSummary
            objectName: "preflightTemplateSummary"
            text: qsTr("Template: default_6p_fake")
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            id: preflightVisibilitySummary
            objectName: "preflightVisibilitySummary"
            text: qsTr("Visibility boundary: event visibility is filtered by selected perspective (god/public/team:werewolf/role:p*)")
            wrapMode: Text.WordWrap
            width: 500
            horizontalAlignment: Text.AlignHCenter
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Button {
            id: startMatchButton
            objectName: "startMatchButton"
            text: qsTr("Start Match")
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: {
                ObserverClient.startDefaultMatch()
                runIdPoller.start()
            }
        }

        Button {
            text: qsTr("Back")
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.StackView.view.parent.navigateSetup()
        }
    }
}
