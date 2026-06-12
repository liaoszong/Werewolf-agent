"""Score Log generation — the per-decision scoring half of the B-3 split. Moved verbatim from scoring.py; import via the werewolf_eval.scoring facade."""

from __future__ import annotations

from typing import Any

from werewolf_eval.decision_log import Decision, DecisionLog
from werewolf_eval.game_log import Event, GameLog
from werewolf_eval.gold_game_fixtures import (
    GOLD_E007_EVENT_ID,
    GOLD_E007_NOTE,
    GOLD_GAME_ID,
    GOLD_SCORE_ID_PREFIX,
    GOLD_SCORE_LOG_ID_S2,
    GOLD_SCORE_LOG_ID_S5,
    GOLD_SOURCE_GAME_LOG,
)
from werewolf_eval.semantic_labels import SemanticLabel, SemanticLabelLog
from werewolf_eval.scoring_types import (
    DecisionAssessment,
    KEY_VILLAGER_ROLES,
    SCORE_RELEVANT_DECISION_ACTIONS,
    SCORE_RELEVANT_EVENT_TYPES,
    ScoreLog,
    ScoreRecord,
    ScoringBoundary,
    SEMANTIC_QUALITY_SCORE_BY_LABEL,
)


# ---------------------------------------------------------------------------
# Task 3: Score Log generation helpers
# ---------------------------------------------------------------------------


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

    if event.event_id == GOLD_E007_EVENT_ID:
        notes = GOLD_E007_NOTE

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
    if game.game_id == GOLD_GAME_ID:
        return GOLD_SCORE_ID_PREFIX
    return f"score_{game.game_id}"


def _score_log_id(game: GameLog, semantic_labels_enabled: bool) -> str:
    if game.game_id == GOLD_GAME_ID:
        return GOLD_SCORE_LOG_ID_S5 if semantic_labels_enabled else GOLD_SCORE_LOG_ID_S2
    return f"{game.game_id}_score_log"


def _score_source_label(game: GameLog, decision_log: DecisionLog | None, semantic_labels_enabled: bool) -> str:
    if game.game_id != GOLD_GAME_ID and decision_log is not None and decision_log.source_label == "[scripted deterministic output]":
        return "[scripted deterministic output][decision-log]"
    if semantic_labels_enabled:
        return "[deterministic][decision-log][semantic-labels]"
    if decision_log is not None:
        return "[deterministic][decision-log]"
    return "[deterministic]"


_current_score_id_prefix: str = GOLD_SCORE_ID_PREFIX


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

    is_g001 = game.game_id == GOLD_GAME_ID
    source_game_log = GOLD_SOURCE_GAME_LOG if is_g001 else f"generated:{game.game_id}"
    return ScoreLog(
        score_log_id=score_log_id,
        game_id=game.game_id,
        source_game_log=source_game_log,
        source_label=source_label,
        phase=phase,
        scoring_boundary=_scoring_boundary(decision_log is not None, semantic_labels_enabled),
        records=records,
    )
