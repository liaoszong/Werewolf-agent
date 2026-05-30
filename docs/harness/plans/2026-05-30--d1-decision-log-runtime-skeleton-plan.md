# D1 Decision Log Runtime Skeleton Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a Phase 2 Decision Log runtime input layer with parser, validator, CLI, tests, and one artificial gold fixture, without enabling `decision_quality_score` scoring yet.

**Architecture:** Introduce a focused `decision_log.py` module that mirrors the current `game_log.py` pattern: frozen dataclasses, `load_*`, `parse_*`, and `validate_*` functions. The validator accepts a Decision Log only when it matches an already-valid Game Log and all `visible_info_refs` point to known Game Log events. A small CLI module exposes the validation entry point for local checks and future scoring integration.

**Tech Stack:** Python standard library only. Existing `unittest` style. No external dependencies, no AI model calls, no backend, no frontend framework.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Basis

Main facts before D1:

- PR #16 is merged into `main`.
- E1/E2/E3/E4 runtime entries are complete.
- Current runtime files include:
  - `src/werewolf_eval/game_log.py`
  - `src/werewolf_eval/validate_game_log.py`
  - `src/werewolf_eval/scoring.py`
  - `src/werewolf_eval/score_game.py`
  - `src/werewolf_eval/attribution.py`
  - `src/werewolf_eval/attribute_game.py`
  - `src/werewolf_eval/render_demo.py`
- Current tests include:
  - `tests/test_game_log.py`
  - `tests/test_scoring.py`
  - `tests/test_attribution.py`
  - `tests/test_render_demo.py`
- Current demo outputs include:
  - `docs/demo/phase1-gold-demo.html`
  - `docs/demo/phase2-runtime-demo.html`
- `decision_quality_score` is still fixed at 0 because there is no runtime Decision Log input layer.

## Research PR Decision

No Research PR is needed.

Reasoning:

- The task boundary is clear: implement only the Decision Log runtime schema/parser/validator/CLI/fixture.
- The source schema already exists in `docs/EVALUATION_RUBRIC.md` section B.3.
- The current runtime pattern is established by E1 `game_log.py` and `validate_game_log.py`.
- This task is one implementation unit and does not require model/provider evaluation.
- S5 AI semantic labeling remains outside this plan because it requires accuracy, consistency, and token-cost validation.

## Scope Decision

This Implementation PR implements only D1: Decision Log runtime skeleton.

It creates:

- `src/werewolf_eval/decision_log.py`
- `src/werewolf_eval/validate_decision_log.py`
- `tests/test_decision_log.py`
- `docs/gold-game/g001-decision-log.json`

It modifies:

- `AGENTS.md`
- `README.md`
- `docs/TASKS.md`
- `.oh-my-harness/tree.md`

It does not modify:

- `src/werewolf_eval/scoring.py`
- `src/werewolf_eval/score_game.py`
- `src/werewolf_eval/attribution.py`
- `src/werewolf_eval/attribute_game.py`
- `src/werewolf_eval/render_demo.py`
- `docs/EVALUATION_RUBRIC.md`
- `docs/gold-game/g001-game-log.json`
- `docs/gold-game/s2-score-log.json`
- `docs/gold-game/s2-metrics-summary.json`
- `docs/gold-game/s3-rule-attribution.json`
- `docs/demo/phase1-gold-demo.html`
- `docs/demo/phase2-runtime-demo.html`

It does not create:

- backend/server code
- frontend app code
- AI provider adapters
- Consensus Log runtime code
- scoring integration for `decision_quality_score`

## Runtime Boundary

D1 must keep these boundaries explicit:

- No AI model call.
- No S5 AI semantic labeling.
- No Consensus Log runtime.
- No real AI Agent gameplay.
- No change to deterministic scoring output.
- No claim that `decision_quality_score` is fully usable.
- The new fixture is `[人工 gold sample]`, not `[AI 生成]`.
- `decision_quality_score` remains 0 until a separate scoring integration task is planned and implemented.

