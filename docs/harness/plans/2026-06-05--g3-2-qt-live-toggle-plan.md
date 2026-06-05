# G3-2 Qt Live/Fake Toggle Implementation Plan

> **For agentic workers:** implement task-by-task. Steps use checkbox (`- [ ]`) syntax. **TDD is mandatory** for the Python surfaces: write the failing test, run it red, implement, run it green, commit. The Qt/QML surfaces are validated by the Python **static-contract** suite (offline) plus an optional QtTest build on F:. **No test reads `DEEPSEEK_API_KEY` or opens a real socket; the Qt client never holds/handles a key.**

**Goal:** Bring G3-1's server-side live capability onto the Qt cockpit user path — a `mode=live` profile launch from `MatchSetupView`, a read-only `GET /api/runtime/capabilities` so the client knows live posture *before* launch, an honest HUD data-source chip driven by **server API state** (not local files), and verbatim gate-error surfacing. Fake stays the unconditional default; the key never touches the client.

**Spec:** `docs/superpowers/specs/2026-06-05-g3-2-qt-live-toggle-design.md` (reviewed; decisions locked).

**Tech Stack:** Python stdlib (observer server/protocol) + Qt6/QML (`clients/qt_observer`, builds on F: per `clients/qt_observer/README.md`). No new deps.

---

## Context Basis (verified; executor MUST re-confirm signatures in each task's Step 0)

- **Reuse verbatim (do NOT modify behavior):**
  - `observer_server.py` → `_check_live_capability(state, mode) -> tuple[int,str,str] | None` (None ⇒ available; tuple ⇒ `(status, reason_code, message)` with `reason_code ∈ {live_api_disabled, missing_api_key}`). The capabilities endpoint derives posture **only** from this.
  - `observer_server.py` → `_run_detail_with_reason(self, run_id, run_dir) -> dict` (G3-1; already attaches the key-free `reason`). Extend it to also attach `execution_mode`.
  - `observer_protocol.py` → `build_run_detail`, `DEFAULT_FAKE_MODE = "fake"`, `parse_profile_launch_request` (carries `mode`).
  - `profile_config.py` → `build_resolved_profile_artifact(...)` writes `execution_mode` into `resolved-profile.json` (the server reads its OWN artifact).
