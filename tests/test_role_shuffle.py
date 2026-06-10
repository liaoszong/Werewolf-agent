from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.deepseek_launcher import build_multi_provider_launcher
from werewolf_eval.seat_agents import ProviderCredential


def _factory():
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


class RunnerSeatRolesTests(unittest.TestCase):
    def test_runner_accepts_seat_roles_and_engine_plays_them(self):
        sr = {"p1": "seer", "p2": "villager", "p3": "werewolf", "p4": "witch", "p5": "werewolf", "p6": "villager"}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            run_emergent_deepseek_game(game_id="g", out_dir=out, provider_factory=_factory(),
                                       model="", seat_roles=sr)
            # setup god-view is written UNCONDITIONALLY at engine init (before the main loop),
            # so it exists even if the role-mismatched script later budget-exhausts.
            god = json.loads((out / "snapshots" / "setup_god_view.json").read_text(encoding="utf-8"))
            roles = {p["player_id"]: p["role"] for p in god["players"]}
            self.assertEqual(roles["p3"], "werewolf")
            self.assertEqual(roles["p1"], "seer")


def _seat(pid, role):
    return {"player_id": pid, "provider": "deepseek", "model": "deepseek-v4-flash",
            "role": role, "team": "werewolf" if role == "werewolf" else "villager",
            "strategy": "default", "prompt": "", "temperature": None, "max_tokens": None}


class LauncherSeatRolesTests(unittest.TestCase):
    def test_launcher_passes_resolved_seat_roles_to_runner(self):
        captured: dict = {}
        def fake_runner(**kw):
            captured.update(kw)
            return 0
        seats = [_seat("p1", "seer"), _seat("p2", "villager"), _seat("p3", "werewolf"),
                 _seat("p4", "witch"), _seat("p5", "werewolf"), _seat("p6", "villager")]
        launcher = build_multi_provider_launcher(
            resolved_seats=seats, credentials={"deepseek": ProviderCredential(key="sk")},
            transport=lambda *a, **k: {"choices": [{"message": {"content": "{}"}}], "usage": {}},
            runner=fake_runner)
        with tempfile.TemporaryDirectory() as d:
            launcher("rid", Path(d))
        self.assertEqual(captured["seat_roles"],
                         {"p1": "seer", "p2": "villager", "p3": "werewolf", "p4": "witch", "p5": "werewolf", "p6": "villager"})


if __name__ == "__main__":
    unittest.main()
