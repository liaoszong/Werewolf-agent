from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from werewolf_eval.invariants.artifacts import RunArtifacts
from werewolf_eval.invariants.visibility_oracle import entitled, seat_index_from_players


@dataclass(frozen=True)
class InvariantViolation:
    id: str                       # "I1".."I7" or "artifact_gap"
    severity: str                 # "error" | "artifact_gap"
    game_id: str
    event_ids: tuple[str, ...]
    detail: str


# Registered incrementally by later tasks.
_ALL_CHECKS: list[Callable[[RunArtifacts], list[InvariantViolation]]] = []


def check_run(source: Any) -> list[InvariantViolation]:
    """Run every registered invariant over a finished game. `source` may be a
    RunArtifacts, a GameOutcome, or a run_dir path. Never raises."""
    if isinstance(source, RunArtifacts):
        arts = source
    elif isinstance(source, (str, Path)):
        arts = RunArtifacts.from_run_dir(source)
    else:
        arts = RunArtifacts.from_outcome(source)

    violations: list[InvariantViolation] = [
        InvariantViolation("artifact_gap", "artifact_gap", arts.game_id, (), f"missing {gap}")
        for gap in arts.gaps
    ]
    for check in _ALL_CHECKS:
        violations.extend(check(arts))
    return violations


DEATH_COMMIT_TYPES = ("player_died", "player_eliminated")


def check_i1(arts: RunArtifacts) -> list[InvariantViolation]:
    """Each player is committed dead at most once (candidates may stack; commits may not)."""
    by_target: dict[str, list[str]] = {}
    for e in arts.events:
        if e.get("type") in DEATH_COMMIT_TYPES:
            by_target.setdefault(str(e.get("target")), []).append(str(e.get("event_id")))
    return [
        InvariantViolation("I1", "error", arts.game_id, tuple(eids),
                           f"player {target} committed dead {len(eids)}x")
        for target, eids in by_target.items() if len(eids) > 1
    ]


_ALL_CHECKS.append(check_i1)


ACTIVE_ACTION_TYPES = ("werewolf_kill", "seer_check", "witch_save", "witch_poison",
                       "witch_pass", "player_speech", "player_vote")


def _first_death_sequence(arts: RunArtifacts) -> dict[str, int]:
    dead_at: dict[str, int] = {}
    for e in sorted(arts.events, key=lambda x: x.get("sequence", 0)):
        if e.get("type") in DEATH_COMMIT_TYPES:
            dead_at.setdefault(str(e.get("target")), int(e.get("sequence", 0)))
    return dead_at


def check_i2(arts: RunArtifacts) -> list[InvariantViolation]:
    """A dead actor produces no ordinary action; the on-death window
    (hunter_shoot/hunter_pass, absent from ACTIVE_ACTION_TYPES) is exempt."""
    dead_seq = _first_death_sequence(arts)
    out: list[InvariantViolation] = []
    for e in arts.events:
        if e.get("type") not in ACTIVE_ACTION_TYPES:
            continue
        actor = str(e.get("actor"))
        ds = dead_seq.get(actor)
        if ds is not None and int(e.get("sequence", 0)) > ds:
            out.append(InvariantViolation("I2", "error", arts.game_id, (str(e.get("event_id")),),
                                          f"dead actor {actor} produced {e.get('type')} after death"))
    return out


_ALL_CHECKS.append(check_i2)
