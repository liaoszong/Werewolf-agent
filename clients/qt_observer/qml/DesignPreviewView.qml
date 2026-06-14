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
        { tag: "R2 · " + I18n.t("公告", "Notice"), text: I18n.t("第二天开始", "Day 2 begins"), current: false },
        { tag: "R2 · " + I18n.t("发言", "Speech"), text: I18n.t("p3 像真预言家，p1、p2 抱团更像狼。", "p3 reads as a real Seer; p1, p2 cluster like wolves."), current: false },
        { tag: "R2 · " + I18n.t("投票", "Vote"), text: "p4 → p5", current: false },
        { tag: "R2 · " + I18n.t("投票", "Vote"), text: "p2 → p5", current: false },
        { tag: "R2 · " + I18n.t("发言", "Speech"), text: I18n.t("p5 正在发言，反驳指控。", "p5 is speaking, rebutting the accusation."), current: true }
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
        perspectiveText: I18n.t("视角：god", "View: god")
        live: true
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
                text: I18n.t("视角：上帝视角  ▼", "View: God's-Eye  ▼")
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true; font.pixelSize: Theme.size.micro
            }
        }
    }
    Component {
        id: stubEventLog
        EventLogPanel { live: true; previewRows: root._events }
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
        // Static preview: a fake queue so the segmented speed control shows a
        // highlighted "2x" without a backend EventPresentationQueue.
        PlaybackBar {
            queue: QtObject {
                property bool playing: true
                property int speed: 2
                property bool instant: false
                property bool waiting: false
                function play() {} function pause() {}
                function setSpeed(v) {} function setInstant() {}
                function seekNextPhase() {} function seekQueueEnd() {}
            }
        }
    }

    // 昼/夜/投票/(8座)切换(预览专用)。抬高到回放条之上,避免与底部控制条重叠。
    Row {
        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: 84 }
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
