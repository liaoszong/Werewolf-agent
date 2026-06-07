# Review Packet — P2-D Settlement / Battle-Report Screen

## Metadata
- **Branch:** `p2-d-settlement-screen` (base `main`, branch-point `5f41d04`)
- **Spec:** `docs/superpowers/specs/2026-06-06-p2-d-settlement-screen-design.md`
- **Plan:** `docs/harness/plans/2026-06-06--p2-d-settlement-screen-plan.md`
- **Scope:** server-computed eval-ready settlement bundle + Qt one-shot-morph battle-report screen (28/72 + center spine, single-cursor scroll-sync). Curtain layer from game-log (always); battle-report layer from `score_game`+`summarize_metrics`+`attribute_game` (graceful degrade). Settlement = entry shell for P3 evaluation/review; bundle contract v1 is the P3 anti-rework asset.

## Commits (10 tasks, TDD, per-task)
```
450f8ec feat(p2-d): build_settlement_bundle (eval-ready bundle, curtain always, graceful degrade)        [T1]
c850efe feat(p2-d): build_settlement_response (offline-tested route logic) + /settlement route + artifact [T2]
7b4b21f feat(p2-d): expose settlementBundle + fetchSettlement (latest-wins, no new endpoint shape)        [T3]
63e6076 feat(p2-d): SeatRing layoutMode (ring↔docked morph, presentational boardState input)             [T4]
4936052 feat(p2-d): SettlementSpine vertical timeline scrubber                                            [T5]
d8cc53b feat(p2-d): SettlementReport scrolling battle report + scroll-spy (anti-loop guarded)             [T6]
d23df64 feat(p2-d): WinnerBanner freeze-beat ceremony                                                     [T7]
1f90c30 feat(p2-d): SettlementView morph (freeze→dock→report) + single cursor; theater/history entries    [T8]
78f2952 fix(p2-d): hide theater ring guide in docked SeatRing (stray circle behind sandbox grid)          [T9 visual fix]
```
(Plus doc commits for spec/plan: `0fa9c0c`, `c4c8789`, `a267462`, `3b36084`.)

## Changed Files (17 code/test, within allowlist) — `+1329 / −9`
```
src/werewolf_eval/settlement_bundle.py                 | 255 +  (build_settlement_bundle + build_settlement_response)
src/werewolf_eval/observer_server.py                   |  11 +  (GET /settlement route, 2-line wrapper)
src/werewolf_eval/observer_protocol.py                 |   1 +  (settlement-bundle.json in ALLOWED_ARTIFACTS)
clients/qt_observer/src/ObserverApiClient.h            |  11 +  (settlementBundle Q_PROPERTY + fetchSettlement)
clients/qt_observer/src/ObserverApiClient.cpp          |  44 +  (fetch + latest-wins guard + stale clear)
clients/qt_observer/qml/SettlementView.qml             | 163 +  (NEW: morph 3-beat + single cursorIndex)
clients/qt_observer/qml/components/SettlementReport.qml | 220 + (NEW: scroll-spy + _programmaticScroll guard)
clients/qt_observer/qml/components/SettlementSpine.qml  |  98 + (NEW: vertical scrubber)
clients/qt_observer/qml/components/WinnerBanner.qml     |  89 + (NEW: freeze-beat ceremony)
clients/qt_observer/qml/components/SeatRing.qml         |  70 +  (MODIFY: layoutMode/morphProgress/boardState; presentational)
clients/qt_observer/qml/TheaterView.qml                |  30 +  (MODIFY: overlay activation, completed-only)
clients/qt_observer/qml/HistoryView.qml                |  23 +  (MODIFY: 查看战报 entry)
clients/qt_observer/CMakeLists.txt                     |   4 +  (register 4 new QML)
clients/qt_observer/README.md                          |   2 +  (non-goal note)
tests/test_settlement_bundle.py                        | 154 +  (NEW: 8 tests)
tests/test_settlement_response.py                      |  99 +  (NEW: 7 tests)
tests/test_qt_observer_static_contract.py              |  64 +  (new views/objectNames/invariant asserts)
```

## Diff Check / Allowlist / Forbidden scan
- `git diff --check main...HEAD` → **clean** (no whitespace/conflict markers).
- All changed files within the plan allowlist. **AppShell.qml untouched** (overlay-only, §14.1 — verified empty diff).
- Forbidden/secret scan on `clients` added lines (`QFile|QDir|file://|events.jsonl|snapshots/|werewolf_eval|api_key|Bearer|sk-…`) → **clean**. No client local file I/O; no secrets.

