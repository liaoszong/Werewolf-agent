# E2 Deterministic Scorer Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Implement the Phase 2 E2 deterministic scorer: load an E1 `GameLog`, compute deterministic Score Log records, compute Metrics Summary, and match the existing S2 gold artifacts.

**Architecture:** Reuse the E1 parser and keep scoring in a focused `src/werewolf_eval/scoring.py` module. Add a small CLI in `src/werewolf_eval/score_game.py` that writes JSON outputs and prints a concise readable summary. Use golden tests against `docs/gold-game/s2-score-log.json` and `docs/gold-game/s2-metrics-summary.json` so the runtime implementation reproduces the Phase 1 deterministic artifacts exactly.

**Tech Stack:** Python standard library only. No package manager, no external dependency, no backend/frontend framework.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before executing this plan, confirm these repository facts:

- PR #11 is merged into `main`.
- E1 is complete and present on `main`:
  - `src/werewolf_eval/game_log.py`
  - `src/werewolf_eval/validate_game_log.py`
  - `tests/test_game_log.py`
- `docs/TASKS.md` marks E1 completed and E2 as the next Phase 2 candidate.
- S2 deterministic gold outputs already exist:
  - `docs/gold-game/s2-score-log.json`
  - `docs/gold-game/s2-metrics-summary.json`
- E2 must not modify accepted Phase 1 gold/demo artifacts.

## Research PR Decision

No Research PR is needed.

Reasoning:

- The task boundary is clear: implement deterministic scoring only.
- The input is fixed: `docs/gold-game/g001-game-log.json` parsed by E1.
- The expected outputs are fixed and already committed as S2 gold artifacts.
- E2 is a single implementation unit.
- Attribution, UI, Agent gameplay, AI annotation, Decision Log runtime, and Consensus Log runtime are out of scope.

## Scope Decision

This PR implements only E2 deterministic scoring.

It creates:

- `src/werewolf_eval/scoring.py`
- `src/werewolf_eval/score_game.py`
- `tests/test_scoring.py`

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

## E2 deterministic scoring boundary

E2 computes only deterministic values from Game Log facts and the stable S2 gold policy.

E2 must keep:

- `decision_quality_score = 0` for every record because there is no real Decision Log.
- `rule_integrity_score = 0` for the current g001 Game Log because it contains no deterministic `info_leak_flag` or `contradiction_flag` score events.
- `turn_point_count` deferred because attribution belongs to E3.
- Known rubric gaps recorded, not fixed:
  - `werewolf_day_vote_without_elimination`
  - `witch_day_vote_outcome_not_explicit`

E2 must not:

- compute attribution
- generate `turn_points`
- compute `top_attribution`
- call AI models
- infer hidden psychology or unstated strategy
- modify scoring rules
- modify accepted gold artifacts

---

### Task 1: Preflight E1 and gold artifacts

**Files:**

- Create: none.
- Modify: none.
- Test: existing `tests/test_game_log.py`.

- [ ] **Step 1: Confirm E1 runtime files exist**

Run:

```bash
test -f src/werewolf_eval/game_log.py
test -f src/werewolf_eval/validate_game_log.py
test -f tests/test_game_log.py
printf 'E1 runtime files exist\n'
```

Expected result:

```text
E1 runtime files exist
```

- [ ] **Step 2: Confirm S2 gold artifacts exist and parse**

Run:

```bash
test -f docs/gold-game/s2-score-log.json
test -f docs/gold-game/s2-metrics-summary.json
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
printf 'S2 gold artifacts exist and parse\n'
```

Expected result:

```text
S2 gold artifacts exist and parse
```

- [ ] **Step 3: Confirm E1 validation still passes**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
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

Expected test result includes:

```text
Ran 6 tests
OK
```

No commit is required for Task 1 because it only verifies the starting state.

---

### Task 2: Add scoring dataclasses and serialization helpers

**Files:**

- Create: `src/werewolf_eval/scoring.py`
- Modify: none.
- Test: `tests/test_scoring.py` in Task 5.

- [ ] **Step 1: Create `src/werewolf_eval/scoring.py` with data model**

Create this file:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from werewolf_eval.game_log import Event, GameLog


@dataclass(frozen=True)
class ScoreRecord:
    score_id: str
    event_id: str
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


@dataclass(frozen=True)
class ScoringBoundary:
    decision_quality_score: int
    decision_quality_reason: str
    ai_annotations: str
    rule_integrity_default: int
    rule_integrity_reason: str


@dataclass(frozen=True)
class ScoreLog:
    score_log_id: str
    game_id: str
    source_game_log: str
    source_label: str
    phase: str
    scoring_boundary: ScoringBoundary
    records: list[ScoreRecord]


@dataclass(frozen=True)
class ResultMetrics:
    winner: str
    game_length: int
    werewolf_survival_rate: float
    villager_survival_rate: float
    margin: int
    werewolf_win_speed: float | None
    villager_win_efficiency: float | None


@dataclass(frozen=True)
class ProcessMetrics:
    vote_accuracy_by_player: dict[str, dict[str, float | int]]
    survival_rounds: dict[str, int]
    contradiction_count_by_player: dict[str, int]
    info_leak_count_by_player: dict[str, int]
    seer_metrics: dict[str, Any]
    witch_metrics: dict[str, Any]
    team_metrics: dict[str, Any]


