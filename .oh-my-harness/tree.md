# Tree

Use this file for navigation only. Verify implementation details by reading source files directly.

- Source: `git ls-files --cached --others --exclude-standard`
- Entries: 172

```text
./
├── .agents/
│   └── skills/
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
│       └── tdd/
│           ├── LICENSE.upstream
│           ├── mocking.md
│           ├── SKILL.md
│           └── tests.md
├── .codex/
│   ├── hooks/
│   │   └── tree.mjs
│   └── hooks.json
├── .github/
│   ├── PULL_REQUEST_TEMPLATE/
│   │   ├── implementation.md
│   │   └── research.md
│   ├── codex-review-comment.md
│   └── writing-plan.md
├── .logs/
│   └── review/
│       └── latest/
│           └── review-packet.md
├── .tmp/
│   ├── g1d-failure-audit.json
│   └── g1d-failure-provider-trace.json
├── docs/
│   ├── demo/
│   │   ├── phase1-gold-demo.html
│   │   ├── phase2-runtime-demo.html
│   │   ├── phase2-s5-runtime-demo.html
│   │   ├── phase3-g1-scripted-runtime-demo.html
│   │   ├── phase3-g1b-mock-agent-runtime-demo.html
│   │   ├── phase3-g1c-wolf-consensus-runtime-demo.html
│   │   └── phase3-g1d-fake-provider-runtime-demo.html
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
│   │   ├── g1d-fake-provider-failure-audit.example.json
│   │   ├── g1d-fake-provider-game-log.json
│   │   ├── g1d-fake-provider-metrics-summary.json
│   │   ├── g1d-fake-provider-provider-trace.json
│   │   └── g1d-fake-provider-score-log.json
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
│   │   │   └── 2026-06-02--g1e-deepseek-provider-smoke-plan.md
│   │   └── reviews/
│   │       ├── 2026-06-01--g1c-project-healthcheck-final.md
│   │       ├── 2026-06-01--g1c-project-healthcheck.md
│   │       └── 2026-06-01--project-wide-healthcheck-v2.md
│   ├── prs/
│   │   ├── 2026-05-30--phase2-next-step-research.md
│   │   └── 2026-05-30--s5-semantic-label-research.md
│   ├── semantic-labeling/
│   │   ├── s5-label-contract.md
│   │   └── s5-label-prompts.md
│   ├── specs/
│   │   ├── agent-workflow.md
│   │   ├── review-guidelines.md
│   │   └── review-packet-gate.md
│   ├── CHECKPOINT_TEMPLATE.md
│   ├── EVALUATION_RUBRIC.md
│   ├── GOLD_DEMO.md
│   ├── PRODUCT_ONE_PAGER.md
│   ├── ROADMAP.md
│   ├── SPIKES.md
│   └── TASKS.md
├── scripts/
│   ├── context/
│   │   ├── build_plan_index.py
│   │   └── build_task_context.py
│   ├── dev/
│   │   ├── build_review_packet.py
│   │   └── validate_brief.py
│   └── research/
│       └── evaluate_semantic_labels.py
├── src/
│   └── werewolf_eval/
│       ├── __init__.py
│       ├── attribute_game.py
│       ├── attribution.py
│       ├── consensus_log.py
│       ├── decision_log.py
│       ├── deepseek_provider.py
│       ├── failure_audit.py
│       ├── fake_provider.py
│       ├── game_engine.py
│       ├── game_log.py
│       ├── log_bundle.py
│       ├── provider_agent.py
│       ├── provider_contract.py
│       ├── render_demo.py
│       ├── run_deepseek_provider_game.py
│       ├── run_fake_provider_game.py
│       ├── run_mock_game.py
│       ├── run_scripted_game.py
│       ├── score_game.py
│       ├── scoring.py
│       ├── scripted_game.py
│       ├── semantic_labels.py
│       ├── source_labels.py
│       ├── validate_consensus_log.py
│       ├── validate_decision_log.py
│       ├── validate_failure_audit.py
│       ├── validate_game_log.py
│       ├── validate_log_bundle.py
│       └── validate_semantic_labels.py
├── tests/
│   ├── test_attribution.py
│   ├── test_build_review_packet.py
│   ├── test_consensus_log.py
│   ├── test_context_budget.py
│   ├── test_decision_log.py
│   ├── test_deepseek_provider_game.py
│   ├── test_deepseek_provider.py
│   ├── test_failure_audit.py
│   ├── test_fake_provider_game.py
│   ├── test_fake_provider.py
│   ├── test_game_engine.py
│   ├── test_game_log.py
│   ├── test_log_bundle.py
│   ├── test_provider_contract.py
│   ├── test_render_demo.py
│   ├── test_scoring.py
│   ├── test_scripted_game_runner.py
│   ├── test_semantic_label_research.py
│   ├── test_semantic_labels.py
│   └── test_source_labels.py
├── .gitignore
├── AGENTS.md
└── README.md
```
