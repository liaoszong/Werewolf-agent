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
    property int majority: 0
    property string dataSourceText: ""
    property string perspectiveText: ""
    property Component perspectiveSlot: null
    property Component eventLogSlot: null
    property Component auditSlot: null
    property Component playbackSlot: null
    signal backRequested()

    // 椭圆落位(右区比例,待真机按 table-day.png 桌沿标定)
    property real cx: 0.40
    property real cy: 0.54
    property real ringRx: 0.32
    property real ringRy: 0.21       // ≈ Rx·cos(俯角)
    property real depthK: 0.16

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

        PhaseBackground { anchors.fill: parent; phase: root.phase }

        PhaseIndicator {
            phase: root.phase; round: root.round
            x: stage.width * root.cx - width / 2
            y: stage.height * root.cy - height / 2
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
                        return Qt.point(width * root.cx + width * root.ringRx * Math.cos(th),
                                        height * root.cy + height * root.ringRy * Math.sin(th))
                    }
                return null
            }
            onPaint: {
                var ctx = getContext("2d"); ctx.reset()
                if (!root.votes) return
                ctx.strokeStyle = Theme.warm.primary; ctx.lineWidth = 2
                ctx.setLineDash([6, 5]); ctx.globalAlpha = 0.7
                for (var k = 0; k < root.votes.length; k++) {
                    var pt = _seatPt(root.votes[k].target)
                    if (pt) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 5, 0, 2 * Math.PI); ctx.stroke() }
                }
            }
        }

        // 椭圆头像环
        Repeater {
            model: root.players
            delegate: CharacterAvatar {
                readonly property real _th: root._angle(index, root.players.length)
                readonly property real _sin: Math.sin(_th)
                diameter: Math.min(stage.width, stage.height) * 0.13 * (1 + root.depthK * _sin)
                x: stage.width * root.cx + stage.width * root.ringRx * Math.cos(_th) - width / 2
                y: stage.height * root.cy + stage.height * root.ringRy * _sin - diameter / 2
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
            visible: root.votes && root.votes.length > 0
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
                    model: root.votes
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
            x: stage.width * root.cx - width / 2
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
