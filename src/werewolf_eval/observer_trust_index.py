"""Observer-side trust-source resolution (B-4 layering, ADR 2026-06-11).

The ONLY module that ASSIGNS provenance: which artifact (a player's own
role_projection snapshot vs a god snapshot vs nothing) backs each seat's
role / team / alive / projected_known_roles. Enforcement of these tags lives in
observer_projection; this module imports no sibling visibility module.

Part of the SYS-A4 observer-side witness: must stay independent of the
engine-side single source (B-2 ADR); enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

import json
from pathlib import Path

_SNAPSHOTS_DIR = "snapshots"


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
