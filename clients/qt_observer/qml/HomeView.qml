import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import qt_observer
import "components"

// Warm game-client home — edge-floating HUD over a full-bleed illustration.
// Layout: SceneBackground (full) + NavRail (left) + Hero (top-left, on the cream
// margin) + floating panels (right) + overlapping tarot slider (bottom).
// ObserverClient bindings, navigation calls and required objectNames preserved.
Item {
    id: root
    objectName: "homeView"

    // Day/night phase for the backdrop (screenshot matrix toggles this).
    property string phase: "day"
    property string selectedActiveRunId: ""
    readonly property var activeRuns: _activeRuns()
    readonly property var selectedActiveRun: _findRun(selectedActiveRunId)
    readonly property var primaryActiveRun: activeRuns.length > 0 ? activeRuns[0] : ({})

    // Bilingual role name overlaid on each card's blank banner (re-evaluates on
    // language switch because I18n.t reads I18n.lang).
    function roleName(k) {
        switch (("" + k).toLowerCase()) {
        case "werewolf": return I18n.t("狼人", "Werewolf")
        case "seer":     return I18n.t("预言家", "Seer")
        case "witch":    return I18n.t("女巫", "Witch")
        case "villager": return I18n.t("村民", "Villager")
        case "guard":    return I18n.t("守卫", "Guard")
        case "hunter":   return I18n.t("猎人", "Hunter")
        }
        return ""
    }

    Component.onCompleted: {
        ObserverClient.checkHealth()
        ObserverClient.refreshRuns()
        _ensureSelectedActiveRun()
    }

    Timer {
        id: homeRunsRefreshTimer
        interval: 3000
        repeat: true
        running: true
        onTriggered: {
            ObserverClient.refreshRuns()
            if (root.selectedActiveRunId !== "")
                ObserverClient.fetchRunEvents(root.selectedActiveRunId)
        }
    }

    Connections {
        target: ObserverClient
        function onRunItemsChanged() {
            root._ensureSelectedActiveRun()
        }
    }

    onSelectedActiveRunIdChanged: {
        ObserverClient.fetchRunEvents(selectedActiveRunId)
    }

    function _activeRuns() {
        var runs = ObserverClient.runItems || []
        var out = []
        for (var i = 0; i < runs.length; ++i) {
            var st = (runs[i].status || "").toLowerCase()
            if (st === "running" || st === "queued")
                out.push(runs[i])
        }
        out.sort(function(a, b) {
            var as = (a.status || "").toLowerCase()
            var bs = (b.status || "").toLowerCase()
            if (as !== bs) {
                if (as === "running") return -1
                if (bs === "running") return 1
            }
            var am = Number(a.filesystem_mtime || 0)
            var bm = Number(b.filesystem_mtime || 0)
            if (bm !== am) return bm - am
            return ("" + (b.run_id || "")).localeCompare("" + (a.run_id || ""))
        })
        return out
    }

    function _findRun(runId) {
        if (!runId)
            return ({})
        var runs = ObserverClient.runItems || []
        for (var i = 0; i < runs.length; ++i) {
            if (runs[i].run_id === runId)
                return runs[i]
        }
        return ({})
    }

    function _ensureSelectedActiveRun() {
        var runs = _activeRuns()
        var keep = false
        for (var i = 0; i < runs.length; ++i) {
            if (runs[i].run_id === selectedActiveRunId) {
                keep = true
                break
            }
        }
        if (!keep)
            selectedActiveRunId = runs.length > 0 ? runs[0].run_id : ""
        else if (selectedActiveRunId !== "")
            ObserverClient.fetchRunEvents(selectedActiveRunId)
    }

    function _statusLabel(st) {
        st = (st || "").toLowerCase()
        if (st === "running") return I18n.t("进行中", "Running")
        if (st === "queued") return I18n.t("排队中", "Queued")
        return I18n.t("未知", "Unknown")
    }

    function _shortRunId(id) {
        id = "" + (id || "")
        return id.length > 18 ? id.slice(0, 12) + "..." + id.slice(id.length - 5) : id
    }

    function _eventText(ev) {
        if (!ev)
            return "—"
        var data = ev.data || {}
        return data.summary || ev.summary || ev.kind || ev.type || ev.event_id || "—"
    }

    function _recentPreviewEvents() {
        var events = ObserverClient.previewEventItems || []
        var out = []
        for (var i = events.length - 1; i >= 0 && out.length < 3; --i)
            out.push(events[i])
        return out
    }

    function _continueRun(run) {
        if (!run || !run.run_id)
            return
        ObserverClient.openRun(run.run_id, false)
        root.StackView.view.parent.navigateCockpit()
    }

    // Backdrop fills ONLY the content region (right of the NavRail) so the
    // illustration's cream margin lands under the hero text, not behind the rail.
    SceneBackground {
        id: scene
        phase: root.phase
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
    }

    // ----------------------------------------------------------- Left NavRail
    NavRail {
        id: rail
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 220
        currentKey: "home"
        items: [
            { key: "home",     label: I18n.t("今夜对局", "Tonight"),   glyph: "☾", enabled: true },
            { key: "seats",    label: I18n.t("席位一览", "Seats"),     glyph: "◍", enabled: true },
            { key: "replay",   label: I18n.t("查看复盘", "Replays"),   glyph: "❡", enabled: true },
            { key: "deck",     label: I18n.t("收藏卡牌", "Card Deck"), glyph: "🂠", enabled: false },
            { key: "settings", label: I18n.t("设置", "Settings"),      glyph: "⚙", enabled: true }
        ]
        onActivated: function(key) {
            if (key === "seats")
                root.StackView.view.parent.navigateSetup()
            else if (key === "replay") {
                root.StackView.view.parent.navigateHistory()
            }
            else if (key === "settings")
                root.StackView.view.parent.navigateProviderSettings()
        }
    }

    // ------------------------------------------------ Hero (top-left, on cream)
    Column {
        id: hero
        anchors.left: rail.right
        anchors.top: parent.top
        anchors.leftMargin: Theme.space.huge
        anchors.topMargin: Theme.space.huge
        width: Math.min(parent.width - rail.width - Theme.space.huge * 2, 520)
        spacing: Theme.space.md

        Text {
            text: I18n.t("观 战 席", "OBSERVER COCKPIT")
            color: Theme.warm.primary
            font.family: Theme.fontFamilies.sans
            font.contextFontMerging: true
            font.pixelSize: Theme.size.caption
            font.weight: Theme.weight.bold
            font.letterSpacing: 2
        }

        Text {
            text: I18n.t("狼人杀 · 观察席", "Werewolf Observer")
            color: Theme.warm.ink
            font.family: Theme.fontFamilies.serif
            font.contextFontMerging: true
            font.pixelSize: Theme.warmSize.displayXl
            font.weight: Theme.weight.medium
            font.letterSpacing: -1
            lineHeightMode: Text.ProportionalHeight
            lineHeight: 1.12
        }

        Text {
            width: parent.width
            text: I18n.t("月升月落，谎言与真相交织 —— 在沉默中见证，在洞察中铭记。",
                         "As the moon rises and sets, lies and truth entwine — witness in silence, remember in insight.")
            color: Theme.warm.body
            font.family: Theme.fontFamilies.sans
            font.contextFontMerging: true
            font.pixelSize: Theme.warmSize.bodyLg
            wrapMode: Text.WordWrap
            lineHeightMode: Text.ProportionalHeight
            lineHeight: 1.5
        }

        Row {
            spacing: Theme.space.sm
            topPadding: Theme.space.xs
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("服务器", "Server")
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans
                font.contextFontMerging: true
                font.pixelSize: Theme.size.caption
            }
            StatusBadge {
                id: serverStatusBadge
                objectName: "serverStatusBadge"
                onLight: true
                anchors.verticalCenter: parent.verticalCenter
                status: ObserverClient.connected ? "connected" : "disconnected"
            }
        }

        Column {
            id: heroActions
            width: Math.max(startNewMatchButton.implicitWidth,
                            historyButton.implicitWidth,
                            continueActiveRunButton.implicitWidth)
            spacing: Theme.space.sm
            topPadding: Theme.space.lg
            AppButton {
                id: continueActiveRunButton
                objectName: "continueActiveRunButton"
                onLight: true
                width: parent.width
                visible: root.activeRuns.length > 0
                text: I18n.t("继续观察", "Continue Observing")
                variant: "primary"
                onClicked: root._continueRun(root.selectedActiveRunId !== "" ? root.selectedActiveRun : root.primaryActiveRun)
            }
            AppButton {
                id: startNewMatchButton
                objectName: "startNewMatchButton"
                onLight: true
                width: parent.width
                text: root.activeRuns.length > 0
                      ? I18n.t("开始新对局", "Start New Match")
                      : I18n.t("开始新对局", "Start New Match")
                variant: root.activeRuns.length > 0 ? "secondary" : "primary"
                onClicked: root.StackView.view.parent.navigateSetup()
            }
            AppButton {
                id: historyButton
                objectName: "historyButton"
                onLight: true
                width: parent.width
                text: I18n.t("查看昨夜复盘", "Last Night's Replay")
                variant: "secondary"
                onClicked: root.StackView.view.parent.navigateHistory()
            }
        }
    }

    Rectangle {
        id: homeLanguageToggle
        objectName: "homeLanguageToggle"
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: Theme.space.xxl
        anchors.topMargin: Theme.space.xxl
        width: homeLanguageRow.implicitWidth + 10
        height: 36
        radius: Theme.radius.pill
        color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.84)
        border.width: 1
        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.46)

        Image {
            anchors.fill: parent
            anchors.margins: 1
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.14
        }

        Row {
            id: homeLanguageRow
            anchors.centerIn: parent
            spacing: 0

            Repeater {
                model: [
                    { code: "zh", label: "中文" },
                    { code: "en", label: "EN" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: modelData.code === "zh" ? 58 : 44
                    height: 28
                    radius: Theme.radius.pill
                    readonly property bool selected: I18n.lang === modelData.code
                    color: selected ? Theme.withAlpha(Theme.warm.primary, 0.88)
                                    : "transparent"
                    border.width: selected ? 1 : 0
                    border.color: Theme.withAlpha(Theme.warm.primaryActive, 0.42)
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: parent.selected ? Theme.warm.textOnPrimary : Theme.warm.bodyStrong
                        font.family: Theme.fontFamilies.sans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                        font.weight: Theme.weight.semibold
                    }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: I18n.lang = modelData.code }
                }
            }
        }
    }

    // ------------------------------------ Right floating panels
    // Semi-transparent parchment over the scene (no blur — Phase 1 rule). The
    // panels are an active-runs hub: REST summaries select a run, and the event
    // preview follows that one run without merging multiple streams.
    Column {
        id: rightPanels
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: Theme.space.xxl
        anchors.topMargin: Theme.space.xxl + 48
        width: 264
        spacing: Theme.space.lg

        Rectangle {
            width: parent.width
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.warm.canvas, 0.82)
            border.width: 1
            border.color: Theme.withAlpha(Theme.warm.ink, 0.08)
            implicitHeight: Math.max(tonightBody.implicitHeight + Theme.space.lg * 2, 160)

            Column {
                id: tonightBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.space.lg
                spacing: Theme.space.sm

                Text {
                    text: I18n.t("今夜对局", "Tonight's Match")
                    color: Theme.warm.ink
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.titleMd
                    font.weight: Theme.weight.semibold
                }
                Text {
                    visible: root.activeRuns.length === 0
                    text: I18n.t("暂无进行中对局", "No active runs")
                    color: Theme.warm.muted
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    wrapMode: Text.WordWrap
                    width: parent.width
                    lineHeightMode: Text.ProportionalHeight
                    lineHeight: 1.45
                }

                Rectangle {
                    visible: root.activeRuns.length > 0
                    width: parent.width
                    radius: Theme.radius.md
                    color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.78)
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.42)
                    implicitHeight: primaryRunBody.implicitHeight + Theme.space.md * 2

                    Column {
                        id: primaryRunBody
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.space.md
                        spacing: Theme.space.xs

                        Row {
                            width: parent.width
                            spacing: Theme.space.xs
                            StatusBadge {
                                onLight: true
                                status: root.primaryActiveRun.status || "queued"
                            }
                            Text {
                                width: parent.width - 92
                                text: root._shortRunId(root.primaryActiveRun.run_id)
                                color: Theme.warm.ink
                                font.family: Theme.fontFamilies.mono
                                font.pixelSize: Theme.size.caption
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            width: parent.width
                            text: root._statusLabel(root.primaryActiveRun.status)
                                  + I18n.t(" · 事件 ", " · events ")
                                  + (root.primaryActiveRun.event_count || 0)
                            color: Theme.warm.muted
                            font.family: Theme.fontFamilies.sans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                            elide: Text.ElideRight
                        }

                        AppButton {
                            onLight: true
                            width: parent.width
                            height: 34
                            text: I18n.t("继续观察", "Continue")
                            variant: "primary"
                            onClicked: root._continueRun(root.primaryActiveRun)
                        }
                    }
                }

                Column {
                    visible: root.activeRuns.length > 1
                    width: parent.width
                    spacing: Theme.space.xs

                    Repeater {
                        model: root.activeRuns.slice(0, 5)
                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 34
                            radius: Theme.radius.sm
                            color: modelData.run_id === root.selectedActiveRunId
                                   ? Theme.withAlpha(Theme.warm.primary, 0.14)
                                   : Theme.withAlpha(Theme.warm.canvas, 0.46)
                            border.width: 1
                            border.color: modelData.run_id === root.selectedActiveRunId
                                          ? Theme.withAlpha(Theme.warm.primary, 0.42)
                                          : Theme.withAlpha(Theme.warm.ink, 0.08)

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.space.sm
                                anchors.rightMargin: Theme.space.sm
                                spacing: Theme.space.xs

                                Rectangle {
                                    width: 7; height: 7; radius: 4
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: Theme.statusColor(modelData.status || "queued")
                                }
                                Text {
                                    width: parent.width - 88
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: root._shortRunId(modelData.run_id)
                                    color: Theme.warm.bodyStrong
                                    font.family: Theme.fontFamilies.mono
                                    font.pixelSize: Theme.size.micro
                                    elide: Text.ElideRight
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: root._statusLabel(modelData.status)
                                    color: Theme.warm.muted
                                    font.family: Theme.fontFamilies.sans
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.size.micro
                                }
                            }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: root.selectedActiveRunId = modelData.run_id }
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.warm.canvas, 0.82)
            border.width: 1
            border.color: Theme.withAlpha(Theme.warm.ink, 0.08)
            implicitHeight: eventsBody.implicitHeight + Theme.space.lg * 2

            Column {
                id: eventsBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.space.lg
                spacing: Theme.space.md

                Text {
                    text: I18n.t("实时事件", "Live Events")
                    color: Theme.warm.ink
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.titleMd
                    font.weight: Theme.weight.semibold
                }
                Text {
                    width: parent.width
                    text: root.selectedActiveRunId === ""
                          ? I18n.t("选择一局进行中的对局后显示事件。", "Select an active run to preview events.")
                          : root._shortRunId(root.selectedActiveRunId)
                    color: Theme.warm.muted
                    font.family: Theme.fontFamilies.mono
                    font.pixelSize: Theme.size.micro
                    elide: Text.ElideRight
                }
                Repeater {
                    model: root._recentPreviewEvents().length > 0 ? root._recentPreviewEvents() : [null, null, null]
                    delegate: Row {
                        required property var modelData
                        width: eventsBody.width
                        spacing: Theme.space.sm
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            anchors.verticalCenter: parent.verticalCenter
                            color: modelData ? Theme.withAlpha(Theme.warm.primary, 0.72)
                                             : Theme.withAlpha(Theme.warm.ink, 0.18)
                        }
                        Text {
                            width: parent.width - 16
                            text: modelData ? root._eventText(modelData) : "—"
                            color: Theme.warm.mutedSoft
                            font.family: Theme.fontFamilies.sans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    // ----------------------------- Bottom tarot strip (overlapping linear slider)
    // Horizontal, scrollable, slight overlap + per-card hover lift. Newest role
    // goes leftmost (prepend to the model). Tap -> role detail (later phase).
    ListView {
        id: tarotList
        objectName: "tarotStrip"
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.xxl
        height: 236
        orientation: ListView.Horizontal
        spacing: -34                       // negative -> fish-scale overlap
        leftMargin: Theme.space.huge
        rightMargin: Theme.space.huge
        boundsBehavior: Flickable.StopAtBounds
        clip: false
        model: ["werewolf", "seer", "witch", "villager", "guard", "hunter"]

        delegate: Item {
            id: cardWrapper
            required property var modelData
            required property int index
            width: 152
            height: 228

            // Snap to the resting fan on creation; only animate on hover.
            property bool _ready: false
            Component.onCompleted: _ready = true

            // z changes without moving geometry -> hovered card rises to the top.
            z: cardHover.hovered ? 100 : index

            // Hover/tap detection lives on this STATIC wrapper (it never moves),
            // so lifting the art can't pull the card out from under the cursor —
            // that move-away was the cause of the flicker between two cards.
            HoverHandler { id: cardHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: { /* role detail page — later phase */ } }

            // The art itself lifts/tilts (y + rotation on the Image, pivoting at
            // its bottom edge); the wrapper stays put for stable hovering.
            Image {
                id: tarotArt
                width: parent.width
                height: parent.height
                x: 0
                y: cardHover.hovered ? -20 : (cardWrapper.index % 2 === 0 ? 0 : 6)
                transformOrigin: Item.Bottom
                rotation: cardHover.hovered ? 0 : (cardWrapper.index % 2 === 0 ? -1.5 : 1.5)
                Behavior on y { enabled: cardWrapper._ready; NumberAnimation { duration: 250; easing.type: Easing.OutBack; easing.overshoot: 1.2 } }
                Behavior on rotation { enabled: cardWrapper._ready; NumberAnimation { duration: 200; easing.type: Easing.OutQuart } }

                source: Illustrations.tarot(cardWrapper.modelData)
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                cache: true
                sourceSize.width: Math.max(1, Math.ceil(width * 2))
                sourceSize.height: Math.max(1, Math.ceil(height * 2))
                visible: status === Image.Ready

                // Composite shadow: warm-brown (blends into the parchment), and
                // height-reactive — tight "contact" shadow at rest, wide diffuse
                // "float" shadow on hover. (MultiEffect renders on the desktop
                // platform; the offscreen screenshot platform omits it.)
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.parchment.hoverShadow
                    shadowBlur: cardHover.hovered ? 1.2 : 0.4
                    shadowVerticalOffset: cardHover.hovered ? 16 : 4
                    Behavior on shadowBlur { NumberAnimation { duration: 200 } }
                    Behavior on shadowVerticalOffset { NumberAnimation { duration: 200 } }
                }

                // Localized role name on the card's EMPTY banner. The art ships
                // with a blank scroll so zh/en both render here (no baked text).
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    // Centre the name on the banner (banner centre ≈81% down the card).
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.verticalCenterOffset: parent.height * 0.31
                    text: root.roleName(cardWrapper.modelData)
                    color: Theme.parchment.cardTitleInk
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.titleMd   // bigger
                    font.weight: Theme.weight.bold           // bolder
                    font.letterSpacing: 2
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // Fallback when the art is missing or fails to load (never blank).
            Rectangle {
                anchors.fill: parent
                visible: tarotArt.status !== Image.Ready
                radius: 12
                color: Theme.warm.surfaceCreamStrong
                border.width: 1
                border.color: Theme.withAlpha(Theme.warm.ink, 0.12)
                Text {
                    anchors.centerIn: parent
                    text: Theme.humanizeRole(cardWrapper.modelData)
                    color: Theme.warm.muted
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                }
            }
        }
    }
}
