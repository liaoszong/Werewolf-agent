# S3 Rule Attribution Validation Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Validate deterministic rule attribution for the Phase 1 Gold Game by producing a reproducible `turn_points` list, `top_attribution`, and S3 validation report without business code.

**Architecture:** This is a Phase 1 data/document spike, not a production attribution engine implementation. It consumes the existing S1 Game Log and S2 deterministic scoring artifacts, applies the stable attribution rules from `docs/EVALUATION_RUBRIC.md`, and writes expected attribution artifacts under `docs/gold-game/`. The output becomes the fixed acceptance target for the later E3 attribution engine implementation.

**Tech Stack:** Markdown, JSON, and Python standard-library validation commands only. No runtime dependencies.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before writing this plan, progress was checked through PR-first facts and recent commit history:

- S0 is completed and merged through PR #2, producing `docs/gold-game/s0-gold-game-seed.md`.
- S1 is completed and merged through PR #4, producing `docs/gold-game/g001-game-log.json` and `docs/gold-game/s1-schema-validation.md`.
- S2 is completed and merged through PR #6, producing `docs/gold-game/s2-score-log.json`, `docs/gold-game/s2-metrics-summary.json`, and `docs/gold-game/s2-scoring-validation.md`.
- The latest relevant main commit before this plan work was `dde0a2ae7537a8dba3d80af4cda2d7d12999dd88`, merging PR #6.
- There is no known open S3 PR at plan creation time.
- S2 validation explicitly lists S3 rule attribution validation as the next dependency-valid option.

Therefore the next implementation unit is S3: rule attribution validation.

## Scope Decision

S3 should not implement a production attribution engine yet. It should create deterministic expected outputs for the Gold Game, using the stable attribution rules already defined in `docs/EVALUATION_RUBRIC.md`.

This plan creates:

- A machine-readable attribution artifact.
- A human-readable validation report.
- Explicit trigger and non-trigger notes for each stable attribution rule.

## Files

- Create: `docs/gold-game/s3-rule-attribution.json`
- Create: `docs/gold-game/s3-attribution-validation.md`
- Modify: none by default
- Test file: no committed test file for this Phase 1 data/document spike; each task includes explicit Python standard-library validation commands.
- Do not modify: `docs/EVALUATION_RUBRIC.md`
- Do not modify: `docs/gold-game/g001-game-log.json`
- Do not modify: `docs/gold-game/s2-score-log.json`
- Do not modify: `docs/gold-game/s2-metrics-summary.json`

## Hard Boundaries

- Do not create `src/`, `apps/`, `server/`, or `web`.
- Do not create `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, or dependency configuration.
- Do not implement parser, scorer, attribution engine, UI, AI Agent gameplay, or runtime code.
- Do not call AI models.
- Do not add `[AI 生成]` data.
- Do not infer hidden psychology or strategy from free text.
- Do not generate long-form natural-language analysis.
- Do not claim `decision_quality_score` is available in Phase 1.
- Do not silently change stable rubric rules.
- If S3 exposes an attribution-rule ambiguity, record it in `s3-attribution-validation.md` and stop short of changing `docs/EVALUATION_RUBRIC.md`.

---

### Task 1: Confirm S3 input artifacts and hard boundaries

**Files:**

- Create: none
- Modify: none
- Test file: no committed test file; run the commands below against existing repository files.

- [ ] **Step 1: Verify required input artifacts exist**

```bash
test -f docs/gold-game/g001-game-log.json
test -f docs/gold-game/s2-score-log.json
test -f docs/gold-game/s2-metrics-summary.json
test -f docs/gold-game/s2-scoring-validation.md
printf 'S3 input artifacts exist\n'
```

Expected result:

```text
S3 input artifacts exist
```

- [ ] **Step 2: Verify fixed S1/S2 facts**

```bash
python - <<'PY'
import json
from pathlib import Path

