# G1a Scripted Deterministic Fresh-Log Runner Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add the first Phase 3 / G-track slice: a scripted deterministic fresh-log runner that emits new Game Log, Decision Log, and Consensus Log artifacts and proves they can pass the existing evaluator path.

**Architecture:** A committed scripted scenario is parsed by a deterministic runner. The runner emits scripted deterministic Game Log / Decision Log / Consensus Log outputs, then the existing validators, scorer, attribution, and renderer consume those generated outputs. This is not Agent runtime output and does not complete G1 real AI Agent gameplay.

**Tech Stack:** Python standard library only (`argparse`, `dataclasses`, `json`, `pathlib`, `unittest`, `subprocess`), existing `werewolf_eval` parser / validator / scorer modules, existing demo renderer, existing `scripts/dev/validate_brief.py`, existing `scripts/dev/build_review_packet.py`, existing tree refresh hook.

---

## Context

Current main has Phase 2 evaluator contracts in place, including Game Log, Decision Log, Consensus Log, deterministic scoring, saved S5 semantic labels, and runtime demo rendering.

This plan intentionally implements only G1a:

```text
scripted scenario JSON
-> deterministic runner
-> scripted deterministic Game Log + Decision Log + Consensus Log
-> existing validators
-> evaluator / demo compatibility proof
```

G1a is a fresh-log generation step. It is not an Agent runtime, not provider-backed gameplay, not live AI gameplay, not a live observer, and not human-vs-AI UI.

## Research PR Decision

Research PR: **NO**.

Reasoning:

- `docs/specs/agent-workflow.md` says Research PR is not mandatory when a task boundary is clear and one implementation unit can be planned directly.
- Full G1 remains a Phase 3 / G-track objective, but this plan narrows the next execution unit to scripted deterministic fresh-log generation.
- Provider choice, prompt behavior, runtime agent design, live failure recovery policy, live UI, and multi-game Leaderboard remain out of scope.

## Prerequisite Gate

Before starting implementation, verify S5 saved-label scoring integration and Review Packet Gate v1 are on `main`.

Required files expected on `main`:

- `src/werewolf_eval/semantic_labels.py`
- `src/werewolf_eval/validate_semantic_labels.py`
- `docs/gold-game/s5-score-log.json`
- `docs/gold-game/s5-metrics-summary.json`
- `docs/demo/phase2-s5-runtime-demo.html`
- `docs/specs/review-packet-gate.md`
- `scripts/dev/build_review_packet.py`

Run:

```bash
git checkout main
git pull --ff-only
PYTHONPATH=src python -m unittest tests.test_semantic_labels tests.test_scoring tests.test_render_demo tests.test_build_review_packet -v
```

Expected result:

```text
OK
```

If any required file is missing, stop and finish the missing prerequisite first. Do not start this implementation branch.

## Scope Definition

G1a output classification:

- The generated Game Log is scripted deterministic output.
- The generated Decision Log is scripted deterministic output.
- The generated Consensus Log is scripted deterministic output.
- These logs are not Agent runtime output.
- These logs are not live AI output.
- These logs are not human-authored gold samples.

Required source label decision:

- Add `[scripted deterministic output]` to Decision Log and Consensus Log parser allowlists.
- Generated Decision Log and Consensus Log must use `[scripted deterministic output]`.
- Do not label scripted generated logs as `[人工 gold sample]`.
- Do not label scripted generated logs as `[AI 生成]`.
- This is a provenance compatibility change only. It must not change runtime scoring semantics or validation semantics beyond accepting the new explicit source label.

## Allowed Files

Implementation may create or modify only these files:

- `docs/game-scripts/g1-scripted-game.json`
- `src/werewolf_eval/scripted_game.py`
- `src/werewolf_eval/run_scripted_game.py`
- `tests/test_scripted_game_runner.py`
- `docs/generated-games/g1-scripted-game-log.json`
- `docs/generated-games/g1-scripted-decision-log.json`
- `docs/generated-games/g1-scripted-consensus-log.json`
- `docs/generated-games/g1-scripted-score-log.json`
- `docs/generated-games/g1-scripted-metrics-summary.json`
- `docs/demo/phase3-g1-scripted-runtime-demo.html`
- `README.md`
- `docs/TASKS.md`
- `.oh-my-harness/tree.md`

Provenance compatibility changes are allowed only in these files:

- `src/werewolf_eval/decision_log.py`
- `src/werewolf_eval/consensus_log.py`
- `tests/test_decision_log.py`
- `tests/test_consensus_log.py`
- `src/werewolf_eval/scoring.py`
- `tests/test_scoring.py`
- `src/werewolf_eval/attribution.py`
- `tests/test_attribution.py`
- `src/werewolf_eval/render_demo.py`
- `tests/test_render_demo.py`

Do not modify any other file.

## Global Forbidden Scope

Do not implement or add any of the following:

- provider API calls
- network calls
- SDK additions
- dependency additions
- secrets
- environment-variable requirements
- live AI reasoning
- prompt execution
- stochastic gameplay
- Agent runtime abstraction
- mock-agent abstraction
- real wolf consensus protocol
- Web live observer
- human-vs-AI UI
- multi-game Leaderboard
- canonical `docs/gold-game/g001-*` fixture edits
- scoring formula changes
- automatic repair of invalid generated logs

If implementation appears to require any forbidden item, stop and revise this plan before coding.

## Codex B档 Deep-Review Risk Points

The implementation PR is expected to trigger at least some Review Packet risk markers. The implementer must call these out in the Review Packet risk notes.

Known risk points:

- Changed files may exceed 8.
- `docs/demo/**` will change.
- Generated artifacts under `docs/generated-games/**` will be added.
- `src/werewolf_eval/*log*.py` may change for source label allowlists.
- `src/werewolf_eval/scoring.py` may change for dynamic generated-artifact provenance.
- Source label / provenance changes require careful review.
- Dependency / import diff must show no new dependencies.
- Forbidden pattern scan must show no runtime provider / network / env / live AI capability.

If `src/werewolf_eval/scoring.py`, `src/werewolf_eval/render_demo.py`, or any `*log*.py` file changes, expect Codex A档 to return `NEED_DEEP_REVIEW` unless the Review Packet evidence is very tight.

## Review Packet Requirements

No Review Packet, no Codex implementation review.

After implementation and validation, generate:

```text
.logs/review/latest/review-packet.md
```

The Review Packet must include at least:

- `git diff --name-only`
- `git diff --stat`
- `git diff --check` result
- changed files allowlist check
- forbidden patterns check
- dependency/import diff check
- test command and exact pass/fail summary
- key hunk excerpts
- acceptance checklist with evidence pointer
- implementer risk notes

Use `scripts/dev/build_review_packet.py` with explicit allowlist, test commands, acceptance items, and risk notes. The final command must be updated with the exact validation commands actually run, but it must follow this shape:

```bash
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md \
  --allowlist "docs/game-scripts/g1-scripted-game.json" \
  --allowlist "src/werewolf_eval/scripted_game.py" \
  --allowlist "src/werewolf_eval/run_scripted_game.py" \
  --allowlist "tests/test_scripted_game_runner.py" \
  --allowlist "docs/generated-games/g1-scripted-game-log.json" \
  --allowlist "docs/generated-games/g1-scripted-decision-log.json" \
  --allowlist "docs/generated-games/g1-scripted-consensus-log.json" \
  --allowlist "docs/generated-games/g1-scripted-score-log.json" \
  --allowlist "docs/generated-games/g1-scripted-metrics-summary.json" \
  --allowlist "docs/demo/phase3-g1-scripted-runtime-demo.html" \
  --allowlist "README.md" \
  --allowlist "docs/TASKS.md" \
  --allowlist ".oh-my-harness/tree.md" \
  --allowlist "src/werewolf_eval/decision_log.py" \
  --allowlist "src/werewolf_eval/consensus_log.py" \
  --allowlist "tests/test_decision_log.py" \
  --allowlist "tests/test_consensus_log.py" \
  --allowlist "src/werewolf_eval/scoring.py" \
  --allowlist "tests/test_scoring.py" \
  --allowlist "src/werewolf_eval/attribution.py" \
  --allowlist "tests/test_attribution.py" \
  --allowlist "src/werewolf_eval/render_demo.py" \
  --allowlist "tests/test_render_demo.py" \
  --test-env PYTHONPATH=src \
  --test-command "python -m unittest tests.test_scripted_game_runner tests.test_decision_log tests.test_consensus_log tests.test_scoring tests.test_attribution tests.test_render_demo -v" \
  --test-command "python scripts/dev/validate_brief.py" \
  --acceptance "A-1: generated logs validate | validate_game_log + validate_decision_log + validate_consensus_log commands | PASS" \
  --acceptance "A-2: generated artifacts use g1_scripted_001 | tests.test_scripted_game_runner.ScriptedGameArtifactProvenanceTests | PASS" \
  --acceptance "A-3: generated artifacts do not contain stale s2_g001 ids | tests.test_scripted_game_runner.ScriptedGameArtifactProvenanceTests | PASS" \
  --acceptance "A-4: generated demo labels scripted deterministic boundary | tests.test_render_demo.RuntimeDemoRenderTests | PASS" \
  --acceptance "A-5: no provider, network, dependency, env, or live AI runtime capability | forbidden pattern check + import diff | PASS" \
  --risk-note "Expected risk: docs/demo and generated artifacts changed." \
  --risk-note "Expected risk: source label and provenance compatibility changes may require B档 deep review."
```

Expected output:

```text
wrote .logs/review/latest/review-packet.md
PACKET_TOO_LARGE = NO
```

If the packet reports `PACKET_TOO_LARGE = YES`, the PR description must say Codex A档 should return `NEED_DEEP_REVIEW` and list exact file ranges for B档.

## Files Overview

Create:

- `docs/game-scripts/g1-scripted-game.json`
  - Scripted scenario input. This is runner input, not a gold evaluator fixture.
- `src/werewolf_eval/scripted_game.py`
  - Deterministic script parser and runner that emits Game Log, Decision Log, and Consensus Log dictionaries.
- `src/werewolf_eval/run_scripted_game.py`
  - CLI entrypoint for generating logs from a script file.
- `tests/test_scripted_game_runner.py`
  - Unit and CLI tests for script parsing, log generation, validation compatibility, artifact provenance, and evaluator pipeline compatibility.
- `docs/generated-games/g1-scripted-game-log.json`
  - Generated scripted deterministic Game Log output.
- `docs/generated-games/g1-scripted-decision-log.json`
  - Generated scripted deterministic Decision Log output.
- `docs/generated-games/g1-scripted-consensus-log.json`
  - Generated scripted deterministic Consensus Log output.
- `docs/generated-games/g1-scripted-score-log.json`
  - Generated Score Log from the generated Game Log + Decision Log.
- `docs/generated-games/g1-scripted-metrics-summary.json`
  - Generated Metrics Summary from the generated Game Log + Decision Log.
- `docs/demo/phase3-g1-scripted-runtime-demo.html`
  - Runtime demo generated from scripted deterministic outputs with explicit boundary text.

Modify:

- `src/werewolf_eval/decision_log.py`
  - Add `[scripted deterministic output]` to `VALID_SOURCE_LABELS`.
- `src/werewolf_eval/consensus_log.py`
  - Add `[scripted deterministic output]` to `VALID_SOURCE_LABELS`.
- `tests/test_decision_log.py`
  - Cover Decision Log parser acceptance of the new source label.
- `tests/test_consensus_log.py`
  - Cover Consensus Log parser acceptance of the new source label.
- `src/werewolf_eval/scoring.py`
  - Preserve existing g001 canonical outputs and add dynamic generated-game provenance for non-g001 games.
- `tests/test_scoring.py`
  - Cover that generated-game score IDs and summary metadata do not use stale `s2_g001_*` identifiers.
- `src/werewolf_eval/attribution.py`
  - Preserve existing g001 canonical attribution outputs and add dynamic generated-game provenance for non-g001 games.
- `tests/test_attribution.py`
  - Cover non-g001 attribution metadata.
- `src/werewolf_eval/render_demo.py`
  - Render an explicit scripted deterministic G1a boundary when score input is from generated scripted logs.
- `tests/test_render_demo.py`
  - Cover demo boundary text for generated scripted logs.
- `README.md`
  - Update current status to mention only G1a scripted deterministic fresh-log runner after implementation.
- `docs/TASKS.md`
  - Add G1a status and demo acceptance without saying full G1 is complete.
- `.oh-my-harness/tree.md`
  - Refresh after adding files.

No other files should be modified.

---

### 任务 1：G1a.1 source label and scripted scenario contract

**文件：**
- 修改：`src/werewolf_eval/decision_log.py`
- 修改：`src/werewolf_eval/consensus_log.py`
- 修改：`tests/test_decision_log.py`
- 修改：`tests/test_consensus_log.py`
- 创建：`docs/game-scripts/g1-scripted-game.json`
- 创建：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：添加 source label parser tests**

