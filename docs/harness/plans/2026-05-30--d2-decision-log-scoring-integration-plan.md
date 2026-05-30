# D2 Decision Log Scoring Integration Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Connect the existing D1 Decision Log runtime input to the E2 deterministic scorer so Decision Log decisions are attached to score-relevant events via `decision_id`, illegal `visible_info_refs` trigger `rule_integrity_score` penalties, and traceability from Decision Log through Score Log to Metrics Summary is preserved. Positive `decision_quality_score` assignment remains out of scope and waits for S5 AI semantic judgment.

**Architecture:** Keep the current Game Log-only scoring path backward compatible. Add an optional Decision Log input path that maps accepted decisions onto existing score-relevant Game Log events, applies deterministic Rubric G.1 Step 1-2 checks, and leaves AI semantic judgment for S5. Runtime demo generation should consume the same scorer path so the HTML boundary statement reflects D2 partial deterministic scoring instead of claiming decision quality is fixed at 0.

**Tech Stack:** Python standard library only; existing `unittest` tests; existing JSON fixtures under `docs/gold-game/`; existing static HTML writer under `src/werewolf_eval/render_demo.py`.

---

## Context

Current main facts:

- E1 Game Log parser / validator is implemented in `src/werewolf_eval/game_log.py`.
- E2 deterministic scorer is implemented in `src/werewolf_eval/scoring.py` and `src/werewolf_eval/score_game.py`.
- E3 attribution consumes the current score log.
- E4 runtime demo is implemented in `src/werewolf_eval/render_demo.py`.
- D1 Decision Log parser / validator is implemented in `src/werewolf_eval/decision_log.py` and `src/werewolf_eval/validate_decision_log.py`.
- `docs/gold-game/g001-decision-log.json` exists and validates against `docs/gold-game/g001-game-log.json`.

D2 exists because `decision_quality_score` is still hardcoded to 0 inside `ScoreRecord` construction, and there is no runtime connection from Decision Log to Score Log. This implementation implements Rubric G.1 Step 1-2 deterministic filters only:

```text
Step 1 [deterministic]: check whether every visible_info_ref is visible to the decision actor.
  → illegal refs trigger rule_integrity_score = -3.
Step 2 [deterministic]: if refs are empty, or decision_type is random/default, record decision_id but keep decision_quality_score = 0.
```

Step 3 (AI semantic judgment: whether refs logically support the decision) is the only Rubric entry point for positive `decision_quality_score`. D2 does NOT implement Step 3 — it stays in S5. Therefore D2 never assigns `decision_quality_score > 0`.

## Global Forbidden Scope

Do not implement any of the following in this D2 PR:

- No AI provider, prompt, model call, API key, mock model, or semantic labeling pipeline.
- No S5 AI semantic scoring integration.
- No S4 Consensus Log parser / validator / fixture.
- No G1 real AI Agent gameplay engine.
- No L1 real multi-game Leaderboard.
- No changes to `docs/EVALUATION_RUBRIC.md`.
- No broad scorer refactor beyond what is needed for optional Decision Log scoring.
- No claim that `decision_quality_score` is fully available; D2 is partial deterministic scoring only.

## Files Overview

Implementation PR should modify these existing files only:

- `src/werewolf_eval/scoring.py`
  - Add optional Decision Log support.
  - Add deterministic decision visibility checks.
  - Add decision-to-event matching.
  - Add `decision_id` to score records.
  - Keep no-Decision-Log behavior stable.

- `src/werewolf_eval/score_game.py`
  - Add optional CLI argument `--decision-log`.
  - Load and validate Decision Log when supplied.
  - Pass the Decision Log to `score_game`.

- `src/werewolf_eval/render_demo.py`
  - Add optional CLI argument `--decision-log`.
  - Load and validate Decision Log when supplied.
  - Pass the Decision Log to `score_game`.
  - Update demo context and HTML boundary labels.

- `docs/gold-game/g001-decision-log.json`
  - Adjust gold decision refs only where required by deterministic visibility rules.
  - Preserve `decision_log_id`, `game_id`, `source_label`, and 10 decisions.

- `docs/gold-game/s2-score-log.json`
  - Regenerate from D2 scorer with `--decision-log`.

- `docs/gold-game/s2-metrics-summary.json`
  - Regenerate from D2 scorer with `--decision-log`.

- `docs/demo/phase2-runtime-demo.html`
  - Regenerate using D2-aware runtime demo command.

- `tests/test_scoring.py`
  - Add tests for no-Decision-Log compatibility and D2 scoring behavior.

- `tests/test_render_demo.py`
  - Update / add tests for D2 demo boundary copy and leaderboard decision score.

- `docs/TASKS.md`
  - Mark D2 completed only after implementation and validation pass.
  - Add D2 UX / demo acceptance entry.

- `.oh-my-harness/tree.md`
  - Do not edit unless files are added, deleted, or renamed. This D2 implementation is expected to modify existing files only, so tree should remain unchanged.

---

### 任务 1：Add D2 tests before implementation

**文件：**
- 修改：`tests/test_scoring.py`
- 读取：`src/werewolf_eval/scoring.py`
- 读取：`src/werewolf_eval/decision_log.py`
- 读取：`docs/gold-game/g001-game-log.json`
- 读取：`docs/gold-game/g001-decision-log.json`

