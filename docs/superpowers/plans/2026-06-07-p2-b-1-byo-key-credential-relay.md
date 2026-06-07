# P2-B-1 BYO-key Credential Relay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user supply their own DeepSeek API key in the Qt client; the key is saved locally (QSettings, dev-only), relayed as a session credential to the local server (`/api/credentials`), kept in server process memory, and injected into the server-executed DeepSeek live call (env key as fallback). The key never touches any artifact, log, or error response. Qt never calls DeepSeek directly.

**Architecture:** Client-held secret, server-executed call. Server gains an injected in-memory `CredentialStore` + a `POST/DELETE /api/credentials` endpoint. The live launcher changes from a **prebuilt env launcher** to a **per-launch launcher built from `(in-memory key ?? env key)`** via a factory closure. The capability gate's `deepseek_available` becomes "a credential exists (in-memory client key OR env key)". Qt gets a `CredentialStore` (C++ QObject over QSettings) and an inline key panel in `MatchSetupView`; arming live is a UX gate, the server re-validates at launch.

**Tech Stack:** Python 3.12 stdlib `http.server` (`unittest`), Qt 6.10 QML + C++ (`ObserverApiClient` singleton pattern), build via `F:/Qt/Tools/CMake_64/bin/cmake.exe`.

**Spec:** `docs/superpowers/specs/2026-06-07-p2-b-1-byo-key-credential-relay-design.md` (commit `7065e05`).

**Branch:** `p2-b-1-byo-key` (already created).

---

## File Structure

- **NEW** `src/werewolf_eval/credential_store.py` — in-memory, lock-guarded, redacted-repr credential store (one responsibility: hold `{provider: key}` in process memory).
- **MODIFY** `src/werewolf_eval/observer_server.py` — `ObserverServerState` gains `credential_store` + `live_launcher_factory` + `env_key_available`; `_check_live_capability` consults credential-or-env; new `POST /api/credentials` + `DELETE /api/credentials/{provider}` routes; `_handle_profile_launch` builds the live launcher per-launch; error sanitization for live failures.
- **MODIFY** `src/werewolf_eval/run_observer_server.py` — pass a `live_launcher_factory(api_key)` (closure over base_url/model/tokens/budget) + `env_key` into the server instead of a single prebuilt env launcher.
- **NEW** `clients/qt_observer/src/CredentialStore.h` / `.cpp` — C++ QObject: QSettings (dev-only) persistence, masked accessors, server sync via POST/DELETE; NO `getRawKey` exposed to QML.
- **MODIFY** `clients/qt_observer/qml/MatchSetupView.qml` — inline credential panel + arming gate + save→sync states.
- **MODIFY** `clients/qt_observer/CMakeLists.txt` — register `CredentialStore`.
- **NEW** `tests/test_credential_store.py`, `tests/test_observer_credentials_endpoint.py`, `tests/test_observer_byo_key_launch.py` — server-side offline tests.
- **MODIFY** `tests/test_qt_observer_static_contract.py` — credential-panel objectNames + forbidden-leak guards.

