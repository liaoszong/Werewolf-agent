"""Runtime event contract and writer for live-observation G1h spine.

This module defines the event envelope, validation helpers, secret redaction,
and the ``RuntimeEventWriter`` that appends structured events to a JSONL file
during a live game run.  All public names below are part of the contract.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Event-kind constants
# ---------------------------------------------------------------------------

RUNTIME_EVENT_KINDS: tuple[str, ...] = (
    "game_started",
    "round_started",
    "observation_delivered",
    "decision_made",
    "action_executed",
    "provider_request",
    "provider_response",
    "provider_failure",
    "provider_request_prepared",
    "provider_response_received",
    "provider_parse_succeeded",
    "provider_parse_failed",
    "provider_action_invalid",
    "provider_timeout",
    "provider_failed",
    "player_eliminated",
    "game_ended",
    "snapshot_written",
    "vote_cast",
    "run_started",
    "phase_started",
    "consensus_started",
    "consensus_resolved",
    "observation_built",
    "agent_action_selected",
    "game_event_emitted",
    "artifact_written",
    "run_finalized",
)

RUNTIME_EVENT_VISIBILITIES: tuple[str, ...] = (
    "public",
    "private",
    "internal",
    "all",
    "seer",
    "witch",
    "werewolf_team",
)

# Substrings that look like API-key / bearer-token secrets.
# The redaction check is case-insensitive.
SECRET_KEY_FRAGMENTS: tuple[str, ...] = (
    "sk-",
    "Bearer ",
    "api-key",
    "api_key",
    "apikey",
    "secret",
    "token",
    "auth",
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RuntimeEventError(ValueError):
    """Raised when a runtime event fails validation or encounters a secret."""


# ---------------------------------------------------------------------------
# Secret helpers
# ---------------------------------------------------------------------------


def _contains_secret_fragment(value: object) -> bool:
    """Return True when *value* (coerced to str) contains any secret fragment."""
    text = str(value).lower()
    return any(fragment.lower() in text for fragment in SECRET_KEY_FRAGMENTS)


def redact_secret_values(value: object) -> object:
    """Recursively walk *value* and replace any secret-like value with
    ``"<REDACTED>"``.

    Dictionaries and lists are traversed; scalar values are checked directly.
    """
    if isinstance(value, dict):
        return {k: redact_secret_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_secret_values(item) for item in value]
    if isinstance(value, str):
        return "<REDACTED>" if _contains_secret_fragment(value) else value
    return value


def assert_no_secret_patterns(value: object) -> None:
    """Raise ``RuntimeEventError`` if *value* (or any nested value) contains a
    secret fragment."""
    # We piggyback on redact_secret_values by checking whether redaction
    # would change anything.  This walks the structure once.
    redacted = redact_secret_values(value)
    if redacted != value:
        # Find the first offending key/value for a better error message.
        _raise_for_secrets(value)


def _raise_for_secrets(value: object, _path: str = "") -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _raise_for_secrets(v, f"{_path}.{k}" if _path else k)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _raise_for_secrets(item, f"{_path}[{i}]")
    elif isinstance(value, str) and _contains_secret_fragment(value):
        raise RuntimeEventError(
            f"Secret pattern detected in runtime event at '{_path}'"
        )


# ---------------------------------------------------------------------------
# Event validation
# ---------------------------------------------------------------------------

_REQUIRED_EVENT_FIELDS = (
    "event_id",
    "seq",
    "kind",
    "round",
    "phase",
    "actor",
    "visibility",
    "ts",
)

_ENVELOPE_FIELDS = _REQUIRED_EVENT_FIELDS + ("payload", "refs")


def validate_runtime_event(event: dict[str, object]) -> None:
    """Validate a runtime event envelope.

    Checks:
    * Required fields are present.
    * ``kind`` is in ``RUNTIME_EVENT_KINDS``.
    * ``visibility`` is in ``RUNTIME_EVENT_VISIBILITIES``.
    * ``seq`` and ``round`` are non-negative integers.
    * ``actor`` and ``phase`` are non-empty strings.
    * No secret patterns in ``payload`` or ``refs``.
    """
    for field in _REQUIRED_EVENT_FIELDS:
        if field not in event:
            raise RuntimeEventError(f"Missing required event field: {field!r}")

    kind = event["kind"]
    if not isinstance(kind, str) or kind not in RUNTIME_EVENT_KINDS:
        raise RuntimeEventError(
            f"Invalid event kind: {kind!r}.  Allowed: {RUNTIME_EVENT_KINDS}"
        )

    visibility = event["visibility"]
    if not isinstance(visibility, str) or visibility not in RUNTIME_EVENT_VISIBILITIES:
        raise RuntimeEventError(
            f"Invalid visibility: {visibility!r}.  "
            f"Allowed: {RUNTIME_EVENT_VISIBILITIES}"
        )

    for field, expected_type in (
        ("seq", int),
        ("round", int),
    ):
        val = event[field]
        if not isinstance(val, expected_type) or val < 0:
            raise RuntimeEventError(
                f"Field {field!r} must be a non-negative {expected_type.__name__}, "
                f"got {val!r}"
            )

    for field in ("actor", "phase"):
        val = event[field]
        if not isinstance(val, str) or not val:
            raise RuntimeEventError(
                f"Field {field!r} must be a non-empty string, got {val!r}"
            )

    ts = event.get("ts")
    if not isinstance(ts, str) or not ts:
        raise RuntimeEventError(f"Field 'ts' must be a non-empty string, got {ts!r}")

    # Check payload and refs for secrets.
    for opt_field in ("payload", "refs"):
        val = event.get(opt_field)
        if val is not None:
            assert_no_secret_patterns(val)


# ---------------------------------------------------------------------------
# JSONL reader
# ---------------------------------------------------------------------------


def read_events_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read an ``events.jsonl`` file, validate every event, and return the
    list.

    Raises ``RuntimeEventError`` on:
    * Empty lines
    * Malformed JSON
    * Duplicate ``event_id``
    * Non-monotonic ``seq``
    * Validation failures from ``validate_runtime_event``
    """
    if not path.is_file():
        raise RuntimeEventError(f"Events file not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    prev_seq: int | None = None

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            raise RuntimeEventError(
                f"Empty line at {path}:{lineno}"
            )

        try:
            event: dict[str, Any] = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise RuntimeEventError(
                f"Malformed JSON at {path}:{lineno}: {exc}"
            ) from exc

        if not isinstance(event, dict):
            raise RuntimeEventError(
                f"Line at {path}:{lineno} is not a JSON object"
            )

        validate_runtime_event(event)

        event_id = str(event["event_id"])
        if event_id in seen_ids:
            raise RuntimeEventError(
                f"Duplicate event_id {event_id!r} at {path}:{lineno}"
            )
        seen_ids.add(event_id)

        seq = int(event["seq"])
        if prev_seq is not None and seq <= prev_seq:
            raise RuntimeEventError(
                f"Non-monotonic seq at {path}:{lineno}: "
                f"{seq} after {prev_seq}"
            )
        prev_seq = seq

        events.append(event)

    return events


# ---------------------------------------------------------------------------
# RuntimeEventWriter
# ---------------------------------------------------------------------------

_DEFAULT_ISO_TS: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat()


class RuntimeEventWriter:
    """Append-only writer for runtime event JSONL files.

    Threading note: this writer is **not** thread-safe.  A single game run
    uses one writer instance from the main event loop.
    """

    def __init__(
        self,
        run_id: str,
        out_dir: Path,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._run_id = run_id
        self._out_dir = out_dir
        self._clock = clock or _DEFAULT_ISO_TS

        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Start a fresh events file.
        self._events_path.write_text("", encoding="utf-8")

        self._seq: int = 0

    # -- properties ---------------------------------------------------------

    @property
    def events_path(self) -> Path:
        return self._out_dir / "events.jsonl"

    @property
    def snapshots_dir(self) -> Path:
        return self._out_dir / "snapshots"

    # -- internal helpers ---------------------------------------------------

    @property
    def _events_path(self) -> Path:
        return self.events_path

    @property
    def _snapshots_dir(self) -> Path:
        return self.snapshots_dir

    def _next_seq(self) -> int:
        val = self._seq
        self._seq += 1
        return val

    # -- emit ---------------------------------------------------------------

    def emit(
        self,
        kind: str,
        *,
        round: int,
        phase: str,
        actor: str,
        visibility: str,
        payload: dict[str, object] | None = None,
        refs: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Build, validate, append, and return an event envelope."""
        event: dict[str, object] = {
            "event_id": str(uuid.uuid4()),
            "seq": self._next_seq(),
            "kind": kind,
            "round": round,
            "phase": phase,
            "actor": actor,
            "visibility": visibility,
            "ts": self._clock(),
        }
        if payload is not None:
            event["payload"] = payload
        if refs is not None:
            event["refs"] = refs

        validate_runtime_event(event)

        line = json.dumps(event, ensure_ascii=False, sort_keys=True)
        with self._events_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

        return event

    # -- write_snapshot -----------------------------------------------------

    def write_snapshot(
        self,
        name: str,
        snapshot: dict[str, object],
        *,
        visibility: str,
        round: int,
        phase: str,
        actor: str,
    ) -> str:
        """Redact secrets in *snapshot*, write ``snapshots/<name>.json``, and
        emit a ``snapshot_written`` event.

        Returns the relative path ``snapshots/<name>.json``.
        """
        safe = redact_secret_values(snapshot)
        # Ensure the redacted snapshot is also JSON-safe; deep-copy is implicit.
        snapshot_path = self._snapshots_dir / f"{name}.json"
        with snapshot_path.open("w", encoding="utf-8") as fh:
            json.dump(safe, fh, ensure_ascii=False, sort_keys=True)

        self.emit(
            "snapshot_written",
            round=round,
            phase=phase,
            actor=actor,
            visibility=visibility,
            payload={"snapshot_name": name},
        )
        return f"snapshots/{name}.json"

    # -- write_prompt_manifest ----------------------------------------------

    def write_prompt_manifest(self, manifest: dict[str, object]) -> Path:
        """Redact secrets in *manifest* and write ``prompt-manifest.json``."""
        safe = redact_secret_values(manifest)
        path = self._out_dir / "prompt-manifest.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(safe, fh, ensure_ascii=False, sort_keys=True, indent=2)
        return path


# ---------------------------------------------------------------------------
# Snapshot / projection builders
# ---------------------------------------------------------------------------

_KNOWN_ROLE_TEAMS: dict[str, str] = {
    "villager": "villager",
    "seer": "villager",
    "witch": "villager",
    "werewolf": "werewolf",
}


def _project_known_roles_for_observer(
    known_roles: dict[str, str],
    observer_team: str,
) -> dict[str, str]:
    """Filter *known_roles* so that non-wolf observers never see hidden wolf roles.

    If the observer is on the villager team, any player whose role is "werewolf"
    is replaced with "unknown" in the projected output.  Wolf-team observers
    see the full table.
    """
    if observer_team == "werewolf":
        return dict(known_roles)
    # Non-wolves: hide werewolf roles.
    projected: dict[str, str] = {}
    for pid, role in known_roles.items():
        team = _KNOWN_ROLE_TEAMS.get(role, "villager")
        if team == "werewolf":
            projected[pid] = "unknown"
        else:
            projected[pid] = role
    return projected


def build_god_snapshot(
    *,
    run_id: str,
    game_id: str,
    round: int,
    phase: str,
    players: list[dict[str, object]],
    alive_players: list[str],
    public_event_ids: list[str],
    private_event_ids: list[str],
) -> dict[str, object]:
    """Build a full god-view snapshot with complete role/team visibility."""
    return {
        "run_id": run_id,
        "game_id": game_id,
        "round": round,
        "phase": phase,
        "players": players,
        "alive_players": list(alive_players),
        "public_event_ids": list(public_event_ids),
        "private_event_ids": list(private_event_ids),
        "snapshot_type": "god",
    }


def build_role_projection_snapshot(
    *,
    run_id: str,
    observation: object,
) -> dict[str, object]:
    """Build a role-filtered projection from an observation.

    *observation* may be an object with a ``to_dict()`` method, or a plain
    ``dict``.  The projection strips hidden wolf roles for non-wolf observers.
    """
    if hasattr(observation, "to_dict"):
        obs_dict: dict[str, object] = observation.to_dict()  # type: ignore[union-attr]
    else:
        obs_dict = dict(observation)  # type: ignore[arg-type]

    known_roles_raw = obs_dict.get("known_roles", {})
    if not isinstance(known_roles_raw, dict):
        known_roles_raw = {}

    team: str = str(obs_dict.get("team", "villager"))
    projected_roles = _project_known_roles_for_observer(
        {str(k): str(v) for k, v in known_roles_raw.items()}, team
    )

    return {
        "run_id": run_id,
        "player_id": str(obs_dict.get("player_id", "")),
        "role": str(obs_dict.get("role", "")),
        "team": team,
        "phase": str(obs_dict.get("phase", "")),
        "round": int(obs_dict.get("round", 0)),
        "alive_players": list(obs_dict.get("alive_players", [])),
        "public_event_ids": list(obs_dict.get("public_event_ids", [])),
        "private_event_ids": list(obs_dict.get("private_event_ids", [])),
        "projected_known_roles": projected_roles,
        "snapshot_type": "role_projection",
    }


# ---------------------------------------------------------------------------
# Prompt manifest builder
# ---------------------------------------------------------------------------


def _hash_prompt_text(text: str) -> str:
    """Return the SHA-256 hex digest of *text*."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_prompt_manifest(
    *,
    run_id: str,
    source_label: str,
    agents: list[dict[str, object]],
) -> dict[str, object]:
    """Build a prompt manifest with redaction-safe content and SHA-256 hashes.

    Each agent dict may include:

    * ``player_id`` (str)
    * ``role`` (str)
    * ``prompt`` (str) — full prompt text; will be hashed and removed
    * ``provider`` (str)
    * ``model`` (str)

    Returns a manifest dict suitable for ``RuntimeEventWriter.write_prompt_manifest()``.
    """
    hashed_agents: list[dict[str, object]] = []
    for agent in agents:
        entry: dict[str, object] = {}
        for key in ("player_id", "role", "provider", "model"):
            val = agent.get(key)
            if val is not None:
                entry[str(key)] = val

        prompt_text = agent.get("prompt")
        if prompt_text is not None and isinstance(prompt_text, str) and prompt_text:
            entry["prompt_hash"] = _hash_prompt_text(prompt_text)
        else:
            # Hash deterministic metadata when no prompt is available.
            meta_parts: list[str] = []
            for k in ("provider", "model", "player_id"):
                v = agent.get(k)
                if v is not None:
                    meta_parts.append(f"{k}={v}")
            meta_text = "|".join(meta_parts)
            entry["prompt_hash"] = _hash_prompt_text(meta_text) if meta_text else ""

        hashed_agents.append(entry)

    manifest: dict[str, object] = {
        "run_id": run_id,
        "source_label": source_label,
        "agents": hashed_agents,
    }
    return redact_secret_values(manifest)  # type: ignore[return-value]
