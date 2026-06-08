import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Provider / model management centre (P2-B Q1). A dedicated page for BYO-key
// credentials: pick a provider on the left, enter its API key (+ base URL for
// custom OpenAI-compatible endpoints), save+sync to the local server, and press
// "Fetch models" to validate the key by listing the provider's live models.
//
// The page never sees a raw key (CredentialStore masks it); the base URL is the
// only non-secret field surfaced back. Mirrors the server PROVIDER_REGISTRY's
// four providers — kept deliberately small ("精简版"), not the cc-switch preset zoo.
Item {
    id: root
    objectName: "providerSettingsView"

    // Client-side mirror of the server PROVIDER_REGISTRY (provider_registry.py).
    // Only openai_compatible requires a custom base URL; the rest carry a default.
    readonly property var providerCatalog: [
        { id: "deepseek",          defaultBase: "https://api.deepseek.com",  requiresBase: false },
        { id: "openai",            defaultBase: "https://api.openai.com/v1", requiresBase: false },
        { id: "anthropic",         defaultBase: "https://api.anthropic.com", requiresBase: false },
        { id: "openai_compatible", defaultBase: "",                          requiresBase: true  }
    ]

    property string selectedProvider: "deepseek"
    property int credRev: 0            // bump to re-evaluate CredentialStore.* accessors
    property string statusText: ""
    property bool statusIsError: false
    property bool fetching: false

    function specFor(id) {
        for (var i = 0; i < providerCatalog.length; i++)
            if (providerCatalog[i].id === id)
                return providerCatalog[i]
        return providerCatalog[0]
    }
    readonly property var selectedSpec: specFor(selectedProvider)

    // Live-localized label (so the custom provider's "(自定义)" tracks the toggle).
    function labelFor(id) {
        switch (id) {
        case "deepseek": return "DeepSeek"
        case "openai": return "OpenAI"
        case "anthropic": return "Anthropic"
        case "openai_compatible": return I18n.t("OpenAI 兼容(自定义)", "OpenAI-compatible (custom)")
        }
        return id
    }

    // Status dot: gray = not configured, amber = configured (key saved) but not yet
    // validated, green = validated this session (a model list was fetched OK).
    function dotColor(id) {
        var configured = (root.credRev, CredentialStore.hasCredential(id))
        if (!configured)
            return Theme.color.textDisabled
        var validated = (ObserverClient.providerModels[id] || []).length > 0
        return validated ? Theme.color.success : Theme.color.warning
    }

    // Map a server error code to friendly, key-free copy.
    function reasonText(code) {
        switch (code) {
        case "missing_api_key": return I18n.t("服务器无此凭证 — 请先保存并同步", "No credential on server — save & sync first")
        case "provider_unavailable": return I18n.t("无法连接供应商(检查 Key / Base URL)", "Provider unreachable (check key / base URL)")
        case "unsupported_provider": return I18n.t("不支持的供应商", "Unsupported provider")
        case "unreachable": return I18n.t("无法连接本地服务器", "Local server unreachable")
        default: return I18n.t("获取失败:", "Failed: ") + code
        }
    }

    function loadProviderIntoForm() {
        keyField.clear()
        baseField.text = CredentialStore.baseUrlFor(root.selectedProvider)
        root.fetching = false
        root.statusText = ""
        root.statusIsError = false
    }

    onSelectedProviderChanged: loadProviderIntoForm()
    Component.onCompleted: loadProviderIntoForm()

    Connections {
        target: CredentialStore
        // A changed credential invalidates any prior validation: drop the cached
        // model list so the dot drops from green→amber until re-fetched.
        function onCredentialChanged(p) {
            ObserverClient.invalidateProviderModels(p)
            root.credRev++
        }
        function onSyncSucceeded(p) {
            if (p === root.selectedProvider) {
                root.statusIsError = false
                root.statusText = I18n.t("已同步到本地服务器", "Synced to local server")
            }
        }
        function onSyncFailed(p, reason) {
            if (p === root.selectedProvider) {
                root.statusIsError = true
                root.statusText = I18n.t("同步失败:", "Sync failed: ") + reason
            }
        }
    }

    Connections {
        target: ObserverClient
        // Guarded by the reply's own provider (the parameterless property NOTIFY
        // cannot be — it drives the model-list/dot bindings instead). A reply for a
        // provider the user already navigated away from is ignored.
        function onProviderModelsFetched(p) {
            if (p !== root.selectedProvider)
                return
            root.fetching = false
            var n = (ObserverClient.providerModels[p] || []).length
            // A 200 with an empty list means the key authenticated but no models
            // came back — flag it rather than leaving the "Fetching…" line stuck.
            root.statusIsError = (n === 0)
            root.statusText = n > 0
                ? I18n.t("校验成功 · 找到 " + n + " 个模型", "Validated · " + n + " models")
                : I18n.t("未返回模型(检查 Key / Base URL)", "No models returned (check key / base URL)")
        }
        function onProviderModelsFailed(p, reason) {
            if (p === root.selectedProvider) {
                root.fetching = false
                root.statusIsError = true
                root.statusText = root.reasonText(reason)
            }
        }
    }

    Rectangle { anchors.fill: parent; color: Theme.color.bgBase }

    // --------------------------------------------------------------- Header
    Column {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.xxxl
        anchors.leftMargin: Theme.layout.pageMargin
        anchors.rightMargin: Theme.layout.pageMargin
        spacing: Theme.space.xs

        Text {
            text: I18n.t("供应商与模型", "Providers & Models")
            color: Theme.color.text
            font.family: Theme.font.display
            font.pixelSize: Theme.size.h1
            font.weight: Theme.weight.bold
        }
        Text {
            text: I18n.t("配置各家 AI 的 API Key 与接入点,获取可用模型 —— 凭证仅在本机,不上传。",
                         "Configure each AI provider's API key & endpoint, then fetch its models. Keys stay on your machine.")
            color: Theme.color.textMuted
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
        }
    }

    // --------------------------------------------------------------- Body
    Row {
        id: body
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: actionBar.top
        anchors.topMargin: Theme.space.xl
        anchors.leftMargin: Theme.layout.pageMargin
        anchors.rightMargin: Theme.layout.pageMargin
        anchors.bottomMargin: Theme.space.lg
        spacing: Theme.space.xl

        // ----------------------------------------------- Left: provider list
        AppCard {
            id: listCard
            width: 320
            height: parent.height

            Column {
                anchors.fill: parent
                anchors.margins: Theme.space.xl
                spacing: Theme.space.lg

                SectionHeader {
                    title: I18n.t("供应商", "Providers")
                    caption: I18n.t("绿=已校验 · 黄=已配置 · 灰=未配置",
                                    "Green=validated · Amber=configured · Gray=unset")
                }

                Column {
                    width: parent.width
                    spacing: Theme.space.xs

                    Repeater {
                        model: root.providerCatalog
                        delegate: Rectangle {
                            id: providerRow
                            required property var modelData
                            width: parent.width
                            height: 56
                            radius: Theme.radius.md
                            readonly property bool isSelected: root.selectedProvider === modelData.id
                            color: isSelected ? Theme.color.surfaceAlt
                                              : (rowHover.hovered ? Theme.color.surfaceInset : "transparent")

                            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

                            // Left accent bar on the selected provider.
                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                anchors.margins: Theme.space.sm
                                width: 2
                                radius: 1
                                color: Theme.color.primary
                                visible: providerRow.isSelected
                            }

                            GlowDot {
                                id: rowDot
                                anchors.left: parent.left
                                anchors.leftMargin: Theme.space.lg
                                anchors.verticalCenter: parent.verticalCenter
                                diameter: 9
                                color: root.dotColor(providerRow.modelData.id)
                            }

                            Column {
                                anchors.left: rowDot.right
                                anchors.leftMargin: Theme.space.md
                                anchors.right: parent.right
                                anchors.rightMargin: Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                Text {
                                    width: parent.width
                                    elide: Text.ElideRight
                                    text: root.labelFor(providerRow.modelData.id)
                                    color: Theme.color.text
                                    font.family: Theme.font.family
                                    font.pixelSize: Theme.size.body
                                    font.weight: Theme.weight.medium
                                }
                                Text {
                                    width: parent.width
                                    elide: Text.ElideRight
                                    text: (root.credRev, CredentialStore.hasCredential(providerRow.modelData.id))
                                          ? CredentialStore.maskedCredential(providerRow.modelData.id)
                                          : I18n.t("未配置", "Not configured")
                                    color: Theme.color.textMuted
                                    font.family: Theme.font.mono
                                    font.pixelSize: Theme.size.micro
                                }
                            }

                            HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.selectedProvider = providerRow.modelData.id }
                        }
                    }
                }
            }
        }

        // ------------------------------------------------ Right: edit form
        AppCard {
            id: formCard
            width: parent.width - listCard.width - parent.spacing
            height: parent.height

            Flickable {
                anchors.fill: parent
                anchors.margins: Theme.space.xl
                contentHeight: form.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: form
                    width: parent.width
                    spacing: Theme.space.lg

                    Row {
                        spacing: Theme.space.sm
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.labelFor(root.selectedProvider)
                            color: Theme.color.text
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.h2
                            font.weight: Theme.weight.semibold
                        }
                        // "custom" pill for providers that require a base URL.
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: root.selectedSpec.requiresBase
                            height: 18
                            width: customTag.implicitWidth + Theme.space.md
                            radius: Theme.radius.pill
                            color: Theme.withAlpha(Theme.color.info, 0.18)
                            Text {
                                id: customTag
                                anchors.centerIn: parent
                                text: I18n.t("自定义接入点", "custom endpoint")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.micro
                            }
                        }
                    }

                    // ----- API key ------------------------------------------------
                    Column {
                        width: parent.width
                        spacing: Theme.space.xs
                        Text {
                            text: I18n.t("API Key", "API Key")
                            color: Theme.color.textSecondary
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.caption
                            font.weight: Theme.weight.medium
                        }
                        TextField {
                            id: keyField
                            objectName: "providerKeyField"
                            width: parent.width
                            echoMode: TextInput.Password
                            color: Theme.color.text
                            placeholderTextColor: Theme.color.textMuted
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.body
                            leftPadding: Theme.space.md
                            rightPadding: Theme.space.md
                            placeholderText: (root.credRev, CredentialStore.hasCredential(root.selectedProvider))
                                ? I18n.t("已保存 " + CredentialStore.maskedCredential(root.selectedProvider) + " · 重新输入以更新",
                                         "Saved " + CredentialStore.maskedCredential(root.selectedProvider) + " · re-enter to update")
                                : I18n.t("输入 API Key", "Enter API key")
                            background: Rectangle {
                                radius: Theme.radius.sm
                                color: Theme.color.surfaceInset
                                border.width: 1
                                border.color: keyField.activeFocus ? Theme.color.borderStrong : Theme.color.border
                                Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
                            }
                        }
                    }

                    // ----- Base URL -----------------------------------------------
                    Column {
                        width: parent.width
                        spacing: Theme.space.xs
                        Row {
                            spacing: Theme.space.sm
                            Text {
                                text: I18n.t("Base URL", "Base URL")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.caption
                                font.weight: Theme.weight.medium
                            }
                            Text {
                                text: root.selectedSpec.requiresBase
                                      ? I18n.t("必填", "required")
                                      : I18n.t("可选", "optional")
                                color: root.selectedSpec.requiresBase ? Theme.color.warning : Theme.color.textMuted
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.micro
                            }
                        }
                        TextField {
                            id: baseField
                            objectName: "providerBaseUrlField"
                            width: parent.width
                            color: Theme.color.text
                            placeholderTextColor: Theme.color.textMuted
                            font.family: Theme.font.mono
                            font.pixelSize: Theme.size.small
                            leftPadding: Theme.space.md
                            rightPadding: Theme.space.md
                            placeholderText: root.selectedSpec.requiresBase
                                ? I18n.t("https://…  (必填)", "https://…  (required)")
                                : root.selectedSpec.defaultBase + "  " + I18n.t("(默认)", "(default)")
                            background: Rectangle {
                                radius: Theme.radius.sm
                                color: Theme.color.surfaceInset
                                border.width: 1
                                border.color: baseField.activeFocus ? Theme.color.borderStrong : Theme.color.border
                                Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
                            }
                        }
                    }

                    // ----- Actions ------------------------------------------------
                    Row {
                        spacing: Theme.space.sm
                        AppButton {
                            objectName: "providerSaveButton"
                            text: I18n.t("保存并同步", "Save & sync")
                            variant: "primary"
                            onClicked: {
                                if (root.selectedSpec.requiresBase && baseField.text.trim() === "") {
                                    root.statusIsError = true
                                    root.statusText = I18n.t("自定义供应商必须填写 Base URL",
                                                             "Custom provider requires a Base URL")
                                    return
                                }
                                if (keyField.text.trim() === "") {
                                    root.statusIsError = true
                                    root.statusText = I18n.t("请输入 API Key", "Enter an API key")
                                    return
                                }
                                CredentialStore.saveCredential(root.selectedProvider, keyField.text, baseField.text)
                                CredentialStore.syncCredentialToServer(root.selectedProvider)
                                keyField.clear()
                            }
                        }
                        AppButton {
                            objectName: "providerFetchModelsButton"
                            text: root.fetching ? I18n.t("获取中…", "Fetching…")
                                                : I18n.t("获取模型列表", "Fetch models")
                            variant: "secondary"
                            enabled: !root.fetching && (root.credRev, CredentialStore.hasCredential(root.selectedProvider))
                            onClicked: {
                                root.fetching = true
                                root.statusIsError = false
                                root.statusText = I18n.t("正在获取模型…", "Fetching models…")
                                ObserverClient.fetchProviderModels(root.selectedProvider)
                            }
                        }
                        AppButton {
                            objectName: "providerClearButton"
                            text: I18n.t("清除", "Clear")
                            variant: "ghost"
                            enabled: (root.credRev, CredentialStore.hasCredential(root.selectedProvider))
                            onClicked: {
                                CredentialStore.clearCredential(root.selectedProvider)
                                keyField.clear()
                                baseField.clear()
                                root.statusText = ""
                                root.statusIsError = false
                            }
                        }
                    }

                    // ----- Status line --------------------------------------------
                    Text {
                        objectName: "providerStatusText"
                        width: parent.width
                        visible: root.statusText !== ""
                        text: root.statusText
                        wrapMode: Text.WordWrap
                        color: root.statusIsError ? Theme.color.danger : Theme.color.success
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                    }

                    // ----- Fetched models -----------------------------------------
                    readonly property var models: ObserverClient.providerModels[root.selectedProvider] || []

                    Rectangle {
                        width: parent.width
                        height: 220
                        radius: Theme.radius.md
                        color: Theme.color.surfaceInset
                        border.width: 1
                        border.color: Theme.color.border

                        EmptyState {
                            anchors.centerIn: parent
                            visible: form.models.length === 0
                            title: I18n.t("尚未获取模型", "No models yet")
                            subtitle: I18n.t("保存凭证后点击「获取模型列表」校验。",
                                             "Save a credential, then Fetch models to validate.")
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: Theme.space.md
                            spacing: Theme.space.sm
                            visible: form.models.length > 0

                            Text {
                                text: I18n.t("可用模型 (" + form.models.length + ")",
                                             "Available models (" + form.models.length + ")")
                                color: Theme.color.textSecondary
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.caption
                                font.weight: Theme.weight.medium
                            }

                            ListView {
                                objectName: "providerModelsList"
                                width: parent.width
                                height: parent.height - Theme.space.lg - Theme.size.caption
                                clip: true
                                model: form.models
                                boundsBehavior: Flickable.StopAtBounds
                                spacing: 2
                                ScrollIndicator.vertical: ScrollIndicator { }
                                delegate: Text {
                                    required property var modelData
                                    width: ListView.view.width
                                    elide: Text.ElideRight
                                    text: modelData
                                    color: Theme.color.text
                                    font.family: Theme.font.mono
                                    font.pixelSize: Theme.size.small
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // --------------------------------------------------------- Action bar
    Rectangle {
        id: actionBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Theme.layout.actionBarHeight
        color: Theme.color.surface
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 1; color: Theme.color.border }

        AppButton {
            objectName: "providerSettingsBackButton"
            text: I18n.t("完成", "Done")
            variant: "secondary"
            anchors.left: parent.left
            anchors.leftMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.StackView.view.parent.returnFromProviderSettings()
        }
    }
}
