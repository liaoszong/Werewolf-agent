import QtQuick
import QtQuick.Controls
import qt_observer
import "."

Item {
    id: root
    objectName: "seatEditorPanel"

    property var seat: ({})
    property var config: ({})
    property var schema: ({})
    property bool overridden: false
    property string statusText: ""
    property string statusKind: "empty"
    property real panelRadius: 22

    signal edited(string field, var value)
    signal closed()
    signal requestProviderSettings()

    property bool _ready: false
    property int _credRev: 0

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
        { key: "aggressive", label: I18n.t("激进", "Assertive") },
        { key: "cautious",   label: I18n.t("谨慎", "Careful") },
        { key: "custom",     label: I18n.t("自定义", "Custom") }
    ]

    function _roleLabel(role) {
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

    function _seatNumber(seatId) {
        var m = ("" + seatId).match(/\d+/)
        return m ? m[0] + I18n.t("号位", "") : seatId
    }

    function _statusColor() {
        if (root.statusKind === "ready")
            return Theme.warm.success
        if (root.statusKind === "missing")
            return Theme.warm.warning
        return Theme.warm.error
    }

    function _presetsForRole() {
        var r = (root.seat && root.seat.role) ? root.seat.role : ""
        return root.personaPresets[r] || ({})
    }
    function _presetText(key) {
        return root._presetsForRole()[key] || ""
    }
    function _activePreset() {
        var ps = root._presetsForRole()
        var t = promptArea.text
        if (ps.default === t) return "default"
        if (ps.aggressive === t) return "aggressive"
        if (ps.cautious === t) return "cautious"
        return "custom"
    }

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
        tempSlider.value = (root.config && root.config.temperature !== undefined)
            ? root.config.temperature : 0.7
        maxTokensField.text = (root.config && root.config.max_tokens !== undefined)
            ? String(root.config.max_tokens) : ""
    }

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
        if (p === "fake_deterministic")
            return true
        return (root._credRev, CredentialStore.configuredProviders()).indexOf(p) >= 0
    }

    function _specFor(pid) {
        var specs = (ObserverClient.profileSchema
                     && ObserverClient.profileSchema.provider_specs) || []
        for (var i = 0; i < specs.length; i++)
            if (specs[i].id === pid) return specs[i]
        return null
    }

    function _modelsFor(pid) {
        var live = ObserverClient.providerModels[pid]
        if (live && live.length > 0) return live
        var spec = _specFor(pid)
        return (spec && spec.default_models) ? spec.default_models : []
    }

    function _engineLabel(p) {
        if (p === "fake_deterministic") return I18n.t("试玩引擎", "Trial engine")
        var spec = _specFor(p)
        if (spec && spec.label) return spec.label
        return p || I18n.t("未配置", "Unset")
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
            out.push({ value: list[i], label: root._engineLabel(list[i]) })
        return out
    }
    function _providerIndex(p) {
        var opts = root.providerOptions
        for (var i = 0; i < opts.length; i++)
            if (opts[i].value === p) return i
        return -1
    }

    readonly property var modelList: {
        var p = root.config && root.config.provider ? root.config.provider : ""
        if (!p) return []
        return root._modelsFor(p)
    }
    readonly property int promptMax: schema && schema.prompt_max_len ? schema.prompt_max_len : 8000

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 12
        anchors.leftMargin: 5
        anchors.rightMargin: -5
        anchors.bottomMargin: -9
        radius: root.panelRadius
        color: Theme.withAlpha(Theme.parchment.woodShadow, 0.72)
        z: -3
    }

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 5
        anchors.leftMargin: 2
        anchors.rightMargin: -2
        anchors.bottomMargin: -4
        radius: root.panelRadius
        color: Theme.withAlpha(Theme.parchment.woodShadowSoft, 0.82)
        z: -2
    }

    Rectangle {
        anchors.fill: parent
        radius: root.panelRadius
        color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.97)
        border.width: 1
        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.58)
        z: -1

        Image {
            anchors.fill: parent
            anchors.margins: 2
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.27
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: root.panelRadius - 1
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 248 / 255, 234 / 255, 0.48)
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: root.panelRadius
            anchors.rightMargin: root.panelRadius
            height: 1
            color: Qt.rgba(1, 250 / 255, 240 / 255, 0.56)
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: Theme.space.lg
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentHeight: detailContent.implicitHeight + Theme.space.xl

        Column {
            id: detailContent
            width: parent.width
            spacing: Theme.space.sm

            Row {
                width: parent.width
                spacing: Theme.space.md

                Rectangle {
                    width: 48
                    height: 48
                    radius: 24
                    color: Theme.withAlpha(Theme.warm.surfaceCard, 0.92)
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.55)
                    Text {
                        anchors.centerIn: parent
                        text: root._seatNumber(root.seat.player_id)
                        color: Theme.parchment.ink
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: Theme.warmSize.titleMd
                        font.weight: Theme.weight.bold
                    }
                }

                Column {
                    width: parent.width - 48 - closeButton.width - Theme.space.md * 2
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3
                    Text {
                        width: parent.width
                        text: root._seatNumber(root.seat.player_id) + " · " + root._roleLabel(root.seat.role)
                        color: Theme.warm.ink
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: 24
                        font.weight: Theme.weight.bold
                        elide: Text.ElideRight
                    }
                    Row {
                        spacing: Theme.space.xs
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 8
                            height: 8
                            radius: 4
                            color: root._statusColor()
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.statusText
                            color: root._statusColor()
                            font.family: Theme.fontFamilies.cjkSans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                            font.weight: Theme.weight.semibold
                        }
                    }
                }

                Rectangle {
                    id: closeButton
                    width: 32
                    height: 32
                    radius: 16
                    anchors.verticalCenter: parent.verticalCenter
                    color: closeHover.hovered ? Theme.withAlpha(Theme.parchment.goldLine, 0.14) : "transparent"
                    border.width: closeHover.hovered ? 1 : 0
                    border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.36)
                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: closeHover.hovered ? Theme.parchment.inkSoft : Theme.parchment.mutedInk
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.warmSize.titleMd
                    }
                    HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.closed() }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Theme.withAlpha(Theme.parchment.goldLine, 0.25)
            }

            Rectangle {
                width: parent.width
                height: 134
                radius: 16
                color: Theme.withAlpha(Theme.parchment.parchment, 0.66)
                border.width: 1
                border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.40)

                Image {
                    anchors.fill: parent
                    anchors.margins: 2
                    source: Illustrations.texParchment
                    fillMode: Image.Tile
                    opacity: 0.10
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    height: 1
                    color: Qt.rgba(1, 248 / 255, 234 / 255, 0.38)
                }

                Column {
                    anchors.fill: parent
                        anchors.leftMargin: Theme.space.sm
                        anchors.rightMargin: Theme.space.sm
                        anchors.topMargin: Theme.space.sm
                        anchors.bottomMargin: Theme.space.sm
                    spacing: Theme.space.xs

                    FormField {
                        label: I18n.t("AI 引擎", "AI Engine")
                        ParchmentComboBox {
                            id: providerBox
                            objectName: "seatEditorProvider"
                            anchors.fill: parent
                            model: root.providerOptions
                            textRole: "label"
                            compact: true
                            controlRadius: 12
                            surfaceOpacity: 0.58
                            popupMaxHeight: 250
                            font.family: Theme.fontFamilies.cjkSans
                            font.contextFontMerging: true
                            onActivated: {
                                var picked = root.providerOptions[currentIndex].value
                                root.edited("provider", picked)
                                if (root.providerConfigured(picked))
                                    ObserverClient.fetchProviderModels(picked)
                            }
                        }
                    }

                    FormField {
                        label: I18n.t("模型", "Model")
                        ParchmentComboBox {
                            id: modelBox
                            objectName: "seatEditorModel"
                            anchors.fill: parent
                            model: root.modelList
                            compact: true
                            controlRadius: 12
                            surfaceOpacity: 0.58
                            popupMaxHeight: 250
                            font.family: Theme.fontFamilies.cjkSans
                            font.contextFontMerging: true
                            onActivated: root.edited("model", root.modelList[currentIndex])
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: Theme.space.xs
                Text {
                    text: I18n.t("扮演风格", "Role Style")
                    color: Theme.parchment.inkSoft
                    font.family: Theme.fontFamilies.cjkSerif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                }
                Row {
                    objectName: "seatEditorPersona"
                    width: parent.width
                    spacing: Theme.space.xs
                    Repeater {
                        model: root.presetChips
                        delegate: Rectangle {
                            id: chip
                            required property var modelData
                            readonly property bool isCustom: modelData.key === "custom"
                            readonly property bool active: root._activePreset() === modelData.key
                            implicitWidth: chipLabel.implicitWidth + Theme.space.lg
                            height: 30
                            radius: 12
                            color: chip.active ? Theme.withAlpha(Theme.parchment.terracottaWash, 0.72)
                                               : (chipHover.hovered
                                                  ? Theme.withAlpha(Theme.parchment.parchmentSoft, 0.82)
                                                  : Theme.withAlpha(Theme.parchment.parchment, 0.72))
                            border.width: 1
                            border.color: chip.active ? Theme.warm.primaryActive
                                                      : Theme.withAlpha(Theme.parchment.goldLine, 0.34)
                            opacity: (chip.isCustom && !chip.active) ? 0.68 : 1.0
                            scale: chipTap.pressed ? 0.97 : (chipHover.hovered ? 1.015 : 1.0)
                            Behavior on scale { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutQuad } }
                            Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
                            Text {
                                id: chipLabel
                                anchors.centerIn: parent
                                text: chip.modelData.label
                                color: chip.active ? Theme.warm.primaryActive : Theme.warm.body
                                font.family: Theme.fontFamilies.cjkSans
                                font.contextFontMerging: true
                                font.pixelSize: Theme.size.caption
                                font.weight: chip.active ? Theme.weight.semibold : Theme.weight.regular
                            }
                            HoverHandler { id: chipHover; cursorShape: Qt.PointingHandCursor }
                            TapHandler {
                                id: chipTap
                                onTapped: {
                                    if (chip.isCustom) { promptArea.forceActiveFocus(); return }
                                    root.edited("prompt", root._presetText(chip.modelData.key))
                                }
                            }
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: Theme.space.xs
                Row {
                    width: parent.width
                    Text {
                        text: I18n.t("角色指令", "Role Instructions")
                        color: Theme.parchment.inkSoft
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                    }
                    Text {
                        anchors.right: parent.right
                        text: promptArea.text.length + "/" + root.promptMax
                        color: promptArea.text.length > root.promptMax ? Theme.warm.error : Theme.warm.muted
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.micro
                    }
                }
                Rectangle {
                    width: parent.width
                    height: 100
                    radius: 15
                    color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.46)
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.34)

                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: Illustrations.texParchment
                        fillMode: Image.Tile
                        opacity: 0.11
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        height: 1
                        color: Qt.rgba(1, 248 / 255, 234 / 255, 0.42)
                    }
                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        height: 1
                        color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.38)
                    }

                    ScrollView {
                        anchors.fill: parent
                        anchors.topMargin: 4
                        anchors.bottomMargin: 4
                        clip: true
                    TextArea {
                        id: promptArea
                        objectName: "seatEditorPrompt"
                        wrapMode: TextArea.Wrap
                        color: Theme.parchment.ink
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                        leftPadding: 10
                        rightPadding: 10
                        topPadding: 8
                        bottomPadding: 8
                        background: Item {}
                        onTextChanged: if (root._ready) root.edited("prompt", text)
                    }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Theme.withAlpha(Theme.parchment.goldLine, 0.18)
            }

            Column {
                width: parent.width
                spacing: Theme.space.sm
                Text {
                    text: I18n.t("高级参数", "Advanced")
                    color: Theme.parchment.ink
                    font.family: Theme.fontFamilies.cjkSerif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.titleMd
                    font.weight: Theme.weight.semibold
                }

                Row {
                    width: parent.width
                    spacing: Theme.space.md
                    Text {
                        width: 108
                        anchors.verticalCenter: parent.verticalCenter
                        text: I18n.t("温度", "Temperature")
                        color: Theme.parchment.inkSoft
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                    }
                    Slider {
                        id: tempSlider
                        objectName: "seatEditorTemperature"
                        width: parent.width - 108 - 64 - Theme.space.md * 2
                        anchors.verticalCenter: parent.verticalCenter
                        from: 0.0; to: 2.0; stepSize: 0.1
                        background: Rectangle {
                            x: tempSlider.leftPadding
                            y: tempSlider.topPadding + tempSlider.availableHeight / 2 - 4
                            width: tempSlider.availableWidth
                            height: 8
                            radius: 4
                            color: Qt.rgba(145 / 255, 122 / 255, 88 / 255, 0.28)
                            border.width: 1
                            border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.42)
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.leftMargin: 5
                                anchors.rightMargin: 5
                                height: 1
                                color: Qt.rgba(1, 248 / 255, 234 / 255, 0.24)
                            }
                            Rectangle {
                                width: tempSlider.visualPosition * parent.width
                                height: parent.height
                                radius: 4
                                color: Theme.parchment.terracottaDeep
                            }
                            Repeater {
                                model: 5
                                Rectangle {
                                    x: index * (parent.width - 2) / 4
                                    y: -3
                                    width: 1
                                    height: 14
                                    color: Theme.withAlpha(Theme.parchment.inkSoft, 0.28)
                                }
                            }
                        }
                        handle: Rectangle {
                            x: tempSlider.leftPadding + tempSlider.visualPosition
                               * (tempSlider.availableWidth - width)
                            y: tempSlider.topPadding + tempSlider.availableHeight / 2 - height / 2
                            width: 18; height: 18; radius: 5
                            color: tempHandleHover.hovered ? "#d3a35e" : "#c79752"
                            border.width: 2
                            border.color: Qt.rgba(1, 244 / 255, 216 / 255, 0.82)
                            rotation: 45
                            HoverHandler { id: tempHandleHover; cursorShape: Qt.PointingHandCursor }
                        }
                        onMoved: root.edited("temperature", Math.round(value * 10) / 10)
                    }
                    Text {
                        width: 64
                        anchors.verticalCenter: parent.verticalCenter
                        text: tempSlider.value.toFixed(2)
                        horizontalAlignment: Text.AlignRight
                        color: Theme.parchment.ink
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                    }
                }

                Row {
                    width: parent.width
                    spacing: Theme.space.md
                    Text {
                        width: 108
                        anchors.verticalCenter: parent.verticalCenter
                        text: I18n.t("最大 Token", "Max Tokens")
                        color: Theme.parchment.inkSoft
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                    }
                    TextField {
                        id: maxTokensField
                        objectName: "seatEditorMaxTokens"
                        width: 116
                        height: 34
                        inputMethodHints: Qt.ImhDigitsOnly
                        validator: IntValidator { bottom: 1; top: 8192 }
                        color: Theme.parchment.ink
                        placeholderTextColor: Theme.parchment.mutedInk
                        placeholderText: "1024"
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                        leftPadding: Theme.space.md
                        rightPadding: Theme.space.md
                        background: Item {
                            Rectangle {
                                anchors.fill: parent
                                radius: 11
                                color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.42)
                                border.width: 1
                                border.color: maxTokensField.activeFocus
                                              ? Theme.withAlpha(Theme.warm.primaryActive, 0.42)
                                              : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.28)
                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    source: Illustrations.texParchment
                                    fillMode: Image.Tile
                                    opacity: 0.08
                                }
                            }
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                height: 2
                                color: maxTokensField.activeFocus ? Theme.warm.primaryActive
                                                                  : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.58)
                            }
                        }
                        onEditingFinished: {
                            var v = parseInt(text)
                            if (!isNaN(v))
                                root.edited("max_tokens", Math.max(1, Math.min(8192, v)))
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 32
                radius: 0
                color: "transparent"
                border.width: 0
                Row {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space.xs
                    anchors.rightMargin: Theme.space.xs
                    spacing: Theme.space.sm
                    Item {
                        width: 18
                        height: 18
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle {
                            anchors.centerIn: parent
                            width: 18
                            height: 18
                            radius: 9
                            color: Theme.withAlpha(root._statusColor(), 0.18)
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 10
                            height: 10
                            radius: 5
                            color: root._statusColor()
                        }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: I18n.t("状态：", "Status: ") + root.statusText + " · "
                              + (root.overridden ? I18n.t("席位覆盖", "Seat override")
                                                 : I18n.t("继承角色默认", "Role default"))
                        color: Theme.parchment.inkSoft
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                        font.weight: Theme.weight.semibold
                    }
                }
            }

        }
    }

    component FormField: Column {
        default property alias content: slot.data
        required property string label
        width: parent.width
        spacing: Theme.space.xs
        Text {
            text: label
            color: Theme.parchment.inkSoft
            font.family: Theme.fontFamilies.cjkSerif
            font.contextFontMerging: true
            font.pixelSize: Theme.size.micro
        }
        Item {
            id: slot
            width: parent.width
            height: 36
        }
    }
}
