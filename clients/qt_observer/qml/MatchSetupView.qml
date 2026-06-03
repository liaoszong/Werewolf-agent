import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "matchSetupView"
    anchors.fill: parent

    property var roles: [
        { seatId: "p1", roleName: "Werewolf" },
        { seatId: "p2", roleName: "Werewolf" },
        { seatId: "p3", roleName: "Seer" },
        { seatId: "p4", roleName: "Witch" },
        { seatId: "p5", roleName: "Villager" },
        { seatId: "p6", roleName: "Villager" },
    ]

    Column {
        anchors.centerIn: parent
        spacing: 16

        Text {
            text: qsTr("Match Setup")
            font.pixelSize: 24
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: qsTr("Template: default_6p_fake")
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: qsTr("Prompt/profile editing is planned for G2d.")
            font.pixelSize: 11
            color: "#888"
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Grid {
            id: setupRoleCards
            objectName: "setupRoleCards"
            anchors.horizontalCenter: parent.horizontalCenter
            columns: 3
            spacing: 8

            Repeater {
                model: root.roles
                delegate: RoleCard {
                    seatId: modelData.seatId
                    roleName: modelData.roleName
                }
            }
        }

        Button {
            id: setupContinueButton
            objectName: "setupContinueButton"
            text: qsTr("Continue")
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.StackView.view.parent.navigatePreflight()
        }

        Button {
            text: qsTr("Back")
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.StackView.view.parent.navigateHome()
        }
    }
}
