# S1 Schema Validation — Game Log g001

## Input

- S0 seed: `docs/gold-game/s0-gold-game-seed.md`
- Output JSON: `docs/gold-game/g001-game-log.json`
- Rubric source: `docs/EVALUATION_RUBRIC.md`

## Validation Summary

| Item | Status | Evidence |
|---|---|---|
| 6 players represented | pass | `players.length = 6` |
| 38 events represented | pass | `events.length = 38` |
| sequence continuous | pass | event sequence is `1..38` |
| required event types covered | pass | `role_assignment`, `werewolf_kill`, `seer_check`, `witch_save`, `witch_poison`, `player_speech`, `player_vote`, `player_eliminated`, `player_died`, `role_revealed`, `game_over` |
| visibility explicit | pass | every event has `visibility` |
| actor and target explicit | pass | every event has `actor` and `target` |
| result explicit | pass | `winner`, `end_round`, `survivors`, and `end_condition` exist |
| S0 poison evidence preserved | pass | `g001_e025.data.visible_info_refs` includes `g001_e011`, `g001_e012`, `g001_e017`, `g001_e023` |

## Schema Findings

| Finding | Severity | Recommendation |
|---|---|---|
| Game Log example shows numeric `event_id`, but downstream refs need stable IDs such as `g001_e025`. | medium | Use string event IDs in Phase 1 artifacts; propose a rubric clarification in a later targeted Spec PR if reviewers accept this pattern. |
| Game Log example lists `night`, `day`, and `game_end` as phase examples, but role assignment is clearer as `setup`. | medium | Keep `phase: setup` in this S1 artifact and record it as a schema clarification candidate. Do not silently edit `docs/EVALUATION_RUBRIC.md` in this PR. |
| `result.end_condition` uses `all_werewolves_eliminated`, but `docs/EVALUATION_RUBRIC.md` B.1 only shows `werewolf_majority` in the example. | low | Treat `all_werewolves_eliminated` as a reasonable village-win extension for this game and record it as a schema finding instead of silently assuming the enum. |
| Game Log example has `data: {}` but does not define where event text belongs. | low | Store event text in `data.summary` for this artifact. |
| Game Log JSON extends event-type-specific data fields: `assigned_role`, `assigned_team`, `effect`, `death_cause`, `source_event_id`, `vote_count`, `revealed_role`, and `revealed_team`. | low | Keep these fields because they make S1 unambiguous, but define them explicitly in a later schema clarification if the pattern is accepted. |
| `visible_info_refs` is defined in Decision Log and Consensus Log examples, not in the base Game Log example. | low | Store S1 traceability refs in `data.visible_info_refs` only where the S0 seed already provided a concrete handoff note. |

## Naming Consistency Notes

- `result.winner` uses `villager`.
- `g001_e038.target` uses `villager_team`.
- These values are semantically consistent in this artifact, but the naming style is not fully uniform.
- A future scorer that matches team names by string should use one explicit enum strategy for winner values and team-target values before computing scores.

## Visibility and Flag Notes

- This JSON does not add `info_leak_flag`.
- This JSON does not add `contradiction_flag`.
- No event in this JSON was found to reference invisible information.
- `g001_e025.data.visible_info_refs` only references public events: `g001_e011`, `g001_e012`, `g001_e017`, and `g001_e023`.

## S1 Decision

S1 passes if reviewers accept `docs/gold-game/g001-game-log.json` as a complete and unambiguous representation of the S0 game.

Schema changes are not applied in this PR. If reviewers decide one of the findings is stable, create a later targeted Spec PR or rubric update.

## Not Represented

- This artifact is not a parser.
- This artifact is not a scorer.
- This artifact is not an attribution engine.
- This artifact is not a UI.
- This artifact is not real AI Agent gameplay.
- This artifact does not make `decision_quality_score` available in Phase 1.
