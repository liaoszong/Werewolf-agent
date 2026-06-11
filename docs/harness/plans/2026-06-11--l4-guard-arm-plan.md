# L4 Guard Arm (l4_guard) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Spec (authority):** `docs/superpowers/specs/2026-06-11-l4-guard-arm-design.md` — 8 条用户硬边界 + 3 审查补丁全部生效。执行中与本 plan 冲突时以 spec 为准。
> **Execution discipline:** 隔离 worktree(`.agents/skills/committing-in-shared-worktrees/SKILL.md`);prompt 字节改动走 `.agents/skills/guarding-prompt-bytes/SKILL.md`;live 批次走 `.agents/skills/running-live-games/SKILL.md`(Task 16,用户触发)。

**Goal:** 新增守卫角色(rules_v1_2)+ 6p 保护型结构替换臂 `l4_guard`(prompt_v3 + guard board + cap=3),含 I8 不变量、板感知指标与 b4 基线回算,验证守卫是否打开预言家生存窗口。

**Architecture:** 「加角色=加数据」(猎人先例):ruleset/TARGET_RULES/RuntimeState 数据层 → 纯 GuardResolver(SeerResolver 同款)→ 引擎最小接线(NIGHT_DISPATCH_ORDER + NightIntents.guard_target,JointSettler 零改动,守卫路径已预埋于 settler.py:46-53)。Prompt 面只动 v3 链且非守卫板字节恒等(两处硬编码「没有守卫」文案改为板条件渲染)。

**Tech Stack:** Python 3 / unittest;DeepSeek live(Task 16);无新依赖。

**关键已核实事实(不必再考古):**
- `settler.py:16` `NightIntents.guard_target` 字段已预留;`:46-53` guard 挡刀 + 奶穿(`guard+save_same_target`→death)已实现。
- `ruleset.py:62` 奶穿规则键已在 v1 表中;v1_2 无新键。
- `emergent_engine.py:90` `NIGHT_DISPATCH_ORDER`;`:302` ruleset 引用;`:1129-1148` 夜循环与 `NightIntents` 构造;`:1168`「A peaceful night」公告路径现成;`:351` `_private_refs` 的 `v == role` 泛型匹配 → visibility="guard" 引擎侧观察过滤零改动。
- `abilities.py:28` `TARGET_RULES` 谓词表;`state.py` `RuntimeState.night_victim` 先例。
- 两处 prompt 字节雷:`prompt_v2.py:57`(规则卡「没有守卫或守夜人」)与 `llm_providers.py:145`(v3 发言「没有警长、守卫等」)。
- 指标雷:`metrics.py:7` `MECHANIC_WORDS` 含「守卫/守夜人」→ 守卫板需板感知。
- QML 角色标签连 hunter 都没有(猎人先例未进 QML)→ 守卫同样不动 `clients/**`(已知 cosmetic gap,verdict 备注即可)。

---

### Task 1: Rules 数据层 — `exclude_last_guarded` 谓词 + `RuntimeState.last_guarded_target` + `rules_v1_2` + visibility 枚举

**Files:**
- Modify: `src/werewolf_eval/action_runtime/state.py`
- Modify: `src/werewolf_eval/action_runtime/abilities.py`
- Modify: `src/werewolf_eval/action_runtime/ruleset.py`
- Modify: `src/werewolf_eval/runtime_events.py:53-61`
- Test: `tests/test_rules_v1_2.py`(新建)

注意:本 task **不**把 `rules_v1_2` 注册进 `all_rulesets()`(那会立刻打红词汇哨兵与 KnownRoleTeams 钉死测试)——注册随词汇一起在 Task 2 落,保证每个 commit 全绿。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_rules_v1_2.py
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.abilities import ARITY_ONE, TARGET_RULES
from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.runtime_events import RUNTIME_EVENT_VISIBILITIES


class RulesV12Tests(unittest.TestCase):
    def test_guard_role_and_ability(self):
        rs = rules_v1_2()
        self.assertEqual(rs.rules_version, "rules_v1_2")
        guard = next(r for r in rs.roles if r.role == "guard")
        self.assertEqual(guard.team, "villager")
        self.assertEqual(guard.ability_ids, ("guard_protect", "player_vote"))
        ab = rs.ability("guard_protect")
        self.assertEqual(
            (ab.trigger, ab.target_rule, ab.target_arity, ab.visibility),
            ("phase:night", "exclude_last_guarded", ARITY_ONE, "guard"),
        )

    def test_v1_1_untouched_superset(self):
        # append-only:v1_1 的角色/能力是 v1_2 的前缀,逐字段相等(spec §3 硬边界)
        self.assertEqual(rules_v1_1().roles, rules_v1_2().roles[:-1])
        self.assertEqual(rules_v1_1().abilities, rules_v1_2().abilities[:-1])

    def test_night_rules_inherited_no_new_keys(self):
        self.assertEqual(rules_v1_2().night_settlement_rule("guard+save_same_target"), "death")

    def test_guard_visibility_registered(self):
        self.assertIn("guard", RUNTIME_EVENT_VISIBILITIES)


class ExcludeLastGuardedPredicateTests(unittest.TestCase):
    def test_predicate(self):
        pred = TARGET_RULES["exclude_last_guarded"]
        s = RuntimeState(alive=frozenset({"p1", "p2", "p5"}), roles={}, last_guarded_target="p2")
        self.assertTrue(pred(s, "p5", "p5"))   # 可自守
        self.assertTrue(pred(s, "p5", "p1"))
        self.assertFalse(pred(s, "p5", "p2"))  # 不可连守
        self.assertFalse(pred(s, "p5", "p6"))  # 非存活
        night1 = RuntimeState(alive=frozenset({"p1", "p2", "p5"}), roles={})
        self.assertTrue(pred(night1, "p5", "p2"))  # 夜1 无上夜目标:全存活合法


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=src python -m unittest tests.test_rules_v1_2 -v`
Expected: FAIL/ERROR(`cannot import name 'rules_v1_2'`)

- [ ] **Step 3: 实现**

`state.py` — `RuntimeState` 加字段(`night_victim` 之后):

```python
    night_victim: str | None = None  # tonight's pending wolf victim (witch save rule)
    # last target the guard ACTUALLY protected on the previous guard night —
    # fallback-chosen targets count (spec §2 patch). None on night 1 / guardless boards.
    last_guarded_target: str | None = None
```

`abilities.py` — `_is_night_victim` 之后加谓词,并注册:

```python
def _exclude_last_guarded(s: RuntimeState, actor: str, cand: str) -> bool:
    # guard may self-protect; may NOT repeat the previous guard night's target.
    return cand in s.alive and cand != s.last_guarded_target
```

```python
TARGET_RULES: dict[str, TargetPredicate] = {
    "alive_only": _alive_only,
    "exclude_self": _exclude_self,
    "alive_non_wolf": _alive_non_wolf,
    "is_night_victim": _is_night_victim,
    "exclude_last_guarded": _exclude_last_guarded,
}
```

`ruleset.py` — `rules_v1_1` 之后新增(`rules_v1_1` 函数一字不动):

```python
def rules_v1_2() -> BoardRuleset:
    """rules_v1_1 + the guard (L4 protective-structure arm, spec 2026-06-11).
    Versioned superset — does NOT edit rules_v1_1. Boards without a guard behave
    byte-identically under v1_2 (pinned by test_allowed_actions_pinned + the
    determinism canary). The guard's no-consecutive-protect rule lives in the
    exclude_last_guarded target rule, fed by RuntimeState.last_guarded_target —
    minimal inline state (witch one-shot precedent), NOT a CapabilityLedger."""
    base = rules_v1_1()
    guard_abilities = (
        AbilityDefinition("guard_protect", "phase:night", "exclude_last_guarded", ARITY_ONE, "guard"),
    )
    guard = RoleDefinition("guard", "villager", ("guard_protect", "player_vote"))
    return BoardRuleset(
        "rules_v1_2",
        base.roles + (guard,),
        base.abilities + guard_abilities,
        dict(base._night_rules),
        base.death_order_key,
    )
```

`runtime_events.py:53` — 元组 `"witch",` 之后加 `"guard",`(`"werewolf_team"` 之前)。

- [ ] **Step 4: 跑测试确认通过 + 全量回归**

Run: `PYTHONPATH=src python -m unittest tests.test_rules_v1_2 -v` → PASS
Run: `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3` → 与基准一致(1107+5 OK,0 FAIL)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/state.py src/werewolf_eval/action_runtime/abilities.py src/werewolf_eval/action_runtime/ruleset.py src/werewolf_eval/runtime_events.py tests/test_rules_v1_2.py
git commit -m "feat(l4): rules_v1_2 guard role data — exclude_last_guarded rule + RuntimeState.last_guarded_target + guard visibility"
```

---

### Task 2: 词汇 + `all_rulesets()` 注册 + 哨兵网更新

