# SYS-B4 Claim Ledger + Vote Scaffold (prompt_v3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec(`docs/superpowers/specs/2026-06-11-sys-b4-claim-ledger-vote-scaffold-design.md`,已过双审)的输入侧脚手架为 **prompt_v3**:每轮发言后 1 次 scribe 摘要调用(方案 C)→ 跨轮累积 Claim Ledger → digest 注入发言+投票、强比较程序只进投票;**action strict-JSON 契约一字不动**;v1/v2 字节不变;最后跑 b4 臂 45 局对照 baseline/b1。

**Architecture:** 新增纯函数模块 `prompt_v3.py`(scribe 输入渲染/claim 解析/digest/vote scaffold,不 import engine);scribe 系统提示与 v3 发言提示放 `llm_providers.py`(`_system_for` 加 scaffold 分支,additive);engine 加 `_claim_ledger` 状态 + `_run_scribe`(独立 scaffold_agent,请求级 temperature=0,`live_requested=False`)+ day 流程插入 + v3 注入点(speech 尾加 digest、vote 尾加 scaffold);runner 加 `scaffold_provider_factory`;metrics 改 live 率玩家口径 + `scaffold_coverage` 臂纯度门 + 失败链指标。

**Tech Stack:** Python 3、pytest、既有 golden/ledger/不变量/消融臂基建。无新依赖。

---

## 验收硬门 = spec §8 双审合并清单(10 条)
本 plan 每条都有对应 Task(映射见 Self-Review);执行者与 reviewer 以 spec §8 为最终验收依据。

## 已核实的代码事实(免重查)
- **Day 流程插入点**:`emergent_engine.py:1093-1096` — `for speaker in ...: self._resolve_speech(speaker, rnd)` 之后、`eliminated = self._RESOLVERS["player_vote"](rnd)` 之前。
- **vote 请求路径**:`_run_vote_round`(:669)→ `_run_single_turn(VoteResolver(), voter, role, "day_vote", "day", "day", rnd)`(:674)→ `_provider_action(actor, "day", rnd)`(:637)。**`_provider_action` 内 `phase=="day"` ⇔ vote 请求**(夜间动作 phase=="night";hunter 走独立 `_resolve_hunter_shot`)——干净判别子,v3 vote scaffold 注入用它。
- **`_provider_action`**(:554 起):`rendered = self._render_obs(obs)` 后构造 turn dict、`assert_prompt_entitled`、`agent.decide(obs, observation_text=rendered.text, ...)`。speech 同构(`_resolve_speech` :869 起,直接构造 ProviderRequest)。
- **`ProviderRequest.temperature` 已存在且请求级覆盖 config**(`provider_contract.py:38`,`_effective_temperature` :178)→ **scribe 低温零 provider-config 改动**,请求带 `temperature=0.0` 即可。
- **`_build_payload`**(llm_providers:288):`response_kind != "speech"` 即带 `response_format={"type":"json_object"}` → scaffold 请求自动拿 JSON mode,正合需。
- **`_system_for`**(llm_providers:213):现有 unknown-version 硬门 + speech v1/v2 分支 + else action + board_card 前缀。scaffold 分支插在 kind 判断最前。
- **`KNOWN_PROMPT_VERSIONS = ("prompt_v1","prompt_v2")`**(prompt_version.py)——加 `"prompt_v3"`;**注意 `tests/test_prompt_v2.py::test_known_versions_and_default_constant_unchanged` 钉死了二元组,该测试须同步更新为三元组**(这是预期更新,不是回归)。
- **runner**:`run_emergent_deepseek_game(..., prompt_version="prompt_v1")`(:138);`_collect_trace(game_id, agents, ...)` 汇总 agents 的 provider 请求/响应;`_provider_turns_summary`(:109)`live_success_rate = live_success / live_requested`(live_requested 计数只数 `live_requested=True` 的 turn)→ **scribe turn 带 `live_requested=False` 则 runner 口径自动不被稀释**;metrics 的 `live_rate_from_turns` 分母是 `len(turns)` 全量 → **必须显式排除 scaffold turns**(spec §5.2)。
- **engine ctor**(:248):`prompt_version` KNOWN 硬门 + `self._board_card`(v2 算卡)在 :296-305;`_render_obs` :515。
- **fake 测试配方**:`build_emergent_fake_agents(build_villager_win_script())` 提供 6 座位 fake agents;scribe 的 fake 用本 plan 给的 `_FakeScribeProvider` stub(测试文件内,canned JSON)。
- 测试约定:`NO_PROXY='*' PYTHONPATH=src python -m pytest ... -q`。当前全量 **1056 passed, 2 skipped**。

## 设计决策(spec 已裁决 + plan 固化)
1. **scribe 不是玩家**:engine 持 `self._scaffold_agent`(独立 ProviderAgent,pid="scribe"),v3 必须提供否则 ctor ValueError(无静默无脚手架 v3);scribe turn 计入 budget.charge() 但 `live_requested=False`、kind ∈ {`scaffold_success`,`scaffold_fallback`}。
2. **claim dict 形状**(spec §3):`{"round": int, "claimant": "pX", "claim_type": "identity_claim"|"check_report"|"refutation", "target": "pX"|None, "result": str|None, "refutes": "pX"|None, "source": int(发言序号), "source_quote": str(必填), "uncertain": bool(必填)}`;`confidence` 可选不依赖。解析器丢弃缺必填字段的条目(宽进严出,提取非裁判)。
3. **v3 渲染 = v2 结构化观察(复用 `render_observation_text_v2`,零拷贝)+ 注入**:speech 请求尾加 `render_claim_digest`;vote 请求尾加 `render_vote_scaffold`(= digest + 固定比较程序文字);夜间动作不注入(spec 范围)。digest 内容全部源自公开发言事件 → I4b 天然干净,但注入文本的 source_event_ids 须并入 rendered.source_event_ids(claim 带 `source_event_id` 字段,见 Task 4 注)。
4. **guidance 分级**(spec §4):v3 speech 系统提示=克制版(中性发言要求+反视觉/反机制,无判别程序);比较程序+反协同护栏全部在 `render_vote_scaffold` 的固定文字里(observation 侧,不碰 action 系统提示)。
5. **臂纯度**(spec §5.2b/§6):per-game `scaffold_coverage = scaffold_success / scaffold_attempts`(非 v3 局 attempts=0 → None);有效局 = live≥0.7(玩家口径)且 (coverage is None or ≥0.5);`n_invalid_scaffold` 单列。

