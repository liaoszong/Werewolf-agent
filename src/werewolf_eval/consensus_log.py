from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.game_log import GameLog

VALID_SOURCE_LABELS = {"[人工 gold sample]", "[AI 生成]", "[scripted deterministic output]"}
VALID_CONSENSUS_PHASES = {"night"}
VALID_TEAMS = {"werewolf"}
VALID_CONSENSUS_STATUSES = {
    "consensus",
    "accepted_consensus",
    "coordinator_tie_break",
    "forced_random",
}
VALID_RESPONSE_TYPES = {
    "support_with_reason",
    "oppose_with_reason",
    "revise_target",
    "abstain",
}
MAX_REASON_SUMMARY_CHARS = 150


@dataclass(frozen=True)
class ConsensusProposal:
    proposal_id: int
    proposer: str
    proposed_target: str
    visible_info_refs: list[str]
    reason_summary: str
    confidence: float | None
    action_round: int


@dataclass(frozen=True)
class ConsensusResponse:
    response_id: int
    to_proposal_id: int
    responder: str
    response_type: str
    reason_summary: str
    visible_info_refs: list[str]
    action_round: int


@dataclass(frozen=True)
class FinalConsensusDecision:
    target: str
    decision_type: str
    primary_proposer: str
    supporters: list[str]
    dissenters: list[str]
    resolution_round: int


@dataclass(frozen=True)
class Consensus:
    consensus_id: str
    game_id: str
    round: int
    phase: str
    team: str
    participants: list[str]
    coordinator: str
    max_rounds: int
    actual_rounds: int
    status: str
    proposals: list[ConsensusProposal]
    responses: list[ConsensusResponse]
    final_decision: FinalConsensusDecision


@dataclass(frozen=True)
class ConsensusLog:
    consensus_log_id: str
    game_id: str
    source_label: str
    consensuses: list[Consensus]

    @property
    def consensus_ids(self) -> set[str]:
        return {consensus.consensus_id for consensus in self.consensuses}


class ConsensusLogValidationError(ValueError):
    """Raised when a Consensus Log cannot be accepted as a Phase 2 runtime input."""


def load_consensus_log(path: str | Path, game: GameLog) -> ConsensusLog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("Consensus Log root must be an object")
    return parse_consensus_log(raw, game)


def parse_consensus_log(raw: dict[str, Any], game: GameLog) -> ConsensusLog:
    required_top_level = {"consensus_log_id", "game_id", "source_label", "consensuses"}
    missing = required_top_level - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"missing top-level fields: {sorted(missing)}")

    if not isinstance(raw["consensuses"], list):
        raise ConsensusLogValidationError("consensuses must be a list")

    consensus_log = ConsensusLog(
        consensus_log_id=str(raw["consensus_log_id"]),
        game_id=str(raw["game_id"]),
        source_label=str(raw["source_label"]),
        consensuses=[_parse_consensus(item) for item in raw["consensuses"]],
    )
    validate_consensus_log(consensus_log, game)
    return consensus_log


def validate_consensus_log(consensus_log: ConsensusLog, game: GameLog) -> None:
    if not consensus_log.consensus_log_id:
        raise ConsensusLogValidationError("consensus_log_id must not be empty")

    if consensus_log.game_id != game.game_id:
        raise ConsensusLogValidationError(
            f"game_id mismatch: consensus log {consensus_log.game_id!r} != game {game.game_id!r}"
        )

    if consensus_log.source_label not in VALID_SOURCE_LABELS:
        raise ConsensusLogValidationError(f"invalid source_label: {consensus_log.source_label!r}")

    consensus_ids = [consensus.consensus_id for consensus in consensus_log.consensuses]
    if len(set(consensus_ids)) != len(consensus_ids):
        raise ConsensusLogValidationError("consensus_id values must be unique")

    for consensus in consensus_log.consensuses:
        _validate_consensus(consensus, game)

    _validate_consensus_covers_all_kills(consensus_log, game)


