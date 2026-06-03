"""CLI entry point for the local observer server (G2a)."""

from __future__ import annotations

import argparse
from pathlib import Path

from werewolf_eval.observer_server import create_observer_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Werewolf observer server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runs-dir", default=".runs")
    args = parser.parse_args()

    server = create_observer_server(args.host, args.port, Path(args.runs_dir))
    host, port = server.server_address[:2]
    print("observer_server=started")
    print(f"host={host}")
    print(f"port={port}")
    print(f"runs_dir={Path(args.runs_dir)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("observer_server=stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
