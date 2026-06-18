import QtQuick
import qt_observer

// Right-HUD "Current Votes": one row per vote target with a count badge; the
// current leader is emphasised (filled terracotta badge + bold name). A majority
// footer shows the line to reach. Rows arrive pre-sorted desc with a faction
// accent: rows = [{ target, count, accent }].
HudCard {
    id: root
    property var rows: []
    property int majority: 0
    readonly property int _lead: {
        var m = 0
        for (var i = 0; i < (rows ? rows.length : 0); i++)
            if (rows[i].count > m) m = rows[i].count
        return m
    }

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Theme.space.sm

        Text {
            text: "↣  " + I18n.t("当前票数", "Current Votes") + "  ↢"
            color: Theme.parchment.goldLineSoft
            font.family: Theme.fontFamilies.cjkSans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5; font.weight: Theme.weight.bold
        }

        // Empty state — the panel stays mounted (never disappears); shows a quiet
        // placeholder until votes arrive, instead of vanishing the whole HUD module.
        Text {
            visible: !root.rows || root.rows.length === 0
            text: I18n.t("本轮暂无投票", "No votes this round")
            color: Theme.parchment.mutedInk
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.italic: true; font.pixelSize: Theme.size.caption
        }

        Repeater {
            model: root.rows
            delegate: Item {
                width: parent ? parent.width : 0
                height: 26
                readonly property bool isLeader: modelData.count === root._lead && root._lead > 0

                Row {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.space.sm
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 8; height: 8; radius: 4
                        color: modelData.accent !== undefined ? modelData.accent : Theme.parchment.mutedInk
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.target
                        color: Theme.parchment.ink
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.body
                        font.weight: isLeader ? Theme.weight.bold : Theme.weight.regular
                    }
                }

                // Count badge — filled terracotta for the leader, outlined otherwise.
                Rectangle {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 22; height: 22; radius: 11
                    color: isLeader ? Theme.parchment.terracotta : "transparent"
                    border.width: 1
                    border.color: isLeader ? Theme.parchment.terracotta : Theme.withAlpha(Theme.parchment.goldLine, 0.6)
                    Text {
                        anchors.centerIn: parent
                        text: modelData.count
                        color: isLeader ? Theme.warm.textOnPrimary : Theme.parchment.inkSoft
                        font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption; font.weight: Theme.weight.bold
                    }
                }
            }
        }

        Rectangle {
            visible: root.majority > 0
            width: parent.width; height: 1
            color: Theme.withAlpha(Theme.parchment.goldLine, 0.4)
        }
        Text {
            visible: root.majority > 0
            text: I18n.t("多数线：", "Majority: ") + root.majority
            color: Theme.parchment.mutedInk
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.letterSpacing: 1
        }
    }
}