---

### Task 1: Preflight current runtime baseline

**Files:**

- Create: none.
- Modify: none.
- Test: existing runtime commands and existing test suite.

- [ ] **Step 1: Confirm E1-E4 files exist**

Run:

```bash
test -f src/werewolf_eval/game_log.py
test -f src/werewolf_eval/validate_game_log.py
test -f src/werewolf_eval/scoring.py
test -f src/werewolf_eval/score_game.py
test -f src/werewolf_eval/attribution.py
test -f src/werewolf_eval/attribute_game.py
test -f src/werewolf_eval/render_demo.py
test -f tests/test_game_log.py
test -f tests/test_scoring.py
test -f tests/test_attribution.py
test -f tests/test_render_demo.py
test -f docs/demo/phase2-runtime-demo.html
printf 'E1-E4 runtime baseline exists\n'
```

Expected result:

```text
E1-E4 runtime baseline exists
```

- [ ] **Step 2: Run baseline validation commands**

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

No commit is required for Task 1 because it only verifies the starting state.

---

### Task 2: Add the D1 gold Decision Log fixture

**Files:**

- Create: `docs/gold-game/g001-decision-log.json`
- Modify: none.
- Test: `python -m json.tool docs/gold-game/g001-decision-log.json`

- [ ] **Step 1: Create `docs/gold-game/g001-decision-log.json`**

Create this exact file:

```json
{
  "decision_log_id": "d1_g001_decision_log",
  "game_id": "g001",
  "source_label": "[人工 gold sample]",
  "decisions": [
    {
      "decision_id": "g001_d001",
      "actor": "wolf_team",
      "decision_scope": "team",
      "consensus_id": null,
      "phase": "night",
      "action": "werewolf_kill",
      "target": "p5",
      "visible_info_refs": ["g001_e001", "g001_e002"],
      "reason_summary": "狼队选择先刀平民位 p5，避免过早暴露对预言家 p3 的针对。",
      "decision_type": "team_coordinated",
      "confidence": 0.62,
      "strategy_tag": "night_kill"
    },
    {
      "decision_id": "g001_d002",
      "actor": "p3",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "night",
      "action": "seer_check",
      "target": "p1",
      "visible_info_refs": ["g001_e001"],
      "reason_summary": "预言家优先查验 p1，用第一晚信息确认一个高价值身份点。",
      "decision_type": "inference_based",
      "confidence": 0.7,
      "strategy_tag": "role_check"
    },
    {
      "decision_id": "g001_d003",
      "actor": "p4",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "night",
      "action": "witch_save",
      "target": "p5",
      "visible_info_refs": ["g001_e007"],
      "reason_summary": "女巫看到夜间死亡目标为 p5，选择使用解药保住一名村民。",
      "decision_type": "inference_based",
      "confidence": 0.85,
      "strategy_tag": "save_potion"
    },
    {
      "decision_id": "g001_d004",
      "actor": "p3",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "day",
      "action": "player_speech",
      "target": "p1",
      "visible_info_refs": ["g001_e008"],
      "reason_summary": "p3 基于夜间查验结果，在白天把压力推向 p1。",
      "decision_type": "inference_based",
      "confidence": 0.9,
      "strategy_tag": "seer_pressure"
    },
    {
      "decision_id": "g001_d005",
      "actor": "p1",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "day",
      "action": "player_speech",
      "target": "p3",
      "visible_info_refs": ["g001_e010"],
      "reason_summary": "p1 反打 p3，把预言家的压力包装成狼人强推。",
      "decision_type": "retaliatory",
      "confidence": 0.68,
      "strategy_tag": "counter_claim"
    },
    {
      "decision_id": "g001_d006",
      "actor": "p2",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "day",
      "action": "player_speech",
      "target": "p3",
      "visible_info_refs": ["g001_e011"],
      "reason_summary": "p2 支持 p1 的反打，配合狼队把 p3 描述成激进强推位。",
      "decision_type": "team_coordinated",
      "confidence": 0.64,
      "strategy_tag": "wolf_support"
    },
    {
      "decision_id": "g001_d007",
      "actor": "p4",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "day",
      "action": "player_vote",
      "target": "p1",
      "visible_info_refs": ["g001_e010", "g001_e013"],
      "reason_summary": "p4 观察到 p1 与 p2 站边过快，因此投向 p1。",
      "decision_type": "inference_based",
      "confidence": 0.74,
      "strategy_tag": "vote_suspicious_pair"
    },
    {
      "decision_id": "g001_d008",
      "actor": "p5",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "day",
      "action": "player_vote",
      "target": "p3",
      "visible_info_refs": ["g001_e014"],
      "reason_summary": "p5 认为 p3 的公开证据不足，选择投向 p3。",
      "decision_type": "default",
      "confidence": 0.55,
      "strategy_tag": "uncertain_vote"
    },
    {
      "decision_id": "g001_d009",
      "actor": "p4",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "night",
      "action": "witch_poison",
      "target": "p2",
      "visible_info_refs": ["g001_e017", "g001_e023"],
      "reason_summary": "p3 身份公开后，p2 白天支持 p1 并投出 p3，使 p2 的狼面显著升高。",
      "decision_type": "inference_based",
      "confidence": 0.88,
      "strategy_tag": "poison_suspected_wolf"
    },
    {
      "decision_id": "g001_d010",
      "actor": "p6",
      "decision_scope": "single",
      "consensus_id": null,
      "phase": "day",
      "action": "player_vote",
      "target": "p1",
      "visible_info_refs": ["g001_e029", "g001_e032"],
      "reason_summary": "p6 结合 p2 的狼人身份公开和 p1 第一日行为，最终投向 p1。",
      "decision_type": "inference_based",
      "confidence": 0.82,
      "strategy_tag": "final_vote"
    }
  ]
}
```

