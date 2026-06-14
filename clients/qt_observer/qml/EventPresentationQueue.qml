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
    readonly property bool atEnd: _cursor >= _ordered.length   // drained (all received events consumed)
    readonly property int queuedCount: _ordered.length   // total received (de-duped); 0 = nothing arrived yet

    // Major phase timeline up to the cursor: ordered unique (round, night|day) pairs. Drives
    // the top progress axis; the LAST entry is the current major phase. (voting is part of day.)
    readonly property var phaseTimeline: {
        var out = []
        var seen = ({})
        var n = Math.min(_cursor, _ordered.length)
        for (var i = 0; i < n; i++) {
            var raw = _ordered[i]
            var r = (raw && raw.round !== undefined && raw.round !== null) ? raw.round : 0
            var ph = (raw && raw.phase === "night") ? "night" : "day"
            var key = r + ":" + ph
            if (seen[key])
                continue
            seen[key] = true
            out.push({ round: r, phase: ph })
        }
        return out
    }

    // Current micro-action (which role/step is acting now) derived from the on-stage event —
    // drives the sub-round highlight slider on the timeline.
    readonly property string currentAction: {
        var t = current ? current.type : ""
        if (t === "werewolf_kill") return "wolf"
        if (t === "seer_check") return "seer"
        if (t === "witch_save" || t === "witch_poison" || t === "witch_kill" || t === "witch_pass") return "witch"
        if (t === "player_speech") return "speech"
        if (t === "player_vote" || t === "player_eliminated") return "vote"
        return ""
    }

    // Players who have DIED up to the current playback position — a death only "lands" when
    // its event is consumed, so a replayed/seeked game shows seats die over time instead of
    // all-dead from frame 0. Scans consumed events (indices 0.._cursor-1) for death markers.
    readonly property var deadPlayers: {
        var dead = []
        var n = Math.min(_cursor, _ordered.length)
        for (var i = 0; i < n; i++) {
            var raw = _ordered[i]
            var t = (raw && raw.payload) ? raw.payload.type : (raw ? raw.type : "")
            if (t !== "player_died" && t !== "player_eliminated")
                continue
            var gid = (raw && raw.payload) ? raw.payload.event_id : (raw ? raw.event_id : "")
            var enr = (gid && _enrichedById[gid]) ? _enrichedById[gid] : null
            var tgt = (enr && enr.target && enr.target !== "none") ? enr.target
                    : ((raw && raw.target) ? raw.target : "")
            if (tgt && dead.indexOf(tgt) < 0)
                dead.push(tgt)
        }
        return dead
    }
    property bool playing: true
    property real speed: 1.0
    property bool instant: false

    // 当前 round = phaseTimeline 末项(已按游标截断)。
    readonly property int currentRound: phaseTimeline.length ? phaseTimeline[phaseTimeline.length - 1].round : 0

    // 当前 round 的票数聚合,仅统计「已消费到游标 0.._cursor」的 player_vote(与 deadPlayers 同法
    // 扫描 _ordered;target 优先取 enrichment,缺则 raw.target)。绝不扫完整 source/enriched —
    // 否则回放中会提前显示未来票。返回 [{target, count}] 按票数降序。
    readonly property var voteTally: {
        var counts = ({})
        var n = Math.min(_cursor, _ordered.length)
        var cr = currentRound
        for (var i = 0; i < n; i++) {
            var raw = _ordered[i]
            var t = (raw && raw.payload) ? raw.payload.type : (raw ? raw.type : "")
            if (t !== "player_vote")
                continue
            var rr = (raw && raw.round !== undefined && raw.round !== null) ? raw.round : 0
            if (rr !== cr)
                continue
            var gid = (raw && raw.payload) ? raw.payload.event_id : (raw ? raw.event_id : "")
            var enr = (gid && _enrichedById[gid]) ? _enrichedById[gid] : null
            var tgt = (enr && enr.target && enr.target !== "none") ? enr.target
                    : ((raw && raw.target) ? raw.target : "")
            if (!tgt)
                continue
            counts[tgt] = (counts[tgt] || 0) + 1
        }
        var out = []
        for (var k in counts)
            out.push({ target: k, count: counts[k] })
        return out   // 不排序:队列绝不 reorder(presentation-only 不变量);展示层自行排序
    }

    // Events the playback cursor has ALREADY revealed, in order (indices 0.._cursor-1),
    // each enriched with summary/target. This is the SINGLE source of truth the left event
    // log renders from, so the log reveals one entry exactly when its event lands on the
    // stage — same cursor, same pace, same pause/seek as the right-side state. NEVER scans
    // the full source/enriched (that would let the log race ahead of the stage).
    readonly property var presentedEvents: {
        var out = []
        var n = Math.min(_cursor, _ordered.length)
        for (var i = 0; i < n; i++) {
            var raw = _ordered[i]
            var gid = (raw && raw.payload) ? raw.payload.event_id : (raw ? raw.event_id : "")
            var enr = (gid && _enrichedById[gid]) ? _enrichedById[gid] : { summary: "", target: "none" }
            var ty = (raw && raw.payload) ? raw.payload.type : (raw ? raw.type : "")
            out.push({
                event_id: gid,
                round: (raw && raw.round !== undefined && raw.round !== null) ? raw.round : 0,
                phase: (raw && raw.phase) ? raw.phase : "",
                type: ty,
                actor: (raw && raw.actor) ? raw.actor : "",
                target: enr.target,
                summary: enr.summary,
                current: (i === n - 1)
            })
        }
        return out
    }

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
            witch_save: 1800, witch_poison: 1800, witch_kill: 1800, witch_pass: 1500, player_died: 2000,
            player_speech: 6000, player_vote: 1200, day_announcement: 1000,
            player_eliminated: 2000, role_revealed: 2000, game_over: 3000 })[t] || 1200
        return base   // base hold time; speed/instant applied via _heldMs accumulation in _pump
    }

    property int _cursor: 0
    property bool _gated: false
    property bool _ffToEnd: false   // seekQueueEnd in progress: keep crossing phases after each gated transition
    property real _heldMs: 0        // how long the current event has been on stage (speed-scaled)

    // Fixed-cadence tick; the per-event hold is accumulated into _heldMs so speed/instant
    // changes take effect IMMEDIATELY instead of waiting out the current event's old interval.
    property Timer _tick: Timer {
        interval: 90
        repeat: true
        running: queue.playing
        onTriggered: queue._pump()
    }

    // Safety watchdog: if a layout transition's onStopped is ever missed, never stay gated
    // forever — force a resume after the transition's worst-case duration.
    property Timer _gateWatchdog: Timer {
        interval: 1600
        repeat: false
        running: queue._gated
        onTriggered: queue.resumeAfterTransition()
    }

    function _pump() {
        if (_gated || !playing)
            return
        // Hold the current event for its (speed-scaled) duration before advancing.
        if (_currentRaw !== null) {
            _heldMs += _tick.interval * (instant ? 1000 : Math.max(0.25, speed))
            if (_heldMs < _durationMs(_currentRaw))
                return
        }
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
        _heldMs = 0
    }

    // --- Reset protocol (run / perspective / source-generation change) ---
    function reset() {
        _cursor = 0
        _currentRaw = null
        _gated = false
        waiting = false
        consumedSeq = 0
        layoutPhase = "day"
        _ffToEnd = false
        _heldMs = 0
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
    function setSpeed(x) { instant = false; speed = x }
    function setInstant() { instant = true }
    function resumeAfterTransition() {            // TheaterView onStopped (gate released)
        _gated = false
        _heldMs = 0
        if (_ffToEnd) _ffToEnd = !_consumeCurrentPhaseFast(instant)  // ungated if still in instant mode
    }

    // Instantly consume the rest of the CURRENT layoutPhase; at a phase boundary update
    // layoutPhase and emit phaseBoundary. When ungated=false (gated mode): raise the gate and
    // STOP so the layout transition still runs (D5 invariant). When ungated=true (instant sweep):
    // skip the gate and keep consuming through all phase boundaries in one synchronous pass.
    // Respects _gated (no-op while a transition is in flight). Returns true ONLY when it reaches
    // the end of received events.
    function _consumeCurrentPhaseFast(ungated) {
        if (_gated)
            return false
        while (_cursor < _ordered.length) {
            var raw = _ordered[_cursor]
            if (_seq(raw) < consumedSeq) {            // sequence regression = new generation
                reset()
                return false
            }
            if (_phaseOf(raw) !== layoutPhase) {      // boundary -> update layout + emit marker
                layoutPhase = _phaseOf(raw)
                phaseBoundary(layoutPhase, raw.round || 0)
                if (!ungated) {
                    _gated = true                     // gated: raise gate and stop (D5)
                    return false
                }
                // ungated instant sweep: layoutPhase updated, marker emitted, keep consuming
            }
            _currentRaw = raw
            consumedSeq = _seq(raw)
            _cursor += 1
            _heldMs = 0
        }
        waiting = (ObserverClient.currentStatus === "running")
        return true
    }

    function seekNextPhase() {                    // skip the rest of this phase -> next phase (always gated)
        _ffToEnd = false
        _consumeCurrentPhaseFast(false)
    }
    function seekQueueEnd() {                      // catch up to latest event; ungated in instant mode
        _ffToEnd = !_consumeCurrentPhaseFast(instant)
    }
}
