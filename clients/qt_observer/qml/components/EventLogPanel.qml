import QtQuick
import QtQuick.Controls
import qt_observer

// Dark parchment Event Log for the god-view left column. Header (EVENT LOG · LIVE),
// a scroll of parchment entry blocks (round/phase chip + type + narrated text), and
// a "JUMP TO LATEST" affordance. Reads ObserverClient.projectionEvents live;
// previewRows injects synthetic entries for the static design preview (no backend).
//   previewRows item: { tag, text, current }
Item {
    id: root
    objectName: "eventLogPanel"

    property bool live: false
    property var previewRows: null          // non-null -> static/preview mode
    signal jumpToLatest()

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
    readonly property var _rows: {
        if (previewRows !== null) return previewRows
        var out = []
        var evs = ObserverClient.projectionEvents
        for (var i = 0; i < evs.length; i++) {
            var e = evs[i]
            var t = _evType(e)
            if (!t) continue
            var n = _narrate(e)
            if (!n || n === "") continue
            out.push({
                tag: "R" + (e.round !== undefined ? e.round : 0) + " · " + _typeLabel(t),
                text: n,
                current: (i === evs.length - 1)
            })
        }
        return out
    }

    Rectangle { anchors.fill: parent; color: "transparent" }

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
        // LIVE pill
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

    // ---- Entries ----
    ListView {
        id: list
        objectName: "eventLogList"
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: headRule.bottom; anchors.bottom: jumpBtn.top
        anchors.topMargin: Theme.space.sm; anchors.bottomMargin: Theme.space.sm
        clip: true
        spacing: Theme.space.sm
        model: root._rows
        onCountChanged: Qt.callLater(positionViewAtEnd)
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        delegate: Rectangle {
            width: ListView.view ? ListView.view.width : 0
            height: entryCol.implicitHeight + Theme.space.md
            radius: Theme.radius.sm
            color: modelData.current ? Theme.parchment.terracottaWash : Theme.parchment.parchment
            border.width: 1
            border.color: modelData.current ? Theme.withAlpha(Theme.parchment.terracotta, 0.6)
                                             : Theme.withAlpha(Theme.parchment.goldLine, 0.35)

            Column {
                id: entryCol
                anchors.left: parent.left; anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.space.sm
                spacing: 2
                Text {
                    text: modelData.tag
                    color: modelData.current ? Theme.parchment.terracottaDeep : Theme.parchment.mutedInk
                    font.family: Theme.fontFamilies.mono
                    font.pixelSize: Theme.size.micro; font.letterSpacing: 0.5
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: modelData.text
                    color: Theme.parchment.ink
                    font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                    font.pixelSize: Theme.size.small
                    lineHeight: 1.25
                }
            }
        }

        // Empty state on the dark panel.
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
