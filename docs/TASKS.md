# TASKS — Werewolf-agent

本文件只保留压缩任务索引。产品阶段与当前路线以 `docs/PROJECT_MAP.md` 为准。

## P1 — completed

| Task | Status | Outputs |
|---|---|---|
| S0：gold game seed | completed | `docs/gold-game/s0-gold-game-seed.md`, `docs/gold-game/g001-game-log.json` |
| S1：Game Log parser / validator | completed | `src/werewolf_eval/game_log.py`, `src/werewolf_eval/validate_game_log.py`, `tests/test_game_log.py` |
| S2 / E2：deterministic scoring | completed | `src/werewolf_eval/scoring.py`, `src/werewolf_eval/score_game.py`, `tests/test_scoring.py`, `docs/gold-game/s2-score-log.json` |
| S3 / E3：rule attribution | completed | `src/werewolf_eval/attribution.py`, `src/werewolf_eval/attribute_game.py`, `tests/test_attribution.py`, `docs/gold-game/s3-rule-attribution.json` |
| S4：Consensus Log parser / validator | completed | `src/werewolf_eval/consensus_log.py`, `src/werewolf_eval/validate_consensus_log.py`, `tests/test_consensus_log.py`, `docs/gold-game/g001-consensus-log.json` |
| S5：semantic label validation / saved-label scoring | completed | `src/werewolf_eval/semantic_labels.py`, `src/werewolf_eval/validate_semantic_labels.py`, `scripts/research/evaluate_semantic_labels.py`, `tests/test_semantic_labels.py` |
| S6 / E4：static demo renderer | completed | `src/werewolf_eval/render_demo.py`, `tests/test_render_demo.py`, `docs/demo/phase1-gold-demo.html`, `docs/demo/phase2-runtime-demo.html` |
| D1：Decision Log parser / validator | completed | `src/werewolf_eval/decision_log.py`, `src/werewolf_eval/validate_decision_log.py`, `tests/test_decision_log.py`, `docs/gold-game/g001-decision-log.json` |
| D2：Decision Log scoring integration | completed | `src/werewolf_eval/scoring.py`, `src/werewolf_eval/score_game.py`, `src/werewolf_eval/render_demo.py`, `docs/gold-game/s2-score-log.json` |
| G1a：scripted deterministic fresh-log runner | completed | `src/werewolf_eval/scripted_game.py`, `src/werewolf_eval/run_scripted_game.py`, `docs/game-scripts/g1-scripted-game.json`, `docs/generated-games/g1-scripted-game-log.json` |
| G1b：deterministic engine + mock agent contract | completed | `src/werewolf_eval/game_engine.py`, `src/werewolf_eval/run_mock_game.py`, `tests/test_game_engine.py`, `docs/generated-games/g1b-mock-agent-game-log.json` |
| G1c：wolf consensus + failure recovery | completed | `src/werewolf_eval/game_engine.py`, `src/werewolf_eval/run_mock_game.py`, `tests/test_game_engine.py`, `docs/generated-games/g1c-wolf-consensus-failure-audit.json` |
| G1d：fake-provider contract | completed | `src/werewolf_eval/provider_contract.py`, `src/werewolf_eval/fake_provider.py`, `tests/test_provider_contract.py` |
| G1e：provider-backed single-game smoke | completed | `src/werewolf_eval/deepseek_provider.py`, `src/werewolf_eval/run_deepseek_provider_game.py`, `tests/test_deepseek_provider.py` |
| G1f：DeepSeek consensus smoke | completed | `src/werewolf_eval/run_deepseek_consensus_game.py`, `tests/test_deepseek_consensus_game.py` |
| G1g：provider replay HTML | completed | `src/werewolf_eval/render_provider_replay.py`, `tests/test_render_provider_replay.py`, `docs/demo/phase3-g1f-provider-replay.html` |
| G1h：live runtime event spine | completed | `src/werewolf_eval/runtime_events.py`, `src/werewolf_eval/run_g1h_fake_runtime.py`, `tests/test_runtime_events.py`, `tests/test_g1h_runtime_spine.py` |
| G2a：local observer server / protocol control plane | completed | `src/werewolf_eval/observer_protocol.py`, `src/werewolf_eval/observer_server.py`, `src/werewolf_eval/run_observer_server.py`, `tests/test_observer_protocol.py`, `tests/test_observer_server.py` |

