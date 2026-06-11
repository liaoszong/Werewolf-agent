# SYS-B1 Context Repair (prompt_v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec §3 的 Layer-1 上下文修复为一条 **prompt_v2 渲染路径**(数据驱动规则卡 + 结构化观察 + 发言判别 prompt),与 prompt_v1 **运行时共存**、由 arm 的 `prompt_version` 选择;v1 全链路字节不变(golden 守卫为证),v2 自带 golden + ledger;最后跑 b1 臂 45 局与 baseline 配对对比。

**Architecture:** 新增纯函数模块 `prompt_v2.py`(规则卡 + v2 渲染器,不 import engine 防环);`ProviderRequest` 加两个 additive 字段(`prompt_version`/`board_card`,默认值=v1 字节不变);engine 加 `prompt_version` 构造参数 + `_render_obs` 选择器,照 `seat_roles` 的穿线方式穿过 runner→harness;manifest 戳**每局实际版本**。`PROMPT_VERSION` 常量保持 `"prompt_v1"`(默认路径不翻转——翻转是消融出结果后的独立用户决策)。

**Tech Stack:** Python 3、pytest、现有 golden/ledger 基建(`prompt_goldens.py` + `tests/test_prompt_versioning.py` + `docs/generated-games/prompt-version-ledger.json`)、消融度量台(Part A,已合 main)。

---

## 这份 plan 来自的 spec
`docs/superpowers/specs/2026-06-10-quality-ablation-harness-and-b1-context-design.md` §3(Part B)+ §4(实验协议)。Part A(度量台)已完成合 main(merge `fe0a116`),baseline 已打(45 局 n_valid=45,快照 `docs/harness/reviews/2026-06-11-baseline-prompt-v1-metrics.json`)。

## 已核实的代码事实(给实现者,免重查)
- **渲染在引擎侧**:`render_observation_text(obs, events_by_id) -> RenderedObservation(text, source_event_ids)` 在 `emergent_engine.py:111`;4 个调用点 = `_provider_action`(:542 action)、`_resolve_witch`(:769,叠 `augment_witch_observation`)、`_resolve_speech`(:849)、`_resolve_hunter_shot`(:921,叠 `HUNTER_SHOT_OBSERVATION_SUFFIX`)。每个调用点随后都有 `assert_prompt_entitled(...)` 运行时 I4b 守卫——**v2 改造保留这些调用,一行不动**。
- **system prompt 在 provider 侧**:`llm_providers.py` `_system_for(request)`(:197)按 `request.response_kind` 选 `build_speech_system_prompt`(:109,现仅 4 句)或 `build_action_system_prompt`(:87),再 `compose_system(persona, contract)`(:120)。
- **ProviderRequest**(`provider_contract.py:16`)frozen dataclass,已有 additive 演化先例(`observation_text`/`persona_prompt` 等,默认值=旧行为)。请求在**两处**构造:`provider_agent.py:135`(`ProviderAgent.decide`,action 路径)和 engine 直接构造(speech/witch/hunter 三处)。
- **事件形状**(`_emit`,engine:327):`{event_id, sequence, round, phase, type, actor, target, visibility, data:{summary}}`。**`type` 字段可靠可用**(渲染器用它分区,不要用正则):`player_speech`(public,actor=说话人)、`player_vote`(public,actor→target)、`player_died`/`player_eliminated`/`role_revealed`/`day_announcement`(public/all)、`werewolf_kill`(werewolf_team)、`seer_check`(seer)、`witch_save/witch_poison/witch_pass`(witch)、`hunter_shoot/hunter_pass`(public)、`role_assignment`、`game_end`。
- **可见集**:`obs.public_event_ids`=visibility∈(public,all);`obs.private_event_ids`=visibility==all 或 ==role 或(werewolf_team 且 role==werewolf)——**'all' 事件两个列表都有**,先 public 去重即归公开区。
- **胜负语义**(engine:1053-1094):好人胜=`all_werewolves_eliminated`;狼胜=`werewolves_reach_parity`(狼数达到/超过其余存活)。规则卡照此口径写,勿自创。
- **Ruleset**:`action_runtime/ruleset.py` `rules_v1_1()`;`RoleDefinition(role, team, ability_ids)`、`AbilityDefinition(action_id, ...)`(`abilities.py:41-54`)。engine `__init__`(:288)已持有 `_ruleset = rules_v1_1()`(局部变量,Task 4 需把它存为 `self._ruleset` 或当场算卡)。
- **Golden 基建**:`prompt_goldens.canonical_prompt_samples()`(14 样本)+ `tests/golden_prompts/prompt_v1/` + `tests/test_prompt_versioning.py`(3 规则,锁 `PROMPT_VERSION` 目录)+ ledger `docs/generated-games/prompt-version-ledger.json`(rule2 要求字段:`base_version/reason/expected_change/golden_prompt_hashes{before,after}/behavior_evidence/blessed_by/blessed_at`)。生成器 `tools/generate_golden_prompts.py`(36 行,改造前先读)。
- **runner**:`run_emergent_deepseek_game(*, game_id, out_dir, provider_factory, model, seed, max_requests_per_game, max_day_rounds, source_label, seat_roles)`(:128);manifest 在 :167-184 用 `evaluation_bucket(rules_version=engine.rules_version, prompt_version=PROMPT_VERSION, scoring_version=...)` ——**Task 5 把常量换成 engine 实际版本**。
- **harness 硬门**(Part A 终审修复 `f01749d`):`ablation/harness.py` `run_arm` 开头 `if arm.prompt_version != PROMPT_VERSION: raise ValueError` ——Task 8 替换为真选择器。
- **不变量**:`invariants/checker.py` `check_run(source)` 接受 run_dir 或 outcome,返回 violations 列表(空=全绿),含 I4b。
- **测试约定**:`NO_PROXY='*' PYTHONPATH=src python -m pytest ...`(无 editable install)。当前全量 1034 passed。

## 设计决策(spec 已裁决 + 本 plan 固化)
1. **`PROMPT_VERSION` 常量不动**(保持 `"prompt_v1"`)。spec §3.4 的"v1/v2 运行时共存、arm 选择、manifest 戳实际版本"已裁决;**默认路径翻转到 v2 = 消融出结果后的独立用户决策**,不在本 plan。新增 `KNOWN_PROMPT_VERSIONS = ("prompt_v1", "prompt_v2")` 作为合法版本单源。
2. **v1 字节不变是硬验收**:所有 additive 字段默认值令 v1 请求逐字节同前;现有 14 golden + 全量套件全绿即为证。
3. **声称区不做**(spec 降级方案 c);P5 靠规则卡能力表 + 带标签发言。
4. **规则卡严禁硬编码板子**:从 `BoardRuleset` + 本局 `seat_roles` 计数生成(猎人板/洗牌板自动正确)。

