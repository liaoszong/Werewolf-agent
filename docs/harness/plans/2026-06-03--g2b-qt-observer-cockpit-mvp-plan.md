# G2b Qt Observer Cockpit MVP Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Turn the existing `clients/qt_observer` Qt6 Quick scaffold into the first game-like observer cockpit MVP that consumes the completed G2a client-agnostic observer protocol.

**Architecture:** Implement a Qt/QML rich client with a small C++ protocol adapter for G2a REST/SSE endpoints and a QML-first game lobby / match setup / preflight / live cockpit / history experience. The client must communicate only with the G2a local observer server over HTTP/SSE; it must not import Python runtime internals, read run files directly, or implement its own visibility filtering beyond passing the selected `perspective` to G2a.

**Tech Stack:** Qt 6.8+ / Qt Quick / Qt Quick Controls / Qt Network / Qt Test, CMake, C++17, QML, Python `unittest` static contract checks. No Python runtime changes, no third-party C++ dependencies, no Web UI framework, no provider API calls.

---

## Context Basis

Current route facts:

- `docs/ROADMAP.md` marks G2a Local Observer Server as `completed` and says the next implementation candidate is G2b Qt Observer MVP.
- `docs/TASKS.md` marks G2b as `scaffold_created` with dependency on completed G2a and explicitly says `clients/qt_observer` currently has only Qt Creator generated starter files.
- `clients/qt_observer/README.md` says the current scaffold has no observer protocol integration, no match cockpit UI, no God/Role View rendering, no run control, and no replay/history UI.
- `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md` requires the cockpit to show current phase/round, player seats, event stream, current actor/action, provider/failure status, audit links, and God/Public/Role/Team perspective switching.
- G2b must build on G2a protocol, not on Python runtime internals.

Recommended next development point:

```text
G2b Qt Observer MVP
```

Reason:

```text
G2a has supplied the protocol/control plane. The product now needs its first rich observer surface so users can start a default AI-vs-AI match, watch it live, reopen historical runs, and understand the match without reading JSON.
```

## Scope Summary

G2b includes:

- Qt/QML app shell with Home/Lobby, Start New Match, Preflight, Live Match Cockpit, and Match History views.
- A small C++ `ObserverApiClient` that uses Qt Network to call G2a REST endpoints and consume SSE stream events.
- A game-like visual surface for default 6-player AI-vs-AI matches, including role/player cards, run status, event timeline, perspective switcher, and audit links.
- Minimal default match launch flow through G2a `POST /api/runs` with `template = default_6p_fake`.
- History/replay flow through G2a `GET /api/runs`, `/events`, and `/stream`.
- Tests for C++ parsing/client contracts, QML/static product-contract checks, no direct Python runtime binding, no secret markers, and Qt build/test smoke.
- A compact review packet for Codex省余额审查.

G2b does not include:

- Full prompt/profile editor.
- Seat-level AI/prompt customization UI beyond read-only/default placeholders.
- Full Phase E visibility hardening or client-side trust proof.
- Web observer client.
- Human-vs-AI UI.
- Multi-provider arena.
- Leaderboard or score formula changes.
- Python runtime, provider, scoring, validator, generated fixture, demo HTML, ROADMAP, TASKS, or G2a server behavior changes.

---

## UX Contract For G2b MVP

The MVP must feel like a game observer cockpit, not a raw JSON dashboard.

Required user flow:

```text
Home / Lobby
-> Start New Match
-> default 6-player config preview
-> Preflight summary
-> Start Match
-> Live Match Cockpit
-> Match History / Replay
```

Required visible UI concepts:

- Home / Lobby:
  - observer server base URL field or display,
  - connection status,
  - Start New Match button,
  - History button,
  - recent runs list preview.
- Match Setup:
  - six visual player/role cards,
  - default 6-player AI-vs-AI template label,
  - explicit note that role/prompt customization is later G2d,
  - no prompt editor.
- Preflight:
  - observer server health,
  - selected template,
  - visibility boundary note,
  - output/artifact note,
  - Start Match button.
- Live Cockpit:
  - current run status,
  - current phase/round when available from events,
  - six player cards,
  - event timeline,
  - perspective switcher for `god`, `public`, `role:p1`-`role:p6`, `team:werewolf`,
  - provider/failure status summary,
  - audit links panel for manifest/provider-trace/failure-audit/snapshots/final logs.
- Match History:
  - completed and recent runs from G2a `/api/runs`,
  - open/replay action using the same cockpit surface,
  - no leaderboard.

Important boundary:

```text
The UI may display role cards as setup/observer presentation, but role-view data must always come from G2a perspective-specific endpoints. The Qt client must not implement independent hidden-information filtering from local Python objects or raw files.
```

---

## G2a Protocol Endpoints Used

The implementation must call only G2a HTTP/SSE protocol endpoints:

```text
GET  /health
GET  /api/runs
POST /api/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events?perspective=...
GET  /api/runs/{run_id}/stream?perspective=...
GET  /api/runs/{run_id}/snapshots?perspective=...
GET  /api/runs/{run_id}/artifacts
GET  /api/runs/{run_id}/manifest
GET  /api/runs/{run_id}/provider-trace
GET  /api/runs/{run_id}/failure-audit
```

The Qt client must not:

- read `events.jsonl` or `snapshots/*.json` from disk,
- import or shell out to Python runtime internals,
- call DeepSeek/live providers,
- start a provider runtime directly except through G2a `POST /api/runs`,
- bypass G2a perspective filtering.

---

## File Plan

### Create

- `clients/qt_observer/src/ObserverApiClient.h`
  - QObject protocol adapter exposed to QML.
  - Owns `baseUrl`, `connected`, `currentRunId`, `currentStatus`, `currentPerspective`, `eventItems`, `runItems`, `auditItems`, `lastError`, and invokable methods.

