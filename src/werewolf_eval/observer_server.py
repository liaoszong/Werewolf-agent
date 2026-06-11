"""Local observer HTTP server with live run state (G2a).

Facade module (SYS-C2 split): the implementation lives in
``werewolf_eval.observer.*`` (security / state / run_manager / credentials_api
/ launch / sse / routes / handler); this module re-exports the historical
public-and-private import surface — do-not-touch test files and
``run_observer_server`` import these names from here — plus the server
factory. All I/O is local-filesystem only.
"""

from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from werewolf_eval.deepseek_launcher import build_multi_provider_launcher
from werewolf_eval.observer.credentials_api import (
    _CREDENTIAL_PROVIDERS,
    _credentials_delete_result,
    _credentials_post_result,
    _provider_models_result,
)
from werewolf_eval.observer.handler import _PROFILE_NAME_RE, ObserverRequestHandler
from werewolf_eval.observer.run_manager import (
    _build_capabilities_payload,
    _check_live_capability,
    _check_live_profile_shape,
    _map_launcher_exit_reason,
    _provider_live_posture,
    _read_events_jsonl_safe,
    _read_execution_mode,
    _resolve_live_launcher_for_launch,
    _run_delete_result,
    _sanitize_launcher_error,
    _schema_payload,
)
from werewolf_eval.observer.security import (
    _LOOPBACK_HOSTNAMES,
    _hostname_of,
    _is_loopback_hostname,
)
from werewolf_eval.observer.state import ObserverServerState, RunLauncher
from werewolf_eval.profile_config import build_default_profile, list_profiles
from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime


def default_fake_launcher(run_id: str, run_dir: Path) -> int:
    return run_fake_runtime(game_id=run_id, out_dir=run_dir)


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def _seed_default_profile(profiles_dir: Path) -> None:
    """Seed a baseline default profile when the dir has no VALID profile yet, so a
    fresh setup page is never an empty 'no profiles' state. Idempotent and
    non-fatal: never overwrites an existing file (respects user edits); a read-only
    dir is silently ignored (the empty state simply shows)."""
    if any(entry["valid"] for entry in list_profiles(profiles_dir)):
        return
    profile = build_default_profile()
    path = profiles_dir / f"{profile['name']}.json"
    if path.exists():
        return
    try:
        path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def create_observer_server(
    host: str,
    port: int,
    runs_dir: Path,
    launcher: RunLauncher | None = None,
    profiles_dir: Path | None = None,
    live_enabled: bool = False,
    live_launcher: RunLauncher | None = None,
    live_launcher_factory: Callable[..., RunLauncher] | None = None,
    env_key_available: bool = False,
    live_max_requests: int = 32,
    live_max_tokens: int = 256,
    seed_default_profile: bool = False,
) -> ThreadingHTTPServer:
    """Create and configure a threaded observer HTTP server.

    ``live_enabled``/``live_launcher`` wire the G3-1 opt-in live path: live is
    the only mode that consults them, and only a profile launch (not a template
    launch) may select it.  Both default off so the server stays fake-only.

    ``live_launcher_factory`` is the per-launch builder used with a client-supplied
    key (P2-B-1 BYO-key path); ``env_key_available`` records whether the server
    started with an env key (back-compat signal for capability gate).

    P2-B-4: when live is enabled, a ``multi_provider_launcher_factory`` is built
    with the server live limits — the per-seat multi-provider launch path."""
    if launcher is None:
        launcher = default_fake_launcher
    runs_dir.mkdir(parents=True, exist_ok=True)
    if profiles_dir is None:
        profiles_dir = runs_dir.parent / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    # Opt-in (the CLI passes True): a fresh server isn't an empty setup page. Tests
    # using this factory leave it off so their temp profiles dirs stay pristine.
    if seed_default_profile:
        _seed_default_profile(profiles_dir)

    multi_provider_launcher_factory: Callable[..., RunLauncher] | None = None
    if live_enabled:
        def multi_provider_launcher_factory(resolved_seats, credentials):  # type: ignore[misc]
            return build_multi_provider_launcher(
                resolved_seats=resolved_seats,
                credentials=credentials,
                max_requests=live_max_requests,
                default_max_tokens=live_max_tokens,
            )

    state = ObserverServerState(
        runs_dir=runs_dir,
        launcher=launcher,
        profiles_dir=profiles_dir,
        live_enabled=live_enabled,
        live_launcher=live_launcher,
        live_launcher_factory=live_launcher_factory,
        env_key_available=env_key_available,
        multi_provider_launcher_factory=multi_provider_launcher_factory,
    )

    class _BoundHandler(ObserverRequestHandler):
        pass

    server = ThreadingHTTPServer((host, port), _BoundHandler)
    server.state = state  # type: ignore[attr-defined]
    return server
