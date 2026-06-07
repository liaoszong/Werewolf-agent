import QtQuick
import QtQuick.Controls
import qt_observer

// P2-C-1 event waterfall — the right-hand "script feed". Each presented PresentationEvent
// is appended as a row; newest sits at the bottom with a typewriter reveal, history rows
// scroll UP, dim to a quiet gray, and fade into the stage at the top edge. The user can
// scroll back through the whole match; a "jump to latest" pill appears when they leave the
// bottom. Hovering a row re-arms its actor->target line on the seat ring (handled upstream).
// Reads PresentationEvent fields ONLY (current.type/actor/target/summary/round/phase/event_id).
Item {
    id: root
    objectName: "speechTheater"

    property var current: ({})          // eventQueue.current (PresentationEvent)
    property var players: []            // ObserverClient.playerItems (faction coloring)
    signal openInConsole()
    signal hoverEvent(string actor, string target, string type)  // re-arm ring line
    signal clearHover()

    // ----------------------------------------------------------------- helpers
    function _t(ev)  { return (ev && ev.type) ? ev.type : "" }
    function _a(ev)  { return (ev && ev.actor) ? ev.actor : "" }
    function _s(ev)  { return (ev && ev.summary) ? ev.summary : "" }
    function _tg(ev) { return (ev && ev.target && ev.target !== "none") ? ev.target : "" }

    function _typeLabel(t) {
        var m = ({
            player_speech: I18n.t("发言", "Speech"), player_vote: I18n.t("投票", "Vote"),
            seer_check: I18n.t("查验", "Check"), werewolf_kill: I18n.t("狼刀", "Kill"),
            witch_save: I18n.t("解药", "Save"), witch_kill: I18n.t("毒药", "Poison"),
            witch_poison: I18n.t("毒药", "Poison"),
            witch_pass: I18n.t("弃药", "Pass"), player_died: I18n.t("死亡", "Death"),
            player_eliminated: I18n.t("出局", "Out"), role_revealed: I18n.t("亮牌", "Reveal"),
            role_assignment: I18n.t("分配", "Setup"), day_announcement: I18n.t("公告", "Notice"),
            game_over: I18n.t("终局", "End")
        })
        return m[t] || t
    }
    // Localized role name (role_revealed carries the role only inside the English
    // game-log summary "{pid} revealed as {role}.", so we map it to Chinese here).
    function _roleZh(r) {
        switch (("" + r).toLowerCase()) {
        case "werewolf": return I18n.t("狼人", "Werewolf")
        case "seer": return I18n.t("预言家", "Seer")
        case "witch": return I18n.t("女巫", "Witch")
        case "villager": return I18n.t("村民", "Villager")
        default: return r
        }
    }
    function _phaseTag(ev) {
        var t = _t(ev)
        if (t === "role_assignment") return I18n.t("开局", "Setup")
        if (t === "game_over")       return I18n.t("终局", "End")
        var r = (ev && ev.round !== undefined && ev.round !== null) ? ev.round : 0
        if (t === "player_vote" || t === "player_eliminated") return I18n.t("投票 " + r, "Vote " + r)
        var ph = (ev && ev.phase) ? ev.phase : ""
        if (ph === "night") return I18n.t("夜 " + r, "Night " + r)
        if (ph === "day")   return I18n.t("日 " + r, "Day " + r)
        return "R" + r
    }
    function _narrate(ev) {
        var t = _t(ev), a = _a(ev), tg = _tg(ev)
        switch (t) {
        case "player_speech":     return _s(ev)
        case "player_vote":       return tg ? I18n.t(a + " 投票给 " + tg, a + " votes for " + tg) : _s(ev)
        case "werewolf_kill":     return tg ? I18n.t("狼队袭击了 " + tg, "Werewolves attack " + tg) : _s(ev)
        case "seer_check":        return tg ? I18n.t("预言家 " + a + " 查验了 " + tg, "Seer " + a + " checks " + tg) : _s(ev)
        case "witch_save":        return tg ? I18n.t("女巫 " + a + " 用解药救了 " + tg, "Witch " + a + " saves " + tg) : _s(ev)
        case "witch_kill":
        case "witch_poison":      return tg ? I18n.t("女巫 " + a + " 用毒药毒了 " + tg, "Witch " + a + " poisons " + tg) : _s(ev)
        case "witch_pass":        return I18n.t("女巫 " + a + " 没有用药", "Witch " + a + " uses no potion")
        case "player_died":       return tg ? I18n.t(tg + " 在夜里死亡", tg + " died in the night") : _s(ev)
        case "player_eliminated": return tg ? I18n.t(tg + " 被投票出局", tg + " was voted out") : _s(ev)
        case "role_revealed": {
            if (!tg) return _s(ev)
            var rm = _s(ev).match(/revealed as (\w+)/i)
            return rm ? I18n.t(tg + " 亮牌，身份为" + _roleZh(rm[1]), tg + " revealed as " + _roleZh(rm[1]))
                      : I18n.t(tg + " 亮牌", tg + " revealed")
        }
        case "role_assignment":   return I18n.t("身份已分配给所有玩家", "Roles assigned to all players")
        default:                  return _s(ev) || _typeLabel(t)
        }
    }
    function _factionColor(pid) {
        for (var i = 0; i < players.length; i++)
            if (players[i] && players[i].player_id === pid && players[i].display_role
                    && players[i].display_role !== "unknown")
                return Theme.roleAccent(players[i].display_role)
        return Theme.color.textSecondary
    }
    // Color + embolden player ids so red/blue strokes survive on the near-black stage
    // (thin colored glyphs halate; bold fixes it). dim=true desaturates for history rows.
    function _richIds(text, dim) {
        return text.replace(/p[1-6]/g, function (m) {
            var c = dim ? Theme.withAlpha(_factionColor(m), 0.65) : _factionColor(m)
            return '<b><font color="' + c + '">' + m + '</font></b>'
        })
    }

    // ----------------------------------------------------------- feed accumulation
    ListModel { id: feed }
    property string _activeId: ""
    property string _activeFull: ""
    property int _shown: 0

    onCurrentChanged: _ingest()
    function _ingest() {
        var id = (current && current.event_id) ? current.event_id : ""
        if (id === "")
            return
        var full = _narrate(current)
        if (id !== _activeId) {                  // new event -> append a row
            feed.append({
                evId: id, evType: _t(current), actor: _a(current), target: _tg(current),
                full: full, phaseTag: _phaseTag(current)
            })
            _activeId = id
            _activeFull = full
            _shown = 0
            if (list._follow)
                Qt.callLater(list.positionViewAtEnd)
        } else {                                  // same id (late projection back-fill) -> grow text
            _activeFull = full
            if (feed.count > 0)
                feed.setProperty(feed.count - 1, "full", full)
        }
    }

    // Clear the feed when the queue resets (run / perspective switch), mirroring the queue.
    Connections {
        target: ObserverClient
        function onCurrentRunChanged() { feed.clear(); root._activeId = ""; root._activeFull = ""; root._shown = 0 }
        function onCurrentPerspectiveChanged() { feed.clear(); root._activeId = ""; root._activeFull = ""; root._shown = 0 }
    }

    Timer {
        id: typeTimer
        interval: 26
        repeat: true
        running: root._shown < root._activeFull.length
        onTriggered: root._shown = Math.min(root._activeFull.length, root._shown + 1)
    }

    // -------------------------------------------------------------------- the feed
    ListView {
        id: list
        // Bottom-anchored "chat feed": short feeds hug the floor and grow upward; once the
        // content fills the column it pins to full height and scrolls.
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Math.min(contentHeight + topMargin + bottomMargin, parent.height)
        model: feed
        spacing: Theme.space.lg
        clip: true
        // Bottom margin so the active line never kisses the floor; top margin clears the mask.
        topMargin: Theme.space.xxl
        bottomMargin: Theme.space.sm

        property bool _follow: true
        onMovementEnded: _follow = atYEnd

        // History pushes upward smoothly; new rows fade + rise in.
        add: Transition {
            NumberAnimation { properties: "opacity"; from: 0.0; to: 1.0; duration: Theme.motion.base }
            NumberAnimation { properties: "scale"; from: 0.97; to: 1.0; duration: Theme.motion.base; easing.type: Easing.OutCubic }
        }
        displaced: Transition {
            NumberAnimation { properties: "y"; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
        }

        delegate: Item {
            id: rowItem
            width: ListView.view.width
            implicitHeight: rowCol.implicitHeight

            required property int index
            required property string evId
            required property string evType
            required property string actor
            required property string target
            required property string full
            required property string phaseTag

            readonly property bool isActive: index === ListView.view.count - 1
            opacity: isActive ? 1.0 : 0.78

            Column {
                id: rowCol
                width: parent.width
                spacing: Theme.space.xs

                // L1 — phase tag · type · actor
                Row {
                    spacing: Theme.space.sm
                    visible: rowItem.evType !== ""
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: phaseT.implicitWidth + Theme.space.sm
                        height: phaseT.implicitHeight + 3
                        radius: Theme.radius.sm
                        color: Theme.color.surfaceInset
                        Text {
                            id: phaseT
                            anchors.centerIn: parent
                            text: rowItem.phaseTag
                            color: Theme.color.textMuted
                            font.family: Theme.font.mono
                            font.pixelSize: Theme.size.micro
                            font.weight: Theme.weight.medium
                            renderType: Text.NativeRendering
                        }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root._typeLabel(rowItem.evType)
                        color: Theme.color.textSecondary
                        font.family: Theme.font.mono
                        font.pixelSize: Theme.size.micro
                        font.weight: Theme.weight.semibold
                        renderType: Text.NativeRendering
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: rowItem.actor !== "" && rowItem.actor !== "system"
                        text: rowItem.actor
                        color: root._factionColor(rowItem.actor)
                        font.family: Theme.font.mono
                        font.pixelSize: Theme.size.caption
                        font.weight: Theme.weight.bold
                        renderType: Text.NativeRendering
                    }
                }

                // L2 — narration. Active row types in bright + bold; history is quiet gray.
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.RichText
                    text: rowItem.isActive
                          ? root._richIds(root._activeFull.substring(0, root._shown), false)
                          : root._richIds(rowItem.full, true)
                    color: rowItem.isActive ? Theme.color.text : Theme.color.textMuted
                    font.family: Theme.font.display
                    font.pixelSize: rowItem.isActive ? Theme.size.h2 : Theme.size.body
                    font.weight: rowItem.isActive ? Theme.weight.semibold : Theme.weight.medium
                    lineHeight: 1.35
                    renderType: Text.NativeRendering
                }
            }

            // Hover a row -> re-arm its actor->target arrow on the ring; leave -> clear.
            HoverHandler {
                id: hover
                onHoveredChanged: {
                    if (hovered) root.hoverEvent(rowItem.actor, rowItem.target, rowItem.evType)
                    else root.clearHover()
                }
            }
            // Faint hover wash so the linked row reads as "selected".
            Rectangle {
                anchors.fill: parent
                anchors.margins: -Theme.space.xs
                z: -1
                radius: Theme.radius.sm
                color: Theme.color.surfaceInset
                opacity: hover.hovered ? 0.5 : 0.0
                Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
            }
        }
    }

    // Typewriter cursor pinned to the active line's tail (drawn over the list).
    Text {
        visible: typeTimer.running && list.count > 0
        text: "▌"
        color: Theme.color.textMuted
        font.pixelSize: Theme.size.h2
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.sm
        SequentialAnimation on opacity {
            running: typeTimer.running
            loops: Animation.Infinite
            NumberAnimation { from: 1; to: 0.2; duration: 500 }
            NumberAnimation { from: 0.2; to: 1; duration: 500 }
        }
    }

    // Top fade mask — history dissolves into the stage instead of hard-clipping.
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: Math.max(40, parent.height * 0.14)
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.color.bgBase }
            GradientStop { position: 1.0; color: Theme.withAlpha(Theme.color.bgBase, 0.0) }
        }
    }

    // Empty state.
    Text {
        anchors.centerIn: parent
        visible: list.count === 0
        text: I18n.t("· 等待剧情 ·", "· awaiting the story ·")
        color: Theme.color.textMuted
        font.family: Theme.font.mono
        font.pixelSize: Theme.size.caption
        renderType: Text.NativeRendering
        opacity: 0.6
    }

    // "Jump to latest" pill — appears only when the user has scrolled back.
    Rectangle {
        visible: !list._follow && list.count > 0
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.md
        implicitWidth: jumpRow.implicitWidth + Theme.space.lg * 2
        implicitHeight: jumpRow.implicitHeight + Theme.space.sm * 2
        radius: Theme.radius.pill
        color: Theme.color.surfaceAlt
        border.width: 1
        border.color: Theme.color.borderStrong
        Row {
            id: jumpRow
            anchors.centerIn: parent
            spacing: Theme.space.xs
            Text {
                text: I18n.t("↓ 最新动态", "↓ Latest")
                color: Theme.color.text
                font.family: Theme.font.family
                font.pixelSize: Theme.size.caption
                font.weight: Theme.weight.semibold
                renderType: Text.NativeRendering
            }
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: { list._follow = true; list.positionViewAtEnd() }
        }
    }

    // L3 — open the full reasoning / audit trail in the evidence console.
    Text {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Theme.space.xs
        text: I18n.t("▸ 控制台查看推理与审计", "▸ reasoning & audit in console")
        color: Theme.color.textMuted
        font.family: Theme.font.mono
        font.pixelSize: Theme.size.micro
        renderType: Text.NativeRendering
        visible: list.count > 0
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openInConsole()
        }
    }
}
