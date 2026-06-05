# Review Packet — G3-2 Qt Live/Fake Toggle (capabilities endpoint, honest HUD)

## Metadata
- **Branch:** `feat/g3-2-qt-live-toggle`  •  **Base:** `main`
- **Date:** 2026-06-05  •  **Author:** liaoszong
- **Spec:** `docs/superpowers/specs/2026-06-05-g3-2-qt-live-toggle-design.md`
- **Plan:** `docs/harness/plans/2026-06-05--g3-2-qt-live-toggle-plan.md`
- **Scope:** bring G3-1's server-side live capability onto the Qt cockpit user path —
  read-only `GET /api/runtime/capabilities`, a `mode=live` profile launch, an honest HUD
  data-source chip driven by run-detail `execution_mode`, verbatim gate-error surfacing.
  Fake stays the unconditional default; the Qt client never holds/handles a key.
- **Implementation commits (TDD, one per task):**
  - `f3ea636` feat(g3-2): build_runtime_capabilities protocol helper (g3.runtime_capabilities.v1)
  - `3c4cbc9` feat(g3-2): GET /api/runtime/capabilities (read-only live posture)
  - `877e961` feat(g3-2): surface execution_mode in run detail (API-mediated HUD truth)
  - `289615c` feat(g3-2): ObserverApiClient mode param + runtime capabilities + execution-mode
  - `2de1651` feat(g3-2): ModeControl arming FSM + DataSourceChip HUD + MatchSetup/AppShell wiring
  - `f6ece92` docs(g3-2): README live toggle + boundary reaffirmation; secret/boundary regression green
  - `8c9eb91` test(g3-2): pin C1-bis reset per-trigger + C2 resolvedMode + C3 disarm wiring (review)
- Docs (already on branch): `1f50571` spec, `6b5ef3c` plan, `c3be5c9` plan-review round 1.

## Changed files & diff stat (`main...HEAD`, implementation only)
```
 src/werewolf_eval/observer_protocol.py             |  36 +   (build_runtime_capabilities + schema ver)
 src/werewolf_eval/observer_server.py               |  61 +-  (capabilities route + _read_execution_mode)
 tests/test_observer_protocol.py                    |  96 +
 tests/test_observer_server.py                      | 144 +
 clients/qt_observer/src/ObserverApiClient.h        |  33 +-
 clients/qt_observer/src/ObserverApiClient.cpp      |  92 +-
 clients/qt_observer/qml/MatchSetupView.qml         |  57 +-  (banner -> ModeControl + wiring)
 clients/qt_observer/qml/AppShell.qml               |   9 +   (DataSourceChip in top bar)
 clients/qt_observer/qml/components/ModeControl.qml | 151 +   (new)
 clients/qt_observer/qml/components/DataSourceChip.qml | 51 + (new)
 clients/qt_observer/CMakeLists.txt                 |   2 +   (register both components)
 clients/qt_observer/README.md                      |  11 +   (live toggle + boundary reaffirmation)
 tests/test_qt_observer_static_contract.py          | 144 +-  (+ review hardening)
```
`compileall src tests` → clean.

## Allowlist conformance
- Every changed file is in the plan Allowlist. **PASS**
- **Forbidden scope untouched** (`git diff --name-only main...HEAD`): no edits to G3-1 gate
  logic (`_check_live_capability`/`_check_live_profile_shape` reused verbatim), no
  `deepseek_provider.py` / `provider_agent.py` / consensus runner / `game_engine.py`; no API-key
  UI; no new artifact-read endpoint; no `docs/ROADMAP|TASKS|adr`; no new deps; no Web client. **PASS**

## A1 — `GET /api/runtime/capabilities` (read-only; reuses `_check_live_capability`)
Localhost HTTP is env-blocked (`RemoteDisconnected`), so the read-only endpoint is proven
**offline** by feeding a real `ObserverServerState` through the pure derivation helper
`_build_capabilities_payload`, exactly as the G3-1 gate matrix is proven via `_check_live_capability`.
The live-socket GET variant is env-blocked and intentionally not exercised.

| Posture | `enabled` | `available` | `reason_code` | == launch-time 403 code | Test |
|---|---|---|---|---|---|
| flag off | false | false | `live_api_disabled` | yes | `RuntimeCapabilitiesEndpointTests.test_disabled_posture_reason_matches_launch_403` |
| flag on, no key | true | false | `missing_api_key` | yes | `...test_flag_on_no_key_posture_reason_matches_launch_403` |
| flag on + launcher | true | true | (omitted) | gate proceeds | `...test_available_posture_proceeds_with_no_reason` |

- Posture derives ONLY from `_check_live_capability(state,"live")` (None ⇒ available; tuple ⇒
  `(status, reason_code, message)`), so the capabilities `reason_code` is identical to the
  launch-time 403 code. `default_mode` is hard-coded `"fake"`. Read-only: no writes, no provider call.
