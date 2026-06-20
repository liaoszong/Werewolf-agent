# Agent Action Runtime Architecture — Design Spec

> Status: **DESIGN — pending user review** · Date: 2026-06-09 · Author: brainstorming session (liaoszong + Claude + GPT cross-review)
> Supersedes the hardcoded action-resolution path in `emergent_engine.py`; does **not** supersede the engine's output contracts, visibility projection, or runtime spine.
> Companion context: `docs/PROJECT_MAP.md` (phases + SYS-A2 / SYS-C3 system view), `docs/superpowers/specs/2026-06-09-p2a-invariant-safety-net-design.md` (runtime verification guardrails).

---

## 1. Motivation

### 1.1 Current state (what gets replaced)

Today the game's action resolution is a **hardcoded linear script** with **role-specific resolver methods**, all crammed into `EmergentGameEngine`:

- `_run_inner` (emergent_engine.py, ~L800) runs a fixed sequence: setup → for each round { night: `_resolve_wolf_kill` → `_resolve_seer` → `_resolve_witch` → apply deaths → day: announce → `_resolve_speech` × alive → `_resolve_votes` → eliminate → reveal }.
- Each role has a bespoke method: `_resolve_wolf_kill` (~L505), `_resolve_seer` (~L614), `_resolve_witch` (~L643, the largest — it inlines its own ProviderRequest build + parse + 3-way validation + downgrade, **bypassing** the shared `_provider_action` ~L432).
- Allowed actions are a static map: `ALLOWED_ACTIONS_BY_ROLE_PHASE` (provider_agent.py:19).
- The wolf "consensus" is a **vote tally with a synthesized consensus log** (`_build_consensus_entry`, ~L563) — the support/oppose reasons are template strings, not model output.

**Consequence:** adding a role (hunter, guard, wolf-king, …) means surgery on the linear loop + new `if role == …` branches + new entries in the static action map. The structure does not scale to the gameplay depth the product needs.

### 1.2 Independent confirmation (health check, 2026-06-08)

The read-only health check flagged the same coupling without knowing about this design discussion:

- **B-5** — "extract `EmergentGameEngine`'s night/day resolvers into composable units; unify the witch path through `_provider_action`" (emergent_engine.py:454-756).
- **B-2** — duplicate observation/visibility ref-building and near-duplicate wolf-consensus entry shape between `game_engine.py` and `emergent_engine.py` (needs a visibility ADR).
- **D-4** — single-DeepSeek factory (`run_emergent_deepseek_game.py:199`) bypasses the registry identity stamp.
- **E-5** — overlapping fake-emergent entrypoints.

These four are **claimed by this rewrite** (see §7); they must **not** be patched as separate optimization PRs.

### 1.3 What this spec is NOT

This spec is the **action runtime** (extensibility plumbing + baseline rule-layer guards). It is **not** the decision-quality / role-play work. The observed quality problems — P5 voting itself, twin-wolf identical speeches, speech↔vote decoupling — are **enhancement-layer** concerns (memory, real wolf coordination, persona, reflection) and get their own specs. This spec only **leaves the seam** for them (§4.5, `AgentContextPacket`). The single overlap: baseline `target_rule` guards (e.g. `exclude_self`) that stop the *mechanically* illegal self-vote belong here, in the rule layer.

---

## 2. Locked design principles

These were converged across the brainstorming dialogue and a GPT cross-review. They are **invariants** for the implementation, not suggestions.

1. **Two layers.**
   - `baseline_fair` — **frozen, versioned, measured.** Unified rules, unified observation, unified minimal memory, unified action protocol. This is what makes model-vs-model comparison valid. Cross-model comparisons are only valid **within the same baseline version**.
   - `enhancement` — **toggleable, logged, ablatable.** Private memory, wolf channel, persona, reflection, speech-vote consistency, spectator cards. Every toggle is recorded in the run manifest, default **off**.
