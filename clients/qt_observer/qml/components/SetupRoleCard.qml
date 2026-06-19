import QtQuick
import QtQuick.Effects
import qt_observer

// Role seat card for the Match Ready Room.
// Visual philosophy: the tarot CARD ART is the visual subject — its alpha defines
// the shadow shape. The container owns only geometry, click/hover/selected affordances,
// and overlay elements (scrim, medallion, info strip, selected outline).
// No Rectangle shadow, no visible shadowArt duplicate, no clip: true on a filled rect.
//
// Shadow strategy matches HomeView: MultiEffect is applied directly to the
// tarot Image via layer.effect, so shadow follows the PNG's transparent rounded
// corners naturally. This eliminates the "right-angle shadow at top corners"
// visible when a separate shadow element or Rectangle backing is used.
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

    // Match the HomeView tarot strip's 2:3 card proportion. Delegates may allocate
    // a wider click box in MatchSetupView, but the visible card, shadow, selected
    // outline, and glow are all centered on this 2:3 visual card.
    implicitWidth: 152
    implicitHeight: 228
    readonly property real _cardRatio: 2 / 3
    // Approximate corner radius matching the tarot PNG's transparent corners.
    readonly property real _cardRadius: 17

    // Selected floats up; hover nudges gently; press dips. No bounce.
    scale: tapHandler.pressed ? 0.985
          : (root.selected ? 1.03 : (hoverHandler.hovered ? 1.015 : 1.0))

    readonly property color _accent: Theme.roleAccent(roleKey)
    readonly property color _stateColor: stateKind === "ready" ? Theme.warm.success
                                      : (stateKind === "missing" ? Theme.warm.warning : Theme.warm.error)
    readonly property color _selColor: Theme.warm.primary   // terracotta coral

    Behavior on scale { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutQuad } }

    // --- Card visual: centered 2:3 area ---------------------------------------
    Item {
        id: cardVisual
        width: Math.min(root.width, root.height * root._cardRatio)
        height: Math.min(root.height, root.width / root._cardRatio)
        anchors.centerIn: parent

        // 1) Card art — shadow follows image alpha (same pattern as HomeView
        //    tarot strip). The tarot PNGs have transparent rounded corners, so
        //    MultiEffect shadow naturally traces the card silhouette — no
        //    rectangular shadow bleed at the corners.
        Image {
            id: cardArt
            anchors.fill: parent
            source: Illustrations.tarot(root.roleKey)
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: true
            sourceSize.width: 304
            sourceSize.height: 456
            opacity: status === Image.Ready ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutCubic } }
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                    shadowColor: Theme.withAlpha(Theme.parchment.sealShadowBase, root.selected ? 0.60 : 0.48)
                shadowBlur: root.selected ? 1.02 : (hoverHandler.hovered ? 0.96 : 0.88)
                shadowHorizontalOffset: root.selected ? 7 : 6
                shadowVerticalOffset: root.selected ? 16 : (hoverHandler.hovered ? 15 : 13)
                Behavior on shadowBlur { NumberAnimation { duration: Theme.anim.color } }
                Behavior on shadowVerticalOffset { NumberAnimation { duration: Theme.anim.color } }
            }
        }

        // 2) Fallback when tarot art is not loaded (never blank).
        Rectangle {
            anchors.fill: parent
            opacity: cardArt.status === Image.Ready ? 0 : 1
            radius: root._cardRadius
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.46)
            Behavior on opacity { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutCubic } }
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Theme.withAlpha(Theme.parchment.sealShadowBase, root.selected ? 0.56 : 0.44)
                shadowBlur: root.selected ? 0.98 : (hoverHandler.hovered ? 0.92 : 0.84)
                shadowHorizontalOffset: root.selected ? 7 : 6
                shadowVerticalOffset: root.selected ? 16 : (hoverHandler.hovered ? 15 : 13)
            }
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.withAlpha(Theme.parchment.woodShadow, 0.82) }
                GradientStop { position: 0.58; color: Theme.withAlpha(Theme.parchment.shadowBrown, 0.70) }
                GradientStop { position: 1.0; color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.86) }
            }
            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: Illustrations.texParchment
                fillMode: Image.Tile
                opacity: 0.12
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: 8
                radius: Math.max(2, root._cardRadius - 6)
                color: "transparent"
                border.width: 1
                border.color: Theme.withAlpha(Theme.parchment.highlightLine, 0.24)
            }
            Text {
                anchors.centerIn: parent
                text: root.roleLabel
                color: Theme.withAlpha(Theme.parchment.highlightCream, 0.78)
                font.family: Theme.fontFamilies.cjkSerif
                font.contextFontMerging: true
                font.pixelSize: Theme.warmSize.titleMd
            }
        }

        // 3) Selected ambient glow — soft wash behind the card, not the primary
        //    outline. Drawn outside the art so it does not enter the shadow pass.
        Rectangle {
            anchors.fill: parent
            anchors.margins: -6
            radius: root._cardRadius + 6
            color: Theme.withAlpha(root._selColor, 0.18)
            border.width: 0
            opacity: root.selected ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.motion.base; easing.type: Easing.OutCubic } }
            z: -1
        }

        // 4) Top scrim — tiny vignette so the seat number medallion reads, NOT a
        //    white header band. Sits on top of the art (z: 1) so the shadow
        //    computed on layer 0 (the art) is unaffected.
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: parent.height * 0.32
            radius: root._cardRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.withAlpha(Theme.parchment.woodShadow, 0.30) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            z: 1
        }

        // 5) Seat medallion — translucent parchment, sits on the art.
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
            z: 2
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

        // 6) Selected check — coral dot, top-right, small.
        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 12
            width: 24
            height: 24
            radius: 12
            visible: root.selected
            color: root._selColor
            z: 3
            Text {
                anchors.centerIn: parent
                text: "\u2713"
                color: Theme.warm.textOnPrimary
                font.family: Theme.fontFamilies.cjkSans
                font.contextFontMerging: true
                font.pixelSize: 13
                font.weight: Theme.weight.bold
            }
        }

        // 7) Bottom info strip — LIGHT translucent parchment ribbon, never solid
        //    white block, never dark gradient. Two micro rows + state dot.
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
            z: 4

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

    // True selected outline: drawn outside cardVisual so it does not enter the
    // shadow pass. The ambient glow behind the card is separate (z: -1).
    Rectangle {
        id: selectedOutline
        anchors.fill: cardVisual
        anchors.margins: -3
        radius: root._cardRadius + 3
        color: "transparent"
        border.width: root.selected ? 3 : 0
        border.color: Theme.warm.primaryActive
        opacity: root.selected ? 1 : 0
        z: 8
        Behavior on opacity { NumberAnimation { duration: Theme.motion.base; easing.type: Easing.OutCubic } }
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
