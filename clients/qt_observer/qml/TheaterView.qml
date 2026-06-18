import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// P2 上帝视角圆桌直播页（navigateCockpit target）。重做为 CockpitSurface 的 live 宿主：
// 把 ObserverClient.* 绑到表现组件属性（绑定语义逐字保留），视角切换在左上单实例，
// 票数走 eventQueue.voteTally（按播放游标截断，绝不显示未来票），审计 EvidenceConsole
// 底部全宽（showPerspectiveSwitcher:false 避免与左上重复）。结算同页 overlay 不变。
Item {
    id: theaterRoot
    objectName: "theaterView"
    state: eventQueue.layoutPhase

    Component.onCompleted: {
        if (ObserverClient.currentRunId !== "") {
            ObserverClient.refreshProjection()
            // Only tail the live stream for an active run; a completed run's events were
            // already loaded by openRun (avoids a redundant SSE replay storm on re-open).
            if (ObserverClient.currentStatus !== "completed"
                    && ObserverClient.currentStatus !== "failed"
                    && ObserverClient.currentStatus !== "interrupted")
                ObserverClient.connectStream()
        }
        Qt.callLater(theaterRoot._maybeAutoSeekReport)
    }
    Component.onDestruction: ObserverClient.disconnectStream()

    // Re-fetch the (enriched) projection as new events arrive, throttled.
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

    // Non-visual presentation queue: thin SSE notifications joined with enriched
    // projection summaries, paced onto the stage.
    EventPresentationQueue {
        id: eventQueue
        source: ObserverClient.eventItems
        enriched: ObserverClient.projectionEvents
    }

    // Majority line = floor(alive/2) + 1, alive = seats minus those dead up to the cursor.
    readonly property int _deadCount: eventQueue.deadPlayers ? eventQueue.deadPlayers.length : 0
    readonly property int _majority: Math.floor((ObserverClient.playerItems.length - theaterRoot._deadCount) / 2) + 1

    // -------------------------------------------------------------- The stage
    CockpitSurface {
        id: surface
        anchors { left: parent.left; right: parent.right; top: parent.top; bottom: evidence.top }
        players: ObserverClient.playerItems
        deadIds: eventQueue.deadPlayers
        speakingId: eventQueue.current ? (eventQueue.current.actor || "") : ""
        phase: eventQueue.layoutPhase
        round: eventQueue.currentRound
        votes: eventQueue.voteTally
        majority: theaterRoot._majority
        dataSourceText: ObserverClient.currentExecutionMode === "live"
                        ? I18n.t("真实 LIVE", "LIVE") : I18n.t("模拟", "SIMULATION")
        perspectiveText: I18n.t("视角：", "View: ") + ObserverClient.currentPerspective
        live: ObserverClient.connected
        phaseTimeline: eventQueue.phaseTimeline
        currentAction: eventQueue.currentAction
        perspectiveSlot: livePerspective
        eventLogSlot: liveEventLog
        playbackSlot: livePlayback
        // 审计在底部全宽 EvidenceConsole（下），左区不再放，故 auditSlot 不注入。
        onBackRequested: {
            ObserverClient.disconnectStream()
            theaterRoot.StackView.view.parent.returnFromCockpit()
        }
    }

    // 视角切换（左上,单实例,P1-C：只写 currentPerspective,绝不写 ring.perspective）。
    // 不带 objectName：EvidenceConsole 里那个（隐藏）保留 "perspectiveSwitcher" 契约名,
    // 此处不复用同名,避免 findChild 歧义。
    Component { id: livePerspective; PerspectiveSwitcher { } }
    // Left event log shares the SAME playback cursor as the stage (presentedEvents),
    // so a log entry reveals exactly when its event lands on the table.
    Component { id: liveEventLog;   EventLogPanel { live: ObserverClient.connected; events: eventQueue.presentedEvents } }
    Component { id: livePlayback;   PlaybackBar { queue: eventQueue } }

    // ------------------------------------------------------ Bottom evidence console
    // Full-width honesty chain (boundary / projection proof / raw log / audit links).
    // showPerspectiveSwitcher:false — the seat lens lives in CockpitSurface's top-left
    // perspectiveSlot, so the two never both write ObserverClient.currentPerspective.
    EvidenceConsole {
        id: evidence
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        perspective: ObserverClient.currentPerspective
        showPerspectiveSwitcher: false
    }

    // ------------------------------------------------- P2-D settlement overlay (§7.7)
    // Same-view overlay (NOT a StackView page swap, NOT an AppShell nav target, §14.1).
    // Activates ONLY when the run is `completed` (never `failed`, §2.5) AND its
    // game-log is present (projection players loaded) AND the event queue has drained.
    readonly property bool _settlementReady:
        ObserverClient.currentStatus === "completed"
        && ObserverClient.playerItems.length > 0
        && eventQueue.atEnd
    readonly property int settlementEntryMode: ObserverClient.settlementEntry

    // §5 report entry: auto fast-forward the replay queue ONCE per run, only when
    // (entry==report) ∧ (run completed) ∧ (queue actually populated).
    property string _autoSeekDoneForRun: ""

    function _maybeAutoSeekReport() {
        if (ObserverClient.settlementEntry !== 1) return                  // rule 5: open untouched
        if (ObserverClient.currentStatus !== "completed") return          // rule 1: completed only
        if (ObserverClient.currentRunId === "") return
        if (eventQueue.queuedCount === 0) return                      // rule 2: queue filled
        if (_autoSeekDoneForRun === ObserverClient.currentRunId) return   // rule 3: one-shot
        _autoSeekDoneForRun = ObserverClient.currentRunId
        eventQueue.setInstant()
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
            onExitRequested: {
                ObserverClient.disconnectStream()
                var nav = theaterRoot.StackView.view.parent
                if (theaterRoot.settlementEntryMode === 1)
                    nav.returnFromCockpit()
                else
                    nav.navigateHome()
            }
        }
    }

    // -------------------------------------------------- Phase gate (D5) release
    // The queue raises a hard gate at each phase boundary (night/day/voting) and STOPS.
    // After the background crossfade settles, resume consuming. (Full breathing layout
    // lands in Phase 7; here the gate is released after the base crossfade duration.)
    states: [
        State { name: "night" },
        State { name: "day" },
        State { name: "voting" }
    ]
    transitions: Transition {
        SequentialAnimation {
            PauseAnimation { duration: Theme.motion.base }
            ScriptAction { script: eventQueue.resumeAfterTransition() }
        }
    }
}
