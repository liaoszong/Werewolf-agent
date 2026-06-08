import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Match-setup "scheduling sandbox" (P2-B Q2). The six seats sit as a centred
// board of RoleCards; clicking one scales the board down + slides it left, dims
// the others, highlights the chosen seat in coral, and slides a per-seat
// inspector in from the right. Credentials now live entirely on the provider
// settings page (reached via the global top-bar gear) — this page only assigns
// already-configured providers/models to seats.
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
    readonly property int cardWidth: 156
    readonly property int cardHeight: 176

    Component.onCompleted: {
        ObserverClient.refreshProfileSchema()
        ObserverClient.refreshProfiles()
        // Learn the live posture BEFORE launch (no "guess, click, get 403").
        ObserverClient.refreshCapabilities()
        // Q2: re-sync every locally-configured credential into the server session
        // so the inspector's live model fetch (and live launch) authenticate even
        // after a server restart — credentials live only in the client + server RAM.
        var configured = CredentialStore.configuredProviders()
        for (var i = 0; i < configured.length; i++)
            CredentialStore.syncCredentialToServer(configured[i])
    }

    // C3: any seat (de)selection disarms the live FSM through the single entry.
    onSelectedSeatIdChanged: setupModeControl.resetToFake()

    Connections {
        target: ObserverClient
        function onProfileItemsChanged() {
            // One-shot initial auto-load of the first profile.
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
            root.selectedSeatId = ""          // Q2: a fresh profile opens in the sandbox
            setupModeControl.resetToFake()     // C3: a new profile disarms live
        }
        // C3: live becoming unavailable must disarm any armed/confirmed state.
        function onCapabilitiesChanged() {
            if (!ObserverClient.liveAvailable) setupModeControl.resetToFake()
        }
        function onLaunchSucceeded() { root.StackView.view.parent.navigatePreflight() }
    }

    // Lookup a provider spec from the server registry (provider_specs in profileSchema).
    function _specFor(pid) {
        var specs = (ObserverClient.profileSchema
                     && ObserverClient.profileSchema.provider_specs) || []
        for (var i = 0; i < specs.length; i++)
            if (specs[i].id === pid) return specs[i]
        return null
    }

    // Friendly provider label for the seat card's AI line (mirrors the inspector's
    // SeatEditorPanel._providerLabel so the board and inspector agree).
    function providerLabel(p) {
        if (p === "fake_deterministic") return I18n.t("模拟(无需 Key)", "Simulation (no key)")
        var spec = _specFor(p)
        if (spec && spec.label) return spec.label
        return p || I18n.t("未设", "unset")
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
            prompt: ov.prompt !== undefined ? ov.prompt : (def.prompt || ""),
            // Q3 per-seat sampling knobs — may be undefined (unset → provider default).
            temperature: ov.temperature !== undefined ? ov.temperature : def.temperature,
            max_tokens: ov.max_tokens !== undefined ? ov.max_tokens : def.max_tokens
        }
    }

    // Materialize a full coherent override fragment on edit.
    function applyEdit(seatId, field, value) {
        var eff = effective(seatId)
        if (eff[field] === value) return   // no-op: ignore init/seat-switch re-binds
        var frag = { provider: eff.provider, model: eff.model, strategy: eff.strategy, prompt: eff.prompt }
        // Carry the optional numeric knobs only when already set, so editing another
        // field never invents a temperature/max_tokens the user didn't choose.
        if (eff.temperature !== undefined) frag.temperature = eff.temperature
        if (eff.max_tokens !== undefined) frag.max_tokens = eff.max_tokens
        frag[field] = value
        if (field === "provider") {
            // Seed a model that's valid for the NEW provider, mirroring the
            // inspector's modelList preference (live fetched list first, static
            // schema fallback). Never keep the previous provider's model — that
            // would persist an incoherent {provider, model} pair and launch it.
            // "" when nothing is known yet; the inspector reconciles once the live
            // list arrives, and an empty model fails validation (blocks launch).
            var live = ObserverClient.providerModels[value] || []
            var spec = root._specFor(value)
            var stat = (spec && spec.default_models) ? spec.default_models : []
            var models = live.length > 0 ? live : stat
            frag.model = models.length > 0 ? models[0] : ""
        }
        var ep = JSON.parse(JSON.stringify(root.editedProfile))
        if (!ep.seat_overrides) ep.seat_overrides = ({})
        if (root._matchesRoleDefault(seatId, frag)) {
            // Reverting every field back to the role default — drop the redundant
            // override so the seat reads as inherited (and the inherit/override
            // badge stays honest).
            delete ep.seat_overrides[seatId]
        } else {
            ep.seat_overrides[seatId] = frag
        }
        root.editedProfile = ep
        root.profileRevision++          // any edit invalidates a prior verdict
    }

    // "" / null / undefined all mean "unset" for override comparison; 0 stays 0.
    function _norm(v) { return (v === undefined || v === null || v === "") ? "" : v }

    // Does this fragment equal the seat's role default across every config field?
    function _matchesRoleDefault(seatId, frag) {
        var role = root.seatRoles[seatId] || ""
        var def = (root.editedProfile.role_defaults && root.editedProfile.role_defaults[role]) || {}
        var keys = ["provider", "model", "strategy", "prompt", "temperature", "max_tokens"]
        for (var i = 0; i < keys.length; i++)
            if (root._norm(frag[keys[i]]) !== root._norm(def[keys[i]]))
                return false
        return true
    }

    Rectangle { anchors.fill: parent; color: Theme.color.bgBase }

    // -------------------------------------------------------------- Header
    Column {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.xxxl
        anchors.leftMargin: Theme.layout.pageMargin
        anchors.rightMargin: Theme.layout.pageMargin
        spacing: Theme.space.md

        // Intent (setup control), NOT executed truth — the fake/live arming control.
        ModeControl {
            id: setupModeControl
            objectName: "setupModeControl"
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

    // -------------------------------------------------- Scheduling sandbox
    Item {
        id: board
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: actionBar.top
        anchors.topMargin: Theme.space.xl
        anchors.leftMargin: Theme.layout.pageMargin
        anchors.rightMargin: Theme.layout.pageMargin
        anchors.bottomMargin: Theme.space.lg
        visible: ObserverClient.profileItems.length > 0
        clip: true
        state: root.selectedSeatId !== "" ? "editing" : ""

        // Card board — centred in the sandbox, scaled + shifted left when editing.
        Item {
            id: gridStage
            width: setupRoleCards.width
            height: setupRoleCards.height
            anchors.verticalCenter: parent.verticalCenter
            x: (board.width - width) / 2
            transformOrigin: Item.Left

            Grid {
                id: setupRoleCards
                objectName: "setupRoleCards"
                columns: 3
                spacing: Theme.space.lg
                Repeater {
                    model: root.seatIds
                    // RoleCard public API: seatId, roleName, displayRole, displayTeam,
                    // visibilityLabel, aiLabel, statusText, accentText, selected,
                    // selectedAccent.
                    delegate: RoleCard {
                        required property var modelData
                        property var eff: root.effective(modelData)
                        seatId: modelData
                        roleName: eff.role
                        displayRole: eff.role
                        displayTeam: eff.team || ""
                        aiLabel: root.providerLabel(eff.provider) + " · " + (eff.model || I18n.t("未设","unset"))
                        selected: root.selectedSeatId === modelData
                        selectedAccent: Theme.report.accent   // coral
                        // Non-selected seats dim while a seat is being edited.
                        opacity: (board.state === "editing" && root.selectedSeatId !== modelData) ? 0.4 : 1.0
                        width: root.cardWidth
                        height: root.cardHeight
                        MouseArea { anchors.fill: parent; onClicked: root.selectedSeatId = modelData }
                    }
                }
            }
        }

        // Sandbox hint (only while nothing is selected).
        Text {
            anchors.top: gridStage.bottom
            anchors.topMargin: Theme.space.xl
            anchors.horizontalCenter: board.horizontalCenter
            visible: root.selectedSeatId === ""
            text: I18n.t("点击座位卡进行配置", "Click a seat to configure it")
            color: Theme.color.textMuted
            font.family: Theme.font.family; font.pixelSize: Theme.size.caption
        }

        // Per-seat inspector — parked off-screen right, slides in when editing.
        SeatEditorPanel {
            id: inspector
            width: 380
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            x: board.width
            seat: root.selectedSeatId ? root.effective(root.selectedSeatId) : ({})
            config: root.selectedSeatId ? root.effective(root.selectedSeatId) : ({})
            schema: ObserverClient.profileSchema
            // Q3: a per-seat override exists once seat_overrides carries this seat.
            overridden: root.selectedSeatId !== "" && root.editedProfile.seat_overrides
                        && root.editedProfile.seat_overrides[root.selectedSeatId] !== undefined
            onEdited: function(field, value) { root.applyEdit(root.selectedSeatId, field, value) }
            onClosed: root.selectedSeatId = ""
            onRequestProviderSettings: root.StackView.view.parent.navigateProviderSettings()
        }

        states: State {
            name: "editing"
            PropertyChanges { target: gridStage; x: board.width * 0.03; scale: 0.86 }
            PropertyChanges { target: inspector; x: board.width - inspector.width }
        }
        transitions: Transition {
            ParallelAnimation {
                NumberAnimation { target: gridStage; properties: "x,scale"; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
                NumberAnimation { target: inspector; property: "x"; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
            }
        }
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
            // C2: pass an EXPLICIT resolved mode ("fake"|"live"). Credentials are
            // configured + synced on the settings page (and re-synced on load above),
            // so there is no inline credential gate here — a missing per-seat server
            // credential surfaces as the server's 403 on launch.
            onClicked: ObserverClient.launchFromProfile(root.editedProfile, setupModeControl.resolvedMode)
        }
    }
}
