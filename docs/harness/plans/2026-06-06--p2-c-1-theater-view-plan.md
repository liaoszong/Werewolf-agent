# P2-C-1 Theater View + Bottom Evidence Console — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Do NOT start until the spec is approved** — it is (2026-06-06 user review, 4 edits merged).

**Goal:** Replace the data-dashboard cockpit with a **theater-style default spectator view** (`TheaterView`) that breathes by `phase` (night ring-center / day speech-theater / voting ring+tally), driven by a QML-side **Event Presentation Queue**; demote the honesty-chain into a bottom **3-state Evidence Console** with a reversible **Seat Lens**; and back-fill action text via a **visibility-safe projection enrichment** (the only backend change).

**Architecture:** One additive backend change (`build_projection_envelope` joins `game-log.json` summaries onto already-visibility-filtered projection events — no leak, no engine touch). `ObserverApiClient` gains one read-only `projectionEvents` Q_PROPERTY (same latest-wins guard, no new endpoint). Six new QML files: `TheaterView` (compose + breathing transitions + queue yield-gate), `SeatRing`, `SpeechTheater` (typewriter + 3-layer trace), `EvidenceConsole` (3-state + re-homed honesty chain), `PlaybackControls`, `EventPresentationQueue` (non-visual controller). `navigateCockpit()` retargets to `TheaterView`; `LiveCockpitView` retires from nav (delete only after re-home + green). The static contract is the test-first gate for the C++/QML surface; pure-Python visibility tests gate the backend; Qt build + 3-state `grabToImage` verify the UI.

**Tech Stack:** Python stdlib (extends P1-D `observer_visibility`), Qt 6.10 Quick/Quick Controls, C++17, QML, CMake. No new third-party deps, no live providers, no client local file I/O, no engine changes.

**Spec:** `docs/superpowers/specs/2026-06-06-p2-c-1-theater-view-design.md` (approved 2026-06-06, 4 edits merged).

**Branch:** `p2-c-1-theater-view` (base `main`).

---

## Context Basis (verified — file:line)

- **Enrichment crux (already traced):** `emergent_engine.py:261-269` `_emit()` appends the rich event (`data.summary`) to in-memory `self._events` (→ `game-log.json`) but writes only `payload={event_id,type}` to the runtime spine. ⇒ SSE + `/projection` are thin. `observer_visibility.py:519-533` `project_events()` copies visible events without enrichment; `build_projection_envelope():697-736` returns `events: event_projection["events"]` (thin). `game-log.json` is written once at completion (`run_emergent_deepseek_game.py:117`); it is an `ALLOWED_ARTIFACTS` member (`observer_protocol.py:34`) but its artifact route (`observer_server.py:404-417`) is **not** perspective-gated → cannot feed Seat Lens directly.
- **Visibility boundary:** `observer_visibility.py:114-127` source rules — "Do not return prompt text, provider secrets, paths, secret-like fields." `event_visible_in_projection()` gates each event before it enters `events[]`. Perspectives `observer_protocol.py:42-52` = `god`/`public`/`role:p1..p6`/`team:werewolf`.
- **Projection envelope keys:** `contract_version, run_id, perspective, view_kind, players, events, hidden_event_count, snapshots, hidden_snapshot_count, proof` (`observer_visibility.py:725-736`). Existing tests: `tests/test_observer_visibility.py:540+` (`TestBuildProjectionEnvelope`, calls with `events=[...]`).
- **C++ client:** `ObserverApiClient` Q_PROPERTYs incl. `currentRunId/currentStatus/currentPerspective/eventItems/playerItems/projectionProof/hiddenEventCount/hiddenSnapshotCount/visibilityContractVersion`; `refreshProjection()` → `GET /api/runs/{id}/projection?perspective={p}` with a **latest-wins** guard (`++m_projectionRequestSerial`; callback returns if serial/runId/perspective changed). It currently parses `players/proof/hidden_*` but **ignores `events[]`**. SSE via `ObserverSseParser.feed()` (`event: runtime_event`/`run_status`) → each frame → `QVariantMap` + `_eventType` → appended to `eventItems`. `currentPerspective` setter re-triggers stream + projection.
- **Shell/nav:** `AppShell.qml:159` StackView (`appShellStack`); `:180` `cockpitComponent { LiveCockpitView { objectName:"liveCockpitView" } }`; `:198` `navigateCockpit()` replaces with `cockpitComponent`. `LiveCockpitView.qml` `Component.onCompleted` → `connectStream()` + `refreshProjection()`.
- **Design system:** `Theme.*` tokens — `color.bgBase/bg/surface/surfaceInset/border/text/textSecondary/textMuted`, factions `color.werewolf #EF4444 / seer #FBBF24 / witch #A855F7 / villager #60A5FA`, helpers `roleAccent/roleTint/roleBorder/withAlpha`, `space.{xs..huge}`, `radius.{sm..pill}`, `font.{family,display,mono}`, `size.{display,h1,h2,body,small,caption,micro}`, `weight.*`, `motion.{fast120,base180,slow260}`, `layout.{pageMargin40,contentMax1040,actionBarHeight72}`. `I18n.t(zh,en)` — **English 2nd arg**, default zh. Both `pragma Singleton`.
- **Static contract** (`tests/test_qt_observer_static_contract.py`): `REQUIRED_QML_VIEWS` (:28), `REQUIRED_OBJECT_NAMES` (:46; `LiveCockpitView.qml` → `[liveCockpitView, runStatusBadge, playerPanelGrid, eventTimeline, perspectiveSwitcher, auditLinksPanel, providerFailureSummary]`), CMake-registration test, forbidden scans (`events.jsonl`/`snapshots/`/`QFile`/`QDir`/`file://`/`werewolf_eval` + secret markers), `QtObserverCockpitContractTests` (perspective values on `PerspectiveSwitcher.qml`, audit chips on `AuditLinksPanel.qml`), `QtObserverProjectionClientTests` (asserts client exposes `playerItems/projectionProof/...`).

**Build/verify (Qt toolchain on F:, runnable here — see memory `qt-observer-build-verify`):**
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer   # exit 0 = QML AOT-valid
ctest --test-dir .tmp/qt-observer-build
```
Pure-Python visibility tests run here. **P2-C-1 adds no server-route tests** — projection enrichment is fully covered by `test_observer_visibility`; pre-existing server-route tests remain env-blocked and are out of this slice.

---

## Allowlist

```text
src/werewolf_eval/observer_visibility.py
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/TheaterView.qml
clients/qt_observer/qml/EventPresentationQueue.qml
clients/qt_observer/qml/components/SeatRing.qml
clients/qt_observer/qml/components/SpeechTheater.qml
clients/qt_observer/qml/components/PlaybackControls.qml
clients/qt_observer/qml/components/EvidenceConsole.qml
clients/qt_observer/qml/AppShell.qml
clients/qt_observer/qml/LiveCockpitView.qml        (retire from nav; delete only after re-home + green)
clients/qt_observer/CMakeLists.txt
clients/qt_observer/README.md
tests/test_observer_visibility.py
tests/test_qt_observer_static_contract.py
docs/superpowers/specs/2026-06-06-p2-c-1-theater-view-design.md
docs/harness/plans/2026-06-06--p2-c-1-theater-view-plan.md
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

