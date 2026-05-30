# E4 Runtime Demo HTML Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Implement the Phase 2 runtime demo HTML exporter: reuse E1 Game Log parsing, E2 deterministic scoring, and E3 rule attribution to generate a double-clickable single-file HTML demo at `docs/demo/phase2-runtime-demo.html`.

**Architecture:** Add a focused `src/werewolf_eval/render_demo.py` module that builds a render context from the runtime pipeline and renders a static HTML string with embedded CSS and no external assets. Keep the accepted Phase 1 static demo unchanged, and create a separate Phase 2 runtime-generated demo file. Validate the exporter with standard-library `unittest` tests and HTML content checks.

**Tech Stack:** Python standard library only. Existing `unittest` test style. No package manager, no external dependency, no backend/frontend framework, no React/Vite.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before executing this plan, confirm these repository facts:

- PR #13 is merged into `main`.
- E1 parser / validator is complete:
  - `src/werewolf_eval/game_log.py`
  - `src/werewolf_eval/validate_game_log.py`
  - `tests/test_game_log.py`
- E2 deterministic scorer is complete:
  - `src/werewolf_eval/scoring.py`
  - `src/werewolf_eval/score_game.py`
  - `tests/test_scoring.py`
- E3 deterministic rule attribution is complete:
  - `src/werewolf_eval/attribution.py`
  - `src/werewolf_eval/attribute_game.py`
  - `tests/test_attribution.py`
- `docs/TASKS.md` marks E1, E2, and E3 completed, and E4 as the remaining Phase 2 candidate.
- Phase 1 demo remains at `docs/demo/phase1-gold-demo.html` and must not be overwritten.

## Research PR Decision

No Research PR is needed.

Reasoning:

- The task boundary is clear: generate a single-file deterministic runtime HTML demo.
- The input is fixed: `docs/gold-game/g001-game-log.json`.
- The runtime pipeline is already available through E1/E2/E3.
- E4 is one implementation unit.
- The output is a deterministic static HTML artifact, not a frontend app or server.
- The UX goal is already defined in `docs/TASKS.md`: a screenshot / double-clickable page that a non-technical user can understand in 3 minutes.

## Scope Decision

This PR implements only the E4 runtime demo exporter.

It creates:

- `src/werewolf_eval/render_demo.py`
- `tests/test_render_demo.py`
- `docs/demo/phase2-runtime-demo.html`

It modifies:

- `AGENTS.md`
- `README.md`
- `docs/TASKS.md`
- `.oh-my-harness/tree.md`

It does not modify:

- `docs/demo/phase1-gold-demo.html`
- `docs/EVALUATION_RUBRIC.md`
- `docs/gold-game/g001-game-log.json`
- `docs/gold-game/s2-score-log.json`
- `docs/gold-game/s2-metrics-summary.json`
- `docs/gold-game/s3-rule-attribution.json`

It does not create:

- `apps/`
- `server/`
- `web/`
- package manager files
- external dependency files

## E4 runtime demo boundary

E4 must make the runtime pipeline visible without expanding product scope.

E4 must keep:

- `docs/demo/phase1-gold-demo.html` unchanged.
- A new output file: `docs/demo/phase2-runtime-demo.html`.
- Explicit labels for `[deterministic]` and `[mock]` rows.
- Explicit caveats that this is not real AI Agent gameplay, not real Decision Log / Consensus Log collection, not a real multi-model Leaderboard, and not real `decision_quality_score`.
- `decision_quality_score` fixed at 0 in boundary copy.
- A single-file HTML output with embedded CSS and no external assets.

E4 must not:

- call AI models
- introduce JavaScript build tools
- introduce React/Vite/frontend framework
- introduce a backend server
- implement real leaderboard aggregation
- implement Agent gameplay
- modify accepted gold artifacts

---

### Task 1: Preflight E1/E2/E3 runtime chain

**Files:**

- Create: none.
- Modify: none.
- Test: existing `tests/test_game_log.py`, `tests/test_scoring.py`, `tests/test_attribution.py`.

- [ ] **Step 1: Confirm runtime files exist**

Run:

```bash
test -f src/werewolf_eval/game_log.py
test -f src/werewolf_eval/validate_game_log.py
test -f src/werewolf_eval/scoring.py
test -f src/werewolf_eval/score_game.py
test -f src/werewolf_eval/attribution.py
test -f src/werewolf_eval/attribute_game.py
test -f tests/test_game_log.py
test -f tests/test_scoring.py
test -f tests/test_attribution.py
printf 'E1/E2/E3 runtime files exist\n'
```

