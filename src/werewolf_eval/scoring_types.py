"""Score/metrics datatypes, serializers, and scoring constants (health-check B-3 split).

Moved verbatim from ``scoring.py``; that module remains the public facade —
import from ``werewolf_eval.scoring`` unless you are inside the scoring package."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from werewolf_eval.evaluation_versions import SCORING_VERSION, UNKNOWN_VERSION, evaluation_bucket as _evaluation_bucket


@dataclass(frozen=True)
class ScoreRecord:
    score_id: str
    event_id: str
    decision_id: str | None
    actor: str
    scope: str
    round: int
    phase: str
    action_type: str
    target: str
    outcome_score: int
    decision_quality_score: int
    rule_integrity_score: int
    rules_triggered: list[str]
    evidence_event_ids: list[str]
    notes: str


@dataclass(frozen=True)
class DecisionAssessment:
    decision_id: str | None
    decision_quality_score: int
    rule_integrity_score: int
    rules_triggered: list[str]
    evidence_event_ids: list[str]
    notes: list[str]


@dataclass(frozen=True)
class ScoringBoundary:
    decision_quality_score: int
    decision_quality_reason: str
    ai_annotations: str
    rule_integrity_default: int
    rule_integrity_reason: str


@dataclass(frozen=True)
class ScoreLog:
    score_log_id: str
    game_id: str
    source_game_log: str
    source_label: str
    phase: str
    scoring_boundary: ScoringBoundary
    records: list[ScoreRecord]


@dataclass(frozen=True)
class ResultMetrics:
    winner: str
    game_length: int
    werewolf_survival_rate: float
    villager_survival_rate: float
    margin: int
    werewolf_win_speed: float | None
    villager_win_efficiency: float | None


@dataclass(frozen=True)
class ProcessMetrics:
    vote_accuracy_by_player: dict[str, dict[str, float | int]]
    survival_rounds: dict[str, int]
    contradiction_count_by_player: dict[str, int]
    info_leak_count_by_player: dict[str, int]
    seer_metrics: dict[str, Any]
    witch_metrics: dict[str, Any]
    team_metrics: dict[str, Any]


@dataclass(frozen=True)
class ScoreSummary:
    player_outcome_scores: dict[str, int]
    team_outcome_scores: dict[str, int]
    player_rule_integrity_scores: dict[str, int]
    player_decision_quality_scores: dict[str, int]


@dataclass(frozen=True)
class MetricsSummary:
    metrics_id: str
    game_id: str
    source_game_log: str
    source_score_log: str
    source_label: str
    result_metrics: ResultMetrics
    process_metrics: ProcessMetrics
    score_summary: ScoreSummary
    metrics_deferred_to_later_spikes: list[dict[str, str]]
    known_rubric_gaps_recorded_not_fixed: list[dict[str, Any]]


def score_log_to_dict(
    score_log: ScoreLog, *, evaluation_bucket: dict[str, str] | None = None
) -> dict[str, Any]:
    d = asdict(score_log)
    # Spec 2026-06-10-prompt-versioning §4.3/§4.5: score records always carry the
    # bucket. Callers without version context (re-scoring legacy logs) get the
    # honest "unknown" stamp — browsable, never rankable.
    d["evaluation_bucket"] = (
        dict(evaluation_bucket)
        if evaluation_bucket is not None
        else _evaluation_bucket(
            rules_version=UNKNOWN_VERSION,
            prompt_version=UNKNOWN_VERSION,
            scoring_version=SCORING_VERSION,
        )
    )
    return d


def metrics_summary_to_dict(summary: MetricsSummary) -> dict[str, Any]:
    return asdict(summary)


SCORE_RELEVANT_EVENT_TYPES = {
    "werewolf_kill",
    "seer_check",
    "witch_save",
    "witch_poison",
    "player_vote",
}

KEY_VILLAGER_ROLES = {"seer", "witch", "hunter", "guard"}

SCORE_RELEVANT_DECISION_ACTIONS = SCORE_RELEVANT_EVENT_TYPES

SEMANTIC_QUALITY_SCORE_BY_LABEL = {
    "supported_good": 2,
    "supported_neutral": 1,
    "random_or_default": 0,
    "unsupported": -1,
    "contradicted": -2,
}
