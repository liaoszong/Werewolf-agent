# G1c Wolf Consensus + Failure Recovery Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add G1c wolf-team night consensus and failure-recovery behavior to the deterministic mock game engine, producing auditable Consensus Log and failure-audit outputs without provider calls or forged valid logs.

**Architecture:** G1a already proves fresh scripted logs can feed validators and evaluator demos; G1b already provides a deterministic game engine, private observations, mock agents, and structured `AgentAction`. G1c extends that engine loop at the wolf night phase: collect wolf actions, resolve consensus deterministically, reject invalid / timed-out / parse-failed actions into an audit trail, and emit a valid Consensus Log only from valid wolf proposals. This remains a deterministic local runtime slice; provider boundaries remain G1d.

**Tech Stack:** Python standard library, existing `src/werewolf_eval/game_engine.py`, existing `src/werewolf_eval/run_mock_game.py`, existing Game Log / Decision Log / Consensus Log validators, existing scoring / rendering commands, `unittest`.

---

## Source-of-Truth Routing

This plan follows the current `docs/specs/agent-workflow.md` rule that next-step decisions use `docs/TASKS.md`, `docs/ROADMAP.md`, relevant file state, generated artifacts, and recent PRs together. `docs/TASKS.md` marks G1c as `next_candidate` and describes it as wolf consensus + failure recovery; `docs/ROADMAP.md` says G1c should handle werewolf night consensus protocol, invalid action, timeout, parse failure, and audit trail before G1d provider adapter research.

## Research PR Decision

No Research PR is needed.

The boundary is narrow and implementation-ready:

- extend the deterministic G1b mock game engine;
- use existing mock agents / structured actions;
- generate Consensus Log for valid wolf-team night coordination;
- record invalid action, timeout, and parse-failure cases in an audit artifact;
- keep provider integration, live AI, fake-provider research, and multi-game Leaderboard out of scope.

## Bound Implementation PR

Future Implementation PR title:

```text
feat: G1c wolf consensus failure recovery
```

Bound plan path:

```text
docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md
```

## Global Allowlist

The Implementation PR may modify only these paths:

```text
src/werewolf_eval/game_engine.py
src/werewolf_eval/run_mock_game.py
tests/test_game_engine.py
docs/generated-games/g1c-wolf-consensus-game-log.json
docs/generated-games/g1c-wolf-consensus-decision-log.json
docs/generated-games/g1c-wolf-consensus-consensus-log.json
docs/generated-games/g1c-wolf-consensus-failure-audit.json
docs/generated-games/g1c-wolf-consensus-score-log.json
docs/generated-games/g1c-wolf-consensus-metrics-summary.json
docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
README.md
docs/TASKS.md
docs/ROADMAP.md
.oh-my-harness/tree.md
```

If `.logs/review/latest/review-packet.md` is generated locally, it must stay untracked.

## Global Forbidden Scope

Do not modify:

```text
src/werewolf_eval/scoring.py
src/werewolf_eval/score_game.py
src/werewolf_eval/semantic_labels.py
src/werewolf_eval/validate_semantic_labels.py
src/werewolf_eval/consensus_log.py
src/werewolf_eval/validate_consensus_log.py
src/werewolf_eval/decision_log.py
src/werewolf_eval/validate_decision_log.py
src/werewolf_eval/render_demo.py
docs/gold-game/**
docs/semantic-labeling/**
docs/EVALUATION_RUBRIC.md
requirements.txt
requirements-dev.txt
pyproject.toml
package.json
package-lock.json
pnpm-lock.yaml
```

Do not introduce:

```text
provider API calls
network calls
new runtime dependencies
secrets or credential requirements
live AI reasoning
prompt execution
stochastic gameplay
fake provider contract
provider adapter research
multi-game Leaderboard aggregation
human-vs-AI UI
silent repair of invalid behavior
```

Invalid wolf actions must be represented as invalid in the audit trail. They must not be rewritten into valid decisions or hidden from generated evidence.

## Files and Responsibilities

- `src/werewolf_eval/game_engine.py`
  - Add deterministic wolf consensus collection / resolution inside the existing G1b engine.
  - Add failure-audit records for invalid action, timeout, and parse failure.
  - Emit Consensus Log dictionaries compatible with the existing Consensus Log validator.
