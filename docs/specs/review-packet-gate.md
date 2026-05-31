# Review Packet Gate v1

## Purpose

Review Packet Gate v1 changes Codex review from repository-wide context discovery to evidence-packet review.

## Roles

| Actor | Responsibility |
|---|---|
| Claude Code / local implementer | Implement scoped changes, run validation, generate review packet |
| Review Packet script | Produce objective Git/test evidence |
| Codex A档 | Review only `review-packet.md` and return PASS / BLOCK / NEED_DEEP_REVIEW |
| Codex B档 | Read only requested file ranges after NEED_DEEP_REVIEW |

## Required Gate

No `review-packet.md`, no Codex implementation review.

## A档 Rules

- Codex A档 reviews only `.logs/review/latest/review-packet.md`.
- A档 has exactly three verdicts: PASS, BLOCK, NEED_DEEP_REVIEW.
- A档 outputs one conclusion only.
- If evidence is insufficient, A档 lists Minimal Next Reads with explicit file paths and line ranges.
- A档 must not request broad repository material.

## Review Packet v1 Required Sections

The generated file at `.logs/review/latest/review-packet.md` must include these sections in this order:

1. Metadata
2. Changed Files
3. Diff Stat
4. Diff Check
5. Allowed Files Check
6. Forbidden Patterns Check
7. Dependency / Import Diff
8. Test Summary
9. Key Hunks
10. Evidence Map
11. Acceptance Checklist
12. Implementer Risk Notes
13. Review Trigger Result

## Length Limits

- review-packet.md <= 300 lines
- Key Hunks <= 120 lines
- Test output: summary only; do not include full logs
- Each changed file gets at most one key hunk unless a risk trigger is hit

If any limit is exceeded:
- `PACKET_TOO_LARGE = YES`
- `Suggested action: NEED_DEEP_REVIEW with explicit line ranges`

If within limits:
- `PACKET_TOO_LARGE = NO`

## Evidence Map

The packet must include an Evidence Map table with one row per acceptance item:

| Acceptance | Evidence | Status |
|---|---|---|
| A-N: description | test reference or artifact path | PASS / FAIL / MANUAL_REVIEW_REQUIRED |

When the script cannot infer an acceptance item automatically, status must be `MANUAL_REVIEW_REQUIRED`.

## Risk Triggers

The generator must mark risk when evidence shows any of:

- Changed file count > 8
- Diff stat indicates more than 500 changed lines
- PACKET_TOO_LARGE = YES
- Forbidden pattern scan hits provider / network / env / dependency / live AI
- Changed files include `src/werewolf_eval/scoring.py`
- Changed files include `src/werewolf_eval/*parser*.py`
- Changed files include `src/werewolf_eval/*log*.py`
- Changed files include `docs/gold-game/**`
- Changed files include `docs/demo/**`
- Changed files include dependency manifests
- Key hunks were truncated
- Allowlist check is not PASS

## B档 Escalation

B档 starts only after NEED_DEEP_REVIEW and reads only the requested file ranges.

## Out-of-Scope Extension Points

- Plan allowlist parsing from Implementation Plan front matter
- Automatic acceptance extraction from plan checkboxes
- Exact source line pointer generation for Evidence Map rows
- Deep Review Packet generator for Codex B档
- CI enforcement that rejects implementation PRs without review-packet.md evidence
