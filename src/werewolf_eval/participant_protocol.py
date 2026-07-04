"""P3-C participant-seat protocol types and validators.

This module owns pure protocol validation for human participant sessions and
action windows. It deliberately has no HTTP routes, no persistence, and no game
loop coupling; P3-C-0b can import these helpers when adding server skeletons.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from werewolf_eval.observer_protocol import ObserverProtocolError, validate_run_id

PARTICIPANT_SESSION_SCHEMA_VERSION = "p3c.participant_session.v1"
ACTION_WINDOW_SCHEMA_VERSION = "p3c.action_window.v1"
ACTION_SUBMIT_RESULT_SCHEMA_VERSION = "p3c.action_submit_result.v1"
PARTICIPANT_ERROR_SCHEMA_VERSION = "p3c.error.v1"

TEXT_ACTION_CAP = 2000

ALLOWED_SEAT_IDS: tuple[str, ...] = ("p1", "p2", "p3", "p4", "p5", "p6")
ALLOWED_ACTION_TYPES: tuple[str, ...] = (
    "speech",
    "response",
    "vote",
    "final_words",
    "pass",
    "werewolf_kill",
    "seer_check",
    "witch_save",
    "witch_poison",
    "guard_protect",
    "hunter_shoot",
)
ACTION_WINDOW_STATUSES: tuple[str, ...] = (
    "open",
    "accepted",
    "timed_out",
    "cancelled",
    "superseded",
)
TIMEOUT_POLICIES: tuple[str, ...] = ("skip", "pass", "ai_takeover")

PARTICIPANT_ERROR_CODES: tuple[str, ...] = (
    "invalid_payload",
    "missing_or_invalid_session",
    "seat_not_controlled_by_session",
    "visibility_forbidden",
    "run_not_found",
    "action_window_not_found",
    "stale_game_revision",
    "idempotency_conflict",
    "action_window_closed",
    "illegal_action",
    "run_not_accepting_actions",
)

PARTICIPANT_ERROR_HTTP_STATUS: dict[str, int] = {
    "invalid_payload": 400,
    "missing_or_invalid_session": 401,
    "seat_not_controlled_by_session": 403,
    "visibility_forbidden": 403,
    "run_not_found": 404,
    "action_window_not_found": 404,
    "stale_game_revision": 409,
    "idempotency_conflict": 409,
    "action_window_closed": 409,
    "illegal_action": 422,
    "run_not_accepting_actions": 423,
}

_SAFE_PROTOCOL_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,255}$")
_FORBIDDEN_ENVELOPE_KEYS = {
    "authorization",
    "authorization_header",
    "join_code",
    "participant_session_token",
    "provider_secret",
    "token",
}


class ParticipantProtocolError(ValueError):
    """Raised when participant protocol input is invalid."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        run_id: str | None = None,
        seat_id: str | None = None,
        action_window_id: str | None = None,
        current_game_revision: int | None = None,
        reconnect_cursor: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        if error_code not in PARTICIPANT_ERROR_CODES:
            raise ValueError(f"Unknown participant error_code: {error_code!r}")
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.run_id = run_id
        self.seat_id = seat_id
        self.action_window_id = action_window_id
        self.current_game_revision = current_game_revision
        self.reconnect_cursor = reconnect_cursor
        self.details = dict(details or {})

    @property
    def http_status(self) -> int:
        return PARTICIPANT_ERROR_HTTP_STATUS[self.error_code]

    def to_envelope(self) -> dict[str, object]:
        """Return the public error envelope, with secret-bearing keys stripped."""
        return build_participant_error_envelope(
            self.error_code,
            self.message,
            run_id=self.run_id,
            seat_id=self.seat_id,
            action_window_id=self.action_window_id,
            current_game_revision=self.current_game_revision,
            reconnect_cursor=self.reconnect_cursor,
            details=self.details,
        )


def _protocol_error(error_code: str, message: str, **context: object) -> ParticipantProtocolError:
    return ParticipantProtocolError(error_code, message, **context)


def validate_seat_id(seat_id: str) -> str:
    """Validate and return a first-slice seat id (``p1`` .. ``p6``)."""
    if not isinstance(seat_id, str):
        raise _protocol_error(
            "invalid_payload",
            f"seat_id must be a string, got {type(seat_id).__name__}",
        )
    if seat_id not in ALLOWED_SEAT_IDS:
        raise _protocol_error(
            "invalid_payload",
            f"seat_id must be one of {ALLOWED_SEAT_IDS}, got {seat_id!r}",
        )
    return seat_id


