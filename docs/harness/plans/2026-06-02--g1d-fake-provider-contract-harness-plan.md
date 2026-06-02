# G1d Fake Provider Contract Harness Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** 建立一个完全离线、确定性、可审查的 fake-provider contract harness，让 G1d 能验证 provider-shaped request / response / parse / failure 边界，同时继续禁止 live provider、network、secret、SDK 和依赖变更。

**Architecture:** 新增 provider contract / fake provider / provider agent adapter 三层：contract 只定义可序列化请求、响应、trace 和 failure record；fake provider 只从本地 deterministic script 返回 provider-shaped JSON；provider agent adapter 把 provider response 转换成现有 `AgentAction`，并在 parse failure / invalid action / timeout 时产出不可修复的 failure evidence。`GameEngine` 只做最小注入点，使默认 mock 路径保持不变，同时允许 CLI 使用 fake-provider agents 跑一局确定性 harness game，并通过现有 validators / scoring / render pipeline 生成机器证据。

**Tech Stack:** Python stdlib only (`dataclasses`, `json`, `argparse`, `unittest`, `pathlib`, `typing`), existing Werewolf-agent validators, existing scoring/render CLI, existing review-packet generator.

---

## Decision

The next development point is **G1d Fake Provider Contract Harness**.

Reasoning:

- `docs/ROADMAP.md` defines G1d as provider adapter research / fake-provider contract and places it after G1c.
- The repository already contains the pre-G1d evaluation trust hardening plan and its runtime artifacts on `main`; the next step should not repeat Game / Decision / Consensus / Failure Audit trust hardening.
- The highest-value next slice is the non-live half of G1d: provider-shaped request/response contracts and a deterministic fake provider harness that proves the action loop boundary without spending API budget.
- This plan intentionally does not implement live API calls, provider SDKs, secrets, env handling, CI live calls, or provider-backed smoke. Those remain outside G1d fake-provider contract harness and belong only after this contract is stable.

No Research PR is required for this narrowed implementation slice because the task is not provider selection or live integration. It is a deterministic contract harness with explicit forbidden scope.

## Context Budget Gate for Claude Code

Do not read this full plan during implementation. Use the context workflow below.

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-06-02--g1d-fake-provider-contract-harness-plan.md
```

```bash
python - <<'PY'
import json
from pathlib import Path

plan = Path("docs/harness/plans/2026-06-02--g1d-fake-provider-contract-harness-plan.md")
index_path = Path("docs/generated-context") / f"{plan.stem}.index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))

for task in index["tasks"]:
    print(f"{task['id']}: {task['title']} lines={task['line_start']}-{task['line_end']}")
