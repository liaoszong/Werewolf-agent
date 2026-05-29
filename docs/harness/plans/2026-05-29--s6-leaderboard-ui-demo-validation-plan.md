# S6 Leaderboard UI Demo Validation Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Build a Phase 1 static HTML Gold Demo page that lets a non-technical user understand the evaluated Werewolf game, deterministic scores, rule attribution, and mock Leaderboard within 3 minutes.

**Architecture:** This is a Phase 1 UI validation spike, not a production frontend. It creates one self-contained static HTML file under `docs/demo/`, consuming the existing Gold Game artifacts from `docs/gold-game/` as fixed reference data. The page must clearly distinguish `[结构化事件]`, `[deterministic]`, and `[mock]` data, and must not introduce a build system, runtime dependency, backend, React/Vite app, or production UI architecture.

**Tech Stack:** Plain HTML, CSS, and vanilla JavaScript in a single file. Python standard library may be used only for validation checks. No npm dependencies.

---

## Writing-plan mode

我正在使用 writing-plans 来创建实施计划。

## Progress Check Summary

Before writing this plan, progress must be checked through PR-first facts and main artifacts:

- S0 is completed and merged through PR #2, producing `docs/gold-game/s0-gold-game-seed.md`.
- S1 is completed and merged through PR #4, producing `docs/gold-game/g001-game-log.json` and `docs/gold-game/s1-schema-validation.md`.
- S2 is completed and merged through PR #6, producing `docs/gold-game/s2-score-log.json`, `docs/gold-game/s2-metrics-summary.json`, and `docs/gold-game/s2-scoring-validation.md`.
- S3 is completed and merged through PR #7, producing `docs/gold-game/s3-rule-attribution.json` and `docs/gold-game/s3-attribution-validation.md`.
- There is no open S6 PR at plan creation time.
- `docs/TASKS.md` may lag behind merged PRs; use merged PRs and main artifacts as the progress source of truth.

Therefore the next implementation unit is S6: Leaderboard UI demo validation.

## Scope Decision

S6 should create the first strongly user-visible Phase 1 artifact: a directly openable static Gold Demo page.

This implementation creates:

- `docs/demo/phase1-gold-demo.html`

The HTML page must include:

- Gold Game summary.
- Timeline view.
- Player status table.
- Vote table.
- Result metrics.
- Process metrics.
- Single-game score card.
- Rule attribution panel.
- Leaderboard UI demo with one Gold Game deterministic row and multiple `[mock]` rows.
- Sort switching for supported Leaderboard dimensions.
- Sample-size warnings.

## Files

- Create: `docs/demo/phase1-gold-demo.html`
- Modify: none by default
- Test file: no committed test file for this Phase 1 static-demo spike; each task includes explicit Python standard-library validation commands.
- Use as input:
  - `docs/gold-game/g001-game-log.json`
  - `docs/gold-game/s2-score-log.json`
  - `docs/gold-game/s2-metrics-summary.json`
  - `docs/gold-game/s3-rule-attribution.json`
- Do not modify:
  - `docs/EVALUATION_RUBRIC.md`
  - `docs/GOLD_DEMO.md`
  - `docs/SPIKES.md`
  - existing `docs/gold-game/*` artifacts

## Hard Boundaries