**Reference facts (verified against current code):**
- `ObserverServerState` dataclass (`observer_server.py:73`): `runs_dir, launcher, profiles_dir, run_status, run_errors, lock, live_enabled, live_launcher`.
- `_check_live_capability(state, mode)` (`:87`): live→ `live_enabled` false ⇒ `(403,"live_api_disabled",...)`; `live_launcher is None` ⇒ `(403,"missing_api_key",...)`; else None.
- `_build_capabilities_payload` (`:127`) derives posture from `_check_live_capability`; `build_runtime_capabilities(live_enabled, deepseek_available, reason_code?, message?)` → `{schema_version, default_mode:"fake", live_api:{enabled, providers:{deepseek:{available[,reason_code,message]}}}}`.
- `_handle_profile_launch` (`:512`): cap gate → load/validate → shape gate (`_check_live_profile_shape`) → `base = state.live_launcher if is_live else state.launcher` (`:559`) → wraps `_profile_launcher` (writes `resolved-profile.json` via `build_resolved_profile_artifact`, which takes only `profile, run_id, execution_mode, live_api` — NO credentials) → `_launch_run_async`.
- `_read_json_body` (`:216`): reads Content-Length, `json.loads`, requires dict; raises `ObserverProtocolError`. Does NOT check Content-Type.
- `do_POST` (`:592`): `["api","runs"]` (profile vs plain), `["api","profiles","validate"]`. `do_GET` `["api","runtime","capabilities"]` (`:292`).
- `do_GET`/`do_POST` use `self._path_segments()`; errors via `_send_error_json(status, code, message)`; `log_message` already suppressed (`:276`).
- `run_observer_server.resolve_live_launcher` (`run_observer_server.py:36`): reads env key once, builds `build_emergent_deepseek_launcher(api_key, base_url, model, max_tokens=_LIVE_MAX_TOKENS, max_requests)`; returns `(live_enabled, launcher|None)`.
- `deepseek_launcher.build_emergent_deepseek_launcher(*, api_key, base_url, model, timeout_seconds=, max_tokens, max_requests=, max_day_rounds=, provider_factory=None) -> RunLauncher` (built in PR #56).
- `profile_config.ALLOWED_PROVIDERS = {"fake_deterministic","deepseek"}`.
- ObserverApiClient is a registered QML singleton (C++); CredentialStore will follow the same registration in `CMakeLists.txt` and `main.cpp`.

**Forbidden (git diff MUST be empty):** `emergent_engine.py`, `game_engine.py`, `scoring.py`, `attribution.py`, `settlement_bundle.py`, `observer_visibility.py`, `deepseek_provider.py`, `PROJECT_MAP.md`, `TASKS.md`.

---

## Task 1: Server in-memory CredentialStore

**Files:** Create `src/werewolf_eval/credential_store.py`, `tests/test_credential_store.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_credential_store.py`:

```python
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.credential_store import CredentialStore

_KEY = "sk-test-fake-credential-store-1234"


class CredentialStoreTests(unittest.TestCase):
    def test_set_get_has_clear(self) -> None:
        s = CredentialStore()
        self.assertFalse(s.has("deepseek"))
        self.assertIsNone(s.get("deepseek"))
        s.set("deepseek", _KEY)
        self.assertTrue(s.has("deepseek"))
        self.assertEqual(s.get("deepseek"), _KEY)
        self.assertTrue(s.clear("deepseek"))      # existed -> True
        self.assertFalse(s.has("deepseek"))
        self.assertFalse(s.clear("deepseek"))     # idempotent -> False

    def test_repr_and_str_never_contain_key(self) -> None:
        s = CredentialStore()
        s.set("deepseek", _KEY)
        self.assertNotIn(_KEY, repr(s))
        self.assertNotIn(_KEY, str(s))
        self.assertNotIn("sk-", repr(s))

    def test_thread_safe_set_get(self) -> None:
        s = CredentialStore()
        errors: list = []

        def worker(i: int) -> None:
            try:
                for _ in range(200):
                    s.set("deepseek", f"sk-{i}")
                    s.get("deepseek")
                    s.has("deepseek")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertTrue(s.has("deepseek"))

    def test_empty_key_rejected(self) -> None:
        s = CredentialStore()
        with self.assertRaises(ValueError):
            s.set("deepseek", "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_credential_store -v`
Expected: FAIL — `No module named 'werewolf_eval.credential_store'`.

- [ ] **Step 3: Write the implementation**

Create `src/werewolf_eval/credential_store.py`:

```python
"""In-memory, process-lifetime credential store for BYO-key live runs (P2-B-1).

Holds {provider: api_key} ONLY in process memory: never persisted, never logged,
never serialized into any artifact or HTTP response. The single plaintext-returning
method is `get`, called only by the launch wiring. `__repr__`/`__str__` are redacted
so a failing test or debug log can never print a key. Lock-guarded because the
observer runs on a ThreadingHTTPServer."""

from __future__ import annotations

import threading


class CredentialStore:
    def __init__(self) -> None:
        self._creds: dict[str, str] = {}
        self._lock = threading.Lock()

    def set(self, provider: str, api_key: str) -> None:
        if not api_key:
            raise ValueError("api_key must be non-empty")
        with self._lock:
            self._creds[provider] = api_key

    def get(self, provider: str) -> str | None:
        with self._lock:
            return self._creds.get(provider)

    def has(self, provider: str) -> bool:
        with self._lock:
            return provider in self._creds

    def clear(self, provider: str) -> bool:
        """Remove the provider's key. Returns True if one existed (idempotent)."""
        with self._lock:
            return self._creds.pop(provider, None) is not None

    def __repr__(self) -> str:
        with self._lock:
            return f"CredentialStore(providers={sorted(self._creds)})"

    __str__ = __repr__
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_credential_store -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/credential_store.py tests/test_credential_store.py
git commit -m "feat(server): in-memory redacted CredentialStore for BYO-key"
```

---

## Task 2: Wire CredentialStore + live_launcher_factory into ObserverServerState; capability gate

**Files:** Modify `src/werewolf_eval/observer_server.py`, `tests/test_observer_credentials_endpoint.py` (new, capability slice here)

- [ ] **Step 1: Write the failing test (capability semantics)**

Create `tests/test_observer_credentials_endpoint.py` (capability portion; endpoint added in Task 3):

```python
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.observer_server import ObserverServerState, _build_capabilities_payload


def _state(tmp, *, live_enabled, env_key_available, has_client_key):
    cs = CredentialStore()
    if has_client_key:
        cs.set("deepseek", "sk-test-fake-client-key")
    return ObserverServerState(
        runs_dir=Path(tmp), launcher=lambda r, d: 0,
        live_enabled=live_enabled,
        credential_store=cs,
        live_launcher_factory=(lambda api_key: (lambda r, d: 0)),
        env_key_available=env_key_available,
    )


class CapabilityCredentialTests(unittest.TestCase):
    def test_available_with_client_key_no_env(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=True, env_key_available=False, has_client_key=True))
            self.assertTrue(cap["live_api"]["providers"]["deepseek"]["available"])

    def test_available_with_env_no_client_key(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=True, env_key_available=True, has_client_key=False))
            self.assertTrue(cap["live_api"]["providers"]["deepseek"]["available"])

    def test_unavailable_with_neither(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=True, env_key_available=False, has_client_key=False))
            dp = cap["live_api"]["providers"]["deepseek"]
            self.assertFalse(dp["available"])
            self.assertEqual(dp["reason_code"], "missing_api_key")

    def test_unavailable_when_live_disabled(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=False, env_key_available=True, has_client_key=True))
            self.assertFalse(cap["live_api"]["enabled"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_credentials_endpoint -v`
Expected: FAIL — `ObserverServerState.__init__() got an unexpected keyword argument 'credential_store'`.

- [ ] **Step 3: Extend `ObserverServerState`**

In `observer_server.py`, add to the dataclass (after `live_launcher`, `:84`). Import `CredentialStore` at top (`from werewolf_eval.credential_store import CredentialStore`) and `Callable` from typing:

```python
    # P2-B-1 BYO-key: in-memory client credentials + a per-launch live launcher
    # factory (built from a key at launch). live_launcher above stays as the
    # prebuilt ENV launcher (back-compat / fallback); env_key_available records
    # whether the server started with an env key.
    credential_store: CredentialStore = field(default_factory=CredentialStore)
    live_launcher_factory: Callable[[str], RunLauncher] | None = None
    env_key_available: bool = False
```

- [ ] **Step 4: Update `_check_live_capability` to consult credential-or-env**

Replace the body of `_check_live_capability` (`:95-101`):

```python
    if mode != "live":
        return None
    if not state.live_enabled:
        return (403, "live_api_disabled", "live API is not enabled on this server")
    # BYO-key: a credential is available if the client synced one OR the server
    # started with an env key (back-compat). Prefer the legacy prebuilt launcher
    # signal when present so existing env-only deployments are unchanged.
    has_credential = (
        state.credential_store.has("deepseek")
        or state.env_key_available
        or state.live_launcher is not None
    )
    if not has_credential:
        return (403, "missing_api_key", "no DeepSeek credential is available (set one in the client)")
    return None
```

- [ ] **Step 5: Run the capability tests to verify they pass**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_credentials_endpoint -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Run the existing observer-server suite to confirm no regression**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_server 2>&1 | grep -E "^(OK|FAILED|Ran)|non-socket"`
Expected: same pre-existing 47 socket errors only (the capability-logic tests like `LiveOptInTests`/`LiveGateHelperTests` still pass). If a non-socket capability test now fails because it constructs `ObserverServerState` without the new fields, that's fine — the new fields have defaults; investigate only a real assertion failure.

- [ ] **Step 7: Commit**

```bash
git add src/werewolf_eval/observer_server.py tests/test_observer_credentials_endpoint.py
git commit -m "feat(server): ObserverServerState credential store + factory; capability = client-or-env key"
```

---

## Task 3: `POST /api/credentials` + `DELETE /api/credentials/{provider}`

**Files:** Modify `src/werewolf_eval/observer_server.py`, `tests/test_observer_credentials_endpoint.py`

This task drives the endpoint via an in-process handler (no socket — localhost HTTP is env-blocked). Add a tiny in-process handler harness mirroring `tests/test_observer_server.py`'s `_InProcessHandler` if one is reusable; otherwise call the handler methods directly. To keep this offline and simple, factor the credential logic into pure helpers and test those plus a thin route assertion.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_observer_credentials_endpoint.py`:

```python
from werewolf_eval.observer_server import (
    _credentials_post_result,
    _credentials_delete_result,
)


class CredentialsEndpointLogicTests(unittest.TestCase):
    def _cs(self):
        return CredentialStore()

    def test_post_stores_deepseek_and_does_not_echo_key(self):
        cs = self._cs()
        status, payload = _credentials_post_result(
            cs, "application/json", {"provider": "deepseek", "api_key": "sk-test-fake-xyz"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"stored": ["deepseek"]})
        self.assertNotIn("sk-test-fake-xyz", str(payload))
        self.assertTrue(cs.has("deepseek"))

    def test_post_rejects_non_json_content_type(self):
        cs = self._cs()
        status, payload = _credentials_post_result(cs, "text/plain", {"provider": "deepseek", "api_key": "k"})
        self.assertEqual(status, 415)
        self.assertFalse(cs.has("deepseek"))

    def test_post_accepts_charset_suffix(self):
        cs = self._cs()
        status, _ = _credentials_post_result(
            cs, "application/json; charset=utf-8", {"provider": "deepseek", "api_key": "sk-ok"}
        )
        self.assertEqual(status, 200)

    def test_post_rejects_empty_or_missing(self):
        cs = self._cs()
        for body in ({}, {"provider": "deepseek"}, {"provider": "deepseek", "api_key": ""}, {"api_key": "k"}):
            status, _ = _credentials_post_result(cs, "application/json", body)
            self.assertEqual(status, 400, body)
        self.assertFalse(cs.has("deepseek"))

    def test_post_rejects_non_allowlisted_provider(self):
        cs = self._cs()
        for prov in ("fake_deterministic", "openai", "anthropic", "weird"):
            status, _ = _credentials_post_result(cs, "application/json", {"provider": prov, "api_key": "k"})
            self.assertEqual(status, 400, prov)

    def test_delete_clears_and_is_idempotent(self):
        cs = self._cs()
        cs.set("deepseek", "sk-x")
        self.assertEqual(_credentials_delete_result(cs, "deepseek"), (200, {"cleared": "deepseek"}))
        self.assertFalse(cs.has("deepseek"))
        self.assertEqual(_credentials_delete_result(cs, "deepseek")[0], 200)   # idempotent
        self.assertEqual(_credentials_delete_result(cs, "openai")[0], 400)     # not allowlisted
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_credentials_endpoint -v`
Expected: FAIL — `cannot import name '_credentials_post_result'`.

- [ ] **Step 3: Add the pure helpers**

In `observer_server.py`, add near the other module helpers (after `_build_capabilities_payload`). Add `from werewolf_eval.profile_config import ALLOWED_PROVIDERS` if not already imported; define the credential allowlist locally as deepseek-only for this slice:

```python
# P2-B-1: credentials this slice accepts (deepseek-only; multi-provider is P2-B-3).
_CREDENTIAL_PROVIDERS: frozenset[str] = frozenset({"deepseek"})


def _credentials_post_result(
    store: "CredentialStore", content_type: str, body: dict[str, object]
) -> tuple[int, dict[str, object]]:
    """Pure logic for POST /api/credentials. NEVER returns or logs the key."""
    if not str(content_type or "").split(";")[0].strip() == "application/json":
        return (415, {"error": "unsupported_media_type"})
    provider = body.get("provider")
    api_key = body.get("api_key")
    if not isinstance(provider, str) or provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    if not isinstance(api_key, str) or not api_key:
        return (400, {"error": "missing_api_key"})
    store.set(provider, api_key)
    return (200, {"stored": [provider]})


def _credentials_delete_result(
    store: "CredentialStore", provider: str
) -> tuple[int, dict[str, object]]:
    """Pure logic for DELETE /api/credentials/{provider}. Idempotent."""
    if provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    store.clear(provider)
    return (200, {"cleared": provider})
```

- [ ] **Step 4: Wire the routes (POST + DELETE), with body-size cap + loopback guard**

In `do_POST` (`:595`), add BEFORE the `["api","runs"]` branch:

```python
            if segments == ["api", "credentials"]:
                if not self._is_loopback():
                    self._send_error_json(403, "forbidden", "credentials endpoint is loopback-only")
                    return
                content_type = self.headers.get("Content-Type", "")
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 8192:
                    self._send_error_json(413, "payload_too_large", "credential body too large")
                    return
                # Read body WITHOUT _read_json_body so a non-JSON content-type is a
                # clean 415 (not a JSON parse error); never log the body.
                raw = self.rfile.read(content_length) if content_length else b""
                try:
                    body = json.loads(raw) if raw else {}
                    if not isinstance(body, dict):
                        body = {}
                except json.JSONDecodeError:
                    self._send_error_json(400, "invalid_json", "credential body must be JSON")
                    return
                status, payload = _credentials_post_result(
                    self._get_state().credential_store, content_type, body
                )
                if status == 200:
                    self._send_json(200, payload)
                else:
                    self._send_error_json(status, str(payload.get("error", "bad_request")), "")
                return
```

Add a `do_DELETE` method (the handler currently has none) near `do_POST`:

```python
    def do_DELETE(self) -> None:
        segments = self._path_segments()
        try:
            if len(segments) == 3 and segments[:2] == ["api", "credentials"]:
                if not self._is_loopback():
                    self._send_error_json(403, "forbidden", "credentials endpoint is loopback-only")
                    return
                status, payload = _credentials_delete_result(
                    self._get_state().credential_store, segments[2]
                )
                if status == 200:
                    self._send_json(200, payload)
                else:
                    self._send_error_json(status, str(payload.get("error", "bad_request")), "")
                return
            self._send_error_json(404, "not_found", "unknown endpoint")
        except ObserverProtocolError as exc:
            self._send_error_json(400, "bad_request", str(exc))
```

Add the `_is_loopback` helper near `_get_state`:

```python
    def _is_loopback(self) -> bool:
        host = self.client_address[0] if self.client_address else ""
        return host in ("127.0.0.1", "::1", "localhost")
```

- [ ] **Step 5: Run the endpoint logic tests**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_credentials_endpoint -v`
Expected: PASS (capability + endpoint-logic tests).

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/observer_server.py tests/test_observer_credentials_endpoint.py
git commit -m "feat(server): POST/DELETE /api/credentials (deepseek-only, JSON-only, no echo, loopback, body cap)"
```

---

## Task 4: Launch wiring — build live launcher from in-memory key (env fallback); no key in artifacts

**Files:** Modify `src/werewolf_eval/observer_server.py`, `tests/test_observer_byo_key_launch.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_observer_byo_key_launch.py`:

```python
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.observer_server import _resolve_live_launcher_for_launch

_CLIENT = "sk-test-fake-client-AAAA"
_ENV = "sk-test-fake-env-BBBB"


class ResolveLiveLauncherTests(unittest.TestCase):
    def _state(self, *, client, env):
        cs = CredentialStore()
        if client:
            cs.set("deepseek", _CLIENT)
        captured = {}

        def factory(api_key):
            captured["key"] = api_key
            return lambda r, d: 0

        from werewolf_eval.observer_server import ObserverServerState
        st = ObserverServerState(
            runs_dir=Path("."), launcher=lambda r, d: 0,
            live_enabled=True, credential_store=cs,
            live_launcher_factory=factory,
            env_key_available=bool(env),
            live_launcher=(lambda r, d: 0) if env else None,
        )
        return st, captured

    def test_client_key_preferred_over_env(self):
        st, captured = self._state(client=True, env=True)
        launcher, err = _resolve_live_launcher_for_launch(st)
        self.assertIsNone(err)
        self.assertIsNotNone(launcher)
        self.assertEqual(captured["key"], _CLIENT)   # client beats env

    def test_env_fallback_when_no_client_key(self):
        st, captured = self._state(client=False, env=True)
        launcher, err = _resolve_live_launcher_for_launch(st)
        self.assertIsNone(err)
        self.assertIs(launcher, st.live_launcher)    # uses the prebuilt env launcher

    def test_error_when_neither(self):
        st, _ = self._state(client=False, env=False)
        st.live_launcher = None
        st.env_key_available = False
        launcher, err = _resolve_live_launcher_for_launch(st)
        self.assertIsNone(launcher)
        self.assertEqual(err[1], "missing_api_key")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_byo_key_launch -v`
Expected: FAIL — `cannot import name '_resolve_live_launcher_for_launch'`.

- [ ] **Step 3: Add the resolver + use it in `_handle_profile_launch`**

Add the resolver helper near `_check_live_capability`:

```python
def _resolve_live_launcher_for_launch(
    state: ObserverServerState,
) -> tuple[RunLauncher | None, tuple[int, str, str] | None]:
    """Pick the live launcher for THIS launch: a fresh one built from the client's
    in-memory key (preferred), else the prebuilt env launcher, else a 403. The key
    flows ONLY into the launcher closure (provider Authorization), never returned."""
    client_key = state.credential_store.get("deepseek")
    if client_key is not None and state.live_launcher_factory is not None:
        return state.live_launcher_factory(client_key), None
    if state.live_launcher is not None:
        return state.live_launcher, None
    return None, (403, "missing_api_key", "no DeepSeek credential is available")
```

In `_handle_profile_launch`, replace the live branch of `base = ...` (`:558-559`):

```python
        is_live = mode == "live"
        if is_live:
            base, live_reject = _resolve_live_launcher_for_launch(state)
            if live_reject is not None:
                self._send_error_json(*live_reject)
                return
        else:
            base = state.launcher
```

> `build_resolved_profile_artifact(profile, run_id, execution_mode, live_api)` takes no credential, so `resolved-profile.json` already cannot contain the key — Step 4 adds a regression test that asserts it.

- [ ] **Step 4: Add a secret-scan regression test (artifacts carry no key)**

Append to `tests/test_observer_byo_key_launch.py`:

```python
class ResolvedProfileNoKeyTests(unittest.TestCase):
    def test_resolved_profile_artifact_has_no_credential(self):
        from werewolf_eval.profile_config import build_resolved_profile_artifact
        profile = {"name": "p", "role_defaults": {}, "seat_overrides": {}}
        art = build_resolved_profile_artifact(profile, "r1", execution_mode="live", live_api="used")
        blob = json.dumps(art)
        for marker in ("sk-", "api_key", "authorization", "bearer"):
            self.assertNotIn(marker, blob.lower())
```

(If `build_resolved_profile_artifact` lives elsewhere, import from its real module — confirm during implementation.)

- [ ] **Step 5: Run the launch tests**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_byo_key_launch -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/observer_server.py tests/test_observer_byo_key_launch.py
git commit -m "feat(server): live launcher built per-launch from client key (env fallback); resolved-profile carries no key"
```

---

## Task 5: Sanitize live-failure run status (no key in error)

**Files:** Modify `src/werewolf_eval/observer_server.py`, `tests/test_observer_byo_key_launch.py`

The launcher already maps exit codes to `provider_failure`/`budget_exhausted` (`_map_launcher_exit_reason`). The risk is an EXCEPTION path: `_launch_run_async` catches launcher exceptions and records a reason (`observer_server.py:~465`). Ensure that recorded reason is a canonical code, never the exception text (which could carry a key/url).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_observer_byo_key_launch.py`:

```python
from werewolf_eval.observer_server import _sanitize_launcher_error


class SanitizeLauncherErrorTests(unittest.TestCase):
    def test_auth_error_maps_to_provider_auth_failed_without_key(self):
        msg = "401 Unauthorized: Authorization: Bearer sk-test-fake-LEAK url=https://api.deepseek.com"
        code = _sanitize_launcher_error(RuntimeError(msg))
        self.assertEqual(code, "provider_auth_failed")
        self.assertNotIn("sk-", code)
        self.assertNotIn("Bearer", code)

    def test_generic_error_maps_to_provider_failure(self):
        self.assertEqual(_sanitize_launcher_error(RuntimeError("connection reset")), "provider_failure")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_byo_key_launch.SanitizeLauncherErrorTests -v`
Expected: FAIL — `cannot import name '_sanitize_launcher_error'`.

- [ ] **Step 3: Add the sanitizer and use it in the exception path**

Add near `_map_launcher_exit_reason`:

```python
def _sanitize_launcher_error(exc: BaseException) -> str:
    """Map a launcher EXCEPTION to a key-free canonical reason. Inspects only the
    exception CLASS and a lowercased 'is this auth?' check on the type/args — never
    embeds the message (which could carry an Authorization header / key / url)."""
    text = f"{type(exc).__name__} {exc}".lower()
    if "401" in text or "unauthor" in text or "forbidden" in text or "invalid api key" in text:
        return "provider_auth_failed"
    return "provider_failure"
```

Find where `_launch_run_async`/`_execute_run` records the exception reason (`observer_server.py:~465`, the `except` that records `provider_failure`) and replace the recorded reason with `_sanitize_launcher_error(exc)`. Confirm the run-status reason setter stores this code only (no `str(exc)`).

- [ ] **Step 4: Run the suite slice**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_byo_key_launch -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/observer_server.py tests/test_observer_byo_key_launch.py
git commit -m "fix(server): sanitize live-failure run status to key-free canonical codes"
```

---

## Task 6: `run_observer_server` — pass factory + env key presence (loopback default unchanged)

**Files:** Modify `src/werewolf_eval/run_observer_server.py`

- [ ] **Step 1: Update `resolve_live_launcher` to also return a factory + env flag**

Change `resolve_live_launcher` so that, when `--allow-live-api` is set, it returns a `live_launcher_factory` closure (builds `build_emergent_deepseek_launcher` from a supplied key, capturing base_url/model/max_tokens/max_requests) AND an `env_key_available` flag, in addition to the legacy prebuilt env launcher (built only when an env key exists). Concretely, make `main()` build the server like:

```python
    live_enabled, env_launcher, env_key_available, factory = resolve_live_launcher(args, os.environ)
    server = create_observer_server(
        args.host, args.port, Path(args.runs_dir),
        launcher=default_emergent_fake_launcher,
        live_enabled=live_enabled,
        live_launcher=env_launcher,            # prebuilt env launcher (fallback)
        live_launcher_factory=factory,         # build-from-client-key (preferred)
        env_key_available=env_key_available,
    )
```

Where the factory is:

```python
    def factory(api_key: str) -> RunLauncher:
        return build_emergent_deepseek_launcher(
            api_key=api_key, base_url=args.deepseek_base_url, model=args.deepseek_model,
            max_tokens=_LIVE_MAX_TOKENS, max_requests=args.max_live_requests,
        )
```

`resolve_live_launcher` returns `(live_enabled, env_launcher_or_None, env_key_available, factory_or_None)`. When `--allow-live-api` is off: `(False, None, False, None)`.

- [ ] **Step 2: Extend `create_observer_server` signature**

In `observer_server.py`, add `live_launcher_factory=None, env_key_available=False` params to `create_observer_server` (`:729`) and pass them into `ObserverServerState(...)`.

- [ ] **Step 3: Run the live-opt-in resolver tests**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_server.ObserverServerLiveOptInTests -v`
Expected: PASS — update those tests if they destructure `resolve_live_launcher`'s now-4-tuple return (allowed file: it's a test). Keep semantics: flag off → disabled; flag on + key → factory present; flag on + no key → factory present but env launcher None and env_key_available False (live still arms because client can supply a key).

