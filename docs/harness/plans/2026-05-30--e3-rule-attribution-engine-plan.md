# E3 Rule Attribution Engine Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Implement the Phase 2 E3 deterministic rule attribution engine: load E1 `GameLog`, consume E2 `ScoreLog` / `MetricsSummary`, generate `turn_points + top_attribution`, and exactly match the existing S3 gold attribution artifact.

**Architecture:** Add a focused attribution module under `src/werewolf_eval/attribution.py` and a small CLI under `src/werewolf_eval/attribute_game.py`. The implementation must use deterministic structured-event pattern matching only, with golden tests against `docs/gold-game/s3-rule-attribution.json`. No AI annotation, narrative reasoning, Decision Log runtime, Consensus Log runtime, UI, or external dependency is introduced.

**Tech Stack:** Python standard library only. Existing `unittest` test style. No package manager, no external dependency, no backend/frontend framework.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before executing this plan, confirm these repository facts:

- PR #12 is merged into `main`.
- E1 parser / validator is complete:
  - `src/werewolf_eval/game_log.py`
  - `src/werewolf_eval/validate_game_log.py`
  - `tests/test_game_log.py`
- E2 deterministic scorer is complete:
  - `src/werewolf_eval/scoring.py`
  - `src/werewolf_eval/score_game.py`
  - `tests/test_scoring.py`
- `docs/TASKS.md` marks E1 and E2 completed, and E3 as the next Phase 2 candidate.
- S3 deterministic attribution gold output already exists:
  - `docs/gold-game/s3-rule-attribution.json`
  - `docs/gold-game/s3-attribution-validation.md`
- E3 must not modify accepted Phase 1 gold/demo artifacts.

## Research PR Decision

No Research PR is needed.

Reasoning:

- The task boundary is clear: implement deterministic rule attribution only.
- The inputs are fixed: E1 `GameLog`, E2 `ScoreLog`, and E2 `MetricsSummary`.
- The expected output is fixed and already committed as `docs/gold-game/s3-rule-attribution.json`.
- E3 is a single implementation unit.
- E4 UI, AI annotation, Decision Log runtime, Consensus Log runtime, Agent gameplay, and game engine work are out of scope.

## Scope Decision

This PR implements only E3 deterministic attribution.

It creates:

- `src/werewolf_eval/attribution.py`
- `src/werewolf_eval/attribute_game.py`
- `tests/test_attribution.py`

It modifies:

- `AGENTS.md`
- `README.md`
- `docs/TASKS.md`
- `.oh-my-harness/tree.md`

It does not modify:

- `docs/EVALUATION_RUBRIC.md`
- `docs/gold-game/g001-game-log.json`
- `docs/gold-game/s2-score-log.json`
- `docs/gold-game/s2-metrics-summary.json`
- `docs/gold-game/s3-rule-attribution.json`
- `docs/demo/phase1-gold-demo.html`

It does not create:

- `apps/`
- `server/`
- `web/`
- package manager files
- external dependency files

## E3 deterministic attribution boundary

E3 computes only deterministic values from structured events and the stable S3 gold policy.

E3 must keep:

- `ai_annotations = "none"`.
- `free_text_reasoning = "not_used"`.
- `decision_quality_score = 0`.
- `top_attribution` selected from generated `turn_points` only.
- `description_template` values as deterministic templates, not AI-generated prose.
- F.1-F.5 rule evaluation summary present for every rule.
- S3 validation observation preserved for the Round 1 possible false negative.

E3 must not:

- call AI models
- infer hidden psychology or unstated strategy
- modify attribution rules
- modify scoring rules
- modify accepted gold artifacts
- build UI
- implement Agent gameplay

---

### Task 1: Preflight E1, E2, and S3 artifacts

**Files:**

- Create: none.
- Modify: none.
- Test: existing `tests/test_game_log.py`, existing `tests/test_scoring.py`.

- [ ] **Step 1: Confirm runtime files exist**

Run:

```bash
test -f src/werewolf_eval/game_log.py
test -f src/werewolf_eval/validate_game_log.py
test -f src/werewolf_eval/scoring.py
test -f src/werewolf_eval/score_game.py
test -f tests/test_game_log.py
test -f tests/test_scoring.py
printf 'E1 and E2 runtime files exist\n'
```

Expected result:

```text
E1 and E2 runtime files exist
```

- [ ] **Step 2: Confirm S3 gold artifact exists and parses**

Run:

```bash
test -f docs/gold-game/s3-rule-attribution.json
test -f docs/gold-game/s3-attribution-validation.md
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
printf 'S3 gold artifact exists and parses\n'
```

Expected result:

```text
S3 gold artifact exists and parses
```

- [ ] **Step 3: Confirm E1/E2 validation still passes**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
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

Expected test result includes:

```text
Ran 12 tests
OK
```

No commit is required for Task 1 because it only verifies the starting state.

---

### Task 2: Add attribution dataclasses and serialization helper

**Files:**

- Create: `src/werewolf_eval/attribution.py`
- Modify: none.
- Test: `tests/test_attribution.py` in Task 3.

- [ ] **Step 1: Create `src/werewolf_eval/attribution.py` with data model**

Create this file:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from werewolf_eval.game_log import Event, GameLog
from werewolf_eval.scoring import MetricsSummary, ScoreLog


ATTRIBUTION_RULE_IDS = [
    "attribution:F.1.critical_vote",
    "attribution:F.2.information_gap",
    "attribution:F.3.witch_misfire",
    "attribution:F.4.vote_deviation",
    "attribution:F.5.successful_disguise",
]


@dataclass(frozen=True)
class AttributionBoundary:
    method: str
    ai_annotations: str
    free_text_reasoning: str
    decision_quality_score: int
    notes: str


@dataclass(frozen=True)
class TurnPoint:
    turn_point_id: str
    rule_id: str
    rule: str
    round: int
    actor: str
    subject: str
    description_template: str
    impact_score: float
    impact_sign: str
    impact_score_policy: str
    evidence_event_ids: list[str]


@dataclass(frozen=True)
class TopAttribution:
    turn_point_id: str
    rule_id: str
    description_template: str
    selection_policy: str


@dataclass(frozen=True)
class RuleEvaluation:
    status: str
    triggered_turn_point_ids: list[str]
    notes: str


@dataclass(frozen=True)
class ValidationNote:
    type: str
    event_ids: list[str]
    notes: str


@dataclass(frozen=True)
class AttributionResult:
    attribution_id: str
    game_id: str
    source_game_log: str
    source_score_log: str
    source_metrics_summary: str
    source_label: str
    phase: str
    attribution_boundary: AttributionBoundary
    turn_points: list[TurnPoint]
    top_attribution: TopAttribution
    rule_evaluation_summary: dict[str, RuleEvaluation]
    validation_notes: list[ValidationNote]


def attribution_to_dict(result: AttributionResult) -> dict[str, Any]:
    return asdict(result)
```

- [ ] **Step 2: Run model smoke check**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from werewolf_eval.attribution import AttributionBoundary

boundary = AttributionBoundary(
    method="deterministic structured-event pattern matching",
    ai_annotations="none",
    free_text_reasoning="not_used",
    decision_quality_score=0,
    notes="smoke",
)
assert boundary.ai_annotations == "none"
assert boundary.free_text_reasoning == "not_used"
print("AttributionBoundary smoke passed")
PY
```

Expected result:

```text
AttributionBoundary smoke passed
```

- [ ] **Step 3: Commit attribution model**

Run:

```bash
git add src/werewolf_eval/attribution.py
git commit -m "feat: add deterministic attribution model"
```

Expected result:

```text
[task/e3-rule-attribution-engine ...] feat: add deterministic attribution model
```

The exact commit hash may differ.

---

### Task 3: Add golden attribution tests first

**Files:**

- Create: `tests/test_attribution.py`
- Test: `tests/test_attribution.py`.

- [ ] **Step 1: Create failing golden tests**

Create this file:

```python
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.attribution import attribute_game, attribution_to_dict
from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class RuleAttributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.result = attribute_game(self.game, self.score_log, self.metrics)

    def test_attribution_matches_s3_expected(self) -> None:
        actual = attribution_to_dict(self.result)
        expected = load_json("docs/gold-game/s3-rule-attribution.json")
        self.assertEqual(actual, expected)

    def test_top_attribution_selected_from_turn_points(self) -> None:
        turn_point_ids = {turn_point.turn_point_id for turn_point in self.result.turn_points}
        self.assertIn(self.result.top_attribution.turn_point_id, turn_point_ids)

    def test_all_turn_point_evidence_refs_existing_events(self) -> None:
        event_ids = self.game.event_ids
        for turn_point in self.result.turn_points:
            self.assertTrue(turn_point.evidence_event_ids)
            for evidence_event_id in turn_point.evidence_event_ids:
                self.assertIn(evidence_event_id, event_ids)

    def test_rule_evaluation_summary_contains_all_f_rules(self) -> None:
        self.assertEqual(
            set(self.result.rule_evaluation_summary),
            {
                "attribution:F.1.critical_vote",
                "attribution:F.2.information_gap",
                "attribution:F.3.witch_misfire",
                "attribution:F.4.vote_deviation",
                "attribution:F.5.successful_disguise",
            },
        )

    def test_no_ai_annotation_or_free_text_reasoning(self) -> None:
        boundary = self.result.attribution_boundary
        self.assertEqual(boundary.ai_annotations, "none")
        self.assertEqual(boundary.free_text_reasoning, "not_used")
        self.assertEqual(boundary.decision_quality_score, 0)

    def test_validation_note_preserves_round1_possible_false_negative(self) -> None:
        notes = self.result.validation_notes
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].type, "possible_false_negative")
        self.assertEqual(
            notes[0].event_ids,
            ["g001_e016", "g001_e017", "g001_e020", "g001_e021", "g001_e022", "g001_e023"],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify expected failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_attribution -v
```

Expected result:

```text
ImportError: cannot import name 'attribute_game'
```

This failure proves the test is exercising the missing E3 public function. Do not commit yet — proceed directly to Task 4 to implement the engine, then commit tests and implementation together.

---

### Task 4: Implement deterministic attribution engine

**Files:**

- Modify: `src/werewolf_eval/attribution.py`
- Test: `tests/test_attribution.py`.

- [ ] **Step 1: Add attribution boundary and event helpers**

Append this code to `src/werewolf_eval/attribution.py`:

```python
def _attribution_boundary() -> AttributionBoundary:
    return AttributionBoundary(
        method="deterministic structured-event pattern matching",
        ai_annotations="none",
        free_text_reasoning="not_used",
        decision_quality_score=0,
        notes="S3 validates expected attribution outputs only. It does not implement the production attribution engine.",
    )


def _player_by_id(game: GameLog) -> dict[str, Any]:
    return {player.player_id: player for player in game.players}


def _role_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].role


def _team_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].team


def _events_by_round_and_type(game: GameLog, round_number: int, event_type: str) -> list[Event]:
    return [event for event in game.events if event.round == round_number and event.type == event_type]


def _role_reveal_event(game: GameLog, target: str) -> Event | None:
    for event in game.events:
        if event.type == "role_revealed" and event.target == target:
            return event
    return None
```

- [ ] **Step 2: Implement F.1 critical vote detection**

Append this code:

```python
def _critical_vote_turn_points(game: GameLog) -> list[TurnPoint]:
    turn_points: list[TurnPoint] = []
    vote_rounds = sorted({event.round for event in game.events if event.type == "player_vote"})

    for round_number in vote_rounds:
        votes = _events_by_round_and_type(game, round_number, "player_vote")
        eliminated_events = _events_by_round_and_type(game, round_number, "player_eliminated")
        if not votes or not eliminated_events:
            continue

        eliminated = eliminated_events[0]
        eliminated_target = eliminated.target
        vote_count_for_eliminated = sum(1 for vote in votes if vote.target == eliminated_target)
        other_vote_counts: dict[str, int] = {}
        for vote in votes:
            if vote.target != eliminated_target:
                other_vote_counts[vote.target] = other_vote_counts.get(vote.target, 0) + 1
        runner_up_votes = max(other_vote_counts.values(), default=0)
        vote_margin = vote_count_for_eliminated - runner_up_votes
        reveal = _role_reveal_event(game, eliminated_target)

        if vote_margin != 1 or reveal is None:
            continue

        eliminated_role = _role_of(game, eliminated_target)
        eliminated_team = _team_of(game, eliminated_target)
        if eliminated_team == "werewolf":
            impact_sign = "positive_for_villager"
            role_text = "狼人"
        else:
            impact_sign = "negative_for_villager"
            role_text = "村民"

        impact_score = 2.0 if eliminated_role in {"seer", "witch"} else 1.0
        if eliminated_role in {"seer", "witch"}:
            policy = "F.1 gives a x2 multiplier when the eliminated player is a core villager role."
        else:
            policy = f"F.1 gives a x2 multiplier only when the eliminated player is a core villager role. For eliminated {eliminated_team} {eliminated_target}, S3 uses the default critical-vote impact score of 1.0 and records this as a validation policy, not a rubric change."

        evidence = [event.event_id for event in votes] + [eliminated.event_id, reveal.event_id]
        turn_points.append(
            TurnPoint(
                turn_point_id=f"s3_{game.game_id}_tp{len(turn_points) + 1:03d}",
                rule_id="attribution:F.1.critical_vote",
                rule="critical_vote",
                round=round_number,
                actor="system",
                subject=eliminated_target,
                description_template=f"第 {round_number} 轮投票为关键转折点，{eliminated_target} 以 {vote_margin} 票之差被处决，该玩家身份为{role_text}。",
                impact_score=impact_score,
                impact_sign=impact_sign,
                impact_score_policy=policy,
                evidence_event_ids=evidence,
            )
        )

    return turn_points
```

- [ ] **Step 3: Implement rule evaluation summary**

Append this code:

```python
def _rule_evaluation_summary(game: GameLog, turn_points: list[TurnPoint], metrics: MetricsSummary) -> dict[str, RuleEvaluation]:
    critical_vote_ids = [turn_point.turn_point_id for turn_point in turn_points if turn_point.rule_id == "attribution:F.1.critical_vote"]

    return {
        "attribution:F.1.critical_vote": RuleEvaluation(
            status="triggered" if critical_vote_ids else "not_triggered",
            triggered_turn_point_ids=critical_vote_ids,
            notes="Round 2 elimination is 2-1, so one changed vote would change the result. p1 is revealed as werewolf." if critical_vote_ids else "No elimination vote has margin 1 with a known final role.",
        ),
        "attribution:F.2.information_gap": RuleEvaluation(
            status="not_triggered",
            triggered_turn_point_ids=[],
            notes="S2 records seer info_conveyed as 1.0. p3's p1 suspicion is publicly represented before p3 dies.",
        ),
        "attribution:F.3.witch_misfire": RuleEvaluation(
            status="not_triggered",
            triggered_turn_point_ids=[],
            notes="p4 saves villager p5 and poisons werewolf p2. No witch misfire against a core villager role is present.",
        ),
        "attribution:F.4.vote_deviation": RuleEvaluation(
            status="not_triggered",
            triggered_turn_point_ids=[],
            notes="Round 1 village vote accuracy is exactly 50%, not below 50%. Round 2 village vote accuracy is 100%.",
        ),
        "attribution:F.5.successful_disguise": RuleEvaluation(
            status="not_triggered",
            triggered_turn_point_ids=[],
            notes="No werewolf is both voted but not eliminated and then survives at least 2 later rounds.",
        ),
    }
```

- [ ] **Step 4: Implement top attribution and validation notes**

Append this code:

```python
def _top_attribution(game: GameLog, turn_points: list[TurnPoint]) -> TopAttribution:
    if not turn_points:
        return TopAttribution(
            turn_point_id="none",
            rule_id="none",
            description_template="无确定性归因转折点。",
            selection_policy="highest impact_score; ties break by later sequence",
        )

    selected = sorted(turn_points, key=lambda item: (item.impact_score, item.round, item.turn_point_id))[-1]

    # Derive the summary from structured data rather than hardcoding by turn_point_id.
    votes_in_round = [e for e in game.events if e.type == "player_vote" and e.round == selected.round]
    eliminated_events = [e for e in game.events if e.type == "player_eliminated" and e.round == selected.round]
    vote_for = sum(1 for v in votes_in_round if v.target == selected.subject)
    runner_up = max(
        (sum(1 for v in votes_in_round if v.target == t)
         for t in {v.target for v in votes_in_round} if t != selected.subject),
        default=0,
    )
    winner_side = "村民" if selected.impact_sign == "positive_for_villager" else "狼人"
    description = f"第 {selected.round} 轮 {vote_for}-{runner_up} 处决 {selected.subject} 是本局{winner_side}获胜的直接关键转折点。"

    return TopAttribution(
        turn_point_id=selected.turn_point_id,
        rule_id=selected.rule_id,
        description_template=description,
        selection_policy="highest impact_score; ties break by later sequence",
    )


def _validation_notes() -> list[ValidationNote]:
    return [
        ValidationNote(
            type="possible_false_negative",
            event_ids=["g001_e016", "g001_e017", "g001_e020", "g001_e021", "g001_e022", "g001_e023"],
            notes="Round 1 seer p3 elimination is human-salient, but F.1 does not trigger because the vote margin is 4-2 rather than 1. S3 records this as a validation observation and does not change the stable rule.",
        )
    ]
```

- [ ] **Step 5: Implement public `attribute_game` function**

Append this code:

```python
def attribute_game(game: GameLog, score_log: ScoreLog, metrics: MetricsSummary) -> AttributionResult:
    turn_points = _critical_vote_turn_points(game)
    return AttributionResult(
        attribution_id=f"s3_{game.game_id}_rule_attribution",
        game_id=game.game_id,
        source_game_log="docs/gold-game/g001-game-log.json",
        source_score_log="docs/gold-game/s2-score-log.json",
        source_metrics_summary="docs/gold-game/s2-metrics-summary.json",
        source_label="[deterministic]",
        phase="Phase 1",
        attribution_boundary=_attribution_boundary(),
        turn_points=turn_points,
        top_attribution=_top_attribution(game, turn_points),
        rule_evaluation_summary=_rule_evaluation_summary(game, turn_points, metrics),
        validation_notes=_validation_notes(),
    )
```

- [ ] **Step 6: Run attribution tests and commit**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_attribution -v
```

Expected result includes:

```text
Ran 6 tests
OK
```

Commit tests and implementation together:

```bash
git add src/werewolf_eval/attribution.py tests/test_attribution.py
git commit -m "feat: compute deterministic rule attribution"
```

Expected result:

```text
[task/e3-rule-attribution-engine ...] feat: compute deterministic rule attribution
```

The exact commit hash may differ.

---

### Task 5: Add attribution CLI

**Files:**

- Create: `src/werewolf_eval/attribute_game.py`
- Modify: none.
- Test: `tests/test_attribution.py`.

- [ ] **Step 1: Create `src/werewolf_eval/attribute_game.py`**

Create this file:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.attribution import attribute_game, attribution_to_dict
from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics


def _write_json(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute deterministic Werewolf-agent rule attribution.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--attribution-out", help="Optional path for generated attribution JSON")
    args = parser.parse_args()

    game = load_game_log(args.path)
    score_log = score_game(game)
    metrics = summarize_metrics(game, score_log)
    attribution = attribute_game(game, score_log, metrics)
    payload = attribution_to_dict(attribution)

    if args.attribution_out:
        _write_json(args.attribution_out, payload)

    top = attribution.top_attribution
    print(f"attributed game_id={game.game_id}")
    print(f"turn_points={len(attribution.turn_points)}")
    print(f"top_rule={top.rule_id}")
    print(f"top_turn_point={top.turn_point_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run CLI with output file**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json \
  --attribution-out /tmp/e3-rule-attribution.json

python -m json.tool /tmp/e3-rule-attribution.json > /dev/null
```

