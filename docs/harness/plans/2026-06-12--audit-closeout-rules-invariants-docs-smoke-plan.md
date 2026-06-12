# Implementation Plan — Post-Audit Maintenance Closeout: Rules + Invariants + Docs + Provider Smoke Gate

- **Date:** 2026-06-12
- **Branch / worktree:** `maint/audit-closeout-5-9` @ `G:\wt-audit-closeout-5-9` (base main `ce526ee`)
- **Source of scope:** `docs/health-check/2026-06-12-system-view-audit.md` 残留项 5–9（A-2/A-3、C3-2、C3-1、B34-07、A45-1）
- **Route authority:** `AGENTS.md`（PR-first，plan-bound，forbidden-scope）+ `docs/PROJECT_MAP.md`（P2 当前阶段；SYS-A1/A2/A3/A5/B3/C3/A4 系统视图）
- **强约束:** 不新增角色 · 不改 prompt 文案（任一 Part 若需改 prompt 立即停止走 `guarding-prompt-bytes`）· 不重写 observer server / settlement / emergent engine 主流程 · 不做 P3 leaderboard · 不引入 live API 依赖 · 不删 tests · 不改 `docs/ROADMAP.md` / `docs/TASKS.md` · 不改历史 generated-games / gold-game / demo

> 执行口径：**五个 Part 串行**，每个 Part 跑 focused test → 段落汇报 → 再进下一个。最后跑全量。

---

## 全局 prompt 字节判定（动工前一次性裁定）

依据 `.agents/skills/guarding-prompt-bytes`：受字节锁的是 baseline 渲染链
（`build_action_system_prompt` / `build_speech_system_prompt` / `compose_system` /
`render_observation_text`，含 `augment_witch_observation` 与 `HUNTER_SHOT_OBSERVATION_SUFFIX`）。

逐 Part 判定：

| Part | 触碰文件 | 是否改模型可见字节 | 理由 |
|---|---|---|---|
| 1 A-2/A-3 | abilities/ruleset/registry/emergent_engine | **NO** | 仅改死亡触发的因果门控与女巫自救校验（运行时裁决逻辑）；不改任何 renderer 字符串、不改 `allowed_targets` 渲染、不改 augment/suffix 文本 |
| 2 C3-2 | docs/specs + 可选 sentinel 测试 | **NO** | spec 文档为主；不动 renderer |
| 3 C3-1 | invariants/guards + checker | **NO** | 不变量代码，非渲染链 |
| 4 B34-07 | emergent_smoke_check | **NO** | 离线 judge，非渲染链 |
| 5 A45-1 | docs/adr | **NO** | 纯文档 |

**结论：本任务不涉及 prompt 字节变化。** 执行中若任一 Part 被迫改 renderer 字节 → 立即停止并向用户报告。

---

## Part 1 — A-2 / A-3 规则裁决 + pin 测试

**裁决（用户给定）:**
- **A-2:** 毒死的猎人**不能**开枪；被狼刀 / 被票出等**非毒死**死亡仍按现有 hunter on_death 触发规则处理。
- **A-3:** 女巫**允许首夜自救**；非首夜**不得**自救。

**文件面:**
- `src/werewolf_eval/action_runtime/abilities.py` — `AbilityDefinition` 增 `suppressed_by_cause: frozenset[str] = frozenset()`（带默认 → 既有所有 ability 字节/行为不变）。
- `src/werewolf_eval/action_runtime/ruleset.py` — `rules_v1_1()` 中 `hunter_shoot` 设 `suppressed_by_cause=frozenset({"witch_poison"})`（单源裁决数据）。
- `src/werewolf_eval/action_runtime/registry.py` — 增 `death_trigger_suppressing_causes(role) -> frozenset[str]`（union over on_death abilities）。
- `src/werewolf_eval/emergent_engine.py`:
  - A-2：`_trigger_on_death(dead, rnd, phase, cause)` 增 `cause` 形参；夜死循环按 `cause = "werewolf_kill" if pid == victim else "witch_poison"`，白天票出 `cause="vote"`，猎人级联枪杀 `cause="hunter_shoot"`；`_trigger_on_death` 在 `cause ∈ registry.death_trigger_suppressing_causes(role)` 时 no-op（不调 provider、不开枪）。
  - A-3：`_resolve_witch` 校验块加分支——`action_name == WITCH_SAVE` 且 `target == witch`（自救）且 `rnd != 1` → `_record_failure(... "invalid_action" ...)` + `_downgrade_turn` + 落回 `WITCH_PASS`（既有诚实降级路径）。
