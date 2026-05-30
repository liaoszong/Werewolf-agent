from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from werewolf_eval.game_log import Event, GameLog


@dataclass(frozen=True)
class ScoreRecord:
    score_id: str
    event_id: str
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


def score_log_to_dict(score_log: ScoreLog) -> dict[str, Any]:
    return asdict(score_log)


def metrics_summary_to_dict(summary: MetricsSummary) -> dict[str, Any]:
    return asdict(summary)