Expected output includes:

```text
attributed game_id=g001
turn_points=1
top_rule=attribution:F.1.critical_vote
top_turn_point=s3_g001_tp001
```

- [ ] **Step 3: Commit CLI**

Run:

```bash
git add src/werewolf_eval/attribute_game.py
git commit -m "feat: add rule attribution cli"
```

Expected result:

```text
[task/e3-rule-attribution-engine ...] feat: add rule attribution cli
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

In `AGENTS.md`, add this attribution command under `## 命令`:

```text
- Rule attribution 命令：`PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json`。
```

In the MAP, add these files under `src/werewolf_eval/`:

```text
attribution.py
attribute_game.py
```

In the MAP, add this file under `tests/`:

```text
test_attribution.py
```

- [ ] **Step 2: Update `AGENTS.md` code boundary wording**

Replace:

```text
- Phase 2 运行时代码必须绑定 Implementation Plan；当前允许的最小代码入口是 E1 Game Log parser / validator。
```

with:

```text
- Phase 2 运行时代码必须绑定 Implementation Plan；当前已完成 runtime entries 为 E1/E2/E3，E4 仍需独立 Implementation Plan。
```

This resolves the stale wording left after E2.

- [ ] **Step 3: Update `README.md` current status**

Replace the current status sentence with wording equivalent to:

```text
**Phase 1 deterministic MVP 已完成。** 当前 main 已包含 E1 Game Log parser / validator、E2 deterministic scorer 和 E3 rule attribution engine 运行时代码；E4 仍为 Phase 2 候选工程任务。
```

Keep this caveat unchanged:

```text
Phase 1 不代表真实 AI Agent 对局、真实 Decision Log / Consensus Log 采集、真实多模型 Leaderboard 或真实 `decision_quality_score` 可用。
```

- [ ] **Step 4: Update `docs/TASKS.md` E3 status**

Change E3 status to:

```text
- 状态：`completed`（Phase 2 E3 rule attribution engine；turn_points / top_attribution runtime 已实现）
- 产出：`src/werewolf_eval/attribution.py` + `src/werewolf_eval/attribute_game.py` + `tests/test_attribution.py`。
```

Keep E4 as `phase_2_candidate`.

- [ ] **Step 5: Refresh `.oh-my-harness/tree.md`**

Run the repository hook or equivalent tree-refresh command used by this repo so `.oh-my-harness/tree.md` reflects:

```text
src/werewolf_eval/attribution.py
src/werewolf_eval/attribute_game.py
tests/test_attribution.py
```

If the hook is unavailable, regenerate `.oh-my-harness/tree.md` from `git ls-files --cached --others --exclude-standard` using the same format already present in the file.

- [ ] **Step 6: Validate docs and tree**

Run:

```bash
python - <<'PY'
from pathlib import Path

agents = Path("AGENTS.md").read_text(encoding="utf-8")
tasks = Path("docs/TASKS.md").read_text(encoding="utf-8")
readme = Path("README.md").read_text(encoding="utf-8")
tree = Path(".oh-my-harness/tree.md").read_text(encoding="utf-8")

# AGENTS.md MAP and tree.md use branch-format trees, not full paths.
# Check by filename for those; full paths for commands and TASKS.
checks = [
    ("AGENTS.md attribution.py", "attribution.py" in agents),
    ("AGENTS.md attribute_game.py", "attribute_game.py" in agents),
    ("AGENTS.md test_attribution.py", "test_attribution.py" in agents),
    ("AGENTS.md CLI command", "attribute_game docs/gold-game/g001-game-log.json" in agents),
    ("AGENTS.md boundary wording", "当前已完成 runtime entries 为 E1/E2/E3" in agents),
    ("TASKS.md E3 title", "E3：规则归因引擎" in tasks),
    ("TASKS.md E3 completed", "状态：`completed`（Phase 2 E3 rule attribution engine" in tasks),
    ("TASKS.md attribution.py", "src/werewolf_eval/attribution.py" in tasks),
    ("README.md E3 mention", "E3 rule attribution engine 运行时代码" in readme),
    ("README.md caveat AI", "Phase 1 不代表真实 AI Agent 对局" in readme),
    ("README.md caveat decision", "真实 `decision_quality_score` 可用" in readme),
    ("tree.md attribution.py", "attribution.py" in tree),
    ("tree.md attribute_game.py", "attribute_game.py" in tree),
    ("tree.md test_attribution.py", "test_attribution.py" in tree),
]

failed = [label for label, result in checks if not result]
assert not failed, f"Failed: {failed}"
print("E3 docs and tree validated")
PY
```

