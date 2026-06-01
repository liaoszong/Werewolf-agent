from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.game_log import GameLog
from werewolf_eval.source_labels import VALID_SOURCE_LABELS


VALID_FAILURE_KINDS = {
    "timeout",
    "parse_failure",
    "invalid_action",
    "wolf_consensus_failure",
}
VALID_FAILURE_PHASES = {"night", "day"}


@dataclass(frozen=True)
class FailureRecord:
    game_id: str
    round: int
    phase: str
    actor: str
    kind: str
    target: str | None
    reason: str
    repaired_to_valid_action: bool


@dataclass(frozen=True)
class FailureAudit:
    game_id: str
    source_label: str
    failures: list[FailureRecord]


class FailureAuditValidationError(ValueError):
    """Raised when a Failure Audit cannot be accepted as runtime evidence."""


def load_failure_audit(path: str | Path, game: GameLog) -> FailureAudit:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise FailureAuditValidationError("Failure Audit root must be an object")
    return parse_failure_audit(raw, game)


def parse_failure_audit(raw: dict[str, Any], game: GameLog) -> FailureAudit:
    required_top_level = {"game_id", "source_label", "failures"}
    missing = required_top_level - set(raw)
    if missing:
        raise FailureAuditValidationError(f"missing top-level fields: {sorted(missing)}")

    if not isinstance(raw["failures"], list):
        raise FailureAuditValidationError("failures must be a list")

    source_label = str(raw["source_label"])
    if source_label not in VALID_SOURCE_LABELS:
        raise FailureAuditValidationError(f"invalid source_label: {source_label!r}")

    audit = FailureAudit(
        game_id=str(raw["game_id"]),
        source_label=source_label,
        failures=[_parse_failure(item) for item in raw["failures"]],
    )
    validate_failure_audit(audit, game)
    return audit


def validate_failure_audit(audit: FailureAudit, game: GameLog) -> None:
    if audit.game_id != game.game_id:
        raise FailureAuditValidationError(
            f"game_id mismatch: failure audit {audit.game_id!r} != game {game.game_id!r}"
        )

    known_actors = game.player_ids | {"wolf_team"}
    for failure in audit.failures:
        _validate_failure(failure, game, known_actors)


def _parse_failure(raw: Any) -> FailureRecord:
    if not isinstance(raw, dict):
        raise FailureAuditValidationError("failure entries must be objects")

    required_fields = {
        "game_id",
        "round",
        "phase",
        "actor",
        "kind",
        "target",
        "reason",
        "repaired_to_valid_action",
    }
    missing = required_fields - set(raw)
    if missing:
        raise FailureAuditValidationError(f"failure missing fields: {sorted(missing)}")

    target = raw["target"]
    return FailureRecord(
        game_id=str(raw["game_id"]),
        round=int(raw["round"]),
        phase=str(raw["phase"]),
        actor=str(raw["actor"]),
        kind=str(raw["kind"]),
        target=None if target is None else str(target),
        reason=str(raw["reason"]),
        repaired_to_valid_action=bool(raw["repaired_to_valid_action"]),
    )


def _validate_failure(failure: FailureRecord, game: GameLog, known_actors: set[str]) -> None:
    if failure.game_id != game.game_id:
        raise FailureAuditValidationError(
            f"failure game_id mismatch: {failure.game_id!r} != {game.game_id!r}"
        )
    if failure.round < 1:
        raise FailureAuditValidationError("failure round must be >= 1")
    if failure.phase not in VALID_FAILURE_PHASES:
        raise FailureAuditValidationError(f"invalid failure phase: {failure.phase!r}")
    if failure.actor not in known_actors:
        raise FailureAuditValidationError(f"unknown actor in failure audit: {failure.actor!r}")
    if failure.kind not in VALID_FAILURE_KINDS:
        raise FailureAuditValidationError(f"invalid failure kind: {failure.kind!r}")
    if not failure.reason:
        raise FailureAuditValidationError("failure reason must not be empty")
    if failure.repaired_to_valid_action is not False:
        raise FailureAuditValidationError("repaired_to_valid_action must be false")
