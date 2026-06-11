# tests/test_guard_sentinels.py
"""Guard engine sentinels (L4 arm): block / 奶穿 / no-consecutive / self-protect.
Boards WITHOUT a witch where possible (the witch acts every night she is alive;
omitting her from seat_roles removes that turn from the script entirely)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # fake_scribe helper

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    _act, build_emergent_fake_agents, SPEECH_REQUEST_PHASE,
)

# 无女巫板:2狼 + 预言家 + 守卫 + 2民(脚本免去女巫每夜回合)
SEATS_NO_WITCH = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                  "p4": "guard", "p5": "villager", "p6": "villager"}
# 奶穿板:2狼 + 预言家 + 女巫 + 守卫 + 1民
SEATS_WITH_WITCH = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                    "p4": "witch", "p5": "guard", "p6": "villager"}


def _speeches(s, rnd, pids=("p1", "p2", "p3", "p4", "p5", "p6")):
    for pid in pids:
        s[(pid, SPEECH_REQUEST_PHASE, rnd)] = f"{pid}: speech r{rnd}"


def _votes(s, rnd, mapping):
    for pid, tgt in mapping.items():
        s[(pid, "day", rnd)] = _act("player_vote", tgt, "inference_based", f"{pid}->{tgt}")


def build_guard_blocks_script():
    """R1 守卫守 p6,狼刀 p6 -> 平安夜;R1 票出 p1;R2 守 p5(换目标),狼刀 p6 落地;R2 票出 p2 -> 村胜。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p6": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("guard_protect", "p5", "inference_based", "protect p5")
    _speeches(s, 2)
    _votes(s, 2, {"p3": "p2", "p4": "p2", "p5": "p2", "p2": "p3"})
    return s


def build_milk_pierce_script():
    """R1 狼刀 p6 + 守卫守 p6 + 女巫救 p6 -> 奶穿:p6 死;R1 票出 p1;
    R2 狼刀 p3 被守卫(守 p3)挡下 + 女巫毒 p2 -> 狼全灭,村胜。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("witch_save", "p6", "inference_based", "save p6")
    s[("p5", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("witch_poison", "p2", "retaliatory", "poison p2")
    s[("p5", "night", 2)] = _act("guard_protect", "p3", "inference_based", "protect p3")
    return s


def build_consecutive_repeat_script():
    """R1 守 p6 合法;R2 又守 p6 -> 非法,须 invalid_action + 确定性兜底(目标≠p6)。
    R1 狼刀 p5(落地),R1 票出 p1;R2 狼刀 p3;R2 票出 p2 -> 终局。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p6": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("guard_protect", "p6", "inference_based", "ILLEGAL repeat p6")
    _speeches(s, 2)
    _votes(s, 2, {"p3": "p2", "p4": "p2", "p6": "p2", "p2": "p4"})
    return s


def build_self_protect_script():
    """R1 狼刀守卫 p4,守卫自守 -> 平安夜;R1 票出 p1;R2 狼刀 p3 落地(守卫换守 p6);R2 票出 p2。"""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p4", "team_coordinated", "kill p4")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p4", "team_coordinated", "kill p4")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("guard_protect", "p4", "inference_based", "self-protect")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p6": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 2)
    _votes(s, 2, {"p4": "p2", "p5": "p2", "p6": "p2", "p2": "p4"})
    return s


def _run(game_id, seats, script, seed=0):
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=game_id, seat_roles=seats),
        agents=build_emergent_fake_agents(script),
        seed=seed,
    )
    return engine.run()


class GuardBlocksKillSentinel(unittest.TestCase):
    def test_guard_block_yields_peaceful_night(self):
        outcome = _run("guard_block", SEATS_NO_WITCH, build_guard_blocks_script())
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        r1_deaths = [e for e in events if e["type"] == "player_died" and e["round"] == 1]
        self.assertEqual(r1_deaths, [])
        self.assertTrue(any("A peaceful night" in e["data"]["summary"]
                            for e in events if e["type"] == "day_announcement" and e["round"] == 1))
        protects = [e for e in events if e["type"] == "guard_protect"]
        self.assertEqual([e["target"] for e in protects], ["p6", "p5"])
        self.assertTrue(all(e["visibility"] == "guard" for e in protects))
        # R2 守卫不在位 -> 刀落地
        self.assertTrue(any(e["type"] == "player_died" and e["target"] == "p6" and e["round"] == 2
                            for e in events))