## 文件结构
- Create `src/werewolf_eval/prompt_v3.py` — 纯函数:`render_scribe_input`、`parse_scribe_claims`、`render_claim_digest`、`render_vote_scaffold`、常量 `SCRIBE_MAX_OUTPUT_TOKENS=400`。不 import engine/llm_providers。
- Modify `src/werewolf_eval/prompt_version.py` — KNOWN 加 `"prompt_v3"`。
- Modify `src/werewolf_eval/llm_providers.py` — `build_scribe_system_prompt`、`build_speech_system_prompt_v3`、`_system_for` scaffold 分支 + v3 speech 选择。
- Modify `src/werewolf_eval/emergent_engine.py` — `scaffold_agent` ctor 参数、`_claim_ledger`、`_run_scribe`、day 流程插入、speech/vote 注入、`_render_obs`/board card 扩 v3。
- Modify `src/werewolf_eval/run_emergent_deepseek_game.py` — `scaffold_provider_factory` 参数、trace 合并、turns 汇总分列。
- Modify `src/werewolf_eval/ablation/metrics.py` — live 率玩家口径、`scaffold_coverage`、`n_invalid_scaffold`、`verify_seer_voted_out`/`seer_voted_out_in_verify_cases`。
- Modify `src/werewolf_eval/ablation/harness.py` — v3 臂的 scaffold factory。
- Modify `src/werewolf_eval/prompt_goldens.py` + `tools/generate_golden_prompts.py` + `tests/test_prompt_versioning.py` + ledger — v3 golden 三类样本。
- Tests: `tests/test_prompt_v3.py`(新)、`tests/test_prompt_v3_invariants.py`(新)、改 `tests/test_prompt_v2.py`(KNOWN 三元组)、`tests/test_ablation_metrics.py`、`tests/test_ablation_harness_fake.py`。

---

### Task 1: `prompt_v3.py` — scribe 输入渲染 + claim 解析器

**Files:**
- Create: `src/werewolf_eval/prompt_v3.py`
- Test: `tests/test_prompt_v3.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_prompt_v3.py
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q`
Expected: FAIL (ModuleNotFoundError: werewolf_eval.prompt_v3)

- [ ] **Step 3: 写实现**

```python
# src/werewolf_eval/prompt_v3.py
"""prompt_v3 (SYS-B4 Claim Ledger + Vote Scaffold): pure functions for the scribe
extraction artifact and its injection texts. NO engine / llm_providers import
(the engine and provider layer import US). Spec:
docs/superpowers/specs/2026-06-11-sys-b4-claim-ledger-vote-scaffold-design.md.
Hard constraint (spec §0): input-side scaffold only; the action strict-JSON
contract is untouched — everything here lands in observation_text or the
scribe's OWN scaffold request."""
from __future__ import annotations

import json
from typing import Any

SCRIBE_MAX_OUTPUT_TOKENS = 400

CLAIM_TYPES = ("identity_claim", "check_report", "refutation")
# spec §3: source_quote + uncertain are REQUIRED; confidence optional (unused v1).
_REQUIRED_FIELDS = ("claimant", "claim_type", "source_quote", "uncertain")


def render_scribe_input(rnd: int, speeches: list[tuple[str, str]]) -> str:
    """Scribe user message: THIS round's labeled public speeches, numbered so
    claims can reference their source by index."""
    lines = [f"第 {rnd} 轮白天发言记录(按发言顺序):"]
    for i, (speaker, text) in enumerate(speeches, start=1):
        lines.append(f"{i}. {speaker}: {text}")
    return "\n".join(lines)


def parse_scribe_claims(raw_content: str) -> list[dict[str, Any]] | None:
    """Parse the scribe's JSON. Returns None on malformed response (-> this
    round adds nothing; the cross-round ledger is PRESERVED, spec §3 评审修订②).
    Individually invalid entries are dropped, valid ones kept (extraction, not
    adjudication — a bad entry must not poison the round)."""
    try:
        doc = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("claims"), list):
        return None
    out: list[dict[str, Any]] = []
    for c in doc["claims"]:
        if not isinstance(c, dict):
            continue
        if any(f not in c or c[f] is None for f in _REQUIRED_FIELDS):
            continue
        if c["claim_type"] not in CLAIM_TYPES:
            continue
        out.append({
            "claimant": str(c["claimant"]),
            "claim_type": c["claim_type"],
            "target": c.get("target"),
            "result": c.get("result"),
            "refutes": c.get("refutes"),
            "source": c.get("source"),
            "source_quote": str(c["source_quote"]),
            "uncertain": bool(c["uncertain"]),
        })
    return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/prompt_v3.py tests/test_prompt_v3.py
git commit -m "feat(prompt-v3): scribe input renderer + lenient-strict claim parser (SYS-B4)"
```

---

### Task 2: `prompt_v3.py` — claim digest + vote scaffold 渲染

**Files:**
- Modify: `src/werewolf_eval/prompt_v3.py`
- Test: `tests/test_prompt_v3.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_prompt_v3.py
from werewolf_eval.prompt_v3 import render_claim_digest, render_vote_scaffold

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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q`
Expected: FAIL (ImportError: render_claim_digest)

- [ ] **Step 3: 写实现**(追加到 prompt_v3.py)

```python
_CLAIM_LINE = {
    "identity_claim": lambda c: f"声称自己是 {c.get('result') or '?'}",
    "check_report": lambda c: f"报验 {c.get('target') or '?'} → {c.get('result') or '?'}",
    "refutation": lambda c: f"反驳 {c.get('refutes') or '?'}",
}

VOTE_PROGRAM = (
    "【投票前判断程序】\n"
    "对上面的声称,逐条比较后再决定投票,而不是默认相信或默认怀疑:\n"
    "1. 可验证性:声称内容能否与公开事实(死亡/出局/翻牌/票史)对上?有没有矛盾?\n"
    "2. 对跳关系:若多人声称同一身份,至多一人为真;比较各自报点的具体性与一致性。\n"
    "3. 发言与投票是否一致:声称者过往投票是否符合其声称身份的利益?\n"
    "护栏:不要因为出现对跳就自动否定先声称者;不要因为第一天就声称预言家而自动判定是假冒;"
    "不要默认相信预言家声称——用上面三条比较,选出对你阵营最优的一票。"
)


def render_claim_digest(claims: list[dict[str, Any]]) -> str:
    """【声称账本】 section. Every line carries the verbatim source_quote so an
    extraction error is self-evident (spec §3: 辅助提取,非裁判事实). Empty
    ledger -> "" (sections are omitted entirely, matching the v2 convention)."""
    if not claims:
        return ""
    lines = ["【声称账本】(由系统从公开发言提取,可能不完全,以原文为准)"]
    for c in claims:
        desc = _CLAIM_LINE.get(c["claim_type"], lambda _: c["claim_type"])(c)
        mark = "[不确定]" if c.get("uncertain") else ""
        lines.append(f"- (r{c.get('round')}) {c['claimant']} {desc}{mark}(原文:\"{c['source_quote']}\")")
    return "\n".join(lines)


def render_vote_scaffold(claims: list[dict[str, Any]]) -> str:
    """Vote-request-ONLY injection (spec §4 分级:vote 强 / speech 克制):
    digest + the fixed comparison program. Lands in observation_text — the
    action system prompt / strict-JSON contract is untouched (spec §0)."""
    digest = render_claim_digest(claims)
    if digest:
        return f"{digest}\n{VOTE_PROGRAM}"
    return f"本局到目前为止没有可记录的身份声称。\n{VOTE_PROGRAM}"
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/prompt_v3.py tests/test_prompt_v3.py
git commit -m "feat(prompt-v3): claim digest + vote scaffold with anti-coordination program (SYS-B4 2.2/2.3)"
```

---

### Task 3: provider 层 — scribe 系统提示 + v3 克制发言提示 + `_system_for` scaffold 分支

