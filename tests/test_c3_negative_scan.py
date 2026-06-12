# tests/test_c3_negative_scan.py
"""C3-2: 守卫板局负向扫描 — 所有非女巫座位 prompt 不得包含 victim/协调提示。

在 prompt_v4 guard board 局中，只有女巫的夜行动观察应包含 WITCH_COORD_GUIDANCE
和 augment_witch_observation 注入的 victim 信息（仅当晚有 victim 时）。
其他所有座位（狼人、预言家、守卫、村民）的 prompt 必须零包含。

C3-7 (artifact_gap) 和 C3-12 (check_run) 在其他文件中。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # fake_scribe

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config, EmergentBudget
from werewolf_eval.emergent_fake_script import (
    _act, build_emergent_fake_agents, SPEECH_REQUEST_PHASE,
)
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.prompt_v4 import WITCH_COORD_GUIDANCE
from fake_scribe import _FakeScribeProvider

# 守卫+女巫板:2狼 + 预言家 + 女巫 + 守卫 + 1民
SEATS_GUARD_WITCH = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                     "p4": "witch", "p5": "guard", "p6": "villager"}
# 无女巫板(守卫可自守/挡刀)
SEATS_NO_WITCH = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                  "p4": "guard", "p5": "villager", "p6": "villager"}

ROLES = {
    "p1": "werewolf", "p2": "werewolf", "p3": "seer",
    "p4": "witch", "p5": "guard", "p6": "villager",
}
NON_WITCH_SEATS = ("p1", "p2", "p3", "p5", "p6")


def _speeches(s, rnd, pids=("p1", "p2", "p3", "p4", "p5", "p6")):
    for pid in pids:
        s[(pid, SPEECH_REQUEST_PHASE, rnd)] = f"{pid}: speech r{rnd}"


def _votes(s, rnd, mapping):
    for pid, tgt in mapping.items():
        s[(pid, "day", rnd)] = _act("player_vote", tgt, "inference_based", f"{pid}->{tgt}")


def build_milk_pierce_script():
    """R1:狼刀p6 + 守卫守p6 + 女巫救p6 -> 奶穿;
    R1:票出p1; R2:狼刀p3 + 守卫守p3(挡刀) + 女巫毒p2 -> 村胜."""
    s = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("witch_save", "p6", "inference_based", "save p6")
    s[("p5", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
    _speeches(s, 1)
    _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p6": "p1", "p1": "p3"})
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("witch_poison", "p2", "retaliatory", "poison p2")
    s[("p5", "night", 2)] = _act("guard_protect", "p3", "inference_based", "protect p3")
    _speeches(s, 2)
    _votes(s, 2, {"p3": "p2", "p4": "p2", "p5": "p2", "p2": "p4"})
    return s


class _RecordingProvider:
    """Wraps a provider and captures every ProviderRequest for later inspection."""

    def __init__(self, inner):
        self._inner = inner
        self.requests = []
        self.model = getattr(inner, "model", None)

    def respond(self, request):
        self.requests.append(request)
        return self._inner.respond(request)


def _run_and_capture(script, seats, game_id="c3_scan"):
    """Run a guard board game with prompt_v4, capturing all provider requests."""
    agents = build_emergent_fake_agents(script)
    recs = {}
    for pid in agents:
        recs[pid] = _RecordingProvider(agents[pid].provider)
        agents[pid] = SimpleNamespace(provider=recs[pid])
    scribe = ProviderAgent("scribe", _FakeScribeProvider())
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id=game_id, seat_roles=seats),
        agents=agents, seed=0, prompt_version="prompt_v4",
        budget=EmergentBudget(max_requests=80, max_day_rounds=3),
        scaffold_agent=scribe,
    )
    outcome = engine.run()
    return outcome, recs


class NegativeScanCoordGuidanceTest(unittest.TestCase):
    """C3-2: 守卫板局扫描所有非女巫座位 prompt,不得包含协调提示(victim/coord)。"""

    def test_non_witch_prompts_exclude_coord_guidance(self):
        """所有非女巫座位的observation_text不得包含WITCH_COORD_GUIDANCE。"""
        outcome, recs = _run_and_capture(
            build_milk_pierce_script(), SEATS_GUARD_WITCH, "c3_2_coord",
        )
        self.assertEqual(outcome.status, "completed")
        for pid in NON_WITCH_SEATS:
            rec = recs.get(pid)
            if not rec:
                continue  # seat may not have been called if eliminated
            for req in rec.requests:
                text = req.observation_text
                if WITCH_COORD_GUIDANCE in text:
                    self.fail(
                        f"Non-witch seat {pid}({ROLES[pid]}) prompt contains "
                        f"WITCH_COORD_GUIDANCE: ...{text[-200:]}"
                    )

    def test_non_witch_prompts_exclude_victim_text(self):
        """所有非女巫座位的observation_text不得包含victim augmentation文本。"""
        outcome, recs = _run_and_capture(
            build_milk_pierce_script(), SEATS_GUARD_WITCH, "c3_2_victim",
        )
        self.assertEqual(outcome.status, "completed")
        # augment_witch_observation 注入的文本: "今晚 {victim} 被狼人袭击"
        victim_marker = "被狼人袭击"
        for pid in NON_WITCH_SEATS:
            rec = recs.get(pid)
            if not rec:
                continue
            for req in rec.requests:
                text = req.observation_text
                if victim_marker in text:
                    self.fail(
                        f"Non-witch seat {pid}({ROLES[pid]}) prompt contains "
                        f"victim text '{victim_marker}': ...{text[-200:]}"
                    )

    def test_guard_board_standard_also_clean(self):
        """无女巫 guard board 同样零泄漏(守卫无 witch_obs_suffix 注入点)。"""
        script = {}
        script[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
        script[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
        script[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
        script[("p4", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
        _speeches(script, 1)
        _votes(script, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p6": "p1", "p1": "p3"})

        outcome, recs = _run_and_capture(script, SEATS_NO_WITCH, "c3_2_std")
        self.assertEqual(outcome.status, "completed")
        for pid, rec in recs.items():
            for req in rec.requests:
                text = req.observation_text
                self.assertNotIn(WITCH_COORD_GUIDANCE, text,
                                 f"Seat {pid} in no-witch guard board has coord guidance")
                self.assertNotIn("被狼人袭击", text,
                                 f"Seat {pid} in no-witch guard board has victim text")


class NegativeScanVictimNightTest(unittest.TestCase):
    """C3-2b: victim 存在时女巫自身获得注入,其他座位仍零包含。"""

    def test_witch_gets_victim_others_dont(self):
        """R1 victim=p6 时,女巫 prompt 含 victim 文本,其他座位零包含。"""
        # 夜1有victim的简化剧本
        s = {}
        s[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
        s[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "kill p6")
        s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
        s[("p4", "night", 1)] = _act("witch_save", "p6", "inference_based", "save p6")
        s[("p5", "night", 1)] = _act("guard_protect", "p6", "inference_based", "protect p6")
        _speeches(s, 1)
        _votes(s, 1, {"p2": "p1", "p3": "p1", "p4": "p1", "p5": "p1", "p6": "p1", "p1": "p3"})

        outcome, recs = _run_and_capture(s, SEATS_GUARD_WITCH, "c3_2b_victim")
        self.assertEqual(outcome.status, "completed")

        # 女巫至少有一条请求含 victim 文本
        witch_rec = recs.get("p4")
        self.assertIsNotNone(witch_rec)
        witch_has_victim = any(
            "被狼人袭击" in req.observation_text for req in witch_rec.requests
        )
        self.assertTrue(witch_has_victim, "Witch should see victim text in her prompt")

        # 非女巫座位零包含
        for pid in NON_WITCH_SEATS:
            rec = recs.get(pid)
            if not rec:
                continue
            for req in rec.requests:
                text = req.observation_text
                if "被狼人袭击" in text:
                    self.fail(f"Non-witch {pid} has victim text: ...{text[-200:]}")
                if WITCH_COORD_GUIDANCE in text:
                    self.fail(f"Non-witch {pid} has coord guidance: ...{text[-200:]}")


if __name__ == "__main__":
    unittest.main()
