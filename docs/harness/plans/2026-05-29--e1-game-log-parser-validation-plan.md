# E1 Game Log Parser and Validation Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Implement the first Phase 2 runtime unit: a minimal Game Log parser / validator that loads `docs/gold-game/g001-game-log.json`, validates Phase 2 input invariants, and exposes a reusable typed in-memory representation for E2 deterministic scorer work.

**Architecture:** This PR introduces the smallest runtime code surface needed after Phase 1 closure. It creates a Python standard-library parser module, a CLI validation entry, and unit tests against the existing Gold Game artifact. It does not implement scoring, attribution, UI, game engine, Agent gameplay, AI annotation, or external dependencies.

**Tech Stack:** Python standard library only. No package manager, no external dependency, no backend/frontend framework.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before executing this plan, confirm the repository facts:

- Phase 1 deterministic MVP has been closed by PR #10.
- S0/S1/S2/S3/S6 are completed.
- S4/S5 are deferred to Phase 2.
- E1-E4 are Phase 2 candidate engineering tasks.
- E1 dependency is satisfied because S0 and S1 are complete.
- Phase 2 runtime code is allowed only with a clear Implementation Plan and explicit test constraints.

Therefore the next implementation unit is E1: Game Log parser and validator.

## Research PR Decision

No Research PR is needed.

Reasoning:

- The task boundary is clear.
- The input file is fixed: `docs/gold-game/g001-game-log.json`.
- The expected E1 responsibility is already defined: read structured Game Log JSON, validate schema, convert to internal data structure.
- Known non-goals are clear: no scorer, no attribution engine, no UI, no Agent runtime.
- The first implementation can be dependency-free and reversible.

## Scope Decision

This PR should introduce only the parser / validator layer.

It creates:

- A runtime package under `src/werewolf_eval/`.
- A Game Log parser module.
- A CLI validator module.
- Unit tests for valid and invalid Game Log cases.
- Minimal `AGENTS.md` test-command update because Phase 2 introduces code.
- `docs/TASKS.md` status update for E1 after implementation.

It does not create:

- Scoring logic.
- Attribution logic.
- Frontend or backend app.
- Game engine.
- AI Agent gameplay.
- Consensus Log runtime.
- Decision Log runtime.
- AI semantic annotation.
- Package manager files or dependency manifests.

## Files

- Create: `src/werewolf_eval/__init__.py`
- Create: `src/werewolf_eval/game_log.py`
- Create: `src/werewolf_eval/validate_game_log.py`
- Create: `tests/test_game_log.py`
- Modify: `AGENTS.md`
- Modify: `docs/TASKS.md`
- Do not modify: `docs/EVALUATION_RUBRIC.md`
- Do not modify: `docs/gold-game/g001-game-log.json`
- Do not modify: `docs/gold-game/s2-score-log.json`
- Do not modify: `docs/gold-game/s2-metrics-summary.json`
- Do not modify: `docs/gold-game/s3-rule-attribution.json`
- Do not modify: `docs/demo/phase1-gold-demo.html`
- Test files: `tests/test_game_log.py`

## Hard Boundaries

- Do not create `apps/`, `server/`, or `web`.
- Do not create `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `pyproject.toml`, `requirements.txt`, or dependency configuration.
- Do not implement E2 deterministic scorer.
- Do not implement E3 attribution engine.
- Do not implement E4 runtime UI.
- Do not compute `outcome_score`, `rule_integrity_score`, or `decision_quality_score`.
- Do not infer hidden strategy or psychology.
- Do not call AI models.
- Do not change accepted Phase 1 artifacts.
- Do not claim real `decision_quality_score`, real Consensus Log, real Decision Log, or real Leaderboard exists.

---

### Task 1: Preflight repository state and E1 boundary

**Files:**

- Create: none.
- Modify: none.
- Test file: none.

- [ ] **Step 1: Verify recent PR facts**

Run:

```bash
gh pr list --state merged --limit 10
```

Expected result includes:

```text
#10 Close Phase 1 MVP, align Phase 2 routing
#9 Add S6 Leaderboard UI Demo Validation
#7 Add S3 Rule Attribution Validation
#6 Add S2 Deterministic Scorer Validation
#4 Add S1 Game Log Schema Validation
#2 Add S0 Gold Game Seed
```

- [ ] **Step 2: Verify required input artifacts exist**

Run:

```bash
test -f docs/gold-game/g001-game-log.json
test -f docs/gold-game/s1-schema-validation.md
test -f docs/gold-game/s2-score-log.json
test -f docs/gold-game/s2-metrics-summary.json
test -f docs/gold-game/s3-rule-attribution.json
test -f docs/demo/phase1-gold-demo.html
printf 'E1 input artifacts exist\n'
```

Expected result:

```text
E1 input artifacts exist
```

- [ ] **Step 3: Verify accepted JSON artifacts still parse**

Run:

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
printf 'Accepted JSON artifacts parse\n'
```