## 文件结构
- Create `src/werewolf_eval/prompt_v2.py` — 纯函数:`build_board_rules_card`、`render_observation_text_v2`。**不 import emergent_engine**(防环;返回 tuple,engine 包装成 RenderedObservation)。
- Modify `src/werewolf_eval/prompt_version.py` — 加 `KNOWN_PROMPT_VERSIONS`。
- Modify `src/werewolf_eval/provider_contract.py` — `ProviderRequest` 加 `prompt_version`/`board_card`。
- Modify `src/werewolf_eval/llm_providers.py` — 加 `build_speech_system_prompt_v2`;`_system_for` 选择 + 拼卡。
- Modify `src/werewolf_eval/provider_agent.py` — `decide` 加透传参数。
- Modify `src/werewolf_eval/emergent_engine.py` — ctor `prompt_version` + `_render_obs` + 4 调用点 + 请求字段。
- Modify `src/werewolf_eval/run_emergent_deepseek_game.py` — 穿 `prompt_version` + manifest 戳实际版本。
- Modify `src/werewolf_eval/prompt_goldens.py` + `tools/generate_golden_prompts.py` + `tests/test_prompt_versioning.py` + `docs/generated-games/prompt-version-ledger.json` — v2 golden/ledger/守卫。
- Modify `src/werewolf_eval/ablation/harness.py` — 真选择器。
- Tests: `tests/test_prompt_v2.py`(新)、`tests/test_prompt_v2_invariants.py`(新)、`tests/test_ablation_harness_fake.py`(改)。

---

### Task 1: 数据驱动规则卡 `build_board_rules_card`

**Files:**
- Create: `src/werewolf_eval/prompt_v2.py`
- Test: `tests/test_prompt_v2.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_prompt_v2.py
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: FAIL (ModuleNotFoundError: werewolf_eval.prompt_v2)

- [ ] **Step 3: 写实现**

```python
# src/werewolf_eval/prompt_v2.py
"""prompt_v2 (SYS-B1 Layer-1 context repair): data-driven board rules card +
structured observation renderer. PURE functions over (ruleset, seat_roles) and
(AgentObservation, events_by_id) — no engine import (the engine imports US), no
side effects. The v1 chain (render_observation_text / build_*_system_prompt /
compose_system) is byte-locked by tests/golden_prompts/prompt_v1 and is NOT
touched by this module."""
from __future__ import annotations

from collections import Counter
from typing import Any

from werewolf_eval.action_runtime.ruleset import BoardRuleset

ROLE_NAMES_ZH = {
    "werewolf": "狼人", "seer": "预言家", "witch": "女巫",
    "villager": "村民", "hunter": "猎人",
}
TEAM_NAMES_ZH = {"werewolf": "狼人阵营", "villager": "好人阵营"}
ABILITY_DESCRIPTIONS = {
    "werewolf_kill": "夜间与狼队友共同袭击一名玩家",
    "seer_check": "夜间查验一名玩家的真实身份",
    "witch_save": "用解药救下当晚被袭击的玩家(整局一次)",
    "witch_poison": "用毒药毒杀一名玩家(整局一次)",
    "witch_pass": "选择不用药",
    "player_vote": "白天投票放逐一名玩家",
    "hunter_shoot": "出局时开枪带走一名存活玩家",
    "hunter_pass": "出局时选择不开枪",
}


def build_board_rules_card(ruleset: BoardRuleset, seat_roles: dict[str, str]) -> str:
    """Render THIS board's rules card from data (never hardcode the composition:
    hunter boards / shuffled boards must come out right automatically)."""
    counts = Counter(seat_roles.values())
    comp = "、".join(
        f"{ROLE_NAMES_ZH.get(r, r)}×{n}" for r, n in sorted(counts.items())
    )
    lines = [
        "【本局规则卡】",
        f"规则版本:{ruleset.rules_version}。本局 {sum(counts.values())} 名玩家,身份构成:{comp}。",
        "各身份能力:",
    ]
    for role_def in ruleset.roles:
        if counts.get(role_def.role, 0) == 0:
            continue  # data-driven: only roles actually ON this board
        abilities = ";".join(
            ABILITY_DESCRIPTIONS.get(a, a) for a in role_def.ability_ids
        )
        lines.append(
            f"- {ROLE_NAMES_ZH.get(role_def.role, role_def.role)}"
            f"({TEAM_NAMES_ZH.get(role_def.team, role_def.team)}):{abilities}"
        )
    lines.append(
        "胜负规则:所有狼人出局→好人阵营胜;狼人数量达到或超过其余存活玩家数→狼人阵营胜。"
    )
    lines.append(
        "本局不存在的机制:没有警长竞选、没有警徽流、没有警上警下之分、没有守卫或守夜人。"
        "上面能力表就是本局的全部机制,不要据不存在的机制推理,也不要在发言中讨论它们。"
    )
    lines.append(
        "重要:这是纯文字推理游戏,不存在表情、眼神、语气、肢体动作等任何视觉或听觉信息;"
        "不得以此类\"观察\"作为推理依据。"
    )
    return "\n".join(lines)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/prompt_v2.py tests/test_prompt_v2.py
git commit -m "feat(prompt-v2): data-driven board rules card (SYS-B1 3.1)"
```

---

### Task 2: 结构化观察渲染器 `render_observation_text_v2`

**Files:**
- Modify: `src/werewolf_eval/prompt_v2.py`
- Test: `tests/test_prompt_v2.py`

- [ ] **Step 1: 写失败测试**(含可见集子集硬不变量——spec §6 风险 1 的 TDD 要求)

```python
# 追加到 tests/test_prompt_v2.py
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: FAIL (ImportError: render_observation_text_v2)

- [ ] **Step 3: 写实现**(追加到 `prompt_v2.py`)

