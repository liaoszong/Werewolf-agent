from __future__ import annotations

from typing import Any

from werewolf_eval.observer_visibility import event_visible_in_projection


def seat_index_from_players(players: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    """Build a seat_index from the game-log `players` map. Marks every field's
    source as `role_projection_snapshot` so `_trusted_role_for_player` /
    `_trusted_team_for_player` (observer_visibility.py:521/533) trust it — without
    this the observer returns 'unknown' and every seat reads as all-hidden."""
    return {
        p["player_id"]: {
            "player_id": p["player_id"],
            "role": p.get("role", "unknown"),
            "team": p.get("team", "unknown"),
            "role_source": "role_projection_snapshot",
            "team_source": "role_projection_snapshot",
        }
        for p in players
    }


def entitled(seat: str, event: dict[str, Any], seat_index: dict[str, dict[str, object]]) -> bool:
    """True iff `seat` (a player id) may legitimately see `event`, decided by the
    OBSERVER's visibility implementation (event tag + trusted role) — a different
    code path from the engine's `_build_obs` (the anti-circularity). The observer
    returns a (visible, reason) tuple; unpack it."""
    visible, _reason = event_visible_in_projection(event, f"role:{seat}", seat_index)
    return bool(visible)
