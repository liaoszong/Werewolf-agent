# SYS-B1 Prompt 版本接缝 — PromptRenderer 注册表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 执行者必须先读 `.agents/skills/guarding-prompt-bytes/SKILL.md` 与 `.agents/skills/committing-in-shared-worktrees/SKILL.md`。

**Goal:** 把散在 10 处的 prompt_v1/v2/v3 版本 if/else 收成一个「版本 → PromptRenderer 适配器」注册表,全链字节恒等(golden 0 变化、PROMPT_VERSION 不翻、ledger 不动)。

**Architecture:** 新模块 `prompt_renderers.py` 持有 RendererV1/V2/V3 三个适配器 + registry;v1 渲染件移居新模块 `prompt_v1.py`(verbatim move,旧址 re-export),v2/v3 speech builder 移回各自版本模块,消除 import 环。引擎与 provider 只持有适配器,不再各自 if/else;v3 的「需要 scribe」从 3 处字面量判断收成适配器上的 `requires_scaffold` 标志。

**Tech Stack:** Python(src-layout `werewolf_eval`)、pytest/unittest、既有 golden 字节锁(`tests/test_prompt_versioning.py` RULE 1/2/3)、fake runtime 字节门。

---

## §0 设计前言(替代 spec;评审一次,以下 D1–D6 是裁决点)

### 0.1 分叉清单(走查实测:评审 HTML 写的是 v1/v2 五处;B4 落地 prompt_v3 后实际是三版本 10 处)

| # | 位置 | 分叉内容 | 收口去向 |
|---|------|----------|----------|
| 1 | `emergent_engine.py:319-322` | unknown version fail-loud | `get_renderer()` 统一 fail-loud(报错文本不变) |
| 2 | `emergent_engine.py:324-328` | `if v in ("prompt_v2","prompt_v3")` 建 board_card | `renderer.board_card(ruleset, seat_roles)`(v1 返回 `""`) |
| 3 | `emergent_engine.py:332-333` | v3 必须有 scaffold_agent | `renderer.requires_scaffold` 标志 |
| 4 | `emergent_engine.py:544-548` | `_render_obs` v2/v3 vs v1 | `renderer.render_observation(obs, events_by_id)` |
| 5 | `emergent_engine.py:596-600` | v3 白天投票注入 vote scaffold | `renderer.action_obs_suffix(phase, claim_ledger)` |
| 6 | `emergent_engine.py:923-926` | v3 发言注入 claim digest | `renderer.speech_obs_suffix(claim_ledger)` |
| 7 | `emergent_engine.py:1200-1201` | v3 才跑 scribe | `renderer.requires_scaffold` 门 |
| 8 | `llm_providers.py:257-280` | `_system_for` speech 契约三选一 | `renderer.speech_contract(request)` |
| 9 | `run_emergent_deepseek_game.py:132-136` | v3 必须有 scaffold factory | `renderer.requires_scaffold` |
| 10 | `ablation/harness.py:42-43, 63-65` | v3 缺省 scribe 工厂 + 传参门 | `renderer.requires_scaffold` |

不属于版本分叉、**明确不动**的:`build_action_system_prompt`、`compose_system`、`build_scribe_system_prompt`(按 response_kind 分支,版本无关)、`augment_witch_observation` / `HUNTER_SHOT_OBSERVATION_SUFFIX`(版本无关的内联增强,v1/v2 文本都叠加,留在引擎)、goldens 的三个样本函数(版本专属内容,不是分叉)、引擎 `self.prompt_version` 属性(manifest/request 盖戳要用,保留)。

### 0.2 裁决点

- **D1 — registry 放新模块 `prompt_renderers.py`,不放 `prompt_version.py`。** 评审 HTML 提议放 prompt_version.py;但该文件的 docstring 是字节锁权威、被 llm_providers/engine/harness 多方 import,塞入会引入 prompt_v2→action_runtime 的传递依赖,冷启动环风险(SYS-A2 踩过 action_runtime↔game_engine 真环)。prompt_version.py 保持极小常量文件**零改动**。
- **D2 — 单源靠哨兵不靠反向 import。** `KNOWN_PROMPT_VERSIONS` 保持字面量;新增哨兵测试钉 `tuple(REGISTRY) == KNOWN_PROMPT_VERSIONS`(含顺序)。漂移=测试红,与 SYS-A2/D-4 的哨兵网手法一致。
- **D3 — v1 渲染件移居 `prompt_v1.py`(verbatim move)。** `RenderedObservation` + `render_observation_text` 出 `emergent_engine.py`(L116-167),`build_speech_system_prompt` 出 `llm_providers.py`(L110-118);v2/v3 speech builder(含 `_board_card_has_guard`)分别移入 `prompt_v2.py`/`prompt_v3.py`。否则 registry 要 import 引擎和 provider,而引擎和 provider 要 import registry——真环。旧址一律保留 import 即 re-export(已核实消费方:`prompt_goldens.py`、`tests/test_p2a2_live_path.py`、`tests/test_prompt_v2.py`)。函数体逐字搬移;唯一允许的差异是注解(`obs: AgentObservation → Any`,沿 prompt_v2 先例),注解不是模型可见字节。
- **D4 — 适配器用普通类 + 继承表达真实关系。** V3 继承 V2(v3 确实复用 v2 的 obs 渲染和 board card),V2 继承 V1 的 no-op suffix。无 ABC 仪式,与 `RoleAbilityRegistry` 风格一致。
- **D5 — 字节恒等是硬验收。** golden 目录 0 变化(RULE 1/2/3 全绿,不 regen、不翻版本、不动 ledger);v1 fake 局工件前后字节恒等;v3 注入文本的拼接字节(`"\n" + render_vote_scaffold(...)` 等)由新单测逐字钉死。
- **D6 — 与 B-2 并行的错峰约束。** B-2(worktree `b2-engine-visibility-single-source`)的提取区是 `emergent_engine.py` 的 `_public_refs/_private_refs/_build_obs`(L359-543),本计划碰 `__init__`/`_render_obs`(L544+)/散点,函数级不重叠但 `_build_obs`/`_render_obs` 文本相邻、import 块必然双方都改。**合并前必须**:确认 B-2 是否已合 main → rebase → 重跑 Task 8 全部门。若 T17 live 批次在跑,遵守 merge hold,worktree 内作业不受限。

