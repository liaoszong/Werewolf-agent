# P3-C-0 Server Action Protocol Design

> Status: **DESIGN — protocol boundary locked**  
> Date: 2026-07-03  
> Scope: server-side human participant action protocol  
> Decision: **server-owned action windows + participant session tokens + idempotent submit + reconnect cursor**

---

## 1. Context

P3 promotes Werewolf-agent from a watchable AI-vs-AI theater into a mixed human/AI social deduction game. P3-E can build a Flutter client that observes runs, but a real human seat cannot be implemented safely until the server owns a participant action protocol.

The current observer protocol already exposes run lists, status, projections, snapshots, artifacts, and SSE. It was originally built for a local single-operator observer. P3-C adds a different trust model: a human player controls exactly one seat and must never receive god/audit artifacts, other-seat private data, provider traces, or hidden role facts through the participant channel.

This spec defines the server contract that P3-E-3 depends on. It does not implement the endpoints.

---

## 2. Decision

Add a participant-seat protocol beside the existing observer protocol.

The server remains authoritative for:

- which seat is human-controlled;
- which perspective/session may see which projection;
- which action window is currently open;
- which action kinds are legal in that window;
- whether a submitted action is accepted, duplicated, stale, forbidden, or timed out;
- what event is appended to the auditable event stream.

Clients only render legal state and submit candidate actions. They do not derive legality from local artifacts, local snapshots, god projection, or client-side timers.

---

## 3. First Slice

P3-C first playable scope:

- one local human villager seat;
- one participant client per human seat;
- LAN/local server topology from P3-E;
- public discussion, response windows, voting, final words where the game rules allow them;
- timeout and reconnect support;
- no human wolf/seer/witch/private night ability yet.

The protocol is shaped so later roles can reuse it, but P3-C-0 must not require implementing multi-human games, role-private abilities, accounts, matchmaking, cloud hosting, mobile push, or room-code discovery.

---

## 4. Core Objects

### ParticipantSession

```text
participant_session_token
run_id
seat_id
perspective = role:<seat_id>
controller = human
issued_at
expires_at
revoked_at?
last_seen_cursor
```

Rules:

- A token binds one client session to one run and one seat.
- A token is bearer-style in the first local slice; it must never be logged, exported, written to events, or embedded in public artifacts.
- A token never grants artifact access.
- A token never grants god projection.
- A token can be revoked when the run ends, the seat is no longer human-controlled, or the host resets the session.

### ActionWindow

```text
action_window_id
run_id
seat_id
phase
round
game_revision
opened_at_event_id
deadline_at
allowed_actions[]
required
default_on_timeout
status = open | accepted | timed_out | cancelled | superseded
reconnect_cursor
```

Rules:

- The server creates action windows; the client cannot request arbitrary turns.
- Only one open required window may exist for a given human seat.
- `game_revision` changes when the game advances in a way that can stale a submission.
- `allowed_actions` is rendered from server truth, not inferred by the client.
- `reconnect_cursor` lets the client resume from a known stream/event position.

### ParticipantActionSubmission

```text
action_window_id
game_revision
idempotency_key
action_type
payload
client_observed_event_id?
client_sent_at?
```

Rules:

- `idempotency_key` is required for every submit.
- Repeating the same `idempotency_key` for the same window returns the first result.
- Reusing an `idempotency_key` with different payload is rejected as conflict.
- `payload` is action-type-specific but always validated by server-side action contracts.
- Human free text is untrusted game data.

---

## 5. Endpoint Shape

Endpoint names are design targets, not implemented routes.

### Join Or Resume Seat

```text
POST /api/runs/{run_id}/participants/join
```

Request:

```json
{
  "seat_id": "p3",
  "join_code": "local-dev-code"
}
```

Response:

```json
{
  "schema_version": "p3c.participant_session.v1",
  "run_id": "run_123",
  "seat_id": "p3",
  "participant_session_token": "<opaque>",
  "perspective": "role:p3",
  "reconnect_cursor": "event:42"
}
```

First-slice join policy:

- Local dev may use a host-visible join code or explicit local setup token.
- No account identity is required.
- The join response must not include role facts beyond what `role:p3` may know.

### Get Participant State

```text
GET /api/runs/{run_id}/participant/state
Authorization: Bearer <participant_session_token>
```

Response:

```json
{
  "schema_version": "p3c.participant_state.v1",
  "run_id": "run_123",
  "seat_id": "p3",
  "perspective": "role:p3",
  "run_status": "running",
  "projection": { "...": "role-safe projection envelope" },
  "open_action_window": { "...": "ActionWindow or null" },
  "reconnect_cursor": "event:57"
}
```

Rules:

- This endpoint uses participant authorization, not a query-string `perspective` lens.
- It returns projection-filtered data only.
- It never returns raw artifacts, provider trace, full game log, god snapshots, or other-seat private notes.

### Submit Action

```text
POST /api/runs/{run_id}/participant/actions
Authorization: Bearer <participant_session_token>
```

Request:

```json
{
  "action_window_id": "aw_0007",
  "game_revision": 18,
  "idempotency_key": "client-generated-uuid",
  "action_type": "vote",
  "payload": {
    "target": "p5"
  }
}
```

Response when accepted:

```json
{
  "schema_version": "p3c.action_submit_result.v1",
  "status": "accepted",
  "action_window_id": "aw_0007",
  "game_revision": 19,
  "accepted_event_id": "evt_0091",
  "reconnect_cursor": "event:91"
}
```

Response when duplicated:

```json
{
  "schema_version": "p3c.action_submit_result.v1",
  "status": "duplicate",
  "action_window_id": "aw_0007",
  "accepted_event_id": "evt_0091",
  "reconnect_cursor": "event:91"
}
```

### Participant SSE

```text
GET /api/runs/{run_id}/participant/events?cursor=event:57
Authorization: Bearer <participant_session_token>
```

Event kinds:

- `participant_projection_updated`
- `action_window_opened`
- `action_window_updated`
- `action_accepted`
- `action_rejected`
- `action_window_timed_out`
- `run_status`

Rules:

- SSE data is filtered to the participant session perspective.
- The stream may include action-window state, but never raw hidden facts.
- Clients should treat SSE as a convenience; reconnect must be correct through `GET participant/state`.

---

## 6. Action Types

P3-C first slice needs these human-facing action types:

| action_type | Phase | Payload | Notes |
|---|---|---|---|
| `speech` | day discussion | `{ "text": string, "reply_to_event_ids"?: string[], "addressed_seats"?: string[] }` | Free text is untrusted game data. Length capped server-side. |
| `response` | limited response window | same as `speech` | Triggered by table-talk rules; not an infinite chat loop. |
| `vote` | day voting | `{ "target": "p1".."p6" }` | Target must be alive and legal. |
| `final_words` | post-execution if allowed | `{ "text": string }` | Optional by ruleset. |
| `pass` | any optional window | `{}` | Only legal when the server marks the window optional or passable. |

Later roles can add `seer_check`, `witch_save`, `witch_poison`, `werewolf_kill_vote`, and `team_message`, but those are out of P3-C first slice.

---

## 7. Error Semantics

Errors are machine-readable and stable. HTTP codes are transport hints; clients should branch on `error_code`.

| HTTP | error_code | Meaning |
|---|---|---|
| 400 | `invalid_payload` | JSON shape, missing fields, invalid enum, text too long. |
| 401 | `missing_or_invalid_session` | No valid participant token. |
| 403 | `seat_not_controlled_by_session` | Token does not own the target seat/run. |
| 403 | `visibility_forbidden` | Request would expose data outside this seat's perspective. |
| 404 | `run_not_found` | Unknown run. |
| 404 | `action_window_not_found` | Unknown window for this run/seat. |
| 409 | `stale_game_revision` | Client submitted against an old revision. |
| 409 | `idempotency_conflict` | Same key, different payload. |
| 409 | `action_window_closed` | Window already accepted/timed out/cancelled/superseded. |
| 422 | `illegal_action` | Action kind or payload is not legal in this window. |
| 423 | `run_not_accepting_actions` | Run not running or paused/interrupted. |