def _parse_consensus(raw: Any) -> Consensus:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("consensus entries must be objects")

    required_fields = {
        "consensus_id",
        "game_id",
        "round",
        "phase",
        "team",
        "participants",
        "coordinator",
        "max_rounds",
        "actual_rounds",
        "status",
        "proposals",
        "responses",
        "final_decision",
    }
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"consensus missing fields: {sorted(missing)}")

    participants = raw["participants"]
    proposals = raw["proposals"]
    responses = raw["responses"]
    if not isinstance(participants, list):
        raise ConsensusLogValidationError("participants must be a list")
    if not isinstance(proposals, list):
        raise ConsensusLogValidationError("proposals must be a list")
    if not isinstance(responses, list):
        raise ConsensusLogValidationError("responses must be a list")

    return Consensus(
        consensus_id=str(raw["consensus_id"]),
        game_id=str(raw["game_id"]),
        round=int(raw["round"]),
        phase=str(raw["phase"]),
        team=str(raw["team"]),
        participants=[str(participant) for participant in participants],
        coordinator=str(raw["coordinator"]),
        max_rounds=int(raw["max_rounds"]),
        actual_rounds=int(raw["actual_rounds"]),
        status=str(raw["status"]),
        proposals=[_parse_proposal(item) for item in proposals],
        responses=[_parse_response(item) for item in responses],
        final_decision=_parse_final_decision(raw["final_decision"]),
    )


def _parse_proposal(raw: Any) -> ConsensusProposal:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("proposal entries must be objects")

    required_fields = {"proposal_id", "proposer", "proposed_target", "visible_info_refs", "reason_summary"}
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"proposal missing fields: {sorted(missing)}")

    visible_info_refs = raw["visible_info_refs"]
    if not isinstance(visible_info_refs, list):
        raise ConsensusLogValidationError("proposal visible_info_refs must be a list")

    confidence = raw.get("confidence")
    if confidence is not None:
        confidence = float(confidence)

    return ConsensusProposal(
        proposal_id=int(raw["proposal_id"]),
        proposer=str(raw["proposer"]),
        proposed_target=str(raw["proposed_target"]),
        visible_info_refs=[str(ref) for ref in visible_info_refs],
        reason_summary=str(raw["reason_summary"]),
        confidence=confidence,
        action_round=int(raw.get("action_round", 1)),
    )


def _parse_response(raw: Any) -> ConsensusResponse:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("response entries must be objects")

    required_fields = {"response_id", "to_proposal_id", "responder", "response_type", "reason_summary", "visible_info_refs"}
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"response missing fields: {sorted(missing)}")

    visible_info_refs = raw["visible_info_refs"]
    if not isinstance(visible_info_refs, list):
        raise ConsensusLogValidationError("response visible_info_refs must be a list")

    return ConsensusResponse(
        response_id=int(raw["response_id"]),
        to_proposal_id=int(raw["to_proposal_id"]),
        responder=str(raw["responder"]),
        response_type=str(raw["response_type"]),
        reason_summary=str(raw["reason_summary"]),
        visible_info_refs=[str(ref) for ref in visible_info_refs],
        action_round=int(raw.get("action_round", 1)),
    )


def _parse_final_decision(raw: Any) -> FinalConsensusDecision:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("final_decision must be an object")

    required_fields = {"target", "decision_type", "primary_proposer", "supporters", "dissenters", "resolution_round"}
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"final_decision missing fields: {sorted(missing)}")

    supporters = raw["supporters"]
    dissenters = raw["dissenters"]
    if not isinstance(supporters, list):
        raise ConsensusLogValidationError("final_decision supporters must be a list")
    if not isinstance(dissenters, list):
        raise ConsensusLogValidationError("final_decision dissenters must be a list")

    return FinalConsensusDecision(
        target=str(raw["target"]),
        decision_type=str(raw["decision_type"]),
        primary_proposer=str(raw["primary_proposer"]),
        supporters=[str(supporter) for supporter in supporters],
        dissenters=[str(dissenter) for dissenter in dissenters],
        resolution_round=int(raw["resolution_round"]),
    )


