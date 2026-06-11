# ADR — Test strategy: fake-deterministic default, live behind an explicit gate

- **Status:** Accepted (retroactive documentation of a decision in force since G3-1 /
  P2-A-2; written down per health-check T-6, 2026-06-11)
- **Deciders:** owner + agent (grill 2026-06-05 locked the acceptance bar; this ADR
  distills `docs/PROJECT_MAP.md` "P2-A-2 验收口径" into a stable decision record)

## Context

The platform has two execution modes: **fake-deterministic** (scripted/seeded providers,
zero network, zero keys) and **live** (real provider HTTP calls, real keys, real cost).
Every entry point — engine CLIs, the observer server, profile templates — must choose a
default. Two failure modes threaten the project if this choice is left implicit:

1. **Accidental live**: a test, CI job, or default launch silently spends money, leaks a
   key into artifacts, or makes results network-dependent and flaky.
2. **Fake passed off as live**: a live run quietly degrades to fallback output and the
   aggregate metrics look fine ("fallback 糊过"). Live-quality conclusions drawn from
   such runs are worthless.

This is the project's instance of **Deterministic Simulation Testing** (SYS-C3 in
`docs/PROJECT_MAP.md`): the entire suite (1200+ tests) runs offline on the fake path;
live runs are a separately gated, separately audited activity.

## Decision

1. **fake-deterministic is the unconditional default at every entry point.** No key, no
   flag, no network is ever required to run an engine, the observer server, or the test
   suite. Profile templates default to the `fake_deterministic` provider
   (`default_6p_fake`), and the resolved-profile artifact stamps
   `execution_mode: "fake"` unless live was explicitly requested.
2. **Live requires an explicit double gate: opt-in flag AND a credential.**
   - CLI runners: `--allow-live-api` must be passed; without it the process exits
     non-zero **and writes no artifacts**. With the flag but no key in the environment,
     same outcome.
   - Observer server: live is off unless started with `--allow-live-api`; a live launch
     request against a non-live server is `403 live_disabled`, and with live enabled but
     no usable credential it is `403 missing_api_key` — in both cases **no run directory
     is created**.
3. **Determinism is a pinned property, not a convention.** Same seed ⇒ byte-identical
   artifacts. This is what makes golden/byte-gate refactor proofs and the scripted
   fixture contracts possible.
4. **Live output must prove it is live (honesty chain).** Live responses are stamped
   `source_label == "[DeepSeek API output]"`, carry `token_usage > 0` (fake is always 0),
   and every provider turn is classified via `provider_result_kind`
   (`live_success` / `invalid_then_fallback` / `timeout_then_fallback` /
   `error_then_fallback` / `budget_exhausted`). Fallback may save a game; it never
   counts toward live success, and `budget_exhausted` is a hard fail.
5. **CI runs only the fake path.** Live batches are user-run with the user's own key;
   the agent reviews raw artifacts offline (user-run / agent-offline-review, spec-review
   2026-06-05). CI must never need or carry a provider key.

## Enforcing tests (do not "fix" these — they encode this ADR)

- Gate at the CLI:
  `tests/test_deepseek_provider_game.py::test_cli_without_allow_live_api_exits_nonzero_and_writes_nothing`
  (+ `..._with_allow_live_but_missing_key_...`), and the same pair plus
  `test_cli_write_runtime_spine_without_allow_live_api_exits_nonzero` in
  `tests/test_deepseek_consensus_game.py`.
- Gate at the observer server: `tests/test_observer_server.py::`
  `test_capability_live_not_enabled_is_403_disabled`,
  `test_capability_live_enabled_no_launcher_is_403_missing_key`,
  `test_live_not_enabled_403_disabled_no_run_dir`,
  `test_live_enabled_no_key_403_missing_no_run_dir`.
- Fake as default: `tests/test_profile_config.py::test_default_call_stays_fake_back_compat`
  (and the `fake_deterministic` allowlist assertions in the same file).
- Determinism: `tests/test_emergent_engine.py::test_deterministic_same_seed_byte_identical`
  (+ `test_seeded_tiebreak_is_deterministic_per_seed`).
- Honesty chain: `tests/test_observer_server.py::test_live_dispatch_stamps_live_markers`,
  `tests/test_p2a2_live_path.py::test_timeout_then_fallback_classified_and_excluded_from_success`
  and `::test_invalid_live_action_downgraded_not_counted_success`.
- Artifact-shape parity (fake and live produce the same top-level artifact set, so the
  offline suite exercises the same contracts live runs ship):
  `tests/test_observer_server.py::test_live_and_fake_produce_same_top_level_artifact_set`.

## Consequences

- The full suite is runnable anywhere (no key, no network) and stays deterministic;
  flaky-by-network tests are structurally impossible on the default path.
- Live behaviour changes cannot be validated by CI; they require a gated live batch and
  offline artifact review (see `.agents/skills/running-live-games/`). This is accepted:
  the cost asymmetry (live = money + nondeterminism) justifies the split.
- Any new entry point (CLI, server route, launcher) MUST inherit both gates; a new
  surface that defaults to live or skips the no-artifacts-on-refusal behaviour is a
  regression against this ADR.

## References

- `docs/PROJECT_MAP.md` — "P2-A-2 验收口径" (hard gates ①–③, soft gate, user-run /
  agent-offline-review) and SYS-C3 (Deterministic Simulation Testing).
- `docs/adr/2026-06-11-byo-key-security-invariants.md` — the key-handling side of the
  same boundary.
- Health check: `docs/health-check/03-architecture-optimization.md` §T-6.
