"""Tasks 15-16: prove the B1 (prompt-leak) and B4 (double-death) runtime guards
are wired into EmergentGameEngine correctly.

The keystone is the HIGH-1 invariant: every B1 call sits OUTSIDE the provider
`try:` so a PromptLeakError PROPAGATES out of run() instead of being swallowed by
the broad `except Exception` and silently downgraded to a fallback turn.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import werewolf_eval.emergent_engine as ee
from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
    build_werewolf_win_script,
)
from werewolf_eval.invariants.guards import PromptLeakError, DoubleDeathCommitError


def _engine(script, *, seed=0, game_id="wiring_test"):
    return EmergentGameEngine(
        config=build_emergent_config(game_id=game_id),
        agents=build_emergent_fake_agents(script),
        seed=seed,
    )


class NormalGameDoesNotTripGuards(unittest.TestCase):
    def test_normal_fake_game_does_not_trip_guards(self) -> None:
        # A full, well-formed fake game must run to completion without any guard
        # firing — happy path never raises (no PromptLeakError / DoubleDeathCommit).
        for script in (build_villager_win_script(), build_werewolf_win_script()):
            engine = _engine(script)
            try:
                outcome = engine.run()
            except (PromptLeakError, DoubleDeathCommitError) as exc:  # pragma: no cover
                self.fail(f"normal fake game tripped a guard: {exc!r}")
            self.assertEqual(outcome.status, "completed")


class B1PropagatesOutsideTry(unittest.TestCase):
    def test_b1_propagates_outside_try(self) -> None:
        # THE HIGH-1 regression. Force a B1 raise at a DIRECT-respond site (speech),
        # whose surrounding `except Exception` WOULD swallow the error if the guard
        # were placed inside the try. p5 is a plain villager: its first guarded
        # provider call is the speech turn (a direct provider.respond site). If the
        # guard is correctly OUTSIDE the try, run() must re-raise PromptLeakError.
        orig = ee.assert_prompt_entitled

        def leaky(seat, source_event_ids, events_by_id, seat_index):
            if seat == "p5":
                raise PromptLeakError("synthetic leak at direct speech site for p5")
            return orig(seat, source_event_ids, events_by_id, seat_index)

        engine = _engine(build_villager_win_script())
        ee.assert_prompt_entitled = leaky
        try:
            with self.assertRaises(PromptLeakError):
                engine.run()
        finally:
            ee.assert_prompt_entitled = orig

    def test_b1_propagates_at_witch_direct_site(self) -> None:
        # Second direct-respond site coverage: the witch night call. p4 (witch) is
        # asked via provider.respond inside a `try/except Exception`. A raise here
        # must propagate, not downgrade to witch_pass.
        orig = ee.assert_prompt_entitled

        def leaky(seat, source_event_ids, events_by_id, seat_index):
            if seat == "p4":
                raise PromptLeakError("synthetic leak at direct witch site for p4")
            return orig(seat, source_event_ids, events_by_id, seat_index)

        engine = _engine(build_villager_win_script())
        ee.assert_prompt_entitled = leaky
        try:
            with self.assertRaises(PromptLeakError):
                engine.run()
        finally:
            ee.assert_prompt_entitled = orig


class B4DoubleCommitRaises(unittest.TestCase):
    def test_b4_double_commit_raises(self) -> None:
        # Force a COMMITTED (not candidate) duplicate at the night death-commit
        # site. In the werewolf-win script p5 dies on night 1. Pre-seeding
        # _death_committed with p5 makes the second commit a hard duplicate: p5 is
        # still alive at the commit (the legal `pid not in self._alive` candidate
        # skip does NOT apply), so assert_death_commit_once must raise.
        engine = _engine(build_werewolf_win_script())
        engine._death_committed.add("p5")
        with self.assertRaises(DoubleDeathCommitError):
            engine.run()

    def test_b4_candidate_skip_is_silent_not_a_double_commit(self) -> None:
        # Guard against false positives: the legal co-victim candidate skip (a pid
        # already removed from _alive) must NOT reach the commit guard. A clean game
        # completes with no DoubleDeathCommitError.
        engine = _engine(build_werewolf_win_script())
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")


if __name__ == "__main__":
    unittest.main()