- [ ] **步骤 1：扩展 imports**

在 `tests/test_scoring.py` 中加入 Decision Log loader：

```python
from werewolf_eval.decision_log import load_decision_log, parse_decision_log
```

- [ ] **步骤 2：在 setUp 中加载 Decision Log**

将 `setUp` 改为同时保留旧路径和 D2 路径：

```python
class DeterministicScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.decision_log = load_decision_log(ROOT / "docs/gold-game/g001-decision-log.json", self.game)
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.d2_score_log = score_game(self.game, decision_log=self.decision_log)
        self.d2_metrics = summarize_metrics(self.game, self.d2_score_log)
```

- [ ] **步骤 3：保留无 Decision Log 的兼容性测试**

保留现有测试，并将测试名改清楚：

```python
    def test_decision_quality_is_zero_without_decision_log(self) -> None:
        self.assertTrue(self.score_log.records)
        for record in self.score_log.records:
            self.assertIsNone(record.decision_id)
            self.assertEqual(record.decision_quality_score, 0)
```

- [ ] **步骤 4：新增 D2 正向评分测试**

在 `tests/test_scoring.py` 增加：

```python
    def test_d2_decision_log_attaches_decision_id_and_preserves_quality_zero(self) -> None:
        records = {record.event_id: record for record in self.d2_score_log.records}

        self.assertEqual(records["g001_e019"].decision_id, "g001_d007")
        self.assertEqual(records["g001_e019"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e019"].rules_triggered)

        self.assertEqual(records["g001_e025"].decision_id, "g001_d009")
        self.assertEqual(records["g001_e025"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e025"].rules_triggered)

        self.assertEqual(records["g001_e035"].decision_id, "g001_d010")
        self.assertEqual(records["g001_e035"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e035"].rules_triggered)
```

Rationale for the expected records:

- `g001_e019` is p4 voting p1, matched to `g001_d007`.
- `g001_e025` is p4 poisoning p2, matched to `g001_d009`.
- `g001_e035` is p6 voting p1, matched to `g001_d010`.

D2 does NOT assign `decision_quality_score > 0`. The rule `rubric:G.1.decision_logged` is a traceability marker, not a scoring rule. Positive decision quality waits for S5 AI semantic judgment (Rubric G.1 Step 3).

- [ ] **步骤 5：新增 random/default 不加分测试**

```python
    def test_d2_default_or_empty_ref_decisions_keep_quality_zero(self) -> None:
        records = {record.event_id: record for record in self.d2_score_log.records}

        self.assertEqual(records["g001_e020"].decision_id, "g001_d008")
        self.assertEqual(records["g001_e020"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.no_decision_quality_for_default", records["g001_e020"].rules_triggered)
```

- [ ] **步骤 6：新增非法 visibility refs 扣规则分测试**

```python
    def test_d2_illegal_visible_info_ref_penalizes_rule_integrity(self) -> None:
        raw = load_json("docs/gold-game/g001-decision-log.json")
        raw["decisions"] = [
            {
                "decision_id": "bad_d001",
                "actor": "p5",
                "decision_scope": "single",
                "consensus_id": None,
                "phase": "day",
                "action": "player_vote",
                "target": "p3",
                "visible_info_refs": ["g001_e008"],
                "reason_summary": "p5 illegally relies on the seer-only check result.",
                "decision_type": "inference_based",
                "confidence": 0.5,
                "strategy_tag": "illegal_ref_test",
            }
        ]
        decision_log = parse_decision_log(raw, self.game)

        score_log = score_game(self.game, decision_log=decision_log)
        records = {record.event_id: record for record in score_log.records}

        self.assertEqual(records["g001_e020"].decision_id, "bad_d001")
        self.assertEqual(records["g001_e020"].decision_quality_score, 0)
        self.assertEqual(records["g001_e020"].rule_integrity_score, -3)
        self.assertIn("rubric:G.1.illegal_visible_info_ref", records["g001_e020"].rules_triggered)
```

- [ ] **步骤 7：新增 summary 聚合测试**

```python
    def test_d2_metrics_summary_reflects_decision_log_input(self) -> None:
        payload = metrics_summary_to_dict(self.d2_metrics)
        decision_scores = payload["score_summary"]["player_decision_quality_scores"]

        # D2 does not assign positive decision_quality_score.
        # All scores remain 0; the value is in decision_id traceability and rule_integrity checks.
        self.assertEqual(decision_scores["p4"], 0)
        self.assertEqual(decision_scores["p6"], 0)
        self.assertEqual(decision_scores["p5"], 0)
```

- [ ] **步骤 8：运行测试，确认失败原因是功能未实现**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring
```

预期结果：失败，主要错误包括：

```text
TypeError: score_game() got an unexpected keyword argument 'decision_log'
```

If the error is not caused by the missing `decision_log` argument or missing `decision_id` field, stop and check whether D2 has already been merged.

---

### 任务 2：Add optional Decision Log fields and helper types to scorer

**文件：**
- 修改：`src/werewolf_eval/scoring.py`
- 测试：`tests/test_scoring.py`

- [ ] **步骤 1：导入 Decision Log 类型**

在 `src/werewolf_eval/scoring.py` 顶部加入：

```python
from werewolf_eval.decision_log import Decision, DecisionLog
```

- [ ] **步骤 2：扩展 ScoreRecord**

将 `ScoreRecord` 增加 `decision_id` 字段，放在 `event_id` 后：

```python
@dataclass(frozen=True)
class ScoreRecord:
    score_id: str
    event_id: str
    decision_id: str | None
    actor: str
    scope: str
    round: int
    phase: str
    action_type: str
    target: str
    outcome_score: int
    decision_quality_score: int
    rule_integrity_score: int
    rules_triggered: list[str]
    evidence_event_ids: list[str]
    notes: str
