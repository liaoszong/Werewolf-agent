"""CLI entry point for the local observer server (G2a; G3-1 live opt-in)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Mapping

from werewolf_eval.deepseek_launcher import DEFAULT_MAX_LIVE_REQUESTS
from werewolf_eval.release_metadata import read_version
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
    # B5 closeout: --api-key-env is deprecated (retained for CLI back-compat).
    # The deepseek-only env-key fallback has been retired; live launches now
    # require a client-supplied credential via POST /api/credentials.
    parser.add_argument(
        "--api-key-env",
        default="DEEPSEEK_API_KEY",
        help="(deprecated, ignored) env-key fallback was retired in B5 closeout",
    )
    parser.add_argument("--max-live-requests", type=int, default=DEFAULT_MAX_LIVE_REQUESTS)
    parser.add_argument("--deepseek-base-url", default="https://api.deepseek.com")
    # Default aligns with the P2-A-2 emergent live-smoke calibration; overridable.
    parser.add_argument("--deepseek-model", default="deepseek-v4-flash")
    parser.add_argument("--version", action="version",
                        version=f"observer-server {read_version()}")
    return parser


def resolve_live_launcher(
    args: argparse.Namespace, environ: Mapping[str, str]
) -> bool:
    """Pure resolver: map parsed args to ``live_enabled`` for
    ``create_observer_server``.

    B5 closeout: the deepseek-only env-key fallback has been retired. The
    ``--api-key-env`` flag is retained for CLI back-compat but ignored (with a
    deprecation warning if the env var it names is actually set). Live launches
    now require a client-supplied credential for every provider via
    POST /api/credentials; the old single-provider ``live_launcher_factory`` was
    write-only (never read by the launch path) and has been removed."""
    if not args.allow_live_api:
        return False
    # Deprecation warning: if the named env var is set, warn that it's ignored.
    api_key_env_name = getattr(args, "api_key_env", "DEEPSEEK_API_KEY")
    if environ.get(api_key_env_name):
        print(
            f"warning: {api_key_env_name} is set but --api-key-env is deprecated "
            f"and ignored (B5 closeout: use POST /api/credentials instead)",
            file=sys.stderr,
        )
    return True


def main() -> int:
    args = build_arg_parser().parse_args()

    live_enabled = resolve_live_launcher(args, os.environ)

    server = create_observer_server(
        args.host,
        args.port,
        Path(args.runs_dir),
        launcher=default_emergent_fake_launcher,
        live_enabled=live_enabled,
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
