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

    Component.onCompleted: ObserverClient.checkHealth()

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
                ObserverClient.refreshRuns()
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

        Row {
            spacing: Theme.space.md
            topPadding: Theme.space.lg
            AppButton {
                id: startNewMatchButton
                objectName: "startNewMatchButton"
                onLight: true
                text: I18n.t("进入今夜对局", "Enter Tonight's Match")
                variant: "primary"
                onClicked: root.StackView.view.parent.navigateSetup()
            }
            AppButton {
                id: historyButton
                objectName: "historyButton"
                onLight: true
                text: I18n.t("查看昨夜复盘", "Last Night's Replay")
                variant: "secondary"
                onClicked: {
                    ObserverClient.refreshRuns()
                    root.StackView.view.parent.navigateHistory()
                }
            }
        }
    }

    // ------------------------------------ Right floating panels (placeholder)
    // Semi-transparent parchment over the scene (no blur — Phase 1 rule). Static
    // structure for now; live "今夜对局 / 实时事件" data wired in a later phase.
    Column {
        id: rightPanels
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: Theme.space.xl
        anchors.topMargin: Theme.space.xl
        width: 264
        spacing: Theme.space.lg

        // 今夜对局
        Rectangle {
            width: parent.width
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.warm.canvas, 0.82)
            border.width: 1
            border.color: Theme.withAlpha(Theme.warm.ink, 0.08)
            implicitHeight: tonightBody.implicitHeight + Theme.space.lg * 2

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
                    text: I18n.t("暂未开始 · 开始一局后在此查看", "Not started — begin a match to see it here")
                    color: Theme.warm.muted
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    wrapMode: Text.WordWrap
                    width: parent.width
                    lineHeightMode: Text.ProportionalHeight
                    lineHeight: 1.45
                }
            }
        }

        // 实时事件
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
                Repeater {
                    model: 3
                    delegate: Row {
                        width: eventsBody.width
                        spacing: Theme.space.sm
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            anchors.verticalCenter: parent.verticalCenter
                            color: Theme.withAlpha(Theme.warm.ink, 0.18)
                        }
                        Text {
                            text: "—"
                            color: Theme.warm.mutedSoft
                            font.family: Theme.fontFamilies.sans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
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
        anchors.bottomMargin: Theme.space.xl
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

            // Snap to the resting fan on creation; only animate on hover (so
            // returning to Home does NOT replay a right-to-left settle wave).
            property bool _ready: false
            Component.onCompleted: _ready = true

            z: cardHover.hovered ? 100 : index
            y: cardHover.hovered ? -18 : (index % 2 === 0 ? 0 : 5)
            rotation: cardHover.hovered ? 0 : (index % 2 === 0 ? -1.5 : 1.5)
            Behavior on y { enabled: cardWrapper._ready; NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
            Behavior on rotation { enabled: cardWrapper._ready; NumberAnimation { duration: 200; easing.type: Easing.OutExpo } }

            Image {
                id: tarotArt
                anchors.fill: parent
                source: Illustrations.tarot(cardWrapper.modelData)
                fillMode: Image.PreserveAspectFit
                asynchronous: false      // bundled + cached -> show instantly on re-entry (no pop)
                cache: true
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Qt.rgba(0, 0, 0, 0.32)
                    shadowBlur: 0.5
                    shadowVerticalOffset: 6
                }
            }

            // Fallback when the art is missing or fails to load (never blank).
            Rectangle {
                anchors.fill: parent
                visible: tarotArt.status !== Image.Ready
                radius: Theme.radius.md
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

            HoverHandler { id: cardHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: { /* role detail page — later phase */ } }
        }
    }
}
