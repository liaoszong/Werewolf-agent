# 02 — 瘦身候选(Slimming Candidates)

> <span style="color:red">**🔴 本轮只产候选,不删任何代码 / 文档。** 这是 ARTIFACT-ONLY 只读诊断 —— 下表全部为"建议动作",没有任何一行被执行。删除决策须由人类审阅后另起一支单独 PR,逐项二次确认动态引用(CLI / 反射 / 文档 acceptance gate)后才可落地。</span>

> worktree `worktree-health-check-2026-06-08` @ 快照 `1d721fd` · 范围 `src/` `tests/` `clients/` `docs/` · 基线 `docs/health-check/_baseline/`(import-refs / entrypoint-wiring / doc-refs / bigfiles)

---

## 方法说明

- **三层判据**:`import-refs`(静态 import 计数)+ `entrypoint-wiring`(被 launcher / doc / test / CI 提及)+ `doc-refs`(被其它 md/py/json 引用)+ `last-commit`/PR + **动态引用**(CLI `python -m`、QML `import`、`json` fixture 路径、文档 acceptance gate)。
- **复核纠偏**:编排者交付的 `triage` 数据有数条证据失真(下文每条以"复核结论"点明)。本文件对每条 DEAD-* 候选给出 **复核后的 final_grade**,并保留与原 triage 判档的差异。
- **基线 import-refs 是子串正则**(见 `_baseline/baseline.py`):对同名函数 / 短模块名会**误计**。凡涉及计数,本文件以 `git grep` 精确复核为准,不直接采信 triage 里的裸数字。
- **4 级**:`DEAD-CONFIRMED`(零静态 + 零动态引用,删之无回归)/ `DEAD-LIKELY`(零/极弱引用,但存在家族一致性或文档约定,删前须人工确认)/ `FUTURE-SCAFFOLD`(为未交付 phase 预置,刻意保留)/ `KEEP`(活跃,误报澄清)。

---

## A. DEAD-CONFIRMED — 零静态 + 零动态引用

| 路径 | 等级 | 证据(refs / cov / wiring / last-commit / PR / 动态引用) | 建议动作 |
|---|---|---|---|
| `docs/generated-games/g1d-fake-provider-failure-audit.example.json` | **DEAD-CONFIRMED** | doc-refs 仅 1(`2026-06-02--g1d-...harness-plan.md` 历史计划)。`git grep g1d-fake-provider-failure-audit -- tests/ src/ *.py` = **0**;`test_failure_audit.py:15,20` 实际加载的是 `g1c-wolf-consensus-failure-audit.json`(非 example)。同目录的 `g1d-fake-provider-game-log.json` 被 `test_fake_provider_game.py` 真用,但 **本 `.example.json` 无任何 test/code 路径**。last-commit `ffcbb0f`(2026-06-02 G1d harness),自此未被消费。**复核结论**:triage 判 KEEP 理由(".example.json 命名清晰即文档示例")成立但与"是否有消费者"无关;它是 G1d 阶段一次性产出、从未接入测试的孤儿 fixture。 | 候选移除或归档至 `docs/specs/examples/`。删前确认 `docs/TASKS.md` G1d phase 状态=completed。零回归(无测试引用)。 |

---

## B. DEAD-LIKELY — 极弱引用 / 家族不一致,删前须人工确认

