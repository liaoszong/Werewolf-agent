# tests/test_settler_guard_branches.py
"""Pin the two I8 branches of JointSettler's PRE-EXISTING guard path (settler.py:46-53).
The settler is NOT modified by the L4 arm — these tests freeze the contract the
engine wiring relies on, incl. poison-not-blocked."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_2
from werewolf_eval.action_runtime.settler import JointSettler, NightIntents
from werewolf_eval.action_runtime.state import RuntimeState


def _state():
    return RuntimeState(
        alive=frozenset({"p1", "p2", "p3", "p4", "p5", "p6"}),
        roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer",
               "p4": "witch", "p5": "guard", "p6": "villager"},
    )


class SettlerGuardBranchTests(unittest.TestCase):
    def setUp(self):
        self.settler = JointSettler(rules_v1_2())

    def test_i8a_guard_blocks_kill_no_save(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=False, poison_target=None, guard_target="p6"),
            _state())
        self.assertNotIn("p6", r.deaths)

    def test_i8b_guard_plus_save_same_target_dies(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=True, poison_target=None, guard_target="p6"),
            _state())
        self.assertIn("p6", r.deaths)  # 奶穿(guard+save_same_target=death,查表)

    def test_guard_does_not_block_poison(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim=None, saved=False, poison_target="p6", guard_target="p6"),
            _state())
        self.assertIn("p6", r.deaths)  # 守卫不挡毒

    def test_guard_elsewhere_kill_lands(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=False, poison_target=None, guard_target="p3"),
            _state())
        self.assertIn("p6", r.deaths)


if __name__ == "__main__":
    unittest.main()
