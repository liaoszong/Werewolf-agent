"""Metrics Summary aggregation — the per-game metrics half of the B-3 split. Moved verbatim from scoring.py; import via the werewolf_eval.scoring facade."""

from __future__ import annotations

from typing import Any

from werewolf_eval.decision_log import DecisionLog
from werewolf_eval.game_log import Event, GameLog
from werewolf_eval.gold_game_fixtures import (
    GOLD_GAME_ID,
    GOLD_KNOWN_RUBRIC_GAPS,
    GOLD_METRICS_ID_S2,
    GOLD_METRICS_ID_S5,
    GOLD_SOURCE_GAME_LOG,
)
from werewolf_eval.scoring_records import (
    _decision_by_event_id,
    _player_by_id,
    _role_of,
    _team_of,
)
from werewolf_eval.scoring_types import (
    MetricsSummary,
    ProcessMetrics,
    ResultMetrics,
    ScoreLog,
    ScoreSummary,
)


# Decision Log decision_types that do NOT represent a genuine model vote:
# the seat produced no deliberate choice, so the vote is engine fallback noise
# and must not enter model-vote process metrics (vote_accuracy / cohesion /
# coordination). Only applied when a real Decision Log is supplied; without one
# there is no reliable decision_type signal and historical behavior is kept.
_FALLBACK_DECISION_TYPES = {"default", "random"}


# ---------------------------------------------------------------------------
# Task 4: Metrics Summary generation helpers
# ---------------------------------------------------------------------------


def _round_float(value: float) -> float:
    return round(value, 6)


def _alive_players_after_game(game: GameLog) -> set[str]:
    dead = {event.target for event in game.events if event.type in {"player_died", "player_eliminated"}}
    return game.player_ids - dead


def _vote_events(game: GameLog, decision_log: DecisionLog | None = None) -> list[Event]:
    # Only player-to-player votes participate in vote metrics. game_log validation
    # permits non-player actors ("system"/"wolf_team") and targets ("none"/"*_team")
    # on a player_vote; the engine never emits them, but replays / hand-written logs
    # can, and the role/team lookups in the metric helpers would KeyError on them.
    players = _player_by_id(game)
    events = [
        event
        for event in game.events
        if event.type == "player_vote" and event.actor in players and event.target in players
    ]
    # scoring_v2: when a real Decision Log is supplied, drop default/random
    # (engine-fallback) votes so they don't pollute model-vote metrics. Without a
    # Decision Log there is no reliable signal and the historical set is returned.
    if decision_log is not None:
        decisions_by_event = _decision_by_event_id(game, decision_log)
        events = [
            event
            for event in events
            if event.event_id not in decisions_by_event
            or decisions_by_event[event.event_id].decision_type not in _FALLBACK_DECISION_TYPES
        ]
    return events


def _vote_accuracy_by_player(game: GameLog, votes: list[Event] | None = None) -> dict[str, dict[str, float | int]]:
    # `votes` is the already-filtered player-to-player vote set computed once in
    # summarize_metrics. It may include scoring_v2 default/random filtering. The
    # legacy form `_vote_accuracy_by_player(game)` recomputes the unfiltered set
    # via _vote_events(game) so direct callers keep their old behavior.
    events = votes if votes is not None else _vote_events(game)
    result = {player.player_id: {"accurate_votes": 0, "total_votes": 0, "vote_accuracy": 0.0} for player in game.players}
    for event in events:  # already filtered to player-to-player votes
        actor_team = _team_of(game, event.actor)
        target_team = _team_of(game, event.target)
        result[event.actor]["total_votes"] += 1
        if actor_team != target_team:
            result[event.actor]["accurate_votes"] += 1
    for item in result.values():
        total = int(item["total_votes"])
        item["vote_accuracy"] = _round_float(float(item["accurate_votes"]) / total) if total else 0.0
    return result
    result = {player.player_id: {"accurate_votes": 0, "total_votes": 0, "vote_accuracy": 0.0} for player in game.players}
    for event in _vote_events(game):  # already filtered to player-to-player votes
        actor_team = _team_of(game, event.actor)
        target_team = _team_of(game, event.target)
        result[event.actor]["total_votes"] += 1
        if actor_team != target_team:
            result[event.actor]["accurate_votes"] += 1
    for item in result.values():
        total = int(item["total_votes"])
        item["vote_accuracy"] = _round_float(float(item["accurate_votes"]) / total) if total else 0.0
    return result


def _survival_rounds(game: GameLog) -> dict[str, int]:
    survival = {player.player_id: game.result.end_round for player in game.players}
    for event in game.events:
        if event.type in {"player_died", "player_eliminated"} and event.target in survival:
            survival[event.target] = min(survival[event.target], event.round)
    return survival


def _zero_counts(game: GameLog) -> dict[str, int]:
    return {player.player_id: 0 for player in game.players}


