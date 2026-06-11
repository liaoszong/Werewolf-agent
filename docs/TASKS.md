# TASKS — Werewolf-agent Task Status

> **⚠️ 产品阶段与"下一步"以 `docs/PROJECT_MAP.md` 为准(2026-06-05 起)。** 本文件中"下一候选 = G4 evaluation platform"等一切"下一步"表述均已 **superseded**——当前工作任务请读 PROJECT_MAP,不要从本文件推断。旧 G/E/S → 新 P 编号映射见 PROJECT_MAP「Reconcile」表。本文件保留为 P1/G-track 任务状态台账。

> **Progress note:** 本文件描述 Phase 1 任务依赖关系和计划状态，但任务完成状态可能滞后于实际进度。判断当前进度时，必须以已合入 PR 和 main 上实际存在的产物文件为准。如果本文件状态与 PR / main 文件冲突，以 PR / main 文件为准。

> **Roadmap note:** Phase 2 / Phase 3 route boundaries are defined in `docs/ROADMAP.md`. This file tracks task status and candidate engineering work; it does not replace the roadmap.

任务按类型组织。每个 spike 通过前不展开对应的 engineering task。

---

## Product Milestone

**M1：评测系统概念验证完成**

- 输入：一局 6 人狼人杀结构化 Game Log（Spike 0 产出。优先路径：人工编写虚拟对局）。
- 输出：确定性的 outcome_score + rule_integrity_score + 过程指标 + 规则归因 + 单局评分卡 + Leaderboard UI demo（静态 HTML）。
- 验收：两次运行同一 Game Log 所有指标一致；非技术用户 3 分钟能理解评测系统工作方式。
- 状态：`completed`（deterministic MVP closure：S0/S1/S2/S3/S6 已完成；S4/S5 延后到 Phase 2）
- 完成产物：
  - `docs/gold-game/g001-game-log.json`
  - `docs/gold-game/s2-score-log.json`
  - `docs/gold-game/s2-metrics-summary.json`
  - `docs/gold-game/s3-rule-attribution.json`
  - `docs/demo/phase1-gold-demo.html`
- 注意：Phase 1 的 decision_quality_score 恒为 0（无真实 Decision Log），不宣称已真实可用。Consensus Log 和 Decision Log 的真实数据采集转入 Phase 2。

---

## Spike Tasks

### S0：名局筛选 + 资料完整性 + 版权风险

- 状态：`completed`（人工构造虚拟对局，PR #2）
- 产出：`docs/gold-game/s0-gold-game-seed.md`。
- 依赖：无。
- 通过标准：见 `@docs/SPIKES.md` Spike 0。

### S1：Game Log schema 验证

- 状态：`completed`（PR #3 plan, PR #4 impl）
- 产出：`docs/gold-game/g001-game-log.json` + `docs/gold-game/s1-schema-validation.md`。
- 依赖：S0。
- 通过标准：见 `@docs/SPIKES.md` Spike 1。

### S2：确定性评分器验证

- 状态：`completed`（PR #5 plan, PR #6 impl）
- 产出：`docs/gold-game/s2-score-log.json` + `docs/gold-game/s2-metrics-summary.json` + `docs/gold-game/s2-scoring-validation.md`。
- 依赖：S1。
- 通过标准：见 `@docs/SPIKES.md` Spike 2。

### S3：规则归因验证

- 状态：`completed`（PR #7 impl）
- 产出：`docs/gold-game/s3-rule-attribution.json` + `docs/gold-game/s3-attribution-validation.md`。
- 依赖：S2。
- 通过标准：见 `@docs/SPIKES.md` Spike 3。

### S4：狼人 Consensus Log schema 验证

- 状态：`deferred_to_phase_2`（真实 Consensus Log 为 Phase 2 启用；Phase 1 deterministic MVP 不再阻塞于人工 consensus sample）
- 产出：人工 gold consensus sample + schema 可用性评估。
- 依赖：S1（可与 S2、S3 并行）。
- 通过标准：见 `@docs/SPIKES.md` Spike 4。

### S5：AI 语义标注可行性验证

