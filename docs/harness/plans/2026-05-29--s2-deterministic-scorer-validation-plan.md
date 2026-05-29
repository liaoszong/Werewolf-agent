# S2 Deterministic Scorer Validation Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Validate that the Phase 1 Gold Game Log can produce deterministic `outcome_score`, `rule_integrity_score`, process metrics, result metrics, and a repeatable score summary without business code.

**Architecture:** This is a Phase 1 data/document spike, not a runtime scorer implementation. It consumes `docs/gold-game/g001-game-log.json`, creates deterministic expected scoring artifacts under `docs/gold-game/`, and validates internal consistency with Python standard-library commands. The output becomes the fixed acceptance target for E2 scorer implementation.

**Tech Stack:** JSON, Markdown, Python standard library validation commands only. No runtime dependencies.

---

## Progress Check Summary

Before writing this plan, the current progress was checked through PR-first facts and recent commit history:

- S0 is completed and merged through PR #2, producing `docs/gold-game/s0-gold-game-seed.md`.
- S1 plan is completed and merged through PR #3.
- S1 implementation is completed and merged through PR #4, producing `docs/gold-game/g001-game-log.json` and `docs/gold-game/s1-schema-validation.md`.
- The latest workflow update requires agents to check merged PRs and recent git log before deciding the next task.
- `docs/TASKS.md` now marks S0 and S1 as completed and leaves S2 as the next dependency-valid spike.

Therefore the next implementation unit is S2: deterministic scorer validation.

## Scope Decision

S2 should not create the production scorer yet. `docs/TASKS.md` says engineering tasks are created only after their corresponding spike passes. S2 is the validation step that proves the scoring rules can be applied deterministically to the S1 Game Log.

This plan creates expected outputs for the Gold Game:

- Event-level deterministic score log.
- Aggregated result metrics.
- Aggregated process metrics.
- Per-player score summary.
- A validation report documenting assumptions, rubric mappings, and S2 acceptance.

## Files

- Create: `docs/gold-game/s2-score-log.json`
- Create: `docs/gold-game/s2-metrics-summary.json`
- Create: `docs/gold-game/s2-scoring-validation.md`
- Modify: `docs/harness/plans/2026-05-29--s2-deterministic-scorer-validation-plan.md` only if implementation review reveals the embedded S2 examples must be corrected to keep the bound plan reproducible.
- Test file: no separate committed test file for this Phase 1 data/document spike. Each task includes an explicit Python standard-library validation command.

## Hard Boundaries

- Do not create `src/`, `apps/`, `server/`, or `web`.
- Do not create `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, or dependency configuration.
- Do not modify `docs/EVALUATION_RUBRIC.md` in this PR.
- Do not implement parser, scorer, attribution engine, UI, AI Agent gameplay, or runtime code.
- Do not claim `decision_quality_score` is available in Phase 1.
- Do not call AI models or add `[AI 生成]` data.
- Do not introduce mock leaderboard rows in this S2 PR.

---

## Task 1: Confirm S1 input and boundary facts

**Files:**

- Create: none
- Modify: none
- Test file: no separate test file; run the command below against `docs/gold-game/g001-game-log.json` and `docs/gold-game/s1-schema-validation.md`.

- [ ] **Step 1: Verify S1 artifacts exist and contain expected fixed input**

```bash
test -f docs/gold-game/g001-game-log.json
test -f docs/gold-game/s1-schema-validation.md
python - <<'PY'
import json
from pathlib import Path

game = json.loads(Path('docs/gold-game/g001-game-log.json').read_text(encoding='utf-8'))
events = {event['event_id']: event for event in game['events']}

assert game['game_id'] == 'g001'
assert len(game['players']) == 6
assert len(game['events']) == 38
assert game['result']['winner'] == 'villager'
assert game['result']['survivors'] == ['p4', 'p6']
assert events['g001_e008']['type'] == 'seer_check'
assert events['g001_e008']['data']['result'] == 'werewolf'
assert events['g001_e025']['type'] == 'witch_poison'
assert events['g001_e025']['target'] == 'p2'
assert events['g001_e038']['type'] == 'game_over'

