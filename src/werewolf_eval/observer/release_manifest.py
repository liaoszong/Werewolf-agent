"""Write release-manifest.json into each run directory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def write_release_manifest(
    run_dir: Path,
    release_version: str,
    channel: str = "dev",
    git_commit: str = "unknown",
    build_timestamp: str | None = None,
    observer_protocol_version: int = 1,
) -> None:
    """Atomically write release-manifest.json into run_dir.

    Must be called after run directory is created, before run execution.
    Raises OSError on failure -- caller must fail the run.
    """
    ts = build_timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "release_version": release_version,
        "channel": channel,
        "git_commit": git_commit,
        "build_timestamp": ts,
        "bootstrapper_version": release_version,
        "server_version": release_version,
        "observer_protocol_version": observer_protocol_version,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    path = run_dir / "release-manifest.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
