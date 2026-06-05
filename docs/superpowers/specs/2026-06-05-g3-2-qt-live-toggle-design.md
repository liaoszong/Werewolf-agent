# G3-2 Qt Live/Fake Toggle — Design Spec

**Status:** draft (for spec review)
**Route:** Phase 3 / G3 experiment route — second slice (`docs/ROADMAP.md` §G3 "Replay + live dual mode"). Consumes G3-1 (server live execution) + G2b/G2c/G2d Qt cockpit.
**Date:** 2026-06-05

---

## 1. Goal

Bring G3-1's server-side live capability onto the **Qt cockpit user path**: let an operator launch a profile in **live** mode from `MatchSetupView`, see — before clicking Launch — whether live is even possible on this server, and read the **honest executed truth** of a run afterward. Fake-deterministic stays the unconditional default; the API key is **never** entered, displayed, or handled by the Qt client.

**Success criteria**
- A read-only `GET /api/runtime/capabilities` lets the client know the server's live posture (enabled / available / why-not) *before* launch — no "guess, click, get 403".
- The Qt client can launch `mode=live` (profile launch only) and otherwise launches `fake`.
- A global **HUD data-source chip** shows the run's *executed truth* (`SYS: LIVE_API` / `SYS: SIMULATION`), sourced from **server API state**, never from local artifact files.
- Gate errors surface the server's canonical `{code, message}` verbatim.
- **Zero key handling in the client**; the static secret-scan contract stays green.

---

## 2. Current state (verified)

- **The Qt client can only launch fake.** `ObserverApiClient::launchFromProfile(profile)` (`ObserverApiClient.cpp:466`) posts `{"profile": …}` with **no `mode`** → the server defaults to fake. `startDefaultMatch()` (`:141`) posts `template=default_6p_fake, mode=fake` — a **template** launch, which G3-1 forbids going live. So live can attach **only** to the profile-launch path in `MatchSetupView`.
- **The launch path already surfaces gate errors.** `launchFromProfile`'s 4xx branch parses `{code,message}` and calls `setError(message)` + `emit launchFailed()` (`:475-495`); it advances **only** on HTTP 202 + a `run_id`. The QML navigates from `onLaunchSucceeded`, never optimistically.
- **The honesty cue is a hard-coded amber banner.** `MatchSetupView.qml` `setupExecutionBanner` (`:101`) is warning-amber and reads "Deterministic Mock — no real API calls". Semantically wrong (fake is the *safe* default, not a caution) and unconditional.
- **Server live posture is unobservable via API.** G3-1 prints `live_api=enabled/enabled_no_key/disabled` to startup stdout only. The two pure helpers `_check_live_capability(state, mode)` (`observer_server.py`) and the run-status reason already exist; there is **no** capability endpoint yet.
- **Client boundary contracts already enforced** (`tests/test_qt_observer_static_contract.py`): no `werewolf_eval`/`QProcess`/`events.jsonl`/`snapshots/` references; **no `file://`/`QFile`/`QDir`**; **secret-scan** over all `.cpp/.h/.qml` for `Authorization:`, `Bearer `, `DEEPSEEK_API_KEY=`, `sk-`, **`api_key`**, `api-key`. README must state "no local artifact file reads".

---

## 3. Architecture

```
Qt MatchSetupView (intent)                         Server (G3-1, unchanged gate logic)
  page load → ObserverClient.refreshCapabilities() ──► GET /api/runtime/capabilities  (READ-ONLY)
       ◄── { default_mode, live_api:{enabled, providers:{deepseek:{available,reason_code?,message?}}} }
  segmented [DETERMINISTIC | LIVE API]
    LIVE disabled + "UNAVAIL · <reason_code>" when !available   (reason_code == the 403 code)
    two-click arming FSM (fake → live_armed → live_confirmed)
  Launch → ObserverClient.launchFromProfile(profile, mode)  ──► POST /api/runs {profile, mode}
       mode = "live" ONLY when state==live_confirmed; else "fake"
       ◄── 202 {run_id, mode, status} | 4xx {code, message}  (gate errors surfaced verbatim)

Global AppShell HUD chip (executed truth)
  on current run → GET /api/runs/{id}  ──► includes "execution_mode" (server reads ITS OWN artifact)
       chip = "SYS: LIVE_API" iff execution_mode=="live", else "SYS: SIMULATION"
       (NO Qt file I/O — truth arrives as a JSON field over the existing API)
```