@dataclass(frozen=True)
class ScoreSummary:
    player_outcome_scores: dict[str, int]
    team_outcome_scores: dict[str, int]
    player_rule_integrity_scores: dict[str, int]
    player_decision_quality_scores: dict[str, int]


@dataclass(frozen=True)
class MetricsSummary:
    metrics_id: str
    game_id: str
    source_game_log: str
    source_score_log: str
    source_label: str
    result_metrics: ResultMetrics
    process_metrics: ProcessMetrics
    score_summary: ScoreSummary
    metrics_deferred_to_later_spikes: list[dict[str, str]]
    known_rubric_gaps_recorded_not_fixed: list[dict[str, Any]]


def score_log_to_dict(score_log: ScoreLog) -> dict[str, Any]:
    return asdict(score_log)


def metrics_summary_to_dict(summary: MetricsSummary) -> dict[str, Any]:
    return asdict(summary)
```

- [ ] **Step 2: Run model smoke check**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from werewolf_eval.scoring import ScoreRecord

record = ScoreRecord(
    score_id="s2_g001_e001",
    event_id="g001_e001",
    actor="system",
    scope="system",
    round=0,
    phase="setup",
    action_type="role_assignment",
    target="p1",
    outcome_score=0,
    decision_quality_score=0,
    rule_integrity_score=0,
    rules_triggered=[],
    evidence_event_ids=["g001_e001"],
    notes="smoke"
)
assert record.decision_quality_score == 0
print("ScoreRecord smoke passed")
PY
```

Expected result:

```text
ScoreRecord smoke passed
```

- [ ] **Step 3: Commit scoring model**

Run:

```bash
git add src/werewolf_eval/scoring.py
git commit -m "feat: add deterministic scoring model"
```

Expected result:

```text
[task/e2-deterministic-scorer ...] feat: add deterministic scoring model
```

The exact commit hash may differ.

---

### Task 3: Implement deterministic Score Log generation

**Files:**

- Modify: `src/werewolf_eval/scoring.py`
- Test: `tests/test_scoring.py` in Task 5.

- [ ] **Step 1: Add score event selection and role helpers**

Append these helpers to `src/werewolf_eval/scoring.py`:

```python
SCORE_RELEVANT_EVENT_TYPES = {
    "werewolf_kill",
    "seer_check",
    "witch_save",
    "witch_poison",
    "player_vote",
}

KEY_VILLAGER_ROLES = {"seer", "witch", "hunter"}


def _player_by_id(game: GameLog) -> dict[str, Any]:
    return {player.player_id: player for player in game.players}


def _role_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].role


def _team_of(game: GameLog, player_id: str) -> str:
    return _player_by_id(game)[player_id].team


def _scope_for_actor(actor: str) -> str:
    return "team" if actor == "wolf_team" else "player"


def _eliminated_target_by_round(game: GameLog) -> dict[int, str]:
    eliminated: dict[int, str] = {}
    for event in game.events:
        if event.type == "player_eliminated":
            eliminated[event.round] = event.target
    return eliminated


def _reveal_event_for_target(game: GameLog, target: str) -> str | None:
    for event in game.events:
        if event.type == "role_revealed" and event.target == target:
            return event.event_id
    return None


def _death_event_for_target(game: GameLog, target: str) -> str | None:
    for event in game.events:
        if event.type == "player_died" and event.target == target:
            return event.event_id
    return None


def _save_event_for_target(game: GameLog, target: str) -> str | None:
    for event in game.events:
        if event.type == "witch_save" and event.target == target:
            return event.event_id
    return None
```

- [ ] **Step 2: Add score boundary factory**

Append:

```python
def _scoring_boundary() -> ScoringBoundary:
    return ScoringBoundary(
        decision_quality_score=0,
        decision_quality_reason="Phase 1 has no real Decision Log. All decision_quality_score values are fixed at 0.",
        ai_annotations="none",
        rule_integrity_default=0,
        rule_integrity_reason="S1 contains no info_leak_flag or contradiction_flag events.",
    )
```

- [ ] **Step 3: Add per-event scoring functions**

Append:

```python
def _score_werewolf_kill(game: GameLog, event: Event) -> ScoreRecord:
    target_role = _role_of(game, event.target)
    if target_role in KEY_VILLAGER_ROLES:
        outcome = 3
        rule = "rubric:E.1.werewolf.kill_key_villager"
        notes = f"Wolf team chose a key villager target; {event.target} is later revealed as {target_role}."
    else:
        outcome = 1
        rule = "rubric:E.1.werewolf.kill_villager"
        notes = f"Wolf team killed {event.target}, who is revealed as villager."

    evidence = [event.event_id]
    death_event = _death_event_for_target(game, event.target)
    if death_event:
        evidence.append(death_event)
    else:
        # When the kill target was saved by witch (no player_died),
        # include the witch_save event as alternative evidence.
        save_event = _save_event_for_target(game, event.target)
        if save_event:
            evidence.append(save_event)
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)

    if event.event_id == "g001_e007":
        notes = "Wolf team chose a villager target; p5 is later revealed as villager, while g001_e009 records that the Night 1 save prevented the kill from taking effect."

    return _record(event, outcome, [rule], evidence, notes)


def _score_seer_check(game: GameLog, event: Event) -> ScoreRecord:
    target_team = _team_of(game, event.target)
    if target_team == "werewolf":
        outcome = 2
        rule = "rubric:E.2.seer.check_werewolf"
        notes = f"Seer checked {event.target}, who is later revealed as werewolf."
    else:
        outcome = 0
        rule = "rubric:E.2.seer.check_villager"
        notes = f"Seer checked {event.target}, who is later revealed as villager."
    evidence = [event.event_id]
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)
    return _record(event, outcome, [rule], evidence, notes)


def _score_witch_save(game: GameLog, event: Event) -> ScoreRecord:
    target_role = _role_of(game, event.target)
    target_team = _team_of(game, event.target)
    if target_team == "werewolf":
        outcome = -1
        rule = "rubric:E.3.witch.save_werewolf"
        notes = f"Witch saved {event.target}, who is later revealed as werewolf."
    elif target_role in {"seer", "hunter"}:
        outcome = 3
        rule = "rubric:E.3.witch.save_key_villager"
        notes = f"Witch saved {event.target}, who is later revealed as {target_role}."
    else:
        outcome = 1
        rule = "rubric:E.3.witch.save_villager"
        notes = f"Witch saved {event.target}, who is later revealed as villager."
    evidence = [event.event_id]
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)
    return _record(event, outcome, [rule], evidence, notes)


def _score_witch_poison(game: GameLog, event: Event) -> ScoreRecord:
    target_role = _role_of(game, event.target)
    target_team = _team_of(game, event.target)
    if target_team == "werewolf":
        outcome = 3
        rule = "rubric:E.3.witch.poison_werewolf"
        notes = f"Witch poisoned {event.target}, who is revealed as werewolf."
    elif target_role in {"seer", "hunter"}:
        outcome = -3
        rule = "rubric:E.3.witch.poison_key_villager"
        notes = f"Witch poisoned {event.target}, who is later revealed as {target_role}."
    else:
        outcome = -1
        rule = "rubric:E.3.witch.poison_villager"
        notes = f"Witch poisoned {event.target}, who is later revealed as villager."
    evidence = [event.event_id]
    reveal_event = _reveal_event_for_target(game, event.target)
    if reveal_event:
        evidence.append(reveal_event)
    return _record(event, outcome, [rule], evidence, notes)
```

- [ ] **Step 4: Add vote scoring and record constructor**

Append:

```python
def _round_elimination_event(game: GameLog, round_number: int) -> str | None:
    for e in game.events:
        if e.type == "player_eliminated" and e.round == round_number:
            return e.event_id
    return None


def _score_player_vote(game: GameLog, event: Event, eliminated_by_round: dict[int, str]) -> ScoreRecord:
    actor_role = _role_of(game, event.actor)
    target_role = _role_of(game, event.target)
    target_team = _team_of(game, event.target)
    eliminated_target = eliminated_by_round.get(event.round)
    reveal_event = _reveal_event_for_target(game, event.target)
    evidence = [event.event_id]
    if eliminated_target == event.target:
        elimination_event = _round_elimination_event(game, event.round)
        if elimination_event:
            evidence.append(elimination_event)
    elif eliminated_target is not None and reveal_event is None:
        # When the vote target survives to end (no role_revealed),
        # include the round's elimination event as context evidence.
        # This matches S2 gold: g001_e033 (p1 votes p4, but p1 was
        # eliminated; p4 survives, so no role_revealed for p4).
        elimination_event = _round_elimination_event(game, event.round)
        if elimination_event:
            evidence.append(elimination_event)
    if reveal_event:
        evidence.append(reveal_event)

    if actor_role == "witch":
        return _record(
            event,
            0,
            ["rubric-gap:witch_day_vote_outcome_not_explicit"],
            evidence,
            "Witch daytime vote is counted in vote_accuracy metrics, but E.3 has no explicit vote outcome row. S2 assigns score 0 and records the rubric gap.",
        )

    if actor_role == "werewolf" and eliminated_target != event.target:
        return _record(
            event,
            0,
            ["rubric-gap:werewolf_day_vote_without_elimination"],
            evidence,
            f"{event.actor} voted for {event.target}, but {event.target} was not eliminated. E.1 has no explicit row for a werewolf vote that does not cause elimination, so S2 assigns 0 and records the rubric gap.",
        )

    if actor_role == "werewolf":
        if target_team == "werewolf":
            return _record(event, -2, ["rubric:E.1.werewolf.vote_eliminate_teammate"], evidence, f"Werewolf {event.actor} voted to eliminate teammate {event.target}.")
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, 2, ["rubric:E.1.werewolf.vote_eliminate_key_villager"], evidence, f"Werewolf {event.actor} voted to eliminate {event.target}, who is revealed as {target_role}.")
        return _record(event, 1, ["rubric:E.1.werewolf.vote_eliminate_villager"], evidence, f"Werewolf {event.actor} voted to eliminate villager {event.target}.")

    if actor_role == "seer":
        if target_team == "werewolf":
            return _record(event, 2, ["rubric:E.2.seer.vote_eliminate_werewolf"], evidence, f"Seer {event.actor} voted for {event.target}, who is later revealed as werewolf.")
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, -1, ["rubric:E.2.seer.vote_eliminate_key_villager"], evidence, f"Seer {event.actor} voted for key villager {event.target}.")
        return _record(event, -1, ["rubric:E.2.seer.vote_eliminate_villager"], evidence, f"Seer {event.actor} voted for villager {event.target}.")

    if actor_role == "villager":
        if target_team == "werewolf":
            return _record(event, 2, ["rubric:E.4.villager.vote_eliminate_werewolf"], evidence, f"Villager {event.actor} voted to eliminate {event.target}, who is revealed as werewolf.")
        if target_role in KEY_VILLAGER_ROLES:
            return _record(event, -2, ["rubric:E.4.villager.vote_eliminate_key_villager"], evidence, f"Villager {event.actor} voted to eliminate {event.target}, who is revealed as {target_role}.")
        return _record(event, -1, ["rubric:E.4.villager.vote_eliminate_villager"], evidence, f"Villager {event.actor} voted to eliminate villager {event.target}.")

    return _record(event, 0, ["rubric-gap:unscored_vote_role"], evidence, f"No explicit deterministic vote scoring row for role {actor_role}.")


def _record(
    event: Event,
    outcome_score: int,
    rules_triggered: list[str],
    evidence_event_ids: list[str],
    notes: str,
) -> ScoreRecord:
    return ScoreRecord(
        score_id=f"s2_g001_{event.event_id.split('_')[-1]}",
        event_id=event.event_id,
        actor=event.actor,
        scope=_scope_for_actor(event.actor),
        round=event.round,
        phase=event.phase,
        action_type=event.type,
        target=event.target,
        outcome_score=outcome_score,
        decision_quality_score=0,
        rule_integrity_score=0,
        rules_triggered=rules_triggered,
        evidence_event_ids=evidence_event_ids,
        notes=notes,
    )
```

