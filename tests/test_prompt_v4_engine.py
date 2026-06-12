"""Engine-level prompt_v4 wiring + spec §5 canaries: the witch night
observation gains the coordination suffix EXACTLY when board-has-guard AND
victim present AND antidote unused; otherwise byte-identical to prompt_v3."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
)
from werewolf_eval.prompt_v4 import WITCH_COORD_GUIDANCE

_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}


class _RecordingProvider:
    """Wraps the witch's fake provider and captures the ProviderRequest so the
    rendered observation_text can be asserted byte-exactly."""

    def __init__(self, inner):
        self._inner = inner
        self.requests = []
        self.model = getattr(inner, "model", None)

    def respond(self, request):
        self.requests.append(request)
        return self._inner.respond(request)


def _witch_obs_text(prompt_version, seat_roles=None, victim="p5", save_used=False):
    agents = build_emergent_fake_agents(build_villager_win_script())
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id="v4wire", seat_roles=seat_roles),
        agents=agents,
        seed=0,
        prompt_version=prompt_version,
        scaffold_agent=(agents["p4"] if prompt_version in ("prompt_v3", "prompt_v4") else None),
    )
    rec = _RecordingProvider(engine._agents["p4"].provider)
    engine._agents["p4"] = SimpleNamespace(provider=rec)
    engine._emit("setup", 0, "role_assignment", "system", "none", "public", "setup")
    engine._resolve_witch(rnd=1, victim=victim, save_used=save_used, poison_used=False)
    return rec.requests[0].observation_text


class PromptV4EngineWiringTest(unittest.TestCase):
    def test_guard_board_victim_unused_injects(self):
        v4 = _witch_obs_text("prompt_v4", _GUARD_SEATS)
        v3 = _witch_obs_text("prompt_v3", _GUARD_SEATS)
        self.assertEqual(v4, v3 + "\n" + WITCH_COORD_GUIDANCE)

    def test_canary1_standard_board_byte_identical_to_v3(self):
        # spec §5 canary 1: non-guard board → v4 witch night observation == v3
        self.assertEqual(_witch_obs_text("prompt_v4"), _witch_obs_text("prompt_v3"))

    def test_canary2_guard_board_no_victim_byte_identical_to_v3(self):
        # spec §5 canary 2: guard board but victim is None → identical to v3
        self.assertEqual(_witch_obs_text("prompt_v4", _GUARD_SEATS, victim=None),
                         _witch_obs_text("prompt_v3", _GUARD_SEATS, victim=None))

    def test_guard_board_antidote_spent_byte_identical_to_v3(self):
        # spec §5 third identity: antidote already used → identical to v3
        self.assertEqual(_witch_obs_text("prompt_v4", _GUARD_SEATS, save_used=True),
                         _witch_obs_text("prompt_v3", _GUARD_SEATS, save_used=True))


if __name__ == "__main__":
    unittest.main()