**Intent vs truth (write verbatim into the implementation):**
> Intent lives in the setup segmented control; executed truth lives in the global HUD chip. The HUD chip must obtain execution truth through observer/server API state, not direct local artifact file I/O. Qt must not read `resolved-profile.json` from disk.

This prevents the dangerous lie where the user picks live, the server fails the gate and runs nothing live, yet the UI still says "LIVE".

**New/changed surfaces**
1. **`observer_protocol.py` (new pure helper):** `build_runtime_capabilities(*, live_enabled, deepseek_available, reason_code=None, message=None) -> dict` producing the `g3.runtime_capabilities.v1` payload; `RUNTIME_CAPABILITIES_SCHEMA_VERSION`. Pure, offline-testable.
2. **`observer_server.py`:** route `GET /api/runtime/capabilities` → derive `(enabled, available, reason_code, message)` by **reusing `_check_live_capability(state, "live")`** (None → available; tuple → `(status, reason_code, message)`); call the protocol helper; send JSON. Also: **surface `execution_mode`** (and `live_api`) in run detail (`build_run_detail` path) by reading the run's own `resolved-profile.json` server-side when present — a JSON field, not a new artifact endpoint.
3. **`ObserverApiClient` (.h/.cpp):** `launchFromProfile(profile, mode)` gains `mode` (`"fake"|"live"`, default `"fake"`); `refreshCapabilities()` + Q_PROPERTYs `liveAvailable`, `liveReasonCode`, `liveReasonMessage`, `defaultMode`; `currentExecutionMode` populated from run-detail `execution_mode`. On capabilities request failure → `liveReasonCode="unreachable"` (client-only code), `liveAvailable=false`.
4. **`qml/components/ModeControl.qml` (new):** the segmented `[DETERMINISTIC | LIVE API]` control + the two-click arming FSM; emits the resolved launch `mode`. Self-contained, isolated, testable.
5. **`qml/components/DataSourceChip.qml` (new):** the HUD chip (`SYS: SIMULATION` / `SYS: LIVE_API`), driven by a `mode` property.
6. **`MatchSetupView.qml`:** replace `setupExecutionBanner` with `ModeControl` (objectName `setupModeControl`); wire Launch to `launchFromProfile(profile, mode)`; render disabled/error states data-driven from `ObserverClient` capability properties.
7. **`AppShell.qml`:** mount `DataSourceChip` (objectName `dataSourceChip`) in the top bar; bind to `ObserverClient.currentExecutionMode`.

---

## 4. Decisions

**Locked**
- **Capability endpoint, not optimistic-403.** `GET /api/runtime/capabilities` is read-only: **no file writes, no provider call, never returns the key / env var name / Authorization / base-url secret, does not change the fake default.** It mirrors `_check_live_capability`, so `reason_code` ∈ {`live_api_disabled`, `missing_api_key`} is **identical** to the launch-time 403 code.
- **`default_mode` is always `"fake"`.** Live being *available* never changes the default selection.
- **HUD truth is API-mediated.** `execution_mode` arrives as a run-detail JSON field (server reads its own `resolved-profile.json`); the Qt client performs **no** file I/O and never references `resolved-profile.json`, `QFile`, `QDir`, or `file://`.
- **Reason codes are rendered data-driven.** The client displays the server's `reason_code`/`message` **verbatim**; it must **not** embed the literal code strings (e.g. `"missing_api_key"`) in `.cpp/.h/.qml` — both to avoid drift and because `api_key` is a forbidden secret-scan substring. The localized label (`UNAVAIL` / `禁用`) is client I18n; the `<reason_code>` and human `message` come from the server.
- **Launch mode rule (hard):** `mode="live"` is sent **only** when the FSM is `live_confirmed`; `fake` and `live_armed` both launch `mode="fake"`. `mode` omitted ⇒ fake. Template launches stay fake. Only the profile launch can request live.

**Two-click arming FSM (canonical — implement + assert exactly):**
```
fake
  └─ click LIVE API (and available) → live_armed
live_armed
  ├─ click ARM LIVE (BILLED)         → live_confirmed
  ├─ click DETERMINISTIC             → fake
  ├─ switch profile                  → fake
  ├─ switch seat                     → fake
  └─ live becomes unavailable        → fake
live_confirmed
  ├─ Launch                          → POST mode="live"
  ├─ click DETERMINISTIC             → fake
  ├─ switch profile                  → fake
  └─ switch seat                     → fake
```
Implement the FSM as a string `state` property on `ModeControl` with exactly the literal values `"fake"`, `"live_armed"`, `"live_confirmed"`, so the static-contract test can assert them. No auto-retract countdown in v1 (decided). No modal.