```python
# 追加到 src/werewolf_eval/prompt_v2.py
_PUBLIC_FACT_TYPES = (
    "player_died", "player_eliminated", "role_revealed", "day_announcement",
    "hunter_shoot", "hunter_pass",
)


def render_observation_text_v2(obs: Any, events_by_id: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    """Structured, ROLE-SAFE v2 observation. SAME hard invariant as v1
    (emergent_engine.render_observation_text): renders ONLY events whose ids
    appear in obs.public_event_ids ∪ obs.private_event_ids. Returns
    (text, source_event_ids); the engine wraps it into RenderedObservation and
    keeps calling assert_prompt_entitled on the ids."""
    public_ids = list(obs.public_event_ids)
    public_set = set(public_ids)
    ordered: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for ref in public_ids + list(obs.private_event_ids):
        if ref in seen:
            continue
        seen.add(ref)
        ev = events_by_id.get(ref)
        if ev is not None:
            ordered.append((ref, ev))
    ordered.sort(key=lambda kv: kv[1].get("sequence", 0))

    source_event_ids: list[str] = []
    private_lines: list[str] = []
    fact_lines: list[str] = []
    other_lines: list[str] = []
    speech_lines: list[str] = []
    votes_by_round: dict[Any, list[str]] = {}
    for ref, ev in ordered:
        summary = (ev.get("data") or {}).get("summary", "")
        if not summary:
            continue
        source_event_ids.append(ref)
        etype = ev.get("type", "")
        rnd = ev.get("round")
        ph = ev.get("phase")
        if ref not in public_set:
            private_lines.append(f"- (r{rnd} {ph}) {summary}")
        elif etype == "player_speech":
            # speeches are always day-phase; the speaker label is the payload here
            speech_lines.append(f"- (r{rnd}) {ev.get('actor')}: {summary}")
        elif etype == "player_vote":
            votes_by_round.setdefault(rnd, []).append(f"{ev.get('actor')}→{ev.get('target')}")
        elif etype in _PUBLIC_FACT_TYPES:
            # keep the v1-style phase tag: "died in r1 night" vs "eliminated in r1 day"
            # must stay directly readable
            fact_lines.append(f"- (r{rnd} {ph}) {summary}")
        else:
            other_lines.append(f"- (r{rnd} {ph}) {summary}")

    lines = ["【你的私有信息】", f"你是 {obs.player_id}(身份:{obs.role},阵营:{obs.team})。"]
    known_others = {pid: role for pid, role in obs.known_roles.items() if pid != obs.player_id}
    if known_others:
        lines.append("你已知的身份:" + ", ".join(f"{pid}={role}" for pid, role in sorted(known_others.items())) + "。")
    if private_lines:
        lines.append("你的私有事件(仅你/你的阵营可见):")
        lines.extend(private_lines)
    lines.append("【公开状态】")
    lines.append(f"当前:第 {obs.round} 轮 {obs.phase} 阶段。存活玩家:{', '.join(obs.alive_players)}。")
    if fact_lines:
        lines.append("公开事实(死亡/出局/翻牌):")
        lines.extend(fact_lines)
    if other_lines:
        lines.append("其他公开事件:")
        lines.extend(other_lines)
    if speech_lines:
        lines.append("【发言记录】(带说话人,按顺序)")
        lines.extend(speech_lines)
    if votes_by_round:
        lines.append("【投票记录】")
        for rnd in sorted(votes_by_round, key=lambda x: (x is None, x)):
            lines.append(f"- 第{rnd}轮:" + ", ".join(votes_by_round[rnd]))
    return "\n".join(lines), source_event_ids
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/prompt_v2.py tests/test_prompt_v2.py
git commit -m "feat(prompt-v2): structured observation renderer with visibility-subset invariant (SYS-B1 3.2)"
```

---

### Task 3: 发言 prompt v2 + ProviderRequest 字段 + `_system_for` 选择

**Files:**
- Modify: `src/werewolf_eval/prompt_version.py`
- Modify: `src/werewolf_eval/provider_contract.py`
- Modify: `src/werewolf_eval/llm_providers.py`
- Test: `tests/test_prompt_v2.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_prompt_v2.py
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: FAIL (ImportError: KNOWN_PROMPT_VERSIONS / build_speech_system_prompt_v2)

- [ ] **Step 3: 写实现**

`prompt_version.py` 追加(docstring 同步:v2 是**新增共存链**,各有 golden;bump 规则只管"改既有版本的字节"):

```python
# 追加到 src/werewolf_eval/prompt_version.py 末尾
# Runtime-selectable prompt renderers (spec 2026-06-10 quality §3.4): prompt_v1
# stays the default; prompt_v2 (SYS-B1 context repair) coexists and is selected
# per-arm/per-game. Each version has its own golden dir under tests/golden_prompts/.
KNOWN_PROMPT_VERSIONS = ("prompt_v1", "prompt_v2")
```

`provider_contract.py` — `ProviderRequest` 末尾追加两个 additive 字段(默认值=v1 字节不变;入 trace 是 additive schema 演化,与 `persona_prompt` 先例一致):

```python
    # SYS-B1 (additive, back-compat): which prompt rendering chain produced this
    # request ("prompt_v1" default = byte-identical legacy behavior), and the
    # data-driven board rules card to prepend to the system prompt ("" = none).
    prompt_version: str = "prompt_v1"
    board_card: str = ""
```

`llm_providers.py` — 在 `build_speech_system_prompt` 之后追加 v2 构建器,并改 `_system_for`:

```python
def build_speech_system_prompt_v2(request: ProviderRequest) -> str:
    # SYS-B1 §3.3: stance-taking + discrimination structure (NOT "trust the seer" —
    # a fake-claiming wolf would benefit equally). Free text, NO JSON (same machine
    # contract as v1 speech).
    return (
        f"你是狼人杀里的 {request.actor}(第 {request.round} 轮,白天发言)。"
        f"请用自然口吻发言,3-5 句或 120-180 字,不要固定小标题,不要输出 JSON,直接说话。"
        f"发言必须包含:① 当前局势判断;② 对场上已有的硬信息(报身份、报查验结果的发言)"
        f"逐条明确表态:信或不信,并给出理由;③ 你最怀疑或最相信的对象与一个具体理由;④ 本轮投票倾向。"
        f"判别提示:报查验的人可能是真预言家,也可能是假冒的狼人;用对跳(是否有人争同一身份)、"
        f"报点与已公开事实是否矛盾、发言与投票是否一致来检验,而不是默认相信。"
        f"局内不存在表情、眼神、语气等信息,不要编造此类观察。"
    )
```

```python
    def _system_for(self, request: ProviderRequest) -> str:
        if request.prompt_version not in KNOWN_PROMPT_VERSIONS:
            # defense in depth: engine/harness already gate this; never silently
            # render an unknown version as v1.
            raise ValueError(
                f"unknown prompt_version {request.prompt_version!r}; known: {KNOWN_PROMPT_VERSIONS}"
            )
        if request.response_kind == "speech":
            if request.prompt_version == "prompt_v2":
                contract = build_speech_system_prompt_v2(request)
            else:
                contract = build_speech_system_prompt(request)
        else:
            contract = build_action_system_prompt(request)
        composed = compose_system(self._effective_persona(request), contract)
        if request.board_card:
            # board rules card tops the system prompt; empty card (all v1
            # requests) keeps the composed bytes identical to legacy.
            return f"{request.board_card}\n\n{composed}"
        return composed
