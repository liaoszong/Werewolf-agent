pragma ComponentBehavior: Bound
import QtQuick
import qt_observer

// P2-C-1 Event Presentation Queue (non-visual controller).
//
// Consumes thin runtime notifications (ObserverClient.eventItems) in APPEND order,
// normalizes each into a PresentationEvent (type from payload.type, summary/target
// joined from the enriched per-perspective projection), and paces them onto the stage
// with a hard yield-gate for phase transitions.
//
// Presentation-only invariant: de-dup by event_id, NEVER reorder/sort, NEVER synthesize
// business events, NEVER write back to the server. `current` is a computed binding so a
// late projectionEvents back-fills the on-screen event's summary/target without re-pump.
QtObject {
    id: queue
    objectName: "eventQueue"

    // --- inputs (bound by TheaterView) ---
    property var source: []            // ObserverClient.eventItems (thin SSE/replay notifications)
    property var enriched: []          // ObserverClient.projectionEvents (per-perspective: data.summary + target)

    // --- exposed presentation state ---
    property int consumedSeq: 0
    property var _currentRaw: null      // raw runtime event currently on stage (drives `current`)
    // P1-A: `current` is a COMPUTED PresentationEvent — recomputes when `enriched`
    // arrives late so a still-displayed event back-fills summary/target WITHOUT re-pumping.
    readonly property var current: _currentRaw ? _present(_currentRaw) : ({})
    property string layoutPhase: "day"  // "night" | "day" | "voting"
    property bool waiting: false
    property bool playing: true
    property real speed: 1.0
    property bool instant: false

    signal phaseBoundary(string phase, int round)   // UI marker ONLY — never a runtime event

    // --- enrichment lookup: game-log event_id -> {summary (from data.summary), target} ---
    readonly property var _enrichedById: {
        var m = ({})
        for (var i = 0; i < enriched.length; i++) {
            var e = enriched[i]
            var gid = (e && e.payload) ? e.payload.event_id : (e ? e.event_id : "")
            if (!gid)
                continue
            var summ = (e && e.data && e.data.summary) ? e.data.summary : ""
            m[gid] = { summary: summ, target: (e && e.target) ? e.target : "none" }
        }
        return m
    }

    // Normalize a thin rawRuntime notification into the PresentationEvent the stage reads.
    function _present(raw) {
        var gid = (raw && raw.payload) ? raw.payload.event_id : (raw ? raw.event_id : "")
        var enr = (gid && _enrichedById[gid]) ? _enrichedById[gid] : { summary: "", target: "none" }
        return {
            event_id: gid,
            sequence: _seq(raw),
            round: (raw && raw.round !== undefined) ? raw.round : 0,
            phase: (raw && raw.phase) ? raw.phase : "",
            actor: (raw && raw.actor) ? raw.actor : "",
            visibility: (raw && raw.visibility) ? raw.visibility : "",
            type: (raw && raw.payload) ? raw.payload.type : "",   // type = rawRuntime.payload.type
            target: enr.target,                                    // from matching projection event
            summary: enr.summary                                  // from matching projection event data.summary
        }
    }
    function _seq(ev) {
        return (ev && ev.sequence !== undefined) ? ev.sequence
             : ((ev && ev.seq !== undefined) ? ev.seq : 0)
    }

    // Authoritative ordered view: de-dup by event_id, PRESERVE append order (no sort).
    readonly property var _ordered: {
        var out = []
        var seen = ({})
        for (var i = 0; i < source.length; i++) {
            var ev = source[i]
            var id = (ev && ev.payload) ? ev.payload.event_id : (ev ? ev.event_id : "")
            if (!id || seen[id])
                continue
            seen[id] = true
            out.push(ev)
        }
        return out
    }

    function _phaseOf(ev) {
        var t = ev ? (ev.payload ? ev.payload.type : ev.type) : ""
        if (t === "player_vote" || t === "player_eliminated")
            return "voting"
        return (ev && ev.phase === "night") ? "night" : "day"
    }
    function _durationMs(ev) {
        var t = ev ? (ev.payload ? ev.payload.type : ev.type) : ""
        var base = ({ role_assignment: 1000, werewolf_kill: 1800, seer_check: 1800,
            witch_save: 1800, witch_kill: 1800, witch_pass: 1500, player_died: 2000,
            player_speech: 6000, player_vote: 1200, day_announcement: 1000,
            player_eliminated: 2000, role_revealed: 2000, game_over: 3000 })[t] || 1200
        return instant ? 16 : Math.max(16, base / Math.max(1, speed))
    }

    property int _cursor: 0
    property bool _gated: false

    property Timer _tick: Timer {
        interval: 200
        repeat: true
        running: queue.playing
        onTriggered: queue._pump()
    }

    function _pump() {
        if (_gated || !playing)
            return
        if (_cursor >= _ordered.length) {
            waiting = (ObserverClient.currentStatus === "running")
            return
        }
        waiting = false
        var raw = _ordered[_cursor]
        if (_seq(raw) < consumedSeq) {   // sequence regression = a new generation slipped in
            reset()
            return
        }
        var ph = _phaseOf(raw)
        if (ph !== layoutPhase) {        // phase transition -> raise gate, emit marker, STOP (D5)
            layoutPhase = ph
            _gated = true
            phaseBoundary(ph, raw.round || 0)
            return
        }
        _currentRaw = raw                // `current` recomputes via binding (reactive back-fill, P1-A)
        consumedSeq = _seq(raw)
        _cursor += 1
        _tick.interval = _durationMs(raw)
    }

    // --- Reset protocol (run / perspective / source-generation change) ---
    function reset() {
        _cursor = 0
        _currentRaw = null
        _gated = false
        waiting = false
        consumedSeq = 0
        layoutPhase = "day"
        _tick.interval = 200
    }
    property int _lastSourceLen: 0
    onSourceChanged: {
        if (source.length < _lastSourceLen)   // truncation = a new generation
            reset()
        _lastSourceLen = source.length
    }
    property Connections _resetOnSwitch: Connections {
        target: ObserverClient
        function onCurrentRunChanged() { queue.reset() }
        function onCurrentPerspectiveChanged() { queue.reset() }
    }

    // --- queue API (PlaybackControls remote) ---
    function play() { playing = true }
    function pause() { playing = false }      // live: UI only; backend keeps generating
    function setSpeed(x) { instant = false; speed = x; _tick.interval = 200 }
    function setInstant() { instant = true; _tick.interval = 16 }
    function resumeAfterTransition() { _gated = false; _tick.interval = 200 }   // TheaterView onStopped
    function seekNextPhase() {
        while (_cursor < _ordered.length && _phaseOf(_ordered[_cursor]) === layoutPhase) {
            _currentRaw = _ordered[_cursor]
            consumedSeq = _seq(_ordered[_cursor])
            _cursor += 1
        }
        _tick.interval = 16
    }
    function seekQueueEnd() {
        while (_cursor < _ordered.length) {
            _currentRaw = _ordered[_cursor]
            consumedSeq = _seq(_ordered[_cursor])
            _cursor += 1
        }
        waiting = (ObserverClient.currentStatus === "running")
    }
}
