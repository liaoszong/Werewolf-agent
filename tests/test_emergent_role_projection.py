"""Engine-level tests for emergent role_projection and mid-game god snapshots.

Pure offline tests: drive EmergentGameEngine with a RuntimeEventWriter into a
temp dir, then inspect snapshots/ and events.jsonl.
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


if __name__ == "__main__":
    unittest.main()
