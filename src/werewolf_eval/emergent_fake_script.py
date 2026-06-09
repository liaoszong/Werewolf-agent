"""Deterministic fake scripts for the emergent engine (offline tests + runner).

Mirrors `fake_provider.build_default_fake_provider_script`, but covers the
emergent flow: night actions (wolf kill / seer / witch as JSON), day speeches
(natural text keyed by the SPEECH_REQUEST_PHASE), and day votes.

Two canonical scripts: a villager win (ends night 2 via witch poison) and a
werewolf win (ends day 1 by reaching parity). Default board: p1/p2 wolves,
p3 seer, p4 witch, p5/p6 villagers.
"""

from __future__ import annotations

import json

from werewolf_eval.emergent_engine import SPEECH_REQUEST_PHASE
from werewolf_eval.fake_provider import DeterministicFakeProvider
from werewolf_eval.provider_agent import ProviderAgent


def _act(action: str, target: str, dtype: str = "inference_based", reason: str = "x") -> str:
    return json.dumps(
        {"action": action, "target": target, "reason_summary": reason, "decision_type": dtype, "confidence": 1.0},
        ensure_ascii=False,
    )


def _speech(text: str) -> str:
    return text


def build_villager_win_script() -> dict[tuple, str]:
    s: dict[tuple, str] = {}
    # ---- round 1 night ----
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "p1 kills p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "p2 kills p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "p3 checks p1")
    s[("p4", "night", 1)] = _act("witch_save", "p5", "inference_based", "p4 saves p5")
    # ---- round 1 day speeches (all 6 alive) ----
    speeches_r1 = {
        "p1": "我觉得昨晚平安夜很可疑，女巫大概率救了人。我先观望，倾向怀疑 p3 跳得太急。",
        "p2": "我同意 p1，p3 上来就指人，像在带节奏。这一轮我可能投 p3。",
        "p3": "我是预言家，昨晚验了 p1，结果是狼。证据确凿，请大家跟我投 p1。",
        "p4": "我相信 p3 的预言家身份，他的发言逻辑通顺。今天我投 p1。",
        "p5": "我昨晚差点出局，p3 的查验对我来说很关键，我站 p3，投 p1。",
        "p6": "综合来看 p3 像真预言家，p1、p2 抱团踩他更像狼。我也投 p1。",
    }
    for pid, text in speeches_r1.items():
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = _speech(text)
    # ---- round 1 day votes: p3/p4/p5/p6 -> p1 ; p1/p2 -> p3 ----
    s[("p3", "day", 1)] = _act("player_vote", "p1", "inference_based", "p3 votes p1")
    s[("p4", "day", 1)] = _act("player_vote", "p1", "inference_based", "p4 votes p1")
    s[("p5", "day", 1)] = _act("player_vote", "p1", "inference_based", "p5 votes p1")
    s[("p6", "day", 1)] = _act("player_vote", "p1", "inference_based", "p6 votes p1")
    s[("p1", "day", 1)] = _act("player_vote", "p3", "inference_based", "p1 votes p3")
    s[("p2", "day", 1)] = _act("player_vote", "p3", "inference_based", "p2 votes p3")
    # ---- round 2 night (p1 eliminated): p2 kills p3, witch poisons p2 -> villager win ----
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "p2 kills p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "p3 checks p2")
    s[("p4", "night", 2)] = _act("witch_poison", "p2", "retaliatory", "p4 poisons p2")
    return s


def build_werewolf_win_script() -> dict[tuple, str]:
    s: dict[tuple, str] = {}
    # ---- round 1 night: wolves kill villager p5, witch passes ----
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "p1 kills p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "p2 kills p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "p3 checks p1")
    s[("p4", "night", 1)] = json.dumps(
        {"action": "witch_pass", "target": "none", "reason_summary": "save it", "decision_type": "default", "confidence": 1.0},
        ensure_ascii=False,
    )
    # ---- round 1 day speeches (p1,p2,p3,p4,p6 alive; p5 dead) ----
    speeches_r1 = {
        "p1": "p5 出局很可惜。我观察下来 p6 发言飘忽，建议先查他。",
        "p2": "附议 p1，p6 一直在和稀泥，今天我投 p6。",
        "p3": "我验人结果还在确认，但 p6 的票型确实奇怪，我也偏向 p6。",
        "p4": "我手里还有药，先不表态。综合发言我倾向投 p6。",
        "p6": "你们集火我，我才是好人！我怀疑 p1 是狼，我投 p1。",
    }
    for pid, text in speeches_r1.items():
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = _speech(text)
    # ---- round 1 day votes: p1/p2/p3/p4 -> p6 (villager) ; p6 -> p1 -> parity, wolves win ----
    s[("p1", "day", 1)] = _act("player_vote", "p6", "inference_based", "p1 votes p6")
    s[("p2", "day", 1)] = _act("player_vote", "p6", "inference_based", "p2 votes p6")
    s[("p3", "day", 1)] = _act("player_vote", "p6", "inference_based", "p3 votes p6")
    s[("p4", "day", 1)] = _act("player_vote", "p6", "inference_based", "p4 votes p6")
    s[("p6", "day", 1)] = _act("player_vote", "p1", "inference_based", "p6 votes p1")
    return s