## Forbidden Scope

No engine changes (`emergent_engine.py`/`game_engine.py`/runtime/scoring) — enrichment is observer-layer only. No new server **write** endpoint and **no new read endpoint** (reuse `/projection`). No making live action text instantaneous (engine change — deferred). No `reason_summary`/prompt/provider-secret into any projection. No client local file I/O (`QFile`/`QDir`/`file://`). No live providers/secrets, no new deps, no Web/Electron. No route-product docs (root `README.md`, `ROADMAP.md`, `TASKS.md`, `PROJECT_MAP.md`). No heavy shader/glass fog (P2-C polish). No history-run/scrub features (P3-B).

---

## Task 1: Backend projection enrichment (visibility-safe summary join)

**Files:** `src/werewolf_eval/observer_visibility.py`, `tests/test_observer_visibility.py`
**Spec:** §7, D6. **The keystone gate — pure Python, runs here.**

- [ ] **Step 1: Write the failing enrichment + no-leak tests**

Append to `tests/test_observer_visibility.py` a class that builds a run_dir with `events.jsonl`-shaped runtime events + a `game-log.json` + role/god snapshots, then asserts post-filter enrichment. Model the fixture on the existing `TestBuildProjectionEnvelope` setup (snapshots + `events=[...]`). Runtime events carry `payload={"event_id": <gid>, "type": <etype>}`; game-log events carry `event_id=<gid>`, `data.summary`, `target`.

```python
class TestProjectionSummaryEnrichment(unittest.TestCase):
    """P2-C-1 §7: god/role projections back-fill summary+target from game-log.json,
    AFTER the visibility filter (so hidden summaries never leak)."""

    def _run_dir(self, td):
        run_dir = Path(td)
        _write_snapshots(run_dir)  # reuse helper that writes role_projection + god snapshots (seer=p3)
        # game-log.json: a public speech + a seer-only check (night)
        (run_dir / "game-log.json").write_text(json.dumps({"events": [
            {"event_id": "g_e01", "type": "player_speech", "actor": "p3", "target": "none",
             "visibility": "public", "data": {"summary": "p3: I think p1 is suspicious."}},
            {"event_id": "g_e02", "type": "seer_check", "actor": "p3", "target": "p1",
             "visibility": "seer", "data": {"summary": "Seer p3 checks p1, result: werewolf."}},
        ]}, ensure_ascii=False), encoding="utf-8")
        return run_dir

    def _runtime_events(self):
        return [
            {"event_id": "rt1", "seq": 1, "kind": "game_event_emitted", "round": 1, "phase": "day",
             "actor": "p3", "visibility": "public", "payload": {"event_id": "g_e01", "type": "player_speech"}},
            {"event_id": "rt2", "seq": 2, "kind": "game_event_emitted", "round": 1, "phase": "night",
             "actor": "p3", "visibility": "seer", "payload": {"event_id": "g_e02", "type": "seer_check"}},
        ]

    def test_god_gets_all_summaries(self):
        with tempfile.TemporaryDirectory() as td:
            env = build_projection_envelope(run_dir=self._run_dir(td), run_id="r1",
                                            perspective="god", events=self._runtime_events())
            by = {e["payload"]["event_id"]: e for e in env["events"]}
            self.assertEqual(by["g_e01"]["data"]["summary"], "p3: I think p1 is suspicious.")
            self.assertEqual(by["g_e02"]["data"]["summary"], "Seer p3 checks p1, result: werewolf.")
            self.assertEqual(by["g_e02"]["target"], "p1")

    def test_role_visible_enriched_but_hidden_summary_never_leaks(self):
        with tempfile.TemporaryDirectory() as td:
            # p1 (werewolf, not seer): MUST get the enriched summary for events it CAN see,
            # and MUST NOT receive the seer_check event (or its summary) at all. (P2-E)
            env = build_projection_envelope(run_dir=self._run_dir(td), run_id="r1",
                                            perspective="role:p1", events=self._runtime_events())
            by = {e["payload"]["event_id"]: e for e in env["events"]}
            self.assertIn("g_e01", by)              # public speech visible to p1
            self.assertEqual(by["g_e01"]["data"]["summary"],
                             "p3: I think p1 is suspicious.")   # role-visible IS enriched (not god-only)
            self.assertNotIn("g_e02", by)           # seer-only event filtered out entirely
            blob = json.dumps(env, ensure_ascii=False)
            self.assertNotIn("result: werewolf", blob)   # hidden summary did not leak

    def test_missing_game_log_is_thin_not_error(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td); _write_snapshots(run_dir)   # no game-log.json
            env = build_projection_envelope(run_dir=run_dir, run_id="r1",
                                            perspective="god", events=self._runtime_events())
            self.assertEqual(len(env["events"]), 2)
            self.assertNotIn("data", env["events"][0])       # thin (no data.summary), no crash

    def test_no_reason_summary_or_secret_in_envelope(self):
        with tempfile.TemporaryDirectory() as td:
            env = build_projection_envelope(run_dir=self._run_dir(td), run_id="r1",
                                            perspective="god", events=self._runtime_events())
            blob = json.dumps(env, ensure_ascii=False)
            for forbidden in ["reason_summary", "prompt", "api_key", "Bearer", "sk-"]:
                self.assertNotIn(forbidden, blob)
```

> If `_write_snapshots`/role-snapshot helpers don't already exist in the test module, factor the fixture from the existing `TestBuildProjectionEnvelope` setUp (it already writes the snapshots that make `seat_index` resolve p3=seer). Keep the seer at p3 to match the snapshot fixtures.

- [ ] **Step 2: Run → fail**

```bash
PYTHONPATH=src python -m unittest tests.test_observer_visibility -v
```
Expected: `test_god_gets_all_summaries` AND `test_role_visible_enriched_but_hidden_summary_never_leaks` both fail (no `data.summary` on god *or* role-visible events yet) — proving enrichment must apply **per-perspective** (god + role-visible), not god-only.

- [ ] **Step 3: Implement the post-filter join in `observer_visibility.py`**

Add a private loader (never raises) and enrich inside `build_projection_envelope` **after** `project_events` (i.e. only over already-visible events):

