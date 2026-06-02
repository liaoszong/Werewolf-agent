# G1h Decision Round Scoring Disambiguation Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add an explicit `round` field to Decision Log entries and use it in scoring matches so repeated same actor/action/phase/target decisions across rounds no longer trigger ambiguous scorer matches.

**Architecture:** Evolve the Decision Log runtime schema in a backward-incompatible but controlled way for generated/runtime decision logs: parse, validate, serialize, and generated engine decisions must include `round`. Scoring must match decisions to events using round in addition to action, phase, actor, and target. Tests must cover the known DeepSeek case where `wolf_team` kills the same target in two nights.

**Tech Stack:** Python stdlib only; existing `decision_log`, `game_engine`, `scoring`, validators, generated fixtures, and unittest.

---

## Why this follows G1e/G1f

A real DeepSeek smoke exposed a pre-existing scorer limitation: Decision entries do not carry `round`, and `_decision_matches_event` currently matches only action/phase/actor/target. If the same actor repeats the same action and target in the same phase across rounds, scoring can raise `ambiguous Decision Log match`.

This is not part of G1e or G1f because it changes Decision Log schema and scorer semantics. It deserves a separate implementation plan and focused review.

This plan intentionally does not add live provider behavior or HTML replay.

## Implementation PR Draft

Title:

```text
feat: add decision round matching for scoring
```

Body:

```markdown
## Summary

Implements G1h: Decision Log entries now include `round`, validators require it for generated/runtime logs, and scoring uses it to disambiguate repeated decisions across rounds.

Bound plan: `docs/harness/plans/2026-06-02--g1h-decision-round-scoring-disambiguation-plan.md`

## Scope

- Adds `round` to Decision dataclass, parser, validator, and generated engine decisions.
- Updates scorer matching to include decision round.
- Updates affected fixtures/tests.
- Adds regression tests for repeated same actor/action/phase/target across rounds.

## Validation

- targeted decision/scoring/game-engine tests pass
- full unittest discovery passes
- generated fixture validators pass
- review packet contains machine evidence
```

## Context Budget Gate

Do not read this full plan during implementation. Generate task contexts:

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-06-02--g1h-decision-round-scoring-disambiguation-plan.md
python scripts/context/build_task_context.py docs/generated-context/2026-06-02--g1h-decision-round-scoring-disambiguation-plan.index.json <TASK_ID>
```

Read only `docs/generated-context/current-task.ctx.md`. If insufficient, read only referenced plan lines.

## File Structure

Modify:

```text
src/werewolf_eval/decision_log.py
src/werewolf_eval/game_engine.py
src/werewolf_eval/scoring.py
tests/test_decision_log.py
tests/test_game_engine.py
tests/test_scoring.py
docs/gold-game/g001-decision-log.json
docs/generated-games/g1-scripted-decision-log.json
docs/generated-games/g1b-mock-agent-decision-log.json
docs/generated-games/g1c-wolf-consensus-decision-log.json
docs/generated-games/g1d-fake-provider-decision-log.json
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

Potentially modify if tests reveal generated references are asserted:

```text
docs/gold-game/s2-score-log.json
docs/gold-game/s2-metrics-summary.json
docs/gold-game/s5-score-log.json
docs/gold-game/s5-metrics-summary.json
docs/generated-games/g1-scripted-score-log.json
docs/generated-games/g1-scripted-metrics-summary.json
docs/generated-games/g1b-mock-agent-score-log.json
docs/generated-games/g1b-mock-agent-metrics-summary.json
docs/generated-games/g1c-wolf-consensus-score-log.json
docs/generated-games/g1c-wolf-consensus-metrics-summary.json
docs/generated-games/g1d-fake-provider-score-log.json
docs/generated-games/g1d-fake-provider-metrics-summary.json
docs/demo/phase2-runtime-demo.html
docs/demo/phase2-s5-runtime-demo.html
docs/demo/phase3-g1-scripted-runtime-demo.html
docs/demo/phase3-g1b-mock-agent-runtime-demo.html
docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
docs/demo/phase3-g1d-fake-provider-runtime-demo.html
```

