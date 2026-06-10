"""Evaluation comparison tuple — single source (spec 2026-06-10-prompt-versioning).

Deliberately imports NOTHING from werewolf_eval: run-status / manifest / scoring
writers all call evaluation_bucket(), and none of them may be forced to import the
scoring main module (circular-import guard, spec §4.1). scoring.py imports
SCORING_VERSION from here — never the reverse.
"""
from __future__ import annotations

import json
from pathlib import Path

SCORING_VERSION = "scoring_v1"

# Legacy artifacts with no version fields read as "unknown" for every missing
# component. The unknown bucket is browsable but never rankable (spec §4.5).
UNKNOWN_VERSION = "unknown"


def read_manifest_bucket(run_dir: Path) -> dict[str, str] | None:
    """The run's stamped bucket, read from prompt-manifest.json (the single
    source). None for legacy runs without a stamped manifest."""
    try:
        manifest = json.loads(
            (run_dir / "prompt-manifest.json").read_text(encoding="utf-8")
        )
        bucket = manifest.get("evaluation_bucket")
        return dict(bucket) if isinstance(bucket, dict) else None
    except (OSError, ValueError):
        return None


def evaluation_bucket(
    *, rules_version: str, prompt_version: str, scoring_version: str
) -> dict[str, str]:
    """The leaderboard bucket: results are comparable ONLY within one identical
    tuple. All stamping sites MUST call this — hand-assembled tuples are forbidden
    (single source for the key format)."""
    return {
        "rules_version": rules_version,
        "prompt_version": prompt_version,
        "scoring_version": scoring_version,
        "comparison_key": f"{rules_version}__{prompt_version}__{scoring_version}",
    }