- [ ] **Step 4: Build-time sanity (imports resolve)**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -c "import werewolf_eval.run_observer_server as m; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/run_observer_server.py src/werewolf_eval/observer_server.py tests/test_observer_server.py
git commit -m "feat(server): wire live_launcher_factory + env_key_available from run_observer_server"
```

---

## Task 7: Qt CredentialStore (C++ QObject, QSettings dev-only)

**Files:** Create `clients/qt_observer/src/CredentialStore.h` + `.cpp`; Modify `clients/qt_observer/CMakeLists.txt`, `clients/qt_observer/main.cpp`

- [ ] **Step 1: Write the header**

Create `clients/qt_observer/src/CredentialStore.h`:

```cpp
#pragma once
#include <QObject>
#include <QString>
#include <QSettings>
#include <QtQml/qqmlregistration.h>

// P2-B-1: client-side BYO-key store. Persists the user's API key via QSettings
// (DEV-ONLY: plaintext on disk; marked dev-only per the spec Storage invariant)
// and relays it to the LOCAL server as a session credential. QML sees only
// masked/presence accessors — never the raw saved key (no getRawKey()).
class CredentialStore : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
public:
    explicit CredentialStore(QObject *parent = nullptr);

    Q_INVOKABLE bool hasCredential(const QString &provider) const;
    Q_INVOKABLE QString maskedCredential(const QString &provider) const; // "sk-••••1234" or ""
    Q_INVOKABLE void saveCredential(const QString &provider, const QString &rawText);
    Q_INVOKABLE void clearCredential(const QString &provider);           // QSettings + server DELETE
    Q_INVOKABLE void syncCredentialToServer(const QString &provider);    // POST /api/credentials

    void setBaseUrl(const QString &baseUrl); // wired from main.cpp like ObserverApiClient

