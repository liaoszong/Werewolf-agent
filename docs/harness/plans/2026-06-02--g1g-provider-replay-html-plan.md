# G1g Provider Replay HTML Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a standalone static HTML replay report for provider-backed game bundles so a non-technical reviewer can inspect real-provider gameplay, consensus, provider trace, and failure audit without reading raw JSON.

**Architecture:** Build a new replay renderer that consumes existing log files only. It must not call DeepSeek, mutate game state, change scoring, or modify provider/engine logic. The renderer accepts Game Log, Decision Log, optional Consensus Log, optional Provider Trace, and optional Failure Audit paths, then writes a single static HTML report with clear source labels and provider-boundary statements.

**Tech Stack:** Python standard library only: `argparse`, `json`, `html.escape`, `pathlib`, `typing`; existing log loaders and validators where useful.

---

## Why this follows G1f

G1e proved real DeepSeek provider single-game smoke. G1f is planned to prove real-provider wolf consensus. G1g makes those outputs inspectable through an HTML replay/report similar to earlier Phase 1/Phase 2 demos, without mixing in live API calls or runtime behavior changes.

This plan intentionally does not implement G1f consensus or G1h scoring round disambiguation.

## Implementation PR Draft

Title:

```text
feat: add provider replay HTML report
```

Body:

```markdown
## Summary

Implements G1g: a static provider replay HTML report that reads existing Game/Decision/Consensus/ProviderTrace/FailureAudit JSON files and renders an inspectable replay.

Bound plan: `docs/harness/plans/2026-06-02--g1g-provider-replay-html-plan.md`

## Scope

- Adds `render_provider_replay.py` CLI.
- Adds HTML sections for game summary, timeline, decisions, consensus, provider trace, and failure audit.
- Adds tests using deterministic fixture JSON created in temp directories.
- Does not call any provider or modify engine/scoring/provider code.

## Validation

- targeted renderer tests pass
- full unittest discovery passes
- no dependency/import diff
- generated demo HTML contains expected replay sections and source labels
- review packet contains machine evidence
```

## Context Budget Gate

Do not read this full plan during implementation. Generate context:

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-06-02--g1g-provider-replay-html-plan.md
python scripts/context/build_task_context.py docs/generated-context/2026-06-02--g1g-provider-replay-html-plan.index.json <TASK_ID>
```

Read only `docs/generated-context/current-task.ctx.md`. If insufficient, read only referenced plan lines.

## File Structure

Create:

```text
src/werewolf_eval/render_provider_replay.py
tests/test_render_provider_replay.py
```

Modify:

```text
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

Optional generated artifact, only if G1f smoke artifacts exist locally and the operator explicitly approves a committed sanitized sample:

```text
docs/demo/phase3-g1f-provider-replay.html
```

Do not commit raw live `.tmp` logs. Do not commit provider trace raw content if it includes provider response text that the reviewer has not approved for repository history.

## Global Allowlist

```text
src/werewolf_eval/render_provider_replay.py
tests/test_render_provider_replay.py
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
docs/demo/phase3-g1f-provider-replay.html
```

Generated but not committed:

```text
.tmp/g1g-provider-replay/**
.tmp/g1f-deepseek-consensus-smoke/**
.tmp/g1e-live-smoke*/**
```

## Global Forbidden Scope

Do not modify:

```text
docs/ai-worklog/**
docs/TASKS.md
docs/ROADMAP.md
docs/harness/plans/**
docs/generated-games/**
src/werewolf_eval/game_engine.py
src/werewolf_eval/deepseek_provider.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/provider_contract.py
src/werewolf_eval/decision_log.py
src/werewolf_eval/scoring.py
src/werewolf_eval/render_demo.py
src/werewolf_eval/run_deepseek_provider_game.py
src/werewolf_eval/run_deepseek_consensus_game.py
package.json
package-lock.json
pyproject.toml
requirements.txt
requirements-dev.txt
```

Do not add live API calls, network access, provider SDK imports, JS build tooling, React/Vite, dependency changes, scoring changes, or committed `.tmp` logs.

## Task 1: Add replay context builder and HTML renderer

**Files:**

- Create: `src/werewolf_eval/render_provider_replay.py`
- Create: `tests/test_render_provider_replay.py`
- Test: `tests/test_render_provider_replay.py`

- [ ] **Step 1: Add failing renderer tests**

In `tests/test_render_provider_replay.py`, create temp JSON fixtures with this shape:

```python
GAME_LOG = {
    "game_id": "g1g_fixture",
    "source_label": "[DeepSeek API output]",
    "players": [
        {"player_id": "p1", "role": "werewolf", "team": "werewolf"},
        {"player_id": "p2", "role": "werewolf", "team": "werewolf"},
        {"player_id": "p3", "role": "seer", "team": "villager"},
        {"player_id": "p4", "role": "witch", "team": "villager"},
        {"player_id": "p5", "role": "villager", "team": "villager"},
        {"player_id": "p6", "role": "villager", "team": "villager"},
    ],
    "events": [
        {"event_id": "g1g_e001", "sequence": 1, "round": 0, "phase": "setup", "type": "role_assignment", "actor": "system", "target": "none", "visibility": "public", "data": {"summary": "roles assigned", "visible_info_refs": []}},
        {"event_id": "g1g_e002", "sequence": 2, "round": 1, "phase": "night", "type": "werewolf_kill", "actor": "wolf_team", "target": "p5", "visibility": "werewolf_team", "data": {"summary": "wolves target p5", "visible_info_refs": []}},
    ],
    "result": {"winner": "villager", "end_round": 1, "survivors": ["p1", "p2", "p3", "p4", "p6"], "end_condition": "fixture"},
}
```

Also create minimal Decision Log, Consensus Log, Provider Trace, and Failure Audit fixture dicts. Provider Trace fixture must include request metadata and response metadata but must not include real secrets.

Tests:

```python
class ProviderReplayHtmlTests(unittest.TestCase):
    def test_build_replay_context_counts_sections(self): ...
    def test_render_html_contains_required_sections(self): ...
    def test_write_provider_replay_html_escapes_provider_content(self): ...
    def test_cli_writes_html_without_network_access(self): ...
```

Required assertions:

```python
self.assertIn("Provider Replay", html)
self.assertIn("[DeepSeek API output]", html)
self.assertIn("Consensus Replay", html)
self.assertIn("Provider Trace", html)
self.assertIn("Failure Audit", html)
self.assertIn("No live API call is made", html)
self.assertNotIn("<script", html.lower())
self.assertIn("&lt;unsafe&gt;", html)
```

The `self.assertNotIn("<script", html.lower())` test literal is explicitly allowed in tests. The required forbidden scan below must not scan test files for that literal; it must check generated HTML outputs and renderer source behavior separately.

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_render_provider_replay -v
```

Expected before implementation:

```text
FAILED due to missing werewolf_eval.render_provider_replay
```

- [ ] **Step 2: Implement renderer module**

Create `src/werewolf_eval/render_provider_replay.py` with public functions:

```python
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def build_replay_context(
    *,
    game_log: dict[str, Any],
    decision_log: dict[str, Any] | None = None,
    consensus_log: dict[str, Any] | None = None,
    provider_trace: dict[str, Any] | None = None,
    failure_audit: dict[str, Any] | None = None,
) -> dict[str, Any]: ...


def render_provider_replay_html(context: dict[str, Any]) -> str: ...


def write_provider_replay_html(
    *,
    game_log_path: str | Path,
    output_path: str | Path,
    decision_log_path: str | Path | None = None,
    consensus_log_path: str | Path | None = None,
    provider_trace_path: str | Path | None = None,
    failure_audit_path: str | Path | None = None,
) -> None: ...
```

HTML requirements:

```text
- Single static HTML file.
- No external CSS, no JavaScript, no network resources.
- Uses `html.escape` for every untrusted JSON value.
- Clearly states: "No live API call is made during rendering."
- Displays source labels for each supplied log.
- Displays game summary: game_id, winner, end_round, player count, event count.
- Displays player table.
- Displays event timeline table.
- Displays decision table: decision_id, actor, phase, action, target, reason_summary.
- Displays consensus table: consensus_id, round, participants, status, final target, supporters, dissenters.
- Displays provider trace summary: provider_name, request count, response count, failure count, token usage total if available.
- Displays failure audit rows; if empty, shows "zero provider failures".
- Displays boundary banner: "Replay/report only; not a live observer, not a leaderboard, not a scoring mutation."
```

Run after implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_render_provider_replay -v
```

Expected:

```text
OK
```

Commit:

```bash
git add src/werewolf_eval/render_provider_replay.py tests/test_render_provider_replay.py
git commit -m "feat: add provider replay HTML renderer"
```

