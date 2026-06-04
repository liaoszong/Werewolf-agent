import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "appShell"
    anchors.fill: parent

    property string currentView: "home"

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
        height: 52

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
        anchors.top: topBar.bottom
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
    Component { id: cockpitComponent; LiveCockpitView { objectName: "liveCockpitView" } }
    Component { id: historyComponent; HistoryView { objectName: "historyView" } }

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
}
