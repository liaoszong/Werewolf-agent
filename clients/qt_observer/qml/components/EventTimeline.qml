import QtQuick
import QtQuick.Controls
import qt_observer

// Nightfall event timeline — dark, faction-aware rows with phase accent stripes.
// Behavior unchanged: model + bindings come straight from ObserverClient.eventItems.
Column {
    id: root
    objectName: "eventTimeline"

    property alias listView: eventTimelineList

    // Empty placeholder, centered, when the timeline has no events yet.
    Item {
        width: parent.width
        height: parent.height
        visible: ObserverClient.eventItems.length === 0

        EmptyState {
            anchors.centerIn: parent
            title: I18n.t("暂无事件", "No events yet")
            subtitle: I18n.t("开始对局后将在此显示时间线。", "Start a match to see the timeline.")
        }
    }

    ListView {
        id: eventTimelineList
        objectName: "eventTimelineList"
        width: parent.width
        height: parent.height
        model: ObserverClient.eventItems
        clip: true
        visible: ObserverClient.eventItems.length !== 0

        delegate: Rectangle {
            id: rowDelegate
            width: ListView.view.width
            height: 36
            color: index % 2 ? Theme.color.surface : Theme.color.surfaceInset

            // Phase-driven left accent stripe: night = silver, day = amber, else neutral border.
            readonly property string _phase: modelData.phase !== undefined
                                             ? ("" + modelData.phase).toLowerCase()
                                             : ""
            readonly property color _stripe: _phase.indexOf("night") >= 0
                                             ? Theme.color.textSecondary
                                             : (_phase.indexOf("day") >= 0
                                                ? Theme.color.warning
                                                : Theme.color.border)

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 3
                color: rowDelegate._stripe
            }

            // Bottom hairline divider.
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Theme.withAlpha(Theme.color.border, 0.6)
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.space.md
                spacing: Theme.space.md

                Text {
                    visible: modelData.seq !== undefined
                    text: modelData.seq !== undefined ? "#" + modelData.seq : ""
                    width: 44
                    elide: Text.ElideRight
                    font.family: Theme.font.mono
                    font.pixelSize: Theme.size.micro
                    color: Theme.color.textMuted
                }

                Text {
                    text: modelData.kind || ""
                    width: 140
                    elide: Text.ElideRight
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.caption
                    font.weight: Theme.weight.semibold
                    color: Theme.color.text
                }

                Text {
                    text: modelData.phase || ""
                    width: 64
                    elide: Text.ElideRight
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro
                    color: Theme.color.textSecondary
                }

                Text {
                    visible: modelData.round !== undefined
                    text: modelData.round !== undefined ? "R" + modelData.round : ""
                    width: 44
                    elide: Text.ElideRight
                    font.family: Theme.font.mono
                    font.pixelSize: Theme.size.micro
                    color: Theme.color.textMuted
                }

                Text {
                    text: modelData.actor || ""
                    width: 64
                    elide: Text.ElideRight
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro
                    color: Theme.color.text
                }

                Text {
                    text: modelData.visibility || ""
                    elide: Text.ElideRight
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro
                    color: Theme.color.textMuted
                }
            }
        }
    }
}
