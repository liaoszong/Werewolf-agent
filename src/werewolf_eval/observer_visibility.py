"""G2c server-side visibility projection helpers.

Computes projected player lists, event visibility, snapshot metadata, and
projection envelopes for each observer perspective (god / public / role:pN /
team:werewolf).  Designed to be used by the observer server without pulling in
network I/O or server lifecycle.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# R-06: single source of truth for these visibility sets — import them from
# observer_protocol so the /events,/stream filter and the /projection filter can
# never drift apart (the duplicate frozensets were the contract-drift seam).
from werewolf_eval.observer_protocol import (
    KNOWN_ROLE_TEAMS as _KNOWN_ROLE_TEAMS,
    PUBLIC_EVENT_VISIBILITIES as PUBLIC_LIKE_EVENT_VISIBILITIES,
    WEREWOLF_TEAM_EVENT_VISIBILITIES,
)

# ---------------------------------------------------------------------------
# Constants (Step 1)
# ---------------------------------------------------------------------------

CONTRACT_VERSION = "g2c.visibility.v1"
ROLE_PERSPECTIVE_PREFIX = "role:"
DEFAULT_PLAYER_IDS: tuple[str, ...] = tuple(f"p{i}" for i in range(1, 7))
# PUBLIC_LIKE_EVENT_VISIBILITIES / WEREWOLF_TEAM_EVENT_VISIBILITIES are imported from
# observer_protocol above (single source of truth, R-06).
ROLE_SPECIFIC_EVENT_VISIBILITIES: frozenset[str] = frozenset({"seer", "witch", "guard"})

_SNAPSHOTS_DIR = "snapshots"
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
    """Return ``True`` when *role* is ``"werewolf"``."""
    return role == "werewolf"


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
# Seat / role index builder (Step 2)
# ---------------------------------------------------------------------------


# Phase ordering within a round, so "latest snapshot" means newest *game time*
# (not alphabetical filename). game_end/result come last; setup first.
_PHASE_RANK: dict[str, int] = {
    "setup": 0,
    "night": 1,
    "day": 2,
    "vote": 3,
    "voting": 3,
    "game_end": 4,
    "result": 4,
}


def _snap_order(data: dict[str, object]) -> tuple[int, int]:
    """Sortable (round, phase_rank) key for a snapshot — higher == later."""
    try:
        rnd = int(data.get("round", 0))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        rnd = 0
    phase = str(data.get("phase", ""))
    return (rnd, _PHASE_RANK.get(phase, 1))


def build_seat_role_index(run_dir: Path) -> dict[str, dict[str, object]]:
    """Read all role-projection and god snapshots from *run_dir* and build a
    seat-index whose entries carry source-trust metadata.

    Each entry shape::

        {
            "player_id": "p3",
            "role": "seer",
            "team": "villager",
            "alive": True,
            "role_source": "role_projection_snapshot" | "god_snapshot" | "unknown",
            "team_source": "role_projection_snapshot" | "god_snapshot" | "unknown",
            "alive_source": "role_projection_snapshot" | "god_snapshot" | "unknown",
            "projected_known_roles": {"p1": "unknown", "p3": "seer"},
        }

    Source rules:

    1. Prefer each player's own ``role_projection_snapshot`` for that player's
       ``role``, ``team``, ``alive``, and ``projected_known_roles``.
    2. God snapshot data may fill *missing* fields only for server-side god
       projection and diagnostics.
    3. Non-god projections must not expose ``role`` or ``team`` when the
       corresponding source is only ``god_snapshot``.
    4. ``projected_known_roles`` is trusted only from the requesting role
       player's own ``role_projection_snapshot``.
    5. Missing or malformed snapshots produce an empty or partial index; the
       helper must not raise.
    6. Do not return prompt text, provider secrets, local absolute paths, or
       secret-like fields.
    """
    index: dict[str, dict[str, object]] = {}
    snapshots_dir = run_dir / _SNAPSHOTS_DIR
    if not snapshots_dir.is_dir():
        return index

    # Collect role_projection snapshots keyed by player_id.
    role_snaps: dict[str, dict[str, object]] = {}
    # Collect god snapshots.
    god_snaps: list[dict[str, object]] = []

    for snap_path in sorted(snapshots_dir.glob("*.json")):
        try:
            data = json.loads(snap_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        stype = data.get("snapshot_type", "unknown")
        if stype == "role_projection":
            pid = str(data.get("player_id", ""))
            if pid:
                # Keep each player's LATEST own snapshot (alive state evolves per
                # round); alphabetical glob order would wrongly pick e.g. n1 over d2.
                prev = role_snaps.get(pid)
                if prev is None or _snap_order(data) >= _snap_order(prev):
                    role_snaps[pid] = data
        elif stype == "god":
            god_snaps.append(data)

    # Build entries preferring role_projection over god.
    all_player_ids: set[str] = set(role_snaps.keys())

    # Gather player IDs from god snapshots too.
    for gs in god_snaps:
        for p in gs.get("players", []):
            if isinstance(p, dict):
                pid = str(p.get("player_id", ""))
                if pid:
                    all_player_ids.add(pid)

    # Also include alive_players from god snapshots to catch players.
    for gs in god_snaps:
        for pid in gs.get("alive_players", []):
            all_player_ids.add(str(pid))

    # If we have no player IDs at all, return empty.
    if not all_player_ids:
        return index

    # The LATEST god snapshot carrying an alive_players list is the authority for
    # current alive/dead state. Earlier snapshots (e.g. setup) list everyone alive,
    # so "alive in any snapshot" would never report a death (P2-C-1 dead-state bug).
    latest_god_alive: set[str] | None = None
    _latest_god_order: tuple[int, int] | None = None
    for gs in god_snaps:
        ga = gs.get("alive_players")
        if not isinstance(ga, list):
            continue
        order = _snap_order(gs)
        if _latest_god_order is None or order >= _latest_god_order:
            _latest_god_order = order
            latest_god_alive = {str(x) for x in ga}

    for pid in sorted(all_player_ids):
        entry: dict[str, object] = {"player_id": pid}

        role_snap = role_snaps.get(pid)

        # -- role --
        if role_snap is not None:
            entry["role"] = str(role_snap.get("role", "unknown"))
            entry["role_source"] = "role_projection_snapshot"
        else:
            # Try god snapshot
            role_from_god = _find_player_role_in_god_snaps(god_snaps, pid)
            if role_from_god is not None:
                entry["role"] = role_from_god
                entry["role_source"] = "god_snapshot"
            else:
                entry["role"] = "unknown"
                entry["role_source"] = "unknown"

        # -- team --
        if role_snap is not None:
            entry["team"] = str(role_snap.get("team", "unknown"))
            entry["team_source"] = "role_projection_snapshot"
        else:
            team_from_god = _find_player_team_in_god_snaps(god_snaps, pid)
            if team_from_god is not None:
                entry["team"] = team_from_god
                entry["team_source"] = "god_snapshot"
            else:
                entry["team"] = "unknown"
                entry["team_source"] = "unknown"

        # -- alive --
        # Deaths are PUBLIC (announced each day), so the LATEST god snapshot is the
        # authority. A player's own role snapshot can be stale-alive because it
        # predates their death (a dead player stops producing snapshots).
        alive: bool | None = None
        if latest_god_alive is not None:
            alive = pid in latest_god_alive  # present -> alive; absent -> dead
            entry["alive"] = alive
            entry["alive_source"] = "god_snapshot"
        elif role_snap is not None:
            alive_players = role_snap.get("alive_players", [])
            if isinstance(alive_players, list):
                alive = pid in [str(x) for x in alive_players]
                entry["alive"] = alive
                entry["alive_source"] = "role_projection_snapshot"
        if alive is None:
            # Fallback: unknown alive status.
            entry["alive"] = True
            entry["alive_source"] = "unknown"

        # -- projected_known_roles --
        if role_snap is not None:
            pkr = role_snap.get("projected_known_roles", {})
            if isinstance(pkr, dict):
                entry["projected_known_roles"] = {
                    str(k): str(v) for k, v in pkr.items()
                }
            else:
                entry["projected_known_roles"] = {}
        else:
            entry["projected_known_roles"] = {}

        index[pid] = entry

    return index


def _find_player_role_in_god_snaps(
    god_snaps: list[dict[str, object]], player_id: str
) -> str | None:
    """Find *player_id*'s role across god snapshots."""
    for gs in god_snaps:
        for p in gs.get("players", []):
            if isinstance(p, dict) and str(p.get("player_id", "")) == player_id:
                role = p.get("role")
                if role is not None:
                    return str(role)
    return None


