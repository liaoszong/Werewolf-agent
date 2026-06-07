# Emergent role_projection + mid-game god Snapshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `EmergentGameEngine` emit per-seat `role_projection` snapshots at setup (so observer `/projection role:pN` unlocks that seat's private seer/witch/wolf-team events) and per-round night/day `god` snapshots (so mid-game `alive` is accurate), with zero changes to observer/protocol/Qt.

**Architecture:** Engine-side only. Reuse the existing P1 primitives `runtime_events.build_role_projection_snapshot` + `RuntimeEventWriter.write_snapshot` exactly as the scripted `game_engine.py` already does. The observer (`observer_visibility.build_seat_role_index`, `event_visible_in_projection`) already consumes these snapshot shapes — emergent just never produced them. All snapshot writes are no-ops when no `runtime_events` writer is wired (offline CLI path unchanged).

**Tech Stack:** Python 3.12, `unittest`, package `werewolf_eval` under `src/` (run with `PYTHONPATH=src`).

**Spec:** `docs/superpowers/specs/2026-06-07-emergent-role-projection-snapshots-design.md` (commit `f512af7`).

**Branch:** create `p2-emergent-role-projection` off `main` before Task 1.

---

## File Structure

- **Modify** `src/werewolf_eval/emergent_engine.py`
  - Add `_write_role_snapshot(self, player_id: str)` — build the seat's observation and write one `role_view_{pid}` role_projection snapshot.
  - In `_run_inner` setup section (after `setup_god_view`): call `_write_role_snapshot` for all 6 seats.
  - In `_run_inner` round loop: add a `god_view_r{rnd}_night` write after the night death set is applied, and a `god_view_r{rnd}_day` write after the day elimination is applied. Reuse the existing `_write_god_snapshot(name, rnd, phase)` helper (it already reads `self._alive` for `alive_players`).
- **Create** `tests/test_emergent_role_projection.py` — engine-level: role snapshot count/shape/visibility-event, mid-game god file presence, prefix/subset alive-shrink, leak scan.
- **Modify** `tests/test_observer_emergent_bridge.py` — flip the seam test from "downgrade to hidden" to "private events unlocked", keep the reverse non-leak assertion (role:p5).

**Forbidden (git diff MUST be empty):** `observer_server.py`, `observer_protocol.py`, `observer_visibility.py`, `clients/qt_observer/**`, `game_engine.py`, `emergent_fake_script.py`, `runtime_events.py`, `scoring.py`, `attribution.py`, `settlement_bundle.py`, `deepseek_launcher.py`, `run_observer_server.py`, `run_emergent_fake_runtime.py`, `PROJECT_MAP.md`, `TASKS.md`.

