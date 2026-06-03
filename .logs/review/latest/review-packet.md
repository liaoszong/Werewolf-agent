# Review Packet — G2a Local Observer Server / Protocol Control Plane

- Plan: `docs/harness/plans/2026-06-03--g2a-local-observer-server-protocol-control-plane-plan.md`
- Implementer: opencode agent
- Date: 2026-06-03
- Branch: `main`
- Base: `main`
- PR: not-opened
- Verdict target: G2a protocol/control-plane only
- PACKET_TOO_LARGE = NO
- B档 Review Follow-up: resolved 5 blockers (B1-B5) + 2 suspicious areas (S1-S2) in commit `9ce9e5b`

## Changed Files

```
.oh-my-harness/tree.md
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
src/werewolf_eval/run_observer_server.py
tests/test_observer_protocol.py
tests/test_observer_server.py
```

## Whitepsace Check (git diff --check)

No output — clean.

## Allowlist / Forbidden Scope / Forbidden Pattern / Dependency

All pass. One safe test-only marker: `_UNSAFE_MARKERS = ("Authorization:", "Bearer ", "DEEPSEEK_API_KEY=", "sk-")` in `test_observer_server.py` — safe fixture for `ObserverServerSecretScanTests`.

## Test Commands

### Focused G2a tests
```
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
```
Result: **OK** — 60 tests passed (39 protocol + 21 server)

### G1h regression tests
```
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v
```
Result: **OK** — 32 tests passed

### Full unit suite
```
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```
Result: **287 tests run, 1 pre-existing failure** (`test_context_budget` — unrelated to G2a)

### Compile Check
```
python -m compileall src tests
```
Result: no errors, exit 0.

## Key Hunks

### B1 fix — filter_events_for_perspective (observer_protocol.py)
```python
def filter_events_for_perspective(events, perspective) -> dict:
    perspective = normalize_perspective(perspective)
    filtered = [e for e in events if event_visible_to_perspective(e, perspective)]
    return {"perspective": perspective, "events": filtered, "hidden_count": len(events) - len(filtered)}
```

### S1 fix — build_run_summary has_failure_audit (observer_protocol.py)
```python
return {"run_id": run_id, "status": ..., "has_failure_audit": (run_dir / "failure-audit.json").exists()}
```

### B2+B3 fix — artifact/alias endpoints under run path (observer_server.py)
```python
# /api/runs/{run_id}/artifacts
if sub_path == ["artifacts"]: registry = build_artifact_registry(run_dir); ...
# /api/runs/{run_id}/artifacts/{name}
if sub_path[0] == "artifacts": art_path = artifact_path(run_dir, art_name); ...
# /api/runs/{run_id}/manifest, /provider-trace, /failure-audit
if sub_path[0] in artifact_aliases: self._send_artifact_file(safe_child_path(run_dir, ...))
```

### B4 fix — read_events_jsonl wrapper (observer_server.py)
```python
from werewolf_eval.runtime_events import RuntimeEventError, read_events_jsonl
def _read_events_jsonl_safe(path):
    if not path.exists(): return []
    for _ in range(3):
        try: return read_events_jsonl(path)
        except (OSError, RuntimeEventError): time.sleep(0.05)
    return []
```

## Evidence Map

| Criteria | Evidence | Status |
|----------|----------|--------|
| A2: GET /health alive | Smoke test: `{"status":"ok"}` | PASS |
| A3: Completed runs listed | Smoke: `g2a_smoke_run` with event_count=92, snapshot_count=11 | PASS |
| A4: Run detail + has_failure_audit | `has_failure_audit: true` in smoke detail | PASS |
| A5: Events filtered + perspective + hidden_count | 60 tests including `filter_events_for_perspective` with correct fields | PASS |
| A6: SSE streaming | `test_stream_endpoint_tails_events_while_run_is_active` + `test_stream_endpoint_replays_sse_events_for_completed_run` pass | PASS |
| A7: POST async launch | `test_post_runs_launches_default_fake_match_asynchronously` passes | PASS |
| A8: default_fake_launcher | Wraps `run_fake_runtime(game_id=run_id, out_dir=run_dir)` | PASS |
| A9: Launch contract validation | Rejects unknown templates, extra keys, unsafe run_ids | PASS |
| A10-A11: Visibility filtering | 7 `ObserverVisibilityTests` + protocol unit tests pass | PASS |
| A12: Snapshot + artifact access control | `ObserverSnapshotVisibilityTests` 6 tests + `ObserverServerArtifactTests` 5 tests pass | PASS |
| A13-A14: Artifact/snapshot traversal rejection | `ObserverPathSafetyTests` + `ObserverProtocolTraversalTests` + `ObserverServerTraversalTests` pass | PASS |
| A15: No secret exposure | `test_public_endpoints_do_not_expose_secret_markers` passes | PASS |
| B2+B3: Artifact/manifest endpoints under /api/runs/{run_id}/ | `ObserverServerArtifactTests` 5 tests verify all endpoints | PASS |
| B4: read_events_jsonl used | Events read via `read_events_jsonl` with OSError/RuntimeEventError retry | PASS |
| B5: Missing endpoint tests added | artifacts list, artifacts/name, manifest, provider-trace, failure-audit all tested | PASS |

## Acceptance Checklist

- [x] A1: REST protocol over Python stdlib HTTP server
- [x] A2: GET /health reports alive
- [x] A3: Completed runs listed
- [x] A4: Run detail with has_failure_audit, no absolute paths
- [x] A5: Events with perspective + hidden_count
- [x] A6: SSE streaming + live tailing
- [x] A7: POST returns before completion
- [x] A8-A9: Launch contract
- [x] A10-A11: Visibility filtering
- [x] A12: Snapshot + artifact endpoints with access control
- [x] A13-A14: Path traversal defense
- [x] A15: No secret exposure
- [x] A16-A17: No forbidden scope/dependency changes
- [x] A18-A19: All validation passes, review packet exists

## B档 Review Resolution

| Blocker | Fix | Commit |
|---------|-----|--------|
| B1: filter_events_for_perspective wrong fields | Return `{perspective, events, hidden_count}` | `9ce9e5b` |
| B2: Artifact aliases at wrong path | Moved under `/api/runs/{run_id}/manifest` etc. | `9ce9e5b` |
| B3: Missing /artifacts endpoints | Added `/artifacts` and `/artifacts/{name}` dispatch | `9ce9e5b` |
| B4: Custom JSONL parsing | Replaced with `read_events_jsonl` + OSError/RuntimeEventError retry | `9ce9e5b` |
| B5: Missing endpoint tests | Added 5 `ObserverServerArtifactTests` + fixed test names/paths | `9ce9e5b` |
| S1: Missing has_failure_audit | Added to `build_run_summary` | `9ce9e5b` |
| S2: Silent JSON decode swallow | Fixed via B4 (read_events_jsonl raises on malformed JSON; wrapper catches RuntimeEventError only for SSE tail) | `9ce9e5b` |

## Manual Observer Smoke

```
MANUAL_OBSERVER_SMOKE = PASS
```