- 状态：`deferred_to_phase_2`（AI 标注与真实 Agent 输出、Decision Log 启用一起验证；Phase 1 demo 不依赖 AI 标注）
- 产出：标注准确率报告 + 一致性报告 + token 统计。
- 依赖：无（使用独立构造的样例，不依赖前面 spike）。
- 通过标准：见 `@docs/SPIKES.md` Spike 5。

### S6：Leaderboard UI demo 验证

- 状态：`completed`（PR #8 plan, PR #9 impl）
- 产出：`docs/demo/phase1-gold-demo.html`。
- 依赖：S2（可使用真实评分 + mock 数据，不需要 S3 归因先完成）。
- 通过标准：见 `@docs/SPIKES.md` Spike 6。

---

## Phase 2 Candidate Engineering Tasks

**E1-E4、D1/D2、S4/S5 已作为 Phase 2 runtime / input entries 完成，G1a 已作为 Phase 3 scripted deterministic fresh-log runner 完成，G1b deterministic game engine + mock agent contract 已完成，G1c wolf consensus + failure recovery 已完成，G1d fake-provider contract 已完成，G1e provider-backed single-game smoke 已完成，G1f DeepSeek consensus smoke 已完成，G1g provider replay HTML 已完成，G1h Live Runtime Event Spine 已完成，G2a Local Observer Server / Protocol Control Plane 已完成。** G2b Qt Observer MVP、G2c God View / Role View、G2d Prompt Configuration MVP（含 G2d-2 Qt profile setup UI）、G3-1 live DeepSeek execution、G3-2 Qt live/fake toggle、G3-3 manifest real-model + real smoke 均已完成并合入 `main`。**（历史,已 superseded:** 此处原记"下一候选 = G4 evaluation platform（real multi-game leaderboard / role-separated scorecards / provider-model 比较）";真实当前阶段/下一步以 `docs/PROJECT_MAP.md` 为准 —— Phase 2（P2-A 涌现引擎 / P2-C 剧场 / P2-D 结算），G4 评测能力归 P3。**）** G1a-G1h 作为 audit/replay/log bundle/provider trace/failure audit/event spine foundation 保留，G2a 作为 protocol boundary 保留。L1 real multi-game Leaderboard 降级为 G4 evaluation-platform dependent capability，不再是当前 next candidate。以下记录各工程任务的完成状态与产物路径，阶段边界以 `docs/ROADMAP.md` 为准。

### E1：Game Log 解析器

- 状态：`completed`（Phase 2 E1 runtime entry；Game Log parser / validator 已实现）
- 产出：`src/werewolf_eval/game_log.py` + `src/werewolf_eval/validate_game_log.py` + `tests/test_game_log.py`。
- 说明：读取结构化 Game Log JSON，验证 schema，转换为内部数据结构。

### E2：确定性评分器

- 状态：`completed`（Phase 2 E2 deterministic scorer；Score Log / Metrics Summary runtime 已实现）
- 产出：`src/werewolf_eval/scoring.py` + `src/werewolf_eval/score_game.py` + `tests/test_scoring.py`。
- 说明：实现 EVALUATION_RUBRIC.md 中所有确定性评分规则。输出 Score Log。

### E3：规则归因引擎

- 状态：`completed`（Phase 2 E3 rule attribution engine；turn_points / top_attribution runtime 已实现）
- 产出：`src/werewolf_eval/attribution.py` + `src/werewolf_eval/attribute_game.py` + `tests/test_attribution.py`。
- 说明：实现归因规则匹配引擎。输出 turn_points + top_attribution。

### E4：可视化页面

- 状态：`completed`（Phase 2 runtime demo HTML exporter）
- 产出：`src/werewolf_eval/render_demo.py` + `tests/test_render_demo.py` + `docs/demo/phase2-runtime-demo.html`。
- 说明：构建可双击打开的单文件静态 HTML，不依赖后端、不依赖构建工具、不引入 React/Vite。该页面从 E1/E2/E3 runtime pipeline 生成，包含时间线、状态表、投票表、指标表、评分卡、Leaderboard，并保留 Phase 2 边界声明。

### D1：Decision Log runtime skeleton

