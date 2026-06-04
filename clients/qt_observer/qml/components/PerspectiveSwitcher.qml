import QtQuick
import QtQuick.Controls
import qt_observer

// Perspective switcher — choose which observer "lens" the run is viewed through.
// Restyled for the dark "Nightfall" look; labels are localized at display time
// (reactive via I18n). All perspective values and ObserverClient wiring are
// unchanged, and seat labels stay generic ("Seat pN") to preserve the trust
// boundary — they never reveal a player's role.
ComboBox {
    id: root
    objectName: "perspectiveSwitcher"

    model: ["god", "public", "role:p1", "role:p2", "role:p3", "role:p4", "role:p5", "role:p6", "team:werewolf"]

    function labelFor(value) {
        switch (value) {
        case "god": return I18n.t("上帝视角", "God View")
        case "public": return I18n.t("公开", "Public")
        case "role:p1": return I18n.t("座位 p1", "Seat p1")
        case "role:p2": return I18n.t("座位 p2", "Seat p2")
        case "role:p3": return I18n.t("座位 p3", "Seat p3")
        case "role:p4": return I18n.t("座位 p4", "Seat p4")
        case "role:p5": return I18n.t("座位 p5", "Seat p5")
        case "role:p6": return I18n.t("座位 p6", "Seat p6")
        case "team:werewolf": return I18n.t("狼人阵营", "Werewolf Team")
        default: return value
        }
    }

    Component.onCompleted: {
        for (var i = 0; i < model.length; i++) {
            if (model[i] === ObserverClient.currentPerspective) {
                currentIndex = i
                break
            }
        }
    }

    onCurrentIndexChanged: {
        if (currentIndex >= 0 && currentIndex < model.length) {
            var selected = model[currentIndex]
            if (selected !== undefined && selected !== ObserverClient.currentPerspective) {
                ObserverClient.currentPerspective = selected
            }
        }
    }

    // ---------------------------------------------------------------- Geometry
    implicitWidth: 168
    implicitHeight: 34
    leftPadding: Theme.space.md
    rightPadding: Theme.space.xl + Theme.space.md

    readonly property bool _active: hovered || down || popup.visible

    // ------------------------------------------------------------- Background
    background: Rectangle {
        implicitWidth: 150
        implicitHeight: 34
        radius: Theme.radius.sm
        color: Theme.color.surface
        border.width: 1
        border.color: root._active ? Theme.color.borderStrong : Theme.color.border

        Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
    }

    // ------------------------------------------------------------ Content text
    contentItem: Text {
        text: root.currentIndex >= 0 ? root.labelFor(root.model[root.currentIndex]) : ""
        color: Theme.color.text
        font.family: Theme.font.family
        font.pixelSize: Theme.size.caption
        font.weight: Theme.weight.medium
        verticalAlignment: Text.AlignVCenter
        leftPadding: Theme.space.md
        elide: Text.ElideRight
    }

    // -------------------------------------------------------- Chevron indicator
    indicator: Item {
        x: root.width - width - Theme.space.md
        y: root.topPadding + (root.availableHeight - height) / 2
        width: 12
        height: 8

        rotation: root.popup.visible ? 180 : 0
        Behavior on rotation { NumberAnimation { duration: Theme.motion.fast; easing.type: Easing.OutCubic } }

        // Two short bars forming a downward chevron "v".
        Rectangle {
            x: 0
            y: 1
            width: 8
            height: 1.5
            radius: 0.75
            color: root._active ? Theme.color.text : Theme.color.textSecondary
            transformOrigin: Item.BottomLeft
            rotation: 45
            antialiasing: true
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        }
        Rectangle {
            x: 6
            y: 1
            width: 8
            height: 1.5
            radius: 0.75
            color: root._active ? Theme.color.text : Theme.color.textSecondary
            transformOrigin: Item.BottomLeft
            rotation: 135
            antialiasing: true
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        }
    }

    // -------------------------------------------------------------- Delegate
    delegate: ItemDelegate {
        id: delegateItem
        required property var modelData
        required property int index

        width: ListView.view ? ListView.view.width : root.width
        height: 32
        padding: 0

        contentItem: Item {
            anchors.fill: parent

            // Left accent bar marking the currently selected perspective.
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 2
                color: Theme.color.primary
                visible: root.currentIndex === delegateItem.index
            }

            Text {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: Theme.space.md
                anchors.rightMargin: Theme.space.md
                text: root.labelFor(delegateItem.modelData)
                color: Theme.color.text
                font.family: Theme.font.family
                font.pixelSize: Theme.size.caption
                font.weight: root.currentIndex === delegateItem.index ? Theme.weight.semibold : Theme.weight.regular
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }

        background: Rectangle {
            color: delegateItem.highlighted
                   ? Theme.withAlpha(Theme.color.primary, 0.18)
                   : "transparent"
        }

        highlighted: root.highlightedIndex === index
    }

    // ----------------------------------------------------------------- Popup
    popup: Popup {
        y: root.height + Theme.space.xs
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 2, 320)
        padding: 1

        background: Rectangle {
            color: Theme.color.surfaceAlt
            radius: Theme.radius.md
            border.width: 1
            border.color: Theme.color.border
        }

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex

            ScrollIndicator.vertical: ScrollIndicator { }
        }
    }
}
