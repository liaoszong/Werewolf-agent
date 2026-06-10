# History Run Management & Report Entry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add run deletion (server `DELETE /api/runs/{run_id}` + HistoryView per-row & batch delete with confirm) and make「查看战报」jump straight to the settlement report via replay fast-forward — per `docs/superpowers/specs/2026-06-10-history-run-management-and-report-entry-design.md` (the spec's §5 five user-locked rules are NORMATIVE).

**Architecture:** Server side mirrors the credentials-delete pattern: a PURE result function (`_run_delete_result`) unit-tested without HTTP + a thin `do_DELETE` route with the loopback/CSRF/`validate_run_id` guard stack. Client side: `ObserverApiClient::deleteRun` (no auto-refresh — QML decides single-vs-batch refresh), a `m_pendingOpenRunId` guard closing the open-run async race (spec rule 4), QML ConfirmDialog + HistoryView delete UI, and a latched auto-`seekQueueEnd()` in TheaterView (rules 1–3). 「打开」path is untouched (rule 5).

**Tech Stack:** Python 3.12 stdlib unittest (server); Qt 6.10 C++/QML (client). Python suite: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`. Qt build: `cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug && cmake --build .tmp/qt-observer-build --config Debug` then `ctest --test-dir .tmp/qt-observer-build --output-on-failure`.

---

## Verified anchor table (main @ time of writing; re-grep if HEAD moved)

| Site | File:line |
|---|---|
| `_credentials_delete_result` (pure-fn pattern to mirror) | `observer_server.py:301-308` |
| `do_DELETE` (route to extend) | `observer_server.py:865-886` |
| `_get_status` (MEMORY-FIRST then `status.json` — use as-is for the 409 gate) | `observer_server.py:475-482` |
| `_run_dir` (calls `validate_run_id` → traversal guard) | `observer_server.py:502-504` |
| `state.run_status` / `state.run_errors` (in-memory, guarded by `state.lock`) | `observer_server.py:84`, `:296-300` |
| credentials delete tests (pattern to mirror) | `tests/test_observer_credentials_endpoint.py:84,190-194` |
| client `get()` helper / `refreshRuns()` / `m_runItems` | `ObserverApiClient.cpp:98,173,191` |
| `deleteResource` precedent | `CredentialStore.cpp:108` |
| `openRun` (detail cb sets `currentRunId`; events cb sets `m_eventItems`, NO runId guard today) | `ObserverApiClient.cpp:233-300` |
| HistoryView rows + 查看战报/打开 buttons | `HistoryView.qml:141-252` (report btn `:219-232`, open btn `:234-246`) |
| HistoryView panel header (selection toggle goes here) | `HistoryView.qml:90-126` |
| TheaterView settlement gate `eventQueue.atEnd` / `settlementEntryMode` | `TheaterView.qml:245-252` |
| `EventPresentationQueue.seekQueueEnd()` / `atEnd` / `_ordered` | `EventPresentationQueue.qml:277-279,31,126` |
| QML objectName static contract | `tests/test_qt_observer_static_contract.py:75,208-211` |

---

## File Structure

- **Modify** `src/werewolf_eval/observer_server.py` — `_run_delete_result` pure fn + `do_DELETE` route branch.
- **Create** `tests/test_observer_run_delete.py` — pure-logic tests (no HTTP, mirrors credentials tests).
- **Modify** `clients/qt_observer/src/ObserverApiClient.h/.cpp` — `deleteRun` + `deleteRunFinished` + `m_pendingOpenRunId` race guard.
- **Create** `clients/qt_observer/qml/components/ConfirmDialog.qml` — Theme-styled modal confirm.
- **Modify** `clients/qt_observer/qml/HistoryView.qml` — per-row delete, selection mode, batch controller, notice bar.
- **Modify** `clients/qt_observer/qml/TheaterView.qml` — latched auto-seek for report entry.
- **Modify** `clients/qt_observer/CMakeLists.txt` — register ConfirmDialog.qml (match how existing components are listed).
- **Modify** `tests/test_qt_observer_static_contract.py` — new objectNames.

---

## Task 1: Server pure logic — `_run_delete_result`

**Files:** Modify `src/werewolf_eval/observer_server.py` (next to `_credentials_delete_result`, `:301`); Create `tests/test_observer_run_delete.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_observer_run_delete.py
"""Pure-logic tests for DELETE /api/runs/{run_id} (no HTTP — mirrors
tests/test_observer_credentials_endpoint.py's pattern for the same reason:
localhost HTTP is blocked in the agent environment)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.observer_server import _run_delete_result


class RunDeleteResultTests(unittest.TestCase):
    def _mk_run(self, root: Path, run_id: str) -> Path:
        d = root / run_id
        (d / "snapshots").mkdir(parents=True)
        (d / "game-log.json").write_text("{}", encoding="utf-8")
        return d

    def test_completed_run_is_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            status, payload = _run_delete_result(d, "r1", "completed")
            self.assertEqual((status, payload), (200, {"deleted": "r1"}))
            self.assertFalse(d.exists())

    def test_failed_run_is_deletable(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            self.assertEqual(_run_delete_result(d, "r1", "failed")[0], 200)

    def test_running_run_is_refused_409(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            status, payload = _run_delete_result(d, "r1", "running")
            self.assertEqual(status, 409)
            self.assertEqual(payload["error"], "run_active")
            self.assertTrue(d.exists())          # nothing deleted

    def test_queued_run_is_refused_409(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            self.assertEqual(_run_delete_result(d, "r1", "queued")[0], 409)

    def test_missing_dir_is_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = _run_delete_result(Path(tmp) / "ghost", "ghost", "unknown")
            self.assertEqual(status, 404)
            self.assertEqual(payload["error"], "not_found")

    def test_rmtree_failure_is_500_not_fake_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            # Hold a file open WITHOUT delete-sharing so rmtree fails on Windows.
            f = open(d / "game-log.json", "r", encoding="utf-8")  # noqa: SIM115
            try:
                status, payload = _run_delete_result(d, "r1", "completed")
                self.assertEqual(status, 500)
                self.assertEqual(payload["error"], "delete_failed")
            finally:
                f.close()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_observer_run_delete -v`
Expected: FAIL — `ImportError: cannot import name '_run_delete_result'`

- [ ] **Step 3: Implement.** In `observer_server.py`, add `import shutil` to the stdlib imports (top of file, alphabetical), and add directly below `_credentials_delete_result` (`:308`):

```python
def _run_delete_result(run_dir: Path, run_id: str, status: str) -> tuple[int, dict[str, object]]:
    """Pure logic for DELETE /api/runs/{run_id}. An active run (running/queued)
    is never deleted (409); a missing dir is 404; an rmtree failure (e.g. a
    Windows file lock) reports 500 — NEVER success on a partial delete."""
    if status in ("running", "queued"):
        return (409, {"error": "run_active"})
    if not run_dir.is_dir():
        return (404, {"error": "not_found"})
    try:
        shutil.rmtree(run_dir)
    except OSError as exc:
        return (500, {"error": "delete_failed", "detail": str(exc)})
    return (200, {"deleted": run_id})
```

> Note `test_rmtree_failure_is_500_not_fake_success` relies on Windows file-lock semantics (this project's dev environment). If the suite ever runs on POSIX, the open-file trick does not block rmtree — guard the test with `@unittest.skipUnless(sys.platform == "win32", "Windows lock semantics")`. Include that decorator from the start.

- [ ] **Step 4: Run to verify it passes** — same command, Expected: PASS (6 tests, 1 skipped on non-Windows).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/observer_server.py tests/test_observer_run_delete.py
git commit -m "feat(observer): pure run-delete logic (409 active / 404 / honest 500)"
```

---

## Task 2: Server route — `DELETE /api/runs/{run_id}`

**Files:** Modify `src/werewolf_eval/observer_server.py:865-886` (`do_DELETE`).

- [ ] **Step 1: Extend `do_DELETE`.** Inside the existing `try:` block, ABOVE the final `self._send_error_json(404, ...)` fallthrough, add:

```python
            if len(segments) == 3 and segments[:2] == ["api", "runs"]:
                if not self._is_loopback():
                    self._send_error_json(403, "forbidden", "runs delete is loopback-only")
                    return
                if self._reject_cross_origin():
                    return
                run_id = segments[2]
                run_dir = self._run_dir(run_id)          # validate_run_id -> raises on illegal id
                status_now = self._get_status(run_id, run_dir)   # memory-first, then status.json
                code, payload = _run_delete_result(run_dir, run_id, status_now)
                if code == 200:
                    state = self._get_state()
                    with state.lock:                      # drop stale in-memory entries
                        state.run_status.pop(run_id, None)
                        state.run_errors.pop(run_id, None)
                    self._send_json(200, payload)
                else:
                    self._send_error_json(code, str(payload.get("error", "bad_request")),
                                          str(payload.get("detail", "")))
                return
```

`validate_run_id` raising inside `_run_dir` is caught by the existing `except ObserverProtocolError` → 400 (verify `validate_run_id` raises `ObserverProtocolError`; it is the same guard every GET route uses via `_run_dir`).

- [ ] **Step 2: Quick wiring check** (no HTTP available — assert routing shape statically):

Run: `NO_PROXY='*' PYTHONPATH=src python -c "import inspect, werewolf_eval.observer_server as s; src=inspect.getsource(s.ObserverRequestHandler.do_DELETE); assert '\"api\", \"runs\"' in src and '_run_delete_result' in src and '_get_status' in src; print('route wired')"`
Expected: `route wired`

- [ ] **Step 3: Full python suite green**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
Expected: OK (947 + 6 new).

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/observer_server.py
git commit -m "feat(observer): DELETE /api/runs/{run_id} route (loopback+CSRF+validate_run_id+memory cleanup)"
```

---

## Task 3: Client C++ — `deleteRun` + open-run race guard (spec rule 4)

**Files:** Modify `clients/qt_observer/src/ObserverApiClient.h`, `clients/qt_observer/src/ObserverApiClient.cpp`.

- [ ] **Step 1: Header.** In `ObserverApiClient.h` add (next to `Q_INVOKABLE void openRun(...)`, `:109`):

```cpp
    Q_INVOKABLE void deleteRun(const QString &runId);
```

and in the signals section:

```cpp
    void deleteRunFinished(const QString &runId, bool ok, const QString &error);
```

and a private member next to the other `m_` fields:

```cpp
    QString m_pendingOpenRunId;   // last openRun target; stale async replies are dropped
```

- [ ] **Step 2: Implement `deleteRun`** in the .cpp (after `openRun`). Find how `get()` (`:98`) builds requests/uses the network manager and mirror it with `deleteResource` (precedent: `CredentialStore.cpp:108`):

```cpp
void ObserverApiClient::deleteRun(const QString &runId)
{
    QNetworkRequest req(QUrl(m_baseUrl + QStringLiteral("/api/runs/") + runId));
    QNetworkReply *reply = m_network->deleteResource(req);
    connect(reply, &QNetworkReply::finished, this, [this, runId, reply]() {
        reply->deleteLater();
        const bool ok = (reply->error() == QNetworkReply::NoError);
        QString err;
        if (!ok) {
            const QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
            err = doc.isObject() ? doc.object().value(QStringLiteral("error")).toString()
                                 : reply->errorString();
            if (err.isEmpty())
                err = reply->errorString();
        }
        if (ok && runId == m_currentRunId)
            setCurrentRunId(QString());   // the theater must not point at a deleted dir
        emit deleteRunFinished(runId, ok, err);
        // NO auto-refresh here: QML decides (single delete refreshes per-op;
        // a batch refreshes ONCE after all deletes finish — spec §4).
    });
}
```

> IMPLEMENTER: match the real member name for the network manager (grep `QNetworkAccessManager` in the .cpp — `get()` at `:98` shows it) and the real `setCurrentRunId` signature (`openRun`'s detail callback uses it at `:260`). If `setCurrentRunId(QString())` triggers refreshes that assume a non-empty id, use the same "no current run" reset path AppShell uses on startup instead.

- [ ] **Step 3: Race guard (rule 4).** In `openRun` (`:233`):
  - first line of the function body: `m_pendingOpenRunId = runId;`
  - first line of the DETAIL reply lambda (`:245`, after `reply->deleteLater();`): `if (runId != m_pendingOpenRunId) return;`
  - the EVENTS lambda (`:281`) currently captures `[this, eventsReply]` — change to `[this, runId, eventsReply]` and add after `eventsReply->deleteLater();`: `if (runId != m_pendingOpenRunId) return;`

This makes a stale run-A reply (detail OR events) a no-op once run B was opened — closing the race at the data source, which also protects the Task 7 auto-seek (the queue can never be holding A's events while the client claims B).

- [ ] **Step 4: Build + ctest**

Run: `cmake --build .tmp/qt-observer-build --config Debug && ctest --test-dir .tmp/qt-observer-build --output-on-failure`
Expected: build exit 0, tests pass. (If the build dir is stale/missing, run the configure line from the Tech Stack first.)

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/src/ObserverApiClient.h clients/qt_observer/src/ObserverApiClient.cpp
git commit -m "feat(qt): deleteRun + deleteRunFinished; openRun stale-reply guard (spec rule 4)"
```

---

## Task 4: QML — `ConfirmDialog` component

**Files:** Create `clients/qt_observer/qml/components/ConfirmDialog.qml`; Modify `clients/qt_observer/CMakeLists.txt` (add the file where the other `components/*.qml` are listed); Modify `tests/test_qt_observer_static_contract.py`.

- [ ] **Step 1: Failing contract test.** In `tests/test_qt_observer_static_contract.py`, add `"qml/components/ConfirmDialog.qml"` to the tracked-files list (`:38` area) and a required-objectName entry (`:75` area):

```python
    "qml/components/ConfirmDialog.qml": ["confirmDialog", "confirmAcceptButton", "confirmCancelButton"],
```

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v`
Expected: FAIL — file missing.

- [ ] **Step 2: Create the component** (Theme/I18n style; modal `Popup` so it needs no Controls.Dialog theming):

```qml
// clients/qt_observer/qml/components/ConfirmDialog.qml
import QtQuick
import QtQuick.Controls.Basic
import ".."

Popup {
    id: root
    objectName: "confirmDialog"

    property string title: ""
    property string message: ""
    property string confirmText: I18n.t("删除", "Delete")
    signal confirmed()

    modal: true
    anchors.centerIn: parent
    width: Math.min(420, parent ? parent.width - Theme.space.xl * 2 : 420)
    padding: Theme.space.lg
    background: Rectangle {
        color: Theme.color.surface
        radius: Theme.radius.md
        border.width: 1
        border.color: Theme.color.border
    }

    contentItem: Column {
        spacing: Theme.space.md
        Text {
            width: parent.width
            text: root.title
            color: Theme.color.text
            font.pixelSize: Theme.size.body
            font.weight: Theme.weight.semibold
            wrapMode: Text.Wrap
        }
        Text {
            width: parent.width
            text: root.message
            color: Theme.color.textMuted
            font.pixelSize: Theme.size.caption
            wrapMode: Text.Wrap
        }
        Row {
            anchors.right: parent.right
            spacing: Theme.space.sm
            AppButton {
                objectName: "confirmCancelButton"
                text: I18n.t("取消", "Cancel")
                variant: "ghost"
                onClicked: root.close()
            }
            AppButton {
                objectName: "confirmAcceptButton"
                text: root.confirmText
                variant: "danger"
                onClicked: { root.close(); root.confirmed() }
            }
        }
    }
}
```

> IMPLEMENTER: check `AppButton.qml` for the real `variant` values — if there is no `"danger"` variant, either add one (a red-tinted fill following the existing variant switch) or use `"secondary"`; whichever you do, keep it consistent in Tasks 5/6. Also check how other components import the singletons (`import ".."` vs a module URI) and match it exactly.

- [ ] **Step 3: Register in CMakeLists** — add `qml/components/ConfirmDialog.qml` alongside the existing component entries (grep `AppButton.qml` in `CMakeLists.txt` and mirror).

- [ ] **Step 4: Contract test passes + build**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v` → PASS.
Run: `cmake --build .tmp/qt-observer-build --config Debug` → exit 0.

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/qml/components/ConfirmDialog.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(qt): Theme-styled ConfirmDialog component"
```

---

## Task 5: QML HistoryView — per-row delete

**Files:** Modify `clients/qt_observer/qml/HistoryView.qml`; Modify `tests/test_qt_observer_static_contract.py`.

- [ ] **Step 1: Failing contract test.** Extend the HistoryView objectName list (`:75`):

```python
    "qml/HistoryView.qml": ["historyView", "historyRunsList", "historyRefreshButton",
                            "deleteRunButton", "historyConfirmDialog", "historyNoticeBar"],
```

Run the contract test → FAIL (names missing).

- [ ] **Step 2: Add the dialog + notice bar + per-row button.**

At the HistoryView root, add state + the dialog + a transient notice bar:

```qml
    // ---- delete plumbing (spec §4) ----
    property string _pendingDeleteId: ""

    ConfirmDialog {
        id: confirmDialog
        objectName: "historyConfirmDialog"
        parent: Overlay.overlay
        onConfirmed: {
            if (root._pendingDeleteId !== "") {
                ObserverClient.deleteRun(root._pendingDeleteId)
                root._pendingDeleteId = ""
            }
        }
    }

    // Transient notice (delete failures / batch summary). Auto-hides.
    Rectangle {
        id: noticeBar
        objectName: "historyNoticeBar"
        property string text: ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.xl
        z: 10
        visible: text !== ""
        width: noticeLabel.implicitWidth + Theme.space.lg * 2
        height: noticeLabel.implicitHeight + Theme.space.md * 2
        radius: Theme.radius.md
        color: Theme.withAlpha(Theme.color.surface, 0.96)
        border.width: 1
        border.color: Theme.color.border
        Text {
            id: noticeLabel
            anchors.centerIn: parent
            text: noticeBar.text
            color: Theme.color.text
            font.pixelSize: Theme.size.caption
        }
        Timer { id: noticeTimer; interval: 5000; onTriggered: noticeBar.text = "" }
        function show(msg) { text = msg; noticeTimer.restart() }
    }

    Connections {
        target: ObserverClient
        function onDeleteRunFinished(runId, ok, error) {
            if (root._batchActive) return            // Task 6 owns batch handling
            if (ok)
                ObserverClient.refreshRuns()          // SINGLE delete refreshes per-op (spec §4)
            else
                noticeBar.show(I18n.t("删除失败:", "Delete failed: ") + error)
        }
    }
    property bool _batchActive: false                 // set by Task 6's controller
```

In the row delegate, LEFT of `reportButton` (`:219`), add:

```qml
                            AppButton {
                                id: deleteButton
                                objectName: "deleteRunButton"
                                anchors.right: reportButton.visible ? reportButton.left : openButton.left
                                anchors.rightMargin: Theme.space.sm
                                anchors.verticalCenter: parent.verticalCenter
                                text: I18n.t("删除", "Delete")
                                variant: "ghost"
                                enabled: (modelData.status || "") !== "running"
                                         && (modelData.status || "") !== "queued"
                                opacity: enabled ? 1.0 : 0.35
                                onClicked: {
                                    root._pendingDeleteId = modelData.run_id
                                    confirmDialog.title = I18n.t("删除对局", "Delete run")
                                    confirmDialog.message = I18n.t("确定删除对局 ", "Delete run ")
                                        + modelData.run_id
                                        + I18n.t("?删除后不可恢复。", "? This cannot be undone.")
                                    confirmDialog.open()
                                }
                            }
```

> IMPLEMENTER: `root` here is HistoryView's root item id — match the file's actual root id (grep `objectName: "historyView"`). Adjust `reportButton`'s own `anchors.right` chain if needed so the three buttons lay out right-to-left: [删除][查看战报][打开] without overlap; verify visually in Step 4.

- [ ] **Step 3: Contract test passes + build + python suite**

Run: contract test → PASS; `cmake --build .tmp/qt-observer-build --config Debug` → exit 0; full python suite → OK.

- [ ] **Step 4: Screenshot verification.** Launch the app against a local server with a few runs (`launch-theater.bat` or the README run line), open 历史对局, screenshot: per-row 删除 visible, greyed on a running row (if any), dialog opens with run id in message, confirm deletes + list refreshes.

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/qml/HistoryView.qml tests/test_qt_observer_static_contract.py
git commit -m "feat(qt): per-row run delete with confirm + notice bar in HistoryView"
```

---

## Task 6: QML HistoryView — selection mode + batch delete

**Files:** Modify `clients/qt_observer/qml/HistoryView.qml`; Modify `tests/test_qt_observer_static_contract.py`.

- [ ] **Step 1: Failing contract test.** Extend HistoryView's list again:

```python
    "qml/HistoryView.qml": ["historyView", "historyRunsList", "historyRefreshButton",
                            "deleteRunButton", "historyConfirmDialog", "historyNoticeBar",
                            "selectModeButton", "rowSelectBox", "selectAllBox", "batchDeleteButton"],
```

Run → FAIL.

- [ ] **Step 2: Selection state + batch controller** (HistoryView root):

```qml
    // ---- batch selection (spec §4) ----
    property bool selecting: false
    property var _selected: ({})                     // run_id -> true
    readonly property int selectedCount: Object.keys(_selected).length
    property var _batchQueue: []
    property int _batchFailed: 0
    property var _batchErrors: []

    function _toggleSelected(runId, on) {
        var m = _selected
        if (on) m[runId] = true; else delete m[runId]
        _selected = m                                 // reassign to fire bindings
    }
    function _exitSelectMode() { selecting = false; _selected = ({}) }

    function _startBatchDelete() {
        _batchQueue = Object.keys(_selected)
        _batchFailed = 0
        _batchErrors = []
        _batchActive = true
        _pumpBatch()
    }
    function _pumpBatch() {
        if (_batchQueue.length === 0) {
            _batchActive = false
            var total = Object.keys(_selected).length
            var okCount = total - _batchFailed
            noticeBar.show(_batchFailed === 0
                ? I18n.t("已删除 ", "Deleted ") + okCount + I18n.t(" 局", " runs")
                : I18n.t("已删除 ", "Deleted ") + okCount + I18n.t(" 局,", " runs, ")
                  + _batchFailed + I18n.t(" 局失败:", " failed: ") + _batchErrors.join("; "))
            _exitSelectMode()
            ObserverClient.refreshRuns()              // batch refreshes ONCE at the end (spec §4)
            return
        }
        ObserverClient.deleteRun(_batchQueue.shift())
    }
```

Extend the Task 5 `Connections` handler with the batch branch (replace its body):

```qml
        function onDeleteRunFinished(runId, ok, error) {
            if (root._batchActive) {
                if (!ok) { root._batchFailed += 1; root._batchErrors.push(runId + ": " + error) }
                root._pumpBatch()                     // sequential: next delete only after this one
                return
            }
            if (ok) ObserverClient.refreshRuns()
            else noticeBar.show(I18n.t("删除失败:", "Delete failed: ") + error)
        }
```

- [ ] **Step 3: Header toggle + select-all + per-row checkbox + batch button.**

In `panelHeader` (`:90-126`), left of the count chip:

```qml
                    AppButton {
                        objectName: "selectModeButton"
                        anchors.right: parent.right
                        anchors.rightMargin: 60        // keep clear of the count chip; tune visually
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.selecting ? I18n.t("取消", "Cancel") : I18n.t("选择", "Select")
                        variant: "ghost"
                        visible: ObserverClient.runItems.length > 0
                        onClicked: root.selecting ? root._exitSelectMode() : root.selecting = true
                    }
                    CheckBox {
                        objectName: "selectAllBox"
                        visible: root.selecting
                        anchors.left: panelTitle.right
                        anchors.leftMargin: Theme.space.md
                        anchors.verticalCenter: parent.verticalCenter
                        onToggled: {
                            var m = ({})
                            if (checked)
                                for (var i = 0; i < ObserverClient.runItems.length; i++) {
                                    var it = ObserverClient.runItems[i]
                                    var st = it.status || ""
                                    if (st !== "running" && st !== "queued") m[it.run_id] = true
                                }
                            root._selected = m
                        }
                    }
```

Row delegate, at the row's far LEFT (before the existing content; shift content right when selecting):

```qml
                            CheckBox {
                                objectName: "rowSelectBox"
                                visible: root.selecting
                                enabled: (modelData.status || "") !== "running"
                                         && (modelData.status || "") !== "queued"
                                anchors.left: parent.left
                                anchors.leftMargin: Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                checked: root._selected[modelData.run_id] === true
                                onToggled: root._toggleSelected(modelData.run_id, checked)
                            }
```

Below the runs panel (footer area), the batch action:

```qml
                AppButton {
                    objectName: "batchDeleteButton"
                    visible: root.selecting && root.selectedCount > 0
                    text: I18n.t("删除所选(", "Delete selected (") + root.selectedCount + ")"
                    variant: "danger"
                    onClicked: {
                        confirmDialog.title = I18n.t("批量删除", "Batch delete")
                        confirmDialog.message = I18n.t("确定删除 ", "Delete ") + root.selectedCount
                            + I18n.t(" 局?删除后不可恢复。", " runs? This cannot be undone.")
                        root._pendingDeleteId = ""            // batch path, not single
                        confirmDialog.confirmed.connect(function once() {
                            confirmDialog.confirmed.disconnect(once)
                            root._startBatchDelete()
                        })
                        confirmDialog.open()
                    }
                }
```

> IMPLEMENTER: the connect-once pattern above coexists with Task 5's `onConfirmed` (which no-ops when `_pendingDeleteId === ""`). If you prefer, replace both with a single `property var _onConfirm: null` callback on the dialog — pick ONE pattern and make Task 5's single-delete path use it too. Anchoring/placement: follow the file's existing footer anchors; verify no overlap visually. NOTE `_pumpBatch`'s completion uses `Object.keys(_selected).length` as `total` — capture `total` at `_startBatchDelete` time into a property instead if `_selected` mutates during the batch (it shouldn't — selection UI is hidden while `_batchActive`; assert by keeping the list non-interactive during batch if simpler).

- [ ] **Step 4: Contract test PASS + build exit 0 + screenshot** (selection mode on: checkboxes + select-all + batch button with live count; batch of 2-3 deletes shows ONE refresh + summary notice).

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/qml/HistoryView.qml tests/test_qt_observer_static_contract.py
git commit -m "feat(qt): selection mode + sequential batch delete (single refresh) in HistoryView"
```

---

## Task 7: TheaterView — latched report fast-forward (spec rules 1-3, 5)

**Files:** Modify `clients/qt_observer/qml/TheaterView.qml`.

- [ ] **Step 1: Add the latch + trigger** (near `settlementEntryMode`, `:252`):

```qml
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
        if (eventQueue._ordered.length === 0) return                      // rule 2: queue filled
        if (_autoSeekDoneForRun === ObserverClient.currentRunId) return   // rule 3: one-shot
        _autoSeekDoneForRun = ObserverClient.currentRunId
        eventQueue.seekQueueEnd()
    }

    Connections {
        target: ObserverClient
        function onEventItemsChanged() { Qt.callLater(theaterRoot._maybeAutoSeekReport) }
        function onCurrentStatusChanged() { Qt.callLater(theaterRoot._maybeAutoSeekReport) }
    }
```

(`Qt.callLater` lets the `eventQueue.source` binding re-evaluate before the check — calling synchronously inside the change signal would still see the OLD `_ordered`. `theaterRoot` is the file's root id, `:13` area — match it. Note rule 4 needs no code here: Task 3's `m_pendingOpenRunId` guard guarantees `eventItems`/`currentRunId` are never a stale run's data.)

Also call it once on mount for the re-open case (events already loaded, no change signal will fire). In the existing `Component.onCompleted` (`:17-28`), append:

```qml
        Qt.callLater(theaterRoot._maybeAutoSeekReport)
```

- [ ] **Step 2: Build + manual verification matrix.**

Run: `cmake --build .tmp/qt-observer-build --config Debug` → exit 0. Then with a real server + several completed runs:

| Action | Expected |
|---|---|
| 历史 →「查看战报」on completed run | settlement overlay appears in `report` mode within ~1-2s (queue gate-crosses phases), NO full-paced replay |
| 历史 →「打开」same run | full replay from round 1, settlement only after replay ends (unchanged) |
| 「查看战报」A then immediately「打开」B | B replays normally; A's late events never fast-forward B (rule 4, Task 3 guard) |
| 战报 view → switch language (I18n) | no second seek, no queue churn (latch) |

- [ ] **Step 3: Full python suite + contract test green** (TheaterView contract names unchanged).

- [ ] **Step 4: Commit**

```bash
git add clients/qt_observer/qml/TheaterView.qml
git commit -m "feat(qt): report entry auto fast-forwards replay to settlement (latched, completed-only)"
```

---

## Task 8: Closeout — tree hook, validation report, final regression

**Files:** none (verification + generated tree).

- [ ] **Step 1: Tree hook** (root policy — new files were created):

Run: `node .codex/hooks/tree.mjs --force`
(If node/hook unavailable, per AGENTS.md explain and attach `git ls-files --cached --others --exclude-standard` output instead.)

- [ ] **Step 2: Final regression**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` → OK.
Run: `cmake --build .tmp/qt-observer-build --config Debug && ctest --test-dir .tmp/qt-observer-build --output-on-failure` → exit 0 / pass.

- [ ] **Step 3: Validation report (root policy, AGENTS.md「Validation」)** — produce and include with the handoff:
  - `git diff --stat main...HEAD` and `git diff --name-only main...HEAD`
  - Allowlist check: every touched file ∈ {`observer_server.py`, `tests/test_observer_run_delete.py`, `tests/test_qt_observer_static_contract.py`, `ObserverApiClient.h/.cpp`, `ConfirmDialog.qml`, `HistoryView.qml`, `TheaterView.qml`, `CMakeLists.txt`, tree.md}.
  - Forbidden-scope check: NO changes under engine/runtime (`emergent_engine.py`, `action_runtime/**`, `invariants/**`), `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/adr/**`, historical plans, gold-game, `.github/**`.
  - Tests: the new + full suites above; screenshots from Tasks 5/6/7.

- [ ] **Step 4: Commit** (tree update if changed)

```bash
git add .oh-my-harness/tree.md
git commit -m "chore: tree update for history-run-management files"
```

---

## Self-Review (writing-plans checklist)

**Spec coverage:** §3 server protocol → Tasks 1-2 (all 7 guard rows incl. 409/404/500-honest/memory cleanup). §4 delete UX → Tasks 3-6 (per-row + batch + confirm + notice + single-vs-batch refresh semantics + currentRunId clear). §5 rules 1/2/3/5 → Task 7 (each rule cited inline); rule 4 → Task 3 (`m_pendingOpenRunId`, closing the race at the source). §6 testing → pure-logic server tests (no-HTTP pattern), contract tests, build+ctest, screenshot matrix; validation五件套 → Task 8.

**Placeholder scan:** IMPLEMENTER notes (Tasks 3/4/5/6) point at real in-repo patterns to match (member names, variant values, anchor chains) rather than inventing them — each states exactly what to grep. No TBD/TODO.

**Type consistency:** `deleteRun(runId)` / `deleteRunFinished(runId, ok, error)` consistent across Tasks 3/5/6. `_run_delete_result(run_dir, run_id, status) -> (int, dict)` consistent Tasks 1/2. `ConfirmDialog{title,message,confirmText,confirmed()}` consistent Tasks 4/5/6. Latch/trigger names consistent within Task 7.

**Known judgment calls (explicit, not silent):** notice bar instead of a toast framework (none exists; spec's "toast" = transient notice); rebuild-re-seek documented as correct (queue restarts on rebuild); batch `total` capture noted in Task 6's IMPLEMENTER note.