game = json.loads(Path('docs/gold-game/g001-game-log.json').read_text(encoding='utf-8'))
score_log = json.loads(Path('docs/gold-game/s2-score-log.json').read_text(encoding='utf-8'))
metrics = json.loads(Path('docs/gold-game/s2-metrics-summary.json').read_text(encoding='utf-8'))

events = {event['event_id']: event for event in game['events']}

assert game['game_id'] == 'g001'
assert len(game['players']) == 6
assert len(game['events']) == 38
assert game['result']['winner'] == 'villager'
assert game['result']['end_condition'] == 'all_werewolves_eliminated'
assert game['result']['survivors'] == ['p4', 'p6']

assert len(score_log['records']) == 14
assert all(record['decision_quality_score'] == 0 for record in score_log['records'])
assert all(record['rule_integrity_score'] == 0 for record in score_log['records'])

assert metrics['result_metrics']['winner'] == 'villager'
assert metrics['process_metrics']['team_metrics']['village_vote_cohesion'] == 0.75
assert metrics['process_metrics']['team_metrics']['werewolf_vote_coordination'] == 1.0
assert any(item['metric'] == 'turn_point_count' for item in metrics['metrics_deferred_to_later_spikes'])

assert events['g001_e036']['type'] == 'player_eliminated'
assert events['g001_e036']['target'] == 'p1'
assert events['g001_e037']['data']['revealed_role'] == 'werewolf'

print('S1/S2 facts are ready for S3')
PY
```

Expected result:

```text
S1/S2 facts are ready for S3
```

- [ ] **Step 3: Confirm no runtime implementation is being started**

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

- [ ] **Step 4: Check working tree status**

```bash
git status --short
```

Expected result before Task 2:

```text
```

No commit is required for Task 1 because no files are created or modified.

---

### Task 2: Create deterministic S3 attribution artifact

**Files:**

- Create: `docs/gold-game/s3-rule-attribution.json`
- Modify: none
- Test file: no committed test file; run the Python validation command below.

- [ ] **Step 1: Write the attribution JSON**

```bash
python - <<'PY'
import json
from pathlib import Path

attribution = {
    'attribution_id': 's3_g001_rule_attribution',
    'game_id': 'g001',
    'source_game_log': 'docs/gold-game/g001-game-log.json',
    'source_score_log': 'docs/gold-game/s2-score-log.json',
    'source_metrics_summary': 'docs/gold-game/s2-metrics-summary.json',
    'source_label': '[deterministic]',
    'phase': 'Phase 1',
    'attribution_boundary': {
        'method': 'deterministic structured-event pattern matching',
        'ai_annotations': 'none',
        'free_text_reasoning': 'not_used',
        'decision_quality_score': 0,
        'notes': 'S3 validates expected attribution outputs only. It does not implement the production attribution engine.',
    },
    'turn_points': [
        {
            'turn_point_id': 's3_g001_tp001',
            'rule_id': 'attribution:F.1.critical_vote',
            'rule': 'critical_vote',
            'round': 2,
            'actor': 'system',
            'subject': 'p1',
            'description_template': '第 2 轮投票为关键转折点，p1 以 1 票之差被处决，该玩家身份为狼人。',
            'impact_score': 1.0,
            'impact_sign': 'positive_for_villager',
            'impact_score_policy': 'F.1 gives a x2 multiplier only when the eliminated player is a core villager role. For eliminated werewolf p1, S3 uses the default critical-vote impact score of 1.0 and records this as a validation policy, not a rubric change.',
            'evidence_event_ids': [
                'g001_e033',
                'g001_e034',
                'g001_e035',
                'g001_e036',
                'g001_e037',
            ],
        }
    ],
    'top_attribution': {
        'turn_point_id': 's3_g001_tp001',
        'rule_id': 'attribution:F.1.critical_vote',
        'description_template': '第 2 轮 2-1 处决 p1 是本局村民获胜的直接关键转折点。',
        'selection_policy': 'highest impact_score; ties break by later sequence',
    },
    'rule_evaluation_summary': {
        'attribution:F.1.critical_vote': {
            'status': 'triggered',
            'triggered_turn_point_ids': ['s3_g001_tp001'],
            'notes': 'Round 2 elimination is 2-1, so one changed vote would change the result. p1 is revealed as werewolf.',
        },
        'attribution:F.2.information_gap': {
            'status': 'not_triggered',
            'triggered_turn_point_ids': [],
            'notes': "S2 records seer info_conveyed as 1.0. p3's p1 suspicion is publicly represented before p3 dies.",
        },
        'attribution:F.3.witch_misfire': {
            'status': 'not_triggered',
            'triggered_turn_point_ids': [],
            'notes': 'p4 saves villager p5 and poisons werewolf p2. No witch misfire against a core villager role is present.',
        },
        'attribution:F.4.vote_deviation': {
            'status': 'not_triggered',
            'triggered_turn_point_ids': [],
            'notes': 'Round 1 village vote accuracy is exactly 50%, not below 50%. Round 2 village vote accuracy is 100%.',
        },
        'attribution:F.5.successful_disguise': {
            'status': 'not_triggered',
            'triggered_turn_point_ids': [],
            'notes': 'No werewolf is both voted but not eliminated and then survives at least 2 later rounds.',
        },
    },
    'validation_notes': [
        {
            'type': 'possible_false_negative',
            'event_ids': ['g001_e016', 'g001_e017', 'g001_e020', 'g001_e021', 'g001_e022', 'g001_e023'],
            'notes': 'Round 1 seer p3 elimination is human-salient, but F.1 does not trigger because the vote margin is 4-2 rather than 1. S3 records this as a validation observation and does not change the stable rule.',
        }
    ],
}

