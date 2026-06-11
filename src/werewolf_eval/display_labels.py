"""Shared Chinese display labels for renderers (and future Qt/server consumers).

Single source of truth for role / team / event-type / phase / status labels. Before
this module render_demo.py and render_provider_replay.py each carried byte-identical
copies, so a relabel — or a NEW emitted event type — had to be fixed in two places
and silently drifted otherwise (R-12). Add a new label here once.
"""
from __future__ import annotations

ROLE_LABELS = {
    "werewolf": "狼人",
    "seer": "预言家",
    "witch": "女巫",
    "villager": "平民",
    "hunter": "猎人",  # rules_v1_1; was missing -> raw token (R-28 class)
}

TEAM_LABELS = {
    "werewolf": "狼人阵营",
    "villager": "村民阵营",
}

PHASE_LABELS = {
    "night": "夜晚",
    "day": "白天",
    "setup": "开局",
    "game_end": "终局",
}

TYPE_LABELS = {
    "role_assignment": "角色分配",
    "werewolf_kill": "狼人选刀",
    "seer_check": "预言家查验",
    "witch_save": "女巫救人",
    "witch_poison": "女巫毒人",
    "witch_pass": "女巫弃药",  # emitted by the engine; was missing -> raw token
    "player_speech": "发言",
    "player_vote": "投票",
    "player_eliminated": "玩家出局",
    "role_revealed": "身份公开",
    "player_died": "玩家死亡",
    "day_announcement": "天亮公告",  # R-28: was missing -> rendered raw English token
    "hunter_shoot": "猎人开枪",  # rules_v1_1; was missing -> raw token (R-28 class)
    "hunter_pass": "猎人弃枪",
    "game_over": "游戏结束",
}

STATUS_LABELS = {
    "consensus": "一致同意",
    "accepted_consensus": "接受共识",
    "coordinator_tie_break": "协调者裁决",
    "forced_random": "强制随机",
}