## Test Summary
- **Backend pure (runs here):** `tests.test_settlement_bundle` **8/8 OK**, `tests.test_settlement_response` **7/7 OK** (branches: not_completed / no_game_log / completed-full / absent→missing_decision_log / invalid→invalid_decision_log / cache write-then-read / failed-run).
- **Qt static contract:** `tests.test_qt_observer_static_contract` **62/62 OK**.
- **Qt build:** `cmake --build appqt_observer` **exit 0** (QML AOT-valid syntax gate); `qmllint` no `Error:` lines.
- **Visual (Task 9, standalone `.tmp/` harness, mock bundle, grabToImage→PNG→Read):** 6 scenarios judged PASS by the implementing agent — freeze / dock / report / **scroll-sync (sandbox+spine track `board_timeline[cursor_index]`, no feedback loop)** / history-direct (no freeze) / degraded (curtain + EmptyState). Harness fully reverted; tree clean. **NOTE:** PNGs were captured-and-deleted by the harness pass; the orchestrator independently re-verified build exit 0, 77 P2-D tests OK, the fix diff, and tree-clean — but did **not** personally view the PNGs (a reviewer may want a fresh capture).
- **Pre-existing (NOT P2-D regressions):** 47 `RemoteDisconnected` errors in `test_observer_server.py` (localhost HTTP env-blocked, memory `werewolf-env-network-test-limits`); 1 `test_context_budget` failure reproduced on clean `main`.

## Key Hunks
- **`settlement_bundle.py:_board_timeline`** — one node per (round,phase); `alive_player_ids` after deaths; last node == `result.survivors`. Only needs game-log → curtain never depends on scoring.
- **`build_settlement_bundle` degrade pre-check** — `decision_log_status != "present"` → explicit `missing_/invalid_decision_log` (NOT via silent `score_game(game,None)`); scoring chain raise → `scoring_failed`. `degraded_reason` always a bare code (secret-free).
- **dataclass access** — `metrics.result_metrics`/`score_summary` are dataclasses (`rm.margin`, `ss.player_outcome_scores`), not dicts; `mvp_player_id` = max outcome_score.
- **`build_settlement_response`** — filesystem-only lazy compute-or-cache; `{available:false,reason}` for not-completed/no-game-log (incl. failed). Route handler is a 2-line wrapper (offline-tested logic).
- **`ObserverApiClient::fetchSettlement`** — latest-wins serial guard mirroring `refreshProjection`; `setCurrentRunId` clears `m_settlementBundle` + notifies before new requests.
- **`SeatRing` presentational** — `layoutMode`/`morphProgress`/`boardState`; ring↔docked seat-position lerp; docked liveness/highlight from parent `boardState`; references NO `settlementBundle`/`fetchSettlement`/`cursorIndex`; theater path zero-drift (ring guide + connector Canvas gated `visible: layoutMode !== "docked"`).
- **`SettlementView` single cursor** — the ONE writable `cursorIndex`; resolves `board_timeline[cursorIndex]→boardState`; Spine `nodeClicked`/Report `cursorRequested` write via `setCursor`; `setCursor` scrolls report with `_programmaticScroll` guard. Morph `freeze`/`docking`/`report`; history `entryMode=1` → direct `report`.
- **TheaterView activation** — gated on `currentStatus==="completed"` (never `failed`) + projection players loaded (game-log proxy) + `eventQueue.atEnd`; `_completedAtLoad` latch discriminates history-direct vs live without touching AppShell.

## Evidence Map (spec §12)
- A1 overlay completed-only, no StackView/AppShell nav — `test_settlement_view_owns_cursor_and_is_overlay`; AppShell empty diff.
- A2 SeatRing ring↔docked, theater zero-drift, docked boardState — `test_seatring_layoutmode_presentational`; visual dock/sync.
- A3 single cursor, scroll-spy+spine via signals, anti-loop — `test_report_has_scrollspy_and_guard`, `test_spine_reads_cursor_via_binding`; visual sync.
- A4 bundle v1 complete, cursor_index resolves, mvp=max — `test_full_bundle_shape`.
- A5 three degrade codes explicit, curtain intact, bare code — `test_degrade_missing/invalid/on_scoring_error`, `test_degraded_reason_is_code_not_raw_exception`; visual degraded.
- A6 lazy compute-or-cache, available envelope — `test_settlement_response` (7 branches).
- A7 history-direct report entry — visual history.
- A8 god full reveal, secret-free — `test_secret_free`.
- A9 settlementBundle + fetchSettlement + stale clear — `test_client_exposes_settlement`; build.
- A10 contract green + build exit 0 + visual — confirmed.
- A11 no engine/scoring/validator change; only +1 builder +1 route +1 artifact — diff scan.
- A12 P3-deepen contract: bundle keys frozen — spec §5.

## Acceptance Checklist
- [x] A1–A12 evidenced. [x] Build exit 0. [x] 77 P2-D tests OK. [x] Static contract 62 OK. [x] Hygiene/forbidden clean. [x] Tree refreshed.

## Review Trigger Result
Self-review: PASS for merge consideration. **Open follow-ups (not blockers for this slice):**
1. PNGs not independently re-viewed by the orchestrator (harness deleted them) — a reviewer may want a fresh visual capture.
2. Branch based on `5f41d04`; `main` advanced to `7d2eedf` (witch_poison vocab fix PR #43) — **rebase before merge** so live witch-poison scoring flows into the bundle.
3. Cinematic morph polish (depth-of-field blur / spotlight glow / vote-line / poison micro-anim) deferred to P2-D polish.
