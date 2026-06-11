# SYS-A2 Role Facts Single-Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `action_runtime/ruleset.py` the single declaration point for role→team facts; the three verbatim copies (`profile_config.ROLE_TEAMS`, `observer_visibility._KNOWN_ROLE_TEAMS`, `runtime_events._KNOWN_ROLE_TEAMS`) become derived, and sentinel tests make every remaining role touchpoint (product gate, night order, four vocab tables) impossible to drift silently.

**Architecture:** Ruleset is authoritative (adding a role = one `RoleDefinition`); `observer_protocol` re-exports the derived `KNOWN_ROLE_TEAMS` so observer-side modules keep importing protocol constants only (R-06 discipline). Vocab tables are deliberately separate vocabularies (prompt vs UI) and are NOT merged — coverage sentinels only. Full design rationale and rejected alternatives: `docs/adr/2026-06-11-role-facts-single-source.md`.

**Tech Stack:** Python 3.12, stdlib `unittest`, no new dependencies.

**Acceptance bar (user decision, 2026-06-11): byte-identical.** `tests/test_emergent_ledger_golden.py`, `tests/test_rng_draw_order.py`, all prompt_v1/v2 golden tests, and the witch one-shot sentinels must pass UNCHANGED. No model-visible prompt byte changes anywhere (we do not touch `prompt_v2.py` source — sentinels only read it).

---

## Execution context

- **Worktree:** isolated worktree, branch `sys-a2-role-single-source` (use superpowers:using-git-worktrees). THREE Claude instances develop in parallel — never work in the shared main checkout.
- **Skills to read first:** `.agents/skills/committing-in-shared-worktrees/SKILL.md`, `.agents/skills/testing-and-process-control/SKILL.md`.
- **File ownership (parallel-track boundary):** this plan may touch ONLY:
  `src/werewolf_eval/action_runtime/ruleset.py` · `src/werewolf_eval/observer_protocol.py` · `src/werewolf_eval/observer_visibility.py` · `src/werewolf_eval/runtime_events.py` · `src/werewolf_eval/profile_config.py` · `src/werewolf_eval/display_labels.py` · `tests/test_role_single_source.py` (new).
  FORBIDDEN (other tracks / engine line): `observer_server.py`, `run_*.py`, `deepseek_launcher.py`, `pyproject.toml`, `emergent_engine.py`, `prompt_v2.py`, `llm_providers.py`, `scoring.py`, `game_engine.py`.
- **Test command (bash):** `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` — full suite expected baseline: all OK (post-B4 main = 1085 OK).
- **Do not merge or push main yourself.** Finish on the branch, produce a merge-readiness report (commits, full-suite evidence, `git merge-tree` conflict check vs main). Merges across the three tracks are serialized by the user.
- **New file added → run** `node .codex/hooks/tree.mjs --force` (Task 8).

## Non-goals (decided in design review, do not "improve" these)

1. `NIGHT_DISPATCH_ORDER` stays an engine constant — night-order datafication belongs to NightPlan (SYS-A1, waits for the guard role). Sentinel only.
2. `ALLOWED_ROLES` stays an explicit hand-written product gate — new roles do NOT auto-appear in the launch UI. Sentinel only.
3. The two Chinese vocabularies stay physically separate: `prompt_v2` says 村民/好人阵营 (model-facing, byte-locked), `display_labels` says 平民/村民阵营 (UI-facing). Coverage sentinels only — never merge.
4. `observer_visibility.ROLE_SPECIFIC_EVENT_VISIBILITIES` (`{"seer","witch"}`) is SYS-A4 visibility behavior, untouched.
5. `game_engine.py` (legacy scripted engine) untouched. `emergent_engine._RESOLVERS` untouched (behavior wiring, not data).

---

### Task 1: `known_role_teams()` — the single source

**Files:**
- Modify: `src/werewolf_eval/action_runtime/ruleset.py` (append after `rules_v1_1`, ~line 86)
- Test: `tests/test_role_single_source.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_role_single_source.py`:

