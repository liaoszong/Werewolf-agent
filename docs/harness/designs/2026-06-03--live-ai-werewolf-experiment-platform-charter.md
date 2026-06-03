# Live AI Werewolf Experiment Platform Charter

Date: 2026-06-03
Status: draft

This document is not an implementation plan for one PR. It is the product-route and system-architecture charter for turning Werewolf-agent from a provider-backed runtime foundation into a client-agnostic live AI Werewolf experiment platform.

## 1. Product North Star

Werewolf-agent should become a configurable, observable, live AI Werewolf match platform.

The platform is not only "able to run one game." A complete product experience should let a user:

1. start a new AI-vs-AI Werewolf match,
2. configure roles, seats, providers, models, prompts, and strategies,
3. run the match live,
4. observe the match through trustworthy perspectives,
5. inspect the event, snapshot, manifest, provider, and failure-audit evidence behind each action,
6. save and replay completed matches,
7. compare multiple runs and later evaluate model / prompt / role performance.

The surface should feel closer to a game lobby and match cockpit. The system underneath remains an experiment platform with structured profiles, manifests, event streams, snapshots, audit artifacts, and reproducible run bundles.

## 2. Current Foundation

G1a-G1h establish the live-runtime foundation:

- deterministic and provider-backed game paths,
- minimal Werewolf game engine,
- mock agent contract,
- wolf consensus and failure recovery,
- fake-provider and DeepSeek provider smoke paths,
- provider trace and failure audit surfaces,
- offline provider replay HTML artifact,
- live runtime event spine with `events.jsonl`, runtime snapshots, prompt manifest, provider lifecycle events, and standard log-bundle compatibility.

Current route-alignment risk:

- Recent GitHub history shows G1h implementation has merged.
- Some route/status docs may still describe G1h as `next_candidate`.
- This stale-status cleanup is a route closeout task, not new product functionality.

## 3. Experience Architecture

The primary user experience should be organized around matches, not raw files or JSON.

### 3.1 Home / Lobby

The first screen should offer:

- Start New Match,
- Match History,
- recent or running match status,
- secondary entry points for profiles, providers, and artifacts.

The first product action is game-like: start a new AI-vs-AI Werewolf match or open a historical match.

### 3.2 Start New Match

Starting a new match opens a game-like role configuration screen, not a plain settings form.

Recommended interaction:

1. The user sees role cards with role artwork and role names.
2. Clicking a role card animates the selected card into a focused left-side position.
3. Other role cards fade, collapse, or move out of focus.
4. A right-side configuration panel appears seamlessly for the selected role.
5. The user can accept defaults, choose provider/model/AI strategy, edit prompt settings, and save a local reusable configuration.
6. The user can later import saved local configurations.

The UI speaks in game language:

- Start New Match,
- Match History,
- Room Config,
- Role Cards,
- Player Seats,
- AI Lineup,
- Start Match,
- Replay.

The system and artifacts speak in engineering language:

- profile,
- run_id,
- experiment_id,
- prompt manifest,
- event spine,
- snapshots,
- provider trace,
- failure audit.

### 3.3 Role Defaults And Seat Overrides

AI configuration is role-default first and seat-overridable.

Default layer:

- all werewolves inherit the werewolf default AI config,
- all villagers inherit the villager default AI config,
- seer inherits the seer default AI config,
- witch inherits the witch default AI config.

Override layer:

- any individual seat can override provider, model, prompt profile, strategy, temperature, timeout, or budget guard,
- seat overrides are visible in the setup UI,
- the final runtime config resolves every seat into a complete independent AI configuration.

Conceptual data shape:

```text
role_defaults
  -> seat_overrides
  -> resolved_seat_configs
```

The runtime should consume resolved seat configs. The UI and local saved profile templates may preserve role defaults plus seat overrides for usability.

### 3.4 Preflight

Before a live run starts, the platform should run a preflight check:

- profile schema validity,
- provider availability,
- required secret presence without leaking secret values,
- budget guard,
- prompt manifest preview,
- visibility settings,
- output artifact destination,
- run mode: live or replay.