- [ ] **Step 2: Validate fixture JSON syntax**

Run:

```bash
python -m json.tool docs/gold-game/g001-decision-log.json > /dev/null
printf 'decision log json parses\n'
```

Expected result:

```text
decision log json parses
```

- [ ] **Step 3: Commit fixture**

Run:

```bash
git add docs/gold-game/g001-decision-log.json
git commit -m "docs: add D1 gold decision log fixture"
```

---

### Task 3: Add failing Decision Log tests

**Files:**

- Create: `tests/test_decision_log.py`
- Modify: none.
- Test: `tests/test_decision_log.py`

- [ ] **Step 1: Create `tests/test_decision_log.py`**

Create this file:

```python
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.decision_log import DecisionLogValidationError, load_decision_log, parse_decision_log
from werewolf_eval.game_log import load_game_log


class DecisionLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.path = ROOT / "docs/gold-game/g001-decision-log.json"

    def test_load_decision_log_accepts_gold_sample(self) -> None:
        decision_log = load_decision_log(self.path, self.game)

        self.assertEqual(decision_log.decision_log_id, "d1_g001_decision_log")
        self.assertEqual(decision_log.game_id, "g001")
        self.assertEqual(decision_log.source_label, "[人工 gold sample]")
        self.assertEqual(len(decision_log.decisions), 10)
        self.assertEqual(decision_log.decisions[0].decision_id, "g001_d001")
        self.assertEqual(decision_log.decisions[0].actor, "wolf_team")
        self.assertEqual(decision_log.decisions[0].decision_scope, "team")
        self.assertEqual(decision_log.decisions[-1].decision_type, "inference_based")

    def test_rejects_game_id_mismatch(self) -> None:
        raw = {
            "decision_log_id": "bad",
            "game_id": "other_game",
            "source_label": "[人工 gold sample]",
            "decisions": [],
        }

        with self.assertRaisesRegex(DecisionLogValidationError, "game_id mismatch"):
            parse_decision_log(raw, self.game)

    def test_rejects_unknown_actor(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["actor"] = "p99"

        with self.assertRaisesRegex(DecisionLogValidationError, "unknown actor"):
            parse_decision_log(raw, self.game)

    def test_rejects_unknown_visible_info_ref(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["visible_info_refs"] = ["g001_e999"]

        with self.assertRaisesRegex(DecisionLogValidationError, "unknown visible_info_refs"):
            parse_decision_log(raw, self.game)

    def test_rejects_invalid_decision_type(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["decision_type"] = "mind_reading"

        with self.assertRaisesRegex(DecisionLogValidationError, "invalid decision_type"):
            parse_decision_log(raw, self.game)

    def test_rejects_long_reason_summary(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["reason_summary"] = "x" * 201

        with self.assertRaisesRegex(DecisionLogValidationError, "reason_summary"):
            parse_decision_log(raw, self.game)

    def test_rejects_confidence_out_of_range(self) -> None:
        raw = self._minimal_raw()
        raw["decisions"][0]["confidence"] = 1.5

        with self.assertRaisesRegex(DecisionLogValidationError, "confidence"):
            parse_decision_log(raw, self.game)

    def _minimal_raw(self) -> dict[str, object]:
        return {
            "decision_log_id": "test_decision_log",
            "game_id": "g001",
            "source_label": "[人工 gold sample]",
            "decisions": [
                {
                    "decision_id": "test_d001",
                    "actor": "p4",
                    "decision_scope": "single",
                    "consensus_id": None,
                    "phase": "day",
                    "action": "player_vote",
                    "target": "p1",
                    "visible_info_refs": ["g001_e010"],
                    "reason_summary": "p4 votes based on visible public pressure.",
                    "decision_type": "inference_based",
                    "confidence": 0.75,
                    "strategy_tag": "vote_suspicious_pair",
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and confirm they fail for the right reason**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log
```

