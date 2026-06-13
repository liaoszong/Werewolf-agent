# Audit Non-Gated Remainder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) tracking.

**Goal:** Close the genuinely-open, non-gated items from `docs/health-check/2026-06-12-system-view-audit.md` that survive a fresh re-verification of main `e389750`.

**Context / re-verification finding:** The audit's status tables are stale. Re-checking current main shows **A45-7, C12-06, C3-5, A45-2 are already fixed** (decision request_id is plumbed through `_decision`; enrichment uses a composite `(round,phase,actor,action,target)` key; `tests/test_settler_guard_oracle.py` is a full independent guard oracle; observer projection is already set-driven). The only genuinely-open, non-gated, worthwhile items are the four below. Explicitly deferred (out of scope, with reasons): **A-5** (gated on a non-existent `rules_v1_3`; `rules_v1_2` superset is safe now — YAGNI), **A45-9 / A45-12** (P2 semantic; consensus is synthetic *by design*).

**Architecture:** Two real code changes (one product-safety fail-loud, one regression-lock sentinel) plus two doc/docstring corrections. Scope is confined to `src/werewolf_eval/run_emergent_deepseek_game.py`, a new test, `src/werewolf_eval/observer_projection.py` (docstring only), and `docs/PROJECT_MAP.md`. No runtime/scoring/provider/model-visible-prompt/log-contract behavior changes beyond the new fail-loud.

**Tech Stack:** Python 3.12, unittest. Tests run `PYTHONPATH="src;tests" python -m unittest <module>` (Windows bash).

---

### Task 1: B12-04 — guard board + non-scaffold renderer fails loud

**Why:** Product launchers default `prompt_version="prompt_v1"`. `prompt_v1`/`prompt_v2` (`requires_scaffold == False`) render no rules card and have no guard persona, so a guard board launched on them silently degrades into mass invalid-action fallback. `prompt_v3`/`prompt_v4` (`requires_scaffold == True`) carry the guard rules card. `run_emergent_deepseek_game` is the single chokepoint both product launchers route through.

**Files:**
- Modify: `src/werewolf_eval/run_emergent_deepseek_game.py` (the `run_emergent_deepseek_game` fail-loud preamble, ~lines 162-167)
- Test: `tests/test_b1204_guard_prompt_floor.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""B12-04: a guard board on a non-scaffold renderer (prompt_v1/v2) must fail loud
before any side effects — v1/v2 carry no guard rules card, so the live game would
silently degrade into mass invalid-action fallback."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game

GUARD_BOARD = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
               "p4": "witch", "p5": "guard", "p6": "villager"}


def _factory(_pid):
    raise AssertionError("provider factory must not be called: fail-loud precedes side effects")


class GuardPromptFloorTests(unittest.TestCase):
    def test_guard_board_v1_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_emergent_deepseek_game(
                game_id="b1204_v1", out_dir=ROOT / ".tmp_should_not_exist",
                provider_factory=_factory, model="m", seat_roles=GUARD_BOARD,
                prompt_version="prompt_v1",
            )
        self.assertIn("guard", str(ctx.exception).lower())
        self.assertIn("prompt_v1", str(ctx.exception))

    def test_guard_board_v2_raises(self):
        with self.assertRaises(ValueError):
            run_emergent_deepseek_game(
                game_id="b1204_v2", out_dir=ROOT / ".tmp_should_not_exist",
                provider_factory=_factory, model="m", seat_roles=GUARD_BOARD,
                prompt_version="prompt_v2",
            )

    def test_non_guard_board_v1_does_not_raise_on_floor(self):
        # No guard on the board: the floor must not fire. (It may still fail later
        # on the fake factory, but NOT with the guard-floor message.)
        try:
            run_emergent_deepseek_game(
                game_id="b1204_ok", out_dir=ROOT / ".tmp_should_not_exist",
                provider_factory=_factory, model="m", seat_roles=None,
                prompt_version="prompt_v1",
            )
        except ValueError as e:
            self.assertNotIn("rules card", str(e).lower())
        except AssertionError:
            pass  # reached the provider factory => floor correctly did not fire


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="src;tests" python -m unittest test_b1204_guard_prompt_floor -v`
Expected: `test_guard_board_v1_raises` / `_v2_raises` FAIL (no ValueError raised — the game proceeds to the provider factory and AssertionErrors instead).

- [ ] **Step 3: Add the fail-loud floor**

In `run_emergent_deepseek_game`, hoist config construction ahead of the existing scaffold fail-loud and add the guard floor. Replace the preamble:

```python
    # Fail-loud before any side effects (writer/engine construction).
    renderer = get_renderer(prompt_version)
    config = build_emergent_config(game_id=game_id, seat_roles=seat_roles)
    board_roles = {p.role for p in config.players}
    if "guard" in board_roles and not renderer.requires_scaffold:
        raise ValueError(
            f"guard board requires a scaffold-based renderer (prompt_v3+) that carries "
            f"the guard rules card; prompt_version={prompt_version!r} has none — no rules "
            f"card / empty guard persona would degrade the live game into invalid-action "
            f"fallback (B12-04). Set prompt_version to prompt_v3."
        )
    scaffold_agent = None
    if renderer.requires_scaffold:
        if scaffold_provider_factory is None:
            raise ValueError(f"{prompt_version} requires scaffold_provider_factory (scribe provider)")
        scaffold_agent = scaffold_provider_factory()
```

Then reuse the hoisted `config` at the engine construction site (replace the inline `config=build_emergent_config(...)` with `config=config`).

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="src;tests" python -m unittest test_b1204_guard_prompt_floor -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Regression — guard arm still launches on v3**

Run: `PYTHONPATH="src;tests" python -m unittest test_guard_sentinels test_l4_arm_layout test_emergent_engine -v 2>&1 | tail -3`
Expected: OK (guard boards there use prompt_v3 → floor does not fire).

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/run_emergent_deepseek_game.py tests/test_b1204_guard_prompt_floor.py
git commit -m "fix(B12-04): guard board on non-scaffold renderer (v1/v2) fails loud"
```

---

### Task 2: A45-3 — two-side visibility sentinel

**Why:** The engine (`role_visibility.private_refs_for_role`) generalizes private visibility to any role (`v == role`); the observer (`observer_projection.ROLE_SPECIFIC_EVENT_VISIBILITIES`) enumerates a frozenset. Nothing locks the two in sync, so adding a new private-vision role could pass the engine side but silently under-share on the observer side (the audit's A45-3). This sentinel ties the observer frozenset to the canonical `EVENT_TYPE_REQUIRED_VISIBILITY` map (the R-17 drift gate, already enforced against real games) and asserts both engine and observer honor every role-private visibility.

**Files:**
- Test: `tests/test_visibility_two_side_sentinel.py` (create)

- [ ] **Step 1: Write the sentinel test**

```python
"""A45-3: lock the observer's role-private visibility frozenset in sync with the
canonical event->visibility map AND with the engine's generalized private-ref logic.
Adding a new private-vision role must update both sides or this fails."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.observer_projection import (
    ROLE_SPECIFIC_EVENT_VISIBILITIES,
    PUBLIC_LIKE_EVENT_VISIBILITIES,
    event_visible_in_projection,
)
from werewolf_eval.role_visibility import private_refs_for_role
from test_event_visibility_invariant import EVENT_TYPE_REQUIRED_VISIBILITY

# Role-private visibilities derived from the canonical map: drop public-like and the
# werewolf-team channel (handled separately). The remainder are single-role private.
EXPECTED_ROLE_PRIVATE = {
    v for v in EVENT_TYPE_REQUIRED_VISIBILITY.values()
    if v not in PUBLIC_LIKE_EVENT_VISIBILITIES and v != "werewolf_team"
}

SEATS = ["seer", "witch", "guard", "werewolf", "villager", "hunter"]


def _seat_index():
    idx = {}
    for i, role in enumerate(SEATS, start=1):
        team = "werewolf" if role == "werewolf" else "villager"
        idx[f"p{i}"] = {"display_role": role, "display_team": team}
    return idx


class TwoSideVisibilitySentinel(unittest.TestCase):
    def test_observer_frozenset_matches_canonical_map(self):
        self.assertEqual(
            ROLE_SPECIFIC_EVENT_VISIBILITIES, EXPECTED_ROLE_PRIVATE,
            "observer ROLE_SPECIFIC_EVENT_VISIBILITIES drifted from the canonical "
            "EVENT_TYPE_REQUIRED_VISIBILITY map — add the new role-private visibility "
            "to BOTH or fix the map",
        )

    def test_observer_and_engine_agree_per_role_private_visibility(self):
        idx = _seat_index()
        role_to_seat = {entry["display_role"]: pid for pid, entry in idx.items()}
        for vis in sorted(EXPECTED_ROLE_PRIVATE):
            owner_seat = role_to_seat[vis]
            event = {"event_id": f"e_{vis}", "visibility": vis,
                     "type": f"{vis}_check", "actor": owner_seat}
            # Observer: only the owning role's seat sees it.
            for pid in idx:
                visible, _ = event_visible_in_projection(event, f"role:{pid}", idx)
                self.assertEqual(visible, pid == owner_seat,
                                 f"observer {pid} vis={vis}")
            # Engine: private_refs_for_role includes it for the owning role only.
            ev = {"event_id": event["event_id"], "visibility": vis}
            self.assertIn(event["event_id"], private_refs_for_role([ev], vis),
                          f"engine owner role={vis}")
            for role in SEATS:
                if role != vis and role != "werewolf":
                    self.assertNotIn(event["event_id"], private_refs_for_role([ev], role),
                                     f"engine non-owner role={role} vis={vis}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the sentinel**

Run: `PYTHONPATH="src;tests" python -m unittest test_visibility_two_side_sentinel -v`
Expected: PASS (current behavior is correct; this is a regression lock). If `PUBLIC_LIKE_EVENT_VISIBILITIES` is not exported from `observer_projection`, import it from `observer_protocol` instead and adjust.

- [ ] **Step 3: Verify it actually bites (manual scratch check, do NOT commit)**

Temporarily add a bogus `"knight"` to `EVENT_TYPE_REQUIRED_VISIBILITY` in a scratch copy and confirm `test_observer_frozenset_matches_canonical_map` fails. Revert.

- [ ] **Step 4: Commit**

```bash
git add tests/test_visibility_two_side_sentinel.py
git commit -m "test(A45-3): two-side visibility sentinel (observer frozenset <-> canonical map <-> engine)"
```

---

### Task 3: A45-11 — observer projection docstring lists guard_event

**Files:**
- Modify: `src/werewolf_eval/observer_projection.py` (`event_visible_in_projection` docstring, ~line 254)

- [ ] **Step 1: Fix the docstring**

Change the reasons line from:

```
    Reasons: ``god_view``, ``public_event``, ``seer_event``, ``witch_event``,
    ``werewolf_team_event``, ``hidden``.
```

to:

```
    Reasons: ``god_view``, ``public_event``, ``seer_event``, ``witch_event``,
    ``guard_event``, ``werewolf_team_event``, ``hidden``.
```

- [ ] **Step 2: Verify no test pins the old docstring**

Run: `PYTHONPATH="src;tests" python -m unittest test_observer_protocol test_role_single_source -v 2>&1 | tail -3`
Expected: OK.

- [ ] **Step 3: Commit**

```bash
git add src/werewolf_eval/observer_projection.py
git commit -m "docs(A45-11): list guard_event in event_visible_in_projection docstring"
```

---

### Task 4: B34-09 — PROJECT_MAP enabled_scaffolds wording

**Why:** `docs/PROJECT_MAP.md:123` claims the manifest has an `enabled_scaffolds` field; a repo-wide grep finds it only in docs. The real seam is `requires_scaffold` (renderer flag) + `scaffold_model`.

**Files:**
- Modify: `docs/PROJECT_MAP.md` (~line 123)

- [ ] **Step 1: Correct the wording**

Replace the stale claim that `enabled_scaffolds` "已留" with a note that the actual seam is the renderer `requires_scaffold` flag plus `scaffold_model`, and that no `enabled_scaffolds` field exists.

- [ ] **Step 2: Verify the stale token is gone from code-claim context**

Run: `grep -rn "enabled_scaffolds" docs/PROJECT_MAP.md` — expect the wording now describes it as the *not-implemented* name, pointing at `requires_scaffold`/`scaffold_model`.

- [ ] **Step 3: Commit**

```bash
git add docs/PROJECT_MAP.md
git commit -m "docs(B34-09): correct stale enabled_scaffolds claim to requires_scaffold/scaffold_model"
```

---

## Self-Review Notes

- Spec coverage: B12-04 / A45-3 / A45-11 / B34-09 each have a task. Already-fixed (A45-7, C12-06, C3-5, A45-2) and deferred (A-5, A45-9, A45-12) are documented above, not tasked.
- Type consistency: `run_emergent_deepseek_game` signature unchanged; `config`/`renderer` reused after hoist. `private_refs_for_role(events, role)` and `event_visible_in_projection(event, perspective, seat_index)` signatures match the source verified at plan time.
- Forbidden-scope: no changes to ROADMAP/TASKS/adr/historical plans/demo/generated/gold/.agents/skills/.github. PROJECT_MAP.md is the phase-authority doc and is the explicit target of B34-09.