```python
def _load_game_log_summaries(run_dir: Path) -> dict[str, dict[str, str]]:
    """Return {game_log_event_id: {"summary", "target"}} from game-log.json,
    or {} when absent/malformed.  Never raises.  Summaries are public/role-visible
    game narration (NOT prompt/provider secrets); the visibility filter in
    project_events() decides which events reach the client BEFORE this join,
    so attaching summaries here cannot leak hidden facts."""
    path = run_dir / "game-log.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for ev in data.get("events", []):
        if not isinstance(ev, dict):
            continue
        eid = str(ev.get("event_id", ""))
        if not eid:
            continue
        d = ev.get("data", {})
        summary = str(d.get("summary", "")) if isinstance(d, dict) else ""
        target = ev.get("target", "")
        out[eid] = {"summary": summary, "target": "" if target is None else str(target)}
    return out
```

In `build_projection_envelope`, replace the `events=event_projection["events"]` wiring with an enriched copy:

```python
    event_projection = project_events(events, perspective, seat_index)

    # P2-C-1 §7: back-fill summary/target from game-log.json onto ALREADY-VISIBLE
    # events only (post-filter → no leak). Additive keys; thin when game-log absent.
    summaries = _load_game_log_summaries(run_dir)
    enriched_events: list[dict[str, object]] = []
    for ev in event_projection["events"]:
        payload = ev.get("payload")
        gid = str(payload.get("event_id", "")) if isinstance(payload, dict) else ""
        match = summaries.get(gid)
        if match is not None:
            ev = dict(ev)
            # Canonical enrichment shape (spec §7): data.summary nested + target top-level.
            d = dict(ev.get("data") or {})
            d["summary"] = match["summary"]
            ev["data"] = d
            if match.get("target"):
                ev["target"] = match["target"]
        enriched_events.append(ev)
```
…and return `"events": enriched_events` (instead of `event_projection["events"]`). Leave `hidden_event_count`/`snapshots`/`proof` unchanged.

- [ ] **Step 4: Run → pass + full module**

```bash
PYTHONPATH=src python -m unittest tests.test_observer_visibility -v
```
Expected: new class `OK`; all pre-existing `test_observer_visibility` tests still `OK` (additive change).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/observer_visibility.py tests/test_observer_visibility.py
git commit -m "feat(p2-c-1): visibility-safe projection summary enrichment (post-filter game-log join)"
```

---

## Task 2: C++ `projectionEvents` property

**Files:** `clients/qt_observer/src/ObserverApiClient.h`, `.cpp`, `tests/test_qt_observer_static_contract.py`
**Spec:** §5.7. No new endpoint — reads the enriched `events[]` already in the `/projection` response.

- [ ] **Step 1: Extend the projection-client contract test (test-first)**

In `QtObserverProjectionClientTests` add:
```python
    def test_client_exposes_projection_events(self) -> None:
        h = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("projectionEvents", h)
        # parsed from the same /projection response, under the existing latest-wins guard
        self.assertIn('value(QStringLiteral("events"))', cpp)

    def test_stale_guard_in_both_setters_before_requests(self) -> None:
        # Edit 2/7 + P2-F: clear+notify in BOTH setters, BEFORE the new stream/projection request.
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        for setter in ["ObserverApiClient::setCurrentPerspective", "ObserverApiClient::setCurrentRunId"]:
            start = cpp.find(setter)
            self.assertNotEqual(start, -1, f"{setter} not found")
            body = cpp[start:start + 1200]            # setter body window
            self.assertIn("m_projectionEvents.clear()", body, f"{setter} must clear projectionEvents")
            self.assertIn("projectionEventsChanged", body, f"{setter} must emit projectionEventsChanged")
            clr = body.index("m_projectionEvents.clear()")
            for req in ["startStreamRequest", "refreshProjection"]:
                if req in body:
                    self.assertLess(clr, body.index(req), f"{setter}: clear must precede {req}")
```
Run → fail.

- [ ] **Step 2: Declarations (`ObserverApiClient.h`)**

Beside the existing projection properties: `Q_PROPERTY(QVariantList projectionEvents READ projectionEvents NOTIFY projectionEventsChanged)`; accessor `QVariantList projectionEvents() const;`; signal `void projectionEventsChanged();`; member `QVariantList m_projectionEvents;`.

- [ ] **Step 3: Parse in `refreshProjection()` (`.cpp`)**

Inside the finished lambda, **after** the latest-wins guard passes and the object is parsed (next to where `players`/`proof` are read), add:
```cpp
    QVariantList projEvents;
    for (const QJsonValue &v : obj.value(QStringLiteral("events")).toArray())
        projEvents.append(v.toObject().toVariantMap());
    m_projectionEvents = projEvents;
    emit projectionEventsChanged();
```
Add the accessor `QVariantList ObserverApiClient::projectionEvents() const { return m_projectionEvents; }`. No new request, no new include (QJsonArray already used).

- [ ] **Step 3b: Stale-data guard — clear on run/perspective change (Edit 2/7)**

In `setCurrentPerspective(...)` and `setCurrentRunId(...)` (and any run-change path), **before** kicking the new stream/`refreshProjection()`, clear the projection events synchronously so no stale god data survives a Seat Lens switch:
```cpp
    if (!m_projectionEvents.isEmpty()) {
        m_projectionEvents.clear();
        emit projectionEventsChanged();
    }
```
This pairs with the queue `reset()` (Task 3): the UI prefers an empty/placeholder state over stale god projection during a perspective/run change.

- [ ] **Step 4: Build + contract + commit**

```bash
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
```
Expected: build exit 0; contract `OK`.
```bash
git add clients/qt_observer/src/ObserverApiClient.h clients/qt_observer/src/ObserverApiClient.cpp tests/test_qt_observer_static_contract.py
git commit -m "feat(p2-c-1): expose enriched projectionEvents to QML (no new endpoint)"
```

---

## Task 3: EventPresentationQueue.qml (non-visual controller)

**Files:** `clients/qt_observer/qml/EventPresentationQueue.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §6 (incl. **presentation-only invariant**: de-dup OK; **no reorder, no synthetic business events**; phase markers = UI-only), D4/D5.

- [ ] **Step 1: Register + contract (test-first)**

Add `qml/EventPresentationQueue.qml` to CMake `QML_FILES` and to `REQUIRED_QML_VIEWS`; add `"qml/EventPresentationQueue.qml": ["eventQueue"]` to `REQUIRED_OBJECT_NAMES`. Add an invariant assertion:
```python
    def test_event_queue_is_presentation_only(self) -> None:
        c = (QT / "qml/EventPresentationQueue.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "eventQueue"', c)
        self.assertIn("resumeAfterTransition", c)   # yield-gate API (D5)
        self.assertIn("function reset", c)          # Edit 2: run/perspective/source-gen reset
        self.assertIn("_present", c)                # Edit 1: PresentationEvent normalization
        self.assertNotIn(".sort(", c)               # Edit 6: append-order consume, never reorder
        self.assertIn("readonly property var current", c)   # P1-A: current is a computed binding...
        self.assertNotIn("current = _present", c)           # ...never assigned imperatively (reactive back-fill)
        # must not POST/emit business events back to the server
        for forbidden in ["XMLHttpRequest", '"/api/runs"', "ObserverClient.post"]:
            self.assertNotIn(forbidden, c)
```
Run → fail.

