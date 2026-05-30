from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from werewolf_eval.game_log import Event, GameLog
from werewolf_eval.scoring import MetricsSummary, ScoreLog


ATTRIBUTION_RULE_IDS = [
    "attribution:F.1.critical_vote",
    "attribution:F.2.information_gap",
    "attribution:F.3.witch_misfire",
    "attribution:F.4.vote_deviation",
    "attribution:F.5.successful_disguise",
]


@dataclass(frozen=True)
class AttributionBoundary:
    method: str
    ai_annotations: str
    free_text_reasoning: str
    decision_quality_score: int
    notes: str


@dataclass(frozen=True)
class TurnPoint:
    turn_point_id: str
    rule_id: str
    rule: str
    round: int
    actor: str
    subject: str
    description_template: str
    impact_score: float
    impact_sign: str
    impact_score_policy: str
    evidence_event_ids: list[str]


@dataclass(frozen=True)
class TopAttribution:
    turn_point_id: str
    rule_id: str
    description_template: str
    selection_policy: str


@dataclass(frozen=True)
class RuleEvaluation:
    status: str
    triggered_turn_point_ids: list[str]
    notes: str


@dataclass(frozen=True)
class ValidationNote:
    type: str
    event_ids: list[str]
    notes: str


@dataclass(frozen=True)
class AttributionResult:
    attribution_id: str
    game_id: str
    source_game_log: str
    source_score_log: str
    source_metrics_summary: str
    source_label: str
    phase: str
    attribution_boundary: AttributionBoundary
    turn_points: list[TurnPoint]
    top_attribution: TopAttribution
    rule_evaluation_summary: dict[str, RuleEvaluation]
    validation_notes: list[ValidationNote]


def attribution_to_dict(result: AttributionResult) -> dict[str, Any]:
    return asdict(result)