- 状态：`completed`（Phase 2 Decision Log runtime input；Decision Log parser / validator 已实现）
- 产出：`docs/gold-game/g001-decision-log.json` + `src/werewolf_eval/decision_log.py` + `src/werewolf_eval/validate_decision_log.py` + `tests/test_decision_log.py`。
- 说明：读取人工 gold Decision Log JSON，验证其 `game_id` 与 Game Log 一致，验证 actor / target / visible_info_refs / decision_type / confidence 等字段。D1 不调用 AI，不启用 S5，不修改 scoring，`decision_quality_score` 仍未接入评分链。

### D2：Decision Log scoring integration

- 状态：`completed`（Phase 2A evaluator runtime closure；Decision Log 已接入 deterministic scoring）
- 产出：`src/werewolf_eval/scoring.py` + `src/werewolf_eval/score_game.py` + `src/werewolf_eval/render_demo.py` + `docs/gold-game/s2-score-log.json` + `docs/gold-game/s2-metrics-summary.json` + `docs/demo/phase2-runtime-demo.html`。
- 依赖：D1 + E2。
- 目标：将 Decision Log 接入 scoring，完成 deterministic visibility 检查和 decision_id 追溯。`decision_quality_score` 正向评分仍等待 S5 AI 语义判断。
- 边界：只实现 Rubric G.1 Step 1-2 deterministic visibility 检查和 decision_id 追溯；不调用 AI，不启用 S5，不做 Consensus Log，不宣称 `decision_quality_score` 完整可用（正向评分等待 S5 AI 语义判断）。
- 路线依据：`docs/prs/2026-05-30--phase2-next-step-research.md` + `docs/ROADMAP.md`。

### S4：Consensus Log runtime/input

- 状态：`completed`（Phase 2B collaboration input；Consensus Log parser / validator / fixture / CLI 已实现）
- 产出：`docs/gold-game/g001-consensus-log.json` + `src/werewolf_eval/consensus_log.py` + `src/werewolf_eval/validate_consensus_log.py` + `tests/test_consensus_log.py`。
- 依赖：E1 / S1；产品优先级上放在 D2 后。
- 目标：验证狼人夜间协商层 Consensus Log 的 parser / validator / fixture / CLI。
- 边界：不做 AI gameplay，不做 S5 语义标注，不接 scoring，不宣称 team coordination scoring 完整可用。

### S5：AI semantic labeling research and saved-label scoring integration

- 状态：`completed`（Phase 2B semantic input；saved semantic labels can feed deterministic `decision_quality_score`）
- 产出：`docs/semantic-labeling/s5-label-contract.md` + `docs/gold-game/s5-semantic-label-output.example.json` + `src/werewolf_eval/semantic_labels.py` + `src/werewolf_eval/validate_semantic_labels.py` + `scripts/research/evaluate_semantic_labels.py` + `tests/test_semantic_labels.py` + `tests/test_semantic_label_research.py` + `docs/gold-game/s5-score-log.json` + `docs/gold-game/s5-metrics-summary.json` + `docs/demo/phase2-s5-runtime-demo.html`。
- 依赖：D1 + D2。
- 目标：用已保存的 Semantic Label Log 为 Decision Log 对应 Score Records 赋 deterministic `decision_quality_score`。
- 边界：不做 provider integration，不做 live AI labeling，不做 gameplay，不做 multi-game Leaderboard。

### G1：Real AI Agent gameplay engine

G-track 子阶段以 `docs/ROADMAP.md` 为准；这里记录执行状态和候选工程任务。

#### G1a：scripted deterministic fresh-log runner

- 状态：`completed`
- 产出：`docs/game-scripts/g1-scripted-game.json` + `src/werewolf_eval/scripted_game.py` + `src/werewolf_eval/run_scripted_game.py` + `docs/generated-games/g1-scripted-game-log.json` + `docs/generated-games/g1-scripted-decision-log.json` + `docs/generated-games/g1-scripted-consensus-log.json` + `docs/generated-games/g1-scripted-score-log.json` + `docs/generated-games/g1-scripted-metrics-summary.json` + `docs/demo/phase3-g1-scripted-runtime-demo.html`。
- 作用：从 scripted scenario JSON 确定性生成 Game Log / Decision Log / Consensus Log，并接入 evaluator + replay demo。
- 边界：不是 Agent runtime，不接 provider，不做 live AI gameplay，不做 Web live observer / human-vs-AI UI，不做 real multi-game Leaderboard。

#### G1b：deterministic game engine + mock agent contract

