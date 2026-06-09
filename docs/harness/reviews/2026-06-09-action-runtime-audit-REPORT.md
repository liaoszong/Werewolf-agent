# Action Runtime — Independent Audit Report

> **Auditor:** independent, read-only Claude instance, per the charter at
> `docs/harness/reviews/2026-06-09-action-runtime-audit-charter.md`.
> **Frozen state audited:** commit `69dd9bb` (merge of swaps #1+#2). Verified the
> working-tree `src/` & `tests/` are byte-identical to it — the only later commit
> `baec04e` is docs-only (`git diff 69dd9bb HEAD -- src/ tests/` is empty).
> **Method — a differential oracle.** The pre-swap engine at `5ace7bc` (inline night
> settlement + inline wolf/seer/vote validation; all *other* modules identical to today —
> confirmed because `git diff --stat 5ace7bc 69dd9bb -- src/` touches only
> `emergent_engine.py`) is run side-by-side with the current engine on the same
> script+seed; **any non-empty byte diff** of `game_log` / `decision_log` /
> `consensus_log` / `failure_audit` is a reachable behavior divergence (= BLOCKING).
> Executed by an 11-auditor / 42-agent workflow (4 differential behavior-breakers,
> 5 static auditors, 2 fresh independent breakers), with **every** concrete finding
> adversarially re-verified by an independent agent (**30 confirmed, 0 refuted, 0
> BLOCKING**). The orchestrator independently corroborated the three headline
> conclusions before signing off: **72/72** adversarial fallback/tie/invalid
> differential runs (× 12 seeds) byte-identical; the parity harness **proven circular**
> by monkeypatching a poison-dropping bug into the settler (test stays green); the
> orphan inventory confirmed by `grep` (only `from_legacy` is consumed in `src/`
> outside the module). Repro harness lives at `.tmp/audit/diff_harness.py` (gitignored
> scratch, removed after the audit).

VERDICT: **SOLID_WITH_FIXES**

No confirmed reachable old-vs-new divergence exists — all four swaps (night settlement → `JointSettler`; wolf/seer/vote legality → `_action_legal`) are byte-equivalent to the pre-swap oracle (5ace7bc) on every adversarial input tried by 11 independent auditors. The "_WITH_FIXES" is for a confirmed test-quality defect (the parity harness is circular and cannot catch a settler regression) and a cluster of confirmed Phase-3 footguns that are cheaper to fix before the next swap builds on this foundation.

---

## BLOCKING — must fix before remaining Phase 3 builds on this

**None.** The two production swaps are byte-identical to the pre-swap engine on every adversarial input tried. Across the cohort that is **~715 differential games + thousands of unit-verdict comparisons**, every one byte-IDENTICAL on `game_log`/`decision_log`/`consensus_log`/`failure_audit` (and on `provider_turns`/`status`/`end_condition` where extended). Input families covered, all CLEAN:

- **Validation swaps** (wolf `alive_non_wolf` @554, seer `exclude_self` @656, vote `exclude_self` @814): wolf-kills-wolf/teammate/self, seer-checks-self, voter-votes-self, cross-role actions (wolf returns `seer_check`), dead/unknown/`'none'`/`''`/`None`/multi targets, single-leader vs tie tallies, all-voters-invalid. Exhaustive `(role × action × target)` unit-verdict comparison vs OLD inline booleans = **0 mismatches** (A1-8, X1, X2-2). RNG-stream preservation proven by a counting `Random`: OLD and NEW consume identical draw counts (0/0, 7/7, 12/12) — `_action_legal` adds/removes **zero** RNG draws (A1-3).
- **Night-settlement swap** (`JointSettler.resolve_night` @892-897): exhaustive 320-combo grid (A4-3) and 40-combo grid (A1-7) vs OLD inline formula = **0 mismatches**, including poison==victim dedup, save-only, two-death ordering, poison-of-wolf. `roles={}` at the call site is provably harmless — the settler never reads `state.roles` (verified by a trap-dict probe in B5-7).
- **Multi-round / seed sweeps**: fallback-heavy scripts across seeds 0–49, mixed valid/invalid trajectories, 12-round long games, 400-game + 300-game fuzzers — all IDENTICAL (X1-1, X2-3, X2-4, A1-4).
- **Unusual boards**: 0-wolf, at-parity, 1v1, all-wolf, solo-villager all run byte-identically; multi-seer/multi-witch fail-loud IDENTICALLY in OLD and NEW (the R-30 guard predates the swap) (A4-1, A4-2).
- **Witch path** (664-752): byte-untouched vs OLD (full `difflib` diff confirms `_resolve_witch` is absent from the changeset), so it cannot diverge by construction (A3-2).

*Considered and refuted as BLOCKING:* B5-1 was filed as BLOCKING ("parity harness is circular, silently drops every poison death and stays green"). The verifier **ADJUSTED it to NONBLOCKING** — the circularity is real (see ROBUSTNESS GAPS / ROT) but it is a test-quality false-assurance issue, **not** a runtime divergence (diff_harness reports IDENTICAL on both canonical scripts), and the same drop-poison regression IS caught by the genuine `tests/test_action_runtime_settler.py` unit tests (4 failures under mutation, B5-4). No auditor found a reachable behavior divergence; `refuted_findings` is empty because nothing was filed claiming one survived.

---

## ROBUSTNESS GAPS — untested/under-tested paths + risky inputs

1. **`_action_legal` raises `KeyError` on an actor role OR phase unknown to rules_v1; OLD never raised.** `registry.allowed_actions` does unguarded `self._by_role[role]` (registry.py:25) and `_PHASE_TRIGGER[phase]` (registry.py:8). Confirmed via direct call: `eng._action_legal('p4','hunter','day_vote',…)` → `KeyError 'hunter'`; phase `'dusk'` → `KeyError 'dusk'`. OLD's inline checks only compared the action string + alive + not-self/not-wolf and never looked up a role, so the swap introduced a new hard-fail surface. **Currently unreachable**: `ProviderAgent.decide` gates on `ALLOWED_ACTIONS_BY_ROLE_PHASE.get((role,phase),[])` → `[]` for unknown roles → rejected upstream as `invalid_action` before `_action_legal` runs; full hunter/guard boards complete byte-IDENTICAL. The gate holds **only by coincidence** that `rules_v1` roles and the static map roles coincide exactly. **Proven lockstep-drift hazard** (X1-2 verifier): monkeypatching `ALLOWED_ACTIONS_BY_ROLE_PHASE[('hunter','day')]=['player_vote']` *without* adding hunter to `rules_v1()` makes OLD run to completion while NEW crashes mid-game with `KeyError 'hunter'`. **Fix:** make `allowed_actions`/`abilities_for` return `[]` for unknown role/phase (`self._by_role.get(...)` / `_PHASE_TRIGGER.get(...)`) so it degrades to a clean `invalid_action` (matching OLD's never-raise contract), OR keep the two role sets in lockstep via a single source. Load-bearing at the hunter v1.1 swap. (A4-4, B2-1, X1-2.)