- [ ] **Step 2: Create the controller**

A non-visual `QtObject` exposing consume state + queue API. Encodes the locked invariants: **consume in `ObserverClient.eventItems` append order** (de-dup by `event_id`, **no sort/reorder**), **emit a normalized `PresentationEvent` as `current`** (components never read raw `.payload`), **phase markers are local UI signals only**, a **hard transition gate** (`_gated`) cleared only by `resumeAfterTransition()`, and a **`reset()`** on run/perspective/source-generation change.

```qml
pragma ComponentBehavior: Bound
import QtQuick
import qt_observer

QtObject {
    id: queue
    objectName: "eventQueue"

    // --- inputs (bound by TheaterView) ---
    property var source: []          // ObserverClient.eventItems (thin SSE/replay notifications)
    property var enriched: []         // ObserverClient.projectionEvents (per-perspective, summary-bearing)

    // --- exposed presentation state (read by SeatRing / SpeechTheater) ---
    property int consumedSeq: 0       // highest sequence handed to the stage
    property var _currentRaw: null    // raw runtime event currently on stage (drives `current`)
    // P1-A: `current` is a COMPUTED PresentationEvent — it recomputes when `enriched`
    // (projectionEvents) arrives late, so a still-displayed event back-fills summary/target
    // WITHOUT re-pumping. Components bind to it; never assign `current` imperatively.
    readonly property var current: _currentRaw ? _present(_currentRaw) : ({})
    property string layoutPhase: "day"  // "night" | "day" | "voting" (drives breathing layout)
    property bool waiting: false       // queue drained but run still live → "AI thinking"
    property bool playing: true
    property real speed: 1.0           // 1 / 2 / 4 ; Instant uses a near-zero interval
    property bool instant: false

    signal phaseBoundary(string phase, int round)   // UI marker ONLY — never a runtime event

    // --- enrichment lookup: game-log event_id → {summary (from data.summary), target} ---
    readonly property var _enrichedById: {
        var m = ({})
        for (var i = 0; i < enriched.length; i++) {
            var e = enriched[i]
            var gid = (e && e.payload) ? e.payload.event_id : (e ? e.event_id : "")
            if (!gid) continue
            var summ = (e && e.data && e.data.summary) ? e.data.summary : ""   // CANONICAL: data.summary
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

    // --- internal cursor + gate ---
    property int _cursor: 0            // index into the authoritative, de-duped, ordered list
    property bool _gated: false        // true while a phase-transition animation is running (D5)

    // Authoritative ordered view of source: de-dup by event_id, PRESERVE append order.
    // Edit 6: NO sort/reorder — eventItems already arrives in engine sequence order;
    // a sequence regression is handled by reset() (generation change), never by reordering.
    readonly property var _ordered: {
        var out = [], seen = ({})
        for (var i = 0; i < source.length; i++) {
            var ev = source[i]
            var id = ev && ev.payload ? ev.payload.event_id : (ev ? ev.event_id : "")
            if (!id || seen[id]) continue
            seen[id] = true
            out.push(ev)
        }
        return out
    }
    function _seq(ev) { return ev && ev.sequence !== undefined ? ev.sequence
                                : (ev && ev.seq !== undefined ? ev.seq : 0) }
    function _phaseOf(ev) {
        // voting is a day sub-state inferred from vote events; otherwise event.phase
        var t = ev ? (ev.payload ? ev.payload.type : ev.type) : ""
        if (t === "player_vote" || t === "player_eliminated") return "voting"
        return ev && ev.phase === "night" ? "night" : "day"
    }
    function _durationMs(ev) {
        var t = ev ? (ev.payload ? ev.payload.type : ev.type) : ""
        var base = ({ role_assignment:1000, werewolf_kill:1800, seer_check:1800,
            witch_save:1800, witch_kill:1800, witch_pass:1500, player_died:2000,
            player_speech:6000, player_vote:1200, day_announcement:1000,
            player_eliminated:2000, role_revealed:2000, game_over:3000 })[t] || 1200
        return instant ? 16 : Math.max(16, base / Math.max(1, speed))
    }

    property Timer _tick: Timer {
        interval: 200; repeat: true; running: queue.playing
        onTriggered: queue._pump()
    }

    function _pump() {
        if (_gated || !playing) return
        if (_cursor >= _ordered.length) { waiting = (ObserverClient.currentStatus === "running"); return }
        waiting = false
        var raw = _ordered[_cursor]
        // defensive: a sequence regression means a new generation slipped in → reset, never reorder
        if (_seq(raw) < consumedSeq) { reset(); return }
        // phase transition? raise the gate and emit a UI-only boundary marker, then STOP
        // popping until TheaterView's transition onStopped calls resumeAfterTransition().
        var ph = _phaseOf(raw)
        if (ph !== layoutPhase) {
            layoutPhase = ph
            _gated = true
            phaseBoundary(ph, raw.round || 0)
            return        // D5: yield to the layout animation
        }
        _currentRaw = raw                  // `current` recomputes via binding (reactive back-fill, P1-A)
        consumedSeq = _seq(raw)
        _cursor += 1
        _tick.interval = _durationMs(raw)   // hold this event on stage for its budget
    }

    // --- Reset protocol (Edit 2): run / perspective / source-generation change ---
    function reset() {
        _cursor = 0; _currentRaw = null; _gated = false; waiting = false
        consumedSeq = 0; layoutPhase = "day"; _tick.interval = 200
    }
    property int _lastSourceLen: 0
    onSourceChanged: {
        if (source.length < _lastSourceLen) reset()   // truncation = new generation
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
    function resumeAfterTransition() { _gated = false; _tick.interval = 200 }  // called by TheaterView onStopped
    function seekNextPhase() {
        // fast-forward consumption to the next phase boundary among ALREADY-RECEIVED events
        while (_cursor < _ordered.length && _phaseOf(_ordered[_cursor]) === layoutPhase) {
            _currentRaw = _ordered[_cursor]; consumedSeq = _seq(_ordered[_cursor]); _cursor += 1
        }
        _tick.interval = 16
    }
    function seekQueueEnd() {
        while (_cursor < _ordered.length) {
            _currentRaw = _ordered[_cursor]; consumedSeq = _seq(_ordered[_cursor]); _cursor += 1
        }
        waiting = (ObserverClient.currentStatus === "running")
    }
}
```