- 状态：`completed`
- 产出：`src/werewolf_eval/game_engine.py` + `src/werewolf_eval/run_mock_game.py` + `tests/test_game_engine.py` + `docs/generated-games/g1b-mock-agent-game-log.json` + `docs/generated-games/g1b-mock-agent-decision-log.json` + `docs/generated-games/g1b-mock-agent-score-log.json` + `docs/generated-games/g1b-mock-agent-metrics-summary.json` + `docs/demo/phase3-g1b-mock-agent-runtime-demo.html`。
- 作用：建立最小 6 人狼人杀状态机、private observation、structured `AgentAction`、mock agent，并生成可验证 Game Log / Decision Log。
- 边界：不接 provider，不做 live AI，不做 Web live observer，不生成 Consensus Log。

#### G1c：wolf consensus + failure recovery

- 状态：`completed`
- 产出：`src/werewolf_eval/game_engine.py` + `src/werewolf_eval/run_mock_game.py` + `tests/test_game_engine.py` + `docs/generated-games/g1c-wolf-consensus-game-log.json` + `docs/generated-games/g1c-wolf-consensus-decision-log.json` + `docs/generated-games/g1c-wolf-consensus-consensus-log.json` + `docs/generated-games/g1c-wolf-consensus-failure-audit.json` + `docs/generated-games/g1c-wolf-consensus-score-log.json` + `docs/generated-games/g1c-wolf-consensus-metrics-summary.json` + `docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`。
- 作用：处理狼人夜间协商协议、invalid action、timeout、parse failure、audit trail，生成可验证 Consensus Log。
- 边界：不做真实 provider，不伪造合法日志。

#### G1d：provider adapter research / fake-provider contract

- 状态：`completed`
- 作用：研究 provider boundary、secrets、成本、超时、fake provider contract。
- 边界：Research PR 优先，不直接接 live API。

#### G1e：provider-backed single-game smoke

- 状态：`completed`
- 作用：本地预算受控地跑一局 provider-backed game。
- 边界：不做 CI live calls，不做 multi-game Leaderboard，不做人机 UI。
- 产物：`src/werewolf_eval/deepseek_provider.py`（DeepSeek 适配器）、`src/werewolf_eval/run_deepseek_provider_game.py`（CLI + `--allow-live-api` guard）、`tests/test_deepseek_provider.py`、`tests/test_deepseek_provider_game.py`。

#### G1f：DeepSeek consensus smoke

- 状态：`completed`
- 作用：在 G1e DeepSeek 适配器基础上，增加以独立狼人角色（p1/p2）分别调用 provider 的 consensus 模式，生成 Game Log / Decision Log / Consensus Log / Provider Trace / Failure Audit。
- 边界：不做 CI live calls，不做 multi-game Leaderboard，不做人机 UI。
- 产物：`src/werewolf_eval/run_deepseek_consensus_game.py`（CLI + `--allow-live-api` guard）、`tests/test_deepseek_consensus_game.py`、`.tmp/g1f-deepseek-consensus-smoke/*.json`（本地 smoke artifact）。

#### G1g：provider replay HTML

- 状态：`completed`
- 作用：为 provider-backed 游戏包生成独立静态 HTML 回放报告，供审查者查阅真实 provider 对局、consensus、provider trace 和 failure audit，无需阅读原始 JSON。
- 边界：offline audit artifact only。不做实时 API 调用，不修改 game state / scoring / engine / provider，不做 primary UX，不做 live observer，不做真实排行榜。
- 产物：`src/werewolf_eval/render_provider_replay.py`、`tests/test_render_provider_replay.py`、`docs/demo/phase3-g1f-provider-replay.html`。

#### G1h：Live Runtime Event Spine