Append Decision Log test:

```python
    def test_accepts_scripted_deterministic_source_label(self) -> None:
        raw = self._minimal_raw()
        raw["source_label"] = "[scripted deterministic output]"
        decision_log = parse_decision_log(raw, self.game)
        self.assertEqual(decision_log.source_label, "[scripted deterministic output]")
```

Append Consensus Log test:

```python
    def test_accepts_scripted_deterministic_source_label(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["source_label"] = "[scripted deterministic output]"
        consensus_log = parse_consensus_log(raw, self.game)
        self.assertEqual(consensus_log.source_label, "[scripted deterministic output]")
```

- [ ] **步骤 2：运行 tests 确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log tests.test_consensus_log -v
```

Expected result before allowlist update:

```text
invalid source_label
FAILED
```

- [ ] **步骤 3：更新 parser source label allowlists**

In `src/werewolf_eval/decision_log.py`:

```python
VALID_SOURCE_LABELS = {"[人工 gold sample]", "[AI 生成]", "[scripted deterministic output]"}
```

In `src/werewolf_eval/consensus_log.py`:

```python
VALID_SOURCE_LABELS = {"[人工 gold sample]", "[AI 生成]", "[scripted deterministic output]"}
```

Do not change any other validation rule in these files.

- [ ] **步骤 4：运行 source label tests**

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log tests.test_consensus_log -v
```

Expected result:

```text
OK
```

- [ ] **步骤 5：创建 scripted scenario fixture test**

Create `tests/test_scripted_game_runner.py`:

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
    def test_script_fixture_exists_and_has_contract_shape(self) -> None:
        path = ROOT / "docs/game-scripts/g1-scripted-game.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["script_id"], "g1_scripted_001")
        self.assertEqual(payload["game_id"], "g1_scripted_001")
        self.assertEqual(payload["source_label"], "[scripted deterministic output]")
        self.assertEqual(len(payload["players"]), 6)
        self.assertEqual(len(payload["steps"]), 15)
        self.assertEqual(payload["result"]["winner"], "villager")

        decision_steps = [step for step in payload["steps"] if "decision_actor" in step]
        self.assertEqual(len(decision_steps), 7)
        self.assertTrue(all(step["decision_source_label"] == "[scripted deterministic output]" for step in decision_steps))

        wolf_kills = [step for step in payload["steps"] if step["type"] == "werewolf_kill"]
        self.assertEqual(len(wolf_kills), 2)
        self.assertTrue(all(step["consensus_source_label"] == "[scripted deterministic output]" for step in wolf_kills))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 6：运行 fixture test 确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameFixtureTests -v
