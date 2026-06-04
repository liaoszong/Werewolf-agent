import QtQuick
import qt_observer

// Section title with an optional caption underneath.
Column {
    id: root

    property string title: ""
    property string caption: ""

    spacing: Theme.space.xs

    Text {
        text: root.title
        color: Theme.color.text
        font.family: Theme.font.family
        font.pixelSize: Theme.size.h2
        font.weight: Theme.weight.semibold
    }

    Text {
        visible: root.caption !== ""
        text: root.caption
        color: Theme.color.textMuted
        font.family: Theme.font.family
        font.pixelSize: Theme.size.caption
    }
}
