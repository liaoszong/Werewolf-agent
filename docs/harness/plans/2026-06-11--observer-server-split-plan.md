# Implementation Plan: SYS-C2 observer_server god-module split

Date: 2026-06-11
Branch: `sys-c2-observer-split` (isolated worktree `G:/worktree-observer-split`, base main `7066b36`)
Status: ACTIVE (spec reviewed by user; 2 BLOCKING + 1 MEDIUM + byte-list MINOR fixes incorporated)

## Goal

Split `src/werewolf_eval/observer_server.py` (~1212 lines, 10+ responsibilities) into
layered modules under a new package `src/werewolf_eval/observer/`, with
`observer_server.py` retained as a pure facade. **Zero external behavior change**:
endpoint paths, status codes, JSON shapes, SSE framing, and error strings are all
byte-identical. Internal seams become function-level unit-testable.

## Frozen contracts (three layers)

### Layer 1 — HTTP protocol (ADR-0001)

`tests/test_observer_server.py` is the contract oracle: **no existing assertion may
change**; the whole suite must pass unmodified. Qt client is a real consumer.

### Layer 2 — import surface

These files import directly from `werewolf_eval.observer_server` and are **all on the
do-not-touch list**:

- `tests/test_observer_server.py` — `ObserverRequestHandler, ObserverServerState,
  _build_capabilities_payload, _check_live_capability, _check_live_profile_shape,
  _map_launcher_exit_reason, _schema_payload, _seed_default_profile,
  create_observer_server, default_fake_launcher`
- `tests/test_observer_byo_key_launch.py` — `_resolve_live_launcher_for_launch,
  ObserverServerState, ObserverRequestHandler, _sanitize_launcher_error` (+ more)
- `tests/test_observer_credentials_endpoint.py` — `ObserverServerState,
  _build_capabilities_payload, _credentials_post_result, _credentials_delete_result,
  ObserverRequestHandler`
- `tests/test_observer_run_delete.py` — `_run_delete_result`
- `tests/test_observer_models_endpoint.py` — `_provider_models_result`
- `src/werewolf_eval/run_observer_server.py` — `create_observer_server`

⇒ `observer_server.py` stays as a facade re-exporting **all 25 current top-level
names** (verified count): `RunLauncher, _PROFILE_NAME_RE, default_fake_launcher,
ObserverServerState, _resolve_live_launcher_for_launch, _check_live_capability,
_check_live_profile_shape, _provider_live_posture, _schema_payload,
_build_capabilities_payload, _CREDENTIAL_PROVIDERS, _credentials_post_result,
_credentials_delete_result, _run_delete_result, _provider_models_result,
_read_execution_mode, _map_launcher_exit_reason, _sanitize_launcher_error,
_LOOPBACK_HOSTNAMES, _hostname_of, _is_loopback_hostname, ObserverRequestHandler,
_seed_default_profile, create_observer_server, _read_events_jsonl_safe`.

No `mock.patch` targets module attributes (verified), so re-export suffices.

### Layer 3 — handler private-method surface (FROZEN; widened after review)

Tests subclass `ObserverRequestHandler` (skipping socket init) and rely on these
methods **by name, signature, and call-chain position**:

**Override points** (tests replace them; production code must keep CALLING them):
- `_send_json(status, payload)` / `_send_error_json(status, code, message)` — every
  response must flow through these.
- `_get_state()` — all state reads flow through it; its IMPLEMENTATION (`return
  self.server.state`) is also frozen (`_InProcessHandler` only sets
  `self.server = _FakeServer(state)`).
- `_is_loopback()` — loopback gate must be invoked as `self._is_loopback()`
  (test overrides it without setting `client_address`).
- `_read_json_body()` — POST /api/runs body read.
- `_launch_run_async(run_id, run_dir, launcher)` — `_handle_profile_launch` must
  dispatch the chosen launcher through THIS method (LiveDispatchTests, ~18 cases,
  intercepts it to run synchronously).

**Direct call points** (tests call them on a bare handler; must remain methods with
same signatures/behavior):
- `_handle_profile_launch(body)`
- `_reject_cross_origin()` (sends 403 via `self._send_error_json`, returns bool)
- `_execute_run(run_id, run_dir, launcher)`
- `_get_status(run_id, run_dir)` / `_set_status(run_id, status)`
- `_get_error(run_id)` / `_set_error(run_id, error)`
- `_run_detail_with_reason(run_id, run_dir)`
- `do_GET()` / `do_POST()` / `do_DELETE()` (use `self.path`, `self.headers.get`,
  `self.rfile`, overridable per tests)

