"""Single-source release version and metadata helpers.

Reads VERSION from the distribution root. In a PyInstaller frozen bundle,
the VERSION file is placed alongside the executable via --add-data.
In dev mode, walks up from this module's location to find the repo-root VERSION.
"""
from __future__ import annotations

from pathlib import Path


def _dist_root() -> Path:
    """Distribution root containing the VERSION file.

    Frozen: VERSION is next to the executable (onedir layout).
    Dev: walks up from this file to the repo root.
    """
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # Dev: this file is at src/werewolf_eval/release_metadata.py
    return Path(__file__).resolve().parent.parent.parent


def read_version() -> str:
    return (_dist_root() / "VERSION").read_text(encoding="utf-8").strip()


def read_release_metadata(dist_root: Path | None = None) -> dict:
    """Return a dict with release_version and the raw VERSION content.
    dist_root overrides the auto-detected root for testing."""
    root = dist_root or _dist_root()
    ver = (root / "VERSION").read_text(encoding="utf-8").strip()
    return {"release_version": ver}
