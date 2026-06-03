import QtQuick
import QtQuick.Controls
import qt_observer

ApplicationWindow {
    id: root
    objectName: "werewolfObserverMainWindow"
    width: 1280
    height: 800
    visible: true
    title: qsTr("Werewolf Observer")

    Loader {
        id: shellLoader
        objectName: "appShellLoader"
        anchors.fill: parent
        source: "qml/AppShell.qml"
    }
}
