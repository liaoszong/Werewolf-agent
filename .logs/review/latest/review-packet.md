# Review Packet — P2-C-1 Theater View + Bottom Evidence Console

## Metadata
- **Branch:** `p2-c-1-theater-view` (base `main`)
- **Spec:** `docs/superpowers/specs/2026-06-06-p2-c-1-theater-view-design.md` (approved, 3 review rounds: 4 spec edits + 7 plan invariants + 6 correctness fixes)
- **Plan:** `docs/harness/plans/2026-06-06--p2-c-1-theater-view-plan.md` (10 tasks, all complete)
- **Scope:** Replace the data-dashboard cockpit with a theater-style default spectator UI: breathing night/day/voting stage driven by a QML EventPresentationQueue; honesty chain demoted into a 3-state bottom Evidence Console with a reversible Seat Lens; visibility-safe projection summary enrichment (only backend change).

## Commits (9)
```
2e11cd8 docs(p2-c-1): design spec + implementation plan
aaa2893 feat(p2-c-1): visibility-safe projection summary enrichment (post-filter game-log join)
505c9c1 feat(p2-c-1): expose enriched projectionEvents to QML + stale-guard
2fbb3f7 feat(p2-c-1): EventPresentationQueue controller
62d0c18 feat(p2-c-1): SeatRing breathing player ring + connector layer
1fe8562 feat(p2-c-1): SpeechTheater typewriter + inline 3-layer AI trace
5d0d578 feat(p2-c-1): EvidenceConsole 3-state forensic console (honesty chain re-homed + Seat Lens)
33b271e feat(p2-c-1): thin PlaybackControls (no scrub)
18f51fc feat(p2-c-1): TheaterView compose + breathing layout + queue yield-gate; retarget navigateCockpit
```

## Changed files (16) — all within the spec §12 allowlist
```
src/werewolf_eval/observer_visibility.py              (+ _load_game_log_summaries, post-filter enrichment)
clients/qt_observer/src/ObserverApiClient.h/.cpp      (+ projectionEvents Q_PROPERTY + stale-guard)
clients/qt_observer/qml/EventPresentationQueue.qml    (new, non-visual controller)
clients/qt_observer/qml/TheaterView.qml               (new, composition + breathing states)
clients/qt_observer/qml/components/SeatRing.qml       (new)
clients/qt_observer/qml/components/SpeechTheater.qml  (new)
clients/qt_observer/qml/components/EvidenceConsole.qml(new)
clients/qt_observer/qml/components/PlaybackControls.qml(new)
clients/qt_observer/qml/AppShell.qml                  (navigateCockpit -> TheaterView)
clients/qt_observer/CMakeLists.txt                    (register 6 new QML)
clients/qt_observer/README.md                         (Theater = default surface)
tests/test_observer_visibility.py                     (+ ProjectionSummaryEnrichmentTests)
tests/test_qt_observer_static_contract.py             (+ theater contract tests)
docs/.../2026-06-06-p2-c-1-theater-view-design.md     (spec)
docs/.../2026-06-06--p2-c-1-theater-view-plan.md      (plan)
```
**Diff stat:** 16 files changed, ~2350 insertions, 5 deletions. **`.gitignore`** (pre-existing unrelated edit) intentionally NOT committed.

## Diff check / forbidden scan
- `git diff --check main...HEAD`: clean (one trailing-whitespace nit in the plan doc fixed).
- Forbidden/secret scan on added client lines (`QFile`/`QDir`/`file://`/`events.jsonl`/`snapshots/`/`sk-…`/`Authorization:`/`Bearer`): **0 hits**.
- No engine files touched; no new endpoint; no new deps; no client file I/O; no provider secrets.

