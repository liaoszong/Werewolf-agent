# G1f DeepSeek Consensus Smoke Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a local, opt-in DeepSeek provider smoke that exercises wolf consensus with separate werewolf actors instead of the simplified `wolf_team` single-decision path.

**Architecture:** Reuse the G1e DeepSeek adapter and G1c consensus contracts. Add a provider-backed consensus mode that calls `p1` and `p2` agents for wolf proposals while preserving existing deterministic G1c behavior. Add a guarded CLI that writes Game Log, Decision Log, Consensus Log, Provider Trace, and Failure Audit under `.tmp/` only.

**Tech Stack:** Python stdlib only; existing `DeepSeekProvider`, `ProviderAgent`, `GameEngine`, Consensus Log, Failure Audit, and validators.

---

## Implementation PR Draft

Title:

```text
feat: add G1f DeepSeek consensus smoke
```

Body:

```markdown
## Summary

Implements G1f: a local, opt-in DeepSeek consensus-mode smoke that exercises separate wolf-provider decisions and produces Game Log, Decision Log, Consensus Log, Provider Trace, and Failure Audit.

Bound plan: `docs/harness/plans/2026-06-02--g1f-deepseek-consensus-smoke-plan.md`

## Scope

- Adds provider-backed consensus mode for separate wolf actors.
- Adds guarded `run_deepseek_consensus_game` CLI.
- Adds non-live unit tests with fake providers.
- Keeps real DeepSeek calls behind `--allow-live-api`.

## Validation

- targeted unit tests pass
- full unittest discovery passes
- no-live guard exits non-zero and writes no valid logs
- optional manual DeepSeek consensus smoke produces valid Game/Decision/Consensus bundle
- review packet includes machine evidence
```

## Context Budget Gate

Do not read this full plan during implementation. Generate task contexts:

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-06-02--g1f-deepseek-consensus-smoke-plan.md
python scripts/context/build_task_context.py docs/generated-context/2026-06-02--g1f-deepseek-consensus-smoke-plan.index.json <TASK_ID>
```

Read only `docs/generated-context/current-task.ctx.md`. If insufficient, read only referenced plan lines.

## File Structure

Create:

```text
src/werewolf_eval/run_deepseek_consensus_game.py
tests/test_deepseek_consensus_game.py
```

Modify:

```text
src/werewolf_eval/game_engine.py
tests/test_game_engine.py
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

## Global Allowlist

