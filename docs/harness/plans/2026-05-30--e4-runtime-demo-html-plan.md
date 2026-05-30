# E4 Runtime Demo HTML Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Implement the Phase 2 runtime demo HTML exporter: reuse E1 Game Log parsing, E2 deterministic scoring, and E3 rule attribution to generate a double-clickable single-file HTML demo at `docs/demo/phase2-runtime-demo.html`.

**Architecture:** Add one focused Python runtime module, `src/werewolf_eval/render_demo.py`, that loads the Game Log, runs the existing E1/E2/E3 pipeline, builds a small render context, and writes a static HTML file with embedded CSS and no external assets. Keep `docs/demo/phase1-gold-demo.html` unchanged; the new Phase 2 output must prove that the visible demo can be regenerated from runtime code. Validate with standard-library `unittest` tests and command-line smoke checks.

**Tech Stack:** Python standard library only. Existing `unittest` style. No package manager changes, no external dependencies, no backend, no React/Vite, no JavaScript build pipeline.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before executing this plan, confirm these repository facts:

- Latest main includes PR #14 workflow guardrails.
- PR #13 is merged into `main` before starting implementation.
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

- The task boundary is clear: generate a deterministic single-file runtime HTML demo.
- The input is fixed: `docs/gold-game/g001-game-log.json`.
- The runtime pipeline is already available through E1/E2/E3.
- E4 is one implementation unit.
- The output is a static HTML artifact, not a frontend app or server.
- The UX goal is already defined: a double-clickable page that a non-technical user can understand in 3 minutes.

## Review Notes Addressed

This revision incorporates the E4 plan review notes:

- `avg_outcome_score` must be derived from `metrics_payload["score_summary"]`, not from a dead `score_payload["score_summary"]` branch. The planned implementation now computes the single-game total from player outcome scores plus team outcome scores, then divides by `games_played`.
- `AGENTS.md` MAP update must handle `docs/demo/` explicitly. If the MAP already contains `docs/demo/`, add `phase2-runtime-demo.html` under the existing directory. If it does not, add `docs/demo/` with both `phase1-gold-demo.html` and `phase2-runtime-demo.html`.
- PR #13 is an explicit preflight dependency because `render_demo.py` imports `werewolf_eval.attribution.attribute_game`.

## Scope Decision

This Implementation PR implements only the E4 runtime demo exporter.

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
- Explicit labels for `[deterministic]`, `[mock]`, and `[人工 gold sample]` where applicable.
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

- [ ] **Step 1: Confirm PR #13 dependency is merged**

Run:

```bash
gh pr view 13 --json state,mergedAt,title
```

Expected result includes:

```text
"state": "MERGED"
```

If local `gh` is unavailable, verify through GitHub UI/API that PR #13 is merged before continuing.

- [ ] **Step 2: Confirm runtime files exist**

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

- [ ] **Step 3: Confirm accepted JSON artifacts still parse**

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

- [ ] **Step 4: Confirm E1/E2/E3 commands still pass**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected validator output includes:

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
OK
```

No commit is required for Task 1 because it only verifies the starting state.

---

### Task 2: Add failing tests for runtime demo rendering

**Files:**

- Create: `tests/test_render_demo.py`
- Modify: none.
- Test: `tests/test_render_demo.py`

- [ ] **Step 1: Create `tests/test_render_demo.py` with import and fixture setup**

Create this file:

```python
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics
from werewolf_eval.attribution import attribute_game
from werewolf_eval.render_demo import build_demo_context, render_html, write_demo_html


class RuntimeDemoRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.attribution = attribute_game(self.game, self.score_log, self.metrics)
```

- [ ] **Step 2: Add context test**

Append:

```python
    def test_build_demo_context_uses_runtime_outputs(self) -> None:
        context = build_demo_context(self.game, self.score_log, self.metrics, self.attribution)

        self.assertEqual(context["game"]["game_id"], "g001")
        self.assertEqual(context["game"]["winner"], "villager")
        self.assertEqual(context["game"]["winner_label"], "村民阵营")
        self.assertEqual(context["game"]["players"], 6)
        self.assertEqual(context["game"]["events"], 38)
        self.assertEqual(context["score"]["records"], 14)
        self.assertEqual(context["attribution"]["turn_points"], 1)
        self.assertEqual(context["attribution"]["top_turn_point"], "s3_g001_tp001")
        self.assertGreaterEqual(len(context["timeline"]), 38)
        self.assertTrue(any(row["source_label"] == "[deterministic]" for row in context["leaderboard"]))
        self.assertTrue(any(row["source_label"] == "[mock]" for row in context["leaderboard"]))
        deterministic_row = next(row for row in context["leaderboard"] if row["source_label"] == "[deterministic]")
        self.assertEqual(deterministic_row["games_played"], 1)
        self.assertEqual(
            deterministic_row["avg_outcome_score"],
            sum(context["score"]["summary"]["player_outcome_scores"].values())
            + sum(context["score"]["summary"]["team_outcome_scores"].values()),
        )
```

- [ ] **Step 3: Add HTML content test**

Append:

```python
    def test_render_html_contains_required_demo_sections_and_boundaries(self) -> None:
        context = build_demo_context(self.game, self.score_log, self.metrics, self.attribution)
        html = render_html(context)

        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("Werewolf-agent Phase 2 Runtime Demo", html)
        self.assertIn("运行时生成", html)
        self.assertIn("时间线", html)
        self.assertIn("玩家状态", html)
        self.assertIn("投票表", html)
        self.assertIn("确定性指标", html)
        self.assertIn("规则归因", html)
        self.assertIn("Leaderboard", html)
        self.assertIn("[deterministic]", html)
        self.assertIn("[mock]", html)
        self.assertIn("decision_quality_score", html)
        self.assertIn("固定为 0", html)
        self.assertIn("not real AI Agent gameplay", html)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("https://", html)