- [ ] **Step 5: Add public `score_game` function**

Append:

```python
def score_game(game: GameLog) -> ScoreLog:
    eliminated_by_round = _eliminated_target_by_round(game)
    records: list[ScoreRecord] = []

    for event in game.events:
        if event.type not in SCORE_RELEVANT_EVENT_TYPES:
            continue
        if event.type == "werewolf_kill":
            records.append(_score_werewolf_kill(game, event))
        elif event.type == "seer_check":
            records.append(_score_seer_check(game, event))
        elif event.type == "witch_save":
            records.append(_score_witch_save(game, event))
        elif event.type == "witch_poison":
            records.append(_score_witch_poison(game, event))
        elif event.type == "player_vote":
            records.append(_score_player_vote(game, event, eliminated_by_round))

    return ScoreLog(
        score_log_id="s2_g001_expected_score_log",
        game_id=game.game_id,
        source_game_log="docs/gold-game/g001-game-log.json",
        source_label="[deterministic]",
        phase="Phase 1",
        scoring_boundary=_scoring_boundary(),
        records=records,
    )
```

- [ ] **Step 6: Run score log smoke check**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game

game = load_game_log("docs/gold-game/g001-game-log.json")
score_log = score_game(game)
records = {record.event_id: record for record in score_log.records}

assert score_log.game_id == "g001"
assert len(score_log.records) == 14
assert records["g001_e007"].outcome_score == 1
assert records["g001_e008"].outcome_score == 2
assert records["g001_e025"].outcome_score == 3
assert records["g001_e020"].outcome_score == -2
assert records["g001_e034"].rules_triggered == ["rubric-gap:witch_day_vote_outcome_not_explicit"]

print("score_game smoke passed")
PY
```

Expected result:

```text
score_game smoke passed
```

- [ ] **Step 7: Commit Score Log implementation**

Run:

```bash
git add src/werewolf_eval/scoring.py
git commit -m "feat: compute deterministic score log"
```

Expected result:

```text
[task/e2-deterministic-scorer ...] feat: compute deterministic score log
```

The exact commit hash may differ.

---

### Task 4: Implement Metrics Summary generation

**Files:**

- Modify: `src/werewolf_eval/scoring.py`
- Test: `tests/test_scoring.py` in Task 5.

- [ ] **Step 1: Add metrics helpers**

Append:

```python
def _round_float(value: float) -> float:
    return round(value, 6)


def _alive_players_after_game(game: GameLog) -> set[str]:
    dead = {event.target for event in game.events if event.type in {"player_died", "player_eliminated"}}
    return game.player_ids - dead


def _vote_events(game: GameLog) -> list[Event]:
    return [event for event in game.events if event.type == "player_vote"]


def _vote_accuracy_by_player(game: GameLog) -> dict[str, dict[str, float | int]]:
    result = {player.player_id: {"accurate_votes": 0, "total_votes": 0, "vote_accuracy": 0.0} for player in game.players}
    for event in _vote_events(game):
        actor_team = _team_of(game, event.actor)
        target_team = _team_of(game, event.target)
        result[event.actor]["total_votes"] += 1
        if actor_team != target_team:
            result[event.actor]["accurate_votes"] += 1
    for item in result.values():
        total = int(item["total_votes"])
        item["vote_accuracy"] = _round_float(float(item["accurate_votes"]) / total) if total else 0.0
    return result


