import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Warm game-client home (Phase 1 sample page). Layout: NavRail (left) +
// SceneBackground (warm illustration) + editorial hero + tarot strip + recent
// runs. ObserverClient bindings, navigation calls and objectNames preserved.
Item {
    id: root
    objectName: "homeView"

    // Day/night phase for the home backdrop (screenshot matrix toggles this).
    property string phase: "day"

    Component.onCompleted: ObserverClient.checkHealth()

    SceneBackground {
        id: scene
        phase: root.phase
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
            { key: "home",     label: I18n.t("今夜对局", "Tonight"),    glyph: "☾", enabled: true },
            { key: "setup",    label: I18n.t("开始对局", "New Match"),  glyph: "✦", enabled: true },
            { key: "seats",    label: I18n.t("席位一览", "Seats"),      glyph: "◍", enabled: false },
            { key: "events",   label: I18n.t("实时事件", "Events"),     glyph: "≋", enabled: false },
            { key: "history",  label: I18n.t("历史对局", "History"),    glyph: "❡", enabled: true },
            { key: "deck",     label: I18n.t("收藏牌库", "Card Deck"),  glyph: "🂠", enabled: false },
            { key: "settings", label: I18n.t("设置", "Settings"),       glyph: "⚙", enabled: true }
        ]
        onActivated: function(key) {
            if (key === "setup")
                root.StackView.view.parent.navigateSetup()
            else if (key === "history") {
                ObserverClient.refreshRuns()
                root.StackView.view.parent.navigateHistory()
            }
            else if (key === "settings")
                root.StackView.view.parent.navigateProviderSettings()
        }
    }

    // --------------------------------------------------------- Content column
    Flickable {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        contentHeight: content.implicitHeight + Theme.space.huge * 2
        clip: true

        Column {
            id: content
            x: Theme.space.huge
            y: Theme.space.huge
            width: Math.min(parent.width - Theme.space.huge * 2, 760)
            spacing: Theme.space.xxl

            // ----------------------------------------------------- (A) HERO
            Column {
                width: parent.width
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
                    text: I18n.t("观察 AI 玩家如何欺骗、推理与投票 —— 一夜一局。",
                                 "Watch AI agents deceive, deduce, and vote — one night at a time.")
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

                Row {
                    spacing: Theme.space.md
                    topPadding: Theme.space.sm
                    AppButton {
                        id: startNewMatchButton
                        objectName: "startNewMatchButton"
                        onLight: true
                        text: I18n.t("开始新对局", "Start New Match")
                        variant: "primary"
                        onClicked: root.StackView.view.parent.navigateSetup()
                    }
                    AppButton {
                        id: historyButton
                        objectName: "historyButton"
                        onLight: true
                        text: I18n.t("历史对局", "History")
                        variant: "secondary"
                        onClicked: {
                            ObserverClient.refreshRuns()
                            root.StackView.view.parent.navigateHistory()
                        }
                    }
                }
            }

            // ------------------------------------------ (B) TAROT IDENTITY STRIP
            Row {
                width: parent.width
                spacing: Theme.space.md
                Repeater {
                    model: ["werewolf", "seer", "witch", "villager", "guard", "hunter"]
                    delegate: Rectangle {
                        required property var modelData
                        width: (content.width - Theme.space.md * 5) / 6
                        height: width * 1.5
                        radius: Theme.radius.md
                        color: Theme.warm.surfaceCreamStrong
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.warm.ink, 0.08)
                        clip: true

                        Image {
                            id: tarotArt
                            anchors.fill: parent
                            source: Illustrations.tarot(modelData)
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            cache: true
                            visible: status === Image.Ready
                        }
                        // fallback: role name whenever the art is not loaded —
                        // missing url OR a real load error (Image.Error), never blank.
                        Text {
                            anchors.centerIn: parent
                            visible: tarotArt.status !== Image.Ready
                            text: Theme.humanizeRole(modelData)
                            color: Theme.warm.muted
                            font.family: Theme.fontFamilies.serif
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                        }
                    }
                }
            }

            // ------------------------------------------------ (C) RECENT RUNS
            AppCard {
                width: parent.width
                onLight: true
                implicitHeight: runsBody.implicitHeight + Theme.space.xxl * 2

                Column {
                    id: runsBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.xxl
                    spacing: Theme.space.lg

                    SectionHeader {
                        onLight: true
                        title: I18n.t("最近对局", "Recent Runs")
                    }

                    EmptyState {
                        width: parent.width
                        onLight: true
                        visible: ObserverClient.runItems.length === 0
                        title: I18n.t("暂无对局", "No matches yet")
                        subtitle: I18n.t("开始一局，在此实时观战。", "Start a new match to watch it unfold here.")
                    }

                    ListView {
                        id: recentRunsList
                        objectName: "recentRunsList"
                        width: parent.width
                        height: 180
                        clip: true
                        visible: ObserverClient.runItems.length > 0
                        model: ObserverClient.runItems
                        spacing: Theme.space.xs
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: Item {
                            required property var modelData
                            width: ListView.view.width
                            height: 44

                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.radius.md
                                color: hover.hovered ? Theme.warm.surfaceSoft : "transparent"
                                Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }

                                // Fixed two columns: run_id (mono, elide middle) | status badge (fixed width).
                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: Theme.space.md
                                    anchors.right: badgeCol.left
                                    anchors.rightMargin: Theme.space.md
                                    anchors.verticalCenter: parent.verticalCenter
                                    elide: Text.ElideMiddle
                                    text: modelData.run_id || ""
                                    color: Theme.warm.body
                                    font.family: Theme.fontFamilies.mono
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.size.small
                                }
                                Item {
                                    id: badgeCol
                                    width: 112
                                    anchors.right: parent.right
                                    anchors.rightMargin: Theme.space.md
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    StatusBadge {
                                        onLight: true
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        status: modelData.status || ""
                                    }
                                }
                            }

                            HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                            TapHandler {
                                onTapped: {
                                    ObserverClient.openRun(modelData.run_id)
                                    root.StackView.view.parent.navigateCockpit()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