Expected result before implementation:

```text
ModuleNotFoundError: No module named 'werewolf_eval.decision_log'
```

- [ ] **Step 3: Commit failing tests**

Run:

```bash
git add tests/test_decision_log.py
git commit -m "test: specify D1 decision log validation"
```

---

### Task 4: Implement Decision Log parser and validator

**Files:**

- Create: `src/werewolf_eval/decision_log.py`
- Modify: none.
- Test: `tests/test_decision_log.py`

- [ ] **Step 1: Create `src/werewolf_eval/decision_log.py`**

Create this file:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.game_log import GameLog

VALID_DECISION_SCOPES = {"single", "team"}
VALID_DECISION_PHASES = {"night", "day"}
VALID_DECISION_TYPES = {
    "inference_based",
    "random",
    "retaliatory",
    "team_coordinated",
    "default",
}
VALID_SOURCE_LABELS = {"[人工 gold sample]", "[AI 生成]"}
ALLOWED_NON_PLAYER_ACTORS = {"wolf_team"}
ALLOWED_NON_PLAYER_TARGETS = {"none", "villager_team", "werewolf_team"}
MAX_REASON_SUMMARY_CHARS = 200


@dataclass(frozen=True)
class Decision:
    decision_id: str
    actor: str
    decision_scope: str
    consensus_id: str | None
    phase: str
    action: str
    target: str | None
    visible_info_refs: list[str]
    reason_summary: str
    decision_type: str
    confidence: float | None
    strategy_tag: str | None


@dataclass(frozen=True)
class DecisionLog:
    decision_log_id: str
    game_id: str
    source_label: str
    decisions: list[Decision]

    @property
    def decision_ids(self) -> set[str]:
        return {decision.decision_id for decision in self.decisions}


class DecisionLogValidationError(ValueError):
    """Raised when a Decision Log cannot be accepted as a Phase 2 runtime input."""


def load_decision_log(path: str | Path, game: GameLog) -> DecisionLog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DecisionLogValidationError("Decision Log root must be an object")
    return parse_decision_log(raw, game)


