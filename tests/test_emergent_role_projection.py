"""Engine-level tests for emergent role_projection and mid-game god snapshots.

Pure offline tests: drive EmergentGameEngine with a RuntimeEventWriter into a
temp dir, then inspect snapshots/ and events.jsonl.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.observer_visibility import build_seat_role_index
from werewolf_eval.provider_contract import FAKE_PROVIDER_SOURCE_LABEL
from werewolf_eval.runtime_events import RuntimeEventWriter, read_events_jsonl

_PLAYER_IDS = ["p1", "p2", "p3", "p4", "p5", "p6"]
_SECRET_MARKERS = ["sk-", "authorization", "bearer", "api_key", "http://", "https://"]


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
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)
            role_views = [n for n in snaps if n.startswith("role_view_")]
            self.assertEqual(len(role_views), 6)

    def test_role_view_visibility_internal_via_snapshot_written_event(self) -> None:
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


class MidGameGodSnapshotTests(unittest.TestCase):
    def test_per_round_night_and_day_god_snapshots_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)
            self.assertIn("setup_god_view", snaps)
            self.assertIn("god_view_r1_night", snaps)
            self.assertIn("god_view_r1_day", snaps)
            self.assertIn("god_view_r2_night", snaps)
            self.assertIn("final_god_view", snaps)
            self.assertNotIn("god_view_r2_day", snaps)

    def test_night_ending_game_still_writes_night_then_final(self) -> None:
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
            self.assertEqual(
                set(snaps["god_view_r1_night"]["alive_players"]),
                {"p1", "p2", "p3", "p4", "p5", "p6"},
            )
            self.assertNotIn("p1", snaps["god_view_r1_day"]["alive_players"])


class AliveShrinkTests(unittest.TestCase):
    def _subset_dir(self, src: Path, dst: Path, keep_snaps: list[str]) -> Path:
        (dst / "snapshots").mkdir(parents=True)
        for name in keep_snaps:
            shutil.copy(
                src / "snapshots" / f"{name}.json",
                dst / "snapshots" / f"{name}.json",
            )
        for rv in (src / "snapshots").glob("role_view_*.json"):
            shutil.copy(rv, dst / "snapshots" / rv.name)
        return dst

    def test_alive_shrinks_after_night_then_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full = root / "full"
            _run(full)

            night_dir = self._subset_dir(
                full, root / "night", ["setup_god_view", "god_view_r1_night"]
            )
            idx_night = build_seat_role_index(night_dir)
            self.assertTrue(all(idx_night[p]["alive"] for p in _PLAYER_IDS))

            day_dir = self._subset_dir(
                full,
                root / "day",
                ["setup_god_view", "god_view_r1_night", "god_view_r1_day"],
            )
            idx_day = build_seat_role_index(day_dir)
            self.assertFalse(idx_day["p1"]["alive"])
            self.assertTrue(idx_day["p3"]["alive"])
            self.assertEqual(idx_day["p1"]["alive_source"], "god_snapshot")


class LeakSafetyTests(unittest.TestCase):
    def test_non_wolf_role_view_hides_werewolf_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run(out)
            snaps = _load_snaps(out)

            p3 = snaps["role_view_p3"]
            self.assertEqual(p3["role"], "seer")
            self.assertNotIn("werewolf", set(p3.get("projected_known_roles", {}).values()))

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


if __name__ == "__main__":
    unittest.main()