- 状态：`completed`（plan 文件 `docs/harness/plans/2026-06-03--g1h-live-runtime-event-spine-plan.md`；implementation merged in PR #38）
- 作用：把 real/fake provider single-game runtime 输出升级为 client-agnostic live runtime event spine，为后续 local observer server、Qt/QML client、Web client、replay/live dual mode 和 evaluation platform 提供稳定输入。
- Scope：real/fake provider single-game runtime compatibility、`events.jsonl`、runtime snapshots、prompt manifest、provider lifecycle events、standard log bundle compatibility。
- Non-goals：不做 Qt/QML client，不做 Web observer/server，不做 prompt editor UI，不做 multi-provider arena，不做 leaderboard，不改 scoring formula，不改 validators，不改 demo renderer。
- 核心产物：`src/werewolf_eval/runtime_events.py`、`src/werewolf_eval/run_g1h_fake_runtime.py`、`tests/test_runtime_events.py`、`tests/test_g1h_runtime_spine.py`、`events.jsonl` contract、runtime snapshots、prompt manifest、provider lifecycle events、standard log bundle compatibility、与 Game Log / Decision Log / Consensus Log / Provider Trace / Failure Audit 的引用兼容关系。

#### G2a：Local Observer Server / Protocol Control Plane

- 状态：`completed`（plan 文件 `docs/harness/plans/2026-06-03--g2a-local-observer-server-protocol-control-plane-plan.md`）
- 作用：通过本地 client-agnostic protocol 暴露 G1h event spine、run status、snapshots、historical run artifacts，并为后续 Qt/Web observer client 提供协议边界。
- Scope：REST/stream protocol、run/status/artifact/snapshot/event 查询与订阅、minimum match/profile contract seed for default-template launch、visibility trust slices from day one。
- Non-goals：不做 Qt/QML client，不做 Web observer UI，不做完整 prompt/profile editor，不做 multi-provider arena，不做 leaderboard，不改 scoring formula，不改 runtime game behavior。
- 核心产物：`src/werewolf_eval/observer_protocol.py`、`src/werewolf_eval/observer_server.py`、`src/werewolf_eval/run_observer_server.py`、`tests/test_observer_protocol.py`、`tests/test_observer_server.py`。

#### G2b：Qt Observer Cockpit MVP

- 状态：`completed`（plan 文件 `docs/harness/plans/2026-06-03--g2b-qt-observer-cockpit-mvp-plan.md`）
- 作用：将 `clients/qt_observer` Qt6 Quick scaffold 转化为第一个 game-like observer cockpit MVP，通过 G2a client-agnostic protocol 展示 Home/Lobby、default match setup、preflight、live cockpit（run status、player cards、event timeline、perspective switcher、audit links）、history/replay。
- 核心产物：`clients/qt_observer/src/ObserverApiClient.h/cpp`（Qt Network 协议适配器）、`clients/qt_observer/src/ObserverSseParser.h/cpp`（SSE frame parser）、`clients/qt_observer/qml/AppShell.qml` / `HomeView.qml` / `MatchSetupView.qml` / `PreflightView.qml` / `LiveCockpitView.qml` / `HistoryView.qml`（QML views）、`clients/qt_observer/qml/components/RoleCard.qml` / `EventTimeline.qml` / `PerspectiveSwitcher.qml` / `AuditLinksPanel.qml` / `StatusBadge.qml`（QML components）、`clients/qt_observer/tests/tst_observer_sse_parser.cpp`（QtTest）、`tests/test_qt_observer_static_contract.py`（Python static contract tests）。
- 依赖：G2a Local Observer Server / Protocol Control Plane。
- Non-goals：不做 prompt/profile editor，不做 Web observer client，不做 human-vs-AI UI，不做 multi-provider arena，不做 leaderboard，不做 Python runtime 直接绑定，不做本地 artifact 文件读取。

#### G2c：God View / Role View Visibility Trust

- 状态：`completed`（plan 文件 `docs/harness/plans/2026-06-03--g2c-god-role-view-visibility-trust-plan.md`）
- 作用：将 god-view state 与 role-view projection 分离，使隐藏信息在 God/Public/Role/Team 视角下显式、可审计、端到端可执行；通过 G2a protocol 暴露 server-side visibility projection。
- 核心产物：`src/werewolf_eval/observer_visibility.py`、`/api/runs/{run_id}/projection` 端点、`tests/test_observer_visibility.py`、`clients/qt_observer/qml/components/ViewBoundaryBadge.qml` / `ProjectionProofPanel.qml`。
- 依赖：G2a / G2b。
- Non-goals：不做 prompt/profile editor，不做 multi-run experiment system。

#### G2d：Prompt Configuration MVP

