"""Evaluation comparison tuple — single source (spec 2026-06-10-prompt-versioning).

Deliberately imports NOTHING from werewolf_eval: run-status / manifest / scoring
writers all call evaluation_bucket(), and none of them may be forced to import the
scoring main module (circular-import guard, spec §4.1). scoring.py imports
SCORING_VERSION from here — never the reverse.
"""
from __future__ import annotations

import json
from pathlib import Path

SCORING_VERSION = "scoring_v2"

# Legacy artifacts with no version fields read as "unknown" for every missing
# component. The unknown bucket is browsable but never rankable (spec §4.5).
UNKNOWN_VERSION = "unknown"


def rebase_bucket_to_current_scoring(bucket: dict[str, str] | None) -> dict[str, str]:
    """Re-stamp a manifest/legacy bucket to the CURRENT scoring formula.

    Scoring formula changes (e.g. the scoring_v2 default/random vote filtering)
    invalidate any cached settlement computed under an older formula: the same
    game-log + decision-log re-scored today MUST carry today's SCORING_VERSION,
    never the manifest's historical one. The rules_version and prompt_version
    describe the *run inputs* and are preserved as-is (legitimate history); only
    the scoring_version is forced to the current formula. comparison_key is
    always rebuilt through evaluation_bucket() — never hand-assembled.

    None (no manifest / legacy run) -> unknown/unknown/<current scoring> bucket.
    Malformed (non-str / empty) components fall back to UNKNOWN_VERSION.
    Idempotent: a bucket already at the current scoring_version round-trips.
    """
    rules = _clean_component(bucket.get("rules_version")) if bucket else UNKNOWN_VERSION
    prompt = _clean_component(bucket.get("prompt_version")) if bucket else UNKNOWN_VERSION
    return evaluation_bucket(
        rules_version=rules,
        prompt_version=prompt,
        scoring_version=SCORING_VERSION,
    )


def _clean_component(value: object) -> str:
    if isinstance(value, str) and value:
        return value
    return UNKNOWN_VERSION


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