- **Extend (this plan's edits):**
  - `observer_protocol.py`: `RUNTIME_CAPABILITIES_SCHEMA_VERSION = "g3.runtime_capabilities.v1"`; pure `build_runtime_capabilities(*, live_enabled, deepseek_available, reason_code=None, message=None) -> dict`.
  - `observer_server.py`: route `GET /api/runtime/capabilities` in `do_GET`; `_run_detail_with_reason` reads `run_dir/resolved-profile.json` and attaches `execution_mode` when present.
  - `ObserverApiClient.h/.cpp`: `launchFromProfile(const QVariantMap&, const QString &mode)`; `Q_INVOKABLE refreshCapabilities()`; properties `liveAvailable`/`liveReasonCode`/`liveReasonMessage`/`defaultMode`/`currentExecutionMode`; parse `execution_mode` in `openRun`.
  - `MatchSetupView.qml`: replace `setupExecutionBanner` with `ModeControl` (objectName `setupModeControl`); wire Launch to `launchFromProfile(profile, resolvedMode)`; call `setupModeControl.resetToFake()` on the disarm triggers.
  - `AppShell.qml`: mount `DataSourceChip` (objectName `dataSourceChip`).
  - New `qml/components/ModeControl.qml`, `qml/components/DataSourceChip.qml`; register both in `CMakeLists.txt`.
- **Test fakes/patterns to reuse:** G3-1's offline gate-helper unit tests (`tests/test_observer_server.py` `LiveGateHelperTests`, in-process handler harness `_InProcessHandler`); `tests/test_qt_observer_static_contract.py` (objectName / boundary / secret-scan assertions).

**Build/verify:**
```bash
PYTHONPATH=src python -m unittest tests.test_observer_protocol tests.test_observer_server tests.test_qt_observer_static_contract -v
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"   # must stay offline; only env-blocked server-socket tests + pre-existing test_context_budget may fail
PYTHONPATH=src python -m compileall src tests
# Qt (on F:, per clients/qt_observer/README.md): cmake -S clients/qt_observer -B <build> && cmake --build <build> && ctest --test-dir <build>
```
> NOTE: localhost HTTP is blocked in this env (`RemoteDisconnected`) → validate capability logic via the pure helper, not server sockets (as in G3-1). The Qt build/ctest runs on F:.

---

## Allowlist
```
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
tests/test_observer_protocol.py
tests/test_observer_server.py
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/MatchSetupView.qml
clients/qt_observer/qml/AppShell.qml
clients/qt_observer/qml/components/ModeControl.qml          (new)
clients/qt_observer/qml/components/DataSourceChip.qml       (new)
clients/qt_observer/CMakeLists.txt
clients/qt_observer/README.md
clients/qt_observer/tests/tst_observer_api_client_mode.cpp  (new, optional QtTest)
clients/qt_observer/tests/CMakeLists.txt                    (only if QtTest added)
tests/test_qt_observer_static_contract.py
docs/superpowers/specs/2026-06-05-g3-2-qt-live-toggle-design.md
docs/harness/plans/2026-06-05--g3-2-qt-live-toggle-plan.md
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

## Forbidden Scope
No edits to G3-1 server gate logic / `deepseek_provider.py` / `provider_agent.py` / consensus runner / `game_engine.py`. **No API-key UI** (never an input, displayed string, or source literal). **No direct Qt artifact file reads** — no `QFile`/`QDir`/`file://`/`resolved-profile.json` path in the client; execution truth arrives only as a run-detail JSON field. No new artifact-read endpoint. No profile save, real smoke, `prompt-manifest.json` model fix, `max_requests` tuning, cost/metering, per-seat live models, template live launch, or Web client. No `docs/ROADMAP.md`/`docs/TASKS.md`/`docs/adr/**` edits.

### Hard constraints (from spec-review round 1 — bind these exactly)
- **C1 — HUD truth, never intent.** `currentExecutionMode` is set **only** from a `/api/runs/{id}` response's `execution_mode`. The client must **not** flip the chip to `SYS: LIVE_API` because the user armed live or because the 202 launch response echoed `mode=live`. Until run detail returns `execution_mode`, the chip shows the conservative `SYS: SIMULATION`.
- **C2 — explicit mode from QML.** QML always calls `launchFromProfile(profile, resolvedMode)` with `resolvedMode ∈ {"fake","live"}` — never relying on a C++ default arg. Default-fake is guaranteed by two layers: `ModeControl` default `state="fake"` **and** the server treating omitted `mode` as fake.
- **C3 — single disarm entry.** `ModeControl` exposes `function resetToFake()`; `MatchSetupView` calls it on profile-changed / loadedProfile-changed / selectedSeatId-changed / `liveAvailable→false`. The parent never mutates `ModeControl.state` directly.
- **C4 — one client-only code.** `unreachable` is the **only** client-owned reason code. `live_api_disabled` / `missing_api_key` / `unsupported_live_provider` / `mixed_models` / `provider_failure` / `budget_exhausted` are server-owned and rendered **data-driven** (verbatim) — never embedded as client source literals (also avoids the `api_key` secret-scan substring).

---

## Task 1 — `build_runtime_capabilities` (protocol helper)

**Files:** `src/werewolf_eval/observer_protocol.py`, `tests/test_observer_protocol.py`

- [ ] **Step 1 (red):** `RuntimeCapabilitiesTests`:
  - available → `{schema_version:"g3.runtime_capabilities.v1", default_mode:"fake", live_api:{enabled:true, providers:{deepseek:{available:true}}}}` (no `reason_code`/`message`).
  - disabled → `enabled:false`, `available:false`, `reason_code:"live_api_disabled"`, `message` set.
  - flag-on-no-key → `enabled:true`, `available:false`, `reason_code:"missing_api_key"`.
  - **no-secret:** the JSON of every posture contains none of `Authorization`/`Bearer `/`DEEPSEEK_API_KEY`/`sk-`/`api_key`.
  Run → fail.
- [ ] **Step 2 (green):** add `RUNTIME_CAPABILITIES_SCHEMA_VERSION` + `build_runtime_capabilities(*, live_enabled, deepseek_available, reason_code=None, message=None)`; `default_mode` hard-coded `"fake"`; include `reason_code`/`message` only when `not deepseek_available`.
- [ ] **Step 3:** Focused green. Commit: `feat(g3-2): build_runtime_capabilities protocol helper (g3.runtime_capabilities.v1)`.

## Task 2 — `GET /api/runtime/capabilities` (server, reuses `_check_live_capability`)

**Files:** `src/werewolf_eval/observer_server.py`, `tests/test_observer_server.py`

- [ ] **Step 0:** Re-read `do_GET` routing + `_check_live_capability`.
- [ ] **Step 1 (red):** add `RuntimeCapabilitiesEndpointTests` driven **offline** (no socket) — a pure helper `_build_capabilities_payload(state)` mapping `_check_live_capability(state,"live")` → `build_runtime_capabilities(...)`. Assert all three postures via real `ObserverServerState` (disabled / `live_enabled=True,live_launcher=None` / `live_enabled=True,live_launcher=<fake>`). Assert the derived `reason_code` equals the launch-time 403 code. Run → fail.
- [ ] **Step 2 (green):** add `_build_capabilities_payload(state)`; route `segments == ["api","runtime","capabilities"]` in `do_GET` → `self._send_json(200, _build_capabilities_payload(self._get_state()))`. Read-only; no writes; no provider call; never returns a secret.
- [ ] **Step 3:** Focused green (document the live-socket variant as env-blocked). Commit: `feat(g3-2): GET /api/runtime/capabilities (read-only live posture)`.

## Task 3 — `execution_mode` in run detail (server reads its own artifact)

**Files:** `src/werewolf_eval/observer_server.py`, `tests/test_observer_server.py`

- [ ] **Step 1 (red):** extend `LiveRunStatusReasonTests` (or a new `RunDetailExecutionModeTests`): write a fixture `resolved-profile.json` (`execution_mode="live"`) into a run_dir → `_run_detail_with_reason(run_id, run_dir)` returns `detail["execution_mode"]=="live"`; with `execution_mode="fake"` → `"fake"`; with **no** artifact → key absent (or null). Run → fail.
- [ ] **Step 2 (green):** in `_run_detail_with_reason`, after building detail, read `run_dir/resolved-profile.json` (its own file; guard JSON/OS errors) and attach `execution_mode` when a string value is present. (Reads server-local file, NOT a secret; never exposes paths.)
- [ ] **Step 3:** Focused green. Commit: `feat(g3-2): surface execution_mode in run detail (API-mediated HUD truth)`.

## Task 4 — `ObserverApiClient`: mode param + capabilities + execution-mode (C1/C2/C4)

**Files:** `clients/qt_observer/src/ObserverApiClient.h/.cpp`, `tests/test_qt_observer_static_contract.py`, (optional) `clients/qt_observer/tests/tst_observer_api_client_mode.cpp`

- [ ] **Step 1 (red):** extend `tests/test_qt_observer_static_contract.py`:
  - `.h` declares properties `liveAvailable`, `liveReasonCode`, `liveReasonMessage`, `defaultMode`, `currentExecutionMode` + `Q_INVOKABLE refreshCapabilities`.
  - `.cpp` references `/api/runtime/capabilities`; `launchFromProfile` takes a `mode` arg and writes `body["mode"]`; sets `liveReasonCode="unreachable"` on capabilities request error; parses `execution_mode` in the run-detail handler; sets `currentExecutionMode` **only** there (assert `mode=="live"` does NOT directly set `currentExecutionMode`).
  - **C4:** assert the client source contains the literal `unreachable` but **none** of `live_api_disabled`/`missing_api_key`/`mixed_models`/`unsupported_live_provider` (data-driven only). Secret-scan stays green (no `api_key`).
  Run → fail.
- [ ] **Step 2 (green):** implement: `launchFromProfile(const QVariantMap&, const QString &mode)` → `body["mode"]=mode`; `refreshCapabilities()` GET `/api/runtime/capabilities` → set properties (on error set `liveAvailable=false`, `liveReasonCode="unreachable"`); in `openRun` parse `execution_mode` → `m_currentExecutionMode` (default `""`). **C1:** never set `m_currentExecutionMode` from intent/202.
- [ ] **Step 3 (optional QtTest):** `tst_observer_api_client_mode.cpp` — body carries `"mode":"live"`; capabilities JSON → properties; `unreachable` on error. Register in `tests/CMakeLists.txt`. (Skip if the QtTest harness can't build in-env; note it.)
- [ ] **Step 4:** Static-contract green. Commit: `feat(g3-2): ObserverApiClient mode param + runtime capabilities + execution-mode (truth via API)`.

## Task 5 — `ModeControl` + `DataSourceChip` + view wiring (C2/C3, FSM)

**Files:** `clients/qt_observer/qml/components/ModeControl.qml` (new), `qml/components/DataSourceChip.qml` (new), `qml/MatchSetupView.qml`, `qml/AppShell.qml`, `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1 (red):** update `test_qt_observer_static_contract.py`:
  - `REQUIRED_QML_VIEWS` + CMake: add `qml/components/ModeControl.qml`, `qml/components/DataSourceChip.qml`.
  - `REQUIRED_OBJECT_NAMES`: MatchSetupView gains `setupModeControl`; **remove** `setupExecutionBanner`; AppShell gains `dataSourceChip`.
  - `test_setup_is_profile_driven`: **remove** the `"Deterministic Mock"` assertion; add that `MatchSetupView` instantiates `ModeControl` and calls `launchFromProfile(` with an explicit mode variable (C2) and calls `resetToFake(` (C3).
  - `ModeControl.qml` contains the literal FSM tokens `"fake"`, `"live_armed"`, `"live_confirmed"` and `function resetToFake(`.
  - `DataSourceChip.qml` contains `SYS: LIVE_API` and `SYS: SIMULATION`.
  - boundary/secret-scan/no-`QFile`/no-`file://` assertions still pass.
  Run → fail.
- [ ] **Step 2 (green):**
  - `ModeControl.qml`: segmented `[DETERMINISTIC | LIVE API]`; `state` ∈ `{"fake","live_armed","live_confirmed"}`; two-click arming; LIVE disabled + `UNAVAIL · <ObserverClient.liveReasonCode>` when `!ObserverClient.liveAvailable`; `function resetToFake(){ state="fake" }`; expose the resolved launch mode (`state==="live_confirmed" ? "live" : "fake"`). Nightfall tokens; monochrome luminance; pulsing GlowDot for live.
  - `DataSourceChip.qml`: `mode` property → `SYS: LIVE_API` (black/white, blink) iff `mode==="live"`, else `SYS: SIMULATION`.
  - `MatchSetupView.qml`: replace `setupExecutionBanner` with `ModeControl{ objectName:"setupModeControl" }`; Launch → `ObserverClient.launchFromProfile(root.editedProfile, setupModeControl.resolvedMode)`; call `setupModeControl.resetToFake()` on profile/loadedProfile/selectedSeatId change and on `ObserverClient.liveAvailable` going false; call `ObserverClient.refreshCapabilities()` on load.
  - `AppShell.qml`: `DataSourceChip{ objectName:"dataSourceChip"; mode: ObserverClient.currentExecutionMode }` in the top bar (next to the language switcher).
  - Register both components in `CMakeLists.txt`.
- [ ] **Step 3:** Static-contract green; Qt build/ctest on F: (document result). Commit: `feat(g3-2): ModeControl arming FSM + DataSourceChip HUD + MatchSetup/AppShell wiring`.

## Task 6 — README + secret/boundary regression

**Files:** `clients/qt_observer/README.md`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1:** README: document the live/fake toggle + capabilities endpoint; reaffirm "no API key UI", "no local artifact file reads", "execution truth via server API". Keep the existing required README phrases green.
- [ ] **Step 2:** confirm `QtObserverSecretBoundaryTests` + `QtObserverBoundaryTests` + `test_qt_client_does_not_use_local_snapshot_or_event_paths` all pass with the new sources (no `api_key` literal, no `QFile`/`QDir`/`file://`). Treat any failure as a real regression.
- [ ] **Step 3:** Commit: `docs(g3-2): README live toggle + boundary reaffirmation; secret/boundary regression green`.

## Task 7 — Validation + review packet + PR

- [ ] **Step 1:** `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` — only the documented env-blocked `test_observer_server.*` (RemoteDisconnected) + pre-existing `test_context_budget` may fail; `compileall` clean. Qt build/ctest on F: (record result; if the toolchain is unavailable in-session, note it for the owner).
- [ ] **Step 2:** secret/forbidden scan over the diff: no key literal, no `api_key`/`sk-`/`Authorization`/`Bearer ` in client sources, no `QFile`/`QDir`/`file://`, no client-embedded server reason codes.
- [ ] **Step 3:** `node .codex/hooks/tree.mjs --force` (new components/tests).
- [ ] **Step 4:** `.logs/review/latest/review-packet.md` (≤300 lines): metadata, changed files, capabilities-endpoint evidence (3 postures, no-secret), run-detail execution_mode evidence, C1–C4 evidence table, secret/boundary-scan, offline-suite confirmation, Qt build/ctest result, acceptance A1–A7.
- [ ] **Step 5:** Commit; push branch; open PR `feat: add G3-2 Qt live/fake toggle (capabilities endpoint, honest HUD)`; merge per owner approval.

---

## Acceptance Criteria (hard — verbatim review checklist)
- **A1** `GET /api/runtime/capabilities` read-only, no secret, reuses `_check_live_capability`; `reason_code` == launch-time 403 code; `default_mode="fake"`. *(T1/T2)*
- **A2** Run detail exposes `execution_mode` read from the server's own `resolved-profile.json`; **Qt reads no artifact files.** *(T3/T4)*
- **A3** QML calls `launchFromProfile` with an **explicit** mode; `mode="live"` sent **only** in `live_confirmed`; omitted/default/template ⇒ fake. *(T4/T5, C2)*
- **A4** `ModeControl` arming FSM (`fake`/`live_armed`/`live_confirmed`) with a single `resetToFake()` disarm entry; fake stays default. *(T5, C3)*
- **A5** `DataSourceChip` shows executed truth **only** from run-detail `execution_mode` (conservative `SYS: SIMULATION` until it returns, never optimistic-live); amber "Deterministic Mock" banner removed. *(T5, C1)*
- **A6** Unavailable + gate-error render server `reason_code`/`message` verbatim; `unreachable` is the only client-owned code; no server-code literals in client source. *(T4/T5, C4)*
- **A7** No key entry/display anywhere; static-contract secret-scan + no-`QFile`/no-`QDir`/no-`file://` + no-Python-runtime contracts green; default Python suite offline & green (env-blocked socket tests excepted). *(T6/T7)*

---

## PR Description Draft
Title: `feat: add G3-2 Qt live/fake toggle (capabilities endpoint, honest HUD)`
- Adds read-only `GET /api/runtime/capabilities` (reuses G3-1 `_check_live_capability`) + `execution_mode` in run detail; Qt gains a fake/live `ModeControl` (two-click arming), a `DataSourceChip` HUD driven by API-mediated executed truth, and verbatim gate-error surfacing. Fake stays default; the key never touches the client.
- Intent (setup control) vs truth (HUD chip from run-detail `execution_mode`); no Qt file I/O; reason codes data-driven.
- Default Python suite offline; Qt static-contract + (F:) ctest.

## Execution Handoff
Order: (1) capabilities helper, (2) capabilities endpoint, (3) run-detail execution_mode, (4) ApiClient mode+capabilities, (5) ModeControl+DataSourceChip+wiring, (6) README+regression, (7) validate+packet+PR. Each task commits. Keep the default suite offline; the Qt client never handles a key; bind C1–C4 exactly.
