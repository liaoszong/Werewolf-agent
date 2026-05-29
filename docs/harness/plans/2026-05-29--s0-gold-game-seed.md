# S0 Gold Game Seed Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Create one complete, manually authored 6-player Werewolf Gold Game event seed for Phase 1 spike validation.

**Architecture:** This is a document-only Phase 1 spike task. It creates a stable, reviewable event-chain artifact that S1 can convert into a Game Log JSON and S2/S3/S6 can use as fixed input. It does not create business code, runtime code, app/server/web directories, dependencies, or automated game engine logic.

**Tech Stack:** Markdown, structured tables, repository-local manual validation commands. No runtime dependencies.

---

## Scope Decision

This plan implements the recommended next step from the repository state review: start S0 by using a manually authored virtual 6-player game instead of researching public match footage.

Reasoning:

- Phase 1 is still document/spike stage.
- `src/`, `apps/`, `server/`, and `web` directories must not be created in this task.
- S1, S2, S3, and S6 all depend on a stable Gold Game input.
- A virtual game avoids public-match source completeness and copyright risk.

## Files

- Create: `docs/gold-game/s0-gold-game-seed.md`
- Modify: none
- Test file: no separate automated test file for this document-only spike. Manual validation is embedded in `docs/gold-game/s0-gold-game-seed.md` under `S0 Acceptance Check`, and repository commands validate the changed file.

---

## Task 1: Create the S0 Gold Game document shell

**Files:**

- Create: `docs/gold-game/s0-gold-game-seed.md`
- Modify: none
- Test file: `docs/gold-game/s0-gold-game-seed.md` self-check section added later in Task 6

- [ ] **Step 1: Create the directory and file**

```bash
mkdir -p docs/gold-game
cat > docs/gold-game/s0-gold-game-seed.md <<'EOF'
# S0 Gold Game Seed — Werewolf-agent Phase 1

## Status

- Task: S0
- Source type: manually authored virtual game
- Game facts label: `[结构化事件]`
- Author notes label: `[人工 gold sample]`
- Mock data: none
- AI-generated data: none

## Scope

This file defines one logically self-contained 6-player Werewolf game for Phase 1 spike validation.

Role setup is fixed for Phase 1:

| Player | Role | Team |
|---|---|---|
| p1 | werewolf | werewolf |
| p2 | werewolf | werewolf |
| p3 | seer | villager |
| p4 | witch | villager |
| p5 | villager | villager |
| p6 | villager | villager |
EOF
```

- [ ] **Step 2: Validate the file exists and contains the required header**

```bash
test -f docs/gold-game/s0-gold-game-seed.md
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
assert text.startswith('# S0 Gold Game Seed — Werewolf-agent Phase 1')
assert 'Source type: manually authored virtual game' in text
assert '| p1 | werewolf | werewolf |' in text
assert '| p6 | villager | villager |' in text
print('Task 1 validation passed')
PY
```

Expected result:

```text
Task 1 validation passed
```

- [ ] **Step 3: Commit checkpoint for the shell**

```bash
git add docs/gold-game/s0-gold-game-seed.md
git commit -m "docs: add S0 gold game seed shell"
```

Expected result:

```text
[branch-name commit-sha] docs: add S0 gold game seed shell
 1 file changed, ... insertions(+)
 create mode 100644 docs/gold-game/s0-gold-game-seed.md
```

---

## Task 2: Add the fixed game premise and rule assumptions

**Files:**

- Create: none
- Modify: `docs/gold-game/s0-gold-game-seed.md`
- Test file: no separate automated test file; validation command checks the rule-assumption text in the document

- [ ] **Step 1: Append the premise and assumptions**