## P2 — completed

| Task | Status | Outputs |
|---|---|---|
| G2b：Qt observer cockpit MVP | completed | `clients/qt_observer/src/ObserverApiClient.cpp`, `clients/qt_observer/src/ObserverSseParser.cpp`, `clients/qt_observer/qml/AppShell.qml`, `tests/test_qt_observer_static_contract.py` |
| G2c：God View / Role View visibility trust | completed | `src/werewolf_eval/observer_visibility.py`, `clients/qt_observer/qml/components/ViewBoundaryBadge.qml`, `clients/qt_observer/qml/components/ProjectionProofPanel.qml`, `tests/test_observer_visibility.py` |
| G2d：prompt configuration MVP | completed | `src/werewolf_eval/profile_config.py`, `clients/qt_observer/qml/MatchSetupView.qml`, `clients/qt_observer/qml/components/SeatEditorPanel.qml`, `tests/test_profile_config.py` |
| G3-1：live DeepSeek execution | completed | `src/werewolf_eval/deepseek_launcher.py`, `src/werewolf_eval/run_observer_server.py`, `scripts/dev/run_deepseek_live_smoke.py`, `tests/test_deepseek_launcher.py` |
| G3-2：Qt live/fake toggle | completed | `clients/qt_observer/qml/components/ModeControl.qml`, `clients/qt_observer/qml/components/DataSourceChip.qml`, `clients/qt_observer/src/ObserverApiClient.cpp`, `tests/test_qt_observer_static_contract.py` |
| G3-3：runtime manifest honesty + real smoke evidence | completed | `src/werewolf_eval/run_deepseek_consensus_game.py`, `src/werewolf_eval/deepseek_launcher.py`, `scripts/dev/run_deepseek_live_smoke.py`, `tests/test_deepseek_live_smoke.py` |
| P2-A-1：完整自演化的一局 | completed | `src/werewolf_eval/emergent_engine.py`, `src/werewolf_eval/provider_agent.py`, `tests/test_emergent_engine.py` |
| P2-A-2：真实 DeepSeek 涌现对局 live smoke | completed | `src/werewolf_eval/emergent_engine.py`, `scripts/dev/run_deepseek_live_smoke.py`, `tests/test_deepseek_live_smoke.py` |
| P2-B：开局配置 / BYO-key / per-seat provider setup | completed | `src/werewolf_eval/user_config_library.py`, `src/werewolf_eval/provider_registry.py`, `clients/qt_observer/qml/MatchSetupView.qml`, `clients/qt_observer/src/ObserverApiClient.cpp` |
| P2-C：实时观战上帝视角 UI | completed | `clients/qt_observer/qml/TheaterView.qml`, `clients/qt_observer/qml/components/CockpitSurface.qml`, `clients/qt_observer/qml/components/RoleCard.qml`, `clients/qt_observer/qml/components/DataSourceChip.qml` |
| P2-D：结算画面 / 历史回看管理 | completed | `src/werewolf_eval/settlement_bundle.py`, `clients/qt_observer/qml/SettlementView.qml`, `clients/qt_observer/qml/components/SettlementReport.qml`, `clients/qt_observer/qml/HistoryView.qml`, `tests/test_settlement_bundle.py` |
| R0：Windows 桌面发行 / 客户端内更新 | completed | `scripts/release/build-velopack-release.sh`, `scripts/release/upload-github-release.sh`, `scripts/release/release-notes.md`, `scripts/release/smoke-test.sh`, `scripts/release/run-installed-local-e2e.ps1`, `src/werewolf_eval/release_host/update_control.py`, `src/werewolf_eval/release_host/velopack_runtime.py`, `clients/qt_observer/qml/ProviderSettingsView.qml` |

## P3 — current direction

