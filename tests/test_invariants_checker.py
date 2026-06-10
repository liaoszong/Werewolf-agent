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


from werewolf_eval.invariants.checker import check_i1, InvariantViolation
from werewolf_eval.invariants.artifacts import RunArtifacts


def _arts(events, players=None, turns=None):
    return RunArtifacts(game_id="g", players=players or [], events=events,
                        decisions=[], provider_turns=turns or [], result=None)


def _death(eid, target, etype="player_died", seq=1, rnd=1, phase="night"):
    return {"event_id": eid, "type": etype, "actor": "system", "target": target,
            "round": rnd, "phase": phase, "visibility": "all", "sequence": seq,
            "data": {"summary": ""}}


class TestI1(unittest.TestCase):
    def test_single_death_passes(self):
        self.assertEqual(check_i1(_arts([_death("e1", "p3")])), [])

    def test_double_commit_fails(self):
        v = check_i1(_arts([_death("e1", "p3", seq=1), _death("e2", "p3", seq=2)]))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I1")
        self.assertEqual(set(v[0].event_ids), {"e1", "e2"})

    def test_night_death_then_day_vote_same_player_fails(self):
        evs = [_death("e1", "p3", "player_died", seq=1),
               _death("e2", "p3", "player_eliminated", seq=2, phase="day")]
        self.assertEqual(len(check_i1(_arts(evs))), 1)


from werewolf_eval.invariants.checker import check_i2


def _action(eid, actor, etype, seq, rnd=1, phase="night"):
    return {"event_id": eid, "type": etype, "actor": actor, "target": "p9",
            "round": rnd, "phase": phase, "visibility": "all", "sequence": seq,
            "data": {"summary": ""}}


class TestI2(unittest.TestCase):
    def test_live_actor_passes(self):
        self.assertEqual(check_i2(_arts([_action("e1", "p1", "seer_check", 1)])), [])

    def test_action_after_death_fails(self):
        evs = [_death("e1", "p1", seq=1), _action("e2", "p1", "seer_check", 2)]
        v = check_i2(_arts(evs))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I2")

    def test_hunter_shot_after_death_is_exempt(self):
        evs = [_death("e1", "p1", seq=1), _action("e2", "p1", "hunter_shoot", 2)]
        self.assertEqual(check_i2(_arts(evs)), [])

    def test_vote_after_death_fails(self):
        evs = [_death("e1", "p1", seq=1), _action("e2", "p1", "player_vote", 2, phase="day")]
        v = check_i2(_arts(evs))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I2")


from werewolf_eval.invariants.checker import check_i3


def _consume(eid, actor, etype, seq):
    return {"event_id": eid, "type": etype, "actor": actor, "target": "p9",
            "round": 1, "phase": "night", "visibility": "witch", "sequence": seq,
            "data": {"summary": ""}}


class TestI3(unittest.TestCase):
    def test_one_each_passes(self):
        evs = [_consume("e1", "pw", "witch_save", 1), _consume("e2", "pw", "witch_poison", 2)]
        self.assertEqual(check_i3(_arts(evs)), [])

    def test_second_antidote_fails(self):
        evs = [_consume("e1", "pw", "witch_save", 1), _consume("e2", "pw", "witch_save", 2)]
        v = check_i3(_arts(evs))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I3")

    def test_two_hunters_one_shot_each_passes(self):
        evs = [_consume("e1", "ph1", "hunter_shoot", 1), _consume("e2", "ph2", "hunter_shoot", 2)]
        self.assertEqual(check_i3(_arts(evs)), [])


from werewolf_eval.invariants.checker import check_prompt_subset


class TestI4a(unittest.TestCase):
    def test_subset_passes(self):
        self.assertEqual(check_prompt_subset("g", "p1", ["e1", "e2"], {"e1", "e2", "e3"}), [])

    def test_prompt_outside_observation_fails(self):
        v = check_prompt_subset("g", "p1", ["e1", "e9"], {"e1", "e2"})
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I4a")
        self.assertEqual(v[0].event_ids, ("e9",))


from werewolf_eval.invariants.checker import check_i4b

_I4B_PLAYERS = [
    {"player_id": "p1", "role": "seer", "team": "villager"},
    {"player_id": "p2", "role": "villager", "team": "villager"},
]
_SEER_EV = {"event_id": "e1", "type": "seer_check", "actor": "p1", "target": "p3",
            "visibility": "seer", "round": 1, "phase": "night", "sequence": 1,
            "data": {"summary": ""}}


class TestI4b(unittest.TestCase):
    def test_seer_sourcing_own_check_passes(self):
        turns = [{"actor": "p1", "request_id": "g_r01_p1", "phase": "night",
                  "observation_source_event_ids": ["e1"]}]
        self.assertEqual(check_i4b(_arts([_SEER_EV], players=_I4B_PLAYERS, turns=turns)), [])

    def test_villager_sourcing_seer_event_fails(self):
        turns = [{"actor": "p2", "request_id": "g_r01_p2", "phase": "day",
                  "observation_source_event_ids": ["e1"]}]
        v = check_i4b(_arts([_SEER_EV], players=_I4B_PLAYERS, turns=turns))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I4b")
        self.assertEqual(v[0].event_ids, ("e1",))


from werewolf_eval.invariants.checker import check_i5


class TestI5(unittest.TestCase):
    def test_same_request_id_different_phase_passes(self):
        turns = [{"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": []},
                 {"request_id": "g_r01_p1", "phase": "day", "actor": "p1",
                  "observation_source_event_ids": []}]
        self.assertEqual(check_i5(_arts([], turns=turns)), [])

    def test_same_request_id_same_phase_twice_fails(self):
        turns = [{"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": []},
                 {"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": []}]
        v = check_i5(_arts([], turns=turns))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I5")


if __name__ == "__main__":
    unittest.main()
