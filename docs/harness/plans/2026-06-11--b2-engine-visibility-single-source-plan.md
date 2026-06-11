# B-2 Engine Visibility Single Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the three engine-side copies of the role-visibility filtering rule into one shared pure module (`role_visibility.py`), byte-identically, per ADR `docs/adr/2026-06-11-engine-visibility-single-source.md` (committed alongside this plan).

**Architecture:** New leaf module `src/werewolf_eval/role_visibility.py` with two pure functions (`public_refs`, `private_refs_for_role`) — the rule verbatim. `GameEngine` (observation_for + scripted-arc closures + 2 inline comprehensions) and `EmergentGameEngine` (`_public_refs`/`_private_refs`) delegate to it. Observation *assembly* stays per-engine. The observer/oracle witness boundary (SYS-A4/I4b) is locked by a sentinel test. Byte-identity is gated three ways: predicate moved verbatim, existing fixture/invariant suites, and a before/after artifact byte-snapshot of the deterministic fake runners.

**Tech Stack:** Python 3.12 stdlib, unittest-style tests. Test command (both prefixes mandatory):

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q
```

**Coordination constraint:** another agent is running T17 (45 live games) from the main checkout. All work stays in this isolated worktree; **the final merge to main is HELD until the T17 batch finishes** (byte-identity makes a mid-batch merge theoretically safe, but we don't gamble with a live ablation arm).

**Verified facts this plan rests on (read on main `6512bc8`, 2026-06-11):**
- The three copies:
  - `game_engine.py:269-292` `observation_for` — one pass building `public_event_ids` (`visibility in ("public","all")`) and `private_event_ids` (`=="all"` also goes private; `== player.role`; `=="werewolf_team"` for werewolf).
  - `game_engine.py:553-569` closures `_public_refs` / `_private_refs_for_role` / `_private_refs`; plus inline public-predicate comprehensions at `game_engine.py:420` and `:451` (`visible_info_refs`).
  - `emergent_engine.py:359-371` `_public_refs` / `_private_refs`; consumed by `_build_obs` (:522), `:717`, `:813`.
- Identical rule in all three; helpers iterating events in order produce identical list order as the one-pass loop (both append in event order).
- Guard role needs no special case: generic `v == role` match (guard landed in L4 with this).
- Witness side: `invariants/visibility_oracle.py` imports from `observer_visibility` — engine-independent. `test_visibility_parity.py` guards observer-protocol-vs-projection only (NOT the engines).
- `observation_for` external callers: only `tests/test_game_engine.py`.
- Deterministic runners for the byte snapshot: `run_emergent_fake_runtime` (`--out-dir/--script/--seed`), `run_mock_game` (`--game-log-out/--decision-log-out`), `run_scripted_game` (`script_path docs/game-scripts/g1-scripted-game.json --game-log-out --decision-log-out --consensus-log-out`).

---

### Task 1: Commit ADR + plan

**Files:**
- Already written in worktree: `docs/adr/2026-06-11-engine-visibility-single-source.md`, `docs/harness/plans/2026-06-11--b2-engine-visibility-single-source-plan.md`

- [ ] **Step 1:** `node .codex/hooks/tree.mjs --force` (two new docs files)
- [ ] **Step 2:** Commit:

```bash
git add docs/adr/2026-06-11-engine-visibility-single-source.md docs/harness/plans/2026-06-11--b2-engine-visibility-single-source-plan.md .oh-my-harness/tree.md
git commit -m "docs(adr+plan): b2 engine visibility single source — role_visibility.py shared rule, witness boundary locked by sentinel, byte gates"
```

---

### Task 2: Baseline byte snapshot (BEFORE any src change)

**Files:** none committed (all under `.tmp/`, which is gitignored — verify nothing lands in git status)

- [ ] **Step 1: Produce baseline artifacts twice** (two dirs, to establish which files are deterministic):

```bash
for d in b2-base b2-base2; do
  mkdir -p .tmp/$d
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --out-dir .tmp/$d/emergent-vw --script villager_win --seed 0
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --out-dir .tmp/$d/emergent-ww --script werewolf_win --seed 0
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_mock_game --game-log-out .tmp/$d/mock-game.json --decision-log-out .tmp/$d/mock-decision.json
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out .tmp/$d/scripted-game.json --decision-log-out .tmp/$d/scripted-decision.json --consensus-log-out .tmp/$d/scripted-consensus.json
done
```

- [ ] **Step 2: Compute the deterministic file set:**

```bash
(cd .tmp/b2-base && find . -type f | sort | xargs sha256sum) > .tmp/b2-base.sha256
(cd .tmp/b2-base2 && find . -type f | sort | xargs sha256sum) > .tmp/b2-base2.sha256
diff .tmp/b2-base.sha256 .tmp/b2-base2.sha256 > .tmp/b2-nondet.diff; wc -l .tmp/b2-nondet.diff
```

Expected: empty diff (fully deterministic). If some files differ run-to-run (e.g. wall-clock timestamps in runtime artifacts), record the differing paths in `.tmp/b2-nondet-paths.txt` and EXCLUDE exactly those from the byte gate in Tasks 4/5 — report which paths were excluded and why. The game-log/decision-log/consensus-log JSONs MUST be in the deterministic set; if they are not, STOP and report BLOCKED.

- [ ] **Step 3:** Report the deterministic-set result. No commit (nothing tracked changed; verify `git status --short` is clean).

---

### Task 3: Shared module + unit tests + witness sentinel (TDD)

**Files:**
- Create: `src/werewolf_eval/role_visibility.py`
- Create: `tests/test_role_visibility.py`

- [ ] **Step 1: Write the failing tests** — create `tests/test_role_visibility.py`:

```python
"""B-2: unit tests for the shared engine-side visibility rule + witness sentinel.

The rule itself is security-bearing (P2-A-2 no-feed-leak gate renders prompts from
these id sets); the sentinel locks the SYS-A4/I4b witness boundary (observer +
invariants oracle must stay independent implementations)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.role_visibility import private_refs_for_role, public_refs


def _e(eid: str, vis: str) -> dict:
    return {"event_id": eid, "visibility": vis}


EVENTS = [
    _e("e1", "public"),
    _e("e2", "all"),
    _e("e3", "seer"),
    _e("e4", "witch"),
    _e("e5", "werewolf_team"),
    _e("e6", "internal"),
    _e("e7", "guard"),
    _e("e8", "some_future_visibility"),
]


class PublicRefsTest(unittest.TestCase):
    def test_public_and_all_only_in_event_order(self):
        self.assertEqual(public_refs(EVENTS), ["e1", "e2"])

    def test_empty(self):
        self.assertEqual(public_refs([]), [])


class PrivateRefsForRoleTest(unittest.TestCase):
    def test_seer(self):
        self.assertEqual(private_refs_for_role(EVENTS, "seer"), ["e2", "e3"])

    def test_witch(self):
        self.assertEqual(private_refs_for_role(EVENTS, "witch"), ["e2", "e4"])

    def test_werewolf_gets_team_channel(self):
        self.assertEqual(private_refs_for_role(EVENTS, "werewolf"), ["e2", "e5"])

    def test_guard_role_match_is_generic(self):
        self.assertEqual(private_refs_for_role(EVENTS, "guard"), ["e2", "e7"])

    def test_villager_sees_all_only(self):
        self.assertEqual(private_refs_for_role(EVENTS, "villager"), ["e2"])

    def test_internal_and_unknown_visibilities_stay_hidden_from_everyone(self):
        for role in ("villager", "seer", "witch", "werewolf", "guard", "hunter"):
            refs = private_refs_for_role(EVENTS, role)
            self.assertNotIn("e6", refs)
            self.assertNotIn("e8", refs)
        self.assertNotIn("e6", public_refs(EVENTS))
        self.assertNotIn("e8", public_refs(EVENTS))


class WitnessBoundarySentinelTest(unittest.TestCase):
    """SYS-A4 dual-witness / I4b anti-circularity: the observer-side filters and the
    invariants oracle must stay INDEPENDENT implementations of the visibility rule.
    If one of them starts importing role_visibility, the leak net would check the
    engine against itself."""

    def test_observer_and_oracle_do_not_reference_role_visibility(self):
        src = ROOT / "src" / "werewolf_eval"
        witnesses = [
            src / "observer_visibility.py",
            src / "observer_protocol.py",
            *sorted((src / "invariants").glob("*.py")),
        ]
        offenders = [
            p.name
            for p in witnesses
            if "role_visibility" in p.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_role_visibility.py -q`
Expected: collection error / ImportError (`role_visibility` doesn't exist). The sentinel alone would pass — that's fine.

- [ ] **Step 3: Implement** — create `src/werewolf_eval/role_visibility.py`:

```python
"""Single source of truth for the ENGINE-side role-filtered event visibility rule
(health-check B-2; ADR ``docs/adr/2026-06-11-engine-visibility-single-source.md``).

