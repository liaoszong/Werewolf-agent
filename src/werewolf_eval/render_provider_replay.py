from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


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

PHASE_LABELS = {
    "night": "夜晚",
    "day": "白天",
    "setup": "开局",
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

STATUS_LABELS = {
    "consensus": "一致同意",
    "accepted_consensus": "接受共识",
    "coordinator_tie_break": "协调者裁决",
    "forced_random": "强制随机",
}

FAILURE_KIND_LABELS = {
    "timeout": "超时",
    "parse_failure": "解析失败",
    "invalid_action": "无效行动",
    "wolf_consensus_failure": "狼人共识失败",
}


def _role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def _team_label(team: str) -> str:
    return TEAM_LABELS.get(team, team)


def _phase_label(phase: str) -> str:
    return PHASE_LABELS.get(phase, phase)


def _type_label(type_: str) -> str:
    return TYPE_LABELS.get(type_, type_)


def _status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def _failure_kind_label(kind: str) -> str:
    return FAILURE_KIND_LABELS.get(kind, kind)


def _html(value: object) -> str:
    return escape(str(value), quote=True)


def _row(cells: list[object]) -> str:
    return "<tr>" + "".join(f"<td>{_html(cell)}</td>" for cell in cells) + "</tr>"


def _head(cells: list[str]) -> str:
    return "<tr>" + "".join(f"<th>{_html(cell)}</th>" for cell in cells) + "</tr>"


def build_replay_context(
    *,
    game_log: dict[str, Any],
    decision_log: dict[str, Any] | None = None,
    consensus_log: dict[str, Any] | None = None,
    provider_trace: dict[str, Any] | None = None,
    failure_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a replay context dict from raw log dicts.

    This function does NOT load files; it operates on already-parsed dicts.
    No live API call is made during rendering.
    """
    game_id = str(game_log.get("game_id", "unknown"))
    source_label = str(game_log.get("source_label", ""))
    players_raw = game_log.get("players", [])
    events_raw = game_log.get("events", [])
    result = game_log.get("result", {})

    player_rows = []
    for p in players_raw:
        role = str(p.get("role", ""))
        team = str(p.get("team", ""))
        player_rows.append({
            "player_id": str(p.get("player_id", "")),
            "role": role,
            "role_label": _role_label(role),
            "team": team,
            "team_label": _team_label(team),
        })

    event_rows = []
    for e in events_raw:
        etype = str(e.get("type", ""))
        ephase = str(e.get("phase", ""))
        event_rows.append({
            "event_id": str(e.get("event_id", "")),
            "sequence": int(e.get("sequence", 0)),
            "round": int(e.get("round", 0)),
            "phase": ephase,
            "phase_label": _phase_label(ephase),
            "type": etype,
            "type_label": _type_label(etype),
            "actor": str(e.get("actor", "")),
            "target": str(e.get("target", "")),
            "summary": str(e.get("data", {}).get("summary", "")),
        })

    decision_rows = []
    if decision_log:
        for d in decision_log.get("decisions", []):
            decision_rows.append({
                "decision_id": str(d.get("decision_id", "")),
                "actor": str(d.get("actor", "")),
                "phase": str(d.get("phase", "")),
                "action": str(d.get("action", "")),
                "target": str(d.get("target", "")),
                "reason_summary": str(d.get("reason_summary", "")),
            })

    consensus_rows = []
    if consensus_log:
        for c in consensus_log.get("consensuses", []):
            final = c.get("final_decision", {})
            consensus_rows.append({
                "consensus_id": str(c.get("consensus_id", "")),
                "round": int(c.get("round", 0)),
                "participants": ", ".join(str(p) for p in c.get("participants", [])),
                "status": str(c.get("status", "")),
                "final_target": str(final.get("target", "")),
                "supporters": ", ".join(str(s) for s in final.get("supporters", [])),
                "dissenters": ", ".join(str(s) for s in final.get("dissenters", [])),
            })

    trace_info: dict[str, Any] = {"has_trace": False}
    provider_requests: list[dict[str, Any]] = []
    provider_responses: list[dict[str, Any]] = []
    if provider_trace:
        reqs = provider_trace.get("requests", [])
        resps = provider_trace.get("responses", [])
        fails = provider_trace.get("failures", [])
        total_tokens = 0
        for r in resps:
            usage = r.get("token_usage", {})
            total_tokens += int(usage.get("total_tokens", 0))
        trace_info = {
            "has_trace": True,
            "provider_name": str(provider_trace.get("provider_name", "")),
            "request_count": len(reqs),
            "response_count": len(resps),
            "failure_count": len(fails),
            "total_tokens": total_tokens,
        }
        for req in reqs:
            obs = req.get("observation", {})
            provider_requests.append({
                "request_id": str(req.get("request_id", "")),
                "actor": str(req.get("actor", "")),
                "phase": str(req.get("phase", "")),
                "round": int(req.get("round", 0)),
                "observation_summary": json.dumps(obs, ensure_ascii=False),
            })
        for resp in resps:
            usage = resp.get("token_usage", {})
            provider_responses.append({
                "request_id": str(resp.get("request_id", "")),
                "raw_content": str(resp.get("raw_content", "")),
                "latency_ms": int(resp.get("latency_ms", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
            })

    failure_rows = []
    if failure_audit:
        for f in failure_audit.get("failures", []):
            failure_rows.append({
                "round": int(f.get("round", 0)),
                "phase": str(f.get("phase", "")),
                "actor": str(f.get("actor", "")),
                "kind": str(f.get("kind", "")),
                "reason": str(f.get("reason", "")),
            })

    return {
        "source_label": source_label,
        "game": {
            "game_id": game_id,
            "winner": str(result.get("winner", "")),
            "end_round": int(result.get("end_round", 0)),
            "player_count": len(player_rows),
            "event_count": len(event_rows),
        },
        "players": player_rows,
        "events": event_rows,
        "decisions": decision_rows,
        "consensuses": consensus_rows,
        "provider_trace": trace_info,
        "provider_requests": provider_requests,
        "provider_responses": provider_responses,
        "failures": failure_rows,
        "decision_log_supplied": decision_log is not None,
        "consensus_log_supplied": consensus_log is not None,
        "failure_audit_supplied": failure_audit is not None,
    }


def render_provider_replay_html(context: dict[str, Any]) -> str:
    """Render the replay context as a single static HTML page.

    No external CSS, no JavaScript, no network resources are referenced.
    All untrusted values are escaped with html.escape.
    No live API call is made during rendering.
    """
    game = context["game"]
    source_label = context["source_label"]
    winner_label = _team_label(game["winner"]) if game["winner"] else game["winner"]

    # -- Player table --
    player_rows = "\n".join(
        _row([p["player_id"], p["role_label"], p["team_label"]])
        for p in context["players"]
    )

    # -- Event timeline --
    event_rows = "\n".join(
        _row([e["sequence"], e["round"], e["phase_label"], e["type_label"], e["actor"], e["target"], e["summary"]])
        for e in context["events"]
    )

    # -- Decision table --
    decision_section = ""
    if context["decision_log_supplied"]:
        d_rows = "\n".join(
            _row([d["decision_id"], d["actor"], _phase_label(d["phase"]), d["action"], d["target"], d["reason_summary"]])
            for d in context["decisions"]
        )
        decision_section = f"""<section><h2>决策回放</h2>
<div class="scroll"><table>
{_head(["决策 ID", "行动者", "阶段", "行动", "目标", "理由摘要"])}
{d_rows}
</table></div></section>"""

    # -- Consensus table --
    consensus_section = ""
    if context["consensus_log_supplied"]:
        c_rows = "\n".join(
            _row([c["consensus_id"], c["round"], c["participants"], _status_label(c["status"]), c["final_target"], c["supporters"], c["dissenters"]])
            for c in context["consensuses"]
        )
        consensus_section = f"""<section><h2>共识回放</h2>
<div class="scroll"><table>
{_head(["共识 ID", "轮次", "参与者", "状态", "最终目标", "支持者", "反对者"])}
{c_rows}
</table></div></section>"""

    # -- Provider trace --
    trace_section = ""
    if context["provider_trace"]["has_trace"]:
        t = context["provider_trace"]
        reqs = context.get("provider_requests", [])
        resps = context.get("provider_responses", [])
        req_rows = ""
        if reqs:
            req_rows = "\n".join(
                _row([r["request_id"], r["actor"], _phase_label(r["phase"]), str(r["round"]), r.get("observation_summary", "")])
                for r in reqs
            )
        resp_rows = ""
        if resps:
            resp_rows = "\n".join(
                _row([r["request_id"], r["raw_content"], str(r["latency_ms"]), str(r["total_tokens"])])
                for r in resps
            )
        trace_section = f"""<section><h2>Provider 调用记录</h2>
<p><strong>{_html(t['provider_name'])}</strong> — 请求: {t['request_count']}, 响应: {t['response_count']}, 失败: {t['failure_count']}, 总 Tokens: {t['total_tokens']}</p>
{f'''<h3>请求</h3><div class="scroll"><table>
{_head(["请求 ID", "行动者", "阶段", "轮次", "观察"])}
{req_rows}
</table></div>''' if req_rows else ''}
{f'''<h3>响应</h3><div class="scroll"><table>
{_head(["请求 ID", "原始内容", "延迟(ms)", "Tokens"])}
{resp_rows}
</table></div>''' if resp_rows else ''}
</section>"""

    # -- Failure audit --
    failure_section = ""
    if context["failure_audit_supplied"]:
        if context["failures"]:
            f_rows = "\n".join(
                _row([f["round"], _phase_label(f["phase"]), f["actor"], _failure_kind_label(f["kind"]), f["reason"]])
                for f in context["failures"]
            )
            failure_section = f"""<section><h2>失败审计</h2>
<div class="scroll"><table>
{_head(["轮次", "阶段", "行动者", "类型", "原因"])}
{f_rows}
</table></div></section>"""
        else:
            failure_section = """<section><h2>失败审计</h2>
<p>零次 Provider 失败</p>
</section>"""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Provider 回放 — {_html(game['game_id'])}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #172033; background: #f7f8fb; }}
    main {{ max-width: 1280px; margin: 0 auto; }}
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
  <h1>Provider 回放 — {_html(game['game_id'])}</h1>
  <p><span class="badge">来源: {_html(source_label)}</span></p>
  <p><em>渲染过程中未发起任何实时 API 调用。</em></p>

  <section class="warning"><h2>边界声明</h2><p>仅供回放/报告使用；不是实时观察器，不是排行榜，不是评分变更。</p></section>

  <section><h2>对局摘要</h2>
  <p>对局: {_html(game['game_id'])} / 胜方: {_html(winner_label)} / 结束轮次: {_html(game['end_round'])} / 玩家数: {_html(game['player_count'])} / 事件数: {_html(game['event_count'])} / 来源: {_html(source_label)}</p>
  </section>

  <section><h2>玩家列表</h2>
  <div class="scroll"><table>
  {_head(["玩家 ID", "角色", "阵营"])}
  {player_rows}
  </table></div></section>

  <section><h2>事件时间线</h2>
  <div class="scroll"><table>
  {_head(["序号", "轮次", "阶段", "类型", "行动者", "目标", "摘要"])}
  {event_rows}
  </table></div></section>

  {decision_section}

  {consensus_section}

  {trace_section}

  {failure_section}
</main>
</body>
</html>
"""


def write_provider_replay_html(
    *,
    game_log_path: str | Path,
    output_path: str | Path,
    decision_log_path: str | Path | None = None,
    consensus_log_path: str | Path | None = None,
    provider_trace_path: str | Path | None = None,
    failure_audit_path: str | Path | None = None,
) -> None:
    """Read log files from disk and write a single static provider replay HTML.

    No live API call is made during rendering. All output is self-contained.
    """
    game_log = json.loads(Path(game_log_path).read_text(encoding="utf-8"))

    decision_log = None
    if decision_log_path is not None:
        decision_log = json.loads(Path(decision_log_path).read_text(encoding="utf-8"))

    consensus_log = None
    if consensus_log_path is not None:
        consensus_log = json.loads(Path(consensus_log_path).read_text(encoding="utf-8"))

    provider_trace = None
    if provider_trace_path is not None:
        provider_trace = json.loads(Path(provider_trace_path).read_text(encoding="utf-8"))

    failure_audit = None
    if failure_audit_path is not None:
        failure_audit = json.loads(Path(failure_audit_path).read_text(encoding="utf-8"))

    context = build_replay_context(
        game_log=game_log,
        decision_log=decision_log,
        consensus_log=consensus_log,
        provider_trace=provider_trace,
        failure_audit=failure_audit,
    )
    html = render_provider_replay_html(context)
    Path(output_path).write_text(html, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for provider replay HTML generation.

    No live API call is made during rendering.
    """
    parser = argparse.ArgumentParser(description="Generate provider replay HTML report.")
    parser.add_argument("--game-log", required=True, help="Path to Game Log JSON")
    parser.add_argument("--decision-log", help="Optional path to Decision Log JSON")
    parser.add_argument("--consensus-log", help="Optional path to Consensus Log JSON")
    parser.add_argument("--provider-trace", help="Optional path to Provider Trace JSON")
    parser.add_argument("--failure-audit", help="Optional path to Failure Audit JSON")
    parser.add_argument("--html-out", required=True, help="Output HTML file path")
    args = parser.parse_args(argv)

    write_provider_replay_html(
        game_log_path=args.game_log,
        output_path=args.html_out,
        decision_log_path=args.decision_log,
        consensus_log_path=args.consensus_log,
        provider_trace_path=args.provider_trace,
        failure_audit_path=args.failure_audit,
    )

    sections = ["game"]
    if args.decision_log:
        sections.append("decisions")
    if args.consensus_log:
        sections.append("consensus")
    if args.provider_trace:
        sections.append("provider_trace")
    if args.failure_audit:
        sections.append("failure_audit")

    print(f"wrote {args.html_out}")
    print(f"replay_sections={','.join(sections)}")
    print("live_api=not_called")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
