"""Observer-side perspective projection (B-4 layering, ADR 2026-06-11).

The ONLY module that CONSUMES provenance tags (``role_source`` / ``team_source``
/ ``alive_source`` assigned by observer_trust_index): perspective vocabulary,
player/event/snapshot projection, and the proof section. Auditing "what may a
non-god perspective expose" means reading observer_trust_index + this file.

Part of the SYS-A4 observer-side witness: must stay independent of the
engine-side single source (B-2 ADR); enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

import json
from pathlib import Path

# R-06: single source of truth for these visibility sets — import them from
# observer_protocol so the /events,/stream filter and the /projection filter can
# never drift apart (the duplicate frozensets were the contract-drift seam).
from werewolf_eval.observer_protocol import (
    KNOWN_ROLE_TEAMS as _KNOWN_ROLE_TEAMS,
    PUBLIC_EVENT_VISIBILITIES as PUBLIC_LIKE_EVENT_VISIBILITIES,
    WEREWOLF_TEAM_EVENT_VISIBILITIES,
)
from werewolf_eval.observer_trust_index import _SNAPSHOTS_DIR

# ---------------------------------------------------------------------------
# Constants (Step 1)
# ---------------------------------------------------------------------------

CONTRACT_VERSION = "g2c.visibility.v1"
ROLE_PERSPECTIVE_PREFIX = "role:"
DEFAULT_PLAYER_IDS: tuple[str, ...] = tuple(f"p{i}" for i in range(1, 7))
# PUBLIC_LIKE_EVENT_VISIBILITIES / WEREWOLF_TEAM_EVENT_VISIBILITIES are imported from
# observer_protocol above (single source of truth, R-06).
ROLE_SPECIFIC_EVENT_VISIBILITIES: frozenset[str] = frozenset({"seer", "witch", "guard"})

# _KNOWN_ROLE_TEAMS is imported from observer_protocol above (derived from the
# ruleset, ADR 2026-06-11) — the former literal copy here was drift-prone.


class VisibilityProjectionError(ValueError):
    """Raised when a visibility projection cannot be built safely."""


# ---------------------------------------------------------------------------
# Perspective helpers (Step 1)
# ---------------------------------------------------------------------------


def perspective_kind(perspective: str) -> str:
    """Return the kind of *perspective*: ``"god"``, ``"public"``, ``"role"``,
    ``"team"``, or raise ``VisibilityProjectionError`` for unknown values."""
    if not isinstance(perspective, str) or not perspective.strip():
        raise VisibilityProjectionError(f"perspective must be a non-empty string, got {perspective!r}")
    canonical = perspective.strip()
    if canonical == "god":
        return "god"
    if canonical == "public":
        return "public"
    if canonical.startswith(ROLE_PERSPECTIVE_PREFIX):
        return "role"
    if canonical == "team:werewolf":
        return "team"
    raise VisibilityProjectionError(
        f"Unknown perspective: {canonical!r}"
    )


def is_werewolf_role(role: str) -> bool:
    """Return ``True`` when *role* belongs to the werewolf team."""
    return _KNOWN_ROLE_TEAMS.get(role) == "werewolf"


def infer_player_ids(seat_index: dict[str, dict[str, object]]) -> list[str]:
    """Return sorted player IDs from *seat_index*, falling back to ``p1``-``p6``."""
    if seat_index:
        return sorted(seat_index.keys())
    return list(DEFAULT_PLAYER_IDS)


def unknown_player(
    player_id: str, alive: bool | None = None
) -> dict[str, object]:
    """Build an ``unknown`` player projection entry."""
    entry: dict[str, object] = {
        "player_id": player_id,
        "display_role": "unknown",
        "display_team": "unknown",
        "visibility": "hidden",
    }
    if alive is not None:
        entry["alive"] = alive
    return entry


# ---------------------------------------------------------------------------
# Player projection builder (Step 3)
# ---------------------------------------------------------------------------


def build_player_projection(
    seat_index: dict[str, dict[str, object]],
    perspective: str,
) -> list[dict[str, object]]:
    """Build a list of player projection entries visible to *perspective*.

    Rules:

    - ``god`` exposes complete known role/team labels, including fields sourced
      from god snapshot.
    - ``public`` sets hidden roles and teams to ``"unknown"``.
    - ``role:pN`` exposes pN's own role/team only if pN's entry has
      ``role_source == "role_projection_snapshot"``.
    - ``role:pN`` may expose non-wolf known roles only if pN's own
      ``projected_known_roles`` says so.
    - ``team:werewolf`` exposes only entries whose role/team are backed by
      ``role_projection_snapshot`` and prove werewolf team membership.
    """
    kind = perspective_kind(perspective)
    player_ids = infer_player_ids(seat_index)
    result: list[dict[str, object]] = []

    if kind == "god":
        for pid in player_ids:
            entry = seat_index.get(pid, {"player_id": pid})
            role = entry.get("role", "unknown")
            team = entry.get("team", "unknown")
            alive = entry.get("alive")
            result.append({
                "player_id": pid,
                "display_role": str(role),
                "display_team": str(team),
                "alive": bool(alive) if alive is not None else None,
                "visibility": "full",
                "source": str(entry.get("role_source", "unknown")),
            })

    elif kind == "public":
        for pid in player_ids:
            entry = seat_index.get(pid, {"player_id": pid})
            alive = entry.get("alive")
            result.append({
                "player_id": pid,
                "display_role": "unknown",
                "display_team": "unknown",
                "alive": bool(alive) if alive is not None else None,
                "visibility": "public",
                "source": str(entry.get("alive_source", "unknown")),
            })

    elif kind == "role":
        role_player = perspective[len(ROLE_PERSPECTIVE_PREFIX):]
        self_entry = seat_index.get(role_player, {"player_id": role_player})
        self_trusted = (
            str(self_entry.get("role_source", "unknown"))
            == "role_projection_snapshot"
        )
        self_team_trusted = (
            str(self_entry.get("team_source", "unknown"))
            == "role_projection_snapshot"
        )
        projected_known_roles: dict[str, str] = {}
        if isinstance(self_entry.get("projected_known_roles"), dict):
            projected_known_roles = {
                str(k): str(v)
                for k, v in self_entry["projected_known_roles"].items()  # type: ignore[union-attr]
            }

        for pid in player_ids:
            entry = seat_index.get(pid, {"player_id": pid})
            alive = entry.get("alive")

            if pid == role_player:
                display_role = str(entry.get("role", "unknown")) if self_trusted else "unknown"
                display_team = str(entry.get("team", "unknown")) if self_team_trusted else "unknown"
                result.append({
                    "player_id": pid,
                    "display_role": display_role,
                    "display_team": display_team,
                    "alive": bool(alive) if alive is not None else None,
                    "visibility": "self",
                    "source": str(entry.get("role_source", "unknown")),
                })
            else:
                # Other players: only expose if in projected_known_roles and non-wolf
                known_role = projected_known_roles.get(pid, "unknown")
                # Never expose wolf-team roles from projected_known_roles for non-self.
                if known_role == "unknown" or is_werewolf_role(known_role):
                    display_role = "unknown"
                    display_team = "unknown"
                else:
                    display_role = known_role
                    display_team = _KNOWN_ROLE_TEAMS.get(known_role, "villager")

                result.append({
                    "player_id": pid,
                    "display_role": display_role,
                    "display_team": display_team,
                    "alive": bool(alive) if alive is not None else None,
                    "visibility": "hidden",
                    "source": "projected_known_roles",
                })

    elif kind == "team":
        # team:werewolf
        for pid in player_ids:
            entry = seat_index.get(pid, {"player_id": pid})
            role_source = str(entry.get("role_source", "unknown"))
            team_source = str(entry.get("team_source", "unknown"))
            role = str(entry.get("role", "unknown"))
            team = str(entry.get("team", "unknown"))
            alive = entry.get("alive")
            trusted = (
                role_source == "role_projection_snapshot"
                and team_source == "role_projection_snapshot"
            )
            is_wolf = (team == "werewolf")

            if trusted and is_wolf:
                result.append({
                    "player_id": pid,
                    "display_role": role,
                    "display_team": team,
                    "alive": bool(alive) if alive is not None else None,
                    "visibility": "team",
                    "source": "role_projection_snapshot",
                })
            else:
                result.append({
                    "player_id": pid,
                    "display_role": "unknown",
                    "display_team": "unknown",
                    "alive": bool(alive) if alive is not None else None,
                    "visibility": "hidden",
                    "source": "role_projection_snapshot" if trusted else str(role_source),
                })

    return result


# ---------------------------------------------------------------------------
# Event projection helper (Step 4)
# ---------------------------------------------------------------------------


def event_visible_in_projection(
    event: dict[str, object],
    perspective: str,
    seat_index: dict[str, dict[str, object]],
) -> tuple[bool, str]:
    """Return ``(visible, reason)`` for *event* under *perspective*.

    Reasons: ``god_view``, ``public_event``, ``seer_event``, ``witch_event``,
    ``guard_event``, ``werewolf_team_event``, ``hidden``.
    """
    kind = perspective_kind(perspective)
    visibility = event.get("visibility", "internal")
    if not isinstance(visibility, str):
        visibility = "internal"

    if kind == "god":
        return True, "god_view"

    if kind == "public":
        return visibility in PUBLIC_LIKE_EVENT_VISIBILITIES, "public_event"

    if kind == "role":
        # role:pN
        role_player = perspective[len(ROLE_PERSPECTIVE_PREFIX):]
        # Always visible: public/all
        if visibility in PUBLIC_LIKE_EVENT_VISIBILITIES:
            return True, "public_event"
        if visibility in ROLE_SPECIFIC_EVENT_VISIBILITIES:
            trusted_role = _trusted_role_for_player(seat_index, role_player)
            if trusted_role == visibility:
                return True, f"{visibility}_event"
            return False, "hidden"
        # werewolf_team only if trusted team is werewolf
        if visibility == "werewolf_team":
            trusted_team = _trusted_team_for_player(seat_index, role_player)
            if trusted_team == "werewolf":
                return True, "werewolf_team_event"
            return False, "hidden"
        return False, "hidden"

    if kind == "team":
        # team:werewolf
        if visibility in WEREWOLF_TEAM_EVENT_VISIBILITIES:
            return True, "werewolf_team_event"
        return False, "hidden"

    return False, "hidden"


def _trusted_role_for_player(
    seat_index: dict[str, dict[str, object]], player_id: str
) -> str:
    """Return the trusted role for *player_id* from role_projection_snapshot only."""
    entry = seat_index.get(player_id)
    if entry is None:
        return "unknown"
    if str(entry.get("role_source", "unknown")) == "role_projection_snapshot":
        return str(entry.get("role", "unknown"))
    return "unknown"


def _trusted_team_for_player(
    seat_index: dict[str, dict[str, object]], player_id: str
) -> str:
    """Return the trusted team for *player_id* from role_projection_snapshot only."""
    entry = seat_index.get(player_id)
    if entry is None:
        return "unknown"
    if str(entry.get("team_source", "unknown")) == "role_projection_snapshot":
        return str(entry.get("team", "unknown"))
    return "unknown"


def project_events(
    events: list[dict[str, object]],
    perspective: str,
    seat_index: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Filter *events* by *perspective* and return projection metadata.

    Return shape::

        {
            "events": [...],
            "hidden_event_count": 8,
            "event_visibility_reasons": {"public_event": 4, "hidden": 8},
        }
    """
    visible: list[dict[str, object]] = []
    hidden_count = 0
    reason_counts: dict[str, int] = {}

    for event in events:
        is_visible, reason = event_visible_in_projection(event, perspective, seat_index)
        if is_visible:
            copy = dict(event)
            copy["_visibility_reason"] = reason
            visible.append(copy)
        else:
            hidden_count += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return {
        "events": visible,
        "hidden_event_count": hidden_count,
        "event_visibility_reasons": reason_counts,
    }