⇒ All of these stay on the handler as thin delegates. New modules are the
implementation hosts, never the call surface.

## Module map (`src/werewolf_eval/observer/`)

| Module | Contents | Seam |
|---|---|---|
| `state.py` | `ObserverServerState`, `RunLauncher` | verbatim move |
| `security.py` | `_LOOPBACK_HOSTNAMES`, `_hostname_of`, `_is_loopback_hostname`, new `evaluate_request_guards(client_ip, headers, *, loopback_message, require_same_origin) -> tuple[int,str,str] \| None` | pure functions; unit-test target. Handler keeps `_is_loopback`/`_is_same_origin_local`/`_reject_cross_origin` as overridable shells. Route dispatch translates guard flags into calls to `self._is_loopback()` / `self._reject_cross_origin()` — NEVER feeds `self.client_address` to the pure function directly. |
| `run_manager.py` | class `RunManager(state)`: `get_status/set_status` (memory+status.json dual write), `get_error/set_error`, `execute_run`, `delete_run` (incl. in-memory eviction under lock), `run_detail_with_reason`; module-level: `_read_execution_mode`, `_read_events_jsonl_safe`, `_resolve_live_launcher_for_launch`, `_check_live_capability`, `_check_live_profile_shape`, `_provider_live_posture`, `_map_launcher_exit_reason`, `_sanitize_launcher_error`, `_schema_payload`, `_build_capabilities_payload` | functions stay module-level (tests import by name); RunManager methods are function-level testable. Handler keeps same-named `_`-methods delegating to a per-state RunManager. Thread spawn stays in handler `_launch_run_async` (frozen override point). |
| `credentials_api.py` | `_CREDENTIAL_PROVIDERS`, `_credentials_post_result`, `_credentials_delete_result`, `_provider_models_result` | verbatim move (already pure) |
| `launch.py` | `execute_profile_launch(state, body) -> ("error", status, code, message) \| ("launch", run_id, run_dir, launcher, payload_202)` | NO thread spawn inside; gate ORDER preserved verbatim: capability → load(named) → validate → shuffle gate → 409-exists → shape → launcher resolve → mkdir → synchronous resolved-profile write. Handler `_handle_profile_launch` = thin shell: call, then `self._send_error_json(*err)` or `self._launch_run_async(...)` + `self._send_json(202, payload)`. |
| `sse.py` | `stream_run_events(wfile, *, run_id, run_dir, perspective, get_status, get_error, poll_interval)` | DI callables; testable with fake wfile. Response headers (`text/event-stream`/`no-cache`/`Connection: close`) AND `close_connection = True` stay in the handler wrapper; normal return from the stream fn means "close now". Depends one-way: sse → run_manager (`_read_events_jsonl_safe`). |
| `routes.py` | `Route(pattern, handler_name, loopback_message=None, same_origin=False)`; `GET_ROUTES/POST_ROUTES/DELETE_ROUTES`; `match(routes, segments)` | table order == current branch order (`profiles/schema` before `profiles/{name}`); `{name}` captures one segment; trailing-extra-segments-ignored flag for `snapshots/{name}` and `artifacts/{name}`. Run subtree = GROUP route: validate_run_id (raises → 400) → missing dir → 404 `Run not found: {id}` → parse perspective (current timing: BEFORE sub-dispatch, so `/artifacts` etc. also 400 on bad perspective) → sub-table → group fallback 404 `Not found`. |
| `handler.py` | `ObserverRequestHandler` — protocol translation only + the frozen Layer-3 method surface | `do_GET/do_POST/do_DELETE` keep their OWN try/except blocks (per-method error-string forks preserved). |
| `factory.py` | `create_observer_server`, `_seed_default_profile`, `default_fake_launcher` | verbatim move |
| `observer_server.py` | pure facade: explicit re-export of all 25 names | pinned by a parity test |

## Byte-level risk checklist (copy verbatim during migration)

