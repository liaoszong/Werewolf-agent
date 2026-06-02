# G1e DeepSeek Provider Smoke Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a local, opt-in, budget-bounded DeepSeek API single-game smoke path that proves G1 can run one provider-backed game without CI live calls, multi-game leaderboard claims, or human-vs-AI UI scope creep.

**Decision:** The next development point is **G1e provider-backed single-game smoke**, narrowed to **DeepSeek API**. The repository route already marks G1d complete and G1e as the next candidate, so this plan must not revisit G1c/G1d runtime, generated artifacts, or roadmap status.

**Architecture:** Build on the completed G1d provider contract harness. Add a DeepSeek provider adapter that implements the existing `respond(ProviderRequest) -> ProviderResponse` shape, make `ProviderAgent` preserve provider response provenance, and add a guarded CLI that performs live calls only when the operator passes `--allow-live-api` and supplies the configured API-key environment variable.

**Tech stack:** Python standard library only: `argparse`, `dataclasses`, `json`, `os`, `re`, `sys`, `time`, `urllib.request`, `urllib.error`, `unittest`, `pathlib`, and `typing`. Do not add provider SDKs or dependencies.

---

## Implementation PR Draft

Title:

```text
feat: add G1e DeepSeek provider smoke
```

Body:

```markdown
## Summary

Implements G1e DeepSeek provider-backed single-game smoke as a local opt-in harness.

Bound plan: `docs/harness/plans/2026-06-02--g1e-deepseek-provider-smoke-plan.md`

## Scope

- Adds a DeepSeek provider adapter using Python stdlib HTTP only.
- Adds guarded `run_deepseek_provider_game` CLI.
- Preserves provider `source_label` through `ProviderAgent`.
- Adds non-live unit tests using fake transports.
- Keeps live DeepSeek API execution out of CI and out of default tests.

## Validation

- `python -m compileall src/werewolf_eval scripts`
- `PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_fake_provider tests.test_deepseek_provider tests.test_deepseek_provider_game -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- no-live CLI guard exits non-zero and writes no valid logs
- manual DeepSeek smoke result is recorded in the review packet when run locally with `DEEPSEEK_API_KEY`

## Boundaries

No CI live calls, dependency changes, provider SDKs, multi-game leaderboard aggregation, human-vs-AI UI, or repair path that turns invalid provider output into valid logs.
```

## Context Budget Gate for Claude Code

Do not read this full plan during implementation. Use the context workflow.

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-06-02--g1e-deepseek-provider-smoke-plan.md
```

```bash
python - <<'PY'
import json
from pathlib import Path

plan = Path("docs/harness/plans/2026-06-02--g1e-deepseek-provider-smoke-plan.md")
index_path = Path("docs/generated-context") / f"{plan.stem}.index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))
for task in index["tasks"]:
    print(f"{task['id']}: {task['title']} lines={task['line_start']}-{task['line_end']}")
PY
```

For each task:

```bash
python scripts/context/build_task_context.py docs/generated-context/2026-06-02--g1e-deepseek-provider-smoke-plan.index.json <TASK_ID>
```

Read only:

```text
docs/generated-context/current-task.ctx.md
```

If insufficient, read only the exact original plan lines referenced inside `current-task.ctx.md`.

## DeepSeek API Boundary

Implementation constants:

```python
DEEPSEEK_PROVIDER_SOURCE_LABEL = "[DeepSeek API output]"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_CHAT_PATH = "/chat/completions"
```

Request payload requirements:

```python
{
    "model": model,
    "messages": messages,
    "response_format": {"type": "json_object"},
    "stream": False,
    "max_tokens": max_tokens,
    "thinking": {"type": "disabled"},
}
```

Prompt requirements:

- The prompt must contain the word `json`.
- The prompt must include one exact example JSON object with `action`, `target`, `reason_summary`, `decision_type`, and `confidence`.
- The prompt must include `allowed_actions` and `allowed_targets` from `ProviderRequest`.
- The prompt must instruct the model to choose only from allowed values.
- The adapter must not insert fallback action defaults.

Secret and evidence boundary:

- Read only the environment variable named by `--api-key-env`, default `DEEPSEEK_API_KEY`.
- Never write a real API key, captured `Authorization` header value, shell environment dump, or raw provider credential into ProviderTrace, Failure Audit, stdout, stderr, generated logs, tests, or review packet.
- Tests and review packets may contain field names and harmless literals such as `Authorization` and `"Bearer "` because they are necessary to prove header construction. Secret checks must block real values, not those field names.
- Error messages may say the configured environment variable is missing but must not echo any value.

Live-call requirements:

- Live DeepSeek calls are disabled unless `--allow-live-api` is present.
- Automated tests must not perform network access.
- CI must not run the live smoke command.
- Live outputs must be written under `.tmp/g1e-deepseek-provider-smoke/` by default and must not be committed.

## File Structure

### Create

```text
src/werewolf_eval/deepseek_provider.py
tests/test_deepseek_provider.py
src/werewolf_eval/run_deepseek_provider_game.py
tests/test_deepseek_provider_game.py
```

### Modify

```text
src/werewolf_eval/provider_contract.py
src/werewolf_eval/source_labels.py
src/werewolf_eval/provider_agent.py
tests/test_source_labels.py
tests/test_fake_provider.py
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

Implementation branches must not modify this plan file unless a reviewer explicitly asks for a plan-only correction. This planning PR itself may modify only this plan file.

## Global Allowlist

Implementation branches may modify only these paths:

```text
src/werewolf_eval/provider_contract.py
src/werewolf_eval/source_labels.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/deepseek_provider.py
src/werewolf_eval/run_deepseek_provider_game.py
tests/test_source_labels.py
tests/test_fake_provider.py
tests/test_deepseek_provider.py
tests/test_deepseek_provider_game.py
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

No live smoke artifact path is in the allowlist. Files under `.tmp/g1e-deepseek-provider-smoke/` may be generated locally but must not be committed.

## Global Forbidden Scope

Do not modify:

```text
docs/ai-worklog/**
README.md
docs/ROADMAP.md
docs/TASKS.md
docs/PRODUCT_ONE_PAGER.md
docs/EVALUATION_RUBRIC.md
docs/harness/plans/**
docs/prs/**
docs/specs/**
docs/generated-context/**
docs/gold-game/**
docs/game-scripts/**
docs/semantic-labeling/**
docs/generated-games/**
docs/demo/**
src/werewolf_eval/game_engine.py
src/werewolf_eval/scoring.py
src/werewolf_eval/score_game.py
src/werewolf_eval/render_demo.py
src/werewolf_eval/log_bundle.py
src/werewolf_eval/failure_audit.py
src/werewolf_eval/validate_failure_audit.py
src/werewolf_eval/semantic_labels.py
scripts/dev/build_review_packet.py
scripts/context/build_plan_index.py
scripts/context/build_task_context.py
package.json
package-lock.json
pyproject.toml
requirements.txt
requirements-dev.txt
```

Do not add:

```text
provider SDK imports
OpenAI SDK dependency
requests / httpx / aiohttp dependency
CI live-call behavior
automatic live API execution
multi-game aggregation
real leaderboard ranking
human-vs-AI UI
random provider retries without a hard cap
fallback defaults that repair invalid provider output into valid actions
committed `.tmp` live outputs
committed API keys, tokens, captured Authorization header values, or environment dumps
```

## Task 1: Preserve provider source labels through ProviderAgent

**Files to modify:**

```text
src/werewolf_eval/provider_contract.py
src/werewolf_eval/source_labels.py
src/werewolf_eval/provider_agent.py
tests/test_source_labels.py
tests/test_fake_provider.py
```

**Test files to add/modify:**

```text
tests/test_source_labels.py
tests/test_fake_provider.py
```

- [ ] Add `[DeepSeek API output]` to the expected source-label set and assert generic labels remain rejected:

```python
self.assertNotIn("[provider output]", VALID_SOURCE_LABELS)
self.assertNotIn("[live provider output]", VALID_SOURCE_LABELS)
```

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels -v
```

Expected result before implementation:

```text
FAIL: test_expected_labels_present
```

- [ ] Add a `ProviderAgent` regression test with a test-local provider that returns `ProviderResponse(source_label="[DeepSeek API output]", raw_content=...)`.

Required assertion:

```python
self.assertEqual(action.source_label, "[DeepSeek API output]")
```

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_fake_provider.FakeProviderAdapterTests.test_provider_agent_preserves_provider_response_source_label -v
```