- 状态：`completed`（含 G2d-1 backend slice 与 G2d-2 Qt profile setup UI；spec `docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md`；plan `docs/harness/plans/2026-06-04--g2d-prompt-configuration-mvp-plan.md`）
- 作用：通过受控的 server-side JSON profile surface 配置可复用、可校验、可审计的 role defaults / seat overrides / resolved seat configs，并以 fake-deterministic 执行记录 declared provider/model/prompt/strategy；Qt `MatchSetupView` 提供 select/edit/validate/launch（G2d-2）。
- 核心产物：`src/werewolf_eval/profile_config.py`、`/api/profiles` / `/api/profiles/{name}` / `/api/profiles/validate` 端点、`POST /api/runs` profile launch + `resolved-profile.json`、`tests/test_profile_config.py`、`clients/qt_observer/qml/MatchSetupView.qml` + `qml/components/SeatEditorPanel.qml`。
- 依赖：G2a / G2c。
- Non-goals：server-side profiles only（无本地 prompt template library）；不做 multi-provider arena，不做 leaderboard，不改 game engine / fake runtime。

#### G3-1：live DeepSeek execution（server-side）

- 状态：`completed`（merged to `main`）
- 作用：通过 observer server 用真实 DeepSeek provider 跑一局 profile，opt-in、fake-by-default。四重 gate（`mode=live` + `--allow-live-api` + env key + all-deepseek single-model seats）；fail-closed 预算 `max_requests=32` 按 launcher exit code 映射为 key-free run-status reason（`budget_exhausted`/`provider_failure`）；`resolved-profile.json` 记录 `execution_mode`/`live_api`。
- 核心产物：`src/werewolf_eval/deepseek_launcher.py`、`observer_server.py`（`_check_live_capability`/`_check_live_profile_shape`/gate matrix）、`run_observer_server.py`（`--allow-live-api`/`--api-key-env`/`--max-live-requests`）、`scripts/dev/run_deepseek_live_smoke.py`、`tests/test_deepseek_launcher.py`。
- Non-goals：server-side only；API key 仅存在于 server env；默认套件全程离线（从不读 key、不开 socket）。

#### G3-2：Qt live/fake toggle

- 状态：`completed`（merged to `main`）
- 作用：把 G3-1 的实时能力带到 Qt 座舱——只读 `GET /api/runtime/capabilities`、两次确认武装的 `ModeControl`、由 run-detail `execution_mode` 驱动的全局 `DataSourceChip` HUD（intent vs. truth）；gate 错误码 data-driven 原样显示；后续修复了 unreachable 空白行 bug 并将档位文案改为大白话（模拟（免费）/真实AI（计费））。
- 核心产物：`observer_protocol.build_runtime_capabilities`、`observer_server`（capabilities route + run-detail `execution_mode`）、`clients/qt_observer/src/ObserverApiClient.{h,cpp}`、`qml/components/ModeControl.qml` + `DataSourceChip.qml`、`qml/MatchSetupView.qml` + `AppShell.qml`、`tests/test_qt_observer_static_contract.py`。
- Non-goals：无 API-key UI；Qt 无 artifact 文件 I/O；fake 为无条件默认；key 不接触客户端。

#### G3-3：runtime-manifest honesty + real smoke + budget evidence

- 状态：`completed`（merged to `main`）
- 作用：把真实 deepseek 模型写进 runtime-spine `prompt-manifest.json`（此前硬编码 `"unknown"`）；为 gated smoke 增加 text-free `manifest_model_honest` 检查；真实 DeepSeek 冒烟跑通一次（PASS：一整局 6 人约 10 次 provider 调用，故 `max_requests=32` 保持不变）。
- 核心产物：`run_deepseek_consensus_game.py`（`model` 参数）、`deepseek_launcher.py`（穿透 model）、`scripts/dev/run_deepseek_live_smoke.py`（manifest 校验）、`tests/test_deepseek_consensus_game.py` / `test_deepseek_launcher.py` / `test_deepseek_live_smoke.py`。
- Non-goals：smoke 为 gated/manual；不做 CI live calls。

#### Backlog / prerequisite fix candidate：Decision Round Scoring Disambiguation