**Reference facts (verified against current code):**
- `EmergentGameEngine._build_obs(self, player_id, phase, rnd) -> AgentObservation` (emergent_engine.py:343) — builds the role-safe observation; for a wolf, `known_roles` already includes both wolves.
- `EmergentGameEngine._write_god_snapshot(self, name, rnd, phase)` (emergent_engine.py:330) — no-op without writer; else writes `build_god_snapshot(..., alive_players=sorted(self._alive), private_event_ids=[])` via `write_snapshot(name, snap, visibility="internal", round=rnd, phase=phase, actor="system")`.
- `runtime_events.build_role_projection_snapshot(*, run_id, observation) -> dict` (runtime_events.py:484) — returns `{"snapshot_type": "role_projection", "player_id", "role", "team", "projected_known_roles", ...}`. Hides werewolf roles from non-wolf observers. **No `visibility` key in the JSON.**
- `RuntimeEventWriter.write_snapshot(name, snapshot, *, visibility, round, phase, actor) -> str` (runtime_events.py:382) — redacts secrets, writes `snapshots/{name}.json`, AND emits a `snapshot_written` event carrying `visibility` + `payload={"snapshot_name": name}`.
- `_run_inner` (emergent_engine.py:767): setup emits `role_assignment` then `_write_god_snapshot("setup_god_view", 0, "setup")`; round loop applies night deaths (`self._alive.discard(pid)` + `player_died` emit) then win-check/break, else day announcement/speeches/votes, then elimination (`self._alive.discard(eliminated)` + `player_eliminated`/`role_revealed`), then win-check/break; on win it emits `game_over` + `_write_god_snapshot("final_god_view", end_round, "game_end")`.
- `observer_visibility.build_seat_role_index(run_dir)` keeps each seat's LATEST `role_projection` (by `_snap_order=(round, phase_rank)`), and `alive` is taken from the LATEST **god** snapshot's `alive_players`. `_PHASE_RANK = {setup:0, night:1, day:2, vote:3, game_end:4}`.
- `observer_visibility.event_visible_in_projection(event, perspective, seat_index) -> (visible, reason)` — role:pN unlocks `seer`/`witch` only when `_trusted_role_for_player(seat_index, pN) == role` (role_source must be `role_projection_snapshot`); `werewolf_team` needs trusted team werewolf. Reasons: `seer_event`/`witch_event`/`werewolf_team_event`/`public_event`/`hidden`/`god_view`.
- Default board (build_emergent_config): p1/p2 werewolf, p3 seer, p4 witch, p5/p6 villager.
- Runtime stream game events carry the game type at `payload["type"]` with top-level `visibility`; helper in test reads `e["payload"]["type"]` for `kind=="game_event_emitted"`.

---

## Task 0: Branch

- [ ] **Step 1: Create the feature branch**

Run:
```bash
git checkout main && git checkout -b p2-emergent-role-projection
```
Expected: `Switched to a new branch 'p2-emergent-role-projection'`

---

## Task 1: role_projection snapshots at setup (6 seats)

**Files:**
- Create: `tests/test_emergent_role_projection.py`
- Modify: `src/werewolf_eval/emergent_engine.py` (add `_write_role_snapshot`; call it 6× in `_run_inner` setup section after `setup_god_view`)

- [ ] **Step 1: Write the failing test**

Create `tests/test_emergent_role_projection.py`:

```python
"""Engine-level tests for emergent role_projection + mid-game god snapshots.

Pure offline (no socket, no key). Drives EmergentGameEngine with a
RuntimeEventWriter into a temp dir and inspects snapshots/ + events.jsonl.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.provider_contract import FAKE_PROVIDER_SOURCE_LABEL
from werewolf_eval.runtime_events import RuntimeEventWriter, read_events_jsonl

_PLAYER_IDS = ["p1", "p2", "p3", "p4", "p5", "p6"]


def _run(out_dir: Path, *, script=None, max_requests=80, max_day_rounds=3, game_id="rp"):
    writer = RuntimeEventWriter(run_id=game_id, out_dir=out_dir)
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=game_id),
        agents=build_emergent_fake_agents(script or build_villager_win_script()),
        seed=0,
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        budget=EmergentBudget(max_requests=max_requests, max_day_rounds=max_day_rounds),
        runtime_events=writer,
    )
    outcome = engine.run()
    return outcome, writer


def _load_snaps(out_dir: Path) -> dict[str, dict]:
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in (out_dir / "snapshots").glob("*.json")
    }


class RoleProjectionSnapshotTests(unittest.TestCase):
    def test_setup_writes_exactly_six_role_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)
            role_views = {n: s for n, s in snaps.items() if n.startswith("role_view_")}
            self.assertEqual(
                sorted(role_views), [f"role_view_{p}" for p in _PLAYER_IDS]
            )
            for name, snap in role_views.items():
                self.assertEqual(snap["snapshot_type"], "role_projection", name)

    def test_role_view_count_does_not_grow_with_rounds(self) -> None:
        # A 2-round game still has exactly 6 role_view_* (setup-only, not per-round).
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)  # villager_win runs 2 rounds
            snaps = _load_snaps(out)
            role_views = [n for n in snaps if n.startswith("role_view_")]
            self.assertEqual(len(role_views), 6)

    def test_role_view_visibility_internal_via_snapshot_written_event(self) -> None:
        # visibility is NOT in the snapshot JSON; assert it on the snapshot_written event.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            events = read_events_jsonl(out / "events.jsonl")
            written = {
                e["payload"]["snapshot_name"]: e
                for e in events
                if e["kind"] == "snapshot_written" and isinstance(e.get("payload"), dict)
            }
            for pid in _PLAYER_IDS:
                ev = written.get(f"role_view_{pid}")
                self.assertIsNotNone(ev, f"no snapshot_written for role_view_{pid}")
                self.assertEqual(ev["visibility"], "internal")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_emergent_role_projection.RoleProjectionSnapshotTests -v`
