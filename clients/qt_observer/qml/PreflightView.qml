import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "preflightView"

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

    // Page backdrop — deep night.
    Rectangle {
        anchors.fill: parent
        color: Theme.color.bgBase
    }

    // Left-aligned content sharing the page gutter with the action bar below.
    Flickable {
        id: scroller
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: actionBar.top
        contentWidth: width
        contentHeight: Math.max(height, launchColumn.implicitHeight + Theme.space.xxxl * 2)
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: launchColumn
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.max(Theme.space.xxxl, (scroller.height - launchColumn.implicitHeight) / 2)
            width: Math.min(600, scroller.width - Theme.layout.pageMargin * 2)
            spacing: Theme.space.lg

            // Eyebrow label — keeps the "Nightfall" mystique restrained.
            Text {
                text: I18n.t("启动序列", "LAUNCH SEQUENCE")
                color: Theme.color.textMuted
                font.family: Theme.font.family
                font.pixelSize: Theme.size.micro
                font.weight: Theme.weight.semibold
                font.letterSpacing: 2
            }

            // The launch panel.
            AppCard {
                width: parent.width
                implicitHeight: panelColumn.implicitHeight + Theme.space.xxl * 2

                Column {
                    id: panelColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.xxl
                    spacing: Theme.space.lg

                    Text {
                        text: I18n.t("启动前检查", "Preflight Check")
                        color: Theme.color.text
                        font.family: Theme.font.display
                        font.pixelSize: Theme.size.h1
                        font.weight: Theme.weight.bold
                    }

                    Text {
                        width: parent.width
                        text: I18n.t("启动前请确认对局配置。", "Confirm the match configuration before launch.")
                        color: Theme.color.textSecondary
                        wrapMode: Text.WordWrap
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.body
                    }

                    // ---- Check rows -------------------------------------------------
                    Column {
                        width: parent.width
                        spacing: 0

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Theme.color.border
                        }

                        // Server status
                        Item {
                            width: parent.width
                            height: Math.max(serverLabel.implicitHeight, serverBadge.implicitHeight) + Theme.space.md * 2

                            Text {
                                id: serverLabel
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 120
                                text: I18n.t("服务器", "Server")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.body
                            }

                            StatusBadge {
                                id: serverBadge
                                objectName: "preflightServerStatus"
                                anchors.left: parent.left
                                anchors.leftMargin: 120 + Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                status: ObserverClient.connected ? "connected" : "disconnected"
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Theme.color.border
                        }

                        // Template
                        Item {
                            width: parent.width
                            height: Math.max(templateLabel.implicitHeight, templateValue.implicitHeight) + Theme.space.md * 2

                            Text {
                                id: templateLabel
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 120
                                text: I18n.t("模板", "Template")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.body
                            }

                            Text {
                                id: templateValue
                                objectName: "preflightTemplateSummary"
                                anchors.left: parent.left
                                anchors.leftMargin: 120 + Theme.space.md
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: I18n.t("模板：default_6p_fake", "Template: default_6p_fake")
                                color: Theme.color.text
                                wrapMode: Text.WordWrap
                                font.family: Theme.font.mono
                                font.pixelSize: Theme.size.small
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Theme.color.border
                        }

                        // Visibility boundary
                        Item {
                            width: parent.width
                            height: Math.max(visibilityLabel.implicitHeight, visibilityValue.implicitHeight) + Theme.space.md * 2

                            Text {
                                id: visibilityLabel
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.topMargin: Theme.space.md
                                width: 120
                                text: I18n.t("可见性", "Visibility")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.body
                            }

                            Text {
                                id: visibilityValue
                                objectName: "preflightVisibilitySummary"
                                anchors.left: parent.left
                                anchors.leftMargin: 120 + Theme.space.md
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.topMargin: Theme.space.md
                                text: I18n.t("可见性边界：事件可见性按所选视角过滤（god/public/team:werewolf/role:p*）", "Visibility boundary: event visibility is filtered by the selected perspective (god/public/team:werewolf/role:p*)")
                                color: Theme.color.textSecondary
                                wrapMode: Text.WordWrap
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.small
                                lineHeight: 1.25
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Theme.color.border
                        }
                    }
                }
            }
        }
    }

    // ------------------------------------------------------ Bottom action bar
    // Same wizard pattern as Match Setup: Back on the left, Start on the right.
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
            onClicked: root.StackView.view.parent.navigateSetup()
        }

        AppButton {
            id: startMatchButton
            objectName: "startMatchButton"
            text: I18n.t("开始对局", "Start Match")
            variant: "primary"
            width: 200
            anchors.right: parent.right
            anchors.rightMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            onClicked: {
                ObserverClient.startDefaultMatch()
                runIdPoller.start()
            }
        }
    }
}
