from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1
from werewolf_eval.action_runtime.settler import JointSettler, NightIntents
from werewolf_eval.action_runtime.state import RuntimeState


class SettlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settler = JointSettler(rules_v1())
        self.all_alive = RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p4", "p5", "p6"}), roles={}
        )

    def test_unsaved_victim_dies(self) -> None:
        r = self.settler.resolve_night(NightIntents(wolf_victim="p5"), self.all_alive)
        self.assertEqual(r.deaths, ["p5"])

    def test_saved_victim_lives(self) -> None:
        r = self.settler.resolve_night(NightIntents(wolf_victim="p5", saved=True), self.all_alive)
        self.assertEqual(r.deaths, [])

    def test_poison_adds_death_victim_then_poison_order(self) -> None:
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p5", poison_target="p2"), self.all_alive
        )
        self.assertEqual(r.deaths, ["p5", "p2"])

    def test_poison_only(self) -> None:
        r = self.settler.resolve_night(NightIntents(poison_target="p2"), self.all_alive)
        self.assertEqual(r.deaths, ["p2"])

    def test_dead_targets_ignored(self) -> None:
        st = RuntimeState(alive=frozenset({"p1", "p3"}), roles={})
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p5", poison_target="p9"), st
        )
        self.assertEqual(r.deaths, [])

    def test_poison_same_as_victim_not_duplicated(self) -> None:
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p5", poison_target="p5"), self.all_alive
        )
        self.assertEqual(r.deaths, ["p5"])

    def test_naide_chuan_guard_plus_save_dies(self) -> None:
        # 奶穿 (rules_v1): guard + witch_save on the same target -> dies anyway.
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p5", saved=True, guard_target="p5"), self.all_alive
        )
        self.assertEqual(r.deaths, ["p5"])

    def test_guard_alone_cancels_kill(self) -> None:
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p5", guard_target="p5"), self.all_alive
        )
        self.assertEqual(r.deaths, [])


if __name__ == "__main__":
    unittest.main()