### 0.3 import 图(无环证明)

```
prompt_version.py(叶,零改动)
provider_contract.py(叶,已核实零项目 import)
prompt_v1.py  → provider_contract(仅注解)
prompt_v2.py  → action_runtime.ruleset(现状已有)
prompt_v3.py  → (json,无项目依赖;新增 provider_contract 仅注解)
prompt_renderers.py → prompt_version + prompt_v1 + prompt_v2 + prompt_v3
llm_providers.py    → prompt_renderers(+ 从 v1/v2/v3 re-export 三个 speech builder)
emergent_engine.py  → prompt_renderers + prompt_v1(re-export)+ prompt_v3(scribe 件,现状已有)
```

冷启动验证:Task 8 跑全量(含 SYS-A2 留下的 ColdImport 测试)。

### 0.4 验收门(全部满足才可合并)

1. `pytest tests/ -q` 全绿(基线 ~1219 OK)。
2. `git diff --exit-code tests/golden_prompts/` 空;`docs/generated-games/prompt-version-ledger.json` 零改动;`PROMPT_VERSION` 不翻。
3. v1 fake 局字节门:Task 1 基线 vs Task 8 复跑,`diff -r` 空(扣除 Task 1 实测的非确定性路径)。
4. 新哨兵/等价测试全绿(`tests/test_prompt_renderers.py`)。
5. allowlist 之外零文件变化(见 §0.5)。

### 0.5 改动面 allowlist

```
src/werewolf_eval/prompt_v1.py          (新)
src/werewolf_eval/prompt_renderers.py   (新)
src/werewolf_eval/prompt_v2.py          (+speech builder 移入)
src/werewolf_eval/prompt_v3.py          (+speech builder 移入)
src/werewolf_eval/emergent_engine.py    (分叉 1-7 收口)
src/werewolf_eval/llm_providers.py      (分叉 8 收口 + re-export)
src/werewolf_eval/run_emergent_deepseek_game.py (分叉 9)
src/werewolf_eval/ablation/harness.py   (分叉 10)
src/werewolf_eval/prompt_goldens.py     (仅 import 行改指新址,样本字节不动)
tests/test_prompt_renderers.py          (新)
docs/harness/plans/2026-06-11--sys-b1-prompt-renderer-registry-plan.md
.oh-my-harness/tree.md                  (hook 再生)
```

禁区:`prompt_version.py`、`tests/golden_prompts/**`、ledger、`game_engine.py`、`observer_*`、`action_runtime/**`、scoring、`docs/ROADMAP.md`、`docs/TASKS.md`。

---

## Task 1: v1 fake 局字节基线(不产生 commit)

**Files:** none committed(全在 `.tmp/`,gitignored;结束后核 `git status --short` 干净)

- [ ] **Step 1: 跑两次确定性基线**

```bash
cd /g/Werewolf-agent/.claude/worktrees/sys-b1-prompt-renderer-registry
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --game-id b1pr_gate --out-dir .tmp/b1pr-base-1 --seed 7
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --game-id b1pr_gate --out-dir .tmp/b1pr-base-2 --seed 7
diff -r .tmp/b1pr-base-1 .tmp/b1pr-base-2
```

Expected: diff 为空(完全确定性)。若个别文件 run-to-run 不同(如 runtime 工件里的墙钟时间戳),把这些路径记入 `.tmp/b1pr-nondet-paths.txt`,Task 8 的字节门**恰好排除这些路径**并在汇报中说明。`game-log.json` / `decision-log.json` / `provider-trace.json` 必须在确定性集合内;不在则 STOP 报 BLOCKED。