**Files:**
- Modify: `src/werewolf_eval/action_runtime/ruleset.py`(`all_rulesets`)
- Modify: `src/werewolf_eval/prompt_v2.py:14-28`(词汇表)
- Modify: `src/werewolf_eval/display_labels.py`
- Modify: `tests/test_role_single_source.py`(KnownRoleTeams 钉死值)
- Test: 既有哨兵(`tests/test_role_single_source.py`)+ `tests/test_rules_v1_2.py` 扩展

- [ ] **Step 1: 写失败测试(扩展 test_rules_v1_2.py)+ 更新钉死值**

`tests/test_rules_v1_2.py` 加:

```python
class AllRulesetsRegistrationTests(unittest.TestCase):
    def test_v1_2_registered_append_only(self):
        from werewolf_eval.action_runtime.ruleset import all_rulesets, known_role_teams
        versions = [rs.rules_version for rs in all_rulesets()]
        self.assertEqual(versions, ["rules_v1", "rules_v1_1", "rules_v1_2"])
        self.assertEqual(known_role_teams()["guard"], "villager")
```

`tests/test_role_single_source.py` 的 `KnownRoleTeamsTest.test_union_over_all_rulesets_in_declaration_order`:在期望字典/顺序断言的**末尾**(hunter 之后)追加 `"guard": "villager"`(声明序:werewolf→seer→witch→villager→hunter→guard)。

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=src python -m unittest tests.test_rules_v1_2.AllRulesetsRegistrationTests tests.test_role_single_source -v`
Expected: AllRulesetsRegistrationTests FAIL(只有 2 个 ruleset);KnownRoleTeams FAIL(期望含 guard,实际无)

- [ ] **Step 3: 实现**

`ruleset.py` `all_rulesets()`:

```python
    return (rules_v1(), rules_v1_1(), rules_v1_2())
```

`prompt_v2.py`:

```python
ROLE_NAMES_ZH = {
    "werewolf": "狼人", "seer": "预言家", "witch": "女巫",
    "villager": "村民", "hunter": "猎人", "guard": "守卫",
}
```

`ABILITY_DESCRIPTIONS` 加一行(`"hunter_pass"` 之后):

```python
    "guard_protect": "夜间守护一名玩家,使其免受当晚狼人袭击(可守自己,不可连续两晚守同一人,守护结果不会获得反馈)",
```

`display_labels.py`:`ROLE_LABELS` 加 `"guard": "守卫",  # rules_v1_2 (L4 guard arm)`;`TYPE_LABELS` 加 `"guard_protect": "守卫守护",  # rules_v1_2`。

- [ ] **Step 4: 全量哨兵验证**

Run: `PYTHONPATH=src python -m unittest tests.test_role_single_source tests.test_rules_v1_2 -v` → PASS(词汇哨兵 ×6 + ColdImportTest + 闸门全绿)
Run: `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3` → 0 FAIL
(若 `observer_visibility`/`profile_config` 有别的钉 `known_role_teams` 输出的测试被打红:那是 Task 7/10 的认领面,先记录失败名单,在对应 task 修;若失败属于本 task 词汇覆盖面,在此修。)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/ruleset.py src/werewolf_eval/prompt_v2.py src/werewolf_eval/display_labels.py tests/test_role_single_source.py tests/test_rules_v1_2.py
git commit -m "feat(l4): register rules_v1_2 in all_rulesets + guard vocab (prompt_v2 tables, display_labels) + sentinel pins"
```

---

### Task 3: Registry/Provider 升 v1_2 + allowed_actions 钉死扩展

**Files:**
- Modify: `src/werewolf_eval/provider_agent.py:6,24`
- Modify: `tests/test_action_runtime_registry.py`(`test_allowed_actions_pinned`)

- [ ] **Step 1: 扩展钉死测试(先红)**

`test_allowed_actions_pinned` 的期望映射加两行(保持既有 7 组逐字节不动):

```python
        ("guard", "night"): ["guard_protect"],
        ("guard", "day_vote"): ["player_vote"],
```

注意该测试当前用 `rules_v1_1()` 建 registry 的话改为 `rules_v1_2()`;若它钉的是 provider_agent 的模块级 registry 则只加行。

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=src python -m unittest tests.test_action_runtime_registry -v` → FAIL(guard 组合缺失/registry 不识 guard)

- [ ] **Step 3: 实现**

`provider_agent.py:6`:`from werewolf_eval.action_runtime import RoleAbilityRegistry, rules_v1_2`(若 `action_runtime/__init__` 未 re-export `rules_v1_2`,在 `src/werewolf_eval/action_runtime/__init__.py` 按 `rules_v1_1` 同款方式补 re-export——注意 A2 坑:该 `__init__` 不能顶层 import protocol,保持现有惰性结构,只加 ruleset re-export)。

`provider_agent.py:24`:

```python
_ALLOWED_ACTIONS_REGISTRY = RoleAbilityRegistry(rules_v1_2())
```

注释同步:`rules_v1_2 is a backward-compatible superset (guard); 4/5-role games get identical lists`(保持原注释语义,只改版本号措辞)。

- [ ] **Step 4: 验证**

Run: `PYTHONPATH=src python -m unittest tests.test_action_runtime_registry -v` → PASS
Run: `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3` → 0 FAIL(确定性 canary 此时仍绿 = 无守卫板 provider 行为字节恒等的第一道证明)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/provider_agent.py src/werewolf_eval/action_runtime/__init__.py tests/test_action_runtime_registry.py
git commit -m "feat(l4): provider allowed-actions registry -> rules_v1_2 + guard rows pinned"
```

---

### Task 4: GuardResolver(纯 resolver)

**Files:**
- Modify: `src/werewolf_eval/action_runtime/turn.py`(`SeerResolver` 之后)
- Test: `tests/test_guard_resolver.py`(新建)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_guard_resolver.py
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1_2
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.turn import DecisionWindow, GuardResolver
from werewolf_eval.action_runtime.validator import ActionValidator
from werewolf_eval.game_engine import AgentAction


def _window(live_action, alive=("p1", "p2", "p3", "p5"), last=None):
    state = RuntimeState(
        alive=frozenset(alive),
        roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p5": "guard"},
        last_guarded_target=last,
    )
    return DecisionWindow(
        rnd=2, actor="p5", role="guard", emit_phase="night", registry_phase="night",
        alive_seat_order=tuple(alive), roles=dict(state.roles), public_refs=(),
        live_action=live_action,
        validator=ActionValidator(RoleAbilityRegistry(rules_v1_2())),
        runtime_state=state,
    )


def _act(target):
    return AgentAction(action="guard_protect", target=target, reason_summary="t",
                       decision_type="inference_based", confidence=0.9)


class GuardResolverTests(unittest.TestCase):
    def test_legal_protect_accepted(self):
        adj = GuardResolver().adjudicate(_window(_act("p3"), last="p1"))
        self.assertEqual(adj.accepted_target, "p3")
        self.assertEqual(adj.decision_type, "inference_based")
        self.assertIsNone(adj.failure)

    def test_self_protect_accepted(self):
        adj = GuardResolver().adjudicate(_window(_act("p5"), last="p1"))
        self.assertEqual(adj.accepted_target, "p5")

    def test_consecutive_repeat_rejected_with_fallback(self):
        adj = GuardResolver().adjudicate(_window(_act("p3"), last="p3"))
        self.assertIsNone(adj.accepted_target)
        self.assertEqual(adj.failure.kind, "invalid_action")
        self.assertEqual(adj.decision_type, "default")
        # 兜底候选 = 存活含自己、剔上夜所守
        self.assertEqual(adj.rng_pick.over, ("p1", "p2", "p5"))
        self.assertIsNotNone(adj.downgrade_reason)

    def test_provider_error_falls_back_without_failure_row(self):
        adj = GuardResolver().adjudicate(_window(None, last="p3"))
        self.assertIsNone(adj.failure)          # err-path 由引擎记录
        self.assertEqual(adj.rng_pick.over, ("p1", "p2", "p5"))

    def test_render_event_shape(self):
        w = _window(_act("p3"), last="p1")
        plan = GuardResolver().render(w, "p3", "inference_based")
        self.assertEqual(plan.event.etype, "guard_protect")
        self.assertEqual(plan.event.visibility, "guard")
        self.assertEqual(plan.event.summary, "Guard p5 protects p3.")
        self.assertEqual(plan.decision.action, "guard_protect")
        self.assertEqual(plan.decision.phase, "night")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑确认失败** — `PYTHONPATH=src python -m unittest tests.test_guard_resolver -v` → ImportError(GuardResolver)

- [ ] **Step 3: 实现(turn.py,SeerResolver 之后)**

```python
class GuardResolver:
    """Pure single-actor resolver for guard_protect (L4 guard arm). Mirrors
    SeerResolver EXCEPT candidates: the guard MAY self-protect and may NOT repeat
    the previous guard night's target, so fallback candidates derive from
    runtime_state.last_guarded_target — NOT DecisionWindow.candidates() (which
    excludes self)."""

    def adjudicate(self, w: DecisionWindow) -> Adjudication:
        if w.live_action is not None and w.is_legal():
            return Adjudication(accepted_target=w.live_action.target, decision_type="inference_based")
        failure = downgrade = None
        if w.live_action is not None:   # present but illegal (err-path is engine-recorded)
            tgt = w.live_action.target
            failure = FailureRow("invalid_action", f"{w.actor} bad guard_protect {tgt}", tgt)
            downgrade = f"engine rejected guard_protect {tgt}"
        last = w.runtime_state.last_guarded_target
        cands = tuple(p for p in w.alive_seat_order if p != last)
        if not cands:
            return Adjudication(skip=True)
        return Adjudication(rng_pick=RngPick("choice", cands), decision_type="default",
                            failure=failure, downgrade_reason=downgrade)

    def render(self, w: DecisionWindow, target: str, dtype: str) -> EmitPlan:
        return EmitPlan(
            decision=DecisionRow(w.actor, "single", "night", "guard_protect", target, dtype,
                                 f"guard protects {target}"),
            event=EventRow("night", "guard_protect", w.actor, target, "guard",
                           f"Guard {w.actor} protects {target}."),
        )