def perspective_for_seat(seat_id: str) -> str:
    """Return the participant perspective derived from seat ownership."""
    return f"role:{validate_seat_id(seat_id)}"


def validate_participant_run_id(run_id: str) -> str:
    """Validate and return *run_id* using the observer protocol authority."""
    try:
        return validate_run_id(run_id)
    except ObserverProtocolError as exc:
        raise _protocol_error("invalid_payload", str(exc)) from exc


def validate_protocol_id(value: str, field_name: str) -> str:
    """Validate an action-window/idempotency style protocol identifier."""
    if not isinstance(value, str):
        raise _protocol_error(
            "invalid_payload",
            f"{field_name} must be a string, got {type(value).__name__}",
        )
    if not value:
        raise _protocol_error("invalid_payload", f"{field_name} must not be empty")
    if ".." in value or "/" in value or "\\" in value or "?" in value or "%" in value:
        raise _protocol_error(
            "invalid_payload",
            f"{field_name} contains forbidden characters: {value!r}",
        )
    if not _SAFE_PROTOCOL_ID_RE.match(value):
        raise _protocol_error(
            "invalid_payload",
            f"{field_name} contains invalid characters: {value!r}",
        )
    return value


def validate_game_revision(game_revision: int) -> int:
    """Validate a non-negative game revision.

    P3-C-0a only validates the scalar shape. The server integration slice must
    bump this monotonically when a seat-visible event changes visible state or
    current action legality for that participant.
    """
    if isinstance(game_revision, bool) or not isinstance(game_revision, int):
        raise _protocol_error(
            "invalid_payload",
            f"game_revision must be a non-negative integer, got {type(game_revision).__name__}",
        )
    if game_revision < 0:
        raise _protocol_error("invalid_payload", "game_revision must be non-negative")
    return game_revision


def validate_non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _protocol_error(
            "invalid_payload",
            f"{field_name} must be a non-negative integer, got {type(value).__name__}",
        )
    if value < 0:
        raise _protocol_error("invalid_payload", f"{field_name} must be non-negative")
    return value


@dataclass(frozen=True, order=True)
class ReconnectCursor:
    """Comparable reconnect cursor backed by a numeric event index."""

    event_index: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "event_index", validate_non_negative_int(self.event_index, "event_index")
        )

    def __str__(self) -> str:
        return f"event:{self.event_index}"


def parse_reconnect_cursor(cursor: str) -> ReconnectCursor:
    """Parse ``event:<non-negative-int>`` into a comparable cursor."""
    if not isinstance(cursor, str):
        raise _protocol_error(
            "invalid_payload",
            f"reconnect_cursor must be a string, got {type(cursor).__name__}",
        )
    if not cursor.startswith("event:"):
        raise _protocol_error(
            "invalid_payload",
            "reconnect_cursor must use event:<non-negative-int> format",
        )
    raw_index = cursor[len("event:"):]
    if not raw_index or not raw_index.isdecimal():
        raise _protocol_error(
            "invalid_payload",
            "reconnect_cursor must use event:<non-negative-int> format",
        )
    return ReconnectCursor(int(raw_index))


def format_reconnect_cursor(event_index: int) -> str:
    """Return the canonical reconnect cursor for *event_index*."""
    return str(ReconnectCursor(event_index))


def validate_reconnect_cursor(cursor: str) -> str:
    """Validate and canonicalize a reconnect cursor string."""
    return str(parse_reconnect_cursor(cursor))


def validate_action_type(action_type: str) -> str:
    if not isinstance(action_type, str):
        raise _protocol_error(
            "invalid_payload",
            f"action_type must be a string, got {type(action_type).__name__}",
        )
    if action_type not in ALLOWED_ACTION_TYPES:
        raise _protocol_error(
            "invalid_payload",
            f"action_type must be one of {ALLOWED_ACTION_TYPES}, got {action_type!r}",
        )
    return action_type


def validate_action_window_status(status: str) -> str:
    if not isinstance(status, str):
        raise _protocol_error(
            "invalid_payload",
            f"status must be a string, got {type(status).__name__}",
        )
    if status not in ACTION_WINDOW_STATUSES:
        raise _protocol_error(
            "invalid_payload",
            f"status must be one of {ACTION_WINDOW_STATUSES}, got {status!r}",
        )
    return status


