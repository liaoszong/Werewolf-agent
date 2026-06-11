# ADR — BYO-key: client-owned secret, server-executed provider call

- **Status:** Accepted (architecture direction locked by grill 2026-06-05; implemented
  through P2-B-1 credential relay and the P2-B provider-center rework; written down per
  health-check T-6, 2026-06-11)
- **Deciders:** owner + agent (this ADR distills `docs/PROJECT_MAP.md` "P2-B 架构方向:
  BYO-key" into a stable decision record)

## Context

Live games need real provider API keys. The original posture (dev/server-owned
credentials via environment variables) does not scale to "users configure their own AI
per seat" (P2-B / SYS-B3): users must be able to bring their own keys for nine
OpenAI-compatible providers without the project ever owning, transmitting, or storing
those secrets beyond the user's machine.

Two architectural temptations had to be explicitly rejected:

- letting the Qt client call vendor APIs directly (would fork provider logic into C++/QML
  and break "Python owns engine/provider, Qt is a configure+observe client");
- persisting keys server-side for convenience (turns a local relay into a credential
  store with all the liabilities that implies).

## Decision

**Slogan: client-owned secret, server-executed provider call.** The user's key is
collected by the Qt client and handed to the **local** Python observer server over
loopback; all provider network calls are executed by that Python process only.

Three invariant layers, strictest first:

### 1. Hard invariants (never violated, in any mode)

- No key is ever hardcoded in source.
- No key is ever committed, logged, echoed in an HTTP response, or exported into any
  artifact: review packet, prompt manifest, runtime events, provider trace, settlement
  bundle, client crash logs.
- `fake-deterministic` mode never needs a key (see
  `docs/adr/2026-06-11-fake-default-live-gate-testing-strategy.md`).

### 2. Architecture invariant

- Qt may collect and hold the user's own key and send it to the **local** observer
  server (loopback + CSRF-guarded `POST /api/credentials`).
- Provider network calls are executed **only** by the local Python server/provider
  layer. Qt never talks to vendor APIs directly — the static contract scan
  (`FORBIDDEN_SECRET_PATTERNS`) keeps vendor-call and secret markers out of client
  sources.

### 3. Storage invariant

- Direction (PROJECT_MAP): prefer OS keychain / credential vault; any local fallback
  must be dev-only or encrypted; UI shows masked keys only.
- **Implemented today (stricter than required):** the server-side `CredentialStore` is
  in-memory and process-lifetime only — never persisted, never serialized;
  `__repr__`/`__str__` are redacted so even a failing test cannot print a key. The Qt
  client persists nothing; keys are re-entered (or re-synced) per session. If keychain
  persistence is added later it must land under this layer's rules, not relax them.

### Documented back-compat exception (scheduled for retirement)

`run_observer_server.resolve_live_launcher` still builds a server-side launcher from the
`DEEPSEEK_API_KEY` environment variable when the server is started with
`--allow-live-api`. This is a deliberate, deepseek-only bridge from the pre-BYO-key era;
it is pinned to *not leak across providers* by
`tests/test_observer_credentials_endpoint.py::test_deepseek_env_backcompat_does_not_leak_to_other_providers`,
and its retirement is specced in
`docs/superpowers/specs/2026-06-11-sys-b3-b5-closeout-design.md` (B5).

## Enforcing tests (do not "fix" these — they encode this ADR)

- Store never leaks: `tests/test_credential_store.py::test_repr_and_str_never_contain_key`,
  `::test_repr_never_contains_base_url_or_key`.
- Server never echoes secrets:
  `tests/test_observer_credentials_endpoint.py::test_post_stores_base_url_and_does_not_echo_secret`.
- Env back-compat stays deepseek-scoped:
  `tests/test_observer_credentials_endpoint.py::test_deepseek_env_backcompat_does_not_leak_to_other_providers`,
  `tests/test_observer_server.py::test_live_mixed_models_env_only_requires_client_key`.
- Artifacts carry no secret markers:
  `tests/test_observer_server.py::test_faked_live_artifacts_contain_no_secret_markers`.
- Missing credential refuses cleanly (no run dir, no partial launch):
  `tests/test_observer_server.py::test_live_missing_provider_credential_403_no_run_dir`;
  per-seat credentials flow:
  `::test_live_multi_provider_runs_with_per_seat_creds`.
- Client is statically clean:
  `tests/test_qt_observer_static_contract.py::test_client_sources_do_not_contain_secret_markers`.
- Review packet redacts credentials:
  `tests/test_build_review_packet.py::test_packet_redacts_credentials_from_diff`.

## Consequences

- Provider logic, retries, budgets, and trace redaction live in exactly one place
  (Python provider layer / `provider_registry`); adding a provider never touches the
  client's security surface.
- Keys never cross a machine boundary: Qt → loopback server → vendor API, all local.
- The cost is per-session re-entry of keys (no persistence yet) and a server restart
  losing credentials — accepted until a keychain slice is justified.
- Any new artifact, endpoint, or log line is born under layer 1: the burden of proof is
  on the new surface to show it cannot carry a secret (extend the secret-marker scans
  when in doubt).

## References

- `docs/PROJECT_MAP.md` — "P2-B 架构方向:BYO-key" (the three-layer source text) and
  SYS-B3 (Model Gateway).
- Spec history: `docs/superpowers/specs/2026-06-07-p2-b-1-byo-key-credential-relay-design.md`,
  `docs/superpowers/specs/2026-06-08-byo-key-provider-presets-design.md`.
- Risk closure: `docs/RISK_ASSESSMENT_2026-06-06.md` (R-06 guard, R-19 redaction
  narrowing, R-18 wolf-snapshot leak — the leak class this ADR's scans defend against).
- Health check: `docs/health-check/03-architecture-optimization.md` §T-6.