def _validate_consensus(consensus: Consensus, game: GameLog) -> None:
    if not consensus.consensus_id:
        raise ConsensusLogValidationError("consensus_id must not be empty")

    if consensus.game_id != game.game_id:
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: game_id mismatch: {consensus.game_id!r} != {game.game_id!r}"
        )

    if consensus.phase not in VALID_CONSENSUS_PHASES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid phase {consensus.phase!r}")

    if consensus.team not in VALID_TEAMS:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid team {consensus.team!r}")

    if consensus.status not in VALID_CONSENSUS_STATUSES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid status {consensus.status!r}")

    if not 1 <= consensus.max_rounds <= 3:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: max_rounds must be between 1 and 3")

    if not 1 <= consensus.actual_rounds <= consensus.max_rounds:
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: actual_rounds must be between 1 and max_rounds"
        )

    if not consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: participants must not be empty")

    if len(set(consensus.participants)) != len(consensus.participants):
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: participants must be unique")

    if consensus.coordinator not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: coordinator must be a participant")

    players = {player.player_id: player for player in game.players}
    for participant in consensus.participants:
        if participant not in players:
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown participant {participant!r}")
        if players[participant].team != "werewolf":
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: participant must be werewolf: {participant!r}")

    proposal_ids = [proposal.proposal_id for proposal in consensus.proposals]
    if len(set(proposal_ids)) != len(proposal_ids):
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposal_id values must be unique")

    # Rubric B.2: per wolf, per action_round, at most 1 action (proposal or response).
    action_counts: dict[tuple[str, int], int] = {}
    for proposal in consensus.proposals:
        _validate_action_round(consensus, proposal.action_round)
        key = (proposal.proposer, proposal.action_round)
        action_counts[key] = action_counts.get(key, 0) + 1
    for response in consensus.responses:
        _validate_action_round(consensus, response.action_round)
        key = (response.responder, response.action_round)
        action_counts[key] = action_counts.get(key, 0) + 1
    for (participant, action_round), count in action_counts.items():
        if count > 1:
            raise ConsensusLogValidationError(
                f"{consensus.consensus_id}: participant {participant} has {count} actions in action_round {action_round}; max 1 per action_round"
            )

    for proposal in consensus.proposals:
        _validate_proposal(consensus, proposal, game)

    for response in consensus.responses:
        _validate_response(consensus, response, set(proposal_ids), game)

    _validate_final_decision(consensus, game)


def _validate_consensus_covers_all_kills(consensus_log: ConsensusLog, game: GameLog) -> None:
    kill_events = [
        event for event in game.events if event.type == "werewolf_kill"
    ]
    if not kill_events:
        return

    kill_keys = {(event.round, event.phase, event.target) for event in kill_events}
    covered: dict[tuple[int, str, str], list[str]] = {}
    for consensus in consensus_log.consensuses:
        decision = consensus.final_decision
        key = (consensus.round, consensus.phase, decision.target)
        covered.setdefault(key, []).append(consensus.consensus_id)

    for key in kill_keys:
        matches = covered.get(key, [])
        if len(matches) == 0:
            round, phase, target = key
            raise ConsensusLogValidationError(
                f"werewolf_kill event (round {round}, phase {phase}, target {target}) has no matching consensus entry"
            )
        if len(matches) > 1:
            raise ConsensusLogValidationError(
                f"werewolf_kill event has multiple consensus entries: {matches}"
            )

    for key, consensus_ids in covered.items():
        if key not in kill_keys:
            raise ConsensusLogValidationError(
                f"consensus entries {consensus_ids} target a non-existent werewolf_kill event"
            )


def _validate_proposal(consensus: Consensus, proposal: ConsensusProposal, game: GameLog) -> None:
    if proposal.proposal_id < 1:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposal_id must be >= 1")

    if proposal.proposer not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposer must be a participant")

    if proposal.proposed_target not in game.player_ids:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown proposed_target {proposal.proposed_target!r}")

    if proposal.proposed_target in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposed_target must not be a werewolf participant")

    _validate_reason_summary(consensus.consensus_id, proposal.reason_summary)
    _validate_visible_info_refs(consensus.consensus_id, proposal.visible_info_refs, game, consensus.round)

    if proposal.confidence is not None and not 0.0 <= proposal.confidence <= 1.0:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: confidence must be between 0 and 1")


