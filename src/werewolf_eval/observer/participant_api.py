"""Pure helpers for the P3-C participant route skeleton.

This is intentionally an in-memory, local-dev bridge. It issues bearer-style
participant sessions, creates one stub action window, and validates submit
round-trips without coupling to the real game loop.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Mapping

from werewolf_eval.observer.run_manager import _read_events_jsonl_safe
from werewolf_eval.observer.state import ObserverServerState
from werewolf_eval.observer_visibility import build_projection_envelope
from werewolf_eval.participant_protocol import (
    ACTION_SUBMIT_RESULT_SCHEMA_VERSION,
    ActionWindow,
    ParticipantActionSubmission,
    ParticipantProtocolError,
    ParticipantSession,
    build_participant_error_envelope,
    perspective_for_seat,
    validate_reconnect_cursor,
    validate_seat_id,
    validate_submission_for_window,
)

PARTICIPANT_STATE_SCHEMA_VERSION = "p3c.participant_state.v1"
LOCAL_DEV_JOIN_CODE = "local-dev-code"
_SESSION_TTL = timedelta(hours=12)


def participant_error_response(exc: ParticipantProtocolError) -> tuple[int, dict[str, object]]:
    """Return ``(http_status, p3c.error.v1 envelope)`` for handler translation."""
    return exc.http_status, exc.to_envelope()


def run_not_found_response(run_id: str) -> tuple[int, dict[str, object]]:
    return 404, build_participant_error_envelope(
        "run_not_found",
        f"Run not found: {run_id}",
        run_id=run_id,
    )


def reject_participant_perspective_override(run_id: str) -> tuple[int, dict[str, object]]:
    return 403, build_participant_error_envelope(
        "visibility_forbidden",
        "Participant endpoints derive perspective from the session token",
        run_id=run_id,
    )


def issue_participant_session(
    state: ObserverServerState,
    *,
    run_id: str,
    request_payload: Mapping[str, object],
    now: datetime | None = None,
) -> ParticipantSession:
    """Issue or replace a local-dev participant session for one run + seat."""
    join_code = request_payload.get("join_code")
    if join_code != LOCAL_DEV_JOIN_CODE:
        raise ParticipantProtocolError(
            "missing_or_invalid_session",
            "Missing or invalid participant join code",
        )

    seat_id = validate_seat_id(request_payload.get("seat_id"))
    now = _normalize_now(now)
    token = secrets.token_urlsafe(32)
    cursor = "event:0"
    session = ParticipantSession(
        run_id=run_id,
        seat_id=seat_id,
        participant_session_token=token,
        issued_at=_format_instant(now),
        expires_at=_format_instant(now + _SESSION_TTL),
        last_seen_cursor=cursor,
    )
    with state.lock:
        state.participant_sessions[token] = session
        _ensure_stub_action_window_locked(state, run_id=run_id, seat_id=seat_id)
    return session


def authenticate_participant_session(
    state: ObserverServerState,
    *,
    run_id: str,
    authorization_header: str | None,
    now: datetime | None = None,
) -> ParticipantSession:
    """Authenticate a bearer participant token and bind it to *run_id*."""
    token = _extract_bearer_token(authorization_header)
    if token is None:
        raise ParticipantProtocolError(
            "missing_or_invalid_session",
            "Missing or invalid participant session",
        )
    with state.lock:
        session = state.participant_sessions.get(token)
    if session is None:
        raise ParticipantProtocolError(
            "missing_or_invalid_session",
            "Missing or invalid participant session",
        )
    if session.run_id != run_id:
        raise ParticipantProtocolError(
            "seat_not_controlled_by_session",
            "Participant session does not control this run",
            run_id=session.run_id,
            seat_id=session.seat_id,
            reconnect_cursor=session.last_seen_cursor,
        )
    now = _normalize_now(now)
    expires_at = _parse_instant(session.expires_at)
    if session.revoked_at is not None or expires_at <= now:
        raise ParticipantProtocolError(
            "missing_or_invalid_session",
            "Missing or invalid participant session",
        )
    return session


def build_participant_state_payload(
    state: ObserverServerState,
    *,
    run_id: str,
    run_dir: Path,
    session: ParticipantSession,
    run_status: str,
) -> dict[str, object]:
    """Build a role-safe participant state payload."""
    perspective = perspective_for_seat(session.seat_id)
    events = _read_events_jsonl_safe(run_dir / "events.jsonl")
    projection = build_projection_envelope(
        run_dir=run_dir,
        run_id=run_id,
        perspective=perspective,
        events=events,
    )
    with state.lock:
        window = _open_window_for_session_locked(state, session)
    reconnect_cursor = window.reconnect_cursor if window is not None else session.last_seen_cursor
    return {
        "schema_version": PARTICIPANT_STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "seat_id": session.seat_id,
        "perspective": perspective,
        "run_status": run_status,
        "projection": projection,
        "open_action_window": window.to_payload() if window is not None else None,
        "reconnect_cursor": validate_reconnect_cursor(reconnect_cursor),
    }


def submit_participant_action(
    state: ObserverServerState,
    *,
    run_id: str,
    session: ParticipantSession,
    request_payload: Mapping[str, object],
    run_status: str,
) -> dict[str, object]:
    """Validate and accept a skeleton participant action submission."""
    if run_status != "running":
        raise ParticipantProtocolError(
            "run_not_accepting_actions",
            "Run is not accepting participant actions",
            run_id=run_id,
            seat_id=session.seat_id,
            reconnect_cursor=session.last_seen_cursor,
        )
    submission = ParticipantActionSubmission(
        action_window_id=request_payload.get("action_window_id"),
        game_revision=request_payload.get("game_revision"),
        idempotency_key=request_payload.get("idempotency_key"),
        action_type=request_payload.get("action_type"),
        payload=request_payload.get("payload"),
        client_observed_event_id=(
            request_payload.get("client_observed_event_id")
            if isinstance(request_payload.get("client_observed_event_id"), str)
            else None
        ),
        client_sent_at=(
            request_payload.get("client_sent_at")
            if isinstance(request_payload.get("client_sent_at"), str)
            else None
        ),
    )

    with state.lock:
        duplicate = state.participant_idempotency.duplicate_for(submission)
        if duplicate is not None:
            payload = dict(duplicate.result)
            payload["status"] = "duplicate"
            return payload

        window = state.participant_action_windows.get(submission.action_window_id)
        if window is None or window.run_id != run_id or window.seat_id != session.seat_id:
            raise ParticipantProtocolError(
                "action_window_not_found",
                "Action window not found for this participant session",
                run_id=run_id,
                seat_id=session.seat_id,
                action_window_id=submission.action_window_id,
                reconnect_cursor=session.last_seen_cursor,
            )
        validate_submission_for_window(submission, window)

        state.participant_action_counter += 1
        accepted_event_id = f"evt_participant_action_{state.participant_action_counter:04d}"
        next_revision = window.game_revision + 1
        next_cursor = f"event:{_event_index_from_cursor(window.reconnect_cursor) + 1}"
        result = {
            "schema_version": ACTION_SUBMIT_RESULT_SCHEMA_VERSION,
            "status": "accepted",
            "action_window_id": window.action_window_id,
            "game_revision": next_revision,
            "accepted_event_id": accepted_event_id,
            "reconnect_cursor": next_cursor,
        }
        state.participant_idempotency.record_or_duplicate(submission, result)
        state.participant_action_windows[window.action_window_id] = ActionWindow(
            action_window_id=window.action_window_id,
            run_id=window.run_id,
            seat_id=window.seat_id,
            phase=window.phase,
            round=window.round,
            game_revision=next_revision,
            opened_at_event_id=window.opened_at_event_id,
            deadline_at=window.deadline_at,
            allowed_actions=window.allowed_actions,
            required=window.required,
            default_on_timeout=window.default_on_timeout,
            status="accepted",
            reconnect_cursor=next_cursor,
            skippable=window.skippable,
            ai_takeover_allowed=window.ai_takeover_allowed,
        )
        return dict(result)


def participant_sse_events(
    state: ObserverServerState,
    *,
    run_id: str,
    session: ParticipantSession,
    run_status: str,
) -> list[tuple[str, dict[str, object]]]:
    """Return a finite skeleton event list for the participant SSE route."""
    events: list[tuple[str, dict[str, object]]] = [
        ("run_status", {"run_id": run_id, "status": run_status})
    ]
    with state.lock:
        window = _open_window_for_session_locked(state, session)
    if window is not None:
        events.append(("action_window_opened", window.to_payload()))
    return events


def _ensure_stub_action_window_locked(
    state: ObserverServerState,
    *,
    run_id: str,
    seat_id: str,
) -> ActionWindow:
    existing = [
        window for window in state.participant_action_windows.values()
        if window.run_id == run_id and window.seat_id == seat_id
    ]
    for window in existing:
        if window.status == "open":
            return window
    if existing:
        return existing[-1]

    window = ActionWindow(
        action_window_id=f"aw_{run_id}_{seat_id}_0001",
        run_id=run_id,
        seat_id=seat_id,
        phase="p3c_stub",
        round=0,
        game_revision=0,
        opened_at_event_id="evt_participant_stub_0000",
        deadline_at=_format_instant(datetime.now(UTC) + timedelta(minutes=5)),
        allowed_actions=("speech", "pass"),
        required=False,
        default_on_timeout="pass",
        status="open",
        reconnect_cursor="event:0",
    )
    state.participant_action_windows[window.action_window_id] = window
    return window


def _open_window_for_session_locked(
    state: ObserverServerState,
    session: ParticipantSession,
) -> ActionWindow | None:
    for window in state.participant_action_windows.values():
        if (
            window.run_id == session.run_id
            and window.seat_id == session.seat_id
            and window.status == "open"
        ):
            return window
    return None


def _extract_bearer_token(header: str | None) -> str | None:
    if not isinstance(header, str):
        return None
    prefix = "Bearer "
    if not header.startswith(prefix):
        return None
    token = header[len(prefix):].strip()
    return token or None


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _format_instant(value: datetime) -> str:
    return _normalize_now(value).isoformat().replace("+00:00", "Z")


def _parse_instant(value: str) -> datetime:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = parsedate_to_datetime(value)
    return _normalize_now(parsed)


def _event_index_from_cursor(cursor: str) -> int:
    return int(validate_reconnect_cursor(cursor).split(":", 1)[1])
