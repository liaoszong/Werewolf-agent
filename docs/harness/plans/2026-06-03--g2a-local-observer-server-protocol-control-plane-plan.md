# G2a Local Observer Server / Protocol Control Plane Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Build the G2a local observer server that exposes G1h runtime event-spine runs through a client-agnostic REST + streaming protocol, with a minimum default-match launch contract and visibility-trust slices from day one.

**Architecture:** Add a narrow Python-standard-library observer layer around completed G1h artifacts. The observer server reads and serves run bundles from a local runs directory, can launch the deterministic fake-provider default 6-player match through the existing G1h fake runtime, streams runtime events through Server-Sent Events, and never exposes Python runtime objects directly to clients. It is a protocol/control-plane milestone, not a Qt/Web UI or profile editor milestone.

**Tech Stack:** Python standard library only: `http.server`, `socketserver`/`ThreadingHTTPServer`, `threading`, `json`, `pathlib`, `urllib.request` in tests, `unittest`, existing `werewolf_eval.runtime_events.read_events_jsonl`, existing `werewolf_eval.run_g1h_fake_runtime.run_fake_runtime`. No FastAPI, Flask, websockets, requests, PySide, Qt, or dependency manifest changes.

---

## Context Basis

Current route facts:

- `docs/ROADMAP.md` says G1h Live Runtime Event Spine is completed and the next implementation candidate is G2a Local Observer Server / Protocol Control Plane.
- `docs/TASKS.md` marks G2a as `next_candidate` with REST/stream protocol, run/status/artifact/snapshot/event query and subscription, minimum match/profile contract seed for default-template launch, and visibility trust slices from day one.
- `docs/harness/designs/2026-06-03--live-ai-werewolf-experiment-platform-charter.md` defines Phase C as G2a Local Observer Server / Protocol Control Plane and requires compatibility with completed-run replay and live-run observation.
- G1h artifacts already include `events.jsonl`, runtime snapshots, prompt manifest, provider lifecycle events, final logs, provider trace, and failure audit.
- `clients/qt_observer` exists only as a Qt6 Quick scaffold for future G2b. G2a must not modify it.

Recommended next development point:

```text
G2a Local Observer Server / Protocol Control Plane
```

Reason:

```text
G1h exposes a stable event spine and run bundle, but clients still have no protocol boundary. G2a is the required bridge before Qt/Web observer clients, replay/live dual mode, profile UI, or evaluation platform work can proceed safely.
```

## Scope Summary

G2a includes:

- Local observer protocol helpers for run discovery, run metadata, artifact registry, safe path resolution, visibility filtering, and SSE event formatting.
- Local HTTP server with REST endpoints for health, run listing, run status, events, snapshots, artifacts, prompt manifest, provider trace, failure audit, and default fake-match launch.
- A deterministic, CI-safe minimum match/profile contract seed for launching a default 6-player fake-provider match.
- Streaming endpoint that emits event-spine events from `events.jsonl` using SSE over local HTTP.
- Tests that use only temporary directories, fake G1h runtime output, localhost HTTP, and Python standard library clients.
- A compact review packet for Codex省余额审查.

G2a does not include:

- Qt/QML client implementation.
- Web observer UI.
- Full prompt/profile editor.
- Multi-provider arena.
- Human-vs-AI UI.
- Leaderboard or score formula changes.
- Runtime game behavior changes.
- Provider adapter behavior changes.
- Generated demo HTML changes.
- Generated game fixture updates.
- Live API calls.

---

## File Plan

### Create

- `src/werewolf_eval/observer_protocol.py`
  - Pure helper module for observer contracts.
  - Defines protocol constants, allowed artifact names, match/profile seed shape, run metadata builder, artifact registry, visibility filtering, SSE formatting, and safe path validation.
  - No sockets, no background threads, no CLI parsing.

- `src/werewolf_eval/observer_server.py`
  - Local HTTP server implementation.
  - Uses `ThreadingHTTPServer` and `BaseHTTPRequestHandler`.
  - Serves REST JSON endpoints, artifact JSON, and SSE stream.
  - Launches default fake-provider run through existing `run_fake_runtime()` in a background thread.

- `src/werewolf_eval/run_observer_server.py`
  - CLI entry point.
  - Starts the observer server on `127.0.0.1` by default.
  - Does not auto-launch live provider runs.

- `tests/test_observer_protocol.py`
  - Unit tests for safe path handling, run discovery, metadata, artifact registry, visibility filters, SSE format, and minimum match/profile seed validation.

- `tests/test_observer_server.py`
  - Integration tests for local HTTP endpoints and default fake-run launch using temporary directories and localhost port `0`.

### Modify

- `.logs/review/latest/review-packet.md`
  - Implementation evidence only.

- `.oh-my-harness/tree.md`
  - Refresh only via `node .codex/hooks/tree.mjs --force` because new files are created.

### Do Not Modify

- `clients/qt_observer/**`
- `README.md`
- `docs/PRODUCT_ONE_PAGER.md`
- `docs/ROADMAP.md`
- `docs/TASKS.md`
- `docs/adr/**`
- `docs/demo/**`
- `docs/generated-games/**`
- `docs/gold-game/**`
- `src/werewolf_eval/game_engine.py`
- `src/werewolf_eval/provider_agent.py`
- `src/werewolf_eval/run_g1h_fake_runtime.py`
- `src/werewolf_eval/run_deepseek_consensus_game.py`
- `src/werewolf_eval/scoring.py`
- `src/werewolf_eval/score_game.py`
- `src/werewolf_eval/attribution.py`
- Existing validators.
- Dependency manifests.
- GitHub workflow files.