```bash
cat >> docs/gold-game/s0-gold-game-seed.md <<'EOF'

## Game Premise

This is a manually authored virtual game. It is not copied from a public video, public transcript, streamer match, or forum record.

The game is intentionally designed to exercise Phase 1 scoring and attribution:

- The seer obtains a correct wolf check but is eliminated on Day 1.
- The witch uses the save potion on Night 1 and poison potion on Night 2.
- The village recovers through deterministic public evidence and eliminates both werewolves.
- The game produces clear turn points for later S3 attribution validation.

## Rule Assumptions for This Gold Game

| Rule | Assumption |
|---|---|
| Player count | 6 players |
| Role setup | 2 werewolves, 1 seer, 1 witch, 2 villagers |
| Hunter | Not included |
| Witch save potion | One use per game |
| Witch poison potion | One use per game |
| Witch same-night save and poison | Not used in this game |
| Night death reveal | Public death events are recorded after night resolution |
| Elimination reveal | Eliminated player's role is publicly revealed |
| Win condition | Village wins when all werewolves are eliminated |
| Speech content | Stored as summarized public events, not copied dialogue |
EOF
```

- [ ] **Step 2: Validate assumptions are explicit**

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
required = [
    'This is a manually authored virtual game.',
    '| Hunter | Not included |',
    '| Witch save potion | One use per game |',
    '| Witch poison potion | One use per game |',
    '| Win condition | Village wins when all werewolves are eliminated |',
]
for item in required:
    assert item in text, item
print('Task 2 validation passed')
PY
```

Expected result:

```text
Task 2 validation passed
```

- [ ] **Step 3: Commit checkpoint for premise and assumptions**

```bash
git add docs/gold-game/s0-gold-game-seed.md
git commit -m "docs: define S0 gold game premise"
```

Expected result:

```text
[branch-name commit-sha] docs: define S0 gold game premise
 1 file changed, ... insertions(+)
```

---

## Task 3: Add the complete event chain

**Files:**

- Create: none
- Modify: `docs/gold-game/s0-gold-game-seed.md`
- Test file: no separate automated test file; validation command checks required event types and stable event count in the document

- [ ] **Step 1: Append the full event chain**

```bash
cat >> docs/gold-game/s0-gold-game-seed.md <<'EOF'

## Event Chain

