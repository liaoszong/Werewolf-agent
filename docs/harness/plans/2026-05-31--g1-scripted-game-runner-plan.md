# G1 Scripted Game Runner Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a deterministic scripted gameplay runner that can produce fresh Game Log, Decision Log, and Consensus Log runtime outputs without calling any model provider.

**Architecture:** This is the first G-track implementation after evaluator contracts stabilize. The runner consumes a small scripted scenario JSON, executes a fixed 6-player game flow, emits structured logs that reuse the existing validators, and runs the existing scoring / attribution / demo pipeline. It is an adapter seam for future Agent runtime work, not real AI gameplay.

**Tech Stack:** Python standard library only (`argparse`, `dataclasses`, `json`, `pathlib`, `unittest`, `subprocess`), existing `werewolf_eval` parser / validator / scorer modules, existing demo renderer, existing `scripts/dev/validate_brief.py`, existing tree refresh hook.

---

## Context

Claude Code is currently expected to finish S5 semantic-label scoring integration from `docs/harness/plans/2026-05-31--s5-semantic-label-scoring-integration-plan.md`. Do not start this G1a implementation until that PR is merged.

After S5 scoring integration, the evaluator side should have:

```text
Game Log + Decision Log + saved Semantic Label Log
-> Score Log / Metrics Summary
-> Rule Attribution
-> Runtime HTML Demo
```

The next useful product step is not a live LLM Agent. It is a deterministic scripted game runner that proves the project can generate a fresh set of runtime logs rather than only consuming hand-authored gold fixtures.

This plan intentionally implements a narrow G1a slice:

```text
scripted scenario JSON
-> deterministic runner
-> generated Game Log + Decision Log + Consensus Log
-> existing validators and evaluator pipeline
```

## Research PR Decision

No Research PR is needed.

Reasoning:

- Full G1 real AI Agent gameplay is broad, but this plan deliberately narrows it to a scripted deterministic runner.
- The required output schemas already exist: Game Log, Decision Log, Consensus Log, and S5 saved label scoring.
- The task is one implementation unit and does not require choosing providers, prompts, model behavior, or live failure recovery policy.
- Future real Agent runtime and provider adapters remain separate PRs.

## Prerequisite Gate

Before starting implementation, verify S5 scoring integration has merged.

Required files expected on `main`:

- `src/werewolf_eval/semantic_labels.py`
- `src/werewolf_eval/validate_semantic_labels.py`
- `docs/gold-game/s5-score-log.json`
- `docs/gold-game/s5-metrics-summary.json`
- `docs/demo/phase2-s5-runtime-demo.html`

Run:

```bash
git checkout main
git pull --ff-only
test -f src/werewolf_eval/semantic_labels.py
test -f docs/gold-game/s5-score-log.json
PYTHONPATH=src python -m unittest tests.test_semantic_labels tests.test_scoring tests.test_render_demo -v
```

Expected result:

```text
unittest: OK
```

If any required file is missing, stop and finish / merge S5 first. Do not start this implementation branch.

## Global Forbidden Scope

Do not implement any of the following:

- No provider API calls.
- No network calls.
- No SDK or dependency additions.
- No secrets or environment-variable requirements.
- No live AI Agent reasoning.
- No prompt execution.
- No stochastic gameplay.
- No multi-game Leaderboard aggregation.
- No web frontend.
- No real human-vs-AI UI.
- No changes to existing canonical `g001-*` gold fixtures.
- No changes to existing scoring formulas except any compatibility needed to consume generated logs through public APIs.
- No automatic repair of invalid generated logs.

## Files Overview

Create:

- `docs/game-scripts/g1-scripted-game.json`
  - Scripted scenario input. This is not a gold evaluator fixture; it is the runner input.
- `src/werewolf_eval/scripted_game.py`
  - Deterministic script parser and runner that emits Game Log, Decision Log, and Consensus Log dictionaries.
- `src/werewolf_eval/run_scripted_game.py`
  - CLI entrypoint for generating logs from a script file.
