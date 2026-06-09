# Action Runtime — Independent Audit Charter

> **For the auditing Claude instance.** Read this whole file, then execute it. You are an
> independent, READ-ONLY auditor of the newly-merged Agent Action Runtime work. A long
> autonomous session produced it; the author has confirmed blind spots (three prior
> per-diff reviews EACH caught a real bug). Your job is to find what those narrow reviews
> missed — holistic correctness, robustness, edge cases, and especially **code rot**
> (half-integration, drifting duplicate sources of truth, dead/orphaned code, abstractions
> that won't hold the remaining work).

## Mission

Confirm the foundation is **solid and rot-free** *before* the remaining Phase 3 (the big
resolver-delete + hunter) gets built on top of it. Building a large rewrite on an unaudited
base is how subtle bugs compound — your audit is the gate.

## Hard constraints

- **READ-ONLY.** Produce a report. Do **not** modify any `src/`, `tests/`, or production
  code. You MAY write throwaway scratch probes to a temp dir to test behavior — do not
  commit them, do not leave them in `tests/`.
- **Audit the FROZEN state at commit `69dd9bb`** on local `main` (the merge of swaps #1 +
  #2). Run `git log --oneline -5` to confirm you are at or after it. If `main` has moved
  past it because the author committed more, audit `69dd9bb` specifically
  (`git worktree add` a read-only checkout, or `git stash`-free `git show`/`git diff`).
- **Test env:** run with `NO_PROXY='*' PYTHONPATH=src python -m unittest <target>`.
  **Known NON-bugs (ignore them):** `tests/test_observer_server.*` fail locally because
  localhost HTTP is firewalled in this environment; a few `tests/test_deepseek_*` have an
  import-path quirk when run from repo root. Neither is a defect. The real suite is **863
  tests** and is green on CI / when run with the right path.

## Scope

- **Module:** `src/werewolf_eval/action_runtime/` — `state.py`, `abilities.py`,
  `ruleset.py`, `registry.py`, `envelope.py`, `validator.py`, `settler.py`, `triggers.py`,
  `__init__.py`.
- **Engine integration:** `src/werewolf_eval/emergent_engine.py` — the `_settler` /
  `_validator` wiring in `__init__`, `_runtime_state`, `_action_legal`, the night-settlement
  swap (the `deaths = ... self._settler.resolve_night(...)` block), and the wolf/seer/vote
  validation swaps.
- **Tests:** `tests/test_action_runtime_*.py` + the new reject tests in
  `tests/test_emergent_engine.py` (`RobustnessTests`).
- **Reference (intent):** spec `docs/superpowers/specs/2026-06-09-agent-action-runtime-architecture-design.md`;
  plan `docs/superpowers/plans/2026-06-09-agent-action-runtime.md`.
- **The oracle = the OLD behavior.** Compare against pre-swap logic with
  `git show <older-commit>:src/werewolf_eval/emergent_engine.py` (e.g. the commit before
  `2ba3dff`).

## Audit dimensions (priority order)

### 1. Behavior preservation — TRY TO BREAK THE SWAPS
The two swaps claim to be byte/semantically identical to the old engine.
- **Settlement swap** (night deaths → `JointSettler.resolve_night`) and **validation swap**
  (wolf-kill / seer-check / player-vote legality → registry/validator via `_action_legal`).
- Find **any reachable input** where the new path accepts/rejects, or computes deaths,
  differently than the old inline logic. The two canonical fake scripts never hit the
  fallback/RNG paths — **construct adversarial fake scripts** that force: an invalid
  wolf/seer/vote target, a witch double-poison, a vote tie (seeded tie-break), repeated
  invalid actions. Confirm the seeded R-29 fallback fires in the **identical RNG draw
  order** after the swap (a divergence here silently changes games).
- Confirm `test_deterministic_same_seed_byte_identical` is *meaningful*, not trivially green.

### 2. Robustness / edge cases — hit the thin spots hard
The author flags these as the least-covered areas:
- **Parity harness covers only 2 scripts** (happy path). Probe: peaceful-night-then-poison,
  `poison == victim`, `victim is None`, all-wolves-already-dead, an empty `alive` set.
- **Settler guard / 奶穿 path** is unit-tested but **never runs in a real game** (no guard
  role yet). Is the `guard+save_same_target => death` logic actually correct and reachable?
- **Unusual boards:** multi-seer / multi-witch (the engine has an R-30 fail-loud guard — does
  `action_runtime` degrade sanely or silently misbehave?), 0-wolf, 0-villager.
- **Validator** on malformed input: `None` / `"none"` / empty / multi-target; a `RuntimeState`
  with a missing/partial `roles` map; an unknown role.
- **TriggerSystem:** prove non-termination is impossible, no double-processing, and ordering is
  truly deterministic under simultaneous deaths with real handlers (not just the toy tests).

### 3. Code rot / integration health — THE CORE WORRY
- **Drifting duplicate sources of truth.** `registry.allowed_actions` vs
  `provider_agent.ALLOWED_ACTIONS_BY_ROLE_PHASE` — BOTH exist; a test asserts equality but
  they can silently drift. The settler reproduces the engine's night logic. **List every place
  the same rule lives in two spots** and assess the drift hazard + whether the duplication is
  temporary-by-design (will be deleted in the remaining Phase 3) or permanent rot.
- **Half-swaps.** The validation swap routes legality through the validator, but the prompt's
  `allowed_targets` still comes from `observation.alive_players` (this is *correct* per the
  shown-vs-legal split — confirm it, and confirm no seam is left half-wired).
- **Dead / orphaned code.** Find every exported symbol, method, param, or ruleset key nothing
  uses yet — e.g. `registry.shown_targets`, `NightIntents.guard_target`, the entire
  `TriggerSystem`, `validator` `needs_state`. **Distinguish** intentional forward-scaffolding
  (acceptable IF minimal + clearly documented as "for Phase N") from accidental orphans that
  will rot. Anything scaffolded but undocumented = flag it.
- **Consistency:** naming, file/responsibility boundaries, idiom vs the surrounding codebase,
  anything that will mislead the next editor.

### 4. Foundation soundness for the REMAINING Phase 3
The remaining work (NOT yet done): ① source `allowed_actions` from the registry inside the
**shared** `provider_agent` (+ a `day`→`day_vote` phase map); ② replace the `_resolve_*`
orchestration (provider calls / consensus / decision / emit) with a runtime orchestrator and
**delete** the old methods; ③ **hunter v1.1** (new board + `TriggerSystem` wired into the
death flow + a fake script) + `RoleContract` / `AgentContextPacket`.
- Will the current abstractions support this **cleanly**, or are there design issues that will
  force ugly workarounds (= rot)? Specifically:
  - Can registry/validator drive `provider_agent`'s prompt **without breaking
    `game_engine.py`**, which shares `provider_agent`?
  - Does the `TriggerSystem` handler contract support a `hunter_shoot` that needs a **provider
    call mid-trigger** (the handler signature is `(state, dead) -> list[str]` — is that enough,
    or does it need engine/agent access)?
  - Is the `shown_targets` / `legal_targets` split actually sufficient for the prompt swap?
- **Call out any design change that is cheaper to make NOW** (before the rewrite) than after.

### 5. Test quality
- Do tests pass for the right reasons? Any vacuous/tautological assertions? Does the parity
  harness actually *prove* parity, or could it pass while the settler is subtly wrong (it
  reconstructs intents from the engine's own output — is that circular)?

## Deliverable

Write a structured report to **`docs/harness/reviews/2026-06-09-action-runtime-audit-REPORT.md`**:

```
VERDICT: SOLID | SOLID_WITH_FIXES | FOUNDATION_NEEDS_WORK

BLOCKING — must fix before the remaining Phase 3 builds on this:
  (numbered; each = issue + file:line + why it rots/breaks + recommended fix)

ROBUSTNESS GAPS — untested/under-tested paths + the risky inputs you found:
  (numbered; with a concrete repro for anything that actually misbehaves)

ROT RISKS — duplicate sources of truth / half-swaps / orphaned code / drift hazards:
  (numbered; mark each temporary-by-design vs permanent)

FOUNDATION ASSESSMENT — is this a good base for ①②③ above? what to change NOW?

NON-BLOCKING — quality / naming / simplification.

CONFIDENCE — high/med/low + exactly what you verified (ran) vs only reasoned about.
```

## Rules of engagement

- Be concrete: cite real `file:line`, real values, real repro inputs. **Where you assert a
  behavior, prove it by running it** (a scratch probe), not by reasoning alone.
- Do **not** praise. Find problems. If an area is genuinely clean, say so explicitly — that is
  also signal.
- A reachable input where the new code diverges from the old engine is **BLOCKING**, full stop.
- Stay in your lane: read-only, frozen `69dd9bb`. The author is concurrently writing the
  remaining-Phase-3 *plan* (a doc) and will incorporate your report before touching code.