- `src/werewolf_eval/run_mock_game.py`
  - Add CLI outputs for Consensus Log and failure audit.
  - Generate G1c demo artifacts from the G1c scenario mode.
- `tests/test_game_engine.py`
  - Add tests for valid wolf consensus, split vote, invalid action, timeout, parse failure, CLI outputs, and validator compatibility.
- `docs/generated-games/g1c-*`
  - Store deterministic G1c generated outputs.
- `docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`
  - Store demo HTML generated from the G1c game/decision outputs using existing renderer behavior.
- `README.md`, `docs/TASKS.md`, `docs/ROADMAP.md`
  - Mark G1c complete and move the next G-track candidate to G1d provider adapter research / fake-provider contract.
- `.oh-my-harness/tree.md`
  - Refresh after new generated artifacts are added.

---

## Task 1: Add consensus and failure-recovery tests first

**Files:**

- Modify: `tests/test_game_engine.py`
- Test: `tests/test_game_engine.py`

- [ ] **Step 1: Add failing tests for wolf consensus and failure audit**

Append tests with these concrete expectations. Use existing helper names from `tests/test_game_engine.py`; if helpers differ, keep the assertions and adapt only the fixture construction to the existing test style.

```python
def test_g1c_wolf_consensus_log_is_emitted_for_valid_night_kill(self):
    result = run_mock_game_for_test(mode="g1c_consensus")
    consensus_log = result["consensus_log"]

    self.assertEqual(consensus_log["game_id"], result["game_log"]["game_id"])
    self.assertEqual(consensus_log["source_label"], "[deterministic mock agent output]")
    self.assertGreaterEqual(len(consensus_log["consensuses"]), 1)

    first = consensus_log["consensuses"][0]
    self.assertEqual(first["phase"], "night")
    self.assertEqual(first["status"], "consensus")
    self.assertIn("p1", first["participants"])
    self.assertIn("p2", first["participants"])
    self.assertEqual(first["target"], "p5")


def test_g1c_split_wolf_vote_records_no_consensus_and_audit(self):
    result = run_mock_game_for_test(mode="g1c_split_wolf_vote")
    consensus_log = result["consensus_log"]
    audit = result["failure_audit"]

    self.assertTrue(any(item["status"] == "no_consensus" for item in consensus_log["consensuses"]))
    self.assertTrue(any(item["kind"] == "wolf_consensus_failure" for item in audit["failures"]))
    self.assertFalse(any(item.get("repaired_to_valid_action") for item in audit["failures"]))


def test_g1c_invalid_wolf_action_is_rejected_not_repaired(self):
    result = run_mock_game_for_test(mode="g1c_invalid_wolf_action")
    audit = result["failure_audit"]
    decision_log = result["decision_log"]

    self.assertTrue(any(item["kind"] == "invalid_action" for item in audit["failures"]))
    invalid_targets = {item["target"] for item in audit["failures"] if item["kind"] == "invalid_action"}
    valid_decision_targets = {item.get("target") for item in decision_log["decisions"]}
    self.assertTrue(invalid_targets.isdisjoint(valid_decision_targets))


def test_g1c_timeout_and_parse_failure_are_audited(self):
    result = run_mock_game_for_test(mode="g1c_timeout_parse_failure")
    kinds = {item["kind"] for item in result["failure_audit"]["failures"]}

    self.assertIn("timeout", kinds)
    self.assertIn("parse_failure", kinds)
```

If `run_mock_game_for_test` does not exist, create a local helper in the test file that calls the existing engine function directly and returns a dictionary with these keys:

```text
game_log
decision_log
consensus_log
failure_audit
```

- [ ] **Step 2: Run the new tests and confirm failure before implementation**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected result before implementation:

```text
FAILED
```

The failure must be caused by missing G1c consensus / failure-audit behavior, not syntax errors.

## Task 2: Implement deterministic wolf consensus in the engine

**Files:**

- Modify: `src/werewolf_eval/game_engine.py`
- Modify: `tests/test_game_engine.py`

- [ ] **Step 1: Add explicit data structures or dictionaries for consensus and failures**

In `src/werewolf_eval/game_engine.py`, add local dataclasses or dictionary builders that produce these stable fields:

```python
CONSENSUS_SOURCE_LABEL = "[deterministic mock agent output]"


def build_failure(game_id: str, round_number: int, phase: str, actor: str, kind: str, reason: str, target: str | None = None) -> dict:
    return {
        "game_id": game_id,
        "round": round_number,
        "phase": phase,
        "actor": actor,
        "kind": kind,
        "target": target,
        "reason": reason,
        "repaired_to_valid_action": False,
    }
```

If the project targets a Python version that does not support `str | None`, use `Optional[str]` from `typing` instead.

- [ ] **Step 2: Resolve valid wolf consensus deterministically**

Add a function that receives wolf night kill proposals and returns one consensus record plus failure records. Required behavior:

```text
- If all live wolves propose the same live non-wolf target, emit status `consensus`.
- If live wolves propose different valid targets, emit status `no_consensus` and add one `wolf_consensus_failure` audit record.
- If a wolf proposes an invalid target, add `invalid_action` audit and exclude that action from valid consensus counting.
- If an action is missing because timeout is simulated, add `timeout` audit.
- If an action is present but cannot be parsed into the structured action contract, add `parse_failure` audit.
- Never convert an invalid / timed-out / parse-failed action into a valid Decision Log entry.
```

The consensus record must include these keys so it can be converted to the existing Consensus Log shape:

```text
consensus_id
game_id
round
phase
participants
coordinator
status
primary_proposer
supporters
dissenters
target
source_decision_ids
source_event_ids
source_label
```

- [ ] **Step 3: Wire G1c mode into the existing mock game loop**

Add deterministic G1c modes inside the existing game engine entrypoint:

```text
g1c_consensus
g1c_split_wolf_vote
g1c_invalid_wolf_action
g1c_timeout_parse_failure
```

Each mode must be deterministic and must not use random selection.

- [ ] **Step 4: Run engine tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected result:

```text
OK
```

## Task 3: Extend CLI outputs for Consensus Log and failure audit

**Files:**

- Modify: `src/werewolf_eval/run_mock_game.py`
- Modify: `tests/test_game_engine.py`

- [ ] **Step 1: Add CLI output arguments**

Extend `src/werewolf_eval/run_mock_game.py` with these arguments:

```text
--mode g1c_consensus
--consensus-log-out <path>
--failure-audit-out <path>
```

Keep existing game / decision output flags intact. The CLI must support a single command writing all four artifacts:

```bash
PYTHONPATH=src python -m werewolf_eval.run_mock_game \
  --mode g1c_consensus \
  --game-log-out docs/generated-games/g1c-wolf-consensus-game-log.json \
  --decision-log-out docs/generated-games/g1c-wolf-consensus-decision-log.json \
  --consensus-log-out docs/generated-games/g1c-wolf-consensus-consensus-log.json \
  --failure-audit-out docs/generated-games/g1c-wolf-consensus-failure-audit.json
```

Expected result:

```text
generated game_log=docs/generated-games/g1c-wolf-consensus-game-log.json decision_log=docs/generated-games/g1c-wolf-consensus-decision-log.json consensus_log=docs/generated-games/g1c-wolf-consensus-consensus-log.json failure_audit=docs/generated-games/g1c-wolf-consensus-failure-audit.json
```

- [ ] **Step 2: Add CLI test**

Add a test that runs the command in a temporary directory and verifies all four files exist, are valid JSON, and contain source label `[deterministic mock agent output]` where applicable.

Required assertions:

```python
self.assertTrue(game_log_path.exists())
self.assertTrue(decision_log_path.exists())
self.assertTrue(consensus_log_path.exists())
self.assertTrue(failure_audit_path.exists())
self.assertEqual(consensus_log["source_label"], "[deterministic mock agent output]")
self.assertEqual(failure_audit["source_label"], "[deterministic mock agent output]")
```

- [ ] **Step 3: Run CLI test set**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected result:

```text
OK
```

## Task 4: Generate G1c artifacts and validate them

**Files:**

- Create: `docs/generated-games/g1c-wolf-consensus-game-log.json`
- Create: `docs/generated-games/g1c-wolf-consensus-decision-log.json`
- Create: `docs/generated-games/g1c-wolf-consensus-consensus-log.json`
- Create: `docs/generated-games/g1c-wolf-consensus-failure-audit.json`
- Create: `docs/generated-games/g1c-wolf-consensus-score-log.json`
- Create: `docs/generated-games/g1c-wolf-consensus-metrics-summary.json`
- Create: `docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`
- Test: validator and generation commands below