- `docs/specs/board-rule-rulings.md`（新）— 落条文：A-2 毒死猎人不开枪 / A-3 女巫首夜自救裁决，含触发场景、代码落点、与 SYS-A2/A3 边界。

**pin tests（`tests/test_rule_rulings.py` 新）:**
- `test_poison_death_hunter_no_shoot` — 女巫毒死猎人 → 无 `hunter_shoot` 事件，毒目标死亡。
- `test_wolf_kill_hunter_triggers_shoot` — 狼刀猎人 → 触发开枪。
- `test_vote_out_hunter_triggers_shoot` — 票出猎人 → 触发开枪。
- `test_witch_first_night_self_save_legal` — 首夜女巫=victim 自救合法（救成功，无 failure）。
- `test_witch_non_first_night_self_save_rejected` — 非首夜女巫=victim 自救 → invalid_action 降级，failure-audit 诚实记录，女巫当晚死亡。

**focused tests:**
```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_rule_rulings.py tests/test_allowed_actions_pinned.py tests/test_action_runtime_parity.py tests/test_emergent_engine.py -q
```

**allowlist:** 上列 5 个 src 文件 + `tests/test_rule_rulings.py` + `docs/specs/board-rule-rulings.md`。
**forbidden-scope:** 不新增角色（hunter/guard 已 ship）；不改奶穿/连守等未裁决板规；不改 renderer；不改 settler 死亡顺序字节。
**prompt 字节:** NO。

---

## Part 2 — C3-2 文本注入通道机制 spec

**文件面:**
- `docs/specs/text-injection-channels.md`（新）— 至少含：
  1. 注入点登记表：`augment_witch_observation`、`witch_obs_suffix`、`speech_obs_suffix`、`action_obs_suffix`、scribe 输入（`render_scribe_input`）。每点列：调用站点、消费输入来源、可见性等级、当前是否带 source ids。
  2. 每注入点允许消费的输入来源与可见性等级。
  3. 必须带 source ids 的注入点；当前不能带的（女巫合法刀口知识绕道文本）→ 临时豁免 + 机检补偿（现有 `test_c3_negative_scan.py` 负向扫描）。
  4. 长期方案：合法角色知识迁移到带 id 事件通道；与 EffectQueue / CapabilityLedger 边界（挂 SYS-A2 线）。
  5. 新增注入点 review checklist。
- 可选 lightweight sentinel（仅在确有缺口时）：注入点登记漂移哨兵——若引擎/renderer 出现新 `*_obs_suffix` / `augment_*` 注入而未登记 spec 即 fail。既有 `test_c3_negative_scan.py` 已覆盖女巫泄漏负向扫描，**不重复造轮子**；只补登记漂移这一缺口。

**focused tests:**
```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_c3_negative_scan.py -q
# 若补 sentinel：附带新测试文件
```

**allowlist:** `docs/specs/text-injection-channels.md`（+ 可选 `tests/test_injection_registry_sentinel.py`）。
**forbidden-scope:** 不做大代码改动；不改 renderer 字节；不迁移通道（长期方案只写 spec）。
**prompt 字节:** NO。

---

## Part 3 — C3-1 幽灵 source id fail-loud（双层静默修复）

**文件面:**
- `src/werewolf_eval/invariants/guards.py` — `assert_prompt_entitled`：悬空 id（`ev is None`）不再 `continue` 静默通过 → 运行时 fail-loud（新 `DanglingSourceEventError` 或明确错误）。改如实 docstring（删「离线兜底报 artifact gap」误导措辞）。
- `src/werewolf_eval/invariants/checker.py` — `check_i4b`：`ev is None` → 产 dedicated `InvariantViolation`（如 code `I4b` severity error，message 标 dangling reference / artifact gap），不再 `continue`。
- tests（`tests/test_invariants_dangling.py` 新）— 覆盖：
  - runtime：`assert_prompt_entitled` 引用不存在 event id → 抛错。
  - offline：`check_i4b` 引用不存在 event id → 产 violation（非空）。
  - 回归：合法 source ids 两路径均无误报。

