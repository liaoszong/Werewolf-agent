import QtQuick
import QtQuick.Controls

Item {
    id: root
    objectName: "appShell"
    anchors.fill: parent

    property string currentView: "home"

    StackView {
        id: stackView
        objectName: "appShellStack"
        anchors.fill: parent
        initialItem: homeComponent
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
