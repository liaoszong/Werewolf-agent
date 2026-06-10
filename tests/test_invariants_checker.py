import unittest
from werewolf_eval.invariants.visibility_oracle import entitled, seat_index_from_players

_PLAYERS = [
    {"player_id": "p1", "role": "seer", "team": "villager"},
    {"player_id": "p2", "role": "villager", "team": "villager"},
]
_SEER_EVENT = {"event_id": "e1", "type": "seer_check", "actor": "p1", "target": "p3",
               "visibility": "seer", "round": 1, "phase": "night", "data": {"summary": ""}}
_PUBLIC_EVENT = {"event_id": "e2", "type": "day_announcement", "actor": "system",
                 "target": "none", "visibility": "public", "round": 1, "phase": "day",
                 "data": {"summary": ""}}


class TestVisibilityOracle(unittest.TestCase):
    def setUp(self):
        self.idx = seat_index_from_players(_PLAYERS)

    def test_seer_sees_seer_event(self):
        self.assertTrue(entitled("p1", _SEER_EVENT, self.idx))

    def test_villager_does_not_see_seer_event(self):
        self.assertFalse(entitled("p2", _SEER_EVENT, self.idx))

    def test_everyone_sees_public_event(self):
        self.assertTrue(entitled("p2", _PUBLIC_EVENT, self.idx))

    def test_seat_index_marks_trusted_source(self):
        self.assertEqual(self.idx["p1"]["role_source"], "role_projection_snapshot")


if __name__ == "__main__":
    unittest.main()
