# Tree

Use this file for navigation only. Verify implementation details by reading source files directly.

- Source: `git ls-files --cached --others --exclude-standard`
- Entries: 606

```text
./
├── .agents/
│   └── skills/
│       ├── committing-in-shared-worktrees/
│       │   └── SKILL.md
│       ├── guarding-prompt-bytes/
│       │   └── SKILL.md
│       ├── harness/
│       │   ├── agents/
│       │   │   └── openai.yaml
│       │   ├── refs/
│       │   │   ├── local-review.md
│       │   │   ├── visual-display.md
│       │   │   └── writing-plan.md
│       │   └── SKILL.md
│       ├── receiving-code-review/
│       │   └── SKILL.md
│       ├── running-live-games/
│       │   └── SKILL.md
│       ├── systematic-debugging/
│       │   ├── condition-based-waiting-example.ts
│       │   ├── condition-based-waiting.md
│       │   ├── CREATION-LOG.md
│       │   ├── defense-in-depth.md
│       │   ├── find-polluter.sh
│       │   ├── LICENSE.upstream
│       │   ├── root-cause-tracing.md
│       │   ├── SKILL.md
│       │   ├── test-academic.md
│       │   ├── test-pressure-1.md
│       │   ├── test-pressure-2.md
│       │   └── test-pressure-3.md
│       ├── tdd/
│       │   ├── LICENSE.upstream
│       │   ├── mocking.md
│       │   ├── SKILL.md
│       │   └── tests.md
│       ├── testing-and-process-control/
│       │   └── SKILL.md
│       └── verifying-qt-observer-ui/
│           └── SKILL.md
├── .claude/
│   └── hooks/
│       └── config-protection.cjs
├── .codex/
│   ├── hooks/
│   │   └── tree.mjs
│   └── hooks.json
├── .github/
│   ├── PULL_REQUEST_TEMPLATE/
│   │   ├── implementation.md
│   │   └── research.md
│   ├── workflows/
│   │   └── tests.yml
│   ├── codex-review-comment.md
│   └── writing-plan.md
├── clients/
│   └── qt_observer/
│       ├── assets/
│       │   ├── illustrations/
│       │   │   ├── avatars/
│       │   │   │   ├── guard.png
│       │   │   │   ├── hunter.png
│       │   │   │   ├── seer.png
│       │   │   │   ├── villager.png
│       │   │   │   ├── werewolf.png
│       │   │   │   └── witch.png
│       │   │   ├── scene/
│       │   │   │   ├── history-archive.png
│       │   │   │   ├── home-day.png
│       │   │   │   ├── home-night.png
│       │   │   │   ├── settings-desk.png
│       │   │   │   ├── setup-room.png
│       │   │   │   ├── table-day.png
│       │   │   │   └── table-night.png
│       │   │   └── tarot/
│       │   │       ├── guard.png
│       │   │       ├── hunter.png
│       │   │       ├── seer.png
│       │   │       ├── villager.png
│       │   │       ├── werewolf.png
│       │   │       └── witch.png
│       │   └── textures/
│       │       └── parchment.png
│       ├── qml/
│       │   ├── components/
│       │   │   ├── AppBackground.qml
│       │   │   ├── AppButton.qml
│       │   │   ├── AppCard.qml
│       │   │   ├── AuditLinksPanel.qml
│       │   │   ├── CharacterAvatar.qml
│       │   │   ├── CockpitSurface.qml
│       │   │   ├── ConfirmDialog.qml
│       │   │   ├── DataSourceChip.qml
│       │   │   ├── EmptyState.qml
│       │   │   ├── EventLogPanel.qml
│       │   │   ├── EventTimeline.qml
│       │   │   ├── EvidenceConsole.qml
│       │   │   ├── GearButton.qml
│       │   │   ├── GlowDot.qml
│       │   │   ├── HudCard.qml
│       │   │   ├── LiveStatusCard.qml
│       │   │   ├── ModeControl.qml
│       │   │   ├── NavRail.qml
│       │   │   ├── ParchmentComboBox.qml
│       │   │   ├── ParchmentPopupMenu.qml
│       │   │   ├── PerspectiveSwitcher.qml
│       │   │   ├── PhaseBackground.qml
│       │   │   ├── PhaseCard.qml
│       │   │   ├── PhaseIndicator.qml
│       │   │   ├── PlaybackBar.qml
│       │   │   ├── PlaybackControls.qml
│       │   │   ├── ProjectionProofPanel.qml
│       │   │   ├── RoleCard.qml
│       │   │   ├── SceneBackground.qml
│       │   │   ├── SeatCard.qml
│       │   │   ├── SeatEditorPanel.qml
│       │   │   ├── SeatRing.qml
│       │   │   ├── SectionHeader.qml
│       │   │   ├── SettlementReport.qml
│       │   │   ├── SettlementSpine.qml
│       │   │   ├── SetupRoleCard.qml
│       │   │   ├── SpeechTheater.qml
│       │   │   ├── StatusBadge.qml
│       │   │   ├── ViewBoundaryBadge.qml
│       │   │   ├── VotesPanel.qml
│       │   │   └── WinnerBanner.qml
│       │   ├── AppShell.qml
│       │   ├── DesignPreviewView.qml
│       │   ├── EventPresentationQueue.qml
│       │   ├── HistoryView.qml
│       │   ├── HomeView.qml
│       │   ├── I18n.qml
│       │   ├── Illustrations.qml
│       │   ├── MatchSetupView.qml
│       │   ├── PreflightView.qml
│       │   ├── ProviderSettingsView.qml
│       │   ├── SettlementView.qml
│       │   ├── TheaterView.qml
│       │   └── Theme.qml
│       ├── src/
│       │   ├── CredentialStore.cpp
│       │   ├── CredentialStore.h
│       │   ├── ObserverApiClient.cpp
│       │   ├── ObserverApiClient.h
│       │   ├── ObserverSseParser.cpp
│       │   └── ObserverSseParser.h
│       ├── tests/
│       │   ├── tst_observer_api_client.cpp
│       │   └── tst_observer_sse_parser.cpp
│       ├── CMakeLists.txt
│       ├── main.cpp
│       ├── Main.qml
│       └── README.md
├── docs/
│   ├── adr/
│   │   ├── 0001-client-agnostic-live-observer-protocol.md
│   │   ├── 0002-src-layout-installable-package.md
│   │   ├── 2026-06-09-action-runtime-orchestrator.md
│   │   ├── 2026-06-11-byo-key-security-invariants.md
│   │   ├── 2026-06-11-engine-visibility-single-source.md
│   │   ├── 2026-06-11-fake-default-live-gate-testing-strategy.md
│   │   ├── 2026-06-11-observer-visibility-layering.md
│   │   ├── 2026-06-11-role-facts-single-source.md
│   │   └── 2026-06-12-perspective-not-access-control-boundary.md
│   ├── demo/
│   │   ├── phase1-gold-demo.html
│   │   ├── phase2-runtime-demo.html
│   │   ├── phase2-s5-runtime-demo.html
│   │   ├── phase3-g1-scripted-runtime-demo.html
│   │   ├── phase3-g1b-mock-agent-runtime-demo.html
│   │   ├── phase3-g1c-wolf-consensus-runtime-demo.html
│   │   ├── phase3-g1d-fake-provider-runtime-demo.html
│   │   └── phase3-g1f-provider-replay.html
│   ├── game-scripts/
│   │   └── g1-scripted-game.json
│   ├── generated-games/
│   │   ├── g1-scripted-consensus-log.json
│   │   ├── g1-scripted-decision-log.json
│   │   ├── g1-scripted-game-log.json
│   │   ├── g1-scripted-metrics-summary.json
│   │   ├── g1-scripted-score-log.json
│   │   ├── g1b-mock-agent-decision-log.json
│   │   ├── g1b-mock-agent-game-log.json
│   │   ├── g1b-mock-agent-metrics-summary.json
│   │   ├── g1b-mock-agent-score-log.json
│   │   ├── g1c-wolf-consensus-consensus-log.json
│   │   ├── g1c-wolf-consensus-decision-log.json
│   │   ├── g1c-wolf-consensus-failure-audit.json
│   │   ├── g1c-wolf-consensus-game-log.json
│   │   ├── g1c-wolf-consensus-metrics-summary.json
│   │   ├── g1c-wolf-consensus-score-log.json
│   │   ├── g1d-fake-provider-decision-log.json
│   │   ├── g1d-fake-provider-game-log.json
│   │   ├── g1d-fake-provider-metrics-summary.json
│   │   ├── g1d-fake-provider-provider-trace.json
│   │   ├── g1d-fake-provider-score-log.json
│   │   └── prompt-version-ledger.json
│   ├── gold-game/
│   │   ├── g001-consensus-log.json
│   │   ├── g001-decision-log.json
│   │   ├── g001-game-log.json
│   │   ├── s0-gold-game-seed.md
│   │   ├── s1-schema-validation.md
│   │   ├── s2-metrics-summary.json
│   │   ├── s2-score-log.json
│   │   ├── s2-scoring-validation.md
│   │   ├── s3-attribution-validation.md
│   │   ├── s3-rule-attribution.json
│   │   ├── s5-metrics-summary.json
│   │   ├── s5-score-log.json
│   │   ├── s5-semantic-label-eval-set.json
│   │   └── s5-semantic-label-output.example.json
│   ├── harness/
│   │   ├── designs/
│   │   │   ├── 2026-06-03--live-ai-werewolf-experiment-platform-charter.md
│   │   │   └── 2026-06-03--live-ai-werewolf-experiment-platform-charter.zh.md
│   │   ├── plans/
│   │   │   ├── 2026-05-29--e1-game-log-parser-validation-plan.md
│   │   │   ├── 2026-05-29--phase1-closure-phase2-boundary-alignment-plan.md
│   │   │   ├── 2026-05-29--s0-gold-game-seed-plan.md
│   │   │   ├── 2026-05-29--s1-game-log-schema-validation-plan.md
│   │   │   ├── 2026-05-29--s2-deterministic-scorer-validation-plan.md
│   │   │   ├── 2026-05-29--s3-rule-attribution-validation-plan.md
│   │   │   ├── 2026-05-29--s6-leaderboard-ui-demo-validation-plan.md
│   │   │   ├── 2026-05-30--d1-decision-log-runtime-skeleton-plan.md
│   │   │   ├── 2026-05-30--d2-decision-log-scoring-integration-plan.md
│   │   │   ├── 2026-05-30--e2-deterministic-scorer-plan.md
│   │   │   ├── 2026-05-30--e3-rule-attribution-engine-plan.md
│   │   │   ├── 2026-05-30--e4-runtime-demo-html-plan.md
│   │   │   ├── 2026-05-30--roadmap-alignment-plan.md
│   │   │   ├── 2026-05-30--s4-consensus-log-runtime-input-plan.md
│   │   │   ├── 2026-05-30--s4x-context-budget-hardening-plan.md
│   │   │   ├── 2026-05-30--s5-semantic-label-research-plan.md
│   │   │   ├── 2026-05-31--g1-scripted-game-runner-plan.md
│   │   │   ├── 2026-05-31--g1b-engine-mock-agent-contract-plan.md
│   │   │   ├── 2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md
│   │   │   ├── 2026-05-31--review-packet-gate-v1-plan.md
│   │   │   ├── 2026-05-31--s5-semantic-label-scoring-integration-plan.md
│   │   │   ├── 2026-06-01--pre-g1d-evaluation-trust-hardening-plan.md
│   │   │   ├── 2026-06-02--g1d-fake-provider-contract-harness-plan.md
│   │   │   ├── 2026-06-02--g1e-deepseek-provider-smoke-plan.md
│   │   │   ├── 2026-06-02--g1f-deepseek-consensus-smoke-plan.md
│   │   │   ├── 2026-06-02--g1g-provider-replay-html-plan.md
│   │   │   ├── 2026-06-02--g1h-decision-round-scoring-disambiguation-plan.md
│   │   │   ├── 2026-06-03--g1h-contract-closeout-route-docs-alignment-plan.md
│   │   │   ├── 2026-06-03--g1h-live-runtime-event-spine-plan.md
│   │   │   ├── 2026-06-03--g2a-local-observer-server-protocol-control-plane-plan.md
│   │   │   ├── 2026-06-03--g2b-qt-observer-cockpit-mvp-plan.md
│   │   │   ├── 2026-06-03--g2c-god-role-view-visibility-trust-plan.md
│   │   │   ├── 2026-06-04--g2d-2-qt-setup-ui-plan.md
│   │   │   ├── 2026-06-04--g2d-prompt-configuration-mvp-plan.md
│   │   │   ├── 2026-06-05--g3-1-live-deepseek-execution-plan.md
│   │   │   ├── 2026-06-05--g3-2-qt-live-toggle-plan.md
│   │   │   ├── 2026-06-06--p2-c-1-theater-view-plan.md
│   │   │   ├── 2026-06-06--p2-d-settlement-screen-plan.md
│   │   │   ├── 2026-06-08--full-health-check.md
│   │   │   ├── 2026-06-08--p2b-byo-key-rework-plan.md
│   │   │   ├── 2026-06-11--b2-engine-visibility-single-source-plan.md
│   │   │   ├── 2026-06-11--b3-scoring-split-plan.md
│   │   │   ├── 2026-06-11--b4-observer-visibility-layering-plan.md
│   │   │   ├── 2026-06-11--foundation-artifacts-pyproject-plan.md
│   │   │   ├── 2026-06-11--l4-guard-arm-plan.md
│   │   │   ├── 2026-06-11--observer-server-split-plan.md
│   │   │   ├── 2026-06-11--provider-launcher-mechanical-refactor-plan.md
│   │   │   ├── 2026-06-11--sys-a2-role-single-source-plan.md
│   │   │   ├── 2026-06-11--sys-b1-prompt-renderer-registry-plan.md
│   │   │   ├── 2026-06-12--audit-closeout-rules-invariants-docs-smoke-plan.md
│   │   │   ├── 2026-06-12--b2-engine-failure-classification-plan.md
│   │   │   ├── 2026-06-12--c12-score-id-race-plan.md
│   │   │   ├── 2026-06-12--l4-guard-witch-coord-arm-plan.md
│   │   │   ├── 2026-06-12--p3a-replay-data-pipeline-c12-06-a45-7-plan.md
│   │   │   ├── 2026-06-12-ablation-guardrails-plan.md
│   │   │   ├── 2026-06-13--audit-nongated-remainder-plan.md
│   │   │   └── 2026-06-19--active-runs-navigation-lifecycle-plan.md
│   │   └── reviews/
│   │       ├── 2026-06-01--g1c-project-healthcheck-final.md
│   │       ├── 2026-06-01--g1c-project-healthcheck.md
│   │       ├── 2026-06-01--project-wide-healthcheck-v2.md
│   │       ├── 2026-06-09-action-runtime-audit-charter.md
│   │       ├── 2026-06-09-action-runtime-audit-REPORT.md
│   │       ├── 2026-06-10-live-game-sameness-and-prompt-leak-investigation.md
│   │       ├── 2026-06-10-live-quality-diagnosis.md
│   │       ├── 2026-06-11-b1-context-repair-VERDICT.md
│   │       ├── 2026-06-11-b1-prompt-v2-metrics.json
│   │       ├── 2026-06-11-b4-prompt-v3-metrics.json
│   │       ├── 2026-06-11-b4-scaffold-VERDICT.md
│   │       ├── 2026-06-11-baseline-prompt-v1-metrics.json
│   │       ├── 2026-06-11-l4-baseline-backfill.json
│   │       ├── 2026-06-11-l4-guard-prompt-v3-metrics.json
│   │       ├── 2026-06-11-l4-guard-VERDICT.md
│   │       ├── 2026-06-12-l4-guard-witch-coord-prompt-v4-metrics.json
│   │       └── 2026-06-12-l4-guard-witch-coord-VERDICT.md
│   ├── health-check/
│   │   ├── _baseline/
│   │   │   ├── baseline.py
│   │   │   ├── bigfiles.txt
│   │   │   ├── coverage.txt
│   │   │   ├── doc-refs.txt
│   │   │   ├── entrypoint-wiring.txt
│   │   │   ├── import-refs.txt
│   │   │   ├── preflight-dirty.txt
│   │   │   └── vulture.txt
│   │   ├── 01-risks-bugs.md
│   │   ├── 02-slimming-candidates.md
│   │   ├── 03-architecture-optimization.md
│   │   ├── 2026-06-12-system-view-audit.md
│   │   └── UI代码审查报告.md
│   ├── prs/
│   │   ├── 2026-05-30--phase2-next-step-research.md
│   │   └── 2026-05-30--s5-semantic-label-research.md
│   ├── secrets/
│   │   └── README.md
│   ├── semantic-labeling/
│   │   ├── s5-label-contract.md
│   │   └── s5-label-prompts.md
│   ├── specs/
│   │   ├── agent-workflow.md
│   │   ├── board-rule-rulings.md
│   │   ├── review-guidelines.md
│   │   ├── review-packet-gate.md
│   │   └── text-injection-channels.md
│   ├── superpowers/
│   │   ├── plans/
│   │   │   ├── 2026-06-07-emergent-role-projection-snapshots.md
│   │   │   ├── 2026-06-07-p2-b-1-byo-key-credential-relay.md
│   │   │   ├── 2026-06-08-byo-key-provider-presets.md
│   │   │   ├── 2026-06-09-action-runtime-allowed-actions-swap.md
│   │   │   ├── 2026-06-09-action-runtime-hunter-v1.1.md
│   │   │   ├── 2026-06-09-action-runtime-resolver-deletion.md
│   │   │   ├── 2026-06-09-agent-action-runtime.md
│   │   │   ├── 2026-06-10-ablation-metrics-harness.md
│   │   │   ├── 2026-06-10-game-variety.md
│   │   │   ├── 2026-06-10-history-run-management.md
│   │   │   ├── 2026-06-10-p2a-invariant-safety-net.md
│   │   │   ├── 2026-06-10-prompt-versioning.md
│   │   │   ├── 2026-06-10-role-shuffle.md
│   │   │   ├── 2026-06-11-sys-b1-context-repair.md
│   │   │   ├── 2026-06-11-sys-b4-claim-ledger-vote-scaffold.md
│   │   │   ├── 2026-06-13-game-client-redesign-phase1.md
│   │   │   └── 2026-06-13-livecockpit-godseye-redesign-phase2.md
│   │   └── specs/
│   │       ├── 2026-06-04-g2d-2-qt-setup-ui-design.md
│   │       ├── 2026-06-04-g2d-prompt-configuration-design.md
│   │       ├── 2026-06-05-g3-1-live-deepseek-execution-design.md
│   │       ├── 2026-06-05-g3-2-qt-live-toggle-design.md
│   │       ├── 2026-06-05-p2-a-1-emergent-engine-design.md
│   │       ├── 2026-06-05-p2-a-2-live-deepseek-emergent-smoke-design.md
│   │       ├── 2026-06-06-p2-c-1-theater-view-design.md
│   │       ├── 2026-06-06-p2-d-settlement-screen-design.md
│   │       ├── 2026-06-06-p2-observer-emergent-engine-bridge.md
│   │       ├── 2026-06-07-emergent-role-projection-snapshots-design.md
│   │       ├── 2026-06-07-p2-b-1-byo-key-credential-relay-design.md
│   │       ├── 2026-06-08-byo-key-provider-presets-design.md
│   │       ├── 2026-06-09-agent-action-runtime-architecture-design.md
│   │       ├── 2026-06-09-p2a-invariant-safety-net-design.md
│   │       ├── 2026-06-10-game-variety-design.md
│   │       ├── 2026-06-10-history-run-management-and-report-entry-design.md
│   │       ├── 2026-06-10-prompt-versioning-design.md
│   │       ├── 2026-06-10-quality-ablation-harness-and-b1-context-design.md
│   │       ├── 2026-06-11-l4-guard-arm-design.md
│   │       ├── 2026-06-11-sys-b3-b5-closeout-design.md
│   │       ├── 2026-06-11-sys-b4-claim-ledger-vote-scaffold-design.md
│   │       ├── 2026-06-12-l4-guard-witch-coord-arm-design.md
│   │       ├── 2026-06-13-livecockpit-godseye-redesign-phase2-design.md
│   │       └── 2026-06-13-werewolf-game-client-redesign-design.md
│   ├── CHECKPOINT_TEMPLATE.md
│   ├── EVALUATION_RUBRIC.md
│   ├── GOLD_DEMO.md
│   ├── HEALTH_CHECK_2026-06-08.md
│   ├── PRODUCT_ONE_PAGER.md
│   ├── PROJECT_MAP.md
│   ├── RISK_ASSESSMENT_2026-06-06.md
│   ├── ROADMAP.md
│   ├── SPIKES.md
│   └── TASKS.md
├── scripts/
│   ├── context/
│   │   ├── build_plan_index.py
│   │   └── build_task_context.py
│   ├── dev/
│   │   ├── build_review_packet.py
│   │   ├── run_deepseek_live_smoke.py
│   │   └── validate_brief.py
│   └── research/
│       └── evaluate_semantic_labels.py
├── src/
│   └── werewolf_eval/
│       ├── ablation/
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── arms.py
│       │   ├── harness.py
│       │   └── metrics.py
│       ├── action_runtime/
│       │   ├── __init__.py
│       │   ├── abilities.py
│       │   ├── envelope.py
│       │   ├── registry.py
│       │   ├── ruleset.py
│       │   ├── settler.py
│       │   ├── state.py
│       │   ├── triggers.py
│       │   ├── turn.py
│       │   └── validator.py
│       ├── invariants/
│       │   ├── __init__.py
│       │   ├── artifacts.py
│       │   ├── checker.py
│       │   ├── fuzz.py
│       │   ├── guards.py
│       │   └── visibility_oracle.py
│       ├── observer/
│       │   ├── __init__.py
│       │   ├── credentials_api.py
│       │   ├── factory.py
│       │   ├── handler.py
│       │   ├── launch.py
│       │   ├── routes.py
│       │   ├── run_manager.py
│       │   ├── security.py
│       │   ├── sse.py
│       │   └── state.py
│       ├── __init__.py
│       ├── artifacts.py
│       ├── attribute_game.py
│       ├── attribution.py
│       ├── consensus_log.py
│       ├── credential_store.py
│       ├── decision_log.py
│       ├── deepseek_launcher.py
│       ├── deepseek_provider.py
│       ├── display_labels.py
│       ├── emergent_engine.py
│       ├── emergent_fake_script.py
│       ├── emergent_smoke_check.py
│       ├── evaluation_versions.py
│       ├── failure_audit.py
│       ├── fake_provider.py
│       ├── game_engine.py
│       ├── game_log.py
│       ├── gold_game_fixtures.py
│       ├── llm_providers.py
│       ├── log_bundle.py
│       ├── observer_enrichment.py
│       ├── observer_projection.py
│       ├── observer_protocol.py
│       ├── observer_server.py
│       ├── observer_trust_index.py
│       ├── observer_visibility.py
│       ├── profile_config.py
│       ├── prompt_goldens.py
│       ├── prompt_renderers.py
│       ├── prompt_v1.py
│       ├── prompt_v2.py
│       ├── prompt_v3.py
│       ├── prompt_v4.py
│       ├── prompt_version.py
│       ├── provider_agent.py
│       ├── provider_contract.py
│       ├── provider_registry.py
│       ├── render_demo.py
│       ├── render_provider_replay.py
│       ├── role_visibility.py
│       ├── run_deepseek_consensus_game.py
│       ├── run_deepseek_provider_game.py
│       ├── run_emergent_deepseek_game.py
│       ├── run_emergent_fake_runtime.py
│       ├── run_emergent_game.py
│       ├── run_fake_provider_game.py
│       ├── run_g1h_fake_runtime.py
│       ├── run_mock_game.py
│       ├── run_observer_server.py
│       ├── run_scripted_game.py
│       ├── runtime_events.py
│       ├── score_game.py
│       ├── scoring_metrics.py
│       ├── scoring_records.py
│       ├── scoring_types.py
│       ├── scoring.py
│       ├── scripted_game.py
│       ├── seat_agents.py
│       ├── semantic_labels.py
│       ├── settlement_bundle.py
│       ├── source_labels.py
│       ├── user_config_library.py
│       ├── validate_consensus_log.py
│       ├── validate_decision_log.py
│       ├── validate_failure_audit.py
│       ├── validate_game_log.py
│       ├── validate_log_bundle.py
│       └── validate_semantic_labels.py
├── tests/
│   ├── fixtures/
│   │   ├── ablation/
│   │   │   ├── diag_A_seer_p1_0/
│   │   │   │   ├── game-log.json
│   │   │   │   └── provider-turns.json
│   │   │   ├── diag_A_seer_p2_3/
│   │   │   │   ├── game-log.json
│   │   │   │   └── provider-turns.json
│   │   │   └── diag_A_seer_p3_1/
│   │   │       ├── game-log.json
│   │   │       └── provider-turns.json
│   │   └── emergent_ledger_golden.json
│   ├── golden_prompts/
│   │   ├── prompt_v1/
│   │   │   ├── action_hunter_day_vote.txt
│   │   │   ├── action_hunter_shot.txt
│   │   │   ├── action_seer_night.txt
│   │   │   ├── action_villager_day_vote.txt
│   │   │   ├── action_werewolf_night.txt
│   │   │   ├── action_witch_night.txt
│   │   │   ├── compose_persona_action.txt
│   │   │   ├── obs_hunter_shot.txt
│   │   │   ├── obs_villager_day.txt
│   │   │   ├── obs_werewolf_night.txt
│   │   │   ├── obs_witch_night_no_victim.txt
│   │   │   ├── obs_witch_night_victim.txt
│   │   │   ├── speech_villager_day1.txt
│   │   │   └── speech_werewolf_day1.txt
│   │   ├── prompt_v2/
│   │   │   ├── board_card_standard_6p.txt
│   │   │   ├── compose_full_v2_speech.txt
│   │   │   ├── obs_v2_hunter_shot.txt
│   │   │   ├── obs_v2_seer_day.txt
│   │   │   ├── obs_v2_villager_day.txt
│   │   │   ├── obs_v2_werewolf_night.txt
│   │   │   ├── obs_v2_witch_no_victim.txt
│   │   │   ├── obs_v2_witch_victim.txt
│   │   │   ├── speech_villager_v2.txt
│   │   │   └── speech_werewolf_v2.txt
│   │   ├── prompt_v3/
│   │   │   ├── action_guard_night.txt
│   │   │   ├── board_card_guard_6p.txt
│   │   │   ├── claim_digest_two_claims.txt
│   │   │   ├── obs_v2_guard_night.txt
│   │   │   ├── scribe_input_round1.txt
│   │   │   ├── scribe_system_prompt.txt
│   │   │   ├── speech_villager_v3_guard_board.txt
│   │   │   ├── speech_villager_v3.txt
│   │   │   ├── vote_scaffold_empty_ledger.txt
│   │   │   └── vote_scaffold_with_claims.txt
│   │   └── prompt_v4/
│   │       ├── obs_witch_guard_board_no_victim_identity.txt
│   │       ├── obs_witch_guard_board_victim_coord.txt
│   │       └── witch_coord_suffix_injected.txt
│   ├── fake_scribe.py
│   ├── parity_scripts.py
│   ├── test_ablation_arms.py
│   ├── test_ablation_guardrails.py
│   ├── test_ablation_harness_fake.py
│   ├── test_ablation_metrics.py
│   ├── test_action_runtime_hunter.py
│   ├── test_action_runtime_parity.py
│   ├── test_action_runtime_registry.py
│   ├── test_action_runtime_settler.py
│   ├── test_action_runtime_triggers.py
│   ├── test_action_runtime_turn.py
│   ├── test_action_runtime_validator.py
│   ├── test_anthropic_provider.py
│   ├── test_artifacts.py
│   ├── test_attribution.py
│   ├── test_b1204_guard_prompt_floor.py
│   ├── test_b5_closeout.py
│   ├── test_build_review_packet.py
│   ├── test_c3_negative_scan.py
│   ├── test_consensus_log.py
│   ├── test_context_budget.py
│   ├── test_credential_store.py
│   ├── test_decision_log.py
│   ├── test_deepseek_consensus_game.py
│   ├── test_deepseek_launcher.py
│   ├── test_deepseek_live_smoke.py
│   ├── test_deepseek_provider_game.py
│   ├── test_deepseek_provider.py
│   ├── test_emergent_engine.py
│   ├── test_emergent_ledger_golden.py
│   ├── test_emergent_role_projection.py
│   ├── test_emergent_smoke_check.py
│   ├── test_engine_to_scoring_e2e.py
│   ├── test_evaluation_versions.py
│   ├── test_event_visibility_invariant.py
│   ├── test_failure_audit.py
│   ├── test_fake_provider_game.py
│   ├── test_fake_provider.py
│   ├── test_g1h_runtime_spine.py
│   ├── test_game_engine.py
│   ├── test_game_log.py
│   ├── test_guard_resolver.py
│   ├── test_guard_sentinels.py
│   ├── test_guard_visibility.py
│   ├── test_injection_registry_sentinel.py
│   ├── test_inline_witch_hunter_failure.py
│   ├── test_invariants_artifacts.py
│   ├── test_invariants_bad_examples.py
│   ├── test_invariants_checker.py
│   ├── test_invariants_dangling.py
│   ├── test_invariants_e2e.py
│   ├── test_invariants_engine_wiring.py
│   ├── test_invariants_fuzz_engine.py
│   ├── test_invariants_fuzz.py
│   ├── test_invariants_guards.py
│   ├── test_invariants_i8.py
│   ├── test_l4_arm_layout.py
│   ├── test_l4_metrics.py
│   ├── test_log_bundle.py
│   ├── test_multi_provider_launcher.py
│   ├── test_observer_byo_key_launch.py
│   ├── test_observer_credentials_endpoint.py
│   ├── test_observer_emergent_bridge.py
│   ├── test_observer_enrichment.py
│   ├── test_observer_models_endpoint.py
│   ├── test_observer_protocol.py
│   ├── test_observer_routes.py
│   ├── test_observer_run_delete.py
│   ├── test_observer_run_manager.py
│   ├── test_observer_security.py
│   ├── test_observer_server.py
│   ├── test_observer_sse.py
│   ├── test_observer_visibility.py
│   ├── test_openai_provider.py
│   ├── test_p2a2_live_path.py
│   ├── test_profile_config.py
│   ├── test_prompt_renderers.py
│   ├── test_prompt_v2_invariants.py
│   ├── test_prompt_v2.py
│   ├── test_prompt_v3_invariants.py
│   ├── test_prompt_v3_speech_guard.py
│   ├── test_prompt_v3.py
│   ├── test_prompt_v4_engine.py
│   ├── test_prompt_v4.py
│   ├── test_prompt_versioning.py
│   ├── test_provider_agent_failure_classification.py
│   ├── test_provider_contract.py
│   ├── test_provider_registry.py
│   ├── test_qt_observer_static_contract.py
│   ├── test_render_demo.py
│   ├── test_render_provider_replay.py
│   ├── test_rng_draw_order.py
│   ├── test_role_shuffle.py
│   ├── test_role_single_source.py
│   ├── test_role_visibility.py
│   ├── test_rule_rulings.py
│   ├── test_rules_v1_2.py
│   ├── test_run_emergent_deepseek_game.py
│   ├── test_run_emergent_fake_runtime.py
│   ├── test_run_emergent_game.py
│   ├── test_runtime_events.py
│   ├── test_scoring.py
│   ├── test_scripted_game_runner.py
│   ├── test_seat_agents.py
│   ├── test_semantic_label_research.py
│   ├── test_semantic_labels.py
│   ├── test_settlement_bundle.py
│   ├── test_settlement_response.py
│   ├── test_settler_guard_branches.py
│   ├── test_settler_guard_oracle.py
│   ├── test_source_labels.py
│   ├── test_validate_clis.py
│   ├── test_visibility_parity.py
│   ├── test_visibility_two_side_sentinel.py
│   ├── test_witch_potion_one_shot_sentinel.py
│   └── windows_gate.py
├── tools/
│   ├── backfill_seer_claim_metrics.py
│   ├── generate_golden_prompts.py
│   └── live_check_deepseek.py
├── .gitattributes
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── DESIGN.md
├── launch-theater.bat
├── launch-theater.py
├── live-check.bat
├── pyproject.toml
├── README.md
├── README.zh-CN.md
└── requirements-dev.txt
```
