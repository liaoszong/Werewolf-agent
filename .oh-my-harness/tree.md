# Tree

Use this file for navigation only. Verify implementation details by reading source files directly.

- Source: `git ls-files --cached --others --exclude-standard`
- Entries: 90

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
├── docs/
│   ├── demo/
│   │   ├── phase1-gold-demo.html
│   │   └── phase2-runtime-demo.html
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
│   │   └── s3-rule-attribution.json
│   ├── harness/
│   │   └── plans/
│   │       ├── 2026-05-29--e1-game-log-parser-validation-plan.md
│   │       ├── 2026-05-29--phase1-closure-phase2-boundary-alignment-plan.md
│   │       ├── 2026-05-29--s0-gold-game-seed-plan.md
│   │       ├── 2026-05-29--s1-game-log-schema-validation-plan.md
│   │       ├── 2026-05-29--s2-deterministic-scorer-validation-plan.md
│   │       ├── 2026-05-29--s3-rule-attribution-validation-plan.md
│   │       ├── 2026-05-29--s6-leaderboard-ui-demo-validation-plan.md
│   │       ├── 2026-05-30--d1-decision-log-runtime-skeleton-plan.md
│   │       ├── 2026-05-30--d2-decision-log-scoring-integration-plan.md
│   │       ├── 2026-05-30--e2-deterministic-scorer-plan.md
│   │       ├── 2026-05-30--e3-rule-attribution-engine-plan.md
│   │       ├── 2026-05-30--e4-runtime-demo-html-plan.md
│   │       ├── 2026-05-30--roadmap-alignment-plan.md
│   │       ├── 2026-05-30--s4-consensus-log-runtime-input-plan.md
│   │       └── 2026-05-30--s4x-context-budget-hardening-plan.md
│   ├── prs/
│   │   └── 2026-05-30--phase2-next-step-research.md
│   ├── specs/
│   │   ├── agent-workflow.md
│   │   └── review-guidelines.md
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
│   └── dev/
│       └── validate_brief.py
├── src/
│   └── werewolf_eval/
│       ├── __init__.py
│       ├── attribute_game.py
│       ├── attribution.py
│       ├── consensus_log.py
│       ├── decision_log.py
│       ├── game_log.py
│       ├── render_demo.py
│       ├── score_game.py
│       ├── scoring.py
│       ├── validate_consensus_log.py
│       ├── validate_decision_log.py
│       └── validate_game_log.py
├── tests/
│   ├── test_attribution.py
│   ├── test_consensus_log.py
│   ├── test_context_budget.py
│   ├── test_decision_log.py
│   ├── test_game_log.py
│   ├── test_render_demo.py
│   └── test_scoring.py
├── .gitignore
├── AGENTS.md
└── README.md
```
