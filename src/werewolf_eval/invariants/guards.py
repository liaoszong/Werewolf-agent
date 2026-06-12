from __future__ import annotations

from typing import Any

from werewolf_eval.invariants.visibility_oracle import entitled


class PromptLeakError(Exception):
    """A provider call's prompt would source an event the seat may not see."""


class DanglingSourceEventError(Exception):
    """A provider call's prompt sources an event id that is ABSENT from the event
    log (a dangling reference). Fail-loud: a renderer must never source a
    never-logged event."""


class DoubleDeathCommitError(Exception):
    """A player would be committed dead a second time."""


def assert_prompt_entitled(seat: str, source_event_ids: list[str],
                           events_by_id: dict[str, Any],
                           seat_index: dict[str, dict[str, object]]) -> None:
    """B1: fail-closed before provider.respond/decide. Uses the observer's
    independent visibility (NOT _build_obs).

    C3-1: a source id absent from the event log is a DANGLING reference and fails
    loud (DanglingSourceEventError) — it is NOT silently skipped. The offline
    checker (`check_i4b`) reports the same condition as an I4b error for replays,
    so neither path is blind to a renderer sourcing a never-logged event."""
    for eid in source_event_ids:
        ev = events_by_id.get(eid)
        if ev is None:
            raise DanglingSourceEventError(
                f"seat {seat} prompt sources event {eid} absent from the event log "
                "(dangling reference)")
        if not entitled(seat, ev, seat_index):
            raise PromptLeakError(
                f"seat {seat} prompt would source non-entitled event {eid} "
                f"(visibility={ev.get('visibility')})")


def assert_death_commit_once(pid: str, committed: set[str]) -> None:
    """B4: call immediately before emitting a death-commit event for `pid`. The
    legal duplicate-CANDIDATE skip (engine's `in self._alive` gate) never reaches
    here. A duplicate committed EVENT is the hard fail."""
    if pid in committed:
        raise DoubleDeathCommitError(f"player {pid} committed dead twice")
    committed.add(pid)