Expected result:

```text
Accepted JSON artifacts parse
```

No commit is required for Task 1.

---

### Task 2: Add Game Log parser module

**Files:**

- Create: `src/werewolf_eval/__init__.py`
- Create: `src/werewolf_eval/game_log.py`
- Modify: none.
- Test file: `tests/test_game_log.py` in Task 3.

- [ ] **Step 1: Create package directory**

Run:

```bash
mkdir -p src/werewolf_eval
cat > src/werewolf_eval/__init__.py <<'PY'
"""Werewolf-agent Phase 2 runtime evaluation utilities."""
PY
```

Expected result:

```text
```

No output.

- [ ] **Step 2: Create parser implementation**

Create `src/werewolf_eval/game_log.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


VALID_PHASES = {"setup", "night", "day", "game_end"}
VALID_VISIBILITIES = {
    "public",
    "all",
    "werewolf_team",
    "seer",
    "witch",
    "hunter",
    "specific_player_ids",
}


@dataclass(frozen=True)
class Player:
    player_id: str
    role: str
    team: str


@dataclass(frozen=True)
class Event:
    event_id: str
    sequence: int
    round: int
    phase: str
    type: str
    actor: str
    target: str
    visibility: str
    data: dict[str, Any]


@dataclass(frozen=True)
class GameResult:
    winner: str
    end_round: int
    survivors: list[str]
    end_condition: str


@dataclass(frozen=True)
class GameLog:
    game_id: str
    players: list[Player]
    events: list[Event]
    result: GameResult

    @property
    def player_ids(self) -> set[str]:
        return {player.player_id for player in self.players}

    @property
    def event_ids(self) -> set[str]:
        return {event.event_id for event in self.events}

    def event_by_id(self, event_id: str) -> Event:
        for event in self.events:
            if event.event_id == event_id:
                return event
        raise GameLogValidationError(f"unknown event_id: {event_id}")


class GameLogValidationError(ValueError):
    """Raised when a Game Log cannot be accepted as a Phase 2 runtime input."""


def load_game_log(path: str | Path) -> GameLog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GameLogValidationError("Game Log root must be an object")
    return parse_game_log(raw)


def parse_game_log(raw: dict[str, Any]) -> GameLog:
    required_top_level = {"game_id", "players", "events", "result"}
    missing = required_top_level - set(raw)
    if missing:
        raise GameLogValidationError(f"missing top-level fields: {sorted(missing)}")

    players = [_parse_player(player) for player in raw["players"]]
    events = [_parse_event(event) for event in raw["events"]]
    result = _parse_result(raw["result"])

    game = GameLog(
        game_id=str(raw["game_id"]),
        players=players,
        events=events,
        result=result,
    )
    validate_game_log(game)
    return game


def validate_game_log(game: GameLog) -> None:
    if not game.game_id:
        raise GameLogValidationError("game_id must not be empty")

    if len(game.players) != 6:
        raise GameLogValidationError(f"expected 6 players, got {len(game.players)}")

    player_ids = [player.player_id for player in game.players]
    if len(set(player_ids)) != len(player_ids):
        raise GameLogValidationError("player_id values must be unique")

    if len(game.events) == 0:
        raise GameLogValidationError("events must not be empty")

    sequences = [event.sequence for event in game.events]
    expected_sequences = list(range(1, len(game.events) + 1))
    if sequences != expected_sequences:
        raise GameLogValidationError("event sequence must be continuous from 1 to N")

    event_ids = [event.event_id for event in game.events]
    if len(set(event_ids)) != len(event_ids):
        raise GameLogValidationError("event_id values must be unique")

    known_players = set(player_ids)
    known_events = set(event_ids)

    for event in game.events:
        _validate_event(event, known_players, known_events)

    if game.result.winner not in {"villager", "werewolf"}:
        raise GameLogValidationError(f"invalid winner: {game.result.winner!r}")

    unknown_survivors = set(game.result.survivors) - known_players
    if unknown_survivors:
        raise GameLogValidationError(
            f"result.survivors contains unknown players: {sorted(unknown_survivors)}"
        )


def _parse_player(raw: Any) -> Player:
    if not isinstance(raw, dict):
        raise GameLogValidationError("player entries must be objects")
    for field in ["player_id", "role", "team"]:
        if field not in raw:
            raise GameLogValidationError(f"player missing field: {field}")
    return Player(
        player_id=str(raw["player_id"]),
        role=str(raw["role"]),
        team=str(raw["team"]),
    )


def _parse_event(raw: Any) -> Event:
    if not isinstance(raw, dict):
        raise GameLogValidationError("event entries must be objects")
    for field in ["event_id", "sequence", "round", "phase", "type", "actor", "target", "visibility"]:
        if field not in raw:
            raise GameLogValidationError(f"event missing field: {field}")
    data = raw.get("data", {})
    if not isinstance(data, dict):
        raise GameLogValidationError(f"{raw.get('event_id', '<unknown>')}: data must be an object")
    return Event(
        event_id=str(raw["event_id"]),
        sequence=int(raw["sequence"]),
        round=int(raw["round"]),
        phase=str(raw["phase"]),
        type=str(raw["type"]),
        actor=str(raw["actor"]),
        target=str(raw["target"]),
        visibility=str(raw["visibility"]),
        data=data,
    )


def _parse_result(raw: Any) -> GameResult:
    if not isinstance(raw, dict):
        raise GameLogValidationError("result must be an object")
    for field in ["winner", "end_round", "survivors", "end_condition"]:
        if field not in raw:
            raise GameLogValidationError(f"result missing field: {field}")
    if not isinstance(raw["survivors"], list):
        raise GameLogValidationError("result.survivors must be a list")
    return GameResult(
        winner=str(raw["winner"]),
        end_round=int(raw["end_round"]),
        survivors=[str(player_id) for player_id in raw["survivors"]],
        end_condition=str(raw["end_condition"]),
    )


def _validate_event(event: Event, known_players: set[str], known_events: set[str]) -> None:
    if not event.event_id:
        raise GameLogValidationError("event_id must not be empty")

    if event.phase not in VALID_PHASES:
        raise GameLogValidationError(f"{event.event_id}: invalid phase {event.phase!r}")

    if event.visibility not in VALID_VISIBILITIES:
        raise GameLogValidationError(f"{event.event_id}: invalid visibility {event.visibility!r}")

    if event.actor not in known_players and event.actor not in {"system", "wolf_team"}:
        raise GameLogValidationError(f"{event.event_id}: unknown actor {event.actor!r}")

    if (
        event.target not in known_players
        and event.target not in {"villager_team", "werewolf_team", "none"}
    ):
        raise GameLogValidationError(f"{event.event_id}: unknown target {event.target!r}")

    if "summary" not in event.data:
        raise GameLogValidationError(f"{event.event_id}: data.summary is required")

    visible_info_refs = event.data.get("visible_info_refs", [])
    if visible_info_refs:
        if not isinstance(visible_info_refs, list):
            raise GameLogValidationError(f"{event.event_id}: data.visible_info_refs must be a list")
        unknown_refs = set(visible_info_refs) - known_events
        if unknown_refs:
            raise GameLogValidationError(
                f"{event.event_id}: data.visible_info_refs contains unknown refs: {sorted(unknown_refs)}"
            )
```