- 状态：`planned_backlog`
- 计划文件：`docs/harness/plans/2026-06-02--g1h-decision-round-scoring-disambiguation-plan.md`
- 作用：为 Decision Log 条目增加 `round` 字段，scoring 匹配时使用 round + action + phase + actor + target 消除跨轮次相同决策的歧义。
- 边界：该计划仍是有效 prerequisite / fix candidate，但不再占用 G1h 阶段名。是否先做取决于 G1h Live Runtime Event Spine plan 的 dependency gate。

### L1：Real multi-game Leaderboard

- 状态：`deferred_g4_dependent`
- 依赖：G1h event spine、G2 observer contracts、G3 experiment profiles、足够多局/多角色/多模型数据。
- 目标：形成真实多模型、多版本、按角色区分的 Leaderboard。
- 边界：不在没有多局数据时宣称真实排行榜完成。

---

## UX Acceptance

每个 engineering task 完成后必须提供：

| Task | UX 验收物 | 验收口径 |
|------|----------|---------|
| E1 | 无独立 UX（被 E2 消费） | schema 验证通过 |
| E2 | Score Log 可读摘要 | 每个评分能追溯到 rule_id 和 event_id |
| E3 | 归因面板 | 每个 turn_point 可展开查看触发的规则 |
| E4 | 页面截图（`docs/demo/phase2-runtime-demo.html`） | 非技术用户 3 分钟能查看该页面，复述谁赢了、关键转折点是什么、评测系统如何打分，并能看到明确的 `[deterministic]` / `[mock]` 标签和 Phase 2 边界声明 |
| D1 | Decision Log CLI 校验摘要 | 同一 Game Log + Decision Log 能稳定输出 `decision_log_id`、`game_id`、`decisions`、`source_label`，并拒绝非法 actor / refs / decision_type |
| D2 | Decision Log scoring 摘要 + runtime demo D2 边界声明 | 传入同一 Game Log + Decision Log 后，Score Log 中部分记录带 `decision_id`，gold game 的 canonical Score Log 所有 `rule_integrity_score` 均为 0（无违规 refs）；非法 refs 扣 -3 由 synthetic unit test 覆盖；页面明确标注 D2 只含 deterministic Step 1-2，`decision_quality_score` 仍为 0（正向评分等待 S5） |
| S4 | Consensus Log CLI 校验摘要 | 同一 Game Log + Consensus Log 能稳定输出 `consensus_log_id`、`game_id`、`consensuses`、`source_label`，并拒绝非法 participant / refs / status / final target |

---

## Demo Acceptance

**Demo 1：Phase 1 deterministic Gold Demo**

- 触发条件：S0/S1/S2/S3/S6 完成后。
- 演示内容：固定 Game Log → 确定性评分摘要 → 规则归因 → 静态 Leaderboard UI demo。
- 验收：同一 Game Log 的 deterministic 指标可复现；非技术用户 3 分钟内能复述谁赢了、关键转折点是什么、评测系统如何打分。
- 状态：`completed`（`docs/demo/phase1-gold-demo.html`）

**Demo 2：Phase 2 runtime pipeline demo**

- 状态：`completed`（`docs/demo/phase2-runtime-demo.html`；仅表示 E1/E2/E3 runtime pipeline 可生成可视化 demo，不表示真实 AI Agent / Decision Log / Consensus Log 已启用）
- 触发条件：Phase 2 charter 明确允许业务代码，并完成 E1-E4 或替代实现路径。
- 演示内容：运行时读取 Game Log → 计算 Score Log → 计算 Attribution → 输出或刷新 UI。
- 验收：同一 Game Log 可重新生成 `docs/demo/phase2-runtime-demo.html`，页面展示 Score / Metrics / Attribution / Leaderboard，并保留边界声明。

**Demo 3：Phase 2 Decision Log input validation**

- 状态：`completed`（`docs/gold-game/g001-decision-log.json`；仅表示 Decision Log runtime input 可被验证，不表示 `decision_quality_score` 已接入评分链）
- 触发条件：D1 完成。
- 演示内容：运行时读取 Game Log + Decision Log → 校验结构化决策输入。
- 验收：同一输入稳定输出 `validated decision_log_id=d1_g001_decision_log`、`game_id=g001`、`decisions=10`、`source_label=[人工 gold sample]`。

**Demo 4：Phase 2 Decision Log scoring integration**