```text
src/werewolf_eval/game_engine.py
src/werewolf_eval/run_deepseek_consensus_game.py
tests/test_game_engine.py
tests/test_deepseek_consensus_game.py
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

Generated but not committed:

```text
.tmp/g1f-deepseek-consensus-smoke/**
.tmp/g1f-deepseek-consensus-guard/**
```

## Global Forbidden Scope

Do not modify:

```text
docs/ai-worklog/**
docs/TASKS.md
docs/ROADMAP.md
docs/demo/**
docs/generated-games/**
docs/harness/plans/**
src/werewolf_eval/deepseek_provider.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/provider_contract.py
src/werewolf_eval/decision_log.py
src/werewolf_eval/scoring.py
src/werewolf_eval/render_demo.py
package.json
package-lock.json
pyproject.toml
requirements.txt
requirements-dev.txt
```

Do not add provider SDK imports, dependency changes, CI live calls, committed `.tmp` artifacts, scoring changes, HTML report generation, or Decision Log schema migration in this PR.

## Task 1: Add provider-backed wolf consensus mode

**Files:**

- Modify: `src/werewolf_eval/game_engine.py`
- Modify: `tests/test_game_engine.py`
- Test: `tests/test_game_engine.py`

- [ ] **Step 1: Add failing engine test**

Add a test-local fake agent:

```python
class RecordingWolfAgent:
    def __init__(self, player_id: str, target: str) -> None:
        self.player_id = player_id
        self.target = target
        self.observations = []

    def decide(self, observation):
        self.observations.append(observation)
        return AgentAction(
            actor=self.player_id,
            action="werewolf_kill",
            target=self.target,
            phase=observation.phase,
            round=observation.round,
            reason_summary=f"{self.player_id} proposes {self.target}",
            decision_type="team_coordinated",
            confidence=1.0,
            source_label="[DeepSeek API output]",
            visible_info_refs=list(observation.private_event_ids),
        )
```

Add test:

```python
def test_provider_consensus_mode_calls_each_wolf_agent(self):
    p1 = RecordingWolfAgent("p1", "p5")
    p2 = RecordingWolfAgent("p2", "p5")
    engine = GameEngine.from_config(
        build_default_config(game_id="g1f_provider_consensus_unit"),
        agents={
            "p1": p1,
            "p2": p2,
            "p3": MockAgent("p3"),
            "p4": MockAgent("p4"),
            "p5": MockAgent("p5"),
            "p6": MockAgent("p6"),
        },
        source_label="[DeepSeek API output]",
    )
    outputs = engine.run(mode="g1f_provider_consensus")
    self.assertIsNotNone(outputs.consensus_log)
    first = outputs.consensus_log["consensuses"][0]
    self.assertEqual(first["participants"], ["p1", "p2"])
    self.assertEqual(first["final_decision"]["target"], "p5")
    self.assertEqual([obs.player_id for obs in p1.observations], ["p1"])
    self.assertEqual([obs.player_id for obs in p2.observations], ["p2"])
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine.GameEngineTests.test_provider_consensus_mode_calls_each_wolf_agent -v
```

Expected before implementation:

```text
FAIL or ERROR because g1f_provider_consensus is not implemented
```

- [ ] **Step 2: Implement minimal consensus mode**

In `GameEngine.run`, separate the old G1c check from the new provider consensus mode:

```python
is_consensus_mode = mode.startswith("g1c_") or mode == "g1f_provider_consensus"
```

For `mode == "g1f_provider_consensus"`, call `self._mock_agents[wolf_id].decide(...)` for each alive wolf participant instead of using deterministic target selection. Validate every returned action:

```text
actor == wolf_id
action == "werewolf_kill"
phase == "night"
round == round_num
target in alive
target is not a werewolf
```

Invalid or exception paths must append failure records and must not fabricate valid proposals from invalid returns.

Consensus entry requirements:

```text
participants: actual wolf participants for that night
proposals: one proposal per valid wolf action
responses: support/opposition rows derived from target agreement
action_round: 1
status: consensus or coordinator_tie_break
final_decision.target: consensus target or first valid proposal tie-break target
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected:

```text
OK
```

Commit:

```bash
git add src/werewolf_eval/game_engine.py tests/test_game_engine.py
git commit -m "feat: enable provider-backed wolf consensus mode"
```

Expected:

```text
commit created
```

## Task 2: Add guarded DeepSeek consensus smoke CLI

**Files:**

- Create: `src/werewolf_eval/run_deepseek_consensus_game.py`
- Create: `tests/test_deepseek_consensus_game.py`
- Test: `tests/test_deepseek_consensus_game.py`

- [ ] **Step 1: Add failing CLI tests**

Add tests:

```python
class DeepSeekConsensusGameCliTests(unittest.TestCase):
    def test_cli_without_allow_live_api_exits_nonzero_and_writes_nothing(self): ...
    def test_cli_with_allow_live_but_missing_key_exits_nonzero_and_writes_nothing(self): ...
    def test_helper_with_fake_provider_factory_writes_consensus_artifacts(self): ...
    def test_helper_provider_failure_writes_trace_and_failure_audit_but_no_valid_logs(self): ...
```

Expose helper:

```python
def run_deepseek_consensus_game_with_provider_factory(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory,
) -> int:
    ...
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_consensus_game -v
```

Expected before implementation:

```text
FAILED due to missing werewolf_eval.run_deepseek_consensus_game
```

- [ ] **Step 2: Implement CLI**

CLI arguments:

```text
--game-id default g1f_deepseek_consensus_smoke
--out-dir default .tmp/g1f-deepseek-consensus-smoke
--model default deepseek-v4-flash
--base-url default https://api.deepseek.com
--api-key-env default DEEPSEEK_API_KEY
--timeout-seconds default 30
--max-tokens-per-request default 256
--max-provider-requests default 12
--allow-live-api default false
```

Provider mapping:

```text
p1, p2, p3, p4, p5, p6 use ProviderAgent instances backed by one shared DeepSeekProvider budget.
```

Run engine with:

```python
engine.run(mode="g1f_provider_consensus")
```

Success writes:

```text
<out-dir>/game-log.json
<out-dir>/decision-log.json
<out-dir>/consensus-log.json
<out-dir>/provider-trace.json
<out-dir>/failure-audit.json
```

No-live guard output:

```text
live_api=disabled
game_log=not_written
decision_log=not_written
consensus_log=not_written
```

Success output:

```text
deepseek_consensus_game_id=<game_id>
source_label=[DeepSeek API output]
provider_failures=0
game_log=written
decision_log=written
consensus_log=written
provider_trace=written
failure_audit=written
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_consensus_game -v
```

Expected:

```text
OK
```

Commit:

```bash
git add src/werewolf_eval/run_deepseek_consensus_game.py tests/test_deepseek_consensus_game.py
git commit -m "feat: add DeepSeek consensus smoke CLI"
```

Expected:

```text
commit created
```

## Task 3: Validate G1f outputs and refresh tree

**Files:**

- Modify: `.oh-my-harness/tree.md`
- Generate or update: `.logs/review/latest/review-packet.md`

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected:

```text
tree includes run_deepseek_consensus_game.py and test_deepseek_consensus_game.py
```

Run targeted tests:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine tests.test_deepseek_consensus_game -v
```

Expected:

```text
OK
```

Run full tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected:

```text
OK
```

Run compile check:

```bash
python -m compileall src/werewolf_eval scripts -q
```

Expected:

```text
exit code 0
```

Run no-live guard:

```bash
set +e
PYTHONPATH=src python -m werewolf_eval.run_deepseek_consensus_game --game-id g1f_guard --out-dir .tmp/g1f-deepseek-consensus-guard
code=$?
set -e
echo "exit_code=$code"
test "$code" -eq 1
test ! -e .tmp/g1f-deepseek-consensus-guard/game-log.json
test ! -e .tmp/g1f-deepseek-consensus-guard/decision-log.json
test ! -e .tmp/g1f-deepseek-consensus-guard/consensus-log.json
```

Expected:

```text
live_api=disabled
exit_code=1
```

Manual live smoke, local only:

```bash
rm -rf .tmp/g1f-deepseek-consensus-smoke
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" PYTHONPATH=src python -m werewolf_eval.run_deepseek_consensus_game \
  --allow-live-api \
  --game-id g1f_deepseek_consensus_smoke \
  --out-dir .tmp/g1f-deepseek-consensus-smoke \
  --model deepseek-v4-flash \
  --max-provider-requests 12 \
  --max-tokens-per-request 256 \
  --timeout-seconds 30
```

Expected when G1f completion is claimed:

```text
provider_failures=0
game_log=written
decision_log=written
consensus_log=written
provider_trace=written
failure_audit=written
```

Validate live bundle:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log .tmp/g1f-deepseek-consensus-smoke/game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log .tmp/g1f-deepseek-consensus-smoke/decision-log.json .tmp/g1f-deepseek-consensus-smoke/game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log .tmp/g1f-deepseek-consensus-smoke/consensus-log.json .tmp/g1f-deepseek-consensus-smoke/game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_log_bundle .tmp/g1f-deepseek-consensus-smoke/game-log.json --decision-log .tmp/g1f-deepseek-consensus-smoke/decision-log.json --consensus-log .tmp/g1f-deepseek-consensus-smoke/consensus-log.json --failure-audit .tmp/g1f-deepseek-consensus-smoke/failure-audit.json
```

Expected:

```text
all validators exit 0; bundle game_id matches; consensus entries >= 1
```

Commit tree if changed:

```bash
git add .oh-my-harness/tree.md
git commit -m "chore: refresh tree for G1f consensus smoke"
```

Expected:

```text
commit created, or no commit if tree unchanged
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

Additional G1f packet evidence:

```text
- exact base..head review range
- whether manual DeepSeek consensus smoke was run
- if run: sanitized command, exit code, provider request count, provider failure count, validator summaries
- if not run: exact reason
- confirmation that no API key, captured Authorization header, env dump, or `.tmp` artifact is committed
```

Required checks:

```bash
python - <<'PY'
import subprocess, sys
allowed = {
    "src/werewolf_eval/game_engine.py",
    "src/werewolf_eval/run_deepseek_consensus_game.py",
    "tests/test_game_engine.py",
    "tests/test_deepseek_consensus_game.py",
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

python - <<'PY'
from pathlib import Path
import re, subprocess, sys
changed = subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines()
forbidden_imports = ["import requests", "import httpx", "import aiohttp", "from openai", "import openai"]
secret_patterns = [
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{15,}"),
    re.compile(r"Bearer\s+(?!\{)(?!<)(?!REDACTED)(?!redacted)(?!\$)([A-Za-z0-9._-]{32,})"),
    re.compile(r"DEEPSEEK_API_KEY\s*=\s*['\"]?(?!\$DEEPSEEK_API_KEY)(?!<redacted>)(?!REDACTED)([A-Za-z0-9._-]{16,})", re.IGNORECASE),
]
violations = []
for name in changed:
    if name.startswith(".tmp/"):
        violations.append(f"{name}: committed .tmp artifact")
        continue
    path = Path(name)
    if not path.exists() or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for bad in forbidden_imports:
        if bad in text:
            violations.append(f"{name}: {bad}")
    for lineno, line in enumerate(text.splitlines(), 1):
        if any(p.search(line) for p in secret_patterns):
            if '"Bearer "' in line or "'Bearer '" in line or 'f"Bearer {' in line:
                continue
            violations.append(f"{name}:{lineno}: possible secret")
if violations:
    print("FORBIDDEN_PATTERN_CHECK=FAIL")
    print("\n".join(violations)); sys.exit(1)
print("FORBIDDEN_PATTERN_CHECK=PASS")
PY

git diff -- package.json package-lock.json pyproject.toml requirements.txt requirements-dev.txt
```

Expected:

```text
ALLOWLIST_CHECK=PASS
FORBIDDEN_PATTERN_CHECK=PASS
(no dependency diff output)
```

Key hunk excerpts must include:

```text
- `game_engine.py` hunk proving provider consensus mode calls p1/p2 agents
- `run_deepseek_consensus_game.py` hunk proving live guard and `.tmp` output default
- `tests/test_deepseek_consensus_game.py` hunk proving no-live and fake-provider tests
- `.oh-my-harness/tree.md` hunk if refreshed
```

## Acceptance Criteria

```text
A1. Only allowlisted files changed.
A2. Existing G1c deterministic consensus tests still pass.
A3. New provider-backed consensus mode calls separate wolf agents for p1/p2.
A4. Invalid provider wolf actions create failure records and do not fabricate valid proposals.
A5. DeepSeek consensus CLI is live-gated by `--allow-live-api`.
A6. Automated tests perform no network access.
A7. Successful helper run writes game, decision, consensus, provider trace, and failure audit artifacts.
A8. Failure helper run writes trace/audit and no valid game/decision/consensus logs.
A9. Validators pass for manual live smoke before claiming G1f completion.
A10. No secrets, dependency changes, or `.tmp` artifacts are committed.
A11. Review packet contains all required machine evidence.
```

## Codex B档 Deep Review Risk Points

```text
1. `game_engine.py` consensus path changes can regress G1c deterministic behavior.
2. Provider-backed consensus may accidentally repair invalid wolf outputs into valid proposals.
3. Live DeepSeek CLI can leak secrets or run without explicit `--allow-live-api` if guard is wrong.
4. Provider request count can exceed budget if p1/p2 plus day agents use separate provider budgets.
5. Consensus Log source labels may drift from accepted labels.
6. `.tmp` live artifacts must not be committed.
```

## Final Verification Command Set

```bash
python -m compileall src/werewolf_eval scripts -q
PYTHONPATH=src python -m unittest tests.test_game_engine tests.test_deepseek_consensus_game -v
PYTHONPATH=src python -m unittest discover -s tests -v
set +e
PYTHONPATH=src python -m werewolf_eval.run_deepseek_consensus_game --game-id g1f_guard --out-dir .tmp/g1f-deepseek-consensus-guard
code=$?
set -e
echo "exit_code=$code"
test "$code" -eq 1
git diff --check
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md
```

Expected:

```text
compileall: PASS
targeted unittest: OK
full unittest: OK
no-live guard: exit_code=1 and no valid logs written
git diff --check: no whitespace errors
review packet generated
```