def _validate_response(
    consensus: Consensus,
    response: ConsensusResponse,
    proposal_ids: set[int],
    game: GameLog,
) -> None:
    if response.response_id < 1:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: response_id must be >= 1")

    if response.to_proposal_id not in proposal_ids:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown to_proposal_id {response.to_proposal_id}")

    if response.responder not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: responder must be a participant")

    if response.response_type not in VALID_RESPONSE_TYPES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid response_type {response.response_type!r}")

    _validate_reason_summary(consensus.consensus_id, response.reason_summary)
    _validate_visible_info_refs(consensus.consensus_id, response.visible_info_refs, game, consensus.round)


def _validate_final_decision(consensus: Consensus, game: GameLog) -> None:
    decision = consensus.final_decision

    if decision.decision_type not in VALID_CONSENSUS_STATUSES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid final decision_type {decision.decision_type!r}")

    if decision.decision_type != consensus.status:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: status must match final decision_type")

    if decision.primary_proposer not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: primary_proposer must be a participant")

    for supporter in decision.supporters:
        if supporter not in consensus.participants:
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: supporter must be a participant")

    for dissenter in decision.dissenters:
        if dissenter not in consensus.participants:
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: dissenter must be a participant")

    if set(decision.supporters) & set(decision.dissenters):
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: supporter cannot also be dissenter")

    if decision.decision_type == "consensus" and decision.dissenters:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: consensus decision_type requires 0 dissenters")
    if decision.decision_type == "accepted_consensus" and decision.dissenters:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: accepted_consensus decision_type requires 0 dissenters")
    if decision.decision_type == "coordinator_tie_break" and not decision.dissenters:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: coordinator_tie_break decision_type requires at least 1 dissenter")

    covered = set(decision.supporters) | set(decision.dissenters)
    if covered != set(consensus.participants):
        missing = set(consensus.participants) - covered
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: all participants must appear as supporter or dissenter; missing: {sorted(missing)}"
        )

    if not 1 <= decision.resolution_round <= consensus.actual_rounds:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: resolution_round must be within actual_rounds")

    if decision.target not in game.player_ids:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown final target {decision.target!r}")

    if decision.target in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: final target must not be a werewolf participant")

    matching_kill = next(
        (
            event
            for event in game.events
            if event.type == "werewolf_kill"
            and event.round == consensus.round
            and event.phase == consensus.phase
            and event.target == decision.target
        ),
        None,
    )
    if matching_kill is None:
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: final target does not match werewolf_kill event for round {consensus.round}"
        )


def _validate_action_round(consensus: Consensus, action_round: int) -> None:
    if not 1 <= action_round <= consensus.actual_rounds:
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: action_round {action_round} must be between 1 and actual_rounds ({consensus.actual_rounds})"
        )


def _validate_reason_summary(consensus_id: str, reason_summary: str) -> None:
    if not reason_summary:
        raise ConsensusLogValidationError(f"{consensus_id}: reason_summary must not be empty")
    if len(reason_summary) > MAX_REASON_SUMMARY_CHARS:
        raise ConsensusLogValidationError(f"{consensus_id}: reason_summary exceeds 150 chars")


def _validate_visible_info_refs(consensus_id: str, visible_info_refs: list[str], game: GameLog, round: int) -> None:
    unknown_refs = set(visible_info_refs) - game.event_ids
    if unknown_refs:
        raise ConsensusLogValidationError(f"{consensus_id}: unknown visible_info_refs: {sorted(unknown_refs)}")

    for ref in visible_info_refs:
        event = game.event_by_id(ref)
        if event.visibility in {"public", "all", "werewolf_team"}:
            continue
        if event.visibility == "specific_player_ids":
            player = next((p for p in game.players if p.player_id == event.target), None)
            if player is not None and player.team == "werewolf":
                continue
        raise ConsensusLogValidationError(
            f"{consensus_id}: visible_info_ref {ref} has visibility {event.visibility!r}, "
            f"not visible to werewolf team"
        )

    kill_event = next(
        (e for e in game.events if e.type == "werewolf_kill" and e.round == round),
        None,
    )
    if kill_event is not None:
        for ref in visible_info_refs:
            if game.event_by_id(ref).sequence >= kill_event.sequence:
                raise ConsensusLogValidationError(
                    f"{consensus_id}: visible_info_ref {ref} (seq {game.event_by_id(ref).sequence}) "
                    f"is not before werewolf_kill {kill_event.event_id} (seq {kill_event.sequence})"
                )
