# P2-A Invariant Safety Net — Design Spec

> Status: **DESIGN — review-applied, PLAN-READY** · Date: 2026-06-09 (review 2026-06-10) · Author: brainstorming session (liaoszong + Claude)
> **2026-06-10 independent review applied** (read-only fact-check vs `main==dceac69`, cross-checked against the ②a plan). Fixed: BLOCKING-1 I5 key → `(request_id, phase)`; BLOCKING-2 B4 → silent no-op (user ruling); M-1 `event_visible_in_projection` returns `(bool, reason)` tuple; M-2 I4a is in-memory-only; M-3 B1 anchor = `_provider_action`+3 sites (not `_resolve_*`); M-4 B4 adds day-vote commit site; LOW: I3 per-`(actor, capability)`, I4b in-memory `role_source`. Load-bearing I4b dual-implementation anti-circularity **verified genuine**. Line refs ≥`:545` shift under ②a — re-locate at wiring time (see review's post-②a list).
> Companion context: `docs/superpowers/specs/2026-06-09-agent-action-runtime-architecture-design.md` (the runtime this net protects), `historical harness review 2026-06-09-action-runtime-audit-REPORT.md` (proves the gap), `docs/PROJECT_MAP.md` (P2-A is the current engine core).
> Does **not** modify: `CapabilityLedger`, `EffectQueue`/`TriggerSystem`, `DecisionWindow`, `NightPlan`, or any enhancement-layer code. This spec builds the **net those four rewrites land on**; it does not build them.

---

## 1. Motivation

### 1.1 The gap byte-parity leaves

The Action Runtime rewrite is guarded today by **byte-identity against the pre-swap engine**. The independent audit (`...-audit-REPORT.md`) proved two hard limits of that net:

- It is **circular as a settler guard** (B5-1): a poison-dropping bug monkeypatched into the settler leaves the in-repo parity harness green.
- The determinism canary (`test_emergent_engine.py:84-94`, audit B5-2 / robustness #5) catches only **non-determinism** — a deterministic-but-wrong settler corrupts both halves identically and stays green.
- Most importantly: byte-identity only proves **the OLD 4-role path did not change**. It says **nothing** about whether the NEW abstraction is *semantically* correct. Every "add role = add data" (hunter shipped; guard/wolf-king/lovers next) is currently **flying blind** — no test asserts "this new role did not break a rule."

The four upcoming rewrites — `CapabilityLedger`, `EffectQueue`, `DecisionWindow`, `NightPlan` — are large and will each touch death resolution, capability consumption, prompt construction, and night ordering. Byte-parity cannot net any of them, because they are *new behavior*, not refactors of the 4-role path.

### 1.2 What this is

A **semantic oracle**: a set of rule invariants checked against the engine's artifacts, **independent of byte parity and independent of any old output**. Three layers:

1. **Offline invariant checker** — broad, run-after, zero byte impact.
2. **Runtime fail-closed guards** — only at unrecoverable boundaries.
3. **Deterministic fuzz** — stdlib-random, fixed-seed scenario generation that feeds both.

When this net exists, the four rewrites are no longer blind: a regression that byte-parity cannot see (a double-committed death, an over-consumed potion, a leaked prompt event, a double-settled decision) **turns a checker or a guard red**.

### 1.3 What this is NOT (scope fence)

- **Not** the `CapabilityLedger` (that is swap ②b). This net's capability invariant (I3/§4) reconstructs consumption from **events** today; it gains a ledger cross-check *when the ledger lands*.
- **Not** the `EffectQueue` / `DecisionWindow` / `NightPlan`. The net **specifies the commit-layer contract** those will have to satisfy (§7), but builds none of them.
- **Not** the enhancement layer. The net **guards the seam** (per-seat memory cannot become a covert leak channel — caught by I4b/§9), but implements no memory/persona/strategy.
- **Not** a byte oracle. Acceptance criterion 4 (§10) forbids using old output as ground truth.

---

## 2. Locked design principles

Converged across the brainstorming dialogue. These are invariants for the implementation, not suggestions.

1. **Semantic oracle, never a parity oracle.** Ground truth is the *rules*, derived fresh — never a stored byte stream or a prior run.
2. **Independent witnesses (anti-circularity).** A guard must not be computed from the same code path that produced the thing it checks. The visibility check (I4b/B1) is the load-bearing case: it derives "what seat X may see" from the **recorded event `visibility` tag + role membership** (via `observer_visibility.event_visible_in_projection`, a *different* code path from the engine's `_build_obs`), **never** by re-running the engine's own observation builder. Re-using `_build_obs` to check `_build_obs` is the parity-harness circularity reborn (§9).
3. **DeathCandidate vs DeathCommitted.** Multiple effects targeting one player is **legal** (奶穿 / poison-stack / lovers / hunter cascade). The error is a second **commit**. The queue accepts candidates; commit is **idempotent**; trigger expansion runs off **committed** deaths only (§7).
4. **Three layers, escalate sparingly.** Offline checker is the broad base. Runtime fail-closed only where the damage is **unrecoverable** (a leaked prompt already sent to a model; a dirty state already written to the log). Exactly the boundaries in §5 — no more.
5. **No new dependency.** stdlib `random` + a fixed seed bank. No Hypothesis (the project's stdlib / fake-deterministic / auditable discipline).
6. **Provider-agnostic, offline-checkable.** Fake and live games run the same engine → same artifacts. The checker reads **persisted artifacts** and needs **no API key** (criterion 2).
7. **Additive and orthogonal.** The offline checker and fuzz are new modules that read outputs. The two runtime guards (B1, B4) are fail-closed assertions at boundaries that must be **parity-neutral on the happy path** (they only ever fire on a real violation, which is by definition not a happy path). This net can be built **in parallel** with swap ②a.

---

## 3. Architecture — the three layers

```
                         ┌─────────────────────────────────────────────┐
   fake game ─┐          │ Level 1: offline invariant checker          │
   live game ─┼─ engine ─┼─▶ reads game-log / decision-log / snapshots │──▶ PASS / FAIL report
   fuzz game ─┘    │     │   / provider-trace  (semantic, no bytes)    │
                   │     └─────────────────────────────────────────────┘
                   │     ┌─────────────────────────────────────────────┐
                   └────▶│ Level 2: runtime fail-closed guards         │
                         │   B1 @ provider-call · B4 @ death-commit     │──▶ raise + audit
                         │   (B2 rides CapabilityLedger ②b; B3 rides   │
                         │    EffectQueue — NOT this slice)             │
                         └─────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────┐
   │ Level 3: deterministic fuzz (stdlib random,  │  generates boundary/adversarial scripts →
   │ fixed seeds) → scripts → fake engine → L1     │  every game must PASS L1; known-bad must FAIL
   └─────────────────────────────────────────────┘
```

- **Level 1** is the workhorse: broad coverage, no runtime cost, cannot perturb bytes.
- **Level 2** is the unrecoverable backstop: only the leak and the dirty-commit, fail-closed.
- **Level 3** drives both with cases hand-written tests miss (cascades, ties, ordering).

---

## 4. Level 1 — offline invariant checker (the 7 invariants)

Input: a finished run's artifacts (a `run_dir`, or the in-memory `GameOutcome` for tests). Output: a list of `InvariantViolation{ id, severity, game_id, event_ids, detail }`; empty = PASS. The checker **never raises** on a malformed artifact (it reports `artifact_gap`), mirroring the engine's never-raise contract.

For each invariant: **statement · reads · computed independently as · MUST-FAIL example**.

### I1 `death_once`
- **Statement:** each player transitions `alive:true → alive:false` **at most once**; exactly one `player_died`/elimination *commit* event per player.
- **Reads:** `game-log` events (`player_died`, `player_eliminated`, `hunter_shoot`→death, role reveals).
- **Computed as:** group death-commit events by target; assert count ≤ 1 per player. (Multiple *candidates* — a wolf_kill **and** a witch_poison naming p3 — are fine; only the committed `player_died(p3)` is counted.)
- **MUST FAIL:** two `player_died` events with `target=p3`.

### I2 `no_dead_actor_for_active_decision`
- **Statement:** a dead player produces **no ordinary** night/day active action, except an explicitly-allowed death-trigger window (`hunter_shoot`, future `wolf_king_shoot`).
- **Reads:** `game-log` events + `decision-log` (actor, round, action) cross-referenced with each actor's death round.
- **Computed as:** for every action event, assert the actor was alive at that (round, phase) **unless** the action's ability has `trigger == event:on_death`.
- **MUST FAIL:** a `seer_check` whose actor already has a `player_died` in an earlier round.

### I3 `capability_not_overused`
- **Statement:** each consumable ability's used-count ≤ its declared `max_uses` (witch antidote 1, witch poison 1, hunter shot 1).
- **Reads:** `game-log` events (`witch_save`, `witch_poison`, `hunter_shoot`) per game.
- **Computed as (now, no ledger):** **event-count** — the "等价消耗证据". Count accepted consumes per **`(actor, capability)`**, not per capability-per-game (LOW fix, 2026-06-10 review): `witch_save` ≤ 1, `witch_poison` ≤ 1, `hunter_shoot` ≤ 1 **per holder**. The engine's single-special guard (`:235-240`) only covers seer/witch, not hunter; on the current 4-role board there is one hunter so per-game ≡ per-actor, but a future double-hunter board would false-positive under per-game counting.
- **Computed as (later, with `CapabilityLedger`):** **add** a cross-check `ledger.consumed_count[cap] == event-count[cap]` — two independent witnesses must agree (a second anti-circularity, ledger vs events).
- **MUST FAIL:** two accepted `witch_save` events in one game.

### I4a `prompt_subset_of_observation`
- **Statement:** a provider call's prompt is rendered only from events in that seat's observation (catches a **renderer** that pulls outside `obs`).
- **Reads:** the in-memory `outcome.provider_turns` turn (`observation_source_event_ids` = the prompt's sources, and the seat's full observation event set).
- **In-memory / unit-only (M-2 fix, 2026-06-10 review):** I4a's second operand — "the observation's own event set" — is **not persisted in any artifact**. The turn only stores `observation_source_event_ids` (a single list, `emergent_engine.py:496-509`); the `role_projection` snapshot is written once at setup (`:424-438`), not per call. So I4a is computable **only at the in-memory/unit level**, not from disk. Persisting the full per-call observation would mean adding a turn-dict key — **forbidden during ②a** (any new key makes `provider_turns` diverge index-by-index → breaks the byte-parity gate). Ship I4a as an in-memory check; the offline disk-level leak net is **I4b** (which reads `game-log` tags, already persisted).
- **Computed as:** `prompt_source_ids ⊆ observation_source_ids`. (Cheap; structural.)
- **MUST FAIL:** a prompt source id absent from the turn's observation set.

### I4b `prompt_visibility_entitled` — **the load-bearing, non-circular leak guard**
- **Statement:** every event a provider call's prompt was built from must be one that **seat could legitimately see** — checked against the event's **recorded `visibility` tag**, by an **independent** projection path (catches a **visibility-rule bug** that I4a cannot — see §9).
- **Reads:** `provider-turns.json` → `turns[]` `observation_source_event_ids` (+ `actor` = the seat) + the **god event log** (`game-log.json`, events with their `visibility` tag) + role/team `snapshots` (or a seat→role map passed directly for in-memory tests).
- **Computed as:** build `seat_index` from snapshots (`observer_visibility.build_seat_role_index`); for each `eid ∈ observation_source_event_ids`, look up the event and check `observer_visibility.event_visible_in_projection(event, f"role:{seat}", seat_index)`. **Signature note (M-1 fix, 2026-06-10 review): this returns a `(visible: bool, reason: str)` tuple (`observer_visibility.py:466-470`), NOT a bool.** Unpack it — `visible, _reason = event_visible_in_projection(...)` then `assert visible is True`. A naive `assert ... is True` is always-false; a naive truthy check (`assert event_visible_in_projection(...)`) is always-true (a non-empty tuple is truthy) → the checker goes silent-green, which is the exact failure mode this net exists to prevent. This uses the **observer's** visibility implementation (tag + trusted role), **not** the engine's `_build_obs`.
- **In-memory path (LOW):** the seat→role map variant must synthesize each entry with `role_source == "role_projection_snapshot"`, else `_trusted_role_for_player` (`observer_visibility.py:521-530`) distrusts it and returns all-hidden → false-positive leak reports.
- **MUST FAIL:** a non-seer seat whose prompt sourced a `visibility:"seer"` event (e.g. a check result).

### I5 `decision_settled_once`
- **Statement:** one decision identity produces **at most one accepted effect**. (Multiple `invalid → fallback` attempts are allowed; one final settle.)
- **Reads:** `decision-log` + `game-log` (the turn's `request_id`, `actor`, `phase`).
- **Decision identity = `(request_id, phase)` — NOT `request_id` alone (BLOCKING-1 fix, 2026-06-10 review).** The strict path (wolf/seer/vote) builds `request_id = f"{game}_r{rnd:02d}_{player_id}"` with **no kind suffix** (`emergent_engine.py:497`); only witch/speech/hunter carry a suffix (`_witch`/`_speech`/`_shot`, `:701/778/883`). So a player who acts at night **and** votes that day shares one `request_id` (`g_r01_p1` twice) in every healthy game. Keying I5 on `request_id` alone would false-positive on every normal run; `phase` (`night`/`day`, present in the turn dict) disambiguates. Keyed on `pending_window_id` once `DecisionWindow` lands — but note ②a's `DecisionWindow` is transient and carries **no** identity, so the `(request_id, phase)` form must outlive ②a (it attaches a real window-id only when the net + full `DecisionWindow` formalize).
- **Computed as:** group accepted effects by `(request_id, phase)`; assert ≤ 1 accepted per identity.
- **MUST FAIL:** one `(request_id, phase)` mapped to two accepted `werewolf_kill` effects.

### I6 `effect_causality`
- **Statement:** every state-changing effect traces to a `source_event_id` **or** `source_decision_id`; an automatic effect (lovers heartbreak) traces to its trigger (`lover_death ← death(pX)`).
- **Reads:** `game-log` effect events.
- **Computed as (now, WEAK — no causal field exists):** infer — every `player_died` has an earlier same-round cause event (`werewolf_kill`/`witch_poison`/`hunter_shoot`/vote) naming the same target. **Note:** `attribution.py` does **not** provide this (it computes narrative turn-points, not per-death cause).
- **Computed as (later, STRICT):** when `EffectQueue` lands it emits a real `source_event_id` on each effect; I6 then asserts the field directly. **Recommendation:** ship WEAK-I6 now; STRICT-I6 rides the EffectQueue (which produces source ids first-class) — do **not** force an engine schema change into this slice (§13 Q1).
- **MUST FAIL:** a `player_died(p4)` with no candidate cause anywhere in the round.

### I7 `no_unknown_final_state_mutation`
- **Statement:** every final `alive/team/role/capability` value is explainable from the event chain — nothing changes silently in state.
- **Reads:** final god `snapshot` vs the reduction of the `game-log` event chain.
- **Computed as:** replay alive/role/team from events; assert the replayed final state equals the final snapshot.
- **MUST FAIL:** a player dead in the final snapshot with no death event in the log.

---

## 5. Level 2 — runtime fail-closed guards

Only where damage is **unrecoverable**. **This slice ships B1 and B4.** B2 and B3 are deferred to the rewrites whose enforcement arms they are — listed here so the contract is on record.

### B1 `prompt_visibility_entitled` @ provider-call boundary — **SHIP**
- **Where (M-3 fix, 2026-06-10 review — corrected anchor):** the strict path's `provider.respond` is **not** in any `_resolve_*` — it lives inside `ProviderAgent.decide` (`provider_agent.py:163`). The correct engine-side anchor is **`_provider_action`** (the rendered `source_event_ids` are ready at `emergent_engine.py:494`, just before the `decide()` call at `:511`) — this single site covers wolf/seer/vote. Plus **three** engine-internal direct `respond` sites: witch `:724`, speech `:799`, hunter `:901`. So B1 is **4 anchors**, not "in every resolver" (and `_resolve_wolf/seer/votes` won't even exist post-②a). `_provider_action` is explicitly kept VERBATIM by ②a, so this anchor is ②a-stable.
- **Rule:** run I4b's check on the request's `observation_source_event_ids`. On any non-entitled event → **hard fail** (raise + abort the game) — a leaked prompt cannot be un-sent.
- **Oracle:** the §9 independent path, **not** `_build_obs`.

### B4 `death_once` @ commit boundary — **SHIP**
- **Where:** the **three** death-commit sites (M-4 fix, 2026-06-10 review — the day-vote site was missing): `_run_inner` night loop `emergent_engine.py:997-1002`; **day-vote elimination `:1021-1026`** (`self._alive.discard(eliminated)` + `player_eliminated` emit + `_trigger_on_death`) — I1 counts `player_eliminated` as a commit, so B4 must guard it too; and `_trigger_on_death:866`.
- **Rule:** a re-commit of an **already-dead** player (a duplicate *candidate*) is a **SILENT no-op** — no audit, no artifact write, exactly the current engine behavior (the `in self._alive` gate). A duplicate **`player_died` event emission** for a player is a **hard fail**.
- **Why silent (user ruling, 2026-06-10):** the candidate-skip fires on a *legal, reachable* path — hunter shot already killed a co-victim the night loop is about to commit (`:998`, the engine comment names exactly this case: wolf kills the hunter + witch poisons p5 → hunter shoots p5 → loop reaches p5 already dead). Any audit/artifact write on that path changes bytes in a healthy game, breaking §2.7's parity-neutral guarantee **and** the ②a OLD-oracle differential gate (`failure_audit` is byte-compared). B4's observability lives entirely in the hard-fail arm.

### B2 `capability_not_overused` @ consume boundary — **DEFERRED → ②b (CapabilityLedger)**
- Needs `uses_left` in `RuntimeState`, which does not exist (`state.py:6-17`). B2 is the **ledger's** enforcement arm: `uses_left < 0` or consume-twice → hard fail. Until then, the witch's inline `save_used/poison_used` (`emergent_engine.py:742-751`) is the de-facto guard, and **offline I3** is the net. Ship B2 **with** the ledger.

### B3 `decision_settled_once` @ settle boundary — **DEFERRED → EffectQueue slice**
- The settle/commit boundary that matters is the **queue's** commit layer (where double-settle becomes reachable: double-kill/save/poison). A thin `request_id`-based version may land here; the load-bearing form rides the EffectQueue.

---

## 6. Level 3 — deterministic fuzz

- **Engine:** stdlib `random.Random(seed)` over a **fixed seed bank** (e.g. seeds 0–49), no Hypothesis. Determinism = a failing seed reproduces exactly.
- **Generators** (each produces a fake script for `build_emergent_fake_agents`):
  - **cascade chains** — hunter shoots hunter / shoots into a lover pair (when those land), to exercise transitive death.
  - **duplicate-death candidates** — wolf_kill == witch_poison target; poison a wolf the vote also hangs.
  - **capability over-use attempts** — second antidote / second poison / (future) second shot.
  - **night-order permutations** — witch acts on a victim revealed by the wolf; guard+save same target (奶穿).
  - **illegal action/target** — cross-role action, dead/unknown/self targets.
- **Contract:** every *well-formed* generated game must **PASS all L1 invariants**; every *known-bad* generator (the over-use / double-commit ones) must **FAIL the specific invariant** it targets. A generator that drops its expected failure is itself a test failure (don't silently pass).

---

## 7. Cross-cutting model — DeathCandidate vs DeathCommitted

The single most important semantic distinction; it constrains both this net **and** the future EffectQueue.

```
DeathCandidate(player=p3, cause=wolf_kill)
DeathCandidate(player=p3, cause=witch_poison)   →  OK   (two effects, one person — normal)

DeathCommitted(player=p3)
DeathCommitted(player=p3)                        →  FAIL (committed twice)
```

**Already half-built in the wired engine** (this is a spec of existing-correct behavior, not a new ask):
- `JointSettler.resolve_night` dedups (`settler.py:60`, `p not in deaths`) → candidate-dedup before commit.
- `_trigger_on_death` (`emergent_engine.py:866`) gates `target in self._alive` before discard+emit → **idempotent commit**.
- The night loop (`emergent_engine.py:997-1002`) `if pid not in self._alive: continue` → no duplicate `player_died`.
- Trigger expansion runs **after** commit (`:870`) → expansion follows **committed** deaths.

**The unwired `TriggerSystem` violates it** (audit item 7 / B3-8: `triggers.py:51` enqueue does not gate on `state.alive`, so it processes already-dead pids). **Therefore B4 + this distinction = the design spec for the EffectQueue's commit layer** when `TriggerSystem` is generalized: queue may hold duplicate candidates; **commit is idempotent**; **expansion keys on committed deaths, never candidates**. This converges three threads — B4, audit item 7, EffectQueue commit semantics — into one rule.

---

## 8. Artifacts & dependencies

| Artifact | Holds | Read by |
|---|---|---|
| `game-log.json` events | `event_id, type, actor, target, round, phase, visibility, data.summary` (`_emit` @ `emergent_engine.py:289/309`) | I1, I2, I3, I4b, I6, I7 |
| `decision-log.json` | `actor, action, target, reason_summary` | I2, I5 |
| `snapshots/*.json` | `role_projection` + `god` (role/team/alive, round, phase) | I4b (seat_index), I7 (final state) |
| `provider-turns.json` → `turns[]` (verbatim `outcome.provider_turns`) | per call `request_id`, `actor`, `observation_source_event_ids` — recorded for **all** call types (`_provider_action:508` wolf/seer/vote · witch:717 · speech:794 · hunter:896) | I4a, I4b, I5 |

**Three confirmed gaps to resolve before the plan (also §13):**
1. **I6 has no causal field.** `player_died` carries `actor` + a message, not a structured `source_event_id`. WEAK-I6 infers; STRICT-I6 rides the EffectQueue. **Do not add a death-event schema field in this slice.**
2. **I4b needs the unprojected god event log** (events *with* their `visibility` tags). Confirm `game-log.json` is the **god/full** log (the observer projects it down per request — `observer_visibility.project_events`) and not a pre-filtered stream. If it is pre-filtered, I4b reads the god snapshot instead.
3. **RESOLVED — per-call source ids persist in `provider-turns.json`, NOT `provider-trace.json`.** The live runner (`run_emergent_deepseek_game.py:160`) writes `provider-turns.json` whose `turns[]` is the verbatim `outcome.provider_turns` (each turn carries `observation_source_event_ids`) → criterion 2 is satisfiable. `provider-trace.json` is a *different* artifact (raw provider req/resp via `provider_trace_to_dict`, no source ids — do not read it for I4). **One small gap:** the fake CLI runner (`run_emergent_fake_runtime.py:131`) writes `provider-trace.json` but **not** `provider-turns.json` — the plan adds one `_write_json(out_dir/"provider-turns.json", _provider_turns_summary(outcome.provider_turns))` mirroring the live runner, so a *persisted* fake run is disk-checkable (in-memory fake TESTS read `outcome.provider_turns` directly — no change).

---

## 9. The independent visibility oracle (anti-circularity) — detail

Why I4 is split, and why I4b is the one that matters:

- The engine builds `obs` for seat X via `_build_obs(X)` — **already visibility-filtered**. `render_observation_text(obs, …)` records `source_event_ids` from `obs`.
- **Leak type 1** (renderer pulls outside `obs`): caught by **I4a** (`prompt ⊆ observation`).
- **Leak type 2** (`_build_obs`'s visibility rule is wrong — e.g. a seer result lands in a villager's `obs`): **I4a cannot catch it**, because the leaked event **is already in `obs`**, so the subset holds. This is the dangerous one (and the future memory-layer leak vector).
- A runtime guard that re-runs `_build_obs`/the engine's own filter to "check" `_build_obs` is **circular** — same bug on both sides passes, exactly the parity-harness failure the audit found.

**The non-circular oracle (already exists, different code path):** `observer_visibility.event_visible_in_projection(event, "role:pN", seat_index)` (`observer_visibility.py:466`). It decides visibility from:
- the event's **recorded `visibility` tag** (`public/all/seer/witch/werewolf_team/internal`, set at emit time), and
- the seat's **trusted role/team** rebuilt from **snapshots** (`build_seat_role_index`), not the engine's live role map.

This is a genuine **double-entry check**: the engine's `_build_obs` and the observer's `event_visible_in_projection` are two independent visibility implementations; for the `role:pN` perspective they must agree on "what pN may see." A disagreement is either a real leak or a contract drift — both must be surfaced. I4b/B1 therefore **reuse the observer's tested projection** rather than writing a third visibility implementation.

> Optional deeper layer **I4c** (`event_type → required visibility tag`, e.g. "a `seer_check` must be tagged `seer`") catches a **mis-tag at emit time**, which both `_build_obs` and the oracle would propagate. Out of scope for this slice; recorded for completeness.

---

## 10. Acceptance criteria

1. A **fake-deterministic** full game (villager-win + werewolf-win + hunter scripts) runs to completion → checker **PASS** on all 7 invariants.
2. A **live smoke** run's persisted artifacts run the checker **offline, with no API key** → PASS.
3. **Injected bad examples** each **FAIL** the targeted invariant (and only sympathetically others):
   - second `witch_save`/`witch_poison` accepted → **I3**;
   - same player `player_died` twice → **I1** (and B4 at runtime);
   - same `request_id`/window settled twice → **I5**;
   - a prompt sourced a non-entitled (e.g. `seer`-tagged) event → **I4b** (and B1 at runtime);
   - hunter cascade re-expands an already-committed death → **I1/§7**.
4. The checker **does not depend on byte parity** and **never uses old output as oracle** — all verdicts derive from the rules + the artifacts of the *same* run.
5. Runtime guards exist **only** at the four boundaries (provider-call, capability-consume, decision-settle, death-commit) — and this slice wires **only B1 (provider-call) + B4 (death-commit)**.

---

## 11. Scope, sequencing & orthogonality

**Ships in this slice (`P2-A invariant safety net`):**
- Level 1: all 7 offline invariants (I3 event-count form; I4 split a/b; I6 weak/inferred).
- Level 2: **B1** (provider-call) + **B4** (death-commit) runtime guards.
- Level 3: deterministic fuzz generators + the fixed seed bank.

**Explicitly rides later rewrites (NOT here):**
- **B2** + I3 ledger cross-check → **②b CapabilityLedger** (B2 is the ledger's enforcement arm).
- **B3** load-bearing + I5 `pending_window_id` → **EffectQueue / DecisionWindow** slices.
- **STRICT-I6** (structured `source_event_id`) → **EffectQueue** (emits source ids first-class).

**Orthogonality:** the offline checker + fuzz only **read** artifacts; B1/B4 are fail-closed assertions parity-neutral on the happy path. This net can be built **in parallel with swap ②a** (the `_resolve_*` dispatch reorg) — they do not touch the same surfaces. Recommended order overall: **this net → ②b ledger (+B2) → EffectQueue (+B3, +STRICT-I6) → NightPlan**, so each rewrite lands on a live net.

---

## 12. Proposed file structure

New package `src/werewolf_eval/invariants/` (sibling to `action_runtime/` — the net is a cross-cutting concern over the engine's **output**, not part of action resolution):

- `invariants/checker.py` — Level 1: the 7 invariants + `InvariantViolation` + `check_run(run_dir|outcome) → [violations]`. Never raises.
- `invariants/visibility_oracle.py` — thin wrapper over `observer_visibility` exposing `entitled(seat, event, seat_index) → bool` for I4b **and** B1 (single source, used by both offline and runtime).
- `invariants/guards.py` — Level 2: `assert_prompt_entitled(request, …)` (B1) + `assert_death_commit_once(state, pid, events)` (B4). Imported by the engine at the two boundaries.
- `invariants/fuzz.py` — Level 3: deterministic generators + seed bank → scripts.
- Tests: `tests/test_invariants_checker.py`, `tests/test_invariants_guards.py`, `tests/test_invariants_fuzz.py`, plus a `tests/fixtures/bad_examples/` set (the criterion-3 injected violations).
- Engine integration (M-3/M-4 fix, 2026-06-10 review): **B1×4** (`_provider_action` pre-`decide` for wolf/seer/vote `:494`, + witch `:724` / speech `:799` / hunter `:901` direct-`respond` sites) **+ B4×3** (night-loop `:997-1002`, day-vote `:1021-1026`, `_trigger_on_death:866`) = **7 guard insertions**, not "2 call sites". All land on code ②a keeps VERBATIM (`_provider_action`) or doesn't touch (witch/speech/hunter, day-vote, `_trigger_on_death`); the night-loop site moves under ②a and is re-located at wiring time. No other engine change in this slice.

**Alternative considered:** `action_runtime/invariants/`. Rejected for the home of the *checker/fuzz* (they are about engine output, not rule projection), but the *guards* could arguably live there — see §13 Q4.

---

## 13. Open questions (resolve before writing the plan)

- **Q1 — I6 now or later?** Recommend **WEAK-I6 (inferred) now**, STRICT-I6 with the EffectQueue. Confirm no death-event schema change in this slice. *(Author lean: yes, weak now.)*
- **Q2 — RESOLVED ✓.** `game-log.json` IS the unprojected god log: `_game_log_dict` sets `"events": self._events` (`emergent_engine.py:376`), every event carries `visibility` (`:309`) + `event_id` (`:302`); the live runner writes it verbatim (`run_emergent_deepseek_game.py:172`); the observer projects it down per request (`observer_visibility.project_events`), proving it is unprojected on disk. I4b reads each source event's tag directly from `game-log.json` — no snapshot fallback needed.
- **Q3 — RESOLVED ✓ (rename + 1-line fake-runner add).** Per-call `observation_source_event_ids` persist in **`provider-turns.json` → `turns[]`** (live runner `:160`), recorded for all call types (`:508/717/794/896`). Spec artifact name corrected (was `provider-trace.json`). Plan adds one `_write_json` to `run_emergent_fake_runtime.py` so persisted fake runs are disk-checkable. *(No longer blocking.)*
- **Q4 — guards' home.** `invariants/guards.py` imported by the engine, or co-located in `action_runtime/`? *(Lean: `invariants/`, single visibility-oracle source shared with the offline checker.)*
- **Q5 — RESOLVED ✓ (user ruling 2026-06-10): duplicate candidate = SILENT no-op (no audit).** Duplicate **committed event** = hard fail. The earlier "no-op+audit" draft was rejected: the candidate-skip is reachable in a legal game (hunter co-victim path, `emergent_engine.py:998`), so any audit write would break byte parity + the ②a differential gate. Now truly matches §7 and current engine behavior.