Expected result before implementation:

```text
FAIL
```

- [ ] Implement only these source-label changes:

```python
DEEPSEEK_PROVIDER_SOURCE_LABEL = "[DeepSeek API output]"
```

and in `ProviderAgent` successful return path:

```python
source_label=response.source_label,
```

Do not change parse-failure, invalid-action, invalid-target, timeout, or no-repair behavior.

Run after implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_fake_provider -v
```

Expected result:

```text
OK
```

Commit:

```bash
git add src/werewolf_eval/provider_contract.py src/werewolf_eval/source_labels.py src/werewolf_eval/provider_agent.py tests/test_source_labels.py tests/test_fake_provider.py
git commit -m "feat: preserve provider source labels"
```

Expected result:

```text
commit created
```

## Task 2: Add DeepSeek provider adapter with fake-transport tests

**Files to create:**

```text
src/werewolf_eval/deepseek_provider.py
tests/test_deepseek_provider.py
```

**Test files to add/modify:**

```text
tests/test_deepseek_provider.py
```

Add tests:

```python
class DeepSeekProviderTests(unittest.TestCase):
    def test_missing_api_key_refuses_before_transport_call(self): ...
    def test_builds_openai_compatible_json_request(self): ...
    def test_success_response_becomes_provider_response(self): ...
    def test_empty_content_is_provider_error(self): ...
    def test_http_error_does_not_expose_api_key(self): ...
    def test_request_budget_is_enforced(self): ...
    def test_response_trace_contains_no_authorization_value(self): ...