report = Path('docs/gold-game/s1-schema-validation.md').read_text(encoding='utf-8')
for phrase in ['S1', 'g001-game-log.json', 'schema']:
    assert phrase in report

print('S1 input is ready for S2')
PY
```

Expected result:

```text
S1 input is ready for S2
```

- [ ] **Step 2: Check that this implementation PR has not started runtime work**

```bash
test ! -d src
test ! -d apps
test ! -d server
test ! -d web
test ! -f package.json
test ! -f package-lock.json
test ! -f pnpm-lock.yaml
test ! -f yarn.lock
printf 'No runtime implementation directories or dependency manifests exist\n'
```

Expected result:

```text
No runtime implementation directories or dependency manifests exist
```

---

## Task 2: Create deterministic score log artifact

**Files:**

- Create: `docs/gold-game/s2-score-log.json`
- Modify: none
- Test file: no separate committed test file; the validation command below checks the JSON file.

- [ ] **Step 1: Write the deterministic score log**

```bash
python - <<'PY'
import json
from pathlib import Path

records = [
    ['s2_g001_e007', 'g001_e007', 'wolf_team', 'team', 1, 'night', 'werewolf_kill', 'p5', 1, ['rubric:E.1.werewolf.kill_villager'], ['g001_e007', 'g001_e009', 'g001_e028'], 'Wolf team chose a villager target; p5 is later revealed as villager, while g001_e009 records that the Night 1 save prevented the kill from taking effect.'],
    ['s2_g001_e008', 'g001_e008', 'p3', 'player', 1, 'night', 'seer_check', 'p1', 2, ['rubric:E.2.seer.check_werewolf'], ['g001_e008', 'g001_e037'], 'Seer checked p1, who is later revealed as werewolf.'],
    ['s2_g001_e009', 'g001_e009', 'p4', 'player', 1, 'night', 'witch_save', 'p5', 1, ['rubric:E.3.witch.save_villager'], ['g001_e009', 'g001_e028'], 'Witch saved p5, who is later revealed as villager.'],
    ['s2_g001_e016', 'g001_e016', 'p1', 'player', 1, 'day', 'player_vote', 'p3', 2, ['rubric:E.1.werewolf.vote_eliminate_key_villager'], ['g001_e016', 'g001_e022', 'g001_e023'], 'Werewolf p1 voted to eliminate p3, who is revealed as seer.'],
    ['s2_g001_e017', 'g001_e017', 'p2', 'player', 1, 'day', 'player_vote', 'p3', 2, ['rubric:E.1.werewolf.vote_eliminate_key_villager'], ['g001_e017', 'g001_e022', 'g001_e023'], 'Werewolf p2 voted to eliminate p3, who is revealed as seer.'],
    ['s2_g001_e018', 'g001_e018', 'p3', 'player', 1, 'day', 'player_vote', 'p1', 2, ['rubric:E.2.seer.vote_eliminate_werewolf'], ['g001_e018', 'g001_e037'], 'Seer p3 voted for p1, who is later revealed as werewolf.'],
    ['s2_g001_e019', 'g001_e019', 'p4', 'player', 1, 'day', 'player_vote', 'p1', 0, ['rubric-gap:witch_day_vote_outcome_not_explicit'], ['g001_e019', 'g001_e037'], 'Witch daytime vote is counted in vote_accuracy metrics, but E.3 has no explicit vote outcome row. S2 assigns score 0 and records the rubric gap.'],
    ['s2_g001_e020', 'g001_e020', 'p5', 'player', 1, 'day', 'player_vote', 'p3', -2, ['rubric:E.4.villager.vote_eliminate_key_villager'], ['g001_e020', 'g001_e022', 'g001_e023'], 'Villager p5 voted to eliminate p3, who is revealed as seer.'],
    ['s2_g001_e021', 'g001_e021', 'p6', 'player', 1, 'day', 'player_vote', 'p3', -2, ['rubric:E.4.villager.vote_eliminate_key_villager'], ['g001_e021', 'g001_e022', 'g001_e023'], 'Villager p6 voted to eliminate p3, who is revealed as seer.'],
    ['s2_g001_e024', 'g001_e024', 'wolf_team', 'team', 2, 'night', 'werewolf_kill', 'p5', 1, ['rubric:E.1.werewolf.kill_villager'], ['g001_e024', 'g001_e026', 'g001_e028'], 'Wolf team killed p5, who is revealed as villager.'],
    ['s2_g001_e025', 'g001_e025', 'p4', 'player', 2, 'night', 'witch_poison', 'p2', 3, ['rubric:E.3.witch.poison_werewolf'], ['g001_e025', 'g001_e029'], 'Witch poisoned p2, who is revealed as werewolf.'],
    ['s2_g001_e033', 'g001_e033', 'p1', 'player', 2, 'day', 'player_vote', 'p4', 0, ['rubric-gap:werewolf_day_vote_without_elimination'], ['g001_e033', 'g001_e036'], 'p1 voted for p4, but p4 was not eliminated. E.1 has no explicit row for a werewolf vote that does not cause elimination, so S2 assigns 0 and records the rubric gap.'],
    ['s2_g001_e034', 'g001_e034', 'p4', 'player', 2, 'day', 'player_vote', 'p1', 0, ['rubric-gap:witch_day_vote_outcome_not_explicit'], ['g001_e034', 'g001_e036', 'g001_e037'], 'Witch daytime vote is counted in vote_accuracy metrics, but E.3 has no explicit vote outcome row. S2 assigns score 0 and records the rubric gap.'],
    ['s2_g001_e035', 'g001_e035', 'p6', 'player', 2, 'day', 'player_vote', 'p1', 2, ['rubric:E.4.villager.vote_eliminate_werewolf'], ['g001_e035', 'g001_e036', 'g001_e037'], 'Villager p6 voted to eliminate p1, who is revealed as werewolf.'],
]