- [ ] **Step 3: Run a direct parser smoke check**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from werewolf_eval.game_log import load_game_log

game = load_game_log("docs/gold-game/g001-game-log.json")
assert game.game_id == "g001"
assert len(game.players) == 6
assert len(game.events) == 38
assert game.result.winner == "villager"
assert game.event_by_id("g001_e038").type == "game_over"
print("Game Log parser smoke check passed")
PY
```

Expected result:

```text
Game Log parser smoke check passed
```

- [ ] **Step 4: Commit parser module**

Run:

```bash
git add src/werewolf_eval/__init__.py src/werewolf_eval/game_log.py
git commit -m "feat: add phase2 game log parser"
```

Expected result:

```text
[task/e1-game-log-parser ...] feat: add phase2 game log parser
```

The exact commit hash may differ.

---

### Task 3: Add parser tests

**Files:**

- Create: `tests/test_game_log.py`
- Modify: none.
- Test file: `tests/test_game_log.py`

- [ ] **Step 1: Create unit tests**

Create `tests/test_game_log.py` with:

```python
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.game_log import GameLogValidationError, load_game_log, parse_game_log


def load_raw_gold_game() -> dict:
    return json.loads((ROOT / "docs/gold-game/g001-game-log.json").read_text(encoding="utf-8"))


