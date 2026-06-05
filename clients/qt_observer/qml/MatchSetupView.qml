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
    readonly property int cardWidth: 168

    Component.onCompleted: {
        ObserverClient.refreshProfileSchema()
        ObserverClient.refreshProfiles()
    }

    // Load the first profile once the list arrives.
    Connections {
        target: ObserverClient
        function onProfileItemsChanged() {
            if (root.editedProfile.name === undefined && ObserverClient.profileItems.length > 0)
                ObserverClient.fetchProfile(ObserverClient.profileItems[0].name)
        }
        function onLoadedProfileChanged() {
            root.editedProfile = JSON.parse(JSON.stringify(ObserverClient.loadedProfile))
            if (!root.editedProfile.seat_overrides) root.editedProfile.seat_overrides = ({})
            root.profileRevision++
            root._validatedRevision = -1
            if (!root.selectedSeatId && root.seatIds.length > 0) root.selectedSeatId = root.seatIds[0]
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

        // Declared-vs-executed trust cue: a profile may declare a provider/model,
        // but this build always runs deterministic-fake. Surface it once (global),
        // never per-seat. Low-opacity amber, on-palette.
        Rectangle {
            id: executionBanner
            objectName: "setupExecutionBanner"
            width: parent.width
            implicitHeight: bannerRow.implicitHeight + Theme.space.sm * 2
            color: Theme.withAlpha(Theme.color.warning, 0.10)
            border.width: 1
            border.color: Theme.withAlpha(Theme.color.warning, 0.35)
            radius: Theme.radius.sm
            Row {
                id: bannerRow
                anchors.left: parent.left
                anchors.leftMargin: Theme.space.md
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.space.sm
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 7; height: 7; radius: 3.5
                    color: Theme.color.warning
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("执行模式：确定性模拟 — 不会发起真实 API 调用（供应方/模型仅用于审计记录）。",
                                 "Execution Mode: Deterministic Mock — no real API calls (provider/model recorded for audit only).")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.caption
                }
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
            onClicked: ObserverClient.launchFromProfile(root.editedProfile)
        }
    }
}