> **Invariant audit (must hold):** `_ordered` de-dups by `event_id` and **preserves append order (no sort)**; it never inserts/derives business events. `current` is a **normalized PresentationEvent** (`_present`): `type`=raw `payload.type`, `target`/`summary`=matched projection `target`/`data.summary` — components read `current.type/target/summary`, never raw `.payload`; it is a **computed binding** (`_present(_currentRaw)`) so a late `projectionEvents` back-fills the on-screen event without re-pumping (P1-A). `phaseBoundary` is a QML signal (UI marker), never written back. `_gated` blocks ALL consumption until `resumeAfterTransition()`. `reset()` fires on run/perspective/source-generation change (paired with the C++ `projectionEvents` clear) so no stale current/projection survives a Seat Lens switch. `seek*` consume only already-received events. Timing constants are tunable in visual verification — adjust `base`/interval, not the invariants.

- [ ] **Step 3: Build + contract + commit**

```bash
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
```
```bash
git add clients/qt_observer/qml/EventPresentationQueue.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(p2-c-1): EventPresentationQueue (presentation-only, de-dup/no-reorder, yield-gate)"
```

---

## Task 4: SeatRing.qml (breathing player ring + connectors)

**Files:** `clients/qt_observer/qml/components/SeatRing.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §5.2, §10. Gate = build + contract + visual (Task 9).

- [ ] **Step 1: Register + contract** — add file to CMake + `REQUIRED_QML_VIEWS`; `"qml/components/SeatRing.qml": ["seatRing"]`. Also assert `self.assertNotIn(".payload", (QT/"qml/components/SeatRing.qml").read_text(encoding="utf-8"))` (Edit 1: reads PresentationEvent, not raw runtime). Run → fail.

- [ ] **Step 2: Create `SeatRing.qml`** — skeleton (fill visuals against the design system):
  - Root `Item { objectName: "seatRing"; property var players: []; property var current: ({}); property string layoutPhase: "day"; property string perspective: "god" }`.
  - 6 seat avatars positioned on a circle (`x = cx + r*cos(θ_i)`, `θ_i = -90° + i*60°`). Each seat: faction ring via `Theme.roleAccent(role)`, alive/dead (dead → desaturate + strike), `selected/active` glow when `current.actor === player_id` (reuse `GlowDot` motif).
  - **Connector layer** (`Canvas` or `Shape`): when `current.type ∈ {werewolf_kill, seer_check, player_vote}`, draw a line `actor → target` (`werewolf_kill` red `Theme.color.werewolf`; `seer_check` `Theme.color.seer`; vote neutral). Expanding halo on `player_died`. **No Dialog popups.**
  - **Breathing:** `scale`/`anchors` respond to `layoutPhase` (night = larger/centered; day = smaller/left; voting = emphasized) — actual animation lives in TheaterView states (Task 8); SeatRing only exposes size-friendly bindings.
  - **Lightweight fog (§12, D7):** when `perspective !== "god"` and a seat's role is not visible, show `Unknown`/`████` and hide its connectors (opacity↓). god → no fog.
  - Players come from `ObserverClient.playerItems`; active/connector state from the bound `current` (**PresentationEvent**: `current.type/actor/target` — never raw `.payload`).

- [ ] **Step 3: Build + contract + commit** (`feat(p2-c-1): SeatRing breathing player ring + connector layer`).

---

## Task 5: SpeechTheater.qml (typewriter + 3-layer trace)

**Files:** `clients/qt_observer/qml/components/SpeechTheater.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §5.3, §8. Gate = build + contract + visual.

- [ ] **Step 1: Register + contract** — `"qml/components/SpeechTheater.qml": ["speechTheater"]`. Also assert `SpeechTheater.qml` has no `.payload` (Edit 1: reads PresentationEvent `current.summary/type`). Run → fail.

- [ ] **Step 2: Create `SpeechTheater.qml`** — skeleton:
  - Root `Item { objectName: "speechTheater"; property var current: ({}) }` — `current` is the **PresentationEvent** from `eventQueue.current` (carries `.summary`/`.type`/`.target`). **No `summary` prop, no `summaryFor`, no raw `.payload`.**
  - **Typewriter:** narrative actions in `Theme.font.display` (elegant sans); the reasoning/log line in `Theme.font.mono` (Consolas), semi-transparent. A `Timer`/`NumberAnimation` reveals `current.summary` char-by-char (length-based duration, cap 6–8s). **Live-latency rule (§0/§7):** when `current.summary === ""` (live in-progress, `game-log.json` not yet present), show a placeholder/fade — never block, never error.
  - **Back-fill reactivity (P1-A):** `current` is a computed binding, so when projection arrives late the same-`event_id` `current.summary` flips from `""` to text. **Key the typewriter on `current.event_id`** — reveal the now-available text without restarting from scratch; reset the animation only when `event_id` changes (not when summary back-fills).
  - **3-layer trace (§8):** L1 = `current.type` chip; L2 = `current.summary`; L3 = on click/hover, a disclosure showing `reason_summary` **only if present** (it is not, in P2-C-1) + an "open in console" affordance that opens the Evidence Console Expanded at the audit links. **Never render prompt/provider text on the stage.**

- [ ] **Step 3: Build + contract + commit** (`feat(p2-c-1): SpeechTheater typewriter + inline 3-layer AI trace`).

---

## Task 6: EvidenceConsole.qml (3-state console + re-homed honesty chain)

**Files:** `clients/qt_observer/qml/components/EvidenceConsole.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §9, §5.6, D2/D3/D7. **Re-homes** `PerspectiveSwitcher`(Seat Lens)/`EventTimeline`/`AuditLinksPanel`/`ProjectionProofPanel`/`ViewBoundaryBadge` + failure summary (reused, not rewritten).

- [ ] **Step 1: Register + contract (strong re-home, Edit 5)** — `"qml/components/EvidenceConsole.qml": ["evidenceConsole", "eventTimeline", "perspectiveSwitcher", "auditLinksPanel", "providerFailureSummary"]`. Add a dedicated assertion that **EvidenceConsole.qml itself** instantiates the honesty chain (so a retained `LiveCockpitView.qml` can NOT satisfy the requirement):
```python
    def test_evidence_console_rehomes_honesty_chain(self) -> None:
        c = (QT / "qml/components/EvidenceConsole.qml").read_text(encoding="utf-8")
        for comp in ["ViewBoundaryBadge", "ProjectionProofPanel", "PerspectiveSwitcher",
                     "EventTimeline", "AuditLinksPanel"]:
            self.assertIn(comp, c)
        self.assertIn('objectName: "providerFailureSummary"', c)
