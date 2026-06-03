import QtQuick

Rectangle {
    id: root
    property string status: ""

    width: 80
    height: 24
    radius: 4

    color: {
        switch (root.status) {
            case "running": return "#4caf50";
            case "completed": return "#2196f3";
            case "failed": return "#f44336";
            case "queued": return "#ff9800";
            default: return "#9e9e9e";
        }
    }

    Text {
        anchors.centerIn: parent
        text: root.status
        color: "white"
        font.pixelSize: 12
    }
}