- [ ] **Step 2: 基线测试计数**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q 2>&1 | tail -3
```

Expected: 全绿,记录通过数(预期 ~1219,以实际为准,Task 8 对照)。

## Task 2: `prompt_v1.py` — v1 渲染件 verbatim 迁出

**Files:**
- Create: `src/werewolf_eval/prompt_v1.py`
- Modify: `src/werewolf_eval/emergent_engine.py:116-167`(删除两定义,顶部加 import)
- Modify: `src/werewolf_eval/llm_providers.py:110-118`(删除定义,顶部加 import)

- [ ] **Step 1: 新建 `src/werewolf_eval/prompt_v1.py`**

`RenderedObservation`(原 emergent_engine.py:116-122)、`render_observation_text`(原 :125-167)、`build_speech_system_prompt`(原 llm_providers.py:110-118)**函数体逐字复制**——从当前文件复制,不要凭记忆重打。文件骨架:

```python
"""prompt_v1 (baseline): the byte-locked v1 observation renderer and speech
contract, moved VERBATIM from emergent_engine.py / llm_providers.py so the
PromptRenderer registry (prompt_renderers.py) can package all versions without
an import cycle (engine/providers import the registry; the registry imports US).
The move is NOT a version bump — bytes stay locked by
tests/golden_prompts/prompt_v1; any byte change still requires the full
versioning flow (see prompt_version.py docstring)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from werewolf_eval.provider_contract import ProviderRequest

# <<< RenderedObservation 原文(emergent_engine.py:116-122)>>>
# <<< render_observation_text 原文(emergent_engine.py:125-167),
#     仅签名注解 obs: AgentObservation 改为 obs: Any(prompt_v2 先例,避免 game_engine import)>>>
# <<< build_speech_system_prompt 原文(llm_providers.py:110-118)>>>
```

- [ ] **Step 2: `emergent_engine.py` 删除 L116-122 与 L125-167,在 import 区(L53-55 邻近)加:**

```python
from werewolf_eval.prompt_v1 import RenderedObservation, render_observation_text
```

(import 即 re-export:`from werewolf_eval.emergent_engine import render_observation_text` 的既有消费方——prompt_goldens、test_p2a2_live_path——不破。`augment_witch_observation` 与 `HUNTER_SHOT_OBSERVATION_SUFFIX` **留在原处不动**。)

- [ ] **Step 3: `llm_providers.py` 删除 L110-118 的 `build_speech_system_prompt`,在 import 区加:**

```python
from werewolf_eval.prompt_v1 import build_speech_system_prompt
```

- [ ] **Step 4: 验证字节锁与消费方**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_versioning.py tests/test_prompt_v2.py tests/test_p2a2_live_path.py tests/test_emergent_engine.py -q
git diff --exit-code tests/golden_prompts/
```

Expected: 全绿 + 空 diff。(若 `tests/test_emergent_engine.py` 文件名不存在,用 `ls tests/ | grep -i emergent` 找对应套件替换并汇报。)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/prompt_v1.py src/werewolf_eval/emergent_engine.py src/werewolf_eval/llm_providers.py
git status --short   # 确认无非本任务 staged 项
git commit -m "refactor(prompt): move v1 renderer/speech contract to prompt_v1.py verbatim (re-export at old homes, goldens unchanged)"
```

## Task 3: v2/v3 speech builder 移回版本模块

**Files:**
- Modify: `src/werewolf_eval/prompt_v2.py`(文件尾追加)
- Modify: `src/werewolf_eval/prompt_v3.py`(文件尾追加)
- Modify: `src/werewolf_eval/llm_providers.py:121-160`(删除三定义,加 import)
- Modify: `src/werewolf_eval/prompt_goldens.py:21-30`(import 改指新址)

- [ ] **Step 1: `build_speech_system_prompt_v2`(llm_providers.py:121-133 原文)移入 `prompt_v2.py` 尾部**;`_board_card_has_guard`(:136-141 原文)与 `build_speech_system_prompt_v3`(:144-160 原文)移入 `prompt_v3.py` 尾部。两处签名注解 `request: ProviderRequest` 保留(provider_contract 是叶模块,直接 import)。函数体逐字复制。

- [ ] **Step 2: `llm_providers.py` 删除三个定义,import 区改为:**

```python
from werewolf_eval.prompt_v1 import build_speech_system_prompt
from werewolf_eval.prompt_v2 import build_speech_system_prompt_v2
from werewolf_eval.prompt_v3 import build_speech_system_prompt_v3
```

(`_system_for` 本 Task 不动——它仍直调这三个名字,行为零变化;re-export 保住 prompt_goldens/tests 旧 import 路径。)

- [ ] **Step 3: `prompt_goldens.py` 的 import 改指新址**(L21-28 的 llm_providers 块里去掉 v2/v3 两行;v2/v3 行并入 L29-30 的版本模块 import)。样本函数体一个字节不动。

- [ ] **Step 4: 验证**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_versioning.py tests/test_prompt_v2.py tests/test_prompt_v3.py tests/test_prompt_v3_speech_guard.py tests/test_guard_sentinels.py -q
git diff --exit-code tests/golden_prompts/
```

Expected: 全绿 + 空 diff。

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/prompt_v2.py src/werewolf_eval/prompt_v3.py src/werewolf_eval/llm_providers.py src/werewolf_eval/prompt_goldens.py
git status --short
git commit -m "refactor(prompt): speech contract builders live with their version modules (llm_providers re-exports, bytes unchanged)"
```

## Task 4: `prompt_renderers.py` + 哨兵/等价测试(TDD)

**Files:**
- Create: `tests/test_prompt_renderers.py`
- Create: `src/werewolf_eval/prompt_renderers.py`

- [ ] **Step 1: 先写测试 `tests/test_prompt_renderers.py`**

```python
"""PromptRenderer registry sentinels + byte-equivalence vs the underlying
version functions. The REGISTRY is the single seam: these tests pin (a) the
registry/version-tuple cannot drift, (b) each adapter is byte-identical to the
functions it packages, (c) the v3 injection suffixes reproduce the engine's
historical f-string composition exactly."""
import unittest

from werewolf_eval.prompt_renderers import REGISTRY, get_renderer
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS
from werewolf_eval.prompt_v1 import build_speech_system_prompt, render_observation_text
from werewolf_eval.prompt_v2 import build_speech_system_prompt_v2, build_board_rules_card, render_observation_text_v2
from werewolf_eval.prompt_v3 import build_speech_system_prompt_v3, render_claim_digest, render_vote_scaffold
from werewolf_eval.action_runtime.ruleset import rules_v1_1
from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.provider_contract import ProviderRequest

_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
          "p4": "witch", "p5": "villager", "p6": "villager"}
_EVENTS = {
    "e1": {"event_id": "e1", "sequence": 1, "round": 1, "phase": "night",
           "type": "werewolf_kill", "actor": "p1", "target": "p5",
           "visibility": "werewolf_team", "data": {"summary": "Wolf team kills p5."}},
    "e2": {"event_id": "e2", "sequence": 2, "round": 1, "phase": "day",
           "type": "day_announcement", "actor": "system", "target": "none",
           "visibility": "public", "data": {"summary": "Night fell: p5 died."}},
}
_CLAIMS = [{"round": 1, "claimant": "p3", "claim_type": "check_report",
            "target": "p1", "result": "werewolf", "refutes": None, "source": 1,
            "source_quote": "昨晚验了p1,他是狼人", "uncertain": False}]


def _obs(player_id="p1", role="werewolf", team="werewolf", phase="night"):
    return AgentObservation(
        game_id="t", player_id=player_id, role=role, team=team, phase=phase,
        round=1, alive_players=["p1", "p2", "p3", "p4", "p5", "p6"],
        public_event_ids=["e2"], private_event_ids=["e1"],
        known_roles={"p1": "werewolf", "p2": "werewolf"},
    )


def _req(kind="speech"):
    return ProviderRequest(
        request_id="t", game_id="t", actor="p5", phase="day", round=1,
        observation={}, allowed_actions=[], allowed_targets=[], response_kind=kind,
    )


class RegistrySentinelTest(unittest.TestCase):
    def test_registry_matches_known_versions_in_order(self):
        self.assertEqual(tuple(REGISTRY), KNOWN_PROMPT_VERSIONS)

    def test_adapter_version_matches_its_key(self):
        for key, renderer in REGISTRY.items():
            self.assertEqual(renderer.version, key)

    def test_unknown_version_fails_loud(self):
        with self.assertRaises(ValueError) as ctx:
            get_renderer("prompt_v99")
        self.assertIn("unknown prompt_version", str(ctx.exception))

    def test_requires_scaffold_flags(self):
        self.assertFalse(REGISTRY["prompt_v1"].requires_scaffold)
        self.assertFalse(REGISTRY["prompt_v2"].requires_scaffold)
        self.assertTrue(REGISTRY["prompt_v3"].requires_scaffold)


class AdapterByteEquivalenceTest(unittest.TestCase):
    def test_v1_observation_identical(self):
        obs = _obs()
        self.assertEqual(
            get_renderer("prompt_v1").render_observation(obs, _EVENTS),
            render_observation_text(obs, _EVENTS),
        )

    def test_v2_v3_observation_identical(self):
        obs = _obs()
        text, ids = render_observation_text_v2(obs, _EVENTS)
        for v in ("prompt_v2", "prompt_v3"):
            rendered = get_renderer(v).render_observation(obs, _EVENTS)
            self.assertEqual(rendered.text, text)
            self.assertEqual(rendered.source_event_ids, ids)

    def test_board_card_dispatch(self):
        rs = rules_v1_1()
        self.assertEqual(get_renderer("prompt_v1").board_card(rs, _SEATS), "")
        expected = build_board_rules_card(rs, _SEATS)
        self.assertEqual(get_renderer("prompt_v2").board_card(rs, _SEATS), expected)
        self.assertEqual(get_renderer("prompt_v3").board_card(rs, _SEATS), expected)

    def test_speech_contract_dispatch(self):
        req = _req()
        self.assertEqual(get_renderer("prompt_v1").speech_contract(req),
                         build_speech_system_prompt(req))
        self.assertEqual(get_renderer("prompt_v2").speech_contract(req),
                         build_speech_system_prompt_v2(req))
        self.assertEqual(get_renderer("prompt_v3").speech_contract(req),
                         build_speech_system_prompt_v3(req))


class InjectionSuffixTest(unittest.TestCase):
    """钉死引擎历史拼接字节:f\"{obs_text}\\n{render_vote_scaffold(...)}\" 与
    f\"{obs_text}\\n{render_claim_digest(...)}\"(仅 ledger 非空)。"""

    def test_v1_v2_suffixes_empty(self):
        for v in ("prompt_v1", "prompt_v2"):
            r = get_renderer(v)
            self.assertEqual(r.action_obs_suffix("day", _CLAIMS), "")
            self.assertEqual(r.speech_obs_suffix(_CLAIMS), "")

    def test_v3_action_suffix_day_only(self):
        r = get_renderer("prompt_v3")
        self.assertEqual(r.action_obs_suffix("day", _CLAIMS),
                         "\n" + render_vote_scaffold(_CLAIMS))
        # 空账本时 vote scaffold 仍非空(「没有可记录的身份声称」+ 程序),与引擎旧行为一致
        self.assertEqual(r.action_obs_suffix("day", []),
                         "\n" + render_vote_scaffold([]))
        self.assertEqual(r.action_obs_suffix("night", _CLAIMS), "")

    def test_v3_speech_suffix_gated_on_nonempty_ledger(self):
        r = get_renderer("prompt_v3")
        self.assertEqual(r.speech_obs_suffix(_CLAIMS),
                         "\n" + render_claim_digest(_CLAIMS))
        self.assertEqual(r.speech_obs_suffix([]), "")
