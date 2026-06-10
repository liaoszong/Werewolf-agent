import unittest
from werewolf_eval.invariants import check_run, RunArtifacts


def _ev(seq, etype, actor, target, vis, phase="night"):
    return {"event_id": f"g_e{seq:03d}", "sequence": seq, "round": 1, "phase": phase,
            "type": etype, "actor": actor, "target": target, "visibility": vis,
            "data": {"summary": ""}}


_PLAYERS = [{"player_id": "p1", "role": "seer", "team": "villager"},
            {"player_id": "p2", "role": "witch", "team": "villager"},
            {"player_id": "p3", "role": "hunter", "team": "villager"},
            {"player_id": "p4", "role": "werewolf", "team": "werewolf"}]


def _arts(events, turns=None):
    return RunArtifacts("g", _PLAYERS, events, [], turns or [], None)


class TestBadExamples(unittest.TestCase):
    def test_i1_double_player_died(self):
        evs = [_ev(1, "werewolf_kill", "p4", "p1", "werewolf_team"),
               _ev(2, "player_died", "system", "p1", "all"),
               _ev(3, "player_died", "system", "p1", "all")]
        self.assertIn("I1", {v.id for v in check_run(_arts(evs))})

    def test_i3_second_poison(self):
        evs = [_ev(1, "witch_poison", "p2", "p4", "witch"),
               _ev(2, "witch_poison", "p2", "p3", "witch")]
        self.assertIn("I3", {v.id for v in check_run(_arts(evs))})

    def test_i4b_non_entitled_prompt(self):
        evs = [_ev(1, "seer_check", "p1", "p4", "seer")]
        turns = [{"request_id": "g_r01_p3", "phase": "night", "actor": "p3",
                  "observation_source_event_ids": ["g_e001"]}]
        self.assertIn("I4b", {v.id for v in check_run(_arts(evs, turns))})

    def test_i5_double_settle(self):
        turns = [{"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
                  "observation_source_event_ids": []},
                 {"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
                  "observation_source_event_ids": []}]
        self.assertIn("I5", {v.id for v in check_run(_arts([], turns))})

    def test_i6_uncaused_death(self):
        evs = [_ev(1, "player_died", "system", "p4", "all")]
        self.assertIn("I6", {v.id for v in check_run(_arts(evs))})


if __name__ == "__main__":
    unittest.main()