def _find_player_team_in_god_snaps(
    god_snaps: list[dict[str, object]], player_id: str
) -> str | None:
    """Find *player_id*'s team across god snapshots."""
    for gs in god_snaps:
        for p in gs.get("players", []):
            if isinstance(p, dict) and str(p.get("player_id", "")) == player_id:
                team = p.get("team")
                if team is not None:
                    return str(team)
    return None


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
                # Never expose wolf roles from projected_known_roles for non-self
                if known_role == "werewolf" or known_role == "unknown":
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
    ``werewolf_team_event``, ``hidden``.
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
        # seer/witch visibility only if trusted role matches
        if visibility == "seer":
            trusted_role = _trusted_role_for_player(seat_index, role_player)
            if trusted_role == "seer":
                return True, "seer_event"
            return False, "hidden"
        if visibility == "witch":
            trusted_role = _trusted_role_for_player(seat_index, role_player)
            if trusted_role == "witch":
                return True, "witch_event"
            return False, "hidden"
        if visibility == "guard":
            trusted_role = _trusted_role_for_player(seat_index, role_player)
            if trusted_role == "guard":
                return True, "guard_event"
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


# ---------------------------------------------------------------------------
# Projection envelope builder (Step 6)
# ---------------------------------------------------------------------------


def _load_game_log_summaries(run_dir: Path) -> dict[str, dict[str, str]]:
    """Return ``{game_log_event_id: {"summary", "target"}}`` from ``game-log.json``,
    or ``{}`` when absent/malformed.  Never raises.

    Summaries are public/role-visible game narration (NOT prompt/provider secrets);
    the visibility filter in :func:`project_events` decides which events reach the
    client BEFORE this lookup is joined in :func:`build_projection_envelope`, so
    attaching summaries to already-visible events cannot leak hidden facts (P2-C-1 §7).
    """
    path = run_dir / "game-log.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for event in data.get("events", []):
        if not isinstance(event, dict):
            continue
        eid = str(event.get("event_id", ""))
        if not eid:
            continue
        event_data = event.get("data", {})
        summary = str(event_data.get("summary", "")) if isinstance(event_data, dict) else ""
        target = event.get("target", "")
        out[eid] = {"summary": summary, "target": "" if target is None else str(target)}
    return out