Preflight should be part of the product experience, not only a CLI validation step.

### 3.5 Live Match Cockpit

The cockpit should let a user understand the match without opening raw JSON:

- current day/night/phase/round,
- player seats, roles, alive/dead state,
- public event stream,
- current actor and latest action,
- voting and night-action summaries,
- provider status, failures, latency, and budget indicators,
- audit links for manifest, provider trace, failure audit, snapshots, and final logs,
- perspective switcher: God / Public / Role / Team.

### 3.6 Match History And Replay

Historical matches should support:

- listing completed runs,
- opening replay through the same observer model where possible,
- viewing the profile used,
- opening final logs and audit artifacts,
- comparing multiple runs later through experiment groups.

## 4. System Architecture

The product should keep a client-agnostic architecture:

```text
Profile / Match Setup
-> Python runtime game engine + agent/provider loop
-> event spine + snapshots + prompt manifest + provider lifecycle
-> local observer server
-> Qt/QML or Web observer clients
-> replay / audit / export
-> experiment orchestration
-> evaluation platform
```

Core components:

- Python runtime: owns game engine, agent loop, provider adapters, event bus, log writers, snapshots, manifests, and final bundle generation.
- Event spine: exposes stable runtime events with references to snapshots, prompt manifest entries, provider trace, failure audit, and final logs.
- Observer server: exposes local REST plus streaming protocol for run control, event observation, snapshot access, artifact lookup, and historical run replay.
- Observer client: consumes only client-agnostic protocol; Qt/QML is the recommended first rich client, but the protocol must also support future Web clients.
- Profile registry: stores local reusable match/profile templates and resolves role defaults plus seat overrides into per-seat runtime config.
- Experiment orchestration: groups runs, supports replay/live dual mode, records profile diffs and run metadata.
- Evaluation layer: later converts real run data into scorecards, aggregation, sample-size-aware comparisons, and leaderboards.

## 5. Phase Breakdown

### Phase A: Platform Charter & Experience Architecture

Goal: define the product route, system architecture, experience model, trust contracts, phase exits, and anti-shrinkage gates.

Inputs:

- current product docs,
- current roadmap,
- accepted client-agnostic observer ADR,
- current G1h foundation.

Outputs:

- this charter,
- later route-doc updates derived from approved decisions.

Exit demo:

- no runtime demo required,
- every later implementation plan can cite this document to identify product fit, scope boundaries, and shrinkage risks.

Boundary:

- no runtime code,
- no observer server implementation,
- no Qt/Web implementation,
- no scoring or leaderboard work.

### Phase B: G1h Contract Closeout + Route Docs Alignment

Goal: align canonical docs with merged G1h facts and remove stale route status.

Outputs:

- README / PRODUCT_ONE_PAGER / ROADMAP / TASKS status alignment,
- clear statement that G1h event spine is the foundation for G2a+,
- no false claim that observer server, rich client, profile editor, arena, or leaderboard exists.

Exit demo:

- route docs no longer show stale `next_candidate` facts for already merged G1h work,
- next implementation track is unambiguously G2a Local Observer Server.

Boundary:

- docs/status alignment only unless a bound implementation plan says otherwise.

### Phase C: G2a Local Observer Server / Protocol Control Plane

Goal: expose runtime and historical run data through a local client-agnostic protocol.

Outputs:

- REST endpoints for runs, status, snapshots, artifacts, manifest, provider trace, and failure audit,
- streaming endpoint for runtime events and status changes,
- run-control surface for start, stop, and inspect where allowed by plan,
- minimum match/profile contract seed for launching a default 6-player match without a full profile editor,
- compatibility with completed-run replay and live-run observation.

Exit demo:

- the same run can be observed and audited through protocol calls without manually opening local JSON files,
- a stream consumer can follow match progress from events and snapshots.

Boundary:

- no rich client,
- no prompt editor UI,
- no multi-provider arena,
- no leaderboard,
- no direct client access to Python runtime internals.

