# ROADMAP — Werewolf-agent

## Purpose

`ROADMAP.md` is the canonical route alignment document for Phase 2 / Phase 3 planning. It explains what the project is ultimately trying to become, where the current main branch stands, and why the next task order is D2 before S4/S5/G1.

This document does not replace `docs/TASKS.md`. `TASKS.md` tracks task status and implementation candidates. Implementation details still live in bound plans under `docs/harness/plans/`.

## Final Product Vision

Werewolf-agent aims to become an AI Werewolf Agent evaluation, review, and leaderboard system.

The final product route is:

```text
real or replayed Werewolf games
-> structured Game Log / Decision Log / Consensus Log
-> reproducible Score Log / Metrics Summary
-> deterministic attribution + AI-assisted semantic labels
-> role-separated scorecards and real multi-game Leaderboard
```

The project is not trying to become only a static HTML demo. The static demos exist to prove that the evaluation loop is visible and understandable before real Agent gameplay is introduced.

## Current Main Facts

The current main branch has completed:

- Phase 1 deterministic MVP.
- E1 Game Log parser / validator.
- E2 deterministic scorer.
- E3 rule attribution engine.
- E4 runtime demo HTML exporter.
- D1 Decision Log runtime input skeleton.
- R1 Phase 2 next-step research.

The current main branch has not completed:

- D2 Decision Log scoring integration.
- S4 Consensus Log runtime/input.
- S5 AI semantic labeling research or integration.
- G1 real AI Agent gameplay engine.
- L1 real multi-game Leaderboard.

## Phase Boundaries

### Phase 1: deterministic MVP closure

Goal: prove that a structured Game Log can produce reproducible deterministic scoring, attribution, and a visible demo.

Status: completed.

Completed route:

```text
Game Log -> deterministic Score Log / Metrics Summary -> Rule Attribution -> static and runtime HTML demo
```

Boundary: Phase 1 does not claim real AI Agent gameplay, real Decision Log / Consensus Log collection, real multi-model Leaderboard, or real `decision_quality_score` availability.

### Phase 2A: evaluator runtime closure

Goal: close the evaluation runtime loop before adding real gameplay.

Minimum closure route:

```text
Game Log + Decision Log -> Score Log / Metrics Summary -> Rule Attribution -> Runtime HTML Demo
```

Current priority: D2 Decision Log scoring integration.

D2 must connect D1 Decision Log input to scoring so `decision_quality_score` is no longer globally fixed at 0. D2 is deterministic and does not call AI.

### Phase 2B: collaboration and semantic inputs

Goal: add the next runtime inputs needed for stronger evaluation.

Candidate tasks:

- S4 Consensus Log runtime/input: validate wolf-team coordination logs.
- S5 AI semantic labeling research: evaluate provider, prompt, accuracy, consistency, token cost, and fallback behavior.

Boundary: S5 integration should not happen before D2 because AI labels need a scoring consumer.

### Phase 3 / G-track: real AI Agent gameplay

Goal: introduce real AI Agent automatic gameplay after evaluator and log contracts are stable.

G1 requires:

- game engine or round driver
- Agent runtime
- provider adapter boundary
- structured Game Log generation
- structured Decision Log generation
- Consensus Log generation for wolf-team nights
- failure recovery and invalid-output handling

Boundary: G1 is not Phase 2A. It is a later gameplay track.

### Phase 3+ / L-track: real multi-game Leaderboard

Goal: aggregate many real games across models, versions, and roles.

L1 requires:

- enough games to make role-separated ranking meaningful
- `games_played` and `role_distribution`
- sample-size warnings
- role tabs
- stable aggregation for `avg_outcome_score`, `avg_decision_quality_score`, and `avg_rule_integrity_score`

Boundary: L1 depends on G1 producing enough multi-game data.

## Dependency Graph

```text
E1 Game Log parser
  -> E2 deterministic scorer
  -> E3 rule attribution
  -> E4 runtime demo

D1 Decision Log input
  + E2 deterministic scorer
  -> D2 Decision Log scoring integration

E1 Game Log parser
  -> S4 Consensus Log runtime/input

D1 Decision Log input
  -> S5 AI semantic labeling research / spike

D1 Decision Log input
  + D2 Decision Log scoring integration
  -> S5 AI semantic labeling scoring integration

E1 + D1 + D2 + S4 contracts
  -> G1 real AI Agent gameplay

G1 multi-game outputs
  -> L1 real multi-game Leaderboard
```

## Current Priority

The next implementation priority is D2 Decision Log scoring integration.

Why D2 before S4/S5/G1:

- D2 closes the most important current scoring gap: `decision_quality_score` is still not connected to scoring.
- S4 is valuable but only covers wolf-team coordination.
- S5 needs D2 because semantic labels need a scoring consumer.
- G1 real gameplay should wait until evaluator and log contracts are stable enough to score generated games.

## Explicit Non-goals

Current Phase 2A does not do:

- real AI Agent autonomous gameplay
- game engine implementation
- provider adapter implementation
- real multi-model Leaderboard
- S5 AI semantic scoring integration
- full natural-language review reports
- human-vs-AI UI

D2 specifically must not claim full `decision_quality_score` quality. It only starts the deterministic scoring path. AI-assisted semantic checks remain S5.

## Document Responsibility Map

- `README.md`: short project entry, current status, and links.
- `docs/PRODUCT_ONE_PAGER.md`: product users, value, and high-level product constraints.
- `docs/ROADMAP.md`: phase route, dependency graph, and route conflict resolution.
- `docs/TASKS.md`: task status, candidate tasks, and UX/demo acceptance.
- `docs/EVALUATION_RUBRIC.md`: scoring dimensions, formulas, log schemas, and AI judge boundary.
- `docs/prs/`: research records and route decisions that may later be promoted into stable docs.
- `docs/harness/plans/`: executable implementation protocols.