class GameLogParserTests(unittest.TestCase):
    def test_loads_gold_game(self) -> None:
        game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")

        self.assertEqual(game.game_id, "g001")
        self.assertEqual(len(game.players), 6)
        self.assertEqual(len(game.events), 38)
        self.assertEqual(game.events[0].event_id, "g001_e001")
        self.assertEqual(game.events[-1].type, "game_over")
        self.assertEqual(game.result.winner, "villager")
        self.assertEqual(game.result.survivors, ["p4", "p6"])

    def test_rejects_duplicate_event_id(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][1] = copy.deepcopy(raw["events"][1])
        raw["events"][1]["event_id"] = raw["events"][0]["event_id"]

        with self.assertRaisesRegex(GameLogValidationError, "event_id values must be unique"):
            parse_game_log(raw)

    def test_rejects_non_continuous_sequence(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][1] = copy.deepcopy(raw["events"][1])
        raw["events"][1]["sequence"] = 99

        with self.assertRaisesRegex(GameLogValidationError, "event sequence must be continuous"):
            parse_game_log(raw)

    def test_rejects_unknown_survivor(self) -> None:
        raw = load_raw_gold_game()
        raw["result"] = copy.deepcopy(raw["result"])
        raw["result"]["survivors"] = ["p999"]

        with self.assertRaisesRegex(GameLogValidationError, "unknown players"):
            parse_game_log(raw)

    def test_rejects_invalid_visibility(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][0] = copy.deepcopy(raw["events"][0])
        raw["events"][0]["visibility"] = "secret_table"

        with self.assertRaisesRegex(GameLogValidationError, "invalid visibility"):
            parse_game_log(raw)

    def test_rejects_unknown_visible_info_ref(self) -> None:
        raw = load_raw_gold_game()
        raw["events"][24] = copy.deepcopy(raw["events"][24])
        raw["events"][24]["data"] = copy.deepcopy(raw["events"][24]["data"])
        raw["events"][24]["data"]["visible_info_refs"] = ["g001_e999"]

        with self.assertRaisesRegex(GameLogValidationError, "unknown refs"):
            parse_game_log(raw)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result includes:

```text
Ran 6 tests
OK
```

- [ ] **Step 3: Commit parser tests**

Run:

```bash
git add tests/test_game_log.py
git commit -m "test: cover game log parser validation"
```

Expected result:

```text
[task/e1-game-log-parser ...] test: cover game log parser validation
```

The exact commit hash may differ.

---

### Task 4: Add CLI validation entry

**Files:**

