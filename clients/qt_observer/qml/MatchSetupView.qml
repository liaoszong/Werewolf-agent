import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import qt_observer
import "components"

Item {
    id: root
    objectName: "matchSetupView"

    property string selectedSeatId: ""
    property var editedProfile: ({})
    property int profileRevision: 0
    property int _validatedRevision: -1
    property bool _initialLoadDone: false
    property int _credRev: 0
    property string currentConfigId: ""
    property string configStatusMessage: ""

    readonly property var seatRoles: ObserverClient.profileSchema && ObserverClient.profileSchema.seat_roles
                                      ? ObserverClient.profileSchema.seat_roles : ({})
    readonly property var roleTeams: ObserverClient.profileSchema && ObserverClient.profileSchema.role_teams
                                     ? ObserverClient.profileSchema.role_teams : ({})
    readonly property var seatIds: ObserverClient.profileSchema && ObserverClient.profileSchema.seat_ids
                                   ? ObserverClient.profileSchema.seat_ids : ["p1", "p2", "p3", "p4", "p5", "p6"]
    readonly property bool detailOpen: selectedSeatId !== ""
    readonly property string currentScriptLabel: I18n.t("新手友好 · 经典 6 人局", "Beginner Friendly · Classic 6-player")
    readonly property int arrangedCount: _arrangedCount()
    readonly property int seatTotal: seatIds.length
    readonly property bool autoReady: arrangedCount === seatTotal
                                      && ObserverClient.profileValidation
                                      && ObserverClient.profileValidation.valid === true
                                      && _validatedRevision === profileRevision
    readonly property bool launchEnabled: autoReady

    // Static-contract anchor only. It is intentionally not a visible button.
    Item {
        objectName: "setupValidateButton"
        visible: false
    }

    Dialog {
        id: saveConfigDialog
        objectName: "setupSaveConfigDialog"
        modal: true
        focus: true
        width: 360
        anchors.centerIn: Overlay.overlay
        title: I18n.t("另存为配置", "Save as config")
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: ObserverClient.saveConfig(saveConfigNameField.text, root.editedProfile)
        contentItem: Column {
            spacing: Theme.space.md
            TextField {
                id: saveConfigNameField
                objectName: "setupConfigNameField"
                width: parent.width
                selectByMouse: true
                placeholderText: I18n.t("配置名称", "Config name")
            }
        }
    }

    FileDialog {
        id: exportConfigDialog
        objectName: "setupExportConfigDialog"
        title: I18n.t("导出配置", "Export config")
        fileMode: FileDialog.SaveFile
        nameFilters: [I18n.t("狼人配置 (*.werewolf-config.json)", "Werewolf config (*.werewolf-config.json)"),
                      I18n.t("JSON 文件 (*.json)", "JSON files (*.json)")]
        onAccepted: {
            if (root.currentConfigId)
                ObserverClient.exportConfigToFile(root.currentConfigId, selectedFile.toString())
            else
                ObserverClient.exportProfileToFile(root._currentDisplayName(), root.editedProfile, selectedFile.toString())
        }
    }

    FileDialog {
        id: importConfigDialog
        objectName: "setupImportConfigDialog"
        title: I18n.t("导入配置", "Import config")
        fileMode: FileDialog.OpenFile
        nameFilters: [I18n.t("狼人配置 (*.werewolf-config.json)", "Werewolf config (*.werewolf-config.json)"),
                      I18n.t("JSON 文件 (*.json)", "JSON files (*.json)")]
        onAccepted: ObserverClient.importConfigFromFile(selectedFile.toString())
    }

    Component.onCompleted: {
        selectedSeatId = ""
        ObserverClient.refreshProfileSchema()
        ObserverClient.refreshProfiles()
        ObserverClient.refreshCapabilities()
        var configured = CredentialStore.configuredProviders()
        for (var i = 0; i < configured.length; i++)
            CredentialStore.syncCredentialToServer(configured[i])
    }

    onSelectedSeatIdChanged: setupModeControl.resetToFake()

    Connections {
        target: CredentialStore
        function onCredentialChanged(p) {
            root._credRev++
            root._scheduleAutoReady()
        }
    }

    Connections {
        target: ObserverClient
        function onProfileItemsChanged() {
            if (root.currentConfigId) {
                root._selectProfileItemByConfigId(root.currentConfigId)
                return
            }
            if (!root._initialLoadDone && ObserverClient.profileItems.length > 0) {
                root._initialLoadDone = true
                root._loadProfileItem(ObserverClient.profileItems[0])
            }
        }
        function onLoadedProfileChanged() {
            root.editedProfile = JSON.parse(JSON.stringify(ObserverClient.loadedProfile))
            if (!root.editedProfile.seat_overrides)
                root.editedProfile.seat_overrides = ({})
            root.profileRevision++
            root._validatedRevision = -1
            root.selectedSeatId = ""
            setupModeControl.resetToFake()
            root._scheduleAutoReady()
        }
        function onCapabilitiesChanged() {
            if (!ObserverClient.liveAvailable) setupModeControl.resetToFake()
        }
        function onLaunchSucceeded() {
            ObserverClient.openRun(ObserverClient.currentRunId, false)
            ObserverClient.connectStream()
            root.StackView.view.parent.navigateCockpit()
        }
        function onConfigSaved(configId) {
            root.currentConfigId = configId
            root.configStatusMessage = I18n.t("已保存为新配置", "Saved as new config")
            configStatusTimer.restart()
            ObserverClient.refreshProfiles()
            ObserverClient.fetchConfig(configId)
        }
        function onConfigImported(configId) {
            root.currentConfigId = configId
            root.configStatusMessage = I18n.t("配置已导入", "Config imported")
            configStatusTimer.restart()
            ObserverClient.refreshProfiles()
            ObserverClient.fetchConfig(configId)
        }
        function onConfigExported(filePath) {
            root.configStatusMessage = I18n.t("配置已导出", "Config exported")
            configStatusTimer.restart()
        }
        function onConfigActionFailed(message) {
            root.configStatusMessage = message || ObserverClient.lastError
            configStatusTimer.restart()
        }
    }

    Timer {
        id: autoReadyTimer
        interval: 180
        repeat: false
        onTriggered: {
            if (!root.editedProfile || Object.keys(root.editedProfile).length === 0)
                return
            root._validatedRevision = root.profileRevision
            ObserverClient.validateProfile(root.editedProfile)
        }
    }

    Timer {
        id: configStatusTimer
        interval: 3200
        repeat: false
        onTriggered: root.configStatusMessage = ""
    }

    function _scheduleAutoReady() {
        autoReadyTimer.restart()
    }

    function _loadProfileItem(item) {
        if (!item)
            return
        root.editedProfile = ({})
        root.selectedSeatId = ""
        setupModeControl.resetToFake()
        if (item.source === "config") {
            root.currentConfigId = item.id || ""
            ObserverClient.fetchConfig(root.currentConfigId)
        } else {
            root.currentConfigId = ""
            ObserverClient.fetchProfile(item.name)
        }
    }

    function _selectProfileItemByConfigId(configId) {
        for (var i = 0; i < ObserverClient.profileItems.length; i++) {
            var item = ObserverClient.profileItems[i]
            if (item.source === "config" && item.id === configId) {
                profilePicker.currentIndex = i
                return
            }
        }
    }

    function _currentDisplayName() {
        if (root.currentConfigId) {
            for (var i = 0; i < ObserverClient.profileItems.length; i++) {
                var item = ObserverClient.profileItems[i]
                if (item.source === "config" && item.id === root.currentConfigId)
                    return item.display_name || item.name || root.currentConfigId
            }
        }
        if (root.editedProfile && root.editedProfile.name)
            return root.editedProfile.name
        return I18n.t("新配置", "New config")
    }

    function _openSaveDialog() {
        saveConfigNameField.text = root._currentDisplayName()
        saveConfigDialog.open()
    }

    function _openExportDialog() {
        if (!root.editedProfile || Object.keys(root.editedProfile).length === 0) {
            root.configStatusMessage = I18n.t("没有可导出的配置", "No config to export")
            configStatusTimer.restart()
            return
        }
        exportConfigDialog.open()
    }

    function _specFor(pid) {
        var specs = (ObserverClient.profileSchema
                     && ObserverClient.profileSchema.provider_specs) || []
        for (var i = 0; i < specs.length; i++)
            if (specs[i].id === pid) return specs[i]
        return null
    }

    function engineLabel(p) {
        if (p === "fake_deterministic")
            return I18n.t("试玩引擎", "Trial engine")
        var spec = _specFor(p)
        if (spec && spec.label) return spec.label
        return p || I18n.t("未配置", "Unset")
    }

    function roleLabel(role) {
        switch (("" + role).toLowerCase()) {
        case "werewolf": return I18n.t("狼人", "Werewolf")
        case "seer": return I18n.t("预言家", "Seer")
        case "witch": return I18n.t("女巫", "Witch")
        case "villager": return I18n.t("村民", "Villager")
        case "guard": return I18n.t("守卫", "Guard")
        case "hunter": return I18n.t("猎人", "Hunter")
        default: return Theme.humanizeRole(role)
        }
    }

    function seatNumber(seatId) {
        var m = ("" + seatId).match(/\d+/)
        return m ? m[0] + I18n.t("号", "") : seatId
    }

    function effective(seatId) {
        var role = root.seatRoles[seatId] || ""
        var def = (root.editedProfile.role_defaults && root.editedProfile.role_defaults[role]) || {}
        var ov = (root.editedProfile.seat_overrides && root.editedProfile.seat_overrides[seatId]) || {}
        return {
            player_id: seatId, role: role, team: root.roleTeams[role] || "",
            provider: ov.provider !== undefined ? ov.provider : def.provider,
            model: ov.model !== undefined ? ov.model : def.model,
            strategy: ov.strategy !== undefined ? ov.strategy : def.strategy,
            prompt: ov.prompt !== undefined ? ov.prompt : (def.prompt || ""),
            temperature: ov.temperature !== undefined ? ov.temperature : def.temperature,
            max_tokens: ov.max_tokens !== undefined ? ov.max_tokens : def.max_tokens
        }
    }

    function _providerConfigured(p) {
        if (!p)
            return false
        if (p === "fake_deterministic")
            return true
        return (root._credRev, CredentialStore.configuredProviders()).indexOf(p) >= 0
    }

    function seatStateKind(eff) {
        if (!eff || !eff.provider)
            return "empty"
        if (!root._providerConfigured(eff.provider) || !eff.model || !eff.prompt)
            return "missing"
        return "ready"
    }

    function seatStateText(eff) {
        var kind = seatStateKind(eff)
        if (kind === "ready")
            return I18n.t("已就绪", "Ready")
        if (kind === "missing")
            return I18n.t("待补全", "Needs details")
        return I18n.t("未配置", "Unset")
    }

    function _arrangedCount() {
        var n = 0
        for (var i = 0; i < seatIds.length; i++) {
            if (seatStateKind(effective(seatIds[i])) === "ready")
                n++
        }
        return n
    }

    function statusLine() {
        if (configStatusMessage)
            return configStatusMessage
        if (arrangedCount === seatTotal && autoReady)
            return I18n.t("所有角色已就绪，可以开始对局", "All seats are ready. You can begin.")
        if (arrangedCount === seatTotal)
            return I18n.t("正在整理自动准备状态", "Preparing automatically...")
        return I18n.t("点选待补全角色，补齐 AI 引擎、模型或角色指令", "Select incomplete seats to fill engine, model, or role instructions.")
    }

    function applyEdit(seatId, field, value) {
        var eff = effective(seatId)
        if (eff[field] === value) return
        var frag = { provider: eff.provider, model: eff.model, strategy: eff.strategy, prompt: eff.prompt }
        if (eff.temperature !== undefined) frag.temperature = eff.temperature
        if (eff.max_tokens !== undefined) frag.max_tokens = eff.max_tokens
        frag[field] = value
        if (field === "provider") {
            var live = ObserverClient.providerModels[value] || []
            var spec = root._specFor(value)
            var stat = (spec && spec.default_models) ? spec.default_models : []
            var models = live.length > 0 ? live : stat
            frag.model = models.length > 0 ? models[0] : ""
        }
        var ep = JSON.parse(JSON.stringify(root.editedProfile))
        if (!ep.seat_overrides) ep.seat_overrides = ({})
        if (root._matchesRoleDefault(seatId, frag))
            delete ep.seat_overrides[seatId]
        else
            ep.seat_overrides[seatId] = frag
        root.editedProfile = ep
        root.profileRevision++
        root._validatedRevision = -1
        root._scheduleAutoReady()
    }

    function _norm(v) { return (v === undefined || v === null || v === "") ? "" : v }

    function _matchesRoleDefault(seatId, frag) {
        var role = root.seatRoles[seatId] || ""
        var def = (root.editedProfile.role_defaults && root.editedProfile.role_defaults[role]) || {}
        var keys = ["provider", "model", "strategy", "prompt", "temperature", "max_tokens"]
        for (var i = 0; i < keys.length; i++)
            if (root._norm(frag[keys[i]]) !== root._norm(def[keys[i]]))
                return false
        return true
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.phase.day.bg }
            GradientStop { position: 1.0; color: Theme.warm.canvas }
        }
    }

    Image {
        anchors.fill: parent
        source: Illustrations.setupRoom
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        visible: status === Image.Ready
    }

    Rectangle {
        anchors.fill: parent
        // Warm cream veil, not white — lets the arch window / flora / daylight
        // of setup-room.png breathe through while still lifting legibility.
        color: Theme.withAlpha(Theme.phase.day.bg, 0.06)
    }

    Row {
        id: pageHeader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.space.xxl
        height: 78
        spacing: Theme.space.lg

        Rectangle {
            id: backButton
            objectName: "setupBackButton"
            width: 112
            height: 46
            radius: Theme.radius.pill
            color: backHover.hovered ? Theme.warm.surfaceRaised : Theme.withAlpha(Theme.warm.surfaceRaised, 0.78)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.42)
            anchors.verticalCenter: parent.verticalCenter
            Text {
                anchors.centerIn: parent
                text: I18n.t("← 返回", "← Back")
                color: Theme.parchment.ink
                font.family: Theme.fontFamilies.cjkSerif
                font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.bodyLg
                font.weight: Theme.weight.semibold
            }
            HoverHandler { id: backHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.StackView.view.parent.navigateHome() }
        }

        Column {
            width: 156
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Text {
                text: I18n.t("开局准备室", "Match Ready Room")
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.cjkSerif
                font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.titleLg
                font.weight: Theme.weight.bold
                elide: Text.ElideRight
            }
            Text {
                text: I18n.t("AI 角色编排", "AI Role Direction")
                color: Theme.warm.primaryActive
                font.family: Theme.fontFamilies.cjkSans
                font.contextFontMerging: true
                font.pixelSize: Theme.size.caption
                font.weight: Theme.weight.semibold
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: toolTray
            height: 72
            width: parent.width - backButton.width - 156 - pageHeader.spacing * 2
            anchors.verticalCenter: parent.verticalCenter
            radius: 18
            color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.76)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.44)

            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: Illustrations.texParchment
                fillMode: Image.Tile
                opacity: 0.14
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: parent.radius - 1
                color: "transparent"
                border.width: 1
                border.color: Qt.rgba(1, 248 / 255, 235 / 255, 0.32)
            }

            Row {
                anchors.fill: parent
                anchors.leftMargin: Theme.space.xl
                anchors.rightMargin: Theme.space.xl
                anchors.topMargin: Theme.space.sm
                anchors.bottomMargin: Theme.space.sm
                spacing: Theme.space.lg

                ToolField {
                    label: I18n.t("对局配置", "Match config")
                    width: 218
                    ParchmentComboBox {
                        id: profilePicker
                        objectName: "setupProfilePicker"
                        anchors.fill: parent
                        model: ObserverClient.profileItems
                        textRole: "name"
                        compact: true
                        controlRadius: 12
                        surfaceOpacity: 0.70
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        onActivated: {
                            setupModeControl.resetToFake()
                            root._loadProfileItem(ObserverClient.profileItems[currentIndex])
                        }
                    }
                }

                ToolField {
                    label: I18n.t("当前剧本", "Current script")
                    width: 232
                    ParchmentComboBox {
                        id: scriptPicker
                        objectName: "setupScriptPicker"
                        anchors.fill: parent
                        model: [root.currentScriptLabel]
                        enabled: false
                        compact: true
                        controlRadius: 12
                        surfaceOpacity: 0.62
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                    }
                }

                ModeControl {
                    id: setupModeControl
                    objectName: "setupModeControl"
                    compact: true
                    onLight: true
                    anchors.verticalCenter: parent.verticalCenter
                }

                Item {
                    width: parent.width
                            - 218 - 232 - setupModeControl.width
                            - pageHeader.spacing * 4 + Theme.space.lg
                    height: parent.height
                    anchors.verticalCenter: parent.verticalCenter
                    Button {
                        id: saveLink
                        objectName: "setupSaveConfigButton"
                        width: saveLinkLabel.implicitWidth + Theme.space.xl
                        height: 44
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.space.lg
                        anchors.verticalCenter: parent.verticalCenter
                        enabled: true
                        hoverEnabled: true
                        onClicked: configActionMenu.popup(saveLink, 0, saveLink.height)
                        background: Rectangle {
                            radius: 13
                            color: saveLink.hovered ? Theme.withAlpha(Theme.parchment.parchmentSoft, 0.88)
                                                    : Theme.withAlpha(Theme.parchment.parchment, 0.76)
                            border.width: 1
                            border.color: saveLink.hovered ? Theme.withAlpha(Theme.parchment.goldLine, 0.48)
                                                           : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.34)
                            Image {
                                anchors.fill: parent
                                anchors.margins: 1
                                source: Illustrations.texParchment
                                fillMode: Image.Tile
                                opacity: 0.10
                            }
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                height: 1
                                color: Qt.rgba(1, 248 / 255, 234 / 255, 0.36)
                            }
                        }
                        contentItem: Text {
                            id: saveLinkLabel
                            text: I18n.t("另存为配置 ▼", "Save as config ▼")
                            color: Theme.parchment.ink
                            font.family: Theme.fontFamilies.cjkSans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                            font.weight: Theme.weight.semibold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: I18n.t("另存为配置", "Save as config")
                        ParchmentPopupMenu {
                            id: configActionMenu
                            objectName: "setupConfigActionMenu"
                            actions: [
                                { "key": "save", "objectName": "setupSaveConfigMenuItem",
                                  "text": I18n.t("另存为配置", "Save as config") },
                                { "key": "export", "objectName": "setupExportConfigButton",
                                  "text": I18n.t("导出配置", "Export config") },
                                { "key": "import", "objectName": "setupImportConfigButton",
                                  "text": I18n.t("导入配置", "Import config") }
                            ]
                            onTriggered: function(key) {
                                if (key === "save")
                                    root._openSaveDialog()
                                else if (key === "export")
                                    root._openExportDialog()
                                else if (key === "import")
                                    importConfigDialog.open()
                            }
                        }
                    }
                }
            }
        }
    }

    EmptyState {
        anchors.centerIn: parent
        visible: ObserverClient.profileItems.length === 0
        title: I18n.t("没有可用对局配置", "No match configs")
        subtitle: I18n.t("本地服务器暂未返回可编辑配置。", "The local server has not returned an editable config.")
    }

    Item {
        id: stage
        anchors.top: pageHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomBar.top
        anchors.topMargin: Theme.space.md
        anchors.leftMargin: Theme.space.xxl
        anchors.rightMargin: Theme.space.xxl
        anchors.bottomMargin: Theme.space.lg
        visible: ObserverClient.profileItems.length > 0

        Rectangle {
            id: boardPaper
            // NOTE: deliberately NO left anchor — `anchors.left` + `x` conflict
            // and the anchor wins, which pinned the board to the left in the
            // default (overview) state. Pure positional `x` lets the overview
            // center and the detail state slide left + shrink.
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            height: parent.height
            width: root.detailOpen ? Math.min(820, parent.width - detailPanel.width - Theme.space.lg)
                                   : Math.min(1040, parent.width)
            radius: 18
            color: Qt.rgba(248 / 255, 238 / 255, 220 / 255, 0.34)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.46)
            x: root.detailOpen ? 0 : (parent.width - width) / 2
            Behavior on x { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutCubic } }
            Behavior on width { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutCubic } }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: parent.radius - 1
                color: "transparent"
                border.width: 1
                border.color: Qt.rgba(1, 248 / 255, 234 / 255, 0.58)
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: parent.radius
                anchors.rightMargin: parent.radius
                height: 1
                color: Qt.rgba(1, 250 / 255, 240 / 255, 0.62)
            }
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.topMargin: parent.radius
                anchors.bottomMargin: parent.radius
                width: 1
                color: Qt.rgba(1, 250 / 255, 240 / 255, 0.50)
            }

            Grid {
                id: setupRoleCards
                objectName: "setupRoleCards"
                anchors.centerIn: parent
                columns: 3
                rowSpacing: root.detailOpen ? Theme.space.lg : Theme.space.xxl
                columnSpacing: root.detailOpen ? Theme.space.xl : Theme.space.huge

                Repeater {
                    model: root.seatIds
                    delegate: SetupRoleCard {
                        required property var modelData
                        property var eff: root.effective(modelData)
                        width: root.detailOpen ? 166 : 192
                        height: root.detailOpen ? 232 : 262
                        seatLabel: root.seatNumber(modelData)
                        roleKey: eff.role
                        roleLabel: root.roleLabel(eff.role)
                        engineLabel: root.engineLabel(eff.provider)
                        modelLabel: eff.model || I18n.t("未配置", "Unset")
                        stateKind: root.seatStateKind(eff)
                        stateLabel: root.seatStateText(eff)
                        selected: root.selectedSeatId === modelData
                        opacity: root.detailOpen && root.selectedSeatId !== modelData ? 0.82 : 1.0
                        onActivated: root.selectedSeatId = modelData
                    }
                }
            }
        }

        SeatEditorPanel {
            id: detailPanel
            objectName: "setupDetailPanel"
            width: Math.min(360, parent.width * 0.30)
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            visible: root.detailOpen
            opacity: root.detailOpen ? 1 : 0
            x: root.detailOpen ? parent.width - width : parent.width + Theme.space.xl
            seat: root.detailOpen ? root.effective(root.selectedSeatId) : ({})
            config: root.detailOpen ? root.effective(root.selectedSeatId) : ({})
            schema: ObserverClient.profileSchema
            overridden: root.selectedSeatId !== "" && root.editedProfile.seat_overrides
                        && root.editedProfile.seat_overrides[root.selectedSeatId] !== undefined
            statusText: root.detailOpen ? root.seatStateText(root.effective(root.selectedSeatId)) : ""
            statusKind: root.detailOpen ? root.seatStateKind(root.effective(root.selectedSeatId)) : "empty"
            onEdited: function(field, value) { root.applyEdit(root.selectedSeatId, field, value) }
            onClosed: root.selectedSeatId = ""
            onRequestProviderSettings: root.StackView.view.parent.navigateProviderSettings()
            Behavior on opacity { NumberAnimation { duration: Theme.motion.base; easing.type: Easing.OutCubic } }
        }
    }

    // Floating HUD-style status bar — rounded parchment pill lifted off the
    // board, not a full-bleed footer.
    Rectangle {
        // Soft warm shadow under the floating bar.
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomBar.bottom
        anchors.leftMargin: Theme.space.xxl
        anchors.rightMargin: Theme.space.xxl
        anchors.bottomMargin: -8
        height: bottomBar.height
        radius: bottomBar.radius
        color: Qt.rgba(48 / 255, 32 / 255, 18 / 255, 0.18)
        visible: bottomBar.visible
        z: bottomBar.z - 1
    }

    Rectangle {
        id: bottomBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.space.xxxl
        anchors.rightMargin: Theme.space.xxxl
        anchors.bottomMargin: Theme.space.xxl
        height: 72
        radius: 20
        color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.90)
        border.width: 1
        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.56)
        visible: ObserverClient.profileItems.length > 0

        Image {
            anchors.fill: parent
            anchors.margins: 2
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.18
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 248 / 255, 234 / 255, 0.42)
        }

        Row {
            anchors.left: parent.left
            anchors.leftMargin: Theme.space.xl
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.md

            Rectangle {
                width: 42
                height: 42
                radius: 21
                color: root.autoReady ? Theme.withAlpha(Theme.parchment.alive, 0.18)
                                      : Theme.withAlpha(Theme.parchment.goldLine, 0.18)
                border.width: 1
                border.color: root.autoReady ? Theme.withAlpha(Theme.parchment.alive, 0.72)
                                             : Theme.withAlpha(Theme.parchment.goldLine, 0.62)
                Rectangle {
                    anchors.centerIn: parent
                    width: 28
                    height: 28
                    radius: 14
                    color: Theme.withAlpha(Theme.parchment.parchment, 0.42)
                    border.width: 1
                    border.color: Qt.rgba(1, 246 / 255, 220 / 255, 0.38)
                }
                Text {
                    anchors.centerIn: parent
                    text: root.autoReady ? "✓" : "…"
                    color: root.autoReady ? Theme.parchment.alive : Theme.parchment.goldLineSoft
                    font.family: Theme.fontFamilies.cjkSans
                    font.contextFontMerging: true
                    font.pixelSize: 22
                    font.weight: Theme.weight.bold
                }
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3
                Row {
                    spacing: Theme.space.sm
                    Text {
                        text: I18n.t("准备进度", "Ready")
                        color: Theme.parchment.ink
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: Theme.warmSize.bodyLg
                    }
                    Text {
                        text: root.arrangedCount + " / " + root.seatTotal
                        color: Theme.warm.primaryActive
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: 22
                        font.weight: Theme.weight.bold
                    }
                }
                Text {
                    text: root.statusLine()
                    color: Theme.parchment.inkSoft
                    font.family: Theme.fontFamilies.cjkSans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                }
            }
        }

        // Begin-match button as a matte terracotta seal: tactile, but restrained
        // enough to stay in the parchment tabletop language.
        Item {
            id: setupContinueButton
            objectName: "setupContinueButton"
            width: 210
            height: 50
            anchors.right: parent.right
            anchors.rightMargin: Theme.space.lg
            anchors.verticalCenter: parent.verticalCenter
            opacity: root.launchEnabled ? 1.0 : 0.5

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 5
                anchors.leftMargin: 2
                anchors.rightMargin: -2
                anchors.bottomMargin: -5
                radius: 14
                color: root.launchEnabled ? Qt.rgba(48 / 255, 32 / 255, 18 / 255, 0.20) : "transparent"
            }
            Rectangle {
                id: beginFace
                anchors.fill: parent
                radius: 14
                border.width: 1
                border.color: Qt.rgba(129 / 255, 73 / 255, 49 / 255, 0.62)
                scale: beginTap.pressed ? 0.97 : 1.0
                Behavior on scale { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutQuad } }
                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: root.launchEnabled
                               ? (beginHover.hovered ? "#c6785f" : "#c8735b")
                               : Theme.warm.primaryDisabled
                    }
                    GradientStop {
                        position: 1.0
                        color: root.launchEnabled
                               ? (beginHover.hovered ? "#ae5f48" : "#b7654c")
                               : Theme.warm.primaryDisabled
                    }
                }
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: 18
                    anchors.rightMargin: 18
                    height: 1
                    color: Qt.rgba(1, 246 / 255, 228 / 255, root.launchEnabled ? 0.26 : 0.14)
                }
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 18
                    anchors.rightMargin: 18
                    height: 1
                    color: Qt.rgba(91 / 255, 45 / 255, 30 / 255, root.launchEnabled ? 0.26 : 0.12)
                }
                Row {
                    anchors.centerIn: parent
                    spacing: Theme.space.sm
                    Text {
                        text: I18n.t("开始对局", "Begin Match")
                        color: Theme.warm.textOnPrimary
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.warmSize.bodyLg
                        font.weight: Theme.weight.bold
                    }
                    Text {
                        text: "→"
                        color: Theme.warm.textOnPrimary
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.warmSize.bodyLg
                        font.weight: Theme.weight.bold
                    }
                }
            }
            HoverHandler { id: beginHover; enabled: root.launchEnabled; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                id: beginTap
                enabled: root.launchEnabled
                onTapped: ObserverClient.launchFromProfile(root.editedProfile, setupModeControl.resolvedMode)
            }
        }
    }

    component ToolField: Rectangle {
        default property alias content: controlSlot.data
        required property string label
        height: 56
        radius: 15
        color: Theme.withAlpha(Theme.parchment.parchment, 0.66)
        border.width: 1
        border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.44)
        Image {
            anchors.fill: parent
            anchors.margins: 1
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.10
        }
        Text {
            id: fieldLabel
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 12
            anchors.topMargin: 6
            text: label
            color: Theme.withAlpha(Theme.parchment.mutedInk, 0.82)
            font.family: Theme.fontFamilies.cjkSerif
            font.contextFontMerging: true
            font.pixelSize: Theme.size.micro
            font.weight: Theme.weight.semibold
        }
        Item {
            id: controlSlot
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.bottomMargin: 6
            height: 30
        }
    }
}