- `tests/test_scripted_game_runner.py`
  - Unit and CLI tests for script parsing, log generation, validation compatibility, and evaluator pipeline compatibility.
- `docs/generated-games/g1-scripted-game-log.json`
  - Generated Game Log output from the scripted runner.
- `docs/generated-games/g1-scripted-decision-log.json`
  - Generated Decision Log output from the scripted runner.
- `docs/generated-games/g1-scripted-consensus-log.json`
  - Generated Consensus Log output from the scripted runner.
- `docs/generated-games/g1-scripted-score-log.json`
  - Generated Score Log from the generated Game Log + Decision Log.
- `docs/generated-games/g1-scripted-metrics-summary.json`
  - Generated Metrics Summary from the generated Game Log + Decision Log.
- `docs/demo/phase3-g1-scripted-runtime-demo.html`
  - Runtime demo generated from the scripted game outputs.

Modify:

- `README.md`
  - Update current status to mention G1a scripted runner after implementation.
- `docs/TASKS.md`
  - Add G1a scripted gameplay runner status and demo acceptance entry.
- `.oh-my-harness/tree.md`
  - Refresh after adding files.

No other files should be modified.

---

### 任务 1：Add scripted scenario fixture

**文件：**
- 创建：`docs/game-scripts/g1-scripted-game.json`
- 创建：`tests/test_scripted_game_runner.py`
- 测试：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：创建 failing test skeleton**

Create `tests/test_scripted_game_runner.py` with this content:

```python
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ScriptedGameFixtureTests(unittest.TestCase):
    def test_script_fixture_exists_and_has_minimum_shape(self) -> None:
        path = ROOT / "docs/game-scripts/g1-scripted-game.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["script_id"], "g1_scripted_001")
        self.assertEqual(payload["game_id"], "g1_scripted_001")
        self.assertEqual(len(payload["players"]), 6)
        self.assertGreaterEqual(len(payload["steps"]), 10)
        self.assertEqual(payload["result"]["winner"], "villager")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameFixtureTests -v
```

Expected result before fixture creation:

```text
FileNotFoundError
```

- [ ] **步骤 3：创建 scripted scenario JSON**

Create `docs/game-scripts/g1-scripted-game.json` with this complete content:

