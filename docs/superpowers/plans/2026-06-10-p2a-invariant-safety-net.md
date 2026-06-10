# P2-A Invariant Safety Net — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the three-layer semantic safety net specified in `docs/superpowers/specs/2026-06-09-p2a-invariant-safety-net-design.md` — an offline invariant checker (L1, 7 invariants), two runtime fail-closed guards (L2: B1 prompt-leak + B4 double-death), and a deterministic fuzz layer (L3) — so the new-behavior engine layers (add-role, ledger, EffectQueue, NightPlan) are caught by *semantic* rules, not just byte-parity.

**Architecture:** A new sibling package `src/werewolf_eval/invariants/` that READS engine artifacts (`game-log.json` events with `visibility` tags, `decision-log.json`, `provider-turns.json` with `observation_source_event_ids`, plus the `players` role map embedded in the game log). The checker never raises (reports `artifact_gap`). The leak guard (B1) reuses the **observer's** independent visibility implementation (`observer_visibility.event_visible_in_projection`) — NOT the engine's `_build_obs` — which is the load-bearing anti-circularity. Both checker and guards draw the visibility verdict from one shared wrapper (`invariants/visibility_oracle.py`). The two guards are pure in-memory assertions wired at 7 engine call sites; they write no artifact, so they are byte-neutral on the happy path.

**Tech Stack:** Python 3.12, stdlib `unittest`, stdlib `random` (no Hypothesis). Full-suite test cmd: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`. Single-module: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_checker -v`.

---

## Engine anchor table — verified against merged `main == 1380ba8` (②a complete)

> ②a renumbered everything ≥ the old `:545`. These are the **current** lines. All B1/B4 wiring targets are here. Re-grep before editing if HEAD has moved past `1380ba8`.

| Symbol / site | File:line | Used by |
|---|---|---|
| `_emit` (event schema producer) | `emergent_engine.py:316` | event shape for all invariants |
| event schema | `{event_id, sequence, round, phase, type, actor, target, visibility, data:{summary, visible_info_refs}}` (`:328-338`) | all |
| `_game_log_dict` → `{game_id, source_label, players:[{player_id,role,team}], events, result?}` | `emergent_engine.py:391-407` | `RunArtifacts` loader; `players` is the seat→role source |
| `_provider_action` def | `emergent_engine.py:510` | B1 strict anchor (wolf/seer/vote) |
| strict `request_id` (NO kind suffix) | `emergent_engine.py:524` (`f"{game}_r{rnd:02d}_{player_id}"`) | BLOCKING-1 root — I5 keys on `(request_id, phase)` |
| strict `observation_source_event_ids` ready | `emergent_engine.py:535` | B1 strict — insert guard AFTER this |
| strict `agent.decide(...)` call | `emergent_engine.py:538` | B1 strict — insert guard BEFORE this |
| witch `observation_source_event_ids` | `emergent_engine.py:765` | B1 witch |
| witch `provider.respond(request)` | `emergent_engine.py:771` | B1 witch — guard before |
| speech `observation_source_event_ids` | `emergent_engine.py:842` | B1 speech |
| speech `provider.respond(request)` | `emergent_engine.py:847` | B1 speech — guard before |
| `_trigger_on_death` def | `emergent_engine.py:869` | B4 site 3 |
| trigger alive-gate `target in self._alive` | `emergent_engine.py:878` | B4 site 3 (idempotent commit) |
| trigger emit `player_died` | `emergent_engine.py:880` | B4 site 3 — guard before |
| hunter `observation_source_event_ids` | `emergent_engine.py:908` | B1 hunter |
| hunter `provider.respond(request)` | `emergent_engine.py:913` | B1 hunter — guard before |
| night-loop death gate `pid not in self._alive: continue` | `emergent_engine.py:1014` | B4 site 1 — legal silent no-op (do NOT guard the skip) |
| night-loop emit `player_died` | `emergent_engine.py:1017` | B4 site 1 — guard before |
| day-vote `discard(eliminated)` | `emergent_engine.py:1038` | B4 site 2 |
| day-vote emit `player_eliminated` | `emergent_engine.py:1040` | B4 site 2 — guard before |
| **STABLE (②a untouched):** `observer_visibility.build_seat_role_index` | `observer_visibility.py:126` | I4b/B1 disk seat_index |
| `observer_visibility.event_visible_in_projection` → **`(visible: bool, reason: str)` tuple** | `observer_visibility.py:466` | I4b/B1 verdict (M-1: UNPACK the tuple) |
| `_trusted_role_for_player` (trusts only `role_source == "role_projection_snapshot"`) | `observer_visibility.py:521` | seat_index entry shape |
| `settler.py` candidate dedup | `settler.py:60` | §7 context |
| `RuntimeState` (no `uses_left`) | `state.py:7` | B2 deferred premise |
| fake runner writes (NO provider-turns.json) | `run_emergent_fake_runtime.py:127-131` | Task 2 fixes this |
| deepseek runner `_provider_turns_summary` | `run_emergent_deepseek_game.py:107` | Task 2 reuse |
| deepseek runner writes `provider-turns.json` | `run_emergent_deepseek_game.py:160` | Task 2 mirror |

**Event types in play** (from `_emit` call sites): death-commit `{player_died, player_eliminated}`; consumables `{witch_save, witch_poison, hunter_shoot}` (non-consuming: `witch_pass`, `hunter_pass`); visibility-tagged actions `{werewolf_kill (vis werewolf_team), seer_check (vis seer)}`; other `{player_speech, role_revealed, role_assignment, day_announcement}`.

---

## File Structure

- **Create** `src/werewolf_eval/invariants/__init__.py` — exports `check_run`, `InvariantViolation`, `RunArtifacts`, the guards, and their exception types.
- **Create** `src/werewolf_eval/invariants/artifacts.py` — `RunArtifacts` (unified in-memory `GameOutcome` ↔ disk `run_dir` view). Never raises; records `gaps`.
- **Create** `src/werewolf_eval/invariants/visibility_oracle.py` — the single shared visibility source: `entitled(seat, event, seat_index) -> bool` (unpacks the observer tuple) + `seat_index_from_players(players)` (synthesizes trusted `role_source`). Used by BOTH the offline I4b and the runtime B1.
- **Create** `src/werewolf_eval/invariants/checker.py` — L1: the 7 invariants + `InvariantViolation` + `check_run`. Never raises.
- **Create** `src/werewolf_eval/invariants/guards.py` — L2: `assert_prompt_entitled` (B1, raises `PromptLeakError`) + `assert_death_commit_once` (B4, raises `DoubleDeathCommitError`).
- **Create** `src/werewolf_eval/invariants/fuzz.py` — L3: deterministic synthetic-artifact generators + fixed seed bank.
- **Modify** `src/werewolf_eval/run_emergent_fake_runtime.py:131` — add `provider-turns.json` write (Task 2).
- **Modify** `src/werewolf_eval/emergent_engine.py` — 7 guard insertions only (B1×4, B4×3); add one `self._death_committed: set[str]` field. No other engine change.
- **Tests:** `tests/test_invariants_artifacts.py`, `tests/test_invariants_checker.py`, `tests/test_invariants_guards.py`, `tests/test_invariants_engine_wiring.py`, `tests/test_invariants_fuzz.py`, `tests/test_invariants_bad_examples.py`.

---

## Task 1: Package skeleton — `RunArtifacts` loader + `InvariantViolation` + empty `check_run`

**Files:**
- Create: `src/werewolf_eval/invariants/__init__.py`
- Create: `src/werewolf_eval/invariants/artifacts.py`
- Create: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_artifacts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_invariants_artifacts.py
import unittest
from werewolf_eval.invariants.artifacts import RunArtifacts


class _FakeOutcome:
    def __init__(self):
        self.game_log = {
            "game_id": "g1",
            "players": [{"player_id": "p1", "role": "seer", "team": "villager"}],
            "events": [{"event_id": "g1_e001", "type": "seer_check", "actor": "p1",
                        "target": "p2", "round": 1, "phase": "night",
                        "visibility": "seer", "sequence": 1, "data": {"summary": ""}}],
            "result": {"winner": "villager"},
        }
        self.decision_log = {"decisions": [{"actor": "p1", "phase": "night", "action": "seer_check"}]}
        self.provider_turns = [{"request_id": "g1_r01_p1", "phase": "night", "actor": "p1",
                                "observation_source_event_ids": ["g1_e001"]}]


