import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Settings Desk — UI-only redesign of the provider/model settings page.
// Real credential and model-list behavior stays on the existing CredentialStore /
// ObserverClient boundary. Extra usage, price and validation details are local
// preview data so they can be replaced by future API fields without touching the
// provider call path.
Item {
    id: root
    objectName: "providerSettingsView"

    property string selectedSection: "ai"
    property string selectedProvider: "deepseek"
    property int credRev: 0
    property string statusText: ""
    property bool statusIsError: false
    property bool fetching: false
    property int usagePeriodIndex: 0

    readonly property int outerMargin: 26
    readonly property int pageGap: Theme.space.lg

    readonly property var settingsSections: [
        { key: "ai", label: I18n.t("AI 模型与凭证", "AI Models & Credentials"), caption: I18n.t("真实保存与同步", "Live save and sync"), glyph: "♜", preview: false },
        { key: "usage", label: I18n.t("用量与费用", "Usage & Cost"), caption: I18n.t("示例账本", "Example ledger"), glyph: "▥", preview: true },
        { key: "global", label: I18n.t("全局偏好", "Global Preferences"), caption: I18n.t("示例默认值", "Example defaults"), glyph: "⚙", preview: true },
        { key: "appearance", label: I18n.t("外观", "Appearance"), caption: I18n.t("示例主题项", "Example theme items"), glyph: "✧", preview: true },
        { key: "privacy", label: I18n.t("隐私与数据", "Privacy & Data"), caption: I18n.t("说明与示例", "Notes and examples"), glyph: "◈", preview: true },
        { key: "proxy", label: I18n.t("代理与网络", "Proxy & Network"), caption: I18n.t("说明与示例", "Notes and examples"), glyph: "◎", preview: true },
        { key: "diagnostics", label: I18n.t("诊断", "Diagnostics"), caption: I18n.t("示例状态", "Example status"), glyph: "⌁", preview: true },
        { key: "about", label: I18n.t("关于", "About"), caption: I18n.t("说明信息", "Reference notes"), glyph: "ⓘ", preview: true }
    ]

    readonly property var fallbackProviderCatalog: [
        { id: "deepseek", label: "DeepSeek", defaultBase: "https://api.deepseek.com", requiresBase: false, defaultModels: ["deepseek-chat", "deepseek-reasoner"] },
        { id: "openai", label: "OpenAI", defaultBase: "https://api.openai.com/v1", requiresBase: false, defaultModels: ["gpt-4o", "gpt-4o-mini"] },
        { id: "anthropic", label: "Anthropic", defaultBase: "https://api.anthropic.com", requiresBase: false, defaultModels: ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"] },
        { id: "openai_compatible", label: I18n.t("OpenAI 兼容自定义", "OpenAI-compatible custom"), defaultBase: "", requiresBase: true, defaultModels: [] },
        { id: "zhipu", label: "Zhipu GLM", defaultBase: "https://api.z.ai/api/paas/v4", requiresBase: false, defaultModels: ["glm-4.7", "glm-4.6", "glm-4.5-air"] },
        { id: "moonshot", label: "Moonshot Kimi", defaultBase: "https://api.moonshot.ai/v1", requiresBase: false, defaultModels: ["kimi-k2.6", "moonshot-v1-8k"] },
        { id: "qwen", label: "Alibaba Qwen", defaultBase: "https://dashscope.aliyuncs.com/compatible-mode/v1", requiresBase: false, defaultModels: ["qwen3-max", "qwen-plus", "qwen-flash"] },
        { id: "minimax", label: "MiniMax", defaultBase: "https://api.minimax.io/v1", requiresBase: false, defaultModels: ["MiniMax-M3", "MiniMax-Text-01"] },
        { id: "siliconflow", label: "SiliconFlow", defaultBase: "https://api.siliconflow.cn/v1", requiresBase: false, defaultModels: ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"] },
        { id: "xai", label: "xAI Grok", defaultBase: "https://api.x.ai/v1", requiresBase: false, defaultModels: ["grok-4.3", "grok-4"] },
        { id: "gemini", label: "Google Gemini", defaultBase: "https://generativelanguage.googleapis.com/v1beta/openai", requiresBase: false, defaultModels: ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"] },
        { id: "modelscope", label: "ModelScope", defaultBase: "https://api-inference.modelscope.cn/v1", requiresBase: false, defaultModels: ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"] },
        { id: "openrouter", label: "OpenRouter", defaultBase: "https://openrouter.ai/api/v1", requiresBase: false, defaultModels: ["~openai/gpt-latest", "~anthropic/claude-sonnet-latest", "openrouter/auto"] }
    ]

    readonly property var previewProviderCatalog: [
        { id: "preview_bedrock", label: "Bedrock", defaultBase: I18n.t("预览连接器", "Preview connector"), requiresBase: false, defaultModels: ["claude-sonnet", "llama"], previewOnly: true },
        { id: "preview_cohere", label: "Cohere", defaultBase: I18n.t("预览连接器", "Preview connector"), requiresBase: false, defaultModels: ["command-a"], previewOnly: true }
    ]

    readonly property var usageLedgerData: ({
        todayTokens: "182K",
        monthTokens: "12.45M",
        estimatedCost: "$3.42",
        topModel: "gpt-4o",
        averageRequest: "$0.018",
        availableModels: 0,
        lastValidation: I18n.t("2 分钟前", "2m ago")
    })

    readonly property var usageChartBars: [0.34, 0.42, 0.25, 0.56, 0.38, 0.62, 0.44, 0.70, 0.51, 0.84, 0.47, 0.76]

    readonly property var providerPreviewStats: ({
        deepseek: { context: "64K", input: "$0.27", output: "$1.10", last: I18n.t("预览：2 分钟前", "Preview: 2m ago"), average: "$0.004" },
        openai: { context: "128K", input: "$2.50", output: "$10.00", last: I18n.t("预览：2 分钟前", "Preview: 2m ago"), average: "$0.018" },
        anthropic: { context: "200K", input: "$3.00", output: "$15.00", last: I18n.t("预览：5 分钟前", "Preview: 5m ago"), average: "$0.022" },
        openai_compatible: { context: I18n.t("不固定", "Varies"), input: I18n.t("自定义", "Custom"), output: I18n.t("自定义", "Custom"), last: I18n.t("仅预览", "Preview only"), average: I18n.t("自定义", "Custom") },
        zhipu: { context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.006" },
        moonshot: { context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.007" },
        qwen: { context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.005" },
        minimax: { context: "1M", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.010" },
        siliconflow: { context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.006" },
        xai: { context: "256K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.014" },
        gemini: { context: "1M", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.009" },
        modelscope: { context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: "$0.006" },
        openrouter: { context: I18n.t("不固定", "Varies"), input: I18n.t("路由价格", "Routed"), output: I18n.t("路由价格", "Routed"), last: I18n.t("仅预览", "Preview only"), average: "$0.012" }
    })

    readonly property var modelPreviewRows: ({
        deepseek: [
            { model: "deepseek-chat", context: "64K", input: "$0.27", output: "$1.10", status: "Preview" },
            { model: "deepseek-reasoner", context: "64K", input: "$0.55", output: "$2.19", status: "Preview" }
        ],
        openai: [
            { model: "gpt-4o", context: "128K", input: "$2.50", output: "$10.00", status: "Preview" },
            { model: "gpt-4o-mini", context: "128K", input: "$0.15", output: "$0.60", status: "Preview" }
        ],
        anthropic: [
            { model: "claude-sonnet-4-6", context: "200K", input: "$3.00", output: "$15.00", status: "Preview" },
            { model: "claude-haiku-4-5-20251001", context: "200K", input: "$0.80", output: "$4.00", status: "Preview" }
        ],
        qwen: [
            { model: "qwen3-max", context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), status: "Preview" },
            { model: "qwen-plus", context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), status: "Preview" }
        ],
        moonshot: [
            { model: "kimi-k2.6", context: "128K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), status: "Preview" },
            { model: "moonshot-v1-8k", context: "8K", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), status: "Preview" }
        ],
        minimax: [
            { model: "MiniMax-M3", context: "1M", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), status: "Preview" },
            { model: "MiniMax-Text-01", context: "1M", input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), status: "Preview" }
        ]
    })

    readonly property var sectionPreviewCards: ({
        usage: [
            { label: I18n.t("预算护栏", "Budget guardrail"), value: I18n.t("预览", "Preview"), body: I18n.t("仅本地估算，实际供应商账单可能不同。", "Local estimates only; provider billing may vary.") },
            { label: I18n.t("席位 Token 汇总", "Per-seat token rollup"), value: I18n.t("即将推出", "Coming soon"), body: I18n.t("后续会接入已完成对局摘要。", "Will attach to completed run summaries later.") }
        ],
        global: [
            { label: I18n.t("默认对局模式", "Default match mode"), value: I18n.t("预览", "Preview"), body: I18n.t("Fake deterministic 仍是安全默认值。", "Fake deterministic remains the safe default.") },
            { label: I18n.t("设置同步", "Settings sync"), value: I18n.t("预览", "Preview"), body: I18n.t("后续接入服务端字段前，仅保留本地预览。", "Local preview only until matching server fields exist.") }
        ],
        appearance: [
            { label: I18n.t("羊皮纸密度", "Parchment density"), value: I18n.t("预览", "Preview"), body: I18n.t("未来用于切换紧凑或宽松面板。", "Future control for compact versus spacious panels.") },
            { label: I18n.t("书桌氛围", "Desk ambience"), value: I18n.t("即将推出", "Coming soon"), body: I18n.t("后续可在这里放置场景插画变体。", "Scene artwork variants can land here later.") }
        ],
        privacy: [
            { label: I18n.t("凭证可见性", "Credential visibility"), value: I18n.t("边界生效", "Active boundary"), body: I18n.t("界面只显示打码凭证。", "The UI only displays masked credentials.") },
            { label: I18n.t("导出脱敏", "Export redaction"), value: I18n.t("预览", "Preview"), body: I18n.t("未来导出设置仍会保持无 Key。", "Future export settings will stay key-free.") }
        ],
        proxy: [
            { label: I18n.t("本地服务器端点", "Local server endpoint"), value: I18n.t("预览", "Preview"), body: I18n.t("Qt 仍只和 observer server 通信。", "Qt still talks only to the observer server.") },
            { label: I18n.t("供应商网络路径", "Provider network path"), value: I18n.t("服务端负责", "Server-owned"), body: I18n.t("供应商调用仍留在 Python runtime。", "Provider calls remain in Python runtime.") }
        ],
        diagnostics: [
            { label: I18n.t("最近模型验证", "Last model validation"), value: I18n.t("预览", "Preview"), body: I18n.t("后续状态会来自供应商模型列表调用。", "Status will come from provider model-list calls later.") },
            { label: I18n.t("QML 健康状态", "QML health"), value: I18n.t("预览", "Preview"), body: I18n.t("构建与截图检查覆盖此页面。", "Build and screenshot checks cover this page.") }
        ],
        about: [
            { label: I18n.t("狼人杀观察席", "Werewolf Observer"), value: I18n.t("v1.2 预览", "v1.2 preview"), body: I18n.t("客户端无关的实时 AI 狼人杀观察席。", "Client-agnostic live AI Werewolf spectator.") },
            { label: I18n.t("设计语言", "Design language"), value: I18n.t("桌游剧场", "Tabletop theater"), body: I18n.t("暖色羊皮纸、水粉场景、珊瑚色强调。", "Warm parchment, gouache scenes, coral accents.") }
        ]
    })

    readonly property var providerCatalog: {
        var specs = (ObserverClient.profileSchema
                     && ObserverClient.profileSchema.provider_specs) || []
        if (specs.length === 0)
            return fallbackProviderCatalog
        var out = []
        for (var i = 0; i < specs.length; i++) {
            out.push({
                id: specs[i].id,
                label: root.providerDisplayLabel(specs[i].id, specs[i].label),
                defaultBase: specs[i].default_base_url,
                requiresBase: specs[i].requires_base_url,
                defaultModels: specs[i].default_models || []
            })
        }
        return out
    }

    function specFor(id) {
        var list = root.providerCatalog.concat(root.previewProviderCatalog)
        for (var i = 0; i < list.length; i++)
            if (list[i].id === id)
                return list[i]
        return { id: id, label: id, defaultBase: "", requiresBase: false, defaultModels: [] }
    }
    readonly property var selectedSpec: specFor(selectedProvider)

    function providerDisplayLabel(id, fallback) {
        if (id === "openai_compatible")
            return I18n.t("OpenAI 兼容自定义", "OpenAI-compatible custom")
        return fallback
    }

    function sectionFor(key) {
        for (var i = 0; i < root.settingsSections.length; i++)
            if (root.settingsSections[i].key === key)
                return root.settingsSections[i]
        return root.settingsSections[0]
    }

    function sectionModeLabel(section) {
        return section.preview ? I18n.t("预览", "Preview") : I18n.t("可操作", "Live")
    }

    function sectionModeColor(section) {
        return section.preview ? Theme.warm.primaryActive : Theme.warm.success
    }

    function sectionModeFill(section, selected) {
        if (section.preview)
            return selected ? Theme.withAlpha(Theme.warm.canvas, 0.72)
                            : Theme.withAlpha(Theme.parchment.terracottaWash, 0.75)
        return selected ? Theme.withAlpha(Theme.warm.success, 0.14)
                        : Theme.withAlpha(Theme.warm.success, 0.10)
    }

    function isPreviewProvider(id) {
        return ("" + id).indexOf("preview_") === 0
    }

    function labelFor(id) {
        return root.specFor(id).label || id
    }

    function cardLabelFor(id) {
        if (id === "openai_compatible")
            return "OpenAI-compatible"
        return root.labelFor(id)
    }

    function hasCredential(id) {
        if (root.isPreviewProvider(id))
            return false
        return (root.credRev, CredentialStore.hasCredential(id))
    }

    function liveModels(id) {
        if (root.isPreviewProvider(id))
            return []
        return ObserverClient.providerModels[id] || []
    }

    function isValidated(id) {
        return root.liveModels(id).length > 0
    }

    function providerStateKey(id) {
        if (root.isPreviewProvider(id))
            return "preview"
        if (root.isValidated(id))
            return "connected"
        if (root.hasCredential(id))
            return "saved"
        return "not_configured"
    }

    function providerStateLabel(id) {
        var state = root.providerStateKey(id)
        if (state === "connected")
            return I18n.t("已连接", "Connected")
        if (state === "saved")
            return I18n.t("已保存", "Saved")
        if (state === "preview")
            return I18n.t("预览", "Preview")
        return I18n.t("未配置", "Not configured")
    }

    function providerStateColor(id) {
        var state = root.providerStateKey(id)
        if (state === "connected")
            return Theme.warm.success
        if (state === "saved")
            return Theme.warm.warning
        if (state === "preview")
            return Theme.parchment.goldLine
        return Theme.warm.mutedSoft
    }

    function providerAccent(id) {
        return Theme.providerAccent(id)
    }

    function providerIcon(id) {
        switch (id) {
        case "deepseek": return "DS"
        case "openai": return "◎"
        case "anthropic": return "AI"
        case "openai_compatible": return "↔"
        case "zhipu": return "GLM"
        case "moonshot": return "K"
        case "qwen": return "Q"
        case "minimax": return "M"
        case "siliconflow": return "SF"
        case "xai": return "xAI"
        case "gemini": return "G"
        case "modelscope": return "MS"
        case "openrouter": return "OR"
        case "preview_bedrock": return "BR"
        case "preview_cohere": return "CO"
        default: return "AI"
        }
    }

    function providerGroupRows(groupKey) {
        var out = []
        if (groupKey === "preview")
            return root.previewProviderCatalog
        for (var i = 0; i < root.providerCatalog.length; i++) {
            var p = root.providerCatalog[i]
            var configured = root.hasCredential(p.id)
            if (groupKey === "connected" && configured)
                out.push(p)
            else if (groupKey === "not_configured" && !configured)
                out.push(p)
        }
        return out
    }

    function groupTitle(groupKey) {
        if (groupKey === "connected")
            return I18n.t("已连接", "Connected")
        if (groupKey === "preview")
            return I18n.t("预览", "Preview")
        return I18n.t("未配置", "Not Configured")
    }

    function groupCount(groupKey) {
        return root.providerGroupRows(groupKey).length
    }

    function providerMaskedSummary(id) {
        if (root.isPreviewProvider(id))
            return I18n.t("即将推出", "Coming soon")
        if (root.hasCredential(id))
            return CredentialStore.maskedCredential(id)
        return I18n.t("未配置", "Not configured")
    }

    function modelCountText(id) {
        var count = root.providerModelCount(id)
        return I18n.lang === "zh" ? (count + " 个模型") : (count + " models")
    }

    function modelStatusLabel(status) {
        if (status === "Live")
            return I18n.t("实时", "Live")
        if (status === "Preview")
            return I18n.t("预览", "Preview")
        return status
    }

    function endpointLabel(spec) {
        if (spec.requiresBase)
            return I18n.t("自定义 Base URL", "Custom Base URL")
        return I18n.t("默认端点", "Default endpoint")
    }

    function providerModelCount(id) {
        var live = root.liveModels(id)
        if (live.length > 0)
            return live.length
        var rows = root.modelRowsFor(id)
        if (rows.length > 0)
            return rows.length
        return root.specFor(id).defaultModels.length
    }

    function statFor(id, field) {
        var item = root.providerPreviewStats[id]
        if (!item)
            item = { context: I18n.t("不固定", "Varies"), input: I18n.t("预估", "Estimated"), output: I18n.t("预估", "Estimated"), last: I18n.t("仅预览", "Preview only"), average: I18n.t("预估", "Estimated") }
        return item[field]
    }

    function findPreviewRow(id, modelName) {
        var rows = root.modelPreviewRows[id] || []
        for (var i = 0; i < rows.length; i++)
            if (rows[i].model === modelName)
                return rows[i]
        return null
    }

    function modelRowsFor(id) {
        var rows = []
        var live = root.liveModels(id)
        if (live.length > 0) {
            for (var i = 0; i < live.length; i++) {
                var modelName = "" + live[i]
                var preview = root.findPreviewRow(id, modelName)
                rows.push({
                    model: modelName,
                    context: preview ? preview.context : root.statFor(id, "context"),
                    input: preview ? preview.input : I18n.t("预估", "Estimated"),
                    output: preview ? preview.output : I18n.t("预估", "Estimated"),
                    status: "Live"
                })
            }
            return rows
        }
        rows = root.modelPreviewRows[id] || []
        if (rows.length > 0)
            return rows
        var defaults = root.specFor(id).defaultModels || []
        for (var j = 0; j < defaults.length; j++) {
            rows.push({
                model: defaults[j],
                context: root.statFor(id, "context"),
                input: I18n.t("预估", "Estimated"),
                output: I18n.t("预估", "Estimated"),
                status: "Preview"
            })
        }
        return rows
    }

    function activePreviewCards() {
        return root.sectionPreviewCards[root.selectedSection] || []
    }

    function reasonText(code) {
        switch (code) {
        case "missing_api_key": return I18n.t("服务器无此凭证 — 请先保存并同步", "No credential on server — save & sync first")
        case "provider_unavailable": return I18n.t("无法连接 AI 服务(检查 Key / Base URL)", "AI service unreachable (check key / Base URL)")
        case "unsupported_provider": return I18n.t("不支持的 AI 服务", "Unsupported AI service")
        case "unreachable": return I18n.t("无法连接本地服务器", "Local server unreachable")
        default: return I18n.t("获取失败:", "Failed: ") + code
        }
    }

    function loadProviderIntoForm() {
        keyField.clear()
        if (root.isPreviewProvider(root.selectedProvider))
            baseField.text = root.selectedSpec.defaultBase || ""
        else
            baseField.text = CredentialStore.baseUrlFor(root.selectedProvider)
        root.fetching = false
        root.statusText = ""
        root.statusIsError = false
    }

    onSelectedProviderChanged: loadProviderIntoForm()

    Component.onCompleted: {
        loadProviderIntoForm()
        if (!ObserverClient.profileSchema || !ObserverClient.profileSchema.provider_specs)
            ObserverClient.refreshProfileSchema()
    }

    Connections {
        target: CredentialStore
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
        function onProviderModelsFetched(p) {
            if (p !== root.selectedProvider)
                return
            root.fetching = false
            var n = (ObserverClient.providerModels[p] || []).length
            root.statusIsError = (n === 0)
            root.statusText = n > 0
                ? I18n.t("连接成功 · 找到 " + n + " 个模型", "Connected · " + n + " models")
                : I18n.t("未返回模型(检查 Key / Base URL)", "No models returned (check key / Base URL)")
        }
        function onProviderModelsFailed(p, reason) {
            if (p === root.selectedProvider) {
                root.fetching = false
                root.statusIsError = true
                root.statusText = root.reasonText(reason)
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.phase.day.bg }
            GradientStop { position: 1.0; color: Theme.warm.surfaceSoft }
        }
    }

    Image {
        anchors.fill: parent
        source: Illustrations.settingsDesk
        fillMode: Image.PreserveAspectCrop
        horizontalAlignment: Image.AlignHCenter
        verticalAlignment: Image.AlignVCenter
        asynchronous: true
        cache: true
        sourceSize.width: Math.max(1, Math.ceil(width * 2))
        sourceSize.height: Math.max(1, Math.ceil(height * 2))
        visible: status === Image.Ready
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.withAlpha(Theme.warm.canvas, 0.10)
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: Theme.withAlpha(Theme.warm.canvas, 0.24) }
            GradientStop { position: 0.42; color: Theme.withAlpha(Theme.warm.canvas, 0.06) }
            GradientStop { position: 1.00; color: Theme.withAlpha(Theme.parchment.ink, 0.12) }
        }
    }

    Row {
        id: desk
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: root.outerMargin
        anchors.topMargin: root.outerMargin + 48
        anchors.bottomMargin: root.outerMargin
        spacing: root.pageGap

        Rectangle {
            id: settingsSidebar
            objectName: "settingsSidebar"
            width: Math.max(248, Math.min(306, desk.width * 0.22))
            height: parent.height
            radius: Theme.radius.xl
            color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.94)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.50)

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 8
                anchors.leftMargin: 5
                anchors.rightMargin: -5
                anchors.bottomMargin: -8
                radius: parent.radius
                color: Theme.withAlpha(Theme.parchment.woodShadow, 0.46)
                z: -1
            }

            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: Illustrations.texParchment
                fillMode: Image.Tile
                opacity: 0.17
            }

            Column {
                anchors.fill: parent
                anchors.margins: Theme.space.lg
                spacing: Theme.space.lg

                Row {
                    width: parent.width
                    spacing: Theme.space.md

                    Rectangle {
                        width: 42
                        height: 42
                        radius: 21
                        color: Theme.warm.surfaceCreamStrong
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.64)
                        Text {
                            anchors.centerIn: parent
                            text: "♟"
                            color: Theme.warm.primaryActive
                            font.pixelSize: 20
                        }
                    }

                    Column {
                        width: parent.width - 54
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Text {
                            text: I18n.t("狼人杀", "Werewolf")
                            color: Theme.warm.ink
                            font.family: Theme.fontFamilies.serif
                            font.contextFontMerging: true
                            font.pixelSize: Theme.warmSize.titleMd
                            font.weight: Theme.weight.semibold
                        }
                        Text {
                            text: I18n.t("设置书桌", "Settings Desk")
                            color: Theme.warm.muted
                            font.family: Theme.fontFamilies.sans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Theme.withAlpha(Theme.parchment.goldLine, 0.26)
                }

                Column {
                    id: settingsNavList
                    width: parent.width
                    spacing: Theme.space.xs

                    Repeater {
                        model: root.settingsSections
                        delegate: Rectangle {
                            id: sectionRow
                            required property var modelData
                            width: settingsNavList.width
                            height: 60
                            radius: Theme.radius.md
                            readonly property bool selected: root.selectedSection === modelData.key
                            color: selected ? Theme.withAlpha(Theme.parchment.terracottaWash, 0.88)
                                            : (sectionHover.hovered ? Theme.withAlpha(Theme.parchment.goldLine, 0.10) : "transparent")
                            border.width: selected ? 1 : 0
                            border.color: Theme.withAlpha(Theme.warm.primaryActive, 0.42)

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.space.md
                                anchors.rightMargin: Theme.space.sm
                                spacing: Theme.space.sm

                                Text {
                                    width: 22
                                    anchors.verticalCenter: parent.verticalCenter
                                    horizontalAlignment: Text.AlignHCenter
                                    text: sectionRow.modelData.glyph
                                    color: sectionRow.selected ? Theme.warm.primaryActive : Theme.warm.muted
                                    font.family: Theme.fontFamilies.cjkSans
                                    font.contextFontMerging: true
                                    font.pixelSize: 17
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 34 - sectionModePill.width - Theme.space.sm
                                    spacing: 1

                                    Text {
                                        width: parent.width
                                        elide: Text.ElideRight
                                        text: sectionRow.modelData.label
                                        color: sectionRow.selected ? Theme.warm.primaryActive : Theme.warm.bodyStrong
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.caption
                                        font.weight: Theme.weight.semibold
                                    }
                                    Text {
                                        width: parent.width
                                        elide: Text.ElideRight
                                        text: sectionRow.modelData.caption
                                        color: sectionRow.selected ? Theme.warm.body : Theme.warm.muted
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.micro
                                    }
                                }

                                Rectangle {
                                    id: sectionModePill
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: sectionModeText.implicitWidth + 12
                                    height: 20
                                    radius: Theme.radius.pill
                                    color: root.sectionModeFill(sectionRow.modelData, sectionRow.selected)
                                    border.width: 1
                                    border.color: Theme.withAlpha(root.sectionModeColor(sectionRow.modelData), sectionRow.selected ? 0.42 : 0.35)
                                    Text {
                                        id: sectionModeText
                                        anchors.centerIn: parent
                                        text: root.sectionModeLabel(sectionRow.modelData)
                                        color: root.sectionModeColor(sectionRow.modelData)
                                        font.family: Theme.fontFamilies.sans
                                        font.pixelSize: 9
                                        font.weight: Theme.weight.bold
                                    }
                                }
                            }

                            HoverHandler {
                                id: sectionHover
                                cursorShape: Qt.PointingHandCursor
                            }
                            TapHandler {
                                onTapped: root.selectedSection = sectionRow.modelData.key
                            }
                        }
                    }
                }

                Item { width: 1; height: Math.max(0, parent.height - y - sidebarFooter.height - Theme.space.md) }

                Column {
                    id: sidebarFooter
                    width: parent.width
                    spacing: Theme.space.sm
                    Rectangle { width: parent.width; height: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.24) }
                    Row {
                        width: parent.width
                        spacing: Theme.space.sm
                        Rectangle {
                            width: 28
                            height: 28
                            radius: 14
                            color: Theme.withAlpha(Theme.warm.primary, 0.12)
                            border.width: 1
                            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.38)
                            Text {
                                anchors.centerIn: parent
                                text: "✓"
                                color: Theme.warm.success
                                font.pixelSize: 13
                                font.weight: Theme.weight.bold
                            }
                        }
                        Column {
                            width: parent.width - 36
                            spacing: 1
                            Text {
                                text: I18n.t("Key 仅保留本地", "Keys stay local")
                                color: Theme.warm.body
                                font.family: Theme.fontFamilies.sans
                                font.pixelSize: Theme.size.caption
                                font.weight: Theme.weight.semibold
                            }
                            Text {
                                width: parent.width
                                text: I18n.t("供应商调用仍由服务端执行", "Provider calls stay server-owned")
                                color: Theme.warm.muted
                                font.family: Theme.fontFamilies.sans
                                font.pixelSize: Theme.size.micro
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }

        Item {
            id: workspace
            width: desk.width - settingsSidebar.width - desk.spacing
            height: parent.height

            Item {
                id: aiSettingsContent
                anchors.fill: parent
                visible: root.selectedSection === "ai"

                Row {
                    anchors.fill: parent
                    spacing: root.pageGap

                    Rectangle {
                        id: providerListContainer
                        objectName: "providerListContainer"
                        width: Math.max(320, Math.min(378, parent.width * 0.37))
                        height: parent.height
                        radius: Theme.radius.xl
                        color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.92)
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.48)

                        Rectangle {
                            anchors.fill: parent
                            anchors.topMargin: 8
                            anchors.leftMargin: 5
                            anchors.rightMargin: -5
                            anchors.bottomMargin: -8
                            radius: parent.radius
                            color: Theme.withAlpha(Theme.parchment.woodShadow, 0.44)
                            z: -1
                        }

                        Image {
                            anchors.fill: parent
                            anchors.margins: 2
                            source: Illustrations.texParchment
                            fillMode: Image.Tile
                            opacity: 0.18
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: Theme.space.lg
                            spacing: Theme.space.md

                            SectionHeader {
                                title: I18n.t("供应商索引", "Provider Index")
                                caption: I18n.t("真实供应商可保存凭证；预览连接器只用于示例。", "Live providers can save credentials; preview connectors are examples only.")
                                onLight: true
                            }

                            Flickable {
                                id: providerFlick
                                width: parent.width
                                height: parent.height - y
                                contentHeight: providerGroups.implicitHeight
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: ScrollBar {
                                    parent: providerFlick
                                    anchors.top: providerFlick.top
                                    anchors.right: providerFlick.right
                                    anchors.bottom: providerFlick.bottom
                                    width: 8
                                    policy: providerFlick.contentHeight > providerFlick.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
                                    contentItem: Rectangle {
                                        implicitWidth: 5
                                        radius: 3
                                        color: Theme.withAlpha(Theme.parchment.goldLineSoft, providerFlick.moving ? 0.52 : 0.34)
                                    }
                                    background: Rectangle {
                                        radius: 4
                                        color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.34)
                                        border.width: 1
                                        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.16)
                                    }
                                }

                                Column {
                                    id: providerGroups
                                    width: providerFlick.width - 14
                                    spacing: Theme.space.md

                                    Repeater {
                                        model: ["connected", "not_configured", "preview"]
                                        delegate: Column {
                                            id: providerGroup
                                            required property string modelData
                                            width: providerGroups.width
                                            spacing: Theme.space.xs
                                            property var rows: (root.credRev, ObserverClient.providerModels, root.providerGroupRows(modelData))
                                            visible: rows.length > 0
                                            height: visible ? implicitHeight : 0

                                            Row {
                                                width: parent.width
                                                spacing: Theme.space.sm
                                                Text {
                                                    text: root.groupTitle(providerGroup.modelData)
                                                    color: Theme.warm.muted
                                                    font.family: Theme.fontFamilies.sans
                                                    font.contextFontMerging: true
                                                    font.pixelSize: Theme.size.micro
                                                    font.weight: Theme.weight.bold
                                                    font.letterSpacing: 1
                                                }
                                                Rectangle {
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    width: groupCountText.implicitWidth + 10
                                                    height: 18
                                                    radius: Theme.radius.pill
                                                    color: Theme.withAlpha(Theme.parchment.goldLine, 0.14)
                                                    Text {
                                                        id: groupCountText
                                                        anchors.centerIn: parent
                                                        text: providerGroup.rows.length
                                                        color: Theme.warm.muted
                                                        font.family: Theme.fontFamilies.sans
                                                        font.pixelSize: 9
                                                        font.weight: Theme.weight.bold
                                                    }
                                                }
                                            }

                                            Repeater {
                                                model: providerGroup.rows
                                                delegate: Rectangle {
                                                    id: providerCard
                                                    objectName: root.selectedProvider === modelData.id ? "providerCardSelected" : "providerCard"
                                                    required property var modelData
                                                    width: providerGroup.width
                                                    height: 86
                                                    radius: 14
                                                    readonly property bool selected: root.selectedProvider === modelData.id
                                                    color: selected ? Theme.withAlpha(Theme.parchment.terracottaWash, 0.58)
                                                                    : (providerHover.hovered ? Theme.withAlpha(Theme.parchment.parchment, 0.92)
                                                                                             : Theme.withAlpha(Theme.parchment.parchmentSoft, 0.72))
                                                    border.width: 1
                                                    border.color: selected ? Theme.withAlpha(Theme.warm.primary, 0.78)
                                                                           : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.46)

                                                    Rectangle {
                                                        visible: providerCard.selected
                                                        anchors.left: parent.left
                                                        anchors.top: parent.top
                                                        anchors.bottom: parent.bottom
                                                        width: 4
                                                        radius: 3
                                                        color: Theme.warm.primary
                                                    }

                                                    Row {
                                                        anchors.fill: parent
                                                        anchors.margins: Theme.space.md
                                                        spacing: Theme.space.md

                                                        Item {
                                                            id: providerMedallion
                                                            width: 46
                                                            height: 46
                                                            anchors.verticalCenter: parent.verticalCenter

                                                            Rectangle {
                                                                anchors.fill: face
                                                                anchors.topMargin: 3
                                                                anchors.leftMargin: 2
                                                                anchors.rightMargin: -2
                                                                anchors.bottomMargin: -3
                                                                radius: face.radius
                                                                color: Theme.withAlpha(Theme.parchment.woodShadow, 0.26)
                                                            }

                                                            Rectangle {
                                                                id: face
                                                                anchors.fill: parent
                                                                radius: width / 2
                                                                color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.94)
                                                                border.width: 1
                                                                border.color: Theme.withAlpha(root.providerAccent(providerCard.modelData.id), 0.36)
                                                                Rectangle {
                                                                    anchors.fill: parent
                                                                    anchors.margins: 4
                                                                    radius: width / 2
                                                                    color: Theme.withAlpha(root.providerAccent(providerCard.modelData.id), 0.10)
                                                                    border.width: 1
                                                                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.26)
                                                                }
                                                                Text {
                                                                    anchors.centerIn: parent
                                                                    text: root.providerIcon(providerCard.modelData.id)
                                                                    color: Theme.parchment.ink
                                                                    font.family: Theme.fontFamilies.sans
                                                                    font.contextFontMerging: true
                                                                    font.pixelSize: root.providerIcon(providerCard.modelData.id).length > 2 ? 13 : 15
                                                                    font.weight: Theme.weight.bold
                                                                }
                                                            }
                                                        }

                                                        Column {
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            width: parent.width - 58
                                                            spacing: 4

                                                            Row {
                                                                width: parent.width
                                                                spacing: Theme.space.sm
                                                                Text {
                                                                    width: parent.width - statusChip.width - Theme.space.sm
                                                                    elide: Text.ElideRight
                                                                    text: root.cardLabelFor(providerCard.modelData.id)
                                                                    color: Theme.warm.ink
                                                                    font.family: Theme.fontFamilies.serif
                                                                    font.contextFontMerging: true
                                                                    font.pixelSize: root.cardLabelFor(providerCard.modelData.id).length > 16
                                                                                    ? Theme.size.body
                                                                                    : Theme.warmSize.titleMd
                                                                    font.weight: Theme.weight.semibold
                                                                }
                                                                Rectangle {
                                                                    id: statusChip
                                                                    width: statusText.implicitWidth + 14
                                                                    height: 22
                                                                    radius: Theme.radius.pill
                                                                    color: Theme.withAlpha(root.providerStateColor(providerCard.modelData.id), 0.16)
                                                                    border.width: 1
                                                                    border.color: Theme.withAlpha(root.providerStateColor(providerCard.modelData.id), 0.44)
                                                                    Text {
                                                                        id: statusText
                                                                        anchors.centerIn: parent
                                                                        text: root.providerStateLabel(providerCard.modelData.id)
                                                                        color: Qt.darker(root.providerStateColor(providerCard.modelData.id), 1.22)
                                                                        font.family: Theme.fontFamilies.sans
                                                                        font.pixelSize: 9
                                                                        font.weight: Theme.weight.bold
                                                                    }
                                                                }
                                                            }

                                                            Text {
                                                                width: parent.width
                                                                elide: Text.ElideRight
                                                                text: root.providerMaskedSummary(providerCard.modelData.id)
                                                                color: Theme.warm.muted
                                                                font.family: Theme.fontFamilies.sans
                                                                font.contextFontMerging: true
                                                                font.pixelSize: Theme.size.micro
                                                            }

                                                            Row {
                                                                spacing: Theme.space.xs
                                                                Text {
                                                                    text: root.modelCountText(providerCard.modelData.id)
                                                                    color: Theme.warm.body
                                                                    font.family: Theme.fontFamilies.sans
                                                                    font.pixelSize: Theme.size.micro
                                                                    font.weight: Theme.weight.medium
                                                                }
                                                                Text {
                                                                    text: "•"
                                                                    color: Theme.warm.mutedSoft
                                                                    font.pixelSize: Theme.size.micro
                                                                }
                                                                Text {
                                                                    text: root.endpointLabel(providerCard.modelData)
                                                                    color: Theme.warm.muted
                                                                    font.family: Theme.fontFamilies.sans
                                                                    font.pixelSize: Theme.size.micro
                                                                }
                                                            }
                                                        }
                                                    }

                                                    HoverHandler {
                                                        id: providerHover
                                                        cursorShape: Qt.PointingHandCursor
                                                    }
                                                    TapHandler {
                                                        onTapped: root.selectedProvider = providerCard.modelData.id
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Flickable {
                        id: detailFlick
                        width: parent.width - providerListContainer.width - parent.spacing
                        height: parent.height
                        contentHeight: detailStack.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {
                            parent: detailFlick
                            anchors.top: detailFlick.top
                            anchors.right: detailFlick.right
                            anchors.bottom: detailFlick.bottom
                            width: 8
                            policy: detailFlick.contentHeight > detailFlick.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                            contentItem: Rectangle {
                                implicitWidth: 5
                                radius: 3
                                color: Theme.withAlpha(Theme.parchment.goldLineSoft, detailFlick.moving ? 0.48 : 0.30)
                            }
                            background: Rectangle {
                                radius: 4
                                color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.24)
                            }
                        }

                        Column {
                            id: detailStack
                            width: detailFlick.width
                            spacing: Theme.space.lg

                            Rectangle {
                                id: providerDetailPanel
                                objectName: "providerDetailPanel"
                                width: parent.width
                                radius: Theme.radius.xl
                                color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.94)
                                border.width: 1
                                border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.52)
                                implicitHeight: detailBody.implicitHeight + Theme.space.lg * 2

                                Rectangle {
                                    anchors.fill: parent
                                    anchors.topMargin: 9
                                    anchors.leftMargin: 6
                                    anchors.rightMargin: -6
                                    anchors.bottomMargin: -10
                                    radius: parent.radius
                                    color: Theme.withAlpha(Theme.parchment.woodShadow, 0.46)
                                    z: -1
                                }

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    source: Illustrations.texParchment
                                    fillMode: Image.Tile
                                    opacity: 0.18
                                }

                                Column {
                                    id: detailBody
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: Theme.space.lg
                                    spacing: Theme.space.md

                                    Row {
                                        width: parent.width
                                        spacing: Theme.space.md

                                        Item {
                                            id: providerDetailMedallion
                                            width: 58
                                            height: 58

                                            Rectangle {
                                                anchors.fill: detailFace
                                                anchors.topMargin: 4
                                                anchors.leftMargin: 3
                                                anchors.rightMargin: -3
                                                anchors.bottomMargin: -4
                                                radius: detailFace.radius
                                                color: Theme.withAlpha(Theme.parchment.woodShadow, 0.28)
                                            }

                                            Rectangle {
                                                id: detailFace
                                                anchors.fill: parent
                                                radius: width / 2
                                                color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.96)
                                                border.width: 1
                                                border.color: Theme.withAlpha(root.providerAccent(root.selectedProvider), 0.40)
                                                Rectangle {
                                                    anchors.fill: parent
                                                    anchors.margins: 5
                                                    radius: width / 2
                                                    color: Theme.withAlpha(root.providerAccent(root.selectedProvider), 0.11)
                                                    border.width: 1
                                                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.30)
                                                }
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: root.providerIcon(root.selectedProvider)
                                                    color: Theme.parchment.ink
                                                    font.family: Theme.fontFamilies.sans
                                                    font.contextFontMerging: true
                                                    font.pixelSize: root.providerIcon(root.selectedProvider).length > 2 ? 15 : 18
                                                    font.weight: Theme.weight.bold
                                                }
                                            }
                                        }

                                        Column {
                                            width: parent.width - providerDetailMedallion.width - sectionStatus.width - Theme.space.md * 2
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: Theme.space.xs
                                            Text {
                                                width: parent.width
                                                elide: Text.ElideRight
                                                text: root.labelFor(root.selectedProvider)
                                                color: Theme.warm.ink
                                                font.family: Theme.fontFamilies.serif
                                                font.contextFontMerging: true
                                                font.pixelSize: Theme.warmSize.displayMd
                                                font.weight: Theme.weight.semibold
                                                lineHeightMode: Text.ProportionalHeight
                                                lineHeight: 1.08
                                            }
                                            Text {
                                                width: parent.width
                                                elide: Text.ElideRight
                                                text: root.selectedSpec.defaultBase || I18n.t("需要自定义端点", "Custom endpoint required")
                                                color: Theme.warm.muted
                                                font.family: Theme.fontFamilies.sans
                                                font.contextFontMerging: true
                                                font.pixelSize: Theme.size.caption
                                            }
                                        }

                                        Rectangle {
                                            id: sectionStatus
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: sectionStatusText.implicitWidth + 18
                                            height: 26
                                            radius: Theme.radius.pill
                                            color: Theme.withAlpha(root.providerStateColor(root.selectedProvider), 0.16)
                                            border.width: 1
                                            border.color: Theme.withAlpha(root.providerStateColor(root.selectedProvider), 0.46)
                                            Text {
                                                id: sectionStatusText
                                                anchors.centerIn: parent
                                                text: root.providerStateLabel(root.selectedProvider)
                                                color: Qt.darker(root.providerStateColor(root.selectedProvider), 1.20)
                                                font.family: Theme.fontFamilies.sans
                                                font.pixelSize: Theme.size.micro
                                                font.weight: Theme.weight.bold
                                            }
                                        }
                                    }

                                    Rectangle {
                                        width: parent.width
                                        height: 1
                                        color: Theme.withAlpha(Theme.parchment.goldLine, 0.28)
                                    }

                                    Rectangle {
                                        width: parent.width
                                        radius: 14
                                        color: Theme.withAlpha(Theme.warm.success, 0.08)
                                        border.width: 1
                                        border.color: Theme.withAlpha(Theme.warm.success, 0.24)
                                        implicitHeight: liveBoundaryRow.implicitHeight + Theme.space.md * 2

                                        Row {
                                            id: liveBoundaryRow
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.space.md
                                            spacing: Theme.space.md

                                            Rectangle {
                                                width: 34
                                                height: 34
                                                radius: 17
                                                anchors.verticalCenter: parent.verticalCenter
                                                color: Theme.withAlpha(Theme.warm.success, 0.16)
                                                border.width: 1
                                                border.color: Theme.withAlpha(Theme.warm.success, 0.38)
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "✓"
                                                    color: Qt.darker(Theme.warm.success, 1.22)
                                                    font.pixelSize: 15
                                                    font.weight: Theme.weight.bold
                                                }
                                            }

                                            Column {
                                                width: parent.width - 46
                                                anchors.verticalCenter: parent.verticalCenter
                                                spacing: 2
                                                Text {
                                                    width: parent.width
                                                    text: I18n.t("真实可操作区域", "Live actionable section")
                                                    color: Theme.warm.bodyStrong
                                                    font.family: Theme.fontFamilies.sans
                                                    font.contextFontMerging: true
                                                    font.pixelSize: Theme.size.caption
                                                    font.weight: Theme.weight.semibold
                                                }
                                                Text {
                                                    width: parent.width
                                                    text: I18n.t("保存或清除 API Key 会写入本机凭证库，并同步到本地 observer server；下方价格、用量与预览连接器仍是示例信息。",
                                                                 "Saving or clearing an API key writes to the local credential store and syncs to the local observer server; prices, usage, and preview connectors below remain example information.")
                                                    color: Theme.warm.muted
                                                    font.family: Theme.fontFamilies.sans
                                                    font.contextFontMerging: true
                                                    font.pixelSize: Theme.size.micro
                                                    wrapMode: Text.WordWrap
                                                }
                                            }
                                        }
                                    }

                                    Row {
                                        width: parent.width
                                        spacing: Theme.space.lg

                                        Column {
                                            width: Math.max(280, parent.width * 0.55)
                                            spacing: Theme.space.md

                                            Text {
                                                text: I18n.t("API 密钥", "API Key")
                                                color: Theme.warm.bodyStrong
                                                font.family: Theme.fontFamilies.sans
                                                font.pixelSize: Theme.size.caption
                                                font.weight: Theme.weight.semibold
                                            }
                                            TextField {
                                                id: keyField
                                                objectName: "providerKeyField"
                                                width: parent.width
                                                height: 43
                                                enabled: !root.isPreviewProvider(root.selectedProvider)
                                                echoMode: TextInput.Password
                                                selectByMouse: true
                                                color: Theme.warm.ink
                                                placeholderTextColor: Theme.warm.mutedSoft
                                                font.family: Theme.fontFamilies.sans
                                                font.contextFontMerging: true
                                                font.pixelSize: Theme.size.body
                                                leftPadding: Theme.space.md
                                                rightPadding: Theme.space.md
                                                placeholderText: root.isPreviewProvider(root.selectedProvider)
                                                    ? I18n.t("预览连接器暂不需要凭证字段", "Preview connector has no credential field yet")
                                                    : (root.hasCredential(root.selectedProvider)
                                                       ? I18n.t("已保存 ", "Saved ") + CredentialStore.maskedCredential(root.selectedProvider) + I18n.t(" · 重新输入即可更新", " · re-enter to update")
                                                       : I18n.t("输入 API Key", "Enter API Key"))
                                                background: Rectangle {
                                                    radius: 13
                                                    color: keyField.activeFocus ? Theme.withAlpha(Theme.parchment.parchmentSoft, 0.96)
                                                                                : Theme.withAlpha(Theme.parchment.parchment, 0.70)
                                                    border.width: 1
                                                    border.color: keyField.activeFocus ? Theme.warm.primary
                                                                                       : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.52)
                                                    Image {
                                                        anchors.fill: parent
                                                        anchors.margins: 2
                                                        source: Illustrations.texParchment
                                                        fillMode: Image.Tile
                                                        opacity: 0.08
                                                    }
                                                }
                                            }
                                        }

                                        Column {
                                            width: parent.width - x
                                            spacing: Theme.space.md

                                            Row {
                                                spacing: Theme.space.sm
                                                Text {
                                                    text: I18n.t("基础 URL", "Base URL")
                                                    color: Theme.warm.bodyStrong
                                                    font.family: Theme.fontFamilies.sans
                                                    font.pixelSize: Theme.size.caption
                                                    font.weight: Theme.weight.semibold
                                                }
                                                Rectangle {
                                                    width: baseRequirement.implicitWidth + 10
                                                    height: 18
                                                    radius: Theme.radius.pill
                                                    color: root.selectedSpec.requiresBase ? Theme.withAlpha(Theme.warm.warning, 0.18)
                                                                                          : Theme.withAlpha(Theme.parchment.goldLine, 0.12)
                                                    Text {
                                                        id: baseRequirement
                                                        anchors.centerIn: parent
                                                        text: root.selectedSpec.requiresBase ? I18n.t("必填", "Required") : I18n.t("可选", "Optional")
                                                        color: root.selectedSpec.requiresBase ? Qt.darker(Theme.warm.warning, 1.25) : Theme.warm.muted
                                                        font.family: Theme.fontFamilies.sans
                                                        font.pixelSize: 9
                                                        font.weight: Theme.weight.bold
                                                    }
                                                }
                                            }
                                            TextField {
                                                id: baseField
                                                objectName: "providerBaseUrlField"
                                                width: parent.width
                                                height: 43
                                                enabled: !root.isPreviewProvider(root.selectedProvider)
                                                selectByMouse: true
                                                color: Theme.warm.ink
                                                placeholderTextColor: Theme.warm.mutedSoft
                                                font.family: Theme.fontFamilies.sans
                                                font.contextFontMerging: true
                                                font.pixelSize: Theme.size.small
                                                leftPadding: Theme.space.md
                                                rightPadding: Theme.space.md
                                                placeholderText: root.selectedSpec.requiresBase
                                                    ? I18n.t("https://...（必填）", "https://...  (required)")
                                                    : (root.selectedSpec.defaultBase || I18n.t("默认端点", "Default endpoint"))
                                                background: Rectangle {
                                                    radius: 13
                                                    color: baseField.activeFocus ? Theme.withAlpha(Theme.parchment.parchmentSoft, 0.96)
                                                                                 : Theme.withAlpha(Theme.parchment.parchment, 0.70)
                                                    border.width: 1
                                                    border.color: baseField.activeFocus ? Theme.warm.primary
                                                                                        : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.52)
                                                    Image {
                                                        anchors.fill: parent
                                                        anchors.margins: 2
                                                        source: Illustrations.texParchment
                                                        fillMode: Image.Tile
                                                        opacity: 0.08
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Row {
                                        width: parent.width
                                        spacing: Theme.space.sm

                                        AppButton {
                                            objectName: "providerSaveButton"
                                            text: I18n.t("保存并同步", "Save & Sync")
                                            variant: "primary"
                                            onLight: true
                                            enabled: !root.isPreviewProvider(root.selectedProvider)
                                            onClicked: {
                                                if (root.selectedSpec.requiresBase && baseField.text.trim() === "") {
                                                    root.statusIsError = true
                                                    root.statusText = I18n.t("自定义 AI 服务必须填写 Base URL",
                                                                             "Custom AI service requires a Base URL")
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
                                            text: root.fetching ? I18n.t("获取中...", "Fetching...") : I18n.t("获取模型", "Fetch Models")
                                            variant: "secondary"
                                            onLight: true
                                            enabled: !root.fetching
                                                     && !root.isPreviewProvider(root.selectedProvider)
                                                     && root.hasCredential(root.selectedProvider)
                                            onClicked: {
                                                root.fetching = true
                                                root.statusIsError = false
                                                root.statusText = I18n.t("正在获取模型…", "Fetching models...")
                                                ObserverClient.fetchProviderModels(root.selectedProvider)
                                            }
                                        }
                                        AppButton {
                                            objectName: "providerClearButton"
                                            text: I18n.t("清除", "Clear")
                                            variant: "ghost"
                                            onLight: true
                                            enabled: !root.isPreviewProvider(root.selectedProvider)
                                                     && root.hasCredential(root.selectedProvider)
                                            onClicked: {
                                                CredentialStore.clearCredential(root.selectedProvider)
                                                keyField.clear()
                                                baseField.clear()
                                                root.statusText = ""
                                                root.statusIsError = false
                                            }
                                        }
                                    }

                                    Rectangle {
                                        id: validationPanel
                                        width: parent.width
                                        radius: 14
                                        color: Theme.withAlpha(Theme.parchment.parchment, 0.58)
                                        border.width: 1
                                        border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.48)
                                        implicitHeight: validationContent.implicitHeight + Theme.space.md * 2

                                        Row {
                                            id: validationContent
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.space.md
                                            spacing: Theme.space.md

                                            Rectangle {
                                                width: 34
                                                height: 34
                                                radius: 17
                                                anchors.verticalCenter: parent.verticalCenter
                                                color: Theme.withAlpha(root.statusIsError ? Theme.warm.error : root.providerStateColor(root.selectedProvider), 0.18)
                                                border.width: 1
                                                border.color: Theme.withAlpha(root.statusIsError ? Theme.warm.error : root.providerStateColor(root.selectedProvider), 0.44)
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: root.statusIsError ? "!" : "✓"
                                                    color: root.statusIsError ? Theme.warm.error : Qt.darker(root.providerStateColor(root.selectedProvider), 1.2)
                                                    font.pixelSize: 16
                                                    font.weight: Theme.weight.bold
                                                }
                                            }

                                            Column {
                                                width: parent.width - 46
                                                spacing: 2
                                                Text {
                                                    text: root.statusText !== "" ? root.statusText
                                                                                  : (root.isValidated(root.selectedProvider)
                                                                                     ? I18n.t("验证：本会话已连接", "Validation: connected this session")
                                                                                     : I18n.t("验证：保存凭证后获取模型", "Validation: save a credential, then fetch models"))
                                                    color: root.statusIsError ? Theme.warm.error : Theme.warm.bodyStrong
                                                    font.family: Theme.fontFamilies.sans
                                                    font.contextFontMerging: true
                                                    font.pixelSize: Theme.size.caption
                                                    font.weight: Theme.weight.semibold
                                                    wrapMode: Text.WordWrap
                                                    width: parent.width
                                                }
                                                Text {
                                                    objectName: "providerStatusText"
                                                    width: parent.width
                                                    text: I18n.t("最近验证 ", "Last validation ") + root.statFor(root.selectedProvider, "last")
                                                          + I18n.t(" · 可用模型 ", " · Available models ") + root.providerModelCount(root.selectedProvider)
                                                          + I18n.t(" · 价格为参考示例", " · Prices are reference examples")
                                                    color: Theme.warm.muted
                                                    font.family: Theme.fontFamilies.sans
                                                    font.contextFontMerging: true
                                                    font.pixelSize: Theme.size.micro
                                                    wrapMode: Text.WordWrap
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        width: parent.width
                                        radius: 14
                                        color: Theme.withAlpha(Theme.parchment.parchment, 0.66)
                                        border.width: 1
                                        border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.48)
                                        height: 140

                                        Column {
                                            id: modelTable
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.space.md
                                            spacing: Theme.space.sm

                                            Row {
                                                width: parent.width
                                                Text {
                                                    width: parent.width - modelCountPill.width
                                                    text: I18n.t("可用模型", "Available Models")
                                                    color: Theme.warm.ink
                                                    font.family: Theme.fontFamilies.serif
                                                    font.contextFontMerging: true
                                                    font.pixelSize: Theme.warmSize.titleMd
                                                    font.weight: Theme.weight.semibold
                                                }
                                                Rectangle {
                                                    id: modelCountPill
                                                    width: modelCountText.implicitWidth + 16
                                                    height: 24
                                                    radius: Theme.radius.pill
                                                    color: Theme.withAlpha(Theme.parchment.goldLine, 0.16)
                                                    Text {
                                                        id: modelCountText
                                                        anchors.centerIn: parent
                                                        text: root.providerModelCount(root.selectedProvider)
                                                        color: Theme.warm.body
                                                        font.family: Theme.fontFamilies.sans
                                                        font.pixelSize: Theme.size.micro
                                                        font.weight: Theme.weight.bold
                                                    }
                                                }
                                            }

                                            Rectangle { width: parent.width; height: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.24) }

                                            Grid {
                                                width: parent.width
                                                columns: 5
                                                rows: 1
                                                Repeater {
                                                    model: [
                                                        I18n.t("模型", "Model"),
                                                        I18n.t("上下文", "Context"),
                                                        I18n.t("输入价格", "Input price"),
                                                        I18n.t("输出价格", "Output price"),
                                                        I18n.t("状态", "Status")
                                                    ]
                                                    delegate: Text {
                                                        required property string modelData
                                                        width: modelTable.width / 5
                                                        text: modelData
                                                        color: Theme.warm.muted
                                                        font.family: Theme.fontFamilies.sans
                                                        font.pixelSize: Theme.size.micro
                                                        font.weight: Theme.weight.bold
                                                    }
                                                }
                                            }

                                            ListView {
                                                id: providerModelsList
                                                objectName: "providerModelsList"
                                                width: parent.width
                                                height: Math.min(70, Math.max(56, contentHeight))
                                                clip: true
                                                boundsBehavior: Flickable.StopAtBounds
                                                spacing: 3
                                                model: (root.credRev, ObserverClient.providerModels, root.modelRowsFor(root.selectedProvider))
                                                ScrollBar.vertical: ScrollBar {
                                                    width: 7
                                                    policy: providerModelsList.contentHeight > providerModelsList.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                                                    contentItem: Rectangle {
                                                        implicitWidth: 4
                                                        radius: 3
                                                        color: Theme.withAlpha(Theme.parchment.goldLineSoft, providerModelsList.moving ? 0.48 : 0.30)
                                                    }
                                                    background: Rectangle {
                                                        radius: 3
                                                        color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.22)
                                                    }
                                                }
                                                delegate: Rectangle {
                                                    required property var modelData
                                                    width: ListView.view.width
                                                    height: 28
                                                    radius: 9
                                                    color: modelHover.hovered ? Theme.withAlpha(Theme.parchment.terracottaWash, 0.55)
                                                                             : Theme.withAlpha(Theme.parchment.parchmentSoft, 0.50)
                                                    border.width: 1
                                                    border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.20)

                                                    Row {
                                                        anchors.fill: parent
                                                        anchors.leftMargin: Theme.space.sm
                                                        anchors.rightMargin: Theme.space.sm
                                                        spacing: 0
                                                        Text {
                                                            width: parent.width * 0.34
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            text: modelData.model
                                                            elide: Text.ElideRight
                                                            color: Theme.warm.ink
                                                            font.family: Theme.fontFamilies.sans
                                                            font.contextFontMerging: true
                                                            font.pixelSize: Theme.size.caption
                                                            font.weight: Theme.weight.semibold
                                                        }
                                                        Text {
                                                            width: parent.width * 0.16
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            text: modelData.context
                                                            elide: Text.ElideRight
                                                            color: Theme.warm.body
                                                            font.family: Theme.fontFamilies.sans
                                                            font.pixelSize: Theme.size.micro
                                                        }
                                                        Text {
                                                            width: parent.width * 0.18
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            text: modelData.input
                                                            elide: Text.ElideRight
                                                            color: Theme.warm.body
                                                            font.family: Theme.fontFamilies.sans
                                                            font.pixelSize: Theme.size.micro
                                                        }
                                                        Text {
                                                            width: parent.width * 0.18
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            text: modelData.output
                                                            elide: Text.ElideRight
                                                            color: Theme.warm.body
                                                            font.family: Theme.fontFamilies.sans
                                                            font.pixelSize: Theme.size.micro
                                                        }
                                                        Rectangle {
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            width: statusInRow.implicitWidth + 12
                                                            height: 20
                                                            radius: Theme.radius.pill
                                                            color: modelData.status === "Live"
                                                                   ? Theme.withAlpha(Theme.warm.success, 0.16)
                                                                   : Theme.withAlpha(Theme.parchment.goldLine, 0.14)
                                                            border.width: 1
                                                            border.color: modelData.status === "Live"
                                                                        ? Theme.withAlpha(Theme.warm.success, 0.42)
                                                                        : Theme.withAlpha(Theme.parchment.goldLine, 0.34)
                                                            Text {
                                                                id: statusInRow
                                                                anchors.centerIn: parent
                                                                text: root.modelStatusLabel(modelData.status)
                                                                color: modelData.status === "Live" ? Qt.darker(Theme.warm.success, 1.28) : Theme.warm.muted
                                                                font.family: Theme.fontFamilies.sans
                                                                font.pixelSize: 9
                                                                font.weight: Theme.weight.bold
                                                            }
                                                        }
                                                    }
                                                    HoverHandler { id: modelHover }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                id: usageLedgerCard
                                objectName: "usageLedgerCard"
                                width: parent.width
                                radius: Theme.radius.xl
                                color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.90)
                                border.width: 1
                                border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.48)
                                implicitHeight: usageContent.implicitHeight + Theme.space.sm * 2 + 2

                                Rectangle {
                                    anchors.fill: parent
                                    anchors.topMargin: 7
                                    anchors.leftMargin: 5
                                    anchors.rightMargin: -5
                                    anchors.bottomMargin: -8
                                    radius: parent.radius
                                    color: Theme.withAlpha(Theme.parchment.woodShadow, 0.36)
                                    z: -1
                                }

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    source: Illustrations.texParchment
                                    fillMode: Image.Tile
                                    opacity: 0.16
                                }

                                Column {
                                    id: usageContent
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: Theme.space.sm
                                    spacing: 7

                                    Row {
                                        width: parent.width
                                        Text {
                                            width: parent.width - periodBox.width - Theme.space.md
                                            text: I18n.t("用量账本", "Usage Ledger")
                                            color: Theme.warm.ink
                                            font.family: Theme.fontFamilies.serif
                                            font.contextFontMerging: true
                                            font.pixelSize: Theme.warmSize.titleMd
                                            font.weight: Theme.weight.semibold
                                        }
                                        ParchmentComboBox {
                                            id: periodBox
                                            objectName: "ledgerPeriodDropdown"
                                            width: 158
                                            compact: true
                                            model: [I18n.t("本月", "This Month"), I18n.t("近 30 天", "Last 30 Days")]
                                            currentIndex: root.usagePeriodIndex
                                            onActivated: root.usagePeriodIndex = currentIndex
                                            font.family: Theme.fontFamilies.sans
                                            font.pixelSize: Theme.size.caption
                                        }
                                    }

                                    Text {
                                        width: parent.width
                                        text: I18n.t("示例账本：这些数字不会写入凭证库，也不代表真实供应商账单。", "Example ledger: these numbers are not saved to credentials and do not represent real provider billing.")
                                        color: Theme.warm.muted
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.micro
                                    }

                                    Grid {
                                        width: parent.width
                                        columns: 6
                                        rowSpacing: Theme.space.sm
                                        columnSpacing: Theme.space.sm

                                        Repeater {
                                            model: [
                                                { label: I18n.t("今日 Token", "Today token"), value: root.usageLedgerData.todayTokens },
                                                { label: I18n.t("本月 Token", "Month token"), value: root.usageLedgerData.monthTokens },
                                                { label: I18n.t("预估费用", "Estimated cost"), value: root.usageLedgerData.estimatedCost },
                                                { label: I18n.t("最高费用模型", "Top model"), value: root.usageLedgerData.topModel },
                                                { label: I18n.t("单次平均", "Avg / request"), value: root.usageLedgerData.averageRequest },
                                                { label: I18n.t("可用模型", "Available models"), value: root.providerModelCount(root.selectedProvider) }
                                            ]
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: (usageContent.width - Theme.space.sm * 5) / 6
                                                height: 48
                                                radius: 12
                                                color: Theme.withAlpha(Theme.parchment.parchment, 0.58)
                                                border.width: 1
                                                border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.34)
                                                Column {
                                                    anchors.fill: parent
                                                    anchors.margins: Theme.space.sm
                                                    spacing: 3
                                                    Text {
                                                        width: parent.width
                                                        text: modelData.label
                                                        color: Theme.warm.muted
                                                        font.family: Theme.fontFamilies.sans
                                                        font.pixelSize: 9
                                                        elide: Text.ElideRight
                                                    }
                                                    Text {
                                                        width: parent.width
                                                        text: modelData.value
                                                        color: Theme.warm.ink
                                                        font.family: Theme.fontFamilies.sans
                                                        font.contextFontMerging: true
                                                        font.pixelSize: Theme.size.body
                                                        font.weight: Theme.weight.bold
                                                        elide: Text.ElideRight
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        width: parent.width
                                        height: 52
                                        radius: 12
                                        color: Theme.withAlpha(Theme.parchment.parchment, 0.54)
                                        border.width: 1
                                        border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.34)

                                        Row {
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.bottom: parent.bottom
                                            anchors.leftMargin: Theme.space.md
                                            anchors.rightMargin: Theme.space.md
                                            anchors.bottomMargin: Theme.space.sm
                                            height: parent.height - Theme.space.xl - 2
                                            spacing: 5

                                            Repeater {
                                                model: root.usageChartBars
                                                delegate: Rectangle {
                                                    required property real modelData
                                                    width: (parent.width - 5 * 11) / 12
                                                    height: Math.max(10, parent.height * modelData)
                                                    anchors.bottom: parent.bottom
                                                    radius: 5
                                                    color: Theme.withAlpha(Theme.warm.primary, 0.78)
                                                    opacity: 0.82
                                                }
                                            }
                                        }

                                        Text {
                                            anchors.left: parent.left
                                            anchors.top: parent.top
                                            anchors.margins: Theme.space.sm
                                            text: I18n.t("每日预估支出", "Daily estimated spend")
                                            color: Theme.warm.muted
                                            font.family: Theme.fontFamilies.sans
                                            font.pixelSize: Theme.size.micro
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item {
                id: previewSectionContent
                anchors.fill: parent
                visible: root.selectedSection !== "ai" && root.selectedSection !== "about"

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radius.xl
                    color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.92)
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.48)

                    Rectangle {
                        anchors.fill: parent
                        anchors.topMargin: 9
                        anchors.leftMargin: 6
                        anchors.rightMargin: -6
                        anchors.bottomMargin: -10
                        radius: parent.radius
                        color: Theme.withAlpha(Theme.parchment.woodShadow, 0.42)
                        z: -1
                    }

                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: Illustrations.texParchment
                        fillMode: Image.Tile
                        opacity: 0.17
                    }

                    Column {
                        anchors.fill: parent
                        anchors.margins: Theme.space.xxl
                        spacing: Theme.space.lg

                        Row {
                            width: parent.width
                            spacing: Theme.space.md
                            Rectangle {
                                width: 54
                                height: 54
                                radius: 18
                                color: Theme.withAlpha(Theme.warm.primary, 0.14)
                                border.width: 1
                                border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.46)
                                Text {
                                    anchors.centerIn: parent
                                    text: root.sectionFor(root.selectedSection).glyph
                                    color: Theme.warm.primaryActive
                                    font.family: Theme.fontFamilies.cjkSans
                                    font.contextFontMerging: true
                                    font.pixelSize: 22
                                }
                            }
                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 70
                                spacing: Theme.space.xs
                                Row {
                                    spacing: Theme.space.sm
                                    Text {
                                        text: root.sectionFor(root.selectedSection).label
                                        color: Theme.warm.ink
                                        font.family: Theme.fontFamilies.serif
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.warmSize.displayMd
                                        font.weight: Theme.weight.semibold
                                    }
                                    Rectangle {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: previewSectionPillText.implicitWidth + 14
                                        height: 22
                                        radius: Theme.radius.pill
                                        color: Theme.withAlpha(Theme.parchment.terracottaWash, 0.78)
                                        border.width: 1
                                        border.color: Theme.withAlpha(Theme.warm.primary, 0.34)
                                        Text {
                                            id: previewSectionPillText
                                            anchors.centerIn: parent
                                            text: I18n.t("预览示例", "Preview example")
                                            color: Theme.warm.primaryActive
                                            font.family: Theme.fontFamilies.sans
                                            font.pixelSize: 9
                                            font.weight: Theme.weight.bold
                                        }
                                    }
                                }
                                Text {
                                    width: parent.width
                                    text: I18n.t("此区域是说明或示例预览，不保存配置、不调用后端 API；真实凭证操作只在 AI 模型与凭证区。", "This area is reference or preview content. It does not save configuration or call backend APIs; live credential actions are only in AI Models & Credentials.")
                                    color: Theme.warm.muted
                                    font.family: Theme.fontFamilies.sans
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.size.caption
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        Rectangle {
                            id: languagePreferenceCard
                            visible: root.selectedSection === "global"
                            width: parent.width
                            height: visible ? 122 : 0
                            radius: 16
                            color: Theme.withAlpha(Theme.parchment.parchment, 0.66)
                            border.width: 1
                            border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.42)

                            Row {
                                anchors.fill: parent
                                anchors.margins: Theme.space.lg
                                spacing: Theme.space.lg

                                Column {
                                    width: parent.width - languageToggle.width - Theme.space.lg
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: Theme.space.xs

                                    Row {
                                        spacing: Theme.space.sm
                                        Text {
                                            text: I18n.t("语言偏好", "Language preference")
                                            color: Theme.warm.ink
                                            font.family: Theme.fontFamilies.serif
                                            font.contextFontMerging: true
                                            font.pixelSize: Theme.warmSize.titleMd
                                            font.weight: Theme.weight.semibold
                                        }
                                        Rectangle {
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: languageStatusText.implicitWidth + 14
                                            height: 22
                                            radius: Theme.radius.pill
                                            color: Theme.withAlpha(Theme.parchment.terracottaWash, 0.72)
                                            border.width: 1
                                            border.color: Theme.withAlpha(Theme.warm.primary, 0.30)
                                            Text {
                                                id: languageStatusText
                                                anchors.centerIn: parent
                                                text: I18n.t("实时", "Live")
                                                color: Theme.warm.primaryActive
                                                font.family: Theme.fontFamilies.sans
                                                font.pixelSize: 9
                                                font.weight: Theme.weight.bold
                                            }
                                        }
                                    }

                                    Text {
                                        width: parent.width
                                        text: I18n.t("使用现有前端语言机制；切换后首页和设置页会同步更新。",
                                                     "Uses the existing in-app language switch; Home and Settings update together.")
                                        color: Theme.warm.body
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.caption
                                        wrapMode: Text.WordWrap
                                        lineHeightMode: Text.ProportionalHeight
                                        lineHeight: 1.35
                                    }
                                }

                                Row {
                                    id: languageToggle
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: implicitWidth
                                    spacing: 0

                                    Repeater {
                                        model: [
                                            { code: "zh", label: "中文" },
                                            { code: "en", label: "English" }
                                        ]
                                        delegate: Rectangle {
                                            required property var modelData
                                            width: 94
                                            height: 38
                                            readonly property bool selected: I18n.lang === modelData.code
                                            radius: Theme.radius.md
                                            color: selected ? Theme.withAlpha(Theme.warm.primary, 0.88)
                                                            : Theme.withAlpha(Theme.parchment.parchmentStrong, 0.58)
                                            border.width: 1
                                            border.color: selected ? Theme.withAlpha(Theme.warm.primaryActive, 0.56)
                                                                   : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.34)
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.label
                                                color: parent.selected ? Theme.warm.textOnPrimary : Theme.warm.bodyStrong
                                                font.family: Theme.fontFamilies.sans
                                                font.contextFontMerging: true
                                                font.pixelSize: Theme.size.caption
                                                font.weight: Theme.weight.semibold
                                            }
                                            HoverHandler { id: languageHover; cursorShape: Qt.PointingHandCursor }
                                            TapHandler { onTapped: I18n.lang = modelData.code }
                                        }
                                    }
                                }
                            }
                        }

                        Grid {
                            width: parent.width
                            columns: 2
                            rowSpacing: Theme.space.md
                            columnSpacing: Theme.space.md

                            Repeater {
                                model: root.activePreviewCards()
                                delegate: Rectangle {
                                    required property var modelData
                                    width: (parent.width - Theme.space.md) / 2
                                    height: 148
                                    radius: 16
                                    color: Theme.withAlpha(Theme.parchment.parchment, 0.62)
                                    border.width: 1
                                    border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.42)
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: Theme.space.lg
                                        spacing: Theme.space.sm
                                        Row {
                                            width: parent.width
                                            Text {
                                                width: parent.width - previewValue.width - Theme.space.sm
                                                text: modelData.label
                                                color: Theme.warm.ink
                                                font.family: Theme.fontFamilies.serif
                                                font.contextFontMerging: true
                                                font.pixelSize: Theme.warmSize.titleMd
                                                font.weight: Theme.weight.semibold
                                                elide: Text.ElideRight
                                            }
                                            Rectangle {
                                                id: previewValue
                                                width: previewValueText.implicitWidth + 14
                                                height: 22
                                                radius: Theme.radius.pill
                                                color: Theme.withAlpha(Theme.parchment.goldLine, 0.14)
                                                border.width: 1
                                                border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.34)
                                                Text {
                                                    id: previewValueText
                                                    anchors.centerIn: parent
                                                    text: modelData.value
                                                    color: Theme.warm.muted
                                                    font.family: Theme.fontFamilies.sans
                                                    font.pixelSize: 9
                                                    font.weight: Theme.weight.bold
                                                }
                                            }
                                        }
                                        Text {
                                            width: parent.width
                                            text: modelData.body
                                            color: Theme.warm.body
                                            font.family: Theme.fontFamilies.sans
                                            font.contextFontMerging: true
                                            font.pixelSize: Theme.size.caption
                                            wrapMode: Text.WordWrap
                                            lineHeightMode: Text.ProportionalHeight
                                            lineHeight: 1.35
                                        }
                                    }
                                }
                            }
                        }

                        Item { width: 1; height: Math.max(0, parent.height - y - previewNotice.height) }

                        Rectangle {
                            id: previewNotice
                            width: parent.width
                            height: 72
                            radius: 16
                            color: Theme.withAlpha(Theme.parchment.terracottaWash, 0.58)
                            border.width: 1
                            border.color: Theme.withAlpha(Theme.warm.primary, 0.26)
                            Text {
                                anchors.fill: parent
                                anchors.margins: Theme.space.lg
                                text: I18n.t("预览控件在 observer server 暴露对应字段前不会持久化；这里的数字与开关仅用于说明未来信息架构。", "Preview controls are intentionally non-persistent until the observer server exposes matching fields; numbers and switches here only explain the future information architecture.")
                                color: Theme.warm.bodyStrong
                                font.family: Theme.fontFamilies.sans
                                font.contextFontMerging: true
                                font.pixelSize: Theme.size.caption
                                wrapMode: Text.WordWrap
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }
            }

            // R0: About & Update section
            Item {
                id: aboutContent
                anchors.fill: parent
                visible: root.selectedSection === "about"

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radius.xl
                    color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.92)
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.48)

                    Rectangle {
                        anchors.fill: parent
                        anchors.topMargin: 9
                        anchors.leftMargin: 6
                        anchors.rightMargin: -6
                        anchors.bottomMargin: -10
                        radius: parent.radius
                        color: Theme.withAlpha(Theme.parchment.woodShadow, 0.42)
                        z: -1
                    }

                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: Illustrations.texParchment
                        fillMode: Image.Tile
                        opacity: 0.17
                    }

                    Column {
                        anchors.fill: parent
                        anchors.margins: Theme.space.xxl
                        spacing: Theme.space.lg

                        SectionHeader {
                            title: I18n.t("关于与更新", "About & Updates")
                        }

                        AppCard {
                            width: parent.width
                            implicitHeight: aboutCardContent.implicitHeight + Theme.space.lg * 2

                            Column {
                                id: aboutCardContent
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: Theme.space.lg
                                spacing: 12

                                Row {
                                    spacing: 8
                                    Text {
                                        text: "Werewolf-agent"
                                        font.family: Theme.fontFamilies.serif
                                        font.pixelSize: 18
                                        color: Theme.warm.ink
                                    }
                                }

                                Row {
                                    spacing: 8
                                    Text {
                                        text: I18n.t("版本", "Version") + ": " + ObserverClient.releaseVersion
                                        color: Theme.warm.body
                                        font.family: Theme.fontFamilies.sans
                                        font.pixelSize: Theme.size.caption
                                    }
                                }

                                Row {
                                    spacing: 8
                                    Text {
                                        text: I18n.t("通道", "Channel") + ": " + I18n.t("Stable", "Stable")
                                        color: Theme.warm.body
                                        font.family: Theme.fontFamilies.sans
                                        font.pixelSize: Theme.size.caption
                                    }
                                }

                                Text {
                                    text: I18n.t("通过系统更新工具检查可用更新", "Check for available updates using the system update tool")
                                    color: Theme.warm.muted
                                    font.pixelSize: 12
                                    font.family: Theme.fontFamilies.sans
                                    wrapMode: Text.WordWrap
                                }

                                AppButton {
                                    text: ObserverClient.hasActiveRun()
                                        ? I18n.t("当前有进行中的对局，请等待对局结束后再检查更新", "A match is in progress. Please wait for it to finish before checking for updates.")
                                        : I18n.t("检查更新", "Check for Updates")
                                    enabled: !ObserverClient.hasActiveRun()
                                    onLight: true
                                    onClicked: {
                                        if (ObserverClient.updateRequestPath) {
                                            var req = {
                                                schema_version: 1,
                                                request_id: ObserverClient.generateUuid(),
                                                host_session_id: ObserverClient.hostSessionId,
                                                client_pid: 0,
                                                created_at: new Date().toISOString(),
                                                release_version: ObserverClient.releaseVersion,
                                                action: "launch_maintenance_tool"
                                            }
                                            if (ObserverClient.writeUpdateRequest(req)) {
                                                aboutUpdateStatus.text = I18n.t("正在退出并打开更新工具…", "Exiting and opening update tool…")
                                                Qt.quit()
                                            } else {
                                                aboutUpdateStatus.text = I18n.t("无法启动更新工具，请查看日志", "Cannot start update tool. Please check the logs.")
                                            }
                                        }
                                    }
                                }

                                Text {
                                    id: aboutUpdateStatus
                                    color: Theme.warm.muted
                                    font.pixelSize: Theme.size.caption
                                    font.family: Theme.fontFamilies.sans
                                    visible: text !== ""
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        id: topBackButton
        objectName: "providerSettingsBackButton"
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: root.outerMargin
        anchors.topMargin: Theme.space.lg
        width: backButtonContent.implicitWidth + Theme.space.lg * 2
        height: 38
        radius: Theme.radius.pill
        color: backHover.hovered ? Theme.withAlpha(Theme.parchment.parchmentSoft, 0.96)
                                 : Theme.withAlpha(Theme.parchment.parchmentSoft, 0.86)
        border.width: 1
        border.color: backHover.hovered ? Theme.withAlpha(Theme.warm.primary, 0.46)
                                        : Theme.withAlpha(Theme.parchment.goldLine, 0.48)

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 4
            anchors.leftMargin: 3
            anchors.rightMargin: -3
            anchors.bottomMargin: -5
            radius: parent.radius
            color: Theme.withAlpha(Theme.parchment.woodShadow, 0.26)
            z: -1
        }

        Image {
            anchors.fill: parent
            anchors.margins: 1
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.14
        }

        Row {
            id: backButtonContent
            anchors.centerIn: parent
            spacing: Theme.space.md
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "‹"
                color: Theme.warm.primaryActive
                font.family: Theme.fontFamilies.sans
                font.contextFontMerging: true
                font.pixelSize: 24
                font.weight: Theme.weight.bold
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("返回", "Back")
                color: Theme.warm.bodyStrong
                font.family: Theme.fontFamilies.sans
                font.contextFontMerging: true
                font.pixelSize: Theme.size.caption
                font.weight: Theme.weight.semibold
            }
        }

        HoverHandler {
            id: backHover
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            onTapped: root.StackView.view.parent.returnFromProviderSettings()
        }
    }
}
