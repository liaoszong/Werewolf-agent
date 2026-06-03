# Review Packet

## Metadata
- Base: `main`
- Branch: `feat/g1h-live-runtime-event-spine`
- Generated: 2026-06-03

## Changed Files
- `.oh-my-harness/tree.md`
- `src/werewolf_eval/game_engine.py`
- `src/werewolf_eval/provider_agent.py`
- `src/werewolf_eval/run_deepseek_consensus_game.py`
- `src/werewolf_eval/run_g1h_fake_runtime.py`
- `src/werewolf_eval/runtime_events.py`
- `tests/test_deepseek_consensus_game.py`
- `tests/test_g1h_runtime_spine.py`
- `tests/test_runtime_events.py`

## Diff Stat
```
 .oh-my-harness/tree.md                           |   6 +-
 src/werewolf_eval/game_engine.py                 | 249 +++++++++-
 src/werewolf_eval/provider_agent.py              | 130 ++++++
 src/werewolf_eval/run_deepseek_consensus_game.py | 111 ++++-
 src/werewolf_eval/run_g1h_fake_runtime.py        | 211 +++++++++
 src/werewolf_eval/runtime_events.py              | 568 +++++++++++++++++++++++
 tests/test_deepseek_consensus_game.py            |  57 +++
 tests/test_g1h_runtime_spine.py                  | 412 ++++++++++++++++
 tests/test_runtime_events.py                     | 433 +++++++++++++++++
 9 files changed, 2161 insertions(+), 16 deletions(-)
```

## Diff Check
```
(clean)
```

## Allowed Files Check
ALLOWLIST_CHECK = PASS

All 9 changed files are in the plan allowlist:
- `src/werewolf_eval/runtime_events.py` (new)
- `src/werewolf_eval/run_g1h_fake_runtime.py` (new)
- `src/werewolf_eval/game_engine.py` (modify)
- `src/werewolf_eval/provider_agent.py` (modify)
- `src/werewolf_eval/run_deepseek_consensus_game.py` (modify)
- `tests/test_runtime_events.py` (new)
- `tests/test_g1h_runtime_spine.py` (new)
- `tests/test_deepseek_consensus_game.py` (modify)
- `.oh-my-harness/tree.md` (auto-generated)

## Forbidden Patterns Check
FORBIDDEN_PATTERN_CHECK = PASS

All hits are safe redaction-test markers or legitimate provider instrumentation:
- `"sk-"`, `"Bearer "` in `runtime_events.py`: SECRET_KEY_FRAGMENTS constant for redaction logic
- `"sk-"`, `"Bearer "` in `test_runtime_events.py`: test fixtures for secret detection validation
- `"Authorization"`, `"Bearer "`, `"api_key"`, `"DEEPSEEK_API_KEY"`, `"sk-"` in `test_g1h_runtime_spine.py`: secret scan test patterns
- Provider event kind strings (`"provider_request_prepared"`, etc.) in `provider_agent.py`: legitimate event instrumentation

## Dependency / Import Diff
### Dependency manifest changes
(none)

### Risky import check
(none — no requests/httpx/aiohttp/websockets/fastapi/flask/PySide6/PyQt6/streamlit/gradio/openai/anthropic imports)

## Test Summary
### `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"`
Exit: 1 (pre-existing failure only)
```
Ran 227 tests in 4.636s
FAILED (failures=1)
FAIL: test_agents_documents_context_budget_gate (test_context_budget.ContextBudgetGateDocsTests)
```
Pre-existing failure in `test_context_budget.py` — checks for "Context Budget Gate" string in AGENTS.md which was removed in a prior PR. Not related to G1h changes.

### `$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine tests.test_deepseek_consensus_game -v`
Exit: 0
```
Ran 38 tests in 0.721s
OK
```

### `$env:PYTHONPATH='src'; python -m unittest tests.test_g1h_runtime_spine.G1hFakeRuntimeCliTests -v`
Exit: 0
```
Ran 1 test in 0.161s
OK
```

### `python -m compileall src tests`
Exit: 0
```
Listing 'src'...
Listing 'src\\werewolf_eval'...
Listing 'tests'...
```

### `git diff --cached --check`
Exit: 0 (clean)

### NO_STAGED_TMP_ARTIFACTS
Exit: 0

## Key Hunks
### src/werewolf_eval/runtime_events.py (new, 568 lines)
```diff
+RUNTIME_EVENT_KINDS: tuple[str, ...] = (
+    "game_started", "round_started", "observation_delivered", ...
+    "run_started", "phase_started", "consensus_started", ...
+    "artifact_written", "run_finalized",
+)
+class RuntimeEventWriter:
+    def emit(self, kind, *, round, phase, actor, visibility, payload=None, refs=None): ...
+    def write_snapshot(self, name, snapshot, *, visibility, round, phase, actor): ...
+    def write_prompt_manifest(self, manifest): ...
```