| event_id | seq | round | phase | type | actor | target | visibility | summary | label |
|---|---:|---:|---|---|---|---|---|---|---|
| g001_e001 | 1 | 0 | setup | role_assignment | system | p1 | specific_player_ids | p1 receives the werewolf role. | [结构化事件] |
| g001_e002 | 2 | 0 | setup | role_assignment | system | p2 | specific_player_ids | p2 receives the werewolf role. | [结构化事件] |
| g001_e003 | 3 | 0 | setup | role_assignment | system | p3 | specific_player_ids | p3 receives the seer role. | [结构化事件] |
| g001_e004 | 4 | 0 | setup | role_assignment | system | p4 | specific_player_ids | p4 receives the witch role. | [结构化事件] |
| g001_e005 | 5 | 0 | setup | role_assignment | system | p5 | specific_player_ids | p5 receives the villager role. | [结构化事件] |
| g001_e006 | 6 | 0 | setup | role_assignment | system | p6 | specific_player_ids | p6 receives the villager role. | [结构化事件] |
| g001_e007 | 7 | 1 | night | werewolf_kill | wolf_team | p5 | werewolf_team | The werewolf team chooses p5 as the kill target. | [结构化事件] |
| g001_e008 | 8 | 1 | night | seer_check | p3 | p1 | seer | p3 checks p1 and receives a werewolf result. | [结构化事件] |
| g001_e009 | 9 | 1 | night | witch_save | p4 | p5 | witch | p4 uses the save potion on p5. | [结构化事件] |
| g001_e010 | 10 | 1 | day | player_speech | p3 | p1 | public | p3 claims useful night information and pushes suspicion toward p1. | [结构化事件] |
| g001_e011 | 11 | 1 | day | player_speech | p1 | p3 | public | p1 challenges p3 and frames p3 as a wolf trying to force an early mis-elimination. | [结构化事件] |
| g001_e012 | 12 | 1 | day | player_speech | p2 | p3 | public | p2 supports p1 and argues that p3's pressure is too aggressive. | [结构化事件] |
| g001_e013 | 13 | 1 | day | player_speech | p4 | p1 | public | p4 notes that p1 and p2 are aligned too quickly but does not reveal witch identity. | [结构化事件] |
| g001_e014 | 14 | 1 | day | player_speech | p5 | p3 | public | p5 says p3's claim lacks enough public evidence and leans toward voting p3. | [结构化事件] |
| g001_e015 | 15 | 1 | day | player_speech | p6 | p1 | public | p6 is uncertain but sees a possible p1 and p2 pairing. | [结构化事件] |
| g001_e016 | 16 | 1 | day | player_vote | p1 | p3 | public | p1 votes for p3. | [结构化事件] |
| g001_e017 | 17 | 1 | day | player_vote | p2 | p3 | public | p2 votes for p3. | [结构化事件] |
| g001_e018 | 18 | 1 | day | player_vote | p3 | p1 | public | p3 votes for p1. | [结构化事件] |
| g001_e019 | 19 | 1 | day | player_vote | p4 | p1 | public | p4 votes for p1. | [结构化事件] |
| g001_e020 | 20 | 1 | day | player_vote | p5 | p3 | public | p5 votes for p3. | [结构化事件] |
| g001_e021 | 21 | 1 | day | player_vote | p6 | p3 | public | p6 votes for p3. | [结构化事件] |
| g001_e022 | 22 | 1 | day | player_eliminated | system | p3 | public | p3 is eliminated by a 4-2 vote. | [结构化事件] |
| g001_e023 | 23 | 1 | day | role_revealed | system | p3 | public | p3 is revealed as the seer. | [结构化事件] |
| g001_e024 | 24 | 2 | night | werewolf_kill | wolf_team | p5 | werewolf_team | The werewolf team again chooses p5 as the kill target. | [结构化事件] |
| g001_e025 | 25 | 2 | night | witch_poison | p4 | p2 | witch | p4 uses the poison potion on p2 after p3's reveal makes p2's Day 1 alignment suspicious. | [结构化事件] |
| g001_e026 | 26 | 2 | day | player_died | system | p5 | public | p5 dies from the werewolf night kill. | [结构化事件] |
| g001_e027 | 27 | 2 | day | player_died | system | p2 | public | p2 dies from the witch poison. | [结构化事件] |
| g001_e028 | 28 | 2 | day | role_revealed | system | p5 | public | p5 is revealed as a villager. | [结构化事件] |
| g001_e029 | 29 | 2 | day | role_revealed | system | p2 | public | p2 is revealed as a werewolf. | [结构化事件] |
| g001_e030 | 30 | 2 | day | player_speech | p4 | p1 | public | p4 argues that p1 and p2 formed a coordinated push against the real seer. | [结构化事件] |
| g001_e031 | 31 | 2 | day | player_speech | p1 | p4 | public | p1 argues that p4 is using p2's death to force an easy final vote. | [结构化事件] |
| g001_e032 | 32 | 2 | day | player_speech | p6 | p1 | public | p6 accepts that p2's revealed role makes p1's Day 1 behavior highly suspicious. | [结构化事件] |
| g001_e033 | 33 | 2 | day | player_vote | p1 | p4 | public | p1 votes for p4. | [结构化事件] |
| g001_e034 | 34 | 2 | day | player_vote | p4 | p1 | public | p4 votes for p1. | [结构化事件] |
| g001_e035 | 35 | 2 | day | player_vote | p6 | p1 | public | p6 votes for p1. | [结构化事件] |
| g001_e036 | 36 | 2 | day | player_eliminated | system | p1 | public | p1 is eliminated by a 2-1 vote. | [结构化事件] |
| g001_e037 | 37 | 2 | day | role_revealed | system | p1 | public | p1 is revealed as a werewolf. | [结构化事件] |
| g001_e038 | 38 | 2 | game_end | game_over | system | villager_team | public | The village team wins because all werewolves have been eliminated. | [结构化事件] |
EOF
```

- [ ] **Step 2: Validate required event coverage**

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
required_types = [
    'role_assignment',
    'werewolf_kill',
    'seer_check',
    'witch_save',
    'witch_poison',
    'player_speech',
    'player_vote',
    'player_eliminated',
    'player_died',
    'role_revealed',
    'game_over',
]
for event_type in required_types:
    assert event_type in text, event_type
assert text.count('| g001_e') == 38
assert 'The village team wins because all werewolves have been eliminated.' in text
print('Task 3 validation passed')
PY
```

