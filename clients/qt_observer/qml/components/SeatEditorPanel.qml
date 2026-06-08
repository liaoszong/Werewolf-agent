import QtQuick
import QtQuick.Controls
import qt_observer
import "."

// Per-seat editor (P2-B Q1/Q2/Q3). Provider/model come from the BYO-key data
// (configured providers ∩ schema; live-fetched models). Q3 adds the per-seat
// tuning knobs: persona-preset chips that seed the prompt (replacing the dead
// "strategy" dropdown — the final value sent is only `prompt`), a temperature
// slider and a max-tokens field in a collapsible Advanced section, and an
// inherit/override badge. AppCard is a plain Rectangle (no `padding`), so the
// content Column is inset with explicit margins.
AppCard {
    id: root
    objectName: "seatEditorPanel"

    // { player_id, role, team }
    property var seat: ({})
    // { provider, model, strategy, prompt, temperature?, max_tokens? }
    property var config: ({})
    // ObserverClient.profileSchema
    property var schema: ({})
    // Q3: does this seat carry a per-seat override (vs inheriting the role default)?
    property bool overridden: false

    // Q3: `value` is `var` (not `string`) so the numeric knobs carry real numbers
    // (temperature/max_tokens) through to the profile, not stringified values.
    signal edited(string field, var value)
    signal closed()                    // collapse the inspector back to the sandbox
    signal requestProviderSettings()   // jump to the provider/model settings page

    property bool _ready: false
    property int _credRev: 0
    property bool _advancedOpen: false
    Component.onCompleted: { _syncControls(); _ensureModels(); _ready = true }
    onConfigChanged: { _syncControls(); _ensureModels() }

    Connections {
        target: CredentialStore
        function onCredentialChanged(p) { root._credRev++; root._syncControls() }
    }
    Connections {
        target: ObserverClient
        function onProviderModelsChanged() { root._syncModelBox() }
    }

    // ---------------------------------------------------------- persona presets
    // Client-side starter personas per role × tone. "default" mirrors
    // profile_config.DEFAULT_ROLE_PROMPTS so the 默认 chip highlights when a seat
    // still uses the seeded baseline. Clicking a chip OVERWRITES the prompt box
    // (the user keeps editing from there); the final value sent is just `prompt`.
    readonly property var personaPresets: ({
        "werewolf": {
            "default": "你是狼人阵营的一员。夜晚与狼队友配合选择击杀目标;白天伪装成好人,用合理的逻辑误导其他玩家、把怀疑引向好人,并优先保护狼队友。发言冷静自然,不要暴露身份。",
            "aggressive": "你是狼人,打法激进。主动带节奏、制造对立、强势发言压制好人;敢悍跳神职、敢冲票,优先击杀关键神职,用气势打乱好人阵营的判断。",
            "cautious": "你是狼人,打法保守。少说多听、避免暴露,跟大流投票、不轻易树敌;隐藏好身份,后期再发力,稳稳为狼队保人、苟到最后。"
        },
        "seer": {
            "default": "你是预言家(好人阵营)。每晚可以查验一名玩家的真实身份;白天用查验到的信息引导好人投票放逐狼人,同时提防被狼人冒充。发言条理清晰,让队友信任你。",
            "aggressive": "你是预言家,打法强势。第一天就起跳报查验、主导好人节奏,明确指挥投票方向;顶着狼人的对跳压力也要带队抓狼,牢牢掌握话语权。",
            "cautious": "你是预言家,打法稳健。不急着暴露,先观察发言找狼,必要时再起跳;给出查验时讲清逻辑、留有余地,避免被狼人轻易冒充打乱。"
        },
        "witch": {
            "default": "你是女巫(好人阵营)。你有一瓶解药和一瓶毒药,各只能用一次。谨慎判断何时救人、何时毒人,把药用在最关键的时刻,帮助好人阵营获胜。",
            "aggressive": "你是女巫,打法果断。敢在关键夜用毒搏狼,白天积极发言、亮信息带队抓狼;不畏惧暴露身份,用药和判断主导好人阵营的进攻节奏。",
            "cautious": "你是女巫,打法保守。解药留给关键神职、毒药宁可压手也不空毒;白天低调隐藏身份,靠观察稳妥决策,避免因暴露被狼人针对。"
        },
        "villager": {
            "default": "你是村民(好人阵营),没有特殊能力。通过观察发言、投票和逻辑找出狼人;积极参与讨论、提出你的推理,带领好人阵营走向胜利。",
            "aggressive": "你是村民,打法强势。带头分析、主导投票节奏,敢于站边和质疑;用清晰的逻辑给好人定方向,逼狼人露出破绽。",
            "cautious": "你是村民,打法稳健。先听多方发言再表态,不盲目冲票、不轻易站边;用逻辑慢慢缩小狼人范围,关键票投得稳准。"
        }
    })
    readonly property var presetChips: [
        { key: "default",    label: I18n.t("默认", "Default") },
        { key: "aggressive", label: I18n.t("激进", "Aggressive") },
        { key: "cautious",   label: I18n.t("谨慎", "Cautious") },
        { key: "custom",     label: I18n.t("自定义", "Custom") }
    ]
    function _presetsForRole() {
        var r = (root.seat && root.seat.role) ? root.seat.role : ""
        return root.personaPresets[r] || ({})
    }
    function _presetText(key) {
        return root._presetsForRole()[key] || ""
    }
    // Which preset (if any) the CURRENT prompt text matches — drives chip highlight.
    function _activePreset() {
        var ps = root._presetsForRole()
        var t = promptArea.text
        if (ps.default === t) return "default"
        if (ps.aggressive === t) return "aggressive"
        if (ps.cautious === t) return "cautious"
        return "custom"
    }

    // ---- control sync (imperative: a user edit severs declarative `config` binds)
    function _syncControls() {
        providerBox.currentIndex = Math.max(0, root._providerIndex(root.config.provider))
        _syncModelBox()
        var p = (root.config && root.config.prompt) ? root.config.prompt : ""
        if (promptArea.text !== p) {
            var was = root._ready
            root._ready = false
            promptArea.text = p
            root._ready = was
        }
        // Numeric knobs show a default position when unset; they are only PERSISTED
        // when the user actually moves them (onMoved / onEditingFinished), so an
        // untouched knob stays unset and the provider's own default is used.
        tempSlider.value = (root.config && root.config.temperature !== undefined)
            ? root.config.temperature : 0.7
        maxTokensField.text = (root.config && root.config.max_tokens !== undefined)
            ? String(root.config.max_tokens) : ""
    }

    // Deferred so the lazy `modelList` binding (and the ComboBox's own model
    // binding) have re-evaluated after a provider/seat switch before we read them.
    function _syncModelBox() {
        Qt.callLater(_doSyncModelBox)
    }
    function _doSyncModelBox() {
        var list = root.modelList
        var idx = list.indexOf(root.config.model)
        if (idx < 0 && list.length > 0 && root._ready) {
            root.edited("model", list[0])
            return
        }
        modelBox.currentIndex = Math.max(0, idx)
    }

    function _ensureModels() {
        var p = root.config && root.config.provider ? root.config.provider : ""
        if (p && root.providerConfigured(p)
                && (!ObserverClient.providerModels[p] || ObserverClient.providerModels[p].length === 0))
            ObserverClient.fetchProviderModels(p)
    }

    function providerConfigured(p) {
        return (root._credRev, CredentialStore.configuredProviders()).indexOf(p) >= 0
    }

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
    readonly property bool hasLiveProviders: {
        var configured = (root._credRev, CredentialStore.configuredProviders())
        var allowed = schema && schema.providers ? schema.providers : []
        for (var i = 0; i < allowed.length; i++)
            if (allowed[i] !== "fake_deterministic" && configured.indexOf(allowed[i]) >= 0)
                return true
        return false
    }
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

    readonly property var modelList: {
        var p = config && config.provider ? config.provider : ""
        if (!p) return []
        var live = ObserverClient.providerModels[p]
        if (live && live.length > 0) return live
        return (schema && schema.models && schema.models[p]) ? schema.models[p] : []
    }
    readonly property int promptMax: schema && schema.prompt_max_len ? schema.prompt_max_len : 8000

    Flickable {
        anchors.fill: parent
        contentHeight: content.implicitHeight + Theme.space.lg * 2
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: content
            x: Theme.space.lg
            y: Theme.space.lg
            width: parent.width - 2 * Theme.space.lg
            spacing: Theme.space.md

            // -------- Header: seat label + inherit/override badge + close --------
            Item {
                width: parent.width
                height: Math.max(headerCol.implicitHeight, headerRight.implicitHeight)
                Column {
                    id: headerCol
                    anchors.left: parent.left
                    anchors.right: headerRight.left
                    anchors.rightMargin: Theme.space.sm
                    anchors.verticalCenter: parent.verticalCenter
                    SectionHeader {
                        title: I18n.t("座位", "Seat") + " " + (root.seat.player_id || "")
                        caption: (root.seat.role || "") + (root.seat.team ? " · " + root.seat.team : "")
                    }
                }
                Row {
                    id: headerRight
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.space.sm
                    // inherit / override badge
                    Rectangle {
                        objectName: "seatEditorOverrideBadge"
                        anchors.verticalCenter: parent.verticalCenter
                        height: 20
                        width: badgeText.implicitWidth + Theme.space.md
                        radius: Theme.radius.pill
                        color: root.overridden ? Theme.withAlpha(Theme.report.accent, 0.18)
                                               : Theme.color.surfaceInset
                        border.width: 1
                        border.color: root.overridden ? Theme.report.accent : Theme.color.border
                        Text {
                            id: badgeText
                            anchors.centerIn: parent
                            text: root.overridden ? I18n.t("已覆盖", "Overridden")
                                                  : I18n.t("继承默认", "Inherited")
                            color: root.overridden ? Theme.report.accent : Theme.color.textMuted
                            font.family: Theme.font.family; font.pixelSize: Theme.size.micro
                        }
                    }
                    // × close
                    Rectangle {
                        id: closeBtn
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
            }

            // -------- Empty hint: no LIVE provider configured (fake still usable) --
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
                        onActivated: {
                            var picked = root.providerOptions[currentIndex].value
                            root.edited("provider", picked)
                            if (root.providerConfigured(picked))
                                ObserverClient.fetchProviderModels(picked)
                        }
                    }
                }

                // Model
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
                        onActivated: root.edited("model", root.modelList[currentIndex])
                    }
                }

                // Persona presets (replaces the dead strategy dropdown)
                Column {
                    width: parent.width
                    spacing: Theme.space.xs
                    Text {
                        text: I18n.t("性格", "Personality")
                        color: Theme.color.textSecondary
                        font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                    }
                    Row {
                        objectName: "seatEditorPersona"
                        width: parent.width
                        spacing: Theme.space.sm
                        Repeater {
                            model: root.presetChips
                            delegate: Rectangle {
                                id: chip
                                required property var modelData
                                readonly property bool isCustom: modelData.key === "custom"
                                readonly property bool active: root._activePreset() === modelData.key
                                implicitWidth: chipLabel.implicitWidth + Theme.space.lg
                                height: 28
                                radius: Theme.radius.pill
                                color: chip.active ? Theme.withAlpha(Theme.report.accent, 0.18)
                                                   : Theme.color.surfaceInset
                                border.width: 1
                                border.color: chip.active ? Theme.report.accent : Theme.color.border
                                opacity: (chip.isCustom && !chip.active) ? 0.55 : 1.0
                                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                                Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
                                Text {
                                    id: chipLabel
                                    anchors.centerIn: parent
                                    text: chip.modelData.label
                                    color: chip.active ? Theme.color.text : Theme.color.textSecondary
                                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                                    font.weight: chip.active ? Theme.weight.semibold : Theme.weight.regular
                                }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                TapHandler {
                                    onTapped: {
                                        // "custom" isn't a template — just focus the box to edit.
                                        if (chip.isCustom) { promptArea.forceActiveFocus(); return }
                                        root.edited("prompt", root._presetText(chip.modelData.key))
                                    }
                                }
                            }
                        }
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
                        height: 110
                        TextArea {
                            id: promptArea
                            objectName: "seatEditorPrompt"
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

                // -------- Advanced (collapsible): temperature + max tokens --------
                Column {
                    width: parent.width
                    spacing: Theme.space.sm

                    Item {
                        width: parent.width
                        height: advHeader.implicitHeight + Theme.space.xs * 2
                        Row {
                            id: advHeader
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Theme.space.xs
                            Text {
                                text: root._advancedOpen ? "▾" : "▸"
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                            }
                            Text {
                                text: I18n.t("高级", "Advanced")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                                font.weight: Theme.weight.medium
                            }
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: root._advancedOpen = !root._advancedOpen }
                    }

                    Column {
                        width: parent.width
                        spacing: Theme.space.md
                        visible: root._advancedOpen

                        // Temperature
                        Column {
                            width: parent.width
                            spacing: Theme.space.xs
                            Item {
                                width: parent.width
                                height: tempLabel.implicitHeight
                                Text {
                                    id: tempLabel
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: I18n.t("温度 (Temperature)", "Temperature")
                                    color: Theme.color.textSecondary
                                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                                }
                                Text {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: (root.config && root.config.temperature !== undefined)
                                          ? tempSlider.value.toFixed(1)
                                          : tempSlider.value.toFixed(1) + I18n.t("(未设)", " (unset)")
                                    color: (root.config && root.config.temperature !== undefined)
                                           ? Theme.color.text : Theme.color.textMuted
                                    font.family: Theme.font.mono; font.pixelSize: Theme.size.micro
                                }
                            }
                            Slider {
                                id: tempSlider
                                objectName: "seatEditorTemperature"
                                width: parent.width
                                from: 0.0; to: 2.0; stepSize: 0.1
                                onMoved: root.edited("temperature", Math.round(value * 10) / 10)
                            }
                        }

                        // Max tokens
                        Column {
                            width: parent.width
                            spacing: Theme.space.xs
                            Text {
                                text: I18n.t("最大回复长度", "Max response length")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                            }
                            TextField {
                                id: maxTokensField
                                objectName: "seatEditorMaxTokens"
                                width: parent.width
                                inputMethodHints: Qt.ImhDigitsOnly
                                validator: IntValidator { bottom: 1; top: 8192 }
                                color: Theme.color.text
                                placeholderTextColor: Theme.color.textMuted
                                placeholderText: I18n.t("未设(用模型默认),如 512", "unset (model default), e.g. 512")
                                font.family: Theme.font.mono; font.pixelSize: Theme.size.small
                                leftPadding: Theme.space.md; rightPadding: Theme.space.md
                                background: Rectangle {
                                    radius: Theme.radius.sm
                                    color: Theme.color.surfaceInset
                                    border.width: 1
                                    border.color: maxTokensField.activeFocus ? Theme.color.borderStrong : Theme.color.border
                                    Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
                                }
                                onEditingFinished: {
                                    var v = parseInt(text)
                                    if (!isNaN(v))
                                        root.edited("max_tokens", Math.max(1, Math.min(8192, v)))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
