# G1h Live Runtime Event Spine Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Establish a client-agnostic live runtime event spine for one fake/provider-backed Werewolf run by writing append-only `events.jsonl`, runtime snapshots, prompt manifest, provider lifecycle events, and a standard final log bundle without changing scoring behavior.

**Architecture:** G1h adds a narrow runtime observation layer around the existing G1f provider consensus path. The canonical Game Log, Decision Log, Consensus Log, Provider Trace, and Failure Audit remain the final audit artifacts; `events.jsonl`, snapshots, and prompt manifest are an observation spine for future G2 observer surfaces. The fake-provider path must be deterministic and CI-safe; the DeepSeek live path must remain explicitly opt-in.

**Tech Stack:** Python standard library only. No Qt, Web server, UI framework, dependency change, scoring formula change, validator rewrite, generated HTML change, or provider SDK change.

---

## Context Basis

Current route facts:

- `AGENTS.md` says the current route is G1h Live Runtime Event Spine and forbids Qt/QML, Web observer, prompt editor UI, multi-provider arena, leaderboard, and scoring formula changes in G1h.
- `docs/ROADMAP.md` defines G1h as the step after G1g: emit `events.jsonl`, runtime snapshots, prompt manifest, provider lifecycle events, and final log bundle compatibility.
- `docs/TASKS.md` marks G1a-G1g completed and G1h as `next_candidate`.
- `docs/specs/agent-workflow.md` says connector/cloud agents may create or update Implementation Plans and plan-supporting docs, but must not modify runtime code, tests, validators, generated fixtures, or historical artifacts unless the active plan allows it.
- `.github/writing-plan.md` requires exact files, exact commands, expected outputs, allowlist, forbidden scope, acceptance criteria, and an Implementation PR description.

This plan supersedes the earlier high-level G1h sketch at the same path by turning it into an executable Claude Code implementation protocol.

## Scope Summary

G1h includes:

- Runtime event contract and validator for JSONL events.
- Append-only runtime event writer with strictly monotonic `seq`.
- Runtime snapshot writer for god-view audit state and role-view projection.
- Prompt manifest writer with redaction of secrets and credential-like values.
- Provider lifecycle event recording for request preparation, response receipt, token usage, latency, parse success, parse failure, invalid action, timeout, provider failure, and finalization.
- Integration with the existing G1f provider consensus runtime path.
- Deterministic fake-provider CLI path suitable for CI and Codex review.
- Live DeepSeek path kept behind `--allow-live-api` and excluded from CI by default.
- Standard final log bundle compatibility with Game Log, Decision Log, Consensus Log, Provider Trace, and Failure Audit.

G1h does not include:

- Qt/QML client.
- Web observer/server.
- Prompt editor UI.
- Multi-provider arena.
- Leaderboard.
- Human-vs-AI UI.
- Scoring formula changes.
- Validator rewrites.
- Generated HTML or demo renderer changes.
- Dependency or provider SDK changes.
- CI live API calls.

---

## File Plan

### Create

- `src/werewolf_eval/runtime_events.py`
  - Runtime event envelope constants.
  - JSONL append-only writer.
  - Snapshot writer.
  - Prompt manifest writer.
  - Redaction helpers.
  - JSONL reader / validator helpers used by tests and review evidence.

- `src/werewolf_eval/run_g1h_fake_runtime.py`
  - Deterministic CI-safe fake-provider G1h runtime CLI.
  - Writes `events.jsonl`, `snapshots/`, `prompt-manifest.json`, `game-log.json`, `decision-log.json`, `consensus-log.json`, `provider-trace.json`, and `failure-audit.json`.
  - Uses no network and no secrets.

- `tests/test_runtime_events.py`
  - Unit tests for event envelope validation, monotonic `seq`, JSONL parsing, snapshot writing, manifest redaction, secret-pattern rejection, and role-view projection leak checks.

- `tests/test_g1h_runtime_spine.py`
  - Integration tests for fake-provider event spine output, final log bundle compatibility, provider lifecycle coverage, failure lifecycle events, refs integrity, and live-guard behavior.

### Modify

- `src/werewolf_eval/game_engine.py`
  - Add optional runtime event recorder hook.
  - Emit engine-level events and snapshots without changing existing Game Log / Decision Log / Consensus Log semantics.
  - Preserve existing public method names and existing return payloads.

- `src/werewolf_eval/provider_agent.py`
  - Add optional runtime event recorder hook.
  - Emit provider lifecycle events without changing action parsing behavior or failure semantics.

- `src/werewolf_eval/run_deepseek_consensus_game.py`
  - Add optional event-spine output support.
  - Keep `--allow-live-api` guard unchanged.
  - Keep existing output files and summary lines compatible.
  - Write no live artifacts when live API is disabled or API key is missing, except when a deterministic fake runtime CLI explicitly opts into a fake run.

- `tests/test_deepseek_consensus_game.py`
  - Extend existing fake-provider tests to assert G1h event spine artifacts when the helper is called with event-spine output enabled.
  - Preserve existing tests for disabled live API and missing API key.

### Do Not Modify

- `src/werewolf_eval/scoring.py`
- `src/werewolf_eval/score_game.py`
- `src/werewolf_eval/attribution.py`
- `src/werewolf_eval/render_demo.py`
- `src/werewolf_eval/render_provider_replay.py`
- Existing validators except import-only use in tests.
- `docs/ROADMAP.md`
- `docs/TASKS.md`
- `docs/adr/**`
- `docs/demo/**`
- `docs/generated-games/**`
- `docs/gold-game/**`
- Dependency manifests.
- `.github/**`
- `.agents/skills/**`
- `.tmp/**` as committed files.

---

## Allowlist

