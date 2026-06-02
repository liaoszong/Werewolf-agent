# G1e DeepSeek Provider Smoke Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a local, opt-in, budget-bounded DeepSeek API single-game smoke path that proves G1 can run one provider-backed game without CI live calls, multi-game leaderboard claims, or human-vs-AI UI scope creep.

**Architecture:** Build on the completed G1d provider contract harness instead of adding provider logic to the game engine. Add a DeepSeek provider adapter that implements the existing `respond(ProviderRequest) -> ProviderResponse` shape, make `ProviderAgent` preserve the provider response `source_label`, and add a guarded CLI that only performs live calls when the operator explicitly passes `--allow-live-api` and supplies `DEEPSEEK_API_KEY`. All automated tests must use fake transports or fake providers; the real DeepSeek smoke command is a manual local validation step and must write only to `.tmp/`.

**Tech Stack:** Python standard library only (`argparse`, `dataclasses`, `json`, `os`, `time`, `urllib.request`, `urllib.error`, `unittest`, `pathlib`, `typing`), existing G1d provider contract, existing game engine, existing validators, existing review-packet generator.

---

## Decision

The next development point is **G1e provider-backed single-game smoke**, narrowed to **DeepSeek API** because the operator will run the real AI test with DeepSeek.

This follows the current route:

- `docs/TASKS.md` marks G1e as `next_candidate` and describes it as a local, budget-controlled provider-backed game.
- `docs/ROADMAP.md` states that G1e follows G1d and must remain a single-game smoke, not CI live calls, multi-game leaderboard, or human-vs-AI UI.
- The repository already has G1d fake-provider files and generated artifacts, so this plan must not reimplement fake-provider contract work.

No Research PR is needed. Provider selection is already resolved by the user: DeepSeek API. This is a bound implementation slice.

## Bound Implementation PR

Future Implementation PR title:

```text
feat: add G1e DeepSeek provider smoke
```

Bound plan path:

```text
docs/harness/plans/2026-06-02--g1e-deepseek-provider-smoke-plan.md
```

Implementation PR description draft:

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
- No-live CLI guard exits non-zero and writes no artifacts.
- Manual DeepSeek smoke command is recorded in the review packet when run locally with `DEEPSEEK_API_KEY`.

## Boundaries