```python
"""SYS-A2 role single-source sentinels (ADR 2026-06-11-role-facts-single-source).

known_role_teams() is THE source of role->team facts. The three former verbatim
copies (profile_config.ROLE_TEAMS / observer_visibility._KNOWN_ROLE_TEAMS /
runtime_events._KNOWN_ROLE_TEAMS) derive from it via observer_protocol, so a
role added to a ruleset can never be missing from a projection table again
(a wolf-side role missing from those tables would default to team "villager"
and LEAK its role string to villager observers instead of "unknown")."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import (  # noqa: E402
    all_rulesets,
    known_role_teams,
    rules_v1_1,
)


class KnownRoleTeamsTest(unittest.TestCase):
    def test_union_over_all_rulesets_in_declaration_order(self) -> None:
        self.assertEqual(
            known_role_teams(),
            {
                "werewolf": "werewolf",
                "seer": "villager",
                "witch": "villager",
                "villager": "villager",
                "hunter": "villager",
            },
        )
        # Insertion order is load-bearing: profile_config.ROLE_TEAMS derives
        # from this and is serialized into the capabilities payload
        # (profile_config.py:480), where dict order = byte order.
        self.assertEqual(
            list(known_role_teams()),
            ["werewolf", "seer", "witch", "villager", "hunter"],
        )

    def test_all_rulesets_is_append_only(self) -> None:
        # Observers must recognize roles from logs of ANY shipped rules version.
        self.assertEqual(
            [rs.rules_version for rs in all_rulesets()],
            ["rules_v1", "rules_v1_1"],
        )


if __name__ == "__main__":
    unittest.main()
```

Note: check how existing test files in `tests/` handle imports first (many use `sys.path.insert` boilerplate as shown; mirror the local convention — `git grep -l "sys.path.insert" tests/ | head -3` and copy the exact pattern).

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: ERROR — `ImportError: cannot import name 'all_rulesets'`

- [ ] **Step 3: Implement in `ruleset.py`**

Append after `rules_v1_1()`:

```python
def all_rulesets() -> tuple[BoardRuleset, ...]:
    """Every ruleset this codebase has ever shipped. APPEND-ONLY: observer-side
    consumers derive role->team knowledge from this union, and must keep
    recognizing roles from logs written under ANY rules version."""
    return (rules_v1(), rules_v1_1())


def known_role_teams() -> dict[str, str]:
    """role -> team, union over all_rulesets(), in declaration order.

    THE single source of role->team facts (ADR 2026-06-11): observer_protocol
    re-exports this for observer-side modules; profile_config derives its gated
    ROLE_TEAMS projection from it. A role may not change team across rulesets —
    fail loud instead of silently picking one."""
    teams: dict[str, str] = {}
    for rs in all_rulesets():
        for role_def in rs.roles:
            existing = teams.get(role_def.role)
            if existing is not None and existing != role_def.team:
                raise ValueError(
                    f"role {role_def.role!r} maps to both {existing!r} and "
                    f"{role_def.team!r} across rulesets"
                )
            teams[role_def.role] = role_def.team
    return teams
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: 2 tests, OK

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/ruleset.py tests/test_role_single_source.py
git commit -m "refactor(a2): known_role_teams() union — ruleset is the single source of role->team facts"
```

---

### Task 2: `observer_protocol` re-export (the protocol-side seam)

**Files:**
- Modify: `src/werewolf_eval/observer_protocol.py` (imports are stdlib-only at lines 7-13; add after them)
- Test: `tests/test_role_single_source.py` (extend)

- [ ] **Step 1: Write the failing test** (append to `tests/test_role_single_source.py`)

