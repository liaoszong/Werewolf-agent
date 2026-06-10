import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// History — recorded and in-progress matches, with a one-click replay flow.
// Dark "Nightfall" surface; behaviour, bindings and navigation unchanged.
Item {
    id: root
    objectName: "historyView"

    Component.onCompleted: ObserverClient.refreshRuns()

    // ---- delete plumbing (spec §4) ----
    property string _pendingDeleteId: ""
    property bool _batchActive: false                 // Task 6's batch controller sets this

    ConfirmDialog {
        id: confirmDialog
        objectName: "historyConfirmDialog"
        parent: Overlay.overlay
        onConfirmed: {
            if (root._pendingDeleteId !== "") {
                ObserverClient.deleteRun(root._pendingDeleteId)
                root._pendingDeleteId = ""
            }
        }
    }

    // Transient notice (delete failures / batch summary). Auto-hides.
    Rectangle {
        id: noticeBar
        objectName: "historyNoticeBar"
        property string text: ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.xl
        z: 10
        visible: text !== ""
        width: noticeLabel.implicitWidth + Theme.space.lg * 2
        height: noticeLabel.implicitHeight + Theme.space.md * 2
        radius: Theme.radius.md
        color: Theme.withAlpha(Theme.color.surface, 0.96)
        border.width: 1
        border.color: Theme.color.border
        Text {
            id: noticeLabel
            anchors.centerIn: parent
            text: noticeBar.text
            color: Theme.color.text
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
        }
        Timer { id: noticeTimer; interval: 5000; onTriggered: noticeBar.text = "" }
        function show(msg) { text = msg; noticeTimer.restart() }
    }

    Connections {
        target: ObserverClient
        function onDeleteRunFinished(runId, ok, error) {
            if (root._batchActive) return            // Task 6 owns batch handling
            if (ok)
                ObserverClient.refreshRuns()          // SINGLE delete refreshes per-op (spec §4)
            else
                noticeBar.show(I18n.t("删除失败:", "Delete failed: ") + error)
        }
    }

    // Deep night backdrop so the centered content reads as a focused panel.
    Rectangle {
        anchors.fill: parent
        color: Theme.color.bgBase
    }

    // Centered, max-width content region anchored toward the top.
    Item {
        id: content
        anchors.fill: parent
        anchors.topMargin: Theme.space.xxxl
        anchors.bottomMargin: Theme.space.xxl
        anchors.leftMargin: Theme.space.xxl
        anchors.rightMargin: Theme.space.xxl

        Item {
            id: stack
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: Math.min(parent.width, 1000)

            // ---------------------------------------------------------- Header
            Item {
                id: header
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: titleBlock.implicitHeight

                Column {
                    id: titleBlock
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: refreshButton.left
                    anchors.rightMargin: Theme.space.lg
                    spacing: Theme.space.xs

                    Text {
                        text: I18n.t("历史对局", "History")
                        color: Theme.color.text
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.h1
                        font.weight: Theme.weight.bold
                    }

                    Text {
                        text: I18n.t("已记录与进行中的对局", "Recorded and in-progress matches")
                        color: Theme.color.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                    }
                }

                AppButton {
                    id: refreshButton
                    objectName: "historyRefreshButton"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("刷新", "Refresh")
                    variant: "secondary"
                    onClicked: ObserverClient.refreshRuns()
                }
            }

            // ----------------------------------------------------- Runs panel
            AppCard {
                id: runsPanel
                anchors.top: header.bottom
                anchors.topMargin: Theme.space.lg
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: footer.top
                anchors.bottomMargin: Theme.space.lg

                // Count chip + section label header inside the panel.
                Item {
                    id: panelHeader
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Theme.space.lg
                    height: panelTitle.implicitHeight

                    SectionHeader {
                        id: panelTitle
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        title: I18n.t("对局", "Runs")
                    }

                    Rectangle {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: 22
                        width: countLabel.implicitWidth + Theme.space.md * 2
                        radius: Theme.radius.pill
                        color: Theme.withAlpha(Theme.color.primary, 0.14)
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.color.primary, 0.30)
                        visible: ObserverClient.runItems.length > 0

                        Text {
                            id: countLabel
                            anchors.centerIn: parent
                            text: "" + ObserverClient.runItems.length
                            color: Theme.color.primary
                            font.family: Theme.font.mono
                            font.pixelSize: Theme.size.caption
                            font.weight: Theme.weight.semibold
                        }
                    }
                }

                Rectangle {
                    id: panelDivider
                    anchors.top: panelHeader.bottom
                    anchors.topMargin: Theme.space.md
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 1
                    anchors.rightMargin: 1
                    height: 1
                    color: Theme.color.border
                    visible: ObserverClient.runItems.length > 0
                }

                // The list of runs, or a friendly empty state.
                ListView {
                    id: historyRunsList
                    objectName: "historyRunsList"
                    anchors.top: panelDivider.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.topMargin: Theme.space.sm
                    anchors.bottomMargin: Theme.space.sm
                    model: ObserverClient.runItems
                    clip: true
                    visible: ObserverClient.runItems.length > 0
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }

                    delegate: Item {
                        id: runDelegate
                        width: ListView.view.width
                        height: 52

                        readonly property color _accent: Theme.statusColor(modelData.status || "")

                        Rectangle {
                            id: rowHighlight
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space.lg
                            anchors.rightMargin: Theme.space.lg
                            anchors.topMargin: 2
                            anchors.bottomMargin: 2
                            radius: Theme.radius.md
                            color: rowHover.hovered ? Theme.color.surfaceAlt : "transparent"

                            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

                            // Status-tinted leading accent bar.
                            Rectangle {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 3
                                height: 22
                                radius: 1.5
                                color: runDelegate._accent
                                opacity: rowHover.hovered ? 1.0 : 0.55

                                Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
                            }

                            // Run id (mono for a precise, trustworthy feel).
                            Text {
                                id: runIdText
                                anchors.left: parent.left
                                anchors.leftMargin: Theme.space.lg
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.max(120, parent.width
                                    - statusBadge.width - deleteButton.width - reportButton.width - openButton.width - Theme.space.xl * 5)
                                elide: Text.ElideRight
                                text: modelData.run_id || I18n.t("(未命名对局)", "(unnamed run)")
                                color: Theme.color.text
                                font.family: Theme.font.mono
                                font.pixelSize: Theme.size.small
                            }

                            StatusBadge {
                                id: statusBadge
                                anchors.right: deleteButton.left
                                anchors.rightMargin: Theme.space.lg
                                anchors.verticalCenter: parent.verticalCenter
                                status: modelData.status || ""
                            }

                            AppButton {
                                id: deleteButton
                                objectName: "deleteRunButton"
                                anchors.right: reportButton.visible ? reportButton.left : openButton.left
                                anchors.rightMargin: Theme.space.sm
                                anchors.verticalCenter: parent.verticalCenter
                                text: I18n.t("删除", "Delete")
                                variant: "ghost"
                                enabled: (modelData.status || "") !== "running"
                                         && (modelData.status || "") !== "queued"
                                opacity: enabled ? 1.0 : 0.35
                                onClicked: {
                                    root._pendingDeleteId = modelData.run_id
                                    confirmDialog.title = I18n.t("删除对局", "Delete run")
                                    confirmDialog.message = I18n.t("确定删除对局 ", "Delete run ")
                                        + modelData.run_id
                                        + I18n.t("?删除后不可恢复。", "? This cannot be undone.")
                                    confirmDialog.open()
                                }
                            }

                            // P2-D §7.7 — thin "查看战报" entry for finished runs. openRun's
                            // forReport=true sets the settlement entry intent synchronously, so
                            // the theater's settlement overlay opens straight to `report`
                            // (history-direct), skipping the live freeze ceremony.
                            AppButton {
                                id: reportButton
                                objectName: "openSettlementButton"
                                anchors.right: openButton.left
                                anchors.rightMargin: Theme.space.sm
                                anchors.verticalCenter: parent.verticalCenter
                                visible: (modelData.status || "") === "completed"
                                text: I18n.t("查看战报", "View report")
                                variant: "secondary"
                                onClicked: {
                                    ObserverClient.openRun(modelData.run_id, true)
                                    root.StackView.view.parent.navigateCockpit()
                                }
                            }

                            AppButton {
                                id: openButton
                                objectName: "openReplayButton"
                                anchors.right: parent.right
                                anchors.rightMargin: Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                text: I18n.t("打开", "Open")
                                variant: "ghost"
                                onClicked: {
                                    ObserverClient.openRun(modelData.run_id)
                                    root.StackView.view.parent.navigateCockpit()
                                }
                            }

                            HoverHandler {
                                id: rowHover
                            }
                        }
                    }
                }

                EmptyState {
                    anchors.centerIn: parent
                    visible: ObserverClient.runItems.length === 0
                    title: I18n.t("暂无记录", "No runs recorded")
                    subtitle: I18n.t("已完成与进行中的对局将显示在此。", "Completed and in-progress matches will appear here.")
                }
            }

            // ---------------------------------------------------------- Footer
            Item {
                id: footer
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: backButton.implicitHeight

                AppButton {
                    id: backButton
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("返回首页", "Back to Home")
                    variant: "ghost"
                    onClicked: root.StackView.view.parent.navigateHome()
                }
            }
        }
    }
}