- Do not create `src/`, `apps/`, `server/`, or `web`.
- Do not create `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, or any dependency manifest.
- Do not introduce React, Vite, Vue, Svelte, Tailwind build config, backend services, or runtime dependencies.
- Do not implement a parser, scorer, attribution engine, game engine, or AI Agent gameplay.
- Do not call AI models.
- Do not claim the Leaderboard is real.
- Do not claim `decision_quality_score` is genuinely available in Phase 1.
- All non-Gold-Game leaderboard rows must be visually marked `[mock]`.
- All deterministic scoring and attribution sections must be visually marked `[deterministic]`.
- All Game Log event sections must be visually marked `[结构化事件]`.

---

### Task 1: Confirm required inputs and Phase 1 boundaries

**Files:**

- Create: none
- Modify: none
- Test file: no committed test file; run the commands below against existing repository files.

- [ ] **Step 1: Verify required input artifacts exist**

```bash
test -f docs/gold-game/g001-game-log.json
test -f docs/gold-game/s2-score-log.json
test -f docs/gold-game/s2-metrics-summary.json
test -f docs/gold-game/s3-rule-attribution.json
printf 'S6 input artifacts exist\n'
```

Expected result:

```text
S6 input artifacts exist
```

- [ ] **Step 2: Verify the repository still has no runtime implementation directories**

```bash
test ! -d src
test ! -d apps
test ! -d server
test ! -d web
test ! -f package.json
test ! -f package-lock.json
test ! -f pnpm-lock.yaml
test ! -f yarn.lock
printf 'Phase 1 static-demo boundary is intact\n'
```

Expected result:

```text
Phase 1 static-demo boundary is intact
```

- [ ] **Step 3: Verify fixed Gold Game facts**

```bash
python - <<'PY'
import json
from pathlib import Path

game = json.loads(Path('docs/gold-game/g001-game-log.json').read_text(encoding='utf-8'))
metrics = json.loads(Path('docs/gold-game/s2-metrics-summary.json').read_text(encoding='utf-8'))
attribution = json.loads(Path('docs/gold-game/s3-rule-attribution.json').read_text(encoding='utf-8'))

assert game['game_id'] == 'g001'
assert len(game['players']) == 6
assert len(game['events']) == 38
assert game['result']['winner'] == 'villager'
assert game['result']['end_round'] == 2
assert game['result']['survivors'] == ['p4', 'p6']

assert metrics['result_metrics']['winner'] == 'villager'
assert metrics['source_label'] == '[deterministic]'
assert metrics['score_summary']['player_decision_quality_scores'] == {
    'p1': 0,
    'p2': 0,
    'p3': 0,
    'p4': 0,
    'p5': 0,
    'p6': 0,
}

assert attribution['source_label'] == '[deterministic]'
assert len(attribution['turn_points']) >= 1
assert len(attribution['turn_points']) <= 5
assert attribution['top_attribution']['turn_point_id'] == 's3_g001_tp001'

print('Gold Game UI facts are ready')
PY
```

Expected result:

```text
Gold Game UI facts are ready
```

No commit is required for Task 1 because no files are created or modified.

---

### Task 2: Create the static demo page skeleton

**Files:**

- Create: `docs/demo/phase1-gold-demo.html`
- Modify: none
- Test file: no committed test file; run the validation command below.

- [ ] **Step 1: Create `docs/demo/` and the initial HTML structure**

Create `docs/demo/phase1-gold-demo.html` with these top-level sections:

```text
1. Header / demo boundary
2. Gold Game summary
3. Timeline
4. Player status table
5. Vote table
6. Result metrics
7. Process metrics
8. Score card
9. Rule attribution
10. Leaderboard demo
```

The file must be self-contained and include embedded CSS and embedded vanilla JavaScript.

- [ ] **Step 2: Add visible Phase 1 limitation banner**

The banner must include these exact facts in human-readable text:

```text
Phase 1 只做静态 HTML UI demo。
不包含真实 AI Agent 对局。
decision_quality_score 在 Phase 1 固定为 0。
Leaderboard 只是一行 Gold Game deterministic 数据 + 多行 mock 数据。
```

- [ ] **Step 3: Add embedded CSS**

Minimum visual requirements:

```text
- Clear page title.
- Clear data labels: [结构化事件], [deterministic], [mock].
- Cards or sections for each demo area.
- Tables for players, votes, metrics, score card, and leaderboard.
- Strong warning style for Phase 1 limitations and low sample size.
- Readable without external fonts, images, scripts, or stylesheets.
```

- [ ] **Step 4: Add embedded vanilla JavaScript placeholder for leaderboard sorting**

The initial script must define a `leaderboardRows` array and a `renderLeaderboard(sortKey)` function. The sort keys must be:

```text
avg_decision_quality_score
win_rate
avg_outcome_score
avg_total_score
avg_rule_integrity_score
info_leak_rate
```

For `info_leak_rate`, sort ascending. For the other fields, sort descending.

- [ ] **Step 5: Validate the skeleton is self-contained**

```bash
python - <<'PY'
from pathlib import Path

