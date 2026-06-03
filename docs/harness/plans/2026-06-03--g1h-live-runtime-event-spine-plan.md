# G1h Live Runtime Event Spine Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Establish a client-agnostic live runtime event spine for a single Werewolf run so later observer servers and clients can subscribe to runtime progress without binding to Python internals.

**Architecture:** Extend the existing real/fake provider single-game runtime path with an append-only event writer, runtime snapshots, prompt manifest, provider lifecycle events, and final log-bundle compatibility. G1h must keep Game Log / Decision Log / Consensus Log / Provider Trace / Failure Audit as canonical final artifacts while adding a runtime observation layer around them.

**Tech Stack:** Python stdlib only unless a later approved plan says otherwise. No Qt, Web server, UI framework, dependency change, scoring formula change, or validator rewrite in G1h.

---

## Why this follows G1g

G1g made completed provider-backed game bundles inspectable as an offline HTML replay/report. That is useful for audit and review, but it does not provide live observability. G1h moves the project from "render a completed bundle" to "capture a run as a live event stream that clients can consume later."

G1a-G1g remain valuable as:

- audit foundation
- replay foundation
- log bundle foundation
- provider trace foundation
- failure audit foundation

## Scope

G1h includes:

- real/fake provider single-game runtime compatibility
- `events.jsonl` append-only runtime event output
- runtime snapshots for current round, phase, alive players, role/team/state data, and visibility-safe projections
- prompt manifest with agent prompt/profile/model/temperature/strategy metadata and redacted secret-bearing values
- provider lifecycle events for request preparation, response receipt, parse success, parse failure, invalid action, timeout, latency, token usage, and provider failure
- standard log bundle compatibility with Game Log, Decision Log, Consensus Log, Provider Trace, and Failure Audit
- deterministic fake-provider path suitable for CI tests
- live provider path guarded by explicit opt-in only

## Non-Goals

G1h does not include:

- Qt/QML client
- Web observer/server
- prompt editor UI
- multi-provider arena
- leaderboard
- scoring formula changes
- validator rewrites
- demo renderer changes
- generated HTML changes
- provider SDK or dependency changes
- API spec or data schema overhaul beyond the minimal event/snapshot/manifest contract in this plan

## Proposed Artifacts

Runtime output directory should contain:

```text
events.jsonl
snapshots/
prompt-manifest.json
game-log.json
decision-log.json
consensus-log.json
provider-trace.json
failure-audit.json
```

The exact output directory remains task-specific and should default to `.tmp/` for live smoke runs.

## Event Spine Contract

Each runtime event should be a single JSON object per line. The minimum envelope:

```json
{
  "run_id": "string",
  "seq": 1,
  "event_id": "string",
  "kind": "string",
  "round": 1,
  "phase": "night",
  "actor": "p1",
  "visibility": "god",
  "payload": {},
  "refs": {},
  "created_at": "ISO-8601 timestamp"
}
```

Contract rules:

- `seq` is strictly monotonic within one run.
- `event_id` is stable within one run and unique in `events.jsonl`.
- `kind` is a constrained string documented in the implementation PR.
- `refs` may point to final Game Log event IDs, Decision Log IDs, Consensus Log IDs, provider request IDs, provider response IDs, failure IDs, or snapshot IDs.
- Runtime events do not replace canonical final logs.
- Secret-bearing fields must be redacted before writing.

## Snapshot Contract

G1h should separate:

- god-view snapshot: full audit state for local operator inspection
- role-view projection: what one player/agent is allowed to observe

Acceptance depends on proving the role-view projection does not reveal hidden roles or private team information outside the allowed visibility model.

## Prompt Manifest Contract

Prompt manifest should record enough configuration to make a run auditable:

- run ID
- agent IDs
- role assignments
- prompt/profile identifiers
- model names
- temperature and strategy parameters
- prompt text or prompt hash, depending on sensitivity
- redaction status

Secrets, API keys, bearer tokens, and local credential paths must not appear in the manifest.

## Compatibility Requirements

- Existing Game Log / Decision Log / Consensus Log validators remain unaffected.
- Existing Provider Trace and Failure Audit remain valid audit artifacts.
- Existing scoring behavior remains unchanged.
- Existing HTML replay/report renderer remains unchanged.
- Fake-provider tests must run without network access.
- Live provider execution must remain opt-in and must not run in CI by default.

## Suggested Task Breakdown

### Task 1: Define event, snapshot, and prompt manifest contract

- [ ] Add narrow tests for event envelope validation.
- [ ] Add narrow tests for monotonic `seq`.
- [ ] Add narrow tests for secret redaction in prompt manifest.
- [ ] Document the event kinds introduced by the implementation.

### Task 2: Add append-only event writer and snapshot writer

- [ ] Emit setup, phase transition, observation, agent action, provider lifecycle, consensus, failure, and finalization events.
- [ ] Write god-view snapshots.
- [ ] Write role-view projection snapshots.
- [ ] Keep runtime event writing orthogonal to final log generation.

### Task 3: Integrate fake-provider runtime path

- [ ] Produce `events.jsonl`, snapshots, prompt manifest, provider trace, failure audit, and standard final logs.
- [ ] Verify fake-provider path runs without network.
- [ ] Verify final logs still pass existing validators.

### Task 4: Integrate live-provider opt-in path

- [ ] Preserve explicit live API guard.
- [ ] Record provider lifecycle events without leaking secrets.
- [ ] Write final log bundle compatibility artifacts.
- [ ] Keep live smoke artifacts under `.tmp/` unless a later plan explicitly approves a sanitized committed sample.

### Task 5: Build review packet

- [ ] Include changed files, allowlist, forbidden pattern scan, dependency diff, test summary, event-spine acceptance evidence, and risk notes.
- [ ] Keep review packet compact; do not paste full `events.jsonl`.

## Acceptance Criteria

A1. `events.jsonl` exists for the fake-provider path and contains strictly monotonic `seq` values.

A2. Runtime events can reference final Game Log / Decision Log / Consensus Log / Provider Trace / Failure Audit entries through explicit `refs`.

A3. God-view snapshot and role-view projection are written separately.

A4. Role-view projection does not leak hidden roles or private team data outside the allowed visibility model.

A5. Prompt manifest exists and records prompt/profile/model/temperature/strategy metadata without secrets.

A6. Provider lifecycle events cover request, response, token usage, latency, parse failure, invalid action, timeout, and provider failure where applicable.

A7. Existing validators remain unaffected and continue to validate final logs.

A8. Fake-provider path is testable in CI without network access.

A9. Live provider path remains opt-in only and is not run by CI by default.

A10. No Qt, Web observer/server, prompt editor, multi-provider arena, leaderboard, scoring formula change, validator rewrite, demo renderer change, or generated HTML change is introduced.

## Review Risk Points

1. Event stream can accidentally become a second canonical log format instead of an observation layer.
2. Role-view projection can leak hidden information if it reuses god-view snapshots.
3. Prompt manifest can leak secrets if redaction is not tested.
4. Provider lifecycle events can duplicate provider trace inconsistently if refs are not explicit.
5. G1h can overreach into G2/G3/G4 if UI, server, prompt editor, multi-provider, or leaderboard work enters the PR.