| 路径 | 等级 | 证据(refs / cov / wiring / last-commit / PR / 动态引用) | 建议动作 |
|---|---|---|---|
| `src/werewolf_eval/validate_failure_audit.py` | **DEAD-LIKELY**(triage 原判 KEEP — 证据失真,已纠正) | import-refs=**0**(基线确认)。**triage 的两条 KEEP 证据均不成立**:(1) "used by failure_audit.py:68" —— 经核 `failure_audit.py:69` 调用的 `validate_failure_audit` 是 **同文件第 73 行定义的本地函数**(名字冲突),**不是**本 CLI 模块,纯属同名误判;(2) "docs/TASKS.md line 282 acceptance criteria 'A-3 Failure Audit parser validator CLI'" —— `git grep 'Failure Audit' docs/TASKS.md` 只命中 184/201 行(把 Failure Audit 列为 **log-bundle 产物**),**不存在**该 line-282 验收条目。**真实定位**:这是 6 个 `python -m werewolf_eval.validate_*` 验证器之一,但唯独它**不被任何消费者引用**——`scripts/dev/validate_brief.py:12-14` 编排了 game_log / decision_log / consensus_log 三个,**不含 failure_audit**;无 `test_validate_failure_audit`;`git grep validate_failure_audit -- scripts/ tools/ .github/ *.bat *.sh` = 0(无 CLI/CI 调用)。其余 5 个验证器各有真实消费者(见 §D-1)。last-commit `e0ad999`(2026-06-01),自此零接入。**复核结论**:不是"CLI-only 所以 0 ref 正常"——其 5 个兄弟全有动态引用,**唯独它没有**,是家族里唯一悬空的那个。 | 候选:要么补进 `validate_brief.py` 编排(若 failure-audit 是必验产物则这是缺口),要么移除。**勿盲删**:它是结构完整、可独立运行的 CLI,删前请人工裁决"failure-audit 是否应纳入 validate_brief 验证套件"——若应纳入则是 wiring 缺口(留并接线)而非死代码。 |

---

## C. FUTURE-SCAFFOLD — 为未交付 phase 预置,刻意保留