**Files:**
- Modify: `src/werewolf_eval/prompt_version.py`
- Modify: `src/werewolf_eval/llm_providers.py`
- Modify: `tests/test_prompt_v2.py`(KNOWN 三元组,预期更新)
- Test: `tests/test_prompt_v3.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_prompt_v3.py
from werewolf_eval.llm_providers import (
    ChatProviderConfig,
    OpenAICompatibleProvider,
    build_action_system_prompt,
    build_scribe_system_prompt,
    build_speech_system_prompt_v3,
)
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS
from werewolf_eval.provider_contract import ProviderRequest


def _req(**kw):
    base = dict(request_id="r", game_id="g", actor="p5", phase="day", round=1,
                observation={}, allowed_actions=[], allowed_targets=[],
                response_kind="speech")
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
```

并修改 `tests/test_prompt_v2.py::test_known_versions_and_default_constant_unchanged`:断言改为 `KNOWN_PROMPT_VERSIONS == ("prompt_v1", "prompt_v2", "prompt_v3")`(`PROMPT_VERSION == "prompt_v1"` 断言保留不动)。

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q`
Expected: FAIL (ImportError: build_scribe_system_prompt)

- [ ] **Step 3: 写实现**

`prompt_version.py`:`KNOWN_PROMPT_VERSIONS = ("prompt_v1", "prompt_v2", "prompt_v3")`(注释补一句 prompt_v3 = SYS-B4 scaffold)。

`llm_providers.py` — 在 `build_speech_system_prompt_v2` 之后追加两个构建器:

```python
def build_speech_system_prompt_v3(request: ProviderRequest) -> str:
    # SYS-B4 §4 graded guidance: speech stays RESTRAINED (the b1 lesson — handing
    # the discrimination program to every seat armed wolf fake-claims). Neutral
    # speech requirements + anti-visual/anti-mechanic line only; the comparison
    # program ships ONLY in the vote scaffold (observation side).
    return (
        f"你是狼人杀里的 {request.actor}(第 {request.round} 轮,白天发言)。"
        f"请用自然口吻发言,3-5 句或 120-180 字,不要固定小标题,不要输出 JSON,直接说话。"
        f"发言应包含:当前局势判断、你怀疑或相信的对象、一个具体理由、本轮投票倾向。"
        f"局内不存在表情、眼神、语气等信息,也没有警长、守卫等本局规则卡之外的机制,不要编造。"
    )


def build_scribe_system_prompt(request: ProviderRequest) -> str:
    # SYS-B4 §3 scheme C: the scribe is an EXTRACTION artifact, not a judge.
    # Strict JSON (the scaffold request rides response_format=json_object).
    return (
        "你是狼人杀对局的书记员。你只负责提取,不要判断真假、不要推理谁是狼。"
        "从下面带编号的发言记录中提取所有身份声称、查验报告与反驳,输出 JSON:"
        '{"claims":[{"claimant":"pX","claim_type":"identity_claim|check_report|refutation",'
        '"target":"pX或null","result":"身份或查验结果或null","refutes":"pX或null",'
        '"source":发言编号,"source_quote":"原文片段","uncertain":true或false}]}。'
        "规则:claimant 必须是发言者本人;source_quote 必须是该发言的原文片段;"
        "提取不到明确声称就输出 {\"claims\":[]};语义含糊时照常提取但把 uncertain 设为 true。"
        "不要输出 JSON 以外的任何内容。"
    )
```

`_system_for` 改为(scaffold 分支在最前;v3 speech 选择;其余不动):

```python
    def _system_for(self, request: ProviderRequest) -> str:
        if request.prompt_version not in KNOWN_PROMPT_VERSIONS:
            raise ValueError(
                f"unknown prompt_version {request.prompt_version!r}; known: {KNOWN_PROMPT_VERSIONS}"
            )
        if request.response_kind == "scaffold":
            contract = build_scribe_system_prompt(request)
        elif request.response_kind == "speech":
            if request.prompt_version == "prompt_v3":
                contract = build_speech_system_prompt_v3(request)
            elif request.prompt_version == "prompt_v2":
                contract = build_speech_system_prompt_v2(request)
            else:
                contract = build_speech_system_prompt(request)
        else:
            contract = build_action_system_prompt(request)
        composed = compose_system(self._effective_persona(request), contract)
        if request.board_card:
            return f"{request.board_card}\n\n{composed}"
        return composed
```

> 注:scaffold 请求 `response_kind != "speech"` → `_build_payload` 自动带 `response_format=json_object`(已核),正合 scribe 需要;scaffold 不吃 persona/board_card(engine 侧两者都传空,Task 4)。

- [ ] **Step 4: 跑测试 + v1/v2 字节守卫**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py tests/test_prompt_v2.py tests/test_prompt_versioning.py -q`
Expected: PASS(v3 新测试 + v2 全量 + golden 守卫全绿 = v1/v2 字节没动)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/prompt_version.py src/werewolf_eval/llm_providers.py tests/test_prompt_v3.py tests/test_prompt_v2.py
git commit -m "feat(prompt-v3): scribe system prompt + restrained speech v3 + _system_for scaffold branch (additive, v1/v2 bytes intact)"
```

---

### Task 4: engine — ClaimLedger + `_run_scribe` + day 流程插入

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py`
- Test: `tests/test_prompt_v3.py`

- [ ] **Step 1: 写失败测试**(fake scribe stub 在测试文件内)

```python
# 追加到 tests/test_prompt_v3.py
import pytest

from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.provider_contract import ProviderResponse


class _FakeScribeProvider:
    """Canned scribe: returns a fixed claims JSON (or garbage when broken=True).
    Mimics the BaseChatProvider surface the engine touches (respond/model/requests)."""

    uses_baseline_prompt = False
    provider_runtime_kind = "deterministic_fake"

    def __init__(self, broken=False):
        self.broken = broken
        self.requests = []
        self.responses = []
        self.model = "none"

    def respond(self, request):
        self.requests.append(request)
        content = "GARBAGE" if self.broken else (
            '{"claims":[{"claimant":"p3","claim_type":"identity_claim","target":null,'
            '"result":"seer","refutes":null,"source":1,"source_quote":"测试声称","uncertain":false}]}'
        )
        resp = ProviderResponse(request_id=request.request_id, provider_name="fake_scribe",
                                source_label="[deterministic fake provider output]",
                                raw_content=content, latency_ms=0,
                                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        self.responses.append(resp)
        return resp


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


def test_scribe_failure_preserves_history_and_marks_fallback():
    # 第一轮成功、之后 broken:历史账本必须保留(spec §3 评审修订②)
    agents = build_emergent_fake_agents(build_villager_win_script())
    scribe_provider = _FakeScribeProvider()
    orig_respond = scribe_provider.respond
    calls = {"n": 0}
    def flaky(request):
        calls["n"] += 1
        scribe_provider.broken = calls["n"] >= 2
        return orig_respond(request)
    scribe_provider.respond = flaky
    scribe = ProviderAgent("scribe", scribe_provider)
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id="v3_flaky"),
        agents=agents, seed=7,
        budget=EmergentBudget(max_requests=80, max_day_rounds=3),
        prompt_version="prompt_v3", scaffold_agent=scribe,
    )
    outcome = engine.run()
    if calls["n"] >= 2:   # 多于一个 day 轮才有失败样本
        sturns = [t for t in outcome.provider_turns if t.get("response_kind") == "scaffold"]
        assert any(t["kind"] == "scaffold_fallback" for t in sturns)
    assert engine._claim_ledger                        # 第一轮的 claim 还在
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q`
Expected: FAIL (TypeError: unexpected keyword argument 'scaffold_agent')

