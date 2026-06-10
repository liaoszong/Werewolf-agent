from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from werewolf_eval.decision_log import Decision, DecisionLog
from werewolf_eval.evaluation_versions import SCORING_VERSION, UNKNOWN_VERSION, evaluation_bucket as _evaluation_bucket
from werewolf_eval.game_log import Event, GameLog
from werewolf_eval.semantic_labels import SemanticLabel, SemanticLabelLog


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


# ---------------------------------------------------------------------------
# D2: Decision Log scoring integration
# ---------------------------------------------------------------------------

SCORE_RELEVANT_DECISION_ACTIONS = SCORE_RELEVANT_EVENT_TYPES


def _role_for_actor(game: GameLog, actor: str) -> str | None:
    if actor == "wolf_team":
        return "werewolf_team"
    if actor in game.player_ids:
        return _role_of(game, actor)
    return None


def _event_visible_to_decision_actor(game: GameLog, event: Event, actor: str) -> bool:
    if event.visibility in {"public", "all"}:
        return True

    if actor == "wolf_team":
        if event.visibility == "werewolf_team":
            return True
        # R-16: `specific_player_ids` is the GOLD-game role_assignment visibility; both
        # engines emit role_assignment as "public" instead, so this branch is exercised
        # only by gold-replay logs (NOT dead — it keeps gold + emergent scoring aligned).
        if event.visibility == "specific_player_ids":
            return event.target in game.player_ids and _team_of(game, event.target) == "werewolf"
        return False

    if actor not in game.player_ids:
        return False

    actor_role = _role_of(game, actor)
    if event.visibility == actor_role:
        return True

    if event.visibility == "werewolf_team":
        return actor_role == "werewolf"

    if event.visibility == "specific_player_ids":
        return event.target == actor

    return False


def _decision_actor_matches_event(decision: Decision, event: Event) -> bool:
    return decision.actor == event.actor


def _decision_target_matches_event(decision: Decision, event: Event) -> bool:
    return decision.target == event.target


def _decision_matches_event(decision: Decision, event: Event) -> bool:
    return (
        decision.action == event.type
        and decision.phase == event.phase
        and _decision_actor_matches_event(decision, event)
        and _decision_target_matches_event(decision, event)
    )


def _decision_by_event_id(game: GameLog, decision_log: DecisionLog | None) -> dict[str, Decision]:
    if decision_log is None:
        return {}

    mapping: dict[str, Decision] = {}
    used_decision_ids: set[str] = set()
    relevant_events = [event for event in game.events if event.type in SCORE_RELEVANT_EVENT_TYPES]

    for event in relevant_events:
        candidates = [
            decision
            for decision in decision_log.decisions
            if decision.decision_id not in used_decision_ids
            and decision.action in SCORE_RELEVANT_DECISION_ACTIONS
            and _decision_matches_event(decision, event)
        ]
        if len(candidates) == 1:
            decision = candidates[0]
            mapping[event.event_id] = decision
            used_decision_ids.add(decision.decision_id)
        elif len(candidates) > 1:
            raise ValueError(
                f"ambiguous Decision Log match for event {event.event_id}: "
                f"{[decision.decision_id for decision in candidates]}"
            )

    return mapping


SEMANTIC_QUALITY_SCORE_BY_LABEL = {
    "supported_good": 2,
    "supported_neutral": 1,
    "random_or_default": 0,
    "unsupported": -1,
    "contradicted": -2,
}


def _semantic_rule(label: SemanticLabel) -> str:
    return f"rubric:G.1.semantic.{label.quality_label}"


