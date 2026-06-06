import QtQuick
import QtQuick.Controls
import qt_observer
import "."

// P2-C-1 bottom evidence console. Four states:
//   收起 Closed · 预览 Peek · 展开 Expand   -> human-readable localized match log + Seat Lens
//   审计 Audit                              -> the raw/technical honesty chain (trust boundary,
//                                              projection proof, raw event table, audit links).
// 预览/展开 deliberately show only what a spectator can read; the数据化 backend layer is one
// extra click away under 审计.  The Seat Lens drives ObserverClient.currentPerspective ONLY
// (P1-C); exiting it restores god.
Item {
    id: root
    objectName: "evidenceConsole"

    property int mode: 0                 // 0 Closed, 1 Peek, 2 Expand, 3 Audit
    property string perspective: "god"

    readonly property real fullHeight: parent ? parent.height : 640
    property real _userHeight: 0   // drag-to-resize override (0 = use the mode preset)
    onModeChanged: _userHeight = 0
    // Collapsed = a single quiet status line that blends into the stage; only a real
    // expansion raises the panel. Keeps the main theater the visual focus.
    height: mode === 0 ? 40
          : _userHeight > 0 ? _userHeight
          : mode === 1 ? Math.round(fullHeight * 0.32)
          : Math.round(fullHeight * 0.66)
    Behavior on height { enabled: !resizeHandle.pressed; NumberAnimation { duration: Theme.motion.base; easing.type: Easing.OutCubic } }

    // ---- localized narration helpers (shared shape: PresentationEvent OR enriched projection event) ----
    function _evType(ev) { return (ev && ev.type !== undefined && ev.type !== "") ? ev.type : ((ev && ev.payload) ? ev.payload.type : "") }
    function _evSummary(ev) { return (ev && ev.summary !== undefined) ? ev.summary : ((ev && ev.data) ? (ev.data.summary || "") : "") }
    function _evActor(ev) { return (ev && ev.actor) ? ev.actor : "" }
    function _evTarget(ev) { return (ev && ev.target && ev.target !== "none") ? ev.target : "" }
    function _typeLabel(t) {
        var m = ({
            player_speech: I18n.t("发言", "Speech"), player_vote: I18n.t("投票", "Vote"),
            seer_check: I18n.t("查验", "Check"), werewolf_kill: I18n.t("狼刀", "Kill"),
            witch_save: I18n.t("解药", "Save"), witch_kill: I18n.t("毒药", "Poison"),
            witch_pass: I18n.t("弃药", "Pass"), player_died: I18n.t("死亡", "Death"),
            player_eliminated: I18n.t("出局", "Out"), role_revealed: I18n.t("亮牌", "Reveal"),
            role_assignment: I18n.t("分配", "Setup"), day_announcement: I18n.t("公告", "Notice"),
            game_over: I18n.t("终局", "End")
        })
        return m[t] || t
    }
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
    function _phaseLabel(ev) {
        var t = _evType(ev)
        if (t === "player_vote" || t === "player_eliminated") return I18n.t("投票", "Vote")
        return (ev && ev.phase === "night") ? I18n.t("夜", "Night") : I18n.t("昼", "Day")
    }
    function _factionColor(pid) {
        var ps = ObserverClient.playerItems
        for (var i = 0; i < ps.length; i++)
            if (ps[i] && ps[i].player_id === pid && ps[i].display_role && ps[i].display_role !== "unknown")
                return Theme.roleAccent(ps[i].display_role)
        return Theme.color.textSecondary
    }
    function _richIds(text) {
        return text.replace(/p[1-6]/g, function (m) {
            return '<font color="' + _factionColor(m) + '">' + m + '</font>'
        })
    }
    // Only render events that carry real content (skips empty / undefined runtime ticks).
    readonly property var _logEvents: {
        var out = []
        var evs = ObserverClient.projectionEvents
        for (var i = 0; i < evs.length; i++) {
            var e = evs[i]
            if (!_evType(e))
                continue
            var n = _narrate(e)
            if (!n || n === "")
                continue
            out.push(e)
        }
        return out
    }

    // Backdrop + top hairline. Collapsed: transparent (the bar dissolves into the stage);
    // expanded: the raised surface so the log/audit content has a panel to sit on.
    Rectangle {
        anchors.fill: parent
        color: root.mode === 0 ? "transparent" : Theme.color.surface
        Behavior on color { ColorAnimation { duration: Theme.motion.base } }
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            height: 1
            color: root.mode === 0 ? Theme.withAlpha(Theme.color.border, 0.5) : Theme.color.border
        }
    }

    // Drag-to-resize handle on the top border (desktop affordance).
    MouseArea {
        id: resizeHandle
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 7
        visible: root.mode !== 0
        cursorShape: Qt.SizeVerCursor
        property real _h0: 0
        property real _gy0: 0
        onPressed: (mouse) => { root._userHeight = root.height; _h0 = root.height; _gy0 = mapToItem(null, mouse.x, mouse.y).y }
        onPositionChanged: (mouse) => {
            var gy = mapToItem(null, mouse.x, mouse.y).y
            root._userHeight = Math.max(120, Math.min(root.fullHeight, _h0 + (_gy0 - gy)))
        }
    }

    // ---- Top bar ----
    Item {
        id: topBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: Theme.space.lg
        anchors.rightMargin: Theme.space.lg
        height: root.mode === 0 ? 40 : 46

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.md
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("证据", "Evidence")
                color: root.mode === 0 ? Theme.color.textMuted : Theme.color.text
                font.family: Theme.font.family
                font.pixelSize: Theme.size.body
                font.weight: root.mode === 0 ? Theme.weight.medium : Theme.weight.semibold
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("视角：", "Lens: ") + root.perspective
                color: Theme.color.textMuted
                font.family: Theme.font.mono
                font.pixelSize: Theme.size.micro
            }
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.xs
            AppButton { text: I18n.t("收起", "Hide"); variant: root.mode === 0 ? "secondary" : "ghost"; onClicked: root.mode = 0 }
            AppButton { text: I18n.t("预览", "Peek"); variant: root.mode === 1 ? "secondary" : "ghost"; onClicked: root.mode = 1 }
            AppButton { text: I18n.t("展开", "Expand"); variant: root.mode === 2 ? "secondary" : "ghost"; onClicked: root.mode = 2 }
            AppButton { text: I18n.t("审计", "Audit"); variant: root.mode === 3 ? "secondary" : "ghost"; onClicked: root.mode = 3 }
        }
    }

    // ======================= Readable layer (预览 / 展开) =======================
    Item {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.space.lg
        anchors.rightMargin: Theme.space.lg
        anchors.bottomMargin: Theme.space.lg
        visible: root.mode === 1 || root.mode === 2

        // Seat Lens (perspective switch) — set currentPerspective only; never write ring.perspective.
        Row {
            id: lensRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.space.md
            PerspectiveSwitcher {
                id: perspectiveSwitcher
                objectName: "perspectiveSwitcher"
            }
            AppButton {
                text: I18n.t("回到上帝视角", "Back to God")
                variant: "ghost"
                visible: root.perspective !== "god"
                onClicked: ObserverClient.currentPerspective = "god"
            }
        }

        SectionHeader {
            id: logHeader
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: lensRow.bottom
            anchors.topMargin: Theme.space.md
            title: I18n.t("对局记录", "Match log")
            caption: I18n.t("当前视角下，每个角色说了什么、做了什么决定。", "What each seat said and decided, as visible to the current lens.")
        }

        ListView {
            id: logList
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: logHeader.bottom
            anchors.bottom: parent.bottom
            anchors.topMargin: Theme.space.sm
            clip: true
            model: root._logEvents
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            onCountChanged: Qt.callLater(positionViewAtEnd)   // keep the newest entry in view

            delegate: Item {
                width: logList.width
                height: Math.max(narText.implicitHeight, 18) + Theme.space.md
                readonly property bool isSpeech: root._evType(modelData) === "player_speech"

                Rectangle {
                    id: chip
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.topMargin: 1
                    width: chipText.implicitWidth + Theme.space.sm * 2
                    height: chipText.implicitHeight + Theme.space.xs
                    radius: Theme.radius.sm
                    color: Theme.color.surfaceInset
                    border.width: 1
                    border.color: Theme.color.border
                    Text {
                        id: chipText
                        anchors.centerIn: parent
                        text: "R" + (modelData.round !== undefined ? modelData.round : 0) + " · " + root._phaseLabel(modelData) + " · " + root._typeLabel(root._evType(modelData))
                        color: Theme.color.textMuted
                        font.family: Theme.font.mono
                        font.pixelSize: Theme.size.micro
                    }
                }
                Text {
                    id: narText
                    anchors.left: chip.right
                    anchors.leftMargin: Theme.space.md
                    anchors.right: parent.right
                    anchors.top: parent.top
                    wrapMode: Text.WordWrap
                    textFormat: Text.RichText
                    text: root._richIds(root._narrate(modelData))
                    color: parent.isSpeech ? Theme.color.text : Theme.color.textSecondary
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.small
                    lineHeight: 1.3
                }
            }

            EmptyState {
                anchors.centerIn: parent
                visible: logList.count === 0
                title: I18n.t("暂无记录", "No log yet")
                subtitle: I18n.t("对局开始后将在此显示。", "It will appear once the match starts.")
            }
        }
    }

    // ======================= Audit layer (审计) — raw/technical =======================
    Flickable {
        id: auditFlick
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.space.lg
        anchors.rightMargin: Theme.space.lg
        anchors.bottomMargin: Theme.space.lg
        visible: root.mode === 3
        clip: true
        contentWidth: width
        contentHeight: auditBody.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Column {
            id: auditBody
            width: auditFlick.width
            spacing: Theme.space.lg

            Text {
                text: I18n.t("原始数据 · 仅供核验", "Raw data · for verification")
                color: Theme.color.textMuted
                font.family: Theme.font.mono
                font.pixelSize: Theme.size.micro
            }
            Flow {
                width: parent.width
                spacing: Theme.space.md
                ViewBoundaryBadge {
                    perspective: ObserverClient.currentPerspective
                    contractVersion: ObserverClient.visibilityContractVersion
                    hiddenEventCount: ObserverClient.hiddenEventCount
                    hiddenSnapshotCount: ObserverClient.hiddenSnapshotCount
                }
                ProjectionProofPanel {
                    proof: ObserverClient.projectionProof
                    hiddenEventCount: ObserverClient.hiddenEventCount
                    hiddenSnapshotCount: ObserverClient.hiddenSnapshotCount
                }
            }
            SectionHeader {
                title: I18n.t("原始事件流", "Raw event stream")
                caption: I18n.t("按时间顺序的运行时事件（未本地化）。", "Chronological runtime events (not localized).")
            }
            EventTimeline {
                id: eventTimeline
                objectName: "eventTimeline"
                width: parent.width
                height: 200
            }
            SectionHeader {
                title: I18n.t("审计链接", "Audit Links")
                caption: I18n.t("追溯 prompt / provider / 失败到源记录。", "Trace prompt / provider / failures to source records.")
            }
            AuditLinksPanel {
                id: auditLinksPanel
                objectName: "auditLinksPanel"
                width: parent.width
            }
            Text {
                id: providerFailureSummary
                objectName: "providerFailureSummary"
                width: parent.width
                text: I18n.t("模型调用失败：详见审计链接。", "Provider failures: check audit links for details.")
                color: Theme.color.textMuted
                font.family: Theme.font.family
                font.pixelSize: Theme.size.caption
                wrapMode: Text.WordWrap
            }
        }
    }
}
