"""Pure helpers for the P3-C participant route skeleton.

This is intentionally an in-memory, local-dev bridge. It issues bearer-style
participant sessions, creates one stub action window, and validates submit
round-trips without coupling to the real game loop.
"""

from __future__ import annotations

import secrets
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Mapping

from werewolf_eval.observer.run_manager import _read_events_jsonl_safe
from werewolf_eval.observer.state import ObserverServerState
from werewolf_eval.observer_visibility import build_projection_envelope
from werewolf_eval.participant_protocol import (
    ParticipantProtocolError,
    ParticipantSession,
    build_participant_error_envelope,
    parse_reconnect_cursor,
    perspective_for_seat,
    validate_reconnect_cursor,
    validate_seat_id,
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
    run_has_human_seat = state.participant_controller.run_has_human_seat(run_id)
    if run_has_human_seat and not state.participant_controller.is_human_seat(run_id, seat_id):
        with state.lock:
            state.participant_sessions.pop(token, None)
        raise ParticipantProtocolError(
            "seat_not_controlled_by_session",
            "This run does not assign that seat to a participant",
            run_id=run_id,
            seat_id=seat_id,
        )
    if not run_has_human_seat:
        state.participant_controller.ensure_stub_action_window(run_id=run_id, seat_id=seat_id)
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
    window = state.participant_controller.open_window_for(
        run_id=session.run_id,
        seat_id=session.seat_id,
    )
    reconnect_cursor = session.last_seen_cursor
    controller_cursor = state.participant_controller.latest_reconnect_cursor(
        run_id=session.run_id,
        seat_id=session.seat_id,
    )
    if controller_cursor is not None:
        reconnect_cursor = _newer_reconnect_cursor(reconnect_cursor, controller_cursor)
    if window is not None:
        reconnect_cursor = _newer_reconnect_cursor(reconnect_cursor, window.reconnect_cursor)
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
    """Validate and accept a participant action submission."""
    if run_status != "running":
        raise ParticipantProtocolError(
            "run_not_accepting_actions",
            "Run is not accepting participant actions",
            run_id=run_id,
            seat_id=session.seat_id,
            reconnect_cursor=session.last_seen_cursor,
        )
    result = state.participant_controller.submit_action(
        run_id=run_id,
        seat_id=session.seat_id,
        payload=request_payload,
    )
    reconnect_cursor = result.get("reconnect_cursor")
    if isinstance(reconnect_cursor, str):
        reconnect_cursor = validate_reconnect_cursor(reconnect_cursor)
        with state.lock:
            state.participant_sessions[session.participant_session_token] = replace(
                session,
                last_seen_cursor=reconnect_cursor,
            )
    return result


def participant_sse_events(
    state: ObserverServerState,
    *,
    run_id: str,
    session: ParticipantSession,
    run_status: str,
    cursor: str | None = None,
) -> list[tuple[str, dict[str, object]]]:
    """Return a finite skeleton event list for the participant SSE route."""
    if cursor is not None:
        try:
            validate_reconnect_cursor(cursor)
        except ParticipantProtocolError as exc:
            raise ParticipantProtocolError(
                "invalid_payload",
                exc.message,
                run_id=run_id,
                seat_id=session.seat_id,
                reconnect_cursor=session.last_seen_cursor,
            ) from exc
    events: list[tuple[str, dict[str, object]]] = [
        ("run_status", {"run_id": run_id, "status": run_status})
    ]
    window = state.participant_controller.open_window_for(
        run_id=session.run_id,
        seat_id=session.seat_id,
    )
    if window is not None:
        events.append(("action_window_opened", window.to_payload()))
    return events


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


def _newer_reconnect_cursor(left: str, right: str) -> str:
    return str(max(parse_reconnect_cursor(left), parse_reconnect_cursor(right)))