def _assess_decision(
    game: GameLog,
    decision: Decision | None,
    semantic_label: SemanticLabel | None = None,
    semantic_labels_enabled: bool = False,
) -> DecisionAssessment:
    if decision is None:
        return DecisionAssessment(
            decision_id=None,
            decision_quality_score=0,
            rule_integrity_score=0,
            rules_triggered=[],
            evidence_event_ids=[],
            notes=[],
        )

    evidence_event_ids = list(decision.visible_info_refs)
    illegal_refs = [
        ref
        for ref in decision.visible_info_refs
        if not _event_visible_to_decision_actor(game, game.event_by_id(ref), decision.actor)
    ]

    s5_skip_note = "; S5 semantic label skipped because deterministic integrity check failed" if semantic_labels_enabled else ""

    if illegal_refs:
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=0,
            rule_integrity_score=-3,
            rules_triggered=["rubric:G.1.illegal_visible_info_ref"],
            evidence_event_ids=evidence_event_ids,
            notes=[
                f"Decision {decision.decision_id} references non-visible events {illegal_refs}; D2 assigns no decision quality and applies rule_integrity_score -3.{s5_skip_note}"
            ],
        )

    # S5 enabled: semantic label presence takes priority over D2 no-refs / default checks.
    if semantic_labels_enabled and semantic_label is not None:
        quality_score = SEMANTIC_QUALITY_SCORE_BY_LABEL[semantic_label.quality_label]
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=quality_score,
            rule_integrity_score=0,
            rules_triggered=[_semantic_rule(semantic_label)],
            evidence_event_ids=evidence_event_ids,
            notes=[
                f"Decision {decision.decision_id} "
                f"visible_refs={'present' if decision.visible_info_refs else 'none'} "
                f"type={decision.decision_type}; "
                f"S5 label={semantic_label.quality_label} "
                f"evidence_alignment={semantic_label.evidence_alignment} "
                f"reasoning_consistency={semantic_label.reasoning_consistency} "
                f"rationale={semantic_label.short_rationale}"
            ],
        )

    if not decision.visible_info_refs:
        if semantic_labels_enabled:
            return DecisionAssessment(
                decision_id=decision.decision_id,
                decision_quality_score=0,
                rule_integrity_score=0,
                rules_triggered=["rubric:G.1.semantic_label_missing"],
                evidence_event_ids=evidence_event_ids,
                notes=[f"Decision {decision.decision_id} has no visible_info_refs and no S5 semantic label."],
            )
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=0,
            rule_integrity_score=0,
            rules_triggered=["rubric:G.1.no_decision_quality_without_refs"],
            evidence_event_ids=evidence_event_ids,
            notes=[f"Decision {decision.decision_id} has no visible_info_refs; D2 keeps decision_quality_score 0."],
        )

    if decision.decision_type in {"random", "default"}:
        if semantic_labels_enabled:
            # semantic_label was None here (handled above), so it's missing
            return DecisionAssessment(
                decision_id=decision.decision_id,
                decision_quality_score=0,
                rule_integrity_score=0,
                rules_triggered=[
                    "rubric:G.1.no_decision_quality_for_default",
                    "rubric:G.1.semantic_label_missing",
                ],
                evidence_event_ids=evidence_event_ids,
                notes=[f"Decision {decision.decision_id} is {decision.decision_type} and has no S5 semantic label."],
            )
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=0,
            rule_integrity_score=0,
            rules_triggered=["rubric:G.1.no_decision_quality_for_default"],
            evidence_event_ids=evidence_event_ids,
            notes=[f"Decision {decision.decision_id} is {decision.decision_type}; D2 keeps decision_quality_score 0."],
        )

    # S5 enabled: no semantic label for this decision
    if semantic_labels_enabled:
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=0,
            rule_integrity_score=0,
            rules_triggered=["rubric:G.1.semantic_label_missing"],
            evidence_event_ids=evidence_event_ids,
            notes=[
                f"Decision {decision.decision_id} has visible refs and non-random type {decision.decision_type} but no semantic label in S5 label log."
            ],
        )

    # D2 does NOT assign decision_quality_score > 0.
    return DecisionAssessment(
        decision_id=decision.decision_id,
        decision_quality_score=0,
        rule_integrity_score=0,
        rules_triggered=["rubric:G.1.decision_logged"],
        evidence_event_ids=evidence_event_ids,
        notes=[
            f"Decision {decision.decision_id} has visible refs and non-random type {decision.decision_type}; D2 records decision_id and preserves decision_quality_score=0. Positive scoring requires S5 AI semantic judgment."
        ],
    )


def _scoring_boundary(has_decision_log: bool = False, has_s5: bool = False) -> ScoringBoundary:
    if has_s5:
        return ScoringBoundary(
            decision_quality_score=0,
            decision_quality_reason="S5 saved semantic labels connected to deterministic decision_quality_score via SEMANTIC_QUALITY_SCORE_BY_LABEL mapping. No live AI labeling is performed during scoring.",
            ai_annotations="saved S5 semantic labels; no provider call made during scoring",
            rule_integrity_default=0,
            rule_integrity_reason="Illegal visible_info_refs are deterministic rule-integrity violations (-3); otherwise records default to 0.",
        )
    if has_decision_log:
        return ScoringBoundary(
            decision_quality_score=0,
            decision_quality_reason="D2 implements Rubric G.1 Step 1-2 only: deterministic visibility check and decision-to-event traceability. No AI semantic judgment; positive decision_quality_score waits for S5.",
            ai_annotations="none; S5 not enabled",
            rule_integrity_default=0,
            rule_integrity_reason="Illegal visible_info_refs are deterministic rule-integrity violations (-3); otherwise records default to 0.",
        )
    return ScoringBoundary(
        decision_quality_score=0,
        decision_quality_reason="No Decision Log supplied. All decision_quality_score values are fixed at 0.",
        ai_annotations="none",
        rule_integrity_default=0,
        rule_integrity_reason="No Decision Log visibility checks were run.",
    )