- [ ] **Step 3: 写实现**(`emergent_engine.py`)

(a) imports 追加:

```python
from werewolf_eval.prompt_v3 import (
    SCRIBE_MAX_OUTPUT_TOKENS,
    parse_scribe_claims,
    render_claim_digest,
    render_scribe_input,
    render_vote_scaffold,
)
```

常量区(LIVE_SUCCESS 等旁边)追加:

```python
SCAFFOLD_SUCCESS = "scaffold_success"
SCAFFOLD_FALLBACK = "scaffold_fallback"
```

(b) `__init__` 签名加 `scaffold_agent: Any | None = None`(`prompt_version` 之后);版本门块之后追加:

```python
        # SYS-B4: the scribe is NOT a player. prompt_v3 REQUIRES it (no silent
        # scaffold-less v3); other versions ignore it.
        self._scaffold_agent = scaffold_agent
        if prompt_version == "prompt_v3" and scaffold_agent is None:
            raise ValueError("prompt_v3 requires a scaffold_agent (scribe provider)")
        # Cross-round claim ledger; scribe failures NEVER clear it (spec §3 ②).
        self._claim_ledger: list[dict[str, Any]] = []
```

board card 条件从 `if prompt_version == "prompt_v2":` 改为 `if prompt_version in ("prompt_v2", "prompt_v3"):`。

(c) `_render_obs` 条件同步:`if self.prompt_version in ("prompt_v2", "prompt_v3"):`(v3 复用 v2 结构化渲染)。

(d) 新方法(放 `_resolve_speech` 之后):

```python
    def _run_scribe(self, rnd: int) -> None:
        """SYS-B4 scheme C: one extraction call per day round, AFTER speeches and
        BEFORE the vote. Budget-charged; recorded as a scaffold turn with
        live_requested=False (never dilutes player live_success_rate). A failed
        round adds nothing — the cross-round ledger is preserved."""
        speeches = [(e["actor"], e["data"]["summary"]) for e in self._events
                    if e["type"] == "player_speech" and e["round"] == rnd]
        if not speeches:
            return
        self._budget.charge()
        provider = self._scaffold_agent.provider
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_scribe",
            game_id=self._game_id, actor="scribe", phase="day", round=rnd,
            observation={}, allowed_actions=[], allowed_targets=[],
            observation_text=render_scribe_input(rnd, speeches),
            response_kind="scaffold", max_output_tokens=SCRIBE_MAX_OUTPUT_TOKENS,
            temperature=0.0,                       # extraction task: kill nondeterminism
            prompt_version=self.prompt_version, board_card="",
        )
        turn: dict[str, Any] = {
            "request_id": request.request_id, "round": rnd, "phase": "day", "actor": "scribe",
            "response_kind": "scaffold", "live_requested": False, "kind": None,
            "fallback_reason": None, "source_label": None,
            "model": getattr(provider, "model", None), "token_usage": None,
            "observation_source_event_ids": [],
        }
        self._provider_turns.append(turn)
        claims = None
        try:
            response = provider.respond(request)
            turn["source_label"] = response.source_label
            turn["token_usage"] = dict(response.token_usage)
            claims = parse_scribe_claims(response.raw_content or "")
        except Exception as exc:  # noqa: BLE001 - scaffold is non-adjudicating; never abort
            turn["fallback_reason"] = f"scribe provider error: {exc}"
        if claims is None:
            turn["kind"] = SCAFFOLD_FALLBACK
            if not turn["fallback_reason"]:
                turn["fallback_reason"] = "scribe output unparseable"
            turn["source_label"] = None
            turn["token_usage"] = None
            return                                  # history PRESERVED (spec §3 ②)
        turn["kind"] = SCAFFOLD_SUCCESS
        for c in claims:
            c["round"] = rnd
        self._claim_ledger.extend(claims)
```

(e) day 流程插入(:1094 发言循环之后、:1096 投票之前):

```python
            if self.prompt_version == "prompt_v3":
                self._run_scribe(rnd)
```

- [ ] **Step 4: 跑测试 + 全量回归**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q` → PASS (13 passed)
Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q` → 全绿(v1/v2 路径零改动;若有 fail 原样报告勿自行"修")

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_prompt_v3.py
git commit -m "feat(prompt-v3): claim ledger + per-round scribe call (budget-charged, live_requested=False, history-preserving fallback)"
```

---

### Task 5: engine — v3 注入(speech 尾加 digest、vote 尾加 scaffold)

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py`
- Test: `tests/test_prompt_v3.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_prompt_v3.py

def test_v3_vote_requests_carry_scaffold_and_speech_carry_digest():
    _, outcome, agents, _ = _run_v3_engine()
    reqs = [r for a in agents.values() for r in a.provider.requests]
    votes = [r for r in reqs if r.response_kind == "action" and r.phase == "day"]
    nights = [r for r in reqs if r.response_kind == "action" and r.phase == "night"]
    speeches = [r for r in reqs if r.response_kind == "speech"]
    assert votes and nights and speeches
    # vote:scaffold 程序必在;r1 投票在 r1 scribe 之后 -> 账本也在
    assert all("【投票前判断程序】" in r.observation_text for r in votes)
    assert any("【声称账本】" in r.observation_text for r in votes)
    # speech:r1 发言在任何 scribe 之前 -> 无账本;r2+ 发言带 r1 账本(若到 r2)
    r1_speech = [r for r in speeches if r.round == 1]
    assert all("【声称账本】" not in r.observation_text for r in r1_speech)
    r2_speech = [r for r in speeches if r.round >= 2]
    if r2_speech:
        assert any("【声称账本】" in r.observation_text for r in r2_speech)
    # speech 不带强比较程序(分级:vote 强 / speech 克制)
    assert all("【投票前判断程序】" not in r.observation_text for r in speeches)
    # 夜间动作不注入
    assert all("【声称账本】" not in r.observation_text and "【投票前判断程序】" not in r.observation_text
               for r in nights)
    # 全部请求仍是 v2 结构化观察打底 + 带卡
    assert all("【你的私有信息】" in r.observation_text for r in votes + speeches)
    assert all(r.board_card.startswith("【本局规则卡】") for r in votes + speeches + nights)


def test_v2_and_v1_paths_have_no_v3_injection():
    from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
    for ver in ("prompt_v1", "prompt_v2"):
        agents = build_emergent_fake_agents(build_villager_win_script())
        engine = EmergentGameEngine(config=build_emergent_config(game_id=f"nov3_{ver}"),
                                    agents=agents, seed=7,
                                    budget=EmergentBudget(max_requests=80, max_day_rounds=3),
                                    prompt_version=ver)
        engine.run()
        reqs = [r for a in agents.values() for r in a.provider.requests]
        assert all("【投票前判断程序】" not in r.observation_text for r in reqs)
        assert all("【声称账本】" not in r.observation_text for r in reqs)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py::test_v3_vote_requests_carry_scaffold_and_speech_carry_digest -q`