```

- [ ] **Step 2: 跑测确认失败**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_renderers.py -q
```

Expected: FAIL/ERROR — `No module named 'werewolf_eval.prompt_renderers'`。

- [ ] **Step 3: 新建 `src/werewolf_eval/prompt_renderers.py`**

```python
"""PromptRenderer registry (SYS-B1 seam): ONE version->adapter mapping replaces
the v1/v2/v3 if/else scattered across the engine, provider layer, launcher and
ablation harness. Each adapter packages a version's full model-visible surface:
board card, observation renderer, speech contract, and the v3 injection
suffixes. Adding prompt_v4 = one adapter class + one REGISTRY entry + goldens
(KNOWN_PROMPT_VERSIONS stays a literal in prompt_version.py; the sentinel test
in tests/test_prompt_renderers.py pins registry/tuple equality).

Byte discipline: adapters CALL the version modules' locked functions verbatim —
no string is composed here except the historical engine f-string joins
("\\n" + scaffold/digest), which tests pin byte-exactly."""
from __future__ import annotations

from typing import Any

from werewolf_eval.prompt_v1 import (
    RenderedObservation,
    build_speech_system_prompt,
    render_observation_text,
)
from werewolf_eval.prompt_v2 import (
    build_board_rules_card,
    build_speech_system_prompt_v2,
    render_observation_text_v2,
)
from werewolf_eval.prompt_v3 import (
    build_speech_system_prompt_v3,
    render_claim_digest,
    render_vote_scaffold,
)
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS


class PromptRendererV1:
    """Baseline chain (legacy bytes): plain observation text, v1 speech
    contract, no board card, no injections, no scribe."""

    version = "prompt_v1"
    requires_scaffold = False

    def board_card(self, ruleset: Any, seat_roles: dict[str, str]) -> str:
        return ""

    def render_observation(self, obs: Any, events_by_id: dict[str, dict[str, Any]]) -> RenderedObservation:
        return render_observation_text(obs, events_by_id)

    def speech_contract(self, request: Any) -> str:
        return build_speech_system_prompt(request)

    def action_obs_suffix(self, phase: str, claim_ledger: list[dict[str, Any]]) -> str:
        return ""

    def speech_obs_suffix(self, claim_ledger: list[dict[str, Any]]) -> str:
        return ""


class PromptRendererV2(PromptRendererV1):
    """SYS-B1 context repair: board rules card + structured observation +
    discrimination speech contract."""

    version = "prompt_v2"

    def board_card(self, ruleset: Any, seat_roles: dict[str, str]) -> str:
        return build_board_rules_card(ruleset, seat_roles)

    def render_observation(self, obs: Any, events_by_id: dict[str, dict[str, Any]]) -> RenderedObservation:
        text, ids = render_observation_text_v2(obs, events_by_id)
        return RenderedObservation(text=text, source_event_ids=ids)

    def speech_contract(self, request: Any) -> str:
        return build_speech_system_prompt_v2(request)


class PromptRendererV3(PromptRendererV2):
    """SYS-B4 claim ledger + vote scaffold: v2 observation/board card, restrained
    speech, scribe-backed injections (digest for speech, full scaffold for the
    day vote — graded guidance, spec §4)."""

    version = "prompt_v3"
    requires_scaffold = True

    def speech_contract(self, request: Any) -> str:
        return build_speech_system_prompt_v3(request)

    def action_obs_suffix(self, phase: str, claim_ledger: list[dict[str, Any]]) -> str:
        if phase == "day":
            return "\n" + render_vote_scaffold(claim_ledger)
        return ""

    def speech_obs_suffix(self, claim_ledger: list[dict[str, Any]]) -> str:
        if claim_ledger:
            return "\n" + render_claim_digest(claim_ledger)
        return ""


REGISTRY: dict[str, PromptRendererV1] = {
    r.version: r for r in (PromptRendererV1(), PromptRendererV2(), PromptRendererV3())
}


def get_renderer(version: str) -> PromptRendererV1:
    try:
        return REGISTRY[version]
    except KeyError:
        raise ValueError(
            f"unknown prompt_version {version!r}; known: {KNOWN_PROMPT_VERSIONS}"
        ) from None
```