html = Path('docs/demo/phase1-gold-demo.html').read_text(encoding='utf-8')

required = [
    '<!doctype html>',
    '<style>',
    '<script>',
    'Phase 1',
    'Gold Game',
    'decision_quality_score 在 Phase 1 固定为 0',
    'renderLeaderboard',
]
missing = [item for item in required if item.lower() not in html.lower()]
assert not missing, missing

for forbidden in ['http://', 'https://', 'cdn.', 'unpkg.com', 'esm.sh', 'React', 'Vite']:
    assert forbidden.lower() not in html.lower(), forbidden

print('S6 static demo skeleton is self-contained')
PY
```

Expected result:

```text
S6 static demo skeleton is self-contained
```

- [ ] **Step 6: Commit the skeleton**

```bash
git add docs/demo/phase1-gold-demo.html
git commit -m "docs: add S6 static demo skeleton"
```

Expected result:

```text
[task/s6-leaderboard-ui-demo-validation <sha>] docs: add S6 static demo skeleton
```

---

### Task 3: Populate the Gold Game summary, timeline, and state sections

**Files:**

- Modify: `docs/demo/phase1-gold-demo.html`
- Test file: no committed test file; run the validation command below.

- [ ] **Step 1: Add Gold Game summary data**

Include these exact values:

```text
Game ID: g001
Players: 6
Role setup: 2 werewolves + 1 seer + 1 witch + 2 villagers
Winner: villager
End round: 2
Survivors: p4, p6
End condition: all_werewolves_eliminated
Data source: [结构化事件]
```

- [ ] **Step 2: Add player table**

Columns:

```text
Player
Role
Team
Final status
Source label
```

Rows:

```text
p1 | werewolf | werewolf | eliminated, revealed | [结构化事件]
p2 | werewolf | werewolf | died, revealed | [结构化事件]
p3 | seer | villager | eliminated, revealed | [结构化事件]
p4 | witch | villager | survivor | [结构化事件]
p5 | villager | villager | died, revealed | [结构化事件]
p6 | villager | villager | survivor | [结构化事件]
```

- [ ] **Step 3: Add timeline view**

Render a concise timeline from the 38 existing events. Each timeline item must show:

```text
sequence
round
phase
type
actor
target
summary
visibility
label
```

The UI may group items by round and phase. It must include events from setup through `game_over`.

- [ ] **Step 4: Add vote table**

Include these visible facts:

```text
Round 1 vote summary: p1, p2, p5, p6 voted p3; p3 and p4 voted p1; p3 eliminated 4-2.
Round 2 vote summary: p1 voted p4; p4 and p6 voted p1; p1 eliminated 2-1.
```

- [ ] **Step 5: Validate Gold Game sections**

```bash
python - <<'PY'
from pathlib import Path

html = Path('docs/demo/phase1-gold-demo.html').read_text(encoding='utf-8')

required = [
    'Game ID: g001',
    'Role setup: 2 werewolves + 1 seer + 1 witch + 2 villagers',
    'Winner: villager',
    'End condition: all_werewolves_eliminated',
    '[结构化事件]',
    'p1 | werewolf',
    'p4 | witch',
    'p6 | villager',
    'p3 eliminated 4-2',
    'p1 eliminated 2-1',
    'game_over',
]
missing = [item for item in required if item not in html]
assert not missing, missing