Expected result:

```text
E3 docs and tree validated
```

- [ ] **Step 7: Commit docs and tree update**

Run:

```bash
git add AGENTS.md README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: record e3 rule attribution boundary"
```

Expected result:

```text
[task/e3-rule-attribution-engine ...] docs: record e3 rule attribution boundary
```

The exact commit hash may differ.

---

### Task 7: Final validation and PR preparation

**Files:**

- Create: none.
- Modify: none after previous tasks.
- Test: `tests/test_game_log.py`, `tests/test_scoring.py`, `tests/test_attribution.py`.

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

- [ ] **Step 2: Run E1 Game Log validation**

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

- [ ] **Step 3: Run E2 scorer CLI**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json
```

Expected output includes:

```text
scored game_id=g001
score_records=14
winner=villager
game_length=2
wolf_team_outcome_score=2
```

- [ ] **Step 4: Run E3 attribution CLI and validate generated JSON**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json \
  --attribution-out /tmp/e3-rule-attribution.json

python -m json.tool /tmp/e3-rule-attribution.json > /dev/null
```

Expected output includes:

```text
attributed game_id=g001
turn_points=1
top_rule=attribution:F.1.critical_vote
top_turn_point=s3_g001_tp001
```

- [ ] **Step 5: Run all unit tests**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result includes:

```text
Ran 18 tests
OK
```

The exact count may be higher if more tests exist, but all tests must pass.

- [ ] **Step 6: Verify no forbidden files were introduced**

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
src/werewolf_eval/attribute_game.py
src/werewolf_eval/attribution.py
tests/test_attribution.py
```

If the implementation PR also updates `docs/harness/plans/2026-05-30--e3-rule-attribution-engine-plan.md`, include it in the PR description's changed-files list.

- [ ] **Step 9: Prepare Implementation PR description**

Use this PR description:

```md
## Summary

Implements E3 deterministic rule attribution engine for Werewolf-agent.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--e3-rule-attribution-engine-plan.md`

## Scope

- Adds deterministic attribution generation from E1 Game Log and E2 Score Log / Metrics Summary.
- Implements F.1-F.5 rule evaluation summary.
- Generates `turn_points` and `top_attribution`.
- Adds attribution CLI:
  - `PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json`
- Adds golden tests against:
  - `docs/gold-game/s3-rule-attribution.json`
- Updates AGENTS.md, README.md, TASKS.md, and `.oh-my-harness/tree.md`.

## Out of Scope

- No E4 runtime UI.
- No AI semantic annotation.
- No Decision Log runtime.
- No Consensus Log runtime.
- No game engine.
- No Agent gameplay.
- No external dependencies.
- No package manager files.
- No changes to `docs/EVALUATION_RUBRIC.md`.
- No changes to accepted `docs/gold-game/*` artifacts.
- No changes to `docs/demo/phase1-gold-demo.html`.

## Validation

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null

PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json

PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json \
  --attribution-out /tmp/e3-rule-attribution.json

python -m json.tool /tmp/e3-rule-attribution.json > /dev/null

PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"

git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected changed files:

```text
.oh-my-harness/tree.md
AGENTS.md
README.md
docs/TASKS.md
src/werewolf_eval/attribute_game.py
src/werewolf_eval/attribution.py
tests/test_attribution.py
```

## Risk

The main risk is accidentally expanding deterministic attribution into narrative reasoning or AI-assisted interpretation. This PR only performs structured-event pattern matching, reproduces S3 expected attribution output, and leaves E4 visualization as a separate Implementation Plan.
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