- [ ] **Step 4: 跑测确认通过**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_renderers.py -q
```

Expected: PASS(全部)。

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/prompt_renderers.py tests/test_prompt_renderers.py
git status --short
git commit -m "feat(prompt): PromptRenderer registry — version->adapter seam with sentinel + byte-equivalence tests"
```

## Task 5: `llm_providers._system_for` 切 registry

**Files:**
- Modify: `src/werewolf_eval/llm_providers.py:257-274`

- [ ] **Step 1: 改 `_system_for`**

旧(L257-274):

```python
    def _system_for(self, request: ProviderRequest) -> str:
        if request.prompt_version not in KNOWN_PROMPT_VERSIONS:
            # defense in depth: engine/harness already gate this; never silently
            # render an unknown version as v1.
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
```

新:

```python
    def _system_for(self, request: ProviderRequest) -> str:
        # defense in depth: engine/harness already gate this; never silently
        # render an unknown version as v1 (get_renderer fail-louds for EVERY
        # response_kind, matching the old up-front check).
        renderer = get_renderer(request.prompt_version)
        if request.response_kind == "scaffold":
            contract = build_scribe_system_prompt(request)
        elif request.response_kind == "speech":
            contract = renderer.speech_contract(request)
        else:
            contract = build_action_system_prompt(request)
```