Do not change these optional outputs unless the existing canonical regeneration commands produce deterministic diffs that are required by tests or validators.

## Global Allowlist

```text
src/werewolf_eval/decision_log.py
src/werewolf_eval/game_engine.py
src/werewolf_eval/scoring.py
tests/test_decision_log.py
tests/test_game_engine.py
tests/test_scoring.py
docs/gold-game/g001-decision-log.json
docs/generated-games/g1-scripted-decision-log.json
docs/generated-games/g1b-mock-agent-decision-log.json
docs/generated-games/g1c-wolf-consensus-decision-log.json
docs/generated-games/g1d-fake-provider-decision-log.json
docs/gold-game/s2-score-log.json
docs/gold-game/s2-metrics-summary.json
docs/gold-game/s5-score-log.json
docs/gold-game/s5-metrics-summary.json
docs/generated-games/g1-scripted-score-log.json
docs/generated-games/g1-scripted-metrics-summary.json
docs/generated-games/g1b-mock-agent-score-log.json
docs/generated-games/g1b-mock-agent-metrics-summary.json
docs/generated-games/g1c-wolf-consensus-score-log.json
docs/generated-games/g1c-wolf-consensus-metrics-summary.json
docs/generated-games/g1d-fake-provider-score-log.json
docs/generated-games/g1d-fake-provider-metrics-summary.json
docs/demo/phase2-runtime-demo.html
docs/demo/phase2-s5-runtime-demo.html
docs/demo/phase3-g1-scripted-runtime-demo.html
docs/demo/phase3-g1b-mock-agent-runtime-demo.html
docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
docs/demo/phase3-g1d-fake-provider-runtime-demo.html
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

## Global Forbidden Scope

Do not modify:

```text
docs/ai-worklog/**
docs/TASKS.md
docs/ROADMAP.md
docs/harness/plans/**
src/werewolf_eval/deepseek_provider.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/provider_contract.py
src/werewolf_eval/run_deepseek_provider_game.py
src/werewolf_eval/run_deepseek_consensus_game.py
src/werewolf_eval/render_provider_replay.py
package.json
package-lock.json
pyproject.toml
requirements.txt
requirements-dev.txt
```

Do not add live API calls, provider SDKs, dependency changes, HTML replay behavior, consensus behavior changes unrelated to decision `round`, or a compatibility shim that silently guesses missing rounds from event order.

## Task 1: Add `round` to Decision Log parser and validator

**Files:**

- Modify: `src/werewolf_eval/decision_log.py`
- Modify: `tests/test_decision_log.py`
- Test: `tests/test_decision_log.py`

- [ ] **Step 1: Add failing schema tests**

Add tests:

```python
def test_decision_requires_round(self): ...
def test_decision_rejects_non_integer_round(self): ...
def test_decision_rejects_negative_round(self): ...
def test_decision_accepts_round_matching_game_event_round(self): ...
```

Use a minimal valid decision fixture and remove or mutate `round`.

Required assertions:

```python
with self.assertRaisesRegex(DecisionLogValidationError, "decision missing fields: .*round"):
    parse_decision_log(raw_without_round, game)

with self.assertRaisesRegex(DecisionLogValidationError, "round must be a non-negative integer"):
    parse_decision_log(raw_with_negative_round, game)
```

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log -v
```

Expected before implementation:

```text
FAIL because round is not part of the Decision schema
```

- [ ] **Step 2: Implement parser/dataclass/validator change**

Update `Decision`:

```python
@dataclass(frozen=True)
class Decision:
    decision_id: str
    actor: str
    decision_scope: str
    consensus_id: str | None
    phase: str
    round: int
    action: str
    target: str | None
    visible_info_refs: list[str]
    reason_summary: str
    decision_type: str
    confidence: float | None
    strategy_tag: str | None
```

Update required fields:

```python
required_fields = {
    "decision_id",
    "actor",
    "decision_scope",
    "consensus_id",
    "phase",
    "round",
    "action",
    "target",
    "visible_info_refs",
    "reason_summary",
    "decision_type",
}
```

Parse `round` as int and reject non-integer or negative values with a clear error:

```text
<decision_id>: round must be a non-negative integer
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log -v
```

Expected:

```text
OK
```

Commit:

```bash
git add src/werewolf_eval/decision_log.py tests/test_decision_log.py
git commit -m "feat: require round in Decision Log entries"
```

Expected:

```text
commit created
```

## Task 2: Add round to generated engine decisions and fixtures

**Files:**

- Modify: `src/werewolf_eval/game_engine.py`
- Modify: `tests/test_game_engine.py`
- Modify JSON fixtures listed in allowlist as needed

- [ ] **Step 1: Add failing generated-decision tests**

In `tests/test_game_engine.py`, add:

```python
def test_generated_decision_log_entries_include_round(self):
    engine = GameEngine.from_config(build_default_config(game_id="round_field_unit"))
    outputs = engine.run()
    rounds = [decision.get("round") for decision in outputs.decision_log["decisions"]]
    self.assertTrue(rounds)
    self.assertTrue(all(isinstance(value, int) for value in rounds))
    self.assertIn(1, rounds)
    self.assertIn(2, rounds)
```

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine.GameEngineTests.test_generated_decision_log_entries_include_round -v
```

Expected before implementation:

```text
FAIL because generated decisions do not include round
```

- [ ] **Step 2: Implement generated round field**

Update `GameEngine.run` internal `_decision` helper to accept and emit `round`:

```python
def _decision(actor: str, scope: str, phase: str, round_num: int, action: str, target: str, dtype: str, reason: str, refs: list[str] | None = None, consensus_id: str | None = None) -> dict[str, Any]:
    ...
    return {
        "decision_id": f"{game_id}_d{d_counter:03d}",
        "actor": actor,
        "decision_scope": scope,
        "consensus_id": consensus_id,
        "phase": phase,
        "round": round_num,
        "action": action,
        ...
    }
```

Update all call sites in `game_engine.py` to pass the current round explicitly.

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected:

```text
OK
```

- [ ] **Step 3: Update committed Decision Log fixtures**

Add `round` to every decision entry in committed Decision Log JSON fixtures:

```text
docs/gold-game/g001-decision-log.json
docs/generated-games/g1-scripted-decision-log.json
docs/generated-games/g1b-mock-agent-decision-log.json
docs/generated-games/g1c-wolf-consensus-decision-log.json
docs/generated-games/g1d-fake-provider-decision-log.json
```

Round must match the linked event phase/round where applicable. For setup-independent decisions, use the actual game round that action occurred in; do not use `0` for night/day player actions.

Validate:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1b-mock-agent-decision-log.json docs/generated-games/g1b-mock-agent-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1d-fake-provider-decision-log.json docs/generated-games/g1d-fake-provider-game-log.json
```

Expected:

```text
all commands exit 0 and print validated decision log summaries
```

Commit:

```bash
git add src/werewolf_eval/game_engine.py tests/test_game_engine.py docs/gold-game/g001-decision-log.json docs/generated-games/g1-scripted-decision-log.json docs/generated-games/g1b-mock-agent-decision-log.json docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1d-fake-provider-decision-log.json
git commit -m "feat: emit round in generated decision logs"
```

Expected:

```text
commit created
```

## Task 3: Use decision round in scorer matching

**Files:**

- Modify: `src/werewolf_eval/scoring.py`
- Modify: `tests/test_scoring.py`

- [ ] **Step 1: Add ambiguity regression test**

In `tests/test_scoring.py`, add a synthetic game with two `werewolf_kill` events from `wolf_team` to the same target in rounds 1 and 2, and a Decision Log with two matching decisions that differ only by `round`.

Test name:

```python
def test_decision_round_disambiguates_repeated_same_target_actions(self): ...
```

Required assertion:

```python
score_log = score_game(game, decision_log=decision_log)
matched = [record.decision_id for record in score_log.records if record.action_type == "werewolf_kill"]
self.assertEqual(matched, ["d_round_1", "d_round_2"])
```

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_scoring.ScoringTests.test_decision_round_disambiguates_repeated_same_target_actions -v
```

Expected before implementation:

```text
ERROR: ambiguous Decision Log match
```

- [ ] **Step 2: Update matcher**

Update `_decision_matches_event`:

```python
def _decision_matches_event(decision: Decision, event: Event) -> bool:
    return (
        decision.action == event.type
        and decision.phase == event.phase
        and decision.round == event.round
        and _decision_actor_matches_event(decision, event)
        and _decision_target_matches_event(decision, event)
    )
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_scoring -v
```

Expected:

```text
OK
```

Commit:

```bash
git add src/werewolf_eval/scoring.py tests/test_scoring.py
git commit -m "fix: match decisions to events by round"
```

Expected:

```text
commit created
```

## Task 4: Regenerate dependent score/demo artifacts only when needed

**Files:**

- Optional modify score/metrics/demo artifacts listed in allowlist
- Modify: `.oh-my-harness/tree.md`
- Generate/update: `.logs/review/latest/review-packet.md`

Run existing canonical commands that already exist in the repo or tests. Do not invent a new artifact pipeline. At minimum run validators and tests before deciding whether to commit generated diffs.

Required validation commands:

```bash
PYTHONPATH=src python -m unittest tests.test_decision_log tests.test_game_engine tests.test_scoring -v
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall src/werewolf_eval scripts -q
git diff --check
```

Expected:

```text
all tests OK; compile exits 0; git diff --check has no output
```

If full tests fail because committed score/demo artifacts need regeneration, run the existing generator commands referenced by the failing tests or repository docs, then commit only deterministic outputs.

Refresh tree:

```bash
node .codex/hooks/tree.mjs --force
```

Expected:

```text
tree remains valid; commit only if changed
```

Commit generated artifacts if needed:

```bash
git add <only regenerated allowlisted artifacts> .oh-my-harness/tree.md
git commit -m "chore: refresh decision-round artifacts"
```

Expected:

```text
commit created, or no commit if no deterministic artifact changes are needed
```

## Review Packet Requirements

Implementation must provide `.logs/review/latest/review-packet.md` with machine evidence:

```text
1. git diff --name-only
2. git diff --stat
3. git diff --check result
4. changed files allowlist check
5. forbidden patterns check
6. dependency/import diff check
7. test command + exact pass/fail summary
8. key hunk excerpts
9. acceptance checklist with evidence pointer
10. implementer risk notes
```

Additional G1h evidence:

```text
- exact base..head review range
- list of Decision Log fixtures updated with `round`
- validator output for each updated Decision Log fixture
- regression test output proving repeated same-target actions no longer cause ambiguity
- whether any score/demo artifacts were regenerated and why
```

Required allowlist check:

```bash
python - <<'PY'
import subprocess, sys
allowed = {
    "src/werewolf_eval/decision_log.py",
    "src/werewolf_eval/game_engine.py",
    "src/werewolf_eval/scoring.py",
    "tests/test_decision_log.py",
    "tests/test_game_engine.py",
    "tests/test_scoring.py",
    "docs/gold-game/g001-decision-log.json",
    "docs/generated-games/g1-scripted-decision-log.json",
    "docs/generated-games/g1b-mock-agent-decision-log.json",
    "docs/generated-games/g1c-wolf-consensus-decision-log.json",
    "docs/generated-games/g1d-fake-provider-decision-log.json",
    "docs/gold-game/s2-score-log.json",
    "docs/gold-game/s2-metrics-summary.json",
    "docs/gold-game/s5-score-log.json",
    "docs/gold-game/s5-metrics-summary.json",
    "docs/generated-games/g1-scripted-score-log.json",
    "docs/generated-games/g1-scripted-metrics-summary.json",
    "docs/generated-games/g1b-mock-agent-score-log.json",
    "docs/generated-games/g1b-mock-agent-metrics-summary.json",
    "docs/generated-games/g1c-wolf-consensus-score-log.json",
    "docs/generated-games/g1c-wolf-consensus-metrics-summary.json",
    "docs/generated-games/g1d-fake-provider-score-log.json",
    "docs/generated-games/g1d-fake-provider-metrics-summary.json",
    "docs/demo/phase2-runtime-demo.html",
    "docs/demo/phase2-s5-runtime-demo.html",
    "docs/demo/phase3-g1-scripted-runtime-demo.html",
    "docs/demo/phase3-g1b-mock-agent-runtime-demo.html",
    "docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html",
    "docs/demo/phase3-g1d-fake-provider-runtime-demo.html",
    ".oh-my-harness/tree.md",
    ".logs/review/latest/review-packet.md",
}
changed = set(subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines())
extra = sorted(changed - allowed)
print("changed_files=" + ",".join(sorted(changed)))
if extra:
    print("ALLOWLIST_CHECK=FAIL extra=" + ",".join(extra)); sys.exit(1)
print("ALLOWLIST_CHECK=PASS")
PY
```

Expected:

```text
ALLOWLIST_CHECK=PASS
```

Forbidden/dependency checks:

```bash
python - <<'PY'
from pathlib import Path
import subprocess, sys
changed = subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines()
forbidden = ["import requests", "import httpx", "import aiohttp", "from openai", "import openai", "https://api.deepseek.com", "DEEPSEEK_API_KEY"]
violations = []
for name in changed:
    path = Path(name)
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8", errors="replace")
        for bad in forbidden:
            if bad in text:
                violations.append(f"{name}: {bad}")
if violations:
    print("FORBIDDEN_PATTERN_CHECK=FAIL")
    print("\n".join(violations)); sys.exit(1)
print("FORBIDDEN_PATTERN_CHECK=PASS")
PY

git diff -- package.json package-lock.json pyproject.toml requirements.txt requirements-dev.txt
```

Expected:

```text
FORBIDDEN_PATTERN_CHECK=PASS
(no dependency diff output)
```

Key hunk excerpts must include:

```text
- `decision_log.py` hunk adding `round` to dataclass/parser/validator
- `game_engine.py` hunk emitting `round` in generated decisions
- `scoring.py` hunk matching `decision.round == event.round`
- `tests/test_scoring.py` hunk for repeated same-target regression
- fixture diff excerpt showing `round` added to generated decision logs
```

## Acceptance Criteria

```text
A1. Only allowlisted files changed.
A2. Decision Log entries require non-negative integer `round`.
A3. GameEngine generated Decision Logs include correct `round` for every decision.
A4. Existing committed Decision Log fixtures include `round` and validate.
A5. Scoring uses round to match decisions to events.
A6. Repeated same actor/action/phase/target decisions across different rounds no longer raise ambiguous match.
A7. Existing scoring behavior remains stable except for resolved ambiguity and deterministic fixture/schema updates.
A8. Full unittest discovery and compile check pass.
A9. No provider/live API, dependency, HTML replay, or consensus behavior changes are introduced.
A10. Review packet contains all required machine evidence.
```

## Codex B档 Deep Review Risk Points

```text
1. Decision Log schema migration affects many fixtures and validators.
2. Scoring change can alter decision_id traceability if round values are wrong.
3. Generated fixture churn can hide unintended scoring changes.
4. A compatibility shim that guesses missing rounds would weaken schema trust and is forbidden.
5. The PR must not touch provider/live API or HTML replay code.
```

## Final Verification Command Set

```bash
python -m compileall src/werewolf_eval scripts -q
PYTHONPATH=src python -m unittest tests.test_decision_log tests.test_game_engine tests.test_scoring -v
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1b-mock-agent-decision-log.json docs/generated-games/g1b-mock-agent-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1d-fake-provider-decision-log.json docs/generated-games/g1d-fake-provider-game-log.json
git diff --check
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md
```

Expected:

```text
compileall: PASS
targeted unittest: OK
full unittest: OK
all decision log validators: PASS
git diff --check: no whitespace errors
review packet generated
```
