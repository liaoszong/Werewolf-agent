"""Observer server factory (SYS-C2 split)."""

from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from werewolf_eval.deepseek_launcher import build_multi_provider_launcher
from werewolf_eval.observer.handler import ObserverRequestHandler
from werewolf_eval.observer.state import ObserverServerState, RunLauncher
from werewolf_eval.profile_config import build_default_profile, list_profiles
from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime


def default_fake_launcher(run_id: str, run_dir: Path) -> int:
    return run_fake_runtime(game_id=run_id, out_dir=run_dir)


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
    configs_dir: Path | None = None,
    live_enabled: bool = False,
    live_max_requests: int = 32,
    live_max_tokens: int = 256,
    seed_default_profile: bool = False,
) -> ThreadingHTTPServer:
    """Create and configure a threaded observer HTTP server.

    ``live_enabled`` wires the G3-1 opt-in live path: live is the only mode that
    consults it, and only a profile launch (not a template launch) may select it.
    Defaults off so the server stays fake-only.

    P2-B-4: when live is enabled, a ``multi_provider_launcher_factory`` is built
    with the server live limits — the per-seat multi-provider launch path.

    B5 closeout: the deepseek-only env-key fallback (``live_launcher``,
    ``env_key_available``) has been retired. Live launches now require a
    client-supplied credential for every provider via POST /api/credentials."""
    if launcher is None:
        launcher = default_fake_launcher
    runs_dir.mkdir(parents=True, exist_ok=True)
    if profiles_dir is None:
        profiles_dir = runs_dir.parent / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    if configs_dir is None:
        configs_dir = runs_dir / "user-configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
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
        configs_dir=configs_dir,
        live_enabled=live_enabled,
        multi_provider_launcher_factory=multi_provider_launcher_factory,
    )

    class _BoundHandler(ObserverRequestHandler):
        pass

    server = ThreadingHTTPServer((host, port), _BoundHandler)
    server.state = state  # type: ignore[attr-defined]
    return server