def validate_timeout_policy(
    policy: str,
    *,
    skippable: bool = False,
    ai_takeover_allowed: bool = False,
) -> str:
    """Validate first-slice timeout policy gating.

    ``pass`` is supported broadly. ``ai_takeover`` is supported only where the
    caller explicitly says the profile allows takeover. ``skip`` remains in the
    protocol but must be explicitly marked skippable in this first slice.
    """
    if not isinstance(policy, str):
        raise _protocol_error(
            "invalid_payload",
            f"default_on_timeout must be a string, got {type(policy).__name__}",
        )
    if policy not in TIMEOUT_POLICIES:
        raise _protocol_error(
            "invalid_payload",
            f"default_on_timeout must be one of {TIMEOUT_POLICIES}, got {policy!r}",
        )
    if policy == "skip" and not skippable:
        raise _protocol_error(
            "invalid_payload",
            "timeout policy 'skip' requires an explicitly skippable window",
        )
    if policy == "ai_takeover" and not ai_takeover_allowed:
        raise _protocol_error(
            "invalid_payload",
            "timeout policy 'ai_takeover' requires explicit profile gating",
        )
    return policy


def _validate_allowed_actions(allowed_actions: Iterable[str]) -> tuple[str, ...]:
    if isinstance(allowed_actions, (str, bytes)) or not isinstance(allowed_actions, Iterable):
        raise _protocol_error("invalid_payload", "allowed_actions must be an iterable of action types")
    normalized = tuple(validate_action_type(action) for action in allowed_actions)
    if not normalized:
        raise _protocol_error("invalid_payload", "allowed_actions must not be empty")
    return normalized


def _validate_json_mapping(payload: Mapping[str, object], field_name: str) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise _protocol_error("invalid_payload", f"{field_name} must be a JSON object")
    normalized = dict(payload)
    try:
        json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise _protocol_error("invalid_payload", f"{field_name} must be JSON-serializable") from exc
    return normalized


def _validate_phase(phase: str) -> str:
    if not isinstance(phase, str):
        raise _protocol_error(
            "invalid_payload",
            f"phase must be a string, got {type(phase).__name__}",
        )
    phase = phase.strip()
    if not phase:
        raise _protocol_error("invalid_payload", "phase must not be empty")
    return phase


def _validate_text(text: object, field_name: str, *, cap: int = TEXT_ACTION_CAP) -> str:
    if not isinstance(text, str):
        raise _protocol_error("invalid_payload", f"{field_name} must be a string")
    for ch in text:
        codepoint = ord(ch)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise _protocol_error(
                "invalid_payload",
                f"{field_name} must contain Unicode scalar values only",
            )
    if len(text) > cap:
        raise _protocol_error(
            "invalid_payload",
            f"{field_name} exceeds {cap} Unicode scalar values",
            details={"text_cap": cap},
        )
    return text