All rejection responses include:

```json
{
  "schema_version": "p3c.error.v1",
  "error_code": "stale_game_revision",
  "message": "Human-readable, no secrets",
  "run_id": "run_123",
  "seat_id": "p3",
  "action_window_id": "aw_0007",
  "current_game_revision": 19,
  "reconnect_cursor": "event:91"
}
```

---

## 8. Timeout Policy

Timeout policy is server-side and visible in the action window:

```text
timeout_policy = skip | pass | ai_takeover
```

Rules:

- `skip`: emit timeout and advance without an action when rules allow.
- `pass`: submit deterministic pass/no-op.
- `ai_takeover`: hand the current window to an AI controller and label the event as takeover.

P3-C first slice should prefer `pass` for optional speech/response windows and `ai_takeover` or deterministic fallback for required votes, chosen by profile. The important invariant is auditability: timeout outcome must create explicit events, not silently mutate game state.

Mobile push notification is out of scope. Before push exists, UX relies on foreground countdowns, reconnect, and server timeouts.

---

## 9. Event And Artifact Requirements

Every participant action or timeout must append auditable runtime events:

- action window opened;
- action submitted;
- action accepted or rejected;
- action window closed;
- timeout/takeover when applicable.

Event payloads must include:

- `run_id`
- `seat_id`
- `action_window_id`
- `game_revision`
- `action_type`
- `source = human | timeout | ai_takeover`
- redacted participant/session metadata only

Events must not include:

- participant session token;
- raw Authorization header;
- join code;
- provider secret;
- hidden data from another seat.

Final logs should be able to explain a human turn without needing client-local files.

---

## 10. Security Boundary

P3-C consumes the ADR rule that observer `perspective` is a presentation lens, not authorization. Participant routes must therefore introduce real authorization:

- Session token binds caller to run + seat.
- Participant endpoints reject `perspective` query overrides.
- Participant endpoints never serve raw artifacts.
- Participant endpoints derive projection internally from token-owned seat.
- Action submissions are validated against server-side action windows and current game revision.

Client-side state is never trusted for legality or visibility. Client clocks may drift; deadlines are server-owned. Client text is never interpreted as instruction or code.

---

## 11. Implementation Slices

### P3-C-0a Protocol Types And Validators

- Define schema constants and validators for participant session, action window, submissions, and errors.
- Add deterministic unit tests for validation, idempotency-key rules, and error codes.

### P3-C-0b Server Route Skeleton

- Add participant join/state/submit/SSE routes behind fake/local-only session issuance.
- Stub one action window and trivial submit round-trip for P3-E-1 risk probe.
- No full game-loop integration yet.

### P3-C-1 Villager Seat Integration

- Thread real action windows into day speech/response/vote/final-word windows.
- Ensure human seat receives only role-safe projections.
- Add timeout behavior and reconnect smoke.

### P3-C-2 Multi-role Expansion

- Add role-private abilities after the villager slice proves the protocol.
- Extend visibility tests before enabling human wolf/seer/witch.

---

## 12. Verification Strategy

Docs-only verification for this spec:

- Changed files stay under docs and tree metadata.
- No runtime, provider, validator, fixture, Qt/QML, Flutter, or workflow files change.

Future implementation gates:

- participant token cannot access god/artifact endpoints;
- role participant cannot read other-seat private events;
- submit without valid session is rejected;
- duplicate idempotency key returns the original result;
- same idempotency key with different payload is rejected;
- stale `game_revision` is rejected with current revision and reconnect cursor;
- timeout emits explicit auditable event;
- reconnect after SSE drop returns current role-safe state;
- adversarial player text is rendered/stored as untrusted game data only.

---

## 13. Non-Goals

- No cloud auth, accounts, matchmaking, lobby, or room-code discovery.
- No mobile push service.
- No raw artifact authorization redesign beyond participant routes refusing artifacts.
- No human wolf/seer/witch in the first slice.
- No client-side legality engine.
- No direct provider calls from any client.
- No replacement of existing observer routes.

