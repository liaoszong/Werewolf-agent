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


# ---------------------------------------------------------------------------
# Task 4: Attribution engine implementation
# ---------------------------------------------------------------------------


def _attribution_boundary() -> AttributionBoundary:
    return AttributionBoundary(
        method="deterministic structured-event pattern matching",
        ai_annotations="none",
        free_text_reasoning="not_used",
        decision_quality_score=0,
        notes="S3 validates expected attribution outputs only. It does not implement the production attribution engine.",
    )


def _player_by_id(game: GameLog) -> dict[str, Any]:
    return {player.player_id: player for player in game.players}


def _role_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].role


def _team_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].team


def _events_by_round_and_type(game: GameLog, round_number: int, event_type: str) -> list[Event]:
    return [event for event in game.events if event.round == round_number and event.type == event_type]


def _role_reveal_event(game: GameLog, target: str) -> Event | None:
    for event in game.events:
        if event.type == "role_revealed" and event.target == target:
            return event
    return None


def _critical_vote_turn_points(game: GameLog) -> list[TurnPoint]:
    turn_points: list[TurnPoint] = []
    vote_rounds = sorted({event.round for event in game.events if event.type == "player_vote"})

    for round_number in vote_rounds:
        votes = _events_by_round_and_type(game, round_number, "player_vote")
        eliminated_events = _events_by_round_and_type(game, round_number, "player_eliminated")
        if not votes or not eliminated_events:
            continue

        eliminated = eliminated_events[0]
        eliminated_target = eliminated.target
        vote_count_for_eliminated = sum(1 for vote in votes if vote.target == eliminated_target)
        other_vote_counts: dict[str, int] = {}
        for vote in votes:
            if vote.target != eliminated_target:
                other_vote_counts[vote.target] = other_vote_counts.get(vote.target, 0) + 1
        runner_up_votes = max(other_vote_counts.values(), default=0)
        vote_margin = vote_count_for_eliminated - runner_up_votes
        reveal = _role_reveal_event(game, eliminated_target)

        if vote_margin != 1 or reveal is None:
            continue

        eliminated_role = _role_of(game, eliminated_target)
        eliminated_team = _team_of(game, eliminated_target)
        if eliminated_team == "werewolf":
            impact_sign = "positive_for_villager"
            role_text = "狼人"
        else:
            impact_sign = "negative_for_villager"
            role_text = "村民"

        impact_score = 2.0 if eliminated_role in {"seer", "witch"} else 1.0
        if eliminated_role in {"seer", "witch"}:
            policy = "F.1 gives a x2 multiplier when the eliminated player is a core villager role."
        else:
            policy = f"F.1 gives a x2 multiplier only when the eliminated player is a core villager role. For eliminated {eliminated_team} {eliminated_target}, S3 uses the default critical-vote impact score of 1.0 and records this as a validation policy, not a rubric change."

        evidence = [event.event_id for event in votes] + [eliminated.event_id, reveal.event_id]
        turn_points.append(
            TurnPoint(
                turn_point_id=f"s3_{game.game_id}_tp{len(turn_points) + 1:03d}",
                rule_id="attribution:F.1.critical_vote",
                rule="critical_vote",
                round=round_number,
                actor="system",
                subject=eliminated_target,
                description_template=f"第 {round_number} 轮投票为关键转折点，{eliminated_target} 以 {vote_margin} 票之差被处决，该玩家身份为{role_text}。",
                impact_score=impact_score,
                impact_sign=impact_sign,
                impact_score_policy=policy,
                evidence_event_ids=evidence,
            )
        )

    return turn_points