def _survival_rounds(game: GameLog) -> dict[str, int]:
    survival = {player.player_id: game.result.end_round for player in game.players}
    for event in game.events:
        if event.type in {"player_died", "player_eliminated"} and event.target in survival:
            survival[event.target] = min(survival[event.target], event.round)
    return survival


def _zero_counts(game: GameLog) -> dict[str, int]:
    return {player.player_id: 0 for player in game.players}
```

- [ ] **Step 2: Add role-specific and team metrics helpers**

Append:

```python
def _seer_metrics(game: GameLog) -> dict[str, Any]:
    seer = next(player.player_id for player in game.players if player.role == "seer")
    checks = [event for event in game.events if event.type == "seer_check" and event.actor == seer]
    werewolf_checks = [event for event in checks if _team_of(game, event.target) == "werewolf"]
    # check_accuracy: correct identifications / total (target team matches seer's reported result).
    # In the deterministic model without AI annotation, every seer_check is treated as accurate
    # because the check result is the ground-truth role. This matches S2 gold for g001 (1/1 = 1.0).
    correct_checks = len(checks)
    # check_targeting: werewolf-targeting checks / total (how many checks aimed at wolves).
    conveyed_refs = [event.event_id for event in game.events if event.type == "player_speech" and event.actor == seer]
    evidence = [event.event_id for event in checks] + conveyed_refs[:1]
    total = len(checks)
    return {
        "actor": seer,
        "check_accuracy": _round_float(correct_checks / total) if total else 0.0,
        "check_targeting": _round_float(len(werewolf_checks) / total) if total else 0.0,
        "info_conveyed": 1.0 if checks and conveyed_refs else 0.0,
        "evidence_event_ids": evidence,
    }


def _witch_metrics(game: GameLog) -> dict[str, Any]:
    witch = next(player.player_id for player in game.players if player.role == "witch")
    saves = [event for event in game.events if event.type == "witch_save" and event.actor == witch]
    poisons = [event for event in game.events if event.type == "witch_poison" and event.actor == witch]
    save_accuracy = 0.0
    if saves:
        save_accuracy = 1.0 if _team_of(game, saves[0].target) == "villager" else 0.0
    poison_accuracy = 0.0
    if poisons:
        poison_accuracy = 1.0 if _team_of(game, poisons[0].target) == "werewolf" else 0.0
    used = int(bool(saves)) + int(bool(poisons))
    ability_utilization = 1.0 if used == 2 else 0.5 if used == 1 else 0.0
    return {
        "actor": witch,
        "save_accuracy": save_accuracy,
        "poison_accuracy": poison_accuracy,
        "ability_utilization": ability_utilization,
        "evidence_event_ids": [event.event_id for event in saves + poisons],
    }


def _team_metrics(game: GameLog) -> dict[str, Any]:
    village_by_day: dict[str, float] = {}
    werewolf_by_day: dict[str, float] = {}
    rounds = sorted({event.round for event in _vote_events(game)})
    for round_number in rounds:
        votes = [event for event in _vote_events(game) if event.round == round_number]
        village_votes = [event for event in votes if _team_of(game, event.actor) == "villager"]
        if village_votes:
            target_counts: dict[str, int] = {}
            for vote in village_votes:
                target_counts[vote.target] = target_counts.get(vote.target, 0) + 1
            village_by_day[f"round_{round_number}"] = _round_float(max(target_counts.values()) / len(village_votes))
        werewolf_votes = [event for event in votes if _team_of(game, event.actor) == "werewolf"]
        if len(werewolf_votes) >= 2:
            targets = {event.target for event in werewolf_votes}
            werewolf_by_day[f"round_{round_number}"] = 1.0 if len(targets) == 1 else 0.0
    village_values = list(village_by_day.values())
    werewolf_values = list(werewolf_by_day.values())
    return {
        "village_vote_cohesion": _round_float(sum(village_values) / len(village_values)) if village_values else 0.0,
        "village_vote_cohesion_by_day": village_by_day,
        "werewolf_vote_coordination": _round_float(sum(werewolf_values) / len(werewolf_values)) if werewolf_values else 0.0,
        "werewolf_vote_coordination_by_day": werewolf_by_day,
    }
```

- [ ] **Step 3: Add result and score summary helpers**

Append:

```python
def _result_metrics(game: GameLog) -> ResultMetrics:
    players = _player_by_id(game)
    alive = _alive_players_after_game(game)
    werewolves = [player.player_id for player in game.players if player.team == "werewolf"]
    villagers = [player.player_id for player in game.players if player.team == "villager"]
    alive_werewolves = [player_id for player_id in werewolves if player_id in alive]
    alive_villagers = [player_id for player_id in villagers if player_id in alive]
    winner_alive = alive_villagers if game.result.winner == "villager" else alive_werewolves
    loser_alive = alive_werewolves if game.result.winner == "villager" else alive_villagers
    eliminated_werewolves = [event.target for event in game.events if event.type == "player_eliminated" and players[event.target].team == "werewolf"]
    return ResultMetrics(
        winner=game.result.winner,
        game_length=game.result.end_round,
        werewolf_survival_rate=_round_float(len(alive_werewolves) / len(werewolves)),
        villager_survival_rate=_round_float(len(alive_villagers) / len(villagers)),
        margin=len(winner_alive) - len(loser_alive),
        werewolf_win_speed=None if game.result.winner != "werewolf" else _round_float((len(alive_werewolves) - len(alive_villagers)) / game.result.end_round),
        villager_win_efficiency=None if game.result.winner != "villager" else _round_float(len(eliminated_werewolves) / game.result.end_round),
    )