- 状态：`completed`（`docs/demo/phase2-runtime-demo.html` 使用 Decision Log 生成 D2 deterministic decision score）
- 触发条件：D2 完成。
- 演示内容：运行时读取 Game Log + Decision Log → 计算 Score Log / Metrics Summary → 输出带 D2 边界声明的 HTML demo。
- 验收：同一输入稳定输出 `decision_id` 追溯到 Score Record，synthetic unit test 覆盖非法 refs → `rule_integrity_score = -3` 惩罚路径（canonical gold game 无违规 refs，所有 `rule_integrity_score` 均为 0）；页面明确说明 Decision Log 已接入但 `decision_quality_score` 仍为 0（正向评分等待 S5）。

**Demo 5：Phase 2 Consensus Log input validation**

- 状态：`completed`（`docs/gold-game/g001-consensus-log.json`；仅表示 Consensus Log runtime input 可被验证，不表示真实 AI 狼人协商、team coordination scoring 或 Consensus Log scoring 已启用）
- 触发条件：S4 完成。
- 演示内容：运行时读取 Game Log + Consensus Log → 校验狼人夜间协商结构化输入。
- 验收：同一输入稳定输出 `validated consensus_log_id=s4_g001_consensus_log`、`game_id=g001`、`consensuses=2`、`source_label=[人工 gold sample]`；invalid participant / refs / status / final target 由 unit tests 覆盖并拒绝。

**Demo 6：Phase 2 S5 saved semantic-label scoring**

- 状态：`completed`（`docs/demo/phase2-s5-runtime-demo.html`）
- 触发条件：S5 saved-label scoring integration 完成。
- 演示内容：运行时读取 Game Log + Decision Log + saved Semantic Label Log → 计算 Score Log / Metrics Summary → 输出带 S5 边界声明的 HTML demo。
- 验收：页面明确说明 semantic labels 来自 saved JSON，不是 live AI labeling；Score Log 中部分 `decision_quality_score` 不再全为 0；`decision_quality_total=1` 可追溯到 label rules。

**Demo 7：Phase 3 G1a scripted deterministic fresh-log runner**

- 状态：`completed`（`docs/demo/phase3-g1-scripted-runtime-demo.html`）
- 触发条件：G1a scripted deterministic fresh-log runner 完成。
- 演示内容：scripted scenario JSON → scripted deterministic Game Log / Decision Log / Consensus Log → Score Log / Metrics Summary → Runtime HTML Demo。
- 验收：同一 script 两次生成完全一致；三个 generated logs 均通过现有 validators；generated score log / metrics summary 的 `game_id` 是 `g1_scripted_001` 且不残留 `s2_g001_*`；页面明确标注 scripted deterministic boundary，并明确不代表 live AI Agent gameplay。

---

## Stop / Review Gate

每个 spike 完成后必须复盘，不连续推进 engineering。检查清单：

- [ ] 本轮有用户可见变化？（截图、输出、页面）
- [ ] 确定性指标可复现？
- [ ] 所有 mock / gold / deterministic / real AI 标注清晰？
- [ ] 本轮不代表什么已明确？
- [ ] 下一步最大风险已识别？
- [ ] 是否连续两个任务没有用户可见变化？（如果是 → 停止，做 UX demo 或重排任务）
- [ ] 是否需要修改 EVALUATION_RUBRIC.md 的 stable 规则？
- [ ] 是否应该砍范围？（已发现某方向不可行 → 执行失败决策，不扩文档）

---

## 明确不做（持续更新）

| 条目 | 类型 | 状态 |
|------|------|------|
| AI 角色推理/心理分析 | 真正不做（G1h-G4 均不做） | active |
| 多模型适配 | 真正不做（G3 multi-provider arena 阶段启用） | active |
| 人机混战 UI | 真正不做（当前不做） | active |
| 多局对比 / 真实 Leaderboard | 真正不做（G4 evaluation platform 阶段启用） | active |
| 完整前端观战 UI | 真正不做（G2b Qt/Web observer 之前不做） | active |
| 前端技术栈预选（React/Vite 等） | 不做（Qt/QML 为推荐 first rich client 方向） | active |
| team_coordination_score 权重公式 | 延后到 G4（需积累 ≥ 10 局真实数据后校准） | active |