Expected: FAIL — `role_view_*` snapshots do not exist yet (assertion on sorted role_views list is empty / mismatch).

- [ ] **Step 3: Add `_write_role_snapshot` helper**

In `src/werewolf_eval/emergent_engine.py`, add the import near the existing runtime_events import (currently `from werewolf_eval.runtime_events import build_god_snapshot`):

```python
from werewolf_eval.runtime_events import build_god_snapshot, build_role_projection_snapshot
```

Then add this method right after `_write_god_snapshot` (after emergent_engine.py:341):

```python
    def _write_role_snapshot(self, player_id: str) -> None:
        """Write one role_projection snapshot for `player_id` (P2 seam fix): gives
        observer /projection a trusted role snapshot so role:pN unlocks that seat's
        own private seer/witch/wolf-team events. role/team/known_roles are static in
        the 6-player board, so one snapshot at setup is sufficient. No-op without a
        runtime writer. The builder hides werewolf roles from non-wolf observers."""
        if self._runtime_events is None:
            return
        obs = self._build_obs(player_id, "setup", 0)
        snap = build_role_projection_snapshot(run_id=self._game_id, observation=obs)
        self._runtime_events.write_snapshot(
            f"role_view_{player_id}", snap,
            visibility="internal", round=0, phase="setup", actor=player_id,
        )
```

- [ ] **Step 4: Call it for all 6 seats at setup**

In `_run_inner`, find the setup lines (emergent_engine.py:770-771):

```python
        self._emit("setup", 0, "role_assignment", "system", "none", "public", "Roles assigned to all 6 players.")
        self._write_god_snapshot("setup_god_view", 0, "setup")
```

Add immediately after them:

```python
        for _pid in self._seat_order:
            self._write_role_snapshot(_pid)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_emergent_role_projection.RoleProjectionSnapshotTests -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_emergent_role_projection.py
git commit -m "feat(emergent): write per-seat role_projection snapshots at setup"
```

---

## Task 2: mid-game god snapshots (night + day settlement points)

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py` (two `_write_god_snapshot` calls in the `_run_inner` round loop)
- Test: `tests/test_emergent_role_projection.py` (add `MidGameGodSnapshotTests`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emergent_role_projection.py`:

```python
class MidGameGodSnapshotTests(unittest.TestCase):
    def test_per_round_night_and_day_god_snapshots_exist(self) -> None:
        # villager_win: r1 night (kill p5, witch saves) -> nobody dies -> day r1
        # (p1 eliminated); r2 night (kill p3, witch poisons p2) -> villagers win
        # in the night (no r2 day).
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)
            self.assertIn("setup_god_view", snaps)
            self.assertIn("god_view_r1_night", snaps)
            self.assertIn("god_view_r1_day", snaps)
            self.assertIn("god_view_r2_night", snaps)
            self.assertIn("final_god_view", snaps)
            # r2 ended in the night -> no r2 day snapshot
            self.assertNotIn("god_view_r2_day", snaps)

    def test_night_ending_game_still_writes_night_then_final(self) -> None:
        # Same villager_win game ends in r2 night; both the r2 night settlement
        # snapshot and the final snapshot must be present (early-termination rule).
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            outcome, _ = _run(out)
            self.assertTrue(outcome.completed)
            snaps = _load_snaps(out)
            self.assertIn("god_view_r2_night", snaps)
            self.assertIn("final_god_view", snaps)

    def test_god_snapshots_carry_correct_alive_players(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)
            # nobody dies r1 night (witch saved p5)
            self.assertEqual(set(snaps["god_view_r1_night"]["alive_players"]),
                             {"p1", "p2", "p3", "p4", "p5", "p6"})
            # p1 eliminated by vote r1 day
            self.assertNotIn("p1", snaps["god_view_r1_day"]["alive_players"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_emergent_role_projection.MidGameGodSnapshotTests -v`
