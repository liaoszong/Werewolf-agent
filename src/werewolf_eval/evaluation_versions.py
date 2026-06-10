"""Evaluation comparison tuple — single source (spec 2026-06-10-prompt-versioning).

Deliberately imports NOTHING from werewolf_eval: run-status / manifest / scoring
writers all call evaluation_bucket(), and none of them may be forced to import the
scoring main module (circular-import guard, spec §4.1). scoring.py imports
SCORING_VERSION from here — never the reverse.
"""
from __future__ import annotations

SCORING_VERSION = "scoring_v1"

# Legacy artifacts with no version fields read as "unknown" for every missing
# component. The unknown bucket is browsable but never rankable (spec §4.5).
UNKNOWN_VERSION = "unknown"


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
