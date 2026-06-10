# ADR: Action Runtime orchestrator (②a) — registry-driven dispatch, byte-identical

Date: 2026-06-09 · Status: Accepted

## Decision
- wolf/seer/vote resolution moved to pure `action_runtime/turn.py` units behind a `DecisionWindow`
  boundary; `EmergentGameEngine` stays the single owner of all byte-producing state and enacts the
  units' decisions at the legacy call sites (registry-driven dispatch via `_RESOLVERS` /
  `NIGHT_DISPATCH_ORDER`). Output is byte-identical (gated by a real OLD-oracle differential).
- Parity standard = byte-identical. The spec §7.2/§9-Q1 runtime_v2 RNG-reorder re-baseline is
  DEFERRED to a future behavior phase (would forfeit the byte oracle).
- `TriggerSystem` (triggers.py) stays ORPHAN: `_trigger_on_death` is already data-driven via
  `registry.on_death_abilities`, and `DeathTrigger=(RuntimeState,str)->list[str]` cannot host the
  model-driven hunter shot (no provider/budget/rng). Wiring it is a later behavior-phase PR with a
  `TriggerContext` port (audit B3-5/B4-2). `ARITY_MANY` / `NightIntents.guard_target` /
  `death_order_key` remain intentional forward-scaffolding.
- The WITCH (+ speech, hunter) were DEFERRED from ②a. The witch's migration (②b) is BLOCKED on a
  `RuntimeState` one-shot potion capability ledger + threading the night victim into
  `_runtime_state()` (audit ROT#2/ROT#3); guarded by `test_witch_potion_one_shot_sentinel.py`.

## Why in-engine (not a standalone module + EnginePort)
An EnginePort facade would route every byte-producer (`_emit` bumps `_seq` + flushes; `_decision`
bumps `_d_counter`; `_rng`) through ~15 methods purely to relocate control flow — a re-threading
surface that adds byte-risk for no extensibility the in-engine dispatch lacks.

## Net (what replaced the swap-time scaffolding)
- The OLD-oracle differential gate + its frozen engine copy were deleted once parity was proven.
- Permanent regression net: `tests/test_emergent_ledger_golden.py` (full-ledger golden for the
  canonical scripts), `tests/test_rng_draw_order.py` (draw-count golden), the witch one-shot
  sentinels, and the full suite. Shared scripts live in `tests/parity_scripts.py`.
