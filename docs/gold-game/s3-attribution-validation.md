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
