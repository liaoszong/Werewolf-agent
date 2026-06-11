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


from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.prompt_v2 import render_observation_text_v2


def _ev(eid, seq, rnd, phase, etype, actor, target, summary):
    return {"event_id": eid, "sequence": seq, "round": rnd, "phase": phase, "type": etype,
            "actor": actor, "target": target, "visibility": "public",
            "data": {"summary": summary}}


EVENTS = {
    "e1": _ev("e1", 1, 1, "night", "seer_check", "p3", "p1", "Seer p3 checks p1, result: werewolf."),
    "e2": _ev("e2", 2, 1, "day", "day_announcement", "system", "none", "Night fell: p5 died."),
    "e3": _ev("e3", 3, 1, "day", "player_died", "system", "p5", "p5 died during the night."),
    "e4": _ev("e4", 4, 1, "day", "player_speech", "p3", "none", "我验了p1,他是狼。"),
    "e5": _ev("e5", 5, 1, "day", "player_speech", "p1", "none", "p3在说谎,我是好人。"),
    "e6": _ev("e6", 6, 1, "day", "player_vote", "p3", "p1", "p3 votes p1."),
    "e7": _ev("e7", 7, 1, "day", "player_vote", "p1", "p3", "p1 votes p3."),
    "hidden": _ev("hidden", 8, 1, "night", "werewolf_kill", "p1", "p5", "Wolf team kills p5."),
}


def _seer_obs():
    return AgentObservation(
        game_id="g", player_id="p3", role="seer", team="villager", phase="day", round=2,
        alive_players=["p1", "p2", "p3", "p4", "p6"],
        public_event_ids=["e2", "e3", "e4", "e5", "e6", "e7"],
        private_event_ids=["e1"],
        known_roles={"p3": "seer"},
    )


def test_v2_sections_private_facts_speeches_votes():
    text, ids = render_observation_text_v2(_seer_obs(), EVENTS)
    # 分区标题齐全且顺序:私有 -> 公开 -> 发言 -> 投票
    i_priv, i_pub = text.index("【你的私有信息】"), text.index("【公开状态】")
    i_sp, i_vote = text.index("【发言记录】"), text.index("【投票记录】")
    assert i_priv < i_pub < i_sp < i_vote
    # 私有区含验人结果(seer 私有事件),且在私有区内;事件行保留 phase 标注(夜死/放逐可直读)
    assert "(r1 night) Seer p3 checks p1" in text[i_priv:i_pub]
    assert "(r1 day) p5 died during the night" in text[i_pub:i_sp]
    # 发言带说话人标签(修"无主语一坨")
    assert "p3: 我验了p1" in text and "p1: p3在说谎" in text
    # 投票矩阵按轮聚合
    assert "p3→p1" in text and "p1→p3" in text
    # source ids 覆盖全部被渲染事件
    assert set(ids) == {"e1", "e2", "e3", "e4", "e5", "e6", "e7"}


def test_v2_renders_only_visible_ids_hard_invariant():
    # "hidden" 在 events_by_id 里但不在 obs 的可见 id 列表 -> 内容/出处都不得出现
    text, ids = render_observation_text_v2(_seer_obs(), EVENTS)
    assert "hidden" not in ids
    assert "Wolf team kills" not in text


def test_v2_known_roles_only_others_and_empty_sections_omitted():
    obs = AgentObservation(
        game_id="g", player_id="p1", role="werewolf", team="werewolf", phase="night", round=1,
        alive_players=["p1", "p2", "p3", "p4", "p5", "p6"],
        public_event_ids=[], private_event_ids=[],
        known_roles={"p1": "werewolf", "p2": "werewolf"},
    )
    text, ids = render_observation_text_v2(obs, EVENTS)
    assert ids == []
    assert "p2=werewolf" in text          # 狼队友已知身份保留(与 v1 同语义)
    assert "【发言记录】" not in text      # 空区整段省略
    assert "【投票记录】" not in text


from werewolf_eval.llm_providers import (
    ChatProviderConfig,
    OpenAICompatibleProvider,
    build_speech_system_prompt,
    build_speech_system_prompt_v2,
)
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS, PROMPT_VERSION
from werewolf_eval.provider_contract import ProviderRequest


def _speech_req(**kw):
    base = dict(request_id="r", game_id="g", actor="p5", phase="day", round=1,
                observation={}, allowed_actions=[], allowed_targets=[],
                response_kind="speech")
    base.update(kw)
    return ProviderRequest(**base)


def test_known_versions_and_default_constant_unchanged():
    assert KNOWN_PROMPT_VERSIONS == ("prompt_v1", "prompt_v2")
    assert PROMPT_VERSION == "prompt_v1"   # 默认翻转是消融后的独立决策


def test_speech_v2_has_stance_and_discrimination_structure():
    text = build_speech_system_prompt_v2(_speech_req(prompt_version="prompt_v2"))
    assert "表态" in text and ("信或不信" in text or "信/不信" in text)
    assert "对跳" in text            # 判别结构,不是"相信预言家"新先验
    assert "相信预言家" not in text
    assert "JSON" in text            # 保留机器契约:不要输出 JSON
    assert "眼神" in text            # 反视觉幻觉


def test_system_for_selects_by_prompt_version_and_prepends_card():
    provider = OpenAICompatibleProvider(ChatProviderConfig(api_key="k", base_url="http://x", model="m"))
    # v1 默认请求:逐字节与改造前一致(无卡、v1 发言契约)
    v1 = provider._system_for(_speech_req())
    assert v1 == build_speech_system_prompt(_speech_req())
    # v2 发言请求:v2 契约
    v2 = provider._system_for(_speech_req(prompt_version="prompt_v2"))
    assert v2 == build_speech_system_prompt_v2(_speech_req(prompt_version="prompt_v2"))
    # 规则卡置顶(系统提示最前)
    carded = provider._system_for(_speech_req(prompt_version="prompt_v2", board_card="【本局规则卡】X"))
    assert carded.startswith("【本局规则卡】X\n\n")
    assert carded.endswith(v2)


def test_action_contract_unchanged_under_v2():
    from werewolf_eval.llm_providers import build_action_system_prompt
    a1 = _speech_req(response_kind="action", allowed_actions=["player_vote"], allowed_targets=["p1"])
    a2 = _speech_req(response_kind="action", allowed_actions=["player_vote"], allowed_targets=["p1"],
                     prompt_version="prompt_v2")
    provider = OpenAICompatibleProvider(ChatProviderConfig(api_key="k", base_url="http://x", model="m"))
    # v2 不改 action 机器契约(JSON 解析链零风险);只有卡会前置
    assert provider._system_for(a2) == build_action_system_prompt(a1)


def test_system_for_rejects_unknown_version():
    # 纵深防御:engine/harness 已有 KNOWN 硬门;provider 层对漏网的未知版本
    # 同样 fail-loud,绝不静默降级到 v1(无静默兜底原则)
    import pytest
    provider = OpenAICompatibleProvider(ChatProviderConfig(api_key="k", base_url="http://x", model="m"))
    with pytest.raises(ValueError, match="prompt_version"):
        provider._system_for(_speech_req(prompt_version="prompt_v99"))
