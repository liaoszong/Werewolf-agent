"""A45-3: lock the observer's role-private visibility frozenset in sync with the
canonical event->visibility map AND with the engine's generalized private-ref logic.

The engine (role_visibility.private_refs_for_role) generalizes private visibility to
ANY role (``v == role``); the observer (observer_projection.ROLE_SPECIFIC_EVENT_VISIBILITIES)
enumerates a frozenset. Nothing binds the two, so adding a new private-vision role could
pass the engine side but silently under-share on the observer side. This sentinel ties
the observer frozenset to the canonical EVENT_TYPE_REQUIRED_VISIBILITY map (the R-17
drift gate, enforced against real games in test_event_visibility_invariant) and asserts
both engine and observer honor every role-private visibility for exactly its owner.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.observer_projection import (
    ROLE_SPECIFIC_EVENT_VISIBILITIES,
    PUBLIC_LIKE_EVENT_VISIBILITIES,
)
from werewolf_eval.role_visibility import private_refs_for_role
from werewolf_eval.invariants.visibility_oracle import entitled, seat_index_from_players
from test_event_visibility_invariant import EVENT_TYPE_REQUIRED_VISIBILITY

# Role-private visibilities derived from the canonical map: drop public-like and the
# werewolf-team channel (handled separately). The remainder are single-role private.
EXPECTED_ROLE_PRIVATE = {
    v for v in EVENT_TYPE_REQUIRED_VISIBILITY.values()
    if v not in PUBLIC_LIKE_EVENT_VISIBILITIES and v != "werewolf_team"
}

PLAYERS = [
    {"player_id": "p1", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p2", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p3", "role": "seer", "team": "villager"},
    {"player_id": "p4", "role": "witch", "team": "villager"},
    {"player_id": "p5", "role": "guard", "team": "villager"},
    {"player_id": "p6", "role": "villager", "team": "villager"},
]
ROLE_TO_SEAT = {p["role"]: p["player_id"] for p in PLAYERS}


class TwoSideVisibilitySentinel(unittest.TestCase):
    def test_observer_frozenset_matches_canonical_map(self):
        self.assertEqual(
            ROLE_SPECIFIC_EVENT_VISIBILITIES, EXPECTED_ROLE_PRIVATE,
            "observer ROLE_SPECIFIC_EVENT_VISIBILITIES drifted from the canonical "
            "EVENT_TYPE_REQUIRED_VISIBILITY map — add the new role-private visibility "
            "to BOTH the observer frozenset and the map, or fix the map",
        )

    def test_every_role_private_visibility_has_an_owner_seat(self):
        # The board must seat each owning role so the per-owner assertions below are
        # not vacuous.
        for vis in EXPECTED_ROLE_PRIVATE:
            self.assertIn(vis, ROLE_TO_SEAT, f"no seat for role-private visibility {vis!r}")

    def test_observer_and_engine_agree_per_role_private_visibility(self):
        idx = seat_index_from_players(PLAYERS)
        for vis in sorted(EXPECTED_ROLE_PRIVATE):
            owner_seat = ROLE_TO_SEAT[vis]
            event = {"event_id": f"e_{vis}", "sequence": 1, "round": 1, "phase": "night",
                     "type": f"{vis}_check", "actor": owner_seat, "target": "p6",
                     "visibility": vis, "data": {"summary": f"{vis} private event"}}
            # Observer (I4b oracle): only the owning role's seat is entitled.
            for p in PLAYERS:
                pid = p["player_id"]
                self.assertEqual(
                    entitled(pid, event, idx), pid == owner_seat,
                    f"observer entitlement wrong: seat={pid} vis={vis}",
                )
            # Engine: private_refs_for_role includes the event for the owning role only.
            ev = {"event_id": event["event_id"], "visibility": vis}
            self.assertIn(event["event_id"], private_refs_for_role([ev], vis),
                          f"engine owner role={vis} missing its own private ref")
            for p in PLAYERS:
                role = p["role"]
                if role != vis:
                    self.assertNotIn(
                        event["event_id"], private_refs_for_role([ev], role, p["team"]),
                        f"engine leak: role={role} saw vis={vis}",
                    )


if __name__ == "__main__":
    unittest.main()
