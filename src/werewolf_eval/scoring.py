"""Scoring facade — stable import surface for the B-3 split.

Implementation lives in ``scoring_types`` (dataclasses/constants/serializers),
``scoring_records`` (Score Log generation), ``scoring_metrics`` (Metrics Summary
aggregation), and ``gold_game_fixtures`` (g001 fixture constants). Import from
``werewolf_eval.scoring`` as before; this module only re-exports."""

from __future__ import annotations

from werewolf_eval.scoring_types import (  # noqa: F401 — facade re-exports (B-3 split)
    DecisionAssessment,
    KEY_VILLAGER_ROLES,
    MetricsSummary,
    ProcessMetrics,
    ResultMetrics,
    SCORE_RELEVANT_DECISION_ACTIONS,
    SCORE_RELEVANT_EVENT_TYPES,
    ScoreLog,
    ScoreRecord,
    ScoreSummary,
    ScoringBoundary,
    SEMANTIC_QUALITY_SCORE_BY_LABEL,
    metrics_summary_to_dict,
    score_log_to_dict,
)
from werewolf_eval.scoring_records import (  # noqa: F401 — facade re-exports (B-3 split)
    _assess_decision,
    _player_by_id,
    _record,
    _role_of,
    _score_id_prefix,
    _score_log_id,
    _score_player_vote,
    _score_seer_check,
    _score_source_label,
    _score_werewolf_kill,
    _score_witch_poison,
    _score_witch_save,
    _scoring_boundary,
    _team_of,
    score_game,
)
from werewolf_eval.scoring_metrics import (  # noqa: F401 — facade re-exports (B-3 split)
    _known_rubric_gaps,
    _result_metrics,
    _score_summary,
    _seer_metrics,
    _team_metrics,
    _vote_accuracy_by_player,
    _witch_metrics,
    summarize_metrics,
)