**Capability payload contract (`g3.runtime_capabilities.v1`):**
```json
{
  "schema_version": "g3.runtime_capabilities.v1",
  "default_mode": "fake",
  "live_api": {
    "enabled": true,
    "providers": {
      "deepseek": {
        "available": false,
        "reason_code": "missing_api_key",
        "message": "DeepSeek API key is not configured."
      }
    }
  }
}
```
- `enabled` = `state.live_enabled`.
- `deepseek.available` = `_check_live_capability(state,"live") is None` (i.e. enabled **and** a launcher/key is wired).
- When **available**: `reason_code`/`message` omitted.
- When **not available**: `reason_code` ∈ {`live_api_disabled`, `missing_api_key`} + the matching `message`, both from `_check_live_capability`. **Never** any secret.

**Microcopy (nominalized HUD register, bilingual):**
| Element | EN | ZH |
|---|---|---|
| HUD chip · fake | `SYS: SIMULATION` | `环境: 离线模拟` |
| HUD chip · live | `SYS: LIVE_API` | `环境: 实时接口` |
| segment | `DETERMINISTIC` \| `LIVE API` | (same) |
| disabled | `UNAVAIL · <reason_code>` | `禁用 · <reason_code>` |
| arm → engaged | `ARM LIVE (BILLED)` → `LIVE ENGAGED` | `接入实时接口（计费）` → `实时接口已接入` |
| gate error | `<code>` + server `message` | `<code>` + server `message` |

---

## 5. Scope

**In scope:** read-only `GET /api/runtime/capabilities`; `execution_mode` field in run detail; Qt `mode` param on `launchFromProfile`; `ModeControl` (segmented + two-click arming) replacing the amber banner; `DataSourceChip` HUD; data-driven disabled/error rendering; offline Python tests + Qt static-contract updates.

**Explicitly NOT in scope (hard boundaries):**
- **No API-key UI** — never an input, never displayed, never in client source.
- **No direct Qt artifact file reads** — no `QFile`/`QDir`/`file://`/`resolved-profile.json` path in the client; execution truth only via server API JSON.
- **No new artifact-read endpoint** — reuse run-detail `execution_mode`.
- No profile save; no real DeepSeek smoke; no `prompt-manifest.json` model fix; no `max_requests` tuning; no cost/metering readout; no per-seat live models; no template live launch; no Web client.
- No changes to G3-1 server gate logic / provider / consensus runner / game engine; no `docs/ROADMAP.md`/`docs/TASKS.md`/`docs/adr/**` edits.

**Allowlist (planned):**
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
clients/qt_observer/CMakeLists.txt                          (register new components)
clients/qt_observer/README.md                               (live toggle + reaffirm boundaries)
clients/qt_observer/tests/tst_observer_api_client_mode.cpp  (new, optional QtTest)
clients/qt_observer/tests/CMakeLists.txt                    (if QtTest added)
tests/test_qt_observer_static_contract.py
docs/superpowers/specs/2026-06-05-g3-2-qt-live-toggle-design.md
docs/harness/plans/2026-06-05--g3-2-qt-live-toggle-plan.md
```

---

## 6. Secret & boundary contract

- The capabilities endpoint exposes **only** posture: `enabled`, `available`, a canonical `reason_code`, and a key-free `message`. It must **never** include the key, the env var name, an `Authorization` header, or a base-url secret.
- The Qt client never holds, requests, or renders a key; `reason_code`/`message` are server-supplied and shown verbatim (no client-side code literals).
- `tests/test_qt_observer_static_contract.py` stays the enforcement: no `file://`/`QFile`/`QDir`; secret-scan (`Authorization:`/`Bearer `/`DEEPSEEK_API_KEY=`/`sk-`/`api_key`/`api-key`) over all client sources must stay clean.

---

## 7. Test strategy