### Phase D: G2b Observer Cockpit MVP

Goal: provide the first rich match-observation experience, with Qt/QML as the recommended first client.

Starting scaffold:

- `clients/qt_observer` is the local Qt6 Quick starter project for this phase.
- The scaffold is currently auto-generated only and does not contain observer protocol integration, match cockpit UI, God/Role View, run control, or replay/history UI.

Outputs:

- game-like match cockpit,
- run status,
- player panels,
- live event stream,
- provider trace summary,
- audit links,
- basic replay/open historical run support where protocol permits.

Exit demo:

- a user can start from Home, choose Start New Match, accept the default 6-player config, review a preflight summary, start the run, enter the live cockpit, and later reopen it through history/replay,
- a user can watch a live or replayed AI-vs-AI match without reading JSON,
- the user can understand phase, player states, current actor, major events, and provider/failure status.

Boundary:

- Qt must consume REST/stream/event protocol,
- no direct binding to Python runtime objects or private APIs,
- no full prompt editor,
- no leaderboard.

### Phase E: Visibility Trust Layer

Position: cross-cutting gate plus independent hardening milestone.

Cross-cutting gate:

- G2a protocol must carry visibility fields, projection refs, and permission boundaries.
- G2b cockpit must render God / Public / Role / Team perspectives separately.
- G2c/G2d profile and prompt systems must declare how role information, visibility, and prompt manifest entries affect a run.

Independent hardening milestone:

- formal God/Public/Role/Team projection contract,
- hidden-information leak tests,
- audit proof for why each perspective can or cannot see an event or field,
- UI visibility badges and perspective warnings.

Exit demo:

- the same underlying event renders differently under God, Public, Role, and Team perspectives,
- hidden information leakage is covered by tests or explicit validation artifacts,
- the UI can show why data is hidden rather than silently omitting it.

Boundary:

- no weakening of Werewolf information asymmetry,
- no merging God View and Role View into one convenience payload,
- no prompt or provider artifact that leaks hidden roles into a role-limited view.

### Phase F: Prompt/Profile Configuration MVP

Goal: make match configuration reusable, validated, auditable, and user-facing.

Outputs:

- YAML or local profile template format,
- role defaults,
- seat overrides,
- resolved seat configs,
- profile validator,
- prompt manifest generation,
- local save/import of reusable configurations,
- setup UI entry points for selecting provider/model/prompt/strategy.

Exit demo:

- the user can start a match from a default config,
- customize role defaults and seat overrides,
- save the local configuration,
- import it later,
- start a run whose manifest traces the resolved provider/model/prompt/strategy per seat.

Boundary:

- no hosted account system,
- no cloud profile sync,
- no full multi-provider arena,
- no untraceable free-text prompt mutation at runtime.

### Phase G: Experiment Orchestration

Goal: turn individual matches into repeatable experiments.

Outputs:

- experiment_id and run groups,
- replay/live dual mode over the same observer model,
- profile diff tracking,
- batch metadata,
- cost/failure/latency summaries,
- comparison-ready exports.

Exit demo:

- the same profile group can run multiple matches,
- the user can compare run metadata, failures, costs, profile differences, and outcome summaries.

Boundary:

- no fake leaderboard,
- no score formula changes without real data and a bound evaluation plan,
- no uncontrolled provider-cost expansion.

### Phase H: Evaluation Platform

Goal: convert real run output into robust evaluation products.

Outputs:

- single-run scorecards,
- multi-run aggregation,
- role-separated metrics,
- sample-size warnings,
- provider/model/version comparisons,
- exportable evaluation reports,
- real leaderboard.

Exit demo:

- evaluation results are based on enough real runs,
- every score links back to run artifacts,
- leaderboard entries include sample-size and provenance warnings.

Boundary:

- no real leaderboard before G1h/G2/G3 data is stable and sufficient,
- no artificial gold-sample leaderboard presented as real,
- no scoring changes that cannot be traced to accepted evaluation design.

