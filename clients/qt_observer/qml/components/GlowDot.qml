import QtQuick

// Status indicator dot with an optional pulsing halo.
Item {
    id: root

    property color color: "#34D399"
    property bool pulse: false
    property int diameter: 8

    implicitWidth: diameter
    implicitHeight: diameter

    Rectangle {
        id: halo
        anchors.centerIn: parent
        width: root.diameter * 2.4
        height: width
        radius: width / 2
        color: root.color
        opacity: 0.0
        visible: root.pulse
    }

    Rectangle {
        anchors.centerIn: parent
        width: root.diameter
        height: root.diameter
        radius: width / 2
        color: root.color
    }

    SequentialAnimation {
        running: root.pulse
        loops: Animation.Infinite
        ParallelAnimation {
            NumberAnimation { target: halo; property: "opacity"; from: 0.5; to: 0.0; duration: 1500; easing.type: Easing.OutCubic }
            NumberAnimation { target: halo; property: "scale"; from: 0.55; to: 1.0; duration: 1500; easing.type: Easing.OutCubic }
        }
    }
}