**focused tests:**
```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_invariants_dangling.py tests/test_invariants_e2e.py tests/test_role_visibility.py -q
```

**allowlist:** `guards.py` + `checker.py` + `tests/test_invariants_dangling.py`。
**forbidden-scope:** 不改可见性裁决语义（entitled 逻辑不动）；不改 renderer。
**prompt 字节:** NO。
**风险:** runtime 改 raise 可能触发既有局中本不该有的悬空 id → 全量复跑暴露；TDD 先写测试。

---

## Part 4 — B34-07 provider-agnostic smoke honesty gate

**文件面:**
- `src/werewolf_eval/emergent_smoke_check.py`:
  - `source_label` 不再硬编码只能 `== DEEPSEEK_SOURCE_LABEL`：live turn 须 `label ∈ VALID_SOURCE_LABELS` 且 ∉ fake/simulation 标签集（`FAKE_PROVIDER_SOURCE_LABEL` 等）。
  - manifest 校验支持 per-seat expected provider/model：新增可选 `expected_models_by_seat: dict[str,str] | None`；保留 `expected_model: str | None` 单 provider 旧用法（DeepSeek 兼容）。
  - fake/live 混淆：fallback turn 不得携带真实 live label（泛化现有 `!= DEEPSEEK` 检查）。
- `tests/test_emergent_smoke_check.py`（扩展，不删）:
  - mixed-provider per-seat fixture（离线合成 artifact，fake/test provider 标签）→ 通过。
  - fake turn 冒充 live label → 失败（负向）。
  - 非 DeepSeek live label（如 `[OpenAI API output]`）单 provider → 通过。

**focused tests:**
```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_emergent_smoke_check.py tests/test_source_labels.py -q
```

**allowlist:** `emergent_smoke_check.py` + `tests/test_emergent_smoke_check.py`。
**forbidden-scope:** 不新增真实 provider；不做 live API 调用；不让 CI 依赖 live key；mixed 场景仅离线 fixture / fake provider。
**prompt 字节:** NO。

---

## Part 5 — A45-1 perspective 非鉴权边界 ADR

**文件面:**
- `docs/adr/2026-06-12-perspective-not-access-control-boundary.md`（新）— 明确：
  - observer artifact endpoint 的 `perspective` 参数**不是** access-control boundary。
  - perspective 仅用于展示 / 投影语义。
  - provider-trace / decision-log / game-log 等 artifact 属 God/audit 级别。
  - 当前威胁模型 = local observer / audit operator。
  - P3 多客户端 / 人机混战 / 每座位真实参与方接入前，**必须**补鉴权分级。
  - 当前不实现鉴权的理由（过度设计）。
- 仅文档边界声明，**不做鉴权实现**。

**focused tests:** 无（纯文档）。链接校验靠人读。

**allowlist:** `docs/adr/2026-06-12-perspective-not-access-control-boundary.md`。
**forbidden-scope:** 不改 observer handler / server 代码；不实现鉴权。
**prompt 字节:** NO。

---

## 验收（全任务收口）

1. 每个 Part 给出 focused test 命令与结果。
2. 全量：
   ```bash
   NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
   ```
3. 输出 `git diff --stat` / `git diff --name-only` / allowlist check / forbidden-scope check / prompt 字节判定（NO）。
4. 按 Part 1–5 分段汇报完成内容、测试结果、遗留风险。

## 合并后 allowlist（预期 git diff --name-only 全集）

```
src/werewolf_eval/action_runtime/abilities.py
src/werewolf_eval/action_runtime/ruleset.py
src/werewolf_eval/action_runtime/registry.py
src/werewolf_eval/emergent_engine.py
src/werewolf_eval/invariants/guards.py
src/werewolf_eval/invariants/checker.py
src/werewolf_eval/emergent_smoke_check.py
tests/test_rule_rulings.py
tests/test_invariants_dangling.py
tests/test_emergent_smoke_check.py
docs/specs/board-rule-rulings.md
docs/specs/text-injection-channels.md
docs/adr/2026-06-12-perspective-not-access-control-boundary.md
docs/harness/plans/2026-06-12--audit-closeout-rules-invariants-docs-smoke-plan.md
（可选）tests/test_injection_registry_sentinel.py
```
</content>
</invoke>