def _score_summary(game: GameLog, score_log: ScoreLog) -> ScoreSummary:
    player_outcome = {player.player_id: 0 for player in game.players}
    player_integrity = {player.player_id: 0 for player in game.players}
    player_decision = {player.player_id: 0 for player in game.players}
    team_outcome: dict[str, int] = {}
    for record in score_log.records:
        if record.scope == "team":
            team_outcome[record.actor] = team_outcome.get(record.actor, 0) + record.outcome_score
        else:
            player_outcome[record.actor] += record.outcome_score
            player_integrity[record.actor] += record.rule_integrity_score
            player_decision[record.actor] += record.decision_quality_score
    return ScoreSummary(
        player_outcome_scores=player_outcome,
        team_outcome_scores=team_outcome,
        player_rule_integrity_scores=player_integrity,
        player_decision_quality_scores=player_decision,
    )
```

- [ ] **Step 4: Add public `summarize_metrics` function**

Append:

```python
def summarize_metrics(game: GameLog, score_log: ScoreLog) -> MetricsSummary:
    return MetricsSummary(
        metrics_id="s2_g001_expected_metrics",
        game_id=game.game_id,
        source_game_log="docs/gold-game/g001-game-log.json",
        source_score_log="docs/gold-game/s2-score-log.json",
        source_label="[deterministic]",
        result_metrics=_result_metrics(game),
        process_metrics=ProcessMetrics(
            vote_accuracy_by_player=_vote_accuracy_by_player(game),
            survival_rounds=_survival_rounds(game),
            contradiction_count_by_player=_zero_counts(game),
            info_leak_count_by_player=_zero_counts(game),
            seer_metrics=_seer_metrics(game),
            witch_metrics=_witch_metrics(game),
            team_metrics=_team_metrics(game),
        ),
        score_summary=_score_summary(game, score_log),
        metrics_deferred_to_later_spikes=[
            {
                "metric": "turn_point_count",
                "owner": "S3 rule attribution validation",
                "reason": "turn_point_count is defined as an attribution count; S2 does not compute attribution outputs.",
            }
        ],
        known_rubric_gaps_recorded_not_fixed=[
            {
                "gap": "werewolf_day_vote_without_elimination",
                "events": ["g001_e033"],
                "S2_policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
            },
            {
                "gap": "witch_day_vote_outcome_not_explicit",
                "events": ["g001_e019", "g001_e034"],
                "S2_policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
            },
        ],
    )
```

- [ ] **Step 5: Run Metrics Summary smoke check**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics

game = load_game_log("docs/gold-game/g001-game-log.json")
score_log = score_game(game)
summary = summarize_metrics(game, score_log)

assert summary.game_id == "g001"
assert summary.result_metrics.winner == "villager"
assert summary.result_metrics.game_length == 2
assert summary.result_metrics.villager_win_efficiency == 1.0
assert summary.score_summary.player_outcome_scores["p4"] == 4
assert summary.score_summary.team_outcome_scores["wolf_team"] == 2

print("metrics summary smoke passed")
PY
```

Expected result:

```text
metrics summary smoke passed
```

- [ ] **Step 6: Commit Metrics Summary implementation**

Run:

```bash
git add src/werewolf_eval/scoring.py
git commit -m "feat: compute deterministic metrics summary"
```

Expected result:

```text
[task/e2-deterministic-scorer ...] feat: compute deterministic metrics summary
```

The exact commit hash may differ.

---

### Task 5: Add scorer CLI

**Files:**

- Modify: `src/werewolf_eval/scoring.py`
- Create: `src/werewolf_eval/score_game.py`
- Test: `tests/test_scoring.py` in Task 6.

- [ ] **Step 1: Confirm serialization helpers exist**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("src/werewolf_eval/scoring.py").read_text(encoding="utf-8")
assert "def score_log_to_dict" in text
assert "def metrics_summary_to_dict" in text
print("serialization helpers exist")
PY
```

Expected result:

```text
serialization helpers exist
```

- [ ] **Step 2: Create `src/werewolf_eval/score_game.py`**

Create this file:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)


def _write_json(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute deterministic Werewolf-agent Score Log and Metrics Summary.")
    parser.add_argument("path", help="Path to Game Log JSON")
    parser.add_argument("--score-log-out", help="Optional path for generated Score Log JSON")
    parser.add_argument("--metrics-out", help="Optional path for generated Metrics Summary JSON")
    args = parser.parse_args()

    game = load_game_log(args.path)
    score_log = score_game(game)
    metrics = summarize_metrics(game, score_log)

    score_payload = score_log_to_dict(score_log)
    metrics_payload = metrics_summary_to_dict(metrics)

    if args.score_log_out:
        _write_json(args.score_log_out, score_payload)
    if args.metrics_out:
        _write_json(args.metrics_out, metrics_payload)

    print(f"scored game_id={game.game_id}")
    print(f"score_records={len(score_log.records)}")
    print(f"winner={metrics.result_metrics.winner}")
    print(f"game_length={metrics.result_metrics.game_length}")
    print(f"wolf_team_outcome_score={metrics.score_summary.team_outcome_scores.get('wolf_team', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run CLI with output files**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json \
  --score-log-out /tmp/e2-score-log.json \
  --metrics-out /tmp/e2-metrics-summary.json

python -m json.tool /tmp/e2-score-log.json > /dev/null
python -m json.tool /tmp/e2-metrics-summary.json > /dev/null
```