PY
```

For each task, generate minimal task context before editing:

```bash
python scripts/context/build_task_context.py docs/generated-context/2026-06-02--g1d-fake-provider-contract-harness-plan.index.json <TASK_ID>
```

Read only:

```text
docs/generated-context/current-task.ctx.md
```

If that context is insufficient, read only the exact `Original plan lines` listed inside `current-task.ctx.md`.

## File Structure

### Create

- `src/werewolf_eval/provider_contract.py`
  - Owns deterministic provider request/response/failure/trace dataclasses and JSON conversion helpers.
- `src/werewolf_eval/fake_provider.py`
  - Owns a deterministic offline provider that returns provider-shaped raw JSON from a local script.
- `src/werewolf_eval/provider_agent.py`
  - Owns the adapter that converts provider responses into existing `AgentAction` values and converts provider failures into audit-safe failure records.
- `src/werewolf_eval/run_fake_provider_game.py`
  - CLI harness that runs one fake-provider-driven game, writes Game Log / Decision Log / provider trace, and refuses to write forged valid logs on provider failure.
- `tests/test_provider_contract.py`
  - Unit tests for contract serialization, source label, request shape, trace shape, and failure record shape.
- `tests/test_fake_provider.py`
  - Unit tests for deterministic fake responses, provider response parsing, invalid target rejection, parse failure rejection, timeout failure mapping, and no-repair invariant.
- `tests/test_fake_provider_game.py`
  - CLI and generated-artifact tests for the G1d fake provider harness.
- `docs/generated-games/g1d-fake-provider-game-log.json`
  - Generated deterministic Game Log from fake-provider harness.
- `docs/generated-games/g1d-fake-provider-decision-log.json`
  - Generated deterministic Decision Log from fake-provider harness.
- `docs/generated-games/g1d-fake-provider-provider-trace.json`
  - Machine-readable provider request/response trace. It must contain no secrets, no env values, no URLs, and no auth material.
- `docs/generated-games/g1d-fake-provider-failure-audit.example.json`
  - Deterministic failure-mode example proving provider parse/invalid/timeout failures are audited and not repaired into valid actions.
- `docs/generated-games/g1d-fake-provider-score-log.json`
  - Score Log generated from the fake-provider Game Log + Decision Log.
- `docs/generated-games/g1d-fake-provider-metrics-summary.json`
  - Metrics Summary generated from the fake-provider Game Log + Decision Log.
- `docs/demo/phase3-g1d-fake-provider-runtime-demo.html`
  - Runtime demo generated from the fake-provider artifacts.

### Modify

- `src/werewolf_eval/source_labels.py`
  - Add exactly one new accepted label: `[deterministic fake provider output]`.
- `src/werewolf_eval/game_engine.py`
  - Add dependency injection for per-player agent drivers, wolf-team driver, and output `source_label`, while preserving existing default mock behavior and existing G1b/G1c outputs.
- `tests/test_source_labels.py`
  - Assert the new source label is present and unknown provider labels remain rejected.
- `tests/test_game_engine.py`
  - Add regression tests proving default mock outputs are unchanged and fake-provider injected outputs use `[deterministic fake provider output]`.
- `.oh-my-harness/tree.md`
  - Refresh through `node .codex/hooks/tree.mjs --force` after new files are created.
- `.logs/review/latest/review-packet.md`
  - Generate after implementation for Codex A档 review.

## Allowlist

The implementation branch may modify only these paths:

```text
src/werewolf_eval/source_labels.py
src/werewolf_eval/game_engine.py
src/werewolf_eval/provider_contract.py
src/werewolf_eval/fake_provider.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/run_fake_provider_game.py
tests/test_source_labels.py
tests/test_game_engine.py
tests/test_provider_contract.py
tests/test_fake_provider.py
tests/test_fake_provider_game.py
docs/generated-games/g1d-fake-provider-game-log.json
docs/generated-games/g1d-fake-provider-decision-log.json
docs/generated-games/g1d-fake-provider-provider-trace.json
docs/generated-games/g1d-fake-provider-failure-audit.example.json
docs/generated-games/g1d-fake-provider-score-log.json
docs/generated-games/g1d-fake-provider-metrics-summary.json
docs/demo/phase3-g1d-fake-provider-runtime-demo.html
.oh-my-harness/tree.md
.logs/review/latest/review-packet.md
```

## Forbidden Scope

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
docs/demo/phase1-gold-demo.html
docs/demo/phase2-runtime-demo.html
docs/demo/phase2-s5-runtime-demo.html
docs/demo/phase3-g1-scripted-runtime-demo.html
docs/demo/phase3-g1b-mock-agent-runtime-demo.html
docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
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

- live provider calls
- HTTP client code
- provider SDK imports
- API key, token, secret, or environment-variable handling
- network access
- CI live-call behavior
- new dependencies
- random or stochastic gameplay
- real multi-game leaderboard aggregation
- human-vs-AI UI
- repair behavior that converts invalid, timeout, or parse-failure provider output into valid Decision Log / Consensus Log actions
- broad refactors unrelated to this plan

## Provider Contract Shape

`provider_contract.py` must expose these public values:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FAKE_PROVIDER_SOURCE_LABEL = "[deterministic fake provider output]"

@dataclass(frozen=True)
class ProviderRequest:
    request_id: str
    game_id: str
    actor: str
    phase: str
    round: int
    observation: dict[str, Any]
    allowed_actions: list[str]
    allowed_targets: list[str]
    response_format_version: str = "g1d-action-v1"

@dataclass(frozen=True)
class ProviderResponse:
    request_id: str
    provider_name: str
    source_label: str
    raw_content: str
    latency_ms: int
    token_usage: dict[str, int]

@dataclass(frozen=True)
class ProviderFailure:
    request_id: str
    game_id: str
    round: int
    phase: str
    actor: str
    kind: str
    reason: str
    target: str | None = None
    repaired_to_valid_action: bool = False

@dataclass(frozen=True)
class ProviderTrace:
    game_id: str
    provider_name: str
    source_label: str
    requests: list[ProviderRequest]
    responses: list[ProviderResponse]
    failures: list[ProviderFailure]
```

JSON helpers must convert dataclasses into plain JSON-safe dicts without embedding secrets, env values, URLs, auth headers, prompt chain-of-thought, or raw stack traces.

## Task 0: Preflight Context and Existing Behavior Check

**Files:**
- Create: none
- Modify: none
- Test: none

- [ ] **Step 0.1: Generate context for this plan**