Expected result:

```text
Task 3 validation passed
```

- [ ] **Step 3: Commit checkpoint for event chain**

```bash
git add docs/gold-game/s0-gold-game-seed.md
git commit -m "docs: add S0 gold game event chain"
```

Expected result:

```text
[branch-name commit-sha] docs: add S0 gold game event chain
 1 file changed, ... insertions(+)
```

---

## Task 4: Add completeness assessment

**Files:**

- Create: none
- Modify: `docs/gold-game/s0-gold-game-seed.md`
- Test file: no separate automated test file; validation command checks every required S0 completeness item is marked as covered

- [ ] **Step 1: Append completeness assessment**

```bash
cat >> docs/gold-game/s0-gold-game-seed.md <<'EOF'

## Completeness Assessment

| Required item | Covered | Evidence event_id | Notes |
|---|---|---|---|
| role assignment | yes | g001_e001-g001_e006 | All 6 players have explicit roles and teams. |
| night actions | yes | g001_e007-g001_e009, g001_e024-g001_e025 | Night 1 and Night 2 actions are explicit. |
| seer check | yes | g001_e008 | The seer checks p1 and receives a werewolf result. |
| witch action | yes | g001_e009, g001_e025 | Save and poison usage are both explicit. |
| day speeches | yes | g001_e010-g001_e015, g001_e030-g001_e032 | Public speech summaries exist for each day. |
| votes | yes | g001_e016-g001_e021, g001_e033-g001_e035 | Every living voter has a target. |
| deaths | yes | g001_e022, g001_e026, g001_e027, g001_e036 | Eliminations and night deaths are explicit. |
| role reveals | yes | g001_e023, g001_e028, g001_e029, g001_e037 | Key revealed roles are explicit. |
| game over | yes | g001_e038 | Winner and end condition are explicit. |
| copyright risk | yes | Copyright / Source Risk Assessment | No external copyrighted match material is used. |
EOF
```

- [ ] **Step 2: Validate completeness table**

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
items = [
    'role assignment',
    'night actions',
    'seer check',
    'witch action',
    'day speeches',
    'votes',
    'deaths',
    'role reveals',
    'game over',
    'copyright risk',
]
for item in items:
    assert f'| {item} | yes |' in text, item
print('Task 4 validation passed')
PY
```

Expected result:

```text
Task 4 validation passed
```

- [ ] **Step 3: Commit checkpoint for completeness assessment**

```bash
git add docs/gold-game/s0-gold-game-seed.md
git commit -m "docs: add S0 completeness assessment"
```

Expected result:

```text
[branch-name commit-sha] docs: add S0 completeness assessment
 1 file changed, ... insertions(+)
```

---

## Task 5: Add source and copyright risk assessment

**Files:**

- Create: none
- Modify: `docs/gold-game/s0-gold-game-seed.md`
- Test file: no separate automated test file; validation command checks the risk assessment section in the document

- [ ] **Step 1: Append source risk section**

```bash
cat >> docs/gold-game/s0-gold-game-seed.md <<'EOF'

## Copyright / Source Risk Assessment

| Item | Assessment |
|---|---|
| Source | Manually authored virtual game |
| External copyrighted video used | No |
| External copyrighted audio used | No |
| External copyrighted transcript used | No |
| Direct copied dialogue | No |
| Public figure or streamer content used | No |
| Risk level | Low |
| Decision | Safe for Phase 1 Gold Demo input |

## S0 Decision

S0 uses a manually authored virtual game as the Phase 1 Gold Game seed.