print('Gold Game summary, timeline, and vote sections are present')
PY
```

Expected result:

```text
Gold Game summary, timeline, and vote sections are present
```

- [ ] **Step 6: Commit**

```bash
git add docs/demo/phase1-gold-demo.html
git commit -m "docs: populate S6 gold game timeline"
```

Expected result:

```text
[task/s6-leaderboard-ui-demo-validation <sha>] docs: populate S6 gold game timeline
```

---

### Task 4: Add scoring, metrics, and attribution panels

**Files:**

- Modify: `docs/demo/phase1-gold-demo.html`
- Test file: no committed test file; run the validation command below.

- [ ] **Step 1: Add result metrics panel**

Include these exact values:

```text
winner: villager
game_length: 2
werewolf_survival_rate: 0.0
villager_survival_rate: 0.5
margin: 2
villager_win_efficiency: 1.0
source label: [deterministic]
```

- [ ] **Step 2: Add process metrics panel**

Include these visible subsections:

```text
vote_accuracy_by_player
survival_rounds
seer_metrics
witch_metrics
team_metrics
```

At minimum, include:

```text
p1 vote_accuracy 1.0
p2 vote_accuracy 1.0
p3 vote_accuracy 1.0
p4 vote_accuracy 1.0
p5 vote_accuracy 0.0
p6 vote_accuracy 0.5
seer check_accuracy 1.0
seer info_conveyed 1.0
witch save_accuracy 1.0
witch poison_accuracy 1.0
village_vote_cohesion 0.75
werewolf_vote_coordination 1.0
```

- [ ] **Step 3: Add score card**

Include one row per player plus one wolf-team row.

Minimum columns:

```text
Subject
Role / Scope
Outcome score
Decision quality score
Rule integrity score
Notes
Data label
```

Rows must include:

```text
p1 outcome 2, decision_quality 0, rule_integrity 0
p2 outcome 2, decision_quality 0, rule_integrity 0
p3 outcome 4, decision_quality 0, rule_integrity 0
p4 outcome 4, decision_quality 0, rule_integrity 0
p5 outcome -2, decision_quality 0, rule_integrity 0
p6 outcome 0, decision_quality 0, rule_integrity 0
wolf_team outcome 2, decision_quality 0, rule_integrity 0
```

- [ ] **Step 4: Add attribution panel**

Include these exact facts:

```text
Top attribution: 第 2 轮 2-1 处决 p1 是本局村民获胜的直接关键转折点。
turn_point_id: s3_g001_tp001
rule_id: attribution:F.1.critical_vote
round: 2
subject: p1
impact_score: 1.0
impact_sign: positive_for_villager
evidence_event_ids: g001_e033, g001_e034, g001_e035, g001_e036, g001_e037
source label: [deterministic]
```

- [ ] **Step 5: Add S3 validation observation**

Show this caveat in a visible note:

```text
Round 1 seer p3 elimination is human-salient, but the current deterministic F.1 rule does not trigger because the vote margin is 4-2 rather than 1. This is recorded as a validation observation, not silently changed in the rubric.
```

- [ ] **Step 6: Validate deterministic panels**

```bash
python - <<'PY'
from pathlib import Path

html = Path('docs/demo/phase1-gold-demo.html').read_text(encoding='utf-8')

required = [
    '[deterministic]',
    'winner: villager',
    'game_length: 2',
    'vote_accuracy_by_player',
    'village_vote_cohesion 0.75',
    'werewolf_vote_coordination 1.0',
    'p3 outcome 4',
    'p5 outcome -2',
    'wolf_team outcome 2',
    'decision_quality 0',
    'rule_integrity 0',
    's3_g001_tp001',
    'attribution:F.1.critical_vote',
    'g001_e033',
    'g001_e037',
    'Round 1 seer p3 elimination is human-salient',
]
missing = [item for item in required if item not in html]
assert not missing, missing