def _validate_optional_string_list(value: object, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise _protocol_error("invalid_payload", f"{field_name} must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise _protocol_error("invalid_payload", f"{field_name} must contain non-empty strings")
        result.append(item)
    return result


def validate_action_payload(
    action_type: str,
    payload: Mapping[str, object],
    *,
    text_cap: int = TEXT_ACTION_CAP,
) -> dict[str, object]:
    """Validate first-slice action payload shape and return a normalized copy."""
    action_type = validate_action_type(action_type)
    payload = _validate_json_mapping(payload, "payload")

    if action_type in ("speech", "response"):
        extra = set(payload) - {"text", "reply_to_event_ids", "addressed_seats"}
        if extra:
            raise _protocol_error("invalid_payload", f"Unexpected {action_type} payload keys: {sorted(extra)}")
        if "text" not in payload:
            raise _protocol_error("invalid_payload", f"{action_type} payload requires text")
        text = _validate_text(payload["text"], "text", cap=text_cap)
        reply_to_event_ids = _validate_optional_string_list(
            payload.get("reply_to_event_ids"), "reply_to_event_ids"
        )
        addressed_seats = [
            validate_seat_id(seat)
            for seat in _validate_optional_string_list(payload.get("addressed_seats"), "addressed_seats")
        ]
        normalized: dict[str, object] = {"text": text}
        if "reply_to_event_ids" in payload:
            normalized["reply_to_event_ids"] = reply_to_event_ids
        if "addressed_seats" in payload:
            normalized["addressed_seats"] = addressed_seats
        return normalized

    if action_type == "final_words":
        extra = set(payload) - {"text"}
        if extra:
            raise _protocol_error("invalid_payload", f"Unexpected final_words payload keys: {sorted(extra)}")
        if "text" not in payload:
            raise _protocol_error("invalid_payload", "final_words payload requires text")
        return {"text": _validate_text(payload["text"], "text", cap=text_cap)}

    if action_type in (
        "vote",
        "werewolf_kill",
        "seer_check",
        "witch_save",
        "witch_poison",
        "guard_protect",
        "hunter_shoot",
    ):
        extra = set(payload) - {"target"}
        if extra:
            raise _protocol_error("invalid_payload", f"Unexpected {action_type} payload keys: {sorted(extra)}")
        if "target" not in payload:
            raise _protocol_error("invalid_payload", f"{action_type} payload requires target")
        return {"target": validate_seat_id(payload["target"])}

    if action_type == "pass":
        if payload:
            raise _protocol_error("invalid_payload", "pass payload must be empty")
        return {}

    raise AssertionError(f"Unhandled action_type: {action_type}")


@dataclass(frozen=True)
class ParticipantSession:
    """A bearer participant session bound to one run and one seat."""

    run_id: str
    seat_id: str
    participant_session_token: str = field(repr=False)
    issued_at: str
    expires_at: str
    last_seen_cursor: str
    revoked_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", validate_participant_run_id(self.run_id))
        object.__setattr__(self, "seat_id", validate_seat_id(self.seat_id))
        token = self.participant_session_token
        if not isinstance(token, str) or not token:
            raise _protocol_error(
                "missing_or_invalid_session",
                "participant_session_token must be a non-empty string",
            )
        object.__setattr__(self, "last_seen_cursor", validate_reconnect_cursor(self.last_seen_cursor))

    @property
    def perspective(self) -> str:
        return perspective_for_seat(self.seat_id)

    def to_payload(self, *, include_token: bool = False) -> dict[str, object]:
        """Serialize session metadata.

        The token is omitted by default so diagnostics and error paths do not
        accidentally leak it. Join/resume routes may opt in explicitly.
        """
        payload: dict[str, object] = {
            "schema_version": PARTICIPANT_SESSION_SCHEMA_VERSION,
            "run_id": self.run_id,
            "seat_id": self.seat_id,
            "perspective": self.perspective,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "reconnect_cursor": self.last_seen_cursor,
        }
        if self.revoked_at is not None:
            payload["revoked_at"] = self.revoked_at
        if include_token:
            payload["participant_session_token"] = self.participant_session_token
        return payload


@dataclass(frozen=True)
class ActionWindow:
    """Server-owned participant action window."""

    action_window_id: str
    run_id: str
    seat_id: str
    phase: str
    round: int
    game_revision: int
    opened_at_event_id: str
    deadline_at: str
    allowed_actions: tuple[str, ...]
    required: bool
    default_on_timeout: str
    status: str
    reconnect_cursor: str
    skippable: bool = False
    ai_takeover_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "action_window_id", validate_protocol_id(self.action_window_id, "action_window_id")
        )
        object.__setattr__(self, "run_id", validate_participant_run_id(self.run_id))
        object.__setattr__(self, "seat_id", validate_seat_id(self.seat_id))
        object.__setattr__(self, "phase", _validate_phase(self.phase))
        object.__setattr__(self, "round", validate_non_negative_int(self.round, "round"))
        object.__setattr__(
            self, "game_revision", validate_game_revision(self.game_revision)
        )
        object.__setattr__(
            self,
            "opened_at_event_id",
            validate_protocol_id(self.opened_at_event_id, "opened_at_event_id"),
        )
        object.__setattr__(
            self, "allowed_actions", _validate_allowed_actions(self.allowed_actions)
        )
        if not isinstance(self.required, bool):
            raise _protocol_error("invalid_payload", "required must be a boolean")
        if not isinstance(self.skippable, bool):
            raise _protocol_error("invalid_payload", "skippable must be a boolean")
        if not isinstance(self.ai_takeover_allowed, bool):
            raise _protocol_error("invalid_payload", "ai_takeover_allowed must be a boolean")
        object.__setattr__(
            self,
            "default_on_timeout",
            validate_timeout_policy(
                self.default_on_timeout,
                skippable=self.skippable,
                ai_takeover_allowed=self.ai_takeover_allowed,
            ),
        )
        object.__setattr__(self, "status", validate_action_window_status(self.status))
        object.__setattr__(self, "reconnect_cursor", validate_reconnect_cursor(self.reconnect_cursor))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": ACTION_WINDOW_SCHEMA_VERSION,
            "action_window_id": self.action_window_id,
            "run_id": self.run_id,
            "seat_id": self.seat_id,
            "phase": self.phase,
            "round": self.round,
            "game_revision": self.game_revision,
            "opened_at_event_id": self.opened_at_event_id,
            "deadline_at": self.deadline_at,
            "allowed_actions": list(self.allowed_actions),
            "required": self.required,
            "default_on_timeout": self.default_on_timeout,
            "status": self.status,
            "reconnect_cursor": self.reconnect_cursor,
        }