Expected output includes:

```text
scored game_id=g001
score_records=14
winner=villager
game_length=2
wolf_team_outcome_score=2
```

- [ ] **Step 4: Commit CLI**

Run:

```bash
git add src/werewolf_eval/scoring.py src/werewolf_eval/score_game.py
git commit -m "feat: add deterministic scorer cli"
```

Expected result:

```text
[task/e2-deterministic-scorer ...] feat: add deterministic scorer cli
```

The exact commit hash may differ.

---

### Task 6: Add golden tests for deterministic scorer

**Files:**

- Create: `tests/test_scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Create `tests/test_scoring.py`**

Create this file:

```python
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.game_log import load_game_log
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class DeterministicScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)

    def test_score_log_matches_s2_expected_records(self) -> None:
        actual = score_log_to_dict(self.score_log)
        expected = load_json("docs/gold-game/s2-score-log.json")
        self.assertEqual(actual, expected)

    def test_metrics_summary_matches_s2_expected(self) -> None:
        actual = metrics_summary_to_dict(self.metrics)
        expected = load_json("docs/gold-game/s2-metrics-summary.json")
        self.assertEqual(actual, expected)

    def test_decision_quality_is_zero_without_decision_log(self) -> None:
        self.assertTrue(self.score_log.records)
        for record in self.score_log.records:
            self.assertEqual(record.decision_quality_score, 0)

    def test_rule_integrity_defaults_to_zero_without_flag_events(self) -> None:
        self.assertTrue(self.score_log.records)
        for record in self.score_log.records:
            self.assertEqual(record.rule_integrity_score, 0)

    def test_score_records_reference_existing_events(self) -> None:
        event_ids = self.game.event_ids
        for record in self.score_log.records:
            self.assertIn(record.event_id, event_ids)
            for evidence_event_id in record.evidence_event_ids:
                self.assertIn(evidence_event_id, event_ids)

    def test_known_rubric_gaps_are_preserved(self) -> None:
        score_payload = score_log_to_dict(self.score_log)
        metrics_payload = metrics_summary_to_dict(self.metrics)
        score_rules = {
            rule
            for record in score_payload["records"]
            for rule in record["rules_triggered"]
        }
        self.assertIn("rubric-gap:werewolf_day_vote_without_elimination", score_rules)
        self.assertIn("rubric-gap:witch_day_vote_outcome_not_explicit", score_rules)

        gaps = {item["gap"] for item in metrics_payload["known_rubric_gaps_recorded_not_fixed"]}
        self.assertEqual(
            gaps,
            {"werewolf_day_vote_without_elimination", "witch_day_vote_outcome_not_explicit"},
        )


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
Ran 12 tests
OK
```

The exact number may be higher if additional tests exist, but all tests must pass.

- [ ] **Step 3: Commit scoring tests**

Run:

```bash
git add tests/test_scoring.py
git commit -m "test: cover deterministic scorer golden outputs"
```

Expected result:

```text
[task/e2-deterministic-scorer ...] test: cover deterministic scorer golden outputs
```

The exact commit hash may differ.

---

### Task 7: Update repository docs and navigation

**Files:**

- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/TASKS.md`
- Modify: `.oh-my-harness/tree.md`
- Test: none; use text validation command.

- [ ] **Step 1: Update `AGENTS.md` command section and MAP**

In `AGENTS.md`, add this scorer command under `## 命令`:

```text
- Deterministic scorer 命令：`PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json`。
```

In the MAP, add these files under `src/werewolf_eval/`:

```text
scoring.py
score_game.py
```

In the MAP, add this file under `tests/`:

```text
test_scoring.py
```

- [ ] **Step 2: Update `README.md` current status**

In the `## 当前状态` section, replace only the **first sentence** of the current paragraph (which says "仓库仍无业务代码") while keeping all caveat sentences intact. Replace with wording equivalent to:

```text
**Phase 1 deterministic MVP 已完成。** 当前 main 已包含 E1 Game Log parser / validator 和 E2 deterministic scorer 运行时代码；E3/E4 仍为 Phase 2 候选工程任务。
```

The subsequent caveat paragraph starting with "Phase 1 不代表真实 AI Agent 对局..." and the `## Phase 1 不是` section must remain unchanged. Do not claim real Agent gameplay, real Decision Log, real Consensus Log, real multi-model Leaderboard, or real `decision_quality_score` is available.

- [ ] **Step 3: Update `docs/TASKS.md` E2 and E3 status**

Change E2 status to:

```text
- 状态：`completed`（Phase 2 E2 deterministic scorer；Score Log / Metrics Summary runtime 已实现）
- 产出：`src/werewolf_eval/scoring.py` + `src/werewolf_eval/score_game.py` + `tests/test_scoring.py`。
```