print('Scoring, metrics, and attribution panels are present')
PY
```

Expected result:

```text
Scoring, metrics, and attribution panels are present
```

- [ ] **Step 7: Commit**

```bash
git add docs/demo/phase1-gold-demo.html
git commit -m "docs: add S6 scoring and attribution panels"
```

Expected result:

```text
[task/s6-leaderboard-ui-demo-validation <sha>] docs: add S6 scoring and attribution panels
```

---

### Task 5: Add Leaderboard UI demo with sorting and sample warnings

**Files:**

- Modify: `docs/demo/phase1-gold-demo.html`
- Test file: no committed test file; run the validation command below.

- [ ] **Step 1: Add one Gold Game deterministic leaderboard row**

The row must include:

```text
agent_id: gold-g001-baseline
model: manually-authored-gold-game
agent_version: phase1-gold
source_label: [deterministic]
games_played: 1
win_rate: 1.0
avg_outcome_score: 10.0
avg_decision_quality_score: 0.0
avg_rule_integrity_score: 0.0
avg_total_score: 10.0
info_leak_rate: 0.0
contradiction_rate: 0.0
confidence_level: low
sample_size_warning: 数据不足，排名无统计意义
```

`avg_outcome_score: 10.0` is the sum of player outcome scores from S2: `2 + 2 + 4 + 4 - 2 + 0 = 10`.

- [ ] **Step 2: Add six mock leaderboard rows**

Use exactly these mock row IDs:

```text
mock-werewolf-alpha
mock-seer-beta
mock-witch-gamma
mock-villager-delta
mock-balanced-epsilon
mock-risky-zeta
```

Each mock row must include:

```text
agent_id
model
agent_version
games_played
role_distribution
win_rate
avg_total_score
avg_outcome_score
avg_decision_quality_score
avg_rule_integrity_score
info_leak_rate
contradiction_rate
confidence_level
sample_size_warning
source_label: [mock]
```

- [ ] **Step 3: Add role sections**

Minimum acceptable implementation is visible role sections rather than interactive tabs:

```text
Overview Leaderboard
Werewolf role section with leadership_success, follow_quality, persuasion_success, deadlock_rate
Seer role section
Witch role section
Villager role section
```

The page must state:

```text
Phase 1 不跨角色混合排名；真实角色榜需要足够样本后才有统计意义。
```

- [ ] **Step 4: Implement sorting controls**

Add a select or button group with these options:

```text
avg_decision_quality_score
win_rate
avg_outcome_score
avg_total_score
avg_rule_integrity_score
info_leak_rate
```

Behavior:

```text
Default sort: avg_decision_quality_score descending
info_leak_rate: ascending
all other fields: descending
```

- [ ] **Step 5: Add sample-size warnings**

Apply visible warnings:

```text
games_played < 5: 数据不足，排名无统计意义
games_played < 10: 低置信度
games_played >= 20: 统计可信
```

- [ ] **Step 6: Validate leaderboard requirements**

```bash
python - <<'PY'
from pathlib import Path

html = Path('docs/demo/phase1-gold-demo.html').read_text(encoding='utf-8')

required = [
    'Leaderboard',
    'gold-g001-baseline',
    '[mock]',
    '[deterministic]',
    'mock-werewolf-alpha',
    'mock-seer-beta',
    'mock-witch-gamma',
    'mock-villager-delta',
    'mock-balanced-epsilon',
    'mock-risky-zeta',
    'avg_decision_quality_score',
    'win_rate',
    'avg_outcome_score',
    'avg_total_score',
    'avg_rule_integrity_score',
    'info_leak_rate',
    'games_played',
    '数据不足，排名无统计意义',
    '低置信度',
    '统计可信',
    'Phase 1 不跨角色混合排名',
    'leadership_success',
    'follow_quality',
    'persuasion_success',
    'deadlock_rate',
]
missing = [item for item in required if item not in html]
assert not missing, missing

