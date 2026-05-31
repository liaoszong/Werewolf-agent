# ROADMAP — Werewolf-agent

## Purpose

`ROADMAP.md` is the canonical route alignment document for Phase 2 / Phase 3 planning. It explains what the project is ultimately trying to become, where the current main branch stands, and how the G-track proceeds after G1a.

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
- D2 Decision Log scoring integration.
- S4 Consensus Log runtime/input.
- S5 saved semantic-label research and scoring integration.
- G1a scripted deterministic fresh-log runner.

The current main branch has not completed:

- G1 real AI Agent gameplay engine.
- live provider integration.
- human-vs-AI UI.
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

Status: completed.

D2 connected D1 Decision Log input to scoring through deterministic visibility checks and decision-to-event traceability. Positive semantic decision-quality scoring is handled only by saved S5 semantic labels; Phase 2A does not call live AI.

### Phase 2B: collaboration and semantic inputs

Goal: add collaboration and semantic inputs needed for stronger evaluation.

Completed entries:

- S4 Consensus Log runtime/input: validate wolf-team coordination logs.
- S5 saved semantic-label research and scoring integration: consume saved semantic-label JSON and map it into deterministic `decision_quality_score`.

Status: completed for S4 runtime/input and S5 saved-label scoring integration.

Boundary: S5 consumes saved semantic-label JSON. It does not perform live AI labeling, provider integration, gameplay, or multi-game Leaderboard aggregation.

### Phase 3 / G-track: gameplay route

Goal: move from scripted fresh-log generation toward real AI Agent gameplay without skipping deterministic engine, action-contract, failure-recovery, and provider-boundary gates.

G-track route:

#### G1a: scripted deterministic fresh-log runner

- Status: `completed`.
- Role: reads scripted scenario JSON and deterministically generates fresh Game Log / Decision Log / Consensus Log, then connects those logs to the evaluator and replay demo.
- Boundary: not Agent runtime, not provider integration, not live AI gameplay.

#### G1b: deterministic game engine + mock agent contract

- Status: `next_candidate`.
- Role: establish the minimal 6-player Werewolf state machine, private observation model, structured `AgentAction`, and mock agents.
- Boundary: no provider integration, no live AI, no Web live observer.

#### G1c: wolf consensus + failure recovery

- Status: `future_candidate`.
- Role: handle werewolf night consensus protocol, invalid action, timeout, parse failure, and audit trail.
- Boundary: no real provider integration and no repair path that forges valid logs from invalid behavior.

#### G1d: provider adapter research / fake-provider contract

- Status: `future_research_candidate`.
- Role: research provider boundary, secrets, cost, timeout behavior, and fake-provider contract.
- Boundary: Research PR first; do not connect live APIs directly from this route note.

#### G1e: provider-backed single-game smoke

- Status: `future_candidate_after_G1d`.
- Role: run one local, budget-controlled provider-backed game after G1d establishes the boundary.
- Boundary: no CI live calls, no multi-game Leaderboard, no human-vs-AI UI.

Full G1 real AI Agent gameplay is not complete until the G1b-G1e gates establish a real engine, real action loop, provider boundary, failure recovery, and a provider-backed single-game smoke. G1a alone proves fresh-log generation and evaluator compatibility, not live Agent gameplay.

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
  -> S5 saved semantic-label research / spike

D1 Decision Log input
  + D2 Decision Log scoring integration
  -> S5 saved semantic-label scoring integration

E1 + D1 + D2 + S4 contracts
  -> G1a scripted deterministic fresh-log runner
  -> G1b deterministic game engine + mock agent contract
  -> G1c wolf consensus + failure recovery
  -> G1d provider adapter research / fake-provider contract
  -> G1e provider-backed single-game smoke

G1 multi-game outputs
  -> L1 real multi-game Leaderboard
```

## Current Priority

The next G-track implementation candidate is G1b deterministic game engine + mock agent contract.

Why G1b before G1c/G1d/G1e:

- G1a already proves fresh generated logs can feed validators, scoring, metrics, and replay demo.
- G1b supplies the deterministic state machine, private observations, and structured `AgentAction` contract needed before consensus or provider work.
- G1c failure recovery needs a real engine/action contract to reject invalid behavior without forging valid logs.
- G1d provider research needs a fake-provider contract so cost, timeout, secrets, and adapter behavior can be studied before live API calls.
- G1e must wait for G1d and remains a single-game smoke, not a CI job, multi-game Leaderboard, or human-vs-AI product.

## Explicit Non-goals

Current Phase 2A does not do:

- real AI Agent autonomous gameplay
- game engine implementation
- provider adapter implementation
- real multi-model Leaderboard
- S5 AI semantic scoring integration
- full natural-language review reports
- human-vs-AI UI

`decision_quality_score` quality beyond deterministic visibility checks comes only from saved S5 semantic-label JSON. Live AI semantic labeling remains outside the completed runtime.

G1a specifically must not be described as live AI Agent gameplay, provider-backed gameplay, Web live observer, human-vs-AI UI, or real multi-game Leaderboard. It is scripted deterministic fresh-log generation plus evaluator/replay compatibility only.

## Document Responsibility Map

- `README.md`: short project entry, current status, and links.
- `docs/PRODUCT_ONE_PAGER.md`: product users, value, and high-level product constraints.
- `docs/ROADMAP.md`: phase route, dependency graph, and route conflict resolution.
- `docs/TASKS.md`: task status, candidate tasks, and UX/demo acceptance.
- `docs/EVALUATION_RUBRIC.md`: scoring dimensions, formulas, log schemas, and AI judge boundary.
- `docs/prs/`: research records and route decisions that may later be promoted into stable docs.
- `docs/harness/plans/`: executable implementation protocols.
