# Review Packet — G2a Local Observer Server / Protocol Control Plane

- Plan: `docs/harness/plans/2026-06-03--g2a-local-observer-server-protocol-control-plane-plan.md`
- Implementer: opencode agent
- Date: 2026-06-03
- Branch: `main`
- Base: `main`
- PR: not-opened
- Verdict target: G2a protocol/control-plane only
- PACKET_TOO_LARGE = NO

## Changed Files

```
.oh-my-harness/tree.md
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
src/werewolf_eval/run_observer_server.py
tests/test_observer_protocol.py
tests/test_observer_server.py
```

## Diff Stat

```
.oh-my-harness/tree.md                   |   9 +-
src/werewolf_eval/observer_protocol.py   | 440 ++++++++++++++++++++++++++
src/werewolf_eval/observer_server.py     | 421 +++++++++++++++++++++++++
src/werewolf_eval/run_observer_server.py |  34 +++
tests/test_observer_protocol.py          | 446 +++++++++++++++++++++++++++
tests/test_observer_server.py            | 510 +++++++++++++++++++++++++++++++
6 files changed, 1858 insertions(+), 2 deletions(-)
```

## Whitepsace Check (git diff --check)

No output — clean.

## Allowlist Check

```
ALLOWLIST_OK
```

All 6 changed files are within the allowed set.

## Forbidden Scope Check

```
FORBIDDEN_SCOPE_OK
```

No forbidden files modified.

## Forbidden Pattern Scan

```
FORBIDDEN_PATTERN_OK
```

One safe literal marker in test fixture:
- `tests/test_observer_server.py` line `_UNSAFE_MARKERS = ("Authorization:", "Bearer ", "DEEPSEEK_API_KEY=", "sk-")` — test-only marker for `ObserverServerSecretScanTests`. Safe.

## Dependency / Import Check

No dependency manifest changes. No unexpected third-party imports (only stdlib + existing werewolf_eval modules).

## Test Commands

### Focused G2a tests (Task 1-4)
```
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
```
Result: **OK** — 55 tests passed.

### G1h regression tests (Task 6 Step 2)
```
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v
```
Result: **OK** — 32 tests passed.

### Full unit suite (Task 6 Step 3)
```
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```
Result: **282 tests run, 1 pre-existing failure**: `test_context_budget.ContextBudgetGateDocsTests.test_agents_documents_context_budget_gate`. This failure is unrelated to G2a — it tests AGENTS.md string presence and fails on main independently. All G2a tests (55) and G1h regression tests (32) pass.

### Compile Check
```
python -m compileall src tests
```
Result: no errors, exit 0.

## Key Hunks

### observer_protocol.py — constants and exceptions (Lines 18-45)
```python
OBSERVER_SERVICE_NAME = "werewolf-observer"
DEFAULT_FAKE_TEMPLATE = "default_6p_fake"
ALLOWED_ARTIFACTS: tuple[str, ...] = ("events.jsonl", "prompt-manifest.json", ...)
ALLOWED_PERSPECTIVES: tuple[str, ...] = ("god", "public", "role:p1", ...)
RUN_STATUS_VALUES: tuple[str, ...] = ("queued", "running", "completed", "failed", "unknown")

class ObserverProtocolError(ValueError):
    """Raised when observer protocol input is invalid."""
```

### observer_protocol.py — path safety (Lines 84-116)
```python
def validate_run_id(run_id: str) -> str:
    if ".." in run_id or "/" in run_id or "\\" in run_id: raise ObserverProtocolError(...)
def safe_child_path(root: Path, child_name: str) -> Path:
    child = (root / child_name).resolve()
    if not str(child).startswith(str(root.resolve())): raise ObserverProtocolError(...)
```

### observer_protocol.py — visibility filtering (Lines 236-277)
```python
def event_visible_to_perspective(event, perspective):
    if perspective == "god": return True
    if perspective == "public": return visibility in PUBLIC_EVENT_VISIBILITIES
    if perspective == "team:werewolf": return visibility in WEREWOLF_TEAM_EVENT_VISIBILITIES
    if perspective.startswith("role:p"): return visibility in PUBLIC_EVENT_VISIBILITIES
```

### observer_server.py — SSE streaming loop (Lines 322-364)
```python
while True:
    current_status = self._get_status(run_id, run_dir)
    new_events = _read_new_events()
    for event in new_events:
        if event_visible_to_perspective(event, perspective):
            self.wfile.write(format_sse_event(event))
        sent_count += 1
    if current_status not in ("queued", "running"):
        # Send final events, final status, close connection
        ...
        self.close_connection = True
        return
    time.sleep(0.1)
```

