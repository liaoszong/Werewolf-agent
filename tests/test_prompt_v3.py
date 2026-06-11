import json

from werewolf_eval.prompt_v3 import parse_scribe_claims, render_scribe_input, render_claim_digest, render_vote_scaffold

SPEECHES = [("p3", "我是预言家,昨晚验了p1,他是狼人。"),
            ("p1", "p3在悍跳,我才是真预言家,我验的p3是狼。"),
            ("p5", "我是普通村民,先听听。")]


def test_render_scribe_input_numbers_and_labels():
    text = render_scribe_input(1, SPEECHES)
    assert "第 1 轮" in text
    assert "1. p3:" in text and "2. p1:" in text and "3. p5:" in text


def test_parse_scribe_claims_happy_path():
    raw = json.dumps({"claims": [
        {"claimant": "p3", "claim_type": "check_report", "target": "p1", "result": "werewolf",
         "refutes": None, "source": 1, "source_quote": "昨晚验了p1,他是狼人", "uncertain": False},
        {"claimant": "p1", "claim_type": "refutation", "target": None, "result": None,
         "refutes": "p3", "source": 2, "source_quote": "p3在悍跳", "uncertain": False},
    ]}, ensure_ascii=False)
    claims = parse_scribe_claims(raw)
    assert len(claims) == 2
    assert claims[0]["claim_type"] == "check_report" and claims[0]["target"] == "p1"
    assert claims[1]["refutes"] == "p3"


def test_parse_scribe_claims_drops_invalid_entries_keeps_valid():
    # 宽进严出:缺必填字段(source_quote/uncertain/claimant/claim_type)的条目丢弃,不连坐
    raw = json.dumps({"claims": [
        {"claimant": "p3", "claim_type": "identity_claim", "target": None, "result": "seer",
         "refutes": None, "source": 1, "source_quote": "我是预言家", "uncertain": False},
        {"claimant": "p9", "claim_type": "check_report"},          # 缺 source_quote/uncertain -> 丢
        {"claim_type": "identity_claim", "source_quote": "x", "uncertain": True},  # 缺 claimant -> 丢
        {"claimant": "p1", "claim_type": "weird_type", "source_quote": "y", "uncertain": True},  # 非法类型 -> 丢
    ]}, ensure_ascii=False)
    claims = parse_scribe_claims(raw)
    assert len(claims) == 1 and claims[0]["claimant"] == "p3"


def test_parse_scribe_claims_failure_returns_none():
    assert parse_scribe_claims("not json") is None
    assert parse_scribe_claims(json.dumps({"no_claims_key": []})) is None
    assert parse_scribe_claims(json.dumps({"claims": "not-a-list"})) is None
    assert parse_scribe_claims(json.dumps({"claims": []})) == []   # 合法空=本轮无声称


CLAIMS = [
    {"round": 1, "claimant": "p3", "claim_type": "check_report", "target": "p1",
     "result": "werewolf", "refutes": None, "source": 1,
     "source_quote": "昨晚验了p1,他是狼人", "uncertain": False},
    {"round": 1, "claimant": "p1", "claim_type": "identity_claim", "target": None,
     "result": "seer", "refutes": None, "source": 2,
     "source_quote": "我才是真预言家", "uncertain": False},
    {"round": 1, "claimant": "p1", "claim_type": "refutation", "target": None,
     "result": None, "refutes": "p3", "source": 2,
     "source_quote": "p3在悍跳", "uncertain": True},
]


def test_digest_renders_claims_with_quotes_and_provenance_note():
    d = render_claim_digest(CLAIMS)
    assert d.startswith("【声称账本】")
    assert "由系统从公开发言提取" in d and "以原文为准" in d   # 非裁判事实定位
    assert "p3" in d and "报验 p1 → werewolf" in d
    assert "原文:" in d and "昨晚验了p1" in d                  # source_quote 必现
    assert "[不确定]" in d                                     # uncertain 标注
    assert "反驳 p3" in d                                      # 对跳/反驳关系
    assert render_claim_digest([]) == ""                       # 空账本 -> 空串


def test_vote_scaffold_has_digest_plus_comparison_program():
    s = render_vote_scaffold(CLAIMS)
    assert "【声称账本】" in s and "【投票前判断程序】" in s
    # 反协同护栏(spec §2.3)四条全在
    assert "不要因为出现对跳就自动否定先声称者" in s
    assert "不要因为第一天就声称预言家而自动判定是假冒" in s
    assert "相信预言家" not in s.replace("默认相信预言家", "")   # 不写"相信预言家"先验
    assert "可验证性" in s and "矛盾" in s and "发言与投票是否一致" in s
    # 空账本时:程序文字仍在,只是没有账本区
    s_empty = render_vote_scaffold([])
    assert "【投票前判断程序】" in s_empty and "【声称账本】" not in s_empty
    assert "本局到目前为止没有可记录的身份声称" in s_empty


# ------------------------------------------------------------------ Task 3 tests
from werewolf_eval.llm_providers import (
    ChatProviderConfig,
    OpenAICompatibleProvider,
    build_action_system_prompt,
    build_scribe_system_prompt,
    build_speech_system_prompt_v3,
)
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS
from werewolf_eval.provider_contract import ProviderRequest


def _req(actor="p5", phase="day", allowed_actions=None, allowed_targets=None, **kw):
    base = dict(request_id="r", game_id="g", actor=actor, phase=phase, round=1,
                observation={}, allowed_actions=allowed_actions or [],
                allowed_targets=allowed_targets or [], response_kind="speech")
    base.update(kw)
    return ProviderRequest(**base)


def test_known_versions_has_v3():
    assert KNOWN_PROMPT_VERSIONS == ("prompt_v1", "prompt_v2", "prompt_v3")


