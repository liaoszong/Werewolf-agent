"""prompt_v4 witch coordination suffix: 3-condition truth table + content
discipline locks (spec 2026-06-12-l4-guard-witch-coord-arm-design §3/§4)."""
from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.prompt_v2 import build_board_rules_card
from werewolf_eval.prompt_v4 import WITCH_COORD_GUIDANCE, render_witch_coord_suffix

_STD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
              "p4": "witch", "p5": "villager", "p6": "villager"}
_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}

GUARD_CARD = build_board_rules_card(rules_v1_2(), _GUARD_SEATS)
STD_CARD = build_board_rules_card(rules_v1_1(), _STD_SEATS)


class TruthTableTest(unittest.TestCase):
    """spec §9: 8-combination truth table — ONLY guard∧victim∧antidote-unused injects."""

    def test_only_full_conjunction_injects(self):
        for has_guard, has_victim, save_used in itertools.product((True, False), repeat=3):
            card = GUARD_CARD if has_guard else STD_CARD
            victim = "p5" if has_victim else None
            out = render_witch_coord_suffix(card, victim, save_used)
            if has_guard and has_victim and not save_used:
                self.assertEqual(out, "\n" + WITCH_COORD_GUIDANCE)
            else:
                self.assertEqual(out, "", (has_guard, has_victim, save_used))

    def test_v1_style_empty_or_none_board_card_is_non_guard(self):
        # prompt_v1's renderer board_card is "" — must behave like a non-guard board.
        self.assertEqual(render_witch_coord_suffix("", "p5", False), "")
        self.assertEqual(render_witch_coord_suffix(None, "p5", False), "")


class GuidanceContentTest(unittest.TestCase):
    """spec §4 文案纪律: risk-tradeoff wording, no 「高价值就救」, no lies."""

    def test_guidance_markers(self):
        self.assertIn("【解药协调提示】", WITCH_COORD_GUIDANCE)
        self.assertIn("同守同救", WITCH_COORD_GUIDANCE)
        self.assertIn("你无法知道守卫今晚守了谁", WITCH_COORD_GUIDANCE)
        self.assertIn("不要机械地夜1必救", WITCH_COORD_GUIDANCE)
        self.assertIn("死亡风险高", WITCH_COORD_GUIDANCE)
        self.assertNotIn("高价值", WITCH_COORD_GUIDANCE)
        # 引号字节钉死(独立审 B-1):spec §4 用 ASCII 直引号,不许被"美化"成 CJK 弯引号
        self.assertIn('你认为"死亡风险高、且不太可能同时被守卫守护"的目标', WITCH_COORD_GUIDANCE)
        self.assertNotIn("“", WITCH_COORD_GUIDANCE)
        self.assertNotIn("”", WITCH_COORD_GUIDANCE)

    def test_guidance_has_no_newlines(self):
        # Single paragraph; the injected suffix's ONLY newline is the leading join.
        self.assertNotIn("\n", WITCH_COORD_GUIDANCE)


if __name__ == "__main__":
    unittest.main()