```

- [ ] **Step 4: 验证** — `PYTHONPATH=src python -m unittest tests.test_guard_resolver -v` → PASS;全量 0 FAIL

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/turn.py tests/test_guard_resolver.py
git commit -m "feat(l4): GuardResolver — pure guard_protect resolver (self-protect legal, no-consecutive via last_guarded_target)"
```

---

### Task 5: 引擎接线 + 脚本化守卫哨兵(挡刀/奶穿/连守拒绝/自守)

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py`(`:47` import、`:90`、`:302` 区、`_RESOLVERS` ~`:330`、`_runtime_state` `:549`、`_run_seer` 后新增 `_run_guard`、夜循环 `:1129-1148`、`__init__` 状态)
- Modify: `tests/test_role_single_source.py`(夜序哨兵 v1_1→v1_2)
- Test: `tests/test_guard_sentinels.py`(新建)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_guard_sentinels.py
"""Guard engine sentinels (L4 arm): block / 奶穿 / no-consecutive / self-protect.
Boards WITHOUT a witch where possible (the witch acts every night she is alive;
omitting her from seat_roles removes that turn from the script entirely)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    _act, build_emergent_fake_agents, SPEECH_REQUEST_PHASE,
)

# 无女巫板:2狼 + 预言家 + 守卫 + 2民(脚本免去女巫每夜回合)
SEATS_NO_WITCH = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                  "p4": "guard", "p5": "villager", "p6": "villager"}
# 奶穿板:2狼 + 预言家 + 女巫 + 守卫 + 1民
SEATS_WITH_WITCH = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                    "p4": "witch", "p5": "guard", "p6": "villager"}


def _speeches(s, rnd, pids=("p1", "p2", "p3", "p4", "p5", "p6")):
    for pid in pids:
        s[(pid, SPEECH_REQUEST_PHASE, rnd)] = f"{pid}: speech r{rnd}"


def _votes(s, rnd, mapping):
    for pid, tgt in mapping.items():
        s[(pid, "day", rnd)] = _act("player_vote", tgt, "inference_based", f"{pid}->{tgt}")


def build_guard_blocks_script():
    """R1 守卫守 p6,狼刀 p6 -> 平安夜;R1 票出 p1;R2 守 p5(换目标),狼刀 p6 落地;R2 票出 p2 -> 村胜。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p6": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("guard_protect", "p5", "inference_based", "protect p5")
    _speeches(s, 2)
    _votes(s, 2, {"p3": "p2", "p4": "p2", "p5": "p2", "p2": "p3"})
    return s


def build_milk_pierce_script():
    """R1 狼刀 p6 + 守卫守 p6 + 女巫救 p6 -> 奶穿:p6 死;R1 票出 p1;
    R2 狼刀 p3 被守卫(守 p3)挡下 + 女巫毒 p2 -> 狼全灭,村胜。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("witch_save", "p6", "inference_based", "save p6")
    s[("p5", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("witch_poison", "p2", "retaliatory", "poison p2")
    s[("p5", "night", 2)] = _act("guard_protect", "p3", "inference_based", "protect p3")
    return s


def build_consecutive_repeat_script():
    """R1 守 p6 合法;R2 又守 p6 -> 非法,须 invalid_action + 确定性兜底(目标≠p6)。
    R1 狼刀 p5(落地),R1 票出 p1;R2 狼刀 p3;R2 票出 p2 -> 终局。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p6": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("guard_protect", "p6", "inference_based", "ILLEGAL repeat p6")
    _speeches(s, 2)
    _votes(s, 2, {"p3": "p2", "p4": "p2", "p6": "p2", "p2": "p4"})
    return s


def build_self_protect_script():
    """R1 狼刀守卫 p4,守卫自守 -> 平安夜;R1 票出 p1;R2 狼刀 p3 落地(守卫换守 p6);R2 票出 p2。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p4", "team_coordinated", "kill p4")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p4", "team_coordinated", "kill p4")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("guard_protect", "p4", "inference_based", "self-protect")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p6": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 2)
    _votes(s, 2, {"p4": "p2", "p5": "p2", "p6": "p2", "p2": "p4"})
    return s


def _run(game_id, seats, script, seed=0):
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=game_id, seat_roles=seats),
        agents=build_emergent_fake_agents(script),
        seed=seed,
    )
    return engine.run()


class GuardBlocksKillSentinel(unittest.TestCase):
    def test_guard_block_yields_peaceful_night(self):
        outcome = _run("guard_block", SEATS_NO_WITCH, build_guard_blocks_script())
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        r1_deaths = [e for e in events if e["type"] == "player_died" and e["round"] == 1]
        self.assertEqual(r1_deaths, [])
        self.assertTrue(any("A peaceful night" in e["data"]["summary"]
                            for e in events if e["type"] == "day_announcement" and e["round"] == 1))
        protects = [e for e in events if e["type"] == "guard_protect"]
        self.assertEqual([e["target"] for e in protects], ["p6", "p5"])
        self.assertTrue(all(e["visibility"] == "guard" for e in protects))
        # R2 守卫不在位 -> 刀落地
        self.assertTrue(any(e["type"] == "player_died" and e["target"] == "p6" and e["round"] == 2
                            for e in events))


class MilkPierceSentinel(unittest.TestCase):
    def test_guard_plus_save_same_target_dies(self):
        outcome = _run("guard_milk_pierce", SEATS_WITH_WITCH, build_milk_pierce_script())
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        self.assertTrue(any(e["type"] == "player_died" and e["target"] == "p6" and e["round"] == 1
                            for e in events))  # I8b:同守同救 -> 死
        # R2:守 p3 挡刀(p3 无夜间死亡),毒不被守挡(p2 死)
        self.assertFalse(any(e["type"] == "player_died" and e["target"] == "p3" for e in events))
        self.assertTrue(any(e["type"] == "player_died" and e["target"] == "p2" for e in events))
        self.assertEqual(outcome.game_log["result"]["winner"], "villager")


class ConsecutiveRepeatSentinel(unittest.TestCase):
    def test_repeat_protect_rejected_and_falls_back(self):
        outcome = _run("guard_consecutive", SEATS_NO_WITCH, build_consecutive_repeat_script())
        self.assertEqual(outcome.status, "completed")
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])
        protects = [e for e in outcome.game_log["events"] if e["type"] == "guard_protect"]
        self.assertEqual(len(protects), 2)
        self.assertEqual(protects[0]["target"], "p6")
        self.assertNotEqual(protects[1]["target"], "p6")  # 兜底必不连守


class SelfProtectSentinel(unittest.TestCase):
    def test_self_protect_blocks_own_kill(self):
        outcome = _run("guard_self", SEATS_NO_WITCH, build_self_protect_script())
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        r1_deaths = [e for e in events if e["type"] == "player_died" and e["round"] == 1]
        self.assertEqual(r1_deaths, [])
        self.assertIn(("p4", "p4"), [(e["actor"], e["target"]) for e in events
                                     if e["type"] == "guard_protect" and e["round"] == 1])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑确认失败** — `PYTHONPATH=src python -m unittest tests.test_guard_sentinels -v` → 失败(引擎不识 guard_protect)

- [ ] **Step 3: 实现引擎接线**

1. `:47` import 区:`rules_v1_1` → 同时 import `rules_v1_2`(或替换,见 4);turn.py import 区加 `GuardResolver`。
2. `:90`:`NIGHT_DISPATCH_ORDER = ("guard_protect", "werewolf_kill", "seer_check")`(守卫先行;结算为 joint,女巫看到的仍是狼队原始目标——奶穿语义不受 dispatch 顺序影响)。
3. `__init__`:在初始化 `self._death_committed` 的同区(grep `self._death_committed = ` 定位)加:

```python
        self._last_guarded: str | None = None  # guard's previous EFFECTIVE protect target (spec §2)