for forbidden in ['fetch(', 'import ', 'React', 'Vite', 'package.json', 'http://', 'https://']:
    assert forbidden.lower() not in html.lower(), forbidden

print('Leaderboard UI demo requirements are present')
PY
```

Expected result:

```text
Leaderboard UI demo requirements are present
```

- [ ] **Step 7: Commit**

```bash
git add docs/demo/phase1-gold-demo.html
git commit -m "docs: add S6 leaderboard demo"
```

Expected result:

```text
[task/s6-leaderboard-ui-demo-validation <sha>] docs: add S6 leaderboard demo
```

---

### Task 6: Final validation and Implementation PR preparation

**Files:**

- Modify: none unless validation reveals a missing S6 requirement
- Test file: no committed test file; run the validation commands below.

- [ ] **Step 1: Run JSON validation for all consumed inputs**

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
printf 'Input JSON is valid\n'
```

Expected result:

```text
Input JSON is valid
```

- [ ] **Step 2: Run final HTML content validation**

```bash
python - <<'PY'
from pathlib import Path

html = Path('docs/demo/phase1-gold-demo.html').read_text(encoding='utf-8')

required_phrases = [
    'Werewolf-agent',
    'Phase 1',
    'Gold Demo',
    'g001',
    'villager',
    'Timeline',
    'Vote',
    'Score',
    'Attribution',
    'Leaderboard',
    '[结构化事件]',
    '[deterministic]',
    '[mock]',
    'decision_quality_score 在 Phase 1 固定为 0',
    'Phase 1 只做静态 HTML UI demo',
    'gold-g001-baseline',
    's3_g001_tp001',
    '数据不足，排名无统计意义',
]
missing = [phrase for phrase in required_phrases if phrase not in html]
assert not missing, missing

for forbidden in [
    'cdn.',
    'unpkg.com',
    'esm.sh',
    'React',
    'Vite',
    'tailwind.config',
    'package.json',
    'fetch(',
    'http://',
    'https://',
]:
    assert forbidden.lower() not in html.lower(), forbidden

print('Final S6 HTML validation passed')
PY
```

Expected result:

```text
Final S6 HTML validation passed
```

- [ ] **Step 3: Confirm only the intended demo file changed relative to main**

```bash
git diff --name-only main...HEAD
```

Expected result for the implementation PR:

```text
docs/demo/phase1-gold-demo.html
```

- [ ] **Step 4: Run whitespace validation**

```bash
git diff --check main...HEAD
```

Expected result:

```text
```

No output means there are no whitespace errors.

- [ ] **Step 5: Prepare Implementation PR description**

Use this PR description for the follow-up implementation PR:

```markdown
## Summary

Adds the S6 Phase 1 Leaderboard UI demo validation page.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--s6-leaderboard-ui-demo-validation-plan.md`

## Scope

- Creates `docs/demo/phase1-gold-demo.html`.
- Builds a self-contained static HTML demo for the Phase 1 Gold Game.
- Shows timeline, player state, vote table, deterministic metrics, score card, attribution panel, and Leaderboard UI demo.
- Uses one deterministic Gold Game row plus multiple `[mock]` leaderboard rows.
- Implements vanilla JavaScript sorting for supported Leaderboard dimensions.
- Shows sample-size warnings.

## Out of Scope

- No business code.
- No backend.
- No parser.
- No scorer.
- No attribution engine.
- No React/Vite/frontend app.
- No dependencies.
- No real AI Agent gameplay.
- No real Leaderboard.
- No real `decision_quality_score`.
- No AI semantic annotations.
- No modification to existing `docs/gold-game/*` artifacts.
- No changes to `docs/EVALUATION_RUBRIC.md`.

## Validation