2. **`validate_in_state` raises `KeyError ''` when an ability has `target_rule=''` AND `arity != none`.** validator.py:52 does `TARGET_RULES[ability.target_rule]` after the `ARITY_NONE` early-return. A hand-built ruleset with `rule='' + ARITY_ONE` raised `KeyError ''`. Unreachable in rules_v1 (the only empty-rule ability is `witch_pass`, which is `ARITY_NONE` and short-circuits). Notable internal asymmetry: the sibling `registry.legal_targets` (registry.py:49-52) **already guards** this exact lookup (`if not ability.target_rule: return []`), so the codebase has the pattern in one place but not the other. **Fix:** mirror the guard — `pred = TARGET_RULES.get(ability.target_rule)`. A future-ruleset data-entry footgun for hunter v1.1 / guard v1.5. (B2-2.)

3. **`registry.shown_targets` ignores `action_id` entirely** — returns `sorted(state.alive)` for ANY string, including completely made-up ids, while `legal_targets`/`ability` correctly raise. Benign today (no swap calls `shown_targets`; the prompt's broad target list is sourced directly from `observation.alive_players`, not the registry — B1-5). Flag only as an abstraction sharp-edge: if it is ever wired into prompt rendering, a typo silently renders the broad list. (A4-5.)

4. **Vote-validator's `exclude_self` is reachable but has no engine-level test.** The only validator-discriminated vote-reject path is a self-vote (everything dead/unknown is rejected upstream by `ProviderAgent.decide:333` before `_action_legal`). The existing `RobustnessTests.test_bad_vote_target_falls_back` uses `p99` (out of alive set) → caught upstream, **not** by the swapped validator (proven: mutating `validate_in_state` to always-accept leaves `bad_vote` green but flips `wolf_kills_teammate`/`seer_checks_self` to caught). A voter-votes-self test would be a real guard; none exists. The path itself is byte-equivalent OLD vs NEW. **Fix:** add an engine test where an alive voter votes itself and assert `invalid_action` + seeded fallback. (B5-3.)

5. **Determinism test catches only non-determinism, never a logic error.** `test_emergent_engine.py:84-94` runs the same script+seed twice and compares — a deterministic-but-wrong settler corrupts both halves identically and stays green (proven: a poison-dropping settler that changes `player_died` and adds a round still passes). It is a valid determinism canary, not a swap-correctness guard. **Fix:** label it as a canary; do not count it toward parity. (B5-2.)

6. **TriggerSystem determinism for seat-index ties inherits handler return order.** `queue.sort(key=_seat_index)` is stable; two new deaths that tie (both pids absent from `seat_order` → both key `len(seat)`) preserve the handler's returned order. Unreachable today (real seats have unique indices; no triggers registered; TriggerSystem is unwired). Encode before multi-victim handlers (lovers/wolf-king) ship: add `(seat_index, pid)` tiebreaker, one line. (B3-7.)

7. **TriggerSystem ignores `state.alive`** — `resolve()` will process a returned pid that is already dead (proven: `alive={p1,p3}`, handler returns `['p2']` → result `['p1','p2']`), whereas `JointSettler` gates every death on `in state.alive`. Asymmetry/footgun for a buggy reactive handler producing a phantom death row. Unwired today. **Fix:** add `and d in state.alive` to the line-49 enqueue comprehension to mirror the settler. (B3-8.)

---

## ROT RISKS — duplicate sources of truth / half-swaps / orphaned code

1. **[temporary] Dual source #1: `registry.allowed_actions` vs `provider_agent.ALLOWED_ACTIONS_BY_ROLE_PHASE` — both live, weak parity guard.** The static map (provider_agent.py:19-27) drives prompt BYTES (`llm_providers.py:88` join + `:90` first-element example) and provider rejection (:307); the registry drives engine `_action_legal`. The only guard, `test_action_runtime_registry.py:96`, has confirmed blind spots: (a) it iterates only static-map keys, so a registry-only `(role,phase)` addition is never checked; (b) it `sort()`s both sides, hiding order drift even though the prompt is order-sensitive. *(Verifier ADJUSTED one sub-claim: the `witch_pass` filter is a hardcoded `a != 'witch_pass'`, so a **second** no-target action would be caught, not silently dropped — the mechanism observation stands, the stated consequence was overstated in direction.)* Maps are byte-aligned today → no current divergence. Phase 3 collapses this to one source; **until then, harden the test to assert full bidirectional, order-aware map equality.** (B1-1.)

2. **[temporary] Dual source #2: inline witch legality (engine 726-739) vs validator/registry witch abilities — and the validator path CANNOT express potion exhaustion.** Witch keeps its own inline validation (gating on `save_used`/`poison_used`); `RuntimeState` carries no potion field. Inline and validator AGREE on all single-round save/poison cases, BUT a 2nd potion in a later round is **rejected by inline, accepted by `validate_in_state`** (confirmed `DIVERGE=True`). No current bug (witch is inline in both engines). **Trap for the Phase-3 "delete `_resolve_witch`" step:** extend `RuntimeState`/intent model with one-shot semantics FIRST and add a multi-round second-potion parity test before routing witch through the validator. (B1-2, B4-3.)

3. **[temporary, latent] Half-swap footgun: `night_victim` / `is_night_victim` / witch_save legality are built but dead.** `_runtime_state()` is called once (engine:464) with no argument → `night_victim` always `None`; the witch never routes through `_action_legal`. So `abilities.py:24-25 _is_night_victim` and the `witch_save` registry row are correct-in-isolation but dead and **mutually inconsistent with the inline contract**. Confirmed: `validate_in_state(witch_save p5, night_victim=None)` → `ok=False invalid_target`; with `night_victim='p5'` → `ok=True`. A future engineer naively reusing `_action_legal` for the witch **MUST** thread the live victim into `_runtime_state(night_victim=victim)` or witch_save rejects every target. (A1-9, A3-4.)

4. **[permanent] Dual source #3: `JointSettler` reproduces inline night-death logic; v1.5 guard/奶穿 is half-data/half-hardcode.** The OLD inline settlement block IS genuinely deleted (replaced by the delegate @892-897) — not undeleted duplication. The lingering rot: `night_settlement_rule('guard+save_same_target')` is consulted at exactly one site (settler.py:50) for exactly one key, while `save_cancels_kill`/`poison_stacks` exist only as words in the docstring with no table entry — their semantics are structurally hardcoded. A future v1.5 variant flipping a rule must edit both the table AND settler.py. The guard branch itself is correct (proven: guard cancels kill; guard+save → 奶穿 death; guard non-victim no-op) but fully **dead in rules_v1** (no guard role, call site never sets `guard_target`). (A3-3, B1-3.)

5. **[temporary, intentional] Orphan scaffolding (~104 lines): `TriggerSystem`, `registry.shown_targets`/`legal_targets`, `NightResult` (type), `RuntimeState.night_victim`, `ARITY_MANY`, `TARGET_RULES['alive_only']`, `NightIntents.guard_target`, `BoardRuleset.death_order_key`, `RoleDefinition.team`, `AbilityDefinition.visibility`, `ValidationResult 'needs_state'`, `ActionEnvelope.params`/`.target`.** Confirmed by grep + a live trace-hook: across both canonical games `validate_in_state` fired 19×, `resolve_night` 3×, while `shown_targets`/`legal_targets`/`TriggerSystem.resolve` fired **0×**. All documented Phase-3 scaffolding per the spec/plan — not accidental dead code. *(External `.team`/`.visibility` hits are on unrelated GameLog `Player`/`Event` objects, verified — not these symbols.)* `RuntimeState.is_wolf` is correctly **excluded** — it is LIVE via the `alive_non_wolf` wolf-kill predicate. Risk: `alive_only`, `team`, `visibility`, `needs_state`, `params` have no test asserting their eventual consumer contract — add Phase-3 acceptance tests as each goes live so the scaffolding can't drift from intent. (B1-4, X1-4, B3-9.)

6. **[permanent] `ruleset.death_order_key = ('phase_priority','cause_priority','seat_index')` advertises ordering keys `TriggerSystem` never reads.** `TriggerSystem.__init__(triggers, seat_order)` takes no ruleset; the only ordering key is `seat_index`. The first two components are aspirational metadata — two deaths from different causes (poison + hunter-shot) will be ordered by seat, possibly not the intended adjudication order. **Fix:** when wiring real triggers, pass the ruleset + a cause-tag and build the sort key from all three, OR trim `death_order_key` to `('seat_index',)` until then. (B3-6.)

---

## FOUNDATION ASSESSMENT — is this a good base for remaining Phase 3?

The settler/validator/registry abstractions are **behaviorally sound and the baseline is locked byte-for-byte** — a strong base. But four concrete contract gaps are confirmed and are *materially cheaper to fix now* than after `_resolve_*` is deleted and a hunter is written against the current shapes:

1. **`day` → `day_vote` phase map is load-bearing, not cosmetic (fix NOW).** The engine passes literal phase `'day'` to `provider_agent.decide` for votes, but `registry._PHASE_TRIGGER` only knows `'night'`/`'day_vote'`. A naive `registry.allowed_actions(role, phase)` substitution in `decide()` raises `KeyError('day')` — which is **not** a `ProviderActionError`, so it bypasses the `except ProviderActionError` at engine:501 and is swallowed by the bare `except Exception` at :506 → every day vote silently degrades to a seeded `ERROR_FALLBACK` (a **silent leaderboard regression**, not a loud crash). **Fix:** `rt_phase = {'day':'day_vote'}.get(phase, phase)` immediately before the registry call in `decide()` (and the witch inline site @691); keep the external `'day'` string for log rows; add a unit test that `registry.allowed_actions('werewolf','day')==['player_vote']` via the map. (B4-1.)

2. **`DeathTrigger = (RuntimeState, str) -> list[str]` cannot host a model-driven hunter shot (decide the contract NOW).** The handler gets only a frozen `RuntimeState` + the dead pid — no agent/provider/budget/emitter/decision-recorder/rng. The spec requires the hunter's shot to be a **model decision** with a provider_turn + decision row + budget charge + seeded fallback; a state-only handler can only do a deterministic pick (it can't even do a *seeded* pick — no rng). The spec's open-question #2 explicitly defers this resolver contract. **Fix before step 3:** inject a narrow `TriggerContext`/`ShotDecider` port (`decide/charge/emit/record_decision/rng`) keeping `RuntimeState` read-only, OR a two-pass "pending shot" design; unit-test it with a chain-death fixture (wolf→lover→hunter→wolf-king). One `resolve()` call site + one alias to change now vs re-plumbing every handler later. (B3-5, B4-2.)