signals:
    void credentialChanged(const QString &provider);
    void syncSucceeded(const QString &provider);
    void syncFailed(const QString &provider, const QString &reason); // reason is key-free

private:
    static QString mask(const QString &raw);
    QString rawCredential(const QString &provider) const; // PRIVATE — never Q_INVOKABLE
    QSettings m_settings;
    QString m_baseUrl;
};
```

- [ ] **Step 2: Write the implementation**

Create `clients/qt_observer/src/CredentialStore.cpp` with: `saveCredential` writes `m_settings.setValue("byokey/"+provider, raw)`; `hasCredential` checks non-empty; `maskedCredential` returns `mask(rawCredential(...))`; `mask` shows first 3 + "••••" + last 4 (or "" when empty); `clearCredential` removes the QSettings value, emits `credentialChanged`, and fires a `QNetworkAccessManager` DELETE to `m_baseUrl + "/api/credentials/" + provider`; `syncCredentialToServer` POSTs `{"provider":provider,"api_key":raw}` with `Content-Type: application/json` to `m_baseUrl + "/api/credentials"`, emitting `syncSucceeded`/`syncFailed` (reason mapped from HTTP status to a key-free string — never include the response body verbatim). `rawCredential` stays private (not `Q_INVOKABLE`).

(Mirror `ObserverApiClient.cpp`'s `QNetworkAccessManager` usage and base-url wiring. Keep request/reply error strings key-free.)

- [ ] **Step 3: Register in CMake + main.cpp**

In `clients/qt_observer/CMakeLists.txt`, add `src/CredentialStore.cpp` and `src/CredentialStore.h` to the `qt_add_executable(appqt_observer ...)` sources (alongside `ObserverApiClient`). In `main.cpp`, set the base url on the `CredentialStore` singleton the same way `ObserverApiClient` gets `--observer-base-url` (locate the singleton instance via the QML engine, or expose a setter wired before `engine.load`). Mirror the existing ObserverApiClient base-url plumbing exactly.

- [ ] **Step 4: Build**

Run: `cd G:/Werewolf-agent && export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH" && "F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer 2>&1 | tail -5`
Expected: build exits 0 (CredentialStore compiles + MOC + QML singleton registered).

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/src/CredentialStore.h clients/qt_observer/src/CredentialStore.cpp clients/qt_observer/CMakeLists.txt clients/qt_observer/main.cpp
git commit -m "feat(qt): CredentialStore QObject (QSettings dev-only, masked, server sync; no raw-key to QML)"
```

