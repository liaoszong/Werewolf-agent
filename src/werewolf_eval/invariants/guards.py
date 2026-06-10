from __future__ import annotations

from typing import Any

from werewolf_eval.invariants.visibility_oracle import entitled


class PromptLeakError(Exception):
    """A provider call's prompt would source an event the seat may not see."""


class DoubleDeathCommitError(Exception):
    """A player would be committed dead a second time."""


def assert_prompt_entitled(seat: str, source_event_ids: list[str],
                           events_by_id: dict[str, Any],
                           seat_index: dict[str, dict[str, object]]) -> None:
    """B1: fail-closed before provider.respond/decide. Uses the observer's
    independent visibility (NOT _build_obs). Unknown event ids are skipped (the
    offline checker reports artifact gaps; the runtime guard never aborts on one)."""
    for eid in source_event_ids:
        ev = events_by_id.get(eid)
        if ev is None:
            continue
        if not entitled(seat, ev, seat_index):
            raise PromptLeakError(
                f"seat {seat} prompt would source non-entitled event {eid} "
                f"(visibility={ev.get('visibility')})")
