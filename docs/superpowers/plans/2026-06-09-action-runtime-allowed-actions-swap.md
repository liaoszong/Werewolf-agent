# Phase 3 — allowed_actions source swap + delete the static map

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Make `RoleAbilityRegistry` the single source of `allowed_actions`; delete
`provider_agent.ALLOWED_ACTIONS_BY_ROLE_PHASE`. Closes audit **ROT #1** (two sources of
truth that can silently drift). Behavior-preserving (byte-identical prompts on the decide
path).

**Architecture:** `provider_agent.decide()` is the ONLY production consumer of the static map
(`provider_agent.py:108`; `game_engine.py` does not import `provider_agent` — audit B4-6, so
the scripted gold-game path cannot be affected). `decide()` is invoked only for wolf-kill /
seer-check / day-vote (the witch and speeches call `provider.respond()` directly, bypassing
`decide`). For those `(role, phase)` the registry's `allowed_actions` equals the static map,
so the prompt bytes are unchanged.

**THE TRAP (audit contract A / B4-1) — load-bearing:** the engine passes the external phase
string **`'day'`** to `decide()` for votes, but the registry only knows `'night'` / `'day_vote'`.
A naive `registry.allowed_actions(role, 'day')` returns **`[]`** (the registry was hardened to
degrade unknown phases to `[]` instead of `KeyError`) → `player_vote` would not be in
`allowed_actions` → `decide()` rejects every vote as `invalid_action` → **silent seeded
fallback on every day vote** (a silent leaderboard regression, no crash). The swap MUST map
`'day' → 'day_vote'` before the registry call.

**Tech Stack:** Python 3.12, `unittest` (`NO_PROXY='*' PYTHONPATH=src python -m unittest`).
Gate: full suite + `test_deterministic_same_seed_byte_identical` + `test_action_runtime_parity`
all green; the prompt for wolf/seer/vote byte-unchanged.

---

## File Structure

- Modify: `src/werewolf_eval/provider_agent.py` — `decide()` sources `allowed_actions` from a
  module-level registry with a `day→day_vote` map; delete `ALLOWED_ACTIONS_BY_ROLE_PHASE`.
- Modify: `tests/test_action_runtime_registry.py` — the parity test imports the (now-deleted)
  static map; re-pin it against hardcoded expected values.
- Modify: `tests/test_emergent_engine.py` — add a guard test that the day-vote path still
  yields a legal vote (not a silent fallback) — i.e. a clean game still has zero vote-related
  `invalid_action` failures.

No new files.

---

## Task 1: Pin the trap — a test that the day-vote path stays legal (write FIRST, must pass before + after)

This is the regression guard for contract A. It passes on `main` today (static map) and must
still pass after the swap; if the `day→day_vote` map is wrong, the clean villager-win game
gains a spurious vote `invalid_action` and this FAILS.

**Files:** Modify `tests/test_emergent_engine.py` (RobustnessTests).

- [ ] **Step 1: Write the test**

```python
    def test_clean_game_has_no_vote_invalid_action(self) -> None:
        # Contract A guard: the day-vote allowed_actions must include player_vote, so a clean
        # scripted game produces ZERO vote-phase invalid_action failures. If allowed_actions
        # for phase 'day' were ever empty (bad day->day_vote map), every vote would be
        # rejected -> this fails.
        outcome = _run(build_villager_win_script())
        self.assertEqual(outcome.status, "completed")
        vote_failures = [
            f for f in outcome.failure_audit["failures"]
            if f.get("phase") == "day" and f.get("kind") == "invalid_action"
        ]
        self.assertEqual(vote_failures, [], f"unexpected vote rejections: {vote_failures}")
```

- [ ] **Step 2: Run — must PASS now (pre-swap baseline)**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_emergent_engine.RobustnessTests.test_clean_game_has_no_vote_invalid_action -v`
Expected: PASS (the villager-win script votes legally today).

- [ ] **Step 3: Commit**

```bash
git add tests/test_emergent_engine.py
git commit -m "test(action-runtime): pin day-vote stays legal (contract A guard)"
```

---

## Task 2: Swap `decide()` to the registry + delete the static map

**Files:** Modify `src/werewolf_eval/provider_agent.py`.

- [ ] **Step 1: Add the module registry + phase map (top of file, after imports)**

```python
# provider_agent.py — near the top, after existing imports
from werewolf_eval.action_runtime import RoleAbilityRegistry, rules_v1