Expected result:

```text
E1/E2/E3 runtime files exist
```

- [ ] **Step 2: Confirm accepted JSON artifacts still parse**

Run:

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
printf 'Accepted JSON artifacts still parse\n'
```

Expected result:

```text
Accepted JSON artifacts still parse
```

- [ ] **Step 3: Confirm E1/E2/E3 commands still pass**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected output includes:

```text
validated game_id=g001
players=6
events=38
winner=villager
end_round=2
```

Expected scorer output includes:

```text
scored game_id=g001
score_records=14
winner=villager
game_length=2
wolf_team_outcome_score=2
```

Expected attribution output includes:

```text
attributed game_id=g001
turn_points=1
top_rule=attribution:F.1.critical_vote
top_turn_point=s3_g001_tp001
```

Expected test result includes:

```text
Ran 18 tests
OK
```

No commit is required for Task 1 because it only verifies the starting state.

---

### Task 2: Add render context builder

**Files:**

- Create: `src/werewolf_eval/render_demo.py`
- Modify: none.
- Test: `tests/test_render_demo.py` in Task 5.

- [ ] **Step 1: Create `src/werewolf_eval/render_demo.py` with imports and helpers**

Create this file:

```python
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
    "player_speech": "发言",
    "player_vote": "投票",
    "player_eliminated": "玩家出局",
    "role_revealed": "身份公开",
    "witch_poison": "女巫毒人",
    "player_died": "玩家死亡",
    "game_over": "游戏结束",
}


def _player_lookup(game: GameLog) -> dict[str, Any]:
    return {player.player_id: player for player in game.players}


def _html(value: object) -> str:
    return escape(str(value), quote=True)


def _role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def _team_label(team: str) -> str:
    return TEAM_LABELS.get(team, team)
```

- [ ] **Step 2: Add `build_demo_context`**

Append this code to `src/werewolf_eval/render_demo.py`:

```python
def build_demo_context(game: GameLog, score_log: Any, metrics: Any, attribution: Any) -> dict[str, Any]:
    players = _player_lookup(game)
    score_payload = score_log_to_dict(score_log)
    metrics_payload = metrics_summary_to_dict(metrics)
    attribution_payload = attribution_to_dict(attribution)

    dead_players = {event.target for event in game.events if event.type in {"player_died", "player_eliminated"}}
    player_rows = []
    for player in game.players:
        player_rows.append({
            "player_id": player.player_id,
            "role": player.role,
            "role_label": _role_label(player.role),
            "team": player.team,
            "team_label": _team_label(player.team),
            "final_state": "存活" if player.player_id not in dead_players else "出局 / 死亡",
        })

    timeline_events = []
    for event in game.events:
        timeline_events.append({
            "sequence": event.sequence,
            "round": event.round,
            "phase": event.phase,
            "type": event.type,
            "type_label": TYPE_LABELS.get(event.type, event.type),
            "actor": event.actor,
            "target": event.target,
            "visibility": event.visibility,
            "summary": event.data.get("summary", ""),
        })

    vote_rounds: dict[int, list[dict[str, str]]] = {}
    for event in game.events:
        if event.type != "player_vote":
            continue
        actor = players[event.actor]
        target = players[event.target]
        vote_rounds.setdefault(event.round, []).append({
            "event_id": event.event_id,
            "actor": event.actor,
            "actor_role": _role_label(actor.role),
            "target": event.target,
            "target_role": _role_label(target.role),
        })

    deterministic_row = {
        "agent_id": "g001-runtime",
        "model": "deterministic pipeline",
        "games_played": 1,
        "win_rate": 1.0 if game.result.winner == "villager" else 0.0,
        "avg_outcome_score": sum(score_payload["score_summary"]["player_outcome_scores"].values()) if "score_summary" in score_payload else sum(record["outcome_score"] for record in score_payload["records"]),
        "avg_decision_quality_score": 0.0,
        "avg_rule_integrity_score": 0.0,
        "top_attribution": attribution_payload["top_attribution"]["turn_point_id"],
        "source_label": "[deterministic]",
    }

    leaderboard_rows = [
        deterministic_row,
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
        "game_summary": {
            "game_id": game.game_id,
            "players": len(game.players),
            "winner": game.result.winner,
            "winner_label": _team_label(game.result.winner),
            "end_round": game.result.end_round,
            "survivors": game.result.survivors,
            "end_condition": game.result.end_condition,
        },
        "players": player_rows,
        "timeline_events": timeline_events,
        "vote_rounds": vote_rounds,
        "result_metrics": metrics_payload["result_metrics"],
        "process_metrics": metrics_payload["process_metrics"],
        "score_records": score_payload["records"],
        "score_summary": metrics_payload["score_summary"],
        "turn_points": attribution_payload["turn_points"],
        "top_attribution": attribution_payload["top_attribution"],
        "rule_evaluation_summary": attribution_payload["rule_evaluation_summary"],
        "validation_notes": attribution_payload["validation_notes"],
        "leaderboard_rows": leaderboard_rows,
        "boundary_notes": [
            "Phase 2 runtime generated deterministic demo.",
            "不代表真实 AI Agent 对局。",
            "不代表真实 Decision Log / Consensus Log 采集。",
            "不代表真实多模型 Leaderboard。",
            "decision_quality_score fixed at 0 because no real Decision Log exists.",
        ],
    }
