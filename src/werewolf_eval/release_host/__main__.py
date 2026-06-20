"""Werewolf-agent bootstrapper entry point."""
from __future__ import annotations
import sys
from werewolf_eval.release_host.lifecycle import release_host_main

if __name__ == "__main__":
    sys.exit(release_host_main())