```

(`llm_providers.py` imports 区追加 `from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS`。)

- [ ] **Step 4: 跑测试 + v1 字节守卫**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py tests/test_prompt_versioning.py -q`
Expected: PASS(v2 新测试 + 既有 golden 守卫全绿 = v1 字节没动)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/prompt_version.py src/werewolf_eval/provider_contract.py src/werewolf_eval/llm_providers.py tests/test_prompt_v2.py
git commit -m "feat(prompt-v2): speech v2 contract + ProviderRequest version/card fields + _system_for selection (SYS-B1 3.3)"
```

---

### Task 4: 引擎穿线 — `prompt_version` 构造参数 + `_render_obs` 选择器 + 4 调用点

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py`
- Modify: `src/werewolf_eval/provider_agent.py`
- Test: `tests/test_prompt_v2.py`

- [ ] **Step 1: 写失败测试**(用现成 fake agents 跑整局,断言请求带卡/带 v2 文本;v1 默认零变化)

```python
# 追加到 tests/test_prompt_v2.py
import pytest

from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script


def _run_engine(prompt_version):
    agents = build_emergent_fake_agents(build_villager_win_script())
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=f"v2t_{prompt_version}"),
        agents=agents, seed=7,
        budget=EmergentBudget(max_requests=80, max_day_rounds=3),
        prompt_version=prompt_version,
    )
    outcome = engine.run()
    reqs = [r for a in agents.values() for r in a.provider.requests]
    assert reqs, "fake game produced no provider requests"
    return outcome, reqs


def test_engine_rejects_unknown_prompt_version():
    with pytest.raises(ValueError, match="prompt_version"):
        _run_engine("prompt_v99")


def test_engine_v2_threads_card_and_structured_text():
    _, reqs = _run_engine("prompt_v2")
    assert all(r.prompt_version == "prompt_v2" for r in reqs)
    assert all(r.board_card.startswith("【本局规则卡】") for r in reqs)
    # contains 而非 startswith:witch/hunter 路径对渲染文本做"追加"式增补,现状都在
    # 末尾,但用 contains 防未来前置式增补把断言变脆
    assert all("【你的私有信息】" in r.observation_text for r in reqs)


def test_engine_v1_default_requests_unchanged():
    _, reqs = _run_engine("prompt_v1")
    assert all(r.prompt_version == "prompt_v1" for r in reqs)
    assert all(r.board_card == "" for r in reqs)
    assert all("你是 " in r.observation_text for r in reqs)  # v1 渲染首行(contains 同理加固)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: FAIL (TypeError: unexpected keyword argument 'prompt_version')

- [ ] **Step 3: 写实现**

`emergent_engine.py`:

(a) imports 区追加:

```python
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS
from werewolf_eval.prompt_v2 import build_board_rules_card, render_observation_text_v2
```

(b) `__init__` 签名加参数(`runtime_events` 之后):`prompt_version: str = "prompt_v1"`;在 `_ruleset = rules_v1_1()` 段之后追加:

```python
        # SYS-B1: runtime-selectable prompt rendering chain (v1 default = legacy
        # bytes). Fail loud on unknown versions — no silent fallback.
        if prompt_version not in KNOWN_PROMPT_VERSIONS:
            raise ValueError(
                f"unknown prompt_version {prompt_version!r}; known: {KNOWN_PROMPT_VERSIONS}"
            )
        self.prompt_version = prompt_version
        self._board_card = ""
        if prompt_version == "prompt_v2":
            self._board_card = build_board_rules_card(
                _ruleset, {p.player_id: p.role for p in config.players}
            )
```

(c) 小 helper(放 `_events_by_id` 之后):

```python
    def _render_obs(self, obs: AgentObservation) -> RenderedObservation:
        if self.prompt_version == "prompt_v2":
            text, ids = render_observation_text_v2(obs, self._events_by_id())
            return RenderedObservation(text=text, source_event_ids=ids)
        return render_observation_text(obs, self._events_by_id())
```

(d) 4 个调用点把 `rendered = render_observation_text(obs, self._events_by_id())` 换成 `rendered = self._render_obs(obs)`(`_provider_action` :542、`_resolve_witch` :769、`_resolve_speech` :849、`_resolve_hunter_shot` :921)。**每处后面的 `assert_prompt_entitled(...)` 一行不动**;witch 的 `augment_witch_observation(rendered.text, victim)` 与 hunter 的 `+ HUNTER_SHOT_OBSERVATION_SUFFIX` 叠加保持原样(v2 文本同样适用)。

(e) engine 直接构造 `ProviderRequest` 的三处(speech :850、witch :771、hunter :922)各追加两个字段:

```python
            prompt_version=self.prompt_version,
            board_card=self._board_card,
```

(f) action 路径(`_provider_action` :561 `agent.decide(...)`)追加同名 kwargs:

```python
                prompt_version=self.prompt_version,
                board_card=self._board_card,
```

`provider_agent.py` — `decide` 签名(:82)追加参数 `prompt_version: str = "prompt_v1"`、`board_card: str = ""`;:135 的 `ProviderRequest(...)` 构造追加 `prompt_version=prompt_version, board_card=board_card`。

- [ ] **Step 4: 跑测试 + 全量回归**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: PASS (13 passed)(T1 2 + T2 3 + T3 5 + 本任务 3)

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q`
Expected: 全绿(≥1034 passed + 新增;golden 守卫绿 = v1 字节没动)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/emergent_engine.py src/werewolf_eval/provider_agent.py tests/test_prompt_v2.py
git commit -m "feat(prompt-v2): engine prompt_version threading + _render_obs selector, v1 byte-identical"
```

---

### Task 5: runner 穿线 + manifest 戳实际版本

**Files:**
- Modify: `src/werewolf_eval/run_emergent_deepseek_game.py`
- Test: `tests/test_prompt_v2.py`

- [ ] **Step 1: 先读现状**

读 `run_emergent_deepseek_game.py:128-185`(签名 + manifest 构建)与 `runtime_events.py` 的 `build_prompt_manifest` / `evaluation_versions.py` 的 `evaluation_bucket`,确认 manifest 里 bucket 的确切 JSON 键路径(预期 `manifest["evaluation_bucket"]["prompt_version"]`;若不同,按实际路径写 Step 2 断言)。

- [ ] **Step 2: 写失败测试**(fake 工厂走完整 runner,落盘后读 manifest)

```python
# 追加到 tests/test_prompt_v2.py
import json as _json
from pathlib import Path

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game


def _fake_factory():
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


def test_runner_threads_prompt_version_and_stamps_actual(tmp_path):
    run_emergent_deepseek_game(
        game_id="v2_runner_smoke", out_dir=tmp_path, provider_factory=_fake_factory(),
        model="none", seed=7, max_requests_per_game=80, max_day_rounds=3,
        prompt_version="prompt_v2",
    )
    manifest = _json.loads((tmp_path / "prompt-manifest.json").read_text(encoding="utf-8"))
    assert manifest["evaluation_bucket"]["prompt_version"] == "prompt_v2"