Expected: FAIL(votes 无程序文字)

- [ ] **Step 3: 写实现**(`emergent_engine.py`,两处注入)

`_provider_action`:`rendered = self._render_obs(obs)` 之后、turn dict 之前插入:

```python
        obs_text = rendered.text
        if self.prompt_version == "prompt_v3" and phase == "day":
            # vote request (the only day-phase action path; hunter uses its own
            # site): inject digest + comparison program. Input-side ONLY — the
            # action system prompt / strict-JSON contract is untouched (spec §0).
            obs_text = f"{obs_text}\n{render_vote_scaffold(self._claim_ledger)}"
```

并把后面 `agent.decide(obs, observation_text=rendered.text, ...)` 改为 `observation_text=obs_text`。

`_resolve_speech`:`rendered = self._render_obs(obs)` 之后同构:

```python
        obs_text = rendered.text
        if self.prompt_version == "prompt_v3" and self._claim_ledger:
            # graded guidance: speeches get the DIGEST only (information symmetry),
            # never the comparison program (b1 lesson: don't arm wolf fake-claims).
            obs_text = f"{obs_text}\n{render_claim_digest(self._claim_ledger)}"
```

并把该函数 ProviderRequest 的 `observation_text=rendered.text` 改为 `observation_text=obs_text`。

> 注(I4b):digest/scaffold 内容全部派生自公开 `player_speech` 事件,且这些事件已在该 seat 的可见集与 `rendered.source_event_ids` 里(公开发言人人可见)——注入不引入新事件来源,`assert_prompt_entitled` 调用保持原样、必须全绿(Task 9 的不变量 e2e 是硬验收)。witch(night)与 hunter(独立 site)不注入,代码不动。

- [ ] **Step 4: 跑测试 + 全量**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q` → PASS (15 passed)
Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q` → 全绿

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_prompt_v3.py
git commit -m "feat(prompt-v3): digest into speeches, vote scaffold into vote requests only (graded guidance, input-side)"
```

---

### Task 6: runner — `scaffold_provider_factory` + trace 合并 + turns 分列

**Files:**
- Modify: `src/werewolf_eval/run_emergent_deepseek_game.py`
- Test: `tests/test_prompt_v3.py`

- [ ] **Step 1: 先读现状**
读 `run_emergent_deepseek_game.py` 全函数与 `_collect_trace`/`_provider_turns_summary`,确认 trace 合并的最小改法(scribe agent 并入 collect 的 agents dict;`_provider_identity` 对混入 scribe 的行为——若它据 agents 推导身份,合并 dict 只用于 _collect_trace 调用处,不影响身份推导)。

- [ ] **Step 2: 写失败测试**

```python
# 追加到 tests/test_prompt_v3.py
import json as _json

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game


def _fake_factory():
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


def _fake_scaffold_factory():
    return ProviderAgent("scribe", _FakeScribeProvider())


def test_runner_v3_threads_scribe_and_splits_turn_accounting(tmp_path):
    run_emergent_deepseek_game(
        game_id="v3_runner", out_dir=tmp_path, provider_factory=_fake_factory(),
        model="none", seed=7, max_requests_per_game=80, max_day_rounds=3,
        prompt_version="prompt_v3", scaffold_provider_factory=_fake_scaffold_factory,
    )
    manifest = _json.loads((tmp_path / "prompt-manifest.json").read_text(encoding="utf-8"))
    assert manifest["evaluation_bucket"]["prompt_version"] == "prompt_v3"
    turns_doc = _json.loads((tmp_path / "provider-turns.json").read_text(encoding="utf-8"))
    # 分列口径(spec §8.4):player vs scaffold
    assert turns_doc["scaffold_requests"] >= 1
    assert turns_doc["player_requests"] == turns_doc["live_requested_actions"]
    # 玩家 live 率不被 scribe 稀释:live_requested 口径不含 scaffold turn
    sturns = [t for t in turns_doc["turns"] if t.get("response_kind") == "scaffold"]
    assert sturns and all(t["live_requested"] is False for t in sturns)
    # trace 单列:scribe 的请求进 provider-trace,actor=scribe
    trace = _json.loads((tmp_path / "provider-trace.json").read_text(encoding="utf-8"))
    assert any(r.get("actor") == "scribe" for r in trace["requests"])


def test_runner_v3_without_scaffold_factory_fails_loud(tmp_path):
    with pytest.raises(ValueError, match="scaffold"):
        run_emergent_deepseek_game(
            game_id="v3_noscribe", out_dir=tmp_path, provider_factory=_fake_factory(),
            model="none", seed=7, prompt_version="prompt_v3",
        )
```

- [ ] **Step 3: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py -q`
Expected: FAIL (TypeError: unexpected keyword argument 'scaffold_provider_factory')

- [ ] **Step 4: 写实现**(`run_emergent_deepseek_game.py`)

- 签名加 `scaffold_provider_factory=None`(`prompt_version` 之后;类型注释 `Callable[[], Any] | None`,沿用文件内既有 typing 风格)。
- 函数体开头(writer 之前):

```python
    scaffold_agent = None
    if prompt_version == "prompt_v3":
        if scaffold_provider_factory is None:
            raise ValueError("prompt_v3 requires scaffold_provider_factory (scribe provider)")
        scaffold_agent = scaffold_provider_factory()
```

- engine 构造追加 `scaffold_agent=scaffold_agent`。
- trace 收集:`_collect_trace(game_id, agents, ...)` 调用处把 agents 换成 `{**agents, "scribe": scaffold_agent} if scaffold_agent is not None else agents`(只影响 trace 汇总;`_provider_identity(agents)` 调用维持原 agents 不动——身份推导只看玩家座位)。
- `_provider_turns_summary` 追加两个 additive 字段(函数内 return dict):

```python
        "player_requests": live_requested,
        "scaffold_requests": sum(1 for t in turns if t.get("response_kind") == "scaffold"),
```

(`live_requested` 变量已有;scaffold turn 的 `live_requested=False` 保证两口径不重叠。)

