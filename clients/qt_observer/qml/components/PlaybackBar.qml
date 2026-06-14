import QtQuick
import qt_observer

// Restrained parchment-embedded playback strip. Same EventPresentationQueue API as
// PlaybackControls (play/pause, speed 1x/2x/4x/Instant as a segmented control,
// next-phase, jump-to-latest) but styled to sit inside the board-game HUD instead
// of looking like a row of system buttons.
Rectangle {
    id: root
    objectName: "playbackBar"
    property var queue: null

    implicitHeight: 44
    implicitWidth: bar.implicitWidth + Theme.space.xl
    radius: Theme.radius.lg
    color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.94)
    border.width: 1
    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.7)

    // Inset gold hairline (matches HudCard's engraved look).
    Rectangle {
        anchors.fill: parent; anchors.margins: 3
        radius: Math.max(0, parent.radius - 2)
        color: "transparent"
        border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.35)
    }

    Row {
        id: bar
        anchors.centerIn: parent
        spacing: Theme.space.md

        // ---- Play / Pause ----
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 34; height: 30; radius: Theme.radius.sm
            color: playHover.hovered ? Theme.withAlpha(Theme.parchment.terracotta, 0.14) : "transparent"
            border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.6)
            readonly property bool _playing: root.queue && root.queue.playing
            // Drawn glyphs (Windows renders ▶/⏸ as colour emoji — avoid).
            Row {  // pause = two bars
                anchors.centerIn: parent; spacing: 3; visible: parent._playing
                Rectangle { width: 3.5; height: 13; radius: 1; color: Theme.parchment.ink }
                Rectangle { width: 3.5; height: 13; radius: 1; color: Theme.parchment.ink }
            }
            Canvas {  // play = triangle
                anchors.centerIn: parent; width: 13; height: 14; visible: !parent._playing
                onVisibleChanged: if (visible) requestPaint()
                onPaint: {
                    var c = getContext("2d"); c.reset()
                    c.fillStyle = Theme.parchment.ink
                    c.beginPath(); c.moveTo(0, 0); c.lineTo(13, 7); c.lineTo(0, 14); c.closePath(); c.fill()
                }
            }
            HoverHandler { id: playHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: {
                    if (!root.queue) return
                    if (root.queue.playing) root.queue.pause(); else root.queue.play()
                }
            }
        }

        // ---- Segmented speed control: 1x | 2x | 4x | Instant ----
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: segRow.implicitWidth; height: 30; radius: Theme.radius.sm
            color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.8)
            border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.6)
            clip: true
            Row {
                id: segRow
                Repeater {
                    model: [
                        { label: "1x", v: 1, instant: false },
                        { label: "2x", v: 2, instant: false },
                        { label: "4x", v: 4, instant: false },
                        { label: I18n.t("瞬时", "Now"), v: 0, instant: true }
                    ]
                    delegate: Item {
                        height: 30
                        width: segText.implicitWidth + Theme.space.lg
                        readonly property bool _active: root.queue
                            ? (modelData.instant ? root.queue.instant
                                                  : (!root.queue.instant && root.queue.speed === modelData.v))
                            : false
                        Rectangle {
                            anchors.fill: parent
                            color: parent._active ? Theme.parchment.terracotta
                                  : (segHover.hovered ? Theme.withAlpha(Theme.parchment.terracotta, 0.12) : "transparent")
                        }
                        // Segment divider (skip first).
                        Rectangle {
                            visible: index > 0
                            anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                            width: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.4)
                        }
                        Text {
                            id: segText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent._active ? "#ffffff" : Theme.parchment.inkSoft
                            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                            font.weight: parent._active ? Theme.weight.bold : Theme.weight.regular
                        }
                        HoverHandler { id: segHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler {
                            onTapped: {
                                if (!root.queue) return
                                if (modelData.instant) root.queue.setInstant()
                                else root.queue.setSpeed(modelData.v)
                            }
                        }
                    }
                }
            }
        }

        // ---- Divider ----
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 1; height: 20; color: Theme.withAlpha(Theme.parchment.goldLine, 0.4)
        }

        // ---- Next phase / Jump to latest (subtle text actions) ----
        Repeater {
            model: [
                { label: I18n.t("下一阶段", "Next phase"), act: "next" },
                { label: I18n.t("跳到最新", "Latest"), act: "end" }
            ]
            delegate: Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                height: 30; width: actText.implicitWidth + Theme.space.md
                radius: Theme.radius.sm
                color: actHover.hovered ? Theme.withAlpha(Theme.parchment.terracotta, 0.12) : "transparent"
                Text {
                    id: actText
                    anchors.centerIn: parent
                    text: modelData.label
                    color: Theme.parchment.inkSoft
                    font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                }
                HoverHandler { id: actHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: {
                        if (!root.queue) return
                        if (modelData.act === "next") root.queue.seekNextPhase()
                        else root.queue.seekQueueEnd()
                    }
                }
            }
        }

        // ---- AI thinking indicator ----
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 5
            visible: root.queue && root.queue.waiting
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 6; height: 6; radius: 3; color: Theme.parchment.terracotta
                SequentialAnimation on opacity {
                    running: root.queue && root.queue.waiting; loops: Animation.Infinite
                    NumberAnimation { from: 1; to: 0.3; duration: 600 }
                    NumberAnimation { from: 0.3; to: 1; duration: 600 }
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("AI 思考中…", "AI thinking…")
                color: Theme.parchment.mutedInk
                font.family: Theme.fontFamilies.mono
                font.pixelSize: Theme.size.micro
            }
        }
    }
}