```

4. `:302` 区:`_ruleset = rules_v1_1()` → `_ruleset = rules_v1_2()`;上方注释改为:`rules_v1_2 is a backward-compatible superset (hunter + guard); boards without them behave byte-identically (determinism canary + pinned tests)。`
5. `_RESOLVERS`(`:330` 区)加:

```python
            "guard_protect": self._run_guard,
```

6. `_runtime_state`(`:549`):

```python
        return RuntimeState(
            alive=frozenset(self._alive),
            roles={pid: p.role for pid, p in self._players_by_id.items()},
            night_victim=night_victim,
            last_guarded_target=self._last_guarded,
        )
```

7. `_run_seer`(`:687`)之后:

```python
    def _run_guard(self, rnd):
        guards = [pid for pid in self._alive if self._players_by_id[pid].role == "guard"]
        if not guards:
            return None
        target = self._run_single_turn(GuardResolver(), guards[0], "guard", "night", "night", "night", rnd)
        if target is not None:
            # the ACTUALLY effective protect target (fallback included) drives next
            # night's exclude_last_guarded — spec §2 patch: not the model's raw intent.
            self._last_guarded = target
        return target
```

8. 夜循环(`:1131-1136`):

```python
            victim = None
            guard_target = None
            for ability_id in NIGHT_DISPATCH_ORDER:
                result = self._RESOLVERS[ability_id](rnd)
                if ability_id == "werewolf_kill":
                    victim = result
                elif ability_id == "guard_protect":
                    guard_target = result
```

9. 结算(`:1145`):

```python
                    NightIntents(wolf_victim=victim, saved=saved,
                                 poison_target=poison_target, guard_target=guard_target),
```

10. 夜序哨兵:`tests/test_role_single_source.py` 的 `test_night_dispatch_order_is_subset_of_ruleset_night_abilities` 中 `rules_v1_1()` → `rules_v1_2()`(guard_protect 属 v1_2 夜间能力)。

- [ ] **Step 4: 验证(含字节恒等双证)**

Run: `PYTHONPATH=src python -m unittest tests.test_guard_sentinels tests.test_role_single_source -v` → PASS
Run: `ls tests | grep -iE "canar|determin|parity"` 找到确定性 canary/parity 测试名,逐个跑 → PASS(= 无守卫板在 v1_2 下行为字节恒等)
Run: `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3` → 0 FAIL

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_guard_sentinels.py tests/test_role_single_source.py
git commit -m "feat(l4): engine guard wiring — NIGHT_DISPATCH_ORDER + _run_guard + NightIntents.guard_target + last_guarded state (settler untouched)"
```

---

### Task 6: Settler I8a/I8b 分支显式单测

**Files:**
- Test: `tests/test_settler_guard_branches.py`(新建;`settler.py` **零改动**)

- [ ] **Step 1: 写测试(settler 已实现,应直接绿——这是钉契约,不是 TDD 红绿)**

```python
# tests/test_settler_guard_branches.py
"""Pin the two I8 branches of JointSettler's PRE-EXISTING guard path (settler.py:46-53).
The settler is NOT modified by the L4 arm — these tests freeze the contract the
engine wiring (Task 5) relies on, incl. poison-not-blocked."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_2
from werewolf_eval.action_runtime.settler import JointSettler, NightIntents
from werewolf_eval.action_runtime.state import RuntimeState


def _state():
    return RuntimeState(
        alive=frozenset({"p1", "p2", "p3", "p4", "p5", "p6"}),
        roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer",
               "p4": "witch", "p5": "guard", "p6": "villager"},
    )


class SettlerGuardBranchTests(unittest.TestCase):
    def setUp(self):
        self.settler = JointSettler(rules_v1_2())

    def test_i8a_guard_blocks_kill_no_save(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=False, poison_target=None, guard_target="p6"),
            _state())
        self.assertNotIn("p6", r.deaths)

    def test_i8b_guard_plus_save_same_target_dies(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=True, poison_target=None, guard_target="p6"),
            _state())
        self.assertIn("p6", r.deaths)  # 奶穿(guard+save_same_target=death,查表)

    def test_guard_does_not_block_poison(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim=None, saved=False, poison_target="p6", guard_target="p6"),
            _state())
        self.assertIn("p6", r.deaths)  # 守卫不挡毒

    def test_guard_elsewhere_kill_lands(self):
        r = self.settler.resolve_night(
            NightIntents(wolf_victim="p6", saved=False, poison_target=None, guard_target="p3"),
            _state())
        self.assertIn("p6", r.deaths)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试** — `PYTHONPATH=src python -m unittest tests.test_settler_guard_branches -v` → PASS(若 `NightIntents`/`resolve_night` 签名与上不符,以 `settler.py` 实际签名为准微调测试,**不改 settler**)

- [ ] **Step 3: Commit**

```bash
git add tests/test_settler_guard_branches.py
git commit -m "test(l4): pin settler guard branches — I8a block / I8b milk-pierce / poison-not-blocked"
```

---

### Task 7: Observer 可见性 — guard 私有事件授权

**Files:**
- Modify: `src/werewolf_eval/observer_visibility.py:33,491-507`
- Test: `tests/test_guard_visibility.py`(新建)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_guard_visibility.py
"""guard_protect (visibility='guard') entitlement: ONLY the guard seat sees it —
observer projection (I4b oracle path) + spec §6 hard gate (leak = blocking bug)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.invariants.visibility_oracle import entitled, seat_index_from_players

PLAYERS = [
    {"player_id": "p1", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p2", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p3", "role": "seer", "team": "villager"},
    {"player_id": "p4", "role": "witch", "team": "villager"},
    {"player_id": "p5", "role": "guard", "team": "villager"},
    {"player_id": "p6", "role": "villager", "team": "villager"},
]

GUARD_EVENT = {"event_id": "e9", "sequence": 9, "round": 1, "phase": "night",
               "type": "guard_protect", "actor": "p5", "target": "p6",
               "visibility": "guard", "data": {"summary": "Guard p5 protects p6."}}


class GuardEventEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.idx = seat_index_from_players(PLAYERS)

    def test_guard_seat_entitled(self):
        self.assertTrue(entitled("p5", GUARD_EVENT, self.idx))

    def test_every_other_seat_hidden(self):
        for seat in ("p1", "p2", "p3", "p4", "p6"):
            self.assertFalse(entitled(seat, GUARD_EVENT, self.idx), seat)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑确认失败** — guard 座位 entitled 返回 False(observer 不识 "guard" visibility)

- [ ] **Step 3: 实现(observer_visibility.py)**

`:33`:

```python
ROLE_SPECIFIC_EVENT_VISIBILITIES: frozenset[str] = frozenset({"seer", "witch", "guard"})
```

`:496-500` witch 分支之后,仿 seer/witch 既有惯用法加:

```python
        if visibility == "guard":
            trusted_role = _trusted_role_for_player(seat_index, role_player)
            if trusted_role == "guard":
                return True, "guard_event"
            return False, "hidden"
```

- [ ] **Step 4: 验证** — 新测试 PASS;全量 0 FAIL(R-17 visibility 不变量守卫如有枚举钉死,按报错把 "guard" 补进其期望集)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/observer_visibility.py tests/test_guard_visibility.py
git commit -m "feat(l4): observer guard visibility — only the guard seat is entitled to guard_protect events"
```

---

