from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.envelope import ActionEnvelope
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.validator import ActionValidator


class EnvelopeTests(unittest.TestCase):
    def test_legacy_target_maps_to_targets0(self) -> None:
        e = ActionEnvelope.from_legacy(
            actor="p1", role="werewolf", phase="night", action="werewolf_kill",
            target="p3", reason_summary="x", decision_type="inference_based", confidence=0.9,
        )
        self.assertEqual(e.targets, ["p3"])
        self.assertEqual(e.target, "p3")           # projection back to single target

    def test_no_target_action(self) -> None:
        e = ActionEnvelope(
            actor="p4", role="witch", phase="night", action="witch_pass",
            targets=[], params={}, reason_summary="save it",
            decision_type="default", confidence=1.0,
        )
        self.assertEqual(e.targets, [])
        self.assertIsNone(e.target)

    def test_multi_target(self) -> None:
        e = ActionEnvelope(
            actor="cupid", role="cupid", phase="setup", action="cupid_link",
            targets=["p2", "p5"], params={}, reason_summary="",
            decision_type="inference_based", confidence=1.0,
        )
        self.assertEqual(e.targets, ["p2", "p5"])
        self.assertEqual(e.target, "p2")           # projection = first

    def test_legacy_none_target_is_empty(self) -> None:
        e = ActionEnvelope.from_legacy(
            actor="p4", role="witch", phase="night", action="witch_pass",
            target="none", reason_summary="x", decision_type="default", confidence=1.0,
        )
        self.assertEqual(e.targets, [])


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.v = ActionValidator(RoleAbilityRegistry(rules_v1()))
        self.s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p4", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager"},
            night_victim="p5",
        )

    def _env(self, role: str, phase: str, action: str, target: str) -> ActionEnvelope:
        return ActionEnvelope.from_legacy(
            actor={"werewolf": "p1", "seer": "p3", "witch": "p4", "villager": "p5"}[role],
            role=role, phase=phase, action=action, target=target,
            reason_summary="x", decision_type="inference_based", confidence=0.9,
        )

    # --- target legality: use validate_in_state (needs the RuntimeState) ---
    def test_wolf_kill_villager_ok(self) -> None:
        self.assertTrue(self.v.validate_in_state(self._env("werewolf", "night", "werewolf_kill", "p5"), self.s).ok)

    def test_wolf_kill_wolf_rejected(self) -> None:
        r = self.v.validate_in_state(self._env("werewolf", "night", "werewolf_kill", "p2"), self.s)
        self.assertFalse(r.ok)
        self.assertEqual(r.reason_kind, "invalid_target")

    def test_seer_check_self_rejected(self) -> None:
        self.assertFalse(self.v.validate_in_state(self._env("seer", "night", "seer_check", "p3"), self.s).ok)

    def test_witch_save_non_victim_rejected(self) -> None:
        self.assertFalse(self.v.validate_in_state(self._env("witch", "night", "witch_save", "p1"), self.s).ok)
        self.assertTrue(self.v.validate_in_state(self._env("witch", "night", "witch_save", "p5"), self.s).ok)

    def test_witch_poison_self_rejected(self) -> None:
        # engine rejects the witch poisoning herself (emergent_engine.py:702)
        self.assertFalse(self.v.validate_in_state(self._env("witch", "night", "witch_poison", "p4"), self.s).ok)
        self.assertTrue(self.v.validate_in_state(self._env("witch", "night", "witch_poison", "p1"), self.s).ok)

    # --- action allowed / arity: stateless validate() ---
    def test_action_not_allowed_for_role_phase(self) -> None:
        r = self.v.validate(self._env("villager", "night", "werewolf_kill", "p1"))
        self.assertFalse(r.ok)
        self.assertEqual(r.reason_kind, "invalid_action")

    def test_witch_pass_no_target_ok(self) -> None:
        e = ActionEnvelope(
            actor="p4", role="witch", phase="night", action="witch_pass",
            targets=[], params={}, reason_summary="x", decision_type="default", confidence=1.0,
        )
        self.assertTrue(self.v.validate(e).ok)
        self.assertTrue(self.v.validate_in_state(e, self.s).ok)


if __name__ == "__main__":
    unittest.main()
