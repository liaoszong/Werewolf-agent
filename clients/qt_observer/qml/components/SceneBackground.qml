import QtQuick
import qt_observer

// Illustration backdrop for the content region (the area RIGHT of the NavRail).
// The caller anchors this to that region; the artwork FILLS it (PreserveAspectCrop)
// so the image's own cream breathing-margin lands at the region's left — i.e.
// directly under the hero text — instead of being wasted behind the NavRail.
// Falls back to the parchment gradient when the asset is missing/still loading.
Item {
    id: root

    property string phase: "day"            // "day" | "night"
    readonly property bool _night: phase === "night"

    // Warm parchment floor — matches the artwork margins and is the no-asset
    // fallback. (Gradient is intentional; also satisfies the fallback contract.)
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.phase.day.bg }
            GradientStop { position: 1.0; color: Qt.darker(Theme.phase.day.bg, 1.06) }
        }
    }

    // The illustration fills the region; its left cream margin sits under the hero.
    Image {
        id: art
        anchors.fill: parent
        source: Illustrations.homeScene(root.phase)
        fillMode: Image.PreserveAspectCrop
        horizontalAlignment: Image.AlignHCenter
        verticalAlignment: Image.AlignVCenter
        asynchronous: true
        cache: true
        sourceSize.width: Math.max(1, Math.ceil(width * 2))
        sourceSize.height: Math.max(1, Math.ceil(height * 2))
        visible: status === Image.Ready
    }

    // Light left scrim — insurance so hero text stays crisp where it meets the
    // start of the painted scene (the new bg already bakes in a cream margin).
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: Theme.withAlpha(Theme.phase.day.bg, _night ? 0.5 : 0.4) }
            GradientStop { position: 0.32; color: "transparent" }
            GradientStop { position: 1.00; color: "transparent" }
        }
    }
}
