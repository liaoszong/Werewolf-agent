# ROADMAP — Werewolf-agent

## Purpose

`ROADMAP.md` is the canonical route alignment document for Phase 2 / Phase 3+ planning. It explains what the project is ultimately trying to become, where the current main branch stands, and how the route proceeds from offline replay foundation toward a client-agnostic live AI Werewolf experiment platform.

This document does not replace `docs/TASKS.md`. `TASKS.md` tracks task status and implementation candidates. Implementation details still live in bound plans under `docs/harness/plans/`.

## Final Product Vision

Werewolf-agent aims to become a client-agnostic live AI Werewolf experiment platform.

The final product route is:

```text
configurable AI Werewolf run profile
-> Python runtime game engine + agent/provider loop
-> live runtime event spine + snapshots + prompt manifest
-> client-agnostic observer protocol
-> Qt/QML or Web observer clients
-> replay/audit/export + evaluation and leaderboard layers
```

The project is not trying to become only a static HTML demo or offline replay generator. Static HTML replay/report output remains valuable as an offline audit artifact, but it is not the primary user experience. The primary product direction is a live, configurable, observable experiment platform whose logs can still feed replay, audit, export, scoring, and later leaderboard workflows.

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
- G1b deterministic game engine + mock agent contract.
- G1c wolf consensus + failure recovery.
- G1d provider adapter research / fake-provider contract.
- G1e provider-backed single-game smoke.
- G1f DeepSeek consensus smoke.
- G1g provider replay HTML report.
- G1h Live Runtime Event Spine.

The current main branch has not completed:

- Qt/QML observer client.
- Web observer client.
- Prompt editor UI.
- Multi-provider arena.
- human-vs-AI UI.
- G4 evaluation platform / real multi-game Leaderboard.

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

- Status: `completed`.
- Role: establish the minimal 6-player Werewolf state machine, private observation model, structured `AgentAction`, and mock agents.
- Boundary: no provider integration, no live AI, no Web live observer.

#### G1c: wolf consensus + failure recovery

- Status: `completed`.
- Role: handle werewolf night consensus protocol, invalid action, timeout, parse failure, and audit trail.
- Boundary: no real provider integration and no repair path that forges valid logs from invalid behavior.

#### G1d: provider adapter research / fake-provider contract

- Status: `completed`.
- Role: research provider boundary, secrets, cost, timeout behavior, and fake-provider contract.
- Boundary: Research PR first; do not connect live APIs directly from this route note.

#### G1e: provider-backed single-game smoke

- Status: `completed`.
- Role: run one local, budget-controlled provider-backed game after G1d establishes the boundary.
- Boundary: no CI live calls, no multi-game Leaderboard, no human-vs-AI UI.

#### G1f: DeepSeek consensus smoke

- Status: `completed`.
- Role: run a local, opt-in DeepSeek consensus smoke where separate werewolf roles call provider-backed agents and emit Game Log / Decision Log / Consensus Log / Provider Trace / Failure Audit.
- Boundary: no CI live calls, no multi-game Leaderboard, no observer UI.

#### G1g: provider replay HTML

- Status: `completed`.
- Role: render provider-backed game bundles into a standalone static HTML replay/report for audit and review.
- Boundary: offline audit artifact only. It reads existing logs and does not call providers, mutate game state, change scoring, or act as live observer UI.

#### G1h: Live Runtime Event Spine

- Status: `completed`.
- Role: turn real/fake provider single-game runtime into a client-agnostic event spine by emitting `events.jsonl`, runtime snapshots, prompt manifest, provider lifecycle events, and final standard log bundle compatibility.
- Boundary: no Qt/QML client, no Web observer/server, no prompt editor UI, no multi-provider arena, no leaderboard, no scoring formula changes, no provider adapter behavior changes beyond event emission needed by the bound plan.

G1a-G1h are retained as audit foundation, replay foundation, runtime event spine foundation, and log bundle / provider trace / failure audit foundation. Full observer platform work proceeds through G2a because clients must consume a stable event stream through a protocol boundary.

### Phase 3+ / G2: observer route

Goal: expose the G1h runtime event spine through local observer surfaces without binding clients to Python internals.

#### G2a: Local Observer Server

- Status: `completed`.
- Role: provide local REST access to run control, live events, snapshots, and historical run artifacts through a stdlib HTTP server with SSE live tailing.
- Boundary: server protocol only; no rich client implementation.

#### G2b: Qt Observer MVP

- Role: first rich client direction. Qt/QML consumes the client-agnostic REST/WebSocket/event protocol and shows run status, player panels, event stream, provider trace summary, and audit links.
- Scaffold: `clients/qt_observer` exists as a Qt6 Quick auto-generated starter project only. It is the intended G2b client workspace, not a completed observer client.
- Boundary: Qt must not bind directly to Python runtime objects or private Python APIs.

#### G2c: God View / Role View

