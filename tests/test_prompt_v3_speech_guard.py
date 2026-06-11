# tests/test_prompt_v3_speech_guard.py
"""build_speech_system_prompt_v3 must not deny the guard's existence on guard
boards; non-guard boards stay byte-identical (golden-locked)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.llm_providers import build_speech_system_prompt_v3
from werewolf_eval.prompt_v2 import build_board_rules_card
from werewolf_eval.provider_contract import ProviderRequest

STD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
             "p4": "witch", "p5": "villager", "p6": "villager"}
GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
               "p4": "witch", "p5": "guard", "p6": "villager"}


def _req(board_card):
    return ProviderRequest(
        request_id="t", game_id="t", actor="p5", phase="day", round=1,
        observation={}, allowed_actions=[], allowed_targets=[],
        response_kind="speech", board_card=board_card,
    )


class SpeechV3GuardConditionalTests(unittest.TestCase):
    def test_no_board_card_byte_identical(self):
        # golden 样本路径(board_card 缺省 ""):字节必须保持现状
        text = build_speech_system_prompt_v3(_req(""))
        self.assertIn("也没有警长、守卫等本局规则卡之外的机制", text)

    def test_standard_board_byte_identical(self):
        # 非守卫板的规则卡里有「没有守卫或守夜人」字样,不得误触发条件分支
        card = build_board_rules_card(rules_v1_1(), STD_SEATS)
        text = build_speech_system_prompt_v3(_req(card))
        self.assertIn("也没有警长、守卫等本局规则卡之外的机制", text)

    def test_guard_board_drops_guard_denial(self):
        card = build_board_rules_card(rules_v1_2(), GUARD_SEATS)
        text = build_speech_system_prompt_v3(_req(card))
        self.assertNotIn("守卫等本局规则卡之外的机制", text)
        self.assertIn("也没有警长等本局规则卡之外的机制", text)


if __name__ == "__main__":
    unittest.main()
