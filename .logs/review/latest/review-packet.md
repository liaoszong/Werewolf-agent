# Review Packet — G2b Qt Observer Cockpit MVP

**Plan:** `2026-06-03--g2b-qt-observer-cockpit-mvp-plan`
**Branch:** main (direct implementation)
**Base:** `e242b07`
**Date:** 2026-06-03

---

## git diff --name-only

```
.oh-my-harness/tree.md
clients/qt_observer/CMakeLists.txt
clients/qt_observer/Main.qml
clients/qt_observer/README.md
clients/qt_observer/main.cpp
clients/qt_observer/qml/AppShell.qml          (new)
clients/qt_observer/qml/HomeView.qml           (new)
clients/qt_observer/qml/HistoryView.qml        (new)
clients/qt_observer/qml/LiveCockpitView.qml    (new)
clients/qt_observer/qml/MatchSetupView.qml     (new)
clients/qt_observer/qml/PreflightView.qml      (new)
clients/qt_observer/qml/components/AuditLinksPanel.qml (new)
clients/qt_observer/qml/components/EventTimeline.qml   (new)
clients/qt_observer/qml/components/PerspectiveSwitcher.qml (new)
clients/qt_observer/qml/components/RoleCard.qml      (new)
clients/qt_observer/qml/components/StatusBadge.qml   (new)
clients/qt_observer/src/ObserverApiClient.cpp  (new)
clients/qt_observer/src/ObserverApiClient.h    (new)
clients/qt_observer/src/ObserverSseParser.cpp  (new)
clients/qt_observer/src/ObserverSseParser.h    (new)
clients/qt_observer/tests/tst_observer_sse_parser.cpp (new)
tests/test_qt_observer_static_contract.py      (new)
```

## git diff --stat

```
 .oh-my-harness/tree.md             |  26 ++-
 clients/qt_observer/CMakeLists.txt |  43 +++-
 clients/qt_observer/Main.qml       |  19 +-
 clients/qt_observer/README.md      |  69 ++++--
 clients/qt_observer/main.cpp       |  23 +-
 (+ 17 new files)
```

## git diff --check

PASS — only expected CRLF warnings on Windows.

## Changed Files Allowlist Check

All changed/added files:

| File | In Allowlist? |
|------|--------------|
| `.oh-my-harness/tree.md` | YES (auto-generated) |
| `clients/qt_observer/**` | YES |
| `tests/test_qt_observer_static_contract.py` | YES |

No files outside plan allowlist.

## Forbidden Patterns Scan

- `werewolf_eval`, `observer_server.py`, `events.jsonl`, `snapshots/`, `QProcess`: NOT FOUND in qt_observer src/qml
- `Authorization:`, `Bearer`, `DEEPSEEK_API_KEY=`, `sk-`, `api_key`, `api-key`: NOT FOUND (marked as safe test markers in test file)
- `file://`: NOT FOUND
- No `promptEditor`/`PromptEditor` in QML

WARN: `api_key` appears in `test_qt_observer_static_contract.py` line `FORBIDDEN_SECRET_PATTERNS` — SAFE (test fixtures, not secrets)

## Dependency/Import Diff Check

- No Python dependency files changed (package.json, requirements.txt, etc.)
- No Python runtime imports in Qt client
- No `QProcess`, `openai`, `anthropic`, `PySide6`, `PyQt6` imports
- Uses Qt6::Quick Qt6::QuickControls2 Qt6::Network Qt6::Test Qt6::Core only

## Test Commands

### Python static contract tests
```
$ python -m unittest tests.test_qt_observer_static_contract -v
Ran 18 tests in 0.018s — OK
```

### Qt CTest
```
$ ctest --test-dir .tmp/qt-observer-build --output-on-failure
100% tests passed, 0 tests failed out of 1
```

### G2a regression tests
```
$ python -m unittest tests.test_observer_protocol tests.test_observer_server -v
Ran 60 tests in 5.429s — OK
```

### CMake build verification
```
cmake configure: exit 0
cmake build: exit 0
```

## Key Hunks

### ObserverApiClient.h (singleton registration + Q_PROPERTY API)
```cpp
class ObserverApiClient : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString baseUrl READ baseUrl WRITE setBaseUrl NOTIFY baseUrlChanged)
    Q_PROPERTY(bool connected READ connected NOTIFY connectedChanged)
    Q_PROPERTY(QString currentRunId READ currentRunId NOTIFY currentRunChanged)
    ...
```

### ObserverSseParser.cpp (SSE frame parser)
```cpp
QList<ObserverSseMessage> ObserverSseParser::feed(const QByteArray &chunk) {
    m_buffer.append(chunk);
    while (true) {
        int idx = m_buffer.indexOf("\n\n");
        if (idx < 0) break;
        // parse event: and data: lines
        // validate eventName is runtime_event or run_status
        // parse JSON, yield messages
    }
}
```

### main.cpp (singleton registration)
```cpp
qmlRegisterSingletonInstance("qt_observer", 1, 0, "ObserverClient", &observerClient);
```

### CMakeLists.txt (full target state)
```cmake
find_package(Qt6 REQUIRED COMPONENTS Quick QuickControls2 Network Test)
qt_add_qml_module(appqt_observer URI qt_observer VERSION 1.0 QML_FILES Main.qml qml/*.qml ...)
```

## Evidence Map