```

- [ ] **步骤 3：新增 DecisionAssessment dataclass**

放在 `ScoreRecord` 后：

```python
@dataclass(frozen=True)
class DecisionAssessment:
    decision_id: str | None
    decision_quality_score: int
    rule_integrity_score: int
    rules_triggered: list[str]
    evidence_event_ids: list[str]
    notes: list[str]
```

- [ ] **步骤 4：更新 `_record` 签名**

将 `_record` 改为接受 optional assessment：

```python
def _record(
    event: Event,
    outcome_score: int,
    rules_triggered: list[str],
    evidence_event_ids: list[str],
    notes: str,
    assessment: DecisionAssessment | None = None,
) -> ScoreRecord:
    decision_rules = assessment.rules_triggered if assessment else []
    decision_evidence = assessment.evidence_event_ids if assessment else []
    decision_notes = assessment.notes if assessment else []
    return ScoreRecord(
        score_id=f"s2_g001_{event.event_id.split('_')[-1]}",
        event_id=event.event_id,
        decision_id=assessment.decision_id if assessment else None,
        actor=event.actor,
        scope=_scope_for_actor(event.actor),
        round=event.round,
        phase=event.phase,
        action_type=event.type,
        target=event.target,
        outcome_score=outcome_score,
        decision_quality_score=assessment.decision_quality_score if assessment else 0,
        rule_integrity_score=assessment.rule_integrity_score if assessment else 0,
        rules_triggered=rules_triggered + decision_rules,
        evidence_event_ids=list(dict.fromkeys(evidence_event_ids + decision_evidence)),
        notes=" ".join([notes] + decision_notes).strip(),
    )
```

- [ ] **步骤 5：运行局部测试**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring
```

预期结果：仍失败，但不应再出现 `ScoreRecord.__init__()` 缺字段之类的 dataclass 构造错误。失败点应集中在 `score_game(decision_log=...)` 未实现。

---

### 任务 3：Implement decision-to-event matching

**文件：**
- 修改：`src/werewolf_eval/scoring.py`
- 测试：`tests/test_scoring.py`

- [ ] **步骤 1：添加 score-relevant action set**

放在 `SCORE_RELEVANT_EVENT_TYPES` 旁：

```python
SCORE_RELEVANT_DECISION_ACTIONS = SCORE_RELEVANT_EVENT_TYPES
```

- [ ] **步骤 2：添加 actor matching helper**

```python
def _decision_actor_matches_event(decision: Decision, event: Event) -> bool:
    return decision.actor == event.actor
```

For D2, do not expand `wolf_team` into individual werewolves. The current `werewolf_kill` event actor is already `wolf_team`, and the current Decision Log uses `wolf_team` for team kill decisions.

- [ ] **步骤 3：添加 target matching helper**

```python
def _decision_target_matches_event(decision: Decision, event: Event) -> bool:
    return decision.target == event.target
```

- [ ] **步骤 4：添加 phase/action matching helper**

```python
def _decision_matches_event(decision: Decision, event: Event) -> bool:
    return (
        decision.action == event.type
        and decision.phase == event.phase
        and _decision_actor_matches_event(decision, event)
        and _decision_target_matches_event(decision, event)
    )
```

- [ ] **步骤 5：添加 matching index builder**

```python
def _decision_by_event_id(game: GameLog, decision_log: DecisionLog | None) -> dict[str, Decision]:
    if decision_log is None:
        return {}

    mapping: dict[str, Decision] = {}
    used_decision_ids: set[str] = set()
    relevant_events = [event for event in game.events if event.type in SCORE_RELEVANT_EVENT_TYPES]

    for event in relevant_events:
        candidates = [
            decision
            for decision in decision_log.decisions
            if decision.decision_id not in used_decision_ids
            and decision.action in SCORE_RELEVANT_DECISION_ACTIONS
            and _decision_matches_event(decision, event)
        ]
        if len(candidates) == 1:
            decision = candidates[0]
            mapping[event.event_id] = decision
            used_decision_ids.add(decision.decision_id)
        elif len(candidates) > 1:
            raise ValueError(
                f"ambiguous Decision Log match for event {event.event_id}: "
                f"{[decision.decision_id for decision in candidates]}"
            )

    return mapping
```

- [ ] **步骤 6：运行局部测试**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring
```

预期结果：仍失败，因为 `score_game` has not yet accepted `decision_log` and `_record` calls have not yet passed assessment. There should be no syntax or import errors.

---

### 任务 4：Implement deterministic visibility and decision quality assessment

**文件：**
- 修改：`src/werewolf_eval/scoring.py`
- 测试：`tests/test_scoring.py`

- [ ] **步骤 1：添加 role lookup helper**

```python
def _role_for_actor(game: GameLog, actor: str) -> str | None:
    if actor == "wolf_team":
        return "werewolf_team"
    if actor in game.player_ids:
        return _role_of(game, actor)
    return None