- Pure helper unit tests: `RuntimeCapabilitiesTests` (available / disabled / flag-on-no-key /
  available-ignores-stray-reason / no-secret).
- **No secret:** every posture's JSON contains none of `Authorization`/`Bearer `/`DEEPSEEK_API_KEY`/`sk-`
  (`RuntimeCapabilitiesTests.test_no_secret_markers_in_any_posture`,
  `RuntimeCapabilitiesEndpointTests.test_payload_carries_no_secret_in_any_posture`). The key-free
  canonical reason `missing_api_key` legitimately appears (it must equal the 403 code) — the
  `api_key` substring ban is a *client-source* contract, not a payload contract (mirrors the
  existing `ObserverServerSecretScanTests` markers).

## A2 — `execution_mode` in run detail (server reads its OWN artifact; Qt does zero file I/O)
- `_run_detail_with_reason` attaches `execution_mode` via `_read_execution_mode(run_dir)`, which
  reads the run's own `resolved-profile.json` (guards JSON/OS errors; returns None on missing/corrupt/
  non-string → chip falls back to `SYS: SIMULATION`). Never raises, never exposes a path.
- Tests `RunDetailExecutionModeTests`: live→`"live"`, fake→`"fake"`, no-artifact→omitted,
  non-string(123)→omitted, corrupt-JSON→tolerated+detail still builds, coexists-with-reason.
- **Qt reads no artifact files:** `QtObserverBoundaryTests` + `test_qt_client_does_not_use_local_snapshot_or_event_paths`
  confirm no `QFile`/`QDir`/`file://`/`resolved-profile.json`/`events.jsonl`/`snapshots/` in any
  client `.cpp/.h/.qml`. Direct grep over `clients/qt_observer/src|qml` → **NONE**.

## C1–C4 hard-constraint evidence
| # | Constraint | Implementation | Pinning test |
|---|---|---|---|
| **C1** | `currentExecutionMode` set ONLY from run-detail `execution_mode` (never intent/202 echo) | `openRun` parses `execution_mode` (isString && !empty); `launchFromProfile` never touches it | `test_current_execution_mode_parsed_from_run_detail`, `test_launch_handler_never_sets_execution_mode` (slices launchFromProfile body) |
| **C1-bis** | reset to `""` on run change / missing-string field / detail+capabilities error | `setCurrentRunId` (run change) + `openRun` (error/malformed/else) + `refreshCapabilities` (error) all call `resetExecutionMode()` (`m_currentExecutionMode.clear()`) | `test_stale_guard_reset_wired_to_every_c1bis_trigger` (per-site, mutation-verified: deleting the setCurrentRunId reset turns it red) |
| **C2** | QML passes explicit mode; `live` only in `live_confirmed`; no C++ default arg | `launchFromProfile(profile, mode)` no default; `body["mode"]=mode`; `resolvedMode = state==="live_confirmed" ? "live" : "fake"`; view passes `setupModeControl.resolvedMode` | `test_launch_from_profile_takes_mode_and_writes_body_mode`, `test_mode_control_resolved_mode_maps_only_confirmed_to_live`, `test_setup_is_profile_driven` (regex `launchFromProfile(..., \w+.resolvedMode)`) |
| **C3** | `resetToFake()` single disarm; parent calls it on profile/loadedProfile/seat change + `liveAvailable→false`; never mutates FSM state | `ModeControl.resetToFake()`; MatchSetupView calls it from `onSelectedSeatIdChanged`, `onLoadedProfileChanged`, `onActivated`, `onCapabilitiesChanged`(!liveAvailable). FSM tokens `fake`/`live_armed`/`live_confirmed` | `test_mode_control_declares_canonical_fsm_tokens`, `test_setup_is_profile_driven` (4 disarm sites pinned) |
| **C4** | `unreachable` is the ONLY client-owned code; server codes data-driven (verbatim) | capabilities error → `liveReasonCode="unreachable"`; success reads `reason_code`/`message` from JSON; ModeControl renders `liveReasonCode` as a property ref | `test_no_server_reason_codes_are_client_literals` (.h+.cpp), `test_mode_control_renders_reason_code_data_driven`, `test_capabilities_error_uses_client_only_unreachable_code` |

Direct grep: server reason codes (`live_api_disabled`/`missing_api_key`/`unsupported_live_provider`/
`mixed_models`/`provider_failure`/`budget_exhausted`) in client `src|qml` → **NONE** (C4). `unreachable`
present only in `ObserverApiClient.cpp` (1 literal + comments).

## A3–A6 — toggle behavior, HUD, gate errors
- **A3 (launch mode rule):** `mode="live"` sent only in `live_confirmed`; `fake`/`live_armed` → fake;
  omitted ⇒ fake server-side; template launches stay fake (parser rejects `template`+`live`).