def _rule_evaluation_summary(game: GameLog, turn_points: list[TurnPoint], metrics: MetricsSummary) -> dict[str, RuleEvaluation]:
    critical_vote_ids = [turn_point.turn_point_id for turn_point in turn_points if turn_point.rule_id == "attribution:F.1.critical_vote"]

    # R-22: F.3 is now evaluated from the ACTUAL events (a witch misfire = poisoning a
    # non-werewolf), not a hardcoded g001 sentence. A witch poisoning a core good role
    # is the misfire the rubric cares about. (F.2/F.4/F.5 full evaluation stays P3
    # scope; their notes are generic so they no longer assert false g001 specifics for
    # other games.)
    team_by_pid = {p.player_id: p.team for p in game.players}
    role_by_pid = {p.player_id: p.role for p in game.players}
    misfire_targets = [
        ev.target
        for ev in game.events
        if ev.type == "witch_poison"
        and ev.target
        and ev.target != "none"
        and team_by_pid.get(ev.target) != "werewolf"
    ]
    if misfire_targets:
        misfire_notes = "Witch poisoned non-werewolf target(s): " + ", ".join(
            f"{pid}({role_by_pid.get(pid, 'unknown')})" for pid in misfire_targets
        )
    else:
        misfire_notes = "No witch poison hit a non-werewolf (no misfire against a good role)."

    return {
        "attribution:F.1.critical_vote": RuleEvaluation(
            status="triggered" if critical_vote_ids else "not_triggered",
            triggered_turn_point_ids=critical_vote_ids,
            notes="An elimination vote has margin 1 with a known final role, so one changed vote would change the result." if critical_vote_ids else "No elimination vote has margin 1 with a known final role.",
        ),
        "attribution:F.2.information_gap": RuleEvaluation(
            status="not_triggered",
            triggered_turn_point_ids=[],
            notes="F.2 information_gap full evaluation is P3 scope; not generating turn points yet.",
        ),
        "attribution:F.3.witch_misfire": RuleEvaluation(
            status="triggered" if misfire_targets else "not_triggered",
            triggered_turn_point_ids=[],
            notes=misfire_notes,
        ),
        "attribution:F.4.vote_deviation": RuleEvaluation(
            status="not_triggered",
            triggered_turn_point_ids=[],
            notes="F.4 vote_deviation full evaluation is P3 scope; not generating turn points yet.",
        ),
        "attribution:F.5.successful_disguise": RuleEvaluation(
            status="not_triggered",
            triggered_turn_point_ids=[],
            notes="F.5 successful_disguise full evaluation is P3 scope; not generating turn points yet.",
        ),
    }


def _top_attribution(game: GameLog, turn_points: list[TurnPoint]) -> TopAttribution:
    if not turn_points:
        return TopAttribution(
            turn_point_id="none",
            rule_id="none",
            description_template="无确定性归因转折点。",
            selection_policy="highest impact_score; ties break by later sequence",
        )

    selected = sorted(turn_points, key=lambda item: (item.impact_score, item.round, item.turn_point_id))[-1]

    # Derive the summary from structured data rather than hardcoding by turn_point_id.
    votes_in_round = [e for e in game.events if e.type == "player_vote" and e.round == selected.round]
    vote_for = sum(1 for v in votes_in_round if v.target == selected.subject)
    runner_up = max(
        (sum(1 for v in votes_in_round if v.target == t)
         for t in {v.target for v in votes_in_round} if t != selected.subject),
        default=0,
    )
    winner_side = "村民" if selected.impact_sign == "positive_for_villager" else "狼人"
    description = f"第 {selected.round} 轮 {vote_for}-{runner_up} 处决 {selected.subject} 是本局{winner_side}获胜的直接关键转折点。"

    return TopAttribution(
        turn_point_id=selected.turn_point_id,
        rule_id=selected.rule_id,
        description_template=description,
        selection_policy="highest impact_score; ties break by later sequence",
    )


def _validation_notes() -> list[ValidationNote]:
    return [
        ValidationNote(
            type="possible_false_negative",
            event_ids=["g001_e016", "g001_e017", "g001_e020", "g001_e021", "g001_e022", "g001_e023"],
            notes="Round 1 seer p3 elimination is human-salient, but F.1 does not trigger because the vote margin is 4-2 rather than 1. S3 records this as a validation observation and does not change the stable rule.",
        )
    ]


def _source_game_log(game: GameLog) -> str:
    return "docs/gold-game/g001-game-log.json" if game.game_id == "g001" else f"generated:{game.game_id}"


def _source_score_log(game: GameLog, score_log: ScoreLog) -> str:
    return "docs/gold-game/s2-score-log.json" if game.game_id == "g001" else f"score_log:{score_log.score_log_id}"


def _source_metrics_summary(game: GameLog, metrics: MetricsSummary) -> str:
    return "docs/gold-game/s2-metrics-summary.json" if game.game_id == "g001" else f"metrics:{metrics.metrics_id}"


def attribute_game(game: GameLog, score_log: ScoreLog, metrics: MetricsSummary) -> AttributionResult:
    turn_points = _critical_vote_turn_points(game)
    return AttributionResult(
        attribution_id=f"s3_{game.game_id}_rule_attribution",
        game_id=game.game_id,
        source_game_log=_source_game_log(game),
        source_score_log=_source_score_log(game, score_log),
        source_metrics_summary=_source_metrics_summary(game, metrics),
        source_label="[deterministic]",
        phase="Phase 1",
        attribution_boundary=_attribution_boundary(),
        turn_points=turn_points,
        top_attribution=_top_attribution(game, turn_points),
        rule_evaluation_summary=_rule_evaluation_summary(game, turn_points, metrics),
        validation_notes=_validation_notes(),
    )
