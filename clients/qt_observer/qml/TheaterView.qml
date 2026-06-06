import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// P2-C-1 Theater View — the default spectator surface (navigateCockpit target).
// A breathing stage: SeatRing + SpeechTheater reflow by phase (night = ring center,
// day = speech theater, voting = ring + tally), paced by the EventPresentationQueue and
// gated on the layout transition (D5). theaterRoot.state binds eventQueue.layoutPhase
// declaratively (P2-D) so reset() re-syncs the layout. The demoted honesty chain lives in
// the bottom EvidenceConsole; SeatRing.perspective is single-bound to currentPerspective.
Item {
    id: theaterRoot
    objectName: "theaterView"
    state: eventQueue.layoutPhase

    Component.onCompleted: {
        if (ObserverClient.currentRunId !== "") {
            ObserverClient.connectStream()
            ObserverClient.refreshProjection()
        }
    }

    // Re-fetch the (enriched) projection as new events arrive, throttled — summaries
    // back-fill live; the C++ latest-wins guard drops out-of-order responses.
    Connections {
        target: ObserverClient
        function onEventItemsChanged() { projRefreshTimer.restart() }
    }
    Timer {
        id: projRefreshTimer
        interval: 400
        repeat: false
        onTriggered: ObserverClient.refreshProjection()
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.color.bgBase
    }

    // The presentation queue (non-visual): consumes thin SSE notifications, joins enriched
    // projection summaries, paces them onto the stage.
    EventPresentationQueue {
        id: eventQueue
        source: ObserverClient.eventItems
        enriched: ObserverClient.projectionEvents
    }

    // ----------------------------------------------------------------- Top bar
    Item {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.space.xl
        anchors.rightMargin: Theme.space.xl
        height: 56

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.space.md

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("剧场观战", "Theater")
                color: Theme.color.text
                font.family: Theme.font.display
                font.pixelSize: Theme.size.h1
                font.weight: Theme.weight.bold
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("对局 ", "Run ") + ObserverClient.currentRunId
                color: Theme.color.textMuted
                font.family: Theme.font.mono
                font.pixelSize: Theme.size.small
                visible: ObserverClient.currentRunId !== ""
            }
            StatusBadge {
                anchors.verticalCenter: parent.verticalCenter
                status: ObserverClient.currentStatus
            }
        }

        PlaybackControls {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            queue: eventQueue
        }
    }

    // ------------------------------------------------------------------- Stage
    Item {
        id: stage
        anchors.top: topBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.space.xl
        anchors.bottomMargin: 46 + Theme.space.lg   // reserve the closed evidence strip

        readonly property real smallRing: Math.min(stage.width * 0.40, stage.height * 0.72)
        readonly property real bigRing: Math.min(stage.width * 0.92, stage.height * 0.92)
        readonly property real voteRing: Math.min(stage.width * 0.72, stage.height * 0.78)

        SeatRing {
            id: ring
            players: ObserverClient.playerItems
            current: eventQueue.current
            layoutPhase: eventQueue.layoutPhase
            perspective: ObserverClient.currentPerspective   // single source; never handler-assigned (P1-C)
            // base geometry (overridden by states/transitions)
            x: 0
            y: 0
            width: stage.smallRing
            height: stage.smallRing
        }

        SpeechTheater {
            id: speech
            current: eventQueue.current
            x: stage.smallRing + Theme.space.xxl
            y: 0
            width: stage.width - stage.smallRing - Theme.space.xxl
            height: stage.height
            onOpenInConsole: evidence.mode = 2
        }
    }

    // ------------------------------------------------------ Bottom evidence console
    EvidenceConsole {
        id: evidence
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        perspective: ObserverClient.currentPerspective
    }

    // ----------------------------------------------- Breathing layout (P2-D / D5)
    states: [
        State {
            name: "night"
            PropertyChanges {
                target: ring
                x: (stage.width - stage.bigRing) / 2
                y: (stage.height - stage.bigRing) / 2
                width: stage.bigRing
                height: stage.bigRing
            }
            PropertyChanges {
                target: speech
                opacity: 0.0
                x: stage.width * 0.2
                y: stage.height * 0.82
                width: stage.width * 0.6
                height: stage.height * 0.18
            }
        },
        State {
            name: "day"
            PropertyChanges {
                target: ring
                x: 0
                y: (stage.height - stage.smallRing) / 2
                width: stage.smallRing
                height: stage.smallRing
            }
            PropertyChanges {
                target: speech
                opacity: 1.0
                x: stage.smallRing + Theme.space.xxl
                y: 0
                width: stage.width - stage.smallRing - Theme.space.xxl
                height: stage.height
            }
        },
        State {
            name: "voting"
            PropertyChanges {
                target: ring
                x: (stage.width - stage.voteRing) / 2
                y: 0
                width: stage.voteRing
                height: stage.voteRing
            }
            PropertyChanges {
                target: speech
                opacity: 1.0
                x: stage.width * 0.12
                y: stage.height * 0.80
                width: stage.width * 0.76
                height: stage.height * 0.20
            }
        }
    ]

    transitions: Transition {
        ParallelAnimation {
            id: phaseAnim
            NumberAnimation {
                targets: [ring, speech]
                properties: "x,y,width,height,opacity"
                duration: 700
                easing.type: Easing.OutCubic
            }
            // D5: the queue stays gated until the layout settles, then resumes consuming.
            onStopped: eventQueue.resumeAfterTransition()
        }
    }
}