- [ ] **Step 1: Generate raw G1c logs**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.run_mock_game \
  --mode g1c_consensus \
  --game-log-out docs/generated-games/g1c-wolf-consensus-game-log.json \
  --decision-log-out docs/generated-games/g1c-wolf-consensus-decision-log.json \
  --consensus-log-out docs/generated-games/g1c-wolf-consensus-consensus-log.json \
  --failure-audit-out docs/generated-games/g1c-wolf-consensus-failure-audit.json
```

Expected result:

```text
generated game_log=docs/generated-games/g1c-wolf-consensus-game-log.json decision_log=docs/generated-games/g1c-wolf-consensus-decision-log.json consensus_log=docs/generated-games/g1c-wolf-consensus-consensus-log.json failure_audit=docs/generated-games/g1c-wolf-consensus-failure-audit.json
```

- [ ] **Step 2: Validate generated Game Log**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated game_id=g1c_wolf_consensus
```

The command may include additional counts after the game id. It must exit 0.

- [ ] **Step 3: Validate generated Decision Log**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated decision_log_id=g1c_wolf_consensus_decision_log game_id=g1c_wolf_consensus
```

The command may include additional counts. It must exit 0.

- [ ] **Step 4: Validate generated Consensus Log**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1c-wolf-consensus-consensus-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated consensus_log_id=g1c_wolf_consensus_consensus_log game_id=g1c_wolf_consensus
```

The command may include additional counts. It must exit 0.

- [ ] **Step 5: Generate score and metrics artifacts**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.score_game \
  docs/generated-games/g1c-wolf-consensus-game-log.json \
  --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json \
  --score-log-out docs/generated-games/g1c-wolf-consensus-score-log.json \
  --metrics-out docs/generated-games/g1c-wolf-consensus-metrics-summary.json
```

Expected result:

```text
scored game_id=g1c_wolf_consensus
```

The command may include score-record and winner details. It must exit 0.

- [ ] **Step 6: Generate demo HTML**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo \
  docs/generated-games/g1c-wolf-consensus-game-log.json \
  --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json \
  --html-out docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
```

Expected result:

```text
rendered_demo_html=docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
```

- [ ] **Step 7: Verify generated artifacts carry deterministic provenance**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in [
    Path('docs/generated-games/g1c-wolf-consensus-game-log.json'),
    Path('docs/generated-games/g1c-wolf-consensus-decision-log.json'),
    Path('docs/generated-games/g1c-wolf-consensus-consensus-log.json'),
    Path('docs/generated-games/g1c-wolf-consensus-failure-audit.json'),
    Path('docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html'),
]:
    text = path.read_text(encoding='utf-8')
    assert '[deterministic mock agent output]' in text, path
    assert '[人工 gold sample]' not in text, path
print('g1c provenance check: PASS')
PY
```

Expected result:

```text
g1c provenance check: PASS
```

## Task 5: Update project status docs and tree

**Files:**

- Modify: `README.md`
- Modify: `docs/TASKS.md`
- Modify: `docs/ROADMAP.md`
- Modify: `.oh-my-harness/tree.md`
- Test: inline docs checks below

- [ ] **Step 1: Update status docs**

Make these exact status changes:

```text
docs/TASKS.md:
- Change G1c status from `next_candidate` to `completed`.
- Add outputs for G1c generated Game Log, Decision Log, Consensus Log, failure audit, Score Log, Metrics Summary, and demo HTML.
- Change G1d from `future_research_candidate` to `next_candidate`.

README.md:
- Mention that G1c wolf consensus + failure recovery is completed.
- State that G1d provider adapter research / fake-provider contract is the next candidate.

docs/ROADMAP.md:
- Add G1c to completed current main facts after implementation.
- Change G1c status to `completed`.
- Change current priority to G1d provider adapter research / fake-provider contract.
```

- [ ] **Step 2: Run docs status check**

Run:

```bash
python - <<'PY'
from pathlib import Path
tasks = Path('docs/TASKS.md').read_text(encoding='utf-8')
roadmap = Path('docs/ROADMAP.md').read_text(encoding='utf-8')
readme = Path('README.md').read_text(encoding='utf-8')
for text, name in [(tasks, 'TASKS'), (roadmap, 'ROADMAP'), (readme, 'README')]:
    assert 'G1c' in text, name
    assert 'wolf consensus' in text or 'wolf-team consensus' in text, name