2. **AI submits intent; the system adjudicates.** The model returns an `ActionEnvelope` (an action *intent*). It never calls a kill function. All legality, arbitration, and settlement authority lives in the runtime.
3. **Baseline modality is uniform strict-JSON for every model.** Tool-calling / function-calling is **not** auto-enabled per provider. It is only an **explicitly logged enhancement / ablation axis** — otherwise a tool-calling model vs a JSON model is comparing "model + interface", not model ability.
4. **Identity is a Role Contract, not a callable skill.** It is re-injected stably every turn (you are pX, role, team, win-goal, current abilities, teammates) + enforced by validation. The model must never have to "ask" who it is.
5. **Rules / persona / strategy are separate layers.** `baseline_fair` uses the **rules layer only**. Persona and strategy are enhancement-only and never leak into the rule layer (no "prioritize killing the seer" in a role's rule definition).
6. **Design for the general case; implement incrementally.** The abstraction must pass **paper-validation against the hardest interactions** (奶穿 / lovers heartbreak / chain death — §5) even though the early versions *implement* only hunter (v1.1), then guard (v1.5). We never want to re-architect to fit a later role.
7. **Innovation boundary (honest scope).** Data drives the **wiring** (which role, which phase/trigger, which `target_rule`, which visibility). A genuinely **new effect** still needs a small `resolver` plugin (one handler). We promise "new role = data (+ maybe a small resolver)"; we do **not** promise a no-code general rules DSL.

---

## 3. The "kill p3" lifecycle, re-expressed

The running example, in the new architecture:

```
PhaseScheduler reaches NIGHT
  → asks RoleAbilityRegistry: who has an ability triggered at phase=night?
  → wolves have ability `werewolf_kill` (trigger=night, target_rule=alive_non_wolf)
  → for each wolf: build AgentContextPacket (RoleContract + visible state + abilities)
       → ProviderInputMode renders it (baseline = strict-JSON ability card)
       → model returns ActionEnvelope {actor:p1, action:werewolf_kill, targets:[p3], reason, confidence}
       → ActionValidator checks envelope vs AbilityDefinition (action allowed? each target in alive_non_wolf?)
       → valid envelope recorded as a PENDING INTENT (not executed)
  → JointSettler resolves the night: collect {wolf_kill:p3 (+ tally), witch_save?, witch_poison?, guard?}
       → apply interaction rules → death list
  → emit events (werewolf_kill, player_died) with existing visibility tags + state effects (alive.discard)
  → TriggerSystem processes the death queue (hunter/lovers/… if any) — see §5
```

The model "tells the system it wants to kill p3" by emitting a **schema-validated JSON envelope**; the system **adjudicates and settles**. This is exactly today's strict-JSON contract — but **driven by the registry** and **resolved by a settler**, instead of hardcoded.

---

## 4. Components

Each component has one purpose, a defined interface, and is testable in isolation.

### 4.0 BoardRuleset / RulesVariant — the rules container (read by Registry, Settler, TriggerSystem)
- **Purpose:** make the *rules of this board* an explicit, versioned, swappable object — **not** global truths hardcoded in resolvers. Bundles: board composition + role config, **night interaction rules** (e.g. the 奶穿 outcome), **death-trigger ordering** (§4.10), and win-condition details.
- **`rules_v1`** is the default ruleset (the current standard board). Any rule change (奶穿 dies vs survives, a different win condition, a different death order) is a **new `RulesVariant` that bumps `rules_version`** — never a silent global change. Cross-`rules_version` games are not directly comparable (same discipline as the baseline version).
- **Consumers read from it:** the Registry projects abilities/targets per the ruleset's board; the JointSettler applies the ruleset's interaction table; the TriggerSystem uses the ruleset's death-order key. This is what lets "标准局 / 娱乐局 / 自定义板子" coexist without fighting.
- **Interface:** `active_ruleset(state) → RulesVariant`; settler / trigger / registry take the ruleset as input, never as hardcoded constants.

### 4.1 RoleDefinition
- **Purpose:** declare a role's identity, team, win-condition, and ability list.
- **Shape:** `{ role, team, win_condition_ref, abilities: [ability_id, …] }`.
- **Replaces:** scattered role facts in `build_default_config` / engine constants.

### 4.2 AbilityDefinition
- **Purpose:** declare one ability fully and declaratively.
- **Shape:** `{ action_id, trigger, input_schema, target_rule, visibility, resolver_ref, summary_template, emits: {event?, decision?} }`.
  - `trigger` — `phase:<name>` (e.g. `night`, `day_vote`) **or** `event:<name>` (e.g. `on_death`).
  - `target_rule` — declarative predicate: `alive_only`, `exclude_self`, `alive_non_wolf`, `is_night_victim`, … (baseline rule-layer guards live here; this is where `exclude_self` kills *mechanically illegal* self-targeting — **not** the strategy-layer self-vote *quality* problem, i.e. a model *reasoning* it should vote itself, which is enhancement-layer, §1.3).
  - `visibility` — maps **directly** onto the existing `RUNTIME_EVENT_VISIBILITIES` (`public|all|seer|witch|werewolf_team|…`, runtime_events.py:53). No new visibility primitive invented here.
  - `resolver_ref` — names an effect handler (immediate vs pending-intent — see §4.8).
- **Replaces:** `ALLOWED_ACTIONS_BY_ROLE_PHASE` (provider_agent.py:19) + the per-method inline schemas.

### 4.3 RoleAbilityRegistry
- **Purpose:** hold all RoleDefinitions + AbilityDefinitions; **project** per `(role, phase, game_state)` → `allowed_actions`, `allowed_targets`, and prompt **ability cards**. Drive `ActionValidator`.
- **Interface:** `abilities_for(role, phase, state) → [AbilityDefinition]`; `allowed_targets(ability, state) → [player_id]`; `render_cards(role, phase, state) → cards`.
- **Versioned:** `rules_v1` (part of the measured baseline; bump on any rule change — cross-version games are not directly comparable).

### 4.4 RoleContract
- **Purpose:** the stable per-turn identity injection. "你是 pX,身份 …,阵营 …,胜利目标 …,本回合可用能力 …,你的队友 …"
- **Replaces:** the identity lines currently re-derived ad hoc in `render_observation_text` (emergent_engine.py:95). Now a first-class, always-present contract — the fix for "the model forgot it is p5".
- Optional enhancement: a read-only `read_role_card` introspection action (never a state-changing tool; off in baseline).

### 4.5 AgentContextPacket  ← the enhancement seam
- **Purpose:** assemble what the model sees: `RoleContract` + role-filtered visible state + available ability cards. **This is the single seam where the enhancement memory layer (SeatMemory / WolfChannel / ReflectionSummary) plugs in later** — by enriching the packet, without touching the runtime.
- **Interface:** `build(actor, phase, state, enhancements) → packet`.
- **Baseline:** `enhancements = {}` (minimal memory = the role-filtered event log, as today).

### 4.6 ProviderInputMode
- **Purpose:** render an `AgentContextPacket` + ability cards into the provider call, and parse the response back into an `ActionEnvelope`.
- **Baseline:** strict-JSON ability card + JSON-schema'd response (today's `build_action_system_prompt` path, llm_providers.py:87).
- **Enhancement:** tool-calling adapter (abilities → tools). **Logged in manifest/trace; never auto-selected per provider.**
- **Invariant:** the internal canonical is always `ActionEnvelope`, regardless of modality.