- [ ] **Step 5: 跑测试 + 全量 → 提交**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v3.py tests/ -q` → 全绿

```bash
git add src/werewolf_eval/run_emergent_deepseek_game.py tests/test_prompt_v3.py
git commit -m "feat(prompt-v3): runner scaffold_provider_factory + scribe trace merge + player/scaffold turn split"
```

---

### Task 7: metrics — live 率玩家口径 + `scaffold_coverage` 臂纯度门

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py`
- Test: `tests/test_ablation_metrics.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_ablation_metrics.py
from werewolf_eval.ablation.metrics import scaffold_coverage_from_turns

def test_live_rate_excludes_scaffold_turns():
    # spec §8.1 钉死测试:scribe turns 不得稀释玩家 live 率
    turns = [{"kind": "live_success"}] * 9 + [{"kind": "timeout_then_fallback"}] \
          + [{"kind": "scaffold_success", "response_kind": "scaffold"}] * 3 \
          + [{"kind": "scaffold_fallback", "response_kind": "scaffold"}]
    assert live_rate_from_turns({"turns": turns}) == 0.9      # 9/10,不是 9/14

def test_scaffold_coverage_from_turns():
    turns = [{"kind": "scaffold_success", "response_kind": "scaffold"},
             {"kind": "scaffold_fallback", "response_kind": "scaffold"},
             {"kind": "live_success"}]
    assert scaffold_coverage_from_turns({"turns": turns}) == 0.5
    assert scaffold_coverage_from_turns({"turns": [{"kind": "live_success"}]}) is None  # 非 v3 局

def test_aggregate_gates_low_scaffold_coverage(tmp_path):
    import json, shutil
    # 用真 fixture 复制一份,再伪造 scaffold turns:1 成功 3 失败 -> coverage 0.25 < 0.5
    src = FIX / "diag_A_seer_p2_3"
    bad = tmp_path / "low_cov"; shutil.copytree(src, bad)
    doc = json.loads((bad / "provider-turns.json").read_text(encoding="utf-8"))
    doc["turns"] += [{"kind": "scaffold_success", "response_kind": "scaffold", "live_requested": False}] \
                  + [{"kind": "scaffold_fallback", "response_kind": "scaffold", "live_requested": False}] * 3
    (bad / "provider-turns.json").write_text(json.dumps(doc), encoding="utf-8")
    ok = tmp_path / "good"; shutil.copytree(src, ok)
    agg = aggregate([bad, ok])
    assert agg["n_total"] == 2
    assert agg["n_valid"] == 1                 # low_cov 被臂纯度门剔除
    assert agg["n_invalid_scaffold"] == 1      # 单列计数(spec §8.9)
    assert agg["n_invalid_lowlive"] == 0
    assert agg["games"][0]["scaffold_coverage"] is None   # good 局非 v3 -> None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py -q`
Expected: FAIL(live_rate 9/14 != 0.9;ImportError: scaffold_coverage_from_turns)

- [ ] **Step 3: 写实现**(`metrics.py`)

`live_rate_from_turns` 改为(玩家口径;`SCAFFOLD_COVERAGE_MIN = 0.5` 常量加在 `LIVE_RATE_MIN` 旁):

```python
def live_rate_from_turns(turns_doc) -> float:
    turns = turns_doc.get("turns") if isinstance(turns_doc, dict) else turns_doc
    if turns is None: return 0.0
    player = [t for t in turns if t.get("response_kind") != "scaffold"]
    if not player: return 0.0
    return sum(1 for t in player if t.get("kind") == "live_success") / len(player)
```

新增:

```python
def scaffold_coverage_from_turns(turns_doc):
    """scaffold_success / scaffold attempts; None when the game ran no scribe
    (non-v3 arms) so the validity gate is vacuous for them (spec §5 2b)."""
    turns = turns_doc.get("turns") if isinstance(turns_doc, dict) else (turns_doc or [])
    attempts = [t for t in turns if t.get("response_kind") == "scaffold"]
    if not attempts: return None
    return sum(1 for t in attempts if t.get("kind") == "scaffold_success") / len(attempts)


def scaffold_coverage(run_dir) -> float | None:
    p = Path(run_dir) / "provider-turns.json"
    if not p.exists(): return None
    try:
        return scaffold_coverage_from_turns(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return None
```

`aggregate` 的有效性判定改为(原 try 块内,live 率行之后):

```python
            cov = scaffold_coverage(d)
            if cov is not None and cov < SCAFFOLD_COVERAGE_MIN:
                invalid_scaffold += 1; continue
```

(循环前初始化 `invalid_scaffold = 0`;valid 行加 `row["scaffold_coverage"] = cov`;`out["n_invalid_scaffold"] = invalid_scaffold`。)

- [ ] **Step 4: 跑测试确认通过 → 提交**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py tests/test_ablation_harness_fake.py -q` → 全绿

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_ablation_metrics.py
git commit -m "feat(ablation): player-only live rate + scaffold_coverage arm-purity gate (n_invalid_scaffold)"
```

---

### Task 8: metrics — 失败链指标 `seer_voted_out_in_verify_cases`

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py`
- Test: `tests/test_ablation_metrics.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_ablation_metrics.py
def test_verify_seer_voted_out_per_game_and_aggregate():
    # 复用 test_analyze_game_dict_basic 的 gl 构造,改投票目标为预言家自己
    gl = {
        "players": [
            {"player_id":"p1","role":"seer","team":"villager"},
            {"player_id":"p2","role":"werewolf","team":"werewolf"},
            {"player_id":"p3","role":"villager","team":"villager"},
            {"player_id":"p4","role":"witch","team":"villager"},
            {"player_id":"p5","role":"werewolf","team":"werewolf"},
            {"player_id":"p6","role":"villager","team":"villager"},
        ],
        "result": {"winner":"werewolf","end_round":2},
        "events": [
            {"round":1,"phase":"night","actor":"p1","target":"p2","data":{"summary":"Seer p1 checks p2, result: werewolf."}},
            {"round":1,"phase":"day","actor":"p2","target":"p1","data":{"summary":"p2 votes p1."}},
            {"round":1,"phase":"day","actor":"p3","target":"p1","data":{"summary":"p3 votes p1."}},
            {"round":1,"phase":"day","actor":"p5","target":"p1","data":{"summary":"p5 votes p1."}},
        ],
    }
    g = analyze_game_dict(gl)
    assert g["verify_wolf_followed"] is False
    assert g["verify_seer_voted_out"] is True          # 验狼局,多数票=预言家自己
    agg = aggregate_games([g])
    assert agg["seer_voted_out_in_verify_cases"] == 1.0
    # 非验狼局 -> None,不进分母
    g2 = dict(g); g2["verify_seer_voted_out"] = None; g2["verify_wolf_followed"] = None
    agg2 = aggregate_games([g, g2])
    assert agg2["seer_voted_out_in_verify_cases"] == 1.0
```

(文件顶部已有 `analyze_game_dict`/`aggregate_games` import。)

- [ ] **Step 2: 跑测试确认失败** → KeyError: 'verify_seer_voted_out'

- [ ] **Step 3: 写实现**(`metrics.py`)

`analyze_game_dict` 的 `verify_wolf_followed` 计算块旁追加,并加进返回 dict:

```python
    verify_seer_voted_out = None
    if seer_chk and seer_chk[1] == "werewolf" and d1 is not None:
        verify_seer_voted_out = (d1 == seer)
```

返回 dict 加 `"verify_seer_voted_out": verify_seer_voted_out,`。

`aggregate_games` 追加(vwf 同款 None 过滤):

```python
    svo = [g.get("verify_seer_voted_out") for g in games if g.get("verify_seer_voted_out") is not None]