assert 'g1c-wolf-consensus-consensus-log.json' in tasks
assert 'g1c-wolf-consensus-failure-audit.json' in tasks
assert 'G1d' in tasks and 'next_candidate' in tasks
print('g1c docs status: PASS')
PY
```

Expected result:

```text
g1c docs status: PASS
```

- [ ] **Step 3: Refresh tree**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md updated
```

If the hook prints a different success message but changes the tree file, record the exact output in the PR validation section.

## Final Validation Commands

Run all commands below before opening review.

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected result:

```text
OK
```

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result:

```text
OK
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated game_id=g1c_wolf_consensus
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated decision_log_id=g1c_wolf_consensus_decision_log game_id=g1c_wolf_consensus
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1c-wolf-consensus-consensus-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
```

Expected result:

```text
validated consensus_log_id=g1c_wolf_consensus_consensus_log game_id=g1c_wolf_consensus
```

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --score-log-out docs/generated-games/g1c-wolf-consensus-score-log.json --metrics-out docs/generated-games/g1c-wolf-consensus-metrics-summary.json
```

Expected result:

```text
scored game_id=g1c_wolf_consensus
```

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --html-out docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
```

Expected result:

```text
rendered_demo_html=docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
```

```bash
git diff --check
```

Expected result:

```text
(no output)
```

```bash
python - <<'PY'
import fnmatch
import subprocess
allowlist = [
    'src/werewolf_eval/game_engine.py',
    'src/werewolf_eval/run_mock_game.py',
    'tests/test_game_engine.py',
    'docs/generated-games/g1c-wolf-consensus-game-log.json',
    'docs/generated-games/g1c-wolf-consensus-decision-log.json',
    'docs/generated-games/g1c-wolf-consensus-consensus-log.json',
    'docs/generated-games/g1c-wolf-consensus-failure-audit.json',
    'docs/generated-games/g1c-wolf-consensus-score-log.json',
    'docs/generated-games/g1c-wolf-consensus-metrics-summary.json',
    'docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html',
    'README.md',
    'docs/TASKS.md',
    'docs/ROADMAP.md',
    '.oh-my-harness/tree.md',
]
changed = subprocess.check_output(['git', 'diff', '--name-only', 'main...HEAD'], text=True).splitlines()
misses = [p for p in changed if not any(fnmatch.fnmatch(p, pat) for pat in allowlist)]
if misses:
    raise SystemExit('allowlist misses: ' + ', '.join(misses))
print('changed files allowlist: PASS')
PY
```

Expected result:

```text
changed files allowlist: PASS
```

```bash
python - <<'PY'
import fnmatch
import subprocess
forbidden = [
    'src/werewolf_eval/scoring.py',
    'src/werewolf_eval/score_game.py',
    'src/werewolf_eval/semantic_labels.py',
    'src/werewolf_eval/validate_semantic_labels.py',
    'src/werewolf_eval/consensus_log.py',
    'src/werewolf_eval/validate_consensus_log.py',
    'src/werewolf_eval/decision_log.py',
    'src/werewolf_eval/validate_decision_log.py',
    'src/werewolf_eval/render_demo.py',
    'docs/gold-game/**',
    'docs/semantic-labeling/**',
    'docs/EVALUATION_RUBRIC.md',
    'requirements.txt',
    'requirements-dev.txt',
    'pyproject.toml',
    'package.json',
    'package-lock.json',
    'pnpm-lock.yaml',
]
changed = subprocess.check_output(['git', 'diff', '--name-only', 'main...HEAD'], text=True).splitlines()
hits = [p for p in changed if any(fnmatch.fnmatch(p, pat) for pat in forbidden)]
if hits:
    raise SystemExit('forbidden scope changed: ' + ', '.join(hits))
print('forbidden scope check: PASS')
PY
```

Expected result:

```text
forbidden scope check: PASS
```

## Acceptance Criteria