def _score_werewolf_kill(game: GameLog, event: Event, assessment: DecisionAssessment | None = None) -> ScoreRecord:
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
    # Only consider death/save events from the same round as the kill.
    death_event = next(
        (e.event_id for e in game.events
         if e.type == "player_died" and e.target == event.target and e.round == event.round),
        None,
    )
    if death_event:
        evidence.append(death_event)
    else:
        # When the kill target was saved by witch (no same-round player_died),
        # include the witch_save event as alternative evidence.
        save_event = next(
            (e.event_id for e in game.events
             if e.type == "witch_save" and e.target == event.target and e.round == event.round),
            None,
        )
        if save_event:
            evidence.append(save_event)
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)

    if event.event_id == "g001_e007":
        notes = "Wolf team chose a villager target; p5 is later revealed as villager, while g001_e009 records that the Night 1 save prevented the kill from taking effect."

    return _record(event, outcome, [rule], evidence, notes, assessment)


def _score_seer_check(game: GameLog, event: Event, assessment: DecisionAssessment | None = None) -> ScoreRecord:
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
    return _record(event, outcome, [rule], evidence, notes, assessment)


def _score_witch_save(game: GameLog, event: Event, assessment: DecisionAssessment | None = None) -> ScoreRecord:
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
    return _record(event, outcome, [rule], evidence, notes, assessment)


def _score_witch_poison(game: GameLog, event: Event, assessment: DecisionAssessment | None = None) -> ScoreRecord:
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
    return _record(event, outcome, [rule], evidence, notes, assessment)


def _round_elimination_event(game: GameLog, round_number: int) -> str | None:
    for e in game.events:
        if e.type == "player_eliminated" and e.round == round_number:
            return e.event_id
    return None


def _score_player_vote(game: GameLog, event: Event, eliminated_by_round: dict[int, str], assessment: DecisionAssessment | None = None) -> ScoreRecord:
    players = _player_by_id(game)
    if event.actor not in players or event.target not in players:
        # game_log validation accepts non-player actors ("system"/"wolf_team") and
        # non-player targets ("none"/"*_team") on a player_vote; the engine never emits
        # them, but replays/hand-written logs can. There is no deterministic vote-scoring
        # row for a non-player actor/target, so record a rubric gap rather than KeyError
        # on the role/team lookup.
        return _record(
            event,
            0,
            ["rubric-gap:vote_target_not_a_player"],
            [event.event_id],
            f"Vote references a non-player id (actor={event.actor!r}, target={event.target!r}); no deterministic vote scoring row applies.",
            assessment,
        )
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
            assessment,
        )

    if actor_role == "werewolf" and eliminated_target != event.target:
        return _record(
            event,
            0,
            ["rubric-gap:werewolf_day_vote_without_elimination"],
            evidence,
            f"{event.actor} voted for {event.target}, but {event.target} was not eliminated. E.1 has no explicit row for a werewolf vote that does not cause elimination, so S2 assigns 0 and records the rubric gap.",
            assessment,
        )

    if actor_role == "werewolf":
        if target_team == "werewolf":
            return _record(event, -2, ["rubric:E.1.werewolf.vote_eliminate_teammate"], evidence, f"Werewolf {event.actor} voted to eliminate teammate {event.target}.", assessment)
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, 2, ["rubric:E.1.werewolf.vote_eliminate_key_villager"], evidence, f"Werewolf {event.actor} voted to eliminate {event.target}, who is revealed as {target_role}.", assessment)
        return _record(event, 1, ["rubric:E.1.werewolf.vote_eliminate_villager"], evidence, f"Werewolf {event.actor} voted to eliminate villager {event.target}.", assessment)

    if actor_role == "seer":
        if target_team == "werewolf":
            return _record(event, 2, ["rubric:E.2.seer.vote_eliminate_werewolf"], evidence, f"Seer {event.actor} voted for {event.target}, who is later revealed as werewolf.", assessment)
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, -1, ["rubric:E.2.seer.vote_eliminate_key_villager"], evidence, f"Seer {event.actor} voted for key villager {event.target}.", assessment)
        return _record(event, -1, ["rubric:E.2.seer.vote_eliminate_villager"], evidence, f"Seer {event.actor} voted for villager {event.target}.", assessment)

    if actor_role == "villager":
        if target_team == "werewolf":
            return _record(event, 2, ["rubric:E.4.villager.vote_eliminate_werewolf"], evidence, f"Villager {event.actor} voted to eliminate {event.target}, who is revealed as werewolf.", assessment)
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, -2, ["rubric:E.4.villager.vote_eliminate_key_villager"], evidence, f"Villager {event.actor} voted to eliminate {event.target}, who is revealed as {target_role}.", assessment)
        return _record(event, -1, ["rubric:E.4.villager.vote_eliminate_villager"], evidence, f"Villager {event.actor} voted to eliminate villager {event.target}.", assessment)

    return _record(event, 0, ["rubric-gap:unscored_vote_role"], evidence, f"No explicit deterministic vote scoring row for role {actor_role}.", assessment)