```

返回 dict 加 `"seer_voted_out_in_verify_cases": (sum(svo)/len(svo)) if svo else None,`。
`DEFAULT_COMPARE_KEYS` 追加 `"seer_voted_out_in_verify_cases"`(放 `verify_wolf_followed` 之后)。

- [ ] **Step 4: 跑测试 + 全量 → 提交**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py tests/ -q` → 全绿(fixture 聚合新增键不破坏既有断言)

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_ablation_metrics.py
git commit -m "feat(ablation): seer_voted_out_in_verify_cases — the SYS-B4 failure-chain metric"
```

---

### Task 9: harness v3 支持 + 不变量 e2e

**Files:**
- Modify: `src/werewolf_eval/ablation/harness.py`
- Create: `tests/test_prompt_v3_invariants.py`
- Test: `tests/test_ablation_harness_fake.py`

- [ ] **Step 1: 写失败测试**

`tests/test_ablation_harness_fake.py` 追加(文件内已有 `Arm`/`run_arm`/`build_fake_factory`/`pytest`):

```python
def test_run_arm_v3_smoke_with_scaffold_factory(tmp_path):
    from tests.test_prompt_v3 import _FakeScribeProvider
    from werewolf_eval.provider_agent import ProviderAgent
    arm = Arm(label="v3_smoke", prompt_version="prompt_v3", n_games=1, seed_base=7)
    result = run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory,
                     scaffold_factory_builder=lambda a, k: (lambda: ProviderAgent("scribe", _FakeScribeProvider())))
    assert result["prompt_version"] == "prompt_v3"
    assert (tmp_path / "v3_smoke" / "_metrics.json").exists()
```

(若 `from tests.test_prompt_v3 import ...` 因路径不可行,把 `_FakeScribeProvider` 提为 `tests/fake_scribe.py` 共享模块并双处 import——执行时按实际情况选,报告里说明。)

`tests/test_prompt_v3_invariants.py`(新):

```python
"""SYS-B4 acceptance: a full fake game on prompt_v3 (scribe + injections) passes
ALL invariants (I1-I7 incl. I4b) over persisted artifacts — the injections are
derived from public speeches only, so the visibility oracle must stay green."""
import unittest
import tempfile
from pathlib import Path

from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.invariants.checker import check_run
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game
from tests.test_prompt_v3 import _FakeScribeProvider


class PromptV3InvariantsTests(unittest.TestCase):
    def test_v3_fake_game_passes_all_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            agents = build_emergent_fake_agents(build_villager_win_script())
            run_emergent_deepseek_game(
                game_id="v3_inv", out_dir=Path(d), provider_factory=lambda pid: agents[pid],
                model="none", seed=11, max_requests_per_game=80, max_day_rounds=3,
                prompt_version="prompt_v3",
                scaffold_provider_factory=lambda: ProviderAgent("scribe", _FakeScribeProvider()),
            )
            self.assertEqual(check_run(Path(d)), [])
```

- [ ] **Step 2: 跑测试确认失败** → TypeError: run_arm unexpected 'scaffold_factory_builder'

- [ ] **Step 3: 写实现**(`harness.py`)

- `run_arm` 签名加 `scaffold_factory_builder=None`(`factory_builder` 之后)。docstring 补一句:`scaffold_factory_builder(arm, api_key) -> (() -> ProviderAgent),v3 必填`。
- 版本门之后追加:

```python
    if arm.prompt_version == "prompt_v3" and scaffold_factory_builder is None:
        scaffold_factory_builder = _deepseek_scaffold_factory_builder
```

- 新增默认 DeepSeek scribe 工厂(`_deepseek_factory_builder` 旁;**每局新建实例**,与玩家 provider 同纪律;低温走请求级 temperature=0,无需 config 改动):

```python
def _deepseek_scaffold_factory_builder(arm: Arm, api_key: str):
    # Independent scribe provider instance per game (never a seat's instance:
    # seat trace/token accounting must stay clean — spec §3 评审③).
    def build():
        factory = _deepseek_factory(api_key=api_key, base_url=arm.base_url, model=arm.model,
                                    timeout_seconds=40, max_tokens=512, max_requests=MAX_REQUESTS_PER_GAME)
        return factory("scribe")
    return build
```

- 游戏循环里 `run_emergent_deepseek_game(...)` 调用追加:

```python
                    scaffold_provider_factory=(
                        scaffold_factory_builder(arm, api_key)
                        if arm.prompt_version == "prompt_v3" else None),
```

(工厂在 attempt 循环内调用 → scribe provider 同样每局/每重试新建。)

- [ ] **Step 4: 跑测试 + 全量 → 提交**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_harness_fake.py tests/test_prompt_v3_invariants.py tests/ -q` → 全绿

```bash
git add src/werewolf_eval/ablation/harness.py tests/test_ablation_harness_fake.py tests/test_prompt_v3_invariants.py
git commit -m "feat(ablation): v3 arm support (independent per-game scribe provider) + v3 invariant safety net"
```

---

### Task 10: v3 golden 三类样本 + ledger + 守卫

**Files:**
- Modify: `src/werewolf_eval/prompt_goldens.py`、`tools/generate_golden_prompts.py`、`tests/test_prompt_versioning.py`、`docs/generated-games/prompt-version-ledger.json`
- Create: `tests/golden_prompts/prompt_v3/*.txt`(生成)

- [ ] **Step 1: `prompt_goldens.py` 追加 v3 样本集**(三类样本=spec §8.6;复用 Task 2 的 CLAIMS 形状做冻结 fixture)

```python
from werewolf_eval.llm_providers import build_scribe_system_prompt, build_speech_system_prompt_v3
from werewolf_eval.prompt_v3 import render_claim_digest, render_scribe_input, render_vote_scaffold

_CLAIMS_V3 = [
    {"round": 1, "claimant": "p3", "claim_type": "check_report", "target": "p1",
     "result": "werewolf", "refutes": None, "source": 1,
     "source_quote": "昨晚验了p1,他是狼人", "uncertain": False},
    {"round": 1, "claimant": "p1", "claim_type": "refutation", "target": None,
     "result": None, "refutes": "p3", "source": 2,
     "source_quote": "p3在悍跳", "uncertain": True},
]


def canonical_prompt_samples_v3() -> list[tuple[str, str]]:
    """prompt_v3 golden set — the three spec §8.6 classes: ① scribe prompt+schema,
    ② claim digest injection text, ③ vote scaffold full text; plus the restrained
    speech contract and the scribe input rendering."""
    scaffold_req = _req("scribe", "day", [], [], response_kind="scaffold")
    return [
        ("scribe_system_prompt", build_scribe_system_prompt(scaffold_req)),
        ("scribe_input_round1", render_scribe_input(1, [("p3", "我验了p1,他是狼。"), ("p1", "p3在悍跳。")])),
        ("claim_digest_two_claims", render_claim_digest(_CLAIMS_V3)),
        ("vote_scaffold_with_claims", render_vote_scaffold(_CLAIMS_V3)),
        ("vote_scaffold_empty_ledger", render_vote_scaffold([])),
        ("speech_villager_v3", build_speech_system_prompt_v3(_req("p5", "day", [], [], response_kind="speech"))),
    ]
```

- [ ] **Step 2: 生成器加 v3 目录**(`tools/generate_golden_prompts.py` 的目录循环加 `("prompt_v3", canonical_prompt_samples_v3)`)→ 运行生成 → **硬验收**:

```bash
NO_PROXY='*' PYTHONPATH=src python tools/generate_golden_prompts.py
git diff --exit-code tests/golden_prompts/prompt_v1 tests/golden_prompts/prompt_v2
```
第二条必须 exit 0(v1/v2 字节零变化;有 diff 即 BLOCKED)。`prompt_v3/` 出现 6 个 .txt。