| Acceptance | Evidence | Status |
|------------|----------|--------|
| A1. Build passes (Qt6+CMake) | cmake build exit 0 | PASS |
| A2. No Hello World | test_main_window_is_not_hello_world | PASS |
| A3. All QML files in CMake | test_cmake_registers_all_qml_files | PASS |
| A4. Singleton via qmlRegisterSingletonInstance | test_main_registers_singleton_via_qmlRegisterSingletonInstance | PASS |
| A5. Home with server status, Start New Match, History | test_navigation_object_names_exist | PASS |
| A6. Setup with default 6-player cards | test_setup_contains_default_six_player_roles | PASS |
| A7. Preflight with health, template, visibility | test_preflight_mentions_visibility_boundary_and_default_template | PASS |
| A8. POST /api/runs, parse run_id | test_client_uses_g2a_protocol_endpoint_names + boundary test | PASS |
| A9. Live Cockpit with status, player cards, timeline, perspective, audit | test_cockpit_contains_required_object_names | PASS |
| A10. History lists runs, can open run to cockpit | test_history_view_has_replay_flow_objects | PASS |
| A11. Perspective switcher has god/public/role:p1-p6/team:werewolf | test_perspective_switcher_contains_required_values | PASS |
| A12. Qt client does not reference werewolf_eval / Python runtime | test_client_does_not_reference_python_runtime_modules (incl. main.cpp) | PASS |
| A13. Qt client does not contain secret markers | test_client_sources_do_not_contain_secret_markers | PASS |
| A14. README documents MVP status + non-goals + run instructions | test_readme_documents_mvp_status_and_non_goals | PASS |
| A15. G2b does not modify G2a server/protocol/other modules | git diff --name-only: only qt_observer + test_qt_observer_static_contract.py + tree.md | PASS |
| A16. Static tests + Qt build + CTest + G2a regression + compileall + diff/allowlist/forbidden checks pass | all commands exit 0 | PASS |
| A17. review-packet.md exists and is compact | this file (196 lines < 300) | PASS |

## Acceptance Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| A1. Qt app builds with Qt 6.8+ and CMake | PASS | cmake build exit 0 |
| A2. No Hello World window | PASS | test_main_window_is_not_hello_world |
| A3. CMakeLists.txt registers every QML file | PASS | test_cmake_registers_all_qml_files |
| A4. Singleton via qmlRegisterSingletonInstance (not setContextProperty) | PASS | test_main_registers_singleton + static check |
| A5. Home with server status, Start New Match, History, recent runs | PASS | test_navigation_object_names_exist |
| A6. Setup with default 6-player cards | PASS | test_setup_contains_default_six_player_roles |
| A7. Preflight with health, template, visibility, Start Match | PASS | test_preflight_mentions_visibility_boundary_and_default_template |
| A8. POST /api/runs, parse run_id, no direct Python runtime | PASS | test_client_uses_g2a_protocol_endpoint_names + boundary test |
| A9. Live Cockpit with status, player cards, timeline, perspective, provider summary, audit | PASS | test_cockpit_contains_required_object_names |
| A10. History lists runs, can open run to cockpit | PASS | test_history_view_has_replay_flow_objects |
| A11. Perspective switcher includes god/public/role:p1-p6/team:werewolf | PASS | test_perspective_switcher_contains_required_values |
| A12. Qt client does not reference werewolf_eval, Python runtime modules, local events.jsonl, snapshots/, or QProcess | PASS | test_client_does_not_reference_python_runtime_modules (incl. main.cpp scan) |
| A13. Qt client does not contain API keys, bearer tokens, authorization headers, or secret markers | PASS | test_client_sources_do_not_contain_secret_markers |
| A14. README documents G2b MVP status, build/run instructions, G2a dependency, and non-goals | PASS | test_readme_documents_mvp_status_and_non_goals |
| A15. G2b does not modify G2a server/protocol, runtime, provider, scoring, validators, etc. | PASS | git diff --name-only: only allowlisted files changed |
| A16. Static tests, Qt build, CTest, G2a regression tests, compileall, diff check, allowlist, forbidden checks pass | PASS | all commands exit 0 |
| A17. review-packet.md exists, is compact (< 300 lines) | PASS | this file: 196 lines |

## Implementer Risk Notes

1. **GUI smoke skipped**: No display server in this environment. Build + static contracts + CTest evidence provided as substitute. Recorded `MANUAL_QT_SMOKE = SKIP`.
2. **SSE streaming untested end-to-end**: SSE parser tested in isolation (CTest); live stream integration requires running observer server. Python G2a regression tests cover the server side.
3. **AuditLinksPanel is read-only**: Links are displayed but currently only log to console (not clickable). Per plan, does not open local files.
4. **Preflight auto-navigates via poller**: Timer-based polling for runId change in PreflightView may race with server latency; acceptable for MVP.

### B档 Fixes Applied

| Fix | Description | File |
|-----|-------------|------|
| EG-2 | Add main.cpp to runtime boundary scan | test_qt_observer_static_contract.py |
| SA-1 | PerspectiveSwitcher iterates over `list` not `model` | PerspectiveSwitcher.qml |
| SA-3 | Strengthen `ignoresMultilineDataFramesInMvp` assertions | tst_observer_sse_parser.cpp |

## Review Trigger Result

- Original B档 review PASS with no blockers; EG/SA items fixed above.
- Build/test evidence: all PASS, no failures.

## Packet Length Check

PACKET_TOO_LARGE = NO
