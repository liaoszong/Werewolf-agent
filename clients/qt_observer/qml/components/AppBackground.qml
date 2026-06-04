import QtQuick
import qt_observer

// Layered "night" backdrop: deep vertical gradient + a faint indigo aurora at
// the top and a subtle blood ember at the bottom. Pure QtQuick (no effects).
Item {
    id: root
    anchors.fill: parent

    // Flat matte charcoal base.
    Rectangle {
        anchors.fill: parent
        color: Theme.color.bg
    }

    // Barely-there top sheen for a soft, non-flat matte feel (neutral, no color cast).
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: parent.height * 0.45
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.016) }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }
}