```
(The `QtObserverCockpitContractTests` assertions keyed on the component files `PerspectiveSwitcher.qml`/`AuditLinksPanel.qml` stay untouched + green.) Run → fail.

- [ ] **Step 2: Create `EvidenceConsole.qml`** — skeleton:
  - Root `Item { objectName: "evidenceConsole"; property int mode: 0 /*0 Closed,1 Peek,2 Expanded*/; property string perspective: "god" }` docked bottom; height animates by `mode` (Closed = thin strip; Peek ≈ 30% screen; Expanded ≈ 65%). Three buttons (`AppButton`) toggle `mode` — **no free drag/snap/fullscreen**.
  - **Closed:** strip = `Evidence` · PASS/warning count · current Seat Lens label.
  - **Peek:** `ViewBoundaryBadge` (perspective + contract version + hidden counts) + projection summary + provider status + recent `EventTimeline` (objectName `eventTimeline`, reused).
  - **Expanded:** Seat Lens (`PerspectiveSwitcher`, objectName `perspectiveSwitcher`, label → "Seat Lens / 视角") + `ProjectionProofPanel` + visible-observation list + redacted `[ENCRYPTED]`/`████` hidden facts + raw event table + `AuditLinksPanel` (objectName `auditLinksPanel`, prompt-manifest/provider-trace links) + failure summary (objectName `providerFailureSummary`).
  - **Seat Lens reversibility (§9, locked):** changing the switcher sets `ObserverClient.currentPerspective = "role:pN"` (existing setter re-streams + re-projects). **The stage re-fogs automatically via `SeatRing.perspective: ObserverClient.currentPerspective` — do NOT write `ring.perspective` from a handler (P1-C: breaks the binding and desyncs Back-to-God).** **Exiting Seat Lens restores `god`** (a "Back to God" affordance sets `currentPerspective = "god"`) — the console must not strand the theater in a seat view.

- [ ] **Step 3: Build + contract + commit** (`feat(p2-c-1): EvidenceConsole 3-state forensic console (honesty chain re-homed + Seat Lens)`).

---

## Task 7: PlaybackControls.qml (thin queue remote)

**Files:** `clients/qt_observer/qml/components/PlaybackControls.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §5.4, §7-playback, D8.

- [ ] **Step 1: Register + contract** — `"qml/components/PlaybackControls.qml": ["playbackControls"]`. Also assert `PlaybackControls.qml` has no `.payload` (Edit 1: reads `eventQueue.current` PresentationEvent + queue state). Run → fail.

- [ ] **Step 2: Create `PlaybackControls.qml`** — `Row { objectName: "playbackControls"; property var queue }`: Play/Pause → `queue.play()/pause()`; speed segmented 1x/2x/4x/Instant → `queue.setSpeed(x)`/`queue.setInstant()`; "Next phase" → `queue.seekNextPhase()`; "Queue end" → `queue.seekQueueEnd()`. **No scrub bar.** When `queue.waiting`, show "AI thinking / waiting". Live pause tooltip: "UI paused — match keeps running."

- [ ] **Step 3: Build + contract + commit** (`feat(p2-c-1): thin PlaybackControls (no scrub)`).

---

## Task 8: TheaterView.qml + AppShell retarget + LiveCockpitView retire

**Files:** `clients/qt_observer/qml/TheaterView.qml` (new), `AppShell.qml`, `LiveCockpitView.qml`, `CMakeLists.txt`, `README.md`, `tests/test_qt_observer_static_contract.py`
**Spec:** §5.1, §5.9, §3.3, D1/D5/D9. **Composition + breathing transitions + the queue yield-gate wiring.**

- [ ] **Step 1: Contract updates (test-first)**
  - Add `"qml/TheaterView.qml"` to `REQUIRED_QML_VIEWS`; `"qml/TheaterView.qml": ["theaterView"]` to `REQUIRED_OBJECT_NAMES`.
  - **Retire-not-delete (D-edit-2):** keep the `LiveCockpitView.qml` file + its `REQUIRED_QML_VIEWS`/`REQUIRED_OBJECT_NAMES` entry while the file exists (its objectNames stay satisfied in the now-unreferenced file). Add an assertion that nav points at the theater:
    ```python
    def test_cockpit_nav_targets_theater_view(self) -> None:
        a = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        self.assertIn("TheaterView", a)            # cockpitComponent loads TheaterView
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("resumeAfterTransition", t)  # D5 yield-gate is wired
        self.assertIn('objectName: "eventQueue"', t)  # hosts the queue
        self.assertIn("state: eventQueue.layoutPhase", t)   # P2-D: layout binds layoutPhase (reset re-syncs)
        self.assertNotIn("ring.perspective =", t)           # P1-C: never assign the bound perspective from a handler
    ```
  - Run → fail.

- [ ] **Step 2: Create `TheaterView.qml`** — composition + breathing + gate:
  - Root `Item { id: theaterRoot; objectName: "theaterView"; state: eventQueue.layoutPhase }` (no `anchors.fill` — StackView sizes it; **`state` declaratively tracks `layoutPhase`, P2-D — so `reset()` re-syncs the layout, no residual night/voting**). `Component.onCompleted: if (ObserverClient.currentRunId !== "") { ObserverClient.connectStream(); ObserverClient.refreshProjection() }` (surround per existing `LiveCockpitView` pattern). Re-`refreshProjection()` on new SSE seq (throttled) so summaries back-fill live; latest-wins guard already prevents out-of-order writes.
  - Host the queue + components:
    ```qml
    // theaterRoot.state binds eventQueue.layoutPhase (P2-D) — no imperative onPhaseBoundary.
    EventPresentationQueue {
        id: eventQueue
        source: ObserverClient.eventItems
        enriched: ObserverClient.projectionEvents
    }
    SeatRing      { id: ring;    players: ObserverClient.playerItems; current: eventQueue.current
                    layoutPhase: eventQueue.layoutPhase
                    perspective: ObserverClient.currentPerspective }   // single source; never handler-assigned
    SpeechTheater { id: speech;  current: eventQueue.current }   // current = PresentationEvent (carries .summary)
    PlaybackControls { id: controls; queue: eventQueue }
    EvidenceConsole  { id: console; perspective: ObserverClient.currentPerspective }
    // Seat Lens sets ObserverClient.currentPerspective; ring/console follow via their bindings.
    // Do NOT write ring.perspective from a handler (P1-C: breaks the binding).
    ```
  - **Breathing states + yield-gate (D5):** define `states: [State{name:"night"}, State{name:"day"}, State{name:"voting"}]` repositioning `ring`/`speech` per §3.3. Give `transitions` a **single** terminal `onRunningChanged`/`onStopped` (wrap parallel anims in one `ParallelAnimation`, hook its `onStopped`) that calls `eventQueue.resumeAfterTransition()` — so the queue stays gated until the layout settles, then resumes. Budget ≤ 1.5s (`Theme.motion.slow`-scale).
    ```qml
    transitions: Transition {
        ParallelAnimation {
            id: phaseAnim
            // ... NumberAnimation/AnchorAnimation on ring/speech, duration ~ up to 1500 ...
            onStopped: eventQueue.resumeAfterTransition()
        }
    }
    ```
  - Dark theater backdrop (deepen `AppBackground`); faction accents via `Theme.roleAccent` (D10 — existing tokens; indigo/fluo-green deferred per §16).

