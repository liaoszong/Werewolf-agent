import QtQuick
import QtQuick.Controls
import qt_observer
import "."

// Per-seat editor for provider / model / strategy / prompt.  Driven by the
// `schema` (server /api/profiles/schema) and `config` (effective seat config)
// passed in by MatchSetupView.  P2-B Q2: the provider list is now the user's
// CONFIGURED providers (CredentialStore) ∩ the schema's allowed providers, and
// the model list is the LIVE list fetched via the Q1 endpoint (static schema
// models as an offline fallback). When nothing is configured it degrades to an
// empty state that jumps to the provider-settings page.  AppCard is a plain
// Rectangle (no `padding`), so the content Column is inset with explicit margins.
AppCard {
    id: root
    objectName: "seatEditorPanel"

    // { player_id, role, team }
    property var seat: ({})
    // { provider, model, strategy, prompt }
    property var config: ({})
    // ObserverClient.profileSchema
    property var schema: ({})

    signal edited(string field, string value)
    signal closed()                    // collapse the inspector back to the sandbox
    signal requestProviderSettings()   // jump to the provider/model settings page

    // A control's declarative binding to `config` is severed the instant the user
    // interacts with it.  So on every seat switch / `config` rebind we re-push each
    // control imperatively from `config` via _syncControls, toggling `_ready` so the
    // programmatic prompt write never re-emits `edited`.
    property bool _ready: false
    property int _credRev: 0   // bump to re-evaluate CredentialStore.configuredProviders()
    Component.onCompleted: { _syncControls(); _ensureModels(); _ready = true }
    onConfigChanged: { _syncControls(); _ensureModels() }

    Connections {
        target: CredentialStore
        function onCredentialChanged(p) { root._credRev++; root._syncControls() }
    }
    Connections {
        target: ObserverClient
        // The live model list arrived → re-select the configured model in the box
        // (the model-list binding reset currentIndex when ComboBox.model changed).
        function onProviderModelsChanged() { root._syncModelBox() }
    }

    function _syncControls() {
        providerBox.currentIndex = Math.max(0, root._providerIndex(root.config.provider))
        _syncModelBox()
        strategyBox.currentIndex = Math.max(0, root.strategyList.indexOf(root.config.strategy))
        var p = (root.config && root.config.prompt) ? root.config.prompt : ""
        if (promptArea.text !== p) {
            var was = root._ready
            root._ready = false
            promptArea.text = p
            root._ready = was
        }
    }

    // Deferred so the lazy `modelList` binding (and the ComboBox's own model
    // binding) have re-evaluated after a provider/seat switch before we read them —
    // a synchronous read here returns the STALE previous-provider list. Coalesced
    // by passing a named function to Qt.callLater.
    function _syncModelBox() {
        Qt.callLater(_doSyncModelBox)
    }
    function _doSyncModelBox() {
        var list = root.modelList
        var idx = list.indexOf(root.config.model)
        // The persisted model isn't valid for this provider's effective list (e.g.
        // a cross-provider switch left a foreign model, or the live list arrived and
        // lacks the static default) → reconcile so the LAUNCHED model always equals
        // the DISPLAYED one. Only after the initial load (so we never fight the
        // first declarative push), and the resulting config rebind re-runs this.
        if (idx < 0 && list.length > 0 && root._ready) {
            root.edited("model", list[0])
            return
        }
        modelBox.currentIndex = Math.max(0, idx)
    }

    // Auto-fetch the live model list for the current provider when it isn't cached
    // yet (MatchSetupView syncs every configured credential to the server on load,
    // so the loopback fetch authenticates).
    function _ensureModels() {
        var p = root.config && root.config.provider ? root.config.provider : ""
        if (p && root.providerConfigured(p)
                && (!ObserverClient.providerModels[p] || ObserverClient.providerModels[p].length === 0))
            ObserverClient.fetchProviderModels(p)
    }

    function providerConfigured(p) {
        return (root._credRev, CredentialStore.configuredProviders()).indexOf(p) >= 0
    }

    // Friendly display label for a provider id (raw ids like "openai_compatible"
    // and "fake_deterministic" are unfriendly in a dropdown).
    function _providerLabel(p) {
        switch (p) {
        case "deepseek": return "DeepSeek"
        case "openai": return "OpenAI"
        case "anthropic": return "Anthropic"
        case "openai_compatible": return I18n.t("OpenAI 兼容", "OpenAI-compatible")
        case "fake_deterministic": return I18n.t("模拟(无需 Key)", "Simulation (no key)")
        }
        return p
    }

    // Dropdown options: the always-available no-key simulation provider plus every
    // provider the user has actually configured (∩ what the schema allows). Listing
    // fake_deterministic keeps the display honest for not-yet-assigned seats.
    readonly property var providerList: {
        var configured = (root._credRev, CredentialStore.configuredProviders())
        var allowed = schema && schema.providers ? schema.providers : []
        var out = []
        for (var i = 0; i < allowed.length; i++) {
            var p = allowed[i]
            if (p === "fake_deterministic" || configured.indexOf(p) >= 0)
                out.push(p)
        }
        return out
    }
    // Whether any LIVE (key-backed) provider is configured — drives the "go to
    // settings" hint. fake_deterministic does not count.
    readonly property bool hasLiveProviders: {
        var configured = (root._credRev, CredentialStore.configuredProviders())
        var allowed = schema && schema.providers ? schema.providers : []
        for (var i = 0; i < allowed.length; i++)
            if (allowed[i] !== "fake_deterministic" && configured.indexOf(allowed[i]) >= 0)
                return true
        return false
    }

    // {value,label} pairs so the ComboBox can render friendly labels via textRole
    // (no custom delegate needed — keeps the Basic-style popup intact).
    readonly property var providerOptions: {
        var out = []
        var list = root.providerList
        for (var i = 0; i < list.length; i++)
            out.push({ value: list[i], label: root._providerLabel(list[i]) })
        return out
    }
    function _providerIndex(p) {
        var opts = root.providerOptions
        for (var i = 0; i < opts.length; i++)
            if (opts[i].value === p) return i
        return -1
    }

    // Live fetched models preferred; static schema models as the offline fallback.
    readonly property var modelList: {
        var p = config && config.provider ? config.provider : ""
        if (!p) return []
        var live = ObserverClient.providerModels[p]
        if (live && live.length > 0) return live
        return (schema && schema.models && schema.models[p]) ? schema.models[p] : []
    }
    readonly property var strategyList: schema && schema.strategies ? schema.strategies : []
    readonly property int promptMax: schema && schema.prompt_max_len ? schema.prompt_max_len : 8000

    Column {
        id: content
        x: Theme.space.lg
        y: Theme.space.lg
        width: parent.width - 2 * Theme.space.lg
        spacing: Theme.space.md

        // Header: seat label + close (collapse back to the centred sandbox).
        Item {
            width: parent.width
            height: Math.max(headerCol.implicitHeight, closeBtn.height)
            Column {
                id: headerCol
                anchors.left: parent.left
                anchors.right: closeBtn.left
                anchors.rightMargin: Theme.space.sm
                anchors.verticalCenter: parent.verticalCenter
                SectionHeader {
                    title: I18n.t("座位", "Seat") + " " + (root.seat.player_id || "")
                    caption: (root.seat.role || "") + (root.seat.team ? " · " + root.seat.team : "")
                }
            }
            Rectangle {
                id: closeBtn
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 28; height: 28
                radius: Theme.radius.sm
                color: closeHover.hovered ? Theme.color.surfaceInset : "transparent"
                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: closeHover.hovered ? Theme.color.text : Theme.color.textMuted
                    font.family: Theme.font.family; font.pixelSize: Theme.size.body
                }
                HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.closed() }
            }
        }

        // Compact hint when no LIVE provider is configured — fake (simulation) is
        // still selectable, so this guides rather than blocks.
        Rectangle {
            width: parent.width
            visible: !root.hasLiveProviders
            height: hintCol.implicitHeight + Theme.space.md * 2
            radius: Theme.radius.md
            color: Theme.color.surfaceInset
            border.width: 1; border.color: Theme.color.border

            Column {
                id: hintCol
                anchors.centerIn: parent
                width: parent.width - Theme.space.md * 2
                spacing: Theme.space.sm
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: I18n.t("未配置真实 AI 供应商,当前仅可模拟。",
                                 "No live AI provider configured — simulation only.")
                    color: Theme.color.textMuted
                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                }
                AppButton {
                    text: I18n.t("⚙  去设置添加供应商", "⚙  Open provider settings")
                    variant: "secondary"
                    onClicked: root.requestProviderSettings()
                }
            }
        }

        // -------- Controls (fake_deterministic is always available) --------
        Column {
            width: parent.width
            spacing: Theme.space.md
            visible: root.providerList.length > 0

            // Provider
            Column {
                width: parent.width
                spacing: Theme.space.xs
                Text {
                    text: I18n.t("供应方", "Provider")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                }
                ComboBox {
                    id: providerBox
                    objectName: "seatEditorProvider"
                    width: parent.width
                    model: root.providerOptions
                    textRole: "label"
                    // currentIndex is driven imperatively by root._syncControls.
                    onActivated: {
                        var picked = root.providerOptions[currentIndex].value
                        root.edited("provider", picked)
                        if (root.providerConfigured(picked))
                            ObserverClient.fetchProviderModels(picked)
                    }
                }
            }

            // Model (live list for the selected provider)
            Column {
                width: parent.width
                spacing: Theme.space.xs
                Text {
                    text: I18n.t("模型", "Model")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                }
                ComboBox {
                    id: modelBox
                    objectName: "seatEditorModel"
                    width: parent.width
                    model: root.modelList
                    // currentIndex is driven imperatively by root._syncModelBox.
                    onActivated: root.edited("model", root.modelList[currentIndex])
                }
            }

            // Strategy (kept for Q2; Q3 replaces with persona-preset chips)
            Column {
                width: parent.width
                spacing: Theme.space.xs
                Text {
                    text: I18n.t("策略", "Strategy")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                }
                ComboBox {
                    id: strategyBox
                    objectName: "seatEditorStrategy"
                    width: parent.width
                    model: root.strategyList
                    // currentIndex is driven imperatively by root._syncControls.
                    onActivated: root.edited("strategy", root.strategyList[currentIndex])
                }
            }

            // Prompt + length counter
            Column {
                width: parent.width
                spacing: Theme.space.xs
                Item {
                    width: parent.width
                    height: promptLabel.implicitHeight
                    Text {
                        id: promptLabel
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: I18n.t("提示词", "Prompt")
                        color: Theme.color.textSecondary
                        font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: promptArea.text.length + " / " + root.promptMax
                        color: promptArea.text.length > root.promptMax ? Theme.color.danger : Theme.color.textMuted
                        font.family: Theme.font.mono; font.pixelSize: Theme.size.micro
                    }
                }
                ScrollView {
                    width: parent.width
                    height: 120
                    TextArea {
                        id: promptArea
                        objectName: "seatEditorPrompt"
                        // text is driven imperatively by root._syncControls.
                        wrapMode: TextArea.Wrap
                        color: Theme.color.text
                        background: Rectangle {
                            color: Theme.color.surfaceInset
                            border.width: 1; border.color: Theme.color.border
                            radius: Theme.radius.sm
                        }
                        onTextChanged: if (root._ready) root.edited("prompt", text)
                    }
                }
            }
        }
    }
}
