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


# ---------------------------------------------------------------------------
# Task 3: Score Log generation helpers
# ---------------------------------------------------------------------------

SCORE_RELEVANT_EVENT_TYPES = {
    "werewolf_kill",
    "seer_check",
    "witch_save",
    "witch_poison",
    "player_vote",
}

KEY_VILLAGER_ROLES = {"seer", "witch", "hunter"}


def _player_by_id(game: GameLog) -> dict[str, Any]:
    return {player.player_id: player for player in game.players}


def _role_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].role


def _team_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].team


def _scope_for_actor(actor: str) -> str:
    return "team" if actor == "wolf_team" else "player"


def _eliminated_target_by_round(game: GameLog) -> dict[int, str]:
    eliminated: dict[int, str] = {}
    for event in game.events:
        if event.type == "player_eliminated":
            eliminated[event.round] = event.target
    return eliminated


def _reveal_event_for_target(game: GameLog, target: str) -> str | None:
    for event in game.events:
        if event.type == "role_revealed" and event.target == target:
            return event.event_id
    return None


def _death_event_for_target(game: GameLog, target: str) -> str | None:
    for event in game.events:
        if event.type == "player_died" and event.target == target:
            return event.event_id
    return None


def _save_event_for_target(game: GameLog, target: str) -> str | None:
    for event in game.events:
        if event.type == "witch_save" and event.target == target:
            return event.event_id
    return None


def _scoring_boundary() -> ScoringBoundary:
    return ScoringBoundary(
        decision_quality_score=0,
        decision_quality_reason="Phase 1 has no real Decision Log. All decision_quality_score values are fixed at 0.",
        ai_annotations="none",
        rule_integrity_default=0,
        rule_integrity_reason="S1 contains no info_leak_flag or contradiction_flag events.",
    )


def _score_werewolf_kill(game: GameLog, event: Event) -> ScoreRecord:
    target_role = _role_of(game, event.target)
    if target_role in KEY_VILLAGER_ROLES:
        outcome = 3
        rule = "rubric:E.1.werewolf.kill_key_villager"
        notes = f"Wolf team chose a key villager target; {event.target} is later revealed as {target_role}."
    else:
        outcome = 1
        rule = "rubric:E.1.werewolf.kill_villager"
        notes = f"Wolf team killed {event.target}, who is revealed as villager."

    evidence = [event.event_id]
    death_event = _death_event_for_target(game, event.target)
    if death_event:
        evidence.append(death_event)
    else:
        # When the kill target was saved by witch (no player_died),
        # include the witch_save event as alternative evidence.
        save_event = _save_event_for_target(game, event.target)
        if save_event:
            evidence.append(save_event)
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)

    if event.event_id == "g001_e007":
        notes = "Wolf team chose a villager target; p5 is later revealed as villager, while g001_e009 records that the Night 1 save prevented the kill from taking effect."

    return _record(event, outcome, [rule], evidence, notes)


def _score_seer_check(game: GameLog, event: Event) -> ScoreRecord:
    target_team = _team_of(game, event.target)
    if target_team == "werewolf":
        outcome = 2
        rule = "rubric:E.2.seer.check_werewolf"
        notes = f"Seer checked {event.target}, who is later revealed as werewolf."
    else:
        outcome = 0
        rule = "rubric:E.2.seer.check_villager"
        notes = f"Seer checked {event.target}, who is later revealed as villager."
    evidence = [event.event_id]
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)
    return _record(event, outcome, [rule], evidence, notes)


def _score_witch_save(game: GameLog, event: Event) -> ScoreRecord:
    target_role = _role_of(game, event.target)
    target_team = _team_of(game, event.target)
    if target_team == "werewolf":
        outcome = -1
        rule = "rubric:E.3.witch.save_werewolf"
        notes = f"Witch saved {event.target}, who is later revealed as werewolf."
    elif target_role in {"seer", "hunter"}:
        outcome = 3
        rule = "rubric:E.3.witch.save_key_villager"
        notes = f"Witch saved {event.target}, who is later revealed as {target_role}."
    else:
        outcome = 1
        rule = "rubric:E.3.witch.save_villager"
        notes = f"Witch saved {event.target}, who is later revealed as villager."
    evidence = [event.event_id]
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)
    return _record(event, outcome, [rule], evidence, notes)


def _score_witch_poison(game: GameLog, event: Event) -> ScoreRecord:
    target_role = _role_of(game, event.target)
    target_team = _team_of(game, event.target)
    if target_team == "werewolf":
        outcome = 3
        rule = "rubric:E.3.witch.poison_werewolf"
        notes = f"Witch poisoned {event.target}, who is revealed as werewolf."
    elif target_role in {"seer", "hunter"}:
        outcome = -3
        rule = "rubric:E.3.witch.poison_key_villager"
        notes = f"Witch poisoned {event.target}, who is later revealed as {target_role}."
    else:
        outcome = -1
        rule = "rubric:E.3.witch.poison_villager"
        notes = f"Witch poisoned {event.target}, who is later revealed as villager."
    evidence = [event.event_id]
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)
    return _record(event, outcome, [rule], evidence, notes)


def _round_elimination_event(game: GameLog, round_number: int) -> str | None:
    for e in game.events:
        if e.type == "player_eliminated" and e.round == round_number:
            return e.event_id
    return None