def _shot(target: str, reason: str = "hunter shoots") -> str:
    return json.dumps(
        {"action": "hunter_shoot", "target": target, "reason_summary": reason, "decision_type": "retaliatory", "confidence": 1.0},
        ensure_ascii=False,
    )


def build_hunter_night_kill_script() -> dict[tuple, str]:
    """Hunter board (p6=hunter). Night 1: wolves kill the hunter p6, witch passes; the hunter
    shoots wolf p1 on death. Day 1: villagers vote out the last wolf p2 -> villager win."""
    s: dict[tuple, str] = {}
    s[("p1", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "p1 kills p6")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p6", "team_coordinated", "p2 kills p6")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "p3 checks p1")
    s[("p4", "night", 1)] = json.dumps(
        {"action": "witch_pass", "target": "none", "reason_summary": "save it", "decision_type": "default", "confidence": 1.0},
        ensure_ascii=False)
    # hunter p6 dies -> shoots wolf p1 (distinct request phase "hunter_shot")
    s[("p6", "hunter_shot", 1)] = _shot("p1", "p6 shoots a wolf")
    for pid in ("p2", "p3", "p4", "p5"):   # alive into day 1
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}:狼队已折一只,集中票出剩下的狼。"
    s[("p3", "day", 1)] = _act("player_vote", "p2", "inference_based", "p3 votes p2")
    s[("p4", "day", 1)] = _act("player_vote", "p2", "inference_based", "p4 votes p2")
    s[("p5", "day", 1)] = _act("player_vote", "p2", "inference_based", "p5 votes p2")
    s[("p2", "day", 1)] = _act("player_vote", "p3", "inference_based", "p2 votes p3")
    return s


def build_hunter_voteout_script() -> dict[tuple, str]:
    """Hunter survives night 1 (witch saves the wolf victim p5), votes on day 1, is voted out,
    and shoots wolf p1 on death — exercising the DAY death hook + the distinct shot key
    ((p6,"hunter_shot",1) must NOT collide with p6's vote (p6,"day",1)). Ends round 2."""
    s: dict[tuple, str] = {}
    # night 1: wolves kill p5; witch saves p5 -> peaceful, all 6 alive into day 1
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "p1 kills p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "p2 kills p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "p3 checks p1")
    s[("p4", "night", 1)] = _act("witch_save", "p5", "inference_based", "p4 saves p5")
    for pid in ("p1", "p2", "p3", "p4", "p5", "p6"):
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}:今天先把 p6 票出去看反应。"
    for pid in ("p1", "p2", "p3", "p4", "p5"):
        s[(pid, "day", 1)] = _act("player_vote", "p6", "inference_based", f"{pid} votes p6")
    s[("p6", "day", 1)] = _act("player_vote", "p1", "inference_based", "p6 votes p1")   # vote key
    s[("p6", "hunter_shot", 1)] = _shot("p1", "p6 shoots a wolf")                        # shot key (distinct!)
    # after day 1: p6 voted, p1 shot. alive = p2(wolf),p3,p4,p5. round 2:
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "p2 kills p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "p3 checks p2")
    s[("p4", "night", 2)] = _act("witch_poison", "p2", "retaliatory", "p4 poisons p2")
    return s


def build_emergent_fake_agents(script: dict[tuple, str]) -> dict[str, ProviderAgent]:
    """One ProviderAgent per player, each wrapping a fresh provider over the full
    script (each provider is only ever queried for its own actor keys)."""
    return {
        pid: ProviderAgent(player_id=pid, provider=DeterministicFakeProvider(dict(script)))
        for pid in ("p1", "p2", "p3", "p4", "p5", "p6")
    }