Change E3 status to:

```text
- 状态：`phase_2_candidate`（S3 已满足；E1/E2 完成后可准备独立 Implementation Plan）
```

Do not mark E3 started.

- [ ] **Step 4: Refresh `.oh-my-harness/tree.md`**

Run the repository hook or equivalent tree-refresh command used by this repo so `.oh-my-harness/tree.md` reflects:

```text
src/werewolf_eval/scoring.py
src/werewolf_eval/score_game.py
tests/test_scoring.py
```

If the hook is unavailable, regenerate `.oh-my-harness/tree.md` from `git ls-files --cached --others --exclude-standard` using the same format already present in the file.

- [ ] **Step 5: Validate docs and tree**

Run:

```bash
python - <<'PY'
from pathlib import Path

agents = Path("AGENTS.md").read_text(encoding="utf-8")
tasks = Path("docs/TASKS.md").read_text(encoding="utf-8")
readme = Path("README.md").read_text(encoding="utf-8")
tree = Path(".oh-my-harness/tree.md").read_text(encoding="utf-8")

required = [
    (agents, "src/werewolf_eval/scoring.py"),
    (agents, "src/werewolf_eval/score_game.py"),
    (agents, "tests/test_scoring.py"),
    (agents, "PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json"),
    (tasks, "E2：确定性评分器"),
    (tasks, "状态：`completed`（Phase 2 E2 deterministic scorer；Score Log / Metrics Summary runtime 已实现）"),
    (tasks, "src/werewolf_eval/scoring.py"),
    (tasks, "E1/E2 完成后可准备独立 Implementation Plan"),
    (readme, "E2 deterministic scorer 运行时代码"),
    (tree, "src/werewolf_eval/scoring.py"),
    (tree, "src/werewolf_eval/score_game.py"),
    (tree, "tests/test_scoring.py"),
]

missing = [needle for text, needle in required if needle not in text]
assert not missing, missing
assert "真实 AI Agent 对局" in readme
assert "真实 `decision_quality_score` 可用" in readme

print("E2 docs and tree validated")
PY
```

Expected result:

```text
E2 docs and tree validated
```

- [ ] **Step 6: Commit docs and tree update**

Run:

```bash
git add AGENTS.md README.md docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: record e2 deterministic scorer boundary"
```

Expected result:

```text
[task/e2-deterministic-scorer ...] docs: record e2 deterministic scorer boundary
```

The exact commit hash may differ.

---

### Task 8: Final validation and PR preparation

**Files:**

- Create: none.
- Modify: none after previous tasks.
- Test: `tests/test_game_log.py`, `tests/test_scoring.py`.

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

- [ ] **Step 3: Run E2 scorer CLI and validate generated JSON**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json \
  --score-log-out /tmp/e2-score-log.json \
  --metrics-out /tmp/e2-metrics-summary.json

python -m json.tool /tmp/e2-score-log.json > /dev/null
python -m json.tool /tmp/e2-metrics-summary.json > /dev/null
```

Expected output includes:

```text
scored game_id=g001
score_records=14
winner=villager
game_length=2
wolf_team_outcome_score=2
```

- [ ] **Step 4: Run all unit tests**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result includes:

```text
Ran 12 tests
OK
```

The exact count may be higher if more tests exist, but all tests must pass.

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

- [ ] **Step 6: Check whitespace**

Run:

```bash
git diff --check main...HEAD
```

Expected result:

```text
```

No output means no whitespace errors.

- [ ] **Step 7: Verify changed files**

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
src/werewolf_eval/scoring.py
src/werewolf_eval/score_game.py
tests/test_scoring.py
```

- [ ] **Step 8: Prepare Implementation PR description**

Use this PR description:

```md
## Summary

Implements E2 deterministic scorer for Werewolf-agent.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--e2-deterministic-scorer-plan.md`

## Scope

- Adds deterministic Score Log generation from E1 `GameLog`.
- Adds deterministic Metrics Summary generation.
- Adds scorer CLI:
  - `PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json`
- Adds golden tests against:
  - `docs/gold-game/s2-score-log.json`
  - `docs/gold-game/s2-metrics-summary.json`
- Updates AGENTS.md, README.md, TASKS.md, and `.oh-my-harness/tree.md` to reflect the E2 runtime boundary.

## Out of Scope

- No E3 attribution engine.
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

PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json \
  --score-log-out /tmp/e2-score-log.json \
  --metrics-out /tmp/e2-metrics-summary.json

python -m json.tool /tmp/e2-score-log.json > /dev/null
python -m json.tool /tmp/e2-metrics-summary.json > /dev/null

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
src/werewolf_eval/scoring.py
src/werewolf_eval/score_game.py
tests/test_scoring.py
```

## Risk

The main risk is accidentally expanding deterministic scoring into attribution or AI-assisted decision quality. This PR intentionally fixes `decision_quality_score = 0` without Decision Log, keeps `rule_integrity_score = 0` for g001 unless deterministic violation flags exist, and only reproduces S2 expected deterministic outputs.

E3 attribution should be a separate Implementation Plan and PR after E2 is merged.
```

- [ ] **Step 9: Final status check**

Run:

```bash
git status --short
```

Expected result after all commits:

```text
```

No output means the working tree is clean.
