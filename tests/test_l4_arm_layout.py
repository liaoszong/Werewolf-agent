# tests/test_l4_arm_layout.py
"""Arm.multiset + GUARD_MULTISET pairing semantics (L4 arm Task 14). Layout
literals were pre-computed with the real RNG (random.Random(seed).shuffle)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.ablation.arms import Arm, CANONICAL_MULTISET, GUARD_MULTISET, layout_for


class PairingRegressionTests(unittest.TestCase):
    def test_default_arm_layouts_byte_identical(self):
        # 既有臂(缺省 multiset)布局逐字节不变 —— 三臂快照的配对语义不被破坏
        arm = Arm(label="x", prompt_version="prompt_v1")
        self.assertEqual(layout_for(arm, 0), {
            "p1": "seer", "p2": "villager", "p3": "werewolf",
            "p4": "villager", "p5": "werewolf", "p6": "witch"})
        self.assertEqual(layout_for(arm, 1), {
            "p1": "witch", "p2": "villager", "p3": "seer",
            "p4": "villager", "p5": "werewolf", "p6": "werewolf"})

    def test_guard_arm_layout_seed_paired(self):
        # 同 seed 同 RNG 流,multiset 换为守卫板(配对 = seed 配对,spec §5)
        arm = Arm(label="l4_guard", prompt_version="prompt_v3", multiset=GUARD_MULTISET)
        self.assertEqual(layout_for(arm, 0), {
            "p1": "seer", "p2": "guard", "p3": "werewolf",
            "p4": "villager", "p5": "werewolf", "p6": "witch"})
        self.assertEqual(layout_for(arm, 1), {
            "p1": "witch", "p2": "guard", "p3": "seer",
            "p4": "villager", "p5": "werewolf", "p6": "werewolf"})

    def test_guard_multiset_composition(self):
        self.assertEqual(sorted(GUARD_MULTISET),
                         ["guard", "seer", "villager", "werewolf", "werewolf", "witch"])
        self.assertEqual(sorted(CANONICAL_MULTISET),
                         ["seer", "villager", "villager", "werewolf", "werewolf", "witch"])


if __name__ == "__main__":
    unittest.main()