---

## Task 8: MatchSetupView credential panel + arming gate + save→sync states

**Files:** Modify `clients/qt_observer/qml/MatchSetupView.qml`

- [ ] **Step 1: Add the inline credential panel near `ModeControl`**

Insert a panel after the `ModeControl` block (`MatchSetupView.qml:~118`). It shows, for the current profile's live provider (deepseek this slice):
- a masked `TextField` (`objectName: "setupCredentialField"`, `echoMode: TextInput.Password`, placeholder `已保存:<masked>` when `CredentialStore.hasCredential("deepseek")` else `输入 DeepSeek API Key`); the field is NEVER pre-filled with the stored key.
- `保存` button (`objectName: "setupCredentialSave"`) → `CredentialStore.saveCredential("deepseek", field.text); CredentialStore.syncCredentialToServer("deepseek"); field.clear()`.
- `清除` button (`objectName: "setupCredentialClear"`) → `CredentialStore.clearCredential("deepseek")`.
- a status `Text` (`objectName: "setupCredentialStatus"`) bound to a `_credStatus` helper (Step 2).

- [ ] **Step 2: Add the status state machine**

Add properties + a helper to `MatchSetupView`:

```qml
    property bool _credSynced: false
    property string _credSyncError: ""
    Connections {
        target: CredentialStore
        function onSyncSucceeded(p) { if (p === "deepseek") { root._credSynced = true; root._credSyncError = "" } }
        function onSyncFailed(p, reason) { if (p === "deepseek") { root._credSynced = false; root._credSyncError = reason } }
        function onCredentialChanged(p) { if (p === "deepseek") { root._credSynced = false; root._credSyncError = "" } }
    }
    // Status string per spec §3.6.
    readonly property string _credStatus: {
        var hasLocal = CredentialStore.hasCredential("deepseek")
        var envAvail = ObserverClient.liveAvailable && !hasLocal   // server reports available w/o local key => env
        if (root._credSyncError !== "") return I18n.t("本地已保存,同步失败,无法启动真实 AI", "Saved locally, sync failed — cannot run live")
        if (hasLocal && root._credSynced) return I18n.t("已配置凭证(本地)", "Credential configured (local)")
        if (hasLocal && !root._credSynced) return I18n.t("本地已保存,尚未同步到 server", "Saved locally, not yet synced")
        if (envAvail) return I18n.t("使用服务器环境凭证", "Using server env credential")
        return I18n.t("未配置", "Not configured")
    }
```