@dataclass(frozen=True)
class ParticipantActionSubmission:
    """Client-submitted action candidate for a server-owned action window."""

    action_window_id: str
    game_revision: int
    idempotency_key: str
    action_type: str
    payload: Mapping[str, object]
    client_observed_event_id: str | None = None
    client_sent_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "action_window_id", validate_protocol_id(self.action_window_id, "action_window_id")
        )
        object.__setattr__(
            self, "game_revision", validate_game_revision(self.game_revision)
        )
        object.__setattr__(
            self, "idempotency_key", validate_protocol_id(self.idempotency_key, "idempotency_key")
        )
        action_type = validate_action_type(self.action_type)
        object.__setattr__(self, "action_type", action_type)
        object.__setattr__(self, "payload", validate_action_payload(action_type, self.payload))
        if self.client_observed_event_id is not None:
            object.__setattr__(
                self,
                "client_observed_event_id",
                validate_protocol_id(self.client_observed_event_id, "client_observed_event_id"),
            )

    def idempotency_fingerprint(self) -> str:
        """Canonical material for action-window-scoped idempotency comparison."""
        material = {
            "game_revision": self.game_revision,
            "action_type": self.action_type,
            "payload": self.payload,
        }
        return json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "action_window_id": self.action_window_id,
            "game_revision": self.game_revision,
            "idempotency_key": self.idempotency_key,
            "action_type": self.action_type,
            "payload": dict(self.payload),
        }
        if self.client_observed_event_id is not None:
            payload["client_observed_event_id"] = self.client_observed_event_id
        if self.client_sent_at is not None:
            payload["client_sent_at"] = self.client_sent_at
        return payload


def ensure_single_open_action_window(windows: Iterable[ActionWindow]) -> None:
    """Enforce at most one open action window per run+seat in the first slice."""
    seen: dict[tuple[str, str], str] = {}
    for window in windows:
        if window.status != "open":
            continue
        key = (window.run_id, window.seat_id)
        previous = seen.get(key)
        if previous is not None:
            raise _protocol_error(
                "invalid_payload",
                "only one open action window is allowed per human seat",
                run_id=window.run_id,
                seat_id=window.seat_id,
                action_window_id=window.action_window_id,
                reconnect_cursor=window.reconnect_cursor,
            )
        seen[key] = window.action_window_id


def validate_submission_for_window(
    submission: ParticipantActionSubmission,
    window: ActionWindow,
) -> None:
    """Validate a participant submission against a resolved server window."""
    if submission.action_window_id != window.action_window_id:
        raise _protocol_error(
            "action_window_not_found",
            "action window does not belong to this context",
            run_id=window.run_id,
            seat_id=window.seat_id,
            action_window_id=submission.action_window_id,
            reconnect_cursor=window.reconnect_cursor,
        )
    if window.status != "open":
        raise _protocol_error(
            "action_window_closed",
            f"Action window {window.action_window_id} is {window.status}",
            run_id=window.run_id,
            seat_id=window.seat_id,
            action_window_id=window.action_window_id,
            current_game_revision=window.game_revision,
            reconnect_cursor=window.reconnect_cursor,
        )
    if submission.game_revision != window.game_revision:
        raise _protocol_error(
            "stale_game_revision",
            "Submitted game_revision is not current for this action window",
            run_id=window.run_id,
            seat_id=window.seat_id,
            action_window_id=window.action_window_id,
            current_game_revision=window.game_revision,
            reconnect_cursor=window.reconnect_cursor,
        )
    if submission.action_type not in window.allowed_actions:
        raise _protocol_error(
            "illegal_action",
            f"Action {submission.action_type!r} is not legal for this window",
            run_id=window.run_id,
            seat_id=window.seat_id,
            action_window_id=window.action_window_id,
            current_game_revision=window.game_revision,
            reconnect_cursor=window.reconnect_cursor,
        )