Run:

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-06-02--g1d-fake-provider-contract-harness-plan.md
python scripts/context/build_task_context.py docs/generated-context/2026-06-02--g1d-fake-provider-contract-harness-plan.index.json task-0
```

Expected result:

```text
current-task.ctx.md exists and references this plan path
```

- [ ] **Step 0.2: Run baseline validation before editing**

Run:

```bash
python scripts/dev/validate_brief.py
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests -q
git diff --check
```

Expected result:

```text
validate_brief.py: ok: true
unittest: OK
compileall: exit code 0
git diff --check: exit code 0
```

If baseline fails before edits, stop and report the exact failing command and short summary.

## Task 1: Source Label and Provider Contract

**Files:**
- Create: `src/werewolf_eval/provider_contract.py`
- Modify: `src/werewolf_eval/source_labels.py`
- Test: `tests/test_provider_contract.py`, `tests/test_source_labels.py`

- [ ] **Step 1.1: Add failing contract tests**

Create `tests/test_provider_contract.py` with tests equivalent to:

```python
from __future__ import annotations

import json
import unittest

from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTrace,
    provider_failure_to_dict,
    provider_request_to_dict,
    provider_response_to_dict,
    provider_trace_to_dict,
)
from werewolf_eval.source_labels import VALID_SOURCE_LABELS


