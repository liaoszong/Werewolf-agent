# Qt Observer Cockpit

Status: G2b Observer Cockpit MVP

`clients/qt_observer` is the local Qt/QML observer application that connects to the G2a observer server and provides a visual cockpit for monitoring Werewolf games.

## Requirements

- Qt 6.8+ (Quick, QuickControls2, Network, Test modules)
- CMake 3.16+
- C++17 compiler

## Architecture

- `ObserverApiClient` — QML-facing singleton that communicates with the G2a observer server via REST and SSE.
- `ObserverSseParser` — SSE frame parser that handles `runtime_event` and `run_status` event types.
- QML views: Home, Match Setup, Preflight, Live Cockpit, History.
- QML components: RoleCard, EventTimeline, PerspectiveSwitcher, AuditLinksPanel, StatusBadge.

## Non-goals

- the G2d-2 profile setup editor edits server-side profiles only (select/edit/validate/launch a profile) — no local prompt template library, no provider secrets,
- no Web observer client,
- no human-vs-AI UI,
- no multi-provider arena,
- no leaderboard,
- no direct Python runtime binding,
- no local artifact file reads from the Qt client.

## Running locally

### 1. Start the G2a observer server

```powershell
$env:PYTHONPATH='src'; python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .runs
```

### 2. Build the Qt client

```powershell
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
```

### 3. Run the Qt client

The app connects to `http://127.0.0.1:8765` by default.

Override the base URL with:

```powershell
.\tmp\qt-observer-build\appqt_observer.exe --observer-base-url http://127.0.0.1:8765
```

## Running tests

```powershell
ctest --test-dir .tmp/qt-observer-build --output-on-failure
python -m unittest tests.test_qt_observer_static_contract -v
```