### Task 8: 不变量 — I2 扩 guard_protect + 新增 I8a/I8b/I8c

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_i8.py`(新建)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_invariants_i8.py
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.invariants.artifacts import RunArtifacts
from werewolf_eval.invariants.checker import check_i2, check_i8, check_i8c


def _ev(eid, seq, rnd, phase, etype, actor, target, summary=""):
    return {"event_id": eid, "sequence": seq, "round": rnd, "phase": phase,
            "type": etype, "actor": actor, "target": target,
            "visibility": "internal", "data": {"summary": summary}}


def _arts(events):
    # RunArtifacts 构造:按 invariants/artifacts.py 的实际工厂(from_outcome/from_run_dir
    # 之外应有测试用直构;若只有工厂,按 tests/test_invariants_checker.py 的现成
    # 构造手法复用 —— 该文件已存在同类 fixture)。
    return RunArtifacts(game_id="i8_fixture", players=[], events=events,
                        provider_turns=[], gaps=())


class I8aTests(unittest.TestCase):
    def test_blocked_kill_death_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "player_died", "system", "p6"),
        ]
        self.assertEqual([v.id for v in check_i8(_arts(events))], ["I8a"])

    def test_blocked_kill_no_death_clean(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
        ]
        self.assertEqual(check_i8(_arts(events)), [])

    def test_same_target_poison_excused(self):
        # 守住了刀但同夜被毒死:不是 I8a 违例(守卫不挡毒)
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "witch_poison", "p4", "p6"),
            _ev("e4", 4, 1, "night", "player_died", "system", "p6"),
        ]
        self.assertEqual(check_i8(_arts(events)), [])


class I8bTests(unittest.TestCase):
    def test_milk_pierce_survival_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "witch_save", "p4", "p6"),
        ]
        self.assertEqual([v.id for v in check_i8(_arts(events))], ["I8b"])

    def test_milk_pierce_death_clean(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 2, 1, "night", "werewolf_kill", "p1", "p6"),
            _ev("e3", 3, 1, "night", "witch_save", "p4", "p6"),
            _ev("e4", 4, 1, "night", "player_died", "system", "p6"),
        ]
        self.assertEqual(check_i8(_arts(events)), [])


class I8cTests(unittest.TestCase):
    def test_consecutive_same_target_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 5, 2, "night", "guard_protect", "p5", "p6"),
        ]
        self.assertEqual([v.id for v in check_i8c(_arts(events))], ["I8c"])

    def test_alternating_targets_clean(self):
        events = [
            _ev("e1", 1, 1, "night", "guard_protect", "p5", "p6"),
            _ev("e2", 5, 2, "night", "guard_protect", "p5", "p3"),
            _ev("e3", 9, 3, "night", "guard_protect", "p5", "p6"),  # 隔夜回守合法
        ]
        self.assertEqual(check_i8c(_arts(events)), [])


class I2GuardTests(unittest.TestCase):
    def test_dead_guard_protect_is_violation(self):
        events = [
            _ev("e1", 1, 1, "night", "player_died", "system", "p5"),
            _ev("e2", 2, 2, "night", "guard_protect", "p5", "p6"),
        ]
        self.assertEqual([v.id for v in check_i2(_arts(events))], ["I2"])


if __name__ == "__main__":
    unittest.main()
```

(若 `RunArtifacts` 不能如上直构,改用 `tests/test_invariants_checker.py` 现成的 fixture 构造手法——断言不变。)

- [ ] **Step 2: 跑确认失败** — ImportError(check_i8)/I2 不识 guard_protect

- [ ] **Step 3: 实现(checker.py)**

`:63` `ACTIVE_ACTION_TYPES` 加 `"guard_protect"`;`InvariantViolation` 注释 `"I1".."I7"` → `"I1".."I8c"`。文件尾部(check_i7 之后)加:

```python
def _guard_night_rows(arts: RunArtifacts) -> dict[int, dict[str, Any]]:
    """round -> {kill, guard, save, poison targets; died set} for I8 correlation."""
    rows: dict[int, dict[str, Any]] = {}
    for e in arts.events:
        if e.get("phase") != "night":
            continue
        r = int(e.get("round", 0))
        row = rows.setdefault(r, {"kill": None, "guard": None, "save": None,
                                  "poison": None, "died": set()})
        t = e.get("type")
        if t == "werewolf_kill":
            row["kill"] = str(e.get("target"))
        elif t == "guard_protect":
            row["guard"] = str(e.get("target"))
        elif t == "witch_save":
            row["save"] = str(e.get("target"))
        elif t == "witch_poison":
            row["poison"] = str(e.get("target"))
        elif t == "player_died":
            row["died"].add(str(e.get("target")))
    return rows


def check_i8(arts: RunArtifacts) -> list[InvariantViolation]:
    """I8a: a guard-blocked kill target (no same-target save, no same-target poison)
    must NOT die that night. I8b: guard+save on the SAME kill target MUST die
    (guard+save_same_target=death — 奶穿). Spec 2026-06-11 §7 (split branches)."""
    out: list[InvariantViolation] = []
    for r, row in sorted(_guard_night_rows(arts).items()):
        if row["kill"] is None or row["guard"] != row["kill"]:
            continue
        same_save = row["save"] == row["kill"]
        same_poison = row["poison"] == row["kill"]
        died = row["kill"] in row["died"]
        if not same_save and not same_poison and died:
            out.append(InvariantViolation("I8a", "error", arts.game_id, (),
                       f"r{r}: guard blocked kill on {row['kill']} but they died"))
        if same_save and not died:
            out.append(InvariantViolation("I8b", "error", arts.game_id, (),
                       f"r{r}: guard+save same target {row['kill']} must die (milk-pierce) but survived"))
    return out


_ALL_CHECKS.append(check_i8)


def check_i8c(arts: RunArtifacts) -> list[InvariantViolation]:
    """I8c: no two CONSECUTIVE guard nights protect the same target (actual
    effective targets — fallback included). Non-adjacent repeats are legal."""
    seq = sorted((int(e.get("round", 0)), str(e.get("target")))
                 for e in arts.events if e.get("type") == "guard_protect")
    out: list[InvariantViolation] = []
    for (r1, t1), (r2, t2) in zip(seq, seq[1:]):
        if r2 == r1 + 1 and t1 == t2:
            out.append(InvariantViolation("I8c", "error", arts.game_id, (),
                       f"guard protected {t1} on consecutive nights r{r1},r{r2}"))
    return out


_ALL_CHECKS.append(check_i8c)
```

(`Any` 需要时补 import——`checker.py` 顶部已有 `from typing import Any, Callable`。)

- [ ] **Step 4: 验证** — `PYTHONPATH=src python -m unittest tests.test_invariants_i8 tests.test_guard_sentinels -v` → PASS;全量 0 FAIL(I8 进 `_ALL_CHECKS` 后既有 e2e 不变量测试必须仍绿——无守卫局 I8 恒空)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_i8.py
git commit -m "feat(l4): invariants I8a/I8b/I8c (guard block / milk-pierce / no-consecutive) + I2 covers guard_protect"
```

---

### Task 9: 规则卡板条件渲染(prompt 字节雷 #1)

**Files:**
- Modify: `src/werewolf_eval/prompt_v2.py:53-59`(`build_board_rules_card`)
- Test: `tests/test_prompt_v2.py`(扩展)

先读 `.agents/skills/guarding-prompt-bytes/SKILL.md` 再动本 task 与 Task 10/11。

- [ ] **Step 1: 写失败测试(tests/test_prompt_v2.py 加类)**

```python
GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
               "p4": "witch", "p5": "guard", "p6": "villager"}
STD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
             "p4": "witch", "p5": "villager", "p6": "villager"}


class GuardBoardRulesCardTests(unittest.TestCase):
    def test_standard_board_bytes_unchanged(self):
        # 非守卫板字节恒等(spec §6):「没有守卫或守夜人」原文必须原样保留
        card = build_board_rules_card(rules_v1_1(), STD_SEATS)
        self.assertIn("没有警长竞选、没有警徽流、没有警上警下之分、没有守卫或守夜人。", card)
        self.assertNotIn("同守同救", card)
        # 同板换 v1_2 渲染也必须逐字节相同(守卫不在板上)
        self.assertEqual(card, build_board_rules_card(rules_v1_2(), STD_SEATS))

    def test_guard_board_card(self):
        card = build_board_rules_card(rules_v1_2(), GUARD_SEATS)
        self.assertIn("守卫×1", card)
        self.assertIn("夜间守护一名玩家", card)              # 能力行(数据驱动)
        self.assertIn("同守同救", card)                      # 奶穿规则公示
        self.assertNotIn("没有守卫或守夜人", card)            # 假话行必须消失
        self.assertIn("没有警长竞选、没有警徽流、没有警上警下之分。", card)
```

(import 区补 `rules_v1_2`、`GUARD_SEATS` 所需名字,沿用该文件现有 import 风格。)

- [ ] **Step 2: 跑确认失败** — guard 板断言失败(假话行仍在)

- [ ] **Step 3: 实现(build_board_rules_card)**

把 `:53-59` 的固定 lines.append 改为:

```python
    lines.append(
        "胜负规则:所有狼人出局→好人阵营胜;狼人数量达到或超过其余存活玩家数→狼人阵营胜。"
    )
    if counts.get("guard", 0):
        lines.append(
            "守护规则:守卫的守护可挡住当晚狼人袭击;同一名玩家同一晚既被守卫守护又被女巫解药救治,"
            "仍然死亡(同守同救)。守卫可以守自己,不能连续两晚守同一人,也不会得知守护是否成功。"
        )
        lines.append(
            "本局不存在的机制:没有警长竞选、没有警徽流、没有警上警下之分。"
            "上面能力表就是本局的全部机制,不要据不存在的机制推理,也不要在发言中讨论它们。"
        )
    else:
        lines.append(
            "本局不存在的机制:没有警长竞选、没有警徽流、没有警上警下之分、没有守卫或守夜人。"
            "上面能力表就是本局的全部机制,不要据不存在的机制推理,也不要在发言中讨论它们。"
        )
```

(else 分支字符串与原文**逐字节相同**——从原文件复制,勿手敲。)

- [ ] **Step 4: 验证** — 新测试 PASS;`PYTHONPATH=src python -m unittest tests.test_prompt_versioning -v` → PASS(golden 字节锁绿 = 非守卫板恒等的机器证明);全量 0 FAIL

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/prompt_v2.py tests/test_prompt_v2.py
git commit -m "feat(l4): board-conditional rules card — guard boards drop the false no-guard line + publish 同守同救; non-guard boards byte-identical"
```