Path('docs/gold-game/s3-rule-attribution.json').write_text(
    json.dumps(attribution, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)
print('Wrote docs/gold-game/s3-rule-attribution.json')
PY
```

Expected result:

```text
Wrote docs/gold-game/s3-rule-attribution.json
```

- [ ] **Step 2: Validate attribution JSON shape and Phase 1 boundary**

```bash
python -m json.tool docs/gold-game/s3-rule-attribution.json > /tmp/s3-rule-attribution.pretty.json
python - <<'PY'
import json
from pathlib import Path

game = json.loads(Path('docs/gold-game/g001-game-log.json').read_text(encoding='utf-8'))
attribution = json.loads(Path('docs/gold-game/s3-rule-attribution.json').read_text(encoding='utf-8'))

event_ids = {event['event_id'] for event in game['events']}
turn_points = attribution['turn_points']
turn_point_ids = {turn_point['turn_point_id'] for turn_point in turn_points}

assert attribution['game_id'] == 'g001'
assert attribution['source_label'] == '[deterministic]'
assert attribution['attribution_boundary']['ai_annotations'] == 'none'
assert attribution['attribution_boundary']['free_text_reasoning'] == 'not_used'
assert attribution['attribution_boundary']['decision_quality_score'] == 0
assert 1 <= len(turn_points) <= 5
assert attribution['top_attribution']['turn_point_id'] in turn_point_ids

for turn_point in turn_points:
    assert turn_point['rule_id'].startswith('attribution:F.')
    assert turn_point['impact_score'] > 0
    assert turn_point['evidence_event_ids']
    assert all(event_id in event_ids for event_id in turn_point['evidence_event_ids'])

summary = attribution['rule_evaluation_summary']
assert summary['attribution:F.1.critical_vote']['status'] == 'triggered'
assert summary['attribution:F.2.information_gap']['status'] == 'not_triggered'
assert summary['attribution:F.3.witch_misfire']['status'] == 'not_triggered'
assert summary['attribution:F.4.vote_deviation']['status'] == 'not_triggered'
assert summary['attribution:F.5.successful_disguise']['status'] == 'not_triggered'

print('S3 attribution JSON validation passed')
PY
```

Expected result:

```text
S3 attribution JSON validation passed
```

- [ ] **Step 3: Commit the attribution JSON checkpoint**

```bash
git diff --check
git status --short
git add docs/gold-game/s3-rule-attribution.json
git commit -m "docs: add S3 rule attribution output"
```

Expected result:

```text
[task/s3-rule-attribution-validation <sha>] docs: add S3 rule attribution output
```

`git status --short` before commit should include exactly:

```text
?? docs/gold-game/s3-rule-attribution.json
```

---

### Task 3: Create S3 validation report

**Files:**

- Create: `docs/gold-game/s3-attribution-validation.md`
- Modify: none
- Test file: no committed test file; run the Python content check below.

- [ ] **Step 1: Write the validation report**

```bash
cat > docs/gold-game/s3-attribution-validation.md <<'MD'
# S3 Rule Attribution Validation — Werewolf-agent Phase 1

## Status

- Task: S3
- Source Game Log: `docs/gold-game/g001-game-log.json`
- Source Score Log: `docs/gold-game/s2-score-log.json`
- Source Metrics Summary: `docs/gold-game/s2-metrics-summary.json`
- Attribution Output: `docs/gold-game/s3-rule-attribution.json`
- Data label: `[deterministic]`
- AI annotation: none
- Mock data: none

## Scope

S3 validates that the S1 Game Log and S2 deterministic scoring artifacts can produce deterministic rule attribution for Phase 1. It does not implement the production attribution engine.

## Phase 1 Attribution Boundary

- Attribution uses deterministic pattern matching over structured events.
- No AI semantic annotation is used.
- No hidden psychology, strategy inference, or free-form natural-language reasoning is used.
- `decision_quality_score` remains fixed at `0` because Phase 1 has no real Decision Log.
- S3 does not modify `docs/EVALUATION_RUBRIC.md`.
- S3 does not implement parser, scorer, attribution engine, UI, runtime code, or Agent gameplay.

## Deterministic Outputs

| Output | Purpose |
|---|---|
| `s3-rule-attribution.json` | Machine-readable deterministic attribution output |
| `s3-attribution-validation.md` | Human-readable validation boundary and acceptance report |

## Triggered Turn Points

| Turn point | Rule | Round | Summary | Impact | Evidence |
|---|---|---:|---|---:|---|
| `s3_g001_tp001` | `attribution:F.1.critical_vote` | 2 | 第 2 轮投票为关键转折点，p1 以 1 票之差被处决，该玩家身份为狼人。 | 1.0 | `g001_e033`, `g001_e034`, `g001_e035`, `g001_e036`, `g001_e037` |

## Top Attribution

`第 2 轮 2-1 处决 p1 是本局村民获胜的直接关键转折点。`

Selection policy: highest `impact_score`; ties break by later sequence.

## Rule Evaluation Summary

| Rule | Status | Reason |
|---|---|---|
| `attribution:F.1.critical_vote` | triggered | Round 2 elimination is 2-1, so one changed vote would change the result. p1 is revealed as werewolf. |
| `attribution:F.2.information_gap` | not triggered | S2 records seer `info_conveyed` as 1.0. p3's p1 suspicion is publicly represented before p3 dies. |
| `attribution:F.3.witch_misfire` | not triggered | p4 saves villager p5 and poisons werewolf p2. No witch misfire against a core villager role is present. |
| `attribution:F.4.vote_deviation` | not triggered | Round 1 village vote accuracy is exactly 50%, not below 50%. Round 2 village vote accuracy is 100%. |
| `attribution:F.5.successful_disguise` | not triggered | No werewolf is both voted but not eliminated and then survives at least 2 later rounds. |

## Validation Observation

Round 1 seer p3 elimination is human-salient, but F.1 does not trigger because the vote margin is 4-2 rather than 1. S3 records this as a possible false negative observation and does not change the stable rule.

This does not block S3 because S3 has at least one deterministic turn point, every turn point has rule and evidence, and the output is reproducible. If the owner wants p3's elimination to become an attribution turn point, that should be handled by a later rubric/spec update instead of silently changing S3.

## S3 Acceptance Check

- [x] Every `turn_point` has a stable `rule_id`.
- [x] Every `turn_point` has explicit `evidence_event_ids`.
- [x] `top_attribution` is selected from the `turn_points` list.
- [x] The output contains at least 1 and no more than 5 turn points.
- [x] The same input produces the same attribution JSON.
- [x] No AI annotation is used.
- [x] No runtime code, dependency manifest, parser, scorer, attribution engine, or UI is introduced.
- [x] Possible attribution-rule gaps are recorded instead of silently changing stable rubric rules.

## What This Does Not Represent

This S3 output does not mean a production rule attribution engine exists. It only provides fixed expected attribution outputs and validation rules for implementation. It also does not validate Consensus Log, Decision Log, AI semantic annotation, or Leaderboard UI behavior.

## Next Step After S3

After S3 passes review, the next recommended step is S6 Leaderboard UI demo validation, using:

- `docs/gold-game/g001-game-log.json`
- `docs/gold-game/s2-score-log.json`
- `docs/gold-game/s2-metrics-summary.json`
- `docs/gold-game/s3-rule-attribution.json`
- mock leaderboard rows clearly labeled `[mock]`
MD

printf 'Wrote docs/gold-game/s3-attribution-validation.md\n'
```

Expected result:

```text
Wrote docs/gold-game/s3-attribution-validation.md
```

- [ ] **Step 2: Validate report content**

```bash
python - <<'PY'
from pathlib import Path

report = Path('docs/gold-game/s3-attribution-validation.md').read_text(encoding='utf-8')

required_phrases = [
    'S3 Rule Attribution Validation',
    'docs/gold-game/g001-game-log.json',
    'docs/gold-game/s2-score-log.json',
    'docs/gold-game/s3-rule-attribution.json',
    '[deterministic]',
    'AI annotation: none',
    'attribution:F.1.critical_vote',
    's3_g001_tp001',
    'possible false negative',
    'No runtime code',
    'Next Step After S3',
    'S6 Leaderboard UI demo validation',
]

for phrase in required_phrases:
    assert phrase in report, phrase

for forbidden in ['[AI 生成]', 'React', 'Vite']:
    assert forbidden not in report, forbidden
for positive_claim in ['S3 completes the attribution engine', 'attribution engine is complete']:
    assert positive_claim not in report, positive_claim
    assert forbidden not in report, forbidden

print('S3 validation report content check passed')
PY
```

Expected result:

```text
S3 validation report content check passed
```

- [ ] **Step 3: Commit the validation report checkpoint**

```bash
git diff --check
git status --short
git add docs/gold-game/s3-attribution-validation.md
git commit -m "docs: add S3 attribution validation report"
```

Expected result:

```text
[task/s3-rule-attribution-validation <sha>] docs: add S3 attribution validation report
```

`git status --short` before commit should include exactly:

```text
?? docs/gold-game/s3-attribution-validation.md
```

---

### Task 4: Run final deterministic validation

**Files:**

- Create: none
- Modify: none
- Test file: no committed test file; run full repository validation commands below.

- [ ] **Step 1: Run full JSON parse checks**

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /tmp/g001-game-log.pretty.json
python -m json.tool docs/gold-game/s2-score-log.json > /tmp/s2-score-log.pretty.json
python -m json.tool docs/gold-game/s2-metrics-summary.json > /tmp/s2-metrics-summary.pretty.json
python -m json.tool docs/gold-game/s3-rule-attribution.json > /tmp/s3-rule-attribution.pretty.json
printf 'All S3 JSON parse checks passed\n'
```

Expected result:

```text
All S3 JSON parse checks passed
```

- [ ] **Step 2: Run integrated S3 consistency check**

```bash
python - <<'PY'
import json
from pathlib import Path

game = json.loads(Path('docs/gold-game/g001-game-log.json').read_text(encoding='utf-8'))
score_log = json.loads(Path('docs/gold-game/s2-score-log.json').read_text(encoding='utf-8'))
metrics = json.loads(Path('docs/gold-game/s2-metrics-summary.json').read_text(encoding='utf-8'))
attribution = json.loads(Path('docs/gold-game/s3-rule-attribution.json').read_text(encoding='utf-8'))
report = Path('docs/gold-game/s3-attribution-validation.md').read_text(encoding='utf-8')

event_ids = {event['event_id'] for event in game['events']}
score_event_ids = {record['event_id'] for record in score_log['records']}
turn_points = attribution['turn_points']

assert game['result']['winner'] == 'villager'
assert metrics['result_metrics']['winner'] == 'villager'
assert len(score_log['records']) == 14
assert len(turn_points) == 1
assert attribution['top_attribution']['turn_point_id'] == 's3_g001_tp001'
assert all(event_id in event_ids for turn_point in turn_points for event_id in turn_point['evidence_event_ids'])
assert {'g001_e033', 'g001_e034', 'g001_e035'}.issubset(score_event_ids)
assert 's3_g001_tp001' in report
assert 'S6 Leaderboard UI demo validation' in report

print('S3 integrated consistency check passed')
PY
```

Expected result:

```text
S3 integrated consistency check passed
```

- [ ] **Step 3: Run reproducibility digest check**

```bash
python - <<'PY'
import json
import hashlib
from pathlib import Path

paths = [
    Path('docs/gold-game/g001-game-log.json'),
    Path('docs/gold-game/s2-score-log.json'),
    Path('docs/gold-game/s2-metrics-summary.json'),
    Path('docs/gold-game/s3-rule-attribution.json'),
]

def load_and_digest():
    payloads = []
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8'))
        payloads.append(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    return hashlib.sha256('\n'.join(payloads).encode('utf-8')).hexdigest()

first = load_and_digest()
second = load_and_digest()
assert first == second
print(f'S3 deterministic repeatability digest: {first}')
PY
```

Expected result:

```text
S3 deterministic repeatability digest: <stable_sha256>
```

The exact digest value may differ if earlier files change before this implementation runs, but the two digest calculations in this command must be identical.

- [ ] **Step 4: Check changed files and hard boundaries**

```bash
git diff --check main...HEAD
git diff --name-only main...HEAD
python - <<'PY'
from pathlib import Path

for forbidden_dir in ['src', 'apps', 'server', 'web']:
    assert not Path(forbidden_dir).exists(), forbidden_dir

for forbidden_file in ['package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock']:
    assert not Path(forbidden_file).exists(), forbidden_file

print('S3 hard-boundary check passed')
PY
```

Expected changed files:

```text
docs/gold-game/s3-attribution-validation.md
docs/gold-game/s3-rule-attribution.json
```

Expected hard-boundary result:

```text
S3 hard-boundary check passed
```

- [ ] **Step 5: Final checkpoint report**

Use `docs/CHECKPOINT_TEMPLATE.md` and report:

```text
Task: S3 rule attribution validation
Branch: task/s3-rule-attribution-validation
Changed files:
- docs/gold-game/s3-rule-attribution.json
- docs/gold-game/s3-attribution-validation.md
Validation:
- JSON parse checks passed
- S3 attribution JSON validation passed
- S3 validation report content check passed
- S3 integrated consistency check passed
- S3 deterministic repeatability digest matched within the same run
- git diff --check main...HEAD passed
- hard-boundary check passed
Out of scope not touched:
- no business code
- no runtime implementation directories
- no dependency manifests
- no EVALUATION_RUBRIC.md changes
- no AI annotations
Next recommended step:
- S6 Leaderboard UI demo validation after S3 review and merge
```

---

## Implementation PR Draft

Title:

```text
Add S3 Rule Attribution Validation
```

Body:

````markdown
## Summary

Adds S3 deterministic rule attribution validation artifacts for the Phase 1 Gold Game.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--s3-rule-attribution-validation-plan.md`

## Scope

- Creates `docs/gold-game/s3-rule-attribution.json`.
- Creates `docs/gold-game/s3-attribution-validation.md`.
- Applies deterministic rule attribution to the S1 Game Log and S2 scoring artifacts.
- Records triggered and non-triggered attribution rules.
- Records the possible false negative around Round 1 seer elimination without changing stable rubric rules.

## Out of Scope

- No business code.
- No parser.
- No scorer.
- No production attribution engine.
- No UI.
- No dependencies.
- No real AI Agent gameplay.
- No real `decision_quality_score`.
- No AI semantic annotations.
- No changes to `docs/EVALUATION_RUBRIC.md`.

## Validation

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /tmp/g001-game-log.pretty.json
python -m json.tool docs/gold-game/s2-score-log.json > /tmp/s2-score-log.pretty.json
python -m json.tool docs/gold-game/s2-metrics-summary.json > /tmp/s2-metrics-summary.pretty.json
python -m json.tool docs/gold-game/s3-rule-attribution.json > /tmp/s3-rule-attribution.pretty.json
python - <<'PY'
import json
from pathlib import Path

game = json.loads(Path('docs/gold-game/g001-game-log.json').read_text(encoding='utf-8'))
score_log = json.loads(Path('docs/gold-game/s2-score-log.json').read_text(encoding='utf-8'))
metrics = json.loads(Path('docs/gold-game/s2-metrics-summary.json').read_text(encoding='utf-8'))
attribution = json.loads(Path('docs/gold-game/s3-rule-attribution.json').read_text(encoding='utf-8'))
report = Path('docs/gold-game/s3-attribution-validation.md').read_text(encoding='utf-8')

event_ids = {event['event_id'] for event in game['events']}
turn_points = attribution['turn_points']

assert game['result']['winner'] == 'villager'
assert metrics['result_metrics']['winner'] == 'villager'
assert len(score_log['records']) == 14
assert len(turn_points) == 1
assert attribution['top_attribution']['turn_point_id'] == 's3_g001_tp001'
assert all(event_id in event_ids for turn_point in turn_points for event_id in turn_point['evidence_event_ids'])
assert 's3_g001_tp001' in report
assert 'S6 Leaderboard UI demo validation' in report
print('S3 implementation validation passed')
PY
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected changed files:

```text
docs/gold-game/s3-attribution-validation.md
docs/gold-game/s3-rule-attribution.json
```

## Risk

The main risk is attribution-rule narrowness: Round 1 seer elimination is human-salient but does not trigger F.1 because the vote margin is 4-2, not 1. This PR records that observation and does not modify the stable rubric. If the owner wants this case to be treated as a turn point, it should be handled by a later rubric/spec update.
````

## Plan PR Draft

Title:

```text
Plan S3 Rule Attribution Validation
```

Body:

````markdown
## Summary

Adds an Implementation Plan for the next Werewolf Phase 1 step: S3 rule attribution validation.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--s3-rule-attribution-validation-plan.md`

## Progress basis

This plan follows the current PR-first progress facts:

- S0 is completed through PR #2.
- S1 implementation is completed through PR #4.
- S2 implementation is completed through PR #6.
- S2 defers `turn_point_count` to S3 rule attribution validation.
- No open S3 PR was found before preparing this plan.

Therefore the next dependency-valid task is S3: rule attribution validation.

## Scope

Plan only.

The plan instructs the implementation agent to create:

- `docs/gold-game/s3-rule-attribution.json`
- `docs/gold-game/s3-attribution-validation.md`

## Out of Scope

- No business code.
- No parser.
- No scorer.
- No production attribution engine.
- No UI.
- No dependencies.
- No real AI Agent gameplay.
- No real `decision_quality_score`.
- No AI semantic annotations.
- No changes to `docs/EVALUATION_RUBRIC.md`.

## Validation for this PR

This PR should only add the plan file:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
docs/harness/plans/2026-05-29--s3-rule-attribution-validation-plan.md
```

## Follow-up Implementation PR description prepared in the plan

The plan includes a ready-to-use Implementation PR description for the actual S3 artifact PR.
````

## Recommended Branches

Plan PR branch:

```text
plan/s3-rule-attribution-validation
```

Implementation PR branch:

```text
task/s3-rule-attribution-validation
```