```

- [ ] **步骤 2：添加 visibility helper**

```python
def _event_visible_to_decision_actor(game: GameLog, event: Event, actor: str) -> bool:
    if event.visibility in {"public", "all"}:
        return True

    if actor == "wolf_team":
        if event.visibility == "werewolf_team":
            return True
        if event.visibility == "specific_player_ids":
            return event.target in game.player_ids and _team_of(game, event.target) == "werewolf"
        return False

    if actor not in game.player_ids:
        return False

    actor_role = _role_of(game, actor)
    if event.visibility == actor_role:
        return True

    if event.visibility == "werewolf_team":
        return actor_role == "werewolf"

    if event.visibility == "specific_player_ids":
        return event.target == actor

    return False
```

D2 does not use natural-language reasoning for visibility. It only uses event `visibility`, event `target`, actor role, and team.

- [ ] **步骤 3：添加 assessment function**

```python
def _assess_decision(game: GameLog, decision: Decision | None) -> DecisionAssessment:
    if decision is None:
        return DecisionAssessment(
            decision_id=None,
            decision_quality_score=0,
            rule_integrity_score=0,
            rules_triggered=[],
            evidence_event_ids=[],
            notes=[],
        )

    evidence_event_ids = list(decision.visible_info_refs)
    illegal_refs = [
        ref
        for ref in decision.visible_info_refs
        if not _event_visible_to_decision_actor(game, game.event_by_id(ref), decision.actor)
    ]

    if illegal_refs:
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=0,
            rule_integrity_score=-3,
            rules_triggered=["rubric:G.1.illegal_visible_info_ref"],
            evidence_event_ids=evidence_event_ids,
            notes=[
                f"Decision {decision.decision_id} references non-visible events {illegal_refs}; D2 assigns no decision quality and applies rule_integrity_score -3."
            ],
        )

    if not decision.visible_info_refs:
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=0,
            rule_integrity_score=0,
            rules_triggered=["rubric:G.1.no_decision_quality_without_refs"],
            evidence_event_ids=evidence_event_ids,
            notes=[f"Decision {decision.decision_id} has no visible_info_refs; D2 keeps decision_quality_score 0."],
        )

    if decision.decision_type in {"random", "default"}:
        return DecisionAssessment(
            decision_id=decision.decision_id,
            decision_quality_score=0,
            rule_integrity_score=0,
            rules_triggered=["rubric:G.1.no_decision_quality_for_default"],
            evidence_event_ids=evidence_event_ids,
            notes=[f"Decision {decision.decision_id} is {decision.decision_type}; D2 keeps decision_quality_score 0."],
        )

    # D2 does NOT assign decision_quality_score > 0.
    # Positive scoring requires S5 AI semantic judgment (Rubric G.1 Step 3).
    # This branch records the decision_id and marks traceability only.
    return DecisionAssessment(
        decision_id=decision.decision_id,
        decision_quality_score=0,
        rule_integrity_score=0,
        rules_triggered=["rubric:G.1.decision_logged"],
        evidence_event_ids=evidence_event_ids,
        notes=[
            f"Decision {decision.decision_id} has visible refs and non-random type {decision.decision_type}; D2 records decision_id and preserves decision_quality_score=0. Positive scoring requires S5 AI semantic judgment."
        ],
    )
```

- [ ] **步骤 4：run scoring tests**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring
```

预期结果：仍失败 until `score_game` wires the assessment into `_record` calls. No syntax/import errors should appear.

---

### 任务 5：Wire assessment into score_game and per-event scorers

**文件：**
- 修改：`src/werewolf_eval/scoring.py`
- 测试：`tests/test_scoring.py`

- [ ] **步骤 1：update scorer helper signatures**

Change these functions to accept `assessment: DecisionAssessment | None = None` and pass it to `_record`:

```python
def _score_werewolf_kill(game: GameLog, event: Event, assessment: DecisionAssessment | None = None) -> ScoreRecord:
    ...
    return _record(event, outcome, [rule], evidence, notes, assessment)
```

Apply the same pattern to:

```text
_score_seer_check
_score_witch_save
_score_witch_poison
_score_player_vote
```

Every existing `_record(...)` return inside these functions must become `_record(..., assessment)`.

- [ ] **步骤 2：update `score_game` signature and body**

Change `score_game` to:

```python
def score_game(game: GameLog, decision_log: DecisionLog | None = None) -> ScoreLog:
    eliminated_by_round = _eliminated_target_by_round(game)
    decisions_by_event = _decision_by_event_id(game, decision_log)
    records: list[ScoreRecord] = []

    for event in game.events:
        if event.type not in SCORE_RELEVANT_EVENT_TYPES:
            continue
        assessment = _assess_decision(game, decisions_by_event.get(event.event_id))
        if event.type == "werewolf_kill":
            records.append(_score_werewolf_kill(game, event, assessment))
        elif event.type == "seer_check":
            records.append(_score_seer_check(game, event, assessment))
        elif event.type == "witch_save":
            records.append(_score_witch_save(game, event, assessment))
        elif event.type == "witch_poison":
            records.append(_score_witch_poison(game, event, assessment))
        elif event.type == "player_vote":
            records.append(_score_player_vote(game, event, eliminated_by_round, assessment))

    return ScoreLog(
        score_log_id="s2_g001_expected_score_log",
        game_id=game.game_id,
        source_game_log="docs/gold-game/g001-game-log.json",
        source_label="[deterministic]" if decision_log is None else "[deterministic][decision-log]",
        phase="Phase 1" if decision_log is None else "Phase 2A-D2",
        scoring_boundary=_scoring_boundary(decision_log is not None),
        records=records,
    )
```

