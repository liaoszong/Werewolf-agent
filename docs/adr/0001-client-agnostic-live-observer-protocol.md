# ADR 0001: Client-Agnostic Live Observer Protocol

Date: 2026-06-03

## Status

Accepted.

## Context

G1a-G1g established the audit and replay foundation for Werewolf-agent:

- deterministic and provider-backed game runs can emit structured logs
- consensus, provider trace, and failure audit can be inspected after the run
- G1g can render a static HTML replay/report from existing log bundles

That foundation is useful, but an offline HTML replay/report is not the primary product experience. The project is pivoting toward a configurable, observable, live AI Werewolf experiment platform.

The next user-facing architecture must support multiple clients. Qt/QML is the recommended first rich client because it fits the desired desktop experiment-platform workflow, but the runtime protocol must not bind the product to Qt or to Python internals.

## Decision

Build the platform in this order:

1. G1h Live Runtime Event Spine.
2. G2a Local Observer Server.
3. G2b Qt Observer MVP.
4. Later Web observer and broader experiment/evaluation layers.

The Python runtime owns:

- game engine
- agent runtime
- provider adapter
- prompt registry
- event bus
- log writer
- runtime snapshots
- prompt manifest
- standard log bundle compatibility

Clients consume a client-agnostic protocol. Qt/QML must consume REST/WebSocket/event protocol from the local observer server and must not bind directly to Python runtime objects, private Python APIs, or in-process engine state.

HTML replay/report output remains an offline audit artifact. It can read log bundles and help reviewers inspect completed runs, but it is not the primary UX and must not be treated as a live observer.

## Consequences

- G1h must focus on event spine and artifact compatibility, not UI.
- G2a must expose events and snapshots through transport contracts before a rich client is built.
- G2b can use Qt/QML as the first rich client while preserving future Web support.
- Replay and live modes can converge later because both can consume the same event/snapshot model.
- Evaluation and Leaderboard work moves later, after enough live runs can be captured consistently.

## Explicit Non-Goals For G1h

- no Qt/QML client
- no Web observer/server
- no prompt editor UI
- no multi-provider arena
- no leaderboard
- no scoring formula changes
- no provider adapter behavior changes beyond event-spine instrumentation required by the bound plan

## Compatibility Requirements

- Existing Game Log / Decision Log / Consensus Log validators remain authoritative.
- Provider Trace and Failure Audit remain compatible audit surfaces.
- Runtime events may reference final logs and provider trace entries, but they do not replace canonical final logs.
- Secret-bearing values must be redacted before any event, snapshot, manifest, or replay artifact is written.
