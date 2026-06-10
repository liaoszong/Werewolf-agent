import unittest
from werewolf_eval.invariants.guards import assert_prompt_entitled, PromptLeakError
from werewolf_eval.invariants.visibility_oracle import seat_index_from_players

_PLAYERS = [{"player_id": "p1", "role": "seer", "team": "villager"},
            {"player_id": "p2", "role": "villager", "team": "villager"}]
_SEER_EV = {"event_id": "e1", "type": "seer_check", "actor": "p1", "target": "p3",
            "visibility": "seer", "round": 1, "phase": "night", "data": {"summary": ""}}


class TestB1(unittest.TestCase):
    def setUp(self):
        self.idx = seat_index_from_players(_PLAYERS)
        self.by_id = {"e1": _SEER_EV}

    def test_entitled_prompt_does_not_raise(self):
        assert_prompt_entitled("p1", ["e1"], self.by_id, self.idx)  # seer sees seer event

    def test_non_entitled_prompt_raises(self):
        with self.assertRaises(PromptLeakError):
            assert_prompt_entitled("p2", ["e1"], self.by_id, self.idx)  # villager must not

    def test_unknown_event_id_is_skipped(self):
        assert_prompt_entitled("p2", ["missing"], self.by_id, self.idx)  # no raise


from werewolf_eval.invariants.guards import assert_death_commit_once, DoubleDeathCommitError


class TestB4(unittest.TestCase):
    def test_first_commit_ok(self):
        committed: set[str] = set()
        assert_death_commit_once("p3", committed)
        self.assertIn("p3", committed)

    def test_second_commit_raises(self):
        committed = {"p3"}
        with self.assertRaises(DoubleDeathCommitError):
            assert_death_commit_once("p3", committed)


if __name__ == "__main__":
    unittest.main()
