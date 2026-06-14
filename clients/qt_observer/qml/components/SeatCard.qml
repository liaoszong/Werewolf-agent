import QtQuick
import qt_observer

// Tabletop seat plaque (席位铭牌). A carved identity card, not a sticker + label:
//   · wax-seal seat medallion (gold ring + ink center + serif number)
//   · portrait set INTO a parchment-grained frame with a bottom vignette (depth)
//   · engraved nameplate (paper grain + fine gold rule) carrying name/role/status
//   · SPEAKING = premium terracotta banner + gold-lit portrait edge
//   · ELIMINATED = desaturating warm wash + a distressed "出局" seal (not a slash)
//   · warm layered shadow lifts the plaque off the table
// Faction colour only as a small accent (medallion ring tint, plate dot). Asset
// missing -> role-initial fallback (never a blank seat). Contract: objectName +
// roleKey/seatNumber/alive/speaking/voteCount preserved.
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
    property real cardW: 120

    readonly property real _portraitH: cardW * 0.92
    readonly property real _plateH: 40
    readonly property url _art: Illustrations.avatar(roleKey)
    readonly property bool _hasArt: String(_art) !== "" && portrait.status === Image.Ready

    implicitWidth: cardW
    implicitHeight: _portraitH + _plateH + 12

    // ---- warm layered shadow ----
    Rectangle {
        anchors.fill: portraitFrame; anchors.topMargin: 6; anchors.bottomMargin: -_plateH
        radius: portraitFrame.radius; color: Theme.parchment.woodShadow; z: -1
    }

    // ---- SPEAKING outer glow ----
    Rectangle {
        visible: root.speaking && root.alive
        anchors.fill: portraitFrame; anchors.margins: -5
        radius: portraitFrame.radius + 5
        color: "transparent"
        border.width: 3; border.color: Theme.withAlpha(Theme.parchment.terracotta, 0.5)
    }

    // ---- Portrait set into a parchment frame ----
    Rectangle {
        id: portraitFrame
        width: root.cardW
        height: root._portraitH
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        radius: Theme.radius.md
        color: Theme.parchment.parchmentStrong
        border.width: root.speaking ? 2 : 1.5
        border.color: root.speaking ? Theme.parchment.goldLine : Theme.withAlpha(root.accent, 0.75)
        clip: true

        Image {
            id: portrait
            anchors.fill: parent; anchors.margins: 2
            source: root._art
            fillMode: Image.PreserveAspectCrop
            verticalAlignment: Image.AlignTop
            visible: root._hasArt
        }
        // fallback: role-initial on parchment
        Text {
            anchors.centerIn: parent
            visible: !root._hasArt
            text: (root.roleLabel || root.seatLabel || "?").substring(0, 1)
            color: Theme.parchment.inkSoft
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.pixelSize: root.cardW * 0.4; font.weight: Theme.weight.bold
        }
        // paper grain over the portrait card (very faint — unifies art + frame)
        Image {
            anchors.fill: parent
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.5
        }
        // bottom vignette — sinks the portrait INTO the card (not pasted on)
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: parent.height * 0.4
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: Theme.withAlpha("#241a10", 0.5) }
            }
        }
        // faction top accent hairline
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 2; color: Theme.withAlpha(root.accent, 0.85)
        }

        // ELIMINATED: desaturating warm wash + distressed seal
        Rectangle {
            visible: !root.alive
            anchors.fill: parent
            color: Theme.withAlpha("#4a3a28", 0.5)
        }
        Item {
            visible: !root.alive
            anchors.centerIn: parent
            width: root.cardW * 0.56; height: width; rotation: -14
            Rectangle {
                anchors.fill: parent; radius: width / 2
                color: "transparent"; border.width: 2
                border.color: Theme.withAlpha(Theme.parchment.eliminated, 0.92)
            }
            Text {
                anchors.centerIn: parent
                text: I18n.t("出局", "OUT")
                color: Theme.withAlpha(Theme.parchment.eliminated, 0.95)
                font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                font.pixelSize: root.cardW * 0.18; font.weight: Theme.weight.bold; font.letterSpacing: 1
            }
        }
    }

    // ---- Seat medallion (wax-seal: gold ring + ink center + serif number) ----
    Rectangle {
        width: 26; height: 26; radius: 13
        x: portraitFrame.x - 6; y: portraitFrame.y - 6
        color: Theme.parchment.bgDark
        border.width: 2; border.color: Theme.parchment.goldLine
        Rectangle {
            anchors.fill: parent; anchors.margins: 3; radius: width / 2
            color: "transparent"; border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.5)
        }
        Text {
            anchors.centerIn: parent
            text: root.seatNumber > 0 ? root.seatNumber : root.seatLabel.replace(/\D/g, "")
            color: Theme.parchment.goldText
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.pixelSize: Theme.size.caption; font.weight: Theme.weight.bold
        }
    }

    // ---- Vote-count badge (small; never dominant) ----
    Rectangle {
        visible: root.voteCount > 0
        width: 22; height: 22; radius: 11
        x: portraitFrame.x + portraitFrame.width - 16; y: portraitFrame.y - 6
        color: Theme.parchment.terracotta
        border.width: 1.5; border.color: Theme.withAlpha("#ffffff", 0.85)
        Text {
            anchors.centerIn: parent
            text: root.voteCount
            color: "#ffffff"
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
        }
    }

    // ---- SPEAKING banner (premium ribbon with gold top edge) ----
    Item {
        id: ribbon
        visible: root.speaking && root.alive
        anchors.horizontalCenter: parent.horizontalCenter
        y: portraitFrame.y + portraitFrame.height - 10
        width: ribbonText.implicitWidth + Theme.space.lg
        height: ribbonText.implicitHeight + 7
        z: 6
        Rectangle {
            anchors.fill: parent
            radius: 3
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.lighter(Theme.parchment.terracotta, 1.08) }
                GradientStop { position: 1.0; color: Theme.parchment.terracottaDeep }
            }
            Rectangle { anchors { top: parent.top; left: parent.left; right: parent.right }
                        height: 1; color: Theme.withAlpha(Theme.parchment.goldText, 0.8) }
        }
        // banner tails
        Rectangle { width: 7; height: 7; rotation: 45; color: Theme.parchment.terracottaDeep
                    anchors { left: parent.left; leftMargin: -3; verticalCenter: parent.bottom } }
        Rectangle { width: 7; height: 7; rotation: 45; color: Theme.parchment.terracottaDeep
                    anchors { right: parent.right; rightMargin: -3; verticalCenter: parent.bottom } }
        Text {
            id: ribbonText
            anchors.centerIn: parent
            text: I18n.t("发言中", "SPEAKING")
            color: "#ffffff"
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold; font.letterSpacing: 1
        }
    }

    // ---- Engraved nameplate (paper grain + fine gold rule) ----
    Rectangle {
        id: plate
        width: root.cardW + 8
        height: root._plateH
        anchors.top: portraitFrame.bottom
        anchors.topMargin: 5
        anchors.horizontalCenter: parent.horizontalCenter
        radius: Theme.radius.sm
        opacity: root.alive ? 1.0 : 0.9
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(Theme.parchment.parchment, 1.03) }
            GradientStop { position: 1.0; color: Qt.darker(Theme.parchment.parchment, 1.03) }
        }
        border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.7)
        clip: true
        Image { anchors.fill: parent; source: Illustrations.texParchment; fillMode: Image.Tile; opacity: 0.6 }
        Rectangle { anchors.fill: parent; anchors.margins: 2; radius: 2; color: "transparent"
                    border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.3) }

        Column {
            anchors.centerIn: parent
            spacing: 1
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 5
                Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 7; height: 7; radius: 3.5; color: root.accent }
                Text {
                    text: root.seatLabel + (root.roleLabel ? "  " + root.roleLabel : "")
                    color: root.alive ? Theme.parchment.ink : Theme.parchment.inkSoft
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
