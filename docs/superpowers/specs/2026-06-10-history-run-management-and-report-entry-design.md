# History Run Management & Report Entry — Design Spec

> Status: **DESIGN — user-directed constraints locked** · Date: 2026-06-10 · Author: brainstorming session (liaoszong + Claude)
> Scope is bounded to THREE surfaces: (1) the observer server's history-run **delete protocol**, (2) Qt `HistoryView`'s **delete interaction**, (3) `TheaterView`'s **settlement fast-forward entry**. Nothing else.

---

## 1. Motivation

Two user-reported gaps in the 历史对局 (history) page:

1. **No way to delete runs.** 50 accumulated run dirs, no delete affordance anywhere; the only cleanup path is manual filesystem surgery.
2. **「查看战报」and「打开」feel identical.** Both load the run into the theater, which **replays the full game from round 1 with pacing** — so the report button's promise (jump straight to the settlement report) is never kept. Root cause: the settlement overlay gates on `eventQueue.atEnd` (`TheaterView.qml:249`), and the report entry path never fast-forwards the queue, even though the queue already has the machinery (`EventPresentationQueue.seekQueueEnd()`, `:277`, built for live catch-up). **No new game is ever started — this is a replay-pacing presentation issue, not an engine/launcher issue.**

## 2. Scope fence

**In scope:**
- `DELETE /api/runs/{run_id}` on the observer server.
- `HistoryView` per-row delete + multi-select batch delete + confirm dialogs.
- `TheaterView`/`ObserverApiClient` report-entry auto-fast-forward.

**Out of scope (explicit non-goals):**
- No batch-delete endpoint (client loops single DELETEs — local loopback, YAGNI).
- No recycle bin / soft delete / undo.
- No replay transport controls (pause/seek UI) beyond what exists.
- No engine, runtime, scoring, or artifact-schema change of any kind.
- `HomeView`'s recent-run entries keep their current open behavior (untouched).

## 3. Part A — server delete protocol

`DELETE /api/runs/{run_id}` in `observer_server.py` (`do_DELETE`, `:865`, alongside the credentials delete):

| Guard | Behavior |
|---|---|
| Loopback only | non-loopback → 403 `forbidden` (same as credentials endpoint) |
| Cross-origin | `_reject_cross_origin()` (CSRF defense, same as credentials) |
| run_id legality | must match the existing run-id regex (`observer_protocol._RUN_ID_RE`); illegal → 400. Resolved path MUST stay inside `runs_dir` (no traversal). |
| Existence | run dir absent → 404 `not_found` |
| **Active-run gate** | run status (from the run's persisted `status.json`) is `running` or `queued` → **409 `run_active`**, nothing deleted. A live game writing to disk can never be deleted. |
| Delete | `shutil.rmtree(run_dir)` → 200 `{"deleted": run_id}` |
| rmtree failure | (e.g. Windows file lock) → 500 `internal_error` with detail; NEVER report success on a partial delete. A partially-deleted dir is acceptable residue (it will list as malformed/unknown and can be re-deleted); silent success is not. |

## 4. Part B — HistoryView delete interaction

`ObserverApiClient`: `Q_INVOKABLE void deleteRun(const QString &runId)` → network DELETE → signal `deleteRunFinished(runId, ok, errorCode)`; on success the client refreshes the runs list.

`HistoryView.qml`:
- **Per-row delete:** trash icon button at row end. Disabled (greyed) when row status is `running`/`queued`. Click → confirm dialog 「确定删除对局 {run_id}?删除后不可恢复。」 → `deleteRun`.
- **Batch mode:** a「选择」toggle in the list header enters selection mode (per-row checkboxes + select-all; `running`/`queued` rows not selectable). A「删除所选(N)」button appears while N > 0. Click → confirm dialog 「确定删除 N 局?删除后不可恢复。」 → sequential `deleteRun` per id; failures do not abort the rest; completion toast reports 「已删除 N-k 局,k 局失败:{reason}」.
- All new strings go through `I18n.t` (Chinese default + English fallback); visuals use the existing `Theme` tokens.
- If the deleted run is the client's `currentRunId`, clear it (the theater must not point at a deleted dir).

## 5. Part C — report entry fast-forward (user-locked constraints)

**Semantics statement (normative):**「查看战报」**is a replay fast-forward** — it loads the SAME data through the SAME path as「打开」, then immediately drains the presentation queue and opens the settlement overlay in `report` mode. It is **not** a new game, **not** a bypass that loads settlement from artifacts directly, and **not** a different data source.

The five locked rules:

1. **Completed-only.** Auto-`seekQueueEnd()` fires only for a history run whose status is `completed`. For `running`/`queued` the report button stays hidden (already `visible: status === "completed"`, `HistoryView.qml:225` — keep it); if a non-completed run somehow enters with `settlementEntry=1`, the theater falls back to normal live/replay semantics — never fast-forward to a fake "end" of an unfinished game.
2. **Trigger timing.** Fast-forward fires only when ALL hold: run detail loaded ∧ events loaded ∧ `eventQueue` actually populated (`_ordered.length > 0`) ∧ `settlementEntryMode === 1`. NOT in `Component.onCompleted` (events arrive async from `openRun`; a too-early call is a silent no-op).
3. **One-shot guard.** A `didAutoSeekSettlement` latch **keyed by runId** prevents re-trigger on model refresh, language switch, or component rebuild. Reset only when the active run changes.
4. **Race protection.** The async events callback must verify the loaded run is still the active run (`activeRunId === loadedRunId`) before touching the queue — clicking run A's report then run B's open must never `seekQueueEnd()` B's queue with A's late-arriving trigger.
5. **「打开」untouched.** Open keeps full replay: it never sets `settlementEntry=1` and never calls `seekQueueEnd()`. Resulting UX: 打开 = watch the full replay; 查看战报 = same data, instant jump to the report overlay.

## 6. Testing & acceptance

**Server (stdlib unittest, follows existing server-test patterns incl. the localhost-HTTP skip discipline):**
- delete success / 404 / illegal run_id 400 / traversal attempt rejected / `running` status 409 / non-loopback 403.

**Client:**
- Qt build exit 0 + existing static contract tests stay green.
- QML logic that is pure (e.g. selection-count, guard latch) covered where the existing test harness allows; interaction verified by screenshot (F: 盘 Qt 6.10 mingw flow).

**Acceptance:**
1. Deleting a completed run removes its dir from disk and from the list; deleting a running run is impossible from the UI and refused by the server.
2. 「查看战报」on a completed run shows the settlement overlay in `report` mode without watching the replay; 「打开」still plays the full replay.
3. Rapidly alternating report/open across two runs never fast-forwards the wrong queue (rule 4).
4. Full suite green; no engine/runtime/artifact bytes change (this is server-routing + client-only).

**Validation report (root policy, AGENTS.md「Validation」):** every change PR reports `git diff --stat`, `git diff --name-only`, allowlist check against this spec, forbidden-scope check (no unintended `src/**` beyond `observer_server.py`/`observer_protocol.py`, no `docs/ROADMAP.md`/`docs/TASKS.md`/`docs/adr/**`/historical plans/gold-game/`.github/**`), and the relevant tests.