Expected: FAIL — `god_view_r1_night` / `god_view_r1_day` not in snaps (`KeyError`/`assertIn` failure).

- [ ] **Step 3: Add the night settlement god snapshot**

In `_run_inner`, the night section currently ends (emergent_engine.py:791-798):

```python
            for pid in deaths:
                self._alive.discard(pid)
                self._emit("night", rnd, "player_died", "system", pid, "all", f"{pid} died during the night.")

            winner = self._win_check()
            if winner is not None:
                end_condition = "all_werewolves_eliminated" if winner == "villager" else "werewolves_reach_parity"
                break
```

Insert the snapshot write between the death loop and the win check so it captures post-death alive state on EVERY path (including a night-ending game, which then breaks to the `final_god_view` write):

```python
            for pid in deaths:
                self._alive.discard(pid)
                self._emit("night", rnd, "player_died", "system", pid, "all", f"{pid} died during the night.")

            self._write_god_snapshot(f"god_view_r{rnd}_night", rnd, "night")

            winner = self._win_check()
            if winner is not None:
                end_condition = "all_werewolves_eliminated" if winner == "villager" else "werewolves_reach_parity"
                break
```

- [ ] **Step 4: Add the day settlement god snapshot**

The day elimination section currently ends (emergent_engine.py:809-819):

```python
            eliminated = self._resolve_votes(rnd)
            if eliminated is not None:
                self._alive.discard(eliminated)
                role = self._players_by_id[eliminated].role
                self._emit("day", rnd, "player_eliminated", "system", eliminated, "all", f"{eliminated} eliminated by vote.")
                self._emit("day", rnd, "role_revealed", "system", eliminated, "all", f"{eliminated} revealed as {role}.")

            winner = self._win_check()
            if winner is not None:
                end_condition = "all_werewolves_eliminated" if winner == "villager" else "werewolves_reach_parity"
                break
```

Insert the day snapshot after the elimination block (and the `if eliminated` block), before the win check, so it captures post-elimination alive state on every path:

```python
            eliminated = self._resolve_votes(rnd)
            if eliminated is not None:
                self._alive.discard(eliminated)
                role = self._players_by_id[eliminated].role
                self._emit("day", rnd, "player_eliminated", "system", eliminated, "all", f"{eliminated} eliminated by vote.")
                self._emit("day", rnd, "role_revealed", "system", eliminated, "all", f"{eliminated} revealed as {role}.")

            self._write_god_snapshot(f"god_view_r{rnd}_day", rnd, "day")

            winner = self._win_check()
            if winner is not None:
                end_condition = "all_werewolves_eliminated" if winner == "villager" else "werewolves_reach_parity"
                break
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_emergent_role_projection.MidGameGodSnapshotTests -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_emergent_role_projection.py
git commit -m "feat(emergent): write per-round night/day god snapshots for mid-game alive"
```

---

## Task 3: prefix/subset run_dir proves mid-game alive shrink

**Files:**
- Test: `tests/test_emergent_role_projection.py` (add `AliveShrinkTests`)

Rationale: a full run's latest god snapshot is always `final_god_view`, so `build_seat_role_index` can't show a mid-game point on a complete dir. Copy a controlled subset of god snapshots into a fresh dir and assert the seat index's `alive` reflects exactly that subset's latest god snapshot.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emergent_role_projection.py`:

```python
import shutil

from werewolf_eval.observer_visibility import build_seat_role_index