- [ ] G1c mode emits a valid Consensus Log for valid wolf-team night coordination.
- [ ] Split wolf target proposals produce `no_consensus` and a failure-audit record.
- [ ] Invalid action, timeout, and parse failure are represented in `failure_audit`.
- [ ] Invalid / timed-out / parse-failed behavior is not repaired into a valid Decision Log entry.
- [ ] Generated Game Log validates with existing Game Log validator.
- [ ] Generated Decision Log validates with existing Decision Log validator.
- [ ] Generated Consensus Log validates with existing Consensus Log validator.
- [ ] Generated G1c Score Log and Metrics Summary can be produced without scoring-code changes.
- [ ] Generated G1c demo HTML is produced with deterministic mock-agent provenance.
- [ ] README / TASKS / ROADMAP mark G1c completed and G1d as next candidate.
- [ ] No provider, network, dependency, live AI, fake-provider, or Leaderboard work is introduced.

## Review Packet Requirements

The Implementation PR must generate `.logs/review/latest/review-packet.md` before Codex review. Do not rely on a verbal summary.

The packet must include at least:

1. `git diff --name-only`
2. `git diff --stat`
3. `git diff --check result`
4. changed files allowlist check
5. forbidden patterns check
6. dependency/import diff check
7. test command + exact pass/fail summary
8. key hunk excerpts
9. acceptance checklist with evidence pointer
10. implementer risk notes

Minimum required packet evidence rows:

```text
| Acceptance | Evidence | Status |
|---|---|---|
| A1: valid wolf consensus emits Consensus Log | tests/test_game_engine.py consensus test + generated consensus log validator | PASS |
| A2: split vote / invalid / timeout / parse failure audited | tests/test_game_engine.py failure tests + failure audit JSON | PASS |
| A3: invalid behavior is not repaired into valid Decision Log | tests/test_game_engine.py invalid-action assertion | PASS |
| A4: generated logs validate | validate_game_log / validate_decision_log / validate_consensus_log command summaries | PASS |
| A5: evaluator pipeline still runs | score_game and render_demo command summaries | PASS |
| A6: allowlist respected | changed files allowlist check | PASS |
| A7: forbidden scope untouched | forbidden scope check | PASS |
```

## Codex B档 Deep Review Risk Points

Trigger `NEED_DEEP_REVIEW` if any of these occur:

```text
changed files outside allowlist
any forbidden scope file changed
any dependency manifest changed
any provider / network / credential / live AI pattern appears in non-doc implementation hunks
scoring.py, score_game.py, render_demo.py, consensus_log.py, or validator files changed
failure audit can be omitted for invalid action / timeout / parse failure
invalid behavior is converted into a valid Decision Log entry
Consensus Log fails validation
Game Log / Decision Log validators fail
G1c generated artifacts contain [人工 gold sample]
review packet lacks key hunk excerpts for game_engine.py and run_mock_game.py
```

## Implementation PR Description Draft

```markdown
## Summary

Implement G1c wolf consensus + failure recovery for the deterministic mock game engine.

Bound plan: `docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md`

## What changed

- Extended `game_engine.py` with deterministic wolf-team night consensus resolution.
- Added failure-audit behavior for split vote, invalid action, timeout, and parse failure.
- Extended `run_mock_game.py` to emit Consensus Log and failure-audit outputs.
- Added G1c tests to `tests/test_game_engine.py`.
- Generated G1c game, decision, consensus, failure-audit, score, metrics, and demo artifacts.
- Updated README / TASKS / ROADMAP to mark G1c complete and G1d as next candidate.

## Validation

```text
PYTHONPATH=src python -m unittest tests.test_game_engine -v
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/generated-games/g1c-wolf-consensus-consensus-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --score-log-out docs/generated-games/g1c-wolf-consensus-score-log.json --metrics-out docs/generated-games/g1c-wolf-consensus-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --html-out docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
git diff --check
changed files allowlist check
forbidden scope check
```

## Review Packet

Generated packet:

```text
.logs/review/latest/review-packet.md
```

## Risk notes

- No provider calls, network calls, dependency additions, live AI, fake-provider, or Leaderboard work.
- Invalid behavior is audited and rejected; it is not repaired into valid logs.
- Existing scoring / semantic / consensus validator files are intentionally unchanged.
```
