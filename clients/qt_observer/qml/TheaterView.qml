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
            ObserverClient.refreshProjection()
            // Only tail the live stream for an active run; a completed run's events were
            // already loaded by openRun (avoids a redundant SSE replay storm on re-open).
            if (!ObserverClient.connected
                    && ObserverClient.currentStatus !== "completed"
                    && ObserverClient.currentStatus !== "failed")
                ObserverClient.connectStream()
        }
        // Re-open case: if events are already loaded when the view mounts (history entry),
        // no change signal will fire — check immediately (deferred so queue source binding
        // has a chance to evaluate first).
        Qt.callLater(theaterRoot._maybeAutoSeekReport)
    }

    // Stage status — never leave the user guessing whether it is waiting or ended.
    readonly property bool _runOver: ObserverClient.currentStatus === "completed" || ObserverClient.currentStatus === "failed"
    readonly property string _statusText: {
        if (ObserverClient.currentRunId === "" || !eventQueue.atEnd)
            return ""
        return _runOver ? I18n.t("对局结束", "Game over") : I18n.t("等待 AI 行动…", "Waiting for the next AI move…")
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

            AppButton {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("← 返回", "← Back")
                variant: "ghost"
                onClicked: {
                    ObserverClient.disconnectStream()
                    theaterRoot.StackView.view.parent.navigateHome()
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: I18n.t("剧场观战", "Theater")
                color: Theme.color.text
                font.family: Theme.font.display
                font.pixelSize: Theme.size.h1
                font.weight: Theme.weight.bold
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

    // -------------------------------------------------------- Top phase progress axis
    // Sits between the app bar and the stage (its own band, never overlapping the buttons).
    PhaseTimeline {
        id: phaseAxis
        anchors.top: topBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.xs
        anchors.leftMargin: Theme.space.xl
        anchors.rightMargin: Theme.space.xl
        phases: eventQueue.phaseTimeline
        phase: eventQueue.layoutPhase === "night" ? "night" : "day"
        action: eventQueue.currentAction
        visible: eventQueue.phaseTimeline.length > 0
    }

    // Z-axis separator — a hair-thin, very dim line so the control rail floats above the
    // stage instead of sharing its plane.
    Rectangle {
        anchors.top: phaseAxis.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.sm
        height: 1
        visible: phaseAxis.visible
        color: Theme.withAlpha(Theme.color.text, 0.08)
    }

    // ------------------------------------------------------------------- Stage
    // Two ABSOLUTELY SEPARATED, fixed containers — the ring stage (left) and the event feed
    // (right). The containers NEVER move; only their contents breathe per phase (the ring
    // scales/centers inside its own box, the feed dims). This keeps the waterfall — and its
    // console link / jump pill — pinned to the right like a game kill-feed (no fly-around).
    Item {
        id: stage
        anchors.top: phaseAxis.visible ? phaseAxis.bottom : topBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.space.xl
        anchors.topMargin: Theme.space.md
        anchors.bottomMargin: 40 + Theme.space.md   // reserve the (now quiet) collapsed evidence line

        // LEFT — ring stage (fixed ~56% of the width). The ring only resizes WITHIN here.
        Item {
            id: ringStage
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: parent.width * 0.56
            readonly property real maxRing: Math.min(width, height)

            SeatRing {
                id: ring
                players: ObserverClient.playerItems
                deadIds: eventQueue.deadPlayers   // who has died up to the playback cursor
                current: eventQueue.current
                layoutPhase: eventQueue.layoutPhase
                perspective: ObserverClient.currentPerspective   // single source; never handler-assigned (P1-C)
                // Base geometry: centered in ringStage; states override only the size, so x/y
                // (bound to width/height) keep it centered while it breathes.
                width: ringStage.maxRing * 0.62
                height: width
                x: (ringStage.width - width) / 2
                y: (ringStage.height - height) / 2
            }
        }

        // RIGHT — event feed (fixed, pinned to the right edge). Only opacity breathes.
        Item {
            id: feedPanel
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: ringStage.right
            anchors.leftMargin: Theme.space.xxl

            SpeechTheater {
                id: speech
                anchors.fill: parent
                current: eventQueue.current
                players: ObserverClient.playerItems
                onOpenInConsole: evidence.mode = 2
                // Hovering a waterfall row re-arms that past line on the ring.
                onHoverEvent: (actor, target, type) => {
                    ring.hoverActor = actor; ring.hoverTarget = target; ring.hoverType = type
                }
                onClearHover: { ring.hoverActor = ""; ring.hoverTarget = ""; ring.hoverType = "" }
            }
        }

        // Stage status pill (waiting for the next move / game over) — centered over the ring.
        Rectangle {
            visible: theaterRoot._statusText !== ""
            anchors.horizontalCenter: ringStage.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: Theme.space.md
            implicitWidth: statusRow.implicitWidth + Theme.space.lg * 2
            implicitHeight: statusRow.implicitHeight + Theme.space.sm * 2
            radius: Theme.radius.pill
            color: Theme.color.surfaceInset
            border.width: 1
            border.color: Theme.color.border
            Row {
                id: statusRow
                anchors.centerIn: parent
                spacing: Theme.space.sm
                GlowDot {
                    anchors.verticalCenter: parent.verticalCenter
                    diameter: 8
                    pulse: !theaterRoot._runOver
                    color: theaterRoot._runOver ? Theme.color.completed : Theme.color.info
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: theaterRoot._statusText
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.caption
                }
            }
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

    // ------------------------------------------------- P2-D settlement overlay (§7.7)
    // Same-view overlay (NOT a StackView page swap, NOT an AppShell nav target, §14.1).
    // Activates ONLY when the run is `completed` (never `failed`, §2.5) AND its
    // game-log is present (projection players loaded) AND the event queue has drained.
    // `failed` runs keep the existing P2-C-1 failure pill untouched.
    readonly property bool _settlementReady:
        ObserverClient.currentStatus === "completed"
        && ObserverClient.playerItems.length > 0
        && eventQueue.atEnd
    // entryMode discriminator (§3.3): history "查看战报" opens straight to `report`
    // (no freeze); a live watch shows the `freeze` ceremony. The intent is set
    // SYNCHRONOUSLY at the call site via openRun(forReport) and carried on
    // ObserverClient.settlementEntry — reliable here, unlike the old async-status latch.
    readonly property int settlementEntryMode: ObserverClient.settlementEntry

    // §5 report entry: auto fast-forward the replay queue ONCE per run, only when
    // (entry==report) ∧ (run completed) ∧ (queue actually populated). 「打开」(entry 0)
    // never reaches this. Latch is keyed by runId: refresh/language-switch can't
    // re-trigger; a genuine view rebuild restarts the queue, so re-seeking then is
    // the CORRECT outcome (jump to the end again), and the fresh latch allows it.
    property string _autoSeekDoneForRun: ""

    function _maybeAutoSeekReport() {
        if (ObserverClient.settlementEntry !== 1) return                  // rule 5: open untouched
        if (ObserverClient.currentStatus !== "completed") return          // rule 1: completed only
        if (ObserverClient.currentRunId === "") return
        if (eventQueue.queuedCount === 0) return                      // rule 2: queue filled
        if (_autoSeekDoneForRun === ObserverClient.currentRunId) return   // rule 3: one-shot
        _autoSeekDoneForRun = ObserverClient.currentRunId
        eventQueue.setInstant()   // spec §5 "immediately drains": skip per-event holds (same mode as the 瞬时 control)
        eventQueue.seekQueueEnd()
    }

    Connections {
        target: ObserverClient
        function onEventItemsChanged() { Qt.callLater(theaterRoot._maybeAutoSeekReport) }
        function onCurrentStatusChanged() { Qt.callLater(theaterRoot._maybeAutoSeekReport) }
    }

    Loader {
        id: settlementLoader
        anchors.fill: parent
        active: theaterRoot._settlementReady
        visible: active
        sourceComponent: SettlementView {
            objectName: "settlementView"
            entryMode: theaterRoot.settlementEntryMode
            // Exit the settlement overlay: stop streaming and leave the theater page.
            // History entry (mode 1) returns to the history list; a live watch returns home.
            onExitRequested: {
                ObserverClient.disconnectStream()
                var nav = theaterRoot.StackView.view.parent
                if (theaterRoot.settlementEntryMode === 1)
                    nav.navigateHistory()
                else
                    nav.navigateHome()
            }
        }
    }

    // ----------------------------------------------- Breathing layout (P2-D / D5)
    // Only the ring's SIZE and the feed's OPACITY change — never container positions. The
    // ring's x/y are bound to its (animating) size so it stays centered as it breathes.
    states: [
        State {
            name: "night"   // ring takes the WHOLE stage; feed fades fully out
            PropertyChanges { target: ringStage; width: stage.width }
            PropertyChanges { target: ring; width: ringStage.maxRing * 0.86 }
            PropertyChanges { target: feedPanel; opacity: 0.0 }
        },
        State {
            name: "day"     // ring at ~56%; feed at full brightness
            PropertyChanges { target: ringStage; width: stage.width * 0.56 }
            PropertyChanges { target: ring; width: ringStage.maxRing * 0.60 }
            PropertyChanges { target: feedPanel; opacity: 1.0 }
        },
        State {
            name: "voting"  // ring mid-size (tally on the ring); feed bright
            PropertyChanges { target: ringStage; width: stage.width * 0.56 }
            PropertyChanges { target: ring; width: ringStage.maxRing * 0.80 }
            PropertyChanges { target: feedPanel; opacity: 1.0 }
        }
    ]

    transitions: Transition {
        ParallelAnimation {
            id: phaseAnim
            // The ring stage container expands/contracts; the ring rescales within it; the
            // feed dissolves. x/y stay bound so the ring keeps centred throughout.
            NumberAnimation {
                target: ringStage
                property: "width"
                duration: 700
                easing.type: Easing.InOutCubic
            }
            NumberAnimation {
                target: ring
                property: "width"
                duration: 700
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: feedPanel
                property: "opacity"
                duration: 600
                easing.type: Easing.OutCubic
            }
            // D5: the queue stays gated until the layout settles, then resumes consuming.
            onStopped: eventQueue.resumeAfterTransition()
        }
    }
}
