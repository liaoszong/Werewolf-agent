import QtQuick
import QtQuick.Controls
import qt_observer

// Projection Proof panel — explains how the observed perspective was derived:
// its source, the self role/team it assumes, what got filtered out, and the
// visibility rules applied. Styled as a Nightfall AppCard. Presentation only;
// all bindings, objectNames and visibility semantics are preserved.
Rectangle {
    id: root
    objectName: "projectionProofPanel"

    property var proof: ({})
    property int hiddenEventCount: 0
    property int hiddenSnapshotCount: 0

    width: parent ? parent.width : 400
    height: column.implicitHeight + Theme.space.lg * 2
    radius: Theme.radius.lg
    color: Theme.color.surface
    border.width: 1
    border.color: Theme.color.border

    // Top hairline highlight for depth (matches AppCard house style).
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 1
        height: 1
        color: Theme.color.hairline
    }

    Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.space.lg
        spacing: Theme.space.sm

        // Header: a small drawn shield/lock glyph + title.
        Row {
            spacing: Theme.space.sm

            // Drawn shield glyph (no emoji): rounded crest with a keyhole.
            Item {
                width: 18
                height: 18
                anchors.verticalCenter: parent.verticalCenter

                // Shield body.
                Rectangle {
                    anchors.fill: parent
                    anchors.topMargin: 1
                    radius: Theme.radius.sm
                    color: Theme.withAlpha(Theme.color.info, 0.16)
                    border.width: 1
                    border.color: Theme.color.info
                }
                // Pointed base — a rotated square peeking below the crest.
                Rectangle {
                    width: 9
                    height: 9
                    radius: 2
                    rotation: 45
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: -2
                    color: Theme.withAlpha(Theme.color.info, 0.16)
                    border.width: 1
                    border.color: Theme.color.info
                }
                // Keyhole dot in the center of the crest.
                Rectangle {
                    width: 4
                    height: 4
                    radius: 2
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.verticalCenterOffset: -1
                    color: Theme.color.info
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("投影证明", "Projection Proof")
                color: Theme.color.text
                font.family: Theme.font.family
                font.pixelSize: Theme.size.body
                font.weight: Theme.weight.bold
            }
        }

        Text {
            objectName: "projectionProofSource"
            text: I18n.t("来源：", "Source: ") + (root.proof && root.proof.source ? root.proof.source : I18n.t("未知", "Unknown"))
            color: Theme.color.textSecondary
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
        }

        Text {
            text: I18n.t("自身：", "Self: ") + (root.proof && root.proof.self_role ? root.proof.self_role : I18n.t("无", "N/A")) +
                  (root.proof && root.proof.self_team ? " (" + root.proof.self_team + ")" : "")
            color: Theme.color.textSecondary
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
            visible: root.proof && root.proof.self_role !== undefined
        }

        Text {
            objectName: "projectionProofHiddenCounts"
            text: I18n.t("已过滤：", "Filtered: ") + root.hiddenEventCount + I18n.t(" 个事件，", " events, ") + root.hiddenSnapshotCount + I18n.t(" 个快照", " snapshots")
            color: Theme.color.danger
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
            visible: root.hiddenEventCount > 0 || root.hiddenSnapshotCount > 0
        }

        // Subtle divider before the rules block, only when rules exist.
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.color.hairline
            visible: !!(root.proof && root.proof.rules && root.proof.rules.length > 0)
        }

        Text {
            text: I18n.t("已应用规则：", "Rules applied:")
            color: Theme.color.textSecondary
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
            font.weight: Theme.weight.semibold
            visible: !!(root.proof && root.proof.rules && root.proof.rules.length > 0)
            topPadding: Theme.space.xs
        }

        Repeater {
            objectName: "projectionProofRules"
            model: root.proof && root.proof.rules ? root.proof.rules : []
            delegate: Text {
                text: "• " + modelData
                color: Theme.color.textMuted
                font.family: Theme.font.family
                font.pixelSize: Theme.size.micro
                wrapMode: Text.Wrap
                width: column.width
            }
        }
    }
}