def test_scribe_system_prompt_extraction_not_judgment():
    text = build_scribe_system_prompt(_req(actor="scribe", response_kind="scaffold",
                                           prompt_version="prompt_v3"))
    assert "JSON" in text and "claims" in text
    assert "source_quote" in text and "uncertain" in text
    assert "identity_claim" in text and "check_report" in text and "refutation" in text
    # 提取非裁判:不许下判断
    assert "只负责提取" in text and "不要判断" in text


def test_speech_v3_is_restrained():
    text = build_speech_system_prompt_v3(_req(prompt_version="prompt_v3"))
    # 克制:中性发言要求 + 反视觉,无判别程序(spec §4:别教狼悍跳)
    assert "JSON" in text and "眼神" in text
    assert "对跳" not in text and "表态" not in text and "信或不信" not in text


def test_system_for_routes_scaffold_speech_v3_and_vote_unchanged():
    provider = OpenAICompatibleProvider(ChatProviderConfig(api_key="k", base_url="http://x", model="m"))
    # scaffold 分支
    sc = provider._system_for(_req(actor="scribe", response_kind="scaffold", prompt_version="prompt_v3"))
    assert sc == build_scribe_system_prompt(_req(actor="scribe", response_kind="scaffold", prompt_version="prompt_v3"))
    # v3 speech -> 克制版
    sp = provider._system_for(_req(prompt_version="prompt_v3"))
    assert sp == build_speech_system_prompt_v3(_req(prompt_version="prompt_v3"))
    # v3 action(vote)系统提示 = v1 action 契约原文(strict-JSON 一字不动,spec §0)
    a3 = _req(response_kind="action", allowed_actions=["player_vote"], allowed_targets=["p1"],
              prompt_version="prompt_v3")
    a1 = _req(response_kind="action", allowed_actions=["player_vote"], allowed_targets=["p1"])
    assert provider._system_for(a3) == build_action_system_prompt(a1)


# ------------------------------------------------------------------ Task 4 tests
import pytest
from fake_scribe import _FakeScribeProvider

from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.provider_agent import ProviderAgent


def _run_v3_engine(broken_scribe=False):
    agents = build_emergent_fake_agents(build_villager_win_script())
    scribe = ProviderAgent("scribe", _FakeScribeProvider(broken=broken_scribe))
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id="v3t"),
        agents=agents, seed=7,
        budget=EmergentBudget(max_requests=80, max_day_rounds=3),
        prompt_version="prompt_v3", scaffold_agent=scribe,
    )
    outcome = engine.run()
    return engine, outcome, agents, scribe


def test_v3_requires_scaffold_agent():
    agents = build_emergent_fake_agents(build_villager_win_script())
    with pytest.raises(ValueError, match="scaffold_agent"):
        EmergentGameEngine(config=build_emergent_config(game_id="v3_noscribe"),
                           agents=agents, seed=7, prompt_version="prompt_v3")


def test_scribe_runs_per_day_round_and_fills_ledger():
    engine, outcome, _, scribe = _run_v3_engine()
    assert outcome.completed
    assert len(scribe.provider.requests) >= 1          # 每个 day 轮 1 次
    req = scribe.provider.requests[0]
    assert req.response_kind == "scaffold"
    assert req.temperature == 0.0                      # 低温(spec §3 评审③)
    assert req.board_card == "" and req.persona_prompt == ""
    assert engine._claim_ledger and engine._claim_ledger[0]["claimant"] == "p3"
    assert all("round" in c for c in engine._claim_ledger)
    # scribe turn 口径:scaffold kind + live_requested=False
    sturns = [t for t in outcome.provider_turns if t.get("response_kind") == "scaffold"]
    assert sturns and all(t["kind"] == "scaffold_success" for t in sturns)
    assert all(t["live_requested"] is False for t in sturns)
    assert all(t["actor"] == "scribe" for t in sturns)


def test_scribe_all_broken_marks_fallback_and_completes():
    # 失败路径确定性覆盖(fake 脚本只有 1 个 day 轮,flaky 写法是死分支——评审修复):
    # 全程 broken -> 全部 scaffold_fallback、对局照常完成、账本为空
    engine, outcome, _, scribe = _run_v3_engine(broken_scribe=True)
    assert outcome.completed
    sturns = [t for t in outcome.provider_turns if t.get("response_kind") == "scaffold"]
    assert sturns and all(t["kind"] == "scaffold_fallback" for t in sturns)
    assert all(t["fallback_reason"] for t in sturns)
    assert engine._claim_ledger == []


def test_scribe_failure_preserves_history():
    # 历史保留语义(spec §3 评审修订②/§8.2)确定性单测:预填账本 -> broken scribe
    # 跑一轮 _run_scribe -> 旧 claims 原样还在(不依赖脚本天数)
    agents = build_emergent_fake_agents(build_villager_win_script())
    scribe = ProviderAgent("scribe", _FakeScribeProvider(broken=True))
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id="v3_hist"),
        agents=agents, seed=7,
        budget=EmergentBudget(max_requests=80, max_day_rounds=3),
        prompt_version="prompt_v3", scaffold_agent=scribe,
    )
    old = {"round": 0, "claimant": "p9", "claim_type": "identity_claim", "target": None,
           "result": "seer", "refutes": None, "source": 1,
           "source_quote": "历史条目", "uncertain": False}
    engine._claim_ledger.append(dict(old))
    engine._emit("day", 1, "player_speech", "p3", "none", "public", "测试发言。")
    engine._run_scribe(1)
    assert engine._claim_ledger == [old]               # 失败不清史
    assert engine._provider_turns[-1]["kind"] == "scaffold_fallback"