- [ ] **Step 3: ledger 追加 prompt_v3 条目**(脚本算哈希,样式照 prompt_v2 条目;`base_version: "prompt_v2"`、`reason` 写 SYS-B4 scheme C、`behavior_evidence: {"status":"not_run","reason_if_not_run":"pending ablation arm b4 vs baseline/b1 (plan Task 11)"}`、`blessed_by` 写 dual review 2026-06-11、`touched_chain` 列 prompt_v3.* 与 llm_providers 两构建器与 _system_for scaffold 分支)。

- [ ] **Step 4: 守卫测试**(`tests/test_prompt_versioning.py` 追加 `PromptV3GuardTests`,三个测试与 PromptV2GuardTests 同构:bytes-match golden、ledger hashes、B4 标记断言——标记断言锁:scribe prompt 含 "只负责提取"、digest 含 "以原文为准"、vote scaffold 含 "【投票前判断程序】" 与三条护栏、speech_v3 **不含** "对跳"/"表态")

- [ ] **Step 5: 跑守卫×2 + 全量 → 提交**

```bash
git add src/werewolf_eval/prompt_goldens.py tools/generate_golden_prompts.py tests/golden_prompts/prompt_v3/ docs/generated-games/prompt-version-ledger.json tests/test_prompt_versioning.py
git commit -m "feat(prompt-v3): golden set (scribe/digest/scaffold/speech) + ledger entry + CI guards (v1/v2 untouched)"
```

---

### Task 11: 实验 — b4 臂 45 局(live,opt-in,用户门)

**Files:** 无代码改动;产物落 `.runs/ablation/`(gitignore)+ docs 快照。

> **用户硬门**:跑前报预算——45 局 × (玩家 ~22 + scribe ≤3) ≈ **~1150 次请求**(上限 45×80=3600),输入 token 与 b1 同量级再加 digest/scaffold 增量;参照 b1 实测(996 请求/1.14M completion tokens/57 分钟)。批准后再跑。

- [ ] **Step 0: 准备对比目录**(baseline/b1 的 `_metrics.json` 从 docs 快照重建;b1 原始局在主树 `.runs/ablation/b1/` 若仍在可直接用)

```bash
mkdir -p .runs/ablation/baseline && cp docs/harness/reviews/2026-06-11-baseline-prompt-v1-metrics.json .runs/ablation/baseline/_metrics.json
mkdir -p .runs/ablation/b1 && cp docs/harness/reviews/2026-06-11-b1-prompt-v2-metrics.json .runs/ablation/b1/_metrics.json
```

- [ ] **Step 1: 跑 b4 臂**(key 在主树 `.tmp/deepseek.key`;seed_base 必须=1000 配对)

```bash
export DEEPSEEK_API_KEY=$(tr -d '\r\n' < .tmp/deepseek.key)
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation run b4 --prompt-version prompt_v3 --n 45 --seed-base 1000
```

- [ ] **Step 2: 核有效性 + 臂纯度 + v3 真在跑**
`n_valid` ≥40(<40 补跑);`n_invalid_scaffold` 必须单列检查;抽 2-3 局 trace:vote 请求带 "【投票前判断程序】"、scribe 请求 `temperature=0.0`、`scaffold_coverage` 明细行 ≥0.5;玩家 live 率口径与 baseline/b1 可比。

- [ ] **Step 3: 三臂对比 + 快照**

```bash
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation compare .runs/ablation/baseline .runs/ablation/b4
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation compare .runs/ablation/b1 .runs/ablation/b4
cp .runs/ablation/b4/_metrics.json docs/harness/reviews/2026-06-11-b4-prompt-v3-metrics.json
git add docs/harness/reviews/2026-06-11-b4-prompt-v3-metrics.json
git commit -m "chore(ablation): b4 (prompt_v3) arm metrics snapshot (45 live games, paired seeds)"
```

- [ ] **Step 4: 对照 spec §6 判据汇报用户**(主判据:`seer_voted_out_in_verify_cases` 70%→<30%;跟投 30%→≥60%;狼胜 ≤65% 方向门;幻觉 ≤5% 不回退;玩家 live 率/解析失败不退化;ledger behavior_evidence 待用户裁决后更新)

---

## Self-Review

**1. Spec §8 十条硬门 → Task 映射**:1 live率玩家口径→T7(钉死测试);2 fallback 归类+历史保留→T4(两个测试);3 claim 字段+提取非裁判→T1(解析器测试)+T10(golden 标记);4 budget/turns 分列→T6;5 guidance 分级→T2/T3/T5(speech 无程序、vote 有,三处测试)+T10 golden;6 v3 golden 三类→T10(scribe prompt+input/digest/scaffold 全锁);7 scribe 独立实例+低温+trace 单列→T4(temperature=0 断言)+T6(trace actor=scribe)+T9(每局新建);8 scribe fixture 单测→T1;9 scaffold_coverage+门槛+单列→T7;10 additive 字节安全→T3/T10(golden 守卫 + `git diff --exit-code` v1/v2)。
**2. Spec 其余覆盖**:§1 失败链指标→T8;§2.2 分层摘要(私有结果已在 v2 obs 私有区,scaffold=账本+程序)→T2/T5;§2.4 契约护栏(action 系统提示 v3==v1 钉死)→T3 test 4;§4 v3 组合(v2 PASS 部分复用:卡+结构化观察零拷贝)→T4(c)/T5;§5 风险 1 scribe 质量→T1 fixture;风险 2/2b→T7;风险 3 跨轮累积→T4;风险 4 I4b→T5 注 + T9 e2e;§6 协议→T11;§7 组件边界一致(prompt_v3 纯函数无 engine import→T1/T2;provider additive→T3)。
**3. 占位符扫描**:每个代码 step 都有完整代码;T6 Step 1 与 T9 测试 import 路径给了明确 fallback 指令(共享 fake_scribe 模块),非空占位。
**4. 类型一致性**:`parse_scribe_claims -> list|None`(T1 定义,T4 消费 None=fallback);claim dict 键(T1 输出=T2 渲染消费=T10 fixture);`scaffold_agent`(engine T4)/`scaffold_provider_factory`(runner T6)/`scaffold_factory_builder(arm, api_key) -> () -> ProviderAgent`(harness T9)三层签名一致;`SCAFFOLD_SUCCESS/SCAFFOLD_FALLBACK` 常量(T4)与 metrics 字符串(T7 用 `response_kind=="scaffold"` 判别,不依赖 kind 串)一致;`KNOWN_PROMPT_VERSIONS` 三元组(T3)与 engine/harness 既有 KNOWN 门自动生效(无字符串硬编码新增——engine 的 v2/v3 分支用显式元组 `("prompt_v2","prompt_v3")`,T4(b)(c) 已写)。
**5. 既有测试影响清单**:`test_known_versions_and_default_constant_unchanged`(T3 更新为三元组,预期);`test_live_rate_from_turns` 既有断言不受影响(无 scaffold turn 的 fixture 口径不变);fixture 聚合测试新增键不破坏(T7/T8 验证)。

---

## Execution Handoff
见对话:选 subagent-driven(推荐)或 inline。Task 11 是 live 用户门(报预算批准后执行)。