class AliveShrinkTests(unittest.TestCase):
    def _subset_dir(self, src: Path, dst: Path, keep_snaps: list[str]) -> Path:
        # Build a run_dir containing ONLY the named snapshots (so latest-god logic
        # is pinned to a chosen mid-game point), plus the role_view_* (harmless).
        (dst / "snapshots").mkdir(parents=True)
        for name in keep_snaps:
            shutil.copy(src / "snapshots" / f"{name}.json", dst / "snapshots" / f"{name}.json")
        for rv in (src / "snapshots").glob("role_view_*.json"):
            shutil.copy(rv, dst / "snapshots" / rv.name)
        return dst

    def test_alive_shrinks_after_night_then_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full = root / "full"
            _run(full)

            # (a) up to r1 night only: nobody died (witch saved p5) -> all alive
            night_dir = self._subset_dir(full, root / "night", ["setup_god_view", "god_view_r1_night"])
            idx_night = build_seat_role_index(night_dir)
            self.assertTrue(all(idx_night[p]["alive"] for p in _PLAYER_IDS))

            # (b) add r1 day: p1 eliminated by vote -> p1 now dead, others alive
            day_dir = self._subset_dir(
                full, root / "day", ["setup_god_view", "god_view_r1_night", "god_view_r1_day"]
            )
            idx_day = build_seat_role_index(day_dir)
            self.assertFalse(idx_day["p1"]["alive"])
            self.assertTrue(idx_day["p3"]["alive"])
            self.assertEqual(idx_day["p1"]["alive_source"], "god_snapshot")
```

- [ ] **Step 2: Run the test to verify it fails — then passes**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_emergent_role_projection.AliveShrinkTests -v`
Expected: PASS immediately (Task 2 already produces the needed god snapshots; this task only adds the proving test). If it does NOT pass, the snapshots from Task 2 are wrong — fix Task 2, do not weaken this test.

> Note: this is a test-only task, so there is no separate red phase to engineer — the behavior under test was implemented in Task 2. The test's value is locking acceptance ④ via the prefix/subset method the spec mandates.

- [ ] **Step 3: Commit**

```bash
git add tests/test_emergent_role_projection.py
git commit -m "test(emergent): prove mid-game alive shrink via prefix/subset run_dir"
```

---

## Task 4: leak-safety scan (role_view content + secret scan)

**Files:**
- Test: `tests/test_emergent_role_projection.py` (add `LeakSafetyTests`)

- [ ] **Step 1: Write the test**

Append to `tests/test_emergent_role_projection.py`:

```python
_SECRET_MARKERS = ["sk-", "authorization", "bearer", "api_key", "http://", "https://"]


class LeakSafetyTests(unittest.TestCase):
    def test_non_wolf_role_view_hides_werewolf_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)
            # p3 (seer) is a non-wolf: its projected_known_roles must not name any werewolf.
            p3 = snaps["role_view_p3"]
            self.assertEqual(p3["role"], "seer")
            self.assertNotIn("werewolf", set(p3.get("projected_known_roles", {}).values()))
            # p5 (villager) likewise.
            p5 = snaps["role_view_p5"]
            self.assertNotIn("werewolf", set(p5.get("projected_known_roles", {}).values()))

    def test_wolf_role_view_keeps_team_and_mates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)
            p1 = snaps["role_view_p1"]
            self.assertEqual(p1["role"], "werewolf")
            self.assertEqual(p1["team"], "werewolf")
            self.assertEqual(p1["projected_known_roles"].get("p2"), "werewolf")

    def test_no_secrets_or_urls_in_any_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            for path in (out / "snapshots").glob("*.json"):
                text = path.read_text(encoding="utf-8").lower()
                for marker in _SECRET_MARKERS:
                    self.assertNotIn(marker, text, f"{marker!r} in {path.name}")
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_emergent_role_projection.LeakSafetyTests -v`
Expected: PASS (3 tests).

- [ ] **Step 3: Commit**

```bash
git add tests/test_emergent_role_projection.py
git commit -m "test(emergent): role_view projection leak-safety + secret scan"
```

---

## Task 5: flip the bridge seam test (downgrade -> unlocked), keep reverse non-leak