```json
{
  "script_id": "g1_scripted_001",
  "game_id": "g1_scripted_001",
  "source_label": "[scripted deterministic sample]",
  "players": [
    {"player_id": "p1", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p2", "role": "werewolf", "team": "werewolf"},
    {"player_id": "p3", "role": "seer", "team": "villager"},
    {"player_id": "p4", "role": "witch", "team": "villager"},
    {"player_id": "p5", "role": "villager", "team": "villager"},
    {"player_id": "p6", "role": "villager", "team": "villager"}
  ],
  "steps": [
    {"step_id": "s001", "round": 0, "phase": "setup", "type": "role_assignment", "actor": "system", "target": "none", "visibility": "specific_player_ids", "summary": "Roles are assigned for the scripted game."},
    {"step_id": "s002", "round": 1, "phase": "night", "type": "werewolf_kill", "actor": "wolf_team", "target": "p5", "visibility": "werewolf_team", "decision_actor": "wolf_team", "decision_type": "team_coordinated", "reason_summary": "Wolf team selects p5 as a low-information villager target.", "visible_info_refs": ["g1_scripted_001_e001"], "consensus": {"participants": ["p1", "p2"], "coordinator": "p1", "status": "consensus", "primary_proposer": "p1", "supporters": ["p1", "p2"], "dissenters": []}},
    {"step_id": "s003", "round": 1, "phase": "night", "type": "seer_check", "actor": "p3", "target": "p1", "visibility": "seer", "decision_actor": "p3", "decision_type": "inference_based", "reason_summary": "Seer checks p1 as an early pressure target.", "visible_info_refs": []},
    {"step_id": "s004", "round": 1, "phase": "night", "type": "witch_save", "actor": "p4", "target": "p5", "visibility": "witch", "decision_actor": "p4", "decision_type": "inference_based", "reason_summary": "Witch saves p5 after seeing the night kill target.", "visible_info_refs": []},
    {"step_id": "s005", "round": 1, "phase": "day", "type": "player_speech", "actor": "p3", "target": "p1", "visibility": "public", "summary": "p3 publicly pressures p1 after the night check."},
    {"step_id": "s006", "round": 1, "phase": "day", "type": "player_vote", "actor": "p4", "target": "p1", "visibility": "public", "decision_actor": "p4", "decision_type": "inference_based", "reason_summary": "p4 follows p3's pressure and votes p1.", "visible_info_refs": ["g1_scripted_001_e005"]},
    {"step_id": "s007", "round": 1, "phase": "day", "type": "player_vote", "actor": "p5", "target": "p3", "visibility": "public", "decision_actor": "p5", "decision_type": "default", "reason_summary": "p5 votes p3 because the public claim is not fully proven.", "visible_info_refs": ["g1_scripted_001_e005"]},
    {"step_id": "s008", "round": 1, "phase": "day", "type": "player_eliminated", "actor": "system", "target": "p1", "visibility": "public", "summary": "p1 is eliminated by vote."},
    {"step_id": "s009", "round": 1, "phase": "day", "type": "role_revealed", "actor": "system", "target": "p1", "visibility": "public", "summary": "p1 is revealed as werewolf."},
    {"step_id": "s010", "round": 2, "phase": "night", "type": "werewolf_kill", "actor": "wolf_team", "target": "p3", "visibility": "werewolf_team", "decision_actor": "wolf_team", "decision_type": "team_coordinated", "reason_summary": "Remaining wolf targets the confirmed seer p3.", "visible_info_refs": ["g1_scripted_001_e009"], "consensus": {"participants": ["p2"], "coordinator": "p2", "status": "consensus", "primary_proposer": "p2", "supporters": ["p2"], "dissenters": []}},
    {"step_id": "s011", "round": 2, "phase": "night", "type": "player_died", "actor": "system", "target": "p3", "visibility": "public", "summary": "p3 dies at night."},
    {"step_id": "s012", "round": 2, "phase": "day", "type": "player_vote", "actor": "p6", "target": "p2", "visibility": "public", "decision_actor": "p6", "decision_type": "inference_based", "reason_summary": "p6 votes p2 after p1's reveal and the seer death.", "visible_info_refs": ["g1_scripted_001_e009", "g1_scripted_001_e011"]},
    {"step_id": "s013", "round": 2, "phase": "day", "type": "player_eliminated", "actor": "system", "target": "p2", "visibility": "public", "summary": "p2 is eliminated by vote."},
    {"step_id": "s014", "round": 2, "phase": "day", "type": "role_revealed", "actor": "system", "target": "p2", "visibility": "public", "summary": "p2 is revealed as werewolf."},
    {"step_id": "s015", "round": 2, "phase": "game_end", "type": "game_over", "actor": "system", "target": "villager_team", "visibility": "public", "summary": "Villagers win after both werewolves are eliminated."}
  ],
  "result": {
    "winner": "villager",
    "end_round": 2,
    "survivors": ["p4", "p5", "p6"],
    "end_condition": "all_werewolves_eliminated"
  }
}
```