3. **No one-shot-potion state in the runtime (design the orchestrator slot NOW).** Deleting `_resolve_witch` means the orchestrator must carry `save_used`/`poison_used` itself — `RuntimeState` and `validate_in_state` have no notion of it (the validator accepts a 2nd save/poison; confirmed in ROT #2). The target-axis rejections (target!=victim, victim-None, target==self) ARE covered by `target_rule`; only exhaustion is missing. Keep the validator stateless-per-turn and let the orchestrator veto a spent potion before recording the intent. (B4-3.)

4. **Add a role as DATA only after landing a versioned RulesVariant.** `registry._by_role[role]` bare-`KeyError`s for any role not in `rules_v1`. The "add role = add data" goal requires the hunter `RoleDefinition` + `hunter_shoot`/`hunter_pass` abilities to land in a **new `rules_v1_1()` that bumps `rules_version`** (cross-version games aren't comparable), with the registry constructed from that variant — not a silent edit to `rules_v1`. `TARGET_RULES` reuse of `exclude_self` for `hunter_shoot` is data-only and clean. (B4-7.)

**Pre-deletion parity-harness checklist (B4-5, confirmed by reading the resolver bodies):** before deleting `_resolve_*`, the parity test must assert — not just `deaths` — the full ledger the new `runtime.py` must reproduce: `provider_turn` dicts + `_downgrade_turn` semantics (INVALID_FALLBACK nulls `source_label`/`token_usage`); the exact `decision_type` taxonomy (`team_coordinated`@589, `retaliatory`@746, `inference_based`@742/826, `witch_pass=FALLBACK`@750); `_record_failure` kind strings; the `consensus_entry` shape (coordinator=`wolves[0]`, `consensus` vs `coordinator_tie_break`); seeded R-29 RNG draw order (`self._rng`, NOT seat 0); votes emit `phase='day'` (not `'day_vote'`); `witch_pass` target serializes to literal `'none'` (not `None`). The current spec §7.3 Layer-1 list omits decision_type/failure-kind/provider_turn — add them explicitly.

**Decoupling that helps you:** `game_engine.py` imports nothing from `provider_agent` and never references `ALLOWED_ACTIONS_BY_ROLE_PHASE` (the dependency is the other direction). Registry-driving `provider_agent.decide()` **cannot** break the scripted gold-game path. (B4-6.)

---

## NON-BLOCKING — quality / naming / simplification

1. **Parity harness is circular and its docstring overpromises (test quality).** `test_action_runtime_parity.py` docstring claims "old engine = parity oracle" but never instantiates 5ace7bc — it reconstructs intents from the NEW engine's own `game_log` (lines 34-62) and re-runs a fresh `JointSettler` (line 69) against them, i.e. compares the settler to itself. **Proven**: a settler monkeypatched to drop every poison death leaves the parity test green while the game's `player_died` materially changes. The settler IS still guarded by the genuine direct unit tests, so this is redundant/misleading assurance, not the sole defense. **Fix:** pin the real OLD pre-swap engine as the oracle (productize `diff_harness.py`) and assert `NEW.player_died == OLD.player_died`, OR delete the circular test and lean on the settler unit tests. (B5-1, B5-6, X1-5, X2-6.)

2. **No committed OLD-vs-NEW differential test for the validation swaps.** The merged suite covers the settler on 2 canonical scripts and the validator only as isolated unit tests of `validate_in_state` — it never routes through `_action_legal` nor compares to OLD. The "byte-identical" guarantee is asserted in a commit message, not regression-guarded. Productizing the audit's `diff_harness` (wolf/seer/vote legality + an all-invalid consensus round + a seed sweep) would lock it in. (X1-5, X2-6.)

3. **`registry` parity-test method name `test_allowed_actions_match_static_map_exactly` overstates.** It filters `witch_pass`, so it does not pin `witch_pass`'s presence/position; the static map's `('witch','night')` is `[save,poison]` while the registry returns `[save,poison,pass]`. Unconsumed today (witch prompt uses the literal `WITCH_ACTIONS` tuple, which happily matches registry order — B4-4). **Fix:** add a dedicated assertion `registry.allowed_actions('witch','night') == ['witch_save','witch_poison','witch_pass']`. (B5-5.)

4. **`roles={}` at the settler call site (engine:895) is a behavior-neutral footgun.** Harmless today (settler ignores roles, proven). Not a structural limitation — `_runtime_state()` already builds fully-populated roles; swapping `RuntimeState(alive=…, roles={})` for `self._runtime_state()` at :895 is a one-token change that removes the trap before any role-sensitive night rule lands. (B5-7, B2-3.)

5. **Vote-swap legality is effectively a single `target != voter` test for rules_v1** — `ProviderAgent.decide` pre-gates action-in-`['player_vote']` and target-in-alive, so the validator's `alive` clause in `exclude_self` is never the discriminator on the vote path. Fine and intentional; add differential coverage only if a future RulesVariant adjudicates dead-target votes server-side. (A2-5.)

---

## CONFIDENCE — high/med/low

**Overall: HIGH** for the verdict (no BLOCKING divergence; SOLID_WITH_FIXES).

**Verified by actually running** (highest confidence):
- Zero old-vs-new divergence: ~715 differential games + exhaustive `(role×action×target)` unit-verdict comparisons (0 mismatches) across 11 auditors, every one independently re-run by a verifier. The settler grids (320-combo, 40-combo) and RNG-draw-count parity (0/0, 7/7, 12/12) were executed. *(Orchestrator corroboration: an independent 6-script × 12-seed = 72-run differential sweep over fallback/tie/invalid scripts — all byte-IDENTICAL.)*
- The `KeyError` surfaces (A4-4/B2-1/B2-2/B4-1/B4-7/X1-2): reproduced by direct calls capturing the actual exceptions; the lockstep-drift hazard (X1-2) reproduced by monkeypatch making OLD complete while NEW crashes.
- The circular parity test (B5-1): reproduced by monkeypatching the production settler to drop poison and observing the test stay green while the game changed; the OLD-oracle alternative caught it. *(Orchestrator independently reproduced this exact result with a poison-dropping `JointSettler.resolve_night` monkeypatch.)*
- The witch potion-exhaustion divergence in the validator (B1-2/B4-3) and witch_save-with-None-victim rejection (A3-4): reproduced at the validator level; confirmed no current engine divergence via diff_harness.
- TriggerSystem termination/dedup/ordering, ignores-alive, tie-order, and unwired-in-engine: reproduced by probes + grep.
- Working tree == frozen 69dd9bb for src/ and tests/ (`git diff --stat` empty); orphan inventory (`grep`: only `from_legacy` consumed in `src/` outside the module) — both re-confirmed by the orchestrator this session.

**Reasoned about / read-only (medium confidence)**, not independently re-executed:
- The full pre-deletion parity checklist (B4-5) is reasoned from reading the `_resolve_*` bodies + grep of decision-type/failure-kind constants; the *baseline* was run (IDENTICAL), but the future orchestrator's reproduction of each field is a design assertion, not yet testable.
- The hunter `DeathTrigger` contract gaps (B3-5/B4-2) rest on the spec's stated intent that the hunter shot is model-driven (read from the spec/plan), combined with the verified `(RuntimeState, str)` signature.

**One residual uncertainty (low impact):** several latent `KeyError` paths and dead scaffolding are "unreachable today" only because `ProviderAgent.decide`'s gate and `rules_v1`'s role set happen to coincide. That coincidence is the load-bearing shield — it is not asserted by any test, so a future edit could silently make these reachable. The FOUNDATION fixes above are precisely to remove that reliance before Phase 3.
