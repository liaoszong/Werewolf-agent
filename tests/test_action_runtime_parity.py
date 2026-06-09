"""Phase-2 parity harness: the NEW JointSettler must reproduce the OLD engine's
night-death computation, driven off the engine's own game-log (old engine =
parity oracle, spec §7.2). Semantic parity is the hard gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1
from werewolf_eval.action_runtime.settler import JointSettler, NightIntents
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
    build_werewolf_win_script,
)


def _run_engine(script):
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id="parity"),
        agents=build_emergent_fake_agents(script),
        seed=0,
    )
    return engine.run()


def _night_by_round(game_log: dict) -> dict:
    """Reconstruct per-round night intents + actual night deaths + the alive-set
    at night start, by walking the engine's emitted events in order."""
    alive = {p["player_id"] for p in game_log["players"]}
    rounds: dict = {}

    def ensure(r):
        # The first night event of a round (werewolf_kill) snapshots alive BEFORE
        # this round's deaths are applied — i.e. the alive-set at night start.
        if r not in rounds:
            rounds[r] = {"victim": None, "saved": False, "poison": None,
                         "deaths": [], "alive": set(alive)}
        return rounds[r]

    for ev in game_log["events"]:
        r = ev.get("round")
        t = ev.get("type")
        if t == "werewolf_kill":
            ensure(r)["victim"] = ev.get("target")
        elif t == "witch_save":
            ensure(r)["saved"] = True
        elif t == "witch_poison":
            ensure(r)["poison"] = ev.get("target")
        elif t == "player_died":
            ensure(r)["deaths"].append(ev.get("target"))
            alive.discard(ev.get("target"))
        elif t == "player_eliminated":
            alive.discard(ev.get("target"))
    return rounds


class NightParityTests(unittest.TestCase):
    def _check(self, script) -> None:
        outcome = _run_engine(script)
        self.assertEqual(outcome.status, "completed")
        settler = JointSettler(rules_v1())
        rounds = _night_by_round(outcome.game_log)
        self.assertTrue(rounds, "expected at least one night round")
        for r, d in rounds.items():
            state = RuntimeState(alive=frozenset(d["alive"]), roles={})
            got = settler.resolve_night(
                NightIntents(wolf_victim=d["victim"], saved=d["saved"], poison_target=d["poison"]),
                state,
            )
            self.assertEqual(
                got.deaths, d["deaths"],
                f"round {r}: settler {got.deaths} != engine {d['deaths']}",
            )

    def test_villager_win_night_parity(self) -> None:
        self._check(build_villager_win_script())

    def test_werewolf_win_night_parity(self) -> None:
        self._check(build_werewolf_win_script())


if __name__ == "__main__":
    unittest.main()