- [ ] **Step 3: Gate arming + no-silent-env-fallback at launch**

- Arming: keep `ModeControl` live arming gated on `ObserverClient.liveAvailable` (server posture already = client-or-env credential available).
- No-silent-fallback (spec §3.7): in the Launch button `onClicked`, when `setupModeControl.resolvedMode === "live"` AND `CredentialStore.hasCredential("deepseek")` AND `!root._credSynced` → do NOT launch; surface `_credStatus` (sync-failed/not-synced) instead. Only when there is no local key may the launch proceed on the server env fallback.

```qml
            onClicked: {
                if (setupModeControl.resolvedMode === "live"
                        && CredentialStore.hasCredential("deepseek")
                        && !root._credSynced) {
                    // local key present but not synced -> block; never silent env fallback
                    return
                }
                ObserverClient.launchFromProfile(root.editedProfile, setupModeControl.resolvedMode)
            }
```

- [ ] **Step 4: Build + qmllint**

Run: `cd G:/Werewolf-agent && export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH" && "F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer 2>&1 | tail -3 && cd clients/qt_observer && qmllint -I .tmp/qt-observer-build qml/MatchSetupView.qml 2>&1 | grep -i "error:" || echo "(no Error lines)"`
Expected: build exit 0, no qmllint `Error:` lines.

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/qml/MatchSetupView.qml
git commit -m "feat(qt): MatchSetupView credential panel + arming gate + save->sync states (no silent env fallback)"
```

---

## Task 9: Qt static-contract guards

**Files:** Modify `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Add the guards**

