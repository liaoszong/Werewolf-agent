# SYS-B3 / B5 closeout — per-seat token & cost rollup + retire the deepseek-only env fallback (design)

- **Status:** Design only — no code in this document's slice.
- **⚠️ Implementation gate:** do NOT start implementation until the **T17 live batch
  track is fully closed** (verdict + next-step decided by owner). Both items below touch
  the live launch path; changing it mid-batch would invalidate paired-seed comparisons.
- **Scope owner:** SYS-B3 Model Gateway (`docs/PROJECT_MAP.md`), the "剩 B5 收尾" line.

## Part 1 — Per-seat token & cost rollup

### Current state (verified 2026-06-11)

- Per-turn `token_usage` is recorded on every provider response and lands in
  `provider-trace.json`.
- `settlement_bundle._load_seat_meta` (R-09) already **sums `token_usage` by actor**
  from `provider-trace.json` and stamps it per player into the settlement bundle.
- Gap A — **cost**: nothing converts tokens to money; users configuring 9 different
  providers per seat have no per-seat or per-run cost signal.
- Gap B — **scaffold turns**: `run_emergent_deepseek_game.py` notes that
  `actor == "scribe"` turns (scaffold, not a seat) must not be attributed to a seat;
  today they simply vanish from any total (the per-player loop only reads seat actors),
  so the run total understates real spend.
- Gap C — **surfacing**: the Qt settlement view does not show token/cost columns.

### Design

1. **Pricing is registry metadata, and optional.** Extend each `ProviderSpec` in
   `provider_registry` with an optional `pricing` block:
   `{"input_per_mtok": float, "output_per_mtok": float, "currency": "USD"}`.
   - No pricing on a spec ⇒ that seat shows token totals only, cost row absent. Cost is
     always labeled an **estimate** (prices drift; we do not promise billing accuracy).
   - `fake_deterministic` never has pricing (tokens are 0 by the honesty chain anyway).
2. **Rollup shape (settlement bundle, additive fields only):**
   - per player: keep existing `token_usage` sums; add
     `cost_estimate: {"amount": float, "currency": str} | null`.
   - new top-level `usage_summary`: `{"seats": {...sums...}, "scaffold": {...}',
     "total": {...}}` where `scaffold` carries non-seat actors (e.g. `scribe`) so the
     total is honest. Unknown actors fall into `scaffold` rather than being dropped.
   - Additive ⇒ no `BUNDLE_VERSION` bump *provided* the static/Qt contract tests don't
     pin the exact key set — verify at plan time; if they do, bump and regen fixtures.
3. **Where it computes:** entirely inside `settlement_bundle` (filesystem-only, lazy,
   best-effort like `_load_seat_meta` — absent/garbage trace ⇒ fields absent, never
   raises). No engine or provider changes; live path untouched at request time.
4. **Qt settlement view:** add token/cost per seat to the existing per-player table and
   one run-total line. Masked-key/secret rules unaffected (amounts are not secrets).

### Non-goals

- No automatic price updates, no billing API calls, no historical price versioning
  (a price change is a normal registry edit, reviewable in diff).
- No mid-game/live HUD cost ticker (settlement-time only, this slice).

## Part 2 — Retire the deepseek-only env fallback

### Current state (verified 2026-06-11)

- `run_observer_server.resolve_live_launcher` builds an **env-key launcher** from
  `DEEPSEEK_API_KEY` (`--api-key-env`) at server startup and passes
  `env_key_available` into `create_observer_server`. This predates BYO-key; it is
  deepseek-only and pinned by
  `tests/test_observer_credentials_endpoint.py::test_deepseek_env_backcompat_does_not_leak_to_other_providers`
  and `tests/test_observer_server.py::test_live_mixed_models_env_only_requires_client_key`.
- The BYO-key path (`POST /api/credentials` → `CredentialStore` → per-launch factory)
  is complete and is how the provider-center UI works.

### Design

1. **Remove the env launcher path from the observer server**: drop
   `env_launcher`/`env_key_available` from `resolve_live_launcher` and the
   `create_observer_server` wiring; drop `--api-key-env` from
   `run_observer_server.build_arg_parser`. Live launches then require a
   client-supplied credential for **every** provider, deepseek included —
   `missing_api_key` 403 semantics already exist and become uniform.
2. **Scope: observer server only.** The standalone CLI runners
   (`run_deepseek_*_game.py`, `scripts/dev/run_deepseek_live_smoke.py`, ablation
   harness `--api-key-env`) keep reading env keys — they are user-run terminal tools;
   env is the right interface there (see the fake-default/live-gate ADR:
   user-run / agent-offline-review).
3. **Hard removal, no deprecation period**: this is a local dev tool with one known
   operator; a warning release adds dual-path maintenance for nothing.
4. **Test fallout (update, don't delete coverage):**
   - `test_deepseek_env_backcompat_does_not_leak_to_other_providers` → replaced by a
     test asserting deepseek **without** a client credential is `403 missing_api_key`
     (env var set or not).
   - `test_live_mixed_models_env_only_requires_client_key` → generalizes to "env vars
     never satisfy any provider".
   - Observer-server live tests that seed an env launcher switch to seeding the
     credential store (the per-seat creds tests already show the pattern).
5. **Precondition checklist (gate before the plan executes):**
   - [ ] T17 live track closed (see header).
   - [ ] Owner confirms their live workflow launches via the provider-center /
         credentials flow and no longer relies on `DEEPSEEK_API_KEY` for the observer
         server (grep `launch-theater.py` and any personal scripts for `--api-key-env`
         / env-key reliance at plan time).
6. **Doc fallout:** update the back-compat-exception paragraph in
   `docs/adr/2026-06-11-byo-key-security-invariants.md` (mark retired), README live
   instructions, and `docs/PROJECT_MAP.md` SYS-B3/P2-B "剩 B5 收尾" lines.

## Acceptance sketch (for the future plan, not this doc)

- Full suite green; no new test reads a real key.
- A fake run's settlement bundle is byte-identical except for the new additive fields
  (or regenerated fixtures if a version bump proves necessary).
- Observer server started with `DEEPSEEK_API_KEY` set but no client credential refuses
  live launch with `403 missing_api_key` and creates no run dir.