### src/werewolf_eval/run_g1h_fake_runtime.py (new, 211 lines)
```diff
+def run_fake_runtime(*, game_id, out_dir):
+    writer = RuntimeEventWriter(run_id=game_id, out_dir=out_dir)
+    engine = GameEngine.from_config(..., runtime_events=writer)
+    outputs = engine.run(mode="g1f_provider_consensus")
+    # writes all artifacts + stdout summary
```

### src/werewolf_eval/run_deepseek_consensus_game.py
```diff
+from werewolf_eval.runtime_events import RuntimeEventWriter, build_prompt_manifest
 def run_deepseek_consensus_game_with_provider_factory(
     *, game_id, out_dir, provider_factory,
+    write_runtime_spine=False, runtime_source_label=None,
 ):
```

### src/werewolf_eval/provider_agent.py
```diff
 class ProviderAgent:
     def __init__(self, player_id, provider, ...,
+        runtime_events=None,
     ):
+        self._runtime_events = runtime_events
```

## Evidence Map
| Acceptance | Evidence | Status |
|---|---|---|
| A1 | G1hFakeRuntimeCliTests: events.jsonl exists, monotonic seq | PASS |
| A2 | RuntimeEventWriterTests: validate_event_valid, missing, invalid kind/visibility | PASS |
| A3 | G1hFakeRuntimeCliTests: 92 events with all required kinds | PASS |
| A4 | ProviderLifecycleEventTests: parse_failed, action_invalid, timeout, provider_failed | PASS |
| A5 | G1hRuntimeBundleCompatibilityTests: final logs validate through existing validators | PASS |
| A6 | runtime_events.py: build_god_snapshot + build_role_projection_snapshot separate | PASS |
| A7 | RuntimeSnapshotProjectionTests: non_wolf_projection hides werewolf roles | PASS |
| A8 | RuntimeSnapshotProjectionTests: prompt_manifest redacts secrets, has prompt_hash | PASS |
| A9 | G1hFakeRuntimeCliTests: subprocess CLI exits 0, all artifacts written | PASS |
| A10 | G1hRuntimeBundleCompatibilityTests: game_log, decision_log, consensus_log validate | PASS |
| A11 | Full suite: 227 tests, 1 pre-existing failure (test_context_budget, unrelated) | PASS* |
| A12 | DeepSeekConsensusGameCliTests: --write-runtime-spine without --allow-live-api exits nonzero | PASS |
| A13 | No scoring/validator/demo/Qt/Web/arena/leaderboard/dependency changes | PASS |
| A14 | NO_STAGED_TMP_ARTIFACTS | PASS |
| A15 | .logs/review/latest/review-packet.md exists | PASS |

## Acceptance Checklist
- [x] A1: events.jsonl with monotonic seq
- [x] A2: valid event envelope
- [x] A3: required event kinds present
- [x] A4: provider failure events covered
- [x] A5: refs point to existing IDs
- [x] A6: god/role snapshots separate
- [x] A7: role projection no leak
- [x] A8: prompt manifest no secrets
- [x] A9: fake CLI no network
- [x] A10: existing validators pass
- [x] A11: full suite passes (1 pre-existing unrelated failure)
- [x] A12: live API opt-in only
- [x] A13: no forbidden scope changes
- [x] A14: no .tmp committed
- [x] A15: review packet exists

## Implementer Risk Notes
- Pre-existing test failure: `test_agents_documents_context_budget_gate` in `test_context_budget.py` — checks for "Context Budget Gate" string in AGENTS.md. This string was removed in a prior PR and is unrelated to G1h.
- Live provider API status: not called. All tests use fake/deterministic providers.
- `.tmp/**` artifact status: `.tmp/g1h-fake-runtime/` exists locally but is not staged or committed.
- Role-view projection leak test: PASS — non-wolf projections hide werewolf roles.
- Event stream is observation layer only; final canonical logs remain Game Log / Decision Log / Consensus Log / Provider Trace / Failure Audit.
- Forbidden pattern hits are all safe: SECRET_KEY_FRAGMENTS constant, test fixtures for redaction validation, and legitimate provider event kind strings.

## Review Trigger Result
- changed_file_count=9 > 8 (B档 suggested)
- changed_lines=2177 > 500 (B档 suggested)
- key_hunks_truncated (B档 suggested)

B档 line ranges for deep review:
- `src/werewolf_eval/runtime_events.py:1-568` (new module — full review)
- `src/werewolf_eval/run_g1h_fake_runtime.py:1-211` (new CLI — full review)
- `src/werewolf_eval/game_engine.py:505-520` (runtime event emit in _emit helper)
- `src/werewolf_eval/provider_agent.py:51-180` (provider lifecycle event instrumentation)
- `src/werewolf_eval/run_deepseek_consensus_game.py:69-200` (write_runtime_spine integration)

PACKET_TOO_LARGE = NO