Expected:

```text
commit created
```

## Task 2: Add CLI and optional sample HTML generation

**Files:**

- Modify: `src/werewolf_eval/render_provider_replay.py`
- Modify: `tests/test_render_provider_replay.py`
- Optional create/update: `docs/demo/phase3-g1f-provider-replay.html`

- [ ] **Step 1: Add CLI argument tests**

Add tests for CLI `main(argv)`:

```python
def test_cli_requires_game_log_and_html_out(self): ...
def test_cli_writes_expected_output_path(self): ...
def test_cli_accepts_optional_logs(self): ...
```

CLI arguments:

```text
--game-log required
--decision-log optional
--consensus-log optional
--provider-trace optional
--failure-audit optional
--html-out required
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_render_provider_replay -v
```

Expected before CLI implementation:

```text
FAILED because CLI main does not exist or does not parse required args
```

- [ ] **Step 2: Implement CLI**

Add:

```python
def main(argv: list[str] | None = None) -> int:
    ...

if __name__ == "__main__":
    raise SystemExit(main())
```

CLI output on success:

```text
wrote <html-out>
replay_sections=game,decisions,consensus,provider_trace,failure_audit
live_api=not_called
```

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.render_provider_replay --game-log <fixture-game-log> --html-out .tmp/g1g-provider-replay/fixture.html
```

Expected:

```text
wrote .tmp/g1g-provider-replay/fixture.html
live_api=not_called
```

- [ ] **Step 3: Generate optional committed demo only from approved inputs**

If G1f has produced approved sanitized local artifacts, generate:

```bash
PYTHONPATH=src python -m werewolf_eval.render_provider_replay \
  --game-log .tmp/g1f-deepseek-consensus-smoke/game-log.json \
  --decision-log .tmp/g1f-deepseek-consensus-smoke/decision-log.json \
  --consensus-log .tmp/g1f-deepseek-consensus-smoke/consensus-log.json \
  --provider-trace .tmp/g1f-deepseek-consensus-smoke/provider-trace.json \
  --failure-audit .tmp/g1f-deepseek-consensus-smoke/failure-audit.json \
  --html-out docs/demo/phase3-g1f-provider-replay.html
```

Expected:

```text
wrote docs/demo/phase3-g1f-provider-replay.html
live_api=not_called
```

If approved G1f artifacts are not available, do not create the committed HTML file in this PR. Record `sample_html=not_generated` in the review packet.

Commit if HTML is generated:

```bash
git add src/werewolf_eval/render_provider_replay.py tests/test_render_provider_replay.py docs/demo/phase3-g1f-provider-replay.html
git commit -m "feat: add provider replay HTML CLI"
```

Commit without HTML if no approved sample exists:

```bash
git add src/werewolf_eval/render_provider_replay.py tests/test_render_provider_replay.py
git commit -m "feat: add provider replay HTML CLI"
```

Expected:

```text
commit created
```

## Task 3: Refresh tree and validate

**Files:**

- Modify: `.oh-my-harness/tree.md`
- Generate/update: `.logs/review/latest/review-packet.md`

Run tree refresh:

```bash
node .codex/hooks/tree.mjs --force
```

Expected:

```text
tree includes render_provider_replay.py and test_render_provider_replay.py
```

Run targeted tests:

```bash
PYTHONPATH=src python -m unittest tests.test_render_provider_replay -v
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

Compile:

```bash
python -m compileall src/werewolf_eval scripts -q
```

Expected:

```text
exit code 0
```

Diff check:

```bash
git diff --check
```

Expected:

```text
(no output)
```

Commit tree if changed:

```bash
git add .oh-my-harness/tree.md
git commit -m "chore: refresh tree for provider replay HTML"
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

Additional G1g evidence:

```text
- exact base..head review range
- whether committed sample HTML was generated
- if generated: source artifact paths and confirmation that raw `.tmp` JSON was not committed
- if not generated: exact reason
- confirmation that renderer makes no network/API call
- confirmation that rendered HTML contains no JavaScript tag and no external resource reference
```

Required allowlist check:

```bash
python - <<'PY'
import subprocess, sys
allowed = {
    "src/werewolf_eval/render_provider_replay.py",
    "tests/test_render_provider_replay.py",
    "docs/demo/phase3-g1f-provider-replay.html",
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

Forbidden source/dependency checks:

```bash
python - <<'PY'
from pathlib import Path
import re, subprocess, sys
changed = subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines()
source_files = [name for name in changed if name.startswith("src/")]
test_files = [name for name in changed if name.startswith("tests/")]
html_files = [name for name in changed if name.endswith(".html")]

# These source patterns are forbidden in runtime source. Tests may contain assertion literals
# such as self.assertNotIn("<script", html.lower()), so tests are not scanned for that literal.
forbidden_source_patterns = [
    "import requests",
    "import httpx",
    "import aiohttp",
    "from openai",
    "import openai",
    "fetch(",
    "XMLHttpRequest",
    "https://api.deepseek.com",
]
secret_patterns = [
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{15,}"),
    re.compile(r"Bearer\s+(?!\{)(?!<)(?!REDACTED)(?!redacted)(?!\$)([A-Za-z0-9._-]{32,})"),
]
violations = []
for name in changed:
    if name.startswith(".tmp/"):
        violations.append(f"{name}: committed .tmp artifact")

for name in source_files:
    path = Path(name)
    if not path.exists() or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for bad in forbidden_source_patterns:
        if bad in text:
            violations.append(f"{name}: forbidden source pattern {bad}")

for name in source_files + test_files + html_files:
    path = Path(name)
    if not path.exists() or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), 1):
        if any(p.search(line) for p in secret_patterns):
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
FORBIDDEN_PATTERN_CHECK=PASS
(no dependency diff output)
```

Rendered HTML safety check:

```bash
python - <<'PY'
from pathlib import Path
import sys

html_candidates = [
    Path("docs/demo/phase3-g1f-provider-replay.html"),
    Path(".tmp/g1g-provider-replay/fixture.html"),
]
violations = []
checked = []
for path in html_candidates:
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    checked.append(str(path))
    if "<script" in text:
        violations.append(f"{path}: script tag found")
    if "src=\"http" in text or "href=\"http" in text or "url(http" in text:
        violations.append(f"{path}: external resource reference found")
if violations:
    print("HTML_OUTPUT_SAFETY_CHECK=FAIL")
    print("\n".join(violations)); sys.exit(1)
print("HTML_OUTPUT_SAFETY_CHECK=PASS checked=" + ",".join(checked))
PY
```

Expected:

```text
HTML_OUTPUT_SAFETY_CHECK=PASS
```

This separates test/source scanning from rendered-output scanning. Test assertions may contain the literal `"<script"`; generated HTML must not contain a script tag.

Key hunk excerpts must include:

```text
- renderer hunk proving `html.escape` use
- renderer hunk proving no live API call and no network imports
- CLI hunk proving file-only inputs
- tests hunk proving escaping and script-tag absence assertion
- optional HTML artifact hunk if committed
```

## Acceptance Criteria

```text
A1. Only allowlisted files changed.
A2. Renderer consumes existing JSON logs only and performs no network/API calls.
A3. HTML is single-file static output with no JS and no external resources.
A4. All untrusted JSON values are escaped.
A5. Report includes game summary, player table, timeline, decisions, consensus, provider trace, and failure audit sections.
A6. Report clearly labels `[DeepSeek API output]` and boundary statement.
A7. Tests cover context, HTML content, escaping, and CLI output.
A8. Full unittest discovery and compile check pass.
A9. No dependencies, provider code, engine code, scoring code, or `.tmp` logs are changed/committed.
A10. Review packet contains all required machine evidence.
A11. Forbidden scan does not fail on test assertion literals; rendered HTML safety check verifies generated HTML contains no script tag or external resource reference.
```

## Codex B档 Deep Review Risk Points

```text
1. HTML renderer can accidentally expose raw provider text or unsafe HTML if escaping is incomplete.
2. Optional committed HTML artifact may accidentally include live provider raw responses or sensitive content.
3. Forbidden scan must not self-hit on test literals, but rendered HTML must still be checked for script tags and external resources.
4. This PR must not touch engine/provider/scoring behavior.
5. Large generated HTML may inflate review packet; packet should include excerpts, not entire artifact.
```

## Final Verification Command Set

```bash
python -m compileall src/werewolf_eval scripts -q
PYTHONPATH=src python -m unittest tests.test_render_provider_replay -v
PYTHONPATH=src python -m unittest discover -s tests -v
git diff --check
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md
```

Expected:

```text
compileall: PASS
targeted unittest: OK
full unittest: OK
git diff --check: no whitespace errors
review packet generated
```
