"""In-memory participant action controller for P3-C game-loop integration.

The controller is intentionally process-local. It coordinates the observer HTTP
threads and the single run thread: the engine opens server-owned action windows,
HTTP submit validates against those windows, and the engine waits for the
accepted submission or a timeout.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Condition, RLock

from werewolf_eval.participant_protocol import (
    ACTION_SUBMIT_RESULT_SCHEMA_VERSION,
    ActionIdempotencyTracker,
    ActionWindow,
    ParticipantActionSubmission,
    ParticipantProtocolError,
    ensure_single_open_action_window,
    validate_participant_run_id,
    validate_reconnect_cursor,
    validate_seat_id,
    validate_submission_for_window,
)


def _format_instant(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _event_index_from_cursor(cursor: str) -> int:
    return int(validate_reconnect_cursor(cursor).split(":", 1)[1])


class InMemoryParticipantActionController:
    """Thread-safe action-window store used by participant routes and the engine."""

    def __init__(self) -> None:
        self._condition = Condition(RLock())
        self._configured_seats: set[tuple[str, str]] = set()
        self._windows: dict[str, ActionWindow] = {}
        self._accepted_submissions: dict[str, ParticipantActionSubmission] = {}
        self._idempotency = ActionIdempotencyTracker()
        self._window_counter = 0
        self._action_counter = 0

    def configure_human_seat(self, run_id: str, seat_id: str) -> None:
        """Mark one run+seat as game-loop controlled by a human participant."""
        run_id = validate_participant_run_id(run_id)
        seat_id = validate_seat_id(seat_id)
        with self._condition:
            self._configured_seats.add((run_id, seat_id))
            self._condition.notify_all()

    def run_has_human_seat(self, run_id: str) -> bool:
        run_id = validate_participant_run_id(run_id)
        with self._condition:
            return any(rid == run_id for rid, _seat in self._configured_seats)

    def is_human_seat(self, run_id: str, seat_id: str) -> bool:
        run_id = validate_participant_run_id(run_id)
        seat_id = validate_seat_id(seat_id)
        with self._condition:
            return (run_id, seat_id) in self._configured_seats

    def ensure_stub_action_window(self, *, run_id: str, seat_id: str) -> ActionWindow:
        """Create the P3-C-0b local-dev stub window for non-integrated runs."""
        run_id = validate_participant_run_id(run_id)
        seat_id = validate_seat_id(seat_id)
        with self._condition:
            existing = [
                window for window in self._windows.values()
                if window.run_id == run_id and window.seat_id == seat_id
            ]
            for window in existing:
                if window.status == "open":
                    return window
            if existing:
                return existing[-1]
            return self.open_action_window(
                run_id=run_id,
                seat_id=seat_id,
                phase="p3c_stub",
                round=0,
                game_revision=0,
                opened_at_event_id="evt_participant_stub_0000",
                allowed_actions=("speech", "pass"),
                required=False,
                default_on_timeout="pass",
                reconnect_cursor="event:0",
                deadline_at=_format_instant(datetime.now(UTC) + timedelta(minutes=5)),
            )

    def open_action_window(
        self,
        *,
        run_id: str,
        seat_id: str,
        phase: str,
        round: int,
        game_revision: int,
        opened_at_event_id: str,
        allowed_actions: Iterable[str],
        required: bool,
        default_on_timeout: str,
        reconnect_cursor: str,
        deadline_at: str | None = None,
        skippable: bool = False,
        ai_takeover_allowed: bool = False,
    ) -> ActionWindow:
        """Open one action window and wake any route/test waiting for it."""
        run_id = validate_participant_run_id(run_id)
        seat_id = validate_seat_id(seat_id)
        with self._condition:
            current = [
                window for window in self._windows.values()
                if window.run_id == run_id and window.seat_id == seat_id and window.status == "open"
            ]
            ensure_single_open_action_window(current)
            if current:
                raise ParticipantProtocolError(
                    "invalid_payload",
                    "only one open action window is allowed per human seat",
                    run_id=run_id,
                    seat_id=seat_id,
                    action_window_id=current[0].action_window_id,
                    reconnect_cursor=current[0].reconnect_cursor,
                )
            self._window_counter += 1
            deadline = deadline_at or _format_instant(datetime.now(UTC) + timedelta(seconds=60))
            window = ActionWindow(
                action_window_id=f"aw_{run_id}_{seat_id}_{self._window_counter:04d}",
                run_id=run_id,
                seat_id=seat_id,
                phase=phase,
                round=round,
                game_revision=game_revision,
                opened_at_event_id=opened_at_event_id,
                deadline_at=deadline,
                allowed_actions=tuple(allowed_actions),
                required=required,
                default_on_timeout=default_on_timeout,
                status="open",
                reconnect_cursor=reconnect_cursor,
                skippable=skippable,
                ai_takeover_allowed=ai_takeover_allowed,
            )
            self._windows[window.action_window_id] = window
            self._condition.notify_all()
            return window

    def open_window_for(self, *, run_id: str, seat_id: str) -> ActionWindow | None:
        run_id = validate_participant_run_id(run_id)
        seat_id = validate_seat_id(seat_id)
        with self._condition:
            return self._open_window_for_locked(run_id, seat_id)

    def wait_for_open_window(
        self,
        run_id: str,
        seat_id: str,
        *,
        timeout: float | None = None,
    ) -> ActionWindow | None:
        """Wait until a run+seat has an open window, used by integration tests."""
        run_id = validate_participant_run_id(run_id)
        seat_id = validate_seat_id(seat_id)
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while True:
                window = self._open_window_for_locked(run_id, seat_id)
                if window is not None:
                    return window
                if deadline is None:
                    self._condition.wait()
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)

    def submit_action(
        self,
        *,
        run_id: str,
        seat_id: str,
        payload: Mapping[str, object],
    ) -> dict[str, object]:
        """Validate, accept, and notify a participant action submission."""
        run_id = validate_participant_run_id(run_id)
        seat_id = validate_seat_id(seat_id)
        submission = ParticipantActionSubmission(
            action_window_id=payload.get("action_window_id"),
            game_revision=payload.get("game_revision"),
            idempotency_key=payload.get("idempotency_key"),
            action_type=payload.get("action_type"),
            payload=payload.get("payload"),
            client_observed_event_id=(
                payload.get("client_observed_event_id")
                if isinstance(payload.get("client_observed_event_id"), str)
                else None
            ),
            client_sent_at=(
                payload.get("client_sent_at")
                if isinstance(payload.get("client_sent_at"), str)
                else None
            ),
        )
        with self._condition:
            duplicate = self._idempotency.duplicate_for(submission)
            if duplicate is not None:
                result = dict(duplicate.result)
                result["status"] = "duplicate"
                return result

            window = self._windows.get(submission.action_window_id)
            if window is None or window.run_id != run_id or window.seat_id != seat_id:
                raise ParticipantProtocolError(
                    "action_window_not_found",
                    "Action window not found for this participant session",
                    run_id=run_id,
                    seat_id=seat_id,
                    action_window_id=submission.action_window_id,
                    reconnect_cursor="event:0",
                )
            validate_submission_for_window(submission, window)

            self._action_counter += 1
            next_revision = window.game_revision + 1
            next_cursor = f"event:{_event_index_from_cursor(window.reconnect_cursor) + 1}"
            result = {
                "schema_version": ACTION_SUBMIT_RESULT_SCHEMA_VERSION,
                "status": "accepted",
                "action_window_id": window.action_window_id,
                "game_revision": next_revision,
                "accepted_event_id": f"evt_participant_action_{self._action_counter:04d}",
                "reconnect_cursor": next_cursor,
            }
            self._idempotency.record_or_duplicate(submission, result)
            self._accepted_submissions[window.action_window_id] = submission
            self._windows[window.action_window_id] = replace(
                window,
                status="accepted",
                game_revision=next_revision,
                reconnect_cursor=next_cursor,
            )
            self._condition.notify_all()
            return dict(result)

    def wait_for_action(
        self,
        action_window_id: str,
        *,
        timeout: float | None = None,
    ) -> ParticipantActionSubmission | None:
        """Wait for the accepted submission for *action_window_id*.

        Returns ``None`` when the window times out before a submission arrives.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while True:
                submission = self._accepted_submissions.get(action_window_id)
                if submission is not None:
                    return submission
                window = self._windows.get(action_window_id)
                if window is None or window.status != "open":
                    return None
                if deadline is None:
                    self._condition.wait()
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._windows[action_window_id] = replace(
                        window,
                        status="timed_out",
                        reconnect_cursor=f"event:{_event_index_from_cursor(window.reconnect_cursor) + 1}",
                    )
                    self._condition.notify_all()
                    return None
                self._condition.wait(remaining)

    def _open_window_for_locked(self, run_id: str, seat_id: str) -> ActionWindow | None:
        for window in self._windows.values():
            if window.run_id == run_id and window.seat_id == seat_id and window.status == "open":
                return window
        return None
