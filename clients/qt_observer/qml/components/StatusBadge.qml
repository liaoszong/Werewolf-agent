import QtQuick
import qt_observer

// Compact status pill: a pulsing dot + capitalized label, tinted by status.
// Callers bind running/completed/failed/queued/connected/disconnected/empty.
// Auto-sizes to content so existing callers need not set an explicit width.
Rectangle {
    id: root

    property string status: ""
    property bool onLight: false

    readonly property string _label: {
        switch (("" + root.status).toLowerCase()) {
        case "": return "—"; // em dash for empty
        case "running": return I18n.t("进行中", "Running");
        case "completed": return I18n.t("已完成", "Completed");
        case "failed": return I18n.t("失败", "Failed");
        case "queued": return I18n.t("排队中", "Queued");
        case "connected": return I18n.t("已连接", "Connected");
        case "disconnected": return I18n.t("未连接", "Disconnected");
        default:
            var s = "" + root.status;
            return s.charAt(0).toUpperCase() + s.slice(1);
        }
    }

    implicitWidth: row.implicitWidth + Theme.space.md * 2
    implicitHeight: 22
    radius: Theme.radius.pill

    color: Theme.statusTint(root.status)
    border.width: 1
    border.color: Theme.withAlpha(Theme.statusColor(root.status), 0.5)

    Behavior on color { ColorAnimation { duration: Theme.motion.base } }
    Behavior on border.color { ColorAnimation { duration: Theme.motion.base } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: Theme.space.xs

        GlowDot {
            anchors.verticalCenter: parent.verticalCenter
            diameter: 7
            color: root.onLight ? Qt.darker(Theme.statusColor(root.status), 1.15) : Theme.statusColor(root.status)
            pulse: root.status === "running" || root.status === "connected"
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root._label
            color: root.onLight ? Qt.darker(Theme.statusColor(root.status), 1.25) : Theme.statusColor(root.status)
            font.family: Theme.font.family
            font.pixelSize: Theme.size.micro
            font.weight: Theme.weight.semibold
        }
    }
}
