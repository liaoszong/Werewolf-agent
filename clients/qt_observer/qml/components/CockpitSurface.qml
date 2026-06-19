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
    property bool interruptVisible: false
    // Cursor-gated phase axis + current micro-action (from EventPresentationQueue).
    // Drive the top-band timeline; presentational only (passed in, never read backend).
    property var phaseTimeline: []
    property string currentAction: ""
    property Component perspectiveSlot: null
    property Component eventLogSlot: null
    property Component auditSlot: null
    property Component playbackSlot: null
    signal backRequested()
    signal interruptRequested()

    // 椭圆落位 = 背景图(table-day.png)自身比例，对齐画里的 6 个空座位。
    property real cx: 0.435
    property real cy: 0.585
    property real ringRx: 0.165
    property real ringRy: 0.195
    property real depthK: 0.12

    // 像素级落位：绑定到 PhaseBackground 实际绘制出的图矩形。
    readonly property real _cxPix: bg.paintedX + bg.paintedW * cx
    readonly property real _cyPix: bg.paintedY + bg.paintedH * cy
    readonly property real _rxPix: bg.paintedW * ringRx
    readonly property real _ryPix: bg.paintedH * ringRy
    readonly property real _avSize: bg.paintedW * 0.072

    // 逐座微调(fraction of paintedW/H)：手绘透视桌不是完美椭圆。仅 6 座生效。
    readonly property var _o6: [
        { dx:  0.003, dy:  0.003 },  // 顶
        { dx:  0.014, dy:  0.004 },  // 右上
        { dx:  0.020, dy: -0.028 },  // 右下
        { dx:  0.025, dy: -0.038 },  // 底
        { dx:  0.007, dy: -0.025 },  // 左下
        { dx:  0.021, dy:  0.001 }   // 左上
    ]
    function _offX(i) { return (players.length === 6 && _o6[i]) ? _o6[i].dx : 0 }
    function _offY(i) { return (players.length === 6 && _o6[i]) ? _o6[i].dy : 0 }

    // 名牌外移:上排两座(右上 idx1 / 左上 idx5)的名牌会被下排座(右下/左下)头像压住,
    // 把这两块名牌往外侧推(右上往右、左上往左)。头像/座号/票数徽章一律不动。仅 6 座生效。
    function _plateDx(i) {
        if (players.length !== 6) return 0
        if (i === 1) return root._avSize * 0.75    // 座2(右上)名牌往右
        if (i === 5) return -root._avSize * 0.75   // 座6(左上)名牌往左
        return 0
    }

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
    readonly property int _aliveCount: (players ? players.length : 0) - (deadIds ? deadIds.length : 0)
    readonly property var _speaker: {
        if (!speakingId) return null
        for (var i = 0; i < (players ? players.length : 0); i++)
            if (players[i] && players[i].player_id === speakingId) return players[i]
        return null
    }
    function _phaseTitle() {
        return phase === "night" ? I18n.t("夜晚行动", "Night Actions")
             : phase === "voting" ? I18n.t("投票表决", "Voting")
             : I18n.t("白天辩论", "Daytime Debate")
    }
    function _actionLabel() {
        switch (currentAction) {
        case "wolf":   return I18n.t("狼人行动", "Wolves act")
        case "seer":   return I18n.t("预言家查验", "Seer checks")
        case "witch":  return I18n.t("女巫用药", "Witch acts")
        case "speech": return I18n.t("发言阶段", "Speeches")
        case "vote":   return I18n.t("投票阶段", "Voting")
        default:       return ""
        }
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
                        text: I18n.t("← 返回首页", "← Home")
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
                Rectangle {
                    visible: root.interruptVisible
                    width: parent.width
                    height: visible ? 30 : 0
                    radius: Theme.radius.sm
                    color: interruptHover.hovered ? Theme.withAlpha(Theme.color.failed, 0.16) : "transparent"
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.color.failed, 0.58)
                    Text {
                        anchors.centerIn: parent
                        text: I18n.t("中断对局", "Interrupt Match")
                        color: Theme.color.failed
                        font.family: Theme.fontFamilies.sans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                        font.weight: Theme.weight.semibold
                    }
                    HoverHandler { id: interruptHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.interruptRequested() }
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

        // Contract anchor only; the visible center phase text is intentionally retired.
        PhaseIndicator {
            visible: false
            phase: root.phase
            round: root.round
        }

        // 椭圆座位铭牌环
        Repeater {
            model: root.players
            delegate: SeatCard {
                readonly property real _th: root._angle(index, root.players.length)
                readonly property real _sin: Math.sin(_th)
                cardW: root._avSize * 1.18 * (1 + root.depthK * _sin)
                plateDx: root._plateDx(index)
                x: root._cxPix + root._rxPix * Math.cos(_th) + bg.paintedW * root._offX(index) - width / 2
                y: root._cyPix + root._ryPix * _sin + bg.paintedH * root._offY(index) - cardW / 2
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

        // ---- 浮动阶段卡（满幅盘面上,无水平带底板）：阶段标题 · 仪表时间轴 · LIVE ----
        // 背景已满幅铺(PreserveAspectCrop),无 letterbox,故不再需要顶/底装饰横带。
        // HUD 一律作为羊皮纸浮卡压在画面上,与首页同语言。
        HudCard {
            id: phaseFloat
            anchors { top: parent.top; horizontalCenter: parent.horizontalCenter; topMargin: Theme.space.lg }
            width: Math.min(390, stage.width * 0.44)
            Column {
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 6
                // 标题行：☀/☾ 阶段标题 · 回合  +  LIVE
                Item {
                    width: parent.width; height: phTitle.implicitHeight
                    Row {
                        anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        Text {
                            text: root.phase === "night" ? "☾" : "☀"
                            color: root.phase === "night" ? Theme.parchment.goldLineSoft : Theme.parchment.terracottaDeep
                            font.pixelSize: 16
                        }
                        Text {
                            id: phTitle
                            text: root._phaseTitle() + "  ·  " + I18n.t("第 ", "R") + root.round + I18n.t(" 回合", "")
                            color: Theme.parchment.ink
                            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                            font.pixelSize: Theme.warmSize.titleMd; font.weight: Theme.weight.bold
                        }
                    }
                    Row {
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        spacing: 4
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 7; height: 7; radius: 3.5; color: Theme.parchment.terracotta
                            SequentialAnimation on opacity {
                                running: root.live; loops: Animation.Infinite
                                NumberAnimation { from: 1; to: 0.3; duration: 650 }
                                NumberAnimation { from: 0.3; to: 1; duration: 650 }
                            }
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.live ? "LIVE" : I18n.t("回放", "REPLAY")
                            color: Theme.parchment.terracottaDeep
                            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                            font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5; font.weight: Theme.weight.bold
                        }
                    }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.4) }
                // 仪表式时间轴（节点 + 当前高亮）
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 16
                    Repeater {
                        model: root.phaseTimeline
                        delegate: Row {
                            spacing: 5
                            readonly property bool _cur: index === (root.phaseTimeline ? root.phaseTimeline.length - 1 : -1)
                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                width: _cur ? 9 : 6; height: width; radius: width / 2
                                color: _cur ? Theme.parchment.terracotta : Theme.withAlpha(Theme.parchment.ink, 0.35)
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: (modelData.phase === "night" ? I18n.t("夜", "N") : I18n.t("日", "D")) + modelData.round
                                color: _cur ? Theme.parchment.ink : Theme.parchment.mutedInk
                                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                                font.pixelSize: Theme.size.micro; font.letterSpacing: 1
                                font.weight: _cur ? Theme.weight.bold : Theme.weight.regular
                            }
                        }
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: root._actionLabel() !== ""
                    text: "—  " + root._actionLabel() + "  —"
                    color: Theme.parchment.terracottaDeep
                    font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                    font.pixelSize: Theme.size.micro; font.letterSpacing: 1
                }
            }
        }

        // ---- 右侧信息塔（常驻,结构化）：当前票数 + 当前发言者 + 局势摘要 ----
        Column {
            id: infoTower
            anchors {
                right: parent.right; top: parent.top
                topMargin: Theme.space.lg; rightMargin: Theme.space.lg
            }
            width: Math.min(205, stage.width * 0.22)
            spacing: Theme.space.md

            // 1) 当前票数（常驻,空态占位 — Blocking 2）
            VotesPanel { width: parent.width; rows: root._voteRows; majority: root.majority }

            // 2) 当前发言者
            HudCard {
                width: parent.width
                Column {
                    anchors.left: parent.left; anchors.right: parent.right
                    spacing: 6
                    Text {
                        text: "↣  " + I18n.t("当前发言", "Speaker") + "  ↢"
                        color: Theme.parchment.goldLineSoft
                        font.family: Theme.fontFamilies.cjkSans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5; font.weight: Theme.weight.bold
                    }
                    Row {
                        visible: root._speaker !== null
                        spacing: Theme.space.sm
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 9; height: 9; radius: 4.5
                            color: root._speaker && root._speaker.display_role ? Theme.roleAccent(root._speaker.display_role) : Theme.parchment.terracotta
                        }
                        Column {
                            spacing: 0
                            Text {
                                text: root._speaker ? (root._speaker.player_id
                                      + (root._speaker.display_role && root._speaker.display_role !== "unknown"
                                         ? "  " + root._roleName(root._speaker.display_role) : "")) : ""
                                color: Theme.parchment.ink
                                font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                                font.pixelSize: Theme.size.body; font.weight: Theme.weight.bold
                            }
                            Text {
                                text: I18n.t("正在发言…", "is speaking…")
                                color: Theme.parchment.terracottaDeep
                                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                                font.pixelSize: Theme.size.micro
                            }
                        }
                    }
                    Text {
                        visible: root._speaker === null
                        text: I18n.t("暂无人发言", "No one speaking")
                        color: Theme.parchment.mutedInk
                        font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                        font.italic: true; font.pixelSize: Theme.size.caption
                    }
                }
            }

            // 3) 局势摘要
            HudCard {
                width: parent.width
                Column {
                    anchors.left: parent.left; anchors.right: parent.right
                    spacing: 6
                    Text {
                        text: "↣  " + I18n.t("局势", "Status") + "  ↢"
                        color: Theme.parchment.goldLineSoft
                        font.family: Theme.fontFamilies.cjkSans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5; font.weight: Theme.weight.bold
                    }
                    Row {
                        spacing: Theme.space.sm
                        Text {
                            text: I18n.t("存活", "Alive")
                            color: Theme.parchment.mutedInk
                            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                        }
                        Text {
                            text: root._aliveCount + " / " + (root.players ? root.players.length : 0)
                            color: Theme.parchment.ink
                            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                            font.pixelSize: Theme.size.body; font.weight: Theme.weight.bold
                        }
                    }
                    Text {
                        text: root._phaseTitle() + I18n.t("　·　第 ", "  ·  R") + root.round + I18n.t(" 回合", "")
                        color: Theme.parchment.inkSecondary
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                    }
                }
            }
        }

        // ---- 底部居中浮动控制托盘（满幅盘面上,无底板横带,贴舞台底悬浮）----
        Loader {
            id: playbackHost
            sourceComponent: root.playbackSlot
            x: (stage.width - width) / 2
            y: stage.height - height - Theme.space.lg
        }
    }
}
