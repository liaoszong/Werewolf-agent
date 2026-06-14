import QtQuick
import qt_observer

// Right-HUD phase card: ☀/☾ medallion + phase title + italic subtitle, then a
// ROUND line with progress pips. Pure presentation (phase / round in).
HudCard {
    id: root
    property string phase: "day"
    property int round: 1
    readonly property bool _night: phase === "night"
    readonly property bool _voting: phase === "voting"

    function _title() {
        if (_night) return I18n.t("夜晚行动", "Night Actions")
        if (_voting) return I18n.t("投票表决", "Voting")
        return I18n.t("白天辩论", "Daytime Debate")
    }
    function _subtitle() {
        if (_night) return I18n.t("各角色暗中行动", "Roles act in secret")
        if (_voting) return I18n.t("统计票数，放逐一人", "Tally votes, exile one")
        return I18n.t("讨论并投票出局", "Discuss and vote to eliminate")
    }

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Theme.space.md

        Row {
            spacing: Theme.space.md
            // Gold medallion with the day/night glyph.
            Rectangle {
                width: 38; height: 38; radius: 19
                color: Theme.withAlpha(Theme.parchment.terracotta, 0.14)
                border.width: 1.5; border.color: Theme.parchment.goldLine
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    anchors.centerIn: parent
                    text: root._night ? "☾" : "☀"
                    color: root._night ? Theme.parchment.goldLineSoft : Theme.parchment.terracottaDeep
                    font.pixelSize: 20
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1
                Text {
                    text: root._title()
                    color: Theme.parchment.ink
                    font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.titleMd; font.weight: Theme.weight.bold
                }
                Text {
                    text: root._subtitle()
                    color: Theme.parchment.mutedInk
                    font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                    font.italic: true; font.pixelSize: Theme.size.caption
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: Theme.withAlpha(Theme.parchment.goldLine, 0.4) }

        Row {
            spacing: Theme.space.md
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("回合", "ROUND")
                color: Theme.parchment.mutedInk
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5; font.weight: Theme.weight.bold
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.round
                color: Theme.parchment.terracottaDeep
                font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.titleLg; font.weight: Theme.weight.bold
            }
            // Progress pips up to the current round (max 6 shown; current = terracotta).
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 5
                Repeater {
                    model: Math.min(6, Math.max(1, root.round))
                    delegate: Rectangle {
                        width: 8; height: 8; radius: 4
                        color: (index === root.round - 1) ? Theme.parchment.terracotta
                                                          : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.7)
                    }
                }
            }
        }
    }
}
