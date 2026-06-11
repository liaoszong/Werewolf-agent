from collections import Counter

from werewolf_eval.action_runtime.ruleset import rules_v1_1
from werewolf_eval.prompt_v2 import build_board_rules_card

STD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager", "p6": "villager"}


def test_rules_card_is_data_driven_from_board():
    card = build_board_rules_card(rules_v1_1(), STD_SEATS)
    # 构成计数来自 seat_roles,不是写死的
    assert "狼人×2" in card and "预言家×1" in card and "女巫×1" in card and "村民×2" in card
    # 本局没有猎人 -> 卡上不得出现猎人(数据驱动的核心断言)
    assert "猎人" not in card
    # 能力归属(P5 打击面):验人=预言家、救/毒=女巫
    assert "查验" in card and "解药" in card and "毒药" in card
    # 胜负 / parity 口径与引擎一致
    assert "所有狼人出局" in card and "达到或超过" in card
    # 反视觉幻觉声明(P3 打击面)
    assert "纯文字" in card and "眼神" in card
    # P4 打击面:显式否定不存在的机制(对齐 metrics.MECHANIC_WORDS 扫词面),
    # 并要求不在发言中复述它们(防 halluc_mechanic 扫词被"规则说了没警长"反向污染)
    assert "警长" in card and "警徽" in card and "守卫" in card and "守夜人" in card
    assert "不存在" in card and "不要在发言中讨论" in card


def test_rules_card_includes_hunter_on_hunter_board():
    seats = dict(STD_SEATS); seats["p6"] = "hunter"
    card = build_board_rules_card(rules_v1_1(), seats)
    assert "猎人×1" in card and "开枪" in card and "村民×1" in card