import 区:加 `from werewolf_eval.prompt_renderers import get_renderer`;若 `KNOWN_PROMPT_VERSIONS` 在本文件再无其他消费点则移除该 import(用 `grep -n KNOWN_PROMPT_VERSIONS src/werewolf_eval/llm_providers.py` 核实)。三个 speech builder 的 re-export import **保留**(外部消费方仍走旧址)。

- [ ] **Step 2: 验证**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_v2.py tests/test_prompt_v3.py tests/test_prompt_versioning.py tests/test_llm_providers.py -q
```

Expected: 全绿(尤其 `test_system_for_selects_by_prompt_version_and_prepends_card` e2e 守卫)。文件名漂移用 `ls tests/ | grep -i provider` 找替代并汇报。

- [ ] **Step 3: Commit**

```bash
git add src/werewolf_eval/llm_providers.py
git status --short
git commit -m "refactor(provider): _system_for speech contract dispatch via PromptRenderer registry (bytes unchanged)"
```

## Task 6: 引擎切 registry(分叉 1-7;与 B-2 接触面,放最后接线)

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py`(`__init__`、`_render_obs`、`_provider_action`、`_resolve_speech`、`run()` 五处)

- [ ] **Step 1: `__init__` L317-335 区段**

旧:

```python
        # SYS-B1: runtime-selectable prompt rendering chain (v1 default = legacy
        # bytes). Fail loud on unknown versions — no silent fallback.
        if prompt_version not in KNOWN_PROMPT_VERSIONS:
            raise ValueError(
                f"unknown prompt_version {prompt_version!r}; known: {KNOWN_PROMPT_VERSIONS}"
            )
        self.prompt_version = prompt_version
        self._board_card = ""
        if prompt_version in ("prompt_v2", "prompt_v3"):
            self._board_card = build_board_rules_card(
                _ruleset, {p.player_id: p.role for p in config.players}
            )
        # SYS-B4: the scribe is NOT a player. prompt_v3 REQUIRES it (no silent
        # scaffold-less v3); other versions ignore it.
        self._scaffold_agent = scaffold_agent
        if prompt_version == "prompt_v3" and scaffold_agent is None:
            raise ValueError("prompt_v3 requires a scaffold_agent (scribe provider)")
```

新:

```python
        # SYS-B1: runtime-selectable prompt rendering chain (v1 default = legacy
        # bytes). get_renderer fail-louds on unknown versions — no silent fallback.
        self._renderer = get_renderer(prompt_version)
        self.prompt_version = prompt_version
        self._board_card = self._renderer.board_card(
            _ruleset, {p.player_id: p.role for p in config.players}
        )
        # SYS-B4: the scribe is NOT a player. A scaffold-requiring renderer (v3)
        # REQUIRES it (no silent scaffold-less run); other versions ignore it.
        self._scaffold_agent = scaffold_agent
        if self._renderer.requires_scaffold and scaffold_agent is None:
            raise ValueError(f"{prompt_version} requires a scaffold_agent (scribe provider)")
```

(报错字节:v3 时 f-string 产出与旧串逐字相同。)

- [ ] **Step 2: `_render_obs` L544-548**

旧:

```python
    def _render_obs(self, obs: AgentObservation) -> RenderedObservation:
        if self.prompt_version in ("prompt_v2", "prompt_v3"):
            text, ids = render_observation_text_v2(obs, self._events_by_id())
            return RenderedObservation(text=text, source_event_ids=ids)
        return render_observation_text(obs, self._events_by_id())
```

新:

```python
    def _render_obs(self, obs: AgentObservation) -> RenderedObservation:
        return self._renderer.render_observation(obs, self._events_by_id())
```

- [ ] **Step 3: `_provider_action` L595-600**

旧:

```python
        obs_text = rendered.text
        if self.prompt_version == "prompt_v3" and phase == "day":
            # vote request (the only day-phase action path; hunter uses its own
            # site): inject digest + comparison program. Input-side ONLY — the
            # action system prompt / strict-JSON contract is untouched (spec §0).
            obs_text = f"{obs_text}\n{render_vote_scaffold(self._claim_ledger)}"
```

新:

```python
        # vote request (the only day-phase action path; hunter uses its own
        # site): a scaffold renderer (v3) injects digest + comparison program.
        # Input-side ONLY — the action system prompt / strict-JSON contract is
        # untouched (spec §0). Empty suffix for v1/v2 keeps bytes identical.
        obs_text = rendered.text + self._renderer.action_obs_suffix(phase, self._claim_ledger)
```

- [ ] **Step 4: `_resolve_speech` L922-926**

旧:

```python
        obs_text = rendered.text
        if self.prompt_version == "prompt_v3" and self._claim_ledger:
            # graded guidance: speeches get the DIGEST only (information symmetry),
            # never the comparison program (b1 lesson: don't arm wolf fake-claims).
            obs_text = f"{obs_text}\n{render_claim_digest(self._claim_ledger)}"
```

新:

```python
        # graded guidance: speeches get the DIGEST only (information symmetry),
        # never the comparison program (b1 lesson: don't arm wolf fake-claims).
        # Non-v3 renderers return "" — bytes identical.
        obs_text = rendered.text + self._renderer.speech_obs_suffix(self._claim_ledger)
```

- [ ] **Step 5: `run()` L1200-1201**

旧:

```python
            if self.prompt_version == "prompt_v3":
                self._run_scribe(rnd)
```

新:

```python
            if self._renderer.requires_scaffold:
                self._run_scribe(rnd)
```

- [ ] **Step 6: 清 import**

加 `from werewolf_eval.prompt_renderers import get_renderer`。然后逐个核实并清理不再被引擎直用的名字:`build_board_rules_card`、`render_observation_text_v2`、`render_vote_scaffold`、`render_claim_digest`、`KNOWN_PROMPT_VERSIONS`(`grep -n <name> src/werewolf_eval/emergent_engine.py` 确认仅 import 行残留再删)。**保留**:`render_scribe_input`、`parse_scribe_claims`、`SCRIBE_MAX_OUTPUT_TOKENS`(scribe 机器留在引擎)、`RenderedObservation`/`render_observation_text`(Task 2 的 re-export 义务)。

- [ ] **Step 7: 全量验证**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q 2>&1 | tail -3
git diff --exit-code tests/golden_prompts/
```

Expected: 与 Task 1 Step 2 相同的通过数;空 diff。

- [ ] **Step 8: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py
git status --short
git commit -m "refactor(engine): all 7 prompt-version forks dispatch via PromptRenderer (board card, obs render, v3 injections, scribe gate; bytes unchanged)"
```

## Task 7: launcher + harness 的 `requires_scaffold` 单源

**Files:**
- Modify: `src/werewolf_eval/run_emergent_deepseek_game.py:131-136`
- Modify: `src/werewolf_eval/ablation/harness.py:42-43, 63-65`

- [ ] **Step 1: `run_emergent_deepseek_game.py`**

旧(L131-136):

```python
    # Fail-loud before any side effects (writer/engine construction).
    scaffold_agent = None
    if prompt_version == "prompt_v3":
        if scaffold_provider_factory is None:
            raise ValueError("prompt_v3 requires scaffold_provider_factory (scribe provider)")
        scaffold_agent = scaffold_provider_factory()
```

新:

```python
    # Fail-loud before any side effects (writer/engine construction).
    scaffold_agent = None
    if get_renderer(prompt_version).requires_scaffold:
        if scaffold_provider_factory is None:
            raise ValueError(f"{prompt_version} requires scaffold_provider_factory (scribe provider)")
        scaffold_agent = scaffold_provider_factory()
```