class ProviderContractTests(unittest.TestCase):
    def test_fake_provider_source_label_is_registered(self) -> None:
        self.assertEqual(FAKE_PROVIDER_SOURCE_LABEL, "[deterministic fake provider output]")
        self.assertIn(FAKE_PROVIDER_SOURCE_LABEL, VALID_SOURCE_LABELS)

    def test_request_response_failure_trace_are_json_safe(self) -> None:
        request = ProviderRequest(
            request_id="g1d_fake_provider_r01_p3",
            game_id="g1d_fake_provider",
            actor="p3",
            phase="night",
            round=1,
            observation={"player_id": "p3", "private_event_ids": []},
            allowed_actions=["seer_check"],
            allowed_targets=["p1", "p2"],
        )
        response = ProviderResponse(
            request_id=request.request_id,
            provider_name="deterministic_fake_provider",
            source_label=FAKE_PROVIDER_SOURCE_LABEL,
            raw_content='{"action":"seer_check","target":"p1","reason_summary":"p3 checks p1","decision_type":"inference_based","confidence":1.0}',
            latency_ms=0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
        failure = ProviderFailure(
            request_id="g1d_fake_provider_r01_p4",
            game_id="g1d_fake_provider",
            round=1,
            phase="night",
            actor="p4",
            kind="parse_failure",
            reason="provider response was not valid JSON",
        )
        trace = ProviderTrace(
            game_id="g1d_fake_provider",
            provider_name="deterministic_fake_provider",
            source_label=FAKE_PROVIDER_SOURCE_LABEL,
            requests=[request],
            responses=[response],
            failures=[failure],
        )

        payload = provider_trace_to_dict(trace)
        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertIn("g1d_fake_provider", encoded)
        self.assertNotIn("api_key", encoded.lower())
        self.assertNotIn("authorization", encoded.lower())
        self.assertNotIn("http://", encoded.lower())
        self.assertNotIn("https://", encoded.lower())
        self.assertFalse(provider_failure_to_dict(failure)["repaired_to_valid_action"])
        self.assertEqual(provider_request_to_dict(request)["response_format_version"], "g1d-action-v1")
        self.assertEqual(provider_response_to_dict(response)["source_label"], FAKE_PROVIDER_SOURCE_LABEL)
```

Modify `tests/test_source_labels.py` so the expected set includes `[deterministic fake provider output]` and still rejects unknown labels.

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_provider_contract tests.test_source_labels -v
```

Expected result before implementation:

```text
FAILED or ERROR because werewolf_eval.provider_contract does not exist or the fake-provider source label is not registered
```

- [ ] **Step 1.2: Implement provider contract and source label**

Create `src/werewolf_eval/provider_contract.py` using the public shapes listed in `Provider Contract Shape`.

Update `src/werewolf_eval/source_labels.py` so `VALID_SOURCE_LABELS` is exactly:

```python
VALID_SOURCE_LABELS = {
    "[人工 gold sample]",
    "[AI 生成]",
    "[scripted deterministic output]",
    "[deterministic mock agent output]",
    "[deterministic fake provider output]",
}
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_provider_contract tests.test_source_labels -v
```

Expected result after implementation:

```text
OK
```

## Task 2: Fake Provider and Provider Agent Adapter

**Files:**
- Create: `src/werewolf_eval/fake_provider.py`, `src/werewolf_eval/provider_agent.py`
- Modify: none
- Test: `tests/test_fake_provider.py`

- [ ] **Step 2.1: Add failing fake-provider adapter tests**

Create `tests/test_fake_provider.py` with tests that prove all of these behaviors:

```text
1. DeterministicFakeProvider returns the same ProviderResponse for the same ProviderRequest.
2. ProviderAgent converts valid provider JSON into AgentAction.
3. Invalid target is rejected before an AgentAction is returned.
4. Non-JSON raw_content becomes ProviderFailure(kind="parse_failure") with repaired_to_valid_action=false.
5. Simulated timeout becomes ProviderFailure(kind="timeout") with repaired_to_valid_action=false.
6. The adapter output contains no network URL, env value, API key, or provider SDK reference.
```

Use concrete tests equivalent to:

```python
class FakeProviderAdapterTests(unittest.TestCase):
    def test_valid_response_becomes_agent_action(self) -> None:
        agent = build_default_fake_provider_agent("p3")
        action = agent.decide({
            "game_id": "g1d_fake_provider",
            "player_id": "p3",
            "role": "seer",
            "team": "villager",
            "phase": "night",
            "round": 1,
            "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "public_event_ids": [],
            "private_event_ids": [],
            "known_roles": {"p3": "seer"},
        })
        self.assertEqual(action.actor, "p3")
        self.assertEqual(action.action, "seer_check")
        self.assertEqual(action.target, "p1")
        self.assertEqual(action.source_label, "[deterministic fake provider output]")

    def test_invalid_target_raises_provider_action_error_without_repair(self) -> None:
        agent = build_default_fake_provider_agent("p3", override_raw_content='{"action":"seer_check","target":"p99","reason_summary":"bad target","decision_type":"inference_based","confidence":1.0}')
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide({...valid p3 observation...})
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "invalid_action")
        self.assertEqual(failure.target, "p99")
        self.assertFalse(failure.repaired_to_valid_action)
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_fake_provider -v
```

Expected result before implementation:

```text
FAILED or ERROR because werewolf_eval.fake_provider / werewolf_eval.provider_agent do not exist
```

- [ ] **Step 2.2: Implement deterministic fake provider and adapter**

Create `src/werewolf_eval/fake_provider.py` with:

- `DeterministicFakeProvider`
- `build_default_fake_provider_script()` returning the same valid actions as the existing deterministic mock path for `p3`, `p4`, `p5`, `p6`, and `wolf_team`
- `build_default_fake_provider_agent(actor: str, override_raw_content: str | None = None, failure_mode: str | None = None)`

Create `src/werewolf_eval/provider_agent.py` with:

- `ProviderActionError(ValueError)` carrying a `ProviderFailure`
- `ProviderAgent.decide(observation)` returning existing `AgentAction`
- strict validation against `allowed_actions` and `allowed_targets`
- parse failure / timeout / invalid action mapping into `ProviderFailure`
- no fallback action and no forced random target

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_fake_provider -v
```

Expected result after implementation:

```text
OK
```

## Task 3: GameEngine Injection Without Changing Default Mock Behavior

**Files:**
- Modify: `src/werewolf_eval/game_engine.py`
- Test: `tests/test_game_engine.py`

- [ ] **Step 3.1: Add failing injection regression tests**

Add tests to `tests/test_game_engine.py` proving:

```text
1. GameEngine.from_config(build_default_config()).run() still emits source_label=[deterministic mock agent output].
2. Existing G1b event count remains 18 and decision count remains 11.
3. Existing G1c valid consensus path still emits consensus_log and failure_audit with deterministic mock source label.
4. Injected fake-provider agents emit Game Log and Decision Log with source_label=[deterministic fake provider output].
5. Injected fake-provider game validates through parse_game_log and parse_decision_log.
```

Use an injected-agent construction equivalent to:

```python
from werewolf_eval.fake_provider import build_default_fake_provider_agent
from werewolf_eval.game_engine import GameEngine, build_default_config
from werewolf_eval.provider_contract import FAKE_PROVIDER_SOURCE_LABEL

agents = {pid: build_default_fake_provider_agent(pid) for pid in ["p3", "p4", "p5", "p6"]}
wolf_agent = build_default_fake_provider_agent("wolf_team")
engine = GameEngine.from_config(
    build_default_config(game_id="g1d_fake_provider"),
    agents=agents,
    wolf_agent=wolf_agent,
    source_label=FAKE_PROVIDER_SOURCE_LABEL,
)
outputs = engine.run(mode="g1b_default")
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected result before implementation:

```text
FAILED because GameEngine.from_config does not accept injected agents/source_label
```

- [ ] **Step 3.2: Implement minimal injection point**

Modify `src/werewolf_eval/game_engine.py` only as follows:

- Keep `MockAgent`, `WolfTeamMockAgent`, `AgentObservation`, `AgentAction`, and default `GameEngine.from_config(build_default_config()).run()` behavior compatible.
- Extend `GameEngine.__init__` and `GameEngine.from_config` to accept optional `agents`, optional `wolf_agent`, and optional `source_label`.
- Default `source_label` remains `[deterministic mock agent output]`.
- Use the configured `source_label` for generated Game Log and Decision Log.
- Do not change scoring, validators, semantic labels, or render code.
- Do not change G1c failure recovery semantics.

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine -v
```

Expected result after implementation:

```text
OK
```

## Task 4: Fake Provider Game CLI and Generated Artifacts

**Files:**
- Create: `src/werewolf_eval/run_fake_provider_game.py`
- Create: `docs/generated-games/g1d-fake-provider-game-log.json`
- Create: `docs/generated-games/g1d-fake-provider-decision-log.json`
- Create: `docs/generated-games/g1d-fake-provider-provider-trace.json`
- Create: `docs/generated-games/g1d-fake-provider-failure-audit.example.json`
- Create: `docs/generated-games/g1d-fake-provider-score-log.json`
- Create: `docs/generated-games/g1d-fake-provider-metrics-summary.json`
- Create: `docs/demo/phase3-g1d-fake-provider-runtime-demo.html`
- Test: `tests/test_fake_provider_game.py`

- [ ] **Step 4.1: Add failing CLI tests**

Create `tests/test_fake_provider_game.py` covering these commands through `subprocess.run` with `PYTHONPATH=src`:

```text
1. Valid fake-provider game writes Game Log, Decision Log, and provider trace.
2. Valid fake-provider artifacts validate through Game Log and Decision Log parsers.
3. Provider trace contains request/response counts and no secret/network strings.
4. Parse-failure mode exits non-zero, writes failure-audit example, and does not write forged valid Game Log / Decision Log.
5. Generated HTML includes [deterministic fake provider output] and does not claim provider-backed, live AI, human-vs-AI UI, or real multi-game Leaderboard.
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_fake_provider_game -v
```

Expected result before implementation:

```text
FAILED or ERROR because werewolf_eval.run_fake_provider_game does not exist
```

- [ ] **Step 4.2: Implement CLI harness**

Create `src/werewolf_eval/run_fake_provider_game.py` with arguments:

```text
--game-id
--game-log-out
--decision-log-out
--provider-trace-out
--failure-audit-out
--failure-mode
```

Valid path command:

```bash
PYTHONPATH=src python -m werewolf_eval.run_fake_provider_game --game-id g1d_fake_provider --game-log-out docs/generated-games/g1d-fake-provider-game-log.json --decision-log-out docs/generated-games/g1d-fake-provider-decision-log.json --provider-trace-out docs/generated-games/g1d-fake-provider-provider-trace.json --failure-audit-out docs/generated-games/g1d-fake-provider-failure-audit.example.json
```

Expected result:

```text
fake_provider_game_id=g1d_fake_provider
source_label=[deterministic fake provider output]
events=18
decisions=11
provider_requests=11
provider_responses=11
provider_failures=0
game_log=written
decision_log=written
provider_trace=written
```

Failure path command:

```bash
PYTHONPATH=src python -m werewolf_eval.run_fake_provider_game --game-id g1d_fake_provider_parse_failure --game-log-out /tmp/g1d-failure-game.json --decision-log-out /tmp/g1d-failure-decision.json --provider-trace-out /tmp/g1d-failure-provider-trace.json --failure-audit-out /tmp/g1d-fake-provider-failure-audit.example.json --failure-mode parse_failure
```

Expected result:

```text
exit code 2
fake_provider_game_id=g1d_fake_provider_parse_failure
provider_failures=1
failure_kind=parse_failure
game_log=not_written
decision_log=not_written
failure_audit=written
```

On Windows PowerShell, use a repository-local temp directory such as `.tmp/g1d-failure-game.json` instead of `/tmp/...`.

- [ ] **Step 4.3: Generate score, metrics, and demo artifacts through existing runtime pipeline**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1d-fake-provider-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1d-fake-provider-decision-log.json docs/generated-games/g1d-fake-provider-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json --score-log-out docs/generated-games/g1d-fake-provider-score-log.json --metrics-out docs/generated-games/g1d-fake-provider-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json --html-out docs/demo/phase3-g1d-fake-provider-runtime-demo.html
```

Expected result:

```text
validated game_id=g1d_fake_provider
source_label=[deterministic fake provider output]
validated decision_log_id=g1d_fake_provider_decision_log
game_id=g1d_fake_provider
decisions=11
source_label=[deterministic fake provider output]
validated log_bundle game_id=g1d_fake_provider
decision_log=enabled
consensus_log=disabled
failure_audit=disabled
team_consensus_links=0
scored game_id=g1d_fake_provider
score_records=11
decision_log=enabled
semantic_labels=disabled
bundle_validation=enabled
decision_quality_total=0
wrote docs/demo/phase3-g1d-fake-provider-runtime-demo.html
bundle_validation=disabled
```

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_fake_provider_game -v
```

Expected result after implementation:

```text
OK
```

## Task 5: Full Validation, Tree Refresh, and Review Packet

**Files:**
- Modify: `.oh-my-harness/tree.md`
- Create: `.logs/review/latest/review-packet.md`
- Test: all tests listed below

- [ ] **Step 5.1: Refresh tree after new files**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
tree refreshed successfully or equivalent hook success output
```

- [ ] **Step 5.2: Run complete validation**

Run:

```bash
python scripts/dev/validate_brief.py
PYTHONPATH=src python -m unittest tests.test_provider_contract tests.test_fake_provider tests.test_fake_provider_game tests.test_game_engine tests.test_source_labels -v
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests -q
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1d-fake-provider-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1d-fake-provider-decision-log.json docs/generated-games/g1d-fake-provider-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json --score-log-out docs/generated-games/g1d-fake-provider-score-log.json --metrics-out docs/generated-games/g1d-fake-provider-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json --html-out docs/demo/phase3-g1d-fake-provider-runtime-demo.html
git diff --check
```

Expected result:

```text
validate_brief.py: ok: true
targeted unittest: OK
full unittest discover: OK
compileall: exit code 0
validate_game_log: validated game_id=g1d_fake_provider and source_label=[deterministic fake provider output]
validate_decision_log: decisions=11 and source_label=[deterministic fake provider output]
validate_log_bundle: decision_log=enabled, consensus_log=disabled, failure_audit=disabled, team_consensus_links=0
score_game: score_records=11, decision_log=enabled, semantic_labels=disabled, bundle_validation=enabled, decision_quality_total=0
render_demo: wrote docs/demo/phase3-g1d-fake-provider-runtime-demo.html
git diff --check: exit code 0
```

- [ ] **Step 5.3: Generate review packet**

Run:

```bash
python scripts/dev/build_review_packet.py --base main --out .logs/review/latest/review-packet.md --allowlist "src/werewolf_eval/source_labels.py" --allowlist "src/werewolf_eval/game_engine.py" --allowlist "src/werewolf_eval/provider_contract.py" --allowlist "src/werewolf_eval/fake_provider.py" --allowlist "src/werewolf_eval/provider_agent.py" --allowlist "src/werewolf_eval/run_fake_provider_game.py" --allowlist "tests/test_source_labels.py" --allowlist "tests/test_game_engine.py" --allowlist "tests/test_provider_contract.py" --allowlist "tests/test_fake_provider.py" --allowlist "tests/test_fake_provider_game.py" --allowlist "docs/generated-games/g1d-fake-provider-game-log.json" --allowlist "docs/generated-games/g1d-fake-provider-decision-log.json" --allowlist "docs/generated-games/g1d-fake-provider-provider-trace.json" --allowlist "docs/generated-games/g1d-fake-provider-failure-audit.example.json" --allowlist "docs/generated-games/g1d-fake-provider-score-log.json" --allowlist "docs/generated-games/g1d-fake-provider-metrics-summary.json" --allowlist "docs/demo/phase3-g1d-fake-provider-runtime-demo.html" --allowlist ".oh-my-harness/tree.md" --allowlist ".logs/review/latest/review-packet.md" --test-command "python scripts/dev/validate_brief.py" --test-command "PYTHONPATH=src python -m unittest tests.test_provider_contract tests.test_fake_provider tests.test_fake_provider_game tests.test_game_engine tests.test_source_labels -v" --test-command "PYTHONPATH=src python -m unittest discover -s tests -p \"test_*.py\"" --test-command "python -m compileall src tests -q" --test-command "PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1d-fake-provider-game-log.json" --test-command "PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1d-fake-provider-decision-log.json docs/generated-games/g1d-fake-provider-game-log.json" --test-command "PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json" --test-command "git diff --check" --acceptance "A-1 fake provider source label registered | tests/test_provider_contract.py + tests/test_source_labels.py | PASS" --acceptance "A-2 provider request/response/failure/trace are JSON-safe | tests/test_provider_contract.py | PASS" --acceptance "A-3 fake provider valid response converts to AgentAction | tests/test_fake_provider.py | PASS" --acceptance "A-4 provider invalid/parse/timeout failures are not repaired | tests/test_fake_provider.py + failure audit example | PASS" --acceptance "A-5 GameEngine default mock behavior unchanged | tests/test_game_engine.py | PASS" --acceptance "A-6 injected fake-provider game emits valid Game/Decision logs | tests/test_game_engine.py + validators | PASS" --acceptance "A-7 CLI writes provider trace and refuses forged valid logs on failure | tests/test_fake_provider_game.py | PASS" --acceptance "A-8 generated score/metrics/demo artifacts are reproducible | score/render commands + generated files | PASS" --acceptance "A-9 no live provider/network/secret/dependency capability | packet forbidden/dependency checks | PASS" --acceptance "A-10 packet contains machine evidence and PACKET_TOO_LARGE status | .logs/review/latest/review-packet.md | PASS"
```

If the script option names differ, run:

```bash
python scripts/dev/build_review_packet.py --help
```

Then use the supported equivalent options while preserving the same evidence requirements.

Expected result:

```text
.logs/review/latest/review-packet.md exists
PACKET_TOO_LARGE = NO or PACKET_TOO_LARGE = YES is present
Evidence Map has no MANUAL_REVIEW_REQUIRED rows
Allowed Files Check is PASS
Dependency / Import Diff shows no new dependency manifests and no provider SDK / network / env imports
Forbidden Patterns Check warnings are classified as boundary text, test names, or fake-provider identifiers unless runtime code imports network/client/env/dependency behavior
```

## Acceptance Criteria

A-1. `[deterministic fake provider output]` is accepted by shared source-label validation and appears in generated fake-provider artifacts.

Evidence pointer: `src/werewolf_eval/source_labels.py`, `tests/test_source_labels.py`, `tests/test_provider_contract.py`, `docs/generated-games/g1d-fake-provider-game-log.json`.

A-2. Provider request, response, failure, and trace structures are JSON-safe and contain no secrets, env values, auth headers, provider URLs, or SDK metadata.

Evidence pointer: `src/werewolf_eval/provider_contract.py`, `tests/test_provider_contract.py`, `docs/generated-games/g1d-fake-provider-provider-trace.json`.

A-3. Deterministic fake provider converts valid provider-shaped JSON into existing `AgentAction` without changing the existing action contract.

Evidence pointer: `src/werewolf_eval/fake_provider.py`, `src/werewolf_eval/provider_agent.py`, `tests/test_fake_provider.py`.

A-4. Invalid target, parse failure, and timeout provider outputs are rejected and audited with `repaired_to_valid_action=false`; they are not converted into valid Decision Log or Game Log actions.

Evidence pointer: `tests/test_fake_provider.py`, `tests/test_fake_provider_game.py`, `docs/generated-games/g1d-fake-provider-failure-audit.example.json`.

A-5. Existing G1b/G1c mock-agent behavior remains compatible: default mock source label, event count, decision count, and G1c failure-recovery semantics remain covered by existing tests.

Evidence pointer: `tests/test_game_engine.py`, full unittest discover output.

A-6. Injected fake-provider agents can run one deterministic harness game and emit valid Game Log and Decision Log using `[deterministic fake provider output]`.

Evidence pointer: `tests/test_game_engine.py`, `tests/test_fake_provider_game.py`, validate_game_log and validate_decision_log command output.

A-7. The provider trace is generated as a first-class artifact and records request/response/failure counts without leaking secrets or network configuration.

Evidence pointer: `docs/generated-games/g1d-fake-provider-provider-trace.json`, `tests/test_fake_provider_game.py`.

A-8. Existing evaluator pipeline can score and render the fake-provider harness outputs without modifying scoring or rendering code.

Evidence pointer: `docs/generated-games/g1d-fake-provider-score-log.json`, `docs/generated-games/g1d-fake-provider-metrics-summary.json`, `docs/demo/phase3-g1d-fake-provider-runtime-demo.html`, score/render command output.

A-9. No live provider, network, secret, env, SDK, dependency, CI live call, multi-game leaderboard, or human-vs-AI UI capability is introduced.

Evidence pointer: Review Packet Forbidden Patterns Check, Dependency / Import Diff, changed files allowlist, generated trace content checks.

A-10. Review Packet is generated from machine evidence, not a plain-language implementer summary, and contains no `MANUAL_REVIEW_REQUIRED` acceptance rows.

Evidence pointer: `.logs/review/latest/review-packet.md`.

## Review Packet Requirements

After implementation, generate:

```text
.logs/review/latest/review-packet.md
```

The review packet must include at least these machine-generated evidence sections:

1. `git diff --name-only`
2. `git diff --stat`
3. `git diff --check` result
4. changed files allowlist check
5. forbidden patterns check
6. dependency/import diff check
7. test command + exact pass/fail summary
8. key hunk excerpts
9. acceptance checklist with evidence pointer
10. implementer risk notes
11. Evidence Map
12. review trigger result
13. packet length check with `PACKET_TOO_LARGE = NO` or `PACKET_TOO_LARGE = YES`

Length limits:

- `review-packet.md <= 300 lines`
- Key Hunks <= 120 lines
- Test output contains summaries only, not full logs
- Each changed file gets at most 1 key hunk unless a risk trigger is hit
- If over the limit, write `PACKET_TOO_LARGE = YES`
- If within the limit, write `PACKET_TOO_LARGE = NO`

The packet must not leave any acceptance item as `MANUAL_REVIEW_REQUIRED`. If the generator cannot infer an item automatically, pass explicit `--acceptance` evidence and regenerate.

## Codex B档 Deep Review Risk Points

This implementation may trigger B档 review. Classify these risks in the review packet:

- `src/werewolf_eval/game_engine.py` changes runtime injection behavior.
- New `src/werewolf_eval/provider_contract.py`, `src/werewolf_eval/fake_provider.py`, and `src/werewolf_eval/provider_agent.py` introduce a provider boundary, even though it is fake/offline.
- New CLI `src/werewolf_eval/run_fake_provider_game.py` writes generated artifacts.
- Changed file count may exceed 8.
- Generated artifacts under `docs/generated-games/**` and `docs/demo/**` are user-visible evidence and should be reviewed for false claims.
- Forbidden pattern scan will likely hit words such as provider, network, env, secret, API, HTTP, SDK, and live AI in tests/docs/boundary strings. These must be classified. Any actual runtime import or behavior for network/env/secrets/dependencies is blocking.
- Key hunks may be truncated if the adapter implementation is large. If truncated, request B档 with exact line ranges.

## Implementation PR Description Draft

```markdown
## Summary

Implements the G1d fake-provider contract harness.

Bound plan:

- `docs/harness/plans/2026-06-02--g1d-fake-provider-contract-harness-plan.md`

## What changed

- Added provider request/response/failure/trace contract dataclasses.
- Added deterministic fake provider and provider-agent adapter.
- Added minimal GameEngine injection so default mock behavior remains unchanged while fake-provider agents can drive a deterministic harness game.
- Added `run_fake_provider_game` CLI.
- Added generated G1d fake-provider Game Log, Decision Log, provider trace, failure-audit example, Score Log, Metrics Summary, and runtime demo.
- Generated `.logs/review/latest/review-packet.md` for Codex A档 review.

## Explicit non-goals

- No live provider calls.
- No network access.
- No API keys, secrets, or env handling.
- No provider SDKs or new dependencies.
- No CI live calls.
- No provider-backed smoke.
- No real multi-game Leaderboard.
- No human-vs-AI UI.
- No repair path that turns invalid/timeout/parse-failure provider output into valid actions.

## Validation

- `python scripts/dev/validate_brief.py` → PASS
- `PYTHONPATH=src python -m unittest tests.test_provider_contract tests.test_fake_provider tests.test_fake_provider_game tests.test_game_engine tests.test_source_labels -v` → PASS
- `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` → PASS
- `python -m compileall src tests -q` → PASS
- `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1d-fake-provider-game-log.json` → PASS
- `PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1d-fake-provider-decision-log.json docs/generated-games/g1d-fake-provider-game-log.json` → PASS
- `PYTHONPATH=src python -m werewolf_eval.validate_log_bundle docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json` → PASS
- `PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json --score-log-out docs/generated-games/g1d-fake-provider-score-log.json --metrics-out docs/generated-games/g1d-fake-provider-metrics-summary.json` → PASS
- `PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1d-fake-provider-game-log.json --decision-log docs/generated-games/g1d-fake-provider-decision-log.json --html-out docs/demo/phase3-g1d-fake-provider-runtime-demo.html` → PASS
- `git diff --check` → PASS

## Review packet

- `.logs/review/latest/review-packet.md`
- `PACKET_TOO_LARGE = NO` expected; if `YES`, Codex A档 should request B档 with exact line ranges.
```