Loopback 403 messages — three distinct strings, list verbatim (note: "runs delete"
has NO word "endpoint"):
- `"credentials endpoint is loopback-only"` (POST /api/credentials AND DELETE /api/credentials/{p})
- `"runs delete is loopback-only"` (DELETE /api/runs/{id})
- `"providers endpoint is loopback-only"` (GET /api/providers/{p}/models)
- cross-origin: `"cross-origin or non-loopback Host rejected"`

404 messages — FIVE kinds:
- `"Not found"` (GET/POST global + run-group fallback)
- `f"Run not found: {run_id}"`
- `"unknown endpoint"` (DELETE fallback)
- `"profile not found"` (GET profile + named launch)
- `f"Artifact not found: {art_name}"` (TWO sites: explicit artifacts path + alias path)

Snapshot fork: `ObserverProtocolError` with `"cannot view"` in `str(exc)` → 403
`snapshot_hidden` + `str(exc)`; otherwise 404 `not_found` + `str(exc)` verbatim.

Exception mapping is PER-METHOD:
- GET/POST: `ObserverProtocolError` → 400 `invalid_request`; POST additionally
  `json.JSONDecodeError` → 400 `invalid_json` `"Request body is not valid JSON"`;
  generic → 500 `internal_error` `"Internal server error"`.
- DELETE: `ObserverProtocolError` → 400 `bad_request`; generic → 500 same.
- DELETE error third arg asymmetry: runs delete uses
  `str(payload.get("detail", ""))`; credentials delete uses `""`.

Guard matrix is ASYMMETRIC — do NOT "fix" it:
- POST/DELETE credentials, DELETE runs: loopback + cross-origin.
- POST /api/runs: cross-origin ONLY (no loopback).
- GET providers/models: loopback ONLY (no cross-origin).
- All other GETs: no guard.

Other:
- `_send_json`: `sort_keys=True, ensure_ascii=False`, Content-Length set.
- Credentials POST: 8192 cap → 413; non-dict parsed JSON → 400 `invalid_json`.
- Launch gate order has dedicated regression tests (capability BEFORE load;
  mkdir AFTER launcher resolve — orphan-dir regression).
- SSE: initial status frame → event frames (perspective-filtered, `sent_count`
  counts ALL events) → on terminal status drain + final status frame (with
  reason) → close. File-growth gate (`st_size` unchanged → skip re-read).
- `resolved-profile.json` written synchronously BEFORE 202 (HUD race fix).

## Test strategy

- **Oracle**: full existing suite green (`NO_PROXY='*' PYTHONPATH=src`), with
  `git diff --name-only` proving no existing test file changed.
- **New unit tests** (4 files, internal seams previously untestable):
  - `tests/test_observer_security.py` — hostname parsing edges (userinfo spoof,
    bracketed IPv6, loopback-prefix subdomain) + guard decision matrix.
  - `tests/test_observer_run_manager.py` — status dual-write, restart fallback to
    status.json, delete eviction, launcher 3-way resolution matrix.
  - `tests/test_observer_routes.py` — full endpoint match table, order-sensitive
    cases, trailing-segment tolerance + **facade parity test** (all 25 names
    importable from `werewolf_eval.observer_server`).
  - `tests/test_observer_sse.py` — fake wfile: frame order, perspective filter,
    no-growth no-reread.
- Migration method: move + delegate only, no logic edits; full suite per slice.

## Slices (one commit each, TDD)

1. `security.py` (+ tests first)
2. `state.py` + `run_manager.py` (+ tests)
3. `credentials_api.py` (pure move)
4. `sse.py` (+ tests)
5. `launch.py` (orchestration extraction, handler shell keeps `_launch_run_async` dispatch)
6. `routes.py` + `handler.py` (table-driven dispatch; biggest slice, last among logic moves)
7. `factory.py` + facade + parity test
8. `node .codex/hooks/tree.mjs --force` + merge-readiness report (no merge, no push)

## Validation per slice

- `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
- `git status --short` (no stray staged files) + `git branch --show-current` before commit
- Final: `git diff main --stat` / `--name-only` allowlist check; forbidden-scope check
  (no `observer_protocol.py`/`observer_visibility.py`/`runtime_events.py`/
  `profile_config.py`/`action_runtime/**`/`run_*.py`/`deepseek_launcher.py`/
  `pyproject`/`emergent_engine.py`/`prompt_v2.py`/`llm_providers.py` changes);
  `git merge-tree` conflict probe vs main.
