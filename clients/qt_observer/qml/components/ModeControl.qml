import QtQuick
import qt_observer

// Launch-mode intent control. The FSM tokens and resolvedMode mapping are the
// runtime contract; this component only changes visual language for setup.
Item {
    id: root

    property bool onLight: false
    property bool compact: false

    state: "fake"

    readonly property string resolvedMode: root.state === "live_confirmed" ? "live" : "fake"

    readonly property bool liveAvailable: ObserverClient.liveAvailable
    readonly property string liveReasonCode: ObserverClient.liveReasonCode
    readonly property string liveReasonMessage: ObserverClient.liveReasonMessage

    implicitWidth: root.compact ? 236 : 380
    implicitHeight: content.implicitHeight

    function resetToFake() { root.state = "fake" }

    Column {
        id: content
        width: parent.width
        spacing: Theme.space.xs

        Rectangle {
            width: parent.width
            height: root.compact ? 42 : 46
            radius: Theme.radius.pill
            color: root.onLight ? Theme.withAlpha(Theme.warm.surfaceRaised, 0.72)
                                : Theme.color.surfaceInset
            border.width: 1
            border.color: root.onLight ? Theme.withAlpha(Theme.parchment.goldLine, 0.38)
                                       : Theme.color.border

            Row {
                anchors.fill: parent
                anchors.margins: 3
                spacing: 3

                Segment {
                    width: (parent.width - parent.spacing) / 2
                    height: parent.height
                    label: I18n.t("试玩", "Trial")
                    caption: root.compact ? "" : I18n.t("休闲排练", "rehearsal")
                    active: root.state === "fake"
                    enabled: true
                    onPicked: root.resetToFake()
                }

                Segment {
                    width: (parent.width - parent.spacing) / 2
                    height: parent.height
                    label: root.liveAvailable ? I18n.t("实战", "Live")
                                               : I18n.t("实战", "Live")
                    caption: root.compact ? "" : (root.liveAvailable ? I18n.t("认真对局", "ranked")
                                                                       : I18n.t("暂不可用", "unavailable"))
                    active: root.state === "live_armed" || root.state === "live_confirmed"
                    enabled: root.liveAvailable
                    pulse: root.state === "live_confirmed"
                    onPicked: if (root.liveAvailable) root.state = "live_confirmed"
                    Accessible.description: root.liveReasonCode
                }
            }
        }

        Text {
            width: parent.width
            visible: !root.liveAvailable && root.liveReasonMessage.length > 0 && !root.compact
            text: root.liveReasonMessage
            wrapMode: Text.WordWrap
            color: root.onLight ? Theme.warm.muted : Theme.color.textMuted
            font.family: root.onLight ? Theme.fontFamilies.cjkSans : Theme.font.family
            font.contextFontMerging: root.onLight
            font.pixelSize: Theme.size.micro
        }
    }

    component Segment: Rectangle {
        id: seg
        required property string label
        property string caption: ""
        property bool active: false
        property bool pulse: false
        signal picked()

        radius: Theme.radius.pill
        color: active ? Theme.warm.primary : "transparent"
        opacity: enabled ? 1 : 0.48
        Behavior on color { ColorAnimation { duration: Theme.anim.color; easing.type: Easing.OutCubic } }

        Column {
            anchors.centerIn: parent
            spacing: 0
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: seg.label
                color: seg.active ? Theme.warm.textOnPrimary : Theme.warm.body
                font.family: Theme.fontFamilies.cjkSans
                font.contextFontMerging: true
                font.pixelSize: Theme.size.body
                font.weight: Theme.weight.semibold
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: seg.caption !== ""
                text: seg.caption
                color: seg.active ? Theme.withAlpha(Theme.warm.textOnPrimary, 0.78) : Theme.warm.mutedSoft
                font.family: Theme.fontFamilies.cjkSans
                font.contextFontMerging: true
                font.pixelSize: Theme.size.micro
            }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 7
            height: 7
            radius: 4
            visible: seg.pulse
            color: Theme.warm.textOnPrimary
        }

        TapHandler { enabled: seg.enabled; onTapped: seg.picked() }
        HoverHandler { enabled: seg.enabled; cursorShape: Qt.PointingHandCursor }
    }
}
