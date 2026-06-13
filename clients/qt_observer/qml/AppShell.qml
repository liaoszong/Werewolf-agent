import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "appShell"
    anchors.fill: parent

    property string currentView: "home"
    // The view to return to when leaving the provider-settings page (it is reached
    // from any page via the global gear, so it remembers where it was opened from).
    property string _providerReturnView: "home"

    // CLI --open-run: auto-open a run straight into the theater (mirrors Preflight's
    // poll-then-navigate so currentRunId is set before the cockpit loads).
    Component.onCompleted: {
        if (ObserverClient.initialRunId !== "") {
            ObserverClient.openRun(ObserverClient.initialRunId)
            autoOpenPoller.start()
        }
    }
    Timer {
        id: autoOpenPoller
        interval: 150
        repeat: true
        running: false
        onTriggered: {
            if (ObserverClient.currentRunId !== "") {
                stop()
                navigateCockpit()
            }
        }
    }

    // Ambient night backdrop behind everything
    AppBackground {
        anchors.fill: parent
    }

    // Slim persistent brand bar (wordmark + global connection status)
    Item {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        // Home is a full-bleed warm hub with its own NavRail/chrome; hide the slim
        // top bar there (and collapse its height) so HomeView reaches parent.top.
        visible: root.currentView !== "home"
        height: root.currentView !== "home" ? 52 : 0

        Row {
            anchors.left: parent.left
            anchors.leftMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.md

            // Crescent-moon mark
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 24
                height: 24
                radius: 7
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Theme.color.text }
                    GradientStop { position: 1.0; color: Theme.color.textMuted }
                }

                Rectangle {
                    x: 11
                    y: 4
                    width: 13
                    height: 13
                    radius: 7
                    color: Theme.color.bg
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "WEREWOLF OBSERVER"
                color: Theme.color.text
                font.family: Theme.font.family
                font.pixelSize: Theme.size.caption
                font.weight: Theme.weight.bold
                font.letterSpacing: 2
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.md

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.space.sm

                GlowDot {
                    anchors.verticalCenter: parent.verticalCenter
                    diameter: 8
                    color: ObserverClient.connected ? Theme.color.success : Theme.color.textMuted
                    pulse: ObserverClient.connected
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: ObserverClient.connected ? I18n.t("已连接", "Connected") : I18n.t("离线", "Offline")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro
                    font.weight: Theme.weight.medium
                }
            }

            // Global HUD data-source chip — executed truth (run-detail
            // execution_mode), NOT intent.  Conservative SYS: SIMULATION until a
            // run detail returns a mode; never optimistic-live.
            DataSourceChip {
                objectName: "dataSourceChip"
                anchors.verticalCenter: parent.verticalCenter
                mode: ObserverClient.currentExecutionMode
            }

            // Divider
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 1
                height: 16
                color: Theme.color.border
            }

            // 中 / EN language toggle
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: langRow.implicitWidth + 4
                implicitHeight: 24
                radius: Theme.radius.sm
                color: Theme.color.surfaceInset
                border.width: 1
                border.color: Theme.color.border

                Row {
                    id: langRow
                    anchors.centerIn: parent
                    spacing: 0

                    Repeater {
                        model: [{ code: "zh", label: "中" }, { code: "en", label: "EN" }]
                        delegate: Rectangle {
                            required property var modelData
                            width: 28
                            height: 20
                            radius: Theme.radius.sm - 2
                            color: I18n.lang === modelData.code ? Theme.color.surfaceAlt : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: I18n.lang === modelData.code ? Theme.color.text : Theme.color.textMuted
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.micro
                                font.weight: I18n.lang === modelData.code ? Theme.weight.bold : Theme.weight.regular
                            }

                            TapHandler { onTapped: I18n.lang = modelData.code }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                        }
                    }
                }
            }

            // Divider (hidden alongside the gear so no trailing separator is left
            // dangling on the settings page itself).
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                visible: root.currentView !== "providerSettings"
                width: 1
                height: 16
                color: Theme.color.border
            }

            // Global entry to the provider/model settings page (reachable from any
            // view).  Hidden while already on that page to avoid re-entry loops.
            GearButton {
                objectName: "providerSettingsGear"
                anchors.verticalCenter: parent.verticalCenter
                visible: root.currentView !== "providerSettings"
                onClicked: root.navigateProviderSettings()
            }
        }

        // Bottom hairline
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.color.border
        }
    }

    StackView {
        id: stackView
        objectName: "appShellStack"
        anchors.top: topBar.visible ? topBar.bottom : parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        initialItem: homeComponent

        // Gentle cross-fade between views
        replaceEnter: Transition {
            PropertyAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: Theme.motion.base; easing.type: Easing.OutCubic }
        }
        replaceExit: Transition {
            PropertyAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: Theme.motion.fast; easing.type: Easing.InCubic }
        }
    }

    Component { id: homeComponent; HomeView { objectName: "homeView" } }
    Component { id: setupComponent; MatchSetupView { objectName: "matchSetupView" } }
    Component { id: preflightComponent; PreflightView { objectName: "preflightView" } }
    Component { id: cockpitComponent; TheaterView { objectName: "theaterView" } }
    Component { id: historyComponent; HistoryView { objectName: "historyView" } }
    Component { id: providerSettingsComponent; ProviderSettingsView { objectName: "providerSettingsView" } }

    function navigateHome() {
        stackView.replace(homeComponent)
        currentView = "home"
    }

    function navigateSetup() {
        stackView.replace(setupComponent)
        currentView = "setup"
    }

    function navigatePreflight() {
        stackView.replace(preflightComponent)
        currentView = "preflight"
    }

    function navigateCockpit() {
        stackView.replace(cockpitComponent)
        currentView = "cockpit"
    }

    function navigateHistory() {
        stackView.replace(historyComponent)
        currentView = "history"
    }

    function navigateProviderSettings() {
        if (currentView === "providerSettings")
            return
        _providerReturnView = currentView
        stackView.replace(providerSettingsComponent)
        currentView = "providerSettings"
    }

    // Return to whichever page opened the settings (a fresh replace re-runs that
    // view's Component.onCompleted, so newly configured providers are picked up).
    function returnFromProviderSettings() {
        switch (_providerReturnView) {
        case "setup": navigateSetup(); break
        case "history": navigateHistory(); break
        case "preflight": navigatePreflight(); break
        case "cockpit": navigateCockpit(); break
        default: navigateHome()
        }
    }
}
