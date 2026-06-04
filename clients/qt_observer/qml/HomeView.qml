import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Nightfall Home — the Observer cockpit entry point.
// Presentation only: all ObserverClient bindings, navigation calls and
// objectNames are preserved exactly; only layout / styling / copy changed.
Item {
    id: root
    objectName: "homeView"

    Component.onCompleted: ObserverClient.checkHealth()

    // Centered, top-anchored content column constrained to a comfortable max width.
    Column {
        id: content
        width: Math.min(parent.width - Theme.space.xxl * 2, 900)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: Theme.space.huge
        spacing: Theme.space.xxl

        // ----------------------------------------------------------- (A) HERO
        AppCard {
            width: parent.width
            implicitHeight: heroBody.implicitHeight + Theme.space.xxl * 2

            Column {
                id: heroBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.space.xxl
                spacing: Theme.space.md

                Text {
                    text: I18n.t("观 战 席", "OBSERVER COCKPIT")
                    color: Theme.color.textMuted
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro
                    font.weight: Theme.weight.bold
                    font.letterSpacing: 2
                }

                Text {
                    text: I18n.t("狼人杀 · 观察席", "Werewolf Observer")
                    color: Theme.color.text
                    font.family: Theme.font.display
                    font.pixelSize: Theme.size.display
                    font.weight: Theme.weight.bold
                }

                Text {
                    width: parent.width
                    text: I18n.t("观察 AI 玩家如何欺骗、推理与投票 —— 一夜一局。", "Watch AI agents deceive, deduce, and vote — one night at a time.")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.body
                    wrapMode: Text.WordWrap
                }

                // Server status line
                Row {
                    spacing: Theme.space.sm
                    topPadding: Theme.space.xs

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: I18n.t("服务器", "Server")
                        color: Theme.color.textSecondary
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                    }

                    StatusBadge {
                        id: serverStatusBadge
                        objectName: "serverStatusBadge"
                        anchors.verticalCenter: parent.verticalCenter
                        status: ObserverClient.connected ? "connected" : "disconnected"
                    }
                }

                // Primary actions
                Row {
                    spacing: Theme.space.md
                    topPadding: Theme.space.sm

                    AppButton {
                        id: startNewMatchButton
                        objectName: "startNewMatchButton"
                        text: I18n.t("开始新对局", "Start New Match")
                        variant: "primary"
                        onClicked: root.StackView.view.parent.navigateSetup()
                    }

                    AppButton {
                        id: historyButton
                        objectName: "historyButton"
                        text: I18n.t("历史对局", "History")
                        variant: "ghost"
                        onClicked: {
                            ObserverClient.refreshRuns()
                            root.StackView.view.parent.navigateHistory()
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------- (B) RECENT RUNS
        AppCard {
            width: parent.width
            implicitHeight: runsBody.implicitHeight + Theme.space.xxl * 2

            Column {
                id: runsBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.space.xxl
                spacing: Theme.space.lg

                SectionHeader {
                    title: I18n.t("最近对局", "Recent Runs")
                }

                // Empty state when there is nothing to show.
                EmptyState {
                    width: parent.width
                    visible: ObserverClient.runItems.length === 0
                    title: I18n.t("暂无对局", "No matches yet")
                    subtitle: I18n.t("开始一局，在此实时观战。", "Start a new match to watch it unfold here.")
                }

                ListView {
                    id: recentRunsList
                    objectName: "recentRunsList"
                    width: parent.width
                    height: 180
                    clip: true
                    visible: ObserverClient.runItems.length > 0
                    model: ObserverClient.runItems
                    spacing: Theme.space.xs
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Item {
                        width: ListView.view.width
                        height: 44

                        Rectangle {
                            id: rowBg
                            anchors.fill: parent
                            anchors.leftMargin: 0
                            anchors.rightMargin: 0
                            radius: Theme.radius.md
                            color: hover.hovered ? Theme.color.surfaceAlt : "transparent"

                            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - statusBadge.width - Theme.space.md * 3
                                elide: Text.ElideRight
                                text: modelData.run_id || ""
                                color: Theme.color.text
                                font.family: Theme.font.mono
                                font.pixelSize: Theme.size.small
                            }

                            StatusBadge {
                                id: statusBadge
                                anchors.right: parent.right
                                anchors.rightMargin: Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                status: modelData.status || ""
                            }
                        }

                        HoverHandler {
                            id: hover
                            cursorShape: Qt.PointingHandCursor
                        }
                        TapHandler {
                            onTapped: {
                                ObserverClient.openRun(modelData.run_id)
                                root.StackView.view.parent.navigateCockpit()
                            }
                        }
                    }
                }
            }
        }
    }
}
