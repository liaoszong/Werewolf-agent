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
- QML views: Home, Match Setup, Preflight, **Theater** (P2-C-1 default spectator surface), History. The legacy Live Cockpit is retired from navigation; its honesty chain (trust boundary, projection proof, perspective lens, event timeline, audit links) is re-homed into the Theater's bottom Evidence Console.
- QML components: RoleCard, EventTimeline, PerspectiveSwitcher, AuditLinksPanel, StatusBadge, ModeControl, DataSourceChip; P2-C-1 theater: SeatRing, SpeechTheater, EvidenceConsole, PlaybackControls, EventPresentationQueue.

## Live / fake execution toggle (G3-2)

Fake-deterministic execution stays the **unconditional default**. The API key is **never** entered, displayed, or handled by the Qt client.

- **Capabilities before launch.** On the Match Setup page the client reads the server's live posture via a read-only `GET /api/runtime/capabilities` (`g3.runtime_capabilities.v1`) — no "guess, click, get a 403". The endpoint exposes posture only (`enabled` / `available` / a key-free `reason_code` + `message`); it never returns a key, env-var name, header, or base-url secret.
- **Intent vs. truth.** Intent lives in the setup `ModeControl` (a segmented `[DETERMINISTIC | LIVE API]` control with a two-click arming FSM `fake → live_armed → live_confirmed`). Switching profile/seat, clicking DETERMINISTIC, or live becoming unavailable disarms it through a single `resetToFake()`. The launch sends `mode="live"` **only** when fully confirmed; otherwise fake. Only a profile launch can request live — template launches stay fake.
- **Executed truth via the API.** The global `DataSourceChip` HUD shows the run's executed truth (`SYS: LIVE_API` / `SYS: SIMULATION`) sourced **only** from the run-detail `execution_mode` field (the server reads its own `resolved-profile.json`). It is conservative — `SYS: SIMULATION` until run detail returns a mode, never optimistic-live — and resets on run change / missing field / request error so a prior live run can't leave a stale `LIVE` reading. The Qt client performs **no local artifact file reads** (no `QFile`/`QDir`/`file://`/`resolved-profile.json`).
- **Reason codes are server-owned.** Unavailable and gate-error states render the server's `reason_code`/`message` **verbatim** (data-driven). The only client-owned reason code is `unreachable` (transport failure). No API key UI exists anywhere in the client.

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
