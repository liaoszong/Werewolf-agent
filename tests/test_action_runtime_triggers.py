from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.triggers import TriggerSystem

SEAT = ["p1", "p2", "p3", "p4", "p5", "p6"]


class TriggerTests(unittest.TestCase):
    def test_no_trigger_passthrough_is_seat_ordered(self) -> None:
        ts = TriggerSystem({}, SEAT)
        st = RuntimeState(alive=frozenset({"p2", "p5"}), roles={"p2": "villager", "p5": "villager"})
        self.assertEqual(ts.resolve(["p5", "p2"], st), ["p2", "p5"])

    def test_hunter_lover_chain_death(self) -> None:
        # wolf kills p2 (lover of p5); p2 death -> heartbreak p5; p5 is hunter -> shoots p3.
        st = RuntimeState(
            alive=frozenset({"p2", "p3", "p5"}),
            roles={"p2": "villager", "p3": "seer", "p5": "hunter"},
        )

        def lover(_s: RuntimeState, dead: str) -> list[str]:
            return ["p5"] if dead == "p2" else []

        def hunter(_s: RuntimeState, dead: str) -> list[str]:
            return ["p3"]

        ts = TriggerSystem({"villager": lover, "hunter": hunter}, SEAT)
        self.assertEqual(ts.resolve(["p2"], st), ["p2", "p5", "p3"])

    def test_mutual_lovers_terminate(self) -> None:
        st = RuntimeState(alive=frozenset({"p1", "p2"}), roles={"p1": "lover", "p2": "lover"})

        def lover(_s: RuntimeState, dead: str) -> list[str]:
            return ["p2"] if dead == "p1" else ["p1"]

        ts = TriggerSystem({"lover": lover}, ["p1", "p2"])
        # both die exactly once; no infinite loop.
        self.assertEqual(ts.resolve(["p1"], st), ["p1", "p2"])

    def test_simultaneous_deaths_resolve_in_seat_order(self) -> None:
        ts = TriggerSystem({}, SEAT)
        st = RuntimeState(alive=frozenset(SEAT), roles={p: "villager" for p in SEAT})
        self.assertEqual(ts.resolve(["p4", "p1", "p3"], st), ["p1", "p3", "p4"])


if __name__ == "__main__":
    unittest.main()