```

- [ ] **Step 3: Run context smoke check**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics
from werewolf_eval.attribution import attribute_game
from werewolf_eval.render_demo import build_demo_context

game = load_game_log("docs/gold-game/g001-game-log.json")
score_log = score_game(game)
metrics = summarize_metrics(game, score_log)
attribution = attribute_game(game, score_log, metrics)
ctx = build_demo_context(game, score_log, metrics, attribution)

assert ctx["game_summary"]["game_id"] == "g001"
assert ctx["game_summary"]["winner"] == "villager"
assert len(ctx["score_records"]) == 14
assert len(ctx["turn_points"]) == 1
assert ctx["top_attribution"]["turn_point_id"] == "s3_g001_tp001"
assert any(row["source_label"] == "[deterministic]" for row in ctx["leaderboard_rows"])
assert any(row["source_label"] == "[mock]" for row in ctx["leaderboard_rows"])
print("demo context smoke passed")
PY
```

Expected result:

```text
demo context smoke passed
```

- [ ] **Step 4: Commit context builder**

Run:

```bash
git add src/werewolf_eval/render_demo.py
git commit -m "feat: build runtime demo context"
```

Expected result:

```text
[task/e4-runtime-demo-html ...] feat: build runtime demo context
```

The exact commit hash may differ.

---

### Task 3: Add HTML renderer and writer

**Files:**

- Modify: `src/werewolf_eval/render_demo.py`
- Test: `tests/test_render_demo.py` in Task 5.

- [ ] **Step 1: Add table helper and HTML renderer**

Append this code to `src/werewolf_eval/render_demo.py`:

```python
def _table(headers: list[str], rows: list[list[object]]) -> str:
    header_html = "".join(f"<th>{_html(header)}</th>" for header in headers)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{_html(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"


def render_demo_html(context: dict[str, Any]) -> str:
    game = context["game_summary"]
    players = context["players"]
    timeline = context["timeline_events"]
    score_records = context["score_records"]
    result_metrics = context["result_metrics"]
    score_summary = context["score_summary"]
    turn_points = context["turn_points"]
    top = context["top_attribution"]
    leaderboard = context["leaderboard_rows"]

    player_table = _table(
        ["玩家", "角色", "阵营", "最终状态"],
        [[p["player_id"], p["role_label"], p["team_label"], p["final_state"]] for p in players],
    )

    timeline_table = _table(
        ["序号", "轮次", "阶段", "类型", "行动者", "目标", "摘要"],
        [[e["sequence"], e["round"], e["phase"], e["type_label"], e["actor"], e["target"], e["summary"]] for e in timeline],
    )

    score_table = _table(
        ["event_id", "actor", "action_type", "target", "outcome", "decision", "integrity", "rules"],
        [
            [
                r["event_id"],
                r["actor"],
                r["action_type"],
                r["target"],
                r["outcome_score"],
                r["decision_quality_score"],
                r["rule_integrity_score"],
                ", ".join(r["rules_triggered"]),
            ]
            for r in score_records
        ],
    )

    attribution_table = _table(
        ["turn_point_id", "rule", "round", "subject", "impact", "evidence"],
        [
            [
                t["turn_point_id"],
                t["rule_id"],
                t["round"],
                t["subject"],
                t["impact_score"],
                ", ".join(t["evidence_event_ids"]),
            ]
            for t in turn_points
        ],
    )

    leaderboard_table = _table(
        ["agent_id", "model", "games", "win_rate", "outcome", "decision", "integrity", "top_attribution", "source"],
        [
            [
                row["agent_id"],
                row["model"],
                row["games_played"],
                row["win_rate"],
                row["avg_outcome_score"],
                row["avg_decision_quality_score"],
                row["avg_rule_integrity_score"],
                row["top_attribution"],
                row["source_label"],
            ]
            for row in leaderboard
        ],
    )

    boundary_items = "".join(f"<li>{_html(note)}</li>" for note in context["boundary_notes"])
    player_scores = score_summary["player_outcome_scores"]
    player_score_rows = [[player, score] for player, score in player_scores.items()]
    player_score_table = _table(["player", "outcome_score"], player_score_rows)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Werewolf-agent Phase 2 Runtime Demo</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#0f1117;color:#e6edf3;line-height:1.6;padding:clamp(12px,3vw,32px)}}
h1{{font-size:clamp(1.4rem,3vw,2rem);text-align:center;margin-bottom:6px}}
h2{{font-size:clamp(1rem,2.5vw,1.35rem);border-bottom:2px solid #30363d;padding-bottom:6px;margin:24px 0 12px}}
p{{margin:8px 0}}
table{{width:100%;border-collapse:collapse;font-size:.84rem;margin:8px 0;overflow-wrap:anywhere}}
th,td{{padding:6px 10px;text-align:left;border:1px solid #30363d;vertical-align:top}}
th{{background:#161b22;font-weight:600}}
tr:nth-child(even){{background:#161b2299}}
.panel{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:16px}}
.badge{{display:inline-block;font-size:.72rem;padding:1px 6px;border-radius:3px;font-weight:600;margin-right:4px;white-space:nowrap}}
.badge-deterministic{{background:#1f3a1f;color:#3fb950}}
.badge-mock{{background:#3a2f1f;color:#d29922}}
.badge-warn{{background:#3a1f1f;color:#f85149}}
.badge-runtime{{background:#1f3a4b;color:#58a6ff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px}}
.kv{{background:#0d1117;padding:8px 10px;border-radius:4px;border:1px solid #21262d}}
.kv .key{{font-size:.75rem;color:#8b949e}}
.kv .val{{font-size:1rem;font-weight:700;color:#e6edf3}}
.note{{font-size:.85rem;color:#c9d1d9;border-left:3px solid #58a6ff;padding:6px 10px;margin:8px 0;background:#0d1117}}
footer{{text-align:center;font-size:.75rem;color:#8b949e;margin-top:32px;padding-top:16px;border-top:1px solid #21262d}}
</style>
</head>
<body>
<h1>Werewolf-agent Phase 2 Runtime Demo</h1>
<p style="text-align:center;color:#8b949e">E1 Game Log parser / validator → E2 deterministic scorer → E3 rule attribution engine → E4 runtime HTML exporter</p>

<div class="panel">
<h2>Boundary Notes <span class="badge badge-runtime">Phase 2 runtime generated</span></h2>
<ul>{boundary_items}</ul>
</div>

<div class="panel">
<h2>Game Summary <span class="badge badge-deterministic">[deterministic]</span></h2>
<div class="grid">
<div class="kv"><span class="key">game_id</span><br><span class="val">{_html(game['game_id'])}</span></div>
<div class="kv"><span class="key">winner</span><br><span class="val">{_html(game['winner_label'])}</span></div>
<div class="kv"><span class="key">end_round</span><br><span class="val">{_html(game['end_round'])}</span></div>
<div class="kv"><span class="key">survivors</span><br><span class="val">{_html(', '.join(game['survivors']))}</span></div>
</div>
</div>

<div class="panel"><h2>Game Log - Players</h2>{player_table}</div>
<div class="panel"><h2>Game Log - Timeline</h2>{timeline_table}</div>
<div class="panel"><h2>Score Log <span class="badge badge-deterministic">[deterministic]</span></h2><p>score_records={len(score_records)}</p>{score_table}</div>
<div class="panel"><h2>Metrics Summary <span class="badge badge-deterministic">[deterministic]</span></h2>
<div class="grid">
<div class="kv"><span class="key">winner</span><br><span class="val">{_html(result_metrics['winner'])}</span></div>
<div class="kv"><span class="key">game_length</span><br><span class="val">{_html(result_metrics['game_length'])}</span></div>
<div class="kv"><span class="key">villager_win_efficiency</span><br><span class="val">{_html(result_metrics['villager_win_efficiency'])}</span></div>
<div class="kv"><span class="key">werewolf_survival_rate</span><br><span class="val">{_html(result_metrics['werewolf_survival_rate'])}</span></div>
</div>
<h3>Player outcome scores</h3>{player_score_table}
</div>
<div class="panel"><h2>Rule Attribution <span class="badge badge-deterministic">[deterministic]</span></h2>
<p class="note">Top attribution: {_html(top['description_template'])} ({_html(top['turn_point_id'])})</p>
{attribution_table}
</div>
<div class="panel"><h2>Leaderboard Demo <span class="badge badge-warn">not real multi-model leaderboard</span></h2>{leaderboard_table}</div>
<footer>Generated from runtime pipeline. docs/demo/phase1-gold-demo.html remains unchanged.</footer>
</body>
</html>
"""
```