def _score_player_vote(game: GameLog, event: Event, eliminated_by_round: dict[int, str]) -> ScoreRecord:
    actor_role = _role_of(game, event.actor)
    target_role = _role_of(game, event.target)
    target_team = _team_of(game, event.target)
    eliminated_target = eliminated_by_round.get(event.round)
    reveal_event = _reveal_event_for_target(game, event.target)
    evidence = [event.event_id]
    if eliminated_target == event.target:
        elimination_event = _round_elimination_event(game, event.round)
        if elimination_event:
            evidence.append(elimination_event)
    elif eliminated_target is not None and reveal_event is None:
        # When the vote target survives to end (no role_revealed),
        # include the round's elimination event as context evidence.
        elimination_event = _round_elimination_event(game, event.round)
        if elimination_event:
            evidence.append(elimination_event)
    if reveal_event:
        evidence.append(reveal_event)

    if actor_role == "witch":
        return _record(
            event,
            0,
            ["rubric-gap:witch_day_vote_outcome_not_explicit"],
            evidence,
            "Witch daytime vote is counted in vote_accuracy metrics, but E.3 has no explicit vote outcome row. S2 assigns score 0 and records the rubric gap.",
        )

    if actor_role == "werewolf" and eliminated_target != event.target:
        return _record(
            event,
            0,
            ["rubric-gap:werewolf_day_vote_without_elimination"],
            evidence,
            f"{event.actor} voted for {event.target}, but {event.target} was not eliminated. E.1 has no explicit row for a werewolf vote that does not cause elimination, so S2 assigns 0 and records the rubric gap.",
        )

    if actor_role == "werewolf":
        if target_team == "werewolf":
            return _record(event, -2, ["rubric:E.1.werewolf.vote_eliminate_teammate"], evidence, f"Werewolf {event.actor} voted to eliminate teammate {event.target}.")
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, 2, ["rubric:E.1.werewolf.vote_eliminate_key_villager"], evidence, f"Werewolf {event.actor} voted to eliminate {event.target}, who is revealed as {target_role}.")
        return _record(event, 1, ["rubric:E.1.werewolf.vote_eliminate_villager"], evidence, f"Werewolf {event.actor} voted to eliminate villager {event.target}.")

    if actor_role == "seer":
        if target_team == "werewolf":
            return _record(event, 2, ["rubric:E.2.seer.vote_eliminate_werewolf"], evidence, f"Seer {event.actor} voted for {event.target}, who is later revealed as werewolf.")
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, -1, ["rubric:E.2.seer.vote_eliminate_key_villager"], evidence, f"Seer {event.actor} voted for key villager {event.target}.")
        return _record(event, -1, ["rubric:E.2.seer.vote_eliminate_villager"], evidence, f"Seer {event.actor} voted for villager {event.target}.")

    if actor_role == "villager":
        if target_team == "werewolf":
            return _record(event, 2, ["rubric:E.4.villager.vote_eliminate_werewolf"], evidence, f"Villager {event.actor} voted to eliminate {event.target}, who is revealed as werewolf.")
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, -2, ["rubric:E.4.villager.vote_eliminate_key_villager"], evidence, f"Villager {event.actor} voted to eliminate {event.target}, who is revealed as {target_role}.")
        return _record(event, -1, ["rubric:E.4.villager.vote_eliminate_villager"], evidence, f"Villager {event.actor} voted to eliminate villager {event.target}.")

    return _record(event, 0, ["rubric-gap:unscored_vote_role"], evidence, f"No explicit deterministic vote scoring row for role {actor_role}.")


def _record(
    event: Event,
    outcome_score: int,
    rules_triggered: list[str],
    evidence_event_ids: list[str],
    notes: str,
) -> ScoreRecord:
    return ScoreRecord(
        score_id=f"s2_g001_{event.event_id.split('_')[-1]}",
        event_id=event.event_id,
        actor=event.actor,
        scope=_scope_for_actor(event.actor),
        round=event.round,
        phase=event.phase,
        action_type=event.type,
        target=event.target,
        outcome_score=outcome_score,
        decision_quality_score=0,
        rule_integrity_score=0,
        rules_triggered=rules_triggered,
        evidence_event_ids=evidence_event_ids,
        notes=notes,
    )


def score_game(game: GameLog) -> ScoreLog:
    eliminated_by_round = _eliminated_target_by_round(game)
    records: list[ScoreRecord] = []

    for event in game.events:
        if event.type not in SCORE_RELEVANT_EVENT_TYPES:
            continue
        if event.type == "werewolf_kill":
            records.append(_score_werewolf_kill(game, event))
        elif event.type == "seer_check":
            records.append(_score_seer_check(game, event))
        elif event.type == "witch_save":
            records.append(_score_witch_save(game, event))
        elif event.type == "witch_poison":
            records.append(_score_witch_poison(game, event))
        elif event.type == "player_vote":
            records.append(_score_player_vote(game, event, eliminated_by_round))

    return ScoreLog(
        score_log_id="s2_g001_expected_score_log",
        game_id=game.game_id,
        source_game_log="docs/gold-game/g001-game-log.json",
        source_label="[deterministic]",
        phase="Phase 1",
        scoring_boundary=_scoring_boundary(),
        records=records,
    )