```python
class ProtocolReExportTest(unittest.TestCase):
    def test_protocol_table_is_the_ruleset_projection(self) -> None:
        from werewolf_eval import observer_protocol

        self.assertEqual(observer_protocol.KNOWN_ROLE_TEAMS, known_role_teams())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: FAIL — `AttributeError: module 'werewolf_eval.observer_protocol' has no attribute 'KNOWN_ROLE_TEAMS'`

- [ ] **Step 3: Implement in `observer_protocol.py`**

After the stdlib imports (line 13), add:

```python
from werewolf_eval.action_runtime.ruleset import known_role_teams

# Role -> team facts, derived from the ruleset (the authoritative declaration,
# ADR 2026-06-11). Re-exported HERE so observer-side modules keep importing
# protocol constants only (same R-06 discipline as PUBLIC_LIKE_EVENT_VISIBILITIES)
# and never import action_runtime directly.
KNOWN_ROLE_TEAMS: dict[str, str] = known_role_teams()
```

- [ ] **Step 4: Run test + import-cycle smoke**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: 3 tests, OK

Run: `PYTHONPATH=src python -c "import werewolf_eval.observer_protocol, werewolf_eval.observer_visibility, werewolf_eval.runtime_events, werewolf_eval.profile_config, werewolf_eval.observer_server; print('no import cycle')"`
Expected: `no import cycle` (action_runtime imports nothing outside itself, so protocol→ruleset cannot cycle)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/observer_protocol.py tests/test_role_single_source.py
git commit -m "refactor(a2): observer_protocol re-exports KNOWN_ROLE_TEAMS (R-06 seam, observer import surface unchanged)"
```

---

### Task 3: `observer_visibility` derives its table

**Files:**
- Modify: `src/werewolf_eval/observer_visibility.py` (delete literal dict at lines 35-40; extend the existing observer_protocol import)
- Test: `tests/test_role_single_source.py` (extend)

Background for the executor: the table's ONLY consumer is `observer_visibility.py:413` — `display_team = _KNOWN_ROLE_TEAMS.get(known_role, "villager")` — a pure lookup, so dict insertion order is irrelevant here. The derived table adds `"hunter": "villager"`, and the previous `.get` default for the missing hunter key was ALSO `"villager"`, so behavior is identical even on hunter boards.

- [ ] **Step 1: Write the failing test** (append)

