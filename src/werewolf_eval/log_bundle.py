from __future__ import annotations

from dataclasses import dataclass

from werewolf_eval.consensus_log import Consensus, ConsensusLog
from werewolf_eval.decision_log import Decision, DecisionLog
from werewolf_eval.failure_audit import FailureAudit
from werewolf_eval.game_log import GameLog


class LogBundleValidationError(ValueError):
    """Raised when separately valid logs do not satisfy cross-log invariants."""


@dataclass(frozen=True)
class LogBundleValidationResult:
    game_id: str
    decision_log_enabled: bool
    consensus_log_enabled: bool
    failure_audit_enabled: bool
    team_consensus_links: int


def validate_log_bundle(
    game: GameLog,
    *,
    decision_log: DecisionLog | None = None,
    consensus_log: ConsensusLog | None = None,
    failure_audit: FailureAudit | None = None,
) -> LogBundleValidationResult:
    if decision_log is not None and decision_log.game_id != game.game_id:
        raise LogBundleValidationError("decision_log game_id mismatch")
    if consensus_log is not None and consensus_log.game_id != game.game_id:
        raise LogBundleValidationError("consensus_log game_id mismatch")
    if failure_audit is not None and failure_audit.game_id != game.game_id:
        raise LogBundleValidationError("failure_audit game_id mismatch")

    _validate_source_labels_match(game, decision_log, consensus_log, failure_audit)

    team_links = 0
    if decision_log is not None and consensus_log is not None:
        team_links = _validate_team_decision_consensus_links(decision_log, consensus_log)

    return LogBundleValidationResult(
        game_id=game.game_id,
        decision_log_enabled=decision_log is not None,
        consensus_log_enabled=consensus_log is not None,
        failure_audit_enabled=failure_audit is not None,
        team_consensus_links=team_links,
    )


def _validate_source_labels_match(
    game: GameLog,
    decision_log: DecisionLog | None,
    consensus_log: ConsensusLog | None,
    failure_audit: FailureAudit | None,
) -> None:
    for name, artifact in [
        ("decision_log", decision_log),
        ("consensus_log", consensus_log),
        ("failure_audit", failure_audit),
    ]:
        if artifact is not None and artifact.source_label != game.source_label:
            raise LogBundleValidationError(
                f"source_label mismatch: {name} {artifact.source_label!r} != game {game.source_label!r}"
            )


def _is_team_decision(decision: Decision) -> bool:
    return (
        decision.decision_scope == "team"
        or decision.actor == "wolf_team"
        or decision.action == "werewolf_kill"
        or decision.decision_type == "team_coordinated"
    )


def _validate_team_decision_consensus_links(
    decision_log: DecisionLog,
    consensus_log: ConsensusLog,
) -> int:
    consensuses = {item.consensus_id: item for item in consensus_log.consensuses}
    links = 0

    for decision in decision_log.decisions:
        if not _is_team_decision(decision):
            continue

        if not decision.consensus_id:
            raise LogBundleValidationError(
                f"{decision.decision_id}: missing consensus_id for team decision"
            )
        if decision.consensus_id not in consensuses:
            raise LogBundleValidationError(
                f"{decision.decision_id}: unknown consensus_id {decision.consensus_id!r}"
            )

        consensus = consensuses[decision.consensus_id]
        _validate_decision_matches_consensus(decision, consensus)
        links += 1

    return links


def _validate_decision_matches_consensus(decision: Decision, consensus: Consensus) -> None:
    if decision.target != consensus.final_decision.target:
        raise LogBundleValidationError(
            f"{decision.decision_id}: target mismatch with {consensus.consensus_id}: "
            f"{decision.target!r} != {consensus.final_decision.target!r}"
        )
    if decision.phase != consensus.phase:
        raise LogBundleValidationError(
            f"{decision.decision_id}: phase mismatch with {consensus.consensus_id}: "
            f"{decision.phase!r} != {consensus.phase!r}"
        )
