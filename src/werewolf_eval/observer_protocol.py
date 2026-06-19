"""Observer protocol constants, path helpers, registries, visibility, and SSE helpers.

This module provides the shared protocol surface for the local observer HTTP server
(G2a).  It owns no network I/O, no server lifecycle, and no runtime.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from werewolf_eval.action_runtime.ruleset import known_role_teams

# Role -> team facts, derived from the ruleset (the authoritative declaration,
# ADR 2026-06-11). Re-exported HERE so observer-side modules keep importing
# protocol constants only (same R-06 discipline as PUBLIC_LIKE_EVENT_VISIBILITIES)
# and never import action_runtime directly.
KNOWN_ROLE_TEAMS: dict[str, str] = known_role_teams()

OBSERVER_SERVICE_NAME = "werewolf-observer"
DEFAULT_FAKE_TEMPLATE = "default_6p_fake"
DEFAULT_FAKE_MODE = "fake"

# G3-2 read-only runtime-capabilities payload (live posture, never a secret).
RUNTIME_CAPABILITIES_SCHEMA_VERSION = "g3.runtime_capabilities.v1"

ALLOWED_TEMPLATES: tuple[str, ...] = (
    "default_6p_fake",
)

ALLOWED_MODES: tuple[str, ...] = (
    "fake",
    "live",
)

ALLOWED_ARTIFACTS: tuple[str, ...] = (
    "events.jsonl",
    "prompt-manifest.json",
    "game-log.json",
    "decision-log.json",
    "consensus-log.json",
    "provider-trace.json",
    "failure-audit.json",
    "resolved-profile.json",
    "settlement-bundle.json",
)

ALLOWED_PERSPECTIVES: tuple[str, ...] = (
    "god",
    "public",
    "role:p1",
    "role:p2",
    "role:p3",
    "role:p4",
    "role:p5",
    "role:p6",
    "team:werewolf",
)

RUN_STATUS_VALUES: tuple[str, ...] = (
    "queued",
    "running",
    "completed",
    "failed",
    "interrupted",
    "unknown",
)

_SNAPSHOT_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\.json$")
_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,255}$")

PUBLIC_EVENT_VISIBILITIES: frozenset[str] = frozenset({"public", "all"})
WEREWOLF_TEAM_EVENT_VISIBILITIES: frozenset[str] = frozenset(
    {"public", "all", "werewolf_team"}
)

_SNAPSHOTS_DIR = "snapshots"
_STATUS_FILE = "status.json"


class ObserverProtocolError(ValueError):
    """Raised when observer protocol input is invalid."""


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def validate_run_id(run_id: str) -> str:
    """Validate and return *run_id*.  Raise ObserverProtocolError on bad input."""
    if not isinstance(run_id, str):
        raise ObserverProtocolError(f"run_id must be a string, got {type(run_id).__name__}")
    if not run_id:
        raise ObserverProtocolError("run_id must not be empty")
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise ObserverProtocolError(f"run_id contains forbidden path characters: {run_id!r}")
    if "?" in run_id or "%" in run_id:
        raise ObserverProtocolError(f"run_id contains URL-encoded characters: {run_id!r}")
    if run_id.startswith("/") or run_id.startswith("\\"):
        raise ObserverProtocolError(f"run_id must not be an absolute path: {run_id!r}")
    if not _RUN_ID_RE.match(run_id):
        raise ObserverProtocolError(f"run_id contains invalid characters: {run_id!r}")
    return run_id


def validate_snapshot_name(snapshot_name: str) -> str:
    """Validate and return *snapshot_name*.  Raise ObserverProtocolError on bad input."""
    if not isinstance(snapshot_name, str):
        raise ObserverProtocolError(
            f"snapshot_name must be a string, got {type(snapshot_name).__name__}"
        )
    if not snapshot_name:
        raise ObserverProtocolError("snapshot_name must not be empty")
    if ".." in snapshot_name or "/" in snapshot_name or "\\" in snapshot_name:
        raise ObserverProtocolError(
            f"snapshot_name contains forbidden path characters: {snapshot_name!r}"
        )
    if not _SNAPSHOT_FILENAME_RE.match(snapshot_name):
        raise ObserverProtocolError(
            f"snapshot_name must be a simple .json filename: {snapshot_name!r}"
        )
    return snapshot_name


def safe_child_path(root: Path, child_name: str) -> Path:
    """Resolve *child_name* under *root* and reject path-traversal attempts."""
    if not isinstance(child_name, str) or not child_name:
        raise ObserverProtocolError("child_name must be a non-empty string")
    if ".." in child_name or "/" in child_name or "\\" in child_name:
        raise ObserverProtocolError(f"child_name contains forbidden path characters: {child_name!r}")
    if not _SAFE_NAME_RE.match(child_name):
        raise ObserverProtocolError(f"child_name contains invalid characters: {child_name!r}")
    child = (root / child_name).resolve()
    if not str(child).startswith(str(root.resolve())):
        raise ObserverProtocolError(
            f"child_path resolved outside root: {child!r} not under {root!r}"
        )
    return child


def artifact_path(run_dir: Path, artifact_name: str) -> Path:
    """Return the resolved path to *artifact_name* inside *run_dir*.

    *artifact_name* must be in ``ALLOWED_ARTIFACTS``.
    """
    if artifact_name not in ALLOWED_ARTIFACTS:
        raise ObserverProtocolError(
            f"Unknown artifact: {artifact_name!r}.  Allowed: {ALLOWED_ARTIFACTS}"
        )
    return safe_child_path(run_dir, artifact_name)


def snapshot_path(run_dir: Path, snapshot_name: str) -> Path:
    """Return the resolved path to a snapshot .json file inside *run_dir*."""
    validate_snapshot_name(snapshot_name)
    return safe_child_path(run_dir / _SNAPSHOTS_DIR, snapshot_name)


# ---------------------------------------------------------------------------
# Registries, summary, and launch helpers
# ---------------------------------------------------------------------------


def list_run_dirs(runs_dir: Path) -> list[Path]:
    """Return sorted directories directly under *runs_dir*."""
    if not runs_dir.exists():
        return []
    items: list[Path] = []
    for child in runs_dir.iterdir():
        if child.is_dir():
            items.append(child)
    items.sort()
    return items


def _read_status_payload(run_dir: Path) -> dict[str, object]:
    """Read the durable status payload, falling back to an empty dict."""
    status_path = run_dir / _STATUS_FILE
    if status_path.exists():
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _read_status(run_dir: Path) -> str:
    """Read the run status from the status file, falling back to 'unknown'."""
    status = _read_status_payload(run_dir).get("status")
    if isinstance(status, str) and status in RUN_STATUS_VALUES:
        return status
    return "unknown"


# Public alias for the durable status reader (used by the server's restart fallback).
read_run_status = _read_status


def write_run_status(
    run_dir: Path, status: str, evaluation_bucket: dict[str, str] | None = None
) -> None:
    """Persist the run status durably so it survives a server restart. The server's
    in-memory run_status dict is lost on bounce, which otherwise makes every prior
    completed run report 'unknown' and become permanently un-settleable (the
    settlement route gates on status=='completed'). Atomic temp+replace; best-effort
    (never raises into the run thread). A previously stamped evaluation_bucket is
    preserved across bucket-less rewrites (spec 2026-06-10-prompt-versioning §4.3)."""
    if status not in RUN_STATUS_VALUES:
        return
    try:
        payload: dict[str, object] = {"status": status}
        if evaluation_bucket is not None:
            payload["evaluation_bucket"] = dict(evaluation_bucket)
        else:
            try:
                prev = json.loads((run_dir / _STATUS_FILE).read_text(encoding="utf-8"))
                if isinstance(prev, dict) and "evaluation_bucket" in prev:
                    payload["evaluation_bucket"] = prev["evaluation_bucket"]
            except (OSError, ValueError):
                pass
        run_dir.mkdir(parents=True, exist_ok=True)
        tmp = run_dir / (_STATUS_FILE + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(run_dir / _STATUS_FILE)
    except OSError:
        pass


def _count_events(run_dir: Path) -> int:
    """Count lines in events.jsonl."""
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return 0
    try:
        text = events_path.read_text(encoding="utf-8")
        return len([line for line in text.splitlines() if line.strip()])
    except OSError:
        return 0


def _list_snapshot_files(run_dir: Path) -> list[Path]:
    """List .json snapshot files under the snapshots directory."""
    snapshots_dir = run_dir / _SNAPSHOTS_DIR
    if not snapshots_dir.exists():
        return []
    items = sorted(snapshots_dir.glob("*.json"))
    return items


def build_artifact_registry(run_dir: Path) -> dict[str, dict[str, object]]:
    """Build a registry of allowed artifacts with existence and size info."""
    registry: dict[str, dict[str, object]] = {}
    for name in ALLOWED_ARTIFACTS:
        path = run_dir / name
        if path.exists() and path.is_file():
            size = path.stat().st_size
            registry[name] = {"name": name, "exists": True, "size_bytes": size}
        else:
            registry[name] = {"name": name, "exists": False, "size_bytes": None}
    return registry


def build_snapshot_registry(
    run_dir: Path, perspective: str = "god"
) -> list[dict[str, object]]:
    """Return a list of snapshot entries visible to *perspective*.

    Snapshots hidden from the perspective are returned with ``hidden`` set to
    ``True`` and detail keys omitted.
    """
    normalize_perspective(perspective)
    entries: list[dict[str, object]] = []
    for snap_path in _list_snapshot_files(run_dir):
        name = snap_path.name
        try:
            data = json.loads(snap_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        entry: dict[str, object] = {"name": name}
        snapshot_type = data.get("snapshot_type", "unknown")
        entry["snapshot_type"] = snapshot_type
        visible = snapshot_visible_to_perspective(data, perspective)
        if visible:
            entry["hidden"] = False
            entry["round"] = data.get("round")
            entry["phase"] = data.get("phase")
            player_id = data.get("player_id")
            if player_id is not None:
                entry["player_id"] = player_id
        else:
            entry["hidden"] = True
        entries.append(entry)
    return entries


def load_snapshot_detail(
    run_dir: Path, snapshot_name: str, perspective: str = "god"
) -> dict[str, object]:
    """Load a snapshot dict and raise if *perspective* is not allowed to view it."""
    validate_snapshot_name(snapshot_name)
    normalize_perspective(perspective)
    path = run_dir / _SNAPSHOTS_DIR / snapshot_name
    if not path.exists():
        raise ObserverProtocolError(f"Snapshot not found: {snapshot_name}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ObserverProtocolError(
            f"Failed to read snapshot {snapshot_name}: {exc}"
        ) from exc
    if not snapshot_visible_to_perspective(data, perspective):
        raise ObserverProtocolError(
            f"Perspective {perspective!r} cannot view snapshot {snapshot_name!r}"
        )
    return data


def build_run_summary(
    run_dir: Path, status: str | None = None
) -> dict[str, object]:
    """Build a run summary dictionary exposing relative paths only."""
    run_id = run_dir.name
    current_status = status if status is not None else _read_status(run_dir)
    status_payload = _read_status_payload(run_dir)
    event_count = _count_events(run_dir)
    snapshot_files = _list_snapshot_files(run_dir)
    snapshot_count = len(snapshot_files)
    snapshot_names = [f.name for f in snapshot_files]
    failure_audit_path = run_dir / "failure-audit.json"
    has_failure_audit = failure_audit_path.exists()
    try:
        filesystem_mtime = run_dir.stat().st_mtime
    except OSError:
        filesystem_mtime = 0.0
    game_log_path = run_dir / "game-log.json"
    report_available = current_status == "completed" and game_log_path.exists()
    report_unavailable_reason = None
    if not report_available:
        report_unavailable_reason = (
            "not_completed" if current_status != "completed" else "no_game_log"
        )
    summary: dict[str, object] = {
        "run_id": run_id,
        "status": current_status,
        "is_active": current_status in ("queued", "running"),
        "report_available": report_available,
        "report_unavailable_reason": report_unavailable_reason,
        "filesystem_mtime": filesystem_mtime,
        "event_count": event_count,
        "snapshot_count": snapshot_count,
        "snapshot_names": snapshot_names,
        "has_failure_audit": has_failure_audit,
    }
    for key in (
        "interrupted_at",
        "interrupted_source",
        "status_reason",
        "reason",
        "evaluation_bucket",
    ):
        if key in status_payload:
            summary[key] = status_payload[key]
    if "status_reason" not in summary and isinstance(summary.get("reason"), str):
        summary["status_reason"] = summary["reason"]
    return summary


def build_run_detail(
    run_dir: Path, status: str | None = None
) -> dict[str, object]:
    """Build a detailed run view (summary + artifact registry)."""
    summary = build_run_summary(run_dir, status=status)
    registry = build_artifact_registry(run_dir)
    return {**summary, "artifacts": registry}


def parse_launch_request(payload: dict[str, object]) -> dict[str, object]:
    """Validate and normalize a launch request payload.

    Allowed keys: ``template``, ``run_id``, ``mode``.
    Unknown templates, unknown modes, unsafe run_ids, and extra keys are rejected.
    """
    if not isinstance(payload, dict):
        raise ObserverProtocolError("Launch request payload must be a JSON object")

    allowed_keys = {"template", "run_id", "mode"}
    extra_keys = set(payload.keys()) - allowed_keys
    if extra_keys:
        raise ObserverProtocolError(
            f"Unexpected keys in launch request: {sorted(extra_keys)}.  Allowed: {sorted(allowed_keys)}"
        )

    template = str(payload.get("template", DEFAULT_FAKE_TEMPLATE))
    if template not in ALLOWED_TEMPLATES:
        raise ObserverProtocolError(
            f"Unknown template: {template!r}.  Allowed: {ALLOWED_TEMPLATES}"
        )

    mode = str(payload.get("mode", DEFAULT_FAKE_MODE))
    if mode not in ALLOWED_MODES:
        raise ObserverProtocolError(
            f"Unknown mode: {mode!r}.  Allowed: {ALLOWED_MODES}"
        )
    if mode == "live":
        # Live execution is profile-only (G3-1); template launches may not go
        # live this slice.  Use parse_profile_launch_request for live runs.
        raise ObserverProtocolError(
            "mode 'live' is not allowed for template launches (live is profile-only)"
        )

    run_id = str(payload.get("run_id", ""))
    if run_id:
        validate_run_id(run_id)
    else:
        run_id = generate_run_id(prefix=template.replace("_", "_"))
        if not run_id.startswith(template):
            run_id = f"{template}_{uuid.uuid4().hex[:8]}"

    return {"template": template, "run_id": run_id, "mode": mode}


def parse_profile_launch_request(payload: dict[str, object]) -> dict[str, object]:
    """Validate and normalize a profile-launch payload.

    Exactly one launch source is required: ``profile`` (inline object) or
    ``profile_name`` (saved profile).  Allowed keys: ``profile``,
    ``profile_name``, ``run_id``, ``mode``.  ``template`` is not allowed here
    (template launches use ``parse_launch_request``).
    """
    if not isinstance(payload, dict):
        raise ObserverProtocolError("Launch request payload must be a JSON object")
    allowed_keys = {"profile", "profile_name", "run_id", "mode"}
    extra = set(payload.keys()) - allowed_keys
    if extra:
        raise ObserverProtocolError(
            f"Unexpected keys in profile launch: {sorted(extra)}.  Allowed: {sorted(allowed_keys)}"
        )
    has_inline = "profile" in payload
    has_named = "profile_name" in payload
    if has_inline and has_named:
        raise ObserverProtocolError("Provide either 'profile' or 'profile_name', not both")
    if not has_inline and not has_named:
        raise ObserverProtocolError("Profile launch requires 'profile' or 'profile_name'")

    mode = str(payload.get("mode", DEFAULT_FAKE_MODE))
    if mode not in ALLOWED_MODES:
        raise ObserverProtocolError(f"Unknown mode: {mode!r}.  Allowed: {ALLOWED_MODES}")

    run_id_raw = payload.get("run_id", "")
    if not isinstance(run_id_raw, str):
        raise ObserverProtocolError("run_id must be a string")
    run_id = run_id_raw
    if run_id:
        validate_run_id(run_id)
    else:
        run_id = generate_run_id(prefix="g2d_profile")
        if not run_id.startswith("g2d_profile"):
            run_id = f"g2d_profile_{uuid.uuid4().hex[:8]}"

    if has_inline:
        profile = payload["profile"]
        if not isinstance(profile, dict):
            raise ObserverProtocolError("'profile' must be a JSON object")
        return {"kind": "inline", "profile": profile, "run_id": run_id, "mode": mode}

    profile_name = payload["profile_name"]
    if not isinstance(profile_name, str) or not _SAFE_NAME_RE.match(profile_name):
        raise ObserverProtocolError(f"Unsafe profile_name: {profile_name!r}")
    return {"kind": "named", "profile_name": profile_name, "run_id": run_id, "mode": mode}


def build_runtime_capabilities(
    *,
    live_enabled: bool,
    providers: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Build the read-only ``g3.runtime_capabilities.v1`` live-posture payload.

    P2-B per-provider: ``providers`` maps each registered provider id
    (``deepseek``/``openai``/``anthropic``/``openai_compatible``) to its OWN
    posture ``{"available": bool, "reason_code"?: str, "message"?: str}``.  Each
    entry is normalized independently — ``reason_code``/``message`` are emitted
    ONLY when that provider is not available, mirroring the launch-time 403 code
    from ``_check_live_capability``.  Provider keys are emitted in sorted order
    for deterministic output.

    ``default_mode`` is hard-coded ``"fake"`` — any provider being *available*
    never changes the default selection.

    This payload carries posture only — ``enabled``/``available`` plus a key-free
    canonical ``reason_code``/``message`` per provider — and NEVER a key, the env
    var name, an ``Authorization`` header, or a base-url secret."""
    providers_payload: dict[str, object] = {}
    for name in sorted(providers):
        info = providers[name]
        available = bool(info.get("available", False))
        entry: dict[str, object] = {"available": available}
        if not available:
            reason_code = info.get("reason_code")
            message = info.get("message")
            if reason_code is not None:
                entry["reason_code"] = reason_code
            if message is not None:
                entry["message"] = message
        providers_payload[name] = entry
    return {
        "schema_version": RUNTIME_CAPABILITIES_SCHEMA_VERSION,
        "default_mode": DEFAULT_FAKE_MODE,
        "live_api": {
            "enabled": bool(live_enabled),
            "providers": providers_payload,
        },
    }