class MilkPierceSentinel(unittest.TestCase):
    def test_guard_plus_save_same_target_dies(self):
        outcome = _run("guard_milk_pierce", SEATS_WITH_WITCH, build_milk_pierce_script())
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        self.assertTrue(any(e["type"] == "player_died" and e["target"] == "p6" and e["round"] == 1
                            for e in events))  # I8b:同守同救 -> 死
        # R2:守 p3 挡刀(p3 无夜间死亡),毒不被守挡(p2 死)
        self.assertFalse(any(e["type"] == "player_died" and e["target"] == "p3" for e in events))
        self.assertTrue(any(e["type"] == "player_died" and e["target"] == "p2" for e in events))
        self.assertEqual(outcome.game_log["result"]["winner"], "villager")


class ConsecutiveRepeatSentinel(unittest.TestCase):
    def test_repeat_protect_rejected_and_falls_back(self):
        outcome = _run("guard_consecutive", SEATS_NO_WITCH, build_consecutive_repeat_script())
        self.assertEqual(outcome.status, "completed")
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])
        protects = [e for e in outcome.game_log["events"] if e["type"] == "guard_protect"]
        self.assertEqual(len(protects), 2)
        self.assertEqual(protects[0]["target"], "p6")
        self.assertNotEqual(protects[1]["target"], "p6")  # 兜底必不连守


class BoardRulesVersionSelectionSentinel(unittest.TestCase):
    """The engine's rules version is BOARD-derived: a blanket v1_2 bump would
    rewrite the frozen v2/v3 chains' rules-card version line (model-visible bytes)
    and the manifest stamp for guardless games."""

    def test_guardless_board_keeps_v1_1(self):
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="rules_sel_std"),
            agents=build_emergent_fake_agents({}), seed=0)
        self.assertEqual(engine.rules_version, "rules_v1_1")

    def test_guard_board_selects_v1_2(self):
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="rules_sel_guard", seat_roles=SEATS_NO_WITCH),
            agents=build_emergent_fake_agents({}), seed=0)
        self.assertEqual(engine.rules_version, "rules_v1_2")


class SelfProtectSentinel(unittest.TestCase):
    def test_self_protect_blocks_own_kill(self):
        outcome = _run("guard_self", SEATS_NO_WITCH, build_self_protect_script())
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        r1_deaths = [e for e in events if e["type"] == "player_died" and e["round"] == 1]
        self.assertEqual(r1_deaths, [])
        self.assertIn(("p4", "p4"), [(e["actor"], e["target"]) for e in events
                                     if e["type"] == "guard_protect" and e["round"] == 1])


class TwoGuardBoardRejectedSentinel(unittest.TestCase):
    def test_two_guards_fail_loud_at_construction(self):
        # R-30 extension: _run_guard uses guards[0]; a 2-guard board would silently
        # deactivate the second guard -> must be rejected at construction.
        seats = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                 "p4": "guard", "p5": "guard", "p6": "villager"}
        with self.assertRaises(ValueError):
            EmergentGameEngine(
                config=build_emergent_config(game_id="two_guards", seat_roles=seats),
                agents=build_emergent_fake_agents({}), seed=0)


class GuardBoardV3SmokeSentinel(unittest.TestCase):
    """Full-stack v3 smoke on the guard board — the EXACT l4_guard arm combo
    (prompt_v3 + scribe scaffold + rules_v1_2 + guard board): board-conditional
    rules card, guard night request and scaffold path all compose."""

    def test_v3_guard_board_completes_with_guard_aware_card(self):
        from fake_scribe import _FakeScribeProvider
        from werewolf_eval.emergent_engine import EmergentBudget
        from werewolf_eval.provider_agent import ProviderAgent
        agents = build_emergent_fake_agents(build_guard_blocks_script())
        scribe = ProviderAgent("scribe", _FakeScribeProvider())
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="v3_guard_smoke", seat_roles=SEATS_NO_WITCH),
            agents=agents, seed=0,
            budget=EmergentBudget(max_requests=80, max_day_rounds=3),
            prompt_version="prompt_v3", scaffold_agent=scribe,
        )
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(engine.rules_version, "rules_v1_2")
        self.assertIn("守卫×1", engine._board_card)
        self.assertIn("同守同救", engine._board_card)
        self.assertNotIn("没有守卫或守夜人", engine._board_card)
        protects = [e for e in outcome.game_log["events"] if e["type"] == "guard_protect"]
        self.assertEqual([e["target"] for e in protects], ["p6", "p5"])
        self.assertGreaterEqual(len(scribe.provider.requests), 1)  # scribe 跑了


if __name__ == "__main__":
    unittest.main()
