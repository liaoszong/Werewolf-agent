import QtQuick
import qt_observer

// Board-game seat nameplate. Replaces the bare floating circular avatar with a
// card structure: number badge + portrait (role art) + parchment nameplate with
// name/role and a status ribbon. Status is expressed through the card —
// SPEAKING (terracotta ribbon + gold edge), ELIMINATED (dim + label), and an
// optional vote-count badge near the seat — never a crude red ring.
// Asset missing -> role-initial fallback (never a blank seat).
Item {
    id: root
    objectName: "seatCard"

    property string roleKey: ""
    property string roleLabel: ""
    property string seatLabel: ""
    property int seatNumber: 0
    property color accent: Theme.parchment.goldLine
    property bool alive: true
    property bool speaking: false
    property int voteCount: 0
    // Drives overall scale; the seat ring passes a depth-adjusted value.
    property real cardW: 120

    readonly property real _portraitH: cardW * 0.86
    readonly property real _plateH: 38
    readonly property url _art: Illustrations.avatar(roleKey)
    readonly property bool _hasArt: String(_art) !== "" && portrait.status === Image.Ready

    implicitWidth: cardW
    implicitHeight: _portraitH + _plateH + 8
    opacity: alive ? 1.0 : 0.62

    // ---- SPEAKING glow ring behind the portrait (warm terracotta) ----
    Rectangle {
        visible: root.speaking && root.alive
        anchors.fill: portraitFrame
        anchors.margins: -5
        radius: portraitFrame.radius + 5
        color: "transparent"
        border.width: 3
        border.color: Theme.withAlpha(Theme.parchment.terracotta, 0.55)
    }

    // ---- Portrait card (role art in a rounded frame) ----
    Rectangle {
        id: portraitFrame
        width: root.cardW
        height: root._portraitH
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        radius: Theme.radius.md
        color: Theme.parchment.parchmentStrong
        border.width: root.speaking ? 2 : 1.5
        border.color: root.speaking ? Theme.parchment.goldLine
                                    : Theme.withAlpha(root.accent, 0.7)
        clip: true

        Image {
            id: portrait
            anchors.fill: parent
            anchors.margins: 1.5
            source: root._art
            fillMode: Image.PreserveAspectCrop
            verticalAlignment: Image.AlignTop
            visible: root._hasArt
        }
        // Fallback: role-initial on parchment.
        Text {
            anchors.centerIn: parent
            visible: !root._hasArt
            text: (root.roleLabel || root.seatLabel || "?").substring(0, 1)
            color: Theme.parchment.inkSoft
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.pixelSize: root.cardW * 0.4; font.weight: Theme.weight.bold
        }
        // Eliminated wash + skull (no GPU desaturate needed; reads on screenshots).
        Rectangle {
            visible: !root.alive
            anchors.fill: parent
            color: Theme.withAlpha("#3a2c20", 0.45)
        }
        Text {
            visible: !root.alive
            anchors.centerIn: parent
            text: "☠"
            color: Theme.withAlpha("#ffffff", 0.85)
            font.pixelSize: root.cardW * 0.32
        }
    }

    // ---- Seat number badge (overlaps portrait top-left) ----
    Rectangle {
        width: 24; height: 24; radius: 12
        x: portraitFrame.x - 5
        y: portraitFrame.y - 5
        color: Theme.parchment.bgDark
        border.width: 1.5; border.color: Theme.parchment.goldLine
        Text {
            anchors.centerIn: parent
            text: root.seatNumber > 0 ? root.seatNumber : root.seatLabel.replace(/\D/g, "")
            color: Theme.parchment.textOnDark
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.pixelSize: Theme.size.caption; font.weight: Theme.weight.bold
        }
    }

    // ---- Vote-count badge (overlaps portrait top-right; small, never dominant) ----
    Rectangle {
        visible: root.voteCount > 0
        width: 22; height: 22; radius: 11
        x: portraitFrame.x + portraitFrame.width - 17
        y: portraitFrame.y - 5
        color: Theme.parchment.terracotta
        border.width: 1.5; border.color: "#ffffff"
        Text {
            anchors.centerIn: parent
            text: root.voteCount
            color: "#ffffff"
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
        }
    }

    // ---- SPEAKING ribbon (sits between portrait and plate) ----
    Rectangle {
        id: ribbon
        visible: root.speaking && root.alive
        anchors.horizontalCenter: parent.horizontalCenter
        y: portraitFrame.y + portraitFrame.height - 9
        width: ribbonText.implicitWidth + Theme.space.md
        height: ribbonText.implicitHeight + 5
        radius: Theme.radius.sm
        color: Theme.parchment.terracotta
        z: 5
        Text {
            id: ribbonText
            anchors.centerIn: parent
            text: I18n.t("发言中", "SPEAKING")
            color: "#ffffff"
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold; font.letterSpacing: 1
        }
    }

    // ---- Nameplate ----
    Rectangle {
        id: plate
        width: root.cardW + 6
        height: root._plateH
        anchors.top: portraitFrame.bottom
        anchors.topMargin: 4
        anchors.horizontalCenter: parent.horizontalCenter
        radius: Theme.radius.sm
        color: Theme.parchment.parchment
        border.width: 1
        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.7)

        Column {
            anchors.centerIn: parent
            spacing: 1
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 5
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 7; height: 7; radius: 3.5; color: root.accent
                }
                Text {
                    text: root.seatLabel + (root.roleLabel ? "  " + root.roleLabel : "")
                    color: Theme.parchment.ink
                    font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                    font.pixelSize: Theme.size.body; font.weight: Theme.weight.bold
                }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.alive ? I18n.t("存活", "ALIVE") : I18n.t("出局", "ELIMINATED")
                color: root.alive ? Theme.parchment.alive : Theme.parchment.eliminated
                font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
                font.pixelSize: Theme.size.micro; font.letterSpacing: 1.5; font.weight: Theme.weight.bold
            }
        }
    }
}
