"""Differential regression guard for the Phase-3 swaps.

The oracle is an **independent reimplementation** of the pre-swap engine's inline
logic (copied from `emergent_engine.py` @ commit 5ace7bc) — NOT the new engine's
own output. This avoids the circularity the audit caught in the prior version of
this file, which rebuilt night intents from the *new* engine's game-log and re-ran
the *same* JointSettler against them (comparing the settler to itself; a
poison-dropping settler regression stayed green).

A regression in the new settler/validator now diverges from the hand-written OLD
formula and FAILS here. Covers the settler (night-death formula) and the three
validation swaps (wolf/seer/vote legality).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.envelope import ActionEnvelope
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1
from werewolf_eval.action_runtime.settler import JointSettler, NightIntents
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.validator import ActionValidator

ROSTER = {"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager", "p6": "villager"}
TARGETS = list(ROSTER) + ["pX"]   # include an unknown id (proxy for dead/unknown)


# --- INDEPENDENT oracle: the pre-swap inline formulas (emergent_engine @5ace7bc) ---

def _old_night_deaths(victim, saved, poison, alive):
    deaths = []
    if victim is not None and not saved and victim in alive:
        deaths.append(victim)
    if poison is not None and poison in alive and poison not in deaths:
        deaths.append(poison)
    return deaths


def _old_valid(kind, action, target, alive, actor):
    if kind == "wolf":
        return (action == "werewolf_kill" and target in alive
                and ROSTER.get(target) is not None and ROSTER.get(target) != "werewolf")
    if kind == "seer":
        return action == "seer_check" and target in alive and target != actor
    if kind == "vote":
        return action == "player_vote" and target in alive and target != actor
    raise AssertionError(kind)


class SettlerDifferentialTests(unittest.TestCase):
    def test_settler_matches_old_night_formula_over_grid(self) -> None:
        settler = JointSettler(rules_v1())
        alive_sets = [
            frozenset(ROSTER),
            frozenset({"p2", "p3", "p4", "p5", "p6"}),   # p1 voted out
            frozenset({"p4", "p5"}),
            frozenset(),
        ]
        opts = [None] + list(ROSTER)
        for alive in alive_sets:
            state = RuntimeState(alive=alive, roles=dict(ROSTER))
            for victim in opts:
                for poison in opts:
                    for saved in (False, True):
                        got = settler.resolve_night(
                            NightIntents(wolf_victim=victim, saved=saved, poison_target=poison), state
                        ).deaths
                        exp = _old_night_deaths(victim, saved, poison, alive)
                        self.assertEqual(got, exp, f"victim={victim} saved={saved} poison={poison} alive={sorted(alive)}")


class ValidationDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.v = ActionValidator(RoleAbilityRegistry(rules_v1()))
        self.alive = frozenset(ROSTER)

    def _ok(self, role, phase, action, target, actor) -> bool:
        return self.v.validate_in_state(
            ActionEnvelope.from_legacy(
                actor=actor, role=role, phase=phase, action=action, target=target,
                reason_summary="", decision_type="", confidence=1.0,
            ),
            RuntimeState(alive=self.alive, roles=dict(ROSTER)),
        ).ok

    def test_wolf_kill_matches_old(self) -> None:
        for action in ("werewolf_kill", "seer_check", "player_vote"):
            for target in TARGETS:
                self.assertEqual(
                    self._ok("werewolf", "night", action, target, "p1"),
                    _old_valid("wolf", action, target, self.alive, "p1"),
                    f"wolf action={action} target={target}",
                )

    def test_seer_check_matches_old(self) -> None:
        for action in ("seer_check", "werewolf_kill"):
            for target in TARGETS:
                self.assertEqual(
                    self._ok("seer", "night", action, target, "p3"),
                    _old_valid("seer", action, target, self.alive, "p3"),
                    f"seer action={action} target={target}",
                )

    def test_vote_matches_old_for_every_role(self) -> None:
        for role, actor in (("werewolf", "p1"), ("seer", "p3"), ("witch", "p4"), ("villager", "p5")):
            for target in TARGETS:
                self.assertEqual(
                    self._ok(role, "day_vote", "player_vote", target, actor),
                    _old_valid("vote", "player_vote", target, self.alive, actor),
                    f"vote role={role} target={target}",
                )


if __name__ == "__main__":
    unittest.main()