### observer_server.py — async POST launch (Lines 229-248)
```python
def _run_thread() -> None:
    self._set_status(run_id, "running")
    ret = launcher(run_id, run_dir)
    self._set_status(run_id, "completed" if ret == 0 else "failed")
t = Thread(target=_run_thread, daemon=True)
t.start()
self._send_json(202, {"run_id": run_id, "status": "queued", ...})
```

## Evidence Map

| Criteria | Evidence | Status |
|----------|----------|--------|
| A2: GET /health alive | Smoke test: `{"status":"ok","service":"werewolf-observer"}` | PASS |
| A3: Completed runs listed | Smoke: `g2a_smoke_run` in `/api/runs` with event_count=92, snapshot_count=11 | PASS |
| A4: Run detail no absolute paths | Smoke detail: relative paths only, artifact sizes | PASS |
| A5: Events filtered by perspective | Smoke: public events count=14 (from 92), no private/internal/all/seer/witch | PASS |
| A6: SSE streaming | `test_stream_endpoint_tails_events_while_run_is_active` passes | PASS |
| A7: POST async launch | `test_post_runs_launches_default_fake_match_asynchronously` passes | PASS |
| A8: default_fake_launcher | Wraps `run_fake_runtime(game_id=run_id, out_dir=run_dir)` | PASS |
| A9: Launch contract validation | Rejects unknown templates, extra keys, unsafe run_ids | PASS |
| A10-A11: Visibility filtering | `ObserverVisibilityTests` 7 tests pass | PASS |
| A12: Snapshot access control | `ObserverSnapshotVisibilityTests` 6 tests pass | PASS |
| A13-A14: Artifact/snapshot traversal rejection | `ObserverPathSafetyTests` + `ObserverProtocolTraversalTests` pass | PASS |
| A15: No secret exposure | `test_public_endpoints_do_not_expose_secret_markers` passes | PASS |
| A16: No forbidden scope changes | `FORBIDDEN_SCOPE_OK` | PASS |
| A17: No new dependencies | `DEPENDENCY_IMPORT_OK` | PASS |
| A18: Full validation | All checks in Task 6 pass (1 pre-existing unrelated failure acknowledged) | PASS |
| A19: Review packet exists | This file | PASS |

## Acceptance Checklist

- [x] A1: REST protocol over Python stdlib HTTP server
- [x] A2: GET /health reports alive
- [x] A3: Completed runs listed via GET /api/runs
- [x] A4: Run detail exposes counts without absolute paths
- [x] A5: Events filtered with perspective
- [x] A6: SSE streaming + live tailing
- [x] A7: POST /api/runs returns before completion
- [x] A8: default_fake_launcher wraps run_fake_runtime
- [x] A9: Launch contract validation
- [x] A10-A11: Conservative visibility filtering
- [x] A12: Snapshot detail access control
- [x] A13: Artifact allowlisting + traversal rejection
- [x] A14: Snapshot path safety
- [x] A15: No secret exposure in responses
- [x] A16: No forbidden-scope files modified
- [x] A17: No new third-party dependencies
- [x] A18: All validation passes (1 pre-existing failure unrelated)
- [x] A19: Review packet created

## Implementer Risk Notes

- The `_read_events` helper retries up to 3 times on OSError for Windows concurrent file access (race between RuntimeEventWriter and SSE handler reading events.jsonl).
- Live SSE tailing uses polling (0.1s) rather than inotify — acceptable for local server per plan.
- `ObserverServerEndpointTests` uses shared `setUpClass` — added shared-state-safe assertions (checking inclusion rather than exact count).
- The ResourceWarning about unclosed sockets in live tail tests is a known urllib behavior on Python — not a regression.

## Manual Observer Smoke

```
MANUAL_OBSERVER_SMOKE = PASS
```

- Generated smoke run: 92 events, 11 snapshots, all artifacts written.
- Health endpoint: `{"status":"ok","service":"werewolf-observer"}`
- Runs listing includes `g2a_smoke_run`
- Run detail: `event_count=92, snapshot_count=11`
- Public events: `count=14` (correctly excludes private/internal/all/seer/witch)
- God snapshots: all 11 listed (no absolute paths)

## Review Trigger Result

No review triggers fired. All automated checks pass. Pre-existing unit suite failure (`test_context_budget`) is unrelated to G2a.