---

### Task 10: v3 发言 system prompt 板条件(prompt 字节雷 #2)

**Files:**
- Modify: `src/werewolf_eval/llm_providers.py:136-146`
- Test: `tests/test_prompt_v3_speech_guard.py`(新建)

- [ ] **Step 1: 写失败测试**

```python
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
        # golden 样本路径(board_card=None):字节必须保持现状
        text = build_speech_system_prompt_v3(_req(None))
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
```

(`ProviderRequest` 字段名以 `provider_contract.py` 为准;若构造还需其他必填字段,按其 dataclass 默认补齐。)

- [ ] **Step 2: 跑确认失败** — guard 板断言失败

- [ ] **Step 3: 实现(llm_providers.py)**

`build_speech_system_prompt_v3` 前加 helper(规则卡的守卫**能力行** `- 守卫(` 只在守卫在板时渲染——Task 9 的数据驱动行——比扫「守卫」二字精确,因为非守卫板的「没有守卫或守夜人」行也含该词):

```python
def _board_card_has_guard(board_card: str | None) -> bool:
    """True iff the board card lists the guard as an ON-BOARD role. Keyed to the
    rules-card role line format ('- 守卫(') — golden-locked, so the marker is
    stable; the plain substring '守卫' would false-positive on the standard
    board's '没有守卫或守夜人' line."""
    return bool(board_card) and "- 守卫(" in board_card
```

`build_speech_system_prompt_v3` 改:

```python
def build_speech_system_prompt_v3(request: ProviderRequest) -> str:
    # SYS-B4 §4 graded guidance (unchanged) + L4: on guard boards the anti-mechanic
    # line must not deny the guard. Non-guard boards keep the EXACT original bytes.
    if _board_card_has_guard(request.board_card):
        no_mech = "局内不存在表情、眼神、语气等信息,也没有警长等本局规则卡之外的机制,不要编造。"
    else:
        no_mech = "局内不存在表情、眼神、语气等信息,也没有警长、守卫等本局规则卡之外的机制,不要编造。"
    return (
        f"你是狼人杀里的 {request.actor}(第 {request.round} 轮,白天发言)。"
        f"请用自然口吻发言,3-5 句或 120-180 字,不要固定小标题,不要输出 JSON,直接说话。"
        f"发言应包含:当前局势判断、你怀疑或相信的对象、一个具体理由、本轮投票倾向。"
        f"{no_mech}"
    )
```

(else 分支字符串从原文件复制,逐字节一致;`request.board_card` 若 ProviderRequest 无此字段名,按实际字段名对齐——引擎在 `agent.decide(..., board_card=self._board_card)` 传入。)

- [ ] **Step 4: 验证** — 新测试 PASS;`tests.test_prompt_versioning` PASS(v3 golden `speech_villager_v3` 字节不动);全量 0 FAIL

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/llm_providers.py tests/test_prompt_v3_speech_guard.py
git commit -m "feat(l4): speech v3 board-conditional anti-mechanic line — guard boards stop denying the guard; non-guard bytes identical"
```

---

### Task 11: Golden 守卫板样本 + ledger bless

**Files:**
- Modify: `src/werewolf_eval/prompt_goldens.py`(`canonical_prompt_samples_v3` 追加)
- Modify: `docs/generated-games/prompt-version-ledger.json`(prompt_v3 条目追加哈希)
- Generated: `tools/generate_golden_prompts.py` 产出的 golden/*.txt 新文件

- [ ] **Step 1: 追加 v3 守卫样本(只增不改)**

`prompt_goldens.py` 顶部 import 区补 `rules_v1_2`;`canonical_prompt_samples_v3()` 返回列表**末尾**追加(既有 6 个样本一字不动):

```python
_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}
```

```python
        # ---- L4 guard-board additions (spec §6: new samples only; old hashes frozen) ----
        ("board_card_guard_6p", build_board_rules_card(rules_v1_2(), _GUARD_SEATS)),
        ("speech_villager_v3_guard_board", build_speech_system_prompt_v3(
            _req_with_board("p6", build_board_rules_card(rules_v1_2(), _GUARD_SEATS)))),
        ("action_guard_night",
         build_action_system_prompt(_req("p5", "night", ["guard_protect"], _ALIVE))),
        ("obs_v2_guard_night",
         _v2_text("p5", "guard", "villager", "night", {"p5": "guard"}, [])),
```

并加 helper(`_req` 旁):

```python
def _req_with_board(actor: str, board_card: str) -> ProviderRequest:
    r = _req(actor, "day", [], [], response_kind="speech")
    # frozen literal board card threaded the same way the engine does (decide(board_card=...))
    return replace(r, board_card=board_card)
```

(`from dataclasses import replace`;若 ProviderRequest 非 dataclass 或字段只读不可 replace,直接在 `_req_with_board` 里完整构造一个含 board_card 的 ProviderRequest。)

- [ ] **Step 2: 生成 golden + 跑锁(先红后 bless)**

Run: `PYTHONPATH=src python tools/generate_golden_prompts.py`
Run: `PYTHONPATH=src python -m unittest tests.test_prompt_versioning -v`
Expected: RULE 1 既有样本全绿(字节没动的机器证明);新样本因 ledger 缺哈希而红。

- [ ] **Step 3: bless ledger**

编辑 `docs/generated-games/prompt-version-ledger.json` 的 `prompt_v3` 条目:`golden_prompt_hashes` **追加** 4 个新样本名→SHA256(从生成器输出/测试报错中取),既有哈希一个不动;更新 `blessed_by`("l4-guard-arm plan Task 11")与 `blessed_at`(当日)。

- [ ] **Step 4: 验证** — `tests.test_prompt_versioning` 全绿;全量 0 FAIL;`git diff docs/generated-games/prompt-version-ledger.json` 确认只有追加行 + bless 字段。

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/prompt_goldens.py docs/generated-games/prompt-version-ledger.json
git add -A  # golden/*.txt 新生成文件(确认 git status 只含 golden 新文件后再执行)
git commit -m "feat(l4): golden guard-board samples (rules card / speech v3 / guard action / guard obs) + prompt_v3 ledger bless (append-only)"
```

---

### Task 12: `profile_config.ALLOWED_ROLES` + 暴露面契约

**Files:**
- Modify: `src/werewolf_eval/profile_config.py:53`
- Modify: 钉 roles 输出的测试(`tests/test_profile_config.py` 及 `tests/test_qt_observer_static_contract.py` 若涉及)

- [ ] **Step 1: 更新钉死测试(先红)**

Run: `grep -rn "sorted(ALLOWED_ROLES)\|\"roles\"" tests/test_profile_config.py tests/test_qt_observer_static_contract.py | head` 找到钉 `"roles"` 列表的断言,把期望改为含 `"guard"` 的排序列表:`["guard", "seer", "villager", "werewolf", "witch"]`(**不加 hunter**——它现在就不在,spec §4)。

- [ ] **Step 2: 跑确认失败** — 期望含 guard,实际无

- [ ] **Step 3: 实现**

```python
ALLOWED_ROLES: frozenset[str] = frozenset({"werewolf", "seer", "witch", "villager", "guard"})
```

(`:64` `_ROLE_TEAM` 派生自 `known_role_teams()` 按 ALLOWED_ROLES 过滤——Task 2 注册后自动含 guard,无需改。)

- [ ] **Step 4: 验证** — 相关测试 PASS;全量 0 FAIL

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py tests/test_qt_observer_static_contract.py
git commit -m "feat(l4): ALLOWED_ROLES += guard — capabilities roles exposure updated (hunter intentionally still excluded)"
```

---

### Task 13: 度量台 — 板感知幻觉词 + guard 指标 + 报验生存指标

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py`
- Test: `tests/test_l4_metrics.py`(新建)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_l4_metrics.py
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.ablation.metrics import analyze_game_dict, aggregate_games, classify_event


def _ev(rnd, phase, etype, actor, target, summary):
    return {"event_id": f"e{rnd}{etype}", "sequence": 0, "round": rnd, "phase": phase,
            "type": etype, "actor": actor, "target": target, "visibility": "internal",
            "data": {"summary": summary}}


def _guard_game(speech_text="大家好"):
    players = [
        {"player_id": "p1", "role": "werewolf"}, {"player_id": "p2", "role": "werewolf"},
        {"player_id": "p3", "role": "seer"}, {"player_id": "p4", "role": "witch"},
        {"player_id": "p5", "role": "guard"}, {"player_id": "p6", "role": "villager"},
    ]
    events = [
        _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."),
        _ev(1, "night", "werewolf_kill", "p1", "p3", "Wolf team kills p3."),
        _ev(1, "day", "day_announcement", "system", "none", "A peaceful night: nobody died."),
        _ev(1, "day", "player_speech", "p6", "none", speech_text),
        _ev(2, "night", "guard_protect", "p5", "p6", "Guard p5 protects p6."),
        _ev(2, "night", "werewolf_kill", "p1", "p4", "Wolf team kills p4."),
        _ev(2, "night", "player_died", "system", "p4", "p4 died during the night."),
    ]
    return {"players": players, "events": events,
            "result": {"winner": "werewolf", "end_round": 2}}