def parse_decision_log(raw: dict[str, Any], game: GameLog) -> DecisionLog:
    required_top_level = {"decision_log_id", "game_id", "source_label", "decisions"}
    missing = required_top_level - set(raw)
    if missing:
        raise DecisionLogValidationError(f"missing top-level fields: {sorted(missing)}")

    if not isinstance(raw["decisions"], list):
        raise DecisionLogValidationError("decisions must be a list")

    decisions = [_parse_decision(decision) for decision in raw["decisions"]]
    decision_log = DecisionLog(
        decision_log_id=str(raw["decision_log_id"]),
        game_id=str(raw["game_id"]),
        source_label=str(raw["source_label"]),
        decisions=decisions,
    )
    validate_decision_log(decision_log, game)
    return decision_log


def validate_decision_log(decision_log: DecisionLog, game: GameLog) -> None:
    if not decision_log.decision_log_id:
        raise DecisionLogValidationError("decision_log_id must not be empty")

    if decision_log.game_id != game.game_id:
        raise DecisionLogValidationError(
            f"game_id mismatch: decision log {decision_log.game_id!r} != game {game.game_id!r}"
        )

    if decision_log.source_label not in VALID_SOURCE_LABELS:
        raise DecisionLogValidationError(f"invalid source_label: {decision_log.source_label!r}")

    decision_ids = [decision.decision_id for decision in decision_log.decisions]
    if len(set(decision_ids)) != len(decision_ids):
        raise DecisionLogValidationError("decision_id values must be unique")

    for decision in decision_log.decisions:
        _validate_decision(decision, game)


def _parse_decision(raw: Any) -> Decision:
    if not isinstance(raw, dict):
        raise DecisionLogValidationError("decision entries must be objects")

    required_fields = {
        "decision_id",
        "actor",
        "decision_scope",
        "consensus_id",
        "phase",
        "action",
        "target",
        "visible_info_refs",
        "reason_summary",
        "decision_type",
    }
    missing = required_fields - set(raw)
    if missing:
        raise DecisionLogValidationError(f"decision missing fields: {sorted(missing)}")

    visible_info_refs = raw["visible_info_refs"]
    if not isinstance(visible_info_refs, list):
        raise DecisionLogValidationError("visible_info_refs must be a list")

    confidence = raw.get("confidence")
    if confidence is not None:
        confidence = float(confidence)

    strategy_tag = raw.get("strategy_tag")
    if strategy_tag is not None:
        strategy_tag = str(strategy_tag)

    consensus_id = raw["consensus_id"]
    if consensus_id is not None:
        consensus_id = str(consensus_id)

    target = raw["target"]
    if target is not None:
        target = str(target)

    return Decision(
        decision_id=str(raw["decision_id"]),
        actor=str(raw["actor"]),
        decision_scope=str(raw["decision_scope"]),
        consensus_id=consensus_id,
        phase=str(raw["phase"]),
        action=str(raw["action"]),
        target=target,
        visible_info_refs=[str(ref) for ref in visible_info_refs],
        reason_summary=str(raw["reason_summary"]),
        decision_type=str(raw["decision_type"]),
        confidence=confidence,
        strategy_tag=strategy_tag,
    )


