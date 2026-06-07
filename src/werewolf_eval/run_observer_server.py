"""CLI entry point for the local observer server (G2a; G3-1 live opt-in)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Mapping

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
) -> tuple[bool, RunLauncher | None]:
    """Pure resolver: map parsed args + an env mapping to
    ``(live_enabled, live_launcher)`` for ``create_observer_server``.

    The API key is read **once** from ``environ`` and flows only into the
    launcher closure (provider config + Authorization header) — never logged,
    echoed, or stored elsewhere.  Returns ``live_launcher=None`` when the flag
    is off OR the key is absent (→ ``missing_api_key`` at request time)."""
    if not args.allow_live_api:
        return (False, None)
    api_key = environ.get(args.api_key_env, "")
    if not api_key:
        return (True, None)
    launcher = build_emergent_deepseek_launcher(
        api_key=api_key,
        base_url=args.deepseek_base_url,
        model=args.deepseek_model,
        max_tokens=_LIVE_MAX_TOKENS,
        max_requests=args.max_live_requests,
    )
    return (True, launcher)


def main() -> int:
    args = build_arg_parser().parse_args()

    live_enabled, live_launcher = resolve_live_launcher(args, os.environ)

    server = create_observer_server(
        args.host,
        args.port,
        Path(args.runs_dir),
        launcher=default_emergent_fake_launcher,
        live_enabled=live_enabled,
        live_launcher=live_launcher,
    )
    host, port = server.server_address[:2]
    print("observer_server=started")
    print(f"host={host}")
    print(f"port={port}")
    print(f"runs_dir={Path(args.runs_dir)}")
    # Report the live posture without ever printing the key itself.
    if not live_enabled:
        print("live_api=disabled")
    elif live_launcher is None:
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