- [ ] **步骤 3：update `_scoring_boundary`**

Change it to:

```python
def _scoring_boundary(has_decision_log: bool = False) -> ScoringBoundary:
    if has_decision_log:
        return ScoringBoundary(
            decision_quality_score=0,
            decision_quality_reason="D2 implements Rubric G.1 Step 1-2 only: deterministic visibility check and decision-to-event traceability. No AI semantic judgment; positive decision_quality_score waits for S5.",
            ai_annotations="none; S5 not enabled",
            rule_integrity_default=0,
            rule_integrity_reason="Illegal visible_info_refs are deterministic rule-integrity violations (-3); otherwise records default to 0.",
        )
    return ScoringBoundary(
        decision_quality_score=0,
        decision_quality_reason="No Decision Log supplied. All decision_quality_score values are fixed at 0.",
        ai_annotations="none",
        rule_integrity_default=0,
        rule_integrity_reason="No Decision Log visibility checks were run.",
    )
```

- [ ] **步骤 4：run scoring tests**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring
```

预期结果：new D2 tests should pass or fail only because current gold fixture refs need deterministic visibility cleanup. Existing snapshot equality tests may fail because snapshots still reflect pre-D2 schema. Continue to task 6.

---

### 任务 6：Clean gold Decision Log refs for deterministic visibility

**文件：**
- 修改：`docs/gold-game/g001-decision-log.json`
- 测试：`tests/test_decision_log.py`
- 测试：`tests/test_scoring.py`

- [ ] **步骤 1：update refs that are not actor-visible under D2 rules**

Apply these exact changes to `docs/gold-game/g001-decision-log.json`:

```jsonc
// g001_d002: p3 first-night seer check has no prior public reasoning ref in the current Game Log.
"visible_info_refs": []

// g001_d003: p4 save decision may reference the werewolf kill target event because witch visibility is not modeled as a separate death-notice event in the current Game Log. Keep as is.
"visible_info_refs": ["g001_e007"]

// g001_d004: p3 may reference own seer check result.
"visible_info_refs": ["g001_e008"]

// g001_d005: p1 may reference public p3 speech.
"visible_info_refs": ["g001_e010"]

// g001_d006: p2 may reference public p1 speech.
"visible_info_refs": ["g001_e011"]

// g001_d007: p4 may reference public speeches.
"visible_info_refs": ["g001_e010", "g001_e013"]

// g001_d008: p5 may reference public speech but decision_type default keeps quality 0.
"visible_info_refs": ["g001_e014"]

// g001_d009: p4 may reference public vote/reveal events.
"visible_info_refs": ["g001_e017", "g001_e023"]

// g001_d010: p6 may reference public p2 reveal and own/p4 public argument context.
"visible_info_refs": ["g001_e029", "g001_e032"]
```

Only change entries that differ from the current file. Preserve all other fields.

- [ ] **步骤 2：run Decision Log validator tests**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log
```

预期结果：

```text
Ran 8 tests ... OK
```

