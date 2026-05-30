from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
from typing import Any

from werewolf_eval.attribution import attribute_game, attribution_to_dict
from werewolf_eval.game_log import GameLog, load_game_log
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)

ROLE_LABELS = {
    "werewolf": "狼人",
    "seer": "预言家",
    "witch": "女巫",
    "villager": "平民",
}

TEAM_LABELS = {
    "werewolf": "狼人阵营",
    "villager": "村民阵营",
}

TYPE_LABELS = {
    "role_assignment": "角色分配",
    "werewolf_kill": "狼人选刀",
    "seer_check": "预言家查验",
    "witch_save": "女巫救人",
    "witch_poison": "女巫毒人",
    "player_speech": "发言",
    "player_vote": "投票",
    "player_eliminated": "玩家出局",
    "role_revealed": "身份公开",
    "player_died": "玩家死亡",
    "game_over": "游戏结束",
}


def _html(value: object) -> str:
    return escape(str(value), quote=True)


def _role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def _team_label(team: str) -> str:
    return TEAM_LABELS.get(team, team)


def build_demo_context(game: GameLog, score_log: Any, metrics: Any, attribution: Any) -> dict[str, Any]:
    score_payload = score_log_to_dict(score_log)
    metrics_payload = metrics_summary_to_dict(metrics)
    attribution_payload = attribution_to_dict(attribution)

    dead_players = {event.target for event in game.events if event.type in {"player_died", "player_eliminated"}}
    player_rows = [
        {
            "player_id": player.player_id,
            "role": player.role,
            "role_label": _role_label(player.role),
            "team": player.team,
            "team_label": _team_label(player.team),
            "final_state": "存活" if player.player_id not in dead_players else "出局 / 死亡",
        }
        for player in game.players
    ]

    timeline = [
        {
            "sequence": event.sequence,
            "round": event.round,
            "phase": event.phase,
            "type": event.type,
            "type_label": TYPE_LABELS.get(event.type, event.type),
            "actor": event.actor,
            "target": event.target,
            "visibility": event.visibility,
            "summary": event.data.get("summary", ""),
        }
        for event in game.events
    ]

    vote_rows = [
        {
            "round": event.round,
            "event_id": event.event_id,
            "actor": event.actor,
            "target": event.target,
            "visibility": event.visibility,
            "summary": event.data.get("summary", ""),
        }
        for event in game.events
        if event.type == "player_vote"
    ]

    score_summary = metrics_payload["score_summary"]
    games_played = 1
    single_game_outcome_total = (
        sum(score_summary["player_outcome_scores"].values())
        + sum(score_summary["team_outcome_scores"].values())
    )
    avg_outcome_score = single_game_outcome_total / games_played
    top_attribution = attribution_payload["top_attribution"]

    leaderboard = [
        {
            "agent_id": "g001-runtime",
            "model": "deterministic pipeline",
            "games_played": games_played,
            "win_rate": 1.0 if game.result.winner == "villager" else 0.0,
            "avg_outcome_score": avg_outcome_score,
            "avg_decision_quality_score": 0.0,
            "avg_rule_integrity_score": 0.0,
            "top_attribution": top_attribution["turn_point_id"],
            "source_label": "[deterministic]",
        },
        {
            "agent_id": "mock-baseline-a",
            "model": "mock",
            "games_played": 3,
            "win_rate": 0.33,
            "avg_outcome_score": 1.0,
            "avg_decision_quality_score": 0.0,
            "avg_rule_integrity_score": 0.0,
            "top_attribution": "mock",
            "source_label": "[mock]",
        },
        {
            "agent_id": "mock-baseline-b",
            "model": "mock",
            "games_played": 3,
            "win_rate": 0.67,
            "avg_outcome_score": 2.0,
            "avg_decision_quality_score": 0.0,
            "avg_rule_integrity_score": 0.0,
            "top_attribution": "mock",
            "source_label": "[mock]",
        },
    ]

    return {
        "game": {
            "game_id": game.game_id,
            "players": len(game.players),
            "events": len(game.events),
            "winner": game.result.winner,
            "winner_label": _team_label(game.result.winner),
            "end_round": game.result.end_round,
            "end_condition": game.result.end_condition,
            "source_label": "[人工 gold sample]",
        },
        "players": player_rows,
        "timeline": timeline,
        "votes": vote_rows,
        "score": {
            "records": len(score_payload["records"]),
            "source_label": score_payload["source_label"],
            "boundary": score_payload["scoring_boundary"],
            "summary": score_summary,
            "result_metrics": metrics_payload["result_metrics"],
            "process_metrics": metrics_payload["process_metrics"],
        },
        "attribution": {
            "turn_points": len(attribution_payload["turn_points"]),
            "top_turn_point": top_attribution["turn_point_id"],
            "top_rule": top_attribution["rule_id"],
            "description": top_attribution["description_template"],
            "turn_point_rows": attribution_payload["turn_points"],
            "source_label": attribution_payload["source_label"],
        },
        "leaderboard": leaderboard,
    }
