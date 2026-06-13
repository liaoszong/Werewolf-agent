import QtQuick
import qt_observer

// Full-bleed illustration background with readability scrims. Falls back to a
// phase gradient when the asset is missing or still loading (never a white gap).
Item {
    id: root
    anchors.fill: parent

    property string phase: "day"            // "day" | "night"
    readonly property bool _night: phase === "night"

    // (1) Phase-gradient floor — also shown while the image loads or on error.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root._night ? Theme.phase.night.sky : Theme.phase.day.sky }
            GradientStop { position: 1.0; color: root._night ? Theme.phase.night.bg  : Theme.phase.day.bg }
        }
    }

    // (2) The illustration itself — only painted once fully loaded.
    Image {
        id: art
        anchors.fill: parent
        source: Illustrations.homeScene(root.phase)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        visible: status === Image.Ready
    }

    // (3) Readability scrims — lift the left rail/hero and the right cards off the
    // busy illustration so overlaid text stays legible (spec §4.3).
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: Theme.withAlpha(root._night ? Theme.phase.night.bg : Theme.warm.canvas, root._night ? 0.72 : 0.62) }
            GradientStop { position: 0.40; color: "transparent" }
            GradientStop { position: 0.70; color: "transparent" }
            GradientStop { position: 1.00; color: Theme.withAlpha(root._night ? Theme.phase.night.bg : Theme.warm.canvas, root._night ? 0.66 : 0.52) }
        }
    }
}