### 4.7 ActionEnvelope + ActionValidator
- **ActionEnvelope:** the uniform internal intent —
  ```
  { actor, role, phase, action,
    targets: [],   // 0 (pass / speech), 1 (kill / check), or N (cupid link, multi-target)
    params: {},    // ability-specific extras (e.g. witch potion choice)
    reason_summary, decision_type, confidence }
  ```
  Generalizes today's single-`target` `AgentAction` so no future role is cramped (hunter-pass = 0 targets, cupid = 2, multi-target abilities = N). **Parity projection (preserves §7.1):** for existing single-target actions the serializer writes the legacy `target: targets[0]` into `decision_log` / `game_log` so those artifacts stay **byte-identical**; an inbound legacy `target` maps to `targets[0]`. New `targets[]`/`params` fields surface only for new roles, under the `runtime_v2` boundary.
- **ActionValidator:** validate the envelope against the matched `AbilityDefinition` — action allowed for `(role, phase)`, each `target` in `targets` satisfies `target_rule`, arity matches the ability. On failure → the existing seeded fallback path (R-29), preserved. **Baseline rule guards (`exclude_self`, `alive_only`, `phase_allowed`) are enforced here** — this is where the mechanical self-vote dies.
- **Replaces:** the validation in `ProviderAgent.decide` (provider_agent.py:236-357) + per-resolver inline checks.

