import QtQuick
import qt_observer

// Right-HUD live/spectating status. Pure presentation.
HudCard {
    id: root
    property string liveText: ""        // "真实 LIVE" / "模拟"
    property bool live: false           // pulse the dot only for a true live run
    property string perspectiveLabel: ""// "视角：god"

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4

        Row {
            spacing: Theme.space.sm
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 9; height: 9; radius: 4.5
                color: Theme.parchment.terracotta
                SequentialAnimation on opacity {
                    running: root.live; loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.3; duration: 700; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 0.3; to: 1.0; duration: 700; easing.type: Easing.InOutSine }
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.liveText
                color: Theme.parchment.ink
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.titleMd; font.weight: Theme.weight.bold
                font.letterSpacing: 1
            }
        }
        Text {
            text: I18n.t("观战中", "Spectating")
            color: Theme.parchment.mutedInk
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5
        }
        Text {
            visible: root.perspectiveLabel !== ""
            text: root.perspectiveLabel
            color: Theme.parchment.inkSoft
            font.family: Theme.fontFamilies.mono
            font.pixelSize: Theme.size.micro
        }
    }
}
