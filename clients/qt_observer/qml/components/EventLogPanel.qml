import QtQuick
import QtQuick.Controls
import qt_observer

// Dark parchment Event Log for the god-view left column. Header (EVENT LOG · LIVE),
// a scroll of parchment entry blocks (round/phase chip + type + narrated text), and
// a "JUMP TO LATEST" affordance.
//
// SYNC CONTRACT: the log renders ONLY from `events` — the playback queue's
// cursor-truncated presentedEvents (TheaterView binds eventQueue.presentedEvents).
// It NEVER reads the full enriched projection stream directly, so an entry appears
// in the log exactly when its event lands on the stage (same cursor, same pace, same
// pause/seek). New entries are appended to an internal ListModel one-by-one and
// fade in (no instant materialise / waterfall dump). previewRows injects synthetic
// entries for the static design preview (no backend).
Item {
    id: root
    objectName: "eventLogPanel"

    property bool live: false
    property var events: []                  // queue.presentedEvents (cursor-gated)
    property var previewRows: null           // non-null -> static/preview mode
    signal jumpToLatest()

    onEventsChanged: Qt.callLater(_sync)
    onPreviewRowsChanged: Qt.callLater(_sync)
    Component.onCompleted: _sync()

    // ---- compact inline narration (UI strings; mirrors EvidenceConsole labels) ----
    function _typeLabel(t) {
        var m = ({
            player_speech: I18n.t("发言", "Speech"), player_vote: I18n.t("投票", "Vote"),
            seer_check: I18n.t("查验", "Check"), werewolf_kill: I18n.t("狼刀", "Kill"),
            witch_save: I18n.t("解药", "Save"), witch_kill: I18n.t("毒药", "Poison"),
            witch_poison: I18n.t("毒药", "Poison"), witch_pass: I18n.t("弃药", "Pass"),
            player_died: I18n.t("死亡", "Death"), player_eliminated: I18n.t("出局", "Out"),
            role_revealed: I18n.t("亮牌", "Reveal"), role_assignment: I18n.t("分配", "Setup"),
            day_announcement: I18n.t("公告", "Notice"), game_over: I18n.t("终局", "End")
        })
        return m[t] || t
    }
    // Small per-type emblem: a tinted disc + a safe (non-emoji) glyph.
    function _typeColor(t) {
        switch (t) {
        case "player_speech":  return Theme.parchment.inkSoft
        case "player_vote":    return Theme.parchment.terracotta
        case "werewolf_kill":  return Theme.color.werewolf
        case "seer_check":     return Theme.color.seer
        case "witch_save":     return Theme.parchment.alive
        case "witch_kill":
        case "witch_poison":   return Theme.color.witch
        case "player_died":
        case "player_eliminated": return Theme.parchment.eliminated
        case "role_revealed":  return Theme.parchment.goldLineSoft
        default:               return Theme.parchment.mutedInk
        }
    }
    function _typeGlyph(t) {
        switch (t) {
        case "player_speech":  return "❝"
        case "player_vote":    return "✓"
        case "werewolf_kill":  return "✕"
        case "seer_check":     return "?"
        case "witch_save":     return "✚"
        case "witch_kill":
        case "witch_poison":   return "✕"
        case "player_died":
        case "player_eliminated": return "✝"
        case "role_revealed":  return "✦"
        default:               return "•"
        }
    }
    function _evType(ev) { return (ev && ev.type !== undefined && ev.type !== "") ? ev.type : ((ev && ev.payload) ? ev.payload.type : "") }
    function _evSummary(ev) { return (ev && ev.summary !== undefined) ? ev.summary : ((ev && ev.data) ? (ev.data.summary || "") : "") }
    function _narrate(ev) {
        var t = _evType(ev), a = (ev && ev.actor) ? ev.actor : "", tg = (ev && ev.target && ev.target !== "none") ? ev.target : ""
        switch (t) {
        case "player_speech":     return _evSummary(ev)
        case "player_vote":       return tg ? (a + " → " + tg) : _evSummary(ev)
        case "werewolf_kill":     return tg ? I18n.t("狼队袭击 " + tg, "Wolves attack " + tg) : _evSummary(ev)
        case "seer_check":        return tg ? (a + " " + I18n.t("查验", "checks") + " " + tg) : _evSummary(ev)
        case "witch_save":        return tg ? I18n.t("解药救 " + tg, "Saves " + tg) : _evSummary(ev)
        case "witch_kill":
        case "witch_poison":      return tg ? I18n.t("毒药毒 " + tg, "Poisons " + tg) : _evSummary(ev)
        case "player_eliminated": return tg ? I18n.t(tg + " 被投票出局", tg + " voted out") : _evSummary(ev)
        case "player_died":       return tg ? I18n.t(tg + " 夜里死亡", tg + " died at night") : _evSummary(ev)
        case "role_assignment":   return I18n.t("身份已分配", "Roles assigned")
        default:                  return _evSummary(ev) || _typeLabel(t)
        }
    }
    // Narrated rows in reveal order: [{ tag, text }] (current = last, set during _sync).
    function _computeRows() {
        if (previewRows !== null) return previewRows
        var src = events || []
        var out = []
        for (var i = 0; i < src.length; i++) {
            var t = _evType(src[i])
            if (!t) continue
            var n = _narrate(src[i])
            if (!n || n === "") continue
            out.push({ tag: "R" + (src[i].round !== undefined ? src[i].round : 0) + " · " + _typeLabel(t),
                       text: n, type: t })
        }
        return out
    }

    // Incremental sync: append only the NEW tail rows so the bottom entry fades in
    // one at a time; rebuild only on a shrink (reset / new generation / language flip).
    ListModel { id: _logModel }
    function _sync() {
        var rows = _computeRows()
        if (rows.length < _logModel.count)
            _logModel.clear()
        if (_logModel.count > 0)
            _logModel.setProperty(_logModel.count - 1, "current", false)
        for (var i = _logModel.count; i < rows.length; i++)
            _logModel.append({ tag: rows[i].tag, text: rows[i].text, type: rows[i].type || "", current: false })
        if (_logModel.count > 0)
            _logModel.setProperty(_logModel.count - 1, "current", true)
    }
    // Re-localize the whole log when the language flips.
    Connections {
        target: I18n
        function onLangChanged() { _logModel.clear(); _sync() }
    }

    // ---- Header: EVENT LOG · LIVE ----
    Item {
        id: header
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        height: 26
        Row {
            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.sm
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "✦"
                color: Theme.parchment.goldLine
                font.pixelSize: Theme.size.caption
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("事件日志", "EVENT LOG")
                color: Theme.parchment.goldText
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.caption; font.letterSpacing: 2; font.weight: Theme.weight.bold
            }
        }
        Rectangle {
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            width: liveRow.implicitWidth + Theme.space.md; height: 18
            radius: Theme.radius.sm
            color: "transparent"
            border.width: 1; border.color: Theme.withAlpha(Theme.parchment.terracotta, 0.7)
            Row {
                id: liveRow; anchors.centerIn: parent; spacing: 4
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 6; height: 6; radius: 3; color: Theme.parchment.terracotta
                    SequentialAnimation on opacity {
                        running: root.live; loops: Animation.Infinite
                        NumberAnimation { from: 1; to: 0.3; duration: 650 }
                        NumberAnimation { from: 0.3; to: 1; duration: 650 }
                    }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.live ? "LIVE" : I18n.t("回放", "REPLAY")
                    color: Theme.parchment.terracotta
                    font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                    font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5; font.weight: Theme.weight.bold
                }
            }
        }
    }

    Rectangle {
        id: headRule
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: header.bottom
        anchors.topMargin: 4
        height: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.45)
    }

    // ---- Entries (incremental, synced to the playback cursor) ----
    ListView {
        id: list
        objectName: "eventLogList"
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: headRule.bottom; anchors.bottom: jumpBtn.top
        anchors.topMargin: Theme.space.sm; anchors.bottomMargin: Theme.space.sm
        clip: true
        spacing: Theme.space.sm
        model: _logModel
        onCountChanged: Qt.callLater(positionViewAtEnd)   // keep the newest in view as it reveals
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        // Smooth one-at-a-time reveal: each newly-appended entry fades + slides in.
        add: Transition {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 240; easing.type: Easing.OutCubic }
            NumberAnimation { property: "x"; from: 16; to: 0; duration: 260; easing.type: Easing.OutCubic }
        }
        displaced: Transition { NumberAnimation { properties: "y"; duration: 200; easing.type: Easing.OutCubic } }

        delegate: Item {
            width: ListView.view ? ListView.view.width : 0
            height: card.height

            // left accent rule — terracotta for the current event, faint gold else
            Rectangle {
                anchors { left: card.left; top: card.top; bottom: card.bottom }
                width: 3; radius: 1.5
                color: model.current ? Theme.parchment.terracotta : Theme.withAlpha(Theme.parchment.goldLine, 0.4)
            }

            Rectangle {
                id: card
                anchors.left: parent.left; anchors.right: parent.right
                anchors.leftMargin: 3
                height: entryRow.implicitHeight + Theme.space.md
                radius: Theme.radius.sm
                gradient: Gradient {
                    GradientStop { position: 0.0; color: model.current ? Theme.parchment.terracottaWash : Qt.lighter(Theme.parchment.parchment, 1.03) }
                    GradientStop { position: 1.0; color: model.current ? Qt.darker(Theme.parchment.terracottaWash, 1.04) : Qt.darker(Theme.parchment.parchment, 1.02) }
                }
                border.width: 1
                border.color: model.current ? Theme.withAlpha(Theme.parchment.terracotta, 0.6)
                                             : Theme.withAlpha(Theme.parchment.goldLine, 0.32)
                clip: true
                Image { anchors.fill: parent; source: Illustrations.texParchment; fillMode: Image.Tile; opacity: 0.55 }

                Row {
                    id: entryRow
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.space.sm
                    spacing: Theme.space.sm

                    // type emblem
                    Rectangle {
                        width: 22; height: 22; radius: 11
                        anchors.top: parent.top; anchors.topMargin: 1
                        color: Theme.withAlpha(root._typeColor(model.type), 0.16)
                        border.width: 1; border.color: Theme.withAlpha(root._typeColor(model.type), 0.6)
                        Text {
                            anchors.centerIn: parent
                            text: root._typeGlyph(model.type)
                            color: root._typeColor(model.type)
                            font.pixelSize: Theme.size.caption
                        }
                    }

                    Column {
                        width: parent.width - 22 - Theme.space.sm
                        spacing: 2
                        Text {
                            text: model.tag
                            color: model.current ? Theme.parchment.terracottaDeep : Theme.parchment.mutedInk
                            font.family: Theme.fontFamilies.mono
                            font.pixelSize: Theme.size.micro; font.letterSpacing: 0.5
                        }
                        Text {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            text: model.text
                            color: Theme.parchment.ink
                            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                            font.pixelSize: Theme.size.small
                            lineHeight: 1.25
                        }
                    }
                }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: list.count === 0
            width: parent.width - Theme.space.lg
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: I18n.t("暂无事件 — 对局开始后在此显示。", "No events yet — they appear once the match starts.")
            color: Theme.parchment.textOnDarkSoft
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.pixelSize: Theme.size.small
        }
    }

    // ---- Jump to latest ----
    Rectangle {
        id: jumpBtn
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 30
        radius: Theme.radius.sm
        color: "transparent"
        border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.6)
        Text {
            anchors.centerIn: parent
            text: I18n.t("跳到最新  ↓", "JUMP TO LATEST  ↓")
            color: Theme.parchment.goldText
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5
        }
        TapHandler { onTapped: { list.positionViewAtEnd(); root.jumpToLatest() } }
        HoverHandler { cursorShape: Qt.PointingHandCursor }
    }
}
