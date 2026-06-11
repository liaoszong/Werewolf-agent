# tests/test_invariants_i8.py
"""I8a/I8b/I8c guard invariants + I2 coverage of guard_protect (L4 arm Task 8)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.invariants.artifacts import RunArtifacts
from werewolf_eval.invariants.checker import check_i2, check_i8, check_i8c


def _ev(eid, seq, rnd, phase, etype, actor, target, summary=""):
    return {"event_id": eid, "sequence": seq, "round": rnd, "phase": phase,
            "type": etype, "actor": actor, "target": target,
            "visibility": "internal", "data": {"summary": summary}}


def _arts(events):
    return RunArtifacts(game_id="i8_fixture", players=[], events=events,
                        decisions=[], provider_turns=[], result=None, gaps=())


class I8aTests(unittest.TestCase):
    def test_blocked_kill_death_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "player_died", "system", "p6"),
        ]
        self.assertEqual([v.id for v in check_i8(_arts(events))], ["I8a"])

    def test_blocked_kill_no_death_clean(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
        ]
        self.assertEqual(check_i8(_arts(events)), [])

    def test_same_target_poison_excused(self):
        # 守住了刀但同夜被毒死:不是 I8a 违例(守卫不挡毒)
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "witch_poison", "p4", "p6"),
            _ev("e4", 4, 1, "night", "player_died", "system", "p6"),
        ]
        self.assertEqual(check_i8(_arts(events)), [])


class I8bTests(unittest.TestCase):
    def test_milk_pierce_survival_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "witch_save", "p4", "p6"),
        ]
        self.assertEqual([v.id for v in check_i8(_arts(events))], ["I8b"])

    def test_milk_pierce_death_clean(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "witch_save", "p4", "p6"),
            _ev("e4", 4, 1, "night", "player_died", "system", "p6"),
        ]
        self.assertEqual(check_i8(_arts(events)), [])


class I8cTests(unittest.TestCase):
    def test_consecutive_same_target_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 5, 2, "night", "guard_protect", "p5", "p6"),
        ]
        self.assertEqual([v.id for v in check_i8c(_arts(events))], ["I8c"])

    def test_alternating_targets_clean(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 5, 2, "night", "guard_protect", "p5", "p3"),
            _ev("e3", 9, 3, "night", "guard_protect", "p5", "p6"),  # 隔夜回守合法
        ]
        self.assertEqual(check_i8c(_arts(events)), [])


class I2GuardTests(unittest.TestCase):
    def test_dead_guard_protect_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "player_died", "system", "p5"),
            _ev("e2", 2, 2, "night", "guard_protect", "p5", "p6"),
        ]
        self.assertEqual([v.id for v in check_i2(_arts(events))], ["I2"])


if __name__ == "__main__":
    unittest.main()
