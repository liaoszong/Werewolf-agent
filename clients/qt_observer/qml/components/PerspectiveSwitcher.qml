import QtQuick
import QtQuick.Controls
import qt_observer

ComboBox {
    id: root
    objectName: "perspectiveSwitcher"

    property var perspectiveLabels: ({
        "god": "God View",
        "public": "Public",
        "role:p1": "Seat p1",
        "role:p2": "Seat p2",
        "role:p3": "Seat p3",
        "role:p4": "Seat p4",
        "role:p5": "Seat p5",
        "role:p6": "Seat p6",
        "team:werewolf": "Werewolf Team",
    })

    model: ["god", "public", "role:p1", "role:p2", "role:p3", "role:p4", "role:p5", "role:p6", "team:werewolf"]

    textRole: "label"
    valueRole: "value"

    Component.onCompleted: {
        var list = []
        for (var i = 0; i < model.length; i++) {
            var val = model[i]
            list.push({ label: perspectiveLabels[val] || val, value: val })
        }
        model = list
        for (var j = 0; j < list.length; j++) {
            if (list[j].value === ObserverClient.currentPerspective) {
                currentIndex = j
                break
            }
        }
    }

    onCurrentIndexChanged: {
        if (currentIndex >= 0 && currentIndex < model.length) {
            var selected = model[currentIndex].value
            if (selected !== ObserverClient.currentPerspective) {
                ObserverClient.currentPerspective = selected
            }
        }
    }
}
