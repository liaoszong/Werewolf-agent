import QtQuick
import qt_observer

// Contained illustration plate on a warm parchment page. The artwork is shown
// WHOLE (PreserveAspectFit) so its baked-in cream margins survive — the scene
// stays centered and never crops/enlarges to block the hero, panels or cards.
// Falls back to the parchment gradient when the asset is missing/still loading.
Item {
    id: root
    anchors.fill: parent

    property string phase: "day"            // "day" | "night"
    readonly property bool _night: phase === "night"

    // Warm parchment floor — matches the artwork's own margins, fills the
    // letterbox bands, and is the no-asset fallback. (Gradient is intentional and
    // also satisfies the SceneBackground fallback contract.)
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.phase.day.bg }
            GradientStop { position: 1.0; color: Qt.darker(Theme.phase.day.bg, 1.06) }
        }
    }

    // The illustration, shown whole and centred — no crop, margins preserved.
    Image {
        id: art
        anchors.fill: parent
        source: Illustrations.homeScene(root.phase)
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignHCenter
        verticalAlignment: Image.AlignVCenter
        asynchronous: true
        cache: true
        visible: status === Image.Ready
    }
}