### 4.8 PhaseScheduler
- **Purpose:** the data-driven turn loop (replaces `_run_inner`'s hardcoded sequence).
- **Key design:** express **data dependencies, not a fixed function order.** The night is a **DAG of pending intents** — e.g. the witch's `witch_save` depends on the **wolf kill's pending victim** (NOT on the seer; seer-before-witch in today's code is incidental, not a dependency). The scheduler resolves abilities in dependency order, collecting intents.
- **Interface:** `run(state) → ` drives phases; per phase, gathers the actors/abilities (from the registry), builds packets, collects validated intents, hands them to the settler.

### 4.9 JointSettler
- **Purpose:** phase-level **joint** resolution. The night is not "each ability resolves itself"; it is "collect all pending intents, then adjudicate interactions together."
- **Key design:** a **rule table over the collected intent set** → produces the state effects (death list, check results delivered to actor, etc.). Example night inputs `{wolf_kill, witch_save, witch_poison, guard_protect}` → interaction rules (save cancels kill, guard cancels kill, **guard+save on same target = death (奶穿)**, poison stacks) → death list.
- **Replaces:** the implicit victim-threading (today `_resolve_witch(rnd, victim, …)` passes the wolf victim by hand).

### 4.10 TriggerSystem  ← the hardest component
- **Purpose:** reactive, event-triggered abilities — **a death-resolution queue**, not a single callback.
- **Key design (must be built to this even in v1):**
  - **Queue + transitive closure:** a death enqueues; processing a death may enqueue more (lover heartbreak → hunter shot → wolf-king shot → …). Process until the queue drains.
  - **Deterministic ordering (decided — see §9):** simultaneous deaths in one settlement batch resolve by a deterministic **`death_order_key = (phase_priority, cause_priority, seat_index)`** defined by the active ruleset (§4.0) — **never a seeded shuffle** in baseline. Death-trigger order is *rule semantics*, not randomness: a spectator / replay must be able to explain "why A shot before B", not attribute it to a seed. (A `seeded-shuffle` order is allowed only as an explicit `RulesVariant`.) Fully reproducible either way.
  - **Cycle termination:** a visited/processed set prevents infinite loops (e.g. mutual lover references).
- **Replaces:** would-be `if role == "hunter" and died:` branches in the main loop.

### 4.11 EventStore / RuntimeTrace / Manifest / Visibility — **UNCHANGED**
- The runtime emits into the **existing** event log, runtime spine (events.jsonl/snapshots/partial-log writes), visibility projection (`observer_visibility.py`), and manifest. The new runtime **feeds** these with the same envelope/visibility shapes; it does not reimplement them.
- **Added to manifest/trace:** `runtime_version`, `input_modality`, `enabled_scaffolds` — so eval / leaderboard can trust which conditions produced a game.

---

## 5. Hard-case paper validation

The abstraction is only worth rewriting for if it absorbs the hard interactions **without re-architecture**. The early versions implement only hunter (v1.1) then guard (v1.5); the rest are validated **on paper** here.

### 5.1 奶穿 — guard + witch save the same target
This outcome is a **`rules_v1` settlement rule (§4.0), not a universal truth** — house rules differ (some have 奶穿 *survive*). In `rules_v1` the JointSettler (§4.9) collects `{wolf_kill: A, guard_protect: A, witch_save: A}` and applies the ruleset's rule *two protections on one target cancel → A dies*. ✔ The architectural point: the settler resolves it from the **active ruleset's interaction table** over the collected intent set — no per-ability resolver could see this; a different `RulesVariant` (奶穿 survives) supplies a different rule and bumps `rules_version`. The abstraction holds either way.

### 5.2 猎人 / 狼王 连环死 — chain death
TriggerSystem (§4.10) death queue:
```
wolf kills A → settler death list [A]
queue: [A] → A is a lover → enqueue B (heartbreak)
queue: [B] → B is hunter → B shoots C → enqueue C
queue: [C] → C is wolf-king → C shoots D → enqueue D
queue: [D] → no trigger → drain
```
Ordering by the deterministic `death_order_key` (§4.10); visited set terminates cycles. ✔ Handled by the queue; v1.1 implements only the `hunter_shoot` leaf but the queue exists.

### 5.3 丘比特 情侣殉情 — lovers heartbreak
Cupid sets a **relationship** at setup (not an active per-turn ability). The heartbreak is a TriggerSystem **rule keyed on the relationship** (`on_death(x) → if lover(x)=y and alive(y): enqueue death(y)`). ✔ Fits the trigger queue as a death-propagation rule; no new machinery.

**Conclusion:** registry + scheduler-DAG + joint-settler-rule-table + trigger-death-queue accommodate all three on paper. The implementation ships incrementally (§6).

---

## 6. Scope & sequencing

| Version | Adds | Validates |
|---|---|---|
| **v1.0** | current 4 roles on the new runtime, **no new role** | old↔new **semantic parity** — prove the new foundation is *equivalent* |
| **v1.1** | **+ hunter** | TriggerSystem `on_death` + the add-role path — prove the new foundation is *stronger* |
| **v1.5** | + guard | JointSettler pending-protection (joint settlement incl. 奶穿) |
| **v2** | wolf-king, idiot, knight | trigger variety; non-death special rules |
| **v3** | cupid / lovers / chain-death / custom boards | relationships + deep death-propagation |

**先证明等价(v1.0),再用猎人证明更强(v1.1)** — semantic parity and the first new role are **separate milestones, never merged into one phase**.

**Out of scope for this spec (separate enhancement specs):** SeatMemory, WolfTeamChannel, SpeechVoteConsistency, Persona, ReflectionSummary, Belief/Suspicion model, spectator explanation cards. This spec only leaves the `AgentContextPacket` seam (§4.5).

---

## 7. Migration & Parity strategy

This is a **rewrite of the action-resolution core**, executed behind a **parity gate** — not a greenfield big-bang.

### 7.1 Rewrite vs preserve
- **Rewrite:** `_run_inner` linear sequence + `_resolve_*` methods + `ALLOWED_ACTIONS_BY_ROLE_PHASE` + `_build_consensus_entry` → Registry + Scheduler + Settler + TriggerSystem + Validator (new module `action_runtime/`, **not** in-place edits).
- **Preserve (must not change):** `game_log` / `decision_log` / `consensus_log` shapes; runtime spine (events.jsonl / snapshots / prompt-manifest / partial-log writes); visibility projection (`observer_visibility.py`); provider/agent contract; **seeded determinism**; scoring / attribution / observer consumption.

### 7.2 The old engine is the parity oracle
The current engine + the 799-test suite + the byte-determinism test define correct behavior. The rewrite is validated against them — it cannot silently lose an invisible invariant (witch_poison vocab R-01, R-29 seeded tie-break, fail-closed, no-feed-leak R-17).

### 7.3 Parity gate (decision: **semantic parity = hard; byte parity = best-effort diagnostic**)
- **Layer 1 — semantic parity (HARD GATE).** Same seed / profile / fake provider → identical winner, deaths, votes, night targets, check results, **visibility boundaries**, and fallback behavior.
- **Layer 2 — byte parity (best-effort diagnostic).** Pursue byte-identical output; if it diverges, **locate the exact cause** (the new scheduler/settler may legitimately change RNG draw order). Do not force the new design to mimic the old engine's incidental ordering.
- **Layer 3 — blessed diff ledger (format decided — see §9).** Every non-byte-identical difference is recorded — **no silent blessing.** Primary machine artifact: `docs/generated-games/runtime-v2-parity-diff-ledger.json`; human summary: `.logs/review/latest/parity-diff-summary.md`. Each entry carries at least: `seed`, `profile`, `old_event_ref`, `new_event_ref`, `field_path`, `old_value_hash`, `new_value_hash`, `semantic_class`, `reason`, `affects_visibility`, `affects_scoring`, `affects_replay`, `blessed_by`.
- **Named preserve-invariants (from health check):** (a) the P2-A-2 **no-feed-leak** hard gate; (b) **scripted gold-game g1b/g1c/g1f byte-identical replay** — these run the `game_engine.py` *scripted* path, which the rewrite only *shares code with* (B-2 dedup) and must **not** behaviorally change, so their bytes stay frozen. Both are Layer-1 gates. (This byte-freeze is about the *scripted* path; the *emergent* runtime's own output is governed by the semantic-hard / byte-diagnostic / ledger gate above — see §9.1.)

### 7.4 Discipline
1. New runtime in `action_runtime/`; never patch `emergent_engine.py` resolvers in place.
2. **Phase 1 is parity only — no gameplay/behavior change.**
3. Registry first **only generates** the existing `allowed_actions` / `allowed_targets` / validator (behavior-preserving).
4. Run new vs old on the same seed / fake provider / profile; compare semantic results, event visibility, log shape, provider trace, manifest.
5. After parity holds → **swap-then-delete** the old `_resolve_*` path (no long-lived hybrid).
6. **Behavior improvements are separate later PRs** — anti-self-vote (beyond the mechanical `exclude_self` guard), real wolf consensus, speech↔vote consistency, memory — **never mixed into a parity PR**.
7. First new role = **hunter** (v1.1, only after v1.0 parity + swap-delete — proves "add role = add data"); second = **guard** (v1.5, proves joint settlement). Parity (v1.0) and the first new role (v1.1) are never in the same phase.
8. `baseline_fair` keeps strict-JSON `ActionEnvelope`; tool-calling only as an explicit enhancement / ablation axis.
9. `runtime_version` / `input_modality` / `enabled_scaffolds` → manifest / trace.

### 7.5 Health-check items claimed here (do NOT patch separately)
**B-5** (resolver extraction), **B-2** (shared observation/consensus building — coordinate with the visibility ADR the health check requests), **D-4** (registry identity stamp on the single-DeepSeek factory), **E-5** (fake-emergent entrypoints). The parallel bug-fix track is fenced **out** of these.

### 7.6 Engine behavior the rewrite must FREEZE during parity
`emergent_engine.py`, `game_engine.py`, `provider_agent.py` behavior is the oracle — the parallel bug track must not change it (e.g. `engine-02` fallback-vote metric pollution is fixed **scoring-side** or deferred into the rewrite's behavior phase, never engine-side during parity).

---

## 8. Testing strategy

- **Parity harness:** old vs new runtime across N seeds × the canonical fake scripts (villager-win, werewolf-win) → assert Layer-1 semantic parity + diff-ledger any byte divergence.
- **Per-component unit tests:**
  - Registry projection (`allowed_actions`/`targets`/cards per role/phase/state).
  - Validator rule guards (`exclude_self` rejects self-target; `alive_only`; `phase_allowed`).
  - Scheduler DAG (witch intent depends on wolf victim; ordering deterministic).
  - JointSettler interaction table (save/guard/poison incl. **奶穿**).
  - TriggerSystem death queue (chain death, **deterministic** `death_order_key` §4.10, cycle termination).
- **Role-add acceptance:** hunter added via data (+ one `hunter_shoot` resolver) with **no scheduler/loop edits** — the structural proof.
- **Net preserved:** the existing 799-test suite stays green throughout.

---

## 9. Open questions / risks (honest)

1. **Byte-parity reachability (emergent runtime output).** The *emergent* runtime's own game-logs may not reach byte-identity once the scheduler reorders RNG draws → we accept a `runtime_v2` re-baseline of the **emergent** reference outputs, each divergence recorded in the diff ledger. (Distinct from the **scripted** gold-game replays in §7.3, whose bytes stay frozen.) Decision already leans this way; confirm during phase 1.
2. **Resolver-plugin interface.** The exact contract for an effect handler (immediate vs pending-intent, access to state) needs a small sub-design at implementation time.
3. **B-2 visibility ADR coordination.** The shared observation/visibility extraction touches the no-feed-leak boundary; the health check requires an ADR first. This rewrite should fulfill / reference that ADR rather than fork it.

> **Decided during review** (previously open): **trigger ordering** = deterministic `death_order_key = (phase_priority, cause_priority, seat_index)`, not seeded-shuffle (§4.10); **diff-ledger format** = JSON artifact + markdown summary with the fixed field list (§7.3). **奶穿 / death-order / win-conditions** are now `rules_v1` settlement rules inside `BoardRuleset` (§4.0), not global truths. **ActionEnvelope** carries `targets[]` + `params{}` (§4.7).

---

## 10. Next step

Per the brainstorming flow, after user review of this spec → **writing-plans** to produce the phased implementation plan (phase 1 = parity-preserving registry+validator; phase 2 = scheduler+settler+`BoardRuleset`; phase 3 = swap-delete → **v1.0 parity locked** → hunter **v1.1**). No code before the plan is written and (agent-)reviewed.
