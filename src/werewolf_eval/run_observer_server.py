"""CLI entry point for the local observer server (G2a; G3-1 live opt-in)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Callable, Mapping

from werewolf_eval.deepseek_launcher import (
    DEFAULT_MAX_LIVE_REQUESTS,
    RunLauncher,
    build_emergent_deepseek_launcher,
)
from werewolf_eval.observer_server import create_observer_server
from werewolf_eval.run_emergent_fake_runtime import default_emergent_fake_launcher

# Fixed per-request token cap for live runs (matches the existing CLI runners).
# Not a server flag this slice — timeout/budget are the tunable guardrails.
_LIVE_MAX_TOKENS = 256


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local Werewolf observer server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runs-dir", default=".runs")
    # G3-1 live opt-in (default OFF — server stays fake-only unless asked).
    parser.add_argument("--allow-live-api", action="store_true", default=False)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--max-live-requests", type=int, default=DEFAULT_MAX_LIVE_REQUESTS)
    parser.add_argument("--deepseek-base-url", default="https://api.deepseek.com")
    # Default aligns with the P2-A-2 emergent live-smoke calibration; overridable.
    parser.add_argument("--deepseek-model", default="deepseek-v4-flash")
    return parser


def resolve_live_launcher(
    args: argparse.Namespace, environ: Mapping[str, str]
) -> tuple[bool, Callable[[], RunLauncher] | None, bool, Callable[..., RunLauncher] | None]:
    """Pure resolver: map parsed args + an env mapping to
    ``(live_enabled, env_launcher_factory_or_None, env_key_available, factory_or_None)``
    for ``create_observer_server``.

    The API key is read **once** from ``environ`` and flows only into launcher
    factories (provider config + Authorization header) — never logged, echoed,
    or stored elsewhere.

    - ``env_launcher_factory_or_None``: no-arg factory from the env key
      (back-compat fallback); ``None`` when the flag is off or no env key is
      present. It builds a fresh concrete launcher per run so provider budget
      and trace state cannot bleed across launches.
    - ``env_key_available``: True iff an env key was present at startup.
    - ``factory_or_None``: per-launch builder used with a client-supplied key;
      ``None`` only when the flag is off (factory is always present when live is
      enabled, even with no env key, because a client can supply a key)."""
    if not args.allow_live_api:
        return (False, None, False, None)
    api_key = environ.get(args.api_key_env, "")
    env_key_available = bool(api_key)

    def _build_launcher(key: str, base_url: str | None = None) -> RunLauncher:
        return build_emergent_deepseek_launcher(
            api_key=key,
            base_url=base_url or args.deepseek_base_url,
            model=args.deepseek_model,
            max_tokens=_LIVE_MAX_TOKENS,
            max_requests=args.max_live_requests,
        )

    env_launcher_factory = (
        (lambda: _build_launcher(api_key, args.deepseek_base_url))
        if api_key
        else None
    )

    def factory(key: str, base_url: str | None = None) -> RunLauncher:
        return _build_launcher(key, base_url)

    return (True, env_launcher_factory, env_key_available, factory)


def main() -> int:
    args = build_arg_parser().parse_args()

    live_enabled, env_launcher, env_key_available, factory = resolve_live_launcher(
        args, os.environ
    )

    server = create_observer_server(
        args.host,
        args.port,
        Path(args.runs_dir),
        launcher=default_emergent_fake_launcher,
        live_enabled=live_enabled,
        live_launcher=env_launcher,
        live_launcher_factory=factory,
        env_key_available=env_key_available,
        live_max_requests=args.max_live_requests,
        live_max_tokens=_LIVE_MAX_TOKENS,
        # A fresh server seeds a baseline default profile so the setup page is
        # never an empty 'no profiles' state on first run.
        seed_default_profile=True,
    )
    host, port = server.server_address[:2]
    print("observer_server=started")
    print(f"host={host}")
    print(f"port={port}")
    print(f"runs_dir={Path(args.runs_dir)}")
    # Report the live posture without ever printing the key itself.
    if not live_enabled:
        print("live_api=disabled")
    elif env_launcher is None:
        print("live_api=enabled_no_key")
    else:
        print("live_api=enabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("observer_server=stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