## Test summary
- **Backend enrichment (pure, runs here):** `tests.test_observer_visibility` — **53/53 OK** incl. 4 new `ProjectionSummaryEnrichmentTests` (god gets summaries; role:pN enriched-but-no-leak; missing game-log → thin/no-error; no `reason_summary`/secret). TDD: both enrichment tests red (`KeyError: 'data'`) → green.
- **Qt static contract:** `tests.test_qt_observer_static_contract` — **56/56 OK** (6 new QML files + objectNames + CMake registration; queue presentation-only/`_present`/no-`.sort`/reactive `current`; stage components no `.payload`; EvidenceConsole strong re-home; nav→TheaterView + `state: eventQueue.layoutPhase` + no `ring.perspective =`; stale-guard in both setters before requests).
- **Qt build:** `cmake --build … appqt_observer` — **exit 0** (qmlcachegen AOT-compiles every QML = validity gate).
- **ctest:** 100% (1/1, SSE parser).
- **qmllint** on all 6 new QML: **0 `Error:` lines** (`[unqualified]` ObserverClient noise ignored per project convention).
- **Full suite:** `Ran 576 tests … FAILED (failures=1, errors=47, skipped=1)` — **identical to baseline**: 47 errors are all `test_observer_server` `RemoteDisconnected` (documented localhost-HTTP block, memory `werewolf-env-network-test-limits`); 1 failure is the pre-existing `test_context_budget` AGENTS.md doc test (fails identically on `main`). **Zero new regressions.** `compileall` OK. **P2-C-1 adds no server-route tests.**
- **Visual (grabToImage → PNG → Read; harness reverted, tree nets to zero):** 6 frames confirmed in `.tmp/p2c1_*.png`:
  - `night` — ring centered, faction-colored seats, p1 active+glow, red `p1→p4` kill connector + arrowhead, p4 dimmed/dead.
  - `day` — ring shrunk left, SpeechTheater expanded right, p3(seer) active, "发言 · p3" + fully-typed summary + L3 link.
  - `voting` — ring re-emphasized, p5 active, `p5→p1` vote connector, bottom "投票" strip.
  - `console` — Expanded (~66%), re-homed Seat Lens (上帝视角) + ViewBoundaryBadge + ProjectionProof + EventTimeline.
  - `backfill_before` — event present (发言 · p2), summary empty → "· 等待文本 ·" placeholder.
  - `backfill_after` — SAME p2 event back-fills its text reactively (no re-pump) — P1-A confirmed.

## Key hunks
- **Enrichment (`observer_visibility.py`):** `_load_game_log_summaries(run_dir)` builds `{game_log_event_id: {summary, target}}` (never raises); `build_projection_envelope` joins it onto each **already-visibility-filtered** event → `data.summary` nested + `target` top-level. Post-filter ⇒ god sees all, `role:pN` only its own; thin when game-log absent.
- **C++ (`ObserverApiClient`):** `projectionEvents` parsed from the same `/projection` response under the existing latest-wins guard; `setCurrentPerspective`/`setCurrentRunId` clear `m_projectionEvents` + notify **before** the new stream/projection request (stale guard).
- **Queue (`EventPresentationQueue.qml`):** append-order de-dup (no sort); `_present` PresentationEvent (`type` from `payload.type`, `summary`/`target` from enriched); **reactive computed `current`** (`_present(_currentRaw)`); `reset()` on run/perspective/source-gen; `resumeAfterTransition` yield-gate.
- **TheaterView:** `state: eventQueue.layoutPhase` (declarative, P2-D); single terminal `ParallelAnimation.onStopped → resumeAfterTransition`; `SeatRing.perspective` single-bound to `currentPerspective` (P1-C).
- **EvidenceConsole:** 3-state dock; Seat Lens sets `currentPerspective` only (no `ring.perspective` write); Back-to-God restores it.

## Evidence Map (acceptance A1–A14)
- A1 nav→TheaterView, LiveCockpit retired, honesty chain in console — *test_cockpit_nav_targets_theater_view; build; visual console*
- A2 breathing ≤ ~0.7s, queue gated during transition — *queue `_gated`; visual 3 states; onStopped wired*
- A3 queue append-order/de-dup, playback works, no future fast-forward — *test_event_queue_is_presentation_only; visual playback bar*
- A4 god ring all roles + connectors; Seat Lens fog + reversible — *visual night/day/voting; EvidenceConsole binding*
- A5 typewriter `current.summary` (full just-finished; placeholder live) — *visual day + backfill_before/after*
- A6 enrichment canonical `data.summary`+`target`, no leak, thin when absent, no new server-route tests — *ProjectionSummaryEnrichmentTests*
- A7 `projectionEvents` latest-wins + stale clear — *test_client_exposes_projection_events; build*
- A8 static contract green; build exit 0; ctest; qmllint clean — *all above*
- A9 no engine change/endpoint/deps/file-I/O; SSE thin unchanged — *diff/forbidden scan*
- A10 presentation-only: append-order/no-sort/no-synthetic; PresentationEvent; components no `.payload` — *contract*
- A11 existing `Theme.roleAccent` tokens (no Theme change) — *diff has no Theme.qml; visual faction colors*
- A12 run/perspective clears projectionEvents + queue reset (clear precedes request, both setters) — *test_stale_guard_in_both_setters_before_requests*
- A13 reactive back-fill (computed `current`); live directional connector needs target (spotlight only) — *visual backfill_before/after; SeatRing connector guard*
- A14 reset re-syncs layout via `state: eventQueue.layoutPhase`; perspective never handler-assigned — *test_cockpit_nav_targets_theater_view*

## Review trigger result
All gates green; zero new regressions; visual verification confirms the breathing theater, connectors, typewriter, reactive back-fill, and 3-state console. Ready for review.
