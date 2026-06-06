import QtQuick
import QtQuick.Controls
import qt_observer
import "."

// P2-C-1 bottom evidence console. Three states (Closed / Peek / Expanded) that re-home the
// demoted honesty chain: trust boundary, projection proof, Seat Lens, event timeline and
// audit links. The Seat Lens drives ObserverClient.currentPerspective ONLY — the stage
// re-fogs via its own binding; this console never writes ring.perspective (P1-C). Exiting
// the lens restores the god view.
Item {
    id: root
    objectName: "evidenceConsole"

    property int mode: 0                 // 0 Closed, 1 Peek, 2 Expanded
    property string perspective: "god"

    readonly property real fullHeight: parent ? parent.height : 640
    height: mode === 0 ? 46
          : mode === 1 ? Math.round(fullHeight * 0.30)
          : Math.round(fullHeight * 0.66)
    Behavior on height { NumberAnimation { duration: Theme.motion.base; easing.type: Easing.OutCubic } }

    // Backdrop + top hairline.
    Rectangle {
        anchors.fill: parent
        color: Theme.color.surface
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            color: Theme.color.border
        }
    }

    // ---- Top bar (always visible) ----
    Item {
        id: topBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: Theme.space.lg
        anchors.rightMargin: Theme.space.lg
        height: 46

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.md

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("证据", "Evidence")
                color: Theme.color.text
                font.family: Theme.font.family
                font.pixelSize: Theme.size.body
                font.weight: Theme.weight.semibold
            }
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.space.xs
                GlowDot {
                    anchors.verticalCenter: parent.verticalCenter
                    diameter: 7
                    color: Theme.color.success
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: ObserverClient.hiddenEventCount > 0
                          ? (I18n.t("可见性 · 隐藏 ", "Visibility · ") + ObserverClient.hiddenEventCount + I18n.t(" 事件", " hidden"))
                          : I18n.t("可见性 PASS", "Visibility PASS")
                    color: Theme.color.textMuted
                    font.family: Theme.font.mono
                    font.pixelSize: Theme.size.micro
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("视角：", "Lens: ") + root.perspective
                color: Theme.color.textSecondary
                font.family: Theme.font.mono
                font.pixelSize: Theme.size.micro
            }
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.xs
            AppButton { text: I18n.t("收起", "Hide"); variant: root.mode === 0 ? "secondary" : "ghost"; onClicked: root.mode = 0 }
            AppButton { text: I18n.t("预览", "Peek"); variant: root.mode === 1 ? "secondary" : "ghost"; onClicked: root.mode = 1 }
            AppButton { text: I18n.t("展开", "Expand"); variant: root.mode === 2 ? "secondary" : "ghost"; onClicked: root.mode = 2 }
        }
    }

    // ---- Content (Peek / Expanded) ----
    Flickable {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.space.lg
        anchors.rightMargin: Theme.space.lg
        anchors.bottomMargin: Theme.space.lg
        visible: root.mode > 0
        clip: true
        contentWidth: width
        contentHeight: body.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Column {
            id: body
            width: content.width
            spacing: Theme.space.lg

            // Seat Lens (Expanded): switch sets ObserverClient.currentPerspective; Back-to-God restores it.
            Row {
                spacing: Theme.space.md
                visible: root.mode >= 2
                PerspectiveSwitcher {
                    id: perspectiveSwitcher
                    objectName: "perspectiveSwitcher"
                }
                AppButton {
                    text: I18n.t("回到上帝视角", "Back to God")
                    variant: "ghost"
                    visible: root.perspective !== "god"
                    onClicked: ObserverClient.currentPerspective = "god"
                }
            }

            // Trust boundary + projection proof.
            Flow {
                width: parent.width
                spacing: Theme.space.md
                ViewBoundaryBadge {
                    perspective: ObserverClient.currentPerspective
                    contractVersion: ObserverClient.visibilityContractVersion
                    hiddenEventCount: ObserverClient.hiddenEventCount
                    hiddenSnapshotCount: ObserverClient.hiddenSnapshotCount
                }
                ProjectionProofPanel {
                    visible: root.mode >= 2
                    proof: ObserverClient.projectionProof
                    hiddenEventCount: ObserverClient.hiddenEventCount
                    hiddenSnapshotCount: ObserverClient.hiddenSnapshotCount
                }
            }

            // Event timeline (visible to the current lens).
            SectionHeader {
                title: I18n.t("事件", "Events")
                caption: I18n.t("当前视角可见事件流。", "Event stream as visible to the current lens.")
            }
            EventTimeline {
                id: eventTimeline
                objectName: "eventTimeline"
                width: parent.width
                height: root.mode >= 2 ? 220 : 120
            }

            // Audit links + provider failures (Expanded).
            SectionHeader {
                visible: root.mode >= 2
                title: I18n.t("审计链接", "Audit Links")
                caption: I18n.t("追溯 prompt / provider / 失败到源记录。", "Trace prompt / provider / failures to source records.")
            }
            AuditLinksPanel {
                id: auditLinksPanel
                objectName: "auditLinksPanel"
                visible: root.mode >= 2
                width: parent.width
            }
            Text {
                id: providerFailureSummary
                objectName: "providerFailureSummary"
                visible: root.mode >= 2
                width: parent.width
                text: I18n.t("模型调用失败：详见审计链接。", "Provider failures: check audit links for details.")
                color: Theme.color.textMuted
                font.family: Theme.font.family
                font.pixelSize: Theme.size.caption
                wrapMode: Text.WordWrap
            }
        }
    }
}