- Create: `src/werewolf_eval/validate_game_log.py`
- Modify: none.
- Test file: `tests/test_game_log.py`

- [ ] **Step 1: Create CLI module**

Create `src/werewolf_eval/validate_game_log.py` with:

```python
from __future__ import annotations

import argparse

from werewolf_eval.game_log import load_game_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Game Log JSON file.")
    parser.add_argument("path", help="Path to Game Log JSON")
    args = parser.parse_args()

    game = load_game_log(args.path)

    print(f"validated game_id={game.game_id}")
    print(f"players={len(game.players)}")
    print(f"events={len(game.events)}")
    print(f"winner={game.result.winner}")
    print(f"end_round={game.result.end_round}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run CLI against Gold Game**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
```

Expected result:

```text
validated game_id=g001
players=6
events=38
winner=villager
end_round=2
```

- [ ] **Step 3: Run tests again**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result includes:

```text
Ran 6 tests
OK
```

- [ ] **Step 4: Commit CLI module**

Run:

```bash
git add src/werewolf_eval/validate_game_log.py
git commit -m "feat: add game log validation cli"
```

Expected result:

```text
[task/e1-game-log-parser ...] feat: add game log validation cli
```

The exact commit hash may differ.

---

### Task 5: Update Phase 2 test constraints and E1 task status

**Files:**

- Create: none.
- Modify: `AGENTS.md`
- Modify: `docs/TASKS.md`
- Test file: none; use Python text validation.

- [ ] **Step 1: Update `AGENTS.md` command section**

In `AGENTS.md`, update the command section so Phase 2 has explicit validation commands.

Replace the current command block:

```md
## 命令

- 非显然的 build 命令：暂无（Phase 1 文档阶段）。
- 非显然的 test 命令：暂无。
- 非显然的 lint / format / typecheck 命令：暂无。
```

with:

```md
## 命令

- 非显然的 build 命令：暂无。
- 非显然的 test 命令：`PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`。
- Game Log 校验命令：`PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json`。
- 非显然的 lint / format / typecheck 命令：暂无。
```

- [ ] **Step 2: Update `AGENTS.md` code/test boundary**

In `AGENTS.md`, replace:

```md
- 生成代码目录：暂无（Phase 1 文档阶段）。
```

with:

```md
- 生成代码目录：`src/werewolf_eval/`。
```

Replace:

```md
- Phase 2 引入代码前必须有明确的 Phase 2 Implementation Plan，并更新对应测试约束。
```

with:

```md
- Phase 2 运行时代码必须绑定 Implementation Plan；当前允许的最小代码入口是 E1 Game Log parser / validator。
```

Replace:

```md
- Phase 2 引入代码后，测试约束见届时更新的 AGENTS.md。
```

with:

```md
- Phase 2 当前测试约束：所有运行时代码变更必须通过 `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`。
- 涉及 Game Log 输入契约时，必须同时通过 `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json`。
```

- [ ] **Step 3: Update `docs/TASKS.md` E1 status**

In `docs/TASKS.md`, update E1 from:

```md
- 状态：`phase_2_candidate`（S0/S1 已满足；等待 Phase 2 实现边界打开）
```

to:

```md
- 状态：`completed`（Phase 2 E1 runtime entry；Game Log parser / validator 已实现）
- 产出：`src/werewolf_eval/game_log.py` + `src/werewolf_eval/validate_game_log.py` + `tests/test_game_log.py`。
```

Update E2 status from:

```md
- 状态：`phase_2_candidate`（S2 已满足；等待 E1 与 Phase 2 实现边界）
```

to:

```md
- 状态：`phase_2_candidate`（S2 已满足；E1 完成后可准备独立 Implementation Plan）
```

Do not mark E2 started.

- [ ] **Step 4: Validate doc updates**

Run:

```bash
python - <<'PY'
from pathlib import Path

agents = Path("AGENTS.md").read_text(encoding="utf-8")
tasks = Path("docs/TASKS.md").read_text(encoding="utf-8")

required_agents = [
    "PYTHONPATH=src python -m unittest discover -s tests -p \"test_*.py\"",
    "PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json",
    "生成代码目录：`src/werewolf_eval/`",
    "当前允许的最小代码入口是 E1 Game Log parser / validator",
]

required_tasks = [
    "E1：Game Log 解析器",
    "状态：`completed`（Phase 2 E1 runtime entry；Game Log parser / validator 已实现）",
    "src/werewolf_eval/game_log.py",
    "E2：确定性评分器",
    "E1 完成后可准备独立 Implementation Plan",
]

missing_agents = [item for item in required_agents if item not in agents]
missing_tasks = [item for item in required_tasks if item not in tasks]

assert not missing_agents, missing_agents
assert not missing_tasks, missing_tasks

print("E1 docs and test constraints validated")
PY
```

Expected result:

```text
E1 docs and test constraints validated
```

- [ ] **Step 5: Commit doc updates**

Run:

```bash
git add AGENTS.md docs/TASKS.md
git commit -m "docs: record phase2 e1 test boundary"
```

Expected result:

```text
[task/e1-game-log-parser ...] docs: record phase2 e1 test boundary
```

The exact commit hash may differ.

---

### Task 6: Final validation and PR preparation

**Files:**

- Create: none.
- Modify: none after previous tasks.
- Test file: `tests/test_game_log.py`

- [ ] **Step 1: Run final JSON parse checks**

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

- [ ] **Step 2: Run E1 CLI validation**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
```

Expected result:

```text
validated game_id=g001
players=6
events=38
winner=villager
end_round=2
```

- [ ] **Step 3: Run unit tests**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result includes:

```text
Ran 6 tests
OK
```

- [ ] **Step 4: Verify no dependency or app framework files were introduced**

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

- [ ] **Step 5: Verify changed files**

Run:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
AGENTS.md
docs/TASKS.md
src/werewolf_eval/__init__.py
src/werewolf_eval/game_log.py
src/werewolf_eval/validate_game_log.py
tests/test_game_log.py
```

If `.oh-my-harness/tree.md` changes because a repository hook refreshes it, include it only if it accurately reflects the new tracked files. Do not manually edit `.oh-my-harness/tree.md`.

- [ ] **Step 6: Check whitespace**

Run:

```bash
git diff --check main...HEAD
```

Expected result:

```text
```

No output means no whitespace errors.

- [ ] **Step 7: Prepare Implementation PR description**

Use this PR description:

```md
## Summary

Adds the Phase 2 E1 Game Log parser / validator as the first minimal runtime code unit.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--e1-game-log-parser-validation-plan.md`

## Scope

- Adds a Python standard-library Game Log parser under `src/werewolf_eval/`.
- Adds a CLI validator for `docs/gold-game/g001-game-log.json`.
- Adds unit tests for valid Gold Game loading and invalid Game Log rejection cases.
- Updates AGENTS.md with Phase 2 test commands and runtime code boundary.
- Marks E1 completed in `docs/TASKS.md`.
- Leaves E2 as the next independent Phase 2 candidate task.

## Out of Scope

- No deterministic scorer.
- No rule attribution engine.
- No runtime UI.
- No backend or frontend app.
- No game engine.
- No Agent gameplay.
- No AI semantic annotation.
- No Consensus Log or Decision Log runtime implementation.
- No external dependencies or dependency manifests.
- No changes to `docs/EVALUATION_RUBRIC.md`.
- No changes to accepted `docs/gold-game/*` or `docs/demo/phase1-gold-demo.html`.

## Validation

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected changed files:

```text
AGENTS.md
docs/TASKS.md
src/werewolf_eval/__init__.py
src/werewolf_eval/game_log.py
src/werewolf_eval/validate_game_log.py
tests/test_game_log.py
```

## Risk

The main risk is scope creep from parser validation into scoring. This PR intentionally stops at Game Log loading and structural validation. E2 deterministic scoring should be a separate Implementation Plan and PR after E1 is merged.
```

- [ ] **Step 8: Final status check**

Run:

```bash
git status --short
```

Expected result after all commits:

```text
```

No output means the working tree is clean.