```

Use injected fake transport only. The fake transport must capture payload and headers in memory and return deterministic JSON:

```python
def fake_transport(url: str, headers: dict[str, str], payload: dict, timeout_seconds: int) -> dict:
    return {
        "choices": [{"message": {"content": "{\"action\":\"seer_check\",\"target\":\"p1\",\"reason_summary\":\"check p1\",\"decision_type\":\"inference_based\",\"confidence\":1.0}"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
```

Required assertions are intentionally allowed and must not be blocked by secret checks:

```python
self.assertEqual(captured["payload"]["model"], "deepseek-v4-flash")
self.assertEqual(captured["payload"]["response_format"], {"type": "json_object"})
self.assertEqual(captured["payload"]["stream"], False)
self.assertEqual(captured["payload"]["thinking"], {"type": "disabled"})
self.assertIn("Authorization", captured["headers"])
self.assertIn("Bearer ", captured["headers"]["Authorization"])
self.assertEqual(response.source_label, "[DeepSeek API output]")
self.assertEqual(response.token_usage["total_tokens"], 30)
```

Important: tests may contain the field name `Authorization` and literal `"Bearer "`, but must not contain a real token, a captured full header value, or environment dump.

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider -v
```

Expected result before implementation:

```text
FAILED due to missing werewolf_eval.deepseek_provider
```

Implement `src/werewolf_eval/deepseek_provider.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from werewolf_eval.provider_contract import ProviderRequest, ProviderResponse, DEEPSEEK_PROVIDER_SOURCE_LABEL

Transport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]

@dataclass(frozen=True)
class DeepSeekProviderConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: int = 30
    max_tokens: int = 256
    max_requests: int = 11

class DeepSeekProvider:
    def __init__(self, config: DeepSeekProviderConfig, transport: Transport | None = None) -> None: ...
    @property
    def requests(self) -> list[ProviderRequest]: ...
    @property
    def responses(self) -> list[ProviderResponse]: ...
    def respond(self, request: ProviderRequest) -> ProviderResponse: ...
```

Adapter requirements:

- Strip trailing slash from `base_url` and post to `{base_url}/chat/completions`.
- Use `urllib.request` for default transport.
- Tests must use only injected transport.
- Enforce `max_requests`; exception text includes `request budget exceeded` and does not contain the API key.
- Do not parse the action JSON inside the DeepSeek adapter; return raw content through `ProviderResponse.raw_content`.
- Return `ProviderResponse(provider_name="deepseek", source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL, ...)`.
- Store token usage from response `usage`, defaulting missing values to `0`.
- Never store headers or API key in `ProviderRequest`, `ProviderResponse`, stdout, or exceptions.

Run after implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider -v
```

Expected result:

```text
OK
```

Commit:

```bash
git add src/werewolf_eval/deepseek_provider.py tests/test_deepseek_provider.py
git commit -m "feat: add DeepSeek provider adapter"
```

Expected result:

```text
commit created
```

## Task 3: Add guarded DeepSeek single-game smoke CLI

**Files to create:**

```text
src/werewolf_eval/run_deepseek_provider_game.py
tests/test_deepseek_provider_game.py
```

**Test files to add/modify:**

```text
tests/test_deepseek_provider_game.py
```

Add tests:

```python
class DeepSeekProviderGameCliTests(unittest.TestCase):
    def test_cli_without_allow_live_api_exits_nonzero_and_writes_nothing(self): ...
    def test_cli_with_allow_live_but_missing_key_exits_nonzero_and_writes_nothing(self): ...
    def test_helper_with_fake_provider_factory_writes_valid_artifacts(self): ...
    def test_helper_failure_writes_failure_audit_but_no_valid_logs(self): ...
```

Expose this helper for non-live tests:

```python
def run_deepseek_game_with_provider_factory(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory,
) -> int:
    ...
```

Tests must use deterministic fake providers or fake provider factories and must not call DeepSeek.

Run before implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider_game -v
```

Expected result before implementation:

```text
FAILED due to missing werewolf_eval.run_deepseek_provider_game
```

CLI arguments:

```text
--game-id default g1e_deepseek_smoke
--out-dir default .tmp/g1e-deepseek-provider-smoke
--model default deepseek-v4-flash
--base-url default https://api.deepseek.com
--api-key-env default DEEPSEEK_API_KEY
--timeout-seconds default 30
--max-tokens-per-request default 256
--max-provider-requests default 11
--allow-live-api default false
```

No-live guard expected behavior:

```text
exit code: 1
stdout includes: live_api=disabled
stdout includes: game_log=not_written
stdout includes: decision_log=not_written
```

Missing-key expected behavior:

```text
exit code: 1
stderr includes: missing DEEPSEEK_API_KEY
stdout includes: game_log=not_written
stdout includes: decision_log=not_written
```

Provider success expected behavior:

```text
exit code: 0
writes: <out-dir>/game-log.json
writes: <out-dir>/decision-log.json
writes: <out-dir>/provider-trace.json
writes: <out-dir>/failure-audit.json
stdout includes: deepseek_provider_game_id=<game_id>
stdout includes: source_label=[DeepSeek API output]
stdout includes: provider_requests=11
stdout includes: provider_responses=11
stdout includes: provider_failures=0
stdout includes: game_log=written
stdout includes: decision_log=written
stdout includes: provider_trace=written
stdout includes: failure_audit=written
```

Provider failure expected behavior:

```text
exit code: 2
writes: <out-dir>/provider-trace.json
writes: <out-dir>/failure-audit.json
does not write: <out-dir>/game-log.json
does not write: <out-dir>/decision-log.json
stdout includes: provider_failures=1
stdout includes: game_log=not_written
stdout includes: decision_log=not_written
```

Implementation notes:

- Build DeepSeek-backed `ProviderAgent` instances for `p3`, `p4`, `p5`, `p6`, and `wolf_team`.
- Reuse `GameEngine.from_config(build_default_config(game_id=...), agents=..., wolf_agent=..., source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL)`.
- Collect provider `.requests` and `.responses` like `run_fake_provider_game.py`.
- Write JSON with `ensure_ascii=False`, `indent=2`, and trailing newline.
- Do not write artifacts outside `--out-dir`.
- Do not add generated live outputs to `docs/generated-games/` or `docs/demo/`.

Run after implementation:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider_game -v
```

Expected result:

```text
OK
```

No-live guard validation:

```bash
set +e
PYTHONPATH=src python -m werewolf_eval.run_deepseek_provider_game --game-id g1e_deepseek_guard --out-dir .tmp/g1e-deepseek-provider-smoke-guard
code=$?
set -e
echo "exit_code=$code"
test "$code" -eq 1
test ! -e .tmp/g1e-deepseek-provider-smoke-guard/game-log.json
test ! -e .tmp/g1e-deepseek-provider-smoke-guard/decision-log.json
```

Expected result:

```text
live_api=disabled
exit_code=1
```

Commit:

```bash
git add src/werewolf_eval/run_deepseek_provider_game.py tests/test_deepseek_provider_game.py
git commit -m "feat: add DeepSeek provider smoke CLI"
```

Expected result:

```text
commit created
```

## Task 4: Refresh tree and run validation

**Files to modify:**

```text
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

**Generated locally only:**

```text
.tmp/g1e-deepseek-provider-smoke/**
.tmp/g1e-deepseek-provider-smoke-guard/**
```

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md includes deepseek_provider.py, run_deepseek_provider_game.py, test_deepseek_provider.py, and test_deepseek_provider_game.py
```

Run targeted tests:

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_fake_provider tests.test_deepseek_provider tests.test_deepseek_provider_game -v
```

Expected result:

```text
OK
```

Run full tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected result:

```text
OK
```

Run compile check:

```bash
python -m compileall src/werewolf_eval scripts
```

Expected result:

```text
0 compile errors
```

Run no-live CLI guard:

```bash
set +e
PYTHONPATH=src python -m werewolf_eval.run_deepseek_provider_game --game-id g1e_deepseek_guard --out-dir .tmp/g1e-deepseek-provider-smoke-guard
code=$?
set -e
echo "exit_code=$code"
test "$code" -eq 1
test ! -e .tmp/g1e-deepseek-provider-smoke-guard/game-log.json
test ! -e .tmp/g1e-deepseek-provider-smoke-guard/decision-log.json
```

Expected result:

```text
live_api=disabled
exit_code=1
```

Manual live smoke, local only:

```bash
rm -rf .tmp/g1e-deepseek-provider-smoke
DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" PYTHONPATH=src python -m werewolf_eval.run_deepseek_provider_game \
  --allow-live-api \
  --game-id g1e_deepseek_smoke \
  --out-dir .tmp/g1e-deepseek-provider-smoke \
  --model deepseek-v4-flash \
  --max-provider-requests 11 \
  --max-tokens-per-request 256 \
  --timeout-seconds 30
```

Expected result for G1e completion:

```text
deepseek_provider_game_id=g1e_deepseek_smoke
source_label=[DeepSeek API output]
provider_requests=11
provider_responses=11
provider_failures=0
game_log=written
decision_log=written
provider_trace=written
failure_audit=written
```

If exit code is `2`, the failure path is safe only when these hold:

```text
provider_trace=written
failure_audit=written
game_log=not_written
decision_log=not_written
```

Exit `2` is not G1e completion. It is a blocking implementation or prompt-contract finding that must be fixed within the allowlist before claiming G1e completion.

Validate live smoke outputs when live smoke exits `0`:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log .tmp/g1e-deepseek-provider-smoke/game-log.json
```

Expected result includes:

```text
validated game_id=g1e_deepseek_smoke
source_label=[DeepSeek API output]
players=6
```

```bash
PYTHONPATH=src python -m werewolf_eval.validate_decision_log .tmp/g1e-deepseek-provider-smoke/decision-log.json .tmp/g1e-deepseek-provider-smoke/game-log.json
```

Expected result includes:

```text
game_id=g1e_deepseek_smoke
source_label=[DeepSeek API output]
```

Confirm no live artifacts are staged:

```bash
git status --short
```

Expected result:

```text
No `.tmp/` files are staged or tracked.
```

## Review Packet Requirements

After implementation, generate or prepare `.logs/review/latest/review-packet.md` for Codex A档. The packet must contain machine-generated evidence, not only prose.

Minimum required evidence:

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

It must also include:

```text
- exact base..head review range
- whether manual DeepSeek live smoke was run
- if live smoke was run: sanitized command, exit code, stdout summary, validator summaries
- if live smoke was not run: exact reason, such as missing key or operator did not authorize live call
- confirmation that no real API key, captured Authorization header value, or environment dump appears in tracked files or review packet
- confirmation that `.tmp/g1e-deepseek-provider-smoke/**` is not committed
```

Review packet key hunk excerpts must include:

```text
- `provider_agent.py` hunk proving `source_label=response.source_label`
- `deepseek_provider.py` hunk proving stdlib HTTP, JSON object response_format, thinking disabled, max_requests, and no SDK import
- `run_deepseek_provider_game.py` hunk proving `--allow-live-api` guard and `.tmp` output default
- `tests/test_deepseek_provider.py` hunk proving fake transport tests and no live network
- `tests/test_deepseek_provider_game.py` hunk proving no-live guard and failure audit behavior
```

Important: the review packet may contain the field name `Authorization`, the literal `"Bearer "`, or source-code hunks that construct a header from an env-provided key. That is allowed. The review packet must not contain a real token, a captured full header value from runtime, a shell environment dump, or the actual API key value.

## Required Review Checks

Changed-files allowlist check:

```bash
python - <<'PY'
import subprocess
import sys

allowed = {
    "src/werewolf_eval/provider_contract.py",
    "src/werewolf_eval/source_labels.py",
    "src/werewolf_eval/provider_agent.py",
    "src/werewolf_eval/deepseek_provider.py",
    "src/werewolf_eval/run_deepseek_provider_game.py",
    "tests/test_source_labels.py",
    "tests/test_fake_provider.py",
    "tests/test_deepseek_provider.py",
    "tests/test_deepseek_provider_game.py",
    ".oh-my-harness/tree.md",
    ".logs/review/latest/review-packet.md",
}
changed = set(subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines())
extra = sorted(changed - allowed)
print("changed_files=" + ",".join(sorted(changed)))
if extra:
    print("ALLOWLIST_CHECK=FAIL extra=" + ",".join(extra))
    sys.exit(1)
print("ALLOWLIST_CHECK=PASS")
PY
```

Expected result:

```text
ALLOWLIST_CHECK=PASS
```

Forbidden import/dependency check:

```bash
python - <<'PY'
from pathlib import Path
import subprocess
import sys

changed = subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines()
forbidden = ["import requests", "import httpx", "import aiohttp", "from openai", "import openai"]
violations = []
for name in changed:
    path = Path(name)
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in forbidden:
            if pattern in text:
                violations.append(f"{name}: {pattern}")
if violations:
    print("FORBIDDEN_IMPORT_CHECK=FAIL")
    for item in violations:
        print(item)
    sys.exit(1)
print("FORBIDDEN_IMPORT_CHECK=PASS")
PY
```

Expected result:

```text
FORBIDDEN_IMPORT_CHECK=PASS
```

Dependency diff check:

```bash
git diff -- package.json package-lock.json pyproject.toml requirements.txt requirements-dev.txt
```

Expected result:

```text
(no output)
```

Tracked-secret check:

```bash
python - <<'PY'
from pathlib import Path
import re
import subprocess
import sys

changed = subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines()

# Allowed everywhere: field names, source-code snippets, and harmless literals such as
# `Authorization`, `"Bearer "`, `f"Bearer {api_key}"`, and test assertions that inspect headers.
# Forbidden: real key-like values, captured full Authorization header values, env dumps, or committed .tmp outputs.
real_secret_patterns = [
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{15,}"),
    re.compile(r"Bearer\s+(?!\{)(?!<)(?!REDACTED)(?!redacted)(?!\$)([A-Za-z0-9._-]{32,})"),
    re.compile(r"DEEPSEEK_API_KEY\s*=\s*['\"]?(?!\$DEEPSEEK_API_KEY)(?!<redacted>)(?!REDACTED)([A-Za-z0-9._-]{16,})", re.IGNORECASE),
]
allowed_header_literals = [
    '"Bearer "',
    "'Bearer '",
    'f"Bearer {',
    "f'Bearer {",
]
violations = []
for name in changed:
    if name.startswith(".tmp/"):
        violations.append(f"{name}: committed live-smoke artifact path")
        continue
    path = Path(name)
    if not path.exists() or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in real_secret_patterns:
            if pattern.search(line):
                # Allow source/test literals that do not contain a concrete token value.
                if any(lit in line for lit in allowed_header_literals):
                    continue
                violations.append(f"{name}:{lineno}: possible real secret or captured header value")
if violations:
    print("TRACKED_SECRET_CHECK=FAIL")
    for item in violations:
        print(item)
    sys.exit(1)
print("TRACKED_SECRET_CHECK=PASS")
PY
```

Expected result:

```text
TRACKED_SECRET_CHECK=PASS
```

This check intentionally allows tests and review packets to contain `Authorization` and `"Bearer "` as field names or code literals. It blocks real token-shaped values, captured full runtime header values, environment dumps, and committed `.tmp` artifacts.

## Acceptance Criteria

Implementation acceptance:

```text
A1. Only allowlisted files changed, except uncommitted local `.tmp` files.
A2. `ProviderAgent` preserves provider response source labels.
A3. `[DeepSeek API output]` is accepted by source label validation; generic provider labels remain rejected.
A4. DeepSeek adapter uses stdlib HTTP only and adds no dependency or provider SDK.
A5. DeepSeek adapter sends JSON-output request shape and enforces `max_requests`.
A6. Secret check allows harmless `Authorization` / `"Bearer "` evidence but rejects real secrets, captured header values, env dumps, and `.tmp` artifacts.
A7. CLI refuses live calls without `--allow-live-api`.
A8. CLI refuses missing `DEEPSEEK_API_KEY` without writing valid logs.
A9. Automated tests do not perform network access.
A10. Provider parse/invalid/timeout/transport failures do not write valid Game Log or Decision Log.
A11. Full unittest discovery passes.
A12. Compile check passes.
A13. Review packet contains all required machine evidence and sanitized live-smoke status.
```

G1e milestone completion additionally requires:

```text
A14. Manual local DeepSeek smoke exits 0.
A15. Smoke output validates through `validate_game_log` and `validate_decision_log`.
A16. Smoke used no more than 11 provider requests and `max_tokens_per_request=256` unless the operator explicitly records a different budget in implementer risk notes.
```

If A1-A13 pass but A14-A16 are not run because the operator did not provide a key, the Implementation PR may be reviewed as `harness ready`, but `docs/TASKS.md` must not be changed to mark G1e completed in the same PR.

## Codex B档 Deep Review Risk Points

This plan may trigger B档 because it introduces a network-capable provider adapter boundary. Inspect only explicit hunks if A档 escalates.

Risk points:

```text
1. `deepseek_provider.py` contains network-capable code; verify stdlib-only, opt-in, budget-capped, and secret-safe behavior.
2. `run_deepseek_provider_game.py` can perform live API calls; verify `--allow-live-api` and missing-key guards cannot be bypassed.
3. `ProviderAgent` source-label propagation affects all providers; verify fake-provider outputs still keep `[deterministic fake provider output]`.
4. Adding `[DeepSeek API output]` broadens accepted provenance labels; verify no generic provider label is accepted.
5. Provider failures must not be repaired into valid Decision Log or Game Log actions.
6. Tests and review packet may contain `Authorization` and `"Bearer "`; verify they contain no real token or captured full header value.
7. Live smoke artifacts under `.tmp/` must not be committed.
8. Dependency manifests must not change.
9. Prompt/schema adjustment must remain inside DeepSeek adapter or CLI tests, not inside `game_engine.py`.
10. The PR must not update `docs/TASKS.md` or `docs/ROADMAP.md` to claim G1e completion unless manual DeepSeek smoke evidence is present.
```

## Final Verification Command Set

Run before requesting Codex review:

```bash
python -m compileall src/werewolf_eval scripts
PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_fake_provider tests.test_deepseek_provider tests.test_deepseek_provider_game -v
PYTHONPATH=src python -m unittest discover -s tests -v
set +e
PYTHONPATH=src python -m werewolf_eval.run_deepseek_provider_game --game-id g1e_deepseek_guard --out-dir .tmp/g1e-deepseek-provider-smoke-guard
code=$?
set -e
echo "exit_code=$code"
test "$code" -eq 1
git diff --check
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md
```

Expected final summary:

```text
compileall: PASS
unit targeted: OK
unit discover: OK
no-live guard: exit_code=1 and no valid logs written
git diff --check: no whitespace errors
review packet generated with required evidence
```