**Files:**
- Modify: `tests/test_observer_emergent_bridge.py` — replace `test_projection_role_private_events_downgrade_to_hidden` in `BridgeVisibilityTests` with an "unlocked" assertion + reverse non-leak.

- [ ] **Step 1: Update the test (red against new engine behavior is not needed — engine already changed; this test asserts the NEW contract)**

In `tests/test_observer_emergent_bridge.py`, find the method `test_projection_role_private_events_downgrade_to_hidden` inside `class BridgeVisibilityTests` and replace the WHOLE method with the two methods below. Keep the rest of the class (setUp, `_game_types`, team:werewolf and god tests) unchanged.

```python
    def test_projection_role_private_events_now_unlocked(self) -> None:
        # With per-seat role_projection snapshots, role:pN unlocks that seat's OWN
        # private events: p3=seer, p4=witch, p1=werewolf. Assert via the reasons
        # produced by event_visible_in_projection over the seat index.
        seat_index = build_seat_role_index(self._dir)

        def _reasons(perspective: str) -> set[str]:
            return {event_visible_in_projection(e, perspective, seat_index)[1] for e in self._events}

        self.assertIn("seer_event", _reasons("role:p3"))
        self.assertIn("witch_event", _reasons("role:p4"))
        self.assertIn("werewolf_team_event", _reasons("role:p1"))

        # the unlocked private events now appear in the projection envelope too
        env_p3 = build_projection_envelope(
            run_dir=self._dir, run_id="br_vis", perspective="role:p3", events=self._events
        )
        self.assertIn("seer_check", _game_types(env_p3["events"]))

    def test_projection_villager_still_sees_no_private_events(self) -> None:
        # Reverse non-leak: p5 is a plain villager — another seat's role_projection
        # must NOT unlock seer/witch/wolf events for p5.
        seat_index = build_seat_role_index(self._dir)
        reasons = {event_visible_in_projection(e, "role:p5", seat_index)[1] for e in self._events}
        self.assertNotIn("seer_event", reasons)
        self.assertNotIn("witch_event", reasons)
        self.assertNotIn("werewolf_team_event", reasons)

        env_p5 = build_projection_envelope(
            run_dir=self._dir, run_id="br_vis", perspective="role:p5", events=self._events
        )
        self.assertEqual(_game_types(env_p5["events"]) & _PRIVATE_TYPES, set())
```

Ensure the imports at the top of `tests/test_observer_emergent_bridge.py` include `event_visible_in_projection` (already imported in this file) and `build_seat_role_index` (already imported) and `build_projection_envelope` (already imported). No import changes needed.

- [ ] **Step 2: Run the updated visibility tests**

Run: `cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest tests.test_observer_emergent_bridge.BridgeVisibilityTests -v`
Expected: PASS — including the two new methods, the unchanged team:werewolf (sees `werewolf_kill`) and god tests.

- [ ] **Step 3: Commit**

```bash
git add tests/test_observer_emergent_bridge.py
git commit -m "test(bridge): flip seam test — role private events unlocked + reverse non-leak"
```

---

## Task 6: full verification + forbidden-files diff

**Files:** none (verification only)

- [ ] **Step 1: Run the new + adjacent suites green**

Run:
```bash
cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest \
  tests.test_emergent_role_projection \
  tests.test_observer_emergent_bridge \
  tests.test_run_emergent_fake_runtime \
  tests.test_emergent_engine 2>&1 | grep -E "^(OK|FAILED|Ran)"
```
Expected: `OK`. If `test_emergent_engine` fails because it hard-codes a snapshot count/name set, update that test to reflect the new snapshots (allowlisted), re-run, commit with `test(emergent): update snapshot-count expectations`.

- [ ] **Step 2: Full suite — confirm only the known socket errors remain**

