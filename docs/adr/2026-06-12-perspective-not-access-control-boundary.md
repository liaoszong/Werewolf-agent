# ADR — The observer `perspective` parameter is a presentation lens, NOT an access-control boundary

- **Status:** Accepted (audit 2026-06-12 item A45-1, owner-adjudicated)
- **Deciders:** owner + agent (`docs/health-check/2026-06-12-system-view-audit.md` §A45-1)
- **System view:** SYS-A4 (Information Visibility) × SYS-C2 (Replay / Spectator)

## Context

The observer server (`src/werewolf_eval/observer/handler.py`) accepts a
`perspective` query parameter (`god` / `public` / `role:pN` / `team:werewolf`) on
its run routes. For the **projection / events / snapshots** routes this lens is
enforced: `filter_events_for_perspective`, `build_projection_envelope`, and the
trust-index/projection layers (`observer_trust_index.py` / `observer_projection.py`)
decide what each perspective may see, with the I4b oracle as the independent witness.

The **raw artifact** routes are different. `_route_run_artifact_detail` and
`_route_run_artifact_alias` take `perspective` as a parameter but **do not use it** —
they serve the requested file verbatim via `_send_artifact_file(art_path)`, gated
only by `ALLOWED_ARTIFACTS` (a path/allowlist gate, not a perspective gate).
`ALLOWED_ARTIFACTS` includes `game-log.json`, `decision-log.json`, and
`provider-trace.json`. The provider-trace contains every seat's full private
`observation_text`; the decision-log contains every seat's private reasons; the
game-log contains all events including role-private ones. In other words, **any
client that can reach the artifact endpoint can read God/audit-level data,
regardless of the `perspective` it passes.**

This is correct and safe under the **current threat model**: a single local
operator (the audit/dev running the observer on loopback) inspecting their own
games. It is NOT safe under a future multi-client threat model where each seat is a
distinct, possibly adversarial, real participant hitting the same server.

## Decision

1. **`perspective` is a presentation/projection lens, not an authorization boundary.**
   It shapes what the projection/events/snapshots routes *render*; it confers no
   access control. Passing `perspective=role:p3` does not restrict what artifacts a
   caller may download.

2. **Raw artifacts are God / audit level.** `provider-trace.json`,
   `decision-log.json`, and `game-log.json` (and any other `ALLOWED_ARTIFACTS`
   entry) expose all-seat private information by design. They are intended for the
   local operator / auditor, not for per-seat clients.

3. **Current threat model = local observer / single audit operator.** The server is
   a local, single-trust-domain tool (loopback, same-origin). Within that model,
   serving raw artifacts to "the operator" is the intended behavior, and adding
   per-perspective artifact gating now would be **over-design** — it would imply a
   security guarantee the architecture does not yet need and cannot yet enforce
   end-to-end.

4. **Authorization tiering is REQUIRED before any multi-trust deployment.** Before
   P3 multi-client, human-in-the-loop / human-vs-AI mixed games, or any deployment
   where a real per-seat participant connects to a shared server, the server MUST
   gain an authentication + authorization tier that:
   - binds a caller identity to a perspective, and
   - gates raw artifact access (provider-trace / decision-log / god snapshots /
     full game-log) to operator/audit identities only, exposing per-seat clients
     to projection-filtered data only.
   This ADR is the explicit marker that such tiering is owed at that boundary.

## Consequences

- The visibility *projection* code stays the single audited surface for "what a
  perspective may render" (see `docs/adr/2026-06-11-observer-visibility-layering.md`);
  it is deliberately NOT repurposed as an auth gate.
- Anyone reading the artifact routes is on notice: do not treat `perspective` as a
  permission. A reviewer who sees a per-seat client reaching artifact endpoints
  should flag it as a missing auth tier, not a projection bug.
- No code changes in this ADR; it is a boundary declaration. The compensating
  control today is deployment scope (local loopback, single operator).

## Out of scope (explicitly NOT done here)

- Implementing authentication or authorization (no identity model, no per-artifact
  ACL, no token check). This ADR declares the boundary; it does not build it.
- Changing `ALLOWED_ARTIFACTS`, the artifact routes, or projection behavior.
- P3 multi-client design — that work, when scheduled, must consume this ADR and add
  the auth tier described in Decision §4.

## References

- Audit: `docs/health-check/2026-06-12-system-view-audit.md` §A45-1.
- Code: `src/werewolf_eval/observer/handler.py` (`_route_run_artifact_detail`,
  `_route_run_artifact_alias`, `_query_perspective`);
  `src/werewolf_eval/observer_protocol.py` (`ALLOWED_ARTIFACTS`, `artifact_path`).
- Visibility layering: `docs/adr/2026-06-11-observer-visibility-layering.md`.
- Protocol ADR: `docs/adr/0001-client-agnostic-live-observer-protocol.md`.
