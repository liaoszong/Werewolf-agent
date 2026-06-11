"""prompt_v2 (SYS-B1 Layer-1 context repair): data-driven board rules card +
structured observation renderer. PURE functions over (ruleset, seat_roles) and
(AgentObservation, events_by_id) — no engine import (the engine imports US), no
side effects. The v1 chain (render_observation_text / build_*_system_prompt /
compose_system) is byte-locked by tests/golden_prompts/prompt_v1 and is NOT
touched by this module."""
from __future__ import annotations

from collections import Counter
from typing import Any

from werewolf_eval.action_runtime.ruleset import BoardRuleset

ROLE_NAMES_ZH = {
    "werewolf": "狼人", "seer": "预言家", "witch": "女巫",
    "villager": "村民", "hunter": "猎人", "guard": "守卫",
}
TEAM_NAMES_ZH = {"werewolf": "狼人阵营", "villager": "好人阵营"}
ABILITY_DESCRIPTIONS = {
    "werewolf_kill": "夜间与狼队友共同袭击一名玩家",
    "seer_check": "夜间查验一名玩家的真实身份",
    "witch_save": "用解药救下当晚被袭击的玩家(整局一次)",
    "witch_poison": "用毒药毒杀一名玩家(整局一次)",
    "witch_pass": "选择不用药",
    "player_vote": "白天投票放逐一名玩家",
    "hunter_shoot": "出局时开枪带走一名存活玩家",
    "hunter_pass": "出局时选择不开枪",
    "guard_protect": "夜间守护一名玩家,使其免受当晚狼人袭击(可守自己,不可连续两晚守同一人,守护结果不会获得反馈)",
}


def build_board_rules_card(ruleset: BoardRuleset, seat_roles: dict[str, str]) -> str:
    """Render THIS board's rules card from data (never hardcode the composition:
    hunter boards / shuffled boards must come out right automatically)."""
    counts = Counter(seat_roles.values())
    comp = "、".join(
        f"{ROLE_NAMES_ZH.get(r, r)}×{n}" for r, n in sorted(counts.items())
    )
    lines = [
        "【本局规则卡】",
        f"规则版本:{ruleset.rules_version}。本局 {sum(counts.values())} 名玩家,身份构成:{comp}。",
        "各身份能力:",
    ]
    for role_def in ruleset.roles:
        if counts.get(role_def.role, 0) == 0:
            continue  # data-driven: only roles actually ON this board
        abilities = ";".join(
            ABILITY_DESCRIPTIONS.get(a, a) for a in role_def.ability_ids
        )
        lines.append(
            f"- {ROLE_NAMES_ZH.get(role_def.role, role_def.role)}"
            f"({TEAM_NAMES_ZH.get(role_def.team, role_def.team)}):{abilities}"
        )
    lines.append(
        "胜负规则:所有狼人出局→好人阵营胜;狼人数量达到或超过其余存活玩家数→狼人阵营胜。"
    )
    lines.append(
        "本局不存在的机制:没有警长竞选、没有警徽流、没有警上警下之分、没有守卫或守夜人。"
        "上面能力表就是本局的全部机制,不要据不存在的机制推理,也不要在发言中讨论它们。"
    )
    lines.append(
        "重要:这是纯文字推理游戏,不存在表情、眼神、语气、肢体动作等任何视觉或听觉信息;"
        "不得以此类\"观察\"作为推理依据。"
    )
    return "\n".join(lines)


_PUBLIC_FACT_TYPES = (
    "player_died", "player_eliminated", "role_revealed", "day_announcement",
    "hunter_shoot", "hunter_pass",
)


def render_observation_text_v2(obs: Any, events_by_id: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    """Structured, ROLE-SAFE v2 observation. SAME hard invariant as v1
    (emergent_engine.render_observation_text): renders ONLY events whose ids
    appear in obs.public_event_ids ∪ obs.private_event_ids. Returns
    (text, source_event_ids); the engine wraps it into RenderedObservation and
    keeps calling assert_prompt_entitled on the ids."""
    public_ids = list(obs.public_event_ids)
    public_set = set(public_ids)
    ordered: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for ref in public_ids + list(obs.private_event_ids):
        if ref in seen:
            continue
        seen.add(ref)
        ev = events_by_id.get(ref)
        if ev is not None:
            ordered.append((ref, ev))
    ordered.sort(key=lambda kv: kv[1].get("sequence", 0))

    source_event_ids: list[str] = []
    private_lines: list[str] = []
    fact_lines: list[str] = []
    other_lines: list[str] = []
    speech_lines: list[str] = []
    votes_by_round: dict[Any, list[str]] = {}
    for ref, ev in ordered:
        summary = (ev.get("data") or {}).get("summary", "")
        if not summary:
            continue
        source_event_ids.append(ref)
        etype = ev.get("type", "")
        rnd = ev.get("round")
        ph = ev.get("phase")
        if ref not in public_set:
            private_lines.append(f"- (r{rnd} {ph}) {summary}")
        elif etype == "player_speech":
            # speeches are always day-phase; the speaker label is the payload here
            speech_lines.append(f"- (r{rnd}) {ev.get('actor')}: {summary}")
        elif etype == "player_vote":
            votes_by_round.setdefault(rnd, []).append(f"{ev.get('actor')}→{ev.get('target')}")
        elif etype in _PUBLIC_FACT_TYPES:
            # keep the v1-style phase tag: "died in r1 night" vs "eliminated in r1 day"
            # must stay directly readable
            fact_lines.append(f"- (r{rnd} {ph}) {summary}")
        else:
            other_lines.append(f"- (r{rnd} {ph}) {summary}")

    lines = ["【你的私有信息】", f"你是 {obs.player_id}(身份:{obs.role},阵营:{obs.team})。"]
    known_others = {pid: role for pid, role in obs.known_roles.items() if pid != obs.player_id}
    if known_others:
        lines.append("你已知的身份:" + ", ".join(f"{pid}={role}" for pid, role in sorted(known_others.items())) + "。")
    if private_lines:
        lines.append("你的私有事件(仅你/你的阵营可见):")
        lines.extend(private_lines)
    lines.append("【公开状态】")
    lines.append(f"当前:第 {obs.round} 轮 {obs.phase} 阶段。存活玩家:{', '.join(obs.alive_players)}。")
    if fact_lines:
        lines.append("公开事实(死亡/出局/翻牌):")
        lines.extend(fact_lines)
    if other_lines:
        lines.append("其他公开事件:")
        lines.extend(other_lines)
    if speech_lines:
        lines.append("【发言记录】(带说话人,按顺序)")
        lines.extend(speech_lines)
    if votes_by_round:
        lines.append("【投票记录】")
        for rnd in sorted(votes_by_round, key=lambda x: (x is None, x)):
            lines.append(f"- 第{rnd}轮:" + ", ".join(votes_by_round[rnd]))
    return "\n".join(lines), source_event_ids