# ---------------------------------------------------------------------------
# Snapshot projection helper (Step 5)
# ---------------------------------------------------------------------------


def project_snapshots(
    run_dir: Path, perspective: str
) -> dict[str, object]:
    """Return snapshot *metadata* visible to *perspective*.

    Each metadata item shape::

        {
            "snapshot_name": "role-p3-round1.json",
            "snapshot_type": "role_projection" | "god" | "public" | "unknown",
            "perspective": "role:p3",
            "visible": True,
            "hidden": False,
            "round": 1,
            "phase": "night",
            "detail_endpoint": "/api/runs/{run_id}/snapshots/{name}?perspective=role:p3",
            "hidden_reason": "none" | "not_visible_to_perspective" | "malformed_snapshot",
        }
    """
    snapshots_dir = run_dir / _SNAPSHOTS_DIR
    run_id = run_dir.name
    kind = perspective_kind(perspective)

    items: list[dict[str, object]] = []
    hidden_snapshot_count = 0

    if not snapshots_dir.is_dir():
        return {
            "snapshots": items,
            "hidden_snapshot_count": hidden_snapshot_count,
        }

    for snap_path in sorted(snapshots_dir.glob("*.json")):
        name = snap_path.name
        try:
            data = json.loads(snap_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            items.append({
                "snapshot_name": name,
                "snapshot_type": "unknown",
                "perspective": perspective,
                "visible": False,
                "hidden": True,
                "round": None,
                "phase": None,
                "detail_endpoint": _build_detail_endpoint(run_id, name, perspective),
                "hidden_reason": "malformed_snapshot",
            })
            hidden_snapshot_count += 1
            continue

        if not isinstance(data, dict):
            items.append({
                "snapshot_name": name,
                "snapshot_type": "unknown",
                "perspective": perspective,
                "visible": False,
                "hidden": True,
                "round": None,
                "phase": None,
                "detail_endpoint": _build_detail_endpoint(run_id, name, perspective),
                "hidden_reason": "malformed_snapshot",
            })
            hidden_snapshot_count += 1
            continue

        stype = data.get("snapshot_type", "unknown")

        # Determine visibility using snapshot_visible_to_projection logic
        visible, hidden_reason = _snapshot_visible_to_projection(
            data, kind, perspective
        )

        item: dict[str, object] = {
            "snapshot_name": name,
            "snapshot_type": str(stype),
            "perspective": perspective,
            "visible": visible,
            "hidden": not visible,
            "round": data.get("round"),
            "phase": data.get("phase"),
            "detail_endpoint": _build_detail_endpoint(run_id, name, perspective),
            "hidden_reason": hidden_reason,
        }

        # Safe optional fields
        if visible:
            player_id = data.get("player_id")
            if player_id is not None:
                item["player_id"] = player_id

            team = data.get("team")
            if team is not None:
                item["team"] = team

        ts = data.get("ts") or data.get("timestamp")
        if ts is not None:
            item["timestamp"] = ts

        if not visible:
            hidden_snapshot_count += 1

        items.append(item)

    return {
        "snapshots": items,
        "hidden_snapshot_count": hidden_snapshot_count,
    }


def _snapshot_visible_to_projection(
    data: dict[str, object],
    kind: str,
    perspective: str,
) -> tuple[bool, str]:
    """Determine whether a snapshot is visible to the given projection kind."""
    stype = data.get("snapshot_type", "unknown")

    if kind == "god":
        return True, "none"

    if stype == "god":
        return False, "not_visible_to_perspective"

    if stype == "role_projection":
        if kind == "public":
            return False, "not_visible_to_perspective"

        if kind == "role":
            role_player = perspective[len(ROLE_PERSPECTIVE_PREFIX):]
            snap_player = str(data.get("player_id", ""))
            return role_player == snap_player, (
                "none" if role_player == snap_player else "not_visible_to_perspective"
            )

        if kind == "team":
            snap_team = str(data.get("team", ""))
            return snap_team == "werewolf", (
                "none" if snap_team == "werewolf" else "not_visible_to_perspective"
            )

    return False, "not_visible_to_perspective"


def _build_detail_endpoint(
    run_id: str, snapshot_name: str, perspective: str
) -> str:
    """Build a relative detail endpoint URL."""
    return f"/api/runs/{run_id}/snapshots/{snapshot_name}?perspective={perspective}"


def _build_proof(
    seat_index: dict[str, dict[str, object]],
    perspective: str,
    kind: str,
) -> dict[str, object]:
    """Build the ``proof`` section of a projection envelope."""
    # Check if any entry has role_projection_snapshot source
    has_trusted = any(
        str(e.get("role_source", "unknown")) == "role_projection_snapshot"
        for e in seat_index.values()
    )

    base_rules: list[str] = [
        "visibility computed from role_projection and god snapshots",
        "non-god perspectives only trust role_projection_snapshot sources",
        "team:werewolf exposes only trusted werewolf-team members",
    ]

    if has_trusted:
        proof: dict[str, object] = {
            "source": "snapshots",
            "rules": base_rules,
        }
    else:
        proof = {
            "source": "insufficient_artifacts",
            "rules": base_rules,
        }

    # role:pN proof extras
    if kind == "role":
        role_player = perspective[len(ROLE_PERSPECTIVE_PREFIX):]
        entry = seat_index.get(role_player)
        if entry is not None:
            if str(entry.get("role_source", "unknown")) == "role_projection_snapshot":
                proof["self_player_id"] = role_player
                proof["self_role"] = str(entry.get("role", "unknown"))
                proof["self_team"] = str(entry.get("team", "unknown"))

    # team:werewolf proof extras
    if kind == "team":
        proof["team"] = "werewolf"

    return proof