- [ ] **Step 3: Retarget nav + retire LiveCockpitView**
  - `AppShell.qml`: change `cockpitComponent` to `TheaterView { objectName: "theaterView" }` (keep `navigateCockpit()` name + the StackView wiring). 
  - `LiveCockpitView.qml`: **leave the file in place, unreferenced** (retire-not-delete). It stays registered in CMake + contract while present. (A follow-up may delete it once the console fully subsumes it and all gates are green — out of this task's required path.)
  - `README.md`: update non-goals — default spectator surface is now the Theater View; still no Web client, no Python binding, no local artifact reads, no provider secrets. Keep the substrings the README contract asserts.

- [ ] **Step 4: Build + contract + commit**
```bash
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
```
```bash
git add clients/qt_observer/qml/TheaterView.qml clients/qt_observer/qml/AppShell.qml clients/qt_observer/CMakeLists.txt clients/qt_observer/README.md tests/test_qt_observer_static_contract.py
git commit -m "feat(p2-c-1): TheaterView compose + breathing layout + queue yield-gate; retarget navigateCockpit"
```

---

## Task 9: Build, lint, 3-state visual verification

**Files:** none (verification) — fixes land in the relevant task's files.

- [ ] **Step 1: Clean build + ctest + qmllint**
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
ctest --test-dir .tmp/qt-observer-build --output-on-failure
qmllint -I .tmp/qt-observer-build clients/qt_observer/qml/TheaterView.qml clients/qt_observer/qml/EventPresentationQueue.qml clients/qt_observer/qml/components/SeatRing.qml clients/qt_observer/qml/components/SpeechTheater.qml clients/qt_observer/qml/components/EvidenceConsole.qml clients/qt_observer/qml/components/PlaybackControls.qml
```
Expected: build exit 0; ctest 100%; qmllint no `Error:` lines (ignore `[unqualified]`/`[missing-property]`).

- [ ] **Step 2: 3-state visual capture (grabToImage → PNG → Read) — TEMPORARY, NEVER committed**

The harness edits files **outside the allowlist** (`AppShell.qml` timer) and seeds mock events; none may be staged. Use revertible edits + a hard gate.
1. Temporarily add a timer to `AppShell.qml` that `navigateCockpit()` then seeds, behind a `// TEMP VISUAL ONLY` marker, **two separate arrays matching the real data contract (Edit 1)**: (a) `source` = thin runtime-shaped notifications `{event_id, seq, round, phase, actor, visibility, payload:{event_id, type}}` for the full arc (role_assignment → werewolf_kill → seer_check → player_died → player_speech×N → player_vote×N → player_eliminated → role_revealed → game_over); (b) `projectionEvents` = the matching enriched events `{payload:{event_id,type}, data:{summary}, target}`. The queue normalizes these into PresentationEvents — **do NOT feed pre-merged rich events**. (localhost blocked → mock `ObserverClient`-shaped data only for the capture.)
2. Grab three frames — **night** (ring centered + red kill connector + spotlight), **day** (speech theater typewriter + ring shrunk), **voting** (ring emphasized + vote connectors + tally) — and the **Evidence Console** Peek + Expanded (Seat Lens, audit links). Save to `G:/Werewolf-agent/.tmp/p2c1_{night,day,voting,console}.png`.
2b. **Reactivity scenarios (P1-A / P2-D) — the harness must exercise these, not just static frames:** (i) feed `source` FIRST (thin, no summary → placeholder text, active-seat spotlight, **no directional connector**), THEN feed `projectionEvents` → capture `p2c1_backfill_before.png` / `p2c1_backfill_after.png` showing text + `actor→target` connector appear *without re-pumping*; (ii) drive to **night/voting**, call `eventQueue.reset()`, then feed a day event → capture `p2c1_reset.png` showing the layout snapped back via `state: eventQueue.layoutPhase` (no residual).
3. **Read** each PNG; confirm dark theater palette, faction accents, fog on a `role:pN` capture, no Dialog popups, console docked bottom.
4. **Revert ALL harness edits + prove clean before any commit:**
```bash
git checkout -- clients/qt_observer/qml/AppShell.qml
git diff --quiet -- clients/qt_observer/qml/AppShell.qml || { echo "AppShell still modified"; exit 1; }
```
(Step 3 of Task 8 makes a *real* `AppShell.qml` edit — commit that first, then the visual harness edits/reverts happen on top and must net to zero additional AppShell change.)

- [ ] **Step 3: Full Python suite + compileall**
```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
```
Expected: `test_observer_visibility` green; `compileall` 0 failures. **P2-C-1 adds no server-route tests.** Only acceptable failures = documented pre-existing ones + the unchanged, pre-existing env-blocked server-route tests (`RemoteDisconnected`). **Any new failure = a P2-C-1 regression to fix, not "known".**

---

## Task 10: Validation + review packet

**Files:** `.logs/review/latest/review-packet.md`, `.oh-my-harness/tree.md`

- [ ] **Step 1: Hygiene**
```bash
git diff --check main...HEAD
git diff --name-only main...HEAD     # must be within allowlist
git diff main...HEAD -- clients | python -c "import sys,re; d=sys.stdin.read(); add=[l for l in d.splitlines() if l.startswith('+') and not l.startswith('+++')]; bad=[l for l in add if re.search(r'(QFile|QDir|file://|events\.jsonl|snapshots/|sk-[A-Za-z0-9]{16}|Authorization:|Bearer )', l) and all(k not in l.lower() for k in ('forbidden','assertnotin','marker'))]; print('\n'.join(bad)); assert not bad, bad"
```
- [ ] **Step 2: Refresh tree** — `node .codex/hooks/tree.mjs --force` (includes the 6 new QML).
- [ ] **Step 3: Write review packet** (≤300 lines): Metadata (branch `p2-c-1-theater-view`, base `main`), Changed Files, Diff Stat/Check, Allowlist, Forbidden/secret scan, Test Summary (visibility-enrichment OK incl. no-leak; static contract OK; Qt build exit 0; ctest; qmllint; 4 visual PNGs referenced; **no new server-route tests** — enrichment via pure observer_visibility), Key Hunks (enrichment join + `data.summary` shape, projectionEvents parse + stale-guard, queue PresentationEvent/reset/no-sort, yield-gate, Seat Lens reversibility), Evidence Map (A1–A12), Acceptance Checklist, Review Trigger Result.
- [ ] **Step 4: Commit** — `git add .logs/review/latest/review-packet.md .oh-my-harness/tree.md && git commit -m "docs(p2-c-1): review packet + tree refresh"`.

---

## Acceptance Criteria (mirror spec §14)

- **A1.** `navigateCockpit()` loads `TheaterView` (`theaterView`); `LiveCockpitView` retired from nav; honesty chain visible in `EvidenceConsole`. *(test_cockpit_nav_targets_theater_view; build)*
- **A2.** Breathing layout switches night/day/voting ≤1.5s; **queue does not pop during a transition** (gated until `resumeAfterTransition()` from the single terminal `onStopped`). *(queue `_gated` logic; visual; invariant test)*
- **A3.** Queue consumes per §6 budgets, in **append order** (de-duped, no sort); Pause/1x-4x/Instant/next-phase/queue-end work; live never fast-forwards未来 (waiting state when drained). *(test_event_queue_is_presentation_only; visual)*
- **A4.** god `SeatRing` shows all real roles + night connectors; Seat Lens → `role:pN` re-projects stage+console with lightweight fog (`Unknown`/`████`/`[ENCRYPTED]`); **exiting Seat Lens restores god**. *(visual god + role:pN; Seat Lens reversibility)*
- **A5.** `SpeechTheater` typewriters `current.summary` (full for just-finished runs; live in-progress → placeholder/fade, **not a failure**); 3-layer trace L1/L2 inline + L3 → console audit links; no prompt/secret on stage. *(visual; §0/§7 latency rule)*
- **A6.** Projection enrichment (canonical shape `event.data.summary` + `event.target`): god `events[]` carry summaries; `role:pN` never receives hidden-event summaries; missing `game-log.json` → thin (no `data`), no error; envelope still free of `reason_summary`/prompt/secret. **No new server-route tests.** *(TestProjectionSummaryEnrichment — pure, runs here)*
- **A7.** C++ `projectionEvents` exposed, parsed under the existing latest-wins guard, no new endpoint; `setCurrentPerspective`/`setCurrentRunId` clear it + notify (stale guard). *(test_client_exposes_projection_events; build)*
- **A8.** Static contract updated + green (6 new files/objectNames, re-homed cockpit objectNames, forbidden/secret/file-I/O scans absent, component-file assertions untouched); build exit 0; ctest green; qmllint clean.
- **A9.** No engine change; no new endpoint; no new deps; no client file I/O; SSE/`/events` thin semantics unchanged. *(hygiene)*
- **A10.** EventQueue is presentation-only: de-dup OK, **append-order consume (no `.sort`), no reorder, no synthetic business events**, phase markers UI-only, no write-back; emits a normalized **PresentationEvent** (`_present`) and `SeatRing/SpeechTheater/PlaybackControls` read it (no raw `.payload`). *(test_event_queue_is_presentation_only + per-component .payload asserts; code audit)*
- **A11.** Palette uses existing `Theme.roleAccent` tokens (no shared-token change); indigo/fluo-green deferred. *(visual; diff has no `Theme.qml` change)*
- **A12.** Run/perspective change: C++ clears `projectionEvents` + queue `reset()` (cursor/current/gate/waiting); Seat Lens switch shows no stale god projection / stale current (empty/placeholder preferred); stale-guard clear+notify precedes the new request in **both** setters. *(test_stale_guard_in_both_setters_before_requests; reset test; visual god↔role:pN)*
- **A13.** Reactive back-fill (P1-A): `current` is a computed binding (`_present(_currentRaw)`); a late `projectionEvents` back-fills the on-screen event's summary/target without re-pump; live directional connectors need target → just-finished only, live = active-seat spotlight (P1-B). *(queue binding asserts; visual backfill_before/after)*
- **A14.** Reset re-syncs layout via `theaterRoot.state: eventQueue.layoutPhase` (P2-D, visual night→reset→day); `SeatRing.perspective` single-bound to `currentPerspective`, never handler-assigned (P1-C). *(test_cockpit_nav_targets_theater_view state/no-handler asserts; visual)*

---

## Review Packet Requirements

`.logs/review/latest/review-packet.md` ≤300 lines: Metadata, Changed Files, Diff Stat, Diff Check, Allowlist, Forbidden/secret scan (note safe test markers), Test Summary (visibility no-leak result + Qt build exit code + 4 visual PNG refs + no-new-server-route note), Key Hunks, Evidence Map (A1–A12), Acceptance Checklist, Review Trigger Result.

---

## PR Description Draft

Title: `feat: P2-C-1 Theater View + bottom Evidence Console`

```markdown
## Summary
- New TheaterView replaces LiveCockpitView as the default spectator surface: breathing night/day/voting layout driven by a QML EventPresentationQueue; honesty chain demoted into a 3-state bottom Evidence Console with a reversible Seat Lens.
- Visibility-safe projection enrichment (only backend change): build_projection_envelope joins game-log.json summaries onto already-filtered events — god sees all, role:pN never leaks; thin when game-log absent.
- ObserverApiClient gains read-only projectionEvents (same latest-wins guard, no new endpoint).

## Scope / boundaries
- No engine change; live in-progress action text lags until run completion (game-log written at completion) — thin-event theater (phase/active-seat/board/waiting) is guaranteed live; **directional connectors (`actor→target`) and full summary need projection enrichment → guaranteed for just-finished runs; live shows active-seat spotlight + placeholder until projection arrives**. Instant-live summary deferred.
- EventQueue is presentation-only (append-order de-dup, no sort/reorder, no synthetic business events); emits a normalized PresentationEvent (type from payload, summary/target from projection data.summary); resets on run/perspective change. Existing faction palette reused (no Theme token change).

## Validation
- PYTHONPATH=src python -m unittest tests.test_observer_visibility -v   # enrichment + no-leak
- Qt build (F: toolchain) exit 0; tests.test_qt_observer_static_contract OK; ctest; qmllint
- Visual: .tmp/p2c1_{night,day,voting,console}.png
- No new server-route tests; enrichment covered by pure observer_visibility tests (incl. no-leak).
```

---

## Execution Handoff

Order: (1) backend enrichment + no-leak tests [runs here — the keystone], (2) C++ projectionEvents + stale-guard, (3) EventPresentationQueue [PresentationEvent + reset + no-sort], (4) SeatRing, (5) SpeechTheater, (6) EvidenceConsole [strong re-home], (7) PlaybackControls, (8) TheaterView compose + breathing + yield-gate + nav retarget + LiveCockpitView retire, (9) build/lint/3-state visual, (10) packet. Each task commits. **Hard rules:** canonical enrichment shape = `event.data.summary` + `event.target` (spec/plan/tests/C++/QML agree); the queue emits a normalized **PresentationEvent** and components never read raw `.payload`; **consume append order, never `.sort`/reorder**; `reset()` + C++ `projectionEvents.clear()` on run/perspective change (no stale god data in Seat Lens); never join summaries before the visibility filter; never touch the engine; never change shared `Theme` tokens; **P2-C-1 adds no server-route tests**; Seat Lens must restore god on exit; `AppShell.qml` visual-harness edits must net to zero before any commit.
```