- `clients/qt_observer/src/ObserverApiClient.cpp`
  - Uses `QNetworkAccessManager` for REST.
  - Uses long-lived `QNetworkReply` for SSE stream.
  - Parses G2a JSON and SSE frames.
  - Emits QML-friendly signals.

- `clients/qt_observer/src/ObserverSseParser.h`
  - Small pure C++/Qt helper for SSE frame parsing.

- `clients/qt_observer/src/ObserverSseParser.cpp`
  - Parses `event: runtime_event` and `event: run_status` frames into value objects.

- `clients/qt_observer/qml/AppShell.qml`
  - Root navigation shell and shared layout.

- `clients/qt_observer/qml/HomeView.qml`
  - Lobby page.

- `clients/qt_observer/qml/MatchSetupView.qml`
  - Default 6-player setup page with role cards.

- `clients/qt_observer/qml/PreflightView.qml`
  - Preflight summary page.

- `clients/qt_observer/qml/LiveCockpitView.qml`
  - Main cockpit page.

- `clients/qt_observer/qml/HistoryView.qml`
  - Run history/replay page.

- `clients/qt_observer/qml/components/RoleCard.qml`
  - Visual role/player card.

- `clients/qt_observer/qml/components/EventTimeline.qml`
  - Event stream list.

- `clients/qt_observer/qml/components/PerspectiveSwitcher.qml`
  - God/Public/Role/Team selector.

- `clients/qt_observer/qml/components/AuditLinksPanel.qml`
  - Artifact/action links panel.

- `clients/qt_observer/qml/components/StatusBadge.qml`
  - Status badge component.

- `clients/qt_observer/tests/tst_observer_sse_parser.cpp`
  - QtTest for SSE parsing and conservative parser behavior.

- `tests/test_qt_observer_static_contract.py`
  - Python static tests for CMake/QML contract, no direct Python runtime binding, expected screen/component files, and no secret markers.

### Modify

- `clients/qt_observer/CMakeLists.txt`
  - Add Qt components `Network`, `QuickControls2`, and `Test`.
  - Add source files and QML files.
  - Add QtTest executable and `enable_testing()`.

- `clients/qt_observer/main.cpp`
  - Register `ObserverApiClient` as a QML singleton/context property.
  - Parse optional `--observer-base-url` argument with default `http://127.0.0.1:8765`.
  - Load `AppShell` or keep module entry as `Main` delegating to `AppShell`.

- `clients/qt_observer/Main.qml`
  - Replace default Hello World window with root shell that loads `AppShell`.

- `clients/qt_observer/README.md`
  - Update status from scaffold-only to G2b MVP.
  - Preserve explicit non-goals.
  - Document how to configure/build/run against local G2a server.

- `.logs/review/latest/review-packet.md`
  - Implementation evidence only.

- `.oh-my-harness/tree.md`
  - Refresh only via `node .codex/hooks/tree.mjs --force` because new files are created.

### Do Not Modify

- `src/werewolf_eval/**`
- `tests/test_observer_protocol.py`
- `tests/test_observer_server.py`
- Any G2a observer server/protocol implementation.
- `docs/ROADMAP.md`
- `docs/TASKS.md`
- `docs/PRODUCT_ONE_PAGER.md`
- `README.md` outside `clients/qt_observer/README.md`.
- `docs/adr/**`
- `docs/demo/**`
- `docs/generated-games/**`
- `docs/gold-game/**`
- Dependency manifests outside `clients/qt_observer/CMakeLists.txt`.
- GitHub workflow files.

---

## Allowlist

Implementation may change only these paths:

```text
clients/qt_observer/CMakeLists.txt
clients/qt_observer/main.cpp
clients/qt_observer/Main.qml
clients/qt_observer/README.md
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/src/ObserverSseParser.h
clients/qt_observer/src/ObserverSseParser.cpp
clients/qt_observer/qml/AppShell.qml
clients/qt_observer/qml/HomeView.qml
clients/qt_observer/qml/MatchSetupView.qml
clients/qt_observer/qml/PreflightView.qml
clients/qt_observer/qml/LiveCockpitView.qml
clients/qt_observer/qml/HistoryView.qml
clients/qt_observer/qml/components/RoleCard.qml
clients/qt_observer/qml/components/EventTimeline.qml
clients/qt_observer/qml/components/PerspectiveSwitcher.qml
clients/qt_observer/qml/components/AuditLinksPanel.qml
clients/qt_observer/qml/components/StatusBadge.qml
clients/qt_observer/tests/tst_observer_sse_parser.cpp
tests/test_qt_observer_static_contract.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

`.oh-my-harness/tree.md` is allowed only if refreshed by:

```powershell
node .codex/hooks/tree.mjs --force
```

`.logs/review/latest/review-packet.md` is allowed only for compact implementation evidence.

## Forbidden Scope

Implementation must not:

- Modify `src/werewolf_eval/**` or any Python runtime/server/provider/scoring/validator code.
- Modify `tests/test_observer_protocol.py` or `tests/test_observer_server.py`.
- Modify route docs such as `README.md`, `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/PRODUCT_ONE_PAGER.md`, or `docs/adr/**`.
- Modify historical plans/reviews, demo HTML, generated games, gold-game fixtures, semantic-labeling docs, or `.github/**`.
- Add provider API calls, live API flags, secrets, API keys, or credential handling.
- Add Web UI, Electron, React/Vue, Python GUI bindings, PySide/PyQt, QML WebEngine, or browser automation.
- Add third-party C++ package managers or dependency manifests.
- Read local run files directly from the Qt client.
- Shell out from Qt to Python runtime or `werewolf_eval` modules.
- Implement client-side hidden-information filtering based on raw artifacts; use G2a perspective endpoints instead.
- Claim G2c/G2d/G3/G4 completion.

---

## Task 1: Add Qt protocol adapter and SSE parser

**Files:**

- Create: `clients/qt_observer/src/ObserverSseParser.h`
- Create: `clients/qt_observer/src/ObserverSseParser.cpp`
- Create: `clients/qt_observer/src/ObserverApiClient.h`
- Create: `clients/qt_observer/src/ObserverApiClient.cpp`
- Modify: `clients/qt_observer/CMakeLists.txt`
- Test: `clients/qt_observer/tests/tst_observer_sse_parser.cpp`

- [ ] **Step 1: Add `ObserverSseParser` API**

Implement a small parser with this public shape:

```cpp
#pragma once

#include <QString>
#include <QJsonObject>
#include <QList>

struct ObserverSseMessage {
    QString eventName;
    QJsonObject data;
};

class ObserverSseParser {
public:
    QList<ObserverSseMessage> feed(const QByteArray &chunk);
    void reset();

private:
    QByteArray m_buffer;
};
```

Required behavior:

- Accept chunks from a long-lived G2a SSE reply.
- Split frames by blank line.
- Parse `event: runtime_event` and `event: run_status`.
- Parse `data: {json}` into `QJsonObject`.
- Ignore unknown lines.
- Keep incomplete frames buffered until the next chunk.
- Never throw exceptions.

- [ ] **Step 2: Add `ObserverApiClient` QML-facing API**

Implement a QObject with these Q_PROPERTY names and invokables:

```cpp
class ObserverApiClient : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString baseUrl READ baseUrl WRITE setBaseUrl NOTIFY baseUrlChanged)
    Q_PROPERTY(bool connected READ connected NOTIFY connectedChanged)
    Q_PROPERTY(QString currentRunId READ currentRunId NOTIFY currentRunChanged)
    Q_PROPERTY(QString currentStatus READ currentStatus NOTIFY currentStatusChanged)
    Q_PROPERTY(QString currentPerspective READ currentPerspective WRITE setCurrentPerspective NOTIFY currentPerspectiveChanged)
    Q_PROPERTY(QVariantList runItems READ runItems NOTIFY runItemsChanged)
    Q_PROPERTY(QVariantList eventItems READ eventItems NOTIFY eventItemsChanged)
    Q_PROPERTY(QVariantList auditItems READ auditItems NOTIFY auditItemsChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

public slots:
    Q_INVOKABLE void checkHealth();
    Q_INVOKABLE void refreshRuns();
    Q_INVOKABLE void startDefaultMatch();
    Q_INVOKABLE void openRun(const QString &runId);
    Q_INVOKABLE void connectStream();
    Q_INVOKABLE void disconnectStream();
    Q_INVOKABLE void refreshAuditLinks();
};
```

Required behavior:

- `baseUrl` default is `http://127.0.0.1:8765`.
- `checkHealth()` calls `GET /health`.
- `refreshRuns()` calls `GET /api/runs`.
- `startDefaultMatch()` calls `POST /api/runs` with body `{"template":"default_6p_fake","mode":"fake"}`.
- `openRun(runId)` calls `GET /api/runs/{run_id}` and then `/events?perspective=currentPerspective`.
- `connectStream()` calls `/api/runs/{run_id}/stream?perspective=currentPerspective`.
- Perspective changes reconnect the stream for the current run.
- `refreshAuditLinks()` calls `/artifacts` and builds QML-displayable artifact items.
- All network failures set `lastError` and must not crash the app.
- The client must not read local files.

- [ ] **Step 3: Wire CMake for Qt Network, Quick Controls, and Qt Test**

Modify `clients/qt_observer/CMakeLists.txt`:

```cmake
find_package(Qt6 REQUIRED COMPONENTS Quick QuickControls2 Network Test)

qt_add_executable(appqt_observer
    main.cpp
    src/ObserverApiClient.cpp
    src/ObserverApiClient.h
    src/ObserverSseParser.cpp
    src/ObserverSseParser.h
)

target_link_libraries(appqt_observer
    PRIVATE Qt6::Quick Qt6::QuickControls2 Qt6::Network
)

enable_testing()
qt_add_executable(tst_observer_sse_parser
    tests/tst_observer_sse_parser.cpp
    src/ObserverSseParser.cpp
    src/ObserverSseParser.h
)
target_link_libraries(tst_observer_sse_parser PRIVATE Qt6::Test Qt6::Core)
add_test(NAME observer_sse_parser COMMAND tst_observer_sse_parser)
```

Do not add non-Qt third-party dependencies.

- [ ] **Step 4: Add QtTest for SSE parser**

Create `clients/qt_observer/tests/tst_observer_sse_parser.cpp` with tests:

```cpp
class ObserverSseParserTests : public QObject {
    Q_OBJECT
private slots:
    void parsesRuntimeEventFrame();
    void parsesRunStatusFrame();
    void buffersIncompleteFrameAcrossChunks();
    void ignoresUnknownLinesWithoutCrashing();
};
```

Expected assertions:

- `eventName == "runtime_event"` for runtime event frames.
- `eventName == "run_status"` for status frames.
- JSON data contains `run_id`, `status`, or `kind` when present.
- Incomplete chunk returns zero messages until completed.

- [ ] **Step 5: Run parser tests**

Run from repository root in an environment where Qt 6.8+ CMake packages are available:

```powershell
Remove-Item -Recurse -Force .tmp/qt-observer-build -ErrorAction SilentlyContinue
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
ctest --test-dir .tmp/qt-observer-build --output-on-failure
```

Expected result:

```text
100% tests passed
```

Record exact CMake, build, and CTest summaries in the review packet.

---

## Task 2: Add QML application shell and navigation

**Files:**

- Modify: `clients/qt_observer/main.cpp`
- Modify: `clients/qt_observer/Main.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`
- Create: `clients/qt_observer/qml/AppShell.qml`
- Create: `clients/qt_observer/qml/HomeView.qml`
- Create: `clients/qt_observer/qml/MatchSetupView.qml`
- Create: `clients/qt_observer/qml/PreflightView.qml`
- Create: `clients/qt_observer/qml/LiveCockpitView.qml`
- Create: `clients/qt_observer/qml/HistoryView.qml`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Expose `ObserverApiClient` to QML**

Modify `main.cpp` so the QML context has an `observerClient` object:

```cpp
ObserverApiClient observerClient;
observerClient.setBaseUrl(observerBaseUrlFromArgs(argc, argv));
engine.rootContext()->setContextProperty("observerClient", &observerClient);
engine.loadFromModule("qt_observer", "Main");
```

Required behavior:

- Parse optional CLI argument `--observer-base-url <url>`.
- Default to `http://127.0.0.1:8765`.
- Do not start the Python observer server from Qt.

- [ ] **Step 2: Replace default `Main.qml`**

`Main.qml` must be a real application window, not Hello World:

```qml
import QtQuick
import QtQuick.Controls
import qt_observer

ApplicationWindow {
    id: root
    objectName: "werewolfObserverMainWindow"
    width: 1280
    height: 800
    visible: true
    title: qsTr("Werewolf Observer")

    AppShell {
        id: appShell
        objectName: "appShell"
        anchors.fill: parent
    }
}
```

- [ ] **Step 3: Add `AppShell.qml` navigation**

Required object names:

```text
appShell
homeView
matchSetupView
preflightView
liveCockpitView
historyView
```

Required navigation states:

```text
home
setup
preflight
cockpit
history
```

Buttons or signals must support:

```text
Home -> Start New Match -> Setup
Setup -> Preflight
Preflight -> Start Match -> Cockpit
Home -> History
History -> Open Run -> Cockpit
```

- [ ] **Step 4: Add static contract test for shell files**

Create `tests/test_qt_observer_static_contract.py` with:

```python
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
QT = ROOT / "clients" / "qt_observer"

class QtObserverStaticContractTests(unittest.TestCase):
    def test_required_qml_views_exist(self) -> None: ...
    def test_main_window_is_not_hello_world(self) -> None: ...
    def test_navigation_object_names_exist(self) -> None: ...
```

Expected assertions:

- Each required QML file exists.
- `Main.qml` does not contain `Hello World`.
- QML contains object names listed above.

- [ ] **Step 5: Run static tests**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected result:

```text
OK
```

---

## Task 3: Add game-like Home, Setup, and Preflight UI

**Files:**

- Modify: `clients/qt_observer/qml/HomeView.qml`
- Modify: `clients/qt_observer/qml/MatchSetupView.qml`
- Modify: `clients/qt_observer/qml/PreflightView.qml`
- Create: `clients/qt_observer/qml/components/RoleCard.qml`
- Create: `clients/qt_observer/qml/components/StatusBadge.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Implement `RoleCard.qml`**

Required properties:

```qml
property string seatId
property string roleName
property string aiLabel
property string statusText
property string accentText
property bool selected
```

Required visual behavior:

- Card-like rectangle with rounded corners.
- Role glyph or silhouette using text/shape only; do not add binary image assets in this milestone.
- Displays seat ID, role name, AI label, and status.
- Has `objectName: "roleCard"`.

- [ ] **Step 2: Implement `HomeView.qml`**

Required object names:

```text
homeView
startNewMatchButton
historyButton
serverStatusBadge
recentRunsList
```

Required actions:

- `startNewMatchButton` navigates to setup.
- `historyButton` navigates to history and calls `observerClient.refreshRuns()`.
- Home calls `observerClient.checkHealth()` on completion.

- [ ] **Step 3: Implement `MatchSetupView.qml`**

Required role cards:

```text
p1 Werewolf
p2 Werewolf
p3 Seer
p4 Witch
p5 Villager
p6 Villager
```

Required object names:

```text
matchSetupView
setupRoleCards
setupContinueButton
```

Required behavior:

- Shows default 6-player template.
- Uses six `RoleCard` components.
- Displays note that prompt/profile editing is later G2d.
- Continue navigates to Preflight.

- [ ] **Step 4: Implement `PreflightView.qml`**

Required object names:

```text
preflightView
preflightServerStatus
preflightTemplateSummary
preflightVisibilitySummary
startMatchButton
```

Required behavior:

- Displays selected template `default_6p_fake`.
- Displays server status from `observerClient.connected`.
- Displays visibility boundary note.
- `startMatchButton` calls `observerClient.startDefaultMatch()` and navigates to cockpit when a run id is available.

- [ ] **Step 5: Extend static tests**

Add tests:

```python
class QtObserverSetupContractTests(unittest.TestCase):
    def test_setup_contains_default_six_player_roles(self) -> None: ...
    def test_preflight_mentions_visibility_boundary_and_default_template(self) -> None: ...
    def test_no_prompt_editor_is_added(self) -> None: ...
```

Assertions:

- QML contains `p1`-`p6` and role labels.
- QML contains `default_6p_fake`.
- QML contains visibility boundary text.
- No QML file contains `promptEditor`, `PromptEditor`, or `textarea` intended for prompt editing.

- [ ] **Step 6: Run tests and build**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
```

Expected:

- Python static tests: `OK`.
- CMake configure exits `0`.
- Build exits `0`.

---

## Task 4: Add Live Match Cockpit and History/Replay UI

**Files:**

- Modify: `clients/qt_observer/qml/LiveCockpitView.qml`
- Modify: `clients/qt_observer/qml/HistoryView.qml`
- Create: `clients/qt_observer/qml/components/EventTimeline.qml`
- Create: `clients/qt_observer/qml/components/PerspectiveSwitcher.qml`
- Create: `clients/qt_observer/qml/components/AuditLinksPanel.qml`
- Modify: `clients/qt_observer/qml/components/RoleCard.qml`
- Modify: `clients/qt_observer/CMakeLists.txt`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Implement `PerspectiveSwitcher.qml`**

Required perspective values:

```text
god
public
role:p1
role:p2
role:p3
role:p4
role:p5
role:p6
team:werewolf
```

Required behavior:

- Exposes selected perspective string.
- Calls `observerClient.currentPerspective = selectedPerspective`.
- Has `objectName: "perspectiveSwitcher"`.
- UI labels must distinguish God/Public/Role/Team views.

- [ ] **Step 2: Implement `EventTimeline.qml`**

Required object names:

```text
eventTimeline
eventTimelineList
```

Required display fields when present:

```text
seq
kind
phase
round
actor
visibility
summary
```

The timeline must display empty-state text when no events have arrived.

- [ ] **Step 3: Implement `AuditLinksPanel.qml`**

Required object names:

```text
auditLinksPanel
manifestLink
providerTraceLink
failureAuditLink
snapshotsLink
artifactsLink
```

Required behavior:

- Shows artifact availability from `observerClient.auditItems`.
- Does not open local file paths.
- Uses G2a URLs or copyable endpoint paths only.

- [ ] **Step 4: Implement `LiveCockpitView.qml`**

Required object names:

```text
liveCockpitView
runStatusBadge
playerPanelGrid
eventTimeline
perspectiveSwitcher
auditLinksPanel
providerFailureSummary
```

Required behavior:

- Calls `observerClient.connectStream()` when entering cockpit with a run id.
- Shows current run id and status.
- Shows six player cards.
- Shows event timeline backed by `observerClient.eventItems`.
- Shows perspective switcher.
- Shows provider/failure summary from available event/audit data.
- No raw JSON dump as the primary UI.

- [ ] **Step 5: Implement `HistoryView.qml`**

Required object names:

```text
historyView
historyRunsList
historyRefreshButton
openReplayButton
```

Required behavior:

- Calls `observerClient.refreshRuns()`.
- Lists `observerClient.runItems`.
- Opens selected run by calling `observerClient.openRun(runId)` and then navigates to cockpit.

- [ ] **Step 6: Extend static tests**

Add tests:

```python
class QtObserverCockpitContractTests(unittest.TestCase):
    def test_cockpit_contains_required_object_names(self) -> None: ...
    def test_perspective_switcher_contains_required_values(self) -> None: ...
    def test_audit_panel_has_required_artifact_entries(self) -> None: ...
    def test_history_view_has_replay_flow_objects(self) -> None: ...
```

- [ ] **Step 7: Run tests and build**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
cmake --build .tmp/qt-observer-build --config Debug
ctest --test-dir .tmp/qt-observer-build --output-on-failure
```

Expected:

- Python tests: `OK`.
- Build exits `0`.
- CTest: `100% tests passed`.

---

## Task 5: Add no-runtime-binding, no-secret, and protocol-only guards

**Files:**

- Modify: `tests/test_qt_observer_static_contract.py`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Add no Python runtime binding test**

Add:

```python
class QtObserverBoundaryTests(unittest.TestCase):
    def test_client_does_not_reference_python_runtime_modules(self) -> None: ...
```

Scan files under `clients/qt_observer` excluding README. Fail if any source/QML file contains:

```text
werewolf_eval
src/werewolf_eval
run_g1h_fake_runtime
observer_server.py
observer_protocol.py
events.jsonl
snapshots/
QProcess
```

Allowed exceptions:

- README may mention G2a protocol and non-goals.
- QML may display user-facing text `snapshots` only as an audit concept, not a local path. The test should scan for `snapshots/` with slash as local path indicator, not the word `snapshots` alone.

- [ ] **Step 2: Add no secret marker test**

Add:

```python
class QtObserverSecretBoundaryTests(unittest.TestCase):
    def test_client_sources_do_not_contain_secret_markers(self) -> None: ...
```

Fail on:

```text
Authorization:
Bearer 
DEEPSEEK_API_KEY=
sk-
api_key
api-key
```

Safe references inside the test file itself must be excluded from scan or recorded in review packet as safe test markers.

- [ ] **Step 3: Add protocol endpoint contract test**

Add:

```python
class QtObserverProtocolEndpointTests(unittest.TestCase):
    def test_client_uses_g2a_protocol_endpoint_names(self) -> None: ...
```

Assertions:

- `ObserverApiClient.cpp` contains `/health`.
- Contains `/api/runs`.
- Contains `/stream?perspective=`.
- Contains `/events?perspective=`.
- Contains `/artifacts`.
- Does not contain `file://`.

- [ ] **Step 4: Run boundary tests**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected result:

```text
OK
```

---

## Task 6: Update Qt observer README and manual smoke instructions

**Files:**

- Modify: `clients/qt_observer/README.md`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Update README status**

README must state:

```text
Status: G2b Observer Cockpit MVP
```

It must also state these non-goals:

```text
- no full prompt/profile editor,
- no Web observer client,
- no human-vs-AI UI,
- no multi-provider arena,
- no leaderboard,
- no direct Python runtime binding,
- no local artifact file reads from the Qt client.
```

- [ ] **Step 2: Add local run instructions**

README must include commands:

```powershell
$env:PYTHONPATH='src'; python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .runs
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
```

It must explain that the Qt app connects to:

```text
http://127.0.0.1:8765
```

and can override base URL with:

```text
--observer-base-url http://127.0.0.1:8765
```

- [ ] **Step 3: Add README static test**

Add:

```python
class QtObserverReadmeTests(unittest.TestCase):
    def test_readme_documents_mvp_status_and_non_goals(self) -> None: ...
    def test_readme_documents_local_g2a_server_command(self) -> None: ...
```

- [ ] **Step 4: Run README tests**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected result: `OK`.

---

## Task 7: Manual end-to-end smoke

**Files:**

- Modify: none
- Test: manual smoke evidence only

- [ ] **Step 1: Build Qt app**

Run:

```powershell
Remove-Item -Recurse -Force .tmp/qt-observer-build -ErrorAction SilentlyContinue
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
```

Expected:

- CMake configure exits `0`.
- Build exits `0`.
- Built executable exists under `.tmp/qt-observer-build` or the configured CMake binary output path.

- [ ] **Step 2: Start G2a observer server**

Run in terminal 1:

```powershell
$env:PYTHONPATH='src'; python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .tmp/g2b-observer-runs
```

Expected stdout:

```text
observer_server=started
host=127.0.0.1
port=8765
```

- [ ] **Step 3: Launch Qt app**

Run the built executable with:

```powershell
& .tmp/qt-observer-build/appqt_observer.exe --observer-base-url http://127.0.0.1:8765
```

If the executable path differs on the local kit, record the exact executable path in the review packet.

Expected manual UI result:

```text
Home -> Start New Match -> default 6-player setup -> Preflight -> Start Match -> Live Cockpit -> History / Replay
```

The implementer must record:

```text
MANUAL_QT_SMOKE = PASS
```

only if the flow opens and the app remains responsive without raw JSON being the primary UI. If the GUI cannot be launched in the local environment, record exact environment limitation and still provide build/static/QtTest evidence.

---

## Task 8: Full validation commands

**Files:**

- Modify: `.logs/review/latest/review-packet.md`
- Modify: `.oh-my-harness/tree.md` through tree hook if needed

- [ ] **Step 1: Run Python static contract tests**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected result:

```text
OK
```

Record exact test count.

- [ ] **Step 2: Configure and build Qt client**

Run:

```powershell
Remove-Item -Recurse -Force .tmp/qt-observer-build -ErrorAction SilentlyContinue
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
```

Expected result:

- Configure exits `0`.
- Build exits `0`.

- [ ] **Step 3: Run Qt CTest tests**

Run:

```powershell
ctest --test-dir .tmp/qt-observer-build --output-on-failure
```

Expected result:

```text
100% tests passed
```

- [ ] **Step 4: Run G2a regression tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
```

Expected result:

```text
OK
```

Reason:

```text
G2b depends on G2a protocol. This proves the client work did not modify or break the server protocol contract.
```

- [ ] **Step 5: Compile Python tests**

Run:

```powershell
python -m compileall tests
```

Expected result:

```text
0 failures
```

- [ ] **Step 6: Run diff whitespace check**

Run:

```powershell
git diff --check main...HEAD
```

Expected result:

```text
(no output)
```

- [ ] **Step 7: Run changed files allowlist check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; allowed=set('''clients/qt_observer/CMakeLists.txt
clients/qt_observer/main.cpp
clients/qt_observer/Main.qml
clients/qt_observer/README.md
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/src/ObserverSseParser.h
clients/qt_observer/src/ObserverSseParser.cpp
clients/qt_observer/qml/AppShell.qml
clients/qt_observer/qml/HomeView.qml
clients/qt_observer/qml/MatchSetupView.qml
clients/qt_observer/qml/PreflightView.qml
clients/qt_observer/qml/LiveCockpitView.qml
clients/qt_observer/qml/HistoryView.qml
clients/qt_observer/qml/components/RoleCard.qml
clients/qt_observer/qml/components/EventTimeline.qml
clients/qt_observer/qml/components/PerspectiveSwitcher.qml
clients/qt_observer/qml/components/AuditLinksPanel.qml
clients/qt_observer/qml/components/StatusBadge.qml
clients/qt_observer/tests/tst_observer_sse_parser.cpp
tests/test_qt_observer_static_contract.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md'''.splitlines()); changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p not in allowed]; print('\n'.join(changed)); assert not bad, 'outside allowlist: '+repr(bad)"
```

Expected result:

- Prints only allowed files.
- Exits `0`.

- [ ] **Step 8: Run forbidden-scope check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; forbidden_prefixes=('src/werewolf_eval/','docs/demo/','docs/generated-games/','docs/gold-game/','docs/adr/','.github/','.agents/skills/'); forbidden_exact={'README.md','docs/ROADMAP.md','docs/TASKS.md','docs/PRODUCT_ONE_PAGER.md','tests/test_observer_protocol.py','tests/test_observer_server.py'}; changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p in forbidden_exact or p.startswith(forbidden_prefixes)]; print('\n'.join(bad)); assert not bad, 'forbidden scope changed: '+repr(bad)"
```

Expected result:

```text
(no output)
```

- [ ] **Step 9: Run forbidden pattern scan on added Qt/test lines**

Run:

```powershell
git diff main...HEAD -- clients/qt_observer tests/test_qt_observer_static_contract.py | python -c "import sys; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; markers=['Authorization:', 'Bearer ', 'DEEPSEEK_API_KEY=', 'sk-', 'api_key', 'api-key']; hits=[line for line in added if any(marker in line for marker in markers)]; print('\n'.join(hits)); unsafe=[line for line in hits if 'secret' not in line.lower() and 'marker' not in line.lower() and 'scan' not in line.lower() and 'forbidden' not in line.lower()]; assert not unsafe, 'unsafe forbidden pattern hits: '+repr(unsafe)"
```

Expected result:

- No unsafe committed secret values.
- Safe literal markers inside secret-scan tests may print and must be listed in the review packet as safe test fixtures.

- [ ] **Step 10: Run dependency/import diff check**

Run:

```powershell
git diff --name-only main...HEAD -- package.json package-lock.json pyproject.toml requirements.txt poetry.lock pnpm-lock.yaml yarn.lock uv.lock CMakeLists.txt src/werewolf_eval
```

Expected result:

```text
(no output)
```

Also run:

```powershell
git diff main...HEAD -- clients/qt_observer tests/test_qt_observer_static_contract.py | python -c "import sys,re; data=sys.stdin.read(); risky=[line for line in data.splitlines() if line.startswith('+') and re.search(r'(QProcess|werewolf_eval|src/werewolf_eval|run_g1h_fake_runtime|observer_server\.py|observer_protocol\.py|file://|requests|httpx|fastapi|flask|openai|anthropic|PySide6|PyQt6)', line)]; print('\n'.join(risky)); unsafe=[line for line in risky if 'README.md' not in line and 'non-goal' not in line.lower() and 'forbidden' not in line.lower() and 'scan' not in line.lower()]; assert not unsafe, 'unexpected runtime binding or dependency reference: '+repr(unsafe)"
```

Expected result:

```text
(no output)
```

- [ ] **Step 11: Verify no build/runtime artifacts are staged**

Run:

```powershell
git diff --name-only --cached | python -c "import sys; bad=[p.strip() for p in sys.stdin if p.strip().startswith('.tmp/') or p.strip().startswith('.runs/') or '/build/' in p.strip() or p.strip().endswith('.user')]; assert not bad, 'staged build/runtime artifacts: '+repr(bad); print('NO_STAGED_BUILD_OR_RUNTIME_ARTIFACTS')"
```

Expected result:

```text
NO_STAGED_BUILD_OR_RUNTIME_ARTIFACTS
```

- [ ] **Step 12: Refresh tree for new files**

Run:

```powershell
node .codex/hooks/tree.mjs --force
```

Expected result:

- `.oh-my-harness/tree.md` includes `ObserverApiClient`, `ObserverSseParser`, `LiveCockpitView.qml`, `HistoryView.qml`, and `test_qt_observer_static_contract.py` by filename.
- It must not include `.tmp/`, `.runs/`, build directories, or Qt Creator `.user` files.

---

## Acceptance Criteria

A1. Qt app builds successfully with Qt 6.8+ and CMake.

A2. Qt app no longer displays the default Hello World window.

A3. Home/Lobby screen exists with server status, Start New Match, History, and recent-runs affordance.

A4. Start New Match flow shows default 6-player AI-vs-AI setup with six visual role/player cards.

A5. Preflight screen exists and displays server health, default template, visibility boundary, and Start Match action.

A6. Start Match uses G2a `POST /api/runs` with `template = default_6p_fake`; it does not start Python runtime directly.

A7. Live Cockpit screen exists with run status, player cards, event timeline, perspective switcher, provider/failure summary, and audit links panel.

A8. History screen lists runs from G2a and can open a run into the same cockpit/replay surface.

A9. `ObserverApiClient` uses Qt Network and G2a REST/SSE endpoints only.

A10. SSE parser handles runtime event frames, run status frames, chunk boundaries, and unknown lines without crashing.

A11. Perspective switcher includes `god`, `public`, `role:p1`-`role:p6`, and `team:werewolf`, and the client passes perspective to G2a endpoints rather than filtering raw files.

A12. Qt client does not reference `werewolf_eval`, Python runtime modules, local `events.jsonl`, local `snapshots/` paths, or `QProcess`.

A13. Qt client does not contain API keys, bearer tokens, authorization headers, or secret markers.

A14. Qt client README documents G2b MVP status, build/run instructions, G2a dependency, and non-goals.

A15. G2b does not modify G2a server/protocol, runtime, provider, scoring, validators, generated fixtures, demo HTML, route docs, or dependency manifests outside the Qt client CMake file.

A16. Static tests, Qt build, Qt CTest, G2a regression tests, compileall tests, diff check, allowlist check, forbidden-scope check, forbidden-pattern check, dependency/import check, and build-artifact staging check pass or are documented with exact environment failure evidence.

A17. `.logs/review/latest/review-packet.md` exists, is compact, and contains the machine-generated evidence required below.

---

## Review Packet Requirements

After implementation, create or update:

```text
.logs/review/latest/review-packet.md
```

The packet must be compact and must not rely on oral summaries. Keep the packet at or under 300 lines; if impossible, mark `PACKET_TOO_LARGE = YES` and provide B档 file ranges. It must include these sections in this order.

### 1. Metadata

Include:

```markdown
# Review Packet — G2b Qt Observer Cockpit MVP

- Plan: `docs/harness/plans/2026-06-03--g2b-qt-observer-cockpit-mvp-plan.md`
- Implementer: <name or agent id from local context>
- Date: <YYYY-MM-DD>
- Branch: <branch name>
- Base: `main`
- PR: <PR number or `not-opened`>
- Verdict target: G2b Qt Observer MVP only
```

### 2. Changed Files

Include command and exact output:

```powershell
git diff --name-only main...HEAD
```

### 3. Diff Stat

Include command and exact output:

```powershell
git diff --stat main...HEAD
```

### 4. Diff Check

Include:

```powershell
git diff --check main...HEAD
```

For pass, record `DIFF_CHECK = PASS`.

### 5. Allowed Files Check

Include Task 8 Step 7 command and exact result. For pass, record `ALLOWLIST_CHECK = PASS`.

### 6. Forbidden Patterns Check

Include Task 8 Step 9 command and exact result. For pass, record `FORBIDDEN_PATTERN_CHECK = PASS`. If safe test fixture markers print, list them under `SAFE_TEST_MARKER_HITS`.

### 7. Dependency / Import Diff

Include both Task 8 Step 10 commands and exact result. For pass, record:

```text
DEPENDENCY_DIFF_CHECK = PASS
RUNTIME_BINDING_CHECK = PASS
```

### 8. Test Summary

Include each command and exact observed summary:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
ctest --test-dir .tmp/qt-observer-build --output-on-failure
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
python -m compileall tests
```

For each, include `exit_code` and exact pass/fail summary. If Qt GUI manual smoke cannot run due to headless environment, state the exact limitation and include build/CTest/static evidence.

### 9. Key Hunks

Include concise excerpts, not full diffs, for:

- `ObserverApiClient` endpoint construction and no-file protocol usage,
- `ObserverSseParser` frame parsing,
- `main.cpp` `--observer-base-url` handling and QML context wiring,
- `Main.qml` replacing Hello World with application shell,
- Home/Setup/Preflight navigation QML,
- Live Cockpit QML with event timeline, perspective switcher, audit links,
- History/replay QML flow,
- static tests proving no runtime binding and no secret markers,
- QtTest proving SSE parser behavior.

Each excerpt must include file path and line range after implementation.

### 10. Evidence Map

Include a Markdown table with exactly these columns:

```markdown
| Acceptance | Evidence | Status |
|------------|----------|--------|
| A1 | `cmake --build` result; `ctest` result | PASS |
```

Every A1-A17 item must have one row. Evidence must point to a test name, command result, manual smoke result, or key hunk line range.

### 11. Acceptance Checklist

Include checklist form for A1-A17. Each item must include an evidence pointer.

Example:

```markdown
- [x] A6 Start Match uses G2a POST only — `ObserverApiClient.cpp:Lx-Ly`; `QtObserverProtocolEndpointTests.test_client_uses_g2a_protocol_endpoint_names`
```

### 12. Implementer Risk Notes

Include:

```markdown
## Implementer Risk Notes

- G2b consumes G2a REST/SSE only; it does not import or shell out to Python runtime internals.
- Qt client uses Qt Network, Quick, Quick Controls, and Qt Test only.
- Role cards are visual/default-template presentation only; full seat/prompt editing remains G2d.
- Perspective selection is passed to G2a endpoints; G2b does not implement independent hidden-information filtering.
- Manual GUI smoke may depend on local Qt desktop availability; build and CTest are still required.
- No Web client, human-vs-AI UI, arena, leaderboard, scoring, provider, validator, or G2a server changes are included.
```

### 13. Review Trigger Result

Include:

```text
PACKET_TOO_LARGE = YES|NO
POTENTIAL_CODEX_B_DEEP_REVIEW_TRIGGER = YES|NO
CHANGED_FILES_COUNT = N
CHANGED_LINES = +A/-D
B_DEEP_REVIEW_RANGES = <ranges or none>
```

Set `POTENTIAL_CODEX_B_DEEP_REVIEW_TRIGGER = YES` if any trigger below occurs.

---

## Potential Codex B档 Deep Review Triggers

The implementation may trigger B档 deeper review if any of these happen:

- `git diff --stat main...HEAD` exceeds 25 changed files or 900 changed lines.
- `ObserverApiClient.cpp` grows beyond 450 lines.
- QML view files together exceed 800 added lines.
- Any change touches forbidden scope such as `src/werewolf_eval/**`, G2a server tests, ROADMAP/TASKS, generated fixtures, demo HTML, provider/scoring/validator code, or dependency manifests outside Qt CMake.
- Any client source uses `QProcess`, local file reads for run artifacts, `werewolf_eval`, `events.jsonl`, or `snapshots/` local paths.
- Any client source contains secret markers or provider API credential handling.
- Any client implements hidden-information filtering from raw artifacts instead of using G2a perspective endpoints.
- Qt build or CTest fails without exact environment limitation and passing static tests.
- Review packet lacks Metadata, Evidence Map, Review Trigger Result, key hunk excerpts, or acceptance evidence pointers.

If triggered, the review packet must name explicit files and line ranges for B档 review.

---

## Implementation PR Description Draft

Title:

```text
feat: add G2b Qt observer cockpit MVP
```

Body:

```markdown
## Summary

- Turns `clients/qt_observer` from Qt6 Quick scaffold into a first observer cockpit MVP.
- Adds a Qt Network protocol adapter for G2a REST/SSE endpoints.
- Adds Home, default match setup, preflight, live cockpit, history/replay, role cards, event timeline, perspective switcher, and audit links panel.
- Adds QtTest coverage for SSE parsing and Python static contract tests for UI/protocol boundaries.

## Scope

- G2b Qt/QML rich client only.
- Consumes G2a client-agnostic protocol; no direct Python runtime binding.
- No G2a server changes, no provider/scoring/validator changes, no Web UI, no prompt/profile editor, no arena, no leaderboard.

## Validation

- `python -m unittest tests.test_qt_observer_static_contract -v`
- `cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug`
- `cmake --build .tmp/qt-observer-build --config Debug`
- `ctest --test-dir .tmp/qt-observer-build --output-on-failure`
- `$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v`
- `python -m compileall tests`
- `git diff --check main...HEAD`
- allowlist / forbidden-scope / forbidden-pattern / dependency/import checks recorded in `.logs/review/latest/review-packet.md`

## Review Packet

`.logs/review/latest/review-packet.md` contains Metadata, machine-generated evidence, key hunk excerpts, Evidence Map, acceptance checklist pointers, implementer risk notes, and Review Trigger Result.
```

---

## Execution Handoff

Implementation should proceed task-by-task in order:

1. C++ protocol adapter and SSE parser.
2. QML shell and navigation.
3. Game-like Home / Setup / Preflight UI.
4. Live Cockpit and History / Replay UI.
5. Boundary/static tests for no runtime binding and no secret markers.
6. Qt observer README update.
7. Manual end-to-end smoke.
8. Full validation and review packet.

Do not modify G2a server/protocol code. Do not build Web UI. Do not implement a prompt editor. Do not read local runtime artifacts directly from Qt. Do not treat this as G2c/G2d/G3/G4 completion.