- [ ] **Step 2: Add writer function**

Append this code to `src/werewolf_eval/render_demo.py`:

```python
def write_demo_html(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    game = load_game_log(input_path)
    score_log = score_game(game)
    metrics = summarize_metrics(game, score_log)
    attribution = attribute_game(game, score_log, metrics)
    context = build_demo_context(game, score_log, metrics, attribution)
    html = render_demo_html(context)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return context
```

- [ ] **Step 3: Run HTML render smoke check**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from werewolf_eval.render_demo import write_demo_html

out = Path("/tmp/phase2-runtime-demo.html")
write_demo_html("docs/gold-game/g001-game-log.json", out)
html = out.read_text(encoding="utf-8")

required = [
    "Werewolf-agent Phase 2 Runtime Demo",
    "[deterministic]",
    "[mock]",
    "Game Log",
    "Score Log",
    "Metrics Summary",
    "Rule Attribution",
    "Leaderboard Demo",
    "E1 Game Log parser / validator",
    "E2 deterministic scorer",
    "E3 rule attribution engine",
    "Phase 2 runtime generated",
    "不代表真实 AI Agent 对局",
    "不代表真实 Decision Log / Consensus Log",
    "decision_quality_score fixed at 0",
    "s3_g001_tp001",
]
missing = [item for item in required if item not in html]
assert not missing, missing
print("demo html render smoke passed")
PY
```

Expected result:

```text
demo html render smoke passed
```

- [ ] **Step 4: Commit HTML renderer**

Run:

```bash
git add src/werewolf_eval/render_demo.py
git commit -m "feat: render runtime demo html"
```

Expected result:

```text
[task/e4-runtime-demo-html ...] feat: render runtime demo html
```

The exact commit hash may differ.

---

### Task 4: Add render demo CLI and generate artifact

**Files:**

- Modify: `src/werewolf_eval/render_demo.py`
- Create: `docs/demo/phase2-runtime-demo.html`
- Test: `tests/test_render_demo.py` in Task 5.

- [ ] **Step 1: Add CLI entrypoint to `src/werewolf_eval/render_demo.py`**

Append this code:

```python
def main() -> int:
    parser = argparse.ArgumentParser(description="Render Werewolf-agent Phase 2 runtime demo HTML.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--out", required=True, help="Output HTML path")
    args = parser.parse_args()

    context = write_demo_html(args.path, args.out)
    print(f"rendered demo game_id={context['game_summary']['game_id']}")
    print(f"output={args.out}")
    print("sections=game,timeline,score,metrics,attribution,leaderboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run CLI to generate committed artifact**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json \
  --out docs/demo/phase2-runtime-demo.html
```

Expected output:

```text
rendered demo game_id=g001
output=docs/demo/phase2-runtime-demo.html
sections=game,timeline,score,metrics,attribution,leaderboard
```

- [ ] **Step 3: Validate generated HTML content**

Run:

```bash
test -f docs/demo/phase2-runtime-demo.html
python - <<'PY'
from pathlib import Path
html = Path("docs/demo/phase2-runtime-demo.html").read_text(encoding="utf-8")
required = [
    "Werewolf-agent Phase 2 Runtime Demo",
    "g001",
    "村民阵营",
    "score_records=14",
    "s3_g001_tp001",
    "第 2 轮 2-1 处决 p1",
    "[deterministic]",
    "[mock]",
    "decision_quality_score fixed at 0",
]
missing = [item for item in required if item not in html]
assert not missing, missing
print("phase2 runtime demo html validated")
PY
```

Expected result:

```text
phase2 runtime demo html validated
```

- [ ] **Step 4: Commit CLI and generated artifact**

Run:

```bash
git add src/werewolf_eval/render_demo.py docs/demo/phase2-runtime-demo.html
git commit -m "feat: add phase2 runtime demo artifact"
```

Expected result:

```text
[task/e4-runtime-demo-html ...] feat: add phase2 runtime demo artifact
```

The exact commit hash may differ.

---

### Task 5: Add render demo tests

**Files:**

- Create: `tests/test_render_demo.py`
- Test: `tests/test_render_demo.py`.

- [ ] **Step 1: Create `tests/test_render_demo.py`**

Create this file:

```python
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.attribution import attribute_game
from werewolf_eval.game_log import load_game_log
from werewolf_eval.render_demo import build_demo_context, render_demo_html, write_demo_html
from werewolf_eval.scoring import score_game, summarize_metrics


class RuntimeDemoRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.attribution = attribute_game(self.game, self.score_log, self.metrics)
        self.context = build_demo_context(self.game, self.score_log, self.metrics, self.attribution)

    def test_build_demo_context_contains_e1_e2_e3_outputs(self) -> None:
        self.assertEqual(self.context["game_summary"]["game_id"], "g001")
        self.assertEqual(len(self.context["score_records"]), 14)
        self.assertEqual(len(self.context["turn_points"]), 1)
        self.assertEqual(self.context["top_attribution"]["turn_point_id"], "s3_g001_tp001")

    def test_render_demo_html_contains_required_sections(self) -> None:
        html = render_demo_html(self.context)
        for text in ["Game Log", "Score Log", "Metrics Summary", "Rule Attribution", "Leaderboard Demo"]:
            self.assertIn(text, html)

    def test_rendered_html_preserves_boundary_labels(self) -> None:
        html = render_demo_html(self.context)
        self.assertIn("[deterministic]", html)
        self.assertIn("[mock]", html)
        self.assertIn("不代表真实 AI Agent 对局", html)
        self.assertIn("不代表真实 Decision Log / Consensus Log", html)
        self.assertIn("decision_quality_score fixed at 0", html)

    def test_rendered_html_contains_top_attribution(self) -> None:
        html = render_demo_html(self.context)
        self.assertIn("s3_g001_tp001", html)
        self.assertIn("第 2 轮 2-1 处决 p1", html)

    def test_rendered_html_has_deterministic_and_mock_leaderboard_rows(self) -> None:
        rows = self.context["leaderboard_rows"]
        self.assertTrue(any(row["source_label"] == "[deterministic]" for row in rows))
        self.assertTrue(any(row["source_label"] == "[mock]" for row in rows))

    def test_cli_output_file_is_valid_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "phase2-runtime-demo.html"
            context = write_demo_html(ROOT / "docs/gold-game/g001-game-log.json", out)
            html = out.read_text(encoding="utf-8")
            self.assertEqual(context["game_summary"]["game_id"], "g001")
            self.assertIn("<!DOCTYPE html>", html)
            self.assertIn("Werewolf-agent Phase 2 Runtime Demo", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run all tests**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result includes:

```text
Ran 24 tests
OK
```

The exact number may be higher if more tests exist, but all tests must pass.

- [ ] **Step 3: Commit render tests**

Run:

```bash
git add tests/test_render_demo.py
git commit -m "test: cover runtime demo html renderer"
```

Expected result:

```text
[task/e4-runtime-demo-html ...] test: cover runtime demo html renderer
```

The exact commit hash may differ.

---

### Task 6: Update repository docs and navigation

**Files:**

- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/TASKS.md`
- Modify: `.oh-my-harness/tree.md`
- Test: none; use text validation command.

- [ ] **Step 1: Update `AGENTS.md` command section and MAP**

In `AGENTS.md`, add this command under `## 命令`:

```text
- Runtime demo render 命令：`PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --out docs/demo/phase2-runtime-demo.html`。
```

In the MAP, add this file under `docs/demo/`:

```text
phase2-runtime-demo.html
```

In the MAP, add this file under `src/werewolf_eval/`:

```text
render_demo.py
```

In the MAP, add this file under `tests/`:

```text
test_render_demo.py
```

- [ ] **Step 2: Update `AGENTS.md` code boundary wording**

Replace:

```text
- Phase 2 运行时代码必须绑定 Implementation Plan；当前已完成 runtime entries 为 E1/E2/E3，E4 仍需独立 Implementation Plan。
```

with:

```text
- Phase 2 运行时代码必须绑定 Implementation Plan；当前已完成 runtime entries 为 E1/E2/E3/E4。
```

- [ ] **Step 3: Update `README.md` current status**

Replace the current status sentence with wording equivalent to:

```text
**Phase 1 deterministic MVP 已完成。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer、E3 rule attribution engine 和 E4 runtime demo HTML exporter；Phase 2 deterministic runtime demo 已闭环。
```

Keep this caveat unchanged:

```text
Phase 1 不代表真实 AI Agent 对局、真实 Decision Log / Consensus Log 采集、真实多模型 Leaderboard 或真实 `decision_quality_score` 可用。
```

- [ ] **Step 4: Update `docs/TASKS.md` E4 status**

Change E4 status to:

```text
- 状态：`completed`（Phase 2 E4 runtime demo HTML exporter；runtime-generated 单文件演示页面已实现）
- 产出：`src/werewolf_eval/render_demo.py` + `tests/test_render_demo.py` + `docs/demo/phase2-runtime-demo.html`。
```

- [ ] **Step 5: Refresh `.oh-my-harness/tree.md`**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected behavior: `.oh-my-harness/tree.md` is updated and includes these entries:

```text
phase2-runtime-demo.html
render_demo.py
test_render_demo.py
```

- [ ] **Step 6: Validate docs and tree**

Run:

```bash
python - <<'PY'
from pathlib import Path

agents = Path("AGENTS.md").read_text(encoding="utf-8")
readme = Path("README.md").read_text(encoding="utf-8")
tasks = Path("docs/TASKS.md").read_text(encoding="utf-8")
tree = Path(".oh-my-harness/tree.md").read_text(encoding="utf-8")

checks = [
    ("AGENTS render command", "werewolf_eval.render_demo" in agents),
    ("AGENTS phase2 demo", "phase2-runtime-demo.html" in agents),
    ("AGENTS render_demo.py", "render_demo.py" in agents),
    ("AGENTS test_render_demo.py", "test_render_demo.py" in agents),
    ("AGENTS E1/E2/E3/E4", "当前已完成 runtime entries 为 E1/E2/E3/E4" in agents),
    ("README E4", "E4 runtime demo HTML exporter" in readme),
    ("README closed", "Phase 2 deterministic runtime demo 已闭环" in readme),
    ("README caveat", "真实 Decision Log / Consensus Log" in readme),
    ("TASKS E4", "E4：可视化页面" in tasks),
    ("TASKS completed", "状态：`completed`（Phase 2 E4 runtime demo HTML exporter" in tasks),
    ("tree phase2 demo", "phase2-runtime-demo.html" in tree),
    ("tree render_demo.py", "render_demo.py" in tree),
    ("tree test_render_demo.py", "test_render_demo.py" in tree),
]

failed = [label for label, ok in checks if not ok]
assert not failed, failed
print("E4 docs and tree validated")
PY
```

Expected result:

```text
E4 docs and tree validated
```

- [ ] **Step 7: Commit docs and tree update**

Run:

```bash
git add AGENTS.md README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: record e4 runtime demo boundary"
```

Expected result:

```text
[task/e4-runtime-demo-html ...] docs: record e4 runtime demo boundary
```

The exact commit hash may differ.

---

### Task 7: Final validation and PR preparation

**Files:**

- Create: none.
- Modify: none after previous tasks.
- Test: `tests/test_game_log.py`, `tests/test_scoring.py`, `tests/test_attribution.py`, `tests/test_render_demo.py`.

- [ ] **Step 1: Run accepted JSON artifact parse checks**

Run:

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
printf 'Accepted JSON artifacts still parse\n'
```

Expected result:

```text
Accepted JSON artifacts still parse
```

- [ ] **Step 2: Run runtime pipeline commands**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json \
  --out docs/demo/phase2-runtime-demo.html
```

Expected output includes:

```text
validated game_id=g001
players=6
events=38
winner=villager
end_round=2
```

```text
scored game_id=g001
score_records=14
winner=villager
game_length=2
wolf_team_outcome_score=2
```

```text
attributed game_id=g001
turn_points=1
top_rule=attribution:F.1.critical_vote
top_turn_point=s3_g001_tp001
```

```text
rendered demo game_id=g001
output=docs/demo/phase2-runtime-demo.html
sections=game,timeline,score,metrics,attribution,leaderboard
```

- [ ] **Step 3: Validate committed HTML artifact**

Run:

```bash
python - <<'PY'
from pathlib import Path
html = Path("docs/demo/phase2-runtime-demo.html").read_text(encoding="utf-8")
required = [
    "Werewolf-agent Phase 2 Runtime Demo",
    "g001",
    "村民阵营",
    "score_records=14",
    "s3_g001_tp001",
    "第 2 轮 2-1 处决 p1",
    "[deterministic]",
    "[mock]",
    "decision_quality_score fixed at 0",
]
missing = [item for item in required if item not in html]
assert not missing, missing
print("committed phase2 runtime demo html validated")
PY
```

Expected result:

```text
committed phase2 runtime demo html validated
```

- [ ] **Step 4: Run all unit tests**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result includes:

```text
Ran 24 tests
OK
```

The exact number may be higher if more tests exist, but all tests must pass.

- [ ] **Step 5: Verify no forbidden files were introduced**

Run:

```bash
test ! -d apps
test ! -d server
test ! -d web
test ! -f package.json
test ! -f package-lock.json
test ! -f pnpm-lock.yaml
test ! -f yarn.lock
test ! -f pyproject.toml
test ! -f requirements.txt
printf 'No app framework or dependency manifest introduced\n'
```

Expected result:

```text
No app framework or dependency manifest introduced
```

- [ ] **Step 6: Verify Phase 1 demo remains unchanged from main**

Run:

```bash
git diff --exit-code main...HEAD -- docs/demo/phase1-gold-demo.html
printf 'Phase 1 demo unchanged\n'
```

Expected result:

```text
Phase 1 demo unchanged
```

- [ ] **Step 7: Check whitespace**

Run:

```bash
git diff --check main...HEAD
```

Expected result:

```text
```

No output means no whitespace errors.

- [ ] **Step 8: Verify changed files**

Run:

```bash
git diff --name-only main...HEAD
```

Expected changed files:

```text
.oh-my-harness/tree.md
AGENTS.md
README.md
docs/TASKS.md
docs/demo/phase2-runtime-demo.html
src/werewolf_eval/render_demo.py
tests/test_render_demo.py
```

If this implementation PR also updates `docs/harness/plans/2026-05-30--e4-runtime-demo-html-plan.md`, include it in the PR description's changed-files list.

- [ ] **Step 9: Prepare Implementation PR description**

Use this PR description:

```md
## Summary

Implements E4 runtime demo HTML exporter for Werewolf-agent.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--e4-runtime-demo-html-plan.md`

## Scope

- Adds runtime-generated single-file HTML demo:
  - `docs/demo/phase2-runtime-demo.html`
- Adds `src/werewolf_eval/render_demo.py`.
- Reuses E1 Game Log parser, E2 deterministic scorer, and E3 rule attribution engine.
- Renders Game Summary, Timeline, Vote Summary, Score Log, Metrics Summary, Rule Attribution, and Leaderboard Demo.
- Adds tests for context generation, HTML sections, boundary labels, top attribution, leaderboard source labels, and CLI output.
- Updates AGENTS.md, README.md, TASKS.md, and `.oh-my-harness/tree.md`.

## Out of Scope

- No React/Vite/frontend framework.
- No backend server.
- No AI Agent gameplay.
- No Decision Log runtime.
- No Consensus Log runtime.
- No real multi-model Leaderboard.
- No external dependencies.
- No package manager files.
- No changes to accepted gold artifacts.
- No changes to `docs/demo/phase1-gold-demo.html`.

## Validation

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null

PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json \
  --out docs/demo/phase2-runtime-demo.html

PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"

git diff --exit-code main...HEAD -- docs/demo/phase1-gold-demo.html
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected changed files:

```text
.oh-my-harness/tree.md
AGENTS.md
README.md
docs/TASKS.md
docs/demo/phase2-runtime-demo.html
src/werewolf_eval/render_demo.py
tests/test_render_demo.py
```

## Risk

The main risk is confusing Phase 2 runtime-generated deterministic demo with a real Agent / real Leaderboard product. This PR keeps all source labels explicit, preserves Phase 1 caveats, and creates a separate `phase2-runtime-demo.html` instead of overwriting the Phase 1 static demo.
```

- [ ] **Step 10: Final status check**

Run:

```bash
git status --short
```

Expected result after all commits:

```text
```

No output means the working tree is clean.
