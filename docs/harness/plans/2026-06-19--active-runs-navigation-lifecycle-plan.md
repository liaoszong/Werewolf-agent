# Active Runs Navigation Lifecycle Plan

Date: 2026-06-19

## Goal

Implement active-runs navigation and explicit interrupt lifecycle for the Qt observer client and local observer server.

## Product Semantics

- Leaving Theater only navigates away; it never stops, deletes, or interrupts a run.
- `queued` and `running` are active runs. Active runs can be observed and cannot be deleted.
- Interrupt is an explicit danger action with confirmation. It marks an active run `interrupted`, records metadata, prevents settlement/report presentation, and allows deletion.
- `status` is lifecycle truth. Report availability is a separate capability.
- Completed runs without a report remain `completed` and show report unavailable.
- Stale durable `queued` or `running` runs discovered after server restart become `interrupted` with `server_restart_stale`.
- The one-click launcher interrupts active runs only for the server process it started. Reused external servers are not auto-interrupted.

## Allowed Files

- `src/werewolf_eval/observer_protocol.py`
- `src/werewolf_eval/observer/run_manager.py`
- `src/werewolf_eval/observer/handler.py`
- `launch-theater.py`
- `README.md`
- `clients/qt_observer/src/ObserverApiClient.h`
- `clients/qt_observer/src/ObserverApiClient.cpp`
- `clients/qt_observer/qml/HomeView.qml`
- `clients/qt_observer/qml/TheaterView.qml`
- `clients/qt_observer/qml/HistoryView.qml`
- `clients/qt_observer/qml/components/CockpitSurface.qml`
- Focused tests under `tests/` and `clients/qt_observer/tests/` when needed for the above contracts.

## Forbidden Scope

Do not modify scoring, provider implementations, validators, generated fixtures, historical demo/gold-game artifacts, ADRs, GitHub workflows, or unrelated docs.

## Implementation Steps

1. Extend run summaries/details with status metadata and report availability without forcing settlement generation.
2. Record interrupt metadata (`interrupted_at`, `interrupted_source`, `status_reason`) for user, launcher shutdown, and server restart stale cleanup.
3. Make launcher shutdown ownership-aware: only interrupt active runs when this launcher started the server.
4. Expose enough Qt client data for Home, Theater, and History to render active runs and report availability from REST data.
5. Convert Home's placeholder panels into an active-runs hub backed by `ObserverClient.runItems`; preview events follow the selected active run without multi-run SSE merging.
6. Add Theater return-home semantics, explicit interrupt confirmation, and interrupted terminal state.
7. Update History status/actions so active runs continue observing, interrupted/failed are deletable, and completed-without-report is not mislabeled.
8. Verify with focused Python tests, Qt static contract, Qt build, CTest, qmllint, and screenshot self-check when environment allows.

## Validation

- `git diff --stat`
- `git diff --name-only`
- Allowlist and forbidden-scope check.
- Focused Python tests for observer protocol/server lifecycle.
- Full unittest discover if feasible.
- Qt target build and QML validation per `verifying-qt-observer-ui`.
- Screenshot self-check for changed QML views if Qt runtime is available.