Add assertions: (a) `MatchSetupView.qml` contains objectNames `setupCredentialField`, `setupCredentialSave`, `setupCredentialClear`, `setupCredentialStatus`; (b) `CredentialStore.h` does NOT contain `getRawKey` and does NOT mark `rawCredential` as `Q_INVOKABLE`; (c) `CredentialStore.cpp` uses `QSettings` and carries a `dev-only` comment; (d) forbidden-leak guard: no QML file passes a raw key into a log/Text binding (reuse the existing forbidden-pattern scan; add `getRawKey` to the forbidden list). Follow the file's existing assertion style (read file text, assert substrings / regex).

- [ ] **Step 2: Run the static contract**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract 2>&1 | grep -E "^(OK|FAILED|Ran)"`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_qt_observer_static_contract.py
git commit -m "test(qt): static-contract guards for credential panel + no raw-key exposure"
```

---

## Task 10: Full verification

**Files:** none

- [ ] **Step 1: New + adjacent Python suites green**

Run:
```bash
cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest \
  tests.test_credential_store tests.test_observer_credentials_endpoint \
  tests.test_observer_byo_key_launch tests.test_qt_observer_static_contract 2>&1 | grep -E "^(OK|FAILED|Ran)"
```
Expected: `OK`.

- [ ] **Step 2: Full suite vs baseline (only known socket errors)**