- **A4 (arming FSM):** two-click `fake → live_armed → live_confirmed`; LIVE disabled +
  `UNAVAIL · <reason_code>` when `!liveAvailable`; pulsing GlowDot at `live_confirmed`. Fake default.
- **A5 (HUD truth):** `DataSourceChip` shows `SYS: LIVE_API` iff `mode==="live"` (from
  `currentExecutionMode`), else conservative `SYS: SIMULATION`; resets so a prior live run can't
  leave a stale LIVE (C1-bis). Amber "Deterministic Mock" banner removed.
- **A6 (gate errors verbatim):** unavailable + gate errors render server `reason_code`/`message`
  verbatim; `unreachable` is the only client-owned code.

## A7 — Secret/boundary + offline suite
- **Secret-scan:** `QtObserverSecretBoundaryTests` (no `Authorization:`/`Bearer `/`DEEPSEEK_API_KEY=`/
  `sk-`/`api_key`/`api-key` in any `.cpp/.h/.qml`) green; the `api_key`-bearing reason
  (`missing_api_key`) lives only in server payloads, never a client literal (C4).
- **No file I/O / no key UI:** boundary + no-snapshot/event-path tests green; no API-key input or
  displayed string anywhere.
- **Full offline suite** `python -m unittest discover -s tests -p "test_*.py"`:
  **516 ran, 1 failure, 47 errors, 1 skipped.**
  - 47 errors = ALL `test_observer_server` **HTTP-socket** classes (env-blocked `RemoteDisconnected`);
    the new G3-2 offline classes (`RuntimeCapabilitiesEndpointTests`, `RunDetailExecutionModeTests`)
    are NOT among them.
  - 1 failure = pre-existing unrelated `test_context_budget.ContextBudgetGateDocsTests` (AGENTS.md docs gate).
  - 1 skipped = G3-1 gated live smoke (never reads the key).
  - +27 tests vs. G3-1's 489 baseline (5+4+6+8+4 new), all green.

## Qt build / ctest / runtime (on F:, Qt 6.10.0 mingw)
- `cmake -S clients/qt_observer -B .tmp/qt-observer-build` → configure OK (both new QML files registered).
- `cmake --build ... --target appqt_observer` → **exit 0**; `ModeControl_qml`/`DataSourceChip_qml`
  AOT-compiled by `qmlcachegen` (⇒ all QML syntactically valid, incl. the `state`-property FSM); the
  C++ `ObserverApiClient` changes compiled and linked.
- `ctest --test-dir .tmp/qt-observer-build` → **1/1 passed** (SSE parser).
- `qmllint` on the changed QML → no `Error:` lines (only ignorable `[unqualified]`/`[missing-property]`).
- **Runtime:** ran the GUI (exit 0) with a temp screenshot harness (since removed): the top-bar
  `DataSourceChip` renders `环境：离线模拟` (SYS: SIMULATION) and the `ModeControl` renders the
  segmented `[确定性 | 禁用·]` with DETERMINISTIC selected and LIVE disabled (no server →
  `liveAvailable=false`, reason data-driven). Amber banner gone; layout balanced, on-palette.

## Adversarial review (workflow `wf_29a74582-f04`)
5 review dimensions (constraints / correctness / security / reuse-plan / tests), each finding
independently verified by a refute-by-default agent (11 agents, ~580k tokens, 172 tool uses).
**6 findings, 1 confirmed, 5 refuted.**
- **Confirmed (fixed, `8c9eb91`):** the C1-bis stale-guard test was a single global-OR over the whole
  `.cpp` — it proved a reset literal existed somewhere but not that the reset is wired to each trigger;
  a regression dropping `resetExecutionMode()` from `setCurrentRunId` (the spec's worst-case
  live→fake stale-LIVE flash) would have stayed green. Hardened to per-site pins (+C2 ternary, +C3
  4-trigger wiring) and **mutation-verified**. Production code unchanged (it was already correct).
- **Refuted (5):** all test-hardening suggestions where production code is correct and the constraint
  is pinned elsewhere or structurally guaranteed (e.g. cross-run reset via `setCurrentRunId`; non-string
  `execution_mode` → `""` → SIMULATION; run detail carries only `execution_mode`, not the 202 `mode`
  echo). Two of these (C2/C3 presence-only) overlapped the confirmed theme and were folded into the fix.

## Env-deferred (not blockers)
- **Optional QtTest** `tst_observer_api_client_mode.cpp` (plan T4 Step 3) not added: the Qt toolchain
  builds on F: but adding an uncompilable-in-session C++ test risks the owner's ctest; the offline
  static-contract suite + the successful F: build/ctest are the authoritative gates this slice.

## Acceptance summary
A1 ✅ · A2 ✅ · A3 ✅ · A4 ✅ · A5 ✅ · A6 ✅ · A7 ✅ — all met offline; Qt validated on F: (build exit 0,
ctest 1/1, qmllint clean, runtime render confirmed). Default suite stays offline; the Qt client never
holds a key.
