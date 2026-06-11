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
    "villager": "村民", "hunter": "猎人",
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