# Single source of allowed actions (replaces ALLOWED_ACTIONS_BY_ROLE_PHASE).
_ALLOWED_ACTIONS_REGISTRY = RoleAbilityRegistry(rules_v1())
# External engine phase -> registry phase. The engine emits 'day' for votes; the
# registry keys day votes under 'day_vote'. MUST map or every vote silently fails.
_REGISTRY_PHASE = {"day": "day_vote"}
```

> Circular-import check: `action_runtime` imports nothing from `provider_agent` (verified —
> only the registry *test* imports it), so this import is acyclic.

- [ ] **Step 2: Replace the static-map lookup in `decide()`**

Find (provider_agent.py:108):
```python
        allowed_actions = ALLOWED_ACTIONS_BY_ROLE_PHASE.get((role, phase), [])
```
Replace with:
```python
        allowed_actions = _ALLOWED_ACTIONS_REGISTRY.allowed_actions(
            role, _REGISTRY_PHASE.get(phase, phase)
        )
```

- [ ] **Step 3: Delete the static map definition**

Delete the whole `ALLOWED_ACTIONS_BY_ROLE_PHASE: dict[...] = { ... }` block
(provider_agent.py:19-27).

- [ ] **Step 4: Run the byte-determinism + differential + the Task-1 guard**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_emergent_engine.VillagerWinTests.test_deterministic_same_seed_byte_identical tests.test_action_runtime_parity tests.test_emergent_engine.RobustnessTests.test_clean_game_has_no_vote_invalid_action -v`
Expected: all PASS. (Determinism green = the wolf/seer/vote prompts + decisions are
byte-identical; the Task-1 guard green = the day→day_vote map is correct.)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/provider_agent.py
git commit -m "feat(action-runtime): source decide() allowed_actions from registry; delete static map"
```

---

## Task 3: Re-pin the registry parity test (it imported the deleted map)

**Files:** Modify `tests/test_action_runtime_registry.py`.

- [ ] **Step 1: Replace the import + the static-map-driven assertion**

Delete the import (`from werewolf_eval.provider_agent import ALLOWED_ACTIONS_BY_ROLE_PHASE`)
and replace the `test_allowed_actions_match_static_map_exactly` body with a hardcoded expected
contract (the registry is now the source of truth, so we pin its output directly):

```python
    def test_allowed_actions_pinned(self) -> None:
        # The registry IS the source of truth now; pin its full contract explicitly.
        expected = {
            ("werewolf", "night"): ["werewolf_kill"],
            ("seer", "night"): ["seer_check"],
            ("witch", "night"): ["witch_save", "witch_poison", "witch_pass"],
            ("werewolf", "day_vote"): ["player_vote"],
            ("seer", "day_vote"): ["player_vote"],
            ("witch", "day_vote"): ["player_vote"],
            ("villager", "day_vote"): ["player_vote"],
        }
        for (role, phase), want in expected.items():
            self.assertEqual(self.reg.allowed_actions(role, phase), want, f"{role}/{phase}")
```

- [ ] **Step 2: Run the registry tests**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_action_runtime_registry.py
git commit -m "test(action-runtime): pin registry allowed_actions directly (static map deleted)"
```

---

## Task 4: Acceptance gate — full suite + provider tests green

- [ ] **Step 1: Full suite**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests 2>&1 | grep -E "^(Ran|OK|FAILED)"`
Expected: `OK` (the same count as before, modulo the 1 new guard test). Zero real failures.
(Known env non-bugs: `test_observer_server.*` localhost-blocked; some `test_deepseek_*`
import-path — ignore.)

- [ ] **Step 2: Grep-confirm the static map is fully gone**

Run: `grep -rn "ALLOWED_ACTIONS_BY_ROLE_PHASE" src/ tests/`
Expected: **no hits** in `src/` or `tests/` (docs may still reference it historically — fine).

**Done when:** the registry is the sole `allowed_actions` source, the static map is deleted,
the day→day_vote map is in place + guarded, and the full suite + byte-determinism +
differential are green.

---

## Self-Review (writing-plans checklist)

- **Coverage:** contract A (day→day_vote) is the spine of Task 2 + guarded by Task 1; ROT #1
  (dual source) closed by Task 2/3; byte-safety gated by determinism + differential + the
  prompt-unchanged reasoning (decide is wolf/seer/vote only; witch/speech bypass it).
- **Placeholder scan:** all steps carry concrete code/commands.
- **Type/name consistency:** `_ALLOWED_ACTIONS_REGISTRY` / `_REGISTRY_PHASE` used consistently;
  `RoleAbilityRegistry.allowed_actions(role, phase)` signature matches Phase 1.
- **Risk note for the reviewer:** confirm `decide()` is never invoked with `(witch, night)`
  anywhere (the registry returns 3 witch-night actions vs the old map's 2; if decide *were*
  called for the witch the prompt would gain `witch_pass` → a divergence). The audit asserts
  the witch bypasses `decide`; the reviewer should re-verify by grepping callers of `.decide(`.