The implementation PR may change only these paths:

```text
src/werewolf_eval/runtime_events.py
src/werewolf_eval/run_g1h_fake_runtime.py
src/werewolf_eval/game_engine.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/run_deepseek_consensus_game.py
tests/test_runtime_events.py
tests/test_g1h_runtime_spine.py
tests/test_deepseek_consensus_game.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

`.oh-my-harness/tree.md` is allowed only if a local new-file hook refreshes it after adding files. If the hook is unavailable, do not hand-edit tree output; record the equivalent `git ls-files --cached --others --exclude-standard` evidence in the review packet.

`.logs/review/latest/review-packet.md` is allowed only as review evidence for the implementation PR. Do not treat it as source code.

---

## Forbidden Scope

The implementation PR must not:

- Add or modify dependency manifests such as `package.json`, `package-lock.json`, `pyproject.toml`, `requirements.txt`, `poetry.lock`, `pnpm-lock.yaml`, `yarn.lock`, or `uv.lock`.
- Add networking libraries or provider SDKs.
- Modify scoring, attribution, rendering, validators, canonical fixtures, generated game artifacts, gold-game artifacts, ROADMAP, TASKS, ADRs, or GitHub workflow files.
- Commit `.tmp/**`, local smoke artifacts, API keys, bearer tokens, credential paths, provider raw secret values, or live API response dumps.
- Run live provider calls in CI or unit tests.
- Change final Game Log / Decision Log / Consensus Log schema semantics.
- Change DeepSeek provider request semantics outside event-spine instrumentation.
- Repair invalid provider output into valid game logs.
- Introduce observer server, WebSocket, REST API, Qt/QML, Web UI, prompt editor, multi-provider arena, leaderboard, or human-vs-AI UI.

---

## Event Spine Contract

Every line in `events.jsonl` is exactly one UTF-8 JSON object.

Minimum envelope:

```json
{
  "run_id": "g1h_fake_runtime",
  "seq": 1,
  "event_id": "g1h_fake_runtime_rt_0001",
  "kind": "run_started",
  "round": 0,
  "phase": "setup",
  "actor": "system",
  "visibility": "god",
  "payload": {},
  "refs": {},
  "created_at": "2026-06-03T00:00:00Z"
}
```

Required rules:

- `seq` is strictly increasing from 1 by 1 within a run.
- `event_id` is unique within a run.
- `kind` is one of the documented event kinds below.
- `visibility` is one of `god`, `public`, `role:p1`, `role:p2`, `role:p3`, `role:p4`, `role:p5`, `role:p6`, or `team:werewolf`.
- `payload` never contains API keys, bearer tokens, authorization headers, credential paths, or raw provider secret values.
- `refs` may contain:
  - `game_event_id`
  - `decision_id`
  - `consensus_id`
  - `provider_request_id`
  - `provider_response_id`
  - `failure_id`
  - `snapshot_id`
  - `artifact_path`
- Runtime events do not replace final canonical logs.

Required event kinds for G1h:

```text
run_started
phase_started
observation_built
provider_request_prepared
provider_response_received
provider_parse_succeeded
provider_parse_failed
provider_action_invalid
provider_timeout
provider_failed
agent_action_selected
consensus_started
consensus_resolved
game_event_emitted
snapshot_written
artifact_written
run_finalized
```

The implementation may add narrowly named event kinds only if they are documented in `runtime_events.py`, tested, and included in the review packet evidence map.

---

## Snapshot Contract

G1h must write snapshots under:

```text
snapshots/
```

Required snapshot categories:

- God-view snapshots:
  - Include run ID, round, phase, alive players, players with role/team, public event IDs, and private audit state needed for local operator inspection.
  - Use `visibility = "god"` in the event that references the snapshot.

- Role-view projection snapshots:
  - Include run ID, player ID, role, team, round, phase, alive players, public event IDs, private event IDs visible to that role, and `known_roles`.
  - For a non-werewolf role, `known_roles` must contain only that player’s own role unless public role reveal events already justify more information.
  - For a werewolf role, `known_roles` may contain werewolf teammates.
  - Role-view snapshots must not include full `players` role/team arrays.

Acceptance requires a test that opens at least one non-werewolf role-view snapshot and proves it does not leak hidden roles for `p1` / `p2` before public reveal.

---

## Prompt Manifest Contract

G1h must write:

```text
prompt-manifest.json
```

Minimum fields:

```json
{
  "run_id": "g1h_fake_runtime",
  "source_label": "[deterministic fake provider output]",
  "agents": [
    {
      "agent_id": "p1",
      "role": "werewolf",
      "team": "werewolf",
      "provider": "fake",
      "model": "fake-provider",
      "temperature": 0,
      "strategy": "deterministic",
      "prompt_profile": "g1h-fake-provider-v1",
      "prompt_hash": "sha256:...",
      "redaction_status": "redacted"
    }
  ],
  "secrets_redacted": true
}
```

Rules:

- Manifest may include prompt hashes and non-secret profile metadata.
- Manifest must not include API key values, bearer token values, authorization headers, local credential file paths, or environment variable values.
- For DeepSeek live path, manifest may include `provider = "deepseek"` and `model`, but must not include API key material.

---

## Task 1: Add runtime event contract and writer

**Files:**

- Create: `src/werewolf_eval/runtime_events.py`
- Modify: none
- Test: `tests/test_runtime_events.py`

- [ ] **Step 1: Create `runtime_events.py` with envelope constants and writer interfaces**

Implement these public names:

```python
RUNTIME_EVENT_KINDS: tuple[str, ...]
RUNTIME_EVENT_VISIBILITIES: tuple[str, ...]
SECRET_KEY_FRAGMENTS: tuple[str, ...]

class RuntimeEventError(ValueError): ...

def redact_secret_values(value: object) -> object: ...
def assert_no_secret_patterns(value: object) -> None: ...
def validate_runtime_event(event: dict[str, object]) -> None: ...
def read_events_jsonl(path: Path) -> list[dict[str, object]]: ...

class RuntimeEventWriter:
    def __init__(self, run_id: str, out_dir: Path, clock: Callable[[], str] | None = None) -> None: ...
    @property
    def events_path(self) -> Path: ...
    @property
    def snapshots_dir(self) -> Path: ...
    def emit(
        self,
        kind: str,
        *,
        round: int,
        phase: str,
        actor: str,
        visibility: str,
        payload: dict[str, object] | None = None,
        refs: dict[str, object] | None = None,
    ) -> dict[str, object]: ...
    def write_snapshot(
        self,
        name: str,
        snapshot: dict[str, object],
        *,
        visibility: str,
        round: int,
        phase: str,
        actor: str,
    ) -> str: ...
    def write_prompt_manifest(self, manifest: dict[str, object]) -> Path: ...
```

Implementation constraints:

- Use only Python standard library.
- JSON output must be stable enough for tests: `ensure_ascii=False`, `sort_keys=True` for event lines and manifests.
- `emit()` must append one JSON object plus newline to `events.jsonl`.
- `emit()` must validate before writing.
- `write_snapshot()` must redact secrets, write `snapshots/<name>.json`, then emit `snapshot_written`.
- `write_prompt_manifest()` must redact secrets and write `prompt-manifest.json`.
- `read_events_jsonl()` must reject empty lines, malformed JSON, duplicate `event_id`, and non-monotonic `seq`.

- [ ] **Step 2: Add unit tests for event writer behavior**

Create `tests/test_runtime_events.py` with tests covering:

```python
class RuntimeEventWriterTests(unittest.TestCase):
    def test_emit_writes_monotonic_jsonl_events(self) -> None: ...
    def test_read_events_rejects_duplicate_event_id(self) -> None: ...
    def test_read_events_rejects_non_monotonic_sequence(self) -> None: ...
    def test_prompt_manifest_redacts_secret_like_values(self) -> None: ...
    def test_snapshot_writer_emits_snapshot_event_and_file(self) -> None: ...
    def test_validate_event_rejects_secret_payload(self) -> None: ...
```

The tests must use `TemporaryDirectory()` and must not touch `.tmp/`.

- [ ] **Step 3: Run focused tests for Task 1**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events -v
```

Expected result:

```text
Ran 6 tests
OK
```

If the exact count changes because the implementer adds more narrow tests, the summary must still end with `OK` and the review packet must state the observed count.

---

## Task 2: Add role-safe snapshot helpers and prompt manifest helpers

**Files:**

- Modify: `src/werewolf_eval/runtime_events.py`
- Modify: `tests/test_runtime_events.py`
- Test: `tests/test_runtime_events.py`

- [ ] **Step 1: Add snapshot/projection helper functions**

Add these public helper functions:

```python
def build_god_snapshot(
    *,
    run_id: str,
    game_id: str,
    round: int,
    phase: str,
    players: list[dict[str, object]],
    alive_players: list[str],
    public_event_ids: list[str],
    private_event_ids: list[str],
) -> dict[str, object]: ...

def build_role_projection_snapshot(
    *,
    run_id: str,
    observation: object,
) -> dict[str, object]: ...

def build_prompt_manifest(
    *,
    run_id: str,
    source_label: str,
    agents: list[dict[str, object]],
) -> dict[str, object]: ...
```

Implementation constraints:

- `build_role_projection_snapshot()` may consume an object with `to_dict()` or a plain dict.
- Role projection must copy only the observation fields. It must not add full role assignment tables.
- God snapshot may contain full player role/team data because it is `god` visibility.
- Prompt manifest must run through `redact_secret_values()` before writing.
- Prompt hashes should use SHA-256 over prompt/profile text when prompt text exists. If no prompt text is available, hash deterministic metadata such as provider/model/profile.

- [ ] **Step 2: Add leak-prevention tests**

Extend `tests/test_runtime_events.py` with tests covering:

```python
class RuntimeSnapshotProjectionTests(unittest.TestCase):
    def test_non_wolf_projection_does_not_include_hidden_wolf_roles(self) -> None: ...
    def test_wolf_projection_may_include_wolf_teammate_roles(self) -> None: ...
    def test_god_snapshot_keeps_full_role_table(self) -> None: ...
    def test_prompt_manifest_contains_redaction_status_and_no_secret_values(self) -> None: ...
```

- [ ] **Step 3: Run focused tests for Tasks 1-2**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events -v
```

Expected result:

```text
OK
```

The output must show all runtime event and snapshot tests passing.

---

## Task 3: Instrument `ProviderAgent` lifecycle events

**Files:**

- Modify: `src/werewolf_eval/provider_agent.py`
- Modify: `tests/test_g1h_runtime_spine.py`
- Test: `tests/test_g1h_runtime_spine.py`

- [ ] **Step 1: Add optional runtime event writer to `ProviderAgent`**

Update the constructor signature without breaking existing callers:

```python
def __init__(
    self,
    player_id: str,
    provider: Any,
    override_raw_content: str | None = None,
    failure_mode: str | None = None,
    runtime_events: Any | None = None,
) -> None:
```

Event emission requirements inside `decide()`:

- Before provider call, emit `provider_request_prepared`.
  - Include `request_id`, `allowed_actions`, `allowed_targets`, `round`, `phase`, and actor.
  - Do not include authorization headers or API key data.
- After provider response, emit `provider_response_received`.
  - Include `request_id`, `provider_name`, `latency_ms`, and `token_usage`.
  - Do not include full raw provider content.
- After JSON parse and action validation succeeds, emit `provider_parse_succeeded`.
- On JSON parse failure, emit `provider_parse_failed` before raising `ProviderActionError`.
- On invalid action or invalid target, emit `provider_action_invalid` before raising `ProviderActionError`.
- On `failure_mode == "timeout"`, emit `provider_timeout` before raising `ProviderActionError`.
- On provider exception, emit `provider_failed` before raising `ProviderActionError`.

Required non-behavior-change rule:

- Existing exception type, `ProviderFailure.kind`, `ProviderFailure.reason`, and returned `AgentAction` fields must remain compatible with existing tests.

- [ ] **Step 2: Add provider lifecycle tests**

Create `tests/test_g1h_runtime_spine.py` and add tests covering:

```python
class ProviderLifecycleEventTests(unittest.TestCase):
    def test_successful_provider_decision_emits_request_response_parse_success(self) -> None: ...
    def test_parse_failure_emits_parse_failed_event(self) -> None: ...
    def test_invalid_action_emits_invalid_action_event(self) -> None: ...
    def test_timeout_emits_timeout_event(self) -> None: ...
    def test_provider_exception_emits_provider_failed_event(self) -> None: ...
```

Use small fake providers inside the test file. Do not import live provider transports or call network.

- [ ] **Step 3: Run provider lifecycle tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_g1h_runtime_spine.ProviderLifecycleEventTests -v
```

Expected result:

```text
OK
```

---

## Task 4: Instrument `GameEngine` with optional runtime event writer

**Files:**

- Modify: `src/werewolf_eval/game_engine.py`
- Modify: `tests/test_game_engine.py`
- Modify: `tests/test_g1h_runtime_spine.py`
- Test: `tests/test_game_engine.py`
- Test: `tests/test_g1h_runtime_spine.py`

- [ ] **Step 1: Add optional runtime event writer to `GameEngine`**

Update constructor and `from_config()` with a new optional parameter:

```python
runtime_events: Any | None = None
```

Store it as:

```python
self._runtime_events = runtime_events
```

Do not change existing parameter order except by adding the new optional parameter at the end.

- [ ] **Step 2: Emit engine lifecycle events**

Emit these events when `self._runtime_events` is present:

- `run_started` at the start of `run()`.
- `phase_started` before each major phase block:
  - setup
  - round 1 night
  - round 1 day
  - round 2 night
  - round 2 day
  - game_end
- `observation_built` when `_wolf_obs()` or `_player_obs()` builds an observation for an agent.
- `agent_action_selected` after a valid action returns from an agent.
- `consensus_started` and `consensus_resolved` around `_resolve_wolf_consensus()`.
- `game_event_emitted` each time `_emit()` creates a Game Log event.
- `artifact_written` is not emitted by `GameEngine`; the CLI/runner emits it after writing files.
- `run_finalized` is emitted by the CLI/runner after all final artifacts are written.

Important boundary:

- Do not make runtime events the source of truth for Game Log events.
- Do not change `_emit()` return shape.
- Do not change event IDs, decision IDs, consensus IDs, or final log JSON shape.

- [ ] **Step 3: Write god and role projection snapshots from `GameEngine`**

At minimum:

- Write one god-view snapshot after setup event.
- Write one role-view projection snapshot for each agent observation before the provider/mock agent decides.
- Write one final god-view snapshot after `game_over`.
- Each snapshot write must be followed by a `snapshot_written` event from `RuntimeEventWriter.write_snapshot()`.

Use helpers from `runtime_events.py`.

- [ ] **Step 4: Add engine behavior compatibility tests**

Extend existing `tests/test_game_engine.py` or add cases to `tests/test_g1h_runtime_spine.py`:

```python
class GameEngineRuntimeSpineTests(unittest.TestCase):
    def test_runtime_event_hook_does_not_change_final_logs(self) -> None: ...
    def test_runtime_events_reference_game_log_events(self) -> None: ...
    def test_role_projection_snapshots_do_not_leak_hidden_roles(self) -> None: ...
```

The first test must run the same deterministic engine once without runtime events and once with runtime events, then assert:

```python
self.assertEqual(with_events.game_log, without_events.game_log)
self.assertEqual(with_events.decision_log, without_events.decision_log)
```

If consensus mode is used, assert consensus log equality too.

- [ ] **Step 5: Run engine tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_game_engine tests.test_g1h_runtime_spine.GameEngineRuntimeSpineTests -v
```

Expected result:

```text
OK
```

---

## Task 5: Add CI-safe fake G1h runtime CLI

**Files:**

- Create: `src/werewolf_eval/run_g1h_fake_runtime.py`
- Modify: `tests/test_g1h_runtime_spine.py`
- Test: `tests/test_g1h_runtime_spine.py`

- [ ] **Step 1: Implement fake runtime CLI**

The CLI must support:

```powershell
$env:PYTHONPATH='src'; python -m werewolf_eval.run_g1h_fake_runtime --game-id g1h_fake_runtime --out-dir .tmp/g1h-fake-runtime
```

Required behavior:

- Use deterministic fake provider agents.
- No network.
- No API key.
- No environment secrets.
- Write these files:

```text
events.jsonl
prompt-manifest.json
snapshots/*.json
game-log.json
decision-log.json
consensus-log.json
provider-trace.json
failure-audit.json
```

Required stdout summary lines:

```text
g1h_fake_runtime_game_id=g1h_fake_runtime
source_label=[deterministic fake provider output]
events_jsonl=written
snapshots=written
prompt_manifest=written
game_log=written
decision_log=written
consensus_log=written
provider_trace=written
failure_audit=written
live_api=not_used
```

The exact number of snapshots/events may also be printed, for example:

```text
runtime_events=NN
runtime_snapshots=NN
```

- [ ] **Step 2: Add CLI integration test**

Add a test that runs the module with `subprocess.run()` in a temporary output directory and asserts:

- Return code is `0`.
- Required stdout lines appear.
- Every required artifact exists.
- `events.jsonl` parses through `read_events_jsonl()`.
- `seq` values are strictly monotonic.
- At least one event references a final `game_event_id`.
- At least one event references a `provider_request_id`.
- At least one event references a `consensus_id`.
- At least one event references a `snapshot_id`.
- `prompt-manifest.json` contains `secrets_redacted = true`.
- No artifact contains `Authorization`, `Bearer `, `api_key`, `DEEPSEEK_API_KEY`, or a key-like `sk-` pattern.

- [ ] **Step 3: Run fake runtime CLI test**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_g1h_runtime_spine.G1hFakeRuntimeCliTests -v
```

Expected result:

```text
OK
```

- [ ] **Step 4: Run fake runtime CLI manually for review evidence**

```powershell
Remove-Item -Recurse -Force .tmp/g1h-fake-runtime -ErrorAction SilentlyContinue
$env:PYTHONPATH='src'; python -m werewolf_eval.run_g1h_fake_runtime --game-id g1h_fake_runtime --out-dir .tmp/g1h-fake-runtime
```

Expected stdout must include:

```text
g1h_fake_runtime_game_id=g1h_fake_runtime
events_jsonl=written
snapshots=written
prompt_manifest=written
game_log=written
decision_log=written
consensus_log=written
provider_trace=written
failure_audit=written
live_api=not_used
```

Expected local artifact check:

```powershell
Test-Path .tmp/g1h-fake-runtime/events.jsonl
Test-Path .tmp/g1h-fake-runtime/prompt-manifest.json
Test-Path .tmp/g1h-fake-runtime/game-log.json
Test-Path .tmp/g1h-fake-runtime/decision-log.json
Test-Path .tmp/g1h-fake-runtime/consensus-log.json
Test-Path .tmp/g1h-fake-runtime/provider-trace.json
Test-Path .tmp/g1h-fake-runtime/failure-audit.json
```

Expected result:

```text
True
True
True
True
True
True
True
```

Do not commit `.tmp/g1h-fake-runtime/**`.

---

## Task 6: Integrate event-spine support into existing DeepSeek consensus runner

**Files:**

- Modify: `src/werewolf_eval/run_deepseek_consensus_game.py`
- Modify: `tests/test_deepseek_consensus_game.py`
- Test: `tests/test_deepseek_consensus_game.py`

- [ ] **Step 1: Extend helper signature without breaking existing callers**

Change:

```python
def run_deepseek_consensus_game_with_provider_factory(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory: ProviderFactory,
) -> int:
```

to:

```python
def run_deepseek_consensus_game_with_provider_factory(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory: ProviderFactory,
    write_runtime_spine: bool = False,
    runtime_source_label: str | None = None,
) -> int:
```

Required behavior:

- When `write_runtime_spine=False`, behavior remains exactly compatible with existing tests.
- When `write_runtime_spine=True`, create `RuntimeEventWriter(run_id=game_id, out_dir=out_dir)`.
- Pass the writer into `ProviderAgent` instances and `GameEngine`.
- Write `prompt-manifest.json`.
- Emit `artifact_written` events after writing each final artifact.
- Emit `run_finalized` after artifact writing finishes.
- On provider failure before valid final logs are written:
  - Write `events.jsonl`, `prompt-manifest.json`, `provider-trace.json`, and `failure-audit.json`.
  - Emit provider failure events and `artifact_written` events for trace/audit.
  - Do not write valid final Game Log / Decision Log / Consensus Log.
  - Return existing failure code `2`.

- [ ] **Step 2: Extend CLI arguments**

Add:

```text
--write-runtime-spine
```

Default:

```text
False
```

Rules:

- `--write-runtime-spine` must not bypass `--allow-live-api`.
- When live API is disabled, CLI still returns nonzero and writes no final artifacts.
- If `--write-runtime-spine` is passed without `--allow-live-api`, no `events.jsonl` should be written by the DeepSeek live CLI path. The fake runtime CLI is the CI-safe path for events.

- [ ] **Step 3: Extend existing DeepSeek consensus tests**

Update `tests/test_deepseek_consensus_game.py`:

- Existing disabled-live and missing-key tests must continue passing.
- Existing fake-provider helper test must still pass when `write_runtime_spine=False`.
- Add a new fake-provider helper test with `write_runtime_spine=True` that asserts:
  - `events.jsonl` exists.
  - `prompt-manifest.json` exists.
  - `snapshots/` exists and has JSON files.
  - final standard logs still validate through existing validators.
  - provider trace and failure audit still have the same final semantics.
- Add a live-disabled test with `--write-runtime-spine` and no `--allow-live-api` that asserts:
  - return code is nonzero.
  - stdout includes `live_api=disabled`.
  - no `events.jsonl`, Game Log, Decision Log, or Consensus Log is written.

- [ ] **Step 4: Run DeepSeek consensus tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_deepseek_consensus_game -v
```

Expected result:

```text
OK
```

Expected live guard remains:

```text
live_api=disabled
game_log=not_written
decision_log=not_written
consensus_log=not_written
```

---

## Task 7: Validate final log compatibility and event refs

**Files:**

- Modify: `tests/test_g1h_runtime_spine.py`
- Test: `tests/test_g1h_runtime_spine.py`

- [ ] **Step 1: Add refs integrity test**

In `tests/test_g1h_runtime_spine.py`, add a test that runs the fake runtime and loads:

```text
events.jsonl
game-log.json
decision-log.json
consensus-log.json
provider-trace.json
failure-audit.json
```

The test must build sets for:

```python
game_event_ids
decision_ids
consensus_ids
provider_request_ids
provider_response_ids
failure_ids
snapshot_ids
```

For every runtime event `refs` entry:

- `game_event_id` must exist in `game_event_ids`.
- `decision_id` must exist in `decision_ids`.
- `consensus_id` must exist in `consensus_ids`.
- `provider_request_id` must exist in `provider_request_ids`.
- `provider_response_id` must exist in `provider_response_ids` when present.
- `failure_id` must exist in `failure_ids` when present.
- `snapshot_id` must correspond to an existing snapshot file.

- [ ] **Step 2: Add final log validator test**

Use existing validators in tests:

```python
from werewolf_eval.game_log import load_game_log, validate_game_log
from werewolf_eval.decision_log import load_decision_log, validate_decision_log
from werewolf_eval.consensus_log import load_consensus_log, validate_consensus_log
```

Validate fake runtime final logs after the event spine is written.

Expected:

- Game Log validates.
- Decision Log validates against Game Log.
- Consensus Log validates against Game Log.
- Failure Audit has zero failures for success fake runtime.
- Provider Trace has at least one request and one response.

- [ ] **Step 3: Run refs and validator tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_g1h_runtime_spine.G1hRuntimeBundleCompatibilityTests -v
```

Expected result:

```text
OK
```

---

## Task 8: Guard against secret leaks and forbidden committed artifacts

**Files:**

- Modify: `tests/test_runtime_events.py`
- Modify: `tests/test_g1h_runtime_spine.py`
- Test: `tests/test_runtime_events.py`
- Test: `tests/test_g1h_runtime_spine.py`

- [ ] **Step 1: Add artifact secret-scan test**

Add a test that recursively reads fake runtime output files from a temporary directory and fails if any file contains:

```text
Authorization
Bearer 
DEEPSEEK_API_KEY
api_key
secret
credential
```

Case-insensitive scanning is required for key names except `Bearer `, which should be checked case-sensitively as well.

Also reject key-like patterns:

```text
sk-
```

The test may allow the literal word `redacted` because the manifest should state redaction status.

- [ ] **Step 2: Add committed-file boundary test**

Add a local validation command, not necessarily a committed test, that the implementer must run before PR:

```powershell
git diff --name-only main...HEAD | python -c "import sys; allowed=set('''src/werewolf_eval/runtime_events.py
src/werewolf_eval/run_g1h_fake_runtime.py
src/werewolf_eval/game_engine.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/run_deepseek_consensus_game.py
tests/test_runtime_events.py
tests/test_g1h_runtime_spine.py
tests/test_deepseek_consensus_game.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md'''.splitlines()); changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p not in allowed]; print('\n'.join(changed)); assert not bad, 'outside allowlist: '+repr(bad)"
```

Expected result:

- The command prints changed files.
- No assertion error.

- [ ] **Step 3: Run secret and boundary tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v
```

Expected result:

```text
OK
```

---

## Task 9: Full validation commands

**Files:**

- Modify: none
- Test: no new file; this task executes validation commands for the completed implementation.

Run these commands locally before opening the implementation PR.

- [ ] **Step 1: Parse and validate generated fake runtime artifacts**

```powershell
Remove-Item -Recurse -Force .tmp/g1h-fake-runtime -ErrorAction SilentlyContinue
$env:PYTHONPATH='src'; python -m werewolf_eval.run_g1h_fake_runtime --game-id g1h_fake_runtime --out-dir .tmp/g1h-fake-runtime
python -m json.tool .tmp/g1h-fake-runtime/prompt-manifest.json > $null
python -m json.tool .tmp/g1h-fake-runtime/game-log.json > $null
python -m json.tool .tmp/g1h-fake-runtime/decision-log.json > $null
python -m json.tool .tmp/g1h-fake-runtime/consensus-log.json > $null
python -m json.tool .tmp/g1h-fake-runtime/provider-trace.json > $null
python -m json.tool .tmp/g1h-fake-runtime/failure-audit.json > $null
```

Expected result:

- CLI prints `events_jsonl=written`, `snapshots=written`, `prompt_manifest=written`, and all standard final logs written.
- JSON tool commands exit `0`.

- [ ] **Step 2: Run focused G1h tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine tests.test_deepseek_consensus_game -v
```

Expected result:

```text
OK
```

- [ ] **Step 3: Run full test suite**

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Expected result:

```text
OK
```

The exact test count may differ from earlier PRs because G1h adds tests. The review packet must record the exact observed count.

- [ ] **Step 4: Compile Python files**

```powershell
python -m compileall src tests
```

Expected result:

```text
0 failures
```

`compileall` may print a directory/file listing. It must exit `0`.

- [ ] **Step 5: Run diff whitespace check**

```powershell
git diff --check main...HEAD
```

Expected result:

```text
(no output)
```

- [ ] **Step 6: Run changed files allowlist check**

```powershell
git diff --name-only main...HEAD | python -c "import sys; allowed=set('''src/werewolf_eval/runtime_events.py
src/werewolf_eval/run_g1h_fake_runtime.py
src/werewolf_eval/game_engine.py
src/werewolf_eval/provider_agent.py
src/werewolf_eval/run_deepseek_consensus_game.py
tests/test_runtime_events.py
tests/test_g1h_runtime_spine.py
tests/test_deepseek_consensus_game.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md'''.splitlines()); changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p not in allowed]; print('\n'.join(changed)); assert not bad, 'outside allowlist: '+repr(bad)"
```

Expected result:

- Prints only allowed files.
- Exits `0`.

- [ ] **Step 7: Run forbidden pattern scan on changed source/test lines**

```powershell
git diff main...HEAD -- src tests | python -c "import sys; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; markers=['Authorization:', 'Bearer ', 'DEEPSEEK_API_KEY=', 'sk-']; hits=[line for line in added if any(marker in line for marker in markers)]; print('\n'.join(hits)); unsafe=[line for line in hits if 'redaction' not in line.lower() and 'forbidden' not in line.lower() and 'marker' not in line.lower()]; assert not unsafe, 'unsafe forbidden pattern hits: '+repr(unsafe)"
```

Expected result:

- No unsafe committed secret values are found.
- Safe literal references inside redaction tests may be printed and must be listed in the review packet as non-secret test fixtures.
- The review packet must report the exact result as `FORBIDDEN_PATTERN_CHECK = PASS` only if every hit is a safe redaction-test marker or no hit is present.

- [ ] **Step 8: Run dependency/import diff check**

```powershell
git diff --name-only main...HEAD -- package.json package-lock.json pyproject.toml requirements.txt poetry.lock pnpm-lock.yaml yarn.lock uv.lock
```

Expected result:

```text
(no output)
```

Also run:

```powershell
git diff main...HEAD -- src tests | python -c "import sys,re; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; risky=[line for line in added if re.search(r'^\+\s*(import|from)\s+(requests|httpx|aiohttp|websockets|fastapi|flask|PySide6|PyQt6|streamlit|gradio|openai|anthropic)\b', line)]; print('\n'.join(risky)); assert not risky, 'unexpected dependency/import addition'"
```

Expected result:

```text
(no output)
```

- [ ] **Step 9: Verify no `.tmp` artifacts are staged**

```powershell
git diff --name-only --cached | python -c "import sys; bad=[p.strip() for p in sys.stdin if p.strip().startswith('.tmp/')]; assert not bad, 'staged tmp artifacts: '+repr(bad); print('NO_STAGED_TMP_ARTIFACTS')"
```

Expected result:

```text
NO_STAGED_TMP_ARTIFACTS
```

---

## Acceptance Criteria

A1. `events.jsonl` exists for the deterministic fake-provider path and contains strictly monotonic `seq` values.

A2. Every runtime event has a valid envelope: `run_id`, `seq`, `event_id`, `kind`, `round`, `phase`, `actor`, `visibility`, `payload`, `refs`, and `created_at`.

A3. Runtime events include at least these kinds in a successful fake-provider run: `run_started`, `phase_started`, `observation_built`, `provider_request_prepared`, `provider_response_received`, `provider_parse_succeeded`, `agent_action_selected`, `consensus_started`, `consensus_resolved`, `game_event_emitted`, `snapshot_written`, `artifact_written`, and `run_finalized`.

A4. Provider failure tests cover `provider_parse_failed`, `provider_action_invalid`, `provider_timeout`, and `provider_failed` events without producing forged valid final logs.

A5. Runtime event `refs` point to existing final Game Log events, Decision Log decisions, Consensus Log entries, Provider Trace request/response records, Failure Audit records, or snapshot files.

A6. God-view snapshots and role-view projection snapshots are written separately.

A7. Non-werewolf role-view projection snapshots do not leak hidden werewolf roles or private team information before public reveal.

A8. Prompt manifest exists and records prompt/profile/model/temperature/strategy metadata without secrets.

A9. Fake-provider G1h CLI runs without network access and writes the full runtime bundle.

A10. Existing Game Log / Decision Log / Consensus Log validators continue to validate final logs from the fake runtime path.

A11. Existing full unittest suite passes.

A12. Live DeepSeek execution remains opt-in only and `--write-runtime-spine` does not bypass `--allow-live-api`.

A13. No scoring formula, validator rewrite, demo renderer, generated HTML, Qt/QML client, Web observer/server, prompt editor, multi-provider arena, leaderboard, dependency manifest, or provider SDK change is introduced.

A14. No `.tmp/**` runtime artifacts are committed.

A15. Review packet exists at `.logs/review/latest/review-packet.md` and contains the required machine-generated evidence listed below.

---

## Review Packet Requirements

After implementation, the implementer must generate `.logs/review/latest/review-packet.md` before Codex review. Do not rely on oral summaries.

The packet must be compact and must include at least these machine-generated evidence blocks:

1. `git diff --name-only main...HEAD`
   - Exact changed file list.
   - Must be compared against the allowlist in this plan.

2. `git diff --stat main...HEAD`
   - Exact file-level insertion/deletion summary.
   - If changed file count exceeds 8 or changed lines exceed 500, the packet must mark the trigger and suggest B档 line ranges.

3. `git diff --check main...HEAD` result
   - Exact pass/fail result.
   - For pass, record no whitespace errors.

4. Changed files allowlist check
   - Machine check output using the allowlist command from Task 9.
   - Must report `ALLOWLIST_CHECK = PASS` or include the exact failing paths.

5. Forbidden patterns check
   - Machine scan for secret/provider/network/dependency/live-AI risk patterns.
   - Must report `FORBIDDEN_PATTERN_CHECK = PASS` only when no secret-bearing values are present.
   - If safe literal references appear in tests, list each hit and why it is not a secret value.

6. Dependency/import diff check
   - Machine output proving no dependency manifests changed.
   - Machine output proving no risky new imports such as `requests`, `httpx`, `aiohttp`, `websockets`, `fastapi`, `flask`, `PySide6`, `PyQt6`, `streamlit`, `gradio`, `openai`, or `anthropic`.

7. Test command plus exact pass/fail summary
   - Include each command from Task 9 and the exact observed summary.
   - Include exact unittest count from full discovery.
   - Include fake runtime CLI summary lines.
   - Do not paste full logs.

8. Key hunk excerpts
   - Include compact excerpts for:
     - `runtime_events.py` event envelope / writer.
     - `provider_agent.py` lifecycle emission.
     - `game_engine.py` optional runtime hook.
     - `run_deepseek_consensus_game.py` live guard and event-spine flag.
     - `run_g1h_fake_runtime.py` CLI output path.
     - main G1h tests.
   - Do not paste full files or full generated `events.jsonl`.

9. Acceptance checklist with evidence pointer
   - One row per A1-A15 acceptance item.
   - Each row must include evidence pointer such as test name, command output, artifact path, or key hunk section.
   - Status must be `PASS`, `FAIL`, or `MANUAL_REVIEW_REQUIRED`.

10. Implementer risk notes
    - Include any ambiguity, skipped live smoke, known limitation, or reviewer attention point.
    - Must explicitly state whether live provider API was run.
    - Must explicitly state that `.tmp/**` artifacts were not committed.

Minimum required packet sections should align with `docs/specs/review-packet-gate.md`:

```text
Metadata
Changed Files
Diff Stat
Diff Check
Allowed Files Check
Forbidden Patterns Check
Dependency / Import Diff
Test Summary
Key Hunks
Evidence Map
Acceptance Checklist
Implementer Risk Notes
Review Trigger Result
```

Packet line budget:

- Keep `.logs/review/latest/review-packet.md` at or below 300 lines.
- Key Hunks at or below 120 lines total.
- If packet exceeds limits, mark `PACKET_TOO_LARGE = YES` and name the exact B档 file ranges needed.

---

## Codex B档 Deep Review Risk Points

The implementer must flag these if they occur:

1. More than 8 changed files.
2. More than 500 changed lines.
3. Any change to `src/werewolf_eval/game_engine.py` that touches state transition semantics rather than observation hooks.
4. Any change to `src/werewolf_eval/provider_agent.py` that changes failure kind, failure reason, or valid action parsing behavior.
5. Any committed artifact under `.tmp/**`, `docs/generated-games/**`, `docs/demo/**`, or `docs/gold-game/**`.
6. Any change to scoring, attribution, validators, renderers, ROADMAP, TASKS, ADRs, dependency manifests, or workflow files.
7. Any new provider/network/UI imports.
8. Any raw provider response or credential-like value appearing in committed files.
9. Any role-view snapshot leak risk.
10. Any `--write-runtime-spine` behavior that weakens the existing `--allow-live-api` guard.

If any risk point is triggered, the review packet must return `NEED_DEEP_REVIEW` guidance with exact file paths and line ranges.

---

## Implementation PR Description Draft

Use this as the follow-up Implementation PR body after Claude Code implements the plan:

```markdown
## Summary

Implements G1h Live Runtime Event Spine for the fake/provider-backed single-game runtime path.

Bound Implementation Plan:

- `docs/harness/plans/2026-06-03--g1h-live-runtime-event-spine-plan.md`

## Scope

- Adds runtime event contract and append-only `events.jsonl` writer.
- Adds runtime snapshots with separate god-view and role-view projections.
- Adds prompt manifest generation with secret redaction.
- Instruments the fake/provider consensus runtime path with provider lifecycle events.
- Adds deterministic fake-provider G1h CLI for CI-safe event-spine validation.
- Preserves standard final log bundle compatibility:
  - `game-log.json`
  - `decision-log.json`
  - `consensus-log.json`
  - `provider-trace.json`
  - `failure-audit.json`

## Out of Scope

- No Qt/QML client.
- No Web observer/server.
- No prompt editor UI.
- No multi-provider arena.
- No leaderboard.
- No scoring formula changes.
- No validator rewrites.
- No demo renderer or generated HTML changes.
- No dependency or provider SDK changes.
- No CI live API calls.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine tests.test_deepseek_consensus_game -v
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
git diff --check main...HEAD
```

Observed summary:

- Exact command summaries are copied from `.logs/review/latest/review-packet.md` / Test Summary before requesting review.
- The PR is not ready for Codex review until the packet contains the exact observed test count, pass/fail status, compileall result, and diff-check result.

## Review Packet

Review packet generated at:

- `.logs/review/latest/review-packet.md`

Packet includes:

- changed files
- diff stat
- diff check
- allowlist check
- forbidden pattern scan
- dependency/import diff
- exact test summaries
- key hunks
- acceptance checklist with evidence pointers
- implementer risk notes

## Risk Notes

- Live provider API status is recorded in `.logs/review/latest/review-packet.md` / Implementer Risk Notes.
- `.tmp/**` artifact status is recorded in `.logs/review/latest/review-packet.md` / Implementer Risk Notes.
- Role-view projection leak-test result is recorded in `.logs/review/latest/review-packet.md` / Acceptance Checklist.
- Event stream is an observation layer only; final canonical logs remain Game Log / Decision Log / Consensus Log / Provider Trace / Failure Audit.
```

---

## Plan PR Validation

This plan-update PR should change only:

```text
docs/harness/plans/2026-06-03--g1h-live-runtime-event-spine-plan.md
```

Run locally:

```powershell
git diff --name-only main...HEAD
git diff --stat main...HEAD
git diff --check main...HEAD
```

Expected:

```text
docs/harness/plans/2026-06-03--g1h-live-runtime-event-spine-plan.md
```

`git diff --check main...HEAD` should produce no output.

No tests are required for this plan-only PR because no runtime code, tests, validators, generated artifacts, or fixtures are changed.