def _seer_metrics(game: GameLog) -> dict[str, Any]:
    seer = next(player.player_id for player in game.players if player.role == "seer")
    checks = [event for event in game.events if event.type == "seer_check" and event.actor == seer]
    werewolf_checks = [event for event in checks if _team_of(game, event.target) == "werewolf"]
    correct_checks = len(checks)
    conveyed_refs = [event.event_id for event in game.events if event.type == "player_speech" and event.actor == seer]
    evidence = [event.event_id for event in checks] + conveyed_refs[:1]
    total = len(checks)
    return {
        "actor": seer,
        "check_accuracy": _round_float(correct_checks / total) if total else 0.0,
        "check_targeting": _round_float(len(werewolf_checks) / total) if total else 0.0,
        "info_conveyed": 1.0 if checks and conveyed_refs else 0.0,
        "evidence_event_ids": evidence,
    }


def _witch_metrics(game: GameLog) -> dict[str, Any]:
    witch = next(player.player_id for player in game.players if player.role == "witch")
    saves = [event for event in game.events if event.type == "witch_save" and event.actor == witch]
    poisons = [event for event in game.events if event.type == "witch_poison" and event.actor == witch]
    save_accuracy = 0.0
    if saves:
        save_accuracy = 1.0 if _team_of(game, saves[0].target) == "villager" else 0.0
    poison_accuracy = 0.0
    if poisons:
        poison_accuracy = 1.0 if _team_of(game, poisons[0].target) == "werewolf" else 0.0
    used = int(bool(saves)) + int(bool(poisons))
    ability_utilization = 1.0 if used == 2 else 0.5 if used == 1 else 0.0
    return {
        "actor": witch,
        "save_accuracy": save_accuracy,
        "poison_accuracy": poison_accuracy,
        "ability_utilization": ability_utilization,
        "evidence_event_ids": [event.event_id for event in saves + poisons],
    }


def _team_metrics(game: GameLog, votes: list[Event] | None = None) -> dict[str, Any]:
    # `votes` is the already-filtered vote set computed once in summarize_metrics.
    # The legacy form `_team_metrics(game)` recomputes the unfiltered set.
    if votes is None:
        votes = _vote_events(game)
    village_by_day: dict[str, float] = {}
    werewolf_by_day: dict[str, float] = {}
    rounds = sorted({event.round for event in votes})
    for round_number in rounds:
        round_votes = [event for event in votes if event.round == round_number]
        village_votes = [event for event in round_votes if _team_of(game, event.actor) == "villager"]
        if village_votes:
            target_counts: dict[str, int] = {}
            for vote in village_votes:
                target_counts[vote.target] = target_counts.get(vote.target, 0) + 1
            village_by_day[f"round_{round_number}"] = _round_float(max(target_counts.values()) / len(village_votes))
        werewolf_votes = [event for event in round_votes if _team_of(game, event.actor) == "werewolf"]
        if len(werewolf_votes) >= 2:
            targets = {event.target for event in werewolf_votes}
            werewolf_by_day[f"round_{round_number}"] = 1.0 if len(targets) == 1 else 0.0
        village_votes = [event for event in votes if _team_of(game, event.actor) == "villager"]
        if village_votes:
            target_counts: dict[str, int] = {}
            for vote in village_votes:
                target_counts[vote.target] = target_counts.get(vote.target, 0) + 1
            village_by_day[f"round_{round_number}"] = _round_float(max(target_counts.values()) / len(village_votes))
        werewolf_votes = [event for event in votes if _team_of(game, event.actor) == "werewolf"]
        if len(werewolf_votes) >= 2:
            targets = {event.target for event in werewolf_votes}
            werewolf_by_day[f"round_{round_number}"] = 1.0 if len(targets) == 1 else 0.0
    village_values = list(village_by_day.values())
    werewolf_values = list(werewolf_by_day.values())
    return {
        "village_vote_cohesion": _round_float(sum(village_values) / len(village_values)) if village_values else 0.0,
        "village_vote_cohesion_by_day": village_by_day,
        "werewolf_vote_coordination": _round_float(sum(werewolf_values) / len(werewolf_values)) if werewolf_values else 0.0,
        "werewolf_vote_coordination_by_day": werewolf_by_day,
    }


def _result_metrics(game: GameLog) -> ResultMetrics:
    players = _player_by_id(game)
    alive = _alive_players_after_game(game)
    werewolves = [player.player_id for player in game.players if player.team == "werewolf"]
    villagers = [player.player_id for player in game.players if player.team == "villager"]
    alive_werewolves = [player_id for player_id in werewolves if player_id in alive]
    alive_villagers = [player_id for player_id in villagers if player_id in alive]
    winner_alive = alive_villagers if game.result.winner == "villager" else alive_werewolves
    loser_alive = alive_werewolves if game.result.winner == "villager" else alive_villagers
    werewolf_deaths = {event.target for event in game.events if event.type in {"player_died", "player_eliminated"} and players[event.target].team == "werewolf"}
    return ResultMetrics(
        winner=game.result.winner,
        game_length=game.result.end_round,
        werewolf_survival_rate=_round_float(len(alive_werewolves) / len(werewolves)) if werewolves else 0.0,
        villager_survival_rate=_round_float(len(alive_villagers) / len(villagers)) if villagers else 0.0,
        margin=len(winner_alive) - len(loser_alive),
        werewolf_win_speed=None if game.result.winner != "werewolf" else _round_float((len(alive_werewolves) - len(alive_villagers)) / game.result.end_round),
        villager_win_efficiency=None if game.result.winner != "villager" else _round_float(len(werewolf_deaths) / game.result.end_round),
    )


