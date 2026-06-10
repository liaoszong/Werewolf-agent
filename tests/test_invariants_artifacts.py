import unittest
from werewolf_eval.invariants.artifacts import RunArtifacts


class _FakeOutcome:
    def __init__(self):
        self.game_log = {
            "game_id": "g1",
            "players": [{"player_id": "p1", "role": "seer", "team": "villager"}],
            "events": [{"event_id": "g1_e001", "type": "seer_check", "actor": "p1",
                        "target": "p2", "round": 1, "phase": "night",
                        "visibility": "seer", "sequence": 1, "data": {"summary": ""}}],
            "result": {"winner": "villager"},
        }
        self.decision_log = {"decisions": [{"actor": "p1", "phase": "night", "action": "seer_check"}]}
        self.provider_turns = [{"request_id": "g1_r01_p1", "phase": "night", "actor": "p1",
                                "observation_source_event_ids": ["g1_e001"]}]


class TestRunArtifacts(unittest.TestCase):
    def test_from_outcome_extracts_all_streams(self):
        arts = RunArtifacts.from_outcome(_FakeOutcome())
        self.assertEqual(arts.game_id, "g1")
        self.assertEqual(len(arts.events), 1)
        self.assertEqual(arts.players[0]["role"], "seer")
        self.assertEqual(arts.provider_turns[0]["request_id"], "g1_r01_p1")
        self.assertEqual(arts.gaps, ())

    def test_missing_events_is_a_gap_not_a_raise(self):
        class Empty:
            game_log = {"game_id": "g2"}
            decision_log = {}
            provider_turns = []
        arts = RunArtifacts.from_outcome(Empty())
        self.assertIn("game_log.events", arts.gaps)


if __name__ == "__main__":
    unittest.main()
