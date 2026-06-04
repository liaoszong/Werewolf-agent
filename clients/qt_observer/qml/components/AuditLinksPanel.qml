import QtQuick
import QtQuick.Controls
import qt_observer

// Audit shortcuts rendered as compact, technical "chips".
// Each chip resolves to an inspectable run endpoint (manifest, provider-trace,
// failure-audit, snapshots, artifacts, projection). Click behavior, bindings and
// path construction are preserved exactly — labels are localized at display time.
Flow {
    id: root
    objectName: "auditLinksPanel"
    spacing: Theme.space.sm

    // Localized chip label for an endpoint tag (reactive via I18n).
    function labelFor(tag) {
        switch (tag) {
        case "manifest": return I18n.t("提示词清单", "Prompt Manifest")
        case "provider-trace": return I18n.t("调用追踪", "Provider Trace")
        case "failure-audit": return I18n.t("失败审计", "Failure Audit")
        case "snapshots": return I18n.t("快照", "Snapshots")
        case "artifacts": return I18n.t("产物", "Artifacts")
        case "projection": return I18n.t("投影", "Projection")
        default: return tag
        }
    }

    Repeater {
        model: ["manifest", "provider-trace", "failure-audit", "snapshots", "artifacts", "projection"]

        delegate: Rectangle {
            id: chip
            required property var modelData

            implicitWidth: chipRow.implicitWidth + Theme.space.sm * 2
            implicitHeight: chipRow.implicitHeight + Theme.space.sm * 2
            radius: Theme.radius.sm
            color: hover.hovered ? Theme.color.surfaceAlt : Theme.color.surfaceInset
            border.width: 1
            border.color: hover.hovered ? Theme.color.borderStrong : Theme.color.border

            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
            Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }

            Row {
                id: chipRow
                anchors.centerIn: parent
                spacing: Theme.space.sm

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 6
                    height: 6
                    radius: 3
                    color: Theme.color.textSecondary
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.labelFor(chip.modelData)
                    color: Theme.color.text
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.caption
                    font.weight: Theme.weight.medium
                }
            }

            HoverHandler {
                id: hover
                cursorShape: Qt.PointingHandCursor
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    var path = "/api/runs/" + ObserverClient.currentRunId + "/" + chip.modelData
                    if (chip.modelData === "projection") {
                        path += "?perspective=" + ObserverClient.currentPerspective
                    }
                    console.log("Audit link:", ObserverClient.baseUrl + path)
                }
            }
        }
    }
}
