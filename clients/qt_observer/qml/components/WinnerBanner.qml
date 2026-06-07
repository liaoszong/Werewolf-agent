import QtQuick
import qt_observer

// P2-D §7.2 — the freeze-beat ceremony banner. A faction-colored headline announcing
// the winner, with the honesty chain underneath (end_round · margin · source_label).
// Drops in on the freeze beat; shrinks to a quiet report header in the report state.
// All copy via I18n.t(zh, en); only Theme.* tokens.
Item {
    id: root
    objectName: "winnerBanner"

    property var result: ({})
    // light = rendered on the warm-beige report canvas (deeper faction colors,
    // white card + hairline); default false = dark freeze-beat ceremony.
    property bool light: false

    readonly property string _winner: (result && result.winner) ? ("" + result.winner) : ""
    readonly property color _accent: light
        ? (_winner === "werewolf"
            ? Theme.report.winWerewolf
            : (_winner === "villager" ? Theme.report.winVillager : Theme.report.accent))
        : (_winner === "werewolf"
            ? Theme.color.teamWolf
            : (_winner === "villager" ? Theme.color.teamGood : Theme.color.completed))

    function _winnerLabel(w) {
        if (w === "werewolf")
            return I18n.t("狼人阵营胜利", "Werewolves win")
        if (w === "villager")
            return I18n.t("好人阵营胜利", "Villagers win")
        return I18n.t("对局结束", "Game over")
    }

    implicitHeight: banner.implicitHeight + Theme.space.lg * 2

    Rectangle {
        id: banner
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        implicitHeight: col.implicitHeight + Theme.space.xl * 2
        radius: Theme.radius.lg
        color: root.light ? Theme.report.card : Theme.withAlpha(root._accent, 0.10)
        border.width: 1
        border.color: root.light
            ? Theme.report.border
            : Theme.withAlpha(root._accent, 0.40)

        // Drop-in for the freeze beat. The banner's vertical position is owned by
        // anchors.verticalCenter, so the drop is done via a Translate transform (NOT
        // by animating `y`, which would conflict with the anchor and be ignored).
        opacity: 0
        transform: Translate { id: dropOffset; y: -16 }
        Component.onCompleted: dropIn.start()
        ParallelAnimation {
            id: dropIn
            NumberAnimation { target: banner; property: "opacity"; from: 0; to: 1; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
            NumberAnimation { target: dropOffset; property: "y"; from: -16; to: 0; duration: Theme.motion.slow; easing.type: Easing.OutBack }
        }

        Column {
            id: col
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: Theme.space.xl
            spacing: Theme.space.sm

            Text {
                width: parent.width
                text: root._winnerLabel(root._winner)
                color: root._accent
                font.family: Theme.font.display
                font.pixelSize: Theme.size.h1
                font.weight: Theme.weight.bold
                horizontalAlignment: Text.AlignHCenter
            }

            // Honesty chain — round · margin · source label.
            Text {
                width: parent.width
                text: {
                    var parts = []
                    if (root.result && root.result.end_round !== undefined)
                        parts.push(I18n.t("第", "Round ") + root.result.end_round + I18n.t(" 轮终局", ""))
                    if (root.result && root.result.margin !== undefined && root.result.margin !== null)
                        parts.push(I18n.t("胜负差 ", "margin ") + root.result.margin)
                    if (root.result && root.result.source_label)
                        parts.push("" + root.result.source_label)
                    return parts.join("  ·  ")
                }
                color: root.light ? Theme.report.textMuted : Theme.color.textMuted
                font.family: Theme.font.mono
                font.pixelSize: Theme.size.caption
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }
}