```

- [ ] **Step 4: Add write smoke test**

Append:

```python
    def test_write_demo_html_creates_single_file_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "phase2-runtime-demo.html"
            write_demo_html(ROOT / "docs/gold-game/g001-game-log.json", output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertIn("Werewolf-agent Phase 2 Runtime Demo", html)
            self.assertIn("g001", html)
            self.assertIn("s3_g001_tp001", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run the new test and confirm it fails for the right reason**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_render_demo
```

Expected result before implementation:

```text
ModuleNotFoundError: No module named 'werewolf_eval.render_demo'
```

- [ ] **Step 6: Commit failing test**

```bash
git add tests/test_render_demo.py
git commit -m "test: specify E4 runtime demo rendering"
```

---

### Task 3: Implement runtime demo context builder

**Files:**

- Create: `src/werewolf_eval/render_demo.py`
- Modify: none.
- Test: `tests/test_render_demo.py`

- [ ] **Step 1: Create `src/werewolf_eval/render_demo.py` with imports and labels**

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
```

- [ ] **Step 2: Add `build_demo_context`**

Append:

```python
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
```

- [ ] **Step 3: Run the context test**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_render_demo.RuntimeDemoRenderTests.test_build_demo_context_uses_runtime_outputs
```

Expected result:

```text
OK
```

- [ ] **Step 4: Commit context builder**

```bash
git add src/werewolf_eval/render_demo.py tests/test_render_demo.py
git commit -m "feat: build E4 runtime demo context"
```

---

### Task 4: Implement static HTML renderer and CLI writer

**Files:**

- Modify: `src/werewolf_eval/render_demo.py`
- Test: `tests/test_render_demo.py`

- [ ] **Step 1: Add HTML table helpers**

Append to `src/werewolf_eval/render_demo.py`:

```python
def _row(cells: list[object]) -> str:
    return "<tr>" + "".join(f"<td>{_html(cell)}</td>" for cell in cells) + "</tr>"


def _head(cells: list[str]) -> str:
    return "<tr>" + "".join(f"<th>{_html(cell)}</th>" for cell in cells) + "</tr>"
```

- [ ] **Step 2: Add `render_html`**

Append a `render_html(context: dict[str, Any]) -> str` function that renders one complete `<!doctype html>` document with embedded CSS and no `<script>` tag. It must include these visible sections:

- `Werewolf-agent Phase 2 Runtime Demo`
- `边界声明`
- `对局摘要`
- `玩家状态`
- `时间线`
- `投票表`
- `确定性指标`
- `规则归因`
- `Leaderboard`

Use `_head()` and `_row()` for all table cells so every value passes through `_html()`.

Minimum required body content:

```python
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

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Werewolf-agent Phase 2 Runtime Demo</title>
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
  <h1>Werewolf-agent Phase 2 Runtime Demo</h1>
  <p><span class="badge">运行时生成</span><span class="badge">[deterministic]</span><span class="badge">[人工 gold sample]</span> This page is generated from the E1/E2/E3 runtime pipeline.</p>
  <section class="warning"><h2>边界声明</h2><p>This is not real AI Agent gameplay, not real Decision Log / Consensus Log collection, and not a real multi-model Leaderboard. 当前 decision_quality_score 固定为 0。</p></section>
  <section><h2>对局摘要</h2><p>Game: {_html(game["game_id"])} / Winner: {_html(game["winner_label"])} / Players: {_html(game["players"])} / Events: {_html(game["events"])} / Source: {_html(game["source_label"])}</p></section>
  <section><h2>玩家状态</h2><div class="scroll"><table>{_head(["玩家", "角色", "阵营", "终局状态"])}{player_rows}</table></div></section>
  <section><h2>时间线</h2><div class="scroll"><table>{_head(["序号", "轮次", "阶段", "类型", "行动者", "目标", "摘要"])}{timeline_rows}</table></div></section>
  <section><h2>投票表</h2><div class="scroll"><table>{_head(["轮次", "事件", "投票者", "目标", "摘要"])}{vote_rows}</table></div></section>
  <section><h2>确定性指标</h2><p>Score records: {_html(context["score"]["records"])} {_html(context["score"]["source_label"])}。decision_quality_score: 固定为 0。</p></section>
  <section><h2>规则归因</h2><p>{_html(context["attribution"]["description"])} {_html(context["attribution"]["source_label"])}</p><div class="scroll"><table>{_head(["转折点", "规则", "轮次", "主体", "影响分", "描述"])}{attribution_rows}</table></div></section>
  <section><h2>Leaderboard</h2><div class="scroll"><table>{_head(["Agent", "Model", "Games", "Win rate", "Outcome", "Decision", "Integrity", "Top attribution", "Source"])}{leaderboard_rows}</table></div></section>
</main>
</body>
</html>
"""
```

- [ ] **Step 3: Add writer and CLI**

Append:

```python
def write_demo_html(game_log_path: str | Path, output_path: str | Path) -> None:
    game = load_game_log(game_log_path)
    score_log = score_game(game)
    metrics = summarize_metrics(game, score_log)
    attribution = attribute_game(game, score_log, metrics)
    context = build_demo_context(game, score_log, metrics, attribution)
    Path(output_path).write_text(render_html(context), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Werewolf-agent Phase 2 runtime demo HTML.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--html-out", required=True, help="Output HTML file path")
    args = parser.parse_args()

    write_demo_html(args.path, args.html_out)
    print(f"rendered_demo_html={args.html_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run renderer tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_render_demo
```

Expected result:

```text
OK
```

- [ ] **Step 5: Generate the demo artifact**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html
```

Expected output:

```text
rendered_demo_html=docs/demo/phase2-runtime-demo.html
```

Expected file exists:

```bash
test -f docs/demo/phase2-runtime-demo.html
printf 'phase2 runtime demo exists\n'
```

Expected result:

```text
phase2 runtime demo exists
```

- [ ] **Step 6: Confirm Phase 1 demo was not overwritten**

Run:

```bash
git diff --name-only -- docs/demo/phase1-gold-demo.html
```

Expected result: no output.

- [ ] **Step 7: Commit renderer and generated artifact**

```bash
git add src/werewolf_eval/render_demo.py tests/test_render_demo.py docs/demo/phase2-runtime-demo.html
git commit -m "feat: render E4 runtime demo HTML"
```

---

### Task 5: Update project docs and tree map

**Files:**

- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/TASKS.md`
- Modify: `.oh-my-harness/tree.md`
- Test: existing command checks plus tree/MAP checks

- [ ] **Step 1: Update `README.md` current status**

Modify the current status paragraph to state that main contains E1/E2/E3 runtime code and that E4 adds a runtime-generated Phase 2 demo at `docs/demo/phase2-runtime-demo.html`.

Expected wording:

```markdown
**Phase 1 deterministic MVP 已完成。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer、E3 rule attribution engine 运行时代码；E4 以 `docs/demo/phase2-runtime-demo.html` 提供 Phase 2 runtime-generated demo，不代表真实 AI Agent 对局、真实 Decision Log / Consensus Log 或真实多模型 Leaderboard 已完成。
```

- [ ] **Step 2: Update `docs/TASKS.md` E4 and Demo 2 status**

Change E4 status to completed and record the runtime artifact.

Expected E4 wording:

```markdown
### E4：可视化页面

- 状态：`completed`（Phase 2 runtime demo HTML exporter）
- 产出：`src/werewolf_eval/render_demo.py` + `tests/test_render_demo.py` + `docs/demo/phase2-runtime-demo.html`。
- 说明：构建可双击打开的单文件静态 HTML，不依赖后端、不依赖构建工具、不引入 React/Vite。该页面从 E1/E2/E3 runtime pipeline 生成，包含时间线、状态表、投票表、指标表、评分卡、Leaderboard，并保留 Phase 2 边界声明。
```

Change Demo 2 status to completed for the runtime-generated demo boundary:

```markdown
- 状态：`completed`（`docs/demo/phase2-runtime-demo.html`；仅表示 E1/E2/E3 runtime pipeline 可生成可视化 demo，不表示真实 AI Agent / Decision Log / Consensus Log 已启用）
```

- [ ] **Step 3: Update `AGENTS.md` runtime entries, commands, and MAP**

Add the E4 command near existing command entries:

```markdown
- Runtime demo HTML 命令：`PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html`。
```

Update the runtime boundary sentence to include E4:

```markdown
- Phase 2 运行时代码必须绑定 Implementation Plan；当前已完成 runtime entries 为 E1/E2/E3/E4。
```

Update the MAP to include runtime and test files:

```text
│       ├── render_demo.py
```

```text
│   ├── test_render_demo.py
```

Update the MAP `docs/demo/` block as follows:

- If `docs/demo/` already exists in the MAP, add `phase2-runtime-demo.html` below `phase1-gold-demo.html`.
- If `docs/demo/` does not exist in the MAP, add this block under `docs/`:

```text
│   ├── demo/
│   │   ├── phase1-gold-demo.html
│   │   └── phase2-runtime-demo.html
```

- [ ] **Step 4: Refresh `.oh-my-harness/tree.md`**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result: `.oh-my-harness/tree.md` includes `render_demo.py`, `test_render_demo.py`, and `phase2-runtime-demo.html`.

- [ ] **Step 5: Run documentation boundary checks**

Run:

```bash
grep -R "phase2-runtime-demo.html" README.md docs/TASKS.md AGENTS.md .oh-my-harness/tree.md
grep -R "render_demo.py" AGENTS.md .oh-my-harness/tree.md
grep -R "test_render_demo.py" AGENTS.md .oh-my-harness/tree.md
grep -R "docs/demo" AGENTS.md
```

Expected result:

- The first command prints matches in README, TASKS, AGENTS, and tree.
- The second command prints matches in AGENTS and tree.
- The third command prints matches in AGENTS and tree.
- The fourth command confirms `AGENTS.md` MAP or routing text includes `docs/demo`.

- [ ] **Step 6: Commit documentation and tree updates**

```bash
git add AGENTS.md README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: mark E4 runtime demo complete"
```

---

### Task 6: Final verification and PR preparation

**Files:**

- Create: none.
- Modify: none.
- Test: full repository validation commands.

- [ ] **Step 1: Run full validation chain**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected validator output includes:

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

Expected renderer output:

```text
rendered_demo_html=docs/demo/phase2-runtime-demo.html
```

Expected unittest output includes:

```text
OK
```

- [ ] **Step 2: Confirm only intended files changed**

Run:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
.oh-my-harness/tree.md
AGENTS.md
README.md
docs/TASKS.md
docs/demo/phase2-runtime-demo.html
src/werewolf_eval/render_demo.py
tests/test_render_demo.py
```

- [ ] **Step 3: Confirm forbidden files did not change**

Run:

```bash
git diff --name-only main...HEAD -- docs/demo/phase1-gold-demo.html docs/EVALUATION_RUBRIC.md docs/gold-game/g001-game-log.json docs/gold-game/s2-score-log.json docs/gold-game/s2-metrics-summary.json docs/gold-game/s3-rule-attribution.json
```

Expected result: no output.

- [ ] **Step 4: Run whitespace check**

Run:

```bash
git diff --check
```

Expected result: no output.

- [ ] **Step 5: Prepare Implementation PR**

Use this PR title:

```text
feat: E4 runtime demo HTML exporter
```

Use this PR body:

```markdown
## Summary

Implements E4 runtime demo HTML exporter for Werewolf-agent.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--e4-runtime-demo-html-plan.md`

## Scope

- Adds `src/werewolf_eval/render_demo.py`.
- Adds `tests/test_render_demo.py`.
- Generates `docs/demo/phase2-runtime-demo.html` from the E1/E2/E3 runtime pipeline.
- Updates AGENTS.md, README.md, docs/TASKS.md, and .oh-my-harness/tree.md.

## Runtime boundary

- Keeps `docs/demo/phase1-gold-demo.html` unchanged.
- Does not call AI models.
- Does not introduce backend, React/Vite, frontend framework, external dependencies, or package manager files.
- Does not modify accepted gold artifacts or EVALUATION_RUBRIC.md.
- Clearly labels `[deterministic]`, `[mock]`, and `[人工 gold sample]` data.
- States that this is not real AI Agent gameplay, not real Decision Log / Consensus Log collection, and not a real multi-model Leaderboard.
- Keeps `decision_quality_score` fixed at 0 under the current boundary.

## Validation

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
git diff --check
```

Expected key outputs:

```text
validated game_id=g001
score_records=14
turn_points=1
rendered_demo_html=docs/demo/phase2-runtime-demo.html
OK
```
```

- [ ] **Step 6: Stop for review**

Do not merge automatically. Report changed files, validation outputs, and the generated demo path in the checkpoint summary.

---

## Checkpoint summary template for this PR

Use `docs/CHECKPOINT_TEMPLATE.md` and include:

```markdown
## Checkpoint Summary

Task: E4 runtime demo HTML exporter
Branch: `task/e4-runtime-demo-html-exporter`
Bound plan: `docs/harness/plans/2026-05-30--e4-runtime-demo-html-plan.md`

Changed files:
- `.oh-my-harness/tree.md`
- `AGENTS.md`
- `README.md`
- `docs/TASKS.md`
- `docs/demo/phase2-runtime-demo.html`
- `src/werewolf_eval/render_demo.py`
- `tests/test_render_demo.py`

Validation:
- `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html`
- `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
- `git diff --check`

Boundary confirmation:
- Phase 1 demo unchanged.
- No AI model calls.
- No backend/frontend framework.
- No external dependency or package manager change.
- Accepted gold artifacts unchanged.
```
