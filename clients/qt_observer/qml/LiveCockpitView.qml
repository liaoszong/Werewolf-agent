import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Live Cockpit — "Nightfall" redesign.
// Dense observer surface: header + boundary, players, events and audit links,
// each grouped into AppCard sections inside a scrollable Flickable.
// Presentation only — all ObserverClient bindings/calls and the visibility
// contract are preserved verbatim.
Item {
    id: root
    objectName: "liveCockpitView"

    Component.onCompleted: {
        if (ObserverClient.currentRunId !== "") {
            ObserverClient.connectStream()
            ObserverClient.refreshProjection()
        }
    }

    // Deep-night page backdrop
    Rectangle {
        anchors.fill: parent
        color: Theme.color.bgBase
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        anchors.margins: Theme.space.xl
        contentWidth: width
        contentHeight: contentColumn.implicitHeight + 2 * Theme.space.xl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        Column {
            id: contentColumn
            x: 0
            y: Theme.space.xl
            width: scroller.width
            spacing: Theme.space.lg

            // ------------------------------------------------------- Header
            AppCard {
                width: parent.width
                implicitHeight: headerColumn.implicitHeight + Theme.space.xl * 2

                Column {
                    id: headerColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.xl
                    spacing: Theme.space.lg

                    // Title row: name · run id · status · perspective (right)
                    Item {
                        width: parent.width
                        implicitHeight: Math.max(headerLeft.implicitHeight, perspectiveSwitcher.implicitHeight)

                        Row {
                            id: headerLeft
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Theme.space.md

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: I18n.t("实况控制台", "Live Cockpit")
                                color: Theme.color.text
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.h1
                                font.weight: Theme.weight.bold
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: I18n.t("对局 ", "Run ") + ObserverClient.currentRunId
                                color: Theme.color.textSecondary
                                font.family: Theme.font.mono
                                font.pixelSize: Theme.size.small
                            }

                            StatusBadge {
                                id: runStatusBadge
                                objectName: "runStatusBadge"
                                anchors.verticalCenter: parent.verticalCenter
                                status: ObserverClient.currentStatus
                            }
                        }

                        PerspectiveSwitcher {
                            id: perspectiveSwitcher
                            objectName: "perspectiveSwitcher"
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    // Hairline divider between the title row and the boundary row
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Theme.color.hairline
                    }

                    // Visibility boundary + projection proof (wraps if narrow)
                    Flow {
                        width: parent.width
                        spacing: Theme.space.md

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
                    }
                }
            }

            // ------------------------------------------------------ Players
            AppCard {
                width: parent.width
                implicitHeight: playersColumn.implicitHeight + Theme.space.xl * 2

                Column {
                    id: playersColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.xl
                    spacing: Theme.space.lg

                    SectionHeader {
                        title: I18n.t("玩家", "Players")
                        caption: I18n.t("仅在当前视角允许时显示角色与阵营——隐藏座位保持隐藏。", "Role and team shown only where the perspective permits — hidden seats stay hidden.")
                    }

                    Grid {
                        id: playerPanelGrid
                        objectName: "playerPanelGrid"
                        columns: 6
                        spacing: Theme.space.md

                        Repeater {
                            model: ObserverClient.playerItems
                            delegate: RoleCard {
                                seatId: modelData.player_id
                                roleName: modelData.display_role
                                displayRole: modelData.display_role
                                displayTeam: modelData.display_team
                                visibilityLabel: modelData.visibility
                                statusText: modelData.alive ? "Alive" : "Dead"
                                width: 132
                                height: 150
                            }
                        }
                    }

                    EmptyState {
                        visible: playerPanelGrid.children.length === 0
                            || ObserverClient.playerItems.length === 0
                        anchors.horizontalCenter: parent.horizontalCenter
                        title: I18n.t("暂无可观察的座位", "No seats to observe")
                        subtitle: I18n.t("连接到一局对局以填充座位表。", "Connect to a run to populate the table.")
                    }

                    Text {
                        id: providerFailureSummary
                        objectName: "providerFailureSummary"
                        width: parent.width
                        text: I18n.t("模型调用失败：详见审计链接。", "Provider failures: check audit links for details.")
                        color: Theme.color.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                        wrapMode: Text.WordWrap
                    }
                }
            }

            // ------------------------------------------------------- Events
            AppCard {
                width: parent.width
                implicitHeight: eventsColumn.implicitHeight + Theme.space.xl * 2

                Column {
                    id: eventsColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.xl
                    spacing: Theme.space.md

                    SectionHeader {
                        title: I18n.t("事件", "Events")
                        caption: I18n.t("当前视角可见的按时间顺序排列的事件流。", "Chronological stream as visible to the current perspective.")
                    }

                    EventTimeline {
                        id: eventTimeline
                        objectName: "eventTimeline"
                        width: parent.width
                        height: 220
                    }
                }
            }

            // -------------------------------------------------- Audit Links
            AppCard {
                width: parent.width
                implicitHeight: auditColumn.implicitHeight + Theme.space.xl * 2

                Column {
                    id: auditColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.xl
                    spacing: Theme.space.md

                    SectionHeader {
                        title: I18n.t("审计链接", "Audit Links")
                        caption: I18n.t("将投影决策追溯到其源记录。", "Trace projection decisions back to their source records.")
                    }

                    AuditLinksPanel {
                        id: auditLinksPanel
                        objectName: "auditLinksPanel"
                        width: parent.width
                    }
                }
            }

            // ------------------------------------------------------- Footer
            Row {
                spacing: Theme.space.md

                AppButton {
                    text: I18n.t("断开", "Disconnect")
                    variant: "ghost"
                    onClicked: ObserverClient.disconnectStream()
                }

                AppButton {
                    text: I18n.t("返回首页", "Back to Home")
                    variant: "ghost"
                    onClicked: {
                        ObserverClient.disconnectStream()
                        root.StackView.view.parent.navigateHome()
                    }
                }
            }
        }
    }
}
