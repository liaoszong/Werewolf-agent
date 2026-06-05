# Grill: P2-A-2 live smoke scope + BYO-key architecture direction
Date: 2026-06-05

## Intent
Pin down what the P2-A-2 "real DeepSeek live smoke" actually proves, so it stays a
bounded integration check and does not silently balloon into gameplay-quality tuning
or get faked. Mid-grill, a much larger product decision surfaced and was deliberately
made explicit: the shipping product will use user-supplied (BYO) API keys.

## Constraints
- P2-A-2 is a **live integration smoke, not a gameplay-quality tuning slice**.
- The smoke must be **provably live**, not fake/fallback relabeled.
- Must not touch the user-key / BYO architecture (that is P2-B).
- `fake-deterministic` stays the **unconditional no-key default** (survives BYO-key).

## Key decisions
- **Decision: P2-A-2 success = "live pipeline runs + content floor doesn't collapse", NOT "content looks good".**
  Reason: no UI yet, just de-risking the live path; chasing content quality is a prompt-tuning
  rabbit hole. Alternative rejected: make the smoke a product-hypothesis "is it watchable" test.
- **Decision: prompt visibility safety is a HARD correctness gate ("feed-leak" = blocking bug);
  model "mouth-leak" (hallucinated private knowledge) is only a soft content warning.**
  Reason: text-enrichment renders events into the prompt; rendering a hidden event into a
  non-wolf prompt leaks info and violates the project's visibility-trust invariant (G2c).
  Mechanism: text-enrichment happens ENGINE-SIDE from `_build_obs`'s already role-filtered
  `public_event_ids + private_event_ids`; the provider receives pre-filtered `observation_text`
  only and NEVER the global event store. Machine-checkable: for each seat, rendered prompt's
  source_event_ids ⊆ obs.public+private; plus content-leak assertions (prefer event metadata
  `source_event_id`/`visibility_scope` over brittle keyword scans).
- **Decision: "finished" ≠ "passed" — the smoke passes only if MOST turns were live-driven, not fallback-driven.**
  Reason: deterministic fallback can carry a game to completion even if every live call timed out,
  which would validate nothing. Gate: `max_requests_per_game = 64`, `live_success_rate ≥ 0.80`,
  `live_success_actions ≥ 20` for a normal 6-seat run (absolute floor guards against small-sample
  inflation), `budget_exhausted` = hard fail. Fallback is allowed to RESCUE the game but must be
  counted/exposed (provider_result_kind taxonomy), never hide live failure. Early-rules-termination
  with fewer calls is OK only if explained in the review packet. Alternative rejected: pass on
  "game completed" alone; keep max_requests=32 (too low — would fail on budget, not on real bugs).
- **Decision: I (agent) run the smoke one-stop, reusing the G3-3 honesty chain.**
  Reason: user controls the balance (~¥5, no real financial risk), faster. Honesty proof is
  machine-checkable in artifacts, not my word: `source_label=="[DeepSeek API output]"`, real model
  in `prompt-manifest.json` (G3-3 `manifest_model_honest`), `token_usage` fields > 0 (fake = 0),
  plus the live-success stats. Alternative considered: user runs it via `!` so the key never
  touches the agent — rejected for speed; honesty is provable from artifacts regardless.
- **Decision (P2-B architecture direction, NOW recorded in the map): "Client-owned secret, server-executed provider call."**
  The shipping product moves from dev/server-owned credentials to **BYO local user credentials**.
  The Qt client may collect/store/select user-owned keys locally and pick models via dropdown
  (auto-fetched per provider), but provider network calls remain SERVER-SIDE via the local Python
  observer/server. The client NEVER calls vendor APIs directly. Reason: multi-model BYO-key is a
  necessary, standard pattern (can't connect AI without a key; can't self-fund users' play);
  routing via local server preserves the "Python owns engine/provider, Qt is config+spectator
  client" architecture (so G3-1/2 work evolves, is not torn down). Alternative rejected:
  (i) client calls vendors directly — would make Qt a second provider runtime, fight the observer
  architecture, and force per-vendor auth/networking into C++.

## Surfaced assumptions
- The old "client never touches a key at all" invariant is being deliberately relaxed to
  "client never HARDCODES a key in source / no key in shared env / no key in logs". The
  secret-scan contract (no `sk-`/`Authorization` in `.cpp/.qml`) still holds; what changes is
  that an END USER may store their OWN key in local client config.
- A revised 3-layer invariant set was agreed (hard / architecture / storage) — see PROJECT_MAP.
- BYO-key does not gate gameplay: fake-deterministic remains the no-key default; a key only
  UNLOCKS the live provider.

## Out of scope (for P2-A-2)
- User key storage, UI key entry, model-dropdown UX, multi-vendor config — all belong to P2-B.
- Content/gameplay quality tuning (observation-summary compression, per-role prompts, forced
  speech structure, two-round debate, temperature, failure-sample comparison) — a later
  "readable play quality" slice (P2-A-3 / pre-P2-C).
- P2-A-2 stays a dev live smoke using server-side/dev credentials only.
