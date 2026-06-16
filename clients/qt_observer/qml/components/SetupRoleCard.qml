import QtQuick
import qt_observer

// Role seat card for the Match Ready Room.
// Visual philosophy: the tarot CARD ART is the visual subject. The container is
// nearly transparent — it owns only geometry, click/hover/selected affordances,
// a soft warm drop shadow, and a thin scrim so the per-seat engine/model/state
// chips stay legible over the art. No thick white frame, no "card in a frame".
Item {
    id: root
    objectName: "setupRoleCard"

    property string seatLabel: ""
    property string roleKey: ""
    property string roleLabel: ""
    property string engineLabel: ""
    property string modelLabel: ""
    property string stateLabel: ""
    property string stateKind: "ready"   // ready | missing | empty
    property bool selected: false

    signal activated()

    implicitWidth: 214
    implicitHeight: 298
    // Selected floats up; hover nudges gently; press dips. No bounce.
    scale: tapHandler.pressed ? 0.985
          : (root.selected ? 1.03 : (hoverHandler.hovered ? 1.015 : 1.0))

    readonly property color _accent: Theme.roleAccent(roleKey)
    readonly property color _stateColor: stateKind === "ready" ? Theme.warm.success
                                      : (stateKind === "missing" ? Theme.warm.warning : Theme.warm.error)
    readonly property color _selColor: Theme.warm.primary   // terracotta coral

    Behavior on scale { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutQuad } }

    // --- Soft warm drop shadow (layered low-alpha rects — survives screenshots) ---
    Rectangle {
        z: -2
        anchors.fill: cardClip
        anchors.topMargin: 12
        anchors.leftMargin: 6
        anchors.rightMargin: -6
        anchors.bottomMargin: -12
        radius: cardClip.radius + 2
        color: Theme.withAlpha(Theme.parchment.woodShadow, root.selected ? 0.58
                                   : (hoverHandler.hovered ? 0.50 : 0.40))
        Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }
    }
    Rectangle {
        z: -1
        anchors.fill: cardClip
        anchors.topMargin: 6
        anchors.leftMargin: 3
        anchors.rightMargin: -3
        anchors.bottomMargin: -6
        radius: cardClip.radius + 1
        color: Theme.parchment.woodShadowSoft
    }

    // --- Coral outer glow (selected only) — soft wide wash, not a hard stroke ---
    Rectangle {
        anchors.fill: cardClip
        anchors.margins: -6
        radius: cardClip.radius + 6
        color: Theme.withAlpha(root._selColor, 0.22)
        border.width: 0
        opacity: root.selected ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base; easing.type: Easing.OutCubic } }
        z: -1
    }

    // --- The clip that IS the card edge — transparent fill, just rounds corners ---
    Rectangle {
        id: cardClip
        anchors.fill: parent
        radius: 14
        color: "transparent"
        // Thin warm hairline; on selected it becomes a single coral line.
        border.width: root.selected ? 1.5 : 1
        border.color: root.selected ? root._selColor
                                  : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.30)
        clip: true
        Behavior on border.color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }

        // 1) Card art bleeds to the very edge — the art IS the frame.
        Image {
            id: cardArt
            anchors.fill: parent
            source: Illustrations.tarot(root.roleKey)
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: true
            visible: status === Image.Ready
        }
        Rectangle {
            anchors.fill: parent
            visible: cardArt.status !== Image.Ready
            color: Theme.warm.surfaceCard
            Text {
                anchors.centerIn: parent
                text: root.roleLabel
                color: Theme.warm.muted
                font.family: Theme.fontFamilies.cjkSerif
                font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.titleMd
            }
        }

        // 2) Top scrim — tiny vignette so the seat number medallion reads, NOT a
        // white header band.
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: parent.height * 0.32
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.withAlpha(Theme.parchment.woodShadow, 0.30) }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }

        // 3) Seat medallion — translucent parchment, sits on the art.
        Rectangle {
            id: seatSeal
            x: 14
            y: 14
            width: 38
            height: 38
            radius: 19
            color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.82)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.55)
            Text {
                anchors.centerIn: parent
                text: root.seatLabel
                color: Theme.parchment.ink
                font.family: Theme.fontFamilies.cjkSerif
                font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.bodyLg
                font.weight: Theme.weight.bold
            }
        }

        // 4) Selected check — coral dot, top-right, small.
        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 12
            width: 24
            height: 24
            radius: 12
            visible: root.selected
            color: root._selColor
            Text {
                anchors.centerIn: parent
                text: "✓"
                color: Theme.warm.textOnPrimary
                font.family: Theme.fontFamilies.cjkSans
                font.contextFontMerging: true
                font.pixelSize: 13
                font.weight: Theme.weight.bold
            }
        }

        // 5) Bottom info strip — LIGHT translucent parchment ribbon, never solid
        // white block, never dark gradient. Two micro rows + state dot.
        Rectangle {
            id: infoPlate
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            height: 64
            radius: 9
            color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.80)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.32)

            Column {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 3

                Row {
                    width: parent.width
                    spacing: 4
                    Text {
                        width: 30
                        text: I18n.t("引擎", "Engine")
                        color: Theme.parchment.mutedInk
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: 10
                    }
                    Text {
                        width: parent.width - x
                        text: root.engineLabel
                        color: Theme.parchment.inkSoft
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                }

                Row {
                    width: parent.width
                    spacing: 4
                    Text {
                        width: 30
                        text: I18n.t("模型", "Model")
                        color: Theme.parchment.mutedInk
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: 10
                    }
                    Text {
                        width: parent.width - x
                        text: root.modelLabel
                        color: Theme.parchment.inkSoft
                        font.family: Theme.fontFamilies.cjkSans
                        font.contextFontMerging: true
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                }

                Rectangle { width: parent.width; height: 1; color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.30) }

                Row {
                    width: parent.width
                    spacing: 5
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 8
                        height: 8
                        radius: 4
                        color: root._stateColor
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - x
                        text: root.stateLabel
                        color: root._stateColor
                        font.family: Theme.fontFamilies.cjkSerif
                        font.contextFontMerging: true
                        font.pixelSize: 11
                        font.weight: Theme.weight.semibold
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    HoverHandler {
        id: hoverHandler
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        id: tapHandler
        onTapped: root.activated()
    }
}
