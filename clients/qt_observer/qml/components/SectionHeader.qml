import QtQuick
import qt_observer

// Section title with an optional caption underneath.
Column {
    id: root

    property string title: ""
    property string caption: ""
    property bool onLight: false

    spacing: Theme.space.xs

    Text {
        text: root.title
        color: root.onLight ? Theme.warm.ink : Theme.color.text
        font.family: root.onLight ? Theme.fontFamilies.serif : Theme.font.family
        font.contextFontMerging: root.onLight
        font.pixelSize: root.onLight ? Theme.warmSize.titleLg : Theme.size.h2
        font.weight: Theme.weight.semibold
        lineHeightMode: Text.ProportionalHeight
        lineHeight: 1.15
    }

    Text {
        visible: root.caption !== ""
        text: root.caption
        color: root.onLight ? Theme.warm.muted : Theme.color.textMuted
        font.family: Theme.font.family
        font.pixelSize: Theme.size.caption
    }
}
