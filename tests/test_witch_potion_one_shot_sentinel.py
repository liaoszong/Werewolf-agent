# tests/test_witch_potion_one_shot_sentinel.py
"""Witch one-shot potion sentinels (antidote + poison). GREEN now (inline _resolve_witch);
go RED the day a future witch swap (②b) routes the witch through validate_in_state without a
RuntimeState one-shot ledger. The witch is DEFERRED in ②a, so these stay green throughout.

Each script: witch uses a potion in R1 (consumes it), then ILLEGALLY tries the same potion in
R2 -> the 2nd use MUST be refused (only the R1 event lands; an invalid_action failure is logged).
Both reach wolf-parity by R2 night, so the game terminates with no R3 script needed.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    _act, build_emergent_fake_agents, SPEECH_REQUEST_PHASE,
)


def build_witch_second_save_script():
    """女巫 R1 救 p5(消耗解药),R2 又非法地对 p3 再用一次解药 -> 第二次救必须被拒。"""
    s = {}
    # R1 night: wolves kill p5; seer checks p1; witch SAVES p5 (consumes antidote -> no death)
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("witch_save", "p5", "inference_based", "save p5")
    # R1 day: all 6 alive -> vote out villager p6 (thin the good side; keep BOTH wolves for R2 parity)
    for pid in ("p1", "p2", "p3", "p4", "p5", "p6"):
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}: vote p6"
    for pid in ("p1", "p2", "p3", "p4", "p5"):
        s[(pid, "day", 1)] = _act("player_vote", "p6", "inference_based", f"{pid}->p6")
    s[("p6", "day", 1)] = _act("player_vote", "p1", "inference_based", "p6->p1")
    # after R1 day: alive p1,p2(wolves),p3(seer),p4(witch),p5(villager). R2 night:
    s[("p1", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 2)] = _act("witch_save", "p3", "inference_based", "2nd save (ILLEGAL)")
    # R2 night kills p3 (save refused) -> alive p1,p2(wolves),p4,p5 -> 2v2 parity -> wolf win
    return s


def build_witch_second_poison_script():
    """女巫 R1 毒杀狼 p1(消耗毒药),R2 又非法地对 p2 再用一次毒药 -> 第二次毒必须被拒。"""
    s = {}
    # R1 night: wolves kill p5; seer checks p1; witch POISONS wolf p1 (consumes poison)
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("witch_poison", "p1", "retaliatory", "poison wolf p1")
    # deaths R1 night: p5 (wolf victim) + p1 (poison). alive p2,p3,p4,p6 (1 wolf)
    # R1 day: vote out villager p6 (KEEP wolf p2 for R2): p2/p3/p4 -> p6 ; p6 -> p2
    for pid in ("p2", "p3", "p4", "p6"):
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}: vote p6"
    for pid in ("p2", "p3", "p4"):
        s[(pid, "day", 1)] = _act("player_vote", "p6", "inference_based", f"{pid}->p6")
    s[("p6", "day", 1)] = _act("player_vote", "p2", "inference_based", "p6->p2")
    # after R1 day: alive p2(wolf),p3(seer),p4(witch). R2 night:
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("witch_poison", "p2", "retaliatory", "2nd poison (ILLEGAL)")
    return s


class WitchAntidoteOneShotSentinel(unittest.TestCase):
    def test_second_save_refused_antidote_is_one_shot(self):
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="witch_save_one_shot"),
            agents=build_emergent_fake_agents(build_witch_second_save_script()),
            seed=0,
        )
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        saves = [e for e in events if e["type"] == "witch_save"]
        self.assertEqual([e["target"] for e in saves], ["p5"])  # only the R1 save landed
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])


class WitchPoisonOneShotSentinel(unittest.TestCase):
    def test_second_poison_refused_potion_is_one_shot(self):
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="witch_poison_one_shot"),
            agents=build_emergent_fake_agents(build_witch_second_poison_script()),
            seed=0,
        )
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        poisons = [e for e in events if e["type"] == "witch_poison"]
        self.assertEqual([e["target"] for e in poisons], ["p1"])  # only the R1 poison landed
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])


if __name__ == "__main__":
    unittest.main()