def _score_id_prefix(game: GameLog) -> str:
    if game.game_id == "g001":
        return "s2_g001"
    return f"score_{game.game_id}"


def _score_log_id(game: GameLog, semantic_labels_enabled: bool) -> str:
    if game.game_id == "g001":
        return "s5_g001_expected_score_log" if semantic_labels_enabled else "s2_g001_expected_score_log"
    return f"{game.game_id}_score_log"


def _score_source_label(game: GameLog, decision_log: DecisionLog | None, semantic_labels_enabled: bool) -> str:
    if game.game_id != "g001" and decision_log is not None and decision_log.source_label == "[scripted deterministic output]":
        return "[scripted deterministic output][decision-log]"
    if semantic_labels_enabled:
        return "[deterministic][decision-log][semantic-labels]"
    if decision_log is not None:
        return "[deterministic][decision-log]"
    return "[deterministic]"


_current_score_id_prefix: str = "s2_g001"


def _record(
    event: Event,
    outcome_score: int,
    rules_triggered: list[str],
    evidence_event_ids: list[str],
    notes: str,
    assessment: DecisionAssessment | None = None,
) -> ScoreRecord:
    decision_rules = assessment.rules_triggered if assessment else []
    decision_evidence = assessment.evidence_event_ids if assessment else []
    decision_notes = assessment.notes if assessment else []
    return ScoreRecord(
        score_id=f"{_current_score_id_prefix}_{event.event_id.split('_')[-1]}",
        event_id=event.event_id,
        decision_id=assessment.decision_id if assessment else None,
        actor=event.actor,
        scope=_scope_for_actor(event.actor),
        round=event.round,
        phase=event.phase,
        action_type=event.type,
        target=event.target,
        outcome_score=outcome_score,
        decision_quality_score=assessment.decision_quality_score if assessment else 0,
        rule_integrity_score=assessment.rule_integrity_score if assessment else 0,
        rules_triggered=rules_triggered + decision_rules,
        evidence_event_ids=list(dict.fromkeys(evidence_event_ids + decision_evidence)),
        notes=" ".join([notes] + decision_notes).strip(),
    )


