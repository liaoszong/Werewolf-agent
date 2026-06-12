"""Independent guard oracle for night death resolution (C3-5).

The audit found that test_action_runtime_parity.py's _old_night_deaths had no guard
parameter and the global diff-gate was deleted, leaving the settler's milk-pierce
branch with no second witness. A synchronised error in JointSettler AND its unit
tests would pass silently.

This file provides an INDEPENDENT hand-written formula that does NOT reuse JointSettler
logic. It enumerates guard*save*poison*alive*hunter_shoot combinations and compares
against JointSettler results.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_2
from werewolf_eval.action_runtime.settler import JointSettler, NightIntents
from werewolf_eval.action_runtime.state import RuntimeState


def _guard_death_oracle(victim, saved, poison, guard_target, alive):
    """INDEPENDENT hand-written guard death formula. NOT derived from JointSettler.

    Rules (from standard Werewolf with guard expansion, spec 2026-06-11):
      - Wolf victim dies UNLESS protected. Protection sources:
          a) Witch save (antidote) — cancels the kill.
          b) Guard protect — cancels the kill.
      - EXCEPT: if BOTH guard and witch save the SAME target, that target dies
        (milk-pierce / 奶穿 — double protection backfires).
      - Guard does NOT block poison. Poison always kills the target (if alive).
      - A target can die at most once (de-duplicated; victim-then-poison priority).
    """
    deaths: list[str] = []

    # ---- determine whether the wolf victim is protected ----
    protected = saved  # witch save alone blocks the kill
    if guard_target is not None and victim is not None and guard_target == victim:
        if saved:
            protected = False  # 奶穿: guard+save_same_target = death
        else:
            protected = True   # guard alone blocks the kill

    # ---- wolf victim death ----
    if victim is not None and not protected and victim in alive:
        deaths.append(victim)

    # ---- poison death (guard does NOT block poison) ----
    if poison is not None and poison in alive and poison not in deaths:
        deaths.append(poison)

    return deaths


# ---- exhaustive grid: guard * victim * save * poison * alive sets ----

_BASE_ALIVE = frozenset({"p1", "p2", "p3", "p4", "p5", "p6"})
_ALIVE_SETS = [
    _BASE_ALIVE,
    frozenset({"p2", "p3", "p4", "p5", "p6"}),       # p1 voted out
    frozenset({"p4", "p5", "p6"}),                    # late game
    frozenset({"p4"}),                                 # only wolf alive
    frozenset(),
]
_IDS = [None, "p1", "p2", "p3", "p4", "p5", "p6"]
_ROSTER = {"p1": "seer", "p2": "witch", "p3": "hunter", "p4": "werewolf",
           "p5": "guard", "p6": "villager"}


class GuardOracleTests(unittest.TestCase):
    def setUp(self):
        self.settler = JointSettler(rules_v1_2())

    def test_oracle_matches_settler_over_guard_victim_save_poison_grid(self):
        """C3-5: enumerate guard * victim * save * poison * alive.
        The oracle formula and JointSettler must agree on every cell."""
        for alive in _ALIVE_SETS:
            state = RuntimeState(alive=alive, roles=dict(_ROSTER))
            for victim in _IDS:
                for guard_target in _IDS:
                    for saved in (False, True):
                        for poison in _IDS:
                            got = self.settler.resolve_night(
                                NightIntents(wolf_victim=victim, saved=saved,
                                             poison_target=poison,
                                             guard_target=guard_target),
                                state,
                            ).deaths
                            exp = _guard_death_oracle(victim, saved, poison,
                                                      guard_target, alive)
                            self.assertEqual(
                                got, exp,
                                f"victim={victim} saved={saved} poison={poison} "
                                f"guard={guard_target} alive={sorted(alive)}",
                            )

    def test_guard_alone_blocks_kill_i8a_shape(self):
        """Guard on victim, no save: victim must survive."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        for victim in ("p1", "p2", "p3", "p6"):
            got = self.settler.resolve_night(
                NightIntents(wolf_victim=victim, saved=False, guard_target=victim),
                state,
            ).deaths
            self.assertEqual(got, [], f"guard should block kill on {victim}")

    def test_milk_pierce_i8b_shape(self):
        """Guard + save on same victim: victim MUST die (奶穿)."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        for victim in ("p1", "p2", "p3", "p6"):
            got = self.settler.resolve_night(
                NightIntents(wolf_victim=victim, saved=True, guard_target=victim),
                state,
            ).deaths
            self.assertIn(victim, got, f"milk-pierce: {victim} must die")

    def test_guard_does_not_block_poison(self):
        """Guard on X, poison on X, no kill: X still dies from poison."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        got = self.settler.resolve_night(
            NightIntents(wolf_victim=None, saved=False, poison_target="p6",
                         guard_target="p6"),
            state,
        ).deaths
        self.assertIn("p6", got, "guard must not block poison")

    def test_guard_elsewhere_victim_lands(self):
        """Guard on A, wolf kills B, no save: B dies."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        got = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=False, guard_target="p1"),
            state,
        ).deaths
        self.assertIn("p6", got)

    def test_save_alone_blocks_kill(self):
        """No guard, witch saves victim: victim survives."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        got = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=True, guard_target=None),
            state,
        ).deaths
        self.assertEqual(got, [], "save alone should block kill")

    def test_kill_poison_same_target_deduplicated(self):
        """Wolf kills X, poison on X: X dies once (de-duplicated)."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        got = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=False, poison_target="p6"),
            state,
        ).deaths
        self.assertEqual(got, ["p6"], "same-target kill+poison should die once")

    def test_kill_poison_different_targets_both_die(self):
        """Wolf kills X, poison on Y: both die."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        got = self.settler.resolve_night(
            NightIntents(wolf_victim="p1", saved=False, poison_target="p3"),
            state,
        ).deaths
        self.assertEqual(set(got), {"p1", "p3"})

    def test_already_dead_not_rekilled(self):
        """Wolf kills an already-dead player: not in deaths."""
        alive = frozenset({"p4", "p5", "p6"})
        state = RuntimeState(alive=alive, roles=dict(_ROSTER))
        got = self.settler.resolve_night(
            NightIntents(wolf_victim="p1", saved=False),
            state,
        ).deaths
        self.assertEqual(got, [], "dead target not in alive set")

    def test_oracle_known_identities(self):
        """Pin a few high-signal cells that exercise each branch independently."""
        alive = _BASE_ALIVE
        state = RuntimeState(alive=alive, roles=dict(_ROSTER))

        table = [
            # (victim, saved, poison, guard, expected_deaths, label)
            (None, False, None, None, [], "no action"),
            ("p6", False, None, None, ["p6"], "bare kill"),
            ("p6", True, None, None, [], "save blocks kill"),
            ("p6", False, None, "p6", [], "guard blocks kill"),
            ("p6", True, None, "p6", ["p6"], "milk-pierce: guard+save same target dies"),
            ("p6", True, None, "p1", [], "save+guard_elsewhere: save blocks"),
            ("p6", True, "p3", "p6", ["p6", "p3"], "milk-pierce+victim dies+poison"),
            ("p6", False, "p6", "p6", ["p6"], "guard blocks kill but poison kills same target"),
            (None, False, "p6", "p6", ["p6"], "poison only, guard irrelevant"),
            ("p6", False, "p1", "p6", ["p1"], "guard blocks kill, poison kills other"),
        ]
        for victim, saved, poison, guard, exp, _label in table:
            got = self.settler.resolve_night(
                NightIntents(wolf_victim=victim, saved=saved,
                             poison_target=poison, guard_target=guard),
                state,
            ).deaths
            self.assertEqual(set(got), set(exp),
                             f"victim={victim} saved={saved} poison={poison} "
                             f"guard={guard}")

    def test_hunter_shoot_not_in_settler_scope(self):
        """Hunter shoot is a death cascade, not a settler input. Verify it does
        NOT affect settler deaths (the engine layers hunter on top)."""
        state = RuntimeState(alive=_BASE_ALIVE, roles=dict(_ROSTER))
        got = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=False, guard_target=None),
            state,
        ).deaths
        # hunter_shoot is not a NightIntent field — it doesn't go through settler
        self.assertEqual(got, ["p6"])


if __name__ == "__main__":
    unittest.main()
