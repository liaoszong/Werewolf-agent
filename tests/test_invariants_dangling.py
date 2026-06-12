"""C3-1: a prompt source id that references an event ABSENT from the event log
must fail loud on BOTH paths — the runtime B1 guard and the offline I4b checker.

Before the fix, both paths silently `continue` past a dangling id (the runtime
guard never aborted; the offline checker emitted no violation), and the runtime
guard's docstring falsely claimed the offline checker reported it as an artifact
gap. A renderer that sourced a never-logged event id was invisible to both.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.invariants.guards import (
    DanglingSourceEventError,
    PromptLeakError,
    assert_prompt_entitled,
)
from werewolf_eval.invariants.checker import check_i4b
from werewolf_eval.invariants.artifacts import RunArtifacts
from werewolf_eval.invariants.visibility_oracle import seat_index_from_players

_PLAYERS = [
    {"player_id": "p1", "role": "seer", "team": "villager"},
    {"player_id": "p2", "role": "villager", "team": "villager"},
]
_SEER_EV = {"event_id": "e1", "type": "seer_check", "actor": "p1", "target": "p3",
            "visibility": "seer", "round": 1, "phase": "night", "sequence": 1,
            "data": {"summary": ""}}


def _arts(turns):
    return RunArtifacts(game_id="g", players=_PLAYERS, events=[_SEER_EV],
                        decisions=[], provider_turns=turns, result=None)


class RuntimeDanglingGuardTests(unittest.TestCase):
    def setUp(self):
        self.idx = seat_index_from_players(_PLAYERS)
        self.by_id = {"e1": _SEER_EV}

    def test_dangling_source_id_fails_loud(self):
        """A source id absent from the event log raises (no silent skip)."""
        with self.assertRaises(DanglingSourceEventError):
            assert_prompt_entitled("p2", ["missing"], self.by_id, self.idx)

    def test_known_entitled_id_still_passes(self):
        assert_prompt_entitled("p1", ["e1"], self.by_id, self.idx)

    def test_known_but_nonentitled_id_still_leak_errors(self):
        with self.assertRaises(PromptLeakError):
            assert_prompt_entitled("p2", ["e1"], self.by_id, self.idx)


class OfflineDanglingCheckerTests(unittest.TestCase):
    def test_dangling_source_id_yields_violation(self):
        """check_i4b reports a dangling source id instead of silently skipping it."""
        turns = [{"actor": "p1", "request_id": "g_r01_p1", "phase": "night",
                  "observation_source_event_ids": ["ghost"]}]
        v = check_i4b(_arts(turns))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].event_ids, ("ghost",))
        self.assertIn("ghost", v[0].detail)
        # surfaced as an error-severity integrity failure, not swallowed
        self.assertEqual(v[0].severity, "error")

    def test_present_entitled_id_still_clean(self):
        turns = [{"actor": "p1", "request_id": "g_r01_p1", "phase": "night",
                  "observation_source_event_ids": ["e1"]}]
        self.assertEqual(check_i4b(_arts(turns)), [])


if __name__ == "__main__":
    unittest.main()