class TestRunArtifacts(unittest.TestCase):
    def test_from_outcome_extracts_all_streams(self):
        arts = RunArtifacts.from_outcome(_FakeOutcome())
        self.assertEqual(arts.game_id, "g1")
        self.assertEqual(len(arts.events), 1)
        self.assertEqual(arts.players[0]["role"], "seer")
        self.assertEqual(arts.provider_turns[0]["request_id"], "g1_r01_p1")
        self.assertEqual(arts.gaps, ())

    def test_missing_events_is_a_gap_not_a_raise(self):
        class Empty:
            game_log = {"game_id": "g2"}
            decision_log = {}
            provider_turns = []
        arts = RunArtifacts.from_outcome(Empty())
        self.assertIn("game_log.events", arts.gaps)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_artifacts -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'werewolf_eval.invariants'`

- [ ] **Step 3: Write `artifacts.py`**

```python
# src/werewolf_eval/invariants/artifacts.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunArtifacts:
    """Unified read view over a finished game — either an in-memory GameOutcome
    or a persisted run_dir. NEVER raises: missing/malformed streams are recorded
    in `gaps` so the checker can report `artifact_gap` instead of crashing."""

    game_id: str
    players: list[dict[str, Any]]            # [{player_id, role, team}, ...]
    events: list[dict[str, Any]]             # game-log events (god, with visibility tags)
    decisions: list[dict[str, Any]]
    provider_turns: list[dict[str, Any]]     # each carries observation_source_event_ids
    result: dict[str, Any] | None
    gaps: tuple[str, ...] = ()

    @classmethod
    def from_outcome(cls, outcome: Any) -> "RunArtifacts":
        gl = getattr(outcome, "game_log", None) or {}
        dl = getattr(outcome, "decision_log", None) or {}
        turns = list(getattr(outcome, "provider_turns", None) or [])
        gaps: list[str] = []
        if not gl.get("events"):
            gaps.append("game_log.events")
        return cls(
            game_id=str(gl.get("game_id", "")),
            players=list(gl.get("players", [])),
            events=list(gl.get("events", [])),
            decisions=list(dl.get("decisions", [])),
            provider_turns=turns,
            result=gl.get("result"),
            gaps=tuple(gaps),
        )

    @classmethod
    def from_run_dir(cls, run_dir: str | Path) -> "RunArtifacts":
        run_dir = Path(run_dir)

        def _load(name: str) -> Any:
            p = run_dir / name
            if not p.is_file():
                return None
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None

        gl = _load("game-log.json") or {}
        dl = _load("decision-log.json") or {}
        pt = _load("provider-turns.json")
        gaps: list[str] = []
        if not gl.get("events"):
            gaps.append("game-log.json")
        # provider-turns.json is {"turns": [...], ...} (deepseek _provider_turns_summary shape)
        turns: list[dict[str, Any]] = []
        if isinstance(pt, dict) and isinstance(pt.get("turns"), list):
            turns = list(pt["turns"])
        else:
            gaps.append("provider-turns.json")
        return cls(
            game_id=str(gl.get("game_id", "")),
            players=list(gl.get("players", [])),
            events=list(gl.get("events", [])),
            decisions=list(dl.get("decisions", [])),
            provider_turns=turns,
            result=gl.get("result"),
            gaps=tuple(gaps),
        )
```

- [ ] **Step 4: Write `checker.py` skeleton + `__init__.py`**

```python
# src/werewolf_eval/invariants/checker.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from werewolf_eval.invariants.artifacts import RunArtifacts


@dataclass(frozen=True)
class InvariantViolation:
    id: str                       # "I1".."I7" or "artifact_gap"
    severity: str                 # "error" | "artifact_gap"
    game_id: str
    event_ids: tuple[str, ...]
    detail: str


# Registered incrementally by later tasks.
_ALL_CHECKS: list[Callable[[RunArtifacts], list[InvariantViolation]]] = []


def check_run(source: Any) -> list[InvariantViolation]:
    """Run every registered invariant over a finished game. `source` may be a
    RunArtifacts, a GameOutcome, or a run_dir path. Never raises."""
    if isinstance(source, RunArtifacts):
        arts = source
    elif isinstance(source, (str, Path)):
        arts = RunArtifacts.from_run_dir(source)
    else:
        arts = RunArtifacts.from_outcome(source)

    violations: list[InvariantViolation] = [
        InvariantViolation("artifact_gap", "artifact_gap", arts.game_id, (), f"missing {gap}")
        for gap in arts.gaps
    ]
    for check in _ALL_CHECKS:
        violations.extend(check(arts))
    return violations
```

```python
# src/werewolf_eval/invariants/__init__.py
from werewolf_eval.invariants.artifacts import RunArtifacts
from werewolf_eval.invariants.checker import InvariantViolation, check_run