```python
class DerivedCopiesTest(unittest.TestCase):
    def test_observer_visibility_table_is_the_protocol_object(self) -> None:
        from werewolf_eval import observer_protocol, observer_visibility

        self.assertIs(
            observer_visibility._KNOWN_ROLE_TEAMS,
            observer_protocol.KNOWN_ROLE_TEAMS,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: FAIL — the literal dict is a different object (`assertIs` fails)

- [ ] **Step 3: Implement**

In `observer_visibility.py`: find the existing `from werewolf_eval.observer_protocol import (...)` block (it already imports `PUBLIC_LIKE_EVENT_VISIBILITIES` etc. per the comment at lines 30-31) and add `KNOWN_ROLE_TEAMS as _KNOWN_ROLE_TEAMS` to it. Delete the literal dict at lines 35-40:

```python
# DELETE:
_KNOWN_ROLE_TEAMS: dict[str, str] = {
    "villager": "villager",
    "seer": "villager",
    "witch": "villager",
    "werewolf": "werewolf",
}
```

The internal reference at line 413 keeps working unchanged via the import alias.

- [ ] **Step 4: Run tests**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: OK

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_observer*.py" && NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_visibility*.py"`
Expected: all OK (visibility parity / invariant tests are the SYS-A4 net)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/observer_visibility.py tests/test_role_single_source.py
git commit -m "refactor(a2): observer_visibility derives _KNOWN_ROLE_TEAMS from protocol (copy 1/3 deleted)"
```

---

### Task 4: `runtime_events` derives its table

**Files:**
- Modify: `src/werewolf_eval/runtime_events.py` (delete literal dict at lines 455-460; add import — current imports are stdlib-only at lines 8-16)
- Test: `tests/test_role_single_source.py` (extend)

Background: only consumer is `runtime_events.py:478` — `team = _KNOWN_ROLE_TEAMS.get(role, "villager")` inside `_project_known_roles_for_observer`. Same pure-lookup argument as Task 3: hunter addition is behavior-neutral.

- [ ] **Step 1: Write the failing test** (append to `DerivedCopiesTest`)

```python
    def test_runtime_events_table_is_the_protocol_object(self) -> None:
        from werewolf_eval import observer_protocol, runtime_events

        self.assertIs(
            runtime_events._KNOWN_ROLE_TEAMS,
            observer_protocol.KNOWN_ROLE_TEAMS,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: FAIL (`assertIs`)

- [ ] **Step 3: Implement**

In `runtime_events.py`, after the stdlib imports (line 16) add:

```python
from werewolf_eval.observer_protocol import KNOWN_ROLE_TEAMS as _KNOWN_ROLE_TEAMS
```

Delete the literal dict at lines 455-460 (keep the section comment above it if any). The reference at line 478 keeps working.

- [ ] **Step 4: Run tests — including the byte gates**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: OK

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_runtime*.py" && NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_emergent_ledger_golden tests.test_rng_draw_order -v`
Expected: all OK — the ledger golden is the byte oracle for snapshot/event output

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/runtime_events.py tests/test_role_single_source.py
git commit -m "refactor(a2): runtime_events derives _KNOWN_ROLE_TEAMS from protocol (copy 2/3 deleted)"
```

---

### Task 5: `profile_config.ROLE_TEAMS` becomes a gated projection

**Files:**
- Modify: `src/werewolf_eval/profile_config.py` (replace literal dict at lines 57-62; add import at top)
- Test: `tests/test_role_single_source.py` (extend)

Background: TWO consumers — `profile_config.py:253` (`"team": ROLE_TEAMS[role]`, strict lookup) and `:480` (`"role_teams": dict(ROLE_TEAMS)` serialized into the capabilities payload, where **insertion order = response bytes**). Current insertion order werewolf, seer, witch, villager happens to equal ruleset declaration order, so a declaration-order-preserving derivation is byte-identical. `ALLOWED_ROLES` (line 50) is the explicit product gate and is NOT changed (design decision: new roles do not auto-appear in the launch UI).

- [ ] **Step 1: Write the failing test** (append)

```python
class ProfileRoleTeamsTest(unittest.TestCase):
    def test_role_teams_is_gated_projection_with_pinned_order(self) -> None:
        from werewolf_eval import profile_config

        self.assertEqual(
            profile_config.ROLE_TEAMS,
            {
                "werewolf": "werewolf",
                "seer": "villager",
                "witch": "villager",
                "villager": "villager",
            },
        )
        # Pinned insertion order: serialized into the capabilities payload
        # (profile_config.py:480) — dict order is byte order there.
        self.assertEqual(
            list(profile_config.ROLE_TEAMS),
            ["werewolf", "seer", "witch", "villager"],
        )
        # The projection never invents a role outside the product gate.
        self.assertEqual(
            set(profile_config.ROLE_TEAMS), set(profile_config.ALLOWED_ROLES)
        )
```

- [ ] **Step 2: Run test to verify it passes against the CURRENT literal (pin first)**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: OK — this test pins today's bytes BEFORE the swap, so Step 3's refactor is proven byte-preserving by an already-green test (test-first here means pin-first: the test must never go red across the swap).

- [ ] **Step 3: Implement the derivation**

In `profile_config.py`, add to the top import block:

```python
from werewolf_eval.action_runtime.ruleset import known_role_teams
```

Replace lines 57-62:

```python
# DELETE:
ROLE_TEAMS: dict[str, str] = {
    "werewolf": "werewolf",
    "seer": "villager",
    "witch": "villager",
    "villager": "villager",
}

# REPLACE WITH:
# Derived projection of the single source (ADR 2026-06-11), restricted to the
# product gate. Iteration follows ruleset declaration order, which keeps the
# capabilities payload (":480") byte-identical: werewolf, seer, witch, villager.
ROLE_TEAMS: dict[str, str] = {
    role: team for role, team in known_role_teams().items() if role in ALLOWED_ROLES
}
```

(`ALLOWED_ROLES` is defined at line 50, above this — order of definitions already works.)

- [ ] **Step 4: Run tests**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: OK (still green across the swap)

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_profile*.py"`
Expected: all OK

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/profile_config.py tests/test_role_single_source.py
git commit -m "refactor(a2): profile_config.ROLE_TEAMS = gated projection of known_role_teams (copy 3/3 deleted)"
```

---

### Task 6: gate + night-order sentinels

**Files:**
- Test: `tests/test_role_single_source.py` (extend; no src changes)

These are regression guards (expected green on arrival): they don't drive new code, they make the two deliberate non-derivations (`ALLOWED_ROLES`, `NIGHT_DISPATCH_ORDER`) impossible to drift silently.

- [ ] **Step 1: Add the sentinels**

```python
class GateAndOrderSentinelTest(unittest.TestCase):
    def test_product_gate_is_subset_of_ruleset_roles(self) -> None:
        # ALLOWED_ROLES is a deliberate explicit allowlist (new roles do NOT
        # auto-appear in the launch UI) — but it may never invent a role the
        # ruleset doesn't have.
        from werewolf_eval import profile_config

        self.assertLessEqual(
            set(profile_config.ALLOWED_ROLES), set(known_role_teams())
        )

    def test_night_dispatch_order_is_subset_of_ruleset_night_abilities(self) -> None:
        # NIGHT_DISPATCH_ORDER stays engine data until NightPlan (SYS-A1);
        # this sentinel only forbids it referencing an ability the ruleset
        # doesn't declare as phase:night.
        from werewolf_eval.emergent_engine import NIGHT_DISPATCH_ORDER

        night_ids = {
            a.action_id
            for a in rules_v1_1().abilities
            if a.trigger == "phase:night"
        }
        self.assertLessEqual(set(NIGHT_DISPATCH_ORDER), night_ids)
```

- [ ] **Step 2: Run + bite-check**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: OK

Bite-check (prove the sentinel can fail) without touching src:

```bash
PYTHONPATH=src python -c "
from werewolf_eval.action_runtime.ruleset import known_role_teams
assert not ({'guard'} <= set(known_role_teams())), 'guard must be unknown today'
print('sentinel would catch an ungated role: OK')"
```
Expected: `sentinel would catch an ungated role: OK`

- [ ] **Step 3: Commit**

```bash
git add tests/test_role_single_source.py
git commit -m "test(a2): gate/night-order sentinels (ALLOWED_ROLES ⊆ roles, DISPATCH_ORDER ⊆ night abilities)"
```

---

### Task 7: vocab completeness sentinels (expected RED → fix `display_labels`)

**Files:**
- Modify: `src/werewolf_eval/display_labels.py` (ROLE_LABELS at lines 10-15, TYPE_LABELS at lines 29-43)
- Test: `tests/test_role_single_source.py` (extend)

Background: the two vocabularies are DELIBERATELY different (prompt_v2: 村民/好人阵营, model-facing, byte-locked by goldens; display_labels: 平民/村民阵营, UI-facing) and must NOT be merged. The sentinels force COVERAGE only. Known gap they will expose: `display_labels` has no `hunter` / `hunter_shoot` / `hunter_pass` entries (same i18n-gap class as R-28 — hunter boards currently render raw English tokens in renderers/Qt). `prompt_v2` tables are already complete (hunter present) — that file is READ ONLY here, never modified.

- [ ] **Step 1: Write the sentinels**

```python
class VocabCompletenessSentinelTest(unittest.TestCase):
    """Coverage-only sentinels. The prompt and display vocabularies are
    deliberately different wordings and must never be merged (prompt bytes are
    golden-locked); these tests only guarantee no role/team/ability that a
    ruleset can put on a board is missing a word in either vocabulary."""

    def test_prompt_tables_cover_all_rulesets(self) -> None:
        from werewolf_eval import prompt_v2

        for rs in all_rulesets():
            for role_def in rs.roles:
                self.assertIn(role_def.role, prompt_v2.ROLE_NAMES_ZH)
                self.assertIn(role_def.team, prompt_v2.TEAM_NAMES_ZH)
            for ability in rs.abilities:
                self.assertIn(ability.action_id, prompt_v2.ABILITY_DESCRIPTIONS)

    def test_display_tables_cover_all_rulesets(self) -> None:
        from werewolf_eval import display_labels

        for rs in all_rulesets():
            for role_def in rs.roles:
                self.assertIn(role_def.role, display_labels.ROLE_LABELS)
                self.assertIn(role_def.team, display_labels.TEAM_LABELS)
            for ability in rs.abilities:
                self.assertIn(ability.action_id, display_labels.TYPE_LABELS)
```

- [ ] **Step 2: Run to verify the expected RED**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: `test_prompt_tables_cover_all_rulesets` PASS; `test_display_tables_cover_all_rulesets` FAIL with `'hunter' not found in {...ROLE_LABELS...}`

- [ ] **Step 3: Fix `display_labels.py` (additive only)**

In `ROLE_LABELS` (lines 10-15) add:

```python
    "hunter": "猎人",
```

In `TYPE_LABELS` (lines 29-43) add (wording consistent with the existing `witch_pass: 女巫弃药` pattern):

```python
    "hunter_shoot": "猎人开枪",
    "hunter_pass": "猎人弃枪",
```

Additive keys only: existing 4-role outputs are byte-identical; hunter logs previously rendered raw `hunter`/`hunter_shoot` tokens (bug, same class as R-28).

- [ ] **Step 4: Run tests**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest tests.test_role_single_source -v`
Expected: all OK

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_render*.py" && NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_display*.py"`
Expected: all OK (additive keys don't change existing rendered output)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/display_labels.py tests/test_role_single_source.py
git commit -m "test(a2): vocab completeness sentinels ×4 tables; fix hunter i18n gap in display_labels (R-28 class)"
```

---

### Task 8: full-suite byte gate + merge-readiness report

**Files:** none modified (verification only; `.oh-my-harness/tree.md` regenerated by hook)

- [ ] **Step 1: Tree hook for the new test file**

Run: `node .codex/hooks/tree.mjs --force`

```bash
git add .oh-my-harness/tree.md
git commit -m "chore(a2): tree refresh for tests/test_role_single_source.py"
```

(Skip the commit if the hook reports no change.)

- [ ] **Step 2: Full suite**

Run: `NO_PROXY=localhost,127.0.0.1 PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
Expected: all OK, count ≥ 1085 + new tests (post-B4 baseline 1085). Golden/byte gates inside the suite that MUST be green: `test_emergent_ledger_golden`, `test_rng_draw_order`, prompt_v1/v2 golden tests (proof no model-visible byte moved), witch one-shot sentinels.

- [ ] **Step 3: Validation report (AGENTS.md checklist)**

Produce and include in the merge-readiness report:

```bash
git diff --stat main...HEAD
git diff --name-only main...HEAD
git merge-tree $(git merge-base main HEAD) main HEAD   # expect no conflict markers
```

- Allowlist check: changed files ⊆ the 7 allowed paths (6 src + 1 test) + `.oh-my-harness/tree.md`.
- Forbidden-scope check: NO changes to `observer_server.py`, `run_*.py`, `pyproject.toml`, `emergent_engine.py`, `prompt_v2.py`, `llm_providers.py`, `docs/ROADMAP.md`, `docs/TASKS.md`, `.github/**`, `.agents/skills/**`.
- Stop on the branch. Report merge readiness to the user; do NOT merge/push (three parallel tracks, user serializes merges).
