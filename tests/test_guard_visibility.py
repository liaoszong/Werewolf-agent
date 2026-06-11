# tests/test_guard_visibility.py
"""guard_protect (visibility='guard') entitlement: ONLY the guard seat sees it —
observer projection (I4b oracle path) + spec §6 hard gate (leak = blocking bug)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.invariants.visibility_oracle import entitled, seat_index_from_players

PLAYERS = [
    {"player_id": "p1", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p2", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p3", "role": "seer", "team": "villager"},
    {"player_id": "p4", "role": "witch", "team": "villager"},
    {"player_id": "p5", "role": "guard", "team": "villager"},
    {"player_id": "p6", "role": "villager", "team": "villager"},
]

GUARD_EVENT = {"event_id": "e9", "sequence": 9, "round": 1, "phase": "night",
               "type": "guard_protect", "actor": "p5", "target": "p6",
               "visibility": "guard", "data": {"summary": "Guard p5 protects p6."}}


class GuardEventEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.idx = seat_index_from_players(PLAYERS)

    def test_guard_seat_entitled(self):
        self.assertTrue(entitled("p5", GUARD_EVENT, self.idx))

    def test_every_other_seat_hidden(self):
        for seat in ("p1", "p2", "p3", "p4", "p6"):
            self.assertFalse(entitled(seat, GUARD_EVENT, self.idx), seat)


if __name__ == "__main__":
    unittest.main()