def generate_run_id(prefix: str = "g2a_default_6p_fake") -> str:
    """Generate a unique run_id with a short UUID suffix."""
    validate_run_id(prefix)
    safe_prefix = re.sub(r"[^a-zA-Z0-9_.-]", "_", prefix)
    if not safe_prefix or not _SAFE_NAME_RE.match(safe_prefix):
        raise ObserverProtocolError(f"Invalid prefix for run_id: {prefix!r}")
    candidate = f"{safe_prefix}_{uuid.uuid4().hex[:8]}"
    validate_run_id(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Visibility and SSE helpers
# ---------------------------------------------------------------------------


def normalize_perspective(perspective: str | None) -> str:
    """Return a canonical perspective string.  Reject unknown perspectives."""
    if perspective is None:
        return "god"
    if not isinstance(perspective, str):
        raise ObserverProtocolError(
            f"perspective must be a string or None, got {type(perspective).__name__}"
        )
    canonical = perspective.strip()
    if canonical not in ALLOWED_PERSPECTIVES:
        raise ObserverProtocolError(
            f"Unknown perspective: {canonical!r}.  Allowed: {ALLOWED_PERSPECTIVES}"
        )
    return canonical


def event_visible_to_perspective(
    event: dict[str, object], perspective: str
) -> bool:
    """Return ``True`` when *perspective* is allowed to see *event*."""
    perspective = normalize_perspective(perspective)
    visibility = event.get("visibility", "internal")
    if not isinstance(visibility, str):
        visibility = "internal"

    if perspective == "god":
        return True

    if perspective == "public":
        return visibility in PUBLIC_EVENT_VISIBILITIES

    if perspective == "team:werewolf":
        return visibility in WEREWOLF_TEAM_EVENT_VISIBILITIES

    if perspective.startswith("role:p"):
        return visibility in PUBLIC_EVENT_VISIBILITIES

    return False


def snapshot_visible_to_perspective(
    snapshot: dict[str, object], perspective: str
) -> bool:
    """Return ``True`` when *perspective* is allowed to see *snapshot*."""
    perspective = normalize_perspective(perspective)

    if perspective == "god":
        return True

    snapshot_type = snapshot.get("snapshot_type", "unknown")
    if snapshot_type == "god":
        return False

    if snapshot_type == "role_projection":
        if perspective == "public":
            return False

        if perspective.startswith("role:"):
            role_player = perspective[len("role:"):]
            snap_player = str(snapshot.get("player_id", ""))
            return role_player == snap_player

        if perspective == "team:werewolf":
            snap_team = str(snapshot.get("team", ""))
            return snap_team == "werewolf"

    return False


def filter_events_for_perspective(
    events: list[dict[str, object]], perspective: str
) -> dict[str, object]:
    """Return a dict with ``perspective``, ``events``, and ``hidden_count``."""
    perspective = normalize_perspective(perspective)
    filtered = [e for e in events if event_visible_to_perspective(e, perspective)]
    return {
        "perspective": perspective,
        "events": filtered,
        "hidden_count": len(events) - len(filtered),
    }


def format_sse_event(event: dict[str, object]) -> bytes:
    """Format *event* as an SSE ``runtime_event`` message."""
    data = json.dumps(event, ensure_ascii=False, sort_keys=True)
    return f"event: runtime_event\ndata: {data}\n\n".encode("utf-8")


def format_sse_status(run_id: str, status: str, reason: str | None = None) -> bytes:
    """Format a run-status SSE message.

    When *reason* is provided (a key-free run-status reason such as
    ``budget_exhausted``/``provider_failure``) it is included in the payload."""
    payload: dict[str, str] = {"run_id": run_id, "status": status}
    if reason is not None:
        payload["reason"] = reason
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return f"event: run_status\ndata: {data}\n\n".encode("utf-8")