def _validate_decision(decision: Decision, game: GameLog) -> None:
    if not decision.decision_id:
        raise DecisionLogValidationError("decision_id must not be empty")

    if decision.actor not in game.player_ids and decision.actor not in ALLOWED_NON_PLAYER_ACTORS:
        raise DecisionLogValidationError(f"{decision.decision_id}: unknown actor {decision.actor!r}")

    if decision.decision_scope not in VALID_DECISION_SCOPES:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: invalid decision_scope {decision.decision_scope!r}"
        )

    if decision.phase not in VALID_DECISION_PHASES:
        raise DecisionLogValidationError(f"{decision.decision_id}: invalid phase {decision.phase!r}")

    if not decision.action:
        raise DecisionLogValidationError(f"{decision.decision_id}: action must not be empty")

    if (
        decision.target is not None
        and decision.target not in game.player_ids
        and decision.target not in ALLOWED_NON_PLAYER_TARGETS
    ):
        raise DecisionLogValidationError(f"{decision.decision_id}: unknown target {decision.target!r}")

    unknown_refs = set(decision.visible_info_refs) - game.event_ids
    if unknown_refs:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: unknown visible_info_refs: {sorted(unknown_refs)}"
        )

    if len(decision.reason_summary) > MAX_REASON_SUMMARY_CHARS:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: reason_summary exceeds {MAX_REASON_SUMMARY_CHARS} chars"
        )

    if decision.decision_type not in VALID_DECISION_TYPES:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: invalid decision_type {decision.decision_type!r}"
        )

    if decision.confidence is not None and not 0.0 <= decision.confidence <= 1.0:
        raise DecisionLogValidationError(
            f"{decision.decision_id}: confidence must be between 0 and 1"
        )
```

- [ ] **Step 2: Run Decision Log unit tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log
```

Expected result:

```text
OK
```

- [ ] **Step 3: Commit parser and validator module**

Run:

```bash
git add src/werewolf_eval/decision_log.py tests/test_decision_log.py
git commit -m "feat: add D1 decision log parser"
```

---

### Task 5: Add Decision Log validation CLI

**Files:**

- Create: `src/werewolf_eval/validate_decision_log.py`
- Modify: `tests/test_decision_log.py`
- Test: `tests/test_decision_log.py`

- [ ] **Step 1: Extend `tests/test_decision_log.py` with CLI smoke test**

Add imports near the top:

```python
import subprocess
```

Add this test method inside `DecisionLogTests`:

```python
    def test_validate_decision_log_cli_outputs_summary(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.validate_decision_log",
                str(self.path),
                str(ROOT / "docs/gold-game/g001-game-log.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("validated decision_log_id=d1_g001_decision_log", result.stdout)
        self.assertIn("game_id=g001", result.stdout)
        self.assertIn("decisions=10", result.stdout)
        self.assertIn("source_label=[人工 gold sample]", result.stdout)
```

- [ ] **Step 2: Run CLI smoke test and confirm it fails for the right reason**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log.DecisionLogTests.test_validate_decision_log_cli_outputs_summary
```

Expected result before CLI implementation:

```text
No module named werewolf_eval.validate_decision_log
```

- [ ] **Step 3: Create `src/werewolf_eval/validate_decision_log.py`**

Create this file:

```python
from __future__ import annotations

import argparse

