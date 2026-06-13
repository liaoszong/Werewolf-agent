import QtQuick
import qt_observer

// 表现型直播面:左 20% 实体列(品牌/数据源/视角/事件流/审计) + 右 80%(PhaseBackground +
// 椭圆头像环 + 悬浮 阶段/票数/倍速 + 多数线)。数据/控件全经属性与插槽注入,不直连后端 client。
Item {
    id: root
    objectName: "cockpitSurface"

    property var players: []
    property var deadIds: []
    property string speakingId: ""
    property string phase: "day"
    property int round: 1
    property var votes: []
    // 展示用:按票数降序(队列只给未排序聚合;排序属表现层)
    readonly property var _votesSorted: (votes || []).slice().sort(function (a, b) { return b.count - a.count })
    property int majority: 0
    property string dataSourceText: ""
    property string perspectiveText: ""
    property Component perspectiveSlot: null
    property Component eventLogSlot: null
    property Component auditSlot: null
    property Component playbackSlot: null
    signal backRequested()

    // 椭圆落位 = 背景图(table-day.png)自身比例,对齐画里的桌沿(待真机微调)。
    // cx/cy = 桌心在图中的比例;ringRx/ringRy = 头像环半径占图宽/高比例。
    property real cx: 0.40
    property real cy: 0.55
    property real ringRx: 0.30
    property real ringRy: 0.27
    property real depthK: 0.18

    // 像素级落位:绑定到 PhaseBackground 实际绘制出的图矩形(paintedX/Y/W/H),
    // 这样无论窗口/aspect 怎么变,头像永远落在画里的桌沿上。
    readonly property real _cxPix: bg.paintedX + bg.paintedW * cx
    readonly property real _cyPix: bg.paintedY + bg.paintedH * cy
    readonly property real _rxPix: bg.paintedW * ringRx
    readonly property real _ryPix: bg.paintedH * ringRy
    readonly property real _avSize: bg.paintedW * 0.10

    // 逐座微调(fraction of paintedW/H):手绘透视桌不是完美椭圆,按座位位置(非角色)
    // 把个别座位推到画里的实际座位上。仅 6 座(当前唯一真实局型)生效;其它座数走纯椭圆。
    readonly property var _o6: [
        { dx: -0.03, dy: -0.045 }, // 顶:狼人位 — 上+左(狼人再上移一点)
        { dx:  0.00, dy:  0.00 },  // 右上:预言家位
        { dx:  0.00, dy:  0.00 },  // 右下:女巫位
        { dx: -0.02, dy:  0.00 },  // 底:村民位 — 左(同守卫幅度)
        { dx: -0.02, dy:  0.00 },  // 左下:守卫位 — 略左
        { dx: -0.06, dy:  0.01 }   // 左上:猎人位 — 更左(到守卫左侧)+ 下到桌沿
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

    Rectangle { anchors.fill: parent; color: Theme.warm.canvas }

    // ===== 左区 20% =====
    Rectangle {
        id: leftCol
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: Math.max(340, parent.width * 0.20)
        color: Theme.warm.surfaceCard
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.warm.hairline }

        Column {
            id: leftStack
            anchors.fill: parent
            anchors.margins: Theme.space.lg
            spacing: Theme.space.md

            Text {
                text: I18n.t("上帝视角观察", "God's-Eye Observer")
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.titleMd; font.weight: Theme.weight.bold
            }
            AppButton {
                objectName: "cockpitBackButton"
                text: I18n.t("← 返回", "← Back"); variant: "ghost"; onLight: true
                onClicked: root.backRequested()
            }
            Text {
                visible: root.dataSourceText !== ""
                text: root.dataSourceText
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.mono; font.pixelSize: Theme.size.micro
            }
            Text {
                visible: root.perspectiveText !== ""
                text: root.perspectiveText
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.micro
            }
            Loader { width: parent.width; sourceComponent: root.perspectiveSlot }
            Loader {
                id: eventLogLoader
                width: parent.width
                height: Math.max(0, leftStack.height - y - auditLoader.height - leftStack.spacing)
                sourceComponent: root.eventLogSlot
            }
            Loader { id: auditLoader; width: parent.width; sourceComponent: root.auditSlot }
        }
    }

    // ===== 右区 80% =====
    Item {
        id: stage
        anchors { left: leftCol.right; top: parent.top; right: parent.right; bottom: parent.bottom }
        clip: true

        PhaseBackground { id: bg; anchors.fill: parent; phase: root.phase }

        PhaseIndicator {
            phase: root.phase; round: root.round
            x: root._cxPix - width / 2
            y: root._cyPix - height / 2
        }

        // 投票/行动箭头(座位间珊瑚虚线;Task 7 细化朝向)
        Canvas {
            id: arrows
            anchors.fill: parent
            property var v: root.votes
            onVChanged: requestPaint()
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
                if (!root.votes) return
                // 每个被投目标画一圈珊瑚虚线环,半径随票数增大;领先者填充更实。
                var lead = 0
                for (var m = 0; m < root.votes.length; m++)
                    if (root.votes[m].count > lead) lead = root.votes[m].count
                for (var k = 0; k < root.votes.length; k++) {
                    var v = root.votes[k]
                    var pt = _seatPt(v.target)
                    if (!pt) continue
                    var rad = root._avSize * 0.62 + v.count * (root._avSize * 0.10)
                    ctx.strokeStyle = Theme.warm.primary
                    ctx.lineWidth = (v.count === lead && lead > 0) ? 4 : 2
                    ctx.setLineDash([7, 5])
                    ctx.globalAlpha = (v.count === lead && lead > 0) ? 0.9 : 0.55
                    ctx.beginPath(); ctx.arc(pt.x, pt.y, rad, 0, 2 * Math.PI); ctx.stroke()
                }
            }
        }

        // 椭圆头像环
        Repeater {
            model: root.players
            delegate: CharacterAvatar {
                readonly property real _th: root._angle(index, root.players.length)
                readonly property real _sin: Math.sin(_th)
                diameter: root._avSize * (1 + root.depthK * _sin)
                x: root._cxPix + root._rxPix * Math.cos(_th) + bg.paintedW * root._offX(index) - width / 2
                y: root._cyPix + root._ryPix * _sin + bg.paintedH * root._offY(index) - diameter / 2
                z: 10 + _sin
                roleKey: (modelData.display_role && modelData.display_role !== "unknown") ? modelData.display_role : ""
                roleLabel: roleKey ? root._roleName(modelData.display_role) : ""
                seatLabel: modelData.player_id
                accent: roleKey ? Theme.roleAccent(modelData.display_role) : Theme.warm.hairline
                alive: root.deadIds.indexOf(modelData.player_id) < 0
                speaking: root.speakingId === modelData.player_id
            }
        }

        // 悬浮:阶段(右上)
        Rectangle {
            id: phaseChip
            anchors { right: parent.right; top: parent.top; margins: Theme.space.lg }
            width: stage.width * 0.28
            implicitHeight: phaseChipText.implicitHeight + Theme.space.md
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.9)
            border.width: 1; border.color: Theme.warm.hairline
            Text {
                id: phaseChipText; anchors.centerIn: parent
                text: (root.phase === "night" ? "☾ " + I18n.t("黑夜", "Night") : "☀ " + I18n.t("白天", "Day"))
                      + " · " + I18n.t("第 ", "R") + root.round
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.caption
            }
        }

        // 悬浮:当前票数(右)
        Rectangle {
            id: votesPanel
            anchors { right: parent.right; top: phaseChip.bottom; topMargin: Theme.space.sm; rightMargin: Theme.space.lg }
            width: stage.width * 0.28
            implicitHeight: votesCol.implicitHeight + Theme.space.lg
            radius: Theme.radius.lg
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.9)
            border.width: 1; border.color: Theme.warm.hairline
            visible: root._votesSorted.length > 0
            Column {
                id: votesCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.space.md }
                spacing: 2
                Text {
                    text: I18n.t("当前票数", "Current Votes")
                    color: Theme.warm.primary
                    font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                    font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
                }
                Repeater {
                    model: root._votesSorted
                    delegate: Text {
                        text: modelData.target + "  ●×" + modelData.count
                        color: Theme.warm.body
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                    }
                }
            }
        }

        // 悬浮:倍速/播放(右,票数下)— 宿主插槽
        Loader {
            anchors { right: parent.right; top: votesPanel.bottom; topMargin: Theme.space.sm; rightMargin: Theme.space.lg }
            width: stage.width * 0.28
            sourceComponent: root.playbackSlot
        }

        // 底部居中:多数线
        Rectangle {
            visible: root.majority > 0
            anchors { bottom: parent.bottom; bottomMargin: Theme.space.lg }
            x: root._cxPix - width / 2
            implicitWidth: majText.implicitWidth + Theme.space.xxxl
            implicitHeight: majText.implicitHeight + Theme.space.sm
            radius: Theme.radius.pill
            color: Theme.withAlpha(Theme.warm.surfaceDark, 0.55)
            Text {
                id: majText; anchors.centerIn: parent
                text: "──  " + I18n.t("多数线 ", "Majority ") + root.majority + "  ──"
                color: Theme.warm.canvas
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.caption
            }
        }
    }
}