Both engines (``GameEngine`` scripted/mock arcs and ``EmergentGameEngine``) decide
"which event ids does this seat see" with this rule:

* public set:  ``visibility in {"public", "all"}``
* private set: ``visibility == "all"``, OR ``visibility ==`` the seat's role, OR
  ``visibility == "werewolf_team"`` for werewolf seats

This is the invariant the P2-A-2 "no feed leak" hard gate renders prompts from.

WITNESS BOUNDARY (do not widen): ``observer_visibility.py`` / ``observer_protocol.py``
and ``invariants/`` are deliberate INDEPENDENT implementations (SYS-A4 dual witness /
safety-net I4b anti-circularity). They must never import this module —
``tests/test_role_visibility.py`` enforces that with a sentinel."""

from __future__ import annotations

from typing import Any

PUBLIC_VISIBILITIES = ("public", "all")


def public_refs(events: list[dict[str, Any]]) -> list[str]:
    """Event ids every seat sees, in event order."""
    return [e["event_id"] for e in events if e["visibility"] in PUBLIC_VISIBILITIES]


def private_refs_for_role(events: list[dict[str, Any]], role: str) -> list[str]:
    """Event ids a seat of ``role`` privately sees, in event order: "all" events,
    its own role-private events, and the wolf-team channel for werewolves."""
    refs: list[str] = []
    for e in events:
        v = e["visibility"]
        if v == "all" or v == role or (v == "werewolf_team" and role == "werewolf"):
            refs.append(e["event_id"])
    return refs
```

- [ ] **Step 4: Run tests**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_role_visibility.py -q`
Expected: all PASS.

- [ ] **Step 5: Tree + commit**

```bash
node .codex/hooks/tree.mjs --force
git add src/werewolf_eval/role_visibility.py tests/test_role_visibility.py .oh-my-harness/tree.md
git commit -m "feat(visibility): role_visibility.py — shared engine-side rule + witness-boundary sentinel (health-check B-2, TDD)"
```

---

### Task 4: EmergentGameEngine delegates to the shared rule

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py` (only `_public_refs` at ~:359 and `_private_refs` at ~:362; plus one import line)

- [ ] **Step 1: Implement** — add to the existing `werewolf_eval` import block:

```python
from werewolf_eval.role_visibility import private_refs_for_role, public_refs
```

and replace the two method bodies:

```python
    def _public_refs(self) -> list[str]:
        return public_refs(self._events)

    def _private_refs(self, player_id: str) -> list[str]:
        return private_refs_for_role(self._events, self._players_by_id[player_id].role)
```

(Keep the methods — ~10 call sites stay untouched. Do NOT touch `_build_obs`, `:717`, `:813`, or anything else.)

- [ ] **Step 2: Run the emergent + visibility suites**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_emergent_engine.py tests/test_event_visibility_invariant.py tests/test_guard_visibility.py tests/test_emergent_role_projection.py tests/test_engine_to_scoring_e2e.py tests/test_observer_emergent_bridge.py tests/test_p2a2_live_path.py tests/test_role_visibility.py -q`
Expected: PASS.

- [ ] **Step 3: Byte gate** — re-run the two emergent baselines and diff against Task 2:

```bash
mkdir -p .tmp/b2-after-t4
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --out-dir .tmp/b2-after-t4/emergent-vw --script villager_win --seed 0
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --out-dir .tmp/b2-after-t4/emergent-ww --script werewolf_win --seed 0
(cd .tmp/b2-after-t4 && find . -type f | sort | xargs sha256sum) > .tmp/b2-after-t4.sha256
grep "emergent-" .tmp/b2-base.sha256 | diff - .tmp/b2-after-t4.sha256
```

Expected: empty diff (minus any paths Task 2 recorded as nondeterministic — exclude exactly those on both sides). Non-empty diff on a deterministic file = STOP, report BLOCKED with the differing file.

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py
git commit -m "refactor(visibility): EmergentGameEngine delegates _public_refs/_private_refs to role_visibility (byte gate: emergent fake artifacts identical)"
```

---

### Task 5: GameEngine delegates to the shared rule

**Files:**
- Modify: `src/werewolf_eval/game_engine.py` (4 sites + 1 import)

- [ ] **Step 1: Implement** — add to the existing import block:

```python
from werewolf_eval.role_visibility import private_refs_for_role, public_refs
```

Site A — `observation_for` (~:269): keep the `known_roles` block; replace the whole event loop and the two list initializations with:

```python
        public_event_ids = public_refs(self._events)
        private_event_ids = private_refs_for_role(self._events, player.role)
```

Site B — inline comprehensions at ~:420 and ~:451: replace
`[e["event_id"] for e in events if e["visibility"] in ("public", "all")]` with `public_refs(events)` (both lines).

Site C — scripted-arc closures (~:553): replace the bodies, keeping signatures and the `_private_refs(player_id)` wrapper:

```python
        def _public_refs() -> list[str]:
            return public_refs(events)

        def _private_refs_for_role(role: str) -> list[str]:
            return private_refs_for_role(events, role)

        def _private_refs(player_id: str) -> list[str]:
            return _private_refs_for_role(self._players_by_id[player_id].role)
```

(NOTE the closure names shadow the imported functions — that's intentional minimal-churn; the closures close over the local `events` list. Verify no other behavior in the closures was dropped, e.g. the R-18 comment block above `_wolf_obs` stays.)

- [ ] **Step 2: Run the scripted/gold/visibility suites**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_game_engine.py tests/test_scripted_game_runner.py tests/test_mock_game.py tests/test_fake_provider_game.py tests/test_deepseek_provider_game.py tests/test_deepseek_consensus_game.py tests/test_scoring.py tests/test_render_demo.py tests/test_role_visibility.py -q`
Expected: PASS (some filenames may differ — if a listed file doesn't exist, find the right suite via `ls tests/ | grep -i <topic>` and run that; report substitutions).

- [ ] **Step 3: Byte gate** — re-run mock + scripted baselines and diff:

```bash
mkdir -p .tmp/b2-after-t5
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_mock_game --game-log-out .tmp/b2-after-t5/mock-game.json --decision-log-out .tmp/b2-after-t5/mock-decision.json
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out .tmp/b2-after-t5/scripted-game.json --decision-log-out .tmp/b2-after-t5/scripted-decision.json --consensus-log-out .tmp/b2-after-t5/scripted-consensus.json
(cd .tmp/b2-after-t5 && find . -type f | sort | xargs sha256sum) > .tmp/b2-after-t5.sha256
grep -E "mock-|scripted-" .tmp/b2-base.sha256 | sort | diff - <(sort .tmp/b2-after-t5.sha256)
```

Expected: empty diff. Non-empty = STOP, BLOCKED with the differing file.

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/game_engine.py
git commit -m "refactor(visibility): GameEngine observation_for + scripted closures + visible_info_refs delegate to role_visibility (byte gate: mock/scripted artifacts identical)"
```

---

### Task 6: Full-suite validation + report (merge HELD for T17)

- [ ] **Step 1:** `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q` — expect baseline 1219 + ~10 new, all green.
- [ ] **Step 2:** AGENTS.md validation report: `git diff --stat main...HEAD`, `git diff --name-only main...HEAD`; allowlist = {role_visibility.py, emergent_engine.py, game_engine.py, tests/test_role_visibility.py, ADR, plan, tree.md}; forbidden-scope check: NOTHING else — in particular zero changes to `observer_visibility.py`, `observer_protocol.py`, `invariants/**`, prompts/renderers, `action_runtime/**`, scoring.
- [ ] **Step 3:** Final whole-branch code review (superpowers:requesting-code-review template).
- [ ] **Step 4:** **Do NOT merge.** Report ready-to-merge status; merge happens only after the T17 live batch completes (coordination constraint at top of plan).

---

## Self-Review (done at planning time)

- **Spec coverage:** ADR-first ✓ (Task 1), shared primitive ✓ (Task 3), both engines ✓ (Tasks 4/5 cover all sites enumerated in the health check: observation_for, closures, inline comprehensions, emergent methods), byte gates ✓ (fixture suites + snapshot diff), witness boundary ✓ (sentinel + ADR).
- **Placeholder scan:** all code steps carry full code; Task 5 Step 2 names a fallback procedure for test-file name drift (explicit, not a TODO).
- **Type consistency:** `public_refs(events) -> list[str]`, `private_refs_for_role(events, role) -> list[str]` used identically across Tasks 3/4/5; closure shadowing called out explicitly.
- **Known risks named:** nondeterministic artifact files (Task 2 establishes the deterministic set first); closure-name shadowing (explicit note); T17 merge hold (top-level constraint + Task 6 Step 4).
