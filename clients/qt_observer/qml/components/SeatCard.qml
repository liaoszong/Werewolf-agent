import QtQuick
import qt_observer

// Circular seat portrait badge + nameplate (圆形肖像徽章 + 下方铭牌).
//   · round portrait masked to a circle, ringed by a fine gold + faction double edge
//   · wax-seal seat medallion (gold ring + ink center + serif number)
//   · nameplate below: name / role / status, paper-grain + fine gold rule
//   · SPEAKING = gold-lit ring + a small terracotta banner badge
//   · ELIMINATED = desaturating warm wash + a "出局" seal, dimmed
//   · warm layered shadow under the medallion
// Faction colour only as a small accent. Asset missing -> role-initial fallback.
// Contract: objectName + roleKey/seatNumber/alive/speaking/voteCount preserved.
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
    // 名牌横向偏移(px):仅移下方铭牌,头像/座号/票数徽章不动。用于把被相邻座头像压住的
    // 名牌往外侧推开(见 CockpitSurface._plateDx)。
    property real plateDx: 0

    readonly property real _dia: cardW
    readonly property real _plateH: 40
    readonly property url _art: Illustrations.avatar(roleKey)
    readonly property bool _hasArt: String(_art) !== "" && portrait.status === Image.Ready

    implicitWidth: cardW
    implicitHeight: _dia + _plateH + 16

    // ---- warm shadow under the medallion ----
    Rectangle {
        anchors.fill: medallion; anchors.topMargin: 5
        radius: width / 2; color: Theme.parchment.woodShadow; z: -1
    }

    // ---- SPEAKING glow ring ----
    Rectangle {
        visible: root.speaking && root.alive
        anchors.centerIn: medallion
        width: root._dia + 12; height: width; radius: width / 2
        color: "transparent"; border.width: 3
        border.color: Theme.withAlpha(Theme.parchment.terracotta, 0.55)
    }

    // ---- Circular portrait medallion ----
    Item {
        id: medallion
        width: root._dia; height: root._dia
        anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter

        // parchment disc behind (shows through the transparent art corners / fallback)
        Rectangle { anchors.fill: parent; radius: width / 2; color: Theme.parchment.parchmentStrong }

        // Circular portrait via rounded-rect clip — the bust art is keyed to a
        // transparent background, so its square corners reveal the disc and it reads
        // as a true circle. (MultiEffect masking renders blank in grab / on some GPUs.)
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: "transparent"
            clip: true
            Image {
                id: portrait
                anchors.fill: parent
                source: root._art
                fillMode: Image.PreserveAspectCrop
                verticalAlignment: Image.AlignTop
                asynchronous: true
                cache: true
                sourceSize.width: Math.max(1, Math.ceil(width * 2))
                sourceSize.height: Math.max(1, Math.ceil(height * 2))
                visible: root._hasArt
            }
        }
        // fallback: role-initial
        Text {
            anchors.centerIn: parent
            visible: !root._hasArt
            text: (root.roleLabel || root.seatLabel || "?").substring(0, 1)
            color: Theme.parchment.inkSoft
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.pixelSize: root._dia * 0.4; font.weight: Theme.weight.bold
        }

        // ELIMINATED wash + seal (circular overlays)
        Rectangle {
            visible: !root.alive
            anchors.fill: parent; radius: width / 2
            color: Theme.withAlpha("#4a3a28", 0.5)
        }
        Item {
            visible: !root.alive
            anchors.centerIn: parent
            width: root._dia * 0.6; height: width; rotation: -14
            Rectangle { anchors.fill: parent; radius: width / 2; color: "transparent"
                        border.width: 2; border.color: Theme.withAlpha(Theme.parchment.eliminated, 0.92) }
            Text {
                anchors.centerIn: parent
                text: I18n.t("出局", "OUT")
                color: Theme.withAlpha(Theme.parchment.eliminated, 0.95)
                font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
                font.pixelSize: root._dia * 0.17; font.weight: Theme.weight.bold; font.letterSpacing: 1
            }
        }

        // faction tint ring (inner) + gold ring (outer) — fine decorative edge
        Rectangle {
            anchors.fill: parent; radius: width / 2; color: "transparent"
            border.width: 3; border.color: root.speaking ? Theme.parchment.goldLine : Theme.withAlpha(root.accent, 0.85)
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: 3; radius: width / 2; color: "transparent"
            border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.55)
        }
        opacity: root.alive ? 1.0 : 0.85
    }

    // ---- Seat medallion (wax seal) ----
    Rectangle {
        width: 26; height: 26; radius: 13
        x: medallion.x - 2; y: medallion.y - 2
        color: Theme.parchment.bgDark
        border.width: 2; border.color: Theme.parchment.goldLine
        Rectangle { anchors.fill: parent; anchors.margins: 3; radius: width / 2; color: "transparent"
                    border.width: 1; border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.5) }
        Text {
            anchors.centerIn: parent
            text: root.seatNumber > 0 ? root.seatNumber : root.seatLabel.replace(/\D/g, "")
            color: Theme.parchment.goldText
            font.family: Theme.fontFamilies.serif; font.contextFontMerging: true
            font.pixelSize: Theme.size.caption; font.weight: Theme.weight.bold
        }
    }

    // ---- Vote-count badge ----
    Rectangle {
        visible: root.voteCount > 0
        width: 22; height: 22; radius: 11
        x: medallion.x + medallion.width - 20; y: medallion.y - 2
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

    // ---- SPEAKING banner badge (between circle and plate) ----
    Item {
        id: ribbon
        visible: root.speaking && root.alive
        anchors.horizontalCenter: parent.horizontalCenter
        y: medallion.y + medallion.height - 9
        width: ribbonText.implicitWidth + Theme.space.lg
        height: ribbonText.implicitHeight + 7
        z: 6
        Rectangle {
            anchors.fill: parent; radius: 3
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.lighter(Theme.parchment.terracotta, 1.08) }
                GradientStop { position: 1.0; color: Theme.parchment.terracottaDeep }
            }
            Rectangle { anchors { top: parent.top; left: parent.left; right: parent.right }
                        height: 1; color: Theme.withAlpha(Theme.parchment.goldText, 0.8) }
        }
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

    // ---- Engraved nameplate ----
    Rectangle {
        id: plate
        width: root.cardW + 8
        height: root._plateH
        anchors.top: medallion.bottom
        anchors.topMargin: root.speaking ? 9 : 6
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: root.plateDx
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