def test_runner_default_stamps_v1(tmp_path):
    run_emergent_deepseek_game(
        game_id="v1_runner_smoke", out_dir=tmp_path, provider_factory=_fake_factory(),
        model="none", seed=7, max_requests_per_game=80, max_day_rounds=3,
    )
    manifest = _json.loads((tmp_path / "prompt-manifest.json").read_text(encoding="utf-8"))
    assert manifest["evaluation_bucket"]["prompt_version"] == "prompt_v1"
```

(manifest 文件名/路径若与 `RuntimeEventWriter.write_prompt_manifest` 实际落盘不符,以实际为准修正测试——Step 1 已读。)

- [ ] **Step 3: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py -q`
Expected: FAIL (TypeError: unexpected keyword argument 'prompt_version')

- [ ] **Step 4: 写实现**

`run_emergent_deepseek_game`(:128)签名追加 `prompt_version: str = "prompt_v1"`(放 `seat_roles` 之后);engine 构造(:146)追加 `prompt_version=prompt_version`;manifest 的 `evaluation_bucket(...)`(:171-175)把 `prompt_version=PROMPT_VERSION` 改为 **`prompt_version=engine.prompt_version`**(戳每局实际版本——spec §3.4)。`PROMPT_VERSION` import 若因此不再使用则移除;**fake runtime(`run_emergent_fake_runtime.py`)不改**(永远 v1,manifest 戳常量,语义正确)。

