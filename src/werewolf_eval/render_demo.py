from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

from werewolf_eval.attribution import attribute_game, attribution_to_dict
from werewolf_eval.consensus_log import load_consensus_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.game_log import GameLog, load_game_log
from werewolf_eval.log_bundle import LogBundleValidationResult, validate_log_bundle
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)
from werewolf_eval.semantic_labels import load_semantic_label_log

# Display labels live in one shared module (R-12) so a relabel / new event type lands
# once across all renderers instead of drifting.
from werewolf_eval.display_labels import PHASE_LABELS, ROLE_LABELS, TEAM_LABELS, TYPE_LABELS


def _html(value: object) -> str:
    return escape(str(value), quote=True)


def _role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def _team_label(team: str) -> str:
    return TEAM_LABELS.get(team, team)


def build_demo_context(game: GameLog, score_log: Any, metrics: Any, attribution: Any, game_source_label: str = "[deterministic]", bundle_result: LogBundleValidationResult | None = None) -> dict[str, Any]:
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
            "phase": PHASE_LABELS.get(event.phase, event.phase),
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
    decision_quality_total = sum(record["decision_quality_score"] for record in score_payload["records"])
    decision_log_enabled = score_payload["phase"] in ("Phase 2A-D2", "Phase 2B-S5")
    semantic_labels_enabled = score_payload["phase"] == "Phase 2B-S5"
    is_g1a_scripted = "[scripted deterministic output]" in score_payload.get("source_label", "")

    games_played = 1
    single_game_outcome_total = (
        sum(score_summary["player_outcome_scores"].values())
        + sum(score_summary["team_outcome_scores"].values())
    )
    avg_outcome_score = single_game_outcome_total / games_played
    top_attribution = attribution_payload["top_attribution"]

    avg_decision_quality_score = decision_quality_total / max(len(score_payload["records"]), 1)
    if is_g1a_scripted:
        source_label = "[scripted deterministic output]"
    elif semantic_labels_enabled:
        source_label = "[deterministic][semantic-labels]"
    else:
        source_label = game_source_label

    leaderboard = [
        {
            "agent_id": f"{game.game_id}-runtime",
            "model": "scripted deterministic runner" if is_g1a_scripted else "deterministic mock agent" if game_source_label == "[deterministic mock agent output]" else "deterministic pipeline",
            "games_played": games_played,
            "win_rate": 1.0 if game.result.winner == "villager" else 0.0,
            "avg_outcome_score": avg_outcome_score,
            "avg_decision_quality_score": avg_decision_quality_score,
            "avg_rule_integrity_score": 0.0,
            "top_attribution": top_attribution["turn_point_id"],
            "source_label": source_label,
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

    bundle_enabled = bundle_result is not None
    bundle_team_links = bundle_result.team_consensus_links if bundle_result else 0

    return {
        "bundle": {
            "enabled": bundle_enabled,
            "team_consensus_links": bundle_team_links,
        },
        "game": {
            "game_id": game.game_id,
            "players": len(game.players),
            "events": len(game.events),
            "winner": game.result.winner,
            "winner_label": _team_label(game.result.winner),
            "end_round": game.result.end_round,
            "end_condition": game.result.end_condition,
            "source_label": game_source_label,
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
            "decision_log_enabled": decision_log_enabled,
            "semantic_labels_enabled": semantic_labels_enabled,
            "decision_quality_total": decision_quality_total,
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


# ---------------------------------------------------------------------------
# Task 4: HTML renderer and CLI writer
# ---------------------------------------------------------------------------


def _row(cells: list[object]) -> str:
    return "<tr>" + "".join(f"<td>{_html(cell)}</td>" for cell in cells) + "</tr>"


def _head(cells: list[str]) -> str:
    return "<tr>" + "".join(f"<th>{_html(cell)}</th>" for cell in cells) + "</tr>"


def render_html(context: dict[str, Any]) -> str:
    game = context["game"]
    timeline_rows = "\n".join(
        _row([event["sequence"], event["round"], event["phase"], event["type_label"], event["actor"], event["target"], event["summary"]])
        for event in context["timeline"]
    )
    player_rows = "\n".join(
        _row([player["player_id"], player["role_label"], player["team_label"], player["final_state"]])
        for player in context["players"]
    )
    vote_rows = "\n".join(
        _row([vote["round"], vote["event_id"], vote["actor"], vote["target"], vote["summary"]])
        for vote in context["votes"]
    )
    leaderboard_rows = "\n".join(
        _row([
            row["agent_id"], row["model"], row["games_played"], row["win_rate"],
            row["avg_outcome_score"], row["avg_decision_quality_score"],
            row["avg_rule_integrity_score"], row["top_attribution"], row["source_label"],
        ])
        for row in context["leaderboard"]
    )
    attribution_rows = "\n".join(
        _row([item["turn_point_id"], item["rule_id"], item["round"], item["subject"], item["impact_score"], item["description_template"]])
        for item in context["attribution"]["turn_point_rows"]
    )

    bundle = context.get("bundle", {})
    bundle_enabled = bundle.get("enabled", False)

    is_g1a = "[scripted deterministic output]" in context["score"].get("source_label", "")
    is_mock_agent = "[deterministic mock agent output]" in context["game"].get("source_label", "")

    if is_g1a:
        boundary_copy = "This demo is generated from scripted deterministic Game Log / Decision Log / Consensus Log outputs. It is not Agent runtime output, not live AI Agent gameplay, not provider integration, not a Web live observer, and not human-vs-AI UI."
        decision_copy = "G1a scripted deterministic fresh-log runner: decision_quality_score from scripted decisions; no provider call, no live AI reasoning."
        title = "Werewolf-agent G1a Scripted Deterministic Fresh-Log Runner"
    elif context["score"]["semantic_labels_enabled"]:
        boundary_copy = "This is not real AI Agent gameplay, not live AI labeling, and not a real multi-model Leaderboard. S5 saved semantic labels are connected to deterministic scoring; no provider call is made during rendering."
        decision_copy = f"decision_quality_score: S5 saved semantic labels enabled; decision_quality_total={context['score']['decision_quality_total']}."
        title = "Werewolf-agent Phase 2 Runtime Demo"
    elif context["score"]["decision_log_enabled"]:
        if is_mock_agent:
            boundary_copy = "This is not real AI Agent gameplay, not AI semantic labeling, and not a real multi-model Leaderboard. Consensus Log is generated from deterministic mock-agent wolf team proposals. Decision Log is connected to scoring via D2 deterministic Step 1-2 (visibility check + decision_id traceability), but decision_quality_score remains 0 (positive scoring waits for S5 AI semantic judgment)."
        else:
            boundary_copy = "This is not real AI Agent gameplay, not real Consensus Log collection, not AI semantic labeling, and not a real multi-model Leaderboard. Decision Log is connected to scoring via D2 deterministic Step 1-2 (visibility check + decision_id traceability), but decision_quality_score remains 0 (positive scoring waits for S5 AI semantic judgment)."
        decision_copy = "decision_quality_score: D2 visibility check + decision_id traceability complete; positive scoring still 0 (waiting for S5)."
        title = "Werewolf-agent Phase 2 Runtime Demo"
    else:
        boundary_copy = "This is not real AI Agent gameplay, not real Decision Log / Consensus Log collection, and not a real multi-model Leaderboard. No Decision Log supplied; decision_quality_score fixed at 0."
        decision_copy = "decision_quality_score: no Decision Log supplied; fixed at 0."
        title = "Werewolf-agent Phase 2 Runtime Demo"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html(title)}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #172033; background: #f7f8fb; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    section {{ background: white; border: 1px solid #dde3ee; border-radius: 14px; padding: 18px; margin: 18px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e5e9f2; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f4f9; }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 999px; background: #eef2ff; margin-right: 6px; font-size: 12px; }}
    .scroll {{ overflow-x: auto; }}
    .warning {{ background: #fff7ed; border-color: #fed7aa; }}
  </style>
</head>
<body>
<main>
  <h1>{_html(title)}</h1>
  <p><span class="badge">运行时生成</span><span class="badge">[deterministic]</span><span class="badge">{_html(context["game"]["source_label"])}</span> {" "}<span class="badge">Bundle validation: {"enabled" if bundle_enabled else "disabled"}</span>{" "}{f'<span class="badge">team_consensus_links={bundle["team_consensus_links"]}</span>' if bundle_enabled else ""}This page is generated from the E1/E2/E3 runtime pipeline.</p>
  <section class="warning"><h2>边界声明</h2><p>{_html(boundary_copy)}</p></section>
  <section><h2>对局摘要</h2><p>Game: {_html(game["game_id"])} / Winner: {_html(game["winner_label"])} / Players: {_html(game["players"])} / Events: {_html(game["events"])} / Source: {_html(game["source_label"])}</p></section>
  <section><h2>玩家状态</h2><div class="scroll"><table>{_head(["玩家", "角色", "阵营", "终局状态"])}{player_rows}</table></div></section>
  <section><h2>时间线</h2><div class="scroll"><table>{_head(["序号", "轮次", "阶段", "类型", "行动者", "目标", "摘要"])}{timeline_rows}</table></div></section>
  <section><h2>投票表</h2><div class="scroll"><table>{_head(["轮次", "事件", "投票者", "目标", "摘要"])}{vote_rows}</table></div></section>
  <section><h2>确定性指标</h2><p>Score records: {_html(context["score"]["records"])} {_html(context["score"]["source_label"])}。{_html(decision_copy)}</p></section>
  <section><h2>规则归因</h2><p>{_html(context["attribution"]["description"])} {_html(context["attribution"]["source_label"])}</p><div class="scroll"><table>{_head(["转折点", "规则", "轮次", "主体", "影响分", "描述"])}{attribution_rows}</table></div></section>
  <section><h2>Leaderboard</h2><div class="scroll"><table>{_head(["Agent", "Model", "Games", "Win rate", "Outcome", "Decision", "Integrity", "Top attribution", "Source"])}{leaderboard_rows}</table></div></section>
</main>
</body>
</html>
"""


def write_demo_html(game_log_path: str | Path, output_path: str | Path, decision_log_path: str | Path | None = None, semantic_label_path: str | Path | None = None, *, consensus_log_path: str | Path | None = None, failure_audit_path: str | Path | None = None) -> None:
    raw = json.loads(Path(game_log_path).read_text(encoding="utf-8"))
    game_source_label = str(raw.get("source_label", "[deterministic]"))
    game = load_game_log(game_log_path)
    decision_log = load_decision_log(decision_log_path, game) if decision_log_path else None
    if semantic_label_path and decision_log is None:
        raise ValueError("semantic_label_path requires decision_log_path")
    semantic_label_log = load_semantic_label_log(semantic_label_path, decision_log) if semantic_label_path else None

    consensus_log = load_consensus_log(consensus_log_path, game) if consensus_log_path else None
    failure_audit = load_failure_audit(failure_audit_path, game) if failure_audit_path else None
    bundle_result = None
    if decision_log or consensus_log or failure_audit:
        bundle_result = validate_log_bundle(
            game,
            decision_log=decision_log,
            consensus_log=consensus_log,
            failure_audit=failure_audit,
        )

    score_log = score_game(game, decision_log=decision_log, semantic_label_log=semantic_label_log)
    metrics = summarize_metrics(game, score_log)
    attribution = attribute_game(game, score_log, metrics)
    context = build_demo_context(game, score_log, metrics, attribution, game_source_label=game_source_label, bundle_result=bundle_result)
    Path(output_path).write_text(render_html(context), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Werewolf-agent Phase 2 runtime demo HTML.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--decision-log", help="Optional path to Decision Log JSON for D2 deterministic decision-quality scoring")
    parser.add_argument("--semantic-labels", help="Optional saved S5 Semantic Label Log JSON. Requires --decision-log.")
    parser.add_argument("--consensus-log", help="Optional path to Consensus Log JSON for bundle validation")
    parser.add_argument("--failure-audit", help="Optional path to Failure Audit JSON for bundle validation")
    parser.add_argument("--html-out", required=True, help="Output HTML file path")
    args = parser.parse_args()

    write_demo_html(args.path, args.html_out, args.decision_log, args.semantic_labels, consensus_log_path=args.consensus_log, failure_audit_path=args.failure_audit)
    print(f"wrote {args.html_out}")
    bundle_supplied = bool(args.consensus_log or args.failure_audit)
    print(f"bundle_validation={'enabled' if bundle_supplied else 'disabled'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