| Task | Status | Outputs |
|---|---|---|
| P3-A-0：Agent 角色体验与真人参与路线转向 | completed | `docs/PROJECT_MAP.md`, `docs/superpowers/specs/2026-07-02-agent-roleplay-human-game-pivot-design.md` |
| P3-A：Agent Card + Memory Spine | planned | — |
| P3-B：博弈脚手架与桌面发言 | planned | — |
| P3-C：真人座位实时参与 | in_progress | P3-C-0 protocol + route skeleton complete; P3-C-1d single-human backend closeout complete; remaining response/table-talk depends on P3-B |
| P3-C-0：真人 action protocol spec + minimal server skeleton | completed | `docs/PROJECT_MAP.md`, `docs/superpowers/specs/2026-07-03-p3-c-0-server-action-protocol-design.md`, `src/werewolf_eval/participant_protocol.py`, `src/werewolf_eval/observer/participant_api.py`, `tests/test_participant_protocol.py`, `tests/test_participant_routes.py` |
| P3-C-1：single human seat 接入 game loop | completed | P3-C-1a villager speech/vote slice complete; P3-C-1b profile-driven single human seat backend complete; P3-C-1c final_words/reconnect/timeout backend smoke complete; P3-C-1d route hardening/spec alignment complete; response remains pending with P3-B table-talk |
| P3-C-1a：真人村民发言/投票 game-loop 切片 | completed | `src/werewolf_eval/participant_controller.py`, `src/werewolf_eval/emergent_engine.py`, `src/werewolf_eval/run_emergent_fake_runtime.py`, `src/werewolf_eval/observer/participant_api.py`, `tests/test_participant_game_loop.py` |
| P3-C-1b：profile-driven single human seat 后端 | completed | `src/werewolf_eval/profile_config.py`, `src/werewolf_eval/observer/launch.py`, `src/werewolf_eval/observer/run_manager.py`, `src/werewolf_eval/emergent_engine.py`, `src/werewolf_eval/run_emergent_fake_runtime.py`, `src/werewolf_eval/run_emergent_deepseek_game.py`, `tests/test_profile_config.py`, `tests/test_observer_server.py`, `tests/test_participant_game_loop.py` |
| P3-C-1c：遗言 + 重连/超时后端 smoke | completed | `src/werewolf_eval/emergent_engine.py`, `src/werewolf_eval/participant_controller.py`, `src/werewolf_eval/observer/participant_api.py`, `src/werewolf_eval/display_labels.py`, `tests/test_participant_game_loop.py`, `tests/test_participant_routes.py` |
| P3-C-1d：participant route hardening + spec alignment | completed | `src/werewolf_eval/observer/handler.py`, `src/werewolf_eval/observer/participant_api.py`, `tests/test_participant_routes.py`, `docs/superpowers/specs/2026-07-03-p3-c-0-server-action-protocol-design.md`, `docs/PROJECT_MAP.md` |
| P3-D：趣味性复盘入口 | planned | — |
| P3-E-0：跨平台客户端迁移路线 spec | completed | `docs/PROJECT_MAP.md`, `DESIGN.md`, `docs/superpowers/specs/2026-07-02-p3-e-client-platform-migration-design.md` |
| P3-E-1：Flutter protocol spike | completed | `clients/flutter_app/`, `clients/flutter_app/lib/src/protocol/participant_api_client.dart`, `clients/flutter_app/lib/src/app/session_controller.dart`, `clients/flutter_app/lib/src/screens/live_room_screen.dart`, `clients/flutter_app/lib/src/ui/composer_rail.dart` |
| P3-E-2：Mobile-first live room slice | planned | future Flutter live-room slice |
| P3-E-3：Human seat client slice | planned | depends on P3-C-0 and P3-C-1b profile-driven single-human backend |
| P3-E-4：Desktop parity / Qt retirement gate | planned | future parity review |

## P4 — downstream

| Task | Status | Outputs |
|---|---|---|
| P4-A：评测 · 复盘 | planned | `docs/EVALUATION_RUBRIC.md` |
| P4-B：历史对战聚合 | planned | — |
| P4-C：动态排行榜 | planned | — |
