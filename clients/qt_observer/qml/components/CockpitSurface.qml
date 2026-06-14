import QtQuick
import qt_observer

// 上帝视角圆桌观战盘面（手绘桌游 HUD 重做）。左 = 深色羊皮纸 Event Log 面板；
// 右 80% = 木桌背景 + SeatCard 座位铭牌环 + 右纵向 HUD（阶段卡/直播/当前票数）+
// 底部嵌入式回放控制条 + 桌面方向性投票线。数据/控件全经属性与插槽注入，绝不直连后端。
// 契约逐字保留：properties / slots / cx,cy,ringRx,ringRy,depthK / _angle / _o6 不变。
Item {
    id: root
    objectName: "cockpitSurface"

    property var players: []
    property var deadIds: []
    property string speakingId: ""
    property string phase: "day"
    property int round: 1
    property var votes: []
    // 展示用：按票数降序(队列只给未排序聚合;排序属表现层)
    readonly property var _votesSorted: (votes || []).slice().sort(function (a, b) { return b.count - a.count })
    property int majority: 0
    property string dataSourceText: ""
    property string perspectiveText: ""
    property bool live: false
    property Component perspectiveSlot: null
    property Component eventLogSlot: null
    property Component auditSlot: null
    property Component playbackSlot: null
    signal backRequested()

    // 椭圆落位 = 背景图(table-day.png)自身比例，对齐画里的桌沿(待真机微调)。
    property real cx: 0.40
    property real cy: 0.55
    property real ringRx: 0.275
    property real ringRy: 0.26
    property real depthK: 0.18

    // 像素级落位：绑定到 PhaseBackground 实际绘制出的图矩形。
    readonly property real _cxPix: bg.paintedX + bg.paintedW * cx
    readonly property real _cyPix: bg.paintedY + bg.paintedH * cy
    readonly property real _rxPix: bg.paintedW * ringRx
    readonly property real _ryPix: bg.paintedH * ringRy
    readonly property real _avSize: bg.paintedW * 0.10

    // 逐座微调(fraction of paintedW/H)：手绘透视桌不是完美椭圆。仅 6 座生效。
    readonly property var _o6: [
        { dx: -0.03, dy: -0.045 }, // 顶:狼人位
        { dx:  0.00, dy:  0.00 },  // 右上:预言家位
        { dx:  0.00, dy:  0.00 },  // 右下:女巫位
        { dx: -0.02, dy:  0.00 },  // 底:村民位
        { dx: -0.02, dy:  0.00 },  // 左下:守卫位
        { dx: -0.06, dy:  0.01 }   // 左上:猎人位
    ]
    function _offX(i) { return (players.length === 6 && _o6[i]) ? _o6[i].dx : 0 }
    function _offY(i) { return (players.length === 6 && _o6[i]) ? _o6[i].dy : 0 }

    function _angle(i, n) { return (-90 + i * 360 / Math.max(1, n)) * Math.PI / 180 }
    function _roleName(role) {
        var m = ({
            werewolf: I18n.t("狼人", "Werewolf"), seer: I18n.t("预言家", "Seer"),
            witch: I18n.t("女巫", "Witch"), villager: I18n.t("村民", "Villager"),
            guard: I18n.t("守卫", "Guard"), hunter: I18n.t("猎人", "Hunter")
        })
        return m[role] || role
    }
    function _voteCountFor(pid) {
        for (var i = 0; i < (votes ? votes.length : 0); i++)
            if (votes[i].target === pid) return votes[i].count
        return 0
    }
    // Vote rows enriched with a faction accent for the Current Votes panel.
    readonly property var _voteRows: {
        var out = []
        for (var i = 0; i < _votesSorted.length; i++) {
            var v = _votesSorted[i]
            var acc = Theme.parchment.mutedInk
            for (var j = 0; j < players.length; j++)
                if (players[j] && players[j].player_id === v.target
                        && players[j].display_role && players[j].display_role !== "unknown") {
                    acc = Theme.roleAccent(players[j].display_role); break
                }
            out.push({ target: v.target, count: v.count, accent: acc })
        }
        return out
    }

    Rectangle { anchors.fill: parent; color: Theme.warm.canvas }

    // ===================== 左区：深色羊皮纸 Event Log 面板 =====================
    Rectangle {
        id: leftCol
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Math.max(340, parent.width * 0.20)
        color: Theme.parchment.bgDark
        // Gold hairline on the inner edge.
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.withAlpha(Theme.parchment.goldLine, 0.5) }

        // Compact 中/EN toggle folded into the panel (the global top bar is hidden
        // on the cockpit). I18n is a module-global singleton — flipping it here is
        // presentational, no backend coupling.
        Row {
            anchors { right: parent.right; top: parent.top; margins: Theme.space.md }
            spacing: 0
            z: 5
            Repeater {
                model: [{ code: "zh", label: "中" }, { code: "en", label: "EN" }]
                delegate: Rectangle {
                    required property var modelData
                    width: 26; height: 20
                    radius: Theme.radius.sm
                    color: I18n.lang === modelData.code ? Theme.withAlpha(Theme.parchment.goldLine, 0.22) : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: I18n.lang === modelData.code ? Theme.parchment.goldText : Theme.parchment.textOnDarkSoft
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.micro
                        font.weight: I18n.lang === modelData.code ? Theme.weight.bold : Theme.weight.regular
                    }
                    TapHandler { onTapped: I18n.lang = modelData.code }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
        }

        Column {
            id: leftStack
            anchors.fill: parent
            anchors.margins: Theme.space.lg
            spacing: Theme.space.md

            // ---- Brand block (replaces the generic top toolbar) ----
            Row {
                width: parent.width
                spacing: Theme.space.sm
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 34; height: 34; radius: 17
                    color: "transparent"
                    border.width: 1.5; border.color: Theme.parchment.goldLine
                    Text { anchors.centerIn: parent; text: "◉"; color: Theme.parchment.goldText; font.pixelSize: 16 }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 0
                    Text {
                        text: I18n.t("上帝视角观察", "GOD'S-EYE OBSERVER")
                        color: Theme.parchment.textOnDark
                        font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                        font.pixelSize: Theme.warmSize.titleMd; font.weight: Theme.weight.bold; font.letterSpacing: 1
                    }
                    Text {
                        text: I18n.t("AI 对抗 · 社会推理", "AI vs AI · Social Deduction")
                        color: Theme.parchment.textOnDarkSoft
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.micro; font.letterSpacing: 1
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.35) }

            // ---- Back + run meta ----
            Row {
                width: parent.width
                spacing: Theme.space.md
                Rectangle {
                    objectName: "cockpitBackButton"
                    height: 28; width: backText.implicitWidth + Theme.space.lg
                    radius: Theme.radius.sm
                    color: backHover.hovered ? Theme.withAlpha(Theme.parchment.goldLine, 0.16) : "transparent"
                    border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.6)
                    Text {
                        id: backText; anchors.centerIn: parent
                        text: I18n.t("← 返回", "← Back")
                        color: Theme.parchment.goldText
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.caption
                    }
                    HoverHandler { id: backHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.backRequested() }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 0
                    Text {
                        visible: root.dataSourceText !== ""
                        text: root.dataSourceText
                        color: Theme.parchment.textOnDarkSoft
                        font.family: Theme.fontFamilies.mono; font.pixelSize: Theme.size.micro
                    }
                    Text {
                        visible: root.perspectiveText !== ""
                        text: root.perspectiveText
                        color: Theme.parchment.textOnDarkSoft
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.micro
                    }
                }
            }

            Loader { width: parent.width; sourceComponent: root.perspectiveSlot }

            Loader {
                id: eventLogLoader
                width: parent.width
                height: Math.max(0, leftStack.height - y - footer.height - leftStack.spacing)
                sourceComponent: root.eventLogSlot
            }

            // ---- Footer: spectating + audit slot ----
            Column {
                id: footer
                width: parent.width
                spacing: Theme.space.sm
                Rectangle { width: parent.width; height: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.35) }
                Row {
                    spacing: Theme.space.sm
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 7; height: 7; radius: 3.5; color: Theme.parchment.terracotta
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.live ? I18n.t("观战直播中", "SPECTATING LIVE") : I18n.t("回放观战", "REPLAY")
                        color: Theme.parchment.textOnDarkSoft
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5
                    }
                }
                Loader { width: parent.width; sourceComponent: root.auditSlot }
            }
        }
    }

    // ===================== 右区 80%：木桌主舞台 =====================
    Item {
        id: stage
        anchors { left: leftCol.right; top: parent.top; right: parent.right; bottom: parent.bottom }
        clip: true

        PhaseBackground { id: bg; anchors.fill: parent; phase: root.phase }

        // 桌面方向性投票线（细、克制；从桌心指向被投目标，领先者更实）。
        Canvas {
            id: arrows
            anchors.fill: parent
            property var v: root.votes
            property real pw: bg.paintedW
            property real ph: bg.paintedH
            onVChanged: requestPaint()
            onPwChanged: requestPaint()
            onPhChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            function _seatPt(pid) {
                for (var i = 0; i < root.players.length; i++)
                    if (root.players[i] && root.players[i].player_id === pid) {
                        var th = root._angle(i, root.players.length)
                        return Qt.point(root._cxPix + root._rxPix * Math.cos(th) + bg.paintedW * root._offX(i),
                                        root._cyPix + root._ryPix * Math.sin(th) + bg.paintedH * root._offY(i))
                    }
                return null
            }
            onPaint: {
                var ctx = getContext("2d"); ctx.reset()
                if (!root.votes || root.votes.length === 0) return
                var lead = 0
                for (var m = 0; m < root.votes.length; m++)
                    if (root.votes[m].count > lead) lead = root.votes[m].count
                var cxp = root._cxPix, cyp = root._cyPix
                for (var k = 0; k < root.votes.length; k++) {
                    var vt = root.votes[k]
                    var pt = _seatPt(vt.target)
                    if (!pt) continue
                    var isLead = (vt.count === lead && lead > 0)
                    // Stop short of the seat card so the line points at it, not through it.
                    var dx = pt.x - cxp, dy = pt.y - cyp
                    var len = Math.sqrt(dx * dx + dy * dy) || 1
                    var endx = pt.x - dx / len * (root._avSize * 0.62)
                    var endy = pt.y - dy / len * (root._avSize * 0.62)
                    ctx.strokeStyle = Theme.parchment.terracotta
                    ctx.lineWidth = isLead ? 2.4 : 1.4
                    ctx.globalAlpha = isLead ? 0.8 : 0.4
                    ctx.setLineDash(isLead ? [] : [6, 5])
                    // gentle curve via quadratic control offset perpendicular
                    var mx = (cxp + endx) / 2, my = (cyp + endy) / 2
                    var nx = -dy / len, ny = dx / len
                    var bow = len * 0.10
                    ctx.beginPath()
                    ctx.moveTo(cxp, cyp)
                    ctx.quadraticCurveTo(mx + nx * bow, my + ny * bow, endx, endy)
                    ctx.stroke()
                    // small arrowhead
                    ctx.setLineDash([])
                    var ang = Math.atan2(endy - (my + ny * bow), endx - (mx + nx * bow))
                    var ah = root._avSize * 0.16
                    ctx.beginPath()
                    ctx.moveTo(endx, endy)
                    ctx.lineTo(endx - ah * Math.cos(ang - 0.4), endy - ah * Math.sin(ang - 0.4))
                    ctx.moveTo(endx, endy)
                    ctx.lineTo(endx - ah * Math.cos(ang + 0.4), endy - ah * Math.sin(ang + 0.4))
                    ctx.stroke()
                }
            }
        }

        // 桌心阶段徽记
        PhaseIndicator {
            phase: root.phase; round: root.round
            x: root._cxPix - width / 2
            y: root._cyPix - height / 2
        }

        // 椭圆座位铭牌环
        Repeater {
            model: root.players
            delegate: SeatCard {
                readonly property real _th: root._angle(index, root.players.length)
                readonly property real _sin: Math.sin(_th)
                cardW: root._avSize * 1.4 * (1 + root.depthK * _sin)
                x: root._cxPix + root._rxPix * Math.cos(_th) + bg.paintedW * root._offX(index) - width / 2
                y: root._cyPix + root._ryPix * _sin + bg.paintedH * root._offY(index) - implicitHeight / 2
                z: 10 + _sin
                roleKey: (modelData.display_role && modelData.display_role !== "unknown") ? modelData.display_role : ""
                roleLabel: roleKey ? root._roleName(modelData.display_role) : ""
                seatLabel: modelData.player_id
                seatNumber: index + 1
                accent: roleKey ? Theme.roleAccent(modelData.display_role) : Theme.parchment.goldLine
                alive: root.deadIds.indexOf(modelData.player_id) < 0
                speaking: root.speakingId === modelData.player_id
                voteCount: root._voteCountFor(modelData.player_id)
            }
        }

        // ---- 右纵向 HUD 栈 ----
        Column {
            id: hud
            anchors { right: parent.right; top: parent.top; margins: Theme.space.lg }
            width: Math.min(258, stage.width * 0.25)
            spacing: Theme.space.md

            PhaseCard { width: parent.width; phase: root.phase; round: root.round }
            LiveStatusCard {
                width: parent.width
                liveText: root.dataSourceText
                live: root.live
                perspectiveLabel: root.perspectiveText
            }
            VotesPanel {
                width: parent.width
                visible: root._voteRows.length > 0
                rows: root._voteRows
                majority: root.majority
            }
        }

        // ---- 底部居中：嵌入式回放控制条（宿主插槽）----
        Loader {
            id: playbackHost
            anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: Theme.space.lg }
            sourceComponent: root.playbackSlot
        }
    }
}