@dataclass(frozen=True)
class IdempotencyOutcome:
    """Result of recording a participant action under an idempotency key."""

    status: str
    result: dict[str, object]


@dataclass
class _IdempotencyRecord:
    fingerprint: str
    result: dict[str, object]


class ActionIdempotencyTracker:
    """In-memory action-window-scoped idempotency helper.

    P3-C-0a intentionally does not persist records. P3-C-0b/C-1 can replace the
    backing store without changing the comparison semantics.
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, _IdempotencyRecord]] = {}

    def duplicate_for(
        self,
        submission: ParticipantActionSubmission,
    ) -> IdempotencyOutcome | None:
        """Return the original result for a repeated key, or raise on conflict."""
        window_records = self._records.get(submission.action_window_id, {})
        existing = window_records.get(submission.idempotency_key)
        if existing is None:
            return None
        if existing.fingerprint != submission.idempotency_fingerprint():
            raise _protocol_error(
                "idempotency_conflict",
                "idempotency_key was already used for a different action payload",
                action_window_id=submission.action_window_id,
            )
        return IdempotencyOutcome("duplicate", copy.deepcopy(existing.result))

    def record_or_duplicate(
        self,
        submission: ParticipantActionSubmission,
        result: Mapping[str, object],
    ) -> IdempotencyOutcome:
        duplicate = self.duplicate_for(submission)
        if duplicate is not None:
            return duplicate

        window_records = self._records.setdefault(submission.action_window_id, {})
        fingerprint = submission.idempotency_fingerprint()
        stored_result = copy.deepcopy(dict(result))
        window_records[submission.idempotency_key] = _IdempotencyRecord(
            fingerprint=fingerprint,
            result=stored_result,
        )
        return IdempotencyOutcome("stored", copy.deepcopy(stored_result))


def _strip_forbidden_envelope_keys(value: object) -> object:
    if isinstance(value, Mapping):
        clean: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in _FORBIDDEN_ENVELOPE_KEYS:
                continue
            clean[key_text] = _strip_forbidden_envelope_keys(item)
        return clean
    if isinstance(value, list):
        return [_strip_forbidden_envelope_keys(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_forbidden_envelope_keys(item) for item in value]
    return value


def build_participant_error_envelope(
    error_code: str,
    message: str,
    *,
    run_id: str | None = None,
    seat_id: str | None = None,
    action_window_id: str | None = None,
    current_game_revision: int | None = None,
    reconnect_cursor: str | None = None,
    details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the stable P3-C participant error envelope.

    The builder only emits context fields when the caller knows them. Secret-like
    keys are removed from details so tokens, Authorization headers, join codes,
    and provider secrets cannot leak through generic diagnostic context.
    """
    if error_code not in PARTICIPANT_ERROR_CODES:
        raise ValueError(f"Unknown participant error_code: {error_code!r}")
    if not isinstance(message, str) or not message:
        raise ValueError("message must be a non-empty string")

    envelope: dict[str, object] = {
        "schema_version": PARTICIPANT_ERROR_SCHEMA_VERSION,
        "error_code": error_code,
        "message": message,
    }
    if run_id is not None:
        envelope["run_id"] = validate_participant_run_id(run_id)
    if seat_id is not None:
        envelope["seat_id"] = validate_seat_id(seat_id)
    if action_window_id is not None:
        envelope["action_window_id"] = validate_protocol_id(
            action_window_id, "action_window_id"
        )
    if current_game_revision is not None:
        envelope["current_game_revision"] = validate_game_revision(current_game_revision)
    if reconnect_cursor is not None:
        envelope["reconnect_cursor"] = validate_reconnect_cursor(reconnect_cursor)

    clean_details = _strip_forbidden_envelope_keys(details or {})
    if isinstance(clean_details, dict) and clean_details:
        envelope["details"] = clean_details
    return envelope