| 路径 | 等级 | 证据(refs / cov / wiring / last-commit / PR / 动态引用) | 建议动作 |
|---|---|---|---|
| `docs/superpowers/specs/2026-06-06-p2-observer-emergent-engine-bridge.md` | **FUTURE-SCAFFOLD / KEEP** | doc-refs=0(基线孤儿),但被 **9 个 entrypoint-wiring 条目**间接引用(`run_emergent_fake_runtime`/`run_emergent_game`/`run_deepseek_consensus_game`/`run_observer_server` 等的 refs 列表均含本 spec)。这是 PR #46 合并(`f947e89` 2026-06-07)的 design-only 桥接 spec,MEMORY 记其为 observer→emergent 实现的基础。**复核结论**:triage 判 KEEP 正确;0 doc-refs 是"设计 spec 不被 md 反链"的常态,非死文档。 | 保留。P2-A-2/observer-bridge 实现的权威设计依据。 |
| `docs/harness/plans/2026-06-08--full-health-check.md` | **FUTURE-SCAFFOLD / KEEP** | doc-refs=0,且 `git grep` 确认**无任何其它文件引用**它。但它出现在 10 个 entrypoint-wiring 的 refs 列表里(因 baseline 扫描 docs/**.md 含本计划),且文件名 = 当前 worktree 分支基准日期。**复核结论**:triage 判 KEEP 正确;这是**本轮体检的协调计划本身**(self-referential),它"是"参照源不是消费者。 | 保留。本轮诊断的协调文档。 |
| `clients/qt_observer/qml/EventPresentationQueue.qml` | **KEEP**(triage 原判 FUTURE-SCAFFOLD — 已纠正,见 §E) | 见 §E。 | 见 §E。 |

> 注:`EventPresentationQueue.qml` 经复核**不是** future-scaffold —— 已上移到 §E KEEP 区并附纠正证据。

---

## D. 整组判断

### D-1. `validate_*` 验证器家族(6 组)— 整组判定

| 模块 | bigfiles 行数 | import-refs | 动态消费者(`-m` / import) | 整组判断 |
|---|---|---|---|---|
| `validate_game_log.py` | 25 | 1 | `validate_brief.py:12` 经 `python -m` 编排 | **KEEP** |
| `validate_decision_log.py` | 26 | 2 | `validate_brief.py:13` + `test_decision_log.py` | **KEEP** |
| `validate_consensus_log.py` | 33 | 1 | `validate_brief.py:14` 经 `python -m` 编排 | **KEEP** |
| `validate_log_bundle.py` | 41 | 1 | `src/werewolf_eval/score_game.py` 真 import | **KEEP** |
| `validate_semantic_labels.py` | 29 | 1 | `tests/test_semantic_labels.py` 真 import | **KEEP** |
| `validate_failure_audit.py` | 25 | **0** | **无**(非 validate_brief、无 test、无 CI) | **DEAD-LIKELY**(见 §B) |

**整组结论**:`validate_*` 是一个**有意设计的 CLI 验证器家族**(全部 `python -m werewolf_eval.validate_X`,全部有 `main()`+`__main__`,行数 25-41 行同构)。5/6 有真实动态消费者,**只有 `validate_failure_audit` 悬空**。**家族整体 KEEP**;唯一异常项见 §B,且更可能是 `validate_brief` 的接线缺口而非纯死代码。基线 import-refs=0/1 是 CLI 模块常态,**不可单凭计数判死**——本组已逐一动态核实。

### D-2. demo HTML 渲染产物(8 个)— 整组判定

| 路径(`docs/demo/*.html`) | 跨 md 引用(去 demo/ 自引) | 整组判断 |
|---|---|---|
| `phase1-gold-demo.html` | 13 | KEEP |
| `phase2-runtime-demo.html` | 11 | KEEP |
| `phase2-s5-runtime-demo.html` | 8 | KEEP |
| `phase3-g1-scripted-runtime-demo.html` | 7 | KEEP |
| `phase3-g1b-mock-agent-runtime-demo.html` | 8 | KEEP |
| `phase3-g1c-wolf-consensus-runtime-demo.html` | 9 | KEEP |
| `phase3-g1d-fake-provider-runtime-demo.html` | 4 | KEEP |
| `phase3-g1f-provider-replay.html` | 3 | KEEP |

**整组结论**:全部 demo HTML 均被 ≥3 个 md(`GOLD_DEMO.md`/`ROADMAP.md`/phase plans)引用,是**被文档锚定的可视化交付物**,非孤儿。整组 KEEP。

---

## E. 孤儿文档 / fixture 专节(generated-games · gold-game · demo · QML 纠正)

| 路径 | 等级 | 证据 | 建议动作 |
|---|---|---|---|
| `docs/gold-game/s5-semantic-label-output.example.json` | **KEEP** | `.example.json` 但**被 4 个测试真用**:`test_render_demo.py:27,123` / `test_scoring.py:36,186,207` / `test_semantic_label_research.py` / `test_semantic_labels.py`(共 ~18 处路径加载)。与 §A 的 g1d example 形成对照——**同样 `.example` 命名,这个是活 fixture**,证明"命名规则不能判死,须查消费者"。 | 保留。核心 scorer/renderer 测试 fixture。 |
| `docs/generated-games/*.json`(g1/g1b/g1c/g1d 系列,除 §A 那个 example) | **KEEP** | 被 7 个测试加载:`test_failure_audit.py`/`test_fake_provider_game.py`/`test_game_engine.py`/`test_log_bundle.py`/`test_render_demo.py`/`test_scoring.py`/`test_scripted_game_runner.py`。 | 保留。回归基线 fixture。 |
| `docs/gold-game/g001-*.json` | **KEEP** | 被 `validate_brief.py`(`python -m` 喂参)+ `attribution.py`/`scoring.py`/`emergent_engine.py` + 6 个测试加载。 | 保留。gold seed 单源 fixture。 |
| `clients/qt_observer/qml/EventPresentationQueue.qml` | **KEEP**(纠正 triage 的 FUTURE-SCAFFOLD 误判) | **triage 判 FUTURE-SCAFFOLD 错误**:`git grep EventPresentationQueue -- clients/` 命中 **5 处真实接线** —— `CMakeLists.txt`(注册)、`TheaterView.qml`、`components/PlaybackControls.qml`、`src/ObserverApiClient.cpp`、`README.md`。它**已经被 TheaterView 实例化并消费 `ObserverClient.eventItems`**,是 **P2-C-1 已交付**(PR/commit `ce9cef9` 2026-06-06 "top phase progress axis")的**活跃控制器**,而非"P2-C 待启动 scaffold"。triage 误把头注释里的 "P2-C-1" 标签当成"未来"。**复核结论**:活跃组件,误报。 | 保留。已上线的非可视事件队列控制器。 |
| `clients/qt_observer/qml/components/RoleCard.qml` | **KEEP** | `git grep RoleCard -- clients/` 命中 `CMakeLists.txt`/`README.md`/`LiveCockpitView.qml`/`MatchSetupView.qml`,活跃组件。triage 判 KEEP 正确(注:triage 称其复合在 SettlementView/SeatRing,实际证据是 LiveCockpitView/MatchSetupView,结论同为 KEEP)。 | 保留。活跃 role 渲染组件。 |

---

## F. KEEP — 其余被 triage 列入但经复核确认活跃(误报澄清)

| 路径 | 等级 | 证据(复核纠正) | 建议动作 |
|---|---|---|---|
| `src/werewolf_eval/emergent_fake_script.py` | **KEEP** | **triage 称 import-refs=2,实测 import-refs=9**(基线 bigfiles/import-refs 均列 9):`run_emergent_fake_runtime.py`/`run_emergent_game.py` + 7 个测试(`test_emergent_engine`/`test_emergent_role_projection`/`test_engine_to_scoring_e2e`/`test_event_visibility_invariant`/`test_observer_emergent_bridge`/`test_p2a2_live_path`/`test_run_emergent_deepseek_game`)。结论 KEEP 不变,但**它远比 triage 描述的更核心**,绝非低引用。 | 保留。P2-A 引擎确定性场景脚手架的主力 fixture builder。 |
| `src/werewolf_eval/emergent_smoke_check.py` | **KEEP** | import-refs=2 实测核实(`run_emergent_deepseek_game.py` + `emergent_engine`)。P2-A live smoke 套件。 | 保留。 |
| `src/werewolf_eval/seat_agents.py` | **KEEP** | import-refs=4;实测被 `deepseek_launcher.py`/`observer_server.py` + `test_multi_provider_launcher.py` 真 import(provider→seat 绑定契约)。 | 保留。核心绑定契约。 |
| `src/werewolf_eval/display_labels.py` | **KEEP** | import-refs=3;实测 `render_demo.py`/`render_provider_replay.py`/`test_engine_to_scoring_e2e.py`。R-12 抽出的单源 label 字典(witch_kill/witch_poison 一致性修复成果)。 | 保留。label 单源注册表。 |

---

## 汇总

| 等级 | 计数 | 项 |
|---|---|---|
| **DEAD-CONFIRMED** | 1 | `g1d-fake-provider-failure-audit.example.json` |
| **DEAD-LIKELY** | 1 | `validate_failure_audit.py`(更可能是 validate_brief 接线缺口) |
| **FUTURE-SCAFFOLD** | 2 | bridge spec、本健康检查计划(均 self-/design-ref,刻意留) |
| **KEEP(含误报澄清)** | 多 | validate_* 家族(5/6)、demo HTML(8)、各 fixture、emergent_fake_script/seat_agents/display_labels/EventPresentationQueue/RoleCard 等 |

### 给人类审阅者的提醒

1. **triage 输入数据有 ≥3 处证据失真**,本文件已逐条纠正:`validate_failure_audit` 的两条 KEEP 理由均不成立(同名函数误判 + 不存在的 TASKS.md 行号);`EventPresentationQueue.qml` 被误判 FUTURE-SCAFFOLD(实为已上线);`emergent_fake_script` 被低估为 2-ref(实为 9)。**任何删除决策都不应直接采信原 triage 的裸证据**。
2. **唯二可动的候选**(§A 的 g1d example、§B 的 validate_failure_audit)合计影响极小;§B 那个更建议**补接线**而非删除。本轮**不执行任何删除**。
3. **基线 import-refs 是子串正则**,对短名 / 同名函数会误计——本文件所有计数已用 `git grep` 复核。