- [ ] **步骤 3：run scoring tests**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring
```

预期 result: D2 behavior tests pass. Snapshot equality tests may still fail until generated JSON fixtures are refreshed in task 8.

---

### 任务 7：Add CLI support for Decision Log input

**文件：**
- 修改：`src/werewolf_eval/score_game.py`
- 修改：`src/werewolf_eval/render_demo.py`
- 测试：`tests/test_scoring.py`
- 测试：`tests/test_render_demo.py`

- [ ] **步骤 1：update score_game.py imports**

Add:

```python
from werewolf_eval.decision_log import load_decision_log
```

- [ ] **步骤 2：add score CLI argument**

In `main()` after the `path` argument:

```python
parser.add_argument("--decision-log", help="Optional path to Decision Log JSON for D2 deterministic decision-quality scoring")
```

- [ ] **步骤 3：load optional Decision Log and pass into scorer**

Replace:

```python
score_log = score_game(game)
```

with:

```python
decision_log = load_decision_log(args.decision_log, game) if args.decision_log else None
score_log = score_game(game, decision_log=decision_log)
```

- [ ] **步骤 4：print D2 status**

After existing prints, add:

```python
print(f"decision_log={'enabled' if decision_log else 'disabled'}")
print(f"decision_quality_total={sum(record.decision_quality_score for record in score_log.records)}")
```

- [ ] **步骤 5：update render_demo.py imports**

Add:

```python
from werewolf_eval.decision_log import load_decision_log
```

- [ ] **步骤 6：update render demo writer signature**

Change:

```python
def write_demo_html(game_log_path: str | Path, output_path: str | Path) -> None:
```

to:

```python
def write_demo_html(game_log_path: str | Path, output_path: str | Path, decision_log_path: str | Path | None = None) -> None:
```

Inside it:

```python
game = load_game_log(game_log_path)
decision_log = load_decision_log(decision_log_path, game) if decision_log_path else None
score_log = score_game(game, decision_log=decision_log)
metrics = summarize_metrics(game, score_log)
attribution = attribute_game(game, score_log, metrics)
context = build_demo_context(game, score_log, metrics, attribution)
```

- [ ] **步骤 7：add render CLI argument**

In `render_demo.py main()` add:

```python
parser.add_argument("--decision-log", help="Optional path to Decision Log JSON for D2 deterministic decision-quality scoring")
```

Change writer call to:

```python
write_demo_html(args.path, args.html_out, args.decision_log)
```

- [ ] **步骤 8：add CLI smoke test in `tests/test_scoring.py`**

```python
    def test_score_game_cli_accepts_decision_log(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.score_game",
                str(ROOT / "docs/gold-game/g001-game-log.json"),
                "--decision-log",
                str(ROOT / "docs/gold-game/g001-decision-log.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("decision_log=enabled", result.stdout)
        self.assertIn("decision_quality_total=", result.stdout)
```

If `subprocess` is not already imported in `tests/test_scoring.py`, add:

```python
import subprocess
```

- [ ] **步骤 9：run relevant tests**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring tests.test_render_demo
```

预期结果：D2 CLI smoke passes. Render demo tests may fail on expected boundary copy until task 9.

---

### 任务 8：Refresh generated gold JSON fixtures

**文件：**
- 修改：`docs/gold-game/s2-score-log.json`
- 修改：`docs/gold-game/s2-metrics-summary.json`
- 修改：`src/werewolf_eval/scoring.py`（`summarize_metrics` source_label 透传）
- 测试：`tests/test_scoring.py`

- [ ] **步骤 0：fix MetricsSummary source_label traceability**

Before regenerating fixtures, update `summarize_metrics` in `src/werewolf_eval/scoring.py` to derive `source_label` from the ScoreLog instead of hardcoding `"[deterministic]"`:

```python
# Before (hardcoded):
source_label="[deterministic]",

# After (transparent from ScoreLog):
source_label=score_log.source_label,
```

This ensures the MetricsSummary carries the same provenance label as the ScoreLog that produced it (e.g. `"[deterministic][decision-log]"` when Decision Log is supplied).

- [ ] **步骤 1：regenerate fixtures with Decision Log enabled**

运行：

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --score-log-out docs/gold-game/s2-score-log.json --metrics-out docs/gold-game/s2-metrics-summary.json
```

预期输出包含：

```text
scored game_id=g001
score_records=14
winner=villager
game_length=2
wolf_team_outcome_score=2
decision_log=enabled
decision_quality_total=
```

The exact `decision_quality_total` should be greater than 0.

- [ ] **步骤 2：inspect generated Score Log**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
score = json.loads(Path('docs/gold-game/s2-score-log.json').read_text(encoding='utf-8'))
records = score['records']
print(score['phase'])
print(score['source_label'])
print(sum(r['decision_quality_score'] for r in records))
print([r for r in records if r['decision_id']])
PY
```

预期输出：

```text
Phase 2A-D2
[deterministic][decision-log]
```

The third printed line is an integer greater than 0. The fourth printed line is a non-empty list with at least `g001_d007`, `g001_d009`, and `g001_d010` attached to score records.

- [ ] **步骤 3：run scoring tests**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_scoring
```

预期结果：

```text
OK
```

---

### 任务 9：Update runtime demo context and HTML boundary copy

**文件：**
- 修改：`src/werewolf_eval/render_demo.py`
- 修改：`tests/test_render_demo.py`
- 修改：`docs/demo/phase2-runtime-demo.html`

- [ ] **步骤 1：compute decision quality total in demo context**

In `build_demo_context`, after `score_summary = metrics_payload["score_summary"]`, add:

```python
decision_quality_total = sum(record["decision_quality_score"] for record in score_payload["records"])
decision_log_enabled = score_payload["phase"] == "Phase 2A-D2"
```

- [ ] **步骤 2：keep leaderboard deterministic row at 0.0**

D2 does not assign positive `decision_quality_score`, so the leaderboard row stays at 0.0. Do not update the value. Add a comment noting this is a runtime demo convention — real multi-game Rubric-normalized `avg_decision_quality_score` (sum / total_actions) belongs to L1 real Leaderboard:

```python
"avg_decision_quality_score": 0.0,  # D2 demo convention: decision_quality_score waits for S5 AI semantic judgment
```

Do not update mock rows; keep them at 0.0.

- [ ] **步骤 3：add D2 fields to context score block**

Inside context `"score"` object, add:

```python
"decision_log_enabled": decision_log_enabled,
"decision_quality_total": decision_quality_total,
```

- [ ] **步骤 4：update boundary copy**

Replace the current warning paragraph:

```html
This is not real AI Agent gameplay, not real Decision Log / Consensus Log collection, and not a real multi-model Leaderboard. 当前 decision_quality_score 固定为 0。
```

with conditional Python-rendered text. Before the return string, define:

```python
if context["score"]["decision_log_enabled"]:
    boundary_copy = "This is not real AI Agent gameplay, not real Consensus Log collection, not AI semantic labeling, and not a real multi-model Leaderboard. Decision Log is connected to scoring via D2 deterministic Step 1-2 (visibility check + decision_id traceability), but decision_quality_score remains 0 (positive scoring waits for S5 AI semantic judgment)."
    decision_copy = "decision_quality_score: D2 visibility check + decision_id traceability complete; positive scoring still 0 (waiting for S5)."
else:
    boundary_copy = "This is not real AI Agent gameplay, not real Decision Log / Consensus Log collection, and not a real multi-model Leaderboard. No Decision Log supplied; decision_quality_score fixed at 0."
    decision_copy = "decision_quality_score: no Decision Log supplied; fixed at 0."
```

Then use:

```python
<section class="warning"><h2>边界声明</h2><p>{_html(boundary_copy)}</p></section>
```

and:

```python
<section><h2>确定性指标</h2><p>Score records: {_html(context["score"]["records"])} {_html(context["score"]["source_label"])}。{_html(decision_copy)}</p></section>
```

- [ ] **步骤 5：update render tests**

In `tests/test_render_demo.py`, add or update a test to call `write_demo_html` with Decision Log:

```python
def test_write_demo_html_with_decision_log_shows_d2_boundary(self) -> None:
    output = ROOT / "docs/demo/test-phase2-d2-runtime-demo.html"
    try:
        write_demo_html(
            ROOT / "docs/gold-game/g001-game-log.json",
            output,
            ROOT / "docs/gold-game/g001-decision-log.json",
        )
        html = output.read_text(encoding="utf-8")
        self.assertIn("D2 deterministic Step 1-2", html)
        self.assertIn("D2 visibility check", html)
        self.assertIn("waiting for S5", html)
    finally:
        output.unlink(missing_ok=True)
```

If `ROOT` or `write_demo_html` names differ in the existing file, adapt only to existing local names; do not create a separate test helper.

- [ ] **步骤 6：regenerate runtime demo**

运行：

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --html-out docs/demo/phase2-runtime-demo.html
```

预期输出：

```text
rendered_demo_html=docs/demo/phase2-runtime-demo.html
```

- [ ] **步骤 7：run render tests**

运行：

```bash
PYTHONPATH=src python -m unittest tests.test_render_demo
```

预期结果：

```text
OK
```

---

### 任务 10：Update task status and acceptance docs

**文件：**
- 修改：`docs/TASKS.md`
- 读取：`docs/ROADMAP.md`
- 测试：文档 grep checks

- [ ] **步骤 1：update D2 status**

In `docs/TASKS.md`, change D2 section from:

```markdown
- 状态：`candidate_next`（Phase 2A evaluator runtime closure；下一步推荐任务）
```

to:

```markdown
- 状态：`completed`（Phase 2A evaluator runtime closure；Decision Log 已接入 deterministic scoring）
```

- [ ] **步骤 2：add D2 outputs**

Under D2, add:

```markdown
- 产出：`src/werewolf_eval/scoring.py` + `src/werewolf_eval/score_game.py` + `src/werewolf_eval/render_demo.py` + `docs/gold-game/s2-score-log.json` + `docs/gold-game/s2-metrics-summary.json` + `docs/demo/phase2-runtime-demo.html`。
```

- [ ] **步骤 3：update D2 boundary line**

Keep the no-AI boundary explicit:

```markdown
- 边界：只实现 Rubric G.1 Step 1-2 deterministic visibility 检查和 decision_id 追溯；不调用 AI，不启用 S5，不做 Consensus Log，不宣称 `decision_quality_score` 完整可用（正向评分等待 S5 AI 语义判断）。
```

- [ ] **步骤 4：add UX acceptance row**

Add this row to the UX Acceptance table:

```markdown
| D2 | Decision Log scoring 摘要 + runtime demo D2 边界声明 | 传入同一 Game Log + Decision Log 后，Score Log 中部分记录带 `decision_id` 和非零 `decision_quality_score`；无 Decision Log 时保持全 0；页面明确标注 D2 只含 deterministic Step 1-2，不含 S5 AI 语义判断 |
```

- [ ] **步骤 5：add Demo 4 section**

After Demo 3, add:

```markdown
**Demo 4：Phase 2 Decision Log scoring integration**

- 状态：`completed`（`docs/demo/phase2-runtime-demo.html` 使用 Decision Log 生成 D2 deterministic decision score）
- 触发条件：D2 完成。
- 演示内容：运行时读取 Game Log + Decision Log → 计算 Score Log / Metrics Summary → 输出带 D2 边界声明的 HTML demo。
- 验收：同一输入稳定输出 `decision_id` 追溯到 Score Record，非法 refs 触发 `rule_integrity_score = -3`；页面明确说明 Decision Log 已接入但 `decision_quality_score` 仍为 0（正向评分等待 S5）。
```

- [ ] **步骤 6：run docs checks**

运行：

```bash
grep -c "D2 deterministic" docs/TASKS.md docs/demo/phase2-runtime-demo.html
grep -c "S5 AI" docs/TASKS.md docs/demo/phase2-runtime-demo.html
grep -c "candidate_next" docs/TASKS.md
```

预期结果：First two commands should print counts greater than 0. The third command should print `0` after D2 is marked completed.

---

### 任务 11：Full validation and final review

**文件：**
- 验证：`src/werewolf_eval/scoring.py`
- 验证：`src/werewolf_eval/score_game.py`
- 验证：`src/werewolf_eval/render_demo.py`
- 验证：`tests/test_scoring.py`
- 验证：`tests/test_render_demo.py`
- 验证：`docs/TASKS.md`
- 验证：generated fixtures and demo files

- [ ] **步骤 1：run Game Log validation**

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
```

预期输出：

```text
validated game_id=g001 players=6 events=38 winner=villager end_round=2
```

- [ ] **步骤 2：run Decision Log validation**

```bash
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
```

预期输出：

```text
validated decision_log_id=d1_g001_decision_log game_id=g001 decisions=10 source_label=[人工 gold sample]
```

- [ ] **步骤 3：run D2 scorer command**

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json
```

预期输出 includes:

```text
scored game_id=g001
score_records=14
winner=villager
game_length=2
wolf_team_outcome_score=2
decision_log=enabled
decision_quality_total=
```

The value after `decision_quality_total=` will be 0. D2 does not assign positive decision_quality_score; the value is in decision_id traceability and rule_integrity checks.

- [ ] **步骤 4：run HTML render command**

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --html-out docs/demo/phase2-runtime-demo.html
```

预期输出：

```text
rendered_demo_html=docs/demo/phase2-runtime-demo.html
```

- [ ] **步骤 5：run full test suite**

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

预期输出：

```text
OK
```

The number of tests should be greater than the previous 29 because D2 adds scoring and render tests.

- [ ] **步骤 6：run diff boundary checks**

```bash
git diff --name-only main...HEAD
```

Expected changed files should be limited to:

```text
docs/TASKS.md
docs/demo/phase2-runtime-demo.html
docs/gold-game/g001-decision-log.json
docs/gold-game/s2-metrics-summary.json
docs/gold-game/s2-score-log.json
src/werewolf_eval/render_demo.py
src/werewolf_eval/score_game.py
src/werewolf_eval/scoring.py
tests/test_render_demo.py
tests/test_scoring.py
```

If `.oh-my-harness/tree.md` appears, verify whether files were added/deleted/renamed. If not, revert tree changes.

- [ ] **步骤 7：run no-forbidden-scope checks**

```bash
git diff main...HEAD -- docs/EVALUATION_RUBRIC.md
git diff --name-only main...HEAD | grep -E 'consensus|provider|agent_runtime|game_engine|semantic_label|ai_' || true
grep -R "api_key\|provider\|prompt\|model call\|semantic labeling" -n src tests docs/TASKS.md || true
```

预期结果：

- First command prints no diff.
- Second command prints nothing except paths already known to include historical text. It must not show new S4/S5/G1 implementation files.
- Third command must not reveal newly implemented AI/provider behavior. Existing historical documentation text is acceptable only if unchanged.

- [ ] **步骤 8：final checkpoint report**

Use `docs/CHECKPOINT_TEMPLATE.md` and include:

```text
Task: D2 Decision Log scoring integration
Scope completed: deterministic Rubric G.1 Step 1-2 only
No AI / S5: confirmed
No Consensus Log / S4: confirmed
No G1 gameplay: confirmed
Validation commands: include outputs from steps 1-5
Changed files: paste output from step 6
Known limitation: D2 connects Decision Log to scoring with visibility checks and decision_id traceability, but decision_quality_score remains 0 across all records; positive semantic scoring is deferred to S5
```

---

## Implementation PR Description Draft

```markdown
## Summary

Implements D2 Decision Log scoring integration for Werewolf-agent Phase 2A evaluator runtime closure.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--d2-decision-log-scoring-integration-plan.md`

## Scope

- Adds optional Decision Log input to the deterministic scorer.
- Maps accepted Decision Log entries onto score-relevant Game Log events.
- Implements Rubric G.1 Step 1-2 only:
  - deterministic visibility checks for `visible_info_refs` (illegal refs → `rule_integrity_score = -3`)
  - empty refs or `random/default` decision types keep `decision_quality_score = 0`
  - legal refs plus non-random decision types: `decision_id` attached, marked `rubric:G.1.decision_logged`, but `decision_quality_score` stays 0 (positive scoring waits for S5 AI semantic judgment)
- Adds optional `--decision-log` support to `score_game.py` and `render_demo.py`.
- Refreshes Score Log / Metrics Summary fixtures and Phase 2 runtime HTML demo.
- Updates TASKS status and UX / demo acceptance for D2.

## Boundary

- No AI calls.
- No S5 semantic labeling.
- No S4 Consensus Log.
- No G1 real AI Agent gameplay.
- No L1 real multi-game Leaderboard.
- No changes to `docs/EVALUATION_RUBRIC.md`.
- Does not claim full `decision_quality_score` quality; D2 is deterministic Step 1-2 only.

## Validation

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --html-out docs/demo/phase2-runtime-demo.html
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

## Expected changed files

```text
docs/TASKS.md
docs/demo/phase2-runtime-demo.html
docs/gold-game/g001-decision-log.json
docs/gold-game/s2-metrics-summary.json
docs/gold-game/s2-score-log.json
src/werewolf_eval/render_demo.py
src/werewolf_eval/score_game.py
src/werewolf_eval/scoring.py
tests/test_render_demo.py
tests/test_scoring.py
```
```
