import QtQuick
import qt_observer

// P2-C-1 speech / event narration. Typewriter reveal of the PresentationEvent summary,
// keyed on current.event_id so a late projection back-fill (summary "" -> text) types in
// WITHOUT restarting (P1-A). Narrative in display sans; an L1 type tag + L3 "open in
// console" affordance form the inline 3-layer AI trace. Reads PresentationEvent fields
// only (current.summary / current.type / current.actor / current.event_id).
Item {
    id: root
    objectName: "speechTheater"

    property var current: ({})          // eventQueue.current (PresentationEvent)
    property var players: []             // ObserverClient.playerItems (for faction coloring)
    signal openInConsole()

    readonly property string _full: _narrate(current)
    readonly property string _type: (current && current.type) ? current.type : ""
    readonly property string _actor: (current && current.actor) ? current.actor : ""
    property string _evId: ""
    property int _shown: 0

    onCurrentChanged: {
        var id = (current && current.event_id) ? current.event_id : ""
        if (id !== _evId) {     // new event -> restart typewriter; same id (back-fill) -> keep
            _evId = id
            _shown = 0
        }
    }

    Timer {
        id: typeTimer
        interval: 26
        repeat: true
        running: root._shown < root._full.length
        onTriggered: root._shown = Math.min(root._full.length, root._shown + 1)
    }

    function _typeLabel(t) {
        var m = ({
            player_speech: I18n.t("发言", "Speech"),
            player_vote: I18n.t("投票", "Vote"),
            seer_check: I18n.t("查验", "Check"),
            werewolf_kill: I18n.t("狼刀", "Kill"),
            witch_save: I18n.t("解药", "Save"),
            witch_kill: I18n.t("毒药", "Poison"),
            witch_pass: I18n.t("弃药", "Pass"),
            player_died: I18n.t("死亡", "Death"),
            player_eliminated: I18n.t("出局", "Out"),
            role_revealed: I18n.t("亮牌", "Reveal"),
            role_assignment: I18n.t("分配", "Setup"),
            day_announcement: I18n.t("公告", "Notice"),
            game_over: I18n.t("终局", "End")
        })
        return m[t] || t
    }
    function _evType(ev) { return (ev && ev.type) ? ev.type : "" }
    function _evSummary(ev) { return (ev && ev.summary) ? ev.summary : "" }
    function _evActor(ev) { return (ev && ev.actor) ? ev.actor : "" }
    function _evTarget(ev) { return (ev && ev.target && ev.target !== "none") ? ev.target : "" }
    function _narrate(ev) {
        var t = _evType(ev), a = _evActor(ev), tg = _evTarget(ev)
        switch (t) {
        case "player_speech":     return _evSummary(ev)
        case "player_vote":       return tg ? I18n.t(a + " 投票给 " + tg, a + " votes for " + tg) : _evSummary(ev)
        case "werewolf_kill":     return tg ? I18n.t("狼队袭击了 " + tg, "Werewolves attack " + tg) : _evSummary(ev)
        case "seer_check":        return tg ? I18n.t("预言家 " + a + " 查验了 " + tg, "Seer " + a + " checks " + tg) : _evSummary(ev)
        case "witch_save":        return tg ? I18n.t("女巫 " + a + " 用解药救了 " + tg, "Witch " + a + " saves " + tg) : _evSummary(ev)
        case "witch_kill":        return tg ? I18n.t("女巫 " + a + " 用毒药毒了 " + tg, "Witch " + a + " poisons " + tg) : _evSummary(ev)
        case "witch_pass":        return I18n.t("女巫 " + a + " 没有用药", "Witch " + a + " uses no potion")
        case "player_died":       return tg ? I18n.t(tg + " 在夜里死亡", tg + " died in the night") : _evSummary(ev)
        case "player_eliminated": return tg ? I18n.t(tg + " 被投票出局", tg + " was voted out") : _evSummary(ev)
        case "role_assignment":   return I18n.t("身份已分配给所有玩家", "Roles assigned to all players")
        default:                  return _evSummary(ev) || _typeLabel(t)
        }
    }
    function _factionColor(pid) {
        for (var i = 0; i < players.length; i++)
            if (players[i] && players[i].player_id === pid && players[i].display_role && players[i].display_role !== "unknown")
                return Theme.roleAccent(players[i].display_role)
        return Theme.color.textMuted
    }
    function _richIds(text) {
        return text.replace(/p[1-6]/g, function (m) {
            return '<font color="' + _factionColor(m) + '">' + m + '</font>'
        })
    }

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.space.md

        // L1 — type tag + actor (mono, log register).
        Row {
            spacing: Theme.space.sm
            visible: root._type !== ""
            Rectangle {
                width: tag.implicitWidth + Theme.space.md
                height: tag.implicitHeight + Theme.space.xs
                radius: Theme.radius.sm
                color: Theme.color.surfaceInset
                border.width: 1
                border.color: Theme.color.border
                Text {
                    id: tag
                    anchors.centerIn: parent
                    text: root._typeLabel(root._type)
                    color: Theme.color.textSecondary
                    font.family: Theme.font.mono
                    font.pixelSize: Theme.size.micro
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root._actor
                color: root._factionColor(root._actor)
                font.family: Theme.font.mono
                font.pixelSize: Theme.size.caption
            }
        }

        // L2 — narrative summary, typewriter reveal (display sans).
        Row {
            width: parent.width
            spacing: 2
            visible: root._full !== ""
            Text {
                width: parent.width - cursor.width - 2
                wrapMode: Text.WordWrap
                textFormat: Text.RichText
                text: root._richIds(root._full.substring(0, root._shown))
                color: Theme.color.text
                font.family: Theme.font.display
                font.pixelSize: Theme.size.h2
                lineHeight: 1.35
            }
            Text {
                id: cursor
                text: "▌"
                color: Theme.color.textMuted
                font.pixelSize: Theme.size.h2
                visible: typeTimer.running
                SequentialAnimation on opacity {
                    running: typeTimer.running
                    loops: Animation.Infinite
                    NumberAnimation { from: 1; to: 0.2; duration: 500 }
                    NumberAnimation { from: 0.2; to: 1; duration: 500 }
                }
            }
        }

        // Placeholder when no transcript yet (live in-progress before game-log lands).
        Text {
            visible: root._type !== "" && root._full === ""
            text: I18n.t("· 等待文本 ·", "· awaiting transcript ·")
            color: Theme.color.textMuted
            font.family: Theme.font.mono
            font.pixelSize: Theme.size.caption
            opacity: 0.6
        }

        // L3 — open the full reasoning / audit trail in the evidence console.
        Text {
            text: I18n.t("▸ 在控制台查看推理与审计", "▸ open reasoning & audit in console")
            color: Theme.color.textMuted
            font.family: Theme.font.mono
            font.pixelSize: Theme.size.micro
            visible: root._type !== ""
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.openInConsole()
            }
        }
    }
}