- [ ] **步骤 4：运行 fixture test**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameFixtureTests -v
```

Expected result:

```text
Ran 1 test
OK
```

- [ ] **步骤 5：提交 task 1**

```bash
git add docs/game-scripts/g1-scripted-game.json tests/test_scripted_game_runner.py
git commit -m "test: add G1 scripted game fixture"
```

---

### 任务 2：Implement deterministic scripted runner

**文件：**
- 创建：`src/werewolf_eval/scripted_game.py`
- 修改：`tests/test_scripted_game_runner.py`
- 测试：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：添加 runner failing tests**

Append to `tests/test_scripted_game_runner.py`:

```python
class ScriptedGameRunnerTests(unittest.TestCase):
    def test_runner_emits_valid_log_dicts(self) -> None:
        from werewolf_eval.game_log import parse_game_log
        from werewolf_eval.decision_log import parse_decision_log
        from werewolf_eval.consensus_log import parse_consensus_log
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        outputs = run_scripted_game(script)

        game = parse_game_log(outputs.game_log)
        decision_log = parse_decision_log(outputs.decision_log, game)
        consensus_log = parse_consensus_log(outputs.consensus_log, game)

        self.assertEqual(game.game_id, "g1_scripted_001")
        self.assertEqual(len(game.events), 15)
        self.assertGreaterEqual(len(decision_log.decisions), 6)
        self.assertEqual(len(consensus_log.consensuses), 2)
        self.assertEqual(game.result.winner, "villager")

    def test_runner_is_deterministic(self) -> None:
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        first = run_scripted_game(script)
        second = run_scripted_game(script)

        self.assertEqual(first.game_log, second.game_log)
        self.assertEqual(first.decision_log, second.decision_log)
        self.assertEqual(first.consensus_log, second.consensus_log)
```

- [ ] **步骤 2：运行测试确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameRunnerTests -v
```

Expected result before implementation:

```text
ModuleNotFoundError: No module named 'werewolf_eval.scripted_game'
```

- [ ] **步骤 3：实现 `scripted_game.py`**

Create `src/werewolf_eval/scripted_game.py` with these public objects:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class ScriptedGame:
    raw: dict[str, Any]

@dataclass(frozen=True)
class ScriptedGameOutputs:
    game_log: dict[str, Any]
    decision_log: dict[str, Any]
    consensus_log: dict[str, Any]

def load_scripted_game(path: str | Path) -> ScriptedGame:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("scripted game root must be an object")
    return ScriptedGame(raw=raw)

def run_scripted_game(script: ScriptedGame) -> ScriptedGameOutputs:
    ...
```

Implementation requirements:

- Generate event IDs as `{game_id}_e001`, `{game_id}_e002`, ... from script step order.
- Generate Game Log events from every script step.
- Preserve `data.summary` on every event.
- Preserve `data.visible_info_refs` only when present on the script step.
- Generate Decision Log entries only for steps with `decision_actor`.
- Decision IDs must be `{game_id}_d001`, `{game_id}_d002`, ... in script order.
- Decision Log `source_label` must be `[人工 gold sample]` for compatibility with current parser source labels.
- Generate Consensus Log entries only for steps with `type == "werewolf_kill"` and `consensus` object.
- Consensus IDs must be `{game_id}_c001`, `{game_id}_c002`, ... in script order.
- Consensus Log `source_label` must be `[人工 gold sample]` for compatibility with current parser source labels.
- Each consensus entry must include one proposal from `primary_proposer`, zero or more support responses from other supporters, and a final decision matching the kill target.
- Do not inspect roles beyond the data provided in the script.
- Do not call scorers, renderers, models, or network code from `run_scripted_game()`.

- [ ] **步骤 4：运行 runner tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameRunnerTests -v
```

Expected result:

```text
Ran 2 tests
OK
```

- [ ] **步骤 5：提交 task 2**

```bash
git add src/werewolf_eval/scripted_game.py tests/test_scripted_game_runner.py
git commit -m "feat: add deterministic scripted game runner"
```

---

### 任务 3：Add scripted runner CLI and generated logs

**文件：**
- 创建：`src/werewolf_eval/run_scripted_game.py`
- 修改：`tests/test_scripted_game_runner.py`
- 创建：`docs/generated-games/g1-scripted-game-log.json`
- 创建：`docs/generated-games/g1-scripted-decision-log.json`
- 创建：`docs/generated-games/g1-scripted-consensus-log.json`
- 测试：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：添加 CLI failing test**

Append to `tests/test_scripted_game_runner.py`:

```python
class ScriptedGameCliTests(unittest.TestCase):
    def test_run_scripted_game_cli_writes_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_scripted_game",
                    str(ROOT / "docs/game-scripts/g1-scripted-game.json"),
                    "--game-log-out",
                    str(out / "game.json"),
                    "--decision-log-out",
                    str(out / "decision.json"),
                    "--consensus-log-out",
                    str(out / "consensus.json"),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("scripted_game_id=g1_scripted_001", result.stdout)
            self.assertIn("events=15", result.stdout)
            self.assertIn("decisions=7", result.stdout)
            self.assertIn("consensuses=2", result.stdout)
            self.assertTrue((out / "game.json").exists())
            self.assertTrue((out / "decision.json").exists())
            self.assertTrue((out / "consensus.json").exists())
```

- [ ] **步骤 2：运行 CLI test 确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameCliTests -v
```

Expected result before implementation:

```text
No module named werewolf_eval.run_scripted_game
```

- [ ] **步骤 3：实现 CLI**

Create `src/werewolf_eval/run_scripted_game.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game


def _write_json(path: str | Path, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic logs from a scripted Werewolf game.")
    parser.add_argument("script_path")
    parser.add_argument("--game-log-out", required=True)
    parser.add_argument("--decision-log-out", required=True)
    parser.add_argument("--consensus-log-out", required=True)
    args = parser.parse_args()

    script = load_scripted_game(args.script_path)
    outputs = run_scripted_game(script)

    _write_json(args.game_log_out, outputs.game_log)
    _write_json(args.decision_log_out, outputs.decision_log)
    _write_json(args.consensus_log_out, outputs.consensus_log)

    print(f"scripted_game_id={outputs.game_log['game_id']}")
    print(f"events={len(outputs.game_log['events'])}")
    print(f"decisions={len(outputs.decision_log['decisions'])}")
    print(f"consensuses={len(outputs.consensus_log['consensuses'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 4：生成 canonical generated logs**

Run:

```bash
mkdir -p docs/generated-games
PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out docs/generated-games/g1-scripted-game-log.json --decision-log-out docs/generated-games/g1-scripted-decision-log.json --consensus-log-out docs/generated-games/g1-scripted-consensus-log.json
```

Expected result:

```text
scripted_game_id=g1_scripted_001
events=15
decisions=7
consensuses=2
```

- [ ] **步骤 5：validate generated logs**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-decision-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-consensus-log.json
```

Expected result:

```text
validated game_id=g1_scripted_001
validated decision_log_id=g1_scripted_001_decision_log
validated consensus_log_id=g1_scripted_001_consensus_log
```

- [ ] **步骤 6：运行 CLI tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameCliTests -v
```

Expected result:

```text
Ran 1 test
OK
```

- [ ] **步骤 7：提交 task 3**

```bash
git add src/werewolf_eval/run_scripted_game.py tests/test_scripted_game_runner.py docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-decision-log.json docs/generated-games/g1-scripted-consensus-log.json
git commit -m "feat: add scripted game runner CLI"
```

---

### 任务 4：Connect generated game to evaluator pipeline

**文件：**
- 修改：`tests/test_scripted_game_runner.py`
- 创建：`docs/generated-games/g1-scripted-score-log.json`
- 创建：`docs/generated-games/g1-scripted-metrics-summary.json`
- 创建：`docs/demo/phase3-g1-scripted-runtime-demo.html`
- 测试：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：添加 evaluator pipeline test**

Append to `tests/test_scripted_game_runner.py`:

```python
class ScriptedGameEvaluatorPipelineTests(unittest.TestCase):
    def test_generated_logs_can_be_scored_and_rendered(self) -> None:
        from werewolf_eval.attribution import attribute_game
        from werewolf_eval.decision_log import load_decision_log
        from werewolf_eval.game_log import load_game_log
        from werewolf_eval.render_demo import build_demo_context, render_html
        from werewolf_eval.scoring import score_game, summarize_metrics

        game = load_game_log(ROOT / "docs/generated-games/g1-scripted-game-log.json")
        decision_log = load_decision_log(ROOT / "docs/generated-games/g1-scripted-decision-log.json", game)
        score_log = score_game(game, decision_log=decision_log)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
        html = render_html(build_demo_context(game, score_log, metrics, attribution))

        self.assertEqual(score_log.game_id, "g1_scripted_001")
        self.assertGreater(len(score_log.records), 0)
        self.assertEqual(metrics.result_metrics.winner, "villager")
        self.assertIn("g1_scripted_001", html)
        self.assertNotIn("https://", html)
```

- [ ] **步骤 2：运行 pipeline test 确认当前生成物缺失**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameEvaluatorPipelineTests -v
```

Expected result before generated logs exist:

```text
FileNotFoundError
```

- [ ] **步骤 3：生成 score / metrics outputs**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --score-log-out docs/generated-games/g1-scripted-score-log.json --metrics-out docs/generated-games/g1-scripted-metrics-summary.json
```

Expected result:

```text
scored game_id=g1_scripted_001
score_records=6
winner=villager
game_length=2
wolf_team_outcome_score=5
decision_log=enabled
```

If S5 scoring integration has added `semantic_labels=disabled` to the CLI output, record that line in the PR validation summary.

- [ ] **步骤 4：生成 runtime demo HTML**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --html-out docs/demo/phase3-g1-scripted-runtime-demo.html
```

Expected result:

```text
rendered_demo_html=docs/demo/phase3-g1-scripted-runtime-demo.html
```

- [ ] **步骤 5：运行 pipeline test**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameEvaluatorPipelineTests -v
```

Expected result:

```text
Ran 1 test
OK
```

- [ ] **步骤 6：提交 task 4**

```bash
git add tests/test_scripted_game_runner.py docs/generated-games/g1-scripted-score-log.json docs/generated-games/g1-scripted-metrics-summary.json docs/demo/phase3-g1-scripted-runtime-demo.html
git commit -m "feat: connect scripted game to evaluator pipeline"
```

---

### 任务 5：Update status docs and validate

**文件：**
- 修改：`README.md`
- 修改：`docs/TASKS.md`
- 修改：`.oh-my-harness/tree.md`
- 测试：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：更新 README current status**

Modify the current-status paragraph in `README.md` to include this sentence:

```markdown
G1a 已提供 scripted deterministic game runner，可从 `docs/game-scripts/g1-scripted-game.json` 生成新的 Game Log / Decision Log / Consensus Log，并通过现有 evaluator pipeline 生成 `docs/demo/phase3-g1-scripted-runtime-demo.html`。这仍不代表 live AI Agent gameplay、provider integration 或 human-vs-AI UI 已完成。
```

- [ ] **步骤 2：更新 TASKS G1 section**

In `docs/TASKS.md`, update G1 status to include G1a:

```markdown
### G1：Real AI Agent gameplay engine

- 状态：`phase_3_candidate`; G1a scripted deterministic game runner completed after implementation.
- 产出（G1a）：`docs/game-scripts/g1-scripted-game.json` + `src/werewolf_eval/scripted_game.py` + `src/werewolf_eval/run_scripted_game.py` + `docs/generated-games/g1-scripted-game-log.json` + `docs/generated-games/g1-scripted-decision-log.json` + `docs/generated-games/g1-scripted-consensus-log.json` + `docs/demo/phase3-g1-scripted-runtime-demo.html`。
- 依赖：稳定的 Game Log / Decision Log / Consensus Log / scoring contracts。
- 目标：先以 deterministic scripted runner 验证 fresh log generation，再进入真实 Agent runtime。
- 边界：G1a 不做 provider integration，不做 live AI reasoning，不做 human-vs-AI UI，不做 multi-game Leaderboard。
```

Add Demo Acceptance entry:

```markdown
**Demo 7：Phase 3 G1a scripted runtime game**

- 状态：`completed`（`docs/demo/phase3-g1-scripted-runtime-demo.html`）
- 触发条件：G1a scripted deterministic runner 完成。
- 演示内容：scripted scenario JSON → generated Game Log / Decision Log / Consensus Log → Score Log / Metrics Summary → Runtime HTML Demo。
- 验收：同一 script 两次生成完全一致；三个 generated logs 均通过现有 validators；页面明确不代表 live AI Agent gameplay。
```

- [ ] **步骤 3：运行 targeted tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner -v
```

Expected result:

```text
OK
```

- [ ] **步骤 4：运行 full validation summary**

```bash
PYTHONPATH=src python scripts/dev/validate_brief.py
```

Expected result:

```json
{"ok": true}
```

The JSON may include more fields. `ok` must be `true` and failed commands must be empty.

- [ ] **步骤 5：检查 whitespace**

```bash
git diff --check
```

Expected result:

```text
```

No output means success.

- [ ] **步骤 6：刷新 tree**

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md updated
```

If the hook prints a different success line but updates `.oh-my-harness/tree.md`, record that exact output in the PR body.

- [ ] **步骤 7：提交 task 5**

```bash
git add README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: update G1a scripted runner status"
```

---

## Final Validation Commands

Run all commands before review:

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner -v
PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out docs/generated-games/g1-scripted-game-log.json --decision-log-out docs/generated-games/g1-scripted-decision-log.json --consensus-log-out docs/generated-games/g1-scripted-consensus-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-decision-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-consensus-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --score-log-out docs/generated-games/g1-scripted-score-log.json --metrics-out docs/generated-games/g1-scripted-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --html-out docs/demo/phase3-g1-scripted-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
```

Expected results:

```text
scripted runner tests: OK
run_scripted_game: events=15 decisions=7 consensuses=2
validate_game_log: validated game_id=g1_scripted_001
validate_decision_log: validated decision_log_id=g1_scripted_001_decision_log
validate_consensus_log: validated consensus_log_id=g1_scripted_001_consensus_log
score_game: scored game_id=g1_scripted_001
render_demo: rendered_demo_html=docs/demo/phase3-g1-scripted-runtime-demo.html
validate_brief: ok=true
git diff --check: no output
```

## Self-review Checklist

- G1a does not call providers or run live AI reasoning.
- The runner is deterministic.
- Generated Game Log / Decision Log / Consensus Log validate through existing validators.
- Generated logs are stored under `docs/generated-games/`, not mixed into canonical `docs/gold-game/g001-*` fixtures.
- Existing scorer / attribution / renderer consume the generated logs without special casing.
- README and TASKS do not claim real AI Agent gameplay is complete.
- The implementation waits for S5 scoring integration to merge first.

## Implementation PR Description Draft

Title:

```text
feat: add G1a scripted game runner
```

Body:

```markdown
## Summary

Add a deterministic scripted game runner as the first G-track step after evaluator contracts stabilize.

Bound plan: `docs/harness/plans/2026-05-31--g1-scripted-game-runner-plan.md`

## Changes

- Add scripted scenario fixture at `docs/game-scripts/g1-scripted-game.json`.
- Add deterministic runner and CLI.
- Generate fresh Game Log / Decision Log / Consensus Log under `docs/generated-games/`.
- Validate generated logs with existing validators.
- Run generated logs through scoring / attribution / runtime demo pipeline.
- Add `docs/demo/phase3-g1-scripted-runtime-demo.html`.
- Update README / TASKS status and refresh tree.

## Validation

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner -v
PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out docs/generated-games/g1-scripted-game-log.json --decision-log-out docs/generated-games/g1-scripted-decision-log.json --consensus-log-out docs/generated-games/g1-scripted-consensus-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-decision-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-consensus-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --score-log-out docs/generated-games/g1-scripted-score-log.json --metrics-out docs/generated-games/g1-scripted-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --html-out docs/demo/phase3-g1-scripted-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
```

## Boundaries

- No provider API calls.
- No network calls.
- No new dependencies.
- No live AI Agent reasoning.
- No prompt execution.
- No gameplay UI.
- No multi-game Leaderboard aggregation.
```