This satisfies the S0 fallback path because the event chain is complete, deterministic, and free from external-source risk. It also avoids spending Phase 1 effort on public match research before the scoring pipeline has a fixed input.
EOF
```

- [ ] **Step 2: Validate copyright risk section**

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
required = [
    '| Source | Manually authored virtual game |',
    '| External copyrighted video used | No |',
    '| Direct copied dialogue | No |',
    '| Risk level | Low |',
    '| Decision | Safe for Phase 1 Gold Demo input |',
    'S0 uses a manually authored virtual game as the Phase 1 Gold Game seed.',
]
for item in required:
    assert item in text, item
print('Task 5 validation passed')
PY
```

Expected result:

```text
Task 5 validation passed
```

- [ ] **Step 3: Commit checkpoint for source risk assessment**

```bash
git add docs/gold-game/s0-gold-game-seed.md
git commit -m "docs: record S0 source risk assessment"
```

Expected result:

```text
[branch-name commit-sha] docs: record S0 source risk assessment
 1 file changed, ... insertions(+)
```

---

## Task 6: Add acceptance check and checkpoint report guidance

**Files:**

- Create: none
- Modify: `docs/gold-game/s0-gold-game-seed.md`
- Test file: no separate automated test file; validation command checks all acceptance lines are present in the document

- [ ] **Step 1: Append acceptance check**

```bash
cat >> docs/gold-game/s0-gold-game-seed.md <<'EOF'

## S0 Acceptance Check

- [x] Event chain is continuous with no missing night/day transitions.
- [x] Every night action is explicit.
- [x] Every day has public speech summaries.
- [x] Every vote has voter and target.
- [x] Every death has timing and cause.
- [x] Every role reveal needed by the demo is explicit.
- [x] Winner and end condition are explicit.
- [x] Copyright risk is low because the game is manually authored.
- [x] This file does not claim real AI Agent gameplay.
- [x] This file does not claim `decision_quality_score` is available.

## Checkpoint Report Guidance

When reporting this checkpoint, use `docs/CHECKPOINT_TEMPLATE.md` and state:

- User-visible change: the repository now has one complete Phase 1 Gold Game seed that can be reviewed before Game Log JSON conversion.
- Fixed input: `docs/gold-game/s0-gold-game-seed.md`.
- Fixed output: one complete manually authored event chain with role setup, night actions, day speeches, votes, deaths, reveals, and game result.
- AI annotation record: no AI annotation; this checkpoint is manually authored and deterministic/gold-input preparation only.
- Data label clarity: game facts are marked `[结构化事件]`; no `[mock]` leaderboard data is introduced; no `[AI 生成]` data is introduced.
- This checkpoint does not represent a parser, scorer, attribution engine, UI, real Agent gameplay, or usable `decision_quality_score`.
- Next risk: S1 may reveal that the current Game Log schema needs small field clarifications for night resolution, role reveal timing, or witch potion state.
EOF
```

- [ ] **Step 2: Validate acceptance check**

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
required = [
    '- [x] Event chain is continuous with no missing night/day transitions.',
    '- [x] Every night action is explicit.',
    '- [x] Every day has public speech summaries.',
    '- [x] Every vote has voter and target.',
    '- [x] Winner and end condition are explicit.',
    'Fixed input: `docs/gold-game/s0-gold-game-seed.md`.',
    'This checkpoint does not represent a parser, scorer, attribution engine, UI, real Agent gameplay, or usable `decision_quality_score`.',
]
for item in required:
    assert item in text, item
print('Task 6 validation passed')
PY
```

Expected result:

```text
Task 6 validation passed
```

- [ ] **Step 3: Commit checkpoint for acceptance guidance**

```bash
git add docs/gold-game/s0-gold-game-seed.md
git commit -m "docs: add S0 acceptance guidance"
```

Expected result:

```text
[branch-name commit-sha] docs: add S0 acceptance guidance
 1 file changed, ... insertions(+)
