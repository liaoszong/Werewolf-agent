import json

from werewolf_eval.prompt_v3 import parse_scribe_claims, render_scribe_input

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