__all__ = ["RunArtifacts", "InvariantViolation", "check_run"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_artifacts -v`
Expected: PASS (both tests)

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/invariants/ tests/test_invariants_artifacts.py
git commit -m "feat(invariants): package skeleton — RunArtifacts loader + check_run frame"
```

---

## Task 2: Fake runner writes `provider-turns.json` (disk-level prerequisite for I4b/I5)

**Files:**
- Modify: `src/werewolf_eval/run_emergent_fake_runtime.py:107-132` (reuse the deepseek summary, add one write)
- Test: `tests/test_invariants_artifacts.py` (add a persisted-run case)

**Context:** The fake CLI runner writes `provider-trace.json` but not `provider-turns.json` (`:131`). `RunArtifacts.from_run_dir` needs the latter (it carries `observation_source_event_ids`). The deepseek runner already has `_provider_turns_summary` (`run_emergent_deepseek_game.py:107`) producing `{"turns": <verbatim outcome.provider_turns>, ...}`. Import and reuse it.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_artifacts.py
import json, tempfile
from pathlib import Path
from werewolf_eval.run_emergent_fake_runtime import run_emergent_fake_runtime  # adjust to real entrypoint name


class TestFakeRunnerProviderTurns(unittest.TestCase):
    def test_persisted_fake_run_has_provider_turns_json(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d) / "run"
            run_emergent_fake_runtime(out_dir=out_dir)  # adjust call to the real signature
            pt = out_dir / "provider-turns.json"
            self.assertTrue(pt.is_file(), "fake run must persist provider-turns.json")
            data = json.loads(pt.read_text(encoding="utf-8"))
            self.assertIn("turns", data)
            self.assertTrue(all("observation_source_event_ids" in t for t in data["turns"]))
```

> NOTE for the implementer: open `run_emergent_fake_runtime.py` and match the real entrypoint name + signature (it may be `main(argv)` / a CLI). Wire the test to call the runner the way its existing tests do (grep `tests/` for `run_emergent_fake_runtime`). The assertion content stays the same.

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_artifacts.TestFakeRunnerProviderTurns -v`
Expected: FAIL — `provider-turns.json` does not exist.

- [ ] **Step 3: Add the write**

At `run_emergent_fake_runtime.py`, add the import near the top:

```python
from werewolf_eval.run_emergent_deepseek_game import _provider_turns_summary
```

Then immediately after the `provider-trace.json` write (`:131`):

```python
    _write_json(out_dir / "provider-turns.json", _provider_turns_summary(outcome.provider_turns))
```

> If `outcome.provider_turns` is not in scope at `:131`, grep the function for the `outcome` variable name and use it (the deepseek runner reads `outcome.provider_turns` at `:160`). If importing from the deepseek module pulls heavy deps, instead copy the ~10-line `_provider_turns_summary` body into a shared helper `run_emergent_shared.py` and import from there in both runners (DRY).

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_artifacts.TestFakeRunnerProviderTurns -v`
Expected: PASS

Also confirm the new write didn't break the existing runner suite (its assertions are existence-based, not an exact file manifest, so it should stay green):
Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_run_emergent_fake_runtime -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/run_emergent_fake_runtime.py tests/test_invariants_artifacts.py
git commit -m "feat(runner): fake runtime persists provider-turns.json (invariant net disk prerequisite)"
```

---

## Task 3: `visibility_oracle.py` — the single shared visibility source

**Files:**
- Create: `src/werewolf_eval/invariants/visibility_oracle.py`
- Test: `tests/test_invariants_checker.py`

**Context:** This is the anti-circularity keystone. It reuses the OBSERVER's `event_visible_in_projection` (`observer_visibility.py:466`), which returns a **`(visible, reason)` tuple** — M-1 fix: unpack it. `seat_index_from_players` synthesizes `role_source == "role_projection_snapshot"` so `_trusted_role_for_player` (`:521-530`) actually trusts the entry (LOW fix).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_invariants_checker.py
import unittest
from werewolf_eval.invariants.visibility_oracle import entitled, seat_index_from_players

_PLAYERS = [
    {"player_id": "p1", "role": "seer", "team": "villager"},
    {"player_id": "p2", "role": "villager", "team": "villager"},
]
_SEER_EVENT = {"event_id": "e1", "type": "seer_check", "actor": "p1", "target": "p3",
               "visibility": "seer", "round": 1, "phase": "night", "data": {"summary": ""}}
_PUBLIC_EVENT = {"event_id": "e2", "type": "day_announcement", "actor": "system",
                 "target": "none", "visibility": "public", "round": 1, "phase": "day",
                 "data": {"summary": ""}}


class TestVisibilityOracle(unittest.TestCase):
    def setUp(self):
        self.idx = seat_index_from_players(_PLAYERS)

    def test_seer_sees_seer_event(self):
        self.assertTrue(entitled("p1", _SEER_EVENT, self.idx))

    def test_villager_does_not_see_seer_event(self):
        self.assertFalse(entitled("p2", _SEER_EVENT, self.idx))

    def test_everyone_sees_public_event(self):
        self.assertTrue(entitled("p2", _PUBLIC_EVENT, self.idx))

    def test_seat_index_marks_trusted_source(self):
        self.assertEqual(self.idx["p1"]["role_source"], "role_projection_snapshot")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_checker -v`
Expected: FAIL — `ModuleNotFoundError: ...visibility_oracle`

- [ ] **Step 3: Write `visibility_oracle.py`**

```python
# src/werewolf_eval/invariants/visibility_oracle.py
from __future__ import annotations

from typing import Any

from werewolf_eval.observer_visibility import event_visible_in_projection


def seat_index_from_players(players: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    """Build a seat_index from the game-log `players` map. Marks every field's
    source as `role_projection_snapshot` so `_trusted_role_for_player` /
    `_trusted_team_for_player` (observer_visibility.py:521/533) trust it — without
    this the observer returns 'unknown' and every seat reads as all-hidden."""
    return {
        p["player_id"]: {
            "player_id": p["player_id"],
            "role": p.get("role", "unknown"),
            "team": p.get("team", "unknown"),
            "role_source": "role_projection_snapshot",
            "team_source": "role_projection_snapshot",
        }
        for p in players
    }


def entitled(seat: str, event: dict[str, Any], seat_index: dict[str, dict[str, object]]) -> bool:
    """True iff `seat` (a player id) may legitimately see `event`, decided by the
    OBSERVER's visibility implementation (event tag + trusted role) — a different
    code path from the engine's `_build_obs` (the anti-circularity). M-1: the
    observer returns a (visible, reason) tuple; unpack it."""
    visible, _reason = event_visible_in_projection(event, f"role:{seat}", seat_index)
    return bool(visible)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_checker -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/visibility_oracle.py tests/test_invariants_checker.py
git commit -m "feat(invariants): shared visibility oracle (observer path, tuple-unpacked, trusted seat_index)"
```

---

## Task 4: I1 `death_once`

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_i1, InvariantViolation
from werewolf_eval.invariants.artifacts import RunArtifacts


def _arts(events, players=None, turns=None):
    return RunArtifacts(game_id="g", players=players or [], events=events,
                        decisions=[], provider_turns=turns or [], result=None)


def _death(eid, target, etype="player_died", seq=1, rnd=1, phase="night"):
    return {"event_id": eid, "type": etype, "actor": "system", "target": target,
            "round": rnd, "phase": phase, "visibility": "all", "sequence": seq,
            "data": {"summary": ""}}


class TestI1(unittest.TestCase):
    def test_single_death_passes(self):
        self.assertEqual(check_i1(_arts([_death("e1", "p3")])), [])

    def test_double_commit_fails(self):
        v = check_i1(_arts([_death("e1", "p3", seq=1), _death("e2", "p3", seq=2)]))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I1")
        self.assertEqual(set(v[0].event_ids), {"e1", "e2"})

    def test_night_death_then_day_vote_same_player_fails(self):
        evs = [_death("e1", "p3", "player_died", seq=1),
               _death("e2", "p3", "player_eliminated", seq=2, phase="day")]
        self.assertEqual(len(check_i1(_arts(evs))), 1)
```

- [ ] **Step 2: Run to verify it fails** — `ImportError: cannot import name 'check_i1'`

- [ ] **Step 3: Implement in `checker.py`**

```python
DEATH_COMMIT_TYPES = ("player_died", "player_eliminated")


def check_i1(arts: RunArtifacts) -> list[InvariantViolation]:
    """Each player is committed dead at most once (candidates may stack; commits may not)."""
    by_target: dict[str, list[str]] = {}
    for e in arts.events:
        if e.get("type") in DEATH_COMMIT_TYPES:
            by_target.setdefault(str(e.get("target")), []).append(str(e.get("event_id")))
    return [
        InvariantViolation("I1", "error", arts.game_id, tuple(eids),
                           f"player {target} committed dead {len(eids)}x")
        for target, eids in by_target.items() if len(eids) > 1
    ]


_ALL_CHECKS.append(check_i1)
```

- [ ] **Step 4: Run to verify it passes** — PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I1 death_once"
```

---

## Task 5: I2 `no_dead_actor_for_active_decision`

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

**Context:** A dead player takes no ordinary action. The on-death window (`hunter_shoot`/`hunter_pass`) is naturally exempt by being excluded from `ACTIVE_ACTION_TYPES`. Death-time uses the monotonic `sequence`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_i2


def _action(eid, actor, etype, seq, rnd=1, phase="night"):
    return {"event_id": eid, "type": etype, "actor": actor, "target": "p9",
            "round": rnd, "phase": phase, "visibility": "all", "sequence": seq,
            "data": {"summary": ""}}


class TestI2(unittest.TestCase):
    def test_live_actor_passes(self):
        evs = [_action("e1", "p1", "seer_check", 1)]
        self.assertEqual(check_i2(_arts(evs)), [])

    def test_action_after_death_fails(self):
        evs = [_death("e1", "p1", seq=1), _action("e2", "p1", "seer_check", 2)]
        v = check_i2(_arts(evs))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I2")

    def test_hunter_shot_after_death_is_exempt(self):
        evs = [_death("e1", "p1", seq=1), _action("e2", "p1", "hunter_shoot", 2)]
        self.assertEqual(check_i2(_arts(evs)), [])

    def test_vote_after_death_fails(self):
        evs = [_death("e1", "p1", seq=1), _action("e2", "p1", "player_vote", 2, phase="day")]
        v = check_i2(_arts(evs))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I2")
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`

- [ ] **Step 3: Implement in `checker.py`**

```python
ACTIVE_ACTION_TYPES = ("werewolf_kill", "seer_check", "witch_save", "witch_poison",
                       "witch_pass", "player_speech", "player_vote")
# player_vote IS a game-log event (VoteResolver.render -> EventRow(..,"player_vote",..),
# turn.py:158). Only the on-death window (hunter_shoot/hunter_pass) is exempt — a dead
# player must never produce a vote either.


def _first_death_sequence(arts: RunArtifacts) -> dict[str, int]:
    dead_at: dict[str, int] = {}
    for e in sorted(arts.events, key=lambda x: x.get("sequence", 0)):
        if e.get("type") in DEATH_COMMIT_TYPES:
            tgt = str(e.get("target"))
            dead_at.setdefault(tgt, int(e.get("sequence", 0)))
    return dead_at


def check_i2(arts: RunArtifacts) -> list[InvariantViolation]:
    """A dead actor produces no ordinary action; the on-death window
    (hunter_shoot/hunter_pass, absent from ACTIVE_ACTION_TYPES) is exempt."""
    dead_seq = _first_death_sequence(arts)
    out: list[InvariantViolation] = []
    for e in arts.events:
        if e.get("type") not in ACTIVE_ACTION_TYPES:
            continue
        actor = str(e.get("actor"))
        ds = dead_seq.get(actor)
        if ds is not None and int(e.get("sequence", 0)) > ds:
            out.append(InvariantViolation("I2", "error", arts.game_id, (str(e.get("event_id")),),
                                          f"dead actor {actor} produced {e.get('type')} after death"))
    return out


_ALL_CHECKS.append(check_i2)
```

- [ ] **Step 4: Run to verify it passes** — PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I2 no_dead_actor_for_active_decision"
```

---

## Task 6: I3 `capability_not_overused` (per `(actor, capability)`)

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

**Context (LOW fix):** count per `(actor, capability)`, not per capability-per-game, so a future double-hunter board does not false-positive.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_i3


def _consume(eid, actor, etype, seq):
    return {"event_id": eid, "type": etype, "actor": actor, "target": "p9",
            "round": 1, "phase": "night", "visibility": "witch", "sequence": seq,
            "data": {"summary": ""}}


class TestI3(unittest.TestCase):
    def test_one_each_passes(self):
        evs = [_consume("e1", "pw", "witch_save", 1), _consume("e2", "pw", "witch_poison", 2)]
        self.assertEqual(check_i3(_arts(evs)), [])

    def test_second_antidote_fails(self):
        evs = [_consume("e1", "pw", "witch_save", 1), _consume("e2", "pw", "witch_save", 2)]
        v = check_i3(_arts(evs))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I3")

    def test_two_hunters_one_shot_each_passes(self):
        evs = [_consume("e1", "ph1", "hunter_shoot", 1), _consume("e2", "ph2", "hunter_shoot", 2)]
        self.assertEqual(check_i3(_arts(evs)), [])
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`

- [ ] **Step 3: Implement in `checker.py`**

```python
CONSUME_TYPES = ("witch_save", "witch_poison", "hunter_shoot")


def check_i3(arts: RunArtifacts) -> list[InvariantViolation]:
    """Each consumable used ≤ 1 per (actor, capability). Event-count = the
    consumption witness today; a ledger cross-check is added when ②b lands."""
    by_key: dict[tuple[str, str], list[str]] = {}
    for e in arts.events:
        t = str(e.get("type"))
        if t in CONSUME_TYPES:
            by_key.setdefault((str(e.get("actor")), t), []).append(str(e.get("event_id")))
    return [
        InvariantViolation("I3", "error", arts.game_id, tuple(eids),
                           f"{actor} used {cap} {len(eids)}x (max 1)")
        for (actor, cap), eids in by_key.items() if len(eids) > 1
    ]


_ALL_CHECKS.append(check_i3)
```

- [ ] **Step 4: Run to verify it passes** — PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I3 capability_not_overused (per actor+capability)"
```

---

## Task 7: I4a `prompt_subset_of_observation` (in-memory unit helper — NOT in `_ALL_CHECKS`)

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

**Context (M-2 fix):** I4a's second operand — the seat's full observation event set — is NOT persisted (the turn stores only `observation_source_event_ids`; adding a turn key is forbidden — it would diverge `provider_turns`). So I4a is an in-memory/unit helper that takes both sets explicitly; it is NOT registered in `_ALL_CHECKS` (the disk-level leak net is I4b).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_prompt_subset


class TestI4a(unittest.TestCase):
    def test_subset_passes(self):
        self.assertEqual(check_prompt_subset("g", "p1", ["e1", "e2"], {"e1", "e2", "e3"}), [])

    def test_prompt_outside_observation_fails(self):
        v = check_prompt_subset("g", "p1", ["e1", "e9"], {"e1", "e2"})
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I4a")
        self.assertEqual(v[0].event_ids, ("e9",))
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`

- [ ] **Step 3: Implement in `checker.py`**

```python
def check_prompt_subset(game_id: str, seat: str, prompt_source_ids: list[str],
                        observation_event_ids: set[str]) -> list[InvariantViolation]:
    """I4a (in-memory only): prompt sources ⊆ the seat's observation set. Catches a
    RENDERER pulling outside `obs`. Not in _ALL_CHECKS — its 2nd operand is not on disk."""
    leaked = [eid for eid in prompt_source_ids if eid not in observation_event_ids]
    return [InvariantViolation("I4a", "error", game_id, (eid,),
                               f"seat {seat} prompt sourced {eid} outside its observation")
            for eid in leaked]
```

- [ ] **Step 4: Run to verify it passes** — PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I4a prompt_subset (in-memory unit helper)"
```

---

## Task 8: I4b `prompt_visibility_entitled` — the load-bearing leak invariant

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_i4b

_I4B_PLAYERS = [
    {"player_id": "p1", "role": "seer", "team": "villager"},
    {"player_id": "p2", "role": "villager", "team": "villager"},
]
_SEER_EV = {"event_id": "e1", "type": "seer_check", "actor": "p1", "target": "p3",
            "visibility": "seer", "round": 1, "phase": "night", "sequence": 1,
            "data": {"summary": ""}}


class TestI4b(unittest.TestCase):
    def test_seer_sourcing_own_check_passes(self):
        turns = [{"actor": "p1", "request_id": "g_r01_p1", "phase": "night",
                  "observation_source_event_ids": ["e1"]}]
        self.assertEqual(check_i4b(_arts([_SEER_EV], players=_I4B_PLAYERS, turns=turns)), [])

    def test_villager_sourcing_seer_event_fails(self):
        turns = [{"actor": "p2", "request_id": "g_r01_p2", "phase": "day",
                  "observation_source_event_ids": ["e1"]}]
        v = check_i4b(_arts([_SEER_EV], players=_I4B_PLAYERS, turns=turns))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I4b")
        self.assertEqual(v[0].event_ids, ("e1",))
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`

- [ ] **Step 3: Implement in `checker.py`**

```python
from werewolf_eval.invariants.visibility_oracle import entitled, seat_index_from_players


def check_i4b(arts: RunArtifacts) -> list[InvariantViolation]:
    """Every event a seat's prompt was built from must be one that seat could
    legitimately see — checked by the OBSERVER's independent projection (tag +
    trusted role), never the engine's _build_obs. The non-circular leak guard."""
    seat_index = seat_index_from_players(arts.players)
    by_id = {str(e.get("event_id")): e for e in arts.events}
    out: list[InvariantViolation] = []
    for turn in arts.provider_turns:
        seat = str(turn.get("actor"))
        for eid in turn.get("observation_source_event_ids", []):
            ev = by_id.get(str(eid))
            if ev is None:
                continue  # missing event = artifact gap, surfaced elsewhere
            if not entitled(seat, ev, seat_index):
                out.append(InvariantViolation(
                    "I4b", "error", arts.game_id, (str(eid),),
                    f"seat {seat} prompt sourced non-entitled event {eid} "
                    f"(visibility={ev.get('visibility')})"))
    return out


_ALL_CHECKS.append(check_i4b)
```

- [ ] **Step 4: Run to verify it passes** — PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I4b prompt_visibility_entitled (load-bearing, non-circular)"
```

---

## Task 9: I5 `decision_settled_once` — keyed on `(request_id, phase)` (BLOCKING-1 fix)

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

**Context (BLOCKING-1):** the strict path's `request_id` has no kind suffix (`:524`), so one actor's night action and day vote share a `request_id` (`g_r01_p1` twice) — different `phase`. Keying on `request_id` alone false-positives every game; key on `(request_id, phase)`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_i5


class TestI5(unittest.TestCase):
    def test_same_request_id_different_phase_passes(self):
        turns = [{"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": []},
                 {"request_id": "g_r01_p1", "phase": "day", "actor": "p1",
                  "observation_source_event_ids": []}]
        self.assertEqual(check_i5(_arts([], turns=turns)), [])

    def test_same_request_id_same_phase_twice_fails(self):
        turns = [{"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": []},
                 {"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": []}]
        v = check_i5(_arts([], turns=turns))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I5")
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`

- [ ] **Step 3: Implement in `checker.py`**

```python
def check_i5(arts: RunArtifacts) -> list[InvariantViolation]:
    """One decision identity settles at most once. Identity = (request_id, phase),
    NOT request_id alone (the strict path reuses request_id across night/day —
    BLOCKING-1)."""
    seen: dict[tuple[str, str], int] = {}
    for t in arts.provider_turns:
        key = (str(t.get("request_id")), str(t.get("phase")))
        seen[key] = seen.get(key, 0) + 1
    return [
        InvariantViolation("I5", "error", arts.game_id, (),
                           f"decision identity (request_id={rid}, phase={ph}) settled {n}x")
        for (rid, ph), n in seen.items() if n > 1
    ]


_ALL_CHECKS.append(check_i5)
```

- [ ] **Step 4: Run to verify it passes** — PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I5 decision_settled_once keyed on (request_id, phase)"
```

---

## Task 10: I6 `effect_causality` (WEAK — inferred)

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

**Context:** No structured causal field exists yet (STRICT-I6 rides the EffectQueue). WEAK-I6: every `player_died` has an earlier cause event (`werewolf_kill`/`witch_poison`/`hunter_shoot`) naming the same target. `player_eliminated` is exempt (its cause is the aggregate vote, an announced settlement).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_i6


def _cause(eid, etype, target, seq):
    return {"event_id": eid, "type": etype, "actor": "x", "target": target,
            "round": 1, "phase": "night", "visibility": "all", "sequence": seq,
            "data": {"summary": ""}}


class TestI6(unittest.TestCase):
    def test_death_with_cause_passes(self):
        evs = [_cause("e1", "werewolf_kill", "p3", 1), _death("e2", "p3", seq=2)]
        self.assertEqual(check_i6(_arts(evs)), [])

    def test_uncaused_death_fails(self):
        evs = [_death("e1", "p4", seq=1)]
        v = check_i6(_arts(evs))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].id, "I6")
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`

- [ ] **Step 3: Implement in `checker.py`**

```python
DEATH_CAUSE_TYPES = ("werewolf_kill", "witch_poison", "hunter_shoot")


def check_i6(arts: RunArtifacts) -> list[InvariantViolation]:
    """WEAK causality: every player_died has an earlier cause event naming the same
    target. player_eliminated (vote) is exempt. STRICT-I6 (a real source_event_id)
    rides the EffectQueue — do not add a death-event schema field here."""
    ordered = sorted(arts.events, key=lambda e: e.get("sequence", 0))
    out: list[InvariantViolation] = []
    for e in ordered:
        if e.get("type") != "player_died":
            continue
        tgt = str(e.get("target"))
        seq = int(e.get("sequence", 0))
        has_cause = any(
            int(c.get("sequence", 0)) < seq
            and c.get("type") in DEATH_CAUSE_TYPES
            and str(c.get("target")) == tgt
            for c in ordered
        )
        if not has_cause:
            out.append(InvariantViolation("I6", "error", arts.game_id, (str(e.get("event_id")),),
                                          f"player_died({tgt}) has no candidate cause event"))
    return out


_ALL_CHECKS.append(check_i6)
```

- [ ] **Step 4: Run to verify it passes** — PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I6 effect_causality (weak/inferred)"
```

---

## Task 11: I7 `no_unknown_final_state_mutation` (WEAK — event-chain self-consistency)

**Files:**
- Modify: `src/werewolf_eval/invariants/checker.py`
- Test: `tests/test_invariants_checker.py`

**Context:** Without re-running the engine, I7 checks chain self-consistency that needs no external truth: (1) every death-commit target is a known player; (2) every `role_revealed` matches that player's role in the `players` map. (The stronger "dead in final snapshot with no death event" check needs a god snapshot and rides a later disk-only extension — not in this WEAK slice.)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants.checker import check_i7

_I7_PLAYERS = [{"player_id": "p1", "role": "seer", "team": "villager"},
               {"player_id": "p2", "role": "werewolf", "team": "werewolf"}]


def _reveal(eid, target, role, seq):
    return {"event_id": eid, "type": "role_revealed", "actor": "system", "target": target,
            "round": 1, "phase": "day", "visibility": "all", "sequence": seq,
            "data": {"summary": f"{target} revealed as {role}", "revealed_role": role}}


class TestI7(unittest.TestCase):
    def test_consistent_chain_passes(self):
        evs = [_death("e1", "p2", seq=1), _reveal("e2", "p2", "werewolf", 2)]
        self.assertEqual(check_i7(_arts(evs, players=_I7_PLAYERS)), [])

    def test_death_of_unknown_player_fails(self):
        v = check_i7(_arts([_death("e1", "p9", seq=1)], players=_I7_PLAYERS))
        self.assertTrue(any(x.id == "I7" for x in v))

    def test_reveal_wrong_role_fails(self):
        evs = [_reveal("e2", "p2", "villager", 1)]  # p2 is werewolf
        v = check_i7(_arts(evs, players=_I7_PLAYERS))
        self.assertTrue(any(x.id == "I7" for x in v))
```

- [ ] **Step 2: Run to verify it fails** — `ImportError`

- [ ] **Step 3: Implement in `checker.py`**

```python
def check_i7(arts: RunArtifacts) -> list[InvariantViolation]:
    """WEAK final-state consistency: death-commit targets are known players, and
    role_revealed events match the players map. (Silent-mutation-vs-final-snapshot
    is a later disk-only extension.)"""
    roles = {str(p["player_id"]): str(p.get("role")) for p in arts.players}
    known = set(roles)
    out: list[InvariantViolation] = []
    for e in arts.events:
        t = e.get("type")
        if t in DEATH_COMMIT_TYPES and arts.players and str(e.get("target")) not in known:
            out.append(InvariantViolation("I7", "error", arts.game_id, (str(e.get("event_id")),),
                                          f"death of unknown player {e.get('target')}"))
        if t == "role_revealed":
            tgt = str(e.get("target"))
            revealed = str(e.get("data", {}).get("revealed_role", ""))
            if revealed and tgt in roles and revealed != roles[tgt]:
                out.append(InvariantViolation("I7", "error", arts.game_id, (str(e.get("event_id")),),
                                              f"role_revealed({tgt}={revealed}) != actual {roles[tgt]}"))
    return out


_ALL_CHECKS.append(check_i7)
```

> NOTE: confirm the engine writes the revealed role into `data` (grep `role_revealed` at `:1041` — if the role is only in `summary`, parse it from there or relax the reveal check to a no-op and keep only the unknown-player check). The test's `_reveal` fixture sets `data.revealed_role`; align the fixture to whatever the engine actually emits.

- [ ] **Step 4: Run to verify it passes** — PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/checker.py tests/test_invariants_checker.py
git commit -m "feat(invariants): I7 final-state self-consistency (weak)"
```

---

## Task 12: `check_run` integration — all checks registered, clean game passes

**Files:**
- Test: `tests/test_invariants_checker.py`

- [ ] **Step 1: Write the failing/integration test**

```python
# append to tests/test_invariants_checker.py
from werewolf_eval.invariants import check_run


class TestCheckRunIntegration(unittest.TestCase):
    def test_clean_minimal_game_passes(self):
        players = [{"player_id": "p1", "role": "seer", "team": "villager"},
                   {"player_id": "p2", "role": "werewolf", "team": "werewolf"}]
        events = [_cause("e1", "werewolf_kill", "p1", 1), _death("e2", "p1", seq=2)]
        turns = [{"request_id": "g_r01_p2", "phase": "night", "actor": "p2",
                  "observation_source_event_ids": ["e1"]}]
        arts = RunArtifacts(game_id="g", players=players, events=events,
                            decisions=[], provider_turns=turns, result=None)
        self.assertEqual(check_run(arts), [])

    def test_artifact_gap_reported_not_raised(self):
        v = check_run(RunArtifacts("g", [], [], [], [], None, gaps=("game-log.json",)))
        self.assertTrue(any(x.severity == "artifact_gap" for x in v))
```

- [ ] **Step 2: Run** — Expected PASS (all 7 checks registered in `_ALL_CHECKS` from Tasks 4-11; `werewolf_kill` is tagged `werewolf_team` and sourced by the wolf p2, so I4b passes).

> If `test_clean_minimal_game_passes` fails on I4b, the wolf is not entitled to its own `werewolf_kill` — verify `seat_index_from_players` gives p2 `team=werewolf` and the event `visibility=werewolf_team`. Fix the fixture to match real emit tags.

- [ ] **Step 3: Commit**

```bash
git add tests/test_invariants_checker.py
git commit -m "test(invariants): check_run integration — clean game passes, gaps reported"
```

---

## Task 13: B1 guard — `assert_prompt_entitled` (raises `PromptLeakError`)

**Files:**
- Create: `src/werewolf_eval/invariants/guards.py`
- Test: `tests/test_invariants_guards.py`

**Context:** Runtime fail-closed. Reuses the SAME `visibility_oracle.entitled` as I4b (single source). Raises before a leaked prompt can be sent — a leak cannot be un-sent. **Audit-row emission is intentionally omitted** (the spec §5 once said "raise, audit"): the raise propagates out of `run()` (which only catches `BudgetExhausted`) and aborts the game with NO artifact write — keeping B1 byte-neutral on the happy path, same rationale as the B4 silent-no-op ruling. The traceback is the record.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_invariants_guards.py
import unittest
from werewolf_eval.invariants.guards import assert_prompt_entitled, PromptLeakError
from werewolf_eval.invariants.visibility_oracle import seat_index_from_players

_PLAYERS = [{"player_id": "p1", "role": "seer", "team": "villager"},
            {"player_id": "p2", "role": "villager", "team": "villager"}]
_SEER_EV = {"event_id": "e1", "type": "seer_check", "actor": "p1", "target": "p3",
            "visibility": "seer", "round": 1, "phase": "night", "data": {"summary": ""}}


class TestB1(unittest.TestCase):
    def setUp(self):
        self.idx = seat_index_from_players(_PLAYERS)
        self.by_id = {"e1": _SEER_EV}

    def test_entitled_prompt_does_not_raise(self):
        assert_prompt_entitled("p1", ["e1"], self.by_id, self.idx)  # seer sees seer event

    def test_non_entitled_prompt_raises(self):
        with self.assertRaises(PromptLeakError):
            assert_prompt_entitled("p2", ["e1"], self.by_id, self.idx)  # villager must not

    def test_unknown_event_id_is_skipped(self):
        assert_prompt_entitled("p2", ["missing"], self.by_id, self.idx)  # no raise


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails** — `ModuleNotFoundError: ...guards`

- [ ] **Step 3: Write `guards.py` (B1 portion)**

```python
# src/werewolf_eval/invariants/guards.py
from __future__ import annotations

from typing import Any

from werewolf_eval.invariants.visibility_oracle import entitled


class PromptLeakError(Exception):
    """A provider call's prompt would source an event the seat may not see."""


class DoubleDeathCommitError(Exception):
    """A player would be committed dead a second time."""


def assert_prompt_entitled(seat: str, source_event_ids: list[str],
                           events_by_id: dict[str, Any],
                           seat_index: dict[str, dict[str, object]]) -> None:
    """B1: fail-closed before provider.respond/decide. Uses the observer's
    independent visibility (NOT _build_obs). Unknown event ids are skipped (the
    offline checker reports artifact gaps; the runtime guard never aborts on one)."""
    for eid in source_event_ids:
        ev = events_by_id.get(eid)
        if ev is None:
            continue
        if not entitled(seat, ev, seat_index):
            raise PromptLeakError(
                f"seat {seat} prompt would source non-entitled event {eid} "
                f"(visibility={ev.get('visibility')})")
```

- [ ] **Step 4: Run to verify it passes** — PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/guards.py tests/test_invariants_guards.py
git commit -m "feat(invariants): B1 assert_prompt_entitled guard"
```

---

## Task 14: B4 guard — `assert_death_commit_once` (raises `DoubleDeathCommitError`)

**Files:**
- Modify: `src/werewolf_eval/invariants/guards.py`
- Test: `tests/test_invariants_guards.py`

**Context:** Called right BEFORE emitting a `player_died`/`player_eliminated`, against a persistent `committed` set. The LEGAL candidate-skip (`pid not in self._alive`) never reaches this guard — it stays a silent no-op (Q5 ruling). Happy path never raises.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_guards.py
from werewolf_eval.invariants.guards import assert_death_commit_once, DoubleDeathCommitError


class TestB4(unittest.TestCase):
    def test_first_commit_ok(self):
        committed: set[str] = set()
        assert_death_commit_once("p3", committed)
        self.assertIn("p3", committed)

    def test_second_commit_raises(self):
        committed = {"p3"}
        with self.assertRaises(DoubleDeathCommitError):
            assert_death_commit_once("p3", committed)
```

- [ ] **Step 2: Run to verify it fails** — `ImportError: cannot import name 'assert_death_commit_once'`

- [ ] **Step 3: Add to `guards.py`**

```python
def assert_death_commit_once(pid: str, committed: set[str]) -> None:
    """B4: call immediately before emitting a death-commit event for `pid`. The
    legal duplicate-CANDIDATE skip (engine's `in self._alive` gate) never reaches
    here. A duplicate committed EVENT is the hard fail."""
    if pid in committed:
        raise DoubleDeathCommitError(f"player {pid} committed dead twice")
    committed.add(pid)
```

- [ ] **Step 4: Run to verify it passes** — PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/guards.py tests/test_invariants_guards.py
git commit -m "feat(invariants): B4 assert_death_commit_once guard"
```

---

## Task 15: Engine wiring — B1 at the 4 provider-call sites

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py` (4 insertions + 1 helper)
- Test: `tests/test_invariants_engine_wiring.py`

**Context:** Insert `assert_prompt_entitled` right after `observation_source_event_ids` is ready and BEFORE `decide`/`respond`, at all 4 anchors (strict `:535→538`, witch `:765→771`, speech `:842→847`, hunter `:908→913`). The seat_index is synthesized from `self._config.players` (the engine HAS the true roles; the guard's independence comes from using the observer's verdict logic, not from where roles come from). Add a small helper so the 4 sites are one line each.

- [ ] **Step 1: Write the failing integration test**

```python
# tests/test_invariants_engine_wiring.py
import unittest
from werewolf_eval.invariants.guards import PromptLeakError

# Reuse the project's existing fake-game harness. Grep tests/ for how a 4-role
# fake game is constructed (e.g. build_emergent_fake_agents + EmergentGameEngine);
# import the same builder here. The two tests:
#
#   1. A normal fake game runs to completion with B1 wired and NEVER raises
#      PromptLeakError (happy-path parity — the guard is byte-neutral).
#   2. A monkeypatched _build_obs that injects a seer_check event into a villager's
#      observation makes the engine raise PromptLeakError (the guard bites).


class TestB1Wiring(unittest.TestCase):
    def test_normal_fake_game_does_not_trip_b1(self):
        engine = _build_four_role_fake_engine(seed=0)   # implement via the existing harness
        outcome = engine.run()
        self.assertIsNotNone(outcome)                   # completed, no PromptLeakError

    def test_injected_leak_trips_b1(self):
        # Strict path (wolf/seer/vote via _provider_action).
        engine = _build_four_role_fake_engine(seed=0)
        _monkeypatch_build_obs_to_leak_seer_event(engine, seat="strict")
        with self.assertRaises(PromptLeakError):
            engine.run()

    def test_injected_leak_at_direct_site_trips_b1(self):
        # HIGH-1 regression: the guard must sit OUTSIDE the try at the witch/speech/
        # hunter DIRECT-respond sites, where a broad `except Exception` would otherwise
        # swallow PromptLeakError. Inject the leak into a direct-respond turn (speech)
        # and assert the error PROPAGATES (is not downgraded to a fallback).
        engine = _build_four_role_fake_engine(seed=0)
        _monkeypatch_leak_into_direct_respond_turn(engine, site="speech")
        with self.assertRaises(PromptLeakError):
            engine.run()
```

> IMPLEMENTER: fill `_build_four_role_fake_engine`, `_monkeypatch_build_obs_to_leak_seer_event`, and `_monkeypatch_leak_into_direct_respond_turn` using the existing fake harness (the same one `tests/test_action_runtime_parity.py` / `tests/test_emergent_engine.py` use). Each monkeypatch appends a `visibility:"seer"` event id into a non-seer seat's `rendered.source_event_ids` (or into the obs the renderer reads) — the first targeting a strict-path turn, the second a direct-respond turn (witch/speech/hunter). **The direct-site test is mandatory: it is the only thing that proves the guard was placed outside the `try` at those 3 sites** (if placed inside, this test fails — the leak is swallowed and the game completes normally). Keep the seed at 0 for determinism.

- [ ] **Step 2: Run to verify it fails** — both tests error/fail (B1 not wired yet; the injected-leak test does not raise).

- [ ] **Step 3: Add the seat_index helper to `EmergentGameEngine`** (near `_build_obs`)

```python
    def _b1_seat_index(self) -> dict[str, dict[str, object]]:
        """Synthesize the visibility-oracle seat_index from the config roster, marked
        trusted so the observer's _trusted_role_for_player accepts it. Cached."""
        cached = getattr(self, "_b1_seat_index_cache", None)
        if cached is None:
            from werewolf_eval.invariants.visibility_oracle import seat_index_from_players
            cached = seat_index_from_players(
                [{"player_id": p.player_id, "role": p.role, "team": p.team}
                 for p in self._config.players])
            self._b1_seat_index_cache = cached
        return cached
```

- [ ] **Step 4: Insert B1 at the 4 anchors**

**CRITICAL — the guard MUST sit OUTSIDE the `try:` at every site.** All four provider calls are wrapped in `try: <call> ... except Exception` (strict `_provider_action` `try:537`/`except:549`; witch `try:770`/`except:780`; speech `try:846`/`except:851`; hunter `try:912`). If `assert_prompt_entitled` is placed INSIDE the `try`, the broad `except Exception` swallows `PromptLeakError` and silently downgrades the turn to a parse/error fallback — defeating the guard at that site (the exact "silent pass" this net exists to kill). Place each call AFTER the turn dict is built / appended and BEFORE the `try:`.

Module-top import (once, with the other imports):

```python
from werewolf_eval.invariants.guards import assert_prompt_entitled
```

Strict path — in `_provider_action`, after the `turn = {...}` literal closes (`:536`) and BEFORE `try:` (`:537`):

```python
        assert_prompt_entitled(player_id, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
```

Witch path — after `self._provider_turns.append(turn)` (`:767`) and BEFORE `try:` (`:770`):

```python
        assert_prompt_entitled(witch, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
```

Speech path — after `self._provider_turns.append(turn)` (`:844`) and BEFORE `try:` (`:846`):

```python
        assert_prompt_entitled(player_id, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
```

Hunter path — after `self._provider_turns.append(turn)` (`:910`) and BEFORE `try:` (`:912`):

```python
        assert_prompt_entitled(hunter, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
```

- [ ] **Step 5: Run to verify it passes** — both tests PASS.

- [ ] **Step 6: Regression — full suite stays green (B1 is byte-neutral on happy path)**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
Expected: all green (the 896 pre-existing + new). If any pre-existing parity/byte test fails, B1 is raising on a real game → STOP: either a genuine latent leak (investigate) or a fixture visibility mismatch. Do not weaken the guard to pass; diagnose the prompt that tripped it.

- [ ] **Step 7: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_invariants_engine_wiring.py
git commit -m "feat(engine): wire B1 prompt-leak guard at 4 provider-call sites"
```

---

## Task 16: Engine wiring — B4 at the 3 death-commit sites

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py` (1 field + 3 insertions)
- Test: `tests/test_invariants_engine_wiring.py`

**Context:** Add `self._death_committed: set[str]` (init in `__init__`/`run` setup). Call `assert_death_commit_once(pid, self._death_committed)` immediately before each death-commit emit — night `:1017`, day-vote `:1040`, trigger `:880`. The legal candidate-skip at `:1014` stays a silent no-op (do NOT guard it). Happy path never raises (each player commits once).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_invariants_engine_wiring.py
from werewolf_eval.invariants.guards import DoubleDeathCommitError


class TestB4Wiring(unittest.TestCase):
    def test_normal_fake_game_does_not_trip_b4(self):
        engine = _build_four_role_fake_engine(seed=0)
        outcome = engine.run()
        self.assertIsNotNone(outcome)

    def test_double_commit_trips_b4(self):
        engine = _build_four_role_fake_engine(seed=0)
        # Force a second commit of an already-committed pid (e.g. monkeypatch the
        # settler to return a victim twice, or call _trigger_on_death on a pid that
        # is already in _death_committed). See IMPLEMENTER note.
        _force_double_death_commit(engine)
        with self.assertRaises(DoubleDeathCommitError):
            engine.run()
```

> IMPLEMENTER: `_force_double_death_commit` should drive a *committed* (not merely candidate) duplicate — e.g. monkeypatch `_trigger_on_death` to fire twice on the same target, or seed a settler that yields a death for a pid already emitted. NOT the legal co-victim skip (that must stay silent).

- [ ] **Step 2: Run to verify it fails** — `_death_committed`/guard not wired; the forced double-commit does not raise.

- [ ] **Step 3: Add the field** — in the per-run setup (where `self._alive` is initialized), add:

```python
        self._death_committed: set[str] = set()
```

- [ ] **Step 4: Insert B4 before each commit emit**

Module-top import (with the others):

```python
from werewolf_eval.invariants.guards import assert_death_commit_once
```

Night loop — before `:1017` emit, after `self._alive.discard(pid)`:

```python
                assert_death_commit_once(pid, self._death_committed)
                self._emit("night", rnd, "player_died", "system", pid, "all", f"{pid} died during the night.")
```

Day-vote — before `:1040` emit, after `self._alive.discard(eliminated)`:

```python
                assert_death_commit_once(eliminated, self._death_committed)
                self._emit("day", rnd, "player_eliminated", "system", eliminated, "all", f"{eliminated} eliminated by vote.")
```

Trigger (`_trigger_on_death`) — before `:880` emit, after `self._alive.discard(target)`:

```python
            assert_death_commit_once(target, self._death_committed)
            self._emit(phase, rnd, "player_died", "system", target, "all", f"{target} was shot by {dead}.")
```

> The `discard` already precedes each emit, so the guard sits between `discard` and `emit`. The legal `:1014` `continue` is upstream of `discard` and never reaches the guard — correct.

- [ ] **Step 5: Run to verify it passes** — both tests PASS.

- [ ] **Step 6: Regression — full suite green**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
Expected: all green. A failure here means a normal game double-commits a player → a real bug, not a guard problem.

- [ ] **Step 7: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_invariants_engine_wiring.py
git commit -m "feat(engine): wire B4 double-death guard at 3 commit sites + _death_committed set"
```

---

## Task 17: L3 — deterministic fuzz over synthetic artifacts

**Files:**
- Create: `src/werewolf_eval/invariants/fuzz.py`
- Test: `tests/test_invariants_fuzz.py`

**Context:** Deterministic `random.Random(seed)` over a fixed seed bank (0–49). This slice fuzzes **synthetic `RunArtifacts`** (well-formed games + known-bad mutations) straight into `check_run` — fast, no engine, fully deterministic, covers the checker's logic. The contract: every well-formed seed PASSES all L1; every known-bad generator FAILS its targeted invariant.

> SCOPE NOTE (no silent cap): the spec's §6 also envisions engine-level fuzz (generated scripts → `build_emergent_fake_agents` → engine → L1), which additionally exercises engine↔checker integration. That is deferred to a follow-up; this task ships the synthetic-artifact fuzz, which is the deterministic core. The engine-level variant needs the `build_emergent_fake_agents` script schema — a separate task once this lands.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_invariants_fuzz.py
import unittest
from werewolf_eval.invariants import check_run
from werewolf_eval.invariants.fuzz import SEED_BANK, well_formed_game, known_bad_games


class TestFuzz(unittest.TestCase):
    def test_every_well_formed_seed_passes_all_invariants(self):
        for seed in SEED_BANK:
            arts = well_formed_game(seed)
            violations = [v for v in check_run(arts) if v.severity == "error"]
            self.assertEqual(violations, [], f"seed {seed} produced {violations}")

    def test_each_known_bad_fails_its_target(self):
        for label, arts, expected_id in known_bad_games(seed=0):
            ids = {v.id for v in check_run(arts)}
            self.assertIn(expected_id, ids, f"{label} should fail {expected_id}; got {ids}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails** — `ModuleNotFoundError: ...fuzz`

- [ ] **Step 3: Write `fuzz.py`**

```python
# src/werewolf_eval/invariants/fuzz.py
from __future__ import annotations

import random
from typing import Any

from werewolf_eval.invariants.artifacts import RunArtifacts

SEED_BANK = tuple(range(50))

_ROLES = [("p1", "seer", "villager"), ("p2", "witch", "villager"),
          ("p3", "hunter", "villager"), ("p4", "werewolf", "werewolf")]


def _players() -> list[dict[str, Any]]:
    return [{"player_id": pid, "role": r, "team": t} for pid, r, t in _ROLES]


def _ev(seq: int, etype: str, actor: str, target: str, vis: str, rnd: int = 1,
        phase: str = "night") -> dict[str, Any]:
    return {"event_id": f"g_e{seq:03d}", "sequence": seq, "round": rnd, "phase": phase,
            "type": etype, "actor": actor, "target": target, "visibility": vis,
            "data": {"summary": ""}}


def well_formed_game(seed: int) -> RunArtifacts:
    """A legal game whose shape varies by seed: the wolf kills a random villager,
    the seer checks a random seat, occasionally the witch saves/poisons — always
    inside the rules, so it must PASS every invariant."""
    rng = random.Random(seed)
    seq = 0
    events: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []

    def add(etype, actor, target, vis, phase="night"):
        nonlocal seq
        seq += 1
        events.append(_ev(seq, etype, actor, target, vis, phase=phase))
        return events[-1]["event_id"]

    # night: wolf kill (werewolf_team vis), seer check (seer vis)
    victim = rng.choice(["p1", "p2", "p3"])
    wk = add("werewolf_kill", "p4", victim, "werewolf_team")
    sc = add("seer_check", "p1", rng.choice(["p2", "p3", "p4"]), "seer")
    turns.append({"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
                  "observation_source_event_ids": [wk]})
    turns.append({"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": [sc]})
    # commit the death once
    add("player_died", "system", victim, "all")
    return RunArtifacts(game_id="g", players=_players(), events=events,
                        decisions=[], provider_turns=turns, result=None)


def known_bad_games(seed: int) -> list[tuple[str, RunArtifacts, str]]:
    """Each entry = (label, artifacts, expected_failing_invariant_id)."""
    base = well_formed_game(seed)
    out: list[tuple[str, RunArtifacts, str]] = []

    # I1: commit the same death twice
    evs = list(base.events) + [_ev(900, "player_died", "system", base.events[-1]["target"], "all")]
    out.append(("double_death", _clone(base, events=evs), "I1"))

    # I3: second witch_save by the same actor
    evs = list(base.events) + [
        _ev(910, "witch_save", "p2", "p1", "witch"),
        _ev(911, "witch_save", "p2", "p3", "witch")]
    out.append(("double_antidote", _clone(base, events=evs), "I3"))

    # I4b: a villager (p3) sources a seer-tagged event
    seer_ev = next(e for e in base.events if e["type"] == "seer_check")
    turns = list(base.provider_turns) + [
        {"request_id": "g_r01_p3", "phase": "night", "actor": "p3",
         "observation_source_event_ids": [seer_ev["event_id"]]}]
    out.append(("villager_reads_seer", _clone(base, provider_turns=turns), "I4b"))

    # I5: same (request_id, phase) twice
    turns = list(base.provider_turns) + [
        {"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
         "observation_source_event_ids": []}]
    out.append(("double_settle", _clone(base, provider_turns=turns), "I5"))

    # I6: an uncaused death
    evs = list(base.events) + [_ev(920, "player_died", "system", "p9_ghost", "all")]
    out.append(("uncaused_death", _clone(base, events=evs), "I6"))

    return out


def _clone(arts: RunArtifacts, **over: Any) -> RunArtifacts:
    return RunArtifacts(
        game_id=over.get("game_id", arts.game_id),
        players=over.get("players", arts.players),
        events=over.get("events", arts.events),
        decisions=over.get("decisions", arts.decisions),
        provider_turns=over.get("provider_turns", arts.provider_turns),
        result=over.get("result", arts.result),
        gaps=over.get("gaps", arts.gaps),
    )
```

> The `double_death` known-bad reuses the last event's target (the legitimately-killed victim), so it also trips I6-style checks only if uncaused — keep its expected id as `I1` (the double-commit is unambiguous). If `known_bad_games` finds a generator whose expected failure does not fire, that generator is itself a test failure (do not silently pass) — fix the generator or the invariant.

- [ ] **Step 4: Run to verify it passes** — PASS (both tests; all 50 well-formed seeds clean, all 5 known-bad trip their target).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/invariants/fuzz.py tests/test_invariants_fuzz.py
git commit -m "feat(invariants): L3 deterministic synthetic-artifact fuzz + seed bank"
```

---

## Task 18: Acceptance criterion 3 — injected bad examples each fail their target

**Files:**
- Test: `tests/test_invariants_bad_examples.py`
- Create: `tests/fixtures/invariants_bad_examples/` (optional JSON fixtures, or build in-test)

**Context:** Spec §10 criterion 3 — one curated injected violation per invariant, asserting it FAILS the targeted invariant (and only sympathetically others). This overlaps the fuzz known-bad set but is a stable, human-readable acceptance gate (not seed-derived).

- [ ] **Step 1: Write the test (it will pass once the checker is complete — this is the acceptance gate, not new production code)**

```python
# tests/test_invariants_bad_examples.py
import unittest
from werewolf_eval.invariants import check_run, RunArtifacts


def _ev(seq, etype, actor, target, vis, phase="night"):
    return {"event_id": f"g_e{seq:03d}", "sequence": seq, "round": 1, "phase": phase,
            "type": etype, "actor": actor, "target": target, "visibility": vis,
            "data": {"summary": ""}}


_PLAYERS = [{"player_id": "p1", "role": "seer", "team": "villager"},
            {"player_id": "p2", "role": "witch", "team": "villager"},
            {"player_id": "p3", "role": "hunter", "team": "villager"},
            {"player_id": "p4", "role": "werewolf", "team": "werewolf"}]


def _arts(events, turns=None):
    return RunArtifacts("g", _PLAYERS, events, [], turns or [], None)


class TestBadExamples(unittest.TestCase):
    def test_i1_double_player_died(self):
        evs = [_ev(1, "werewolf_kill", "p4", "p1", "werewolf_team"),
               _ev(2, "player_died", "system", "p1", "all"),
               _ev(3, "player_died", "system", "p1", "all")]
        self.assertIn("I1", {v.id for v in check_run(_arts(evs))})

    def test_i3_second_poison(self):
        evs = [_ev(1, "witch_poison", "p2", "p4", "witch"),
               _ev(2, "witch_poison", "p2", "p3", "witch")]
        self.assertIn("I3", {v.id for v in check_run(_arts(evs))})

    def test_i4b_non_entitled_prompt(self):
        evs = [_ev(1, "seer_check", "p1", "p4", "seer")]
        turns = [{"request_id": "g_r01_p3", "phase": "night", "actor": "p3",
                  "observation_source_event_ids": ["g_e001"]}]
        self.assertIn("I4b", {v.id for v in check_run(_arts(evs, turns))})

    def test_i5_double_settle(self):
        turns = [{"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
                  "observation_source_event_ids": []},
                 {"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
                  "observation_source_event_ids": []}]
        self.assertIn("I5", {v.id for v in check_run(_arts([], turns))})

    def test_i6_uncaused_death(self):
        evs = [_ev(1, "player_died", "system", "p4", "all")]
        self.assertIn("I6", {v.id for v in check_run(_arts(evs))})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — Expected PASS (the checker built in Tasks 4-12 satisfies every criterion-3 gate).**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_invariants_bad_examples -v`

- [ ] **Step 3: Commit**

```bash
git add tests/test_invariants_bad_examples.py
git commit -m "test(invariants): acceptance criterion 3 — injected bad examples per invariant"
```

---

## Task 19: Acceptance criteria 1 & 2 — real fake game offline + full-suite regression

**Files:**
- Test: `tests/test_invariants_engine_wiring.py` (add the offline end-to-end case)

**Context:** Criterion 1 — a real fake-deterministic full game's persisted artifacts run the checker offline with PASS on all 7. Criterion 2 — offline, no API key. (The live-smoke half of criterion 2 is exercised manually against a real run dir; this task automates the fake half, which is byte-identical in shape.)

- [ ] **Step 1: Write the end-to-end test**

```python
# append to tests/test_invariants_engine_wiring.py
import tempfile
from pathlib import Path
from werewolf_eval.invariants import check_run


class TestEndToEndOffline(unittest.TestCase):
    def test_persisted_fake_game_passes_checker(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d) / "run"
            _run_persisted_four_role_fake_game(out_dir, seed=0)  # via the fake runner (Task 2 added provider-turns.json)
            violations = [v for v in check_run(out_dir) if v.severity == "error"]
            self.assertEqual(violations, [], f"clean fake game tripped: {violations}")
```

> IMPLEMENTER: `_run_persisted_four_role_fake_game` drives `run_emergent_fake_runtime` to write a full run dir (game-log/decision-log/provider-turns/snapshots). Reuse Task 2's runner call. The checker reads the dir via `RunArtifacts.from_run_dir`.

- [ ] **Step 2: Run to verify it passes** — PASS (a clean fake game trips nothing).

> If I4b trips on a real fake game, a genuine visibility tag/role mismatch exists between the engine's emit tags and the observer's projection — investigate (it may be a real latent leak the net just caught, or a tag the observer doesn't model). Do not relax I4b to pass.

- [ ] **Step 3: Final full-suite regression**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
Expected: all green — the pre-existing suite + all new `test_invariants_*`. The guards added no artifact bytes, so every parity/byte test stays green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_invariants_engine_wiring.py
git commit -m "test(invariants): acceptance criteria 1&2 — persisted fake game passes checker offline"
```

---

## Self-Review (run against the spec before handing off)

**1. Spec coverage:**

| Spec section | Task |
|---|---|
| §4 I1 death_once | Task 4 |
| §4 I2 no_dead_actor | Task 5 |
| §4 I3 capability_not_overused (per actor+cap) | Task 6 |
| §4 I4a prompt_subset (in-memory) | Task 7 |
| §4 I4b prompt_visibility_entitled | Task 8 |
| §4 I5 decision_settled_once `(request_id, phase)` | Task 9 |
| §4 I6 effect_causality (weak) | Task 10 |
| §4 I7 final-state (weak self-consistency) | Task 11 |
| §5 B1 prompt-leak guard + wiring | Tasks 13, 15 |
| §5 B4 double-death guard + wiring | Tasks 14, 16 |
| §5 B2/B3 deferred | not in slice (correct per spec) |
| §6 L3 fuzz | Task 17 (synthetic core; engine-level deferred, noted) |
| §8 fake-runner provider-turns gap | Task 2 |
| §9 visibility oracle (single source) | Task 3 |
| §10 criteria 1/2/3 | Tasks 19, 19, 18 |
| §12 file structure | Task 1 + per-task creates |

**2. Placeholder scan:** The three `IMPLEMENTER` notes (Tasks 2, 15, 16, 19) point at the existing fake harness rather than inlining its constructor — acceptable because that harness already exists and varies by how the repo's current tests build it; the engineer must match the in-repo pattern, not invent one. Every production code block is complete and runnable. No `TODO`/`TBD`/"add error handling".

**3. Type consistency:** `RunArtifacts` fields are identical across Tasks 1/4-12/17. `InvariantViolation(id, severity, game_id, event_ids, detail)` is used uniformly. `entitled(seat, event, seat_index)` and `seat_index_from_players(players)` signatures match between Task 3, Task 8, Task 13, Task 15. `assert_prompt_entitled(seat, source_event_ids, events_by_id, seat_index)` and `assert_death_commit_once(pid, committed)` match between Tasks 13/14 and their wiring in 15/16.

**Known weak points carried from spec (intended, not gaps):** I6/I7 are WEAK (STRICT forms ride the EffectQueue); I4a is in-memory only; L3 is synthetic-artifact (engine-level fuzz deferred); B2/B3 deferred to ledger/EffectQueue. All match the spec's explicit "rides later rewrites" list (§11).

**Round-2 plan review (GO_WITH_FIXES) applied 2026-06-10:**
- **HIGH-1** — B1 guard moved OUTSIDE the `try:` at ALL 4 sites (a broad `except Exception` at strict `:549` / witch `:780` / speech `:851` / hunter would swallow `PromptLeakError` and silently downgrade to a fallback — defeating the guard). The reviewer flagged the 3 direct sites; verification showed the strict path has the same `except Exception`, so all 4 are fixed. T15 adds a **mandatory** direct-site leak test — the only thing that proves the guard sits outside the try at witch/speech/hunter.
- **MEDIUM-1** — I2 `ACTIVE_ACTION_TYPES` adds `player_vote` (verified it IS a real game-log event: `VoteResolver.render → EventRow(..,"player_vote",..)`, `turn.py:158`) + a dead-voter→I2 test (T5).
- **LOW** — B1 audit-row intentionally omitted (byte-neutral, same as B4 silent ruling), noted in T13; T2 also runs the existing `test_run_emergent_fake_runtime` suite.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-10-p2a-invariant-safety-net.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Natural checkpoints: after Task 12 (L1 checker complete + green), after Task 16 (guards wired + full suite green), after Task 19 (acceptance).

**2. Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints.

**Which approach?**