def _score_summary(game: GameLog, score_log: ScoreLog) -> ScoreSummary:
    player_outcome = {player.player_id: 0 for player in game.players}
    player_integrity = {player.player_id: 0 for player in game.players}
    player_decision = {player.player_id: 0 for player in game.players}
    team_outcome: dict[str, int] = {}
    for record in score_log.records:
        if record.scope == "team":
            team_outcome[record.actor] = team_outcome.get(record.actor, 0) + record.outcome_score
        else:
            player_outcome[record.actor] += record.outcome_score
            player_integrity[record.actor] += record.rule_integrity_score
            player_decision[record.actor] += record.decision_quality_score
    return ScoreSummary(
        player_outcome_scores=player_outcome,
        team_outcome_scores=team_outcome,
        player_rule_integrity_scores=player_integrity,
        player_decision_quality_scores=player_decision,
    )


def summarize_metrics(
    game: GameLog,
    score_log: ScoreLog,
    decision_log: DecisionLog | None = None,
) -> MetricsSummary:
    s5_enabled = score_log.phase == "Phase 2B-S5"
    is_g001 = game.game_id == GOLD_GAME_ID
    if is_g001:
        metrics_id = GOLD_METRICS_ID_S5 if s5_enabled else GOLD_METRICS_ID_S2
        source_game_log = GOLD_SOURCE_GAME_LOG
        source_score_log = "docs/gold-game/s5-score-log.json" if s5_enabled else "docs/gold-game/s2-score-log.json"
    else:
        metrics_id = f"{game.game_id}_metrics_summary"
        source_game_log = f"generated:{game.game_id}"
        source_score_log = f"score_log:{score_log.score_log_id}"
    # scoring_v2: compute the filtered player-to-player vote set ONCE and feed it
    # to both vote_accuracy and team metrics so the decision matcher runs a single
    # time (it is the most expensive step here) and the two metrics stay consistent.
    filtered_votes = _vote_events(game, decision_log)
    return MetricsSummary(
        metrics_id=metrics_id,
        game_id=game.game_id,
        source_game_log=source_game_log,
        source_score_log=source_score_log,
        source_label=score_log.source_label,
        result_metrics=_result_metrics(game),
        process_metrics=ProcessMetrics(
            vote_accuracy_by_player=_vote_accuracy_by_player(game, filtered_votes),
            survival_rounds=_survival_rounds(game),
            contradiction_count_by_player=_zero_counts(game),
            info_leak_count_by_player=_zero_counts(game),
            seer_metrics=_seer_metrics(game),
            witch_metrics=_witch_metrics(game),
            team_metrics=_team_metrics(game, filtered_votes),
        ),
        score_summary=_score_summary(game, score_log),
        metrics_deferred_to_later_spikes=[
            {
                "metric": "turn_point_count",
                "owner": "S3 rule attribution validation",
                "reason": "turn_point_count is defined as an attribution count; S2 does not compute attribution outputs.",
            }
        ],
        known_rubric_gaps_recorded_not_fixed=_known_rubric_gaps(game),
    )


def _known_rubric_gaps(game: GameLog) -> list[dict[str, Any]]:
    """Return rubric gap records using the current game's event IDs.

    For g001, preserve the canonical gap list. For non-g001 games, derive
    gap events from the current game or return an empty list when the game
    does not hit a given rubric gap.
    """
    if game.game_id == GOLD_GAME_ID:
        return GOLD_KNOWN_RUBRIC_GAPS
    # For non-g001 games, scan for rubric-gap events in the current game.
    gaps: list[dict[str, Any]] = []
    players = {p.player_id for p in game.players}
    # werewolf_day_vote_without_elimination: a werewolf voted in day phase
    # but the vote target was not eliminated in the same round.
    werewolf_no_elim: list[str] = []
    for event in game.events:
        if event.actor not in players:
            continue
        team = _team_of(game, event.actor)
        if event.type == "player_vote" and team == "werewolf":
            eliminated_this_round = any(
                e.type == "player_eliminated"
                and e.target == event.target
                and e.round == event.round
                for e in game.events
            )
            if not eliminated_this_round:
                werewolf_no_elim.append(event.event_id)
    if werewolf_no_elim:
        gaps.append({
            "gap": "werewolf_day_vote_without_elimination",
            "events": werewolf_no_elim,
            "policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
        })
    # witch_day_vote_outcome_not_explicit: witch voted in day phase
    # without an explicit score row for witch day votes.
    witch_no_row: list[str] = []
    for event in game.events:
        if event.actor not in players:
            continue
        role = _role_of(game, event.actor)
        if event.type == "player_vote" and role == "witch":
            witch_no_row.append(event.event_id)
    if witch_no_row:
        gaps.append({
            "gap": "witch_day_vote_outcome_not_explicit",
            "events": witch_no_row,
            "policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
        })
    return gaps