```

Expected result before fixture creation:

```text
FileNotFoundError
FAILED
```

- [ ] **步骤 7：创建 scripted scenario JSON**

Create `docs/game-scripts/g1-scripted-game.json` with this complete content:

```json
{
  "script_id": "g1_scripted_001",
  "game_id": "g1_scripted_001",
  "source_label": "[scripted deterministic output]",
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
    {"step_id": "s002", "round": 1, "phase": "night", "type": "werewolf_kill", "actor": "wolf_team", "target": "p5", "visibility": "werewolf_team", "summary": "Wolf team selects p5 as the first night target.", "decision_actor": "wolf_team", "decision_type": "team_coordinated", "decision_source_label": "[scripted deterministic output]", "reason_summary": "Wolf team selects p5 as a low-information villager target.", "visible_info_refs": ["g1_scripted_001_e001"], "consensus_source_label": "[scripted deterministic output]", "consensus": {"participants": ["p1", "p2"], "coordinator": "p1", "status": "consensus", "primary_proposer": "p1", "supporters": ["p1", "p2"], "dissenters": []}},
    {"step_id": "s003", "round": 1, "phase": "night", "type": "seer_check", "actor": "p3", "target": "p1", "visibility": "seer", "summary": "p3 checks p1 at night.", "decision_actor": "p3", "decision_type": "inference_based", "decision_source_label": "[scripted deterministic output]", "reason_summary": "Seer checks p1 as an early pressure target.", "visible_info_refs": []},
    {"step_id": "s004", "round": 1, "phase": "night", "type": "witch_save", "actor": "p4", "target": "p5", "visibility": "witch", "summary": "p4 saves p5.", "decision_actor": "p4", "decision_type": "inference_based", "decision_source_label": "[scripted deterministic output]", "reason_summary": "Witch saves p5 after seeing the night kill target.", "visible_info_refs": []},
    {"step_id": "s005", "round": 1, "phase": "day", "type": "player_speech", "actor": "p3", "target": "p1", "visibility": "public", "summary": "p3 publicly pressures p1 after the night check."},
    {"step_id": "s006", "round": 1, "phase": "day", "type": "player_vote", "actor": "p4", "target": "p1", "visibility": "public", "summary": "p4 votes p1.", "decision_actor": "p4", "decision_type": "inference_based", "decision_source_label": "[scripted deterministic output]", "reason_summary": "p4 follows p3's pressure and votes p1.", "visible_info_refs": ["g1_scripted_001_e005"]},
    {"step_id": "s007", "round": 1, "phase": "day", "type": "player_vote", "actor": "p5", "target": "p3", "visibility": "public", "summary": "p5 votes p3.", "decision_actor": "p5", "decision_type": "default", "decision_source_label": "[scripted deterministic output]", "reason_summary": "p5 votes p3 because the public claim is not fully proven.", "visible_info_refs": ["g1_scripted_001_e005"]},
    {"step_id": "s008", "round": 1, "phase": "day", "type": "player_eliminated", "actor": "system", "target": "p1", "visibility": "public", "summary": "p1 is eliminated by vote."},
    {"step_id": "s009", "round": 1, "phase": "day", "type": "role_revealed", "actor": "system", "target": "p1", "visibility": "public", "summary": "p1 is revealed as werewolf."},
    {"step_id": "s010", "round": 2, "phase": "night", "type": "werewolf_kill", "actor": "wolf_team", "target": "p3", "visibility": "werewolf_team", "summary": "Remaining wolf kills p3.", "decision_actor": "wolf_team", "decision_type": "team_coordinated", "decision_source_label": "[scripted deterministic output]", "reason_summary": "Remaining wolf targets the confirmed seer p3.", "visible_info_refs": ["g1_scripted_001_e009"], "consensus_source_label": "[scripted deterministic output]", "consensus": {"participants": ["p2"], "coordinator": "p2", "status": "consensus", "primary_proposer": "p2", "supporters": ["p2"], "dissenters": []}},
    {"step_id": "s011", "round": 2, "phase": "night", "type": "player_died", "actor": "system", "target": "p3", "visibility": "public", "summary": "p3 dies at night."},
    {"step_id": "s012", "round": 2, "phase": "day", "type": "player_vote", "actor": "p6", "target": "p2", "visibility": "public", "summary": "p6 votes p2.", "decision_actor": "p6", "decision_type": "inference_based", "decision_source_label": "[scripted deterministic output]", "reason_summary": "p6 votes p2 after p1's reveal and the seer death.", "visible_info_refs": ["g1_scripted_001_e009", "g1_scripted_001_e011"]},
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

- [ ] **步骤 8：运行 task 1 tests**

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log tests.test_consensus_log tests.test_scripted_game_runner.ScriptedGameFixtureTests -v
```

Expected result:

```text
OK
```

- [ ] **步骤 9：提交 task 1**

```bash
git add src/werewolf_eval/decision_log.py src/werewolf_eval/consensus_log.py tests/test_decision_log.py tests/test_consensus_log.py docs/game-scripts/g1-scripted-game.json tests/test_scripted_game_runner.py
git commit -m "test: define G1a scripted source and scenario contract"
```

---

### 任务 2：G1a.2 deterministic runner core

**文件：**
- 创建：`src/werewolf_eval/scripted_game.py`
- 修改：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：添加 runner tests**

Append to `tests/test_scripted_game_runner.py`:

```python
class ScriptedGameRunnerTests(unittest.TestCase):
    def test_runner_emits_valid_log_dicts(self) -> None:
        from werewolf_eval.consensus_log import parse_consensus_log
        from werewolf_eval.decision_log import parse_decision_log
        from werewolf_eval.game_log import parse_game_log
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        outputs = run_scripted_game(script)

        game = parse_game_log(outputs.game_log)
        decision_log = parse_decision_log(outputs.decision_log, game)
        consensus_log = parse_consensus_log(outputs.consensus_log, game)

        self.assertEqual(game.game_id, "g1_scripted_001")
        self.assertEqual(outputs.game_log["source_label"], "[scripted deterministic output]")
        self.assertEqual(decision_log.source_label, "[scripted deterministic output]")
        self.assertEqual(consensus_log.source_label, "[scripted deterministic output]")
        self.assertEqual(len(game.events), 15)
        self.assertEqual(len(decision_log.decisions), 7)
        self.assertEqual(len(consensus_log.consensuses), 2)

    def test_runner_is_deterministic(self) -> None:
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        first = run_scripted_game(script)
        second = run_scripted_game(script)

        self.assertEqual(first.game_log, second.game_log)
        self.assertEqual(first.decision_log, second.decision_log)
        self.assertEqual(first.consensus_log, second.consensus_log)
```

- [ ] **步骤 2：运行 runner tests 确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameRunnerTests -v
```

Expected result before implementation:

```text
ModuleNotFoundError: No module named 'werewolf_eval.scripted_game'
FAILED
```

- [ ] **步骤 3：实现 `scripted_game.py`**

Create `src/werewolf_eval/scripted_game.py` with these public dataclasses and functions:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

SCRIPTED_SOURCE_LABEL = "[scripted deterministic output]"


@dataclass(frozen=True)
class ScriptedGame:
    script_id: str
    game_id: str
    source_label: str
    players: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    result: dict[str, Any]


@dataclass(frozen=True)
class ScriptedGameOutputs:
    game_log: dict[str, Any]
    decision_log: dict[str, Any]
    consensus_log: dict[str, Any]


def load_scripted_game(path: str | Path) -> ScriptedGame:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("scripted game root must be an object")
    required = {"script_id", "game_id", "source_label", "players", "steps", "result"}
    missing = required - set(raw)
    if missing:
        raise ValueError(f"scripted game missing fields: {sorted(missing)}")
    if raw["source_label"] != SCRIPTED_SOURCE_LABEL:
        raise ValueError("scripted game source_label must be [scripted deterministic output]")
    return ScriptedGame(
        script_id=str(raw["script_id"]),
        game_id=str(raw["game_id"]),
        source_label=str(raw["source_label"]),
        players=list(raw["players"]),
        steps=list(raw["steps"]),
        result=dict(raw["result"]),
    )


def _event_id(game_id: str, sequence: int) -> str:
    return f"{game_id}_e{sequence:03d}"


def _decision_id(game_id: str, index: int) -> str:
    return f"{game_id}_d{index:03d}"


def _consensus_id(game_id: str, index: int) -> str:
    return f"{game_id}_c{index:03d}"


def _event_from_step(game_id: str, step: dict[str, Any], sequence: int) -> dict[str, Any]:
    event = {
        "event_id": _event_id(game_id, sequence),
        "sequence": sequence,
        "round": step["round"],
        "phase": step["phase"],
        "type": step["type"],
        "actor": step["actor"],
        "target": step["target"],
        "visibility": step["visibility"],
        "data": {"summary": step["summary"]},
    }
    if "visible_info_refs" in step:
        event["data"]["visible_info_refs"] = list(step["visible_info_refs"])
    return event


def _decision_from_step(game_id: str, step: dict[str, Any], decision_index: int, consensus_id: str | None) -> dict[str, Any]:
    return {
        "decision_id": _decision_id(game_id, decision_index),
        "game_id": game_id,
        "actor": step["decision_actor"],
        "decision_scope": "team" if step["decision_actor"] == "wolf_team" else "single",
        "consensus_id": consensus_id,
        "phase": step["phase"],
        "action": step["type"],
        "target": step["target"],
        "visible_info_refs": list(step.get("visible_info_refs", [])),
        "reason_summary": step["reason_summary"],
        "decision_type": step["decision_type"],
        "confidence": 1.0,
        "strategy_tag": "scripted_deterministic",
    }


def _consensus_from_step(game_id: str, step: dict[str, Any], consensus_index: int) -> dict[str, Any]:
    raw = step["consensus"]
    consensus_id = _consensus_id(game_id, consensus_index)
    primary = raw["primary_proposer"]
    supporters = list(raw["supporters"])
    responses = [
        {
            "response_id": f"{consensus_id}_r{index:03d}",
            "to_proposal_id": f"{consensus_id}_p001",
            "responder": supporter,
            "response_type": "support_with_reason",
            "reason_summary": "Scripted supporter accepts the deterministic target.",
            "visible_info_refs": list(step.get("visible_info_refs", [])),
            "action_round": 1,
        }
        for index, supporter in enumerate(supporters, start=1)
        if supporter != primary
    ]
    return {
        "consensus_id": consensus_id,
        "game_id": game_id,
        "round": step["round"],
        "phase": step["phase"],
        "team": "werewolf",
        "participants": list(raw["participants"]),
        "coordinator": raw["coordinator"],
        "max_rounds": 3,
        "actual_rounds": 1,
        "status": raw["status"],
        "proposals": [
            {
                "proposal_id": f"{consensus_id}_p001",
                "proposer": primary,
                "proposed_target": step["target"],
                "visible_info_refs": list(step.get("visible_info_refs", [])),
                "reason_summary": step["reason_summary"],
                "confidence": 1.0,
                "action_round": 1,
            }
        ],
        "responses": responses,
        "final_decision": {
            "target": step["target"],
            "decision_type": raw["status"],
            "primary_proposer": primary,
            "supporters": supporters,
            "dissenters": list(raw["dissenters"]),
            "resolution_round": 1,
        },
    }


def run_scripted_game(script: ScriptedGame) -> ScriptedGameOutputs:
    events = [_event_from_step(script.game_id, step, sequence) for sequence, step in enumerate(script.steps, start=1)]
    decisions: list[dict[str, Any]] = []
    consensuses: list[dict[str, Any]] = []
    consensus_by_step_id: dict[str, str] = {}

    for step in script.steps:
        if step["type"] == "werewolf_kill" and "consensus" in step:
            consensus = _consensus_from_step(script.game_id, step, len(consensuses) + 1)
            consensuses.append(consensus)
            consensus_by_step_id[step["step_id"]] = consensus["consensus_id"]

    for step in script.steps:
        if "decision_actor" in step:
            decisions.append(
                _decision_from_step(
                    script.game_id,
                    step,
                    len(decisions) + 1,
                    consensus_by_step_id.get(step["step_id"]),
                )
            )

    return ScriptedGameOutputs(
        game_log={
            "game_id": script.game_id,
            "source_label": SCRIPTED_SOURCE_LABEL,
            "players": script.players,
            "events": events,
            "result": script.result,
        },
        decision_log={
            "decision_log_id": f"{script.game_id}_decision_log",
            "game_id": script.game_id,
            "source_label": SCRIPTED_SOURCE_LABEL,
            "decisions": decisions,
        },
        consensus_log={
            "consensus_log_id": f"{script.game_id}_consensus_log",
            "game_id": script.game_id,
            "source_label": SCRIPTED_SOURCE_LABEL,
            "consensuses": consensuses,
        },
    )
```

Implementation notes:

- `run_scripted_game()` must not call scorers, renderers, models, provider adapters, prompt code, or network code.
- Invalid generated logs must fail existing validators. Do not auto-repair invalid generated logs.
- The Game Log top-level `source_label` is artifact provenance; the current Game Log parser may ignore it, but the JSON artifact must retain it.

- [ ] **步骤 4：运行 runner tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameRunnerTests -v
```

Expected result:

```text
OK
```

- [ ] **步骤 5：提交 task 2**

```bash
git add src/werewolf_eval/scripted_game.py tests/test_scripted_game_runner.py
git commit -m "feat: add G1a deterministic scripted runner"
```

---

### 任务 3：G1a.2 deterministic runner CLI and generated logs

**文件：**
- 创建：`src/werewolf_eval/run_scripted_game.py`
- 修改：`tests/test_scripted_game_runner.py`
- 创建：`docs/generated-games/g1-scripted-game-log.json`
- 创建：`docs/generated-games/g1-scripted-decision-log.json`
- 创建：`docs/generated-games/g1-scripted-consensus-log.json`

- [ ] **步骤 1：添加 CLI test**

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
            self.assertEqual(json.loads((out / "decision.json").read_text(encoding="utf-8"))["source_label"], "[scripted deterministic output]")
            self.assertEqual(json.loads((out / "consensus.json").read_text(encoding="utf-8"))["source_label"], "[scripted deterministic output]")
```

- [ ] **步骤 2：运行 CLI test 确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameCliTests -v
```

Expected result before implementation:

```text
No module named werewolf_eval.run_scripted_game
FAILED
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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
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
    print(f"source_label={outputs.game_log['source_label']}")
    print(f"events={len(outputs.game_log['events'])}")
    print(f"decisions={len(outputs.decision_log['decisions'])}")
    print(f"consensuses={len(outputs.consensus_log['consensuses'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 4：生成 canonical generated logs**

```bash
PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out docs/generated-games/g1-scripted-game-log.json --decision-log-out docs/generated-games/g1-scripted-decision-log.json --consensus-log-out docs/generated-games/g1-scripted-consensus-log.json
```

Expected result:

```text
scripted_game_id=g1_scripted_001
source_label=[scripted deterministic output]
events=15
decisions=7
consensuses=2
```

- [ ] **步骤 5：validate generated logs**

Correct CLI argument order is required:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1-scripted-decision-log.json docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1-scripted-consensus-log.json docs/generated-games/g1-scripted-game-log.json
```

Expected result:

```text
validated game_id=g1_scripted_001
validated decision_log_id=g1_scripted_001_decision_log
validated consensus_log_id=g1_scripted_001_consensus_log game_id=g1_scripted_001 consensuses=2 source_label=[scripted deterministic output]
```

- [ ] **步骤 6：运行 CLI tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameCliTests -v
```

Expected result:

```text
OK
```

- [ ] **步骤 7：提交 task 3**

```bash
git add src/werewolf_eval/run_scripted_game.py tests/test_scripted_game_runner.py docs/generated-games/g1-scripted-game-log.json docs/generated-games/g1-scripted-decision-log.json docs/generated-games/g1-scripted-consensus-log.json
git commit -m "feat: add G1a scripted runner CLI"
```

---

### 任务 4：G1a.3 evaluator provenance compatibility

**文件：**
- 修改：`src/werewolf_eval/scoring.py`
- 修改：`tests/test_scoring.py`
- 修改：`src/werewolf_eval/attribution.py`
- 修改：`tests/test_attribution.py`
- 修改：`src/werewolf_eval/render_demo.py`
- 修改：`tests/test_render_demo.py`
- 修改：`tests/test_scripted_game_runner.py`

- [ ] **步骤 1：添加 generated artifact provenance tests**

Append to `tests/test_scripted_game_runner.py`:

```python
class ScriptedGameArtifactProvenanceTests(unittest.TestCase):
    def test_generated_score_and_metrics_use_g1_ids(self) -> None:
        score_path = ROOT / "docs/generated-games/g1-scripted-score-log.json"
        metrics_path = ROOT / "docs/generated-games/g1-scripted-metrics-summary.json"
        score = json.loads(score_path.read_text(encoding="utf-8"))
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        combined = json.dumps({"score": score, "metrics": metrics}, ensure_ascii=False)
        self.assertEqual(score["game_id"], "g1_scripted_001")
        self.assertEqual(metrics["game_id"], "g1_scripted_001")
        self.assertNotIn("s2_g001", combined)
        self.assertNotIn("s5_g001", combined)
        self.assertIn("[scripted deterministic output]", combined)
        self.assertNotIn("[人工 gold sample]", combined)
        self.assertNotIn("[AI 生成]", combined)

    def test_generated_artifacts_are_not_written_to_gold_game(self) -> None:
        generated = sorted((ROOT / "docs/generated-games").glob("g1-scripted-*.json"))
        self.assertGreaterEqual(len(generated), 5)
        gold_names = {path.name for path in (ROOT / "docs/gold-game").glob("g1-scripted-*.json")}
        self.assertEqual(gold_names, set())
```

Append to `tests/test_scoring.py`:

```python
    def test_non_g001_score_log_uses_dynamic_provenance(self) -> None:
        game = load_game_log(ROOT / "docs/generated-games/g1-scripted-game-log.json")
        decision_log = load_decision_log(ROOT / "docs/generated-games/g1-scripted-decision-log.json", game)
        score_log = score_game(game, decision_log=decision_log)
        payload = score_log_to_dict(score_log)

        self.assertEqual(payload["game_id"], "g1_scripted_001")
        self.assertNotIn("s2_g001", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(payload["source_label"], "[scripted deterministic output][decision-log]")
```

Append to `tests/test_render_demo.py`:

```python
    def test_g1a_scripted_demo_boundary(self) -> None:
        game = load_game_log(ROOT / "docs/generated-games/g1-scripted-game-log.json")
        decision_log = load_decision_log(ROOT / "docs/generated-games/g1-scripted-decision-log.json", game)
        score_log = score_game(game, decision_log=decision_log)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
        html = render_html(build_demo_context(game, score_log, metrics, attribution))

        self.assertIn("G1a scripted deterministic fresh-log runner", html)
        self.assertIn("not live AI Agent gameplay", html)
        self.assertIn("[scripted deterministic output]", html)
        self.assertNotIn("real AI Agent gameplay complete", html)
        self.assertNotIn("G1 complete", html)
```

- [ ] **步骤 2：运行 provenance tests 确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring tests.test_render_demo tests.test_scripted_game_runner.ScriptedGameArtifactProvenanceTests -v
```

Expected result before provenance compatibility updates:

```text
FAILED
```

- [ ] **步骤 3：update scoring provenance without changing formulas**

In `src/werewolf_eval/scoring.py`, preserve existing canonical g001 behavior and add dynamic metadata for non-g001 games:

```python
def _score_id_prefix(game: GameLog) -> str:
    if game.game_id == "g001":
        return "s2_g001"
    return f"score_{game.game_id}"


def _score_log_id(game: GameLog, semantic_labels_enabled: bool) -> str:
    if game.game_id == "g001":
        return "s5_g001_expected_score_log" if semantic_labels_enabled else "s2_g001_expected_score_log"
    return f"{game.game_id}_score_log"


def _score_source_label(game: GameLog, decision_log: DecisionLog | None, semantic_labels_enabled: bool) -> str:
    if game.game_id != "g001" and decision_log is not None and decision_log.source_label == "[scripted deterministic output]":
        return "[scripted deterministic output][decision-log]"
    if semantic_labels_enabled:
        return "[deterministic][decision-log][semantic-labels]"
    if decision_log is not None:
        return "[deterministic][decision-log]"
    return "[deterministic]"
```

Update `_record()` to accept `score_id_prefix: str` and use:

```python
score_id=f"{score_id_prefix}_{event.event_id}"
```

Pass `_score_id_prefix(game)` from each scoring call path. Do not change outcome, decision quality, rule integrity, rule triggering, or visibility scoring.

Update `summarize_metrics()` so g001 retains existing IDs and non-g001 uses:

```python
metrics_id=f"{game.game_id}_metrics_summary"
source_game_log=f"generated:{game.game_id}"
source_score_log=f"score_log:{score_log.score_log_id}"
```

- [ ] **步骤 4：update attribution provenance without changing attribution rules**

In `src/werewolf_eval/attribution.py`, preserve existing g001 metadata and use dynamic non-g001 metadata:

```python
def _source_game_log(game: GameLog) -> str:
    return "docs/gold-game/g001-game-log.json" if game.game_id == "g001" else f"generated:{game.game_id}"


def _source_score_log(game: GameLog, score_log: ScoreLog) -> str:
    return "docs/gold-game/s2-score-log.json" if game.game_id == "g001" else f"score_log:{score_log.score_log_id}"


def _source_metrics_summary(game: GameLog, metrics: MetricsSummary) -> str:
    return "docs/gold-game/s2-metrics-summary.json" if game.game_id == "g001" else f"metrics:{metrics.metrics_id}"
```

Use these helpers inside `attribute_game()`. Do not change turn point detection or attribution scoring.

- [ ] **步骤 5：update render demo boundary for G1a scripted artifacts**

In `src/werewolf_eval/render_demo.py`, detect G1a by `score_log.source_label` containing `[scripted deterministic output]`. For G1a context:

```python
boundary_title = "G1a scripted deterministic fresh-log runner"
boundary_text = "This demo is generated from scripted deterministic Game Log / Decision Log / Consensus Log outputs. It is not Agent runtime output, not live AI Agent gameplay, not provider integration, not a Web live observer, and not human-vs-AI UI."
leaderboard_agent_id = f"{game.game_id}-runtime"
leaderboard_model = "scripted deterministic runner"
leaderboard_source_label = "[scripted deterministic output]"
```

For existing g001 demos, preserve current Phase 2 behavior and existing tests.

- [ ] **步骤 6：运行 provenance tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scoring tests.test_attribution tests.test_render_demo -v
```

Expected result:

```text
OK
```

- [ ] **步骤 7：提交 task 4**

```bash
git add src/werewolf_eval/scoring.py tests/test_scoring.py src/werewolf_eval/attribution.py tests/test_attribution.py src/werewolf_eval/render_demo.py tests/test_render_demo.py tests/test_scripted_game_runner.py
git commit -m "fix: add G1a generated artifact provenance"
```

---

### 任务 5：G1a.3 evaluator and demo generated artifacts

**文件：**
- 修改：`tests/test_scripted_game_runner.py`
- 创建：`docs/generated-games/g1-scripted-score-log.json`
- 创建：`docs/generated-games/g1-scripted-metrics-summary.json`
- 创建：`docs/demo/phase3-g1-scripted-runtime-demo.html`

- [ ] **步骤 1：添加 evaluator pipeline test**

Append to `tests/test_scripted_game_runner.py`:

```python
class ScriptedGameEvaluatorPipelineTests(unittest.TestCase):
    def test_generated_logs_can_be_scored_and_rendered(self) -> None:
        from werewolf_eval.attribution import attribute_game
        from werewolf_eval.decision_log import load_decision_log
        from werewolf_eval.game_log import load_game_log
        from werewolf_eval.render_demo import build_demo_context, render_html
        from werewolf_eval.scoring import score_game, score_log_to_dict, summarize_metrics, metrics_summary_to_dict

        game = load_game_log(ROOT / "docs/generated-games/g1-scripted-game-log.json")
        decision_log = load_decision_log(ROOT / "docs/generated-games/g1-scripted-decision-log.json", game)
        score_log = score_game(game, decision_log=decision_log)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
        html = render_html(build_demo_context(game, score_log, metrics, attribution))

        score_payload = score_log_to_dict(score_log)
        metrics_payload = metrics_summary_to_dict(metrics)
        self.assertEqual(score_payload["game_id"], "g1_scripted_001")
        self.assertEqual(metrics_payload["game_id"], "g1_scripted_001")
        self.assertNotIn("s2_g001", json.dumps(score_payload, ensure_ascii=False))
        self.assertNotIn("s2_g001", json.dumps(metrics_payload, ensure_ascii=False))
        self.assertIn("G1a scripted deterministic fresh-log runner", html)
        self.assertIn("not live AI Agent gameplay", html)
        self.assertNotIn("https://", html)
```

- [ ] **步骤 2：运行 pipeline test 确认当前 generated score/demo 缺失**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameEvaluatorPipelineTests -v
```

Expected result before generated score/demo artifacts exist:

```text
FileNotFoundError
FAILED
```

- [ ] **步骤 3：生成 score / metrics outputs**

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

- [ ] **步骤 4：生成 runtime demo HTML**

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --html-out docs/demo/phase3-g1-scripted-runtime-demo.html
```

Expected result:

```text
rendered_demo_html=docs/demo/phase3-g1-scripted-runtime-demo.html
```

- [ ] **步骤 5：运行 artifact provenance tests**

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameArtifactProvenanceTests tests.test_scripted_game_runner.ScriptedGameEvaluatorPipelineTests -v
```

Expected result:

```text
OK
```

- [ ] **步骤 6：提交 task 5**

```bash
git add tests/test_scripted_game_runner.py docs/generated-games/g1-scripted-score-log.json docs/generated-games/g1-scripted-metrics-summary.json docs/demo/phase3-g1-scripted-runtime-demo.html
git commit -m "feat: connect G1a scripted logs to evaluator demo"
```

---

### 任务 6：Status docs, tree, final validation, and Review Packet

**文件：**
- 修改：`README.md`
- 修改：`docs/TASKS.md`
- 修改：`.oh-my-harness/tree.md`

- [ ] **步骤 1：更新 README current status**

Modify the current-status paragraph in `README.md` to include this exact boundary sentence:

```markdown
G1a 已提供 scripted deterministic fresh-log runner，可从 `docs/game-scripts/g1-scripted-game.json` 生成新的 scripted deterministic Game Log / Decision Log / Consensus Log，并通过现有 evaluator pipeline 生成 `docs/demo/phase3-g1-scripted-runtime-demo.html`。这不是 Agent runtime output，不代表 real AI Agent gameplay、provider integration、Web live observer、human-vs-AI UI 或 multi-game Leaderboard 已完成。
```

Do not write “G1 complete” or “real AI Agent gameplay complete”.

- [ ] **步骤 2：更新 TASKS G1 section**

In `docs/TASKS.md`, update G1 status to include G1a:

```markdown
### G1：Real AI Agent gameplay engine

- 状态：`phase_3_candidate`; G1a scripted deterministic fresh-log runner completed after implementation.
- 产出（G1a）：`docs/game-scripts/g1-scripted-game.json` + `src/werewolf_eval/scripted_game.py` + `src/werewolf_eval/run_scripted_game.py` + `docs/generated-games/g1-scripted-game-log.json` + `docs/generated-games/g1-scripted-decision-log.json` + `docs/generated-games/g1-scripted-consensus-log.json` + `docs/generated-games/g1-scripted-score-log.json` + `docs/generated-games/g1-scripted-metrics-summary.json` + `docs/demo/phase3-g1-scripted-runtime-demo.html`。
- 依赖：稳定的 Game Log / Decision Log / Consensus Log / scoring contracts。
- 目标：先以 scripted deterministic fresh-log runner 验证 fresh log generation，再进入后续真实 Agent runtime 设计。
- 边界：G1a 的 Game Log / Decision Log / Consensus Log 是 scripted deterministic output；G1a 不是 Agent runtime output，不接 provider，不调用真实 API，不需要 secrets，不做 network calls，不实现真实狼人协商协议，不实现 live AI gameplay，不实现 Web live observer / human-vs-AI UI，不做 multi-game Leaderboard。
```

Add Demo Acceptance entry:

```markdown
**Demo 7：Phase 3 G1a scripted deterministic fresh-log runner**

- 状态：`completed`（`docs/demo/phase3-g1-scripted-runtime-demo.html`）
- 触发条件：G1a scripted deterministic fresh-log runner 完成。
- 演示内容：scripted scenario JSON → scripted deterministic Game Log / Decision Log / Consensus Log → Score Log / Metrics Summary → Runtime HTML Demo。
- 验收：同一 script 两次生成完全一致；三个 generated logs 均通过现有 validators；generated score log / metrics summary 的 `game_id` 是 `g1_scripted_001` 且不残留 `s2_g001_*`；页面明确标注 scripted deterministic boundary，并明确不代表 live AI Agent gameplay。
```

- [ ] **步骤 3：运行 final validation commands**

Correct CLI argument order is required for Decision Log and Consensus Log:

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner tests.test_decision_log tests.test_consensus_log tests.test_scoring tests.test_attribution tests.test_render_demo -v
PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out docs/generated-games/g1-scripted-game-log.json --decision-log-out docs/generated-games/g1-scripted-decision-log.json --consensus-log-out docs/generated-games/g1-scripted-consensus-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1-scripted-decision-log.json docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1-scripted-consensus-log.json docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --score-log-out docs/generated-games/g1-scripted-score-log.json --metrics-out docs/generated-games/g1-scripted-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --html-out docs/demo/phase3-g1-scripted-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
```

Expected result:

```text
unit tests: OK
run_scripted_game: events=15 decisions=7 consensuses=2
validate_game_log: validated game_id=g1_scripted_001
validate_decision_log: validated decision_log_id=g1_scripted_001_decision_log
validate_consensus_log: validated consensus_log_id=g1_scripted_001_consensus_log game_id=g1_scripted_001 consensuses=2 source_label=[scripted deterministic output]
score_game: scored game_id=g1_scripted_001
render_demo: rendered_demo_html=docs/demo/phase3-g1-scripted-runtime-demo.html
validate_brief: ok=true
git diff --check: no output
```

- [ ] **步骤 4：验证 no stale generated provenance**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner.ScriptedGameArtifactProvenanceTests tests.test_render_demo.RuntimeDemoRenderTests -v
```

Expected result:

```text
OK
```

The `tests.test_render_demo.RuntimeDemoRenderTests` suite must include the G1a scripted demo boundary assertions from task 4 before this command is run.

- [ ] **步骤 5：刷新 tree**

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md updated
```

If the hook prints a different success line but updates `.oh-my-harness/tree.md`, record that exact output in the PR body.

- [ ] **步骤 6：生成 Review Packet**

Run the command from the “Review Packet Requirements” section after replacing test summaries and risk notes with the exact commands and evidence from this implementation.

Required output:

```text
wrote .logs/review/latest/review-packet.md
```

Before requesting Codex review, confirm:

```bash
test -f .logs/review/latest/review-packet.md
```

Expected result:

```text
no output
```

- [ ] **步骤 7：提交 task 6**

```bash
git add README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: update G1a scripted runner status"
```

Do not commit `.logs/review/latest/review-packet.md` unless the repository owner explicitly requests committing review packets.

## Self-review Checklist

- G1a is described as scripted deterministic fresh-log generation only.
- G1a does not claim full G1 completion.
- G1a does not claim real AI Agent gameplay completion.
- G1a generated Game Log / Decision Log / Consensus Log use `[scripted deterministic output]`.
- Generated logs are not labeled `[人工 gold sample]`.
- Generated logs are not labeled `[AI 生成]`.
- No provider API calls, network calls, SDK additions, dependency additions, secrets, env requirements, live AI reasoning, prompt execution, stochastic gameplay, Agent runtime abstraction, mock-agent abstraction, live observer, human-vs-AI UI, or multi-game Leaderboard were added.
- No canonical `docs/gold-game/g001-*` fixture was changed.
- Scoring formula behavior is unchanged; only generated-artifact provenance is adjusted.
- Generated Score Log and Metrics Summary have `game_id=g1_scripted_001`.
- Generated artifacts do not contain stale `s2_g001_*` or `s5_g001_*` identifiers.
- Generated demo explicitly says it is not live AI Agent gameplay.
- `.logs/review/latest/review-packet.md` exists before Codex implementation review.

## Implementation PR Description Draft

Title:

```text
feat: add G1a scripted deterministic fresh-log runner
```

Body:

```markdown
## Summary

Add G1a scripted deterministic fresh-log runner as the first Phase 3 / G-track implementation slice.

Bound plan: `docs/harness/plans/2026-05-31--g1-scripted-game-runner-plan.md`

This PR does not complete G1 real AI Agent gameplay. The generated Game Log / Decision Log / Consensus Log are scripted deterministic outputs, not Agent runtime output.

## Changes

- Add scripted scenario fixture at `docs/game-scripts/g1-scripted-game.json`.
- Add `[scripted deterministic output]` provenance support for generated Decision Log and Consensus Log artifacts.
- Add deterministic runner and CLI.
- Generate fresh scripted deterministic Game Log / Decision Log / Consensus Log under `docs/generated-games/`.
- Validate generated logs with existing validators.
- Add generated Score Log / Metrics Summary with `game_id=g1_scripted_001` and no stale `s2_g001_*` identifiers.
- Add `docs/demo/phase3-g1-scripted-runtime-demo.html` with explicit scripted deterministic boundary text.
- Update README / TASKS status and refresh tree.

## Boundaries

- No provider API calls.
- No network calls.
- No SDK or dependency additions.
- No secrets or environment-variable requirements.
- No live AI reasoning.
- No prompt execution.
- No stochastic gameplay.
- No Agent runtime or mock-agent abstraction.
- No real wolf consensus protocol.
- No Web live observer.
- No human-vs-AI UI.
- No multi-game Leaderboard.
- No canonical `docs/gold-game/g001-*` fixture edits.
- No scoring formula changes.
- No automatic repair of invalid generated logs.

## Validation

```bash
PYTHONPATH=src python -m unittest tests.test_scripted_game_runner tests.test_decision_log tests.test_consensus_log tests.test_scoring tests.test_attribution tests.test_render_demo -v
PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json --game-log-out docs/generated-games/g1-scripted-game-log.json --decision-log-out docs/generated-games/g1-scripted-decision-log.json --consensus-log-out docs/generated-games/g1-scripted-consensus-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1-scripted-decision-log.json docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1-scripted-consensus-log.json docs/generated-games/g1-scripted-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --score-log-out docs/generated-games/g1-scripted-score-log.json --metrics-out docs/generated-games/g1-scripted-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1-scripted-game-log.json --decision-log docs/generated-games/g1-scripted-decision-log.json --html-out docs/demo/phase3-g1-scripted-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md
```

The implementation PR must state that the actual Review Packet was generated with the full allowlist, test-command, acceptance, and risk-note arguments listed in the bound plan's "Review Packet Requirements" section.

## Review Packet

Generated for Codex A档:

```text
.logs/review/latest/review-packet.md
```

No Review Packet means no Codex implementation review.

## Risk Notes

- This PR may change more than 8 files.
- `docs/demo/**` and `docs/generated-games/**` are expected to change.
- Source label / provenance compatibility changes may require Codex B档 deep review.
- No provider, network, dependency, env, or live AI runtime capability is intentionally added.
```