- Role: separate god-view state from role-view projections so hidden information remains auditable.
- Boundary: no prompt editor or multi-run experiment system.

#### G2d: Prompt Configuration MVP

- Role: configure local prompt/profile/model/temperature/strategy parameters through a controlled profile surface.
- Boundary: no hosted account system, no multi-provider arena, no leaderboard.

### Phase 3+ / G3: experiment route

Goal: support repeatable experiment profiles and unify replay/live operation.

G3 candidates:

- Experiment profiles.
- Replay + live dual mode over the same observer protocol.
- Multi-provider arena.
- Batch run metadata and comparison-ready exports.

Boundary: G3 depends on G1h event spine and G2 observer contracts.

### Phase 4 / G4: evaluation platform

Goal: convert live/replay experiment output into robust evaluation products.

G4 candidates:

- real multi-game Leaderboard
- role-separated scorecards
- sample-size warnings
- provider/model/version comparison
- exportable evaluation reports

Boundary: real Leaderboard is a later evaluation-platform capability. It is not the next candidate immediately after G1g because it depends on stable live run capture and enough multi-game data.

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
  -> G1f DeepSeek consensus smoke
  -> G1g provider replay HTML audit artifact
  -> G1h Live Runtime Event Spine

G1h event spine
  -> G2a Local Observer Server
  -> G2b Qt Observer MVP
  -> G2c God View / Role View
  -> G2d Prompt Configuration MVP
  -> G3 Experiment Profiles / Replay + Live Dual Mode / Multi-provider Arena
  -> G4 Evaluation Platform / real multi-game Leaderboard
```

## Current Priority

G1h Live Runtime Event Spine and G2a Local Observer Server / Protocol Control Plane are now `completed`. The next implementation candidate is G2b Qt Observer MVP.

G1 series retrospective:
- G1a proved fresh generated logs can feed validators, scoring, metrics, and replay demo.
- G1b supplied the deterministic state machine, private observations, and structured `AgentAction` contract.
- G1c added failure recovery, wolf consensus, and audit trail.
- G1d researched provider boundary and established the fake-provider contract.
- G1e delivered a budget-controlled, provider-backed single-game smoke CLI with a DeepSeek adapter and offline guard.
- G1f proved provider-backed wolf consensus smoke can emit standard logs, provider trace, and failure audit.
- G1g made provider-backed game bundles inspectable as offline HTML replay/report artifacts.

Immediate pivot:

- Keep G1a-G1h as audit/replay/log-bundle/event-spine foundation.
- Do not extend the project by generating more HTML reports as the main user experience.
- Build on the completed G1h event spine through G2a Local Observer Server / Protocol Control Plane before rich Qt/Web clients.

## Explicit Non-goals

Current Phase 2A does not do:

- real AI Agent autonomous gameplay
- game engine implementation
- provider adapter implementation
- real multi-model Leaderboard
- S5 AI semantic scoring integration
- full natural-language review reports
- human-vs-AI UI

G1h specifically does not do:

- Qt/QML client
- Web observer/server
- prompt editor UI
- multi-provider arena
- leaderboard
- scoring formula changes
- provider adapter behavior changes outside event-spine instrumentation

`decision_quality_score` quality beyond deterministic visibility checks comes only from saved S5 semantic-label JSON. Live AI semantic labeling remains outside the completed runtime.

G1a specifically must not be described as live AI Agent gameplay, provider-backed gameplay, Web live observer, human-vs-AI UI, or real multi-game Leaderboard. It is scripted deterministic fresh-log generation plus evaluator/replay compatibility only.

G1g specifically must not be described as primary UX, live observer, Qt/Web client, live API behavior, or leaderboard. It is an offline audit artifact that reads existing log bundles.

Qt/QML is the recommended first rich client direction for G2b, but the protocol must remain client-agnostic. Python owns game engine, agent runtime, provider adapter, prompt registry, event bus, and log writer. Qt/QML consumes REST/WebSocket/event protocol and must not bind to Python runtime internals.

## Document Responsibility Map

- `README.md`: short project entry, current status, and links.
- `docs/PRODUCT_ONE_PAGER.md`: product users, value, and high-level product constraints.
- `docs/ROADMAP.md`: phase route, dependency graph, and route conflict resolution.
- `docs/TASKS.md`: task status, candidate tasks, and UX/demo acceptance.
- `docs/EVALUATION_RUBRIC.md`: scoring dimensions, formulas, log schemas, and AI judge boundary.
- `docs/adr/`: stable architecture decisions such as client-agnostic observer protocol.
- `docs/prs/`: research records and route decisions that may later be promoted into stable docs.
- `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md`: Phase A product-route and system-architecture charter for game-like experience architecture, minimum match/profile contract seed, visibility trust gates, exit demos, and anti-shrinkage gates.
- `docs/harness/plans/`: executable implementation protocols.