Run:
```bash
cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest discover -s tests 2>/tmp/p2b.txt 1>/dev/null; grep -E "^(Ran|OK|FAILED)" /tmp/p2b.txt; echo "non-socket failures:"; grep -E "^(FAIL|ERROR):" /tmp/p2b.txt | grep -v "test_observer_server"
```
Expected: the only errors are the pre-existing `test_observer_server` socket block; "non-socket failures" list EMPTY.

- [ ] **Step 3: Secret-scan the new server code paths**

Run a focused check that no new artifact/response embeds a key (the per-test secret scans already assert this; this is a belt-and-suspenders grep):
```bash
cd G:/Werewolf-agent && grep -rnE "getRawKey|setValue\\(.*api_key" clients/qt_observer/src/CredentialStore.cpp || echo "(no raw-key exposure)"
```
Expected: only the intended `byokey/<provider>` QSettings write; no `getRawKey`.

- [ ] **Step 4: Qt build + qmllint final**

Run: `cd G:/Werewolf-agent && export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH" && "F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer 2>&1 | tail -2`
Expected: `Built target appqt_observer`.

- [ ] **Step 5: Forbidden-files diff empty**

Run:
```bash
cd G:/Werewolf-agent && git diff main --stat -- \
  src/werewolf_eval/emergent_engine.py src/werewolf_eval/game_engine.py \
  src/werewolf_eval/scoring.py src/werewolf_eval/attribution.py \
  src/werewolf_eval/settlement_bundle.py src/werewolf_eval/observer_visibility.py \
  src/werewolf_eval/deepseek_provider.py docs/PROJECT_MAP.md
echo "(empty above = good)"
```
Expected: empty.

- [ ] **Step 6: (Optional) screenshot the credential panel**

Per the qt-observer-build-verify recipe, add a temp grab harness that navigates to MatchSetup, grab a PNG, Read it to confirm the panel renders (masked field + status row), then remove the harness.

---

## Task 11: PR

- [ ] **Step 1: Push (no-proxy)**

```bash
cd G:/Werewolf-agent && git -c http.proxy= -c https.proxy= push -u origin p2-b-1-byo-key
```

- [ ] **Step 2: Open PR** (proxy env stripped) — `gh pr create --base main --head p2-b-1-byo-key --title "feat: P2-B-1 BYO-key credential relay + server-executed DeepSeek live" --body "<spec summary + verification>"`.

- [ ] **Step 3: Merge after review** — `gh pr merge <n> --squash --delete-branch`, then sync local main.

---

## Self-Review (completed by plan author)

**Spec coverage:**
- §3.1 in-memory store (injected, locked, redacted repr) → Task 1 ✓
- §3.2 POST/DELETE endpoint (JSON-only incl. charset prefix, deepseek-only, no echo, no body log, loopback, body cap) → Task 3 ✓
- §3.3 capability split (server ability vs credential status; client-or-env) → Task 2 ✓
- §3.4 launch builds launcher from in-memory key, env fallback, resolved-profile no key → Task 4 ✓
- §3.5 CredentialStore Qt API (has/masked/save/clear/sync, no getRawKey) → Task 7 ✓
- §3.6 inline panel + save→sync middle states → Task 8 ✓
- §3.7 arming UX gate + no-silent-env-fallback → Task 8 Step 3 ✓
- §5 security invariants (key never in artifact/log/error; loopback; QSettings dev-only) → Tasks 3/4/5/7/9 ✓
- §6 error sanitize to provider_failure/provider_auth_failed/missing_api_key → Task 5 ✓
- §6 clear semantics (does not affect running run — launcher copies cred at start) → Task 4 (launcher built+bound at launch) + Task 7 (DELETE clears store) ✓
- §7 test matrix (store/endpoint/capability/launch/error/secret-scan/Qt-contract) → Tasks 1–5, 9, 10 ✓
- §8 allowlist/forbidden → File Structure + Task 10 Step 5 ✓

**Placeholder scan:** Python steps carry complete code. C++/QML steps (Task 7 Step 2, Task 8 Step 1) describe exact behavior + signatures + objectNames rather than full bodies — flagged as the only prose-spec steps; the implementer mirrors the existing `ObserverApiClient.cpp` / QML patterns. Acceptable because the public interface (header, objectNames, QSettings key, endpoints) is fully pinned.

**Type/name consistency:** `CredentialStore` (Python: `set/get/has/clear`; C++: `hasCredential/maskedCredential/saveCredential/clearCredential/syncCredentialToServer`), `ObserverServerState.{credential_store, live_launcher_factory, env_key_available}`, `_credentials_post_result/_credentials_delete_result/_resolve_live_launcher_for_launch/_sanitize_launcher_error/_is_loopback`, endpoint `/api/credentials` + `/api/credentials/{provider}`, objectNames `setupCredential{Field,Save,Clear,Status}` — consistent across tasks.
