"""docs/gold-game ``g001`` fixture constants — the one place the scorer knows the
gold game by name (health-check B-3: lifted from ~10 scattered literals in
``scoring.py``). Everything here is byte-load-bearing for the s2/s5 expected
fixtures; change only together with regenerated fixtures. List/dict constants are
returned by reference (e.g. ``_known_rubric_gaps``) — treat them as immutable."""

from __future__ import annotations

from typing import Any

GOLD_GAME_ID = "g001"
GOLD_SCORE_ID_PREFIX = "s2_g001"
GOLD_SCORE_LOG_ID_S2 = "s2_g001_expected_score_log"
GOLD_SCORE_LOG_ID_S5 = "s5_g001_expected_score_log"
GOLD_METRICS_ID_S2 = "s2_g001_expected_metrics"
GOLD_METRICS_ID_S5 = "s5_g001_expected_metrics"
GOLD_SOURCE_GAME_LOG = "docs/gold-game/g001-game-log.json"
GOLD_E007_EVENT_ID = "g001_e007"
GOLD_E007_NOTE = (
    "Wolf team chose a villager target; p5 is later revealed as villager, while "
    "g001_e009 records that the Night 1 save prevented the kill from taking effect."
)
GOLD_KNOWN_RUBRIC_GAPS: list[dict[str, Any]] = [
    {
        "gap": "werewolf_day_vote_without_elimination",
        "events": ["g001_e033"],
        "S2_policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
    },
    {
        "gap": "witch_day_vote_outcome_not_explicit",
        "events": ["g001_e019", "g001_e034"],
        "S2_policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
    },
]