- [ ] **Step 5: 跑测试确认通过 + 提交**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py tests/ -q`
Expected: 全绿

```bash
git add src/werewolf_eval/run_emergent_deepseek_game.py tests/test_prompt_v2.py
git commit -m "feat(prompt-v2): runner prompt_version param; manifest stamps ACTUAL per-game version"
```

---

### Task 6: v2 golden + 生成器 + ledger 条目 + 守卫测试

**Files:**
- Modify: `src/werewolf_eval/prompt_goldens.py`
- Modify: `tools/generate_golden_prompts.py`(先读 36 行现状再改)
- Create: `tests/golden_prompts/prompt_v2/*.txt`(生成)
- Modify: `docs/generated-games/prompt-version-ledger.json`
- Modify: `tests/test_prompt_versioning.py`

- [ ] **Step 1: `prompt_goldens.py` 追加 v2 样本集**(手工冻结 fixture,确定性;名字带 `_v2` 防混)

```python
# 追加到 src/werewolf_eval/prompt_goldens.py
from werewolf_eval.action_runtime.ruleset import rules_v1_1
from werewolf_eval.llm_providers import build_speech_system_prompt_v2
from werewolf_eval.prompt_v2 import build_board_rules_card, render_observation_text_v2

_STD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
              "p4": "witch", "p5": "villager", "p6": "villager"}

_EVENTS_V2 = {
    "e1": {"event_id": "e1", "sequence": 1, "round": 1, "phase": "night", "type": "werewolf_kill",
           "actor": "p1", "target": "p5", "visibility": "werewolf_team",
           "data": {"summary": "Wolf team kills p5."}},
    "e2": {"event_id": "e2", "sequence": 2, "round": 1, "phase": "night", "type": "seer_check",
           "actor": "p3", "target": "p1", "visibility": "seer",
           "data": {"summary": "Seer p3 checks p1, result: werewolf."}},
    "e3": {"event_id": "e3", "sequence": 3, "round": 1, "phase": "day", "type": "day_announcement",
           "actor": "system", "target": "none", "visibility": "public",
           "data": {"summary": "Night fell: p5 died."}},
    "e4": {"event_id": "e4", "sequence": 4, "round": 1, "phase": "day", "type": "player_speech",
           "actor": "p3", "target": "none", "visibility": "public",
           "data": {"summary": "我验了p1,他是狼。"}},
    "e5": {"event_id": "e5", "sequence": 5, "round": 1, "phase": "day", "type": "player_speech",
           "actor": "p1", "target": "none", "visibility": "public",
           "data": {"summary": "p3在说谎,我是好人。"}},
    "e6": {"event_id": "e6", "sequence": 6, "round": 1, "phase": "day", "type": "player_vote",
           "actor": "p3", "target": "p1", "visibility": "public",
           "data": {"summary": "p3 votes p1."}},
    "e7": {"event_id": "e7", "sequence": 7, "round": 1, "phase": "day", "type": "player_vote",
           "actor": "p1", "target": "p3", "visibility": "public",
           "data": {"summary": "p1 votes p3."}},
}
_PUB_V2 = ["e3", "e4", "e5", "e6", "e7"]


def _obs_v2(player_id, role, team, phase, known, private):
    return AgentObservation(
        game_id="golden_fixture", player_id=player_id, role=role, team=team,
        phase=phase, round=2, alive_players=["p1", "p2", "p3", "p4", "p6"],
        public_event_ids=list(_PUB_V2), private_event_ids=list(private),
        known_roles=known,
    )


def _v2_text(*args):
    return render_observation_text_v2(_obs_v2(*args), _EVENTS_V2)[0]


def canonical_prompt_samples_v2() -> list[tuple[str, str]]:
    """prompt_v2 golden sample set — locks the SYS-B1 chain (rules card +
    structured observation + speech v2 + full system composition)."""
    card = build_board_rules_card(rules_v1_1(), _STD_SEATS)
    speech_v2 = build_speech_system_prompt_v2(
        _req("p5", "day", [], [], response_kind="speech"))
    witch_text = _v2_text("p4", "witch", "villager", "night", {"p4": "witch"}, [])
    return [
        ("board_card_standard_6p", card),
        ("speech_villager_v2", speech_v2),
        ("speech_werewolf_v2", build_speech_system_prompt_v2(
            _req("p1", "day", [], [], response_kind="speech"))),
        ("obs_v2_seer_day",
         _v2_text("p3", "seer", "villager", "day", {"p3": "seer"}, ["e2"])),
        ("obs_v2_werewolf_night",
         _v2_text("p1", "werewolf", "werewolf", "night",
                  {"p1": "werewolf", "p2": "werewolf"}, ["e1"])),
        ("obs_v2_villager_day",
         _v2_text("p6", "villager", "villager", "day", {"p6": "villager"}, [])),
        ("obs_v2_witch_victim", augment_witch_observation(witch_text, "p5")),
        ("obs_v2_witch_no_victim", augment_witch_observation(witch_text, None)),
        ("obs_v2_hunter_shot",
         _v2_text("p6", "hunter", "villager", "hunter_shot", {"p6": "hunter"}, [])
         + HUNTER_SHOT_OBSERVATION_SUFFIX),
        ("compose_full_v2_speech",
         f"{card}\n\n" + compose_system("你是谨慎的分析型玩家。", speech_v2)),
    ]
```

(注:v2 样本里 `_req` 不需要 `prompt_version` 字段——样本直接调 v2 构建器;`compose_full_v2_speech` 复刻 `_system_for` 的拼装次序:卡 + 空行 + persona + 契约。)

- [ ] **Step 2: 生成器改双目录**

先读 `tools/generate_golden_prompts.py` 现状,改成对 `[("prompt_v1", canonical_prompt_samples), ("prompt_v2", canonical_prompt_samples_v2)]` 循环写 `tests/golden_prompts/<ver>/<name>.txt`(保持原有写法/编码)。运行:

```bash
NO_PROXY='*' PYTHONPATH=src python tools/generate_golden_prompts.py
git diff --exit-code tests/golden_prompts/prompt_v1
```
Expected: 第二条命令 exit 0(**v1 golden 字节零变化**——这是硬验收;若有 diff,立刻停,说明 v1 链被碰了)。`prompt_v2/` 出现 10 个 .txt。

- [ ] **Step 3: ledger 追加 prompt_v2 条目**(用脚本算哈希,勿手填)

```bash
NO_PROXY='*' PYTHONPATH=src python - <<'EOF'
import hashlib, json
from pathlib import Path
from werewolf_eval.prompt_goldens import canonical_prompt_samples_v2
p = Path("docs/generated-games/prompt-version-ledger.json")
entries = json.loads(p.read_text(encoding="utf-8"))
after = {n: hashlib.sha256(t.encode("utf-8")).hexdigest() for n, t in canonical_prompt_samples_v2()}
entries.append({
  "prompt_version": "prompt_v2",
  "base_version": "prompt_v1",
  "reason": "SYS-B1 Layer-1 context repair: data-driven board rules card + structured observation (private/facts/labeled-speeches/vote-matrix) + stance-taking speech contract",
  "expected_change": "v2 coexists with v1 at runtime (arm-selected); v1 goldens untouched; targets P3/P4 hallucinations + P5 role-ability confusion + P6 stance",
  "touched_chain": ["prompt_v2.render_observation_text_v2", "prompt_v2.build_board_rules_card", "llm_providers.build_speech_system_prompt_v2", "llm_providers._system_for(board_card prepend)"],
  "golden_prompt_hashes": {"before": None, "after": after},
  "behavior_evidence": {"status": "not_run", "reason_if_not_run": "pending ablation arm b1 vs baseline (plan Task 10)"},
  "blessed_by": "user (spec 2026-06-10 quality §3 review; plan 2026-06-11-sys-b1-context-repair)",
  "blessed_at": "2026-06-11",
})
p.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("ledger entries:", len(entries))
EOF
```

- [ ] **Step 4: 守卫测试**(追加到 `tests/test_prompt_versioning.py`;复刻 3 规则但锁 `prompt_v2`,**不动既有类**)

```python
from werewolf_eval.prompt_goldens import canonical_prompt_samples_v2

PROMPT_V2 = "prompt_v2"


class PromptV2GuardTests(unittest.TestCase):
    """prompt_v2 coexists with prompt_v1; lock its bytes + ledger the same way."""

    def test_v2_rendered_bytes_match_golden(self) -> None:
        golden_dir = GOLDEN_ROOT / PROMPT_V2
        self.assertTrue(golden_dir.is_dir(), "missing tests/golden_prompts/prompt_v2")
        samples = dict(canonical_prompt_samples_v2())
        files = {p.stem: p for p in golden_dir.glob("*.txt")}
        self.assertEqual(sorted(samples), sorted(files))
        for name, text in samples.items():
            self.assertEqual(files[name].read_bytes(), text.encode("utf-8"),
                             f"prompt_v2 bytes changed for '{name}' without regen+ledger")

    def test_v2_ledger_entry_hashes(self) -> None:
        import hashlib
        matches = [e for e in _ledger() if e.get("prompt_version") == PROMPT_V2]
        self.assertEqual(len(matches), 1)
        after = matches[0]["golden_prompt_hashes"]["after"]
        samples = dict(canonical_prompt_samples_v2())
        self.assertEqual(sorted(after), sorted(samples))
        for name, text in samples.items():
            self.assertEqual(after[name], hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_v2_carries_b1_markers(self) -> None:
        # NOT a v1!=v2 dict compare (sample names differ -> trivially true, zero
        # discrimination). Lock the B1 substance instead: the card exists, the
        # structured sections exist, and the full composition is card-topped.
        samples = dict(canonical_prompt_samples_v2())
        self.assertIn("【本局规则卡】", samples["board_card_standard_6p"])
        self.assertIn("不要在发言中讨论", samples["board_card_standard_6p"])
        for name in ("obs_v2_seer_day", "obs_v2_werewolf_night", "obs_v2_villager_day"):
            self.assertIn("【你的私有信息】", samples[name])
            self.assertIn("【发言记录】", samples[name])
        self.assertTrue(samples["compose_full_v2_speech"].startswith("【本局规则卡】"))
        self.assertIn("表态", samples["speech_villager_v2"])
```

> caveat(记一笔,与 v1 的 `compose_persona_action` 同先例):`compose_full_v2_speech` 锁的是 `f"{card}\n\n" + compose_system(...)` 这个**手工复刻**,不是 `_system_for` 真实路径——若将来改拼装次序,golden 不会自动抓到,靠 Task 3 的 `test_system_for_selects_by_prompt_version_and_prepends_card` 端到端断言兜底。

- [ ] **Step 5: 跑守卫 + 样本确定性 + 提交**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_versioning.py -q`
Expected: PASS(既有 v1 规则 + 新 v2 规则全绿)

```bash
git add src/werewolf_eval/prompt_goldens.py tools/generate_golden_prompts.py tests/golden_prompts/prompt_v2/ docs/generated-games/prompt-version-ledger.json tests/test_prompt_versioning.py
git commit -m "feat(prompt-v2): golden sample set + dual-dir generator + ledger entry + CI guards (v1 goldens untouched)"
```

---

### Task 7: 不变量端到端 — v2 fake 整局过 7 不变量 + I4b

**Files:**
- Create: `tests/test_prompt_v2_invariants.py`

- [ ] **Step 1: 写测试**(spec §3.4/§6:改了渲染必须复跑安全网;v2 路径跑真 runner 落盘,`check_run` 全绿)

```python
# tests/test_prompt_v2_invariants.py
"""SYS-B1 acceptance: a full fake game on the prompt_v2 rendering chain must pass
ALL invariants (I1..I7 incl. the I4b visibility oracle) over its persisted
artifacts. The runtime guard assert_prompt_entitled already runs in-engine; this
locks the artifact-level oracle too."""
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.invariants.checker import check_run
from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game


def _fake_factory():
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


def test_v2_fake_game_passes_all_invariants(tmp_path):
    run_emergent_deepseek_game(
        game_id="v2_inv_smoke", out_dir=tmp_path, provider_factory=_fake_factory(),
        model="none", seed=11, max_requests_per_game=80, max_day_rounds=3,
        prompt_version="prompt_v2",
    )
    violations = check_run(tmp_path)
    assert violations == [], f"invariant violations on prompt_v2 artifacts: {violations}"


def test_v1_fake_game_still_passes_all_invariants(tmp_path):
    run_emergent_deepseek_game(
        game_id="v1_inv_smoke", out_dir=tmp_path, provider_factory=_fake_factory(),
        model="none", seed=11, max_requests_per_game=80, max_day_rounds=3,
    )
    assert check_run(tmp_path) == []
```

- [ ] **Step 2: 跑测试**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2_invariants.py -q`
Expected: PASS (2 passed)。若 v2 报 I4b violation,说明 v2 渲染器把不可见事件渲进了 prompt——回 Task 2 修渲染器,**不许放宽 oracle**。

- [ ] **Step 3: 提交**

```bash
git add tests/test_prompt_v2_invariants.py
git commit -m "test(prompt-v2): full invariant safety net (I1-I7 + I4b) green on v2 artifacts"
```

---

### Task 8: harness 真选择器(替换 f01749d 硬门)

**Files:**
- Modify: `src/werewolf_eval/ablation/harness.py`
- Test: `tests/test_ablation_harness_fake.py`

- [ ] **Step 1: 改测试**(原 `test_run_arm_rejects_unrenderable_prompt_version` 语义升级:未知版本拒、v2 可跑)

把 `tests/test_ablation_harness_fake.py` 中原测试整段替换为:

```python
def test_run_arm_rejects_unknown_prompt_version(tmp_path):
    # Unknown versions hard-fail before any side effects (no silent fallback).
    arm = Arm(label="bogus_arm", prompt_version="prompt_v99", n_games=1, seed_base=7)
    with pytest.raises(ValueError, match="prompt_version"):
        run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory)
    assert not (tmp_path / "bogus_arm").exists()


def test_run_arm_v2_smoke_threads_version(tmp_path):
    # prompt_v2 is now a real renderable arm (SYS-B1).
    arm = Arm(label="v2_smoke", prompt_version="prompt_v2", n_games=1, seed_base=7)
    result = run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory)
    assert result["prompt_version"] == "prompt_v2"
    assert (tmp_path / "v2_smoke" / "_metrics.json").exists()
```

(文件顶部 `import pytest` 与 `from werewolf_eval.prompt_version import PROMPT_VERSION` 已在;后者若不再被引用则删掉该 import。)

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_harness_fake.py -q`
Expected: FAIL(v99 现在报错信息不匹配 KNOWN 集 或 v2 被旧硬门拒)

- [ ] **Step 3: 改实现**

`ablation/harness.py`:import 行 `from werewolf_eval.prompt_version import PROMPT_VERSION` 改为 `from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS`;`run_arm` 开头的硬门替换为:

```python
    if arm.prompt_version not in KNOWN_PROMPT_VERSIONS:
        raise ValueError(
            f"prompt_version {arm.prompt_version!r} is not a known renderer "
            f"(known: {KNOWN_PROMPT_VERSIONS})"
        )
```

`run_emergent_deepseek_game(...)` 调用追加 `prompt_version=arm.prompt_version,`。

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_harness_fake.py tests/test_ablation_metrics.py tests/test_ablation_arms.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/harness.py tests/test_ablation_harness_fake.py
git commit -m "feat(ablation): real prompt_version selector replaces the Part-A hard gate"
```

---

### Task 9: `_metrics.json` 落 per-game 明细行(配对统计能力,选项 b)

> **配对语义(评审裁决,写明)**:`_metrics.json` 此前只存聚合,per-game 的 `analyze_game_dict` 结果在 `aggregate` 里算完即丢;baseline 的原始 `.runs` 已随 worktree 删除 → **逐 seed 配对统计(胜负翻转/McNemar)对 baseline 已物理不可能**。本期 b1 vs baseline 的对比 = **聚合 delta,配对 seed 仅用于方差控制**(同 index→同布局)。本任务给 `aggregate` 输出加 per-game 行:**b1 臂起保留明细,为将来 v2 vs v3 的真·逐 seed 配对留能力**;baseline 接受只有聚合。

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py`
- Test: `tests/test_ablation_metrics.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_ablation_metrics.py
def test_aggregate_emits_per_game_rows():
    run_dirs = sorted(p for p in FIX.iterdir() if p.is_dir())
    agg = aggregate(run_dirs)
    rows = agg["games"]
    assert len(rows) == 3
    assert {r["run_dir"] for r in rows} == {d.name for d in run_dirs}
    assert all("winner" in r and "herd_share" in r for r in rows)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py::test_aggregate_emits_per_game_rows -q`
Expected: FAIL (KeyError: 'games')

- [ ] **Step 3: 改实现**(`metrics.py` 的 `aggregate`,两处小改)

`valid.append(analyze_game_dict(gl))` 改为:

```python
        row = analyze_game_dict(gl)
        row["run_dir"] = d.name
        valid.append(row)
```

(`aggregate_games` 只按键取值,多出的 `run_dir` 键无害。)`out["n_total"] = ...` 之前追加:

```python
    out["games"] = valid
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py tests/test_ablation_harness_fake.py -q`
Expected: 全绿(8 + 3 passed;harness 的 `_metrics.json` 自动带上明细)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_ablation_metrics.py
git commit -m "feat(ablation): per-game rows in _metrics.json (paired-stats capability from b1 onward)"
```

---

### Task 10: 实验 — b1 臂 45 局 + 与 baseline 配对对比(live,opt-in,用户门)

**Files:** 无代码改动;产物落 `.runs/ablation/`(gitignore)+ docs 快照。

> **用户硬门**:跑前向用户报预算(45 局 × max_requests 80 = 上限 3600 请求,预期 ~900-1050,参照 baseline 实测 1024 次/779k completion tokens/41 分钟);批准后再跑。
> **对比口径(见 Task 9 裁决)**:聚合 delta + 配对 seed 方差控制;b1 的 `_metrics.json` 含 per-game 明细,baseline 只有聚合。

- [ ] **Step 0: 恢复 baseline 对比目录**(Part A 的原始 `.runs` 已随 worktree 清理;compare 只需 `_metrics.json`)

```bash
mkdir -p .runs/ablation/baseline
cp docs/harness/reviews/2026-06-11-baseline-prompt-v1-metrics.json .runs/ablation/baseline/_metrics.json
```

- [ ] **Step 1: 跑 b1 臂**(key 在主树 `.tmp/deepseek.key`;**seed_base 必须 = 1000,与 baseline 配对**)

```bash
export DEEPSEEK_API_KEY=$(tr -d '\r\n' < .tmp/deepseek.key)
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation run b1 --prompt-version prompt_v2 --n 45 --seed-base 1000
```

- [ ] **Step 2: 核对有效性**

`n_valid` 应接近 45(<40 补跑并排查);任何 `budget_exhausted`/exception 看 `_index.jsonl` 计数。同时抽 2-3 局 `provider-trace.json` 人工确认请求里 `board_card` 非空、`observation_text` 是分区格式(v2 真的在跑,不是假空对比)。

- [ ] **Step 3: 出对比 + 快照**

```bash
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation compare .runs/ablation/baseline .runs/ablation/b1
cp .runs/ablation/b1/_metrics.json docs/harness/reviews/2026-06-11-b1-prompt-v2-metrics.json
git add docs/harness/reviews/2026-06-11-b1-prompt-v2-metrics.json
git commit -m "chore(ablation): b1 (prompt_v2) arm metrics snapshot (45 live games, paired seeds)"
```

- [ ] **Step 4: 对照成功判据汇报用户**(方向性,非验收硬门;spec §4)

- 视觉幻觉发言率 12.4% → 目标 <5%
- 验狼跟投 50% → 目标 85%
- day1 命中 42.2% → 目标 65%+
- 狼胜 77.8% → 按乘法模型预期降至 ~50-60%
- 机制幻觉局率 11.1% → 应趋零(规则卡直接打击面)。**解读注意**:该指标是发言扫词;规则卡已要求"不要在发言中讨论不存在的机制",但若模型仍复述("规则说了没警长"),扫词会把复述计为幻觉——该偏置方向对 v2 不利(保守),若该指标不降反升,先抽发言看是真幻觉还是复述,再下结论。

结果连同 compare 表交用户裁决:显著改善 → 后续子消融(单独规则卡/单独结构化/单独发言,follow-up 非本期);不显著 → 回 spec §4.5(强模型天花板标定 3-5 局,判断结构占比)。

---

## Self-Review

**1. Spec 覆盖**(对 spec §3 + §4):
- §3.1 规则卡数据驱动(BoardRuleset+seat_roles 计数、能力归属、parity、反视觉声明、**显式否定不存在机制(对齐 MECHANIC_WORDS)+ 要求不在发言中复述(防扫词指标被复述污染)**、严禁写死构成)→ Task 1;穿线(engine 算卡 → ProviderRequest.board_card → `_system_for` 拼入)→ Task 3(d/e/f)+ Task 4 ✓。猎人板正确性有专测(Task 1 test 2)✓。
- §3.2 结构化公共状态(私有单列/公开事实/带标签发言/投票矩阵;砍声称区;只用可见集)→ Task 2;hidden-event 硬不变量测试 = spec §6 风险 1 的 TDD 要求 ✓。声称区明确不做(设计决策 3)✓。
- §3.3 发言升级(硬信息表态信/不信+理由;判别结构非"相信预言家")→ Task 3,有 `"相信预言家" not in text` 反断言 ✓。
- §3.4 v1/v2 共存(arm 选择、两套 golden、manifest 戳实际版本、I4b、安全网全绿、v1 golden 不动)→ Task 4(选择器+fail-loud)、Task 5(manifest 实际版本)、Task 6(v2 golden+ledger+守卫+`git diff --exit-code` v1 不动)、Task 7(check_run 全绿)✓。`PROMPT_VERSION` 常量语义冲突已用设计决策 1 化解(不翻默认,新增 KNOWN 集;ledger 仍记 v2 条目满足"ledger 记账")。
- §4 实验协议(baseline 已打;b1 臂 45 局配对 seed;成功判据方向性)→ Task 10 ✓。强模型标定 = §4.5 建议,列为 Task 10 Step 4 的条件分支(不显著才跑),非独立任务 ✓。**配对语义已写明(评审裁决选 b)**:本期=聚合 delta + 配对 seed 方差控制;Task 9 给 `_metrics.json` 落 per-game 行,b1 起留逐 seed 配对能力,baseline 接受只有聚合 ✓。
- **评审加固(2026-06-11 user review)**:provider 层未知版本 fail-loud(Task 3,纵深防御);Task 4 断言 startswith→contains;Task 6 恒真对比测试换 B1 标记断言;v2 事件行带回 phase 标注(Task 2);`compose_full_v2_speech` 复刻拼装的 caveat 已记(靠 Task 3 端到端断言兜底)。
- **未覆盖(刻意)**:默认 PROMPT_VERSION 翻转(消融后用户决策);子消融臂(spec 列 follow-up);声称区(spec 裁决砍);baseline 逐 seed 明细(原始已删,物理不可能)。

**2. 占位符扫描**:每个代码 step 都有完整代码。两处"先读再改"(Task 5 Step 1 manifest 键路径、Task 6 Step 2 生成器)给了预期形态 + 以实际为准的修正指令,非空占位——manifest 键路径在断言里给了预期 `["evaluation_bucket"]["prompt_version"]`,生成器给了确切循环结构。

**3. 类型一致性**:`build_board_rules_card(ruleset, seat_roles: dict[str,str])` Task 1 定义、Task 4(engine)与 Task 6(goldens)同签名调用;`render_observation_text_v2(obs, events_by_id) -> tuple[str, list[str]]` Task 2 定义、Task 4 `_render_obs` 解包 tuple、Task 6 `_v2_text` 取 `[0]` 一致;`ProviderRequest.prompt_version/board_card`(Task 3)与 engine 三处直接构造、`decide` 透传(Task 4)、`_system_for`(Task 3)字段名一致;`KNOWN_PROMPT_VERSIONS` Task 3 定义、Task 4 engine 与 Task 8 harness 同名 import;runner `prompt_version` kwarg(Task 5)与 Task 7/8/9 调用一致;`RoleDefinition.role/.team/.ability_ids` 与 abilities.py:51-54 实际字段一致(已核)。

**4. 风险点已布防**:渲染改动最高风险(spec §6.1)→ Task 2 hidden-event 测试 + Task 4 保留全部 `assert_prompt_entitled` + Task 7 artifact 级 I4b;v1 回归 → Task 3/4/6 三道字节守卫(`_system_for` 等价断言、全量套件、`git diff --exit-code` v1 golden);JSON 解析链零风险 → v2 不改 action 契约(Task 3 test 4 钉死)。

---

## Execution Handoff
见对话:选 subagent-driven(推荐)或 inline。Task 10 是 live 用户门(报预算批准后执行)。