## 6. Cross-Cutting Trust Contracts

### Visibility Contract

Every event, snapshot field, prompt reference, and client payload must declare or derive its visibility boundary.

Required perspectives:

- God,
- Public,
- Role,
- Team.

God View is useful for auditing. Role View is useful for proving the agent or observer sees only allowed information. Team View is especially important for werewolf consensus.

### Artifact Provenance

All user-visible claims should trace back to structured artifacts:

- event ids,
- snapshot ids,
- prompt manifest refs,
- provider trace refs,
- failure audit refs,
- final log refs.

### Secret Redaction

Secrets must not enter:

- runtime events,
- snapshots,
- prompt manifest,
- provider trace payloads intended for user display,
- replay artifacts,
- saved local profiles.

Profiles may reference provider names and local secret keys by logical name, but not embed secret values.

### Failure Audit

Provider failures, parse failures, invalid actions, timeouts, and recovery paths must remain visible and auditable.

The platform must not silently repair provider failure into apparently valid behavior.

### Client-Agnostic Protocol

Clients consume protocol payloads, not Python internals.

Qt/QML can be the first rich client. Web can come later. Both must be able to consume the same conceptual observer model.

### Profile Manifest

Every run should emit a manifest that explains:

- selected match template,
- role defaults,
- seat overrides,
- resolved seat configs,
- provider/model/prompt/strategy refs,
- runtime options,
- visibility settings,
- redaction guarantees.

## 7. Exit Demo Requirements

Every phase needs a human-visible exit demo.

This prevents the route from becoming invisible infrastructure:

- Phase A: approved charter that future plans can cite.
- Phase B: route docs aligned with merged G1h facts.
- Phase C: protocol-observable run without manual JSON inspection.
- Phase D: cockpit-observable match without reading JSON.
- Phase E: perspective-specific rendering with leak-proof evidence.
- Phase F: saved/imported local profile starts a traceable run.
- Phase G: run group comparison with profile diff and failure/cost metadata.
- Phase H: provenance-linked evaluation output with sample-size warnings.

## 8. Anti-Shrinkage Gates

The route must not shrink into any of these:

- static HTML replay as primary UX,
- JSON viewer instead of observer cockpit,
- single-game smoke instead of configurable match platform,
- Qt client directly bound to Python runtime internals,
- prompt editing as an untraceable text box,
- role views that silently leak hidden information,
- provider failures hidden as valid gameplay,
- fake leaderboard before enough real run data exists,
- score formula changes before the evaluation platform has real evidence.

## 9. Open Design Questions

1. Should the first rich client remain Qt/QML-first, with Web later, or should Web become an equal early target?
2. Should G2a use REST + SSE, REST + WebSocket, or support both with one canonical event model?
3. How much raw provider response or reasoning should the cockpit expose by default?
4. Should raw provider responses live only in controlled audit artifacts while the UI shows redacted summaries?
5. How much prompt editing belongs in the first profile MVP versus later prompt editor work?
6. How should local saved profiles be stored, named, versioned, and migrated?
7. Should human player seats be reserved in the protocol now, even though human-vs-AI UI is out of current scope?
8. What is the minimum number of real runs before any G4 leaderboard view can call itself real?

## 10. Recommended Next Implementation Track

Recommended order:

1. Phase B route closeout: align docs with merged G1h facts.
2. Phase C implementation plan: G2a Local Observer Server / Protocol Control Plane.
3. Phase C must seed the minimum match/profile contract needed for default-template launch without becoming the full profile editor.
4. Phase E visibility contract slices embedded into G2a from the beginning.
5. Phase D observer cockpit MVP after protocol contracts exist, including a default-template start-match flow rather than observe-only behavior.
6. Phase F prompt/profile MVP once match setup and run launch boundaries are clear.

Do not jump directly from this charter into a Qt page or a single server endpoint. The next implementation plan should prove that the observer protocol can support the game-like match experience, visibility trust boundary, artifact provenance, and later profile/experiment layers.
