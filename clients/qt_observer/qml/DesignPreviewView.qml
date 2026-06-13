import QtQuick
import qt_observer
import "components"

// 静态宿主:烤死样例 + stub 控件驱动 CockpitSurface,不接后端、不开 run。
// 真相标记固定「设计样例」,绝不读后端运行态(execution mode)。
Item {
    id: root
    objectName: "designPreviewView"

    property string previewPhase: "day"      // day / night / voting
    property bool eightSeat: false           // synthetic 8 座 smoke(验环 N-可变,纯前端)

    readonly property var _six: [
        { player_id: "1", display_role: "werewolf", display_team: "werewolf", visibility: "visible", alive: true },
        { player_id: "2", display_role: "seer",     display_team: "village",  visibility: "visible", alive: true },
        { player_id: "3", display_role: "witch",    display_team: "village",  visibility: "visible", alive: true },
        { player_id: "4", display_role: "villager", display_team: "village",  visibility: "visible", alive: true },
        { player_id: "5", display_role: "guard",    display_team: "village",  visibility: "visible", alive: true },
        { player_id: "6", display_role: "hunter",   display_team: "village",  visibility: "visible", alive: false }
    ]
    readonly property var _eight: _six.concat([
        { player_id: "7", display_role: "villager", display_team: "village",  visibility: "visible", alive: true },
        { player_id: "8", display_role: "werewolf", display_team: "werewolf", visibility: "visible", alive: true }
    ])
    readonly property var _events: [
        { t: "00:01", text: I18n.t("第二天开始", "Day 2 begins") },
        { t: "00:07", text: I18n.t("4 号发言", "Seat 4 speaks") },
        { t: "00:09", text: I18n.t("4 号 → 5 号", "4 -> 5") },
        { t: "00:21", text: I18n.t("2 号附议", "2 seconds it") }
    ]

    Rectangle { anchors.fill: parent; color: Theme.warm.canvas }

    CockpitSurface {
        id: surface
        anchors.fill: parent
        players: root.eightSeat ? root._eight : root._six
        deadIds: ["6"]
        speakingId: "4"
        phase: root.previewPhase
        round: 2
        votes: root.previewPhase === "voting" ? [ { target: "5", count: 3 }, { target: "1", count: 2 } ] : []
        majority: root.previewPhase === "voting" ? 4 : 0
        dataSourceText: I18n.t("设计样例", "Design Sample")
        perspectiveText: I18n.t("上帝视角", "God's-Eye")
        perspectiveSlot: stubPerspective
        eventLogSlot: stubEventLog
        auditSlot: stubAudit
        playbackSlot: stubPlayback
        onBackRequested: root.StackView.view.parent.navigateHome()
    }

    Component {
        id: stubPerspective
        Rectangle {
            height: 28; radius: Theme.radius.pill
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.9); border.width: 1; border.color: Theme.warm.hairline
            Text {
                anchors.centerIn: parent
                text: I18n.t("视角:上帝视角 ▾", "View: God's-Eye ▾")
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.micro
            }
        }
    }
    Component {
        id: stubEventLog
        ListView {
            model: root._events; spacing: Theme.space.xs; clip: true
            delegate: Row {
                spacing: Theme.space.sm
                Text { text: modelData.t; color: Theme.warm.muted; font.family: Theme.fontFamilies.mono; font.pixelSize: Theme.size.micro }
                Text {
                    text: modelData.text; color: Theme.warm.body
                    font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.caption
                }
            }
        }
    }
    Component {
        id: stubAudit
        Rectangle {
            height: 30; radius: Theme.radius.sm
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.7); border.width: 1; border.color: Theme.warm.hairline
            Text {
                anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: Theme.space.sm
                text: I18n.t("▸ 证据 / 审计", "▸ Evidence / Audit")
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.micro
            }
        }
    }
    Component {
        id: stubPlayback
        Rectangle {
            implicitHeight: 36; radius: Theme.radius.md
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.92); border.width: 1; border.color: Theme.warm.primary
            Text {
                anchors.centerIn: parent
                text: "▶   ⏸   1x  2x  4x"
                color: Theme.warm.ink
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.caption
            }
        }
    }

    // 昼/夜/投票/(8座)切换(预览专用)
    Row {
        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: Theme.space.lg }
        spacing: Theme.space.sm
        Repeater {
            model: [ { k: "day", t: I18n.t("白天", "Day") }, { k: "night", t: I18n.t("黑夜", "Night") }, { k: "voting", t: I18n.t("投票", "Voting") } ]
            delegate: AppButton {
                objectName: "previewPhase_" + modelData.k
                text: modelData.t; onLight: true
                variant: root.previewPhase === modelData.k ? "primary" : "ghost"
                onClicked: root.previewPhase = modelData.k
            }
        }
        AppButton {
            objectName: "previewSeatToggle"
            text: root.eightSeat ? I18n.t("6 座", "6") : I18n.t("8 座", "8")
            variant: "ghost"; onLight: true
            onClicked: root.eightSeat = !root.eightSeat
        }
    }
}