```

---

## Task 7: Final repository validation

**Files:**

- Create: none
- Modify: none
- Test file: no separate automated test file; validation commands inspect repository state and the S0 artifact

- [ ] **Step 1: Run whitespace validation**

```bash
git diff --check HEAD~4..HEAD
```

Expected result:

```text
```

No output means whitespace validation passed.

- [ ] **Step 2: Verify only the intended document was added by the implementation branch**

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
docs/gold-game/s0-gold-game-seed.md
```

- [ ] **Step 3: Verify no business-code directories were created**

```bash
python - <<'PY'
from pathlib import Path
for forbidden in ['src', 'apps', 'server', 'web']:
    assert not Path(forbidden).exists(), forbidden
print('No business-code directories created')
PY
```

Expected result:

```text
No business-code directories created
```

- [ ] **Step 4: Verify the document does not introduce real AI or mock leaderboard claims**

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
assert '[AI 生成]' not in text
assert 'Leaderboard' not in text or 'no `[mock]` leaderboard data is introduced' in text
assert 'real AI Agent gameplay' in text
print('No real-AI or leaderboard mock claims introduced')
PY
```

Expected result:

```text
No real-AI or leaderboard mock claims introduced
```

- [ ] **Step 5: Final commit if validation caused doc corrections**

If Step 1-4 reveal wording problems and the document is corrected, commit the correction:

```bash
git add docs/gold-game/s0-gold-game-seed.md
git commit -m "docs: finalize S0 gold game seed"
```

Expected result when corrections were made:

```text
[branch-name commit-sha] docs: finalize S0 gold game seed
 1 file changed, ... insertions(+), ... deletions(-)
```

Expected result when no correction was needed:

```text
nothing to commit, working tree clean
```

---

## Implementation PR Description

Title:

```text
Add S0 Gold Game Seed
```

Body:

```md
## Summary

Adds the S0 Phase 1 Gold Game seed as a manually authored virtual 6-player Werewolf event chain.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-29--s0-gold-game-seed.md`

## Scope

- Creates `docs/gold-game/s0-gold-game-seed.md`.
- Uses a manually authored virtual game instead of public match footage or transcript material.
- Covers role setup, night actions, day speeches, votes, deaths, role reveals, winner, completeness assessment, source risk assessment, and S0 acceptance check.

## Out of Scope

- No business code.
- No parser.
- No scorer.
- No attribution engine.
- No UI.
- No AI Agent gameplay.
- No real `decision_quality_score`.

## Validation

Expected validation commands for the implementation branch:

```bash
git diff --check HEAD~4..HEAD
git diff --name-only main...HEAD
python - <<'PY'
from pathlib import Path
for forbidden in ['src', 'apps', 'server', 'web']:
    assert not Path(forbidden).exists(), forbidden
print('No business-code directories created')
PY
python - <<'PY'
from pathlib import Path
text = Path('docs/gold-game/s0-gold-game-seed.md').read_text(encoding='utf-8')
for event_type in ['role_assignment', 'werewolf_kill', 'seer_check', 'witch_save', 'witch_poison', 'player_speech', 'player_vote', 'player_eliminated', 'player_died', 'role_revealed', 'game_over']:
    assert event_type in text, event_type
assert text.count('| g001_e') == 38
print('S0 event coverage validation passed')
PY
```

Expected results:

- `git diff --check HEAD~4..HEAD` prints no output.
- `git diff --name-only main...HEAD` prints only `docs/gold-game/s0-gold-game-seed.md`.
- Python validations pass.

## Risk

The main follow-up risk is S1 schema conversion: converting this event-chain document into Game Log JSON may reveal small field clarification needs around night resolution, role reveal timing, or witch potion state.
```

---

## Self Review

- Spec coverage: The plan advances S0 only and does not start S1/S2/S3/S6.
- File boundary: The implementation creates only `docs/gold-game/s0-gold-game-seed.md`.
- Business-code boundary: The plan explicitly validates that `src`, `apps`, `server`, and `web` are not created.
- Data label boundary: The plan marks game facts as `[结构化事件]` and avoids real AI output claims.
- Execution handoff: A local coding agent can execute the tasks, commit each checkpoint, and open the Implementation PR with the provided description.