score_records = []
for score_id, event_id, actor, scope, round_no, phase, action_type, target, outcome, rules, evidence, notes in records:
    score_records.append({
        'score_id': score_id,
        'event_id': event_id,
        'actor': actor,
        'scope': scope,
        'round': round_no,
        'phase': phase,
        'action_type': action_type,
        'target': target,
        'outcome_score': outcome,
        'decision_quality_score': 0,
        'rule_integrity_score': 0,
        'rules_triggered': rules,
        'evidence_event_ids': evidence,
        'notes': notes,
    })

score_log = {
    'score_log_id': 's2_g001_expected_score_log',
    'game_id': 'g001',
    'source_game_log': 'docs/gold-game/g001-game-log.json',
    'source_label': '[deterministic]',
    'phase': 'Phase 1',
    'scoring_boundary': {
        'decision_quality_score': 0,
        'decision_quality_reason': 'Phase 1 has no real Decision Log. All decision_quality_score values are fixed at 0.',
        'ai_annotations': 'none',
        'rule_integrity_default': 0,
        'rule_integrity_reason': 'S1 contains no info_leak_flag or contradiction_flag events.',
    },
    'records': score_records,
}

Path('docs/gold-game/s2-score-log.json').write_text(
    json.dumps(score_log, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)
print('Wrote docs/gold-game/s2-score-log.json')
PY
```

Expected result:

```text
Wrote docs/gold-game/s2-score-log.json
```

- [ ] **Step 2: Validate score log shape and Phase 1 scoring boundaries**

```bash
python -m json.tool docs/gold-game/s2-score-log.json > /tmp/s2-score-log.pretty.json
python - <<'PY'
import json
from pathlib import Path

score_log = json.loads(Path('docs/gold-game/s2-score-log.json').read_text(encoding='utf-8'))
records = score_log['records']

assert score_log['game_id'] == 'g001'
assert score_log['source_label'] == '[deterministic]'
assert len(records) == 14
assert all(record['decision_quality_score'] == 0 for record in records)
assert all(record['rule_integrity_score'] == 0 for record in records)
assert all(record['rules_triggered'] for record in records)
assert all(record['evidence_event_ids'] for record in records)
assert {record['score_id'] for record in records} == {
    's2_g001_e007', 's2_g001_e008', 's2_g001_e009', 's2_g001_e016', 's2_g001_e017',
    's2_g001_e018', 's2_g001_e019', 's2_g001_e020', 's2_g001_e021', 's2_g001_e024',
    's2_g001_e025', 's2_g001_e033', 's2_g001_e034', 's2_g001_e035'
}
by_id = {record['score_id']: record for record in records}
assert 'g001_e009' in by_id['s2_g001_e007']['evidence_event_ids']
assert 'killed a villager target' not in by_id['s2_g001_e007']['notes']
assert by_id['s2_g001_e033']['rules_triggered'] == ['rubric-gap:werewolf_day_vote_without_elimination']
assert sum(record['outcome_score'] for record in records if record['scope'] == 'player') == 10
assert sum(record['outcome_score'] for record in records if record['scope'] == 'team') == 2
print('S2 score log validation passed')
PY
```

Expected result:

```text
S2 score log validation passed
```

---

## Task 3: Create deterministic metrics summary artifact

**Files:**

- Create: `docs/gold-game/s2-metrics-summary.json`
- Modify: none
- Test file: no separate committed test file; the validation command below checks the JSON file and recomputes core values from S1 + S2 artifacts.

- [ ] **Step 1: Write the deterministic metrics summary**

```bash
python - <<'PY'
import json
from pathlib import Path

metrics = {
    'metrics_id': 's2_g001_expected_metrics',
    'game_id': 'g001',
    'source_game_log': 'docs/gold-game/g001-game-log.json',
    'source_score_log': 'docs/gold-game/s2-score-log.json',
    'source_label': '[deterministic]',
    'result_metrics': {
        'winner': 'villager',
        'game_length': 2,
        'werewolf_survival_rate': 0.0,
        'villager_survival_rate': 0.5,
        'margin': 2,
        'werewolf_win_speed': None,
        'villager_win_efficiency': 1.0,
    },
    'process_metrics': {
        'vote_accuracy_by_player': {
            'p1': {'accurate_votes': 2, 'total_votes': 2, 'vote_accuracy': 1.0},
            'p2': {'accurate_votes': 1, 'total_votes': 1, 'vote_accuracy': 1.0},
            'p3': {'accurate_votes': 1, 'total_votes': 1, 'vote_accuracy': 1.0},
            'p4': {'accurate_votes': 2, 'total_votes': 2, 'vote_accuracy': 1.0},
            'p5': {'accurate_votes': 0, 'total_votes': 1, 'vote_accuracy': 0.0},
            'p6': {'accurate_votes': 1, 'total_votes': 2, 'vote_accuracy': 0.5},
        },
        'survival_rounds': {'p1': 2, 'p2': 2, 'p3': 1, 'p4': 2, 'p5': 2, 'p6': 2},
        'contradiction_count_by_player': {'p1': 0, 'p2': 0, 'p3': 0, 'p4': 0, 'p5': 0, 'p6': 0},
        'info_leak_count_by_player': {'p1': 0, 'p2': 0, 'p3': 0, 'p4': 0, 'p5': 0, 'p6': 0},
        'seer_metrics': {
            'actor': 'p3',
            'check_accuracy': 1.0,
            'check_targeting': 1.0,
            'info_conveyed': 1.0,
            'evidence_event_ids': ['g001_e008', 'g001_e010'],
        },
        'witch_metrics': {
            'actor': 'p4',
            'save_accuracy': 1.0,
            'poison_accuracy': 1.0,
            'ability_utilization': 1.0,
            'evidence_event_ids': ['g001_e009', 'g001_e025'],
        },
        'team_metrics': {
            'village_vote_cohesion': 0.75,
            'village_vote_cohesion_by_day': {'round_1': 0.5, 'round_2': 1.0},
            'werewolf_vote_coordination': 1.0,
            'werewolf_vote_coordination_by_day': {'round_1': 1.0},
        },
    },
    'score_summary': {
        'player_outcome_scores': {'p1': 2, 'p2': 2, 'p3': 4, 'p4': 4, 'p5': -2, 'p6': 0},
        'team_outcome_scores': {'wolf_team': 2},
        'player_rule_integrity_scores': {'p1': 0, 'p2': 0, 'p3': 0, 'p4': 0, 'p5': 0, 'p6': 0},
        'player_decision_quality_scores': {'p1': 0, 'p2': 0, 'p3': 0, 'p4': 0, 'p5': 0, 'p6': 0},
    },
    'metrics_deferred_to_later_spikes': [
        {
            'metric': 'turn_point_count',
            'owner': 'S3 rule attribution validation',
            'reason': 'turn_point_count is defined as an attribution count; S2 does not compute attribution outputs.',
        }
    ],
    'known_rubric_gaps_recorded_not_fixed': [
        {
            'gap': 'werewolf_day_vote_without_elimination',
            'events': ['g001_e033'],
            'S2_policy': 'count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR',
        },
        {
            'gap': 'witch_day_vote_outcome_not_explicit',
            'events': ['g001_e019', 'g001_e034'],
            'S2_policy': 'count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR',
        }
    ],
}

Path('docs/gold-game/s2-metrics-summary.json').write_text(
    json.dumps(metrics, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)
print('Wrote docs/gold-game/s2-metrics-summary.json')
PY
```

Expected result:

```text
Wrote docs/gold-game/s2-metrics-summary.json
```

- [ ] **Step 2: Validate metrics summary against Game Log and Score Log**

```bash
python -m json.tool docs/gold-game/s2-metrics-summary.json > /tmp/s2-metrics-summary.pretty.json
python - <<'PY'
import json
from pathlib import Path

game = json.loads(Path('docs/gold-game/g001-game-log.json').read_text(encoding='utf-8'))
score_log = json.loads(Path('docs/gold-game/s2-score-log.json').read_text(encoding='utf-8'))
metrics = json.loads(Path('docs/gold-game/s2-metrics-summary.json').read_text(encoding='utf-8'))

players = {player['player_id']: player for player in game['players']}
events = {event['event_id']: event for event in game['events']}
records = score_log['records']

assert metrics['result_metrics']['winner'] == game['result']['winner']
assert metrics['result_metrics']['game_length'] == game['result']['end_round']
assert metrics['result_metrics']['margin'] == 2
assert metrics['result_metrics']['werewolf_survival_rate'] == 0.0
assert metrics['result_metrics']['villager_survival_rate'] == 0.5
assert metrics['result_metrics']['villager_win_efficiency'] == 1.0

player_scores = {player_id: 0 for player_id in players}
team_scores = {'wolf_team': 0}
for record in records:
    if record['scope'] == 'player':
        player_scores[record['actor']] += record['outcome_score']
    elif record['scope'] == 'team':
        team_scores[record['actor']] += record['outcome_score']

assert player_scores == metrics['score_summary']['player_outcome_scores']
assert team_scores == metrics['score_summary']['team_outcome_scores']
assert all(value == 0 for value in metrics['score_summary']['player_rule_integrity_scores'].values())
assert all(value == 0 for value in metrics['score_summary']['player_decision_quality_scores'].values())

votes = [event for event in game['events'] if event['type'] == 'player_vote']
assert len(votes) == 9
assert metrics['process_metrics']['vote_accuracy_by_player']['p6']['vote_accuracy'] == 0.5
assert metrics['process_metrics']['team_metrics']['village_vote_cohesion'] == 0.75
assert metrics['process_metrics']['team_metrics']['werewolf_vote_coordination'] == 1.0
assert 'turn_point_count' not in metrics['process_metrics']['team_metrics']
assert metrics['metrics_deferred_to_later_spikes'][0]['metric'] == 'turn_point_count'
assert {item['gap'] for item in metrics['known_rubric_gaps_recorded_not_fixed']} == {
    'werewolf_day_vote_without_elimination',
    'witch_day_vote_outcome_not_explicit',
}
assert events['g001_e038']['target'] == 'villager_team'

print('S2 metrics summary validation passed')
PY
```

Expected result:

```text
S2 metrics summary validation passed
```

---

## Task 4: Create S2 scoring validation report

**Files:**

- Create: `docs/gold-game/s2-scoring-validation.md`
- Modify: none
- Test file: no separate committed test file; the validation command below checks report contents.

- [ ] **Step 1: Write the validation report**

```bash
cat > docs/gold-game/s2-scoring-validation.md <<'EOF'
# S2 Deterministic Scorer Validation — Werewolf-agent Phase 1

## Status

- Task: S2
- Source Game Log: `docs/gold-game/g001-game-log.json`
- Score Log: `docs/gold-game/s2-score-log.json`
- Metrics Summary: `docs/gold-game/s2-metrics-summary.json`
- Data label: `[deterministic]`
- AI annotation: none
- Mock data: none

## Scope

S2 validates that the S1 Game Log can be scored deterministically for Phase 1. It does not implement the production scorer. It creates expected scoring artifacts that E2 can reproduce.

## Phase 1 Scoring Boundary

- `decision_quality_score` is fixed at `0` for every score record because Phase 1 has no real Decision Log.
- `rule_integrity_score` is `0` for every score record because the S1 Game Log contains no `info_leak_flag` or `contradiction_flag` events.
- No AI semantic annotation is used.
- No runtime parser, scorer, attribution engine, UI, or Agent gameplay is implemented.

## Deterministic Outputs

| Output | Purpose |
|---|---|
| `s2-score-log.json` | Event-level deterministic score records with rule and evidence traceability |
| `s2-metrics-summary.json` | Result metrics, process metrics, and score summaries |
| `s2-scoring-validation.md` | Human-readable validation boundary and acceptance report |

## Result Metrics

| Metric | Value | Source |
|---|---:|---|
| winner | villager | `g001_e038`, `result.winner` |
| game_length | 2 | `result.end_round` |
| werewolf_survival_rate | 0.0 | survivors `p4`, `p6`; no surviving werewolves |
| villager_survival_rate | 0.5 | 2 surviving villagers out of 4 village-team players |
| margin | 2 | winning-side survivors 2 minus losing-side survivors 0 |
| villager_win_efficiency | 1.0 | 2 eliminated werewolves / 2 rounds |

## Process Metrics

| Player | Role | Vote accuracy | Survival rounds | Outcome score | Rule integrity score | Decision quality score |
|---|---|---:|---:|---:|---:|---:|
| p1 | werewolf | 1.0 | 2 | 2 | 0 | 0 |
| p2 | werewolf | 1.0 | 2 | 2 | 0 | 0 |
| p3 | seer | 1.0 | 1 | 4 | 0 | 0 |
| p4 | witch | 1.0 | 2 | 4 | 0 | 0 |
| p5 | villager | 0.0 | 2 | -2 | 0 | 0 |
| p6 | villager | 0.5 | 2 | 0 | 0 | 0 |

## Team Metrics

| Metric | Value | Evidence |
|---|---:|---|
| village_vote_cohesion | 0.75 | Round 1 = 0.5, Round 2 = 1.0 |
| werewolf_vote_coordination | 1.0 | Round 1: p1 and p2 both vote p3; Round 2 excluded because only p1 remains |

## Rubric Mapping Notes

- Werewolf night kills are scored as `wolf_team` team-scope records.
- The Night 1 werewolf kill target was a villager, so S2 records the target-selection outcome; `g001_e009` is included as evidence that the witch save prevented that kill from taking effect.
- A werewolf daytime vote that does not cause elimination is recorded as a rubric gap and assigned `outcome_score = 0`.
- Witch daytime votes are counted in vote accuracy metrics, but S2 assigns `outcome_score = 0` because the current Witch rubric has no explicit daytime vote outcome row.
- This PR records the werewolf non-elimination vote gap and Witch vote rubric gap but does not modify `docs/EVALUATION_RUBRIC.md`.
- `decision_quality_score` is not inferred from summaries or visible refs in S2.
- `turn_point_count` is deferred to S3 rule attribution validation and is not emitted as a non-numeric team metric in `s2-metrics-summary.json`.

## S2 Acceptance Check

- [x] Every score record has `rules_triggered` and `evidence_event_ids`.
- [x] Every `decision_quality_score` is `0`.
- [x] Every `rule_integrity_score` is `0`.
- [x] Result metrics are derived from `docs/gold-game/g001-game-log.json`.
- [x] Metrics summary is internally consistent with `s2-score-log.json`.
- [x] No runtime code, dependency manifest, parser, scorer, attribution engine, or UI is introduced.
- [x] Known rubric gap is recorded instead of silently changing stable rubric rules.

## What This Does Not Represent

This S2 output does not mean a production deterministic scorer exists. It only provides fixed expected outputs and validation rules for implementation. It also does not validate AI semantic annotation, Consensus Log scoring, Decision Log scoring, or rule attribution; those remain separate tasks.

## Next Step After S2

After S2 passes review, the next dependency-valid options are:

1. S3 rule attribution validation, using the S2 score outputs and the S1 Game Log.
2. S4 Consensus Log schema validation, which depends on S1 and can proceed independently.
3. S5 AI semantic annotation feasibility, which has no dependency but should not block deterministic scoring.
EOF
```

Expected result: command exits with status 0 and writes `docs/gold-game/s2-scoring-validation.md`.

- [ ] **Step 2: Validate report text and no forbidden claims**

```bash
python - <<'PY'
from pathlib import Path

text = Path('docs/gold-game/s2-scoring-validation.md').read_text(encoding='utf-8')
required = [
    '# S2 Deterministic Scorer Validation',
    'decision_quality_score',
    'fixed at `0`',
    'No AI semantic annotation is used.',
    'does not implement the production scorer',
    'Witch vote rubric gap',
    'werewolf non-elimination vote gap',
    'turn_point_count` is deferred to S3 rule attribution validation',
    'S2 Acceptance Check',
]
for item in required:
    assert item in text, f'missing: {item}'
for forbidden in [
    'AI semantic annotation is validated',
    'Decision Log scoring is complete',
]:
    assert forbidden not in text, f'forbidden claim present: {forbidden}'
print('S2 validation report text check passed')
PY
```

Expected result:

```text
S2 validation report text check passed
```

---

## Task 5: Run full S2 deterministic repeatability check

**Files:**

- Create: none
- Modify: none
- Test file: no separate committed test file; the command below validates repeatability across the S1 Game Log and S2 artifacts.

- [ ] **Step 1: Run repeatability check twice in one command**

```bash
python - <<'PY'
import json
import hashlib
from pathlib import Path

paths = [
    Path('docs/gold-game/g001-game-log.json'),
    Path('docs/gold-game/s2-score-log.json'),
    Path('docs/gold-game/s2-metrics-summary.json'),
]

def load_and_digest():
    payloads = []
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8'))
        payloads.append(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    joined = '\n'.join(payloads)
    return hashlib.sha256(joined.encode('utf-8')).hexdigest()

first = load_and_digest()
second = load_and_digest()
assert first == second
print(f'S2 deterministic repeatability digest: {first}')
PY
```

Expected result:

```text
S2 deterministic repeatability digest: <64-character sha256 hex digest>
```

- [ ] **Step 2: Run final changed-file and whitespace checks**

```bash
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected result:

```text
docs/gold-game/s2-metrics-summary.json
docs/gold-game/s2-score-log.json
docs/gold-game/s2-scoring-validation.md
docs/harness/plans/2026-05-29--s2-deterministic-scorer-validation-plan.md
```

The `git diff --check` command must produce no output.

---

## Implementation PR Description

Use this body for the follow-up S2 implementation PR:

```md
## Summary

Adds S2 deterministic scorer validation artifacts for the Phase 1 Gold Game.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--s2-deterministic-scorer-validation-plan.md`

## Scope

- Creates `docs/gold-game/s2-score-log.json`.
- Creates `docs/gold-game/s2-metrics-summary.json`.
- Creates `docs/gold-game/s2-scoring-validation.md`.
- Corrects this bound plan's embedded S2 examples after implementation review so the plan remains reproducible.
- Applies deterministic Phase 1 scoring to `docs/gold-game/g001-game-log.json`.
- Records event-level score evidence and rule mappings.
- Records result metrics, process metrics, per-player score summaries, and a repeatability check.

## Out of Scope

- No business code.
- No parser.
- No production scorer.
- No attribution engine.
- No UI.
- No dependencies.
- No real AI Agent gameplay.
- No real `decision_quality_score`.
- No AI semantic annotations.
- No changes to `docs/EVALUATION_RUBRIC.md`.

## Validation

```bash
python -m json.tool docs/gold-game/s2-score-log.json > /tmp/s2-score-log.pretty.json
python -m json.tool docs/gold-game/s2-metrics-summary.json > /tmp/s2-metrics-summary.pretty.json
python - <<'PY'
import json
from pathlib import Path

for path in [
    Path('docs/gold-game/g001-game-log.json'),
    Path('docs/gold-game/s2-score-log.json'),
    Path('docs/gold-game/s2-metrics-summary.json'),
]:
    json.loads(path.read_text(encoding='utf-8'))

score_log = json.loads(Path('docs/gold-game/s2-score-log.json').read_text(encoding='utf-8'))
metrics = json.loads(Path('docs/gold-game/s2-metrics-summary.json').read_text(encoding='utf-8'))
assert len(score_log['records']) == 14
assert all(record['decision_quality_score'] == 0 for record in score_log['records'])
assert all(record['rule_integrity_score'] == 0 for record in score_log['records'])
assert metrics['result_metrics']['winner'] == 'villager'
assert metrics['process_metrics']['team_metrics']['village_vote_cohesion'] == 0.75
assert metrics['process_metrics']['team_metrics']['werewolf_vote_coordination'] == 1.0
assert 'turn_point_count' not in metrics['process_metrics']['team_metrics']
print('S2 implementation validation passed')
PY
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected changed files:

```text
docs/gold-game/s2-metrics-summary.json
docs/gold-game/s2-score-log.json
docs/gold-game/s2-scoring-validation.md
docs/harness/plans/2026-05-29--s2-deterministic-scorer-validation-plan.md
```

## Risk

The main risk is rubric interpretation drift: Witch daytime votes currently have no explicit role-specific outcome row, and a werewolf daytime vote that does not cause elimination also lacks an explicit stable rubric row. This PR records those gaps, counts the votes in vote accuracy metrics, assigns those vote score records `outcome_score = 0`, and does not modify `docs/EVALUATION_RUBRIC.md`.
```

## Self-Review Checklist

- [ ] The plan path is `docs/harness/plans/2026-05-29--s2-deterministic-scorer-validation-plan.md`.
- [ ] Every task lists files, validation commands, and expected results.
- [ ] No step uses placeholder language such as TBD, TODO, or later implementation.
- [ ] The plan does not ask the implementation agent to modify business code.
- [ ] The plan records Phase 1 `decision_quality_score = 0` clearly.
- [ ] The follow-up Implementation PR description is ready to paste.
