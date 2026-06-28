"""Werewolf-agent bootstrapper entry point."""
from __future__ import annotations
import sys
from werewolf_eval.release_host.velopack_runtime import run_velopack_app_once
from werewolf_eval.release_host.lifecycle import release_host_main

if __name__ == "__main__":
    run_velopack_app_once()
    sys.exit(release_host_main())
