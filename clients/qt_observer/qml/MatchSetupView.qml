import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "matchSetupView"

    property string selectedSeatId: ""
    property var editedProfile: ({})
    property int profileRevision: 0

    readonly property var seatRoles: ObserverClient.profileSchema && ObserverClient.profileSchema.seat_roles
                                      ? ObserverClient.profileSchema.seat_roles : ({})
    readonly property var roleTeams: ObserverClient.profileSchema && ObserverClient.profileSchema.role_teams
                                     ? ObserverClient.profileSchema.role_teams : ({})
    readonly property var seatIds: ObserverClient.profileSchema && ObserverClient.profileSchema.seat_ids
                                   ? ObserverClient.profileSchema.seat_ids : ["p1","p2","p3","p4","p5","p6"]
    readonly property bool launchEnabled: ObserverClient.profileValidation
        && ObserverClient.profileValidation.valid === true
        && root._validatedRevision === root.profileRevision
    property int _validatedRevision: -1
    property bool _initialLoadDone: false
    readonly property int cardWidth: 168

    // Step 2: credential sync state machine
    property bool _credSynced: false
    property string _credSyncError: ""
    property int _credRev: 0
    Connections {
        target: CredentialStore
        function onSyncSucceeded(p) { if (p === "deepseek") { root._credSynced = true; root._credSyncError = "" } }
        function onSyncFailed(p, reason) { if (p === "deepseek") { root._credSynced = false; root._credSyncError = reason } }
        function onCredentialChanged(p) { if (p === "deepseek") { root._credSynced = false; root._credSyncError = ""; root._credRev++ } }
    }
    readonly property string _credStatus: {
        var hasLocal = CredentialStore.hasCredential("deepseek")
        var envAvail = ObserverClient.liveAvailable && !hasLocal   // server reports available w/o local key => env
        if (root._credSyncError !== "") return I18n.t("本地已保存，同步失败，无法启动真实 AI", "Saved locally, sync failed — cannot run live")
        if (hasLocal && root._credSynced) return I18n.t("已配置凭证（本地）", "Credential configured (local)")
        if (hasLocal && !root._credSynced) return I18n.t("本地已保存，尚未同步到 server", "Saved locally, not yet synced")
        if (envAvail) return I18n.t("使用服务器环境凭证", "Using server env credential")
        return I18n.t("未配置", "Not configured")
    }

    Component.onCompleted: {
        ObserverClient.refreshProfileSchema()
        ObserverClient.refreshProfiles()
        // Learn the live posture BEFORE launch (no "guess, click, get 403").
        ObserverClient.refreshCapabilities()
    }

    // C3: any profile/seat change or live becoming unavailable disarms the FSM
    // through the SINGLE resetToFake() entry — the parent never mutates state.
    onSelectedSeatIdChanged: setupModeControl.resetToFake()

    // Load the first profile once the list arrives.
    Connections {
        target: ObserverClient
        function onProfileItemsChanged() {
            // One-shot initial auto-load of the first profile; keyed on a
            // dedicated flag so it never competes with an explicit picker-driven
            // fetch (which momentarily clears editedProfile).
            if (!root._initialLoadDone && ObserverClient.profileItems.length > 0) {
                root._initialLoadDone = true
                ObserverClient.fetchProfile(ObserverClient.profileItems[0].name)
            }
        }
        function onLoadedProfileChanged() {
            root.editedProfile = JSON.parse(JSON.stringify(ObserverClient.loadedProfile))
            if (!root.editedProfile.seat_overrides) root.editedProfile.seat_overrides = ({})
            root.profileRevision++
            root._validatedRevision = -1
            if (!root.selectedSeatId && root.seatIds.length > 0) root.selectedSeatId = root.seatIds[0]
            setupModeControl.resetToFake()   // C3: a new profile disarms live
        }
        // C3: live becoming unavailable must disarm any armed/confirmed state.
        function onCapabilitiesChanged() {
            if (!ObserverClient.liveAvailable) setupModeControl.resetToFake()
        }
        function onLaunchSucceeded() { root.StackView.view.parent.navigatePreflight() }
    }

    // Field-level effective config for a seat.
    function effective(seatId) {
        var role = root.seatRoles[seatId] || ""
        var def = (root.editedProfile.role_defaults && root.editedProfile.role_defaults[role]) || {}
        var ov = (root.editedProfile.seat_overrides && root.editedProfile.seat_overrides[seatId]) || {}
        return {
            player_id: seatId, role: role, team: root.roleTeams[role] || "",
            provider: ov.provider !== undefined ? ov.provider : def.provider,
            model: ov.model !== undefined ? ov.model : def.model,
            strategy: ov.strategy !== undefined ? ov.strategy : def.strategy,
            prompt: ov.prompt !== undefined ? ov.prompt : (def.prompt || "")
        }
    }

    // Materialize a full coherent override fragment on edit.
    function applyEdit(seatId, field, value) {
        var eff = effective(seatId)
        if (eff[field] === value) return   // no-op: ignore init/seat-switch re-binds; don't bump revision
        var frag = { provider: eff.provider, model: eff.model, strategy: eff.strategy, prompt: eff.prompt }
        frag[field] = value
        if (field === "provider") {
            var models = (ObserverClient.profileSchema.models || {})[value] || []
            frag.model = models.length > 0 ? models[0] : frag.model
        }
        var ep = JSON.parse(JSON.stringify(root.editedProfile))
        if (!ep.seat_overrides) ep.seat_overrides = ({})
        ep.seat_overrides[seatId] = frag
        root.editedProfile = ep
        root.profileRevision++          // any edit invalidates a prior verdict
    }

    Rectangle { anchors.fill: parent; color: Theme.color.bgBase }

    // -------------------------------------------------------------- Header row
    Column {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.xxxl
        anchors.leftMargin: Theme.layout.pageMargin
        anchors.rightMargin: Theme.layout.pageMargin
        spacing: Theme.space.md

        // Intent (setup control), NOT executed truth.  The segmented fake/live
        // arming control replaces the old amber deterministic-mock banner.
        // Fake stays the unconditional default; live arms in two deliberate
        // clicks and is available only when the server's capabilities say so.
        // (Executed truth lives in the global AppShell DataSourceChip, driven by
        // run-detail execution_mode — never local files.)
        ModeControl {
            id: setupModeControl
            objectName: "setupModeControl"
        }

        // Step 1: Inline credential panel for DeepSeek API key
        Column {
            spacing: Theme.space.sm
            width: parent.width

            Row {
                spacing: Theme.space.sm
                width: parent.width

                TextField {
                    id: credField
                    objectName: "setupCredentialField"
                    echoMode: TextInput.Password
                    width: parent.width - saveCredBtn.width - clearCredBtn.width - Theme.space.sm * 2
                    placeholderText: (root._credRev, CredentialStore.hasCredential("deepseek"))
                        ? I18n.t("已保存：" + CredentialStore.maskedCredential("deepseek"),
                                 "Saved: " + CredentialStore.maskedCredential("deepseek"))
                        : I18n.t("输入 DeepSeek API Key", "Enter DeepSeek API key")
                }

                AppButton {
                    id: saveCredBtn
                    objectName: "setupCredentialSave"
                    text: I18n.t("保存", "Save")
                    variant: "secondary"
                    onClicked: {
                        CredentialStore.saveCredential("deepseek", credField.text)
                        CredentialStore.syncCredentialToServer("deepseek")
                        credField.clear()
                    }
                }

                AppButton {
                    id: clearCredBtn
                    objectName: "setupCredentialClear"
                    text: I18n.t("清除", "Clear")
                    variant: "ghost"
                    onClicked: CredentialStore.clearCredential("deepseek")
                }
            }

            Text {
                objectName: "setupCredentialStatus"
                text: root._credStatus
                color: root._credSyncError !== "" ? Theme.color.danger : Theme.color.textMuted
                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
        }

        Text {
            text: I18n.t("对局配置", "Match Setup")
            color: Theme.color.text
            font.family: Theme.font.display; font.pixelSize: Theme.size.h1; font.weight: Theme.weight.bold
        }

        Row {
            spacing: Theme.space.md
            ComboBox {
                id: profilePicker
                objectName: "setupProfilePicker"
                width: 280
                model: ObserverClient.profileItems
                textRole: "name"
                onActivated: {
                    root.editedProfile = ({})
                    root.selectedSeatId = ""
                    setupModeControl.resetToFake()   // C3: switching profile disarms live
                    ObserverClient.fetchProfile(ObserverClient.profileItems[currentIndex].name)
                }
            }
            AppButton {
                id: validateButton
                objectName: "setupValidateButton"
                text: I18n.t("校验", "Validate")
                variant: "secondary"
                onClicked: {
                    root._validatedRevision = root.profileRevision
                    ObserverClient.validateProfile(root.editedProfile)
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: ObserverClient.profileValidation && ObserverClient.profileValidation.errors
                         && ObserverClient.profileValidation.errors.length > 0
                text: visible ? ObserverClient.profileValidation.errors[0] : ""
                color: Theme.color.danger
                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
        }
    }

    EmptyState {
        anchors.centerIn: parent
        visible: ObserverClient.profileItems.length === 0
        title: I18n.t("没有可用档案", "No profiles")
        subtitle: I18n.t("在服务器 profiles/ 目录放入一个 JSON 档案。",
                         "Drop a JSON into the server's profiles/ dir.")
    }

    // ----------------------------------------------------- Master (seat grid)
    Flickable {
        id: master
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.bottom: actionBar.top
        anchors.topMargin: Theme.space.xl
        anchors.leftMargin: Theme.layout.pageMargin
        width: root.cardWidth * 2 + Theme.space.lg
        contentHeight: setupRoleCards.height
        clip: true
        visible: ObserverClient.profileItems.length > 0

        Grid {
            id: setupRoleCards
            objectName: "setupRoleCards"
            columns: 2
            spacing: Theme.space.lg
            Repeater {
                model: root.seatIds
                // RoleCard verified public API (qml/components/RoleCard.qml):
                //   seatId, roleName, displayRole, displayTeam, visibilityLabel,
                //   aiLabel, statusText, accentText, selected. Use ONLY these.
                delegate: RoleCard {
                    property var eff: root.effective(modelData)
                    seatId: modelData
                    roleName: eff.role
                    displayRole: eff.role
                    displayTeam: eff.team || ""
                    aiLabel: (eff.provider || "") + " · " + (eff.model || "")
                    selected: root.selectedSeatId === modelData
                    width: 168
                    height: 168
                    MouseArea { anchors.fill: parent; onClicked: root.selectedSeatId = modelData }
                }
            }
        }
    }

    // ----------------------------------------------------- Detail (seat editor)
    SeatEditorPanel {
        id: detail
        anchors.top: header.bottom
        anchors.right: parent.right
        anchors.bottom: actionBar.top
        anchors.left: master.right
        anchors.topMargin: Theme.space.xl
        anchors.rightMargin: Theme.layout.pageMargin
        anchors.leftMargin: Theme.space.xl
        anchors.bottomMargin: Theme.space.lg
        visible: root.selectedSeatId !== "" && ObserverClient.profileItems.length > 0
        seat: root.selectedSeatId ? root.effective(root.selectedSeatId) : ({})
        config: root.selectedSeatId ? root.effective(root.selectedSeatId) : ({})
        schema: ObserverClient.profileSchema
        onEdited: function(field, value) { root.applyEdit(root.selectedSeatId, field, value) }
    }

    // ------------------------------------------------------ Bottom action bar
    Rectangle {
        id: actionBar
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: Theme.layout.actionBarHeight
        color: Theme.color.surface
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 1; color: Theme.color.border }

        AppButton {
            text: I18n.t("返回", "Back")
            variant: "ghost"
            anchors.left: parent.left; anchors.leftMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.StackView.view.parent.navigateHome()
        }
        AppButton {
            id: setupContinueButton
            objectName: "setupContinueButton"
            text: I18n.t("启动", "Launch")
            variant: "primary"
            width: 200
            enabled: root.launchEnabled
            anchors.right: parent.right; anchors.rightMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            // Advances to Preflight only via onLaunchSucceeded (202 + currentRunId).
            // C2: pass an EXPLICIT resolved mode ("fake"|"live") — "live" only
            // when the arming FSM is live_confirmed; never a C++ default arg.
            // Step 3: no-silent-env-fallback guard (spec §3.7):
            // if a local key exists but hasn't synced, block launch; never silently fall back to server env.
            onClicked: {
                if (setupModeControl.resolvedMode === "live"
                        && CredentialStore.hasCredential("deepseek")
                        && !root._credSynced) {
                    CredentialStore.syncCredentialToServer("deepseek")  // retry sync; status updates via signals
                    return
                }
                ObserverClient.launchFromProfile(root.editedProfile, setupModeControl.resolvedMode)
            }
        }
    }
}
