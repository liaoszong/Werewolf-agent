import QtQuick
import QtQuick.Controls
import qt_observer

Column {
    id: root
    objectName: "eventTimeline"

    property alias listView: eventTimelineList

    Text {
        id: emptyState
        text: qsTr("No events yet. Start a match to see the timeline.")
        visible: ObserverClient.eventItems.length === 0
        color: "#888"
        font.pixelSize: 14
    }

    ListView {
        id: eventTimelineList
        objectName: "eventTimelineList"
        width: parent.width
        height: parent.height
        model: ObserverClient.eventItems
        clip: true
        visible: !emptyState.visible

        delegate: Rectangle {
            width: ListView.view.width
            height: 36
            color: index % 2 === 0 ? "#fafafa" : "#ffffff"
            border.color: "#e0e0e0"

            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 8
                spacing: 8

                Text {
                    text: modelData.seq !== undefined ? "#" + modelData.seq : ""
                    width: 40
                    font.pixelSize: 11
                    color: "#666"
                }

                Text {
                    text: modelData.kind || ""
                    width: 120
                    font.pixelSize: 12
                    font.bold: true
                }

                Text {
                    text: modelData.phase || ""
                    width: 60
                    font.pixelSize: 11
                    color: "#888"
                }

                Text {
                    text: modelData.round !== undefined ? "R" + modelData.round : ""
                    width: 40
                    font.pixelSize: 11
                    color: "#888"
                }

                Text {
                    text: modelData.actor || ""
                    width: 60
                    font.pixelSize: 11
                }

                Text {
                    text: modelData.visibility || ""
                    width: 60
                    font.pixelSize: 10
                    color: "#aaa"
                }
            }
        }
    }
}
