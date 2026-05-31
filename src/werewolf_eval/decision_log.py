from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.game_log import GameLog

VALID_DECISION_SCOPES = {"single", "team"}
VALID_DECISION_PHASES = {"night", "day"}
VALID_DECISION_TYPES = {
    "inference_based",
    "random",
    "retaliatory",
    "team_coordinated",
    "default",
}
VALID_SOURCE_LABELS = {
    "[人工 gold sample]",
    "[AI 生成]",
    "[scripted deterministic output]",
    "[deterministic mock agent output]",
}
ALLOWED_NON_PLAYER_ACTORS = {"wolf_team"}
ALLOWED_NON_PLAYER_TARGETS = {"none", "villager_team", "werewolf_team"}
MAX_REASON_SUMMARY_CHARS = 200


@dataclass(frozen=True)
class Decision:
    decision_id: str
    actor: str
    decision_scope: str
    consensus_id: str | None
    phase: str
    action: str
    target: str | None
    visible_info_refs: list[str]
    reason_summary: str
    decision_type: str
    confidence: float | None
    strategy_tag: str | None


@dataclass(frozen=True)
class DecisionLog:
    decision_log_id: str
    game_id: str
    source_label: str
    decisions: list[Decision]

    @property
    def decision_ids(self) -> set[str]:
        return {decision.decision_id for decision in self.decisions}


class DecisionLogValidationError(ValueError):
    """Raised when a Decision Log cannot be accepted as a Phase 2 runtime input."""


def load_decision_log(path: str | Path, game: GameLog) -> DecisionLog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DecisionLogValidationError("Decision Log root must be an object")
    return parse_decision_log(raw, game)


def parse_decision_log(raw: dict[str, Any], game: GameLog) -> DecisionLog:
    required_top_level = {"decision_log_id", "game_id", "source_label", "decisions"}
    missing = required_top_level - set(raw)
    if missing:
        raise DecisionLogValidationError(f"missing top-level fields: {sorted(missing)}")

    if not isinstance(raw["decisions"], list):
        raise DecisionLogValidationError("decisions must be a list")

    decisions = [_parse_decision(decision) for decision in raw["decisions"]]
    decision_log = DecisionLog(
        decision_log_id=str(raw["decision_log_id"]),
        game_id=str(raw["game_id"]),
        source_label=str(raw["source_label"]),
        decisions=decisions,
    )
    validate_decision_log(decision_log, game)
    return decision_log


def validate_decision_log(decision_log: DecisionLog, game: GameLog) -> None:
    if not decision_log.decision_log_id:
        raise DecisionLogValidationError("decision_log_id must not be empty")

    if decision_log.game_id != game.game_id:
        raise DecisionLogValidationError(
            f"game_id mismatch: decision log {decision_log.game_id!r} != game {game.game_id!r}"
        )

    if decision_log.source_label not in VALID_SOURCE_LABELS:
        raise DecisionLogValidationError(f"invalid source_label: {decision_log.source_label!r}")

    decision_ids = [decision.decision_id for decision in decision_log.decisions]
    if len(set(decision_ids)) != len(decision_ids):
        raise DecisionLogValidationError("decision_id values must be unique")

    for decision in decision_log.decisions:
        _validate_decision(decision, game)


def _parse_decision(raw: Any) -> Decision:
    if not isinstance(raw, dict):
        raise DecisionLogValidationError("decision entries must be objects")

    required_fields = {
        "decision_id",
        "actor",
        "decision_scope",
        "consensus_id",
        "phase",
        "action",
        "target",
        "visible_info_refs",
        "reason_summary",
        "decision_type",
    }
    missing = required_fields - set(raw)
    if missing:
        raise DecisionLogValidationError(f"decision missing fields: {sorted(missing)}")

    visible_info_refs = raw["visible_info_refs"]
    if not isinstance(visible_info_refs, list):
        raise DecisionLogValidationError("visible_info_refs must be a list")

    confidence = raw.get("confidence")
    if confidence is not None:
        confidence = float(confidence)

    strategy_tag = raw.get("strategy_tag")
    if strategy_tag is not None:
        strategy_tag = str(strategy_tag)

    consensus_id = raw["consensus_id"]
    if consensus_id is not None:
        consensus_id = str(consensus_id)

    target = raw["target"]
    if target is not None:
        target = str(target)

    return Decision(
        decision_id=str(raw["decision_id"]),
        actor=str(raw["actor"]),
        decision_scope=str(raw["decision_scope"]),
        consensus_id=consensus_id,
        phase=str(raw["phase"]),
        action=str(raw["action"]),
        target=target,
        visible_info_refs=[str(ref) for ref in visible_info_refs],
        reason_summary=str(raw["reason_summary"]),
        decision_type=str(raw["decision_type"]),
        confidence=confidence,
        strategy_tag=strategy_tag,
    )


def _validate_decision(decision: Decision, game: GameLog) -> None:
    if not decision.decision_id:
        raise DecisionLogValidationError("decision_id must not be empty")

    if decision.actor not in game.player_ids and decision.actor not in ALLOWED_NON_PLAYER_ACTORS:
        raise DecisionLogValidationError(f"{decision.decision_id}: unknown actor {decision.actor!r}")

    if decision.decision_scope not in VALID_DECISION_SCOPES:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: invalid decision_scope {decision.decision_scope!r}"
        )

    if decision.phase not in VALID_DECISION_PHASES:
        raise DecisionLogValidationError(f"{decision.decision_id}: invalid phase {decision.phase!r}")

    if not decision.action:
        raise DecisionLogValidationError(f"{decision.decision_id}: action must not be empty")

    if (
        decision.target is not None
        and decision.target not in game.player_ids
        and decision.target not in ALLOWED_NON_PLAYER_TARGETS
    ):
        raise DecisionLogValidationError(f"{decision.decision_id}: unknown target {decision.target!r}")

    unknown_refs = set(decision.visible_info_refs) - game.event_ids
    if unknown_refs:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: unknown visible_info_refs: {sorted(unknown_refs)}"
        )

    if len(decision.reason_summary) > MAX_REASON_SUMMARY_CHARS:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: reason_summary exceeds {MAX_REASON_SUMMARY_CHARS} chars"
        )

    if decision.decision_type not in VALID_DECISION_TYPES:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: invalid decision_type {decision.decision_type!r}"
        )

    if decision.confidence is not None and not 0.0 <= decision.confidence <= 1.0:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: confidence must be between 0 and 1"
        )
