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


CONSUME_TYPES = ("witch_save", "witch_poison", "hunter_shoot")


def check_i3(arts: RunArtifacts) -> list[InvariantViolation]:
    """Each consumable used <= 1 per (actor, capability)."""
    by_key: dict[tuple[str, str], list[str]] = {}
    for e in arts.events:
        t = str(e.get("type"))
        if t in CONSUME_TYPES:
            by_key.setdefault((str(e.get("actor")), t), []).append(str(e.get("event_id")))
    return [
        InvariantViolation("I3", "error", arts.game_id, tuple(eids),
                           f"{actor} used {cap} {len(eids)}x (max 1)")
        for (actor, cap), eids in by_key.items() if len(eids) > 1
    ]


_ALL_CHECKS.append(check_i3)


def check_prompt_subset(game_id: str, seat: str, prompt_source_ids: list[str],
                        observation_event_ids: set[str]) -> list[InvariantViolation]:
    """I4a (in-memory only): prompt sources subset of the seat's observation set.
    Not in _ALL_CHECKS — its 2nd operand is not persisted on disk."""
    leaked = [eid for eid in prompt_source_ids if eid not in observation_event_ids]
    return [InvariantViolation("I4a", "error", game_id, (eid,),
                               f"seat {seat} prompt sourced {eid} outside its observation")
            for eid in leaked]


def check_i4b(arts: RunArtifacts) -> list[InvariantViolation]:
    """Every event a seat's prompt was built from must be one that seat could
    legitimately see — checked by the OBSERVER's independent projection, never
    the engine's _build_obs. The non-circular leak guard."""
    seat_index = seat_index_from_players(arts.players)
    by_id = {str(e.get("event_id")): e for e in arts.events}
    out: list[InvariantViolation] = []
    for turn in arts.provider_turns:
        seat = str(turn.get("actor"))
        for eid in turn.get("observation_source_event_ids", []):
            ev = by_id.get(str(eid))
            if ev is None:
                continue
            if not entitled(seat, ev, seat_index):
                out.append(InvariantViolation(
                    "I4b", "error", arts.game_id, (str(eid),),
                    f"seat {seat} prompt sourced non-entitled event {eid} "
                    f"(visibility={ev.get('visibility')})"))
    return out


_ALL_CHECKS.append(check_i4b)


def check_i5(arts: RunArtifacts) -> list[InvariantViolation]:
    """One decision identity settles at most once. Identity = (request_id, phase),
    NOT request_id alone (the strict path reuses request_id across night/day)."""
    seen: dict[tuple[str, str], int] = {}
    for t in arts.provider_turns:
        key = (str(t.get("request_id")), str(t.get("phase")))
        seen[key] = seen.get(key, 0) + 1
    return [
        InvariantViolation("I5", "error", arts.game_id, (),
                           f"decision identity (request_id={rid}, phase={ph}) settled {n}x")
        for (rid, ph), n in seen.items() if n > 1
    ]


_ALL_CHECKS.append(check_i5)


DEATH_CAUSE_TYPES = ("werewolf_kill", "witch_poison", "hunter_shoot")


def check_i6(arts: RunArtifacts) -> list[InvariantViolation]:
    """WEAK causality: every player_died has an earlier cause event naming the same
    target. player_eliminated (vote) is exempt. STRICT-I6 rides the EffectQueue."""
    ordered = sorted(arts.events, key=lambda e: e.get("sequence", 0))
    out: list[InvariantViolation] = []
    for e in ordered:
        if e.get("type") != "player_died":
            continue
        tgt = str(e.get("target"))
        seq = int(e.get("sequence", 0))
        has_cause = any(
            int(c.get("sequence", 0)) < seq
            and c.get("type") in DEATH_CAUSE_TYPES
            and str(c.get("target")) == tgt
            for c in ordered
        )
        if not has_cause:
            out.append(InvariantViolation("I6", "error", arts.game_id, (str(e.get("event_id")),),
                                          f"player_died({tgt}) has no candidate cause event"))
    return out


_ALL_CHECKS.append(check_i6)
