import QtQuick
import qt_observer

// Friendly placeholder for empty lists / regions.
// The mark is a low-opacity wolf-head silhouette — a restrained nod to the
// game's theme that never competes with the foreground (no color, ~12% alpha).
Column {
    id: root

    property string title: "Nothing here yet"
    property string subtitle: ""

    spacing: Theme.space.md

    Canvas {
        id: wolfMark
        anchors.horizontalCenter: parent.horizontalCenter
        width: 64
        height: 64

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            // Stylized, symmetric wolf-head silhouette (front view).
            ctx.beginPath()
            ctx.moveTo(10, 11)   // left ear tip
            ctx.lineTo(26, 31)   // left brow
            ctx.lineTo(32, 26)   // forehead notch
            ctx.lineTo(38, 31)   // right brow
            ctx.lineTo(54, 11)   // right ear tip
            ctx.lineTo(49, 38)   // right temple
            ctx.lineTo(52, 51)   // right cheek
            ctx.lineTo(40, 60)   // right jaw
            ctx.lineTo(32, 64)   // chin / snout
            ctx.lineTo(24, 60)   // left jaw
            ctx.lineTo(12, 51)   // left cheek
            ctx.lineTo(15, 38)   // left temple
            ctx.closePath()
            ctx.fillStyle = "rgba(245, 245, 245, 0.12)"
            ctx.fill()
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.title
        color: Theme.color.textSecondary
        font.family: Theme.font.family
        font.pixelSize: Theme.size.body
        font.weight: Theme.weight.medium
    }

    Text {
        visible: root.subtitle !== ""
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.subtitle
        color: Theme.color.textMuted
        font.family: Theme.font.family
        font.pixelSize: Theme.size.caption
        horizontalAlignment: Text.AlignHCenter
    }
}
