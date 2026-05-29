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
