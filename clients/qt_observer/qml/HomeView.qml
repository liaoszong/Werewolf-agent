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
            width: Math.max(startNewMatchButton.implicitWidth, historyButton.implicitWidth)
            spacing: Theme.space.sm
            topPadding: Theme.space.lg
            AppButton {
                id: startNewMatchButton
                objectName: "startNewMatchButton"
                onLight: true
                width: parent.width
                text: I18n.t("进入今夜对局", "Enter Tonight's Match")
                variant: "primary"
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

    // ------------------------------------ Right floating panels (placeholder)
    // Semi-transparent parchment over the scene (no blur — Phase 1 rule). Static
    // structure for now; live "今夜对局 / 实时事件" data wired in a later phase.
    Column {
        id: rightPanels
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: Theme.space.xxl
        anchors.topMargin: Theme.space.xxl + 48
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
