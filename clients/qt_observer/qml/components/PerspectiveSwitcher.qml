import QtQuick
import QtQuick.Controls
import qt_observer

ComboBox {
    id: root
    objectName: "perspectiveSwitcher"

    property var perspectiveLabels: ({
        "god": "God View",
        "public": "Public",
        "role:p1": "Role: p1 (Werewolf)",
        "role:p2": "Role: p2 (Werewolf)",
        "role:p3": "Role: p3 (Seer)",
        "role:p4": "Role: p4 (Witch)",
        "role:p5": "Role: p5 (Villager)",
        "role:p6": "Role: p6 (Villager)",
        "team:werewolf": "Team: Werewolf",
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