This PR does not add CI live calls, dependency changes, provider SDKs, multi-game leaderboard aggregation, human-vs-AI UI, or any repair path that turns invalid provider output into valid logs.
```

## Context Budget Gate for Claude Code

Do not read this full plan during implementation. Use the existing context tools.

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

Then read only:

```text
docs/generated-context/current-task.ctx.md
```

If the generated context is insufficient, read only the exact original plan line range referenced inside `current-task.ctx.md`.

## DeepSeek API Boundary

Use the OpenAI-compatible DeepSeek endpoint in the adapter, but do not add the OpenAI SDK or any other dependency.

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

- The system or user prompt must contain the word `json`.
- The prompt must include one exact example JSON object with these fields:
  - `action`
  - `target`
  - `reason_summary`
  - `decision_type`
  - `confidence`
- The prompt must include `allowed_actions` and `allowed_targets` from `ProviderRequest`.
- The prompt must instruct the model to choose only from those allowed values.
- The adapter must not insert fallback action defaults.

Secret requirements:

- Read only the environment variable named by `--api-key-env`, default `DEEPSEEK_API_KEY`.
- Never write the API key, Authorization header value, or environment dump into ProviderTrace, Failure Audit, stdout, stderr, generated logs, review packet, or tests.
- Error messages may say the named environment variable is missing, but must not echo any value.

Live-call requirements:

- Live DeepSeek calls are disabled unless `--allow-live-api` is present.
- Automated tests must not perform network access.
- CI must not run the live smoke command.
- Live outputs must be written under `.tmp/g1e-deepseek-provider-smoke/` by default and must not be committed.

## File Structure

### Create

```text
src/werewolf_eval/deepseek_provider.py
```

Responsible for:

- DeepSeek adapter config.
- HTTP request construction via `urllib.request`.
- Request/response recording through existing `ProviderRequest` / `ProviderResponse`.
- Budget and request-count checks.
- No SDK imports and no dependency changes.

```text
src/werewolf_eval/run_deepseek_provider_game.py
```

Responsible for:

- Manual local CLI for one DeepSeek-backed game.
- Guarding live calls behind `--allow-live-api`.
- Writing `.tmp` Game Log, Decision Log, Provider Trace, and Failure Audit.
- Refusing to write valid Game Log / Decision Log artifacts when provider output fails parse, validation, timeout, or budget checks.

```text
tests/test_deepseek_provider.py
```

Responsible for:

- Non-network DeepSeek adapter tests using fake transport callables.
- Payload shape, source label, token usage, missing API key, HTTP error, empty content, and secret-redaction checks.

```text
tests/test_deepseek_provider_game.py
```

Responsible for:

- CLI guard tests with no live calls.
- Helper-level smoke tests with fake providers or fake provider factories.
- Artifact policy checks that generated live outputs stay under `.tmp`.

### Modify

```text
src/werewolf_eval/provider_contract.py
```

Add exactly one exported constant:

```python
DEEPSEEK_PROVIDER_SOURCE_LABEL = "[DeepSeek API output]"
```

Do not change existing G1d dataclass fields unless a test in this plan explicitly requires it.

```text
src/werewolf_eval/source_labels.py
```

Add exactly one accepted label:

```python
"[DeepSeek API output]"
```

Do not remove or rename existing source labels.

```text
src/werewolf_eval/provider_agent.py
```

Change the valid action return path so `AgentAction.source_label` comes from `response.source_label`, not the fake-provider constant.

Required final behavior:

```python
return AgentAction(
    actor=actor,
    action=action_name,
    target=target,
    phase=phase,
    round=round_num,
    reason_summary=reason_summary,
    decision_type=decision_type,
    confidence=confidence,
    source_label=response.source_label,
)
```

Keep the no-repair invariant: parse failure, invalid action, invalid target, timeout, and provider transport failure must raise `ProviderActionError` or fail the CLI without writing valid logs.

```text
tests/test_source_labels.py
```

Update the exact expected set to include `[DeepSeek API output]`.

```text
tests/test_fake_provider.py
```

Add a regression assertion that existing fake-provider actions still carry `[deterministic fake provider output]` after `ProviderAgent` starts preserving provider labels.

```text
.oh-my-harness/tree.md
```

Refresh after new files are created.

```text
.logs/review/latest/review-packet.md
```

Generate after implementation for Codex A档 review. Do not commit this file unless the repository currently tracks it as part of the review workflow. If it is untracked locally, attach or paste the content in the PR review handoff instead.

## Global Allowlist

The implementation branch may modify only these paths:

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
committed API keys, tokens, Authorization header values, or environment dumps
```

## Task 1: Preserve provider source labels through ProviderAgent

**Files:**

- Modify: `src/werewolf_eval/provider_contract.py`
- Modify: `src/werewolf_eval/source_labels.py`
- Modify: `src/werewolf_eval/provider_agent.py`
- Modify: `tests/test_source_labels.py`
- Modify: `tests/test_fake_provider.py`

- [ ] **Step 1: Add failing source-label tests**

In `tests/test_source_labels.py`, update `expected` to include:

```python
"[DeepSeek API output]"
```

Also add:

```python
self.assertNotIn("[provider output]", VALID_SOURCE_LABELS)
self.assertNotIn("[live provider output]", VALID_SOURCE_LABELS)
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels -v
```

Expected result before implementation:

```text
FAIL: test_expected_labels_present
```

The failure must be caused only by the missing DeepSeek source label.

- [ ] **Step 2: Add failing ProviderAgent source-label regression**

In `tests/test_fake_provider.py`, add a test-local provider class that returns a `ProviderResponse` with `source_label="[DeepSeek API output]"`, then pass it through `ProviderAgent`.

Required assertion:

```python
self.assertEqual(action.source_label, "[DeepSeek API output]")
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_fake_provider.FakeProviderAdapterTests.test_provider_agent_preserves_provider_response_source_label -v
```

Expected result before implementation:

```text
FAIL
```

The failure must show that `ProviderAgent` still returns `[deterministic fake provider output]` instead of preserving the provider response label.

- [ ] **Step 3: Implement the source-label changes**

In `src/werewolf_eval/provider_contract.py`, add:

```python
DEEPSEEK_PROVIDER_SOURCE_LABEL = "[DeepSeek API output]"
```

In `src/werewolf_eval/source_labels.py`, add the same string to `VALID_SOURCE_LABELS`.

In `src/werewolf_eval/provider_agent.py`, change only the successful `AgentAction` return path from the fake-provider constant to:

```python
source_label=response.source_label,
```

Do not change parse, invalid-action, invalid-target, timeout, or no-repair behavior in this task.

- [ ] **Step 4: Validate Task 1**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_fake_provider -v
```

Expected result:

```text
OK
```

- [ ] **Step 5: Commit Task 1**

```bash
git add src/werewolf_eval/provider_contract.py src/werewolf_eval/source_labels.py src/werewolf_eval/provider_agent.py tests/test_source_labels.py tests/test_fake_provider.py
git commit -m "feat: preserve provider source labels"
```

Expected result:

```text
[branch] feat: preserve provider source labels
```

## Task 2: Add DeepSeek provider adapter with fake-transport tests

**Files:**

- Create: `src/werewolf_eval/deepseek_provider.py`
- Create: `tests/test_deepseek_provider.py`

- [ ] **Step 1: Add failing adapter tests**

Create `tests/test_deepseek_provider.py` with these test cases:

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

Use a fake transport callable with this signature:

```python
def fake_transport(url: str, headers: dict[str, str], payload: dict, timeout_seconds: int) -> dict:
    return {
        "choices": [{"message": {"content": "{\"action\":\"seer_check\",\"target\":\"p1\",\"reason_summary\":\"check p1\",\"decision_type\":\"inference_based\",\"confidence\":1.0}"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
```

Required assertions:

```python
self.assertEqual(captured["payload"]["model"], "deepseek-v4-flash")
self.assertEqual(captured["payload"]["response_format"], {"type": "json_object"})
self.assertEqual(captured["payload"]["stream"], False)
self.assertEqual(captured["payload"]["thinking"], {"type": "disabled"})
self.assertIn("Bearer ", captured["headers"]["Authorization"])
self.assertEqual(response.source_label, "[DeepSeek API output]")
self.assertEqual(response.token_usage["total_tokens"], 30)
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider -v
```

Expected result before implementation:

```text
FAILED
```

The failure must be caused by the missing `werewolf_eval.deepseek_provider` module.

- [ ] **Step 2: Implement `src/werewolf_eval/deepseek_provider.py`**

Public API:

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

Implementation requirements:

- Strip trailing slash from `base_url` and post to `{base_url}/chat/completions`.
- Use `urllib.request` for the default transport.
- Keep the injected `transport` path as the only path used by tests.
- Increment request count only after validating the request can be sent.
- Enforce `max_requests`; when exceeded, raise an exception whose message contains `request budget exceeded` and does not contain the API key.
- Parse `choices[0].message.content` as the raw provider content string; do not parse action JSON inside the DeepSeek adapter.
- Return `ProviderResponse` with `provider_name="deepseek"` and `source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL`.
- Store `token_usage` from response `usage`, defaulting missing token fields to `0`.
- Never store headers or API key in `ProviderRequest`, `ProviderResponse`, stdout, or exceptions.

- [ ] **Step 3: Validate Task 2**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider -v
```

Expected result:

```text
OK
```

- [ ] **Step 4: Commit Task 2**

```bash
git add src/werewolf_eval/deepseek_provider.py tests/test_deepseek_provider.py
git commit -m "feat: add DeepSeek provider adapter"
```

Expected result:

```text
[branch] feat: add DeepSeek provider adapter
```

## Task 3: Add guarded DeepSeek single-game smoke CLI

**Files:**

- Create: `src/werewolf_eval/run_deepseek_provider_game.py`
- Create: `tests/test_deepseek_provider_game.py`

- [ ] **Step 1: Add failing CLI guard tests**

Create `tests/test_deepseek_provider_game.py` with these cases:

```python
class DeepSeekProviderGameCliTests(unittest.TestCase):
    def test_cli_without_allow_live_api_exits_nonzero_and_writes_nothing(self): ...
    def test_cli_with_allow_live_but_missing_key_exits_nonzero_and_writes_nothing(self): ...
    def test_helper_with_fake_provider_factory_writes_valid_artifacts(self): ...
    def test_helper_failure_writes_failure_audit_but_no_valid_logs(self): ...
```

The tests must call the CLI without real network access. For the helper tests, expose a pure helper from the CLI module:

```python
def run_deepseek_game_with_provider_factory(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory,
) -> int:
    ...
```

Use `DeterministicFakeProvider` or a local provider factory in tests to simulate the provider responses; do not call DeepSeek from tests.

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider_game -v
```

Expected result before implementation:

```text
FAILED
```

The failure must be caused by the missing `werewolf_eval.run_deepseek_provider_game` module.

- [ ] **Step 2: Implement `run_deepseek_provider_game.py` CLI**

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

Behavior when `--allow-live-api` is absent:

```text
exit code: 1
stdout includes: live_api=disabled
stdout includes: game_log=not_written
stdout includes: decision_log=not_written
```

Behavior when `--allow-live-api` is present but the API key env var is missing:

```text
exit code: 1
stderr includes: missing DEEPSEEK_API_KEY
stdout includes: game_log=not_written
stdout includes: decision_log=not_written
```

Behavior on provider success:

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

Behavior on provider failure:

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
- Collect trace from provider `.requests` and `.responses` the same way `run_fake_provider_game.py` does.
- Write JSON with `ensure_ascii=False`, `indent=2`, and a trailing newline.
- Do not write any artifact outside `--out-dir`.
- Do not add generated live outputs to `docs/generated-games/` or `docs/demo/` in this task.

- [ ] **Step 3: Validate Task 3**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_deepseek_provider_game -v
```

Expected result:

```text
OK
```

Run the no-live guard:

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

- [ ] **Step 4: Commit Task 3**

```bash
git add src/werewolf_eval/run_deepseek_provider_game.py tests/test_deepseek_provider_game.py
git commit -m "feat: add DeepSeek provider smoke CLI"
```

Expected result:

```text
[branch] feat: add DeepSeek provider smoke CLI
```

## Task 4: Refresh tree and run validation

**Files:**

- Modify: `.oh-my-harness/tree.md`
- Generated locally only: `.tmp/g1e-deepseek-provider-smoke/**`
- Generated locally only: `.logs/review/latest/review-packet.md`

- [ ] **Step 1: Refresh tree**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md refreshed
```

If the hook prints a different success message, record the exact output in the review packet and verify that `.oh-my-harness/tree.md` contains these filenames:

```text
deepseek_provider.py
run_deepseek_provider_game.py
test_deepseek_provider.py
test_deepseek_provider_game.py
```

- [ ] **Step 2: Run targeted tests**

```bash
PYTHONPATH=src python -m unittest tests.test_source_labels tests.test_fake_provider tests.test_deepseek_provider tests.test_deepseek_provider_game -v
```

Expected result:

```text
OK
```

- [ ] **Step 3: Run full tests**

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected result:

```text
OK
```

- [ ] **Step 4: Run compile check**

```bash
python -m compileall src/werewolf_eval scripts
```

Expected result:

```text
0 compile errors
```

- [ ] **Step 5: Run no-live CLI guard**

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

- [ ] **Step 6: Run manual DeepSeek live smoke only when explicitly allowed locally**

This command is not for CI. Run it only in a local shell where the operator has set a valid key.

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

If the command exits `2`, the failure path is safe only when these conditions hold:

```text
provider_trace=written
failure_audit=written
game_log=not_written
decision_log=not_written
```

Exit `2` is not G1e smoke completion. It is a blocking implementation or prompt-contract finding that must be fixed inside this plan's allowlist before claiming G1e completion.

- [ ] **Step 7: Validate live smoke outputs when Step 6 exits 0**

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

- [ ] **Step 8: Confirm no live artifacts are staged**

```bash
git status --short
```

Expected result:

```text
No `.tmp/` files are staged or tracked.
```

- [ ] **Step 9: Commit Task 4**

```bash
git add .oh-my-harness/tree.md
git commit -m "chore: refresh tree for DeepSeek provider smoke"
```

Expected result:

```text
[branch] chore: refresh tree for DeepSeek provider smoke
```

If `.oh-my-harness/tree.md` is unchanged after refresh, do not create an empty commit. Record `tree refresh: no changes` in the review packet.

## Review Packet Requirements

After implementation, generate or prepare `.logs/review/latest/review-packet.md` for Codex A档. The packet must include machine-generated evidence, not only prose.

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

The review packet must also include:

```text
- exact base..head review range
- whether manual DeepSeek live smoke was run
- if live smoke was run: sanitized command, exit code, stdout summary, validator summaries
- if live smoke was not run: exact reason, such as missing key or operator did not authorize live call
- confirmation that no API key, Authorization value, or environment dump appears in tracked files or review packet
- confirmation that `.tmp/g1e-deepseek-provider-smoke/**` is not committed
```

Required allowlist check command:

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

Required forbidden-pattern checks:

```bash
python - <<'PY'
from pathlib import Path
import subprocess
import sys

changed = subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines()
tracked_text = []
for name in changed:
    path = Path(name)
    if path.exists() and path.is_file():
        tracked_text.append((name, path.read_text(encoding="utf-8", errors="replace")))

forbidden_imports = ["import requests", "import httpx", "import aiohttp", "from openai", "import openai"]
forbidden_secret_literals = ["sk-", "Bearer ${", "Authorization: Bearer "]
violations = []
for name, text in tracked_text:
    for pattern in forbidden_imports + forbidden_secret_literals:
        if pattern in text:
            violations.append(f"{name}: {pattern}")

if violations:
    print("FORBIDDEN_PATTERN_CHECK=FAIL")
    for item in violations:
        print(item)
    sys.exit(1)
print("FORBIDDEN_PATTERN_CHECK=PASS")
PY
```

Expected result:

```text
FORBIDDEN_PATTERN_CHECK=PASS
```

Required dependency/import diff check:

```bash
git diff -- package.json package-lock.json pyproject.toml requirements.txt requirements-dev.txt
```

Expected result:

```text
(no output)
```

Required tracked-secret check:

```bash
python - <<'PY'
from pathlib import Path
import subprocess
import sys

changed = subprocess.check_output(["git", "diff", "--name-only", "main...HEAD"], text=True).splitlines()
secret_patterns = ["DEEPSEEK_API_KEY=", "api_key=", "Authorization", "Bearer "]
violations = []
for name in changed:
    path = Path(name)
    if not path.exists() or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for pattern in secret_patterns:
        if pattern in text and name not in {"src/werewolf_eval/deepseek_provider.py", "src/werewolf_eval/run_deepseek_provider_game.py", "docs/harness/plans/2026-06-02--g1e-deepseek-provider-smoke-plan.md"}:
            violations.append(f"{name}: {pattern}")
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

Key hunk excerpts must include:

```text
- `provider_agent.py` hunk proving `source_label=response.source_label`
- `deepseek_provider.py` hunk proving stdlib HTTP, response_format json_object, thinking disabled, max_requests, and no SDK import
- `run_deepseek_provider_game.py` hunk proving `--allow-live-api` guard and `.tmp` output default
- `tests/test_deepseek_provider.py` hunk proving fake transport tests and no live network
- `tests/test_deepseek_provider_game.py` hunk proving no-live guard and failure audit behavior
```

Acceptance checklist with evidence pointers must include:

```text
| Acceptance | Evidence | Status |
|---|---|---|
| A1: DeepSeek source label is accepted and propagated | `tests.test_source_labels`; `tests.test_fake_provider...preserves_provider_response_source_label`; key hunk in `provider_agent.py` | PASS/FAIL |
| A2: DeepSeek adapter builds OpenAI-compatible JSON request without SDK dependency | `tests.test_deepseek_provider`; key hunk in `deepseek_provider.py`; dependency diff check | PASS/FAIL |
| A3: live API cannot run accidentally | no-live CLI guard command; `tests.test_deepseek_provider_game` | PASS/FAIL |
| A4: provider failures do not write valid logs | `tests.test_deepseek_provider_game`; failure-path stdout if live failure occurred | PASS/FAIL |
| A5: manual DeepSeek single-game smoke completed or is explicitly not run | live command output and validators, or explicit not-run reason | PASS/FAIL/MANUAL_NOT_RUN |
| A6: no secrets or live `.tmp` artifacts are committed | tracked-secret check; `git status --short`; allowlist check | PASS/FAIL |
```

Implementer risk notes must mention:

```text
- whether DeepSeek live smoke was run
- exact model used, default `deepseek-v4-flash`
- total provider request count
- any provider failure kind observed
- whether prompt/schema had to be adjusted to achieve valid actions
- whether review packet contains any intended `Authorization` code hunk and why no secret value is present
```

## Acceptance Criteria

The implementation is accepted only when all of these are true:

```text
A1. Only allowlisted files changed, except locally generated `.tmp` files that are not committed.
A2. `ProviderAgent` preserves provider response source labels.
A3. `[DeepSeek API output]` is accepted by source label validation.
A4. DeepSeek adapter uses stdlib HTTP only and adds no dependency or provider SDK.
A5. DeepSeek adapter sends JSON-output request shape and enforces `max_requests`.
A6. CLI refuses live calls without `--allow-live-api`.
A7. CLI refuses missing `DEEPSEEK_API_KEY` without writing valid logs.
A8. Automated tests do not perform network access.
A9. Provider parse/invalid/timeout/transport failures do not write valid Game Log or Decision Log.
A10. Full unittest discovery passes.
A11. Compile check passes.
A12. Review packet contains all required machine evidence and sanitized live-smoke status.
```

G1e milestone completion additionally requires:

```text
A13. Manual local DeepSeek smoke exits 0.
A14. Smoke output validates through `validate_game_log` and `validate_decision_log`.
A15. Smoke used no more than 11 provider requests and `max_tokens_per_request=256` unless the operator explicitly records a different budget in implementer risk notes.
```

If A1-A12 pass but A13-A15 are not run because the operator did not provide a key, the Implementation PR may be reviewed as `harness ready`, but `docs/TASKS.md` must not be changed to mark G1e completed in the same PR.

## Codex B档 Deep Review Risk Points

This plan can trigger B档 because it intentionally introduces a live-provider adapter boundary. Codex should inspect only the explicit hunks if A档 needs escalation.

Risk points:

```text
1. `deepseek_provider.py` contains network-capable code; verify it is stdlib-only, opt-in, budget-capped, and secret-safe.
2. `run_deepseek_provider_game.py` can perform live API calls; verify `--allow-live-api` and missing-key guards cannot be bypassed.
3. `ProviderAgent` source-label propagation affects all providers; verify fake-provider outputs still keep `[deterministic fake provider output]`.
4. Adding `[DeepSeek API output]` broadens accepted provenance labels; verify no generic provider label is accepted.
5. Provider failures must not be repaired into valid Decision Log or Game Log actions.
6. Review packet may contain intentional `Authorization` code hunk; verify it never contains a real key or captured header value.
7. Live smoke artifacts under `.tmp/` must not be committed.
8. Dependency manifests must not change.
9. Any prompt/schema adjustment must remain inside DeepSeek adapter or CLI tests, not inside `game_engine.py`.
10. The PR must not update `docs/TASKS.md` or `docs/ROADMAP.md` to claim G1e completion unless the manual DeepSeek smoke evidence is present.
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