Run:
```bash
cd G:/Werewolf-agent && PYTHONPATH=src python -m unittest discover -s tests 2>/tmp/wt.txt 1>/dev/null; grep -E "^(Ran|OK|FAILED)" /tmp/wt.txt; echo "non-socket failures:"; grep -E "^(FAIL|ERROR):" /tmp/wt.txt | grep -v "test_observer_server"
```
Expected: `FAILED (errors=47, ...)` with the "non-socket failures" list EMPTY (the 47 are the pre-existing localhost-HTTP block, identical to main baseline).

- [ ] **Step 3: Confirm forbidden-files diff is empty**

Run:
```bash
cd G:/Werewolf-agent && git diff main --stat -- \
  src/werewolf_eval/observer_server.py src/werewolf_eval/observer_protocol.py \
  src/werewolf_eval/observer_visibility.py src/werewolf_eval/game_engine.py \
  src/werewolf_eval/emergent_fake_script.py src/werewolf_eval/runtime_events.py \
  src/werewolf_eval/scoring.py src/werewolf_eval/attribution.py \
  src/werewolf_eval/settlement_bundle.py src/werewolf_eval/deepseek_launcher.py \
  src/werewolf_eval/run_observer_server.py src/werewolf_eval/run_emergent_fake_runtime.py \
  'clients/qt_observer/*' docs/PROJECT_MAP.md
echo "(empty above = good)"
```
Expected: empty output.

- [ ] **Step 4: Verify the only changed source file is emergent_engine.py**

Run: `cd G:/Werewolf-agent && git diff main --name-only -- src/`
Expected: exactly `src/werewolf_eval/emergent_engine.py`.

---

## Task 7: PR + merge

**Files:** none

- [ ] **Step 1: Push (no-proxy, per env note)**

Run:
```bash
cd G:/Werewolf-agent && git -c http.proxy= -c https.proxy= push -u origin p2-emergent-role-projection
```
Expected: branch pushed.

- [ ] **Step 2: Open PR**

Run (with proxy unset env): `gh pr create --base main --head p2-emergent-role-projection --title "feat(emergent): role_projection + mid-game god snapshots (P2 seam #56 follow-up)" --body "<summary of spec + verification>"`

- [ ] **Step 3: Merge after review**

Run: `gh pr merge <n> --squash --delete-branch`, then `git checkout main && git -c http.proxy= -c https.proxy= pull --ff-only origin main`.

---

## Self-Review (completed by plan author)

**Spec coverage:**
- role_projection setup×6 → Task 1 ✓ (acceptance ①)
- mid-game night/day god snapshots → Task 2 ✓ (acceptance ⑤ file presence)
- early-termination night-then-final → Task 2 Step 3 inserts before win-check/break + `test_night_ending_game_still_writes_night_then_final` ✓ (acceptance ⑤)
- latest_god_alive shrink via prefix/subset → Task 3 ✓ (acceptance ④)
- role:p5 reverse non-leak → Task 5 `test_projection_villager_still_sees_no_private_events` ✓ (acceptance ③)
- role private unlock (p3/p4/p1) → Task 5 `test_projection_role_private_events_now_unlocked` ✓ (acceptance ②)
- team:werewolf still sees only kill → unchanged existing test in BridgeVisibilityTests ✓ (acceptance ⑥)
- god sees all / non-leak both channels → unchanged existing tests ✓ (acceptance ⑦)
- leak-safety (role_view content + secret scan) → Task 4 ✓ (§4 invariants)
- forbidden-files diff empty + only emergent_engine.py changed → Task 6 ✓ (acceptance ⑧)
- full suite green vs baseline → Task 6 ✓ (acceptance ⑨)

**Placeholder scan:** none — all test/impl code is complete and concrete.

**Type/name consistency:** `_write_role_snapshot(player_id)`, `_write_god_snapshot(name, rnd, phase)`, `build_role_projection_snapshot(run_id=, observation=)`, `write_snapshot(name, snap, visibility=, round=, phase=, actor=)`, snapshot names `role_view_{pid}` / `god_view_r{rnd}_night` / `god_view_r{rnd}_day`, helper `_game_types` + `_PRIVATE_TYPES` reused from the existing bridge test — all consistent across tasks.
