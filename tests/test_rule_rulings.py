"""Pin tests for the board-rule rulings closed out from the 2026-06-12 audit.

A-2 ruling: a POISON death does NOT trigger the hunter's on-death shot; every
            other death cause (wolf kill, vote-out, being shot) still does.
A-3 ruling: the witch may self-save ONLY on the first night; a self-save on any
            later night is rejected (honest invalid_action + downgrade -> pass).

See docs/specs/board-rule-rulings.md for the authoritative ruling text.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_engine import (
    EmergentGameEngine,
    build_emergent_config,
    build_emergent_hunter_config,
)
from werewolf_eval.emergent_fake_script import (
    SPEECH_REQUEST_PHASE,
    _act,
    build_emergent_fake_agents,
    build_hunter_night_kill_script,
    build_hunter_voteout_script,
)


def _shot(target: str) -> str:
    return json.dumps(
        {"action": "hunter_shoot", "target": target, "reason_summary": "shoot",
         "decision_type": "retaliatory", "confidence": 1.0},
        ensure_ascii=False,
    )


def _witch(action: str, target: str) -> str:
    return json.dumps(
        {"action": action, "target": target, "reason_summary": "x",
         "decision_type": "inference_based", "confidence": 1.0},
        ensure_ascii=False,
    )


def _events(outcome):
    return outcome.game_log["events"]


def _run_hunter(script):
    engine = EmergentGameEngine(
        config=build_emergent_hunter_config(),
        agents=build_emergent_fake_agents(script), seed=0,
    )
    return engine.run()


def _run_default(script, game_id="ruling"):
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=game_id),
        agents=build_emergent_fake_agents(script), seed=0,
    )
    return engine.run()


# ----------------------------------------------------------------------------
# A-2 — hunter death-trigger gated by cause
# ----------------------------------------------------------------------------
class PoisonedHunterRulingTests(unittest.TestCase):
    def test_poison_death_hunter_no_shoot(self) -> None:
        """Witch poisons the hunter (p6). The hunter dies but must NOT shoot, even
        though the script offers a shot — suppression means the engine never asks."""
        s: dict[tuple, str] = {}
        s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
        s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
        s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
        s[("p4", "night", 1)] = _witch("witch_poison", "p6")   # poisons the hunter
        s[("p6", "hunter_shot", 1)] = _shot("p1")              # offered but must be suppressed
        outcome = _run_hunter(s)

        self.assertEqual(outcome.status, "completed")
        shots = [e for e in _events(outcome) if e["type"] == "hunter_shoot"]
        self.assertEqual(shots, [], "poisoned hunter must not shoot")
        # the hunter did die (by poison)
        died = [e for e in _events(outcome) if e["type"] == "player_died" and e.get("target") == "p6"]
        self.assertTrue(died, "the poisoned hunter should be dead")
        # p1 (the offered shot target) was NOT killed -> wolves reach parity, wolves win night 1
        self.assertEqual(outcome.game_log["result"]["winner"], "werewolf")
        self.assertEqual(outcome.game_log["result"]["end_round"], 1)

    def test_wolf_kill_hunter_triggers_shoot(self) -> None:
        """Non-poison death (wolf kill) still fires the hunter's shot."""
        outcome = _run_hunter(build_hunter_night_kill_script())
        self.assertEqual(outcome.status, "completed")
        shots = [e for e in _events(outcome) if e["type"] == "hunter_shoot"]
        self.assertEqual(len(shots), 1)
        self.assertEqual((shots[0]["actor"], shots[0]["target"]), ("p6", "p1"))

    def test_vote_out_hunter_triggers_shoot(self) -> None:
        """Non-poison death (vote-out) still fires the hunter's shot."""
        outcome = _run_hunter(build_hunter_voteout_script())
        self.assertEqual(outcome.status, "completed")
        shots = [e for e in _events(outcome) if e["type"] == "hunter_shoot"]
        self.assertEqual(len(shots), 1)
        self.assertEqual((shots[0]["actor"], shots[0]["target"]), ("p6", "p1"))