---

## Allowlist

The implementation PR may change only these paths:

```text
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
src/werewolf_eval/run_observer_server.py
tests/test_observer_protocol.py
tests/test_observer_server.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

`.oh-my-harness/tree.md` is allowed only if refreshed by:

```powershell
node .codex/hooks/tree.mjs --force
```

`.logs/review/latest/review-packet.md` is allowed only for compact implementation evidence.

## Forbidden Scope

The implementation must not:

- Modify `clients/qt_observer/**`.
- Modify README, ROADMAP, TASKS, PRODUCT_ONE_PAGER, ADRs, historical plans, historical reviews, demo HTML, generated games, gold-game fixtures, semantic-labeling docs, or `.github/**`.
- Modify runtime gameplay behavior, scoring, attribution, provider adapters, validators, G1h fake runtime, or DeepSeek live runtime.
- Add dependency manifests or edit dependency manifests such as `pyproject.toml`, `requirements.txt`, `poetry.lock`, `uv.lock`, `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, or Qt/CMake dependency files outside the allowlist.
- Import `requests`, `httpx`, `aiohttp`, `websockets`, `fastapi`, `flask`, `starlette`, `uvicorn`, `openai`, `anthropic`, `PySide6`, `PyQt6`, `streamlit`, or `gradio`.
- Call live provider APIs in tests or server defaults.
- Expose raw secrets or local credential values in JSON responses, SSE events, or review evidence.
- Serve arbitrary local filesystem paths outside the configured runs directory.
- Treat `clients/qt_observer` scaffold as completed G2b.

---

## Protocol Contract For G2a

### Runs Directory

The server owns one local runs directory:

```text
.runs/
```

Local tests must use `TemporaryDirectory()` and must not write `.runs/` or `.tmp/` in the repository.

Each run directory is expected to contain some or all of:

```text
events.jsonl
snapshots/*.json
prompt-manifest.json
game-log.json
decision-log.json
consensus-log.json
provider-trace.json
failure-audit.json
```

### Minimum Match/Profile Contract Seed

G2a introduces only a minimum launch contract, not a full profile editor.

Accepted launch body:

```json
{
  "template": "default_6p_fake",
  "run_id": "optional-safe-run-id",
  "mode": "fake"
}
```

Rules:

- `template` must be exactly `default_6p_fake`.
- `mode` must be exactly `fake` or omitted.
- `run_id` may be omitted; server generates a safe deterministic prefix plus suffix when omitted.
- `run_id` must match `^[A-Za-z0-9_.-]+$` and must not contain path separators.
- The server must launch only the existing deterministic fake G1h runtime.
- The launch path must not require API keys, network, provider secrets, or live API flags.
- This seed is intentionally not a full prompt/profile editor.

### Required REST Endpoints

All responses use UTF-8 JSON unless otherwise stated.

```text
GET  /health
GET  /api/runs
POST /api/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events?perspective=god|public|role:p1|role:p2|role:p3|role:p4|role:p5|role:p6|team:werewolf
GET  /api/runs/{run_id}/stream?perspective=god|public|role:p1|role:p2|role:p3|role:p4|role:p5|role:p6|team:werewolf
GET  /api/runs/{run_id}/snapshots
GET  /api/runs/{run_id}/artifacts
GET  /api/runs/{run_id}/artifacts/{artifact_name}
GET  /api/runs/{run_id}/manifest
GET  /api/runs/{run_id}/provider-trace
GET  /api/runs/{run_id}/failure-audit
```

Allowed `artifact_name` values:

```text
events.jsonl
prompt-manifest.json
game-log.json
decision-log.json
consensus-log.json
provider-trace.json
failure-audit.json
```

Endpoint behavior:

- `GET /health` returns `200` and `{"status":"ok","service":"werewolf-observer"}`.
- `GET /api/runs` returns an ordered list of run summaries discovered under the runs directory.
- `POST /api/runs` launches a default fake run and returns `201` if it completes synchronously or `202` if still running. Either result is acceptable if the response includes `run_id`, `status`, and `template`.
- `GET /api/runs/{run_id}` returns status, artifact availability, event count, snapshot count, source labels if available, and paths relative to the run directory only.
- `GET /events` returns visibility-filtered events as a JSON array.
- `GET /stream` returns `text/event-stream` with one SSE event per runtime event. For completed runs it may replay the current event file and close.
- `GET /snapshots` returns snapshot file metadata only, not arbitrary file paths.
- `GET /artifacts` returns allowed artifact names and availability.
- Artifact endpoints must return `404` for missing artifacts and `400` or `404` for unknown artifact names.

### Visibility Trust Slices

G2a does not implement the full Phase E trust layer, but it must start with conservative protocol slices.

Perspectives:

```text
god
public
role:p1
role:p2
role:p3
role:p4
role:p5
role:p6
team:werewolf
```

Rules:

- `god` may see all runtime events.
- `public` may see only events whose event-spine visibility is public-like.
- `role:pN` may see public-like events and role/snapshot metadata for that player only. It must not receive events marked internal/private/all-god-only by convenience.
- `team:werewolf` may see public-like events and existing werewolf-team events.
- Unknown perspectives return `400`.
- Filtering must be conservative. If event visibility cannot be safely mapped, hide it from non-god perspectives.
- Responses must include a `perspective` field and, when events are hidden, a `hidden_count` field.

Current G1h event visibilities include values such as `public`, `private`, `internal`, `all`, `seer`, `witch`, and `werewolf_team`. G2a must map them through an observer protocol helper rather than modifying G1h event constants in this milestone.

---

## Task 1: Add observer protocol helpers

**Files:**

- Create: `src/werewolf_eval/observer_protocol.py`
- Test: `tests/test_observer_protocol.py`

- [ ] **Step 1: Create `observer_protocol.py` with constants and exceptions**

Implement these public names:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

OBSERVER_SERVICE_NAME = "werewolf-observer"
DEFAULT_FAKE_TEMPLATE = "default_6p_fake"
DEFAULT_FAKE_MODE = "fake"
ALLOWED_ARTIFACTS: tuple[str, ...] = (
    "events.jsonl",
    "prompt-manifest.json",
    "game-log.json",
    "decision-log.json",
    "consensus-log.json",
    "provider-trace.json",
    "failure-audit.json",
)
ALLOWED_PERSPECTIVES: tuple[str, ...] = (
    "god",
    "public",
    "role:p1",
    "role:p2",
    "role:p3",
    "role:p4",
    "role:p5",
    "role:p6",
    "team:werewolf",
)

class ObserverProtocolError(ValueError):
    """Raised when observer protocol input is invalid."""
```

Constraints:

- Use Python standard library only.
- Do not import networking libraries here.
- Do not import Qt or client code.

- [ ] **Step 2: Add safe ID and path helpers**

Implement:

```python
def validate_run_id(run_id: str) -> str: ...
def safe_child_path(root: Path, child_name: str) -> Path: ...
def artifact_path(run_dir: Path, artifact_name: str) -> Path: ...
```

Required behavior:

- `validate_run_id()` accepts only non-empty IDs matching ASCII letters, digits, `_`, `-`, and `.`.
- Reject `..`, `/`, `\\`, empty values, and path-like input.
- `safe_child_path()` returns a resolved child path under `root` and rejects traversal.
- `artifact_path()` accepts only `ALLOWED_ARTIFACTS` and returns a path under the run directory.

- [ ] **Step 3: Add run metadata and artifact registry helpers**

Implement:

```python
def list_run_dirs(runs_dir: Path) -> list[Path]: ...
def build_artifact_registry(run_dir: Path) -> dict[str, dict[str, object]]: ...
def build_run_summary(run_dir: Path) -> dict[str, object]: ...
def build_run_detail(run_dir: Path) -> dict[str, object]: ...
```

Required behavior:

- `list_run_dirs()` returns sorted child directories only.
- `build_artifact_registry()` reports only allowed artifacts with `exists`, `name`, and relative `path` fields.
- `build_run_summary()` includes `run_id`, `status`, `event_count`, `snapshot_count`, `artifacts`, and `has_failure_audit`.
- `build_run_detail()` includes all summary fields plus `snapshots` list with relative names under `snapshots/`.
- Missing artifacts are represented as unavailable, not as errors.

- [ ] **Step 4: Add launch contract parser**

Implement:

```python
def parse_launch_request(payload: dict[str, object]) -> dict[str, object]: ...
def generate_run_id(prefix: str = "g2a_default_6p_fake") -> str: ...
```

Required behavior:

- Accept only `template`, `run_id`, and `mode` keys.
- Default `template` to `default_6p_fake` when omitted.
- Default `mode` to `fake` when omitted.
- Reject any template other than `default_6p_fake`.
- Reject any mode other than `fake`.
- Validate provided `run_id` through `validate_run_id()`.
- Generated run IDs must pass `validate_run_id()`.

- [ ] **Step 5: Add visibility filtering and SSE formatting**

Implement:

```python
def normalize_perspective(perspective: str | None) -> str: ...
def event_visible_to_perspective(event: dict[str, object], perspective: str) -> bool: ...
def filter_events_for_perspective(events: list[dict[str, object]], perspective: str) -> dict[str, object]: ...
def format_sse_event(event: dict[str, object]) -> bytes: ...
```

Required behavior:

- Missing perspective defaults to `god` for local audit tools.
- Unknown perspectives raise `ObserverProtocolError`.
- `god` sees all events.
- `public` sees only `visibility == "public"`.
- `team:werewolf` sees `public` and `werewolf_team`.
- `role:pN` sees `public` plus role-specific visibility if current G1h event data safely supports it. In this milestone, role views must not receive `private`, `internal`, or `all` events.
- `filter_events_for_perspective()` returns:

```python
{
    "perspective": perspective,
    "events": visible_events,
    "hidden_count": len(events) - len(visible_events),
}
```

- `format_sse_event()` emits bytes in this shape:

```text
event: runtime_event
data: {JSON object}\n\n
```

Use `json.dumps(..., ensure_ascii=False, sort_keys=True)`.

- [ ] **Step 6: Add protocol unit tests**

Create `tests/test_observer_protocol.py` with these test classes and methods:

```python
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from werewolf_eval.observer_protocol import (
    ObserverProtocolError,
    artifact_path,
    build_artifact_registry,
    build_run_detail,
    build_run_summary,
    event_visible_to_perspective,
    filter_events_for_perspective,
    format_sse_event,
    list_run_dirs,
    parse_launch_request,
    safe_child_path,
    validate_run_id,
)

class ObserverPathSafetyTests(unittest.TestCase):
    def test_validate_run_id_rejects_path_traversal(self) -> None: ...
    def test_artifact_path_rejects_unknown_artifact(self) -> None: ...
    def test_safe_child_path_stays_under_root(self) -> None: ...

class ObserverRunSummaryTests(unittest.TestCase):
    def test_build_run_summary_counts_events_and_snapshots(self) -> None: ...
    def test_build_artifact_registry_reports_allowed_artifacts_only(self) -> None: ...

class ObserverLaunchContractTests(unittest.TestCase):
    def test_parse_launch_request_accepts_default_fake_template(self) -> None: ...
    def test_parse_launch_request_rejects_unknown_template(self) -> None: ...
    def test_parse_launch_request_rejects_extra_keys(self) -> None: ...

class ObserverVisibilityTests(unittest.TestCase):
    def test_god_sees_all_events(self) -> None: ...
    def test_public_hides_private_internal_and_all_events(self) -> None: ...
    def test_werewolf_team_sees_public_and_werewolf_team_events(self) -> None: ...
    def test_unknown_perspective_is_rejected(self) -> None: ...
    def test_sse_format_contains_event_and_data_lines(self) -> None: ...
```

Test fixture events should be minimal dictionaries with `visibility` values `public`, `private`, `internal`, `all`, and `werewolf_team`. Do not read repository artifacts.

- [ ] **Step 7: Run protocol focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol -v
```

Expected result:

```text
OK
```

The exact test count must be recorded in the review packet.

---

## Task 2: Add local observer HTTP server

**Files:**

- Create: `src/werewolf_eval/observer_server.py`
- Modify: `tests/test_observer_server.py`
- Test: `tests/test_observer_server.py`

- [ ] **Step 1: Create `observer_server.py` server state and JSON helpers**

Implement public names:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

@dataclass
class ObserverServerState:
    runs_dir: Path
    run_status: dict[str, str] = field(default_factory=dict)

class ObserverRequestHandler(BaseHTTPRequestHandler): ...

def create_observer_server(host: str, port: int, runs_dir: Path) -> ThreadingHTTPServer: ...
```

Implementation requirements:

- Store `ObserverServerState` on the `ThreadingHTTPServer` instance as `server.observer_state`.
- All JSON responses must include `Content-Type: application/json; charset=utf-8`.
- Disable noisy request logging by overriding `log_message()` to no-op unless a local debug flag is added later. Do not add a debug flag in this milestone.
- Use `urllib.parse.urlparse` and `parse_qs` for routes.

- [ ] **Step 2: Implement error responses and request body parsing**

Add helper methods on `ObserverRequestHandler`:

```python
def _send_json(self, status: int, payload: dict[str, object] | list[object]) -> None: ...
def _send_error_json(self, status: int, code: str, message: str) -> None: ...
def _read_json_body(self) -> dict[str, object]: ...
```

Required behavior:

- Invalid JSON body returns `400` with `code = "invalid_json"`.
- Protocol validation errors return `400` with `code = "invalid_request"`.
- Missing runs/artifacts return `404` with stable JSON error shape.
- Error response shape:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "..."
  }
}
```

- [ ] **Step 3: Implement GET endpoints**

Implement `do_GET()` dispatch for:

```text
/health
/api/runs
/api/runs/{run_id}
/api/runs/{run_id}/events
/api/runs/{run_id}/stream
/api/runs/{run_id}/snapshots
/api/runs/{run_id}/artifacts
/api/runs/{run_id}/artifacts/{artifact_name}
/api/runs/{run_id}/manifest
/api/runs/{run_id}/provider-trace
/api/runs/{run_id}/failure-audit
```

Required behavior:

- `/health` returns status `ok` and service name.
- `/api/runs` lists run summaries from the configured runs directory.
- `/api/runs/{run_id}` returns run detail.
- `/events` reads `events.jsonl` through `read_events_jsonl()` and applies `filter_events_for_perspective()`.
- `/stream` returns `text/event-stream; charset=utf-8` and writes formatted SSE bytes for visible events. For completed runs, replay current events and close.
- `/snapshots` returns snapshot metadata from `build_run_detail()`.
- `/artifacts` returns `build_artifact_registry()`.
- Artifact aliases:
  - `/manifest` serves `prompt-manifest.json`.
  - `/provider-trace` serves `provider-trace.json`.
  - `/failure-audit` serves `failure-audit.json`.
- Do not serve files outside allowed artifacts.

- [ ] **Step 4: Implement POST default fake run launch**

Implement `do_POST()` for:

```text
/api/runs
```

Required behavior:

- Parse body through `parse_launch_request()`.
- Create run directory under `runs_dir / run_id`.
- Call existing:

```python
from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime
```

- The first implementation may run the fake runtime synchronously inside the request because it is deterministic, local, and fast. If the implementer uses a background thread instead, tests must wait for completion by polling `/api/runs/{run_id}`.
- Response must include:

```json
{
  "run_id": "...",
  "template": "default_6p_fake",
  "mode": "fake",
  "status": "completed",
  "artifacts": {...}
}
```

- If `run_fake_runtime()` returns nonzero, return `500` with `code = "run_failed"`, keep failure artifacts if written, and do not forge success.
- Do not call DeepSeek or any live provider path.

- [ ] **Step 5: Implement server integration tests**

Create `tests/test_observer_server.py` with helper functions:

```python
import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from werewolf_eval.observer_server import create_observer_server
from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime


def _start_server(runs_dir: Path): ...
def _request_json(base_url: str, path: str, *, method: str = "GET", payload: dict[str, object] | None = None) -> object: ...
def _request_text(base_url: str, path: str) -> str: ...
```

Required helper behavior:

- `_start_server()` must bind host `127.0.0.1` and port `0`, start `serve_forever()` in a daemon thread, and return `(server, base_url, thread)`.
- Tests must call `server.shutdown()` and `server.server_close()` in `finally` blocks.
- Use `urllib.request` only; do not use `requests`.

Add tests:

```python
class ObserverServerEndpointTests(unittest.TestCase):
    def test_health_endpoint_returns_ok(self) -> None: ...
    def test_list_runs_and_run_detail_for_existing_fake_runtime(self) -> None: ...
    def test_events_endpoint_filters_public_perspective(self) -> None: ...
    def test_stream_endpoint_replays_sse_events(self) -> None: ...
    def test_artifact_endpoint_rejects_unknown_artifact(self) -> None: ...
    def test_post_runs_launches_default_fake_match(self) -> None: ...
    def test_post_runs_rejects_unknown_template(self) -> None: ...
```

Test details:

- For existing-run tests, create a temp run directory and call `run_fake_runtime(game_id="server_existing", out_dir=run_dir)`, asserting return code `0`.
- `/api/runs` must include `server_existing`.
- `/api/runs/server_existing` must report `event_count > 0`, `snapshot_count > 0`, and available artifacts.
- `/api/runs/server_existing/events?perspective=public` must return `perspective = "public"` and must not include events with `visibility` `private`, `internal`, or `all`.
- `/stream?perspective=god` response text must contain `event: runtime_event` and `data: `.
- Unknown artifact should raise `urllib.error.HTTPError` with code `400` or `404`.
- `POST /api/runs` with `{"template":"default_6p_fake","run_id":"launch_test","mode":"fake"}` must return status `completed` and write `events.jsonl`, `prompt-manifest.json`, `game-log.json`, `decision-log.json`, `provider-trace.json`, and `failure-audit.json` under the temp runs directory.

- [ ] **Step 6: Run server tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_server -v
```

Expected result:

```text
OK
```

The exact test count must be recorded in the review packet.

---

## Task 3: Add observer server CLI

**Files:**

- Create: `src/werewolf_eval/run_observer_server.py`
- Modify: `tests/test_observer_server.py`
- Test: `tests/test_observer_server.py`

- [ ] **Step 1: Implement CLI entry point**

Create `src/werewolf_eval/run_observer_server.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from werewolf_eval.observer_server import create_observer_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Werewolf observer server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runs-dir", default=".runs")
    args = parser.parse_args()

    server = create_observer_server(args.host, args.port, Path(args.runs_dir))
    host, port = server.server_address[:2]
    print(f"observer_server=started")
    print(f"host={host}")
    print(f"port={port}")
    print(f"runs_dir={Path(args.runs_dir)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("observer_server=stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Required behavior:

- Default host is `127.0.0.1`, not `0.0.0.0`.
- Default runs dir is `.runs`.
- CLI does not auto-launch a run.
- CLI does not call live providers.

- [ ] **Step 2: Add CLI smoke test without hanging**

Extend `tests/test_observer_server.py` with:

```python
class ObserverServerCliTests(unittest.TestCase):
    def test_cli_help_lists_runs_dir_host_and_port(self) -> None: ...
```

Use:

```python
subprocess.run(
    [sys.executable, "-m", "werewolf_eval.run_observer_server", "--help"],
    env={**os.environ, "PYTHONPATH": "src"},
    capture_output=True,
    text=True,
    check=False,
)
```

Expected assertions:

- Return code is `0`.
- stdout contains `--runs-dir`.
- stdout contains `--host`.
- stdout contains `--port`.

Do not start a long-running CLI process in tests.

- [ ] **Step 3: Run CLI-inclusive tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_server -v
```

Expected result:

```text
OK
```

---

## Task 4: Add security, provenance, and no-secret tests

**Files:**

- Modify: `tests/test_observer_protocol.py`
- Modify: `tests/test_observer_server.py`
- Test: both observer test files

- [ ] **Step 1: Add path traversal tests**

Extend `tests/test_observer_protocol.py`:

```python
class ObserverTraversalDefenseTests(unittest.TestCase):
    def test_run_id_rejects_parent_directory_segments(self) -> None: ...
    def test_artifact_path_rejects_nested_paths(self) -> None: ...
```

Inputs to reject:

```text
../x
..\\x
x/y
x\\y

```

- [ ] **Step 2: Add server traversal endpoint test**

Extend `tests/test_observer_server.py`:

```python
class ObserverServerSecurityTests(unittest.TestCase):
    def test_server_does_not_serve_path_traversal_artifact(self) -> None: ...
```

Request path example:

```text
/api/runs/security_run/artifacts/..%2F..%2FREADME.md
```

Expected:

- HTTP error status is `400` or `404`.
- Response body must not contain README content.

- [ ] **Step 3: Add no-secret response scan test**

Extend `tests/test_observer_server.py`:

```python
class ObserverServerSecretScanTests(unittest.TestCase):
    def test_public_endpoints_do_not_expose_secret_markers(self) -> None: ...
```

Procedure:

- Generate a temp fake run with `run_fake_runtime()`.
- Call `/api/runs`, `/api/runs/{run_id}`, `/events?perspective=god`, `/artifacts`, `/manifest`, `/provider-trace`, and `/failure-audit`.
- Concatenate response text.
- Fail if unsafe secret markers appear:

```text
Authorization:
Bearer 
DEEPSEEK_API_KEY=
sk-
```

Safe literal references inside tests must be described in the review packet as test-only forbidden-pattern markers.

- [ ] **Step 4: Run security tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
```

Expected result:

```text
OK
```

---

## Task 5: Manual local smoke commands for review evidence

**Files:**

- Modify: none
- Test: local command evidence only

- [ ] **Step 1: Generate one local fake run for observer smoke**

Run:

```powershell
Remove-Item -Recurse -Force .tmp/g2a-observer-smoke -ErrorAction SilentlyContinue
$env:PYTHONPATH='src'; python -m werewolf_eval.run_g1h_fake_runtime --game-id g2a_smoke_run --out-dir .tmp/g2a-observer-smoke/runs/g2a_smoke_run
```

Expected stdout includes:

```text
g1h_fake_runtime_game_id=g2a_smoke_run
events_jsonl=written
snapshots=written
prompt_manifest=written
game_log=written
decision_log=written
provider_trace=written
failure_audit=written
live_api=not_used
```

Do not commit `.tmp/g2a-observer-smoke/**`.

- [ ] **Step 2: Start observer server manually for smoke**

Run in one terminal:

```powershell
$env:PYTHONPATH='src'; python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .tmp/g2a-observer-smoke/runs
```

Expected stdout includes:

```text
observer_server=started
host=127.0.0.1
port=8765
runs_dir=.tmp/g2a-observer-smoke/runs
```

Stop it with `Ctrl+C` after Step 3.

- [ ] **Step 3: Query local endpoints manually**

Run in another terminal while the server is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/api/runs
Invoke-RestMethod http://127.0.0.1:8765/api/runs/g2a_smoke_run
Invoke-RestMethod 'http://127.0.0.1:8765/api/runs/g2a_smoke_run/events?perspective=public'
```

Expected:

- Health response has `status = ok`.
- Runs response includes `g2a_smoke_run`.
- Run detail has `event_count > 0` and `snapshot_count > 0`.
- Public events response includes `perspective = public` and does not include private/internal events.

- [ ] **Step 4: Record manual smoke status**

In review packet, record:

```text
MANUAL_OBSERVER_SMOKE = PASS
```

only if Steps 1-3 succeed. Otherwise record exact failing command and result.

---

## Task 6: Full validation commands

**Files:**

- Modify: `.logs/review/latest/review-packet.md`
- Modify: `.oh-my-harness/tree.md` through tree hook if needed

- [ ] **Step 1: Run focused G2a tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
```

Expected result:

```text
OK
```

Record exact test count.

- [ ] **Step 2: Run G1h regression tests touched by server launch path**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v
```

Expected result:

```text
OK
```

Reason:

```text
G2a consumes G1h events.jsonl, snapshots, and fake runtime output. These tests prove the event spine contract still passes after adding observer protocol readers.
```

- [ ] **Step 3: Run full unit suite**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Expected result:

```text
OK
```

If a known pre-existing unrelated failure appears, the implementer must include:

- exact failing test name,
- proof it fails on `main` or was documented before this change,
- focused G2a test pass summary.

- [ ] **Step 4: Compile Python files**

Run:

```powershell
python -m compileall src tests
```

Expected result:

```text
0 failures
```

`compileall` may print file names; it must exit `0`.

- [ ] **Step 5: Run diff whitespace check**

Run:

```powershell
git diff --check main...HEAD
```

Expected result:

```text
(no output)
```

- [ ] **Step 6: Run changed files allowlist check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; allowed=set('''src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
src/werewolf_eval/run_observer_server.py
tests/test_observer_protocol.py
tests/test_observer_server.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md'''.splitlines()); changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p not in allowed]; print('\n'.join(changed)); assert not bad, 'outside allowlist: '+repr(bad)"
```

Expected result:

- Prints only allowed files.
- Exits `0`.

- [ ] **Step 7: Run forbidden-scope check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; forbidden_prefixes=('clients/qt_observer/','docs/demo/','docs/generated-games/','docs/gold-game/','docs/adr/','.github/','.agents/skills/'); forbidden_exact={'README.md','docs/ROADMAP.md','docs/TASKS.md','docs/PRODUCT_ONE_PAGER.md','src/werewolf_eval/game_engine.py','src/werewolf_eval/provider_agent.py','src/werewolf_eval/run_g1h_fake_runtime.py','src/werewolf_eval/run_deepseek_consensus_game.py','src/werewolf_eval/scoring.py','src/werewolf_eval/score_game.py'}; changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p in forbidden_exact or p.startswith(forbidden_prefixes)]; print('\n'.join(bad)); assert not bad, 'forbidden scope changed: '+repr(bad)"
```

Expected result:

```text
(no output)
```

- [ ] **Step 8: Run forbidden pattern scan on added source/test lines**

Run:

```powershell
git diff main...HEAD -- src tests | python -c "import sys; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; markers=['Authorization:', 'Bearer ', 'DEEPSEEK_API_KEY=', 'sk-']; hits=[line for line in added if any(marker in line for marker in markers)]; print('\n'.join(hits)); unsafe=[line for line in hits if 'secret' not in line.lower() and 'marker' not in line.lower() and 'scan' not in line.lower() and 'forbidden' not in line.lower()]; assert not unsafe, 'unsafe forbidden pattern hits: '+repr(unsafe)"
```

Expected result:

- No unsafe committed secret values.
- Safe literal markers inside secret-scan tests may print and must be listed in the review packet as safe test fixtures.

- [ ] **Step 9: Run dependency/import diff check**

Run:

```powershell
git diff --name-only main...HEAD -- package.json package-lock.json pyproject.toml requirements.txt poetry.lock pnpm-lock.yaml yarn.lock uv.lock CMakeLists.txt clients/qt_observer/CMakeLists.txt
```

Expected result:

```text
(no output)
```

Also run:

```powershell
git diff main...HEAD -- src tests | python -c "import sys,re; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; risky=[line for line in added if re.search(r'^\+\s*(import|from)\s+(requests|httpx|aiohttp|websockets|fastapi|flask|starlette|uvicorn|openai|anthropic|PySide6|PyQt6|streamlit|gradio)\b', line)]; print('\n'.join(risky)); assert not risky, 'unexpected dependency/import addition'"
```

Expected result:

```text
(no output)
```

- [ ] **Step 10: Verify no `.tmp` or `.runs` artifacts are staged**

Run:

```powershell
git diff --name-only --cached | python -c "import sys; bad=[p.strip() for p in sys.stdin if p.strip().startswith('.tmp/') or p.strip().startswith('.runs/')]; assert not bad, 'staged runtime artifacts: '+repr(bad); print('NO_STAGED_RUNTIME_ARTIFACTS')"
```

Expected result:

```text
NO_STAGED_RUNTIME_ARTIFACTS
```

- [ ] **Step 11: Refresh tree for new files**

Run:

```powershell
node .codex/hooks/tree.mjs --force
```

Expected result:

- `.oh-my-harness/tree.md` includes `observer_protocol.py`, `observer_server.py`, `run_observer_server.py`, `test_observer_protocol.py`, and `test_observer_server.py` by filename.
- It must not include `.tmp/g2a-observer-smoke/**` or `.runs/**`.

---

## Acceptance Criteria

A1. G2a exposes a local REST protocol over Python standard library HTTP server.

A2. `GET /health` reports the observer server is alive.

A3. Existing completed G1h run bundles can be listed through `GET /api/runs`.

A4. Existing run details expose event count, snapshot count, and allowed artifact availability without leaking absolute local file paths.

A5. `GET /api/runs/{run_id}/events` reads and validates `events.jsonl` through `read_events_jsonl()`.

A6. `GET /api/runs/{run_id}/stream` emits SSE-formatted runtime events and uses `Content-Type: text/event-stream; charset=utf-8`.

A7. `POST /api/runs` accepts the minimum default launch contract and starts only the deterministic fake-provider 6-player runtime.

A8. The launch contract rejects unknown templates, unknown modes, unsafe run IDs, and extra keys.

A9. G2a implements conservative visibility filtering for `god`, `public`, `role:p1`-`role:p6`, and `team:werewolf` perspectives.

A10. Non-god perspectives do not receive `private`, `internal`, or unsafe unmapped event visibilities by default.

A11. Artifact serving is restricted to the allowlisted G1h artifact names and rejects path traversal.

A12. No API keys, bearer tokens, authorization headers, secret values, or local credential values are exposed in protocol responses.

A13. G2a does not modify Qt scaffold, Web client, prompt/profile editor, scoring, providers, validators, generated fixtures, demo HTML, ROADMAP, TASKS, README, or PRODUCT_ONE_PAGER.

A14. G2a uses no new third-party dependencies and does not modify dependency manifests.

A15. Focused observer tests, G1h regression tests, full unit suite, compileall, allowlist check, forbidden-scope check, forbidden-pattern check, dependency/import check, and runtime-artifact staging check pass or are documented with exact pre-existing failure evidence.

A16. `.logs/review/latest/review-packet.md` exists and contains the machine-generated evidence required below.

---

## Review Packet Requirements

After implementation, the implementer must create or update:

```text
.logs/review/latest/review-packet.md
```

The packet must be compact and must not rely on oral summaries. It must include at least these sections:

### 1. `git diff --name-only`

Include exact command:

```powershell
git diff --name-only main...HEAD
```

Include exact output.

### 2. `git diff --stat`

Include exact command:

```powershell
git diff --stat main...HEAD
```

Include exact output.

If changed files exceed 8 or changed lines exceed 500, mark:

```text
POTENTIAL_CODEX_B_DEEP_REVIEW_TRIGGER = YES
```

and suggest B档 file ranges for:

- `src/werewolf_eval/observer_protocol.py`
- `src/werewolf_eval/observer_server.py`
- `src/werewolf_eval/run_observer_server.py`
- `tests/test_observer_protocol.py`
- `tests/test_observer_server.py`

### 3. `git diff --check` result

Include command and exact pass/fail result.

For pass:

```text
DIFF_CHECK = PASS
```

For fail, include exact whitespace errors.

### 4. Changed files allowlist check

Include command from Task 6 Step 6 and exact result.

For pass:

```text
ALLOWLIST_CHECK = PASS
```

### 5. Forbidden patterns check

Include command from Task 6 Step 8 and exact result.

For pass:

```text
FORBIDDEN_PATTERN_CHECK = PASS
```

If safe test fixture markers print, list them under:

```text
SAFE_TEST_MARKER_HITS
```

### 6. Dependency/import diff check

Include both dependency manifest command and risky import command from Task 6 Step 9.

For pass:

```text
DEPENDENCY_DIFF_CHECK = PASS
RISKY_IMPORT_CHECK = PASS
```

### 7. Test command + exact pass/fail summary

Include each command and exact observed summary:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
```

For each, include:

```text
exit_code = N
summary = "Ran X tests in Ys / OK"
```

or the exact failure summary.

### 8. Key hunk excerpts

Include concise excerpts, not full diffs, for:

- endpoint dispatch in `observer_server.py`,
- path traversal defense in `observer_protocol.py`,
- visibility filter logic in `observer_protocol.py`,
- `POST /api/runs` fake-launch path in `observer_server.py`,
- tests proving public perspective hides private/internal events,
- tests proving traversal rejection.

Each excerpt must include file path and line range after implementation.

### 9. Acceptance checklist with evidence pointer

Include A1-A16 checklist. Each item must point to a test name, command result, or file hunk excerpt.

Example format:

```markdown
- [x] A1 REST protocol exists — `observer_server.py:Lx-Ly`, `ObserverServerEndpointTests.test_health_endpoint_returns_ok`
```

### 10. Implementer risk notes

Include a short section:

```markdown
## Implementer Risk Notes

- Server uses Python stdlib HTTP only; no FastAPI/Flask/WebSocket dependency.
- SSE stream replays completed run events and closes; full long-lived live tailing is intentionally limited in G2a.
- Minimum match/profile contract supports only `default_6p_fake`; full profile editor is G2d.
- Visibility filtering is conservative and protocol-level; full Phase E trust proof remains later hardening.
- Qt scaffold is untouched; G2b remains not completed.
```

---

## Potential Codex B档 Deep Review Triggers

The implementation may trigger B档 deeper review if any of these happen:

- `git diff --stat main...HEAD` exceeds 8 changed files or 500 changed lines.
- `observer_server.py` grows beyond 350 lines.
- Any source file combines protocol helpers, HTTP routing, CLI, and tests in one file instead of the planned separation.
- Any change touches forbidden scope such as Qt scaffold, ROADMAP/TASKS, runtime engine, provider adapter, scoring, validators, generated fixtures, demo HTML, or dependency manifests.
- Any import introduces third-party server/client dependencies.
- Any endpoint serves arbitrary paths or absolute paths.
- Any non-god perspective returns private/internal/unmapped event data.
- Any test starts a long-running server process without guaranteed shutdown.
- Full suite fails without proof that the failure is pre-existing and unrelated.
- Review packet lacks key hunk excerpts or acceptance checklist evidence pointers.

If triggered, the review packet must name explicit files and line ranges for B档 review.

---

## Implementation PR Description Draft

Title:

```text
feat: add G2a local observer protocol server
```

Body:

```markdown
## Summary

- Adds a Python-stdlib local observer server for G2a.
- Exposes G1h run bundles through client-agnostic REST endpoints and SSE event replay.
- Adds a minimum default fake-match launch contract for `default_6p_fake`.
- Adds conservative visibility filtering for God/Public/Role/Team perspectives from day one.

## Scope

- G2a protocol/control-plane only.
- No Qt/Web UI, no profile editor, no multi-provider arena, no leaderboard.
- No runtime gameplay, scoring, provider adapter, validator, generated artifact, demo HTML, or dependency changes.

## Validation

- `$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v`
- `$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v`
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"`
- `python -m compileall src tests`
- `git diff --check main...HEAD`
- allowlist / forbidden-scope / forbidden-pattern / dependency-import checks recorded in `.logs/review/latest/review-packet.md`

## Review Packet

`.logs/review/latest/review-packet.md` contains machine-generated evidence, key hunk excerpts, acceptance checklist pointers, and implementer risk notes.
```

---

## Execution Handoff

After saving this plan, implementation should proceed task-by-task in order:

1. Observer protocol helpers and unit tests.
2. Local HTTP observer server and endpoint tests.
3. CLI and CLI help test.
4. Security/provenance/no-secret tests.
5. Manual observer smoke evidence.
6. Full validation and review packet.

Do not jump directly into Qt/QML. Do not build a Web UI. Do not broaden the launch contract beyond `default_6p_fake` in this milestone.
