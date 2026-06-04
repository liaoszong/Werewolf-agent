import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "matchSetupView"

    property var roles: [
        { seatId: "p1", roleName: "Werewolf" },
        { seatId: "p2", roleName: "Werewolf" },
        { seatId: "p3", roleName: "Seer" },
        { seatId: "p4", roleName: "Witch" },
        { seatId: "p5", roleName: "Villager" },
        { seatId: "p6", roleName: "Villager" },
    ]

    readonly property int cardWidth: 168

    // Page backdrop — deep night.
    Rectangle {
        anchors.fill: parent
        color: Theme.color.bgBase
    }

    // ----------------------------------------------------------- Main content
    // Left-aligned to the shared page gutter so the title, grid and the action
    // bar below all share one left edge.
    Flickable {
        id: scroller
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: actionBar.top
        contentWidth: width
        contentHeight: Math.max(height, content.implicitHeight + Theme.space.xxxl * 2)
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: content
            // Centered block — balanced on both axes when it fits, scrollable
            // when it doesn't. A natural starting point for the future
            // "select a seat → detail on the right" split.
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.max(Theme.space.xxxl, (scroller.height - content.implicitHeight) / 2)
            width: Math.min(root.cardWidth * 3 + Theme.space.lg * 2, scroller.width - Theme.layout.pageMargin * 2)
            spacing: Theme.space.lg

            // Page title
            Text {
                text: I18n.t("对局配置", "Match Setup")
                color: Theme.color.text
                font.family: Theme.font.display
                font.pixelSize: Theme.size.h1
                font.weight: Theme.weight.bold
            }

            // Template meta: humanized label + precise template id chip
            Row {
                spacing: Theme.space.sm

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("6 人局 · 测试模板", "6-Player Match · Test Template")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.body
                }

                Rectangle {
                    id: templateChip
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.color.surfaceInset
                    border.width: 1
                    border.color: Theme.color.border
                    radius: Theme.radius.sm
                    implicitWidth: chipLabel.implicitWidth + Theme.space.md * 2
                    implicitHeight: chipLabel.implicitHeight + Theme.space.xs * 2

                    Text {
                        id: chipLabel
                        anchors.centerIn: parent
                        text: "default_6p_fake"
                        color: Theme.color.textSecondary
                        font.family: Theme.font.mono
                        font.pixelSize: Theme.size.micro
                    }
                }
            }

            // Authoring note for the upcoming editing milestone.
            Text {
                text: I18n.t("提示词/档案编辑计划于 G2d 实现。", "Prompt/profile editing is planned for G2d.")
                color: Theme.color.textMuted
                font.family: Theme.font.family
                font.pixelSize: Theme.size.caption
            }

            // Breathing room before the seat grid.
            Item { width: 1; height: Theme.space.xs }

            SectionHeader {
                title: I18n.t("座位分配", "Seat Assignments")
                caption: I18n.t("六个座位 · 两大阵营。角色仅在此上帝视角中揭示。", "Six seats — two factions. Roles are revealed in this god view only.")
            }

            // ------------------------------------------------ Role / seat grid
            // Left-aligned (not centered) so the grid shares the title's left edge.
            Grid {
                id: setupRoleCards
                objectName: "setupRoleCards"
                columns: 3
                spacing: Theme.space.lg

                Repeater {
                    model: root.roles
                    delegate: RoleCard {
                        seatId: modelData.seatId
                        roleName: modelData.roleName
                        displayRole: modelData.roleName
                        width: root.cardWidth
                        height: 190
                    }
                }
            }
        }
    }

    // ------------------------------------------------------ Bottom action bar
    // Wizard pattern: Back (ghost) on the left, primary advance on the right.
    Rectangle {
        id: actionBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Theme.layout.actionBarHeight
        color: Theme.color.surface

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            color: Theme.color.border
        }

        AppButton {
            text: I18n.t("返回", "Back")
            variant: "ghost"
            anchors.left: parent.left
            anchors.leftMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.StackView.view.parent.navigateHome()
        }

        AppButton {
            id: setupContinueButton
            objectName: "setupContinueButton"
            text: I18n.t("继续", "Continue")
            variant: "primary"
            width: 200
            anchors.right: parent.right
            anchors.rightMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.StackView.view.parent.navigatePreflight()
        }
    }
}