```bash
python -m json.tool docs/gold-game/g001-game-log.json > /dev/null
python -m json.tool docs/gold-game/s2-score-log.json > /dev/null
python -m json.tool docs/gold-game/s2-metrics-summary.json > /dev/null
python -m json.tool docs/gold-game/s3-rule-attribution.json > /dev/null
python - <<'PY'
from pathlib import Path

html = Path('docs/demo/phase1-gold-demo.html').read_text(encoding='utf-8')

required_phrases = [
    'Werewolf-agent',
    'Phase 1',
    'Gold Demo',
    'g001',
    'villager',
    'Timeline',
    'Vote',
    'Score',
    'Attribution',
    'Leaderboard',
    '[结构化事件]',
    '[deterministic]',
    '[mock]',
    'decision_quality_score 在 Phase 1 固定为 0',
    'Phase 1 只做静态 HTML UI demo',
    'gold-g001-baseline',
    's3_g001_tp001',
    '数据不足，排名无统计意义',
]
missing = [phrase for phrase in required_phrases if phrase not in html]
assert not missing, missing

for forbidden in [
    'cdn.',
    'unpkg.com',
    'esm.sh',
    'React',
    'Vite',
    'tailwind.config',
    'package.json',
    'fetch(',
    'http://',
    'https://',
]:
    assert forbidden.lower() not in html.lower(), forbidden

print('Final S6 HTML validation passed')
PY
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected changed files:

```text
docs/demo/phase1-gold-demo.html
```

## Risk

The main risk is UX density: the page must show timeline, metrics, attribution, and Leaderboard without overwhelming a non-technical user. If the first version is too dense, reduce simultaneous detail by making long sections collapsible while preserving the required facts and labels.
```

- [ ] **Step 6: Commit final fixes only if validation required edits**

```bash
git status --short
git add docs/demo/phase1-gold-demo.html
git commit -m "docs: validate S6 leaderboard UI demo"
```

Expected result if a fix was needed:

```text
[task/s6-leaderboard-ui-demo-validation <sha>] docs: validate S6 leaderboard UI demo
```

If no files changed after validation, do not create an empty commit.

## Final Review Checklist

- [ ] S6 produces a user-visible static HTML demo.
- [ ] The page can be opened directly without build tools.
- [ ] The page contains timeline, player state, vote table, metrics, score card, attribution, and Leaderboard.
- [ ] Sorting works for all supported Leaderboard dimensions.
- [ ] `[mock]`, `[deterministic]`, and `[结构化事件]` labels are visible.
- [ ] Sample-size warnings are visible.
- [ ] The page does not claim a real Leaderboard exists.
- [ ] The page does not claim `decision_quality_score` is real in Phase 1.
- [ ] No runtime code or dependency manifests were added.
- [ ] Existing Gold Game, scoring, attribution, and rubric files were not modified.

## Plan-only PR Description

Use this description for the plan-only PR that adds this file:

```markdown
## Summary

Adds an Implementation Plan for the next Werewolf Phase 1 step: S6 Leaderboard UI demo validation.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--s6-leaderboard-ui-demo-validation-plan.md`

## Scope

Plan only.

The plan instructs the implementation agent to create:

- `docs/demo/phase1-gold-demo.html`

## Out of Scope

- No business code.
- No parser.
- No scorer.
- No attribution engine.
- No backend.
- No React/Vite/frontend app.
- No dependencies.
- No real AI Agent gameplay.
- No real Leaderboard.
- No real `decision_quality_score`.
- No AI semantic annotations.

## Why this is the next step

S0, S1, S2, and S3 are already present on `main` through merged PRs. S3 explicitly recommends S6 as the next user-visible validation step. S6 can use the existing Gold Game, deterministic score log, metrics summary, and rule attribution output without changing business code or introducing runtime architecture.

## Validation for this PR

This PR should only add the plan file:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
docs/harness/plans/2026-05-29--s6-leaderboard-ui-demo-validation-plan.md
```

## Follow-up Implementation PR description prepared in the plan

The plan includes a ready-to-use Implementation PR description for the actual S6 static HTML demo PR.
```
