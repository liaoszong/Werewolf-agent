"""Engine-in-loop guard board fuzz tests (C3-3).

The audit found that the original 50-seed fuzz (fuzz.py) has no guard board,
produces only ~9 effective shapes, and feeds hand-crafted synthetic artifacts
directly to the checker without the engine in the loop. I8a/I8b/I8c vacuously
pass.

This file exercises the guard-board generator that drives JointSettler (the
real engine settlement component) to compute deaths, builds RunArtifacts from
the computed results, then validates through check_run.
"""

import unittest
from werewolf_eval.invariants import check_run
from werewolf_eval.invariants.fuzz import (
    guard_board_game,
    guard_board_known_bad,
)

GUARD_FUZZ_SEEDS = tuple(range(20))


class TestGuardFuzzEngine(unittest.TestCase):
    """C3-3: engine-in-loop fuzz with guard boards."""

    def test_every_guard_board_seed_passes_all_invariants(self):
        """Well-formed guard board games (engine-computed deaths) must pass all
        invariants. I8a/I8b/I8c are actually exercised here — no more vacuum."""
        for seed in GUARD_FUZZ_SEEDS:
            arts = guard_board_game(seed)
            violations = [v for v in check_run(arts) if v.severity == "error"]
            self.assertEqual(
                violations, [],
                f"seed {seed} produced violations: {[(v.id, v.detail) for v in violations]}",
            )

    def test_each_guard_known_bad_fails_its_target(self):
        """Known-bad guard scenarios must hit their expected invariant IDs."""
        for label, arts, expected_id in guard_board_known_bad():
            ids = {v.id for v in check_run(arts)}
            self.assertIn(
                expected_id, ids,
                f"{label} should fail {expected_id}; got {ids}",
            )

    def test_guard_fuzz_exercises_i8(self):
        """At least some guard seeds produce events that trigger I8-relevant
        checker paths (non-vacuous: guard_protect events exist)."""
        any_guard = False
        any_kill_with_guard = False
        for seed in GUARD_FUZZ_SEEDS:
            arts = guard_board_game(seed)
            guard_events = [e for e in arts.events if e.get("type") == "guard_protect"]
            kill_events = [e for e in arts.events if e.get("type") == "werewolf_kill"]
            if guard_events:
                any_guard = True
            # Check if at least one kill and guard share the same target (I8a/I8b path)
            for ge in guard_events:
                for ke in kill_events:
                    if ge.get("target") == ke.get("target"):
                        any_kill_with_guard = True
        self.assertTrue(any_guard, "guard_protect events must appear in fuzz")
        self.assertTrue(any_kill_with_guard,
                        "guard+kill same-target scenarios must appear (I8 path not vacuum)")


if __name__ == "__main__":
    unittest.main()
