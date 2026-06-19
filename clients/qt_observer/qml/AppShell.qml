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
    property string _cockpitReturnView: "home"

    onCurrentViewChanged: {
        if (currentView === "home")
            warmAssetPreloader.schedule()
    }

    // CLI --open-run: auto-open a run straight into the theater (mirrors Preflight's
    // poll-then-navigate so currentRunId is set before the cockpit loads).
    Component.onCompleted: {
        if (ObserverClient.initialRunId !== "") {
            ObserverClient.openRun(ObserverClient.initialRunId)
            autoOpenPoller.start()
        }
        Qt.callLater(warmAssetPreloader.schedule)
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
        // Home is a full-bleed warm hub with its own NavRail/chrome; the god-view
        // cockpit + design preview are full-bleed board-game HUDs that carry their
        // own brand block in the left panel. Hide the slim desktop top bar on all
        // three so the spectator盘面 reaches parent.top (no generic toolbar).
        readonly property bool _chromeless: root.currentView === "home"
                                            || root.currentView === "setup"
                                            || root.currentView === "cockpit"
                                            || root.currentView === "history"
                                            || root.currentView === "providerSettings"
                                            || root.currentView === "designPreview"
        visible: !_chromeless
        height: !_chromeless ? 52 : 0

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
                text: I18n.t("狼人杀观察席", "WEREWOLF OBSERVER")
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

        // Full-bleed illustrated views do their own first-frame painting. Keep
        // StackView swaps instant so the previous page does not flash underneath.
        pushEnter: Transition {}
        pushExit: Transition {}
        popEnter: Transition {}
        popExit: Transition {}
        replaceEnter: Transition {}
        replaceExit: Transition {}
    }

    Item {
        id: warmAssetPreloader
        // Invisible asynchronous warmup for first home -> setup/history jumps.
        // Sources are assigned one by one after the home frame has settled, so
        // navigation clicks do not pay a synchronous decode cost.
        width: 1
        height: 1
        x: -10000
        y: -10000
        opacity: 0
        visible: true

        property int loadedCount: 0
        property bool started: false
        readonly property var assets: [
            { "source": Illustrations.historyArchive, "width": 1672, "height": 941 },
            { "source": Illustrations.setupRoom, "width": 1672, "height": 941 },
            { "source": Illustrations.tarot("werewolf"), "width": 304, "height": 456 },
            { "source": Illustrations.tarot("seer"), "width": 304, "height": 456 },
            { "source": Illustrations.tarot("witch"), "width": 304, "height": 456 },
            { "source": Illustrations.tarot("villager"), "width": 304, "height": 456 },
            { "source": Illustrations.tarot("guard"), "width": 304, "height": 456 },
            { "source": Illustrations.tarot("hunter"), "width": 304, "height": 456 }
        ]

        function schedule() {
            if (ObserverClient.initialRunId !== "")
                return
            if (loadedCount >= assets.length)
                return
            if (started)
                warmStepTimer.start()
            else
                warmStartTimer.restart()
        }

        Timer {
            id: warmStartTimer
            interval: 320
            repeat: false
            onTriggered: {
                if (root.currentView !== "home")
                    return
                warmAssetPreloader.started = true
                warmStepTimer.start()
            }
        }

        Timer {
            id: warmStepTimer
            interval: 120
            repeat: true
            onTriggered: {
                if (root.currentView !== "home") {
                    stop()
                    return
                }
                warmAssetPreloader.loadedCount++
                if (warmAssetPreloader.loadedCount >= warmAssetPreloader.assets.length)
                    stop()
            }
        }

        Repeater {
            model: warmAssetPreloader.assets
            delegate: Image {
                required property int index
                required property var modelData
                width: 1
                height: 1
                source: index < warmAssetPreloader.loadedCount ? modelData.source : ""
                asynchronous: true
                cache: true
                sourceSize.width: modelData.width
                sourceSize.height: modelData.height
                fillMode: Image.PreserveAspectFit
                opacity: 0
                visible: true
            }
        }
    }

    Component { id: homeComponent; HomeView { objectName: "homeView" } }
    Component { id: setupComponent; MatchSetupView { objectName: "matchSetupView" } }
    Component { id: preflightComponent; PreflightView { objectName: "preflightView" } }
    Component { id: cockpitComponent; TheaterView { objectName: "theaterView" } }
    Component { id: historyComponent; HistoryView { objectName: "historyView" } }
    Component { id: providerSettingsComponent; ProviderSettingsView { objectName: "providerSettingsView" } }
    Component { id: designPreviewComponent; DesignPreviewView { objectName: "designPreviewView" } }

    function _finishNav(view) {
        currentView = view
    }

    function _popToHome() {
        if (stackView.depth > 1) {
            while (stackView.depth > 2)
                stackView.pop(StackView.Immediate)
            stackView.pop()
        }
        _finishNav("home")
    }

    function _showPrimary(component, view) {
        if (currentView === view)
            return
        if (currentView !== "home" || stackView.depth > 1) {
            while (stackView.depth > 1)
                stackView.pop(StackView.Immediate)
        }
        stackView.push(component)
        _finishNav(view)
    }

    function _pushOverlay(component, view) {
        if (currentView === view)
            return
        stackView.push(component)
        _finishNav(view)
    }

    function _popOverlay(returnView) {
        if (stackView.depth > 1)
            stackView.pop()
        _finishNav(returnView)
    }

    function _refreshSetupRuntimeState() {
        ObserverClient.refreshCapabilities()
        var configured = CredentialStore.configuredProviders()
        for (var i = 0; i < configured.length; i++)
            CredentialStore.syncCredentialToServer(configured[i])
    }

    function navigateHome() {
        _popToHome()
    }

    function navigateSetup() {
        _showPrimary(setupComponent, "setup")
    }

    function navigatePreflight() {
        _showPrimary(preflightComponent, "preflight")
    }

    function navigateCockpit() {
        _cockpitReturnView = currentView === "history" ? "history" : "home"
        _pushOverlay(cockpitComponent, "cockpit")
    }

    function navigateHistory() {
        if (currentView === "cockpit" && _cockpitReturnView === "history") {
            _popOverlay("history")
            return
        }
        _showPrimary(historyComponent, "history")
    }

    function navigateDesignPreview() {
        _showPrimary(designPreviewComponent, "designPreview")
    }

    function navigateProviderSettings() {
        if (currentView === "providerSettings")
            return
        _providerReturnView = currentView
        _pushOverlay(providerSettingsComponent, "providerSettings")
    }

    // Return to whichever page opened settings without rebuilding that source page.
    function returnFromProviderSettings() {
        if (currentView === "providerSettings" && stackView.depth > 1) {
            if (_providerReturnView === "setup")
                _refreshSetupRuntimeState()
            _popOverlay(_providerReturnView)
            return
        }
        switch (_providerReturnView) {
        case "setup": navigateSetup(); break
        case "history": navigateHistory(); break
        case "preflight": navigatePreflight(); break
        case "cockpit": navigateCockpit(); break
        default: navigateHome()
        }
    }

    function returnFromCockpit() {
        if (_cockpitReturnView === "history" && currentView === "cockpit" && stackView.depth > 1) {
            ObserverClient.refreshRuns()
            _popOverlay("history")
            return
        }
        navigateHome()
    }

}