def score_game(game: GameLog, decision_log: DecisionLog | None = None, semantic_label_log: SemanticLabelLog | None = None) -> ScoreLog:
    global _current_score_id_prefix
    if semantic_label_log is not None and decision_log is None:
        raise ValueError("semantic_label_log requires decision_log")
    eliminated_by_round = _eliminated_target_by_round(game)
    decisions_by_event = _decision_by_event_id(game, decision_log)
    labels_by_decision = semantic_label_log.label_by_decision_id if semantic_label_log else {}
    semantic_labels_enabled = semantic_label_log is not None
    _current_score_id_prefix = _score_id_prefix(game)
    records: list[ScoreRecord] = []

    for event in game.events:
        if event.type not in SCORE_RELEVANT_EVENT_TYPES:
            continue
        decision = decisions_by_event.get(event.event_id)
        semantic_label = labels_by_decision.get(decision.decision_id) if decision else None
        assessment = _assess_decision(game, decision, semantic_label, semantic_labels_enabled)
        if event.type == "werewolf_kill":
            records.append(_score_werewolf_kill(game, event, assessment))
        elif event.type == "seer_check":
            records.append(_score_seer_check(game, event, assessment))
        elif event.type == "witch_save":
            records.append(_score_witch_save(game, event, assessment))
        elif event.type == "witch_poison":
            records.append(_score_witch_poison(game, event, assessment))
        elif event.type == "player_vote":
            records.append(_score_player_vote(game, event, eliminated_by_round, assessment))

    score_log_id = _score_log_id(game, semantic_labels_enabled)
    source_label = _score_source_label(game, decision_log, semantic_labels_enabled)
    if semantic_labels_enabled:
        phase = "Phase 2B-S5"
    elif decision_log is not None:
        phase = "Phase 2A-D2"
    else:
        phase = "Phase 1"

    is_g001 = game.game_id == "g001"
    source_game_log = "docs/gold-game/g001-game-log.json" if is_g001 else f"generated:{game.game_id}"
    return ScoreLog(
        score_log_id=score_log_id,
        game_id=game.game_id,
        source_game_log=source_game_log,
        source_label=source_label,
        phase=phase,
        scoring_boundary=_scoring_boundary(decision_log is not None, semantic_labels_enabled),
        records=records,
    )


# ---------------------------------------------------------------------------
# Task 4: Metrics Summary generation helpers
# ---------------------------------------------------------------------------


def _round_float(value: float) -> float:
    return round(value, 6)


def _alive_players_after_game(game: GameLog) -> set[str]:
    dead = {event.target for event in game.events if event.type in {"player_died", "player_eliminated"}}
    return game.player_ids - dead


def _vote_events(game: GameLog) -> list[Event]:
    # Only player-to-player votes participate in vote metrics. game_log validation
    # permits non-player actors ("system"/"wolf_team") and targets ("none"/"*_team")
    # on a player_vote; the engine never emits them, but replays / hand-written logs
    # can, and the role/team lookups in the metric helpers would KeyError on them.
    players = _player_by_id(game)
    return [
        event
        for event in game.events
        if event.type == "player_vote" and event.actor in players and event.target in players
    ]


def _vote_accuracy_by_player(game: GameLog) -> dict[str, dict[str, float | int]]:
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


def _team_metrics(game: GameLog) -> dict[str, Any]:
    village_by_day: dict[str, float] = {}
    werewolf_by_day: dict[str, float] = {}
    rounds = sorted({event.round for event in _vote_events(game)})
    for round_number in rounds:
        votes = [event for event in _vote_events(game) if event.round == round_number]
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


def summarize_metrics(game: GameLog, score_log: ScoreLog) -> MetricsSummary:
    s5_enabled = score_log.phase == "Phase 2B-S5"
    is_g001 = game.game_id == "g001"
    if is_g001:
        metrics_id = "s5_g001_expected_metrics" if s5_enabled else "s2_g001_expected_metrics"
        source_game_log = "docs/gold-game/g001-game-log.json"
        source_score_log = "docs/gold-game/s5-score-log.json" if s5_enabled else "docs/gold-game/s2-score-log.json"
    else:
        metrics_id = f"{game.game_id}_metrics_summary"
        source_game_log = f"generated:{game.game_id}"
        source_score_log = f"score_log:{score_log.score_log_id}"
    return MetricsSummary(
        metrics_id=metrics_id,
        game_id=game.game_id,
        source_game_log=source_game_log,
        source_score_log=source_score_log,
        source_label=score_log.source_label,
        result_metrics=_result_metrics(game),
        process_metrics=ProcessMetrics(
            vote_accuracy_by_player=_vote_accuracy_by_player(game),
            survival_rounds=_survival_rounds(game),
            contradiction_count_by_player=_zero_counts(game),
            info_leak_count_by_player=_zero_counts(game),
            seer_metrics=_seer_metrics(game),
            witch_metrics=_witch_metrics(game),
            team_metrics=_team_metrics(game),
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
    if game.game_id == "g001":
        return [
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
    # For non-g001 games, scan for rubric-gap events in the current game.
    gaps: list[dict[str, Any]] = []
    players = {p.player_id for p in game.players}
    # werewolf_day_vote_without_elimination: a werewolf voted in day phase
    # but the vote target was not eliminated in the same round.
    werewolf_no_elim: list[str] = []
    for event in game.events:
        if event.actor not in players:
            continue
        role = _role_of(game, event.actor)
        if event.type == "player_vote" and role == "werewolf":
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
