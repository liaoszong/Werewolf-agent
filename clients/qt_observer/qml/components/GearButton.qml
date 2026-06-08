import QtQuick
import qt_observer

// Settings gear — a small hand-drawn cog button used as the entry point to the
// provider/model settings page. Drawn on a Canvas (like EmptyState's wolf mark)
// with a punched-through center so it reads as a gear on ANY background. A faint
// rounded well appears on hover, matching the top-bar language toggle.
Item {
    id: root

    property int diameter: 18          // icon size in px
    property color iconColor: Theme.color.textSecondary
    property color iconColorHover: Theme.color.text
    signal clicked

    implicitWidth: diameter + Theme.space.sm * 2
    implicitHeight: diameter + Theme.space.xs * 2

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius.sm
        color: hover.hovered ? Theme.color.surfaceInset : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
    }

    Canvas {
        id: cog
        anchors.centerIn: parent
        width: root.diameter
        height: root.diameter

        property color c: hover.hovered ? root.iconColorHover : root.iconColor
        onCChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var cx = width / 2
            var cy = height / 2
            ctx.fillStyle = c

            // Eight rectangular teeth radiating from the body (r 0.18w → 0.46w),
            // kept just inside the canvas edge so the cardinal teeth don't clip.
            var teeth = 8
            var tw = width * 0.20
            var th = width * 0.28
            for (var i = 0; i < teeth; i++) {
                ctx.save()
                ctx.translate(cx, cy)
                ctx.rotate(i * Math.PI / 4)
                ctx.fillRect(-tw / 2, -(width * 0.46), tw, th)
                ctx.restore()
            }

            // Gear body (overlaps the tooth roots so they fuse into the ring).
            ctx.beginPath()
            ctx.arc(cx, cy, width * 0.34, 0, 2 * Math.PI)
            ctx.fill()

            // Punch a transparent center so the cog reads on any backdrop.
            ctx.globalCompositeOperation = "destination-out"
            ctx.beginPath()
            ctx.arc(cx, cy, width * 0.13, 0, 2 * Math.PI)
            ctx.fill()
            ctx.globalCompositeOperation = "source-over"
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.clicked() }

    Accessible.role: Accessible.Button
    Accessible.name: I18n.t("供应商设置", "Provider settings")
    Accessible.onPressAction: root.clicked()
}