import 区加 `from werewolf_eval.prompt_renderers import get_renderer`。(附带收益:unknown version 现在在 launcher 层就 fail-loud,早于引擎构造。)

- [ ] **Step 2: `ablation/harness.py`**

L37-41 的 KNOWN 哨兵门**保留原样**(消融硬门,guarding-prompt-bytes skill 点名)。L42-43 改:

```python
    requires_scaffold = get_renderer(arm.prompt_version).requires_scaffold
    if requires_scaffold and scaffold_factory_builder is None:
        scaffold_factory_builder = _deepseek_scaffold_factory_builder
```

L63-65 的传参改:

```python
                    scaffold_provider_factory=(
                        scaffold_factory_builder(arm, api_key)
                        if requires_scaffold else None),
```

import 区加 `from werewolf_eval.prompt_renderers import get_renderer`。

- [ ] **Step 3: 验证**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_harness_fake.py tests/test_ablation_arms.py tests/test_l4_arm_layout.py -q
```

Expected: 全绿。

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/run_emergent_deepseek_game.py src/werewolf_eval/ablation/harness.py
git status --short
git commit -m "refactor(launcher+harness): scribe requirement single-sourced from renderer.requires_scaffold"
```

## Task 8: 终验 — 字节门 + 全量 + tree + 验证报告

**Files:**
- Modify: `.oh-my-harness/tree.md`(hook 再生)

- [ ] **Step 1: v1 fake 局字节门(对 Task 1 基线)**

```bash
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --game-id b1pr_gate --out-dir .tmp/b1pr-after --seed 7
diff -r .tmp/b1pr-base-1 .tmp/b1pr-after
```

Expected: 空 diff(扣除 Task 1 记录的非确定性路径,两侧同样排除)。确定性文件非空 diff = STOP,报 BLOCKED 并列出差异文件。

- [ ] **Step 2: 全量 + 字节锁 + 禁区**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q 2>&1 | tail -3
git diff --exit-code tests/golden_prompts/
git diff main...HEAD --name-only
```

Expected: 通过数 = Task 1 基线 + 新增测试数;golden 空 diff;name-only 输出 ⊆ §0.5 allowlist(尤其确认 `prompt_version.py`、ledger、`game_engine.py`、`action_runtime/**` 零变化)。

- [ ] **Step 3: tree 再生 + commit**

```bash
node .codex/hooks/tree.mjs --force
git add .oh-my-harness/tree.md docs/harness/plans/2026-06-11--sys-b1-prompt-renderer-registry-plan.md
git status --short
git commit -m "chore(tree): regen for prompt_v1/prompt_renderers/test_prompt_renderers"
```

(plan 文档若已在 Task 0 提交则此处只剩 tree.md。)

- [ ] **Step 4: AGENTS.md 验证报告**

汇报:`git diff --stat main...HEAD`、`git diff --name-only main...HEAD`、allowlist 对照、禁区核查、测试结论(基线数 vs 终数)、字节门三项结论(golden / fake 局 / 注入单测)。

- [ ] **Step 5: 合并前置检查(D6)**

```bash
git fetch . 2>/dev/null; git log --oneline -5 main
git -C /g/Werewolf-agent worktree list
```

确认:① B-2 是否已合 main——已合则 rebase 本分支到 main,解 `emergent_engine.py` import 块/相邻函数冲突后**重跑本 Task Step 1-2 全部门**;② T17 live merge hold 是否解除。两项都过才进入 merge 流程(finishing-a-development-branch)。

---

## Self-Review 记录(writing-plans skill 要求)

- **覆盖核对:** §0.1 的 10 处分叉 ↔ Task 5(#8)、Task 6(#1-7)、Task 7(#9-10),全覆盖;goldens 路由(评审 HTML 的第 5 源点)裁决为非分叉(D3/0.1 表下注),样本函数不动、仅 import 改址(Task 3)。
- **占位符扫描:** Task 2/3 的「原文逐字复制」标注了精确行号范围与来源文件,且明确「从当前文件复制不要凭记忆重打」——这是 verbatim-move 的正确做法,不是占位符;其余代码步全部给出完整代码。测试文件名可能漂移的两处给了 `ls tests/ | grep` 兜底程序。
- **类型一致性:** `get_renderer` / `REGISTRY` / `requires_scaffold` / `board_card` / `render_observation` / `speech_contract` / `action_obs_suffix` / `speech_obs_suffix` 在 Task 4 定义与 Task 5/6/7 消费处签名一致;`RenderedObservation` 自 Task 2 起单源于 `prompt_v1.py`。
- **已知风险:** ① fake 工件可能含非确定性路径(Task 1 先建确定性集合);② B-2 同文件相邻区(D6 合并前置检查);③ 冷启动 import 环(0.3 图 + 全量含 ColdImport 测试);④ Windows 工件 CRLF——diff -r 是字节比较,基线/复跑同机同配置,无额外处理。
