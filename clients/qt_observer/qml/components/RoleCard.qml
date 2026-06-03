import QtQuick

Item {
    id: root
    objectName: "roleCard"

    property string seatId: ""
    property string roleName: ""
    property string displayRole: ""
    property string displayTeam: ""
    property string visibilityLabel: ""
    property string aiLabel: ""
    property string statusText: ""
    property string accentText: ""
    property bool selected: false

    width: 140
    height: 160

    Rectangle {
        anchors.fill: parent
        radius: 8
        color: root.selected ? "#e3f2fd" : "#f5f5f5"
        border.color: root.selected ? "#1976d2" : "#bdbdbd"
        border.width: root.selected ? 2 : 1
    }

    Column {
        anchors.centerIn: parent
        spacing: 4
        padding: 8

        Text {
            text: root.seatId
            font.pixelSize: 12
            font.bold: true
            color: "#333"
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Rectangle {
            width: 48
            height: 48
            radius: 24
            color: "#e0e0e0"
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.centerIn: parent
                text: {
                    var r = root.displayRole !== "" ? root.displayRole : root.roleName;
                    if (r === "unknown") return "?";
                    return r.substring(0, 2);
                }
                font.pixelSize: 14
                font.bold: true
                color: "#555"
            }
        }

        Text {
            text: {
                var r = root.displayRole !== "" ? root.displayRole : root.roleName;
                if (r === "unknown") return "Hidden";
                return r;
            }
            font.pixelSize: 13
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: root.displayTeam !== "" ? root.displayTeam : ""
            font.pixelSize: 11
            color: "#666"
            anchors.horizontalCenter: parent.horizontalCenter
            visible: text !== ""
        }

        Text {
            text: root.visibilityLabel !== "" ? root.visibilityLabel : ""
            font.pixelSize: 10
            color: "#1976d2"
            anchors.horizontalCenter: parent.horizontalCenter
            visible: text !== ""
        }

        Text {
            text: root.aiLabel
            font.pixelSize: 11
            color: "#666"
            anchors.horizontalCenter: parent.horizontalCenter
            visible: text !== ""
        }

        Text {
            text: root.statusText
            font.pixelSize: 11
            color: "#888"
            anchors.horizontalCenter: parent.horizontalCenter
            visible: text !== ""
        }
    }
}