class ClassifyGuardEventsTests(unittest.TestCase):
    def test_guard_and_peaceful_kinds(self):
        kind, actor, tgt, _ = classify_event(
            _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."))
        self.assertEqual((kind, actor, tgt), ("guard", "p5", "p3"))
        kind, _, _, _ = classify_event(
            _ev(1, "day", "day_announcement", "system", "none", "A peaceful night: nobody died."))
        self.assertEqual(kind, "peaceful")


class GuardMetricsTests(unittest.TestCase):
    def test_per_game_guard_metrics(self):
        row = analyze_game_dict(_guard_game())
        self.assertEqual(row["guard_nights"], 2)
        self.assertEqual(row["guard_target_seer_share"], 0.5)   # r1 守 seer p3
        self.assertEqual(row["guard_block_share"], 0.5)         # r1 守==刀
        self.assertEqual(row["n_peaceful_nights"], 1)
        self.assertEqual(row["seer_death"], None)               # seer 没死

    def test_guard_board_mechanic_words_exclude_guard(self):
        # 守卫板上正当讨论守卫 ≠ 机制幻觉;警长仍是幻觉词
        row = analyze_game_dict(_guard_game(speech_text="我觉得守卫昨晚守对了"))
        self.assertFalse(row["has_mechanic_halluc"])
        row2 = analyze_game_dict(_guard_game(speech_text="警长应该带队"))
        self.assertTrue(row2["has_mechanic_halluc"])

    def test_non_guard_board_words_unchanged(self):
        g = _guard_game(speech_text="守卫会救我们")
        for p in g["players"]:
            if p["role"] == "guard":
                p["role"] = "villager"
        g["events"] = [e for e in g["events"] if e["type"] != "guard_protect"]
        row = analyze_game_dict(g)
        self.assertTrue(row["has_mechanic_halluc"])   # 无守卫板:守卫仍是幻觉词

    def test_aggregate_keys(self):
        agg = aggregate_games([analyze_game_dict(_guard_game())])
        self.assertEqual(agg["guard_target_seer_rate"], 0.5)
        self.assertEqual(agg["guard_success_rate"], 0.5)
        self.assertEqual(agg["avg_peaceful_nights"], 1.0)
        self.assertEqual(agg["seer_death_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑确认失败**

- [ ] **Step 3: 实现(metrics.py)**

1. `:7` 后加:

```python
# 守卫板上「守卫/守夜人」是真实机制,不是幻觉词(L4);非守卫板维持原词表
GUARD_BOARD_MECHANIC_WORDS = ("警徽", "警长", "警上", "警下")
```

2. `classify_event` 在 `night_death` 分支前加:

```python
    m = re.match(r"Guard (p\d) protects (p\d)", s)
    if m: return ("guard", m.group(1), m.group(2), None)
    if "A peaceful night" in s: return ("peaceful", "system", None, None)
```

3. `analyze_game_dict`:循环前加 `guards_by_round: dict = {}` 与 `peaceful = 0`;分支加:

```python
        elif kind == "guard": guards_by_round[r] = t
        elif kind == "peaceful": peaceful += 1
```

`text_all` 行后:

```python
    has_guard = "guard" in roles.values()
    mech_words = GUARD_BOARD_MECHANIC_WORDS if has_guard else MECHANIC_WORDS
    gn = len(guards_by_round)
```

返回 dict 加(`"seer_death_cause"` 行附近):

```python
        "seer_death": list(seer_death) if seer_death else None,   # (round, cause) — claim 生存回算用
        "guard_nights": gn,
        "guard_target_seer_share": (sum(1 for t in guards_by_round.values() if t == seer) / gn) if gn else None,
        "guard_block_share": (sum(1 for r2, t in guards_by_round.items() if kills.get(r2) == t) / gn) if gn else None,
        "n_peaceful_nights": peaceful,
```

`has_mechanic_halluc` / `n_mechanic_speeches` 两处 `MECHANIC_WORDS` → `mech_words`。

4. 报验生存指标(文件尾部新函数,`parse_scribe_claims` 复用):

```python
def seer_claim_rounds(run_dir, seer: str) -> list[int]:
    """Rounds where the TRUE seer publicly claimed (any check_report, or an
    identity_claim whose result mentions 预言), parsed from the scribe turns in
    provider-trace.json. Non-v3 runs (no scribe) -> []."""
    from werewolf_eval.prompt_v3 import parse_scribe_claims
    p = Path(run_dir) / "provider-trace.json"
    if not p.exists():
        return []
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    turns = doc.get("provider_turns") if isinstance(doc, dict) else doc
    rounds: set[int] = set()
    for t in turns or []:
        if t.get("actor") != "scribe":
            continue
        claims = parse_scribe_claims(t.get("raw_content") or "") or []
        for c in claims:
            if c["claimant"] != seer:
                continue
            if c["claim_type"] == "check_report" or (
                    c["claim_type"] == "identity_claim" and "预言" in str(c.get("result") or "")):
                rounds.add(int(t.get("round", 0)))
                break
    return sorted(rounds)


def seer_claim_to_night_survival(run_dir, row: dict) -> bool | None:
    """First public seer claim at round r: did the seer survive night r+1?
    None when no claim, no seer, or the game ended before night r+1 (no exposure)."""
    seer = row.get("seer")
    if not seer:
        return None
    rounds = seer_claim_rounds(run_dir, seer)
    if not rounds:
        return None
    r = rounds[0]
    if (row.get("end_round") or 0) <= r:
        return None
    sd = row.get("seer_death")
    return not (sd is not None and int(sd[0]) == r + 1 and sd[1] == "night")
```

5. `aggregate()` 循环内 `row["scaffold_coverage"] = cov` 后加:

```python
        row["seer_claimed_then_survived_night"] = seer_claim_to_night_survival(d, row)
```

6. `aggregate_games` 返回 dict 加:

```python
        "guard_target_seer_rate": _mean([g.get("guard_target_seer_share") for g in games]),
        "guard_success_rate": _mean([g.get("guard_block_share") for g in games]),
        "avg_peaceful_nights": _mean([g.get("n_peaceful_nights") for g in games]),
        "seer_death_rate": rate(lambda g: g.get("seer_death") is not None),
        "seer_night_death_rate": rate(lambda g: (g.get("seer_death") or [None, None])[1] == "night"),
        "seer_claim_to_night_survival_rate": _mean(
            [g.get("seer_claimed_then_survived_night") for g in games]),
        "seer_claim_to_night_survival_n": sum(
            1 for g in games if g.get("seer_claimed_then_survived_night") is not None),
```

(`_mean` 已过滤 None;bool 可求和。)

7. `DEFAULT_COMPARE_KEYS` 追加:`"seer_death_rate","seer_night_death_rate","seer_claim_to_night_survival_rate","guard_target_seer_rate","guard_success_rate","avg_peaceful_nights"`。

`seer_death` 元组化注意:`analyze_game_dict` 现有局部变量 `seer_death` 即 `(round, cause)`,直接复用。

- [ ] **Step 4: 验证** — `tests.test_l4_metrics` PASS;既有 metrics 测试(`ls tests | grep -i metric`)PASS;全量 0 FAIL

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_l4_metrics.py
git commit -m "feat(l4): board-aware mechanic words + guard metrics (target-seer/success/peaceful) + seer-claim night-survival metric"
```

---

### Task 14: 臂配置 — `Arm.multiset` + `l4_guard` 臂 + CLI `--board`

**Files:**
- Modify: `src/werewolf_eval/ablation/arms.py`
- Modify: `src/werewolf_eval/ablation/__main__.py`
- Test: `tests/test_l4_arm_layout.py`(新建)

- [ ] **Step 1: 写失败测试(钉死值已预计算,真实 RNG 复算核对过)**

```python
# tests/test_l4_arm_layout.py
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
```

- [ ] **Step 2: 跑确认失败** — ImportError(GUARD_MULTISET / multiset 字段)

- [ ] **Step 3: 实现**

`arms.py`:

```python
CANONICAL_MULTISET = ("werewolf", "werewolf", "seer", "witch", "villager", "villager")
# L4 守卫板:6p 保护型结构替换臂(换一个民,spec §1 — NOT a pure addition)
GUARD_MULTISET = ("werewolf", "werewolf", "seer", "witch", "guard", "villager")
```

`Arm` 加字段(末尾):

```python
    multiset: tuple[str, ...] = CANONICAL_MULTISET  # per-arm board (l4_guard swaps a villager for the guard)
```

`layout_for` 的 `roles = list(CANONICAL_MULTISET)` → `roles = list(arm.multiset)`。

`__main__.py` `_run`:

```python
from werewolf_eval.ablation.arms import Arm, CANONICAL_MULTISET, GUARD_MULTISET
_BOARDS = {"standard": CANONICAL_MULTISET, "guard": GUARD_MULTISET}
```

```python
    arm = Arm(label=a.label, prompt_version=a.prompt_version, n_games=a.n,
              seed_base=a.seed_base, model=a.model, multiset=_BOARDS[a.board])
```

argparse 加:

```python
    r.add_argument("--board", choices=sorted(_BOARDS), default="standard")
```

- [ ] **Step 4: 验证** — `tests.test_l4_arm_layout` PASS;全量 0 FAIL。
冒烟(不打 API):`PYTHONPATH=src python -m werewolf_eval.ablation run smoke --board guard --n 1 --api-key-env NO_SUCH_ENV 2>&1 | head -2` → 输出 `missing NO_SUCH_ENV`(CLI 接线通)。

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/ablation/arms.py src/werewolf_eval/ablation/__main__.py tests/test_l4_arm_layout.py
git commit -m "feat(l4): Arm.multiset + GUARD_MULTISET + ablation CLI --board guard (default arms byte-identical, seed-paired)"
```

---

### Task 15: b4 基线回算(spec §8 前置硬步骤)

**Files:**
- Create: `tools/backfill_seer_claim_metrics.py`
- Create: `docs/harness/reviews/2026-06-11-l4-baseline-backfill.json`

注意:`.runs/ablation/b4/` 只存在于**主树**(gitignored,不进 worktree)。本 task 在 worktree 写代码、用绝对路径读主树数据;输出 JSON 提交进 worktree 分支。

- [ ] **Step 1: 先验证真实产物形状(provider-trace 的 scribe turn 键名)**

Run:
```bash
PYTHONPATH=src python -c "
import json
from pathlib import Path
doc = json.loads(Path('G:/Werewolf-agent/.runs/ablation/b4/b4_000/provider-trace.json').read_text(encoding='utf-8'))
turns = doc.get('provider_turns') if isinstance(doc, dict) else doc
sc = [t for t in (turns or []) if t.get('actor') == 'scribe']
print('n_scribe', len(sc))
print(sorted(sc[0].keys()) if sc else 'NO SCRIBE TURNS')
"
```
Expected: 列出 scribe turn 的键(应含 `actor`、`raw_content`、`round` 同义键)。**若键名与 Task 13 的 `seer_claim_rounds` 实现不符(如 round 在 `request_id` 里、raw_content 叫别名),回 Task 13 的函数修键名并补一条以真实键名为形状的单测,然后再继续。**

- [ ] **Step 2: 写回算工具**

```python
# tools/backfill_seer_claim_metrics.py
"""One-shot backfill (spec §8 前置): compute the L4 seer-survival metric family on
EXISTING arm runs (b4/b1) so the l4_guard arm has a paired baseline. Read-only over
.runs; prints one JSON object per arm dir given."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.ablation import metrics

KEYS = ("n_valid", "n_total", "seer_death_rate", "seer_night_death_rate",
        "seer_claim_to_night_survival_rate", "seer_claim_to_night_survival_n",
        "guard_target_seer_rate", "guard_success_rate", "avg_peaceful_nights",
        "wolf_win_rate")


def backfill(arm_dir: Path) -> dict:
    run_dirs = sorted(d for d in arm_dir.iterdir()
                      if d.is_dir() and (d / "game-log.json").exists())
    agg = metrics.aggregate(run_dirs)
    return {"arm_dir": arm_dir.name, **{k: agg.get(k) for k in KEYS}}


def main(argv: list[str]) -> int:
    out = [backfill(Path(p)) for p in argv]
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 3: 跑回算 + 落快照**

Run:
```bash
PYTHONPATH=src python tools/backfill_seer_claim_metrics.py G:/Werewolf-agent/.runs/ablation/b4 G:/Werewolf-agent/.runs/ablation/b1 > docs/harness/reviews/2026-06-11-l4-baseline-backfill.json
cat docs/harness/reviews/2026-06-11-l4-baseline-backfill.json
```
Expected: b4 的 `n_valid=40`(与 verdict 一致 = 度量台口径没漂);`seer_death_rate≈0.825`(33/40,verdict 交叉验证);`seer_claim_to_night_survival_*` 给出非空基线;b4/b1 的 `guard_*` 为 null(无守卫板)、`wolf_win_rate` 与 verdict 一致(0.875/0.933)。**任何交叉验证不符 = 停下报告,不强行落档。**(b1 若无 scribe 产物,其 claim 指标为 null——可接受,b4 是主对照。)

- [ ] **Step 4: Commit**

```bash
git add tools/backfill_seer_claim_metrics.py docs/harness/reviews/2026-06-11-l4-baseline-backfill.json
git commit -m "feat(l4): b4/b1 seer-survival baseline backfill (spec §8 prerequisite) — cross-checked against b4 verdict numbers"
```

---

### Task 16: 收口 — 全量回归 + tree + 合并门材料

- [ ] **Step 1: 全量回归** — `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3` → 0 FAIL(基准 1107 + 本 plan 新增,期望 ~1140+)
- [ ] **Step 2: 新文件刷 tree** — `node .codex/hooks/tree.mjs --force`(在 worktree 内)
- [ ] **Step 3: 验证报告(AGENTS.md Validation 节)** — `git diff main --stat` / `--name-only`;allowlist 核对:仅 `src/werewolf_eval/{action_runtime/*,emergent_engine.py,runtime_events.py,prompt_v2.py,llm_providers.py,prompt_goldens.py,display_labels.py,observer_visibility.py,profile_config.py,provider_agent.py,invariants/checker.py,ablation/*}`、`tests/*`、`tools/backfill_seer_claim_metrics.py`、`docs/generated-games/prompt-version-ledger.json`(append-only)、`docs/harness/reviews/2026-06-11-l4-baseline-backfill.json`、golden 新 txt、tree.md。**禁区核对:settler.py 零改动;rules_v1/rules_v1_1 函数体零改动;prompt_v1/v2 golden 既有哈希零改动;clients/** 零改动;max_day_rounds 零改动。**
- [ ] **Step 4: Commit + 请求 code review**(superpowers:requesting-code-review;review 后走合并门)

---

### Task 17(合并后,主树,用户触发):45 局 live + verdict

**不在 worktree 执行;先读 `.agents/skills/running-live-games/SKILL.md`。**

- [ ] **Step 1: 跑臂**

```bash
PYTHONPATH=src python -m werewolf_eval.ablation run l4_guard --prompt-version prompt_v3 --board guard --n 45 --seed-base 1000
```
(预算参考 b4:~1016 请求/977K tokens/40 分钟;守卫每夜 +1 请求,仍远低于 per-game cap。)

- [ ] **Step 2: 有效性与不变量** — n_valid 口径同 b4(live≥0.7 + coverage 门);45 局产物全跑 `check_run`(I1-I8c 必须 0 违例,任何 I8 违例=阻断,先修后重跑)。
- [ ] **Step 3: 快照 + 对照表** — `_metrics.json` 复制为 `docs/harness/reviews/2026-06-XX-l4-guard-metrics.json`;`python -m werewolf_eval.ablation compare` 对 b4;按 spec §8 判据(主判据=报验生存窗口族,方向门=狼胜 ≤65% 强通过/≤75%+主判据改善=可接受)写 verdict 文档,**解释口径=「6p 保护型结构替换臂」**(spec §1),交用户裁决。

---

## Self-Review 记录

- **Spec 覆盖:** §2 守卫细则→T1/T4/T5;§3 rules_v1_2→T1/T2;§4 引擎+名单面→T3/T5/T7/T12;§5 臂配置→T14;§6 prompt v3-only→T9/T10/T11;§7 指标+I8→T8/T13;§8 判据+回算前置→T15/T17;§9 测试矩阵→各 task;§10 Out of scope→禁区核对(T16)。spec「claim ledger 词汇/vote scaffold 能力表」项:`VOTE_PROGRAM` 与 claim 类型均为角色无关文本,守卫声称走 `identity_claim` 泛型路径,**零改动即满足**(v3 golden 因此天然安全)——已核对 prompt_v3.py 全文。
- **既知风险:** ① T11 `ProviderRequest` 构造细节(replace vs 直构)留了双路;② T15 trace 键名留了真实形状验证步;③ T5 `_act`/fake-script 对 guard 的泛型支持依赖 ProviderAgent 同款路径(seer 先例),若 fake agent 内有 per-action 白名单,按 witch_pass 的 json.dumps 旁路写 guard 条目。
- **类型一致性:** `last_guarded_target`(state 字段)/`self._last_guarded`(engine 属性)/`GUARD_MULTISET`/`guard_protect` 命名全 plan 一致;I8 检查读 `guard_protect` 事件 = GuardResolver render 的 etype;layout 钉死值经真实 RNG 复算。