def _load_decision_reasons(run_dir: Path) -> dict[str, dict[str, str]]:
    """Return ``{game_log_event_id: {"reason_summary", "actor"}}`` by joining
    ``decision-log.json`` reasons onto ``game-log.json`` events, or ``{}`` when
    absent/malformed.  Never raises.

    UNLIKE summaries, a ``reason_summary`` is PRIVATE strategy: even when the
    underlying event is public (e.g. a vote), the reasoning behind it must only
    reach god or the deciding player.  This loader only builds the join and
    records the deciding ``actor``; :func:`build_projection_envelope` enforces the
    per-actor gate.  Decisions carry no round, so events and decisions are matched
    in chronological order by ``(actor, action==type, target)`` — a greedy
    first-unconsumed pass, so repeated (actor, target) pairs map by sequence.
    """
    try:
        gl = json.loads((run_dir / "game-log.json").read_text(encoding="utf-8"))
        dl = json.loads((run_dir / "decision-log.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(gl, dict) or not isinstance(dl, dict):
        return {}

    decisions = dl.get("decisions", [])
    if not isinstance(decisions, list):
        return {}
    # Pending decisions keyed by (actor, action, target) -> ordered queue of reasons.
    pending: dict[tuple[str, str, str], list[str]] = {}
    for d in decisions:
        if not isinstance(d, dict):
            continue
        reason = d.get("reason_summary")
        if not reason:
            continue
        key = (str(d.get("actor", "")), str(d.get("action", "")),
               "" if d.get("target") is None else str(d.get("target")))
        pending.setdefault(key, []).append(str(reason))

    out: dict[str, dict[str, str]] = {}
    for event in gl.get("events", []):
        if not isinstance(event, dict):
            continue
        eid = str(event.get("event_id", ""))
        actor = str(event.get("actor", ""))
        if not eid or not actor or actor == "system":
            continue
        key = (actor, str(event.get("type", "")),
               "" if event.get("target") is None else str(event.get("target")))
        queue = pending.get(key)
        if queue:
            out[eid] = {"reason_summary": queue.pop(0), "actor": actor}
    return out


def build_projection_envelope(
    *,
    run_dir: Path,
    run_id: str,
    perspective: str,
    events: list[dict[str, object]],
) -> dict[str, object]:
    """Build the top-level projection envelope consumed by observer clients.

    Required output keys:
        contract_version, run_id, perspective, view_kind, players,
        events, hidden_event_count, snapshots, hidden_snapshot_count, proof.
    """
    kind = perspective_kind(perspective)

    # Build seat index and projection
    seat_index = build_seat_role_index(run_dir)
    players = build_player_projection(seat_index, perspective)

    # Project events (visibility filter first), then back-fill summary/target from
    # game-log.json onto ALREADY-VISIBLE events only (P2-C-1 §7, D6) — post-filter, no leak.
    event_projection = project_events(events, perspective, seat_index)
    summaries = _load_game_log_summaries(run_dir)
    reasons = _load_decision_reasons(run_dir)
    # reason_summary is private strategy: god sees all; role:pN sees only pN's own;
    # public/team see none. Gate by the DECIDING actor, never the event's visibility.
    reason_self = perspective[len(ROLE_PERSPECTIVE_PREFIX):] if kind == "role" else None
    enriched_events: list[dict[str, object]] = []
    for ev in event_projection["events"]:
        payload = ev.get("payload")
        gid = str(payload.get("event_id", "")) if isinstance(payload, dict) else ""
        match = summaries.get(gid)
        reason = reasons.get(gid)
        if match is not None or reason is not None:
            ev = dict(ev)
            # Canonical shape (spec §7): data.summary nested + target top-level.
            data = dict(ev.get("data") or {})
            if match is not None:
                data["summary"] = match["summary"]
                if match.get("target"):
                    ev["target"] = match["target"]
            if reason is not None and (kind == "god" or reason_self == reason["actor"]):
                data["reason_summary"] = reason["reason_summary"]
            ev["data"] = data
        enriched_events.append(ev)

    # Project snapshots (metadata only)
    snapshot_projection = project_snapshots(run_dir, perspective)

    # Build proof
    proof = _build_proof(seat_index, perspective, kind)

    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "perspective": perspective,
        "view_kind": kind,
        "players": players,
        "events": enriched_events,
        "hidden_event_count": event_projection["hidden_event_count"],
        "snapshots": snapshot_projection["snapshots"],
        "hidden_snapshot_count": snapshot_projection["hidden_snapshot_count"],
        "proof": proof,
    }


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