# ----------------------------------------------------------------------------
# A-3 — witch self-save only on the first night
# ----------------------------------------------------------------------------
class WitchSelfSaveRulingTests(unittest.TestCase):
    def test_witch_first_night_self_save_legal(self) -> None:
        """Night 1: wolves target the witch (p4); she self-saves -> legal, peaceful
        night, no invalid_action failure recorded for the save."""
        s: dict[tuple, str] = {}
        s[("p1", "night", 1)] = _act("werewolf_kill", "p4", "team_coordinated", "kill witch")
        s[("p2", "night", 1)] = _act("werewolf_kill", "p4", "team_coordinated", "kill witch")
        s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
        s[("p4", "night", 1)] = _witch("witch_save", "p4")   # self-save on the FIRST night
        for pid in ("p1", "p2", "p3", "p4", "p5", "p6"):
            s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}: speak"
        # vote out wolf p1 on day 1
        for pid in ("p2", "p3", "p4", "p5", "p6"):
            s[(pid, "day", 1)] = _act("player_vote", "p1", "inference_based", f"{pid}->p1")
        s[("p1", "day", 1)] = _act("player_vote", "p3", "inference_based", "p1->p3")
        # night 2: last wolf p2 kills p3; witch (save spent) poisons p2 -> villager win
        s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
        s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
        s[("p4", "night", 2)] = _witch("witch_poison", "p2")
        outcome = _run_default(s, "selfsave_n1")

        self.assertEqual(outcome.status, "completed")
        # the witch survived night 1 (no death event for p4 in round 1)
        n1_deaths = [e for e in _events(outcome)
                     if e["type"] == "player_died" and e["round"] == 1]
        self.assertEqual(n1_deaths, [], "first-night self-save should cancel the kill")
        # the save was accepted -> no invalid_action failure on the witch's save
        self.assertNotIn("invalid_action",
                         [f["kind"] for f in outcome.failure_audit["failures"]])
        # a witch_save event exists
        self.assertTrue([e for e in _events(outcome) if e["type"] == "witch_save"])

    def test_witch_non_first_night_self_save_rejected(self) -> None:
        """Night 1 witch passes (save unused). Night 2 wolves target the witch and she
        attempts a self-save -> REJECTED: honest invalid_action + downgrade, witch dies."""
        s: dict[tuple, str] = {}
        # night 1: wolves kill villager p5; witch passes (keeps the antidote)
        s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
        s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
        s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
        s[("p4", "night", 1)] = _witch("witch_pass", "none")
        for pid in ("p1", "p2", "p3", "p4", "p6"):
            s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}: speak"
        # vote out wolf p1 on day 1
        for pid in ("p2", "p3", "p4", "p6"):
            s[(pid, "day", 1)] = _act("player_vote", "p1", "inference_based", f"{pid}->p1")
        s[("p1", "day", 1)] = _act("player_vote", "p3", "inference_based", "p1->p3")
        # night 2: last wolf p2 kills the witch p4; witch attempts self-save -> ILLEGAL
        s[("p2", "night", 2)] = _act("werewolf_kill", "p4", "team_coordinated", "kill witch")
        s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
        s[("p4", "night", 2)] = _witch("witch_save", "p4")   # self-save on night 2 -> rejected
        # day 2: vote out the last wolf p2 -> villager win
        for pid in ("p3", "p6"):
            s[(pid, SPEECH_REQUEST_PHASE, 2)] = f"{pid}: speak r2"
        s[("p3", "day", 2)] = _act("player_vote", "p2", "inference_based", "p3->p2")
        s[("p6", "day", 2)] = _act("player_vote", "p2", "inference_based", "p6->p2")
        s[("p2", "day", 2)] = _act("player_vote", "p3", "inference_based", "p2->p3")
        outcome = _run_default(s, "selfsave_n2")

        self.assertEqual(outcome.status, "completed")
        # the late self-save was rejected -> the witch died on night 2
        n2_deaths = [e for e in _events(outcome)
                     if e["type"] == "player_died" and e["round"] == 2 and e.get("target") == "p4"]
        self.assertTrue(n2_deaths, "non-first-night self-save must NOT cancel the kill")
        # honest audit: an invalid_action failure was recorded for the illegal self-save
        invalids = [f for f in outcome.failure_audit["failures"]
                    if f["kind"] == "invalid_action" and f.get("actor") == "p4"]
        self.assertTrue(invalids, "the illegal self-save must be recorded as invalid_action")


if __name__ == "__main__":
    unittest.main()