from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.game_log import load_game_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Decision Log JSON file.")
    parser.add_argument("decision_log_path", help="Path to Decision Log JSON")
    parser.add_argument("game_log_path", help="Path to matching Game Log JSON")
    args = parser.parse_args()

    game = load_game_log(args.game_log_path)
    decision_log = load_decision_log(args.decision_log_path, game)

    print(f"validated decision_log_id={decision_log.decision_log_id}")
    print(f"game_id={decision_log.game_id}")
    print(f"decisions={len(decision_log.decisions)}")
    print(f"source_label={decision_log.source_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI directly**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
```

Expected result:

```text
validated decision_log_id=d1_g001_decision_log
game_id=g001
decisions=10
source_label=[人工 gold sample]
```

- [ ] **Step 5: Run Decision Log tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log
```

Expected result:

```text
OK
```

- [ ] **Step 6: Commit CLI**

Run:

```bash
git add src/werewolf_eval/validate_decision_log.py tests/test_decision_log.py
git commit -m "feat: add D1 decision log validator CLI"
```

---

### Task 6: Update docs, commands, and tree map

**Files:**

- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/TASKS.md`
- Modify: `.oh-my-harness/tree.md`
- Test: documentation grep checks and full test suite.

- [ ] **Step 1: Update `AGENTS.md` command list**

Add this command under the existing Game Log command:

```markdown
- Decision Log 校验命令：`PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json`。
```

Update runtime boundary text to state:

```markdown
- Phase 2 运行时代码必须绑定 Implementation Plan；当前已完成 runtime entries 为 E1/E2/E3/E4/D1。
```

Update the MAP to include these files:

```text
│   │   ├── g001-decision-log.json
```

```text
│       ├── decision_log.py
│       ├── validate_decision_log.py
```

```text
│   ├── test_decision_log.py
```

- [ ] **Step 2: Update `README.md` current status**

Modify the current status paragraph so it includes D1 without claiming `decision_quality_score` is ready:

```markdown
**Phase 1 deterministic MVP 已完成。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer、E3 rule attribution engine、E4 runtime demo HTML exporter；D1 以 `docs/gold-game/g001-decision-log.json` + `src/werewolf_eval/decision_log.py` 提供 Phase 2 Decision Log runtime input skeleton。当前仍不代表真实 AI Agent 对局、真实 Consensus Log、AI 语义标注或真实多模型 Leaderboard 已完成，`decision_quality_score` 仍未接入评分链。
```

- [ ] **Step 3: Update `docs/TASKS.md` Phase 2 engineering section**

Change the Phase 2 section header sentence to:

```markdown
**E1-E4 与 D1 已作为 Phase 2 runtime entries 完成。** S4/S5 仍延后到 Phase 2。以下记录各工程任务的完成状态与产物路径。
```

Add this section after E4:

```markdown
### D1：Decision Log runtime skeleton

- 状态：`completed`（Phase 2 Decision Log runtime input；Decision Log parser / validator 已实现）
- 产出：`docs/gold-game/g001-decision-log.json` + `src/werewolf_eval/decision_log.py` + `src/werewolf_eval/validate_decision_log.py` + `tests/test_decision_log.py`。
- 说明：读取人工 gold Decision Log JSON，验证其 `game_id` 与 Game Log 一致，验证 actor / target / visible_info_refs / decision_type / confidence 等字段。D1 不调用 AI，不启用 S5，不修改 scoring，`decision_quality_score` 仍未接入评分链。
```

Add D1 to UX Acceptance:

```markdown
| D1 | Decision Log CLI 校验摘要 | 同一 Game Log + Decision Log 能稳定输出 `decision_log_id`、`game_id`、`decisions`、`source_label`，并拒绝非法 actor / refs / decision_type |
```

Add a Decision Log demo note under Demo Acceptance:

```markdown
**Demo 3：Phase 2 Decision Log input validation**

- 状态：`completed`（`docs/gold-game/g001-decision-log.json`；仅表示 Decision Log runtime input 可被验证，不表示 `decision_quality_score` 已接入评分链）
- 触发条件：D1 完成。
- 演示内容：运行时读取 Game Log + Decision Log → 校验结构化决策输入。
- 验收：同一输入稳定输出 `validated decision_log_id=d1_g001_decision_log`、`game_id=g001`、`decisions=10`、`source_label=[人工 gold sample]`。
```

- [ ] **Step 4: Refresh `.oh-my-harness/tree.md`**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result: `.oh-my-harness/tree.md` includes `g001-decision-log.json`, `decision_log.py`, `validate_decision_log.py`, and `test_decision_log.py`.

- [ ] **Step 5: Run documentation checks**

Run:

```bash
grep -R "validate_decision_log" AGENTS.md README.md docs/TASKS.md .oh-my-harness/tree.md
grep -R "g001-decision-log.json" AGENTS.md README.md docs/TASKS.md .oh-my-harness/tree.md
grep -R "test_decision_log.py" AGENTS.md .oh-my-harness/tree.md
grep -R "E1/E2/E3/E4/D1" AGENTS.md
grep -R "decision_quality_score.*仍未接入评分链" README.md docs/TASKS.md
```

Expected result:

- The first command prints matches in AGENTS, TASKS, and tree.
- The second command prints matches in AGENTS, README, TASKS, and tree.
- The third command prints matches in AGENTS and tree.
- The fourth command prints one match in AGENTS.
- The fifth command prints matches in README and TASKS.

- [ ] **Step 6: Commit docs and tree**

Run:

```bash
git add AGENTS.md README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: mark D1 decision log runtime skeleton complete"
```

---

### Task 7: Final verification and PR preparation

**Files:**

- Create: none.
- Modify: none.
- Test: full runtime validation commands.

- [ ] **Step 1: Run full validation chain**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected Game Log output includes:

```text
validated game_id=g001
players=6
events=38
winner=villager
end_round=2
```

Expected Decision Log output:

```text
validated decision_log_id=d1_g001_decision_log
game_id=g001
decisions=10
source_label=[人工 gold sample]
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
docs/gold-game/g001-decision-log.json
src/werewolf_eval/decision_log.py
src/werewolf_eval/validate_decision_log.py
tests/test_decision_log.py
```

- [ ] **Step 3: Confirm forbidden files did not change**

Run:

```bash
git diff --name-only main...HEAD -- src/werewolf_eval/scoring.py src/werewolf_eval/score_game.py src/werewolf_eval/attribution.py src/werewolf_eval/attribute_game.py src/werewolf_eval/render_demo.py docs/EVALUATION_RUBRIC.md docs/gold-game/g001-game-log.json docs/gold-game/s2-score-log.json docs/gold-game/s2-metrics-summary.json docs/gold-game/s3-rule-attribution.json docs/demo/phase1-gold-demo.html docs/demo/phase2-runtime-demo.html
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
feat: D1 decision log runtime skeleton
```

Use this PR body:

```markdown
## Summary

Implements D1 Decision Log runtime skeleton for Werewolf-agent.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--d1-decision-log-runtime-skeleton-plan.md`

## Scope

- Adds `docs/gold-game/g001-decision-log.json` as an artificial gold Decision Log fixture.
- Adds `src/werewolf_eval/decision_log.py` with parser and validator.
- Adds `src/werewolf_eval/validate_decision_log.py` CLI.
- Adds `tests/test_decision_log.py`.
- Updates AGENTS.md, README.md, docs/TASKS.md, and .oh-my-harness/tree.md.

## Runtime boundary

- Does not call AI models.
- Does not implement S5 AI semantic labeling.
- Does not implement Consensus Log runtime.
- Does not modify scoring, attribution, or rendering runtime.
- Does not modify EVALUATION_RUBRIC.md.
- Does not claim `decision_quality_score` is fully usable.
- Keeps the Decision Log fixture labeled `[人工 gold sample]`.

## Validation

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
git diff --check
```

Expected key outputs:

```text
validated game_id=g001
validated decision_log_id=d1_g001_decision_log
decisions=10
score_records=14
turn_points=1
rendered_demo_html=docs/demo/phase2-runtime-demo.html
OK
```
```

- [ ] **Step 6: Stop for review**

Do not merge automatically. Report changed files, validation outputs, and the Decision Log fixture path in the checkpoint summary.

---

## Checkpoint summary template for this PR

Use `docs/CHECKPOINT_TEMPLATE.md` and include:

```markdown
## Checkpoint Summary

Task: D1 Decision Log runtime skeleton
Branch: `task/d1-decision-log-runtime-skeleton`
Bound plan: `docs/harness/plans/2026-05-30--d1-decision-log-runtime-skeleton-plan.md`

Changed files:
- `.oh-my-harness/tree.md`
- `AGENTS.md`
- `README.md`
- `docs/TASKS.md`
- `docs/gold-game/g001-decision-log.json`
- `src/werewolf_eval/decision_log.py`
- `src/werewolf_eval/validate_decision_log.py`
- `tests/test_decision_log.py`

Validation:
- `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json`
- `PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html`
- `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
- `git diff --check`

Boundary confirmation:
- No AI model calls.
- No S5 AI semantic labeling.
- No Consensus Log runtime.
- No scoring / attribution / render_demo changes.
- No EVALUATION_RUBRIC.md changes.
- `decision_quality_score` is not claimed as fully usable.
```