**Default suite — offline, no socket, no key:**
1. **Capabilities helper** (`test_observer_protocol.py`): `build_runtime_capabilities` for the three postures — disabled (`enabled=false`, `available=false`, `live_api_disabled`), flag-on-no-key (`enabled=true`, `available=false`, `missing_api_key`), available (`enabled=true`, `available=true`, no reason). Assert `schema_version`, `default_mode=="fake"`, and **no secret substrings** in the payload.
2. **Endpoint wiring** (`test_observer_server.py`): drive `build_runtime_capabilities` from a real `ObserverServerState` via the **same offline pattern as G3-1** (pure derivation through `_check_live_capability`, no socket). Assert run detail gains `execution_mode` when a `resolved-profile.json` is present (write a fixture artifact, build detail, assert field) and **omits the field (or null) when absent** → the chip defaults to `SYS: SIMULATION`.
3. **Qt static contract** (`test_qt_observer_static_contract.py`, **updated**): new required objectNames `setupModeControl`, `dataSourceChip`; new required components `ModeControl.qml`, `DataSourceChip.qml` (exist + CMake-registered); `ObserverApiClient` exposes `launchFromProfile`(with mode), `refreshCapabilities`, `liveAvailable`, `currentExecutionMode`, and references `/api/runtime/capabilities`; the literal FSM state tokens `live_armed` and `live_confirmed` are present in `ModeControl.qml`; **remove** the stale `setupExecutionBanner` + "Deterministic Mock" assertions, replace with mode-control assertions; secret-scan + no-file-IO assertions stay and must pass (no `api_key` literal — codes are data-driven).
4. **QtTest (optional, C++)** `tst_observer_api_client_mode.cpp`: `launchFromProfile(profile,"live")` puts `"mode":"live"` in the body; default omits→fake; capabilities JSON parses into the properties; `unreachable` on error. Only if the existing QtTest harness builds in this env.

**Build/verify:** `PYTHONPATH=src python -m unittest tests.test_observer_protocol tests.test_observer_server tests.test_qt_observer_static_contract`; `compileall`; (Qt) `cmake -S clients/qt_observer … && ctest` on F: per `clients/qt_observer/README.md`. (Localhost HTTP stays blocked in this env → capability logic is validated via the pure helper, not a live socket, exactly as in G3-1.)

---

## 8. Slice tasks (TDD order)

- **T1** — `observer_protocol.py`: `RUNTIME_CAPABILITIES_SCHEMA_VERSION` + `build_runtime_capabilities`; helper unit tests (3 postures + no-secret).
- **T2** — `observer_server.py`: `GET /api/runtime/capabilities` reusing `_check_live_capability`; offline endpoint-derivation tests.
- **T3** — `observer_server.py`: surface `execution_mode` in run detail (server reads its own `resolved-profile.json`); fixture tests (present / absent).
- **T4** — `ObserverApiClient`: `mode` param on `launchFromProfile`; `refreshCapabilities` + properties + `currentExecutionMode`; `unreachable` fallback. Static-contract + optional QtTest.
- **T5** — `ModeControl.qml` (segmented + two-click arming FSM) replacing `setupExecutionBanner`; `DataSourceChip.qml`; `MatchSetupView`/`AppShell` wiring; CMake + static-contract updates.
- **T6** — README + secret/boundary regression: reaffirm no-key-UI / no-file-reads, document the live toggle; full static-contract green.
- **T7** — Validate (offline suite + Qt build/ctest on F:) + review packet + PR.

---

## 9. Acceptance criteria

- **A1** `GET /api/runtime/capabilities` returns `g3.runtime_capabilities.v1` with `default_mode="fake"` and `live_api` derived from `_check_live_capability`; `reason_code` matches the launch-time 403 codes; payload carries no secret. *(T1/T2)*
- **A2** Run detail includes `execution_mode` sourced from the server's own `resolved-profile.json`; the client consumes it with **zero** file I/O. *(T3/T4)*
- **A3** `launchFromProfile(profile,mode)` sends `mode="live"` **only** in `live_confirmed`; default/omitted/template ⇒ fake. *(T4/T5)*
- **A4** `ModeControl` implements the canonical arming FSM (disarm on Deterministic / profile / seat / unavailability); fake stays the default. *(T5)*
- **A5** The HUD `DataSourceChip` shows executed truth (`SYS: LIVE_API` iff `execution_mode=="live"`, else `SYS: SIMULATION`); the amber "Deterministic Mock" banner is gone. *(T5)*
- **A6** Live-unavailable and gate-error states render the server's `reason_code`/`message` verbatim; no reason-code literals in client source. *(T5/T6)*
- **A7** No key entry/display anywhere; static-contract secret-scan + no-file-IO + no-Python-runtime contracts stay green; default Python suite offline & green (env-blocked server-socket tests excepted). *(T6/T7)*

---

## 10. Follow-ups (named, out of scope — G3-3, already queued)
- Thread the real model into runtime-spine `prompt-manifest.json` (today `"unknown"`).
- Run the gated real-DeepSeek smoke once; record the text-free result.
- Re-tune `max_requests=32` → 48/64 only on smoke evidence.
- (Housekeeping) sync `docs/ROADMAP.md` + `docs/TASKS.md` (stale; omit G2d-2/G3-1).
