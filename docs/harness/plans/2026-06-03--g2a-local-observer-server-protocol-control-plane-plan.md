# G2a Local Observer Server / Protocol Control Plane Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Build the G2a local observer server that exposes G1h runtime event-spine runs through a client-agnostic REST + streaming protocol, with live-run observation, controlled snapshot access, a minimum default-match launch contract, and visibility-trust slices from day one.

**Architecture:** Add a narrow Python-standard-library observer layer around completed G1h artifacts. The observer server reads completed run bundles, launches the deterministic fake-provider default 6-player match asynchronously, tracks run status changes, tails `events.jsonl` while a run is active, serves visibility-filtered events and controlled snapshot details, and never exposes Python runtime objects directly to clients. It is a protocol/control-plane milestone, not a Qt/Web UI or profile editor milestone.

**Tech Stack:** Python standard library only: `http.server`, `ThreadingHTTPServer`, `threading`, `time`, `json`, `pathlib`, `uuid`, `urllib.request` in tests, `unittest`, existing `werewolf_eval.runtime_events.read_events_jsonl`, existing `werewolf_eval.run_g1h_fake_runtime.run_fake_runtime`. No FastAPI, Flask, websockets, requests, PySide, Qt, or dependency manifest changes.

---

## Review Fixes Incorporated

This revision fixes the current plan-review findings before implementation:

- **B1 fixed:** `RunLauncher = Callable[[str, Path], int]` is kept as the observer-server internal adapter type, and the default production launcher must wrap the existing keyword-only `run_fake_runtime(*, game_id, out_dir)` call:

```python
def default_fake_launcher(run_id: str, run_dir: Path) -> int:
    return run_fake_runtime(game_id=run_id, out_dir=run_dir)
```

- **W1 fixed:** Review Packet Requirements now require the review-packet-gate section set and order: Metadata, Changed Files, Diff Stat, Diff Check, Allowed Files Check, Forbidden Patterns Check, Dependency / Import Diff, Test Summary, Key Hunks, Evidence Map, Acceptance Checklist, Implementer Risk Notes, Review Trigger Result.
- **W2 fixed:** `seer` and `witch` event visibility values are hidden from every non-god perspective in G2a because G2a does not yet own authoritative seat-role mapping. Role-specific seer/witch event delivery is deferred to the full Visibility Trust Layer after profile/seat-role contracts exist.
- **W3 fixed:** Live stream tests must use a slow injected launcher with at least `0.5s` delay between events, server polling interval `0.1s`, and test timeout at least `8s` to reduce CI flakiness.
- Previous BLOCK fixes retained: asynchronous live-run observation, status SSE, controlled snapshot detail endpoint, `/events` object response, and no completed-run-only acceptance.

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

---

## Scope Summary

G2a includes:

- Local observer protocol helpers for run discovery, run metadata, artifact registry, safe path resolution, snapshot registry, snapshot visibility checks, event visibility filtering, SSE event formatting, run-id generation, and minimum launch request parsing.
- Local HTTP server with REST endpoints for health, run listing, run status, events, stream, snapshots, snapshot details, artifacts, prompt manifest, provider trace, failure audit, and default fake-match launch.
- A deterministic, CI-safe minimum match/profile contract seed for launching a default 6-player fake-provider match.
- Asynchronous run-control path for `POST /api/runs` with observable `queued` / `running` / `completed` / `failed` status.
- Streaming endpoint that replays existing visible events and tails new `events.jsonl` events until the run reaches terminal status.
- Tests that use only temporary directories, fake G1h runtime output, injected slow local runner, localhost HTTP, and Python standard library clients.
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
- Mapping `seer` or `witch` event visibility to a concrete player role view.

## File Plan

### Create

- `src/werewolf_eval/observer_protocol.py`
  - Pure helper module for observer contracts.
  - Defines protocol constants, allowed artifact names, match/profile seed shape, run metadata builder, artifact registry, snapshot registry, snapshot detail loading, visibility filtering, SSE formatting, run-id generation, and safe path validation.
  - No sockets, no background threads, no CLI parsing.

- `src/werewolf_eval/observer_server.py`
  - Local HTTP server implementation.
  - Uses `ThreadingHTTPServer` and `BaseHTTPRequestHandler`.
  - Serves REST JSON endpoints, artifact JSON, controlled snapshot details, and SSE stream.
  - Launches default fake-provider run through an injectable launcher. Production default uses a wrapper around existing `run_fake_runtime()`.

- `src/werewolf_eval/run_observer_server.py`
  - CLI entry point.
  - Starts the observer server on `127.0.0.1` by default.
  - Does not auto-launch live provider runs.

- `tests/test_observer_protocol.py`
  - Unit tests for safe path handling, run discovery, metadata, artifact registry, snapshot registry/detail visibility, event visibility filters including hidden `seer`/`witch`, SSE format, run-id generation, and minimum match/profile seed validation.

- `tests/test_observer_server.py`
  - Integration tests for local HTTP endpoints, asynchronous default fake-run launch, live stream tailing, controlled snapshot detail access, and security boundaries using temporary directories and localhost port `0`.

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
- Expose raw secrets or local credential values in JSON responses, SSE events, snapshot responses, or review evidence.
- Serve arbitrary local filesystem paths outside the configured runs directory.
- Serve god-view snapshots to non-god perspectives.
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

### Run Status Contract

Run status values:

```text
queued
running
completed
failed
unknown
```

Rules:

- `POST /api/runs` must set status to `queued` before starting a background thread.
- The background thread must set status to `running` before invoking the runner.
- It must set status to `completed` only when the runner returns `0`.
- It must set status to `failed` when the runner returns nonzero or raises.
- Completed run directories discovered from disk without in-memory state are reported as `completed` when `events.jsonl` and final artifacts exist.
- Discovered incomplete run directories are reported as `unknown` unless there is in-memory state.

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
- `run_id` may be omitted; server generates a safe prefix plus UUID suffix when omitted.
- `generate_run_id(prefix="g2a_default_6p_fake")` must return `f"{prefix}_{uuid.uuid4().hex[:8]}"` after validating `prefix` and the final generated ID.
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
GET  /api/runs/{run_id}/snapshots?perspective=god|public|role:p1|role:p2|role:p3|role:p4|role:p5|role:p6|team:werewolf
GET  /api/runs/{run_id}/snapshots/{snapshot_name}?perspective=god|public|role:p1|role:p2|role:p3|role:p4|role:p5|role:p6|team:werewolf
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
- `POST /api/runs` launches a default fake run asynchronously and returns `202` with `run_id`, `status`, `template`, and `mode`. It must not block until the whole run completes.
- `GET /api/runs/{run_id}` returns status, artifact availability, event count, snapshot count, source labels if available, and paths relative to the run directory only.
- `GET /events` returns an object with `perspective`, `events`, and `hidden_count`.
- `GET /stream` returns `text/event-stream; charset=utf-8`, first replays visible events already present, then tails new visible events while the run status is `queued` or `running`, and closes only after a terminal status plus final poll. Completed-run streams replay current visible events and close.
- `GET /snapshots` returns perspective-filtered snapshot metadata. Metadata includes `snapshot_name`, relative `path`, `snapshot_type`, `player_id` when safe, and `visible`.
- `GET /snapshots/{snapshot_name}` returns controlled snapshot content only if the requested perspective is allowed to see it.
- `GET /artifacts` returns allowed artifact names and availability.
- Artifact endpoints must return `404` for missing artifacts and `400` or `404` for unknown artifact names.

### Snapshot Visibility Rules

Snapshot names:

- Must be simple filenames under `snapshots/`.
- Must end with `.json`.
- Must not contain `/`, `\\`, `..`, URL-decoded traversal, or absolute-path syntax.

Snapshot content is loaded only from `run_dir / "snapshots" / snapshot_name`.

Visibility rules:

- `god` may read every snapshot.
- `public` may read only snapshots whose JSON has `snapshot_type == "public"`. Current G1h snapshots normally do not provide public snapshots, so `public` usually sees metadata with hidden snapshots and receives `403` for details.
- `role:pN` may read only `snapshot_type == "role_projection"` snapshots whose `player_id == "pN"`.
- `team:werewolf` may read `snapshot_type == "role_projection"` snapshots whose `team == "werewolf"`.
- No non-god perspective may read `snapshot_type == "god"`.
- If a snapshot lacks `snapshot_type`, hide it from all non-god perspectives.
- Hidden snapshot detail requests return `403` with `code = "snapshot_hidden"` and must not include snapshot content.

### Event Visibility Rules

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
- `public` may see only `visibility == "public"`.
- `role:pN` may see only `visibility == "public"` in G2a. This intentionally hides `private`, `internal`, `all`, `seer`, and `witch` events until G2 owns an authoritative seat-role mapping.
- `team:werewolf` may see `visibility == "public"` and `visibility == "werewolf_team"`.
- Unknown perspectives return `400`.
- Filtering must be conservative. If event visibility cannot be safely mapped, hide it from non-god perspectives.
- Responses must include `perspective` and `hidden_count`.

Current G1h event visibilities include values such as `public`, `private`, `internal`, `all`, `seer`, `witch`, and `werewolf_team`. G2a must map them through an observer protocol helper rather than modifying G1h event constants in this milestone.

---

## Task 1: Add observer protocol helpers

**Files:**

- Create: `src/werewolf_eval/observer_protocol.py`
- Test: `tests/test_observer_protocol.py`

- [ ] **Step 1: Create `observer_protocol.py` constants and exceptions**

Implement these public names:

```python
from __future__ import annotations

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
RUN_STATUS_VALUES: tuple[str, ...] = (
    "queued",
    "running",
    "completed",
    "failed",
    "unknown",
)

class ObserverProtocolError(ValueError):
    """Raised when observer protocol input is invalid."""
```

- [ ] **Step 2: Add path helpers**

Implement:

```python
def validate_run_id(run_id: str) -> str: ...
def validate_snapshot_name(snapshot_name: str) -> str: ...
def safe_child_path(root: Path, child_name: str) -> Path: ...
def artifact_path(run_dir: Path, artifact_name: str) -> Path: ...
def snapshot_path(run_dir: Path, snapshot_name: str) -> Path: ...
```

Required behavior:

- Reject `..`, `/`, `\\`, empty values, absolute paths, and URL-decoded path-like input.
- `artifact_path()` accepts only `ALLOWED_ARTIFACTS`.
- `snapshot_path()` accepts only simple `.json` snapshot filenames.

- [ ] **Step 3: Add registries, summary, and launch helpers**

Implement:

```python
def list_run_dirs(runs_dir: Path) -> list[Path]: ...
def build_artifact_registry(run_dir: Path) -> dict[str, dict[str, object]]: ...
def build_snapshot_registry(run_dir: Path, perspective: str = "god") -> list[dict[str, object]]: ...
def load_snapshot_detail(run_dir: Path, snapshot_name: str, perspective: str = "god") -> dict[str, object]: ...
def build_run_summary(run_dir: Path, status: str | None = None) -> dict[str, object]: ...
def build_run_detail(run_dir: Path, status: str | None = None) -> dict[str, object]: ...
def parse_launch_request(payload: dict[str, object]) -> dict[str, object]: ...
def generate_run_id(prefix: str = "g2a_default_6p_fake") -> str: ...
```

Required behavior:

- `parse_launch_request()` accepts only `template`, `run_id`, and `mode` keys.
- Reject unknown template, unknown mode, unsafe `run_id`, and extra keys.
- `generate_run_id()` uses `uuid.uuid4().hex[:8]` suffix and validates both prefix and final ID.
- Run summaries expose relative paths only and never absolute local paths.

- [ ] **Step 4: Add visibility and SSE helpers**

Implement:

```python
def normalize_perspective(perspective: str | None) -> str: ...
def event_visible_to_perspective(event: dict[str, object], perspective: str) -> bool: ...
def snapshot_visible_to_perspective(snapshot: dict[str, object], perspective: str) -> bool: ...
def filter_events_for_perspective(events: list[dict[str, object]], perspective: str) -> dict[str, object]: ...
def format_sse_event(event: dict[str, object]) -> bytes: ...
def format_sse_status(run_id: str, status: str) -> bytes: ...
```

Required behavior:

- `god` sees every event and snapshot.
- `public` sees public events and public snapshots only.
- `role:pN` sees public events and only matching `role_projection` snapshots for `pN`.
- `role:pN` does not see `seer` or `witch` events in G2a.
- `team:werewolf` sees public/werewolf-team events and werewolf role-projection snapshots.
- `format_sse_event()` uses `event: runtime_event`.
- `format_sse_status()` uses `event: run_status`.

- [ ] **Step 5: Add protocol unit tests**

Create `tests/test_observer_protocol.py` with these required tests:

```python
class ObserverPathSafetyTests(unittest.TestCase):
    def test_validate_run_id_rejects_path_traversal(self) -> None: ...
    def test_artifact_path_rejects_unknown_artifact(self) -> None: ...
    def test_safe_child_path_stays_under_root(self) -> None: ...
    def test_validate_snapshot_name_rejects_nested_paths(self) -> None: ...

class ObserverRunSummaryTests(unittest.TestCase):
    def test_build_run_summary_counts_events_and_snapshots(self) -> None: ...
    def test_build_artifact_registry_reports_allowed_artifacts_only(self) -> None: ...

class ObserverLaunchContractTests(unittest.TestCase):
    def test_parse_launch_request_accepts_default_fake_template(self) -> None: ...
    def test_parse_launch_request_rejects_unknown_template(self) -> None: ...
    def test_parse_launch_request_rejects_extra_keys(self) -> None: ...
    def test_generate_run_id_uses_safe_uuid_suffix(self) -> None: ...

class ObserverVisibilityTests(unittest.TestCase):
    def test_god_sees_all_events(self) -> None: ...
    def test_public_hides_private_internal_all_seer_and_witch_events(self) -> None: ...
    def test_role_hides_private_internal_all_seer_and_witch_events(self) -> None: ...
    def test_werewolf_team_sees_public_and_werewolf_team_events(self) -> None: ...
    def test_unknown_perspective_is_rejected(self) -> None: ...
    def test_sse_format_contains_event_and_data_lines(self) -> None: ...
    def test_sse_status_contains_run_status_event(self) -> None: ...

class ObserverSnapshotVisibilityTests(unittest.TestCase):
    def test_god_can_read_god_snapshot_detail(self) -> None: ...
    def test_public_cannot_read_god_snapshot_detail(self) -> None: ...
    def test_role_can_read_only_own_projection_snapshot(self) -> None: ...
    def test_werewolf_team_can_read_werewolf_projection_snapshot(self) -> None: ...
    def test_snapshot_registry_marks_hidden_snapshots_for_public(self) -> None: ...
```

Use temporary directories and handcrafted event/snapshot fixtures. Do not read repository artifacts.

- [ ] **Step 6: Run protocol focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol -v
```

Expected result:

```text
OK
```

Record exact test count in the review packet.

---

## Task 2: Add local observer HTTP server with live run state

**Files:**

- Create: `src/werewolf_eval/observer_server.py`
- Test: `tests/test_observer_server.py`

- [ ] **Step 1: Create server state and default launcher wrapper**

Implement public names:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from typing import Callable

from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime

RunLauncher = Callable[[str, Path], int]


def default_fake_launcher(run_id: str, run_dir: Path) -> int:
    return run_fake_runtime(game_id=run_id, out_dir=run_dir)


@dataclass
class ObserverServerState:
    runs_dir: Path
    launcher: RunLauncher
    run_status: dict[str, str] = field(default_factory=dict)
    run_errors: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)

class ObserverRequestHandler(BaseHTTPRequestHandler): ...

def create_observer_server(host: str, port: int, runs_dir: Path, launcher: RunLauncher | None = None) -> ThreadingHTTPServer: ...
```

Required behavior:

- `create_observer_server()` uses `default_fake_launcher` when `launcher is None`.
- All `run_status` and `run_errors` access happens under `state.lock`.
- JSON responses use `application/json; charset=utf-8`.
- Disable noisy `log_message()` output.

- [ ] **Step 2: Add request parsing, error helpers, and status helpers**

Implement helper methods on `ObserverRequestHandler`:

```python
def _send_json(self, status: int, payload: dict[str, object] | list[object]) -> None: ...
def _send_error_json(self, status: int, code: str, message: str) -> None: ...
def _read_json_body(self) -> dict[str, object]: ...
def _get_state(self) -> ObserverServerState: ...
def _get_status(self, run_id: str, run_dir: Path) -> str: ...
def _set_status(self, run_id: str, status: str) -> None: ...
```

Required behavior:

- Invalid JSON body returns `400` with `code = "invalid_json"`.
- Protocol validation errors return `400` with `code = "invalid_request"`.
- Hidden snapshot detail returns `403` with `code = "snapshot_hidden"`.
- Missing runs/artifacts/snapshots return `404`.

- [ ] **Step 3: Implement GET endpoints**

Implement `do_GET()` dispatch for all required endpoints listed above.

Required behavior:

- `/api/runs/{run_id}/events` returns `filter_events_for_perspective()` object.
- `/api/runs/{run_id}/stream` uses live SSE tailing.
- `/api/runs/{run_id}/snapshots` uses `build_snapshot_registry(run_dir, perspective)`.
- `/api/runs/{run_id}/snapshots/{snapshot_name}` uses `load_snapshot_detail(run_dir, snapshot_name, perspective)`.
- Artifact aliases `/manifest`, `/provider-trace`, and `/failure-audit` serve only their allowlisted artifact files.

- [ ] **Step 4: Implement live SSE tailing**

Implement:

```python
def _send_event_stream(self, run_id: str, run_dir: Path, perspective: str) -> None: ...
```

Required behavior:

- Sends `Content-Type: text/event-stream; charset=utf-8`.
- Sends initial `run_status` SSE.
- Uses polling interval `0.1` seconds.
- Replays visible events not yet sent.
- While status is `queued` or `running`, continues polling for new events.
- On `completed` or `failed`, performs one final read, sends newly visible events, sends final `run_status`, then closes.
- For completed runs with no active state, replays existing visible events and closes.
- Does not introduce WebSocket or async server dependencies.

- [ ] **Step 5: Implement asynchronous POST default fake run launch**

Implement `do_POST()` for `/api/runs`.

Required behavior:

- Parse body through `parse_launch_request()`.
- Create run directory under `runs_dir / run_id`.
- Set status `queued`.
- Start daemon `Thread`.
- Thread sets `running`, calls `state.launcher(run_id, run_dir)`, then sets `completed` for return code `0`; otherwise sets `failed` and stores error text.
- Response returns `202` immediately:

```json
{
  "run_id": "...",
  "template": "default_6p_fake",
  "mode": "fake",
  "status": "queued"
}
```

- Do not call DeepSeek or any live provider path.
- Do not block until fake runtime finishes.

- [ ] **Step 6: Add server integration tests**

Create `tests/test_observer_server.py` with standard-library helpers:

```python
def _start_server(runs_dir: Path, launcher=None): ...
def _request_json(base_url: str, path: str, *, method: str = "GET", payload: dict[str, object] | None = None) -> object: ...
def _request_text(base_url: str, path: str) -> str: ...
def _wait_for_status(base_url: str, run_id: str, expected: str, timeout_s: float = 8.0) -> dict[str, object]: ...
```

Required test classes and tests:

```python
class ObserverServerEndpointTests(unittest.TestCase):
    def test_health_endpoint_returns_ok(self) -> None: ...
    def test_list_runs_and_run_detail_for_existing_fake_runtime(self) -> None: ...
    def test_events_endpoint_filters_public_perspective(self) -> None: ...
    def test_stream_endpoint_replays_sse_events_for_completed_run(self) -> None: ...
    def test_artifact_endpoint_rejects_unknown_artifact(self) -> None: ...
    def test_snapshot_detail_rejects_god_snapshot_for_public(self) -> None: ...
    def test_snapshot_detail_allows_role_projection_for_matching_role(self) -> None: ...
    def test_post_runs_launches_default_fake_match_asynchronously(self) -> None: ...
    def test_stream_endpoint_tails_events_while_run_is_active(self) -> None: ...
    def test_post_runs_rejects_unknown_template(self) -> None: ...
```

Live tailing test requirements:

- Inject a slow local launcher.
- Launcher uses `RuntimeEventWriter` to write at least two events.
- Delay at least `0.5` seconds between the first and second event.
- Test timeout at least `8.0` seconds.
- Test proves `POST /api/runs` returns before completion, an active status is observable, and `/stream?perspective=god` receives runtime events before final completion status.

- [ ] **Step 7: Run server tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_server -v
```

Expected result:

```text
OK
```

Record exact test count in the review packet.

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
    print("observer_server=started")
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

- [ ] **Step 2: Add CLI help test**

Add:

```python
class ObserverServerCliTests(unittest.TestCase):
    def test_cli_help_lists_runs_dir_host_and_port(self) -> None: ...
```

Use `subprocess.run([sys.executable, "-m", "werewolf_eval.run_observer_server", "--help"], ...)`. Assert return code `0`, stdout contains `--runs-dir`, `--host`, and `--port`. Do not start a long-running CLI process in tests.

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

## Task 4: Add security, provenance, snapshot, and no-secret tests

**Files:**

- Modify: `tests/test_observer_protocol.py`
- Modify: `tests/test_observer_server.py`
- Test: both observer test files

- [ ] **Step 1: Add traversal tests**

Required rejected inputs for run IDs, artifact names, and snapshot names:

```text
../x
..\\x
x/y
x\\y
```

Required server path examples:

```text
/api/runs/security_run/artifacts/..%2F..%2FREADME.md
/api/runs/security_run/snapshots/..%2F..%2FREADME.md
```

Expected HTTP status is `400` or `404`, and response body must not contain README content.

- [ ] **Step 2: Add no-secret response scan test**

Add:

```python
class ObserverServerSecretScanTests(unittest.TestCase):
    def test_public_endpoints_do_not_expose_secret_markers(self) -> None: ...
```

Call `/api/runs`, `/api/runs/{run_id}`, `/events?perspective=god`, `/snapshots?perspective=god`, `/artifacts`, `/manifest`, `/provider-trace`, and `/failure-audit`. Fail if unsafe markers appear:

```text
Authorization:
Bearer 
DEEPSEEK_API_KEY=
sk-
```

Safe literal references inside tests must be described in the review packet as test-only forbidden-pattern markers.

- [ ] **Step 3: Add live-observation non-shrinkage test**

Add:

```python
class ObserverServerLiveObservationTests(unittest.TestCase):
    def test_status_changes_and_stream_events_are_visible_before_completion(self) -> None: ...
```

Required proof:

- Inject slow launcher with at least `0.5s` delay between emitted events.
- `POST /api/runs` returns before launcher completion.
- A status query observes `queued` or `running` before `completed`.
- `/stream?perspective=god` receives at least one runtime event from the active run before final completion status.
- The test fails if the implementation only runs synchronously and only replays completed runs.

- [ ] **Step 4: Run security and live-observation tests**

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

- [ ] **Step 1: Generate one local fake run**

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

- [ ] **Step 2: Start observer server manually**

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
Invoke-RestMethod 'http://127.0.0.1:8765/api/runs/g2a_smoke_run/snapshots?perspective=god'
```

Expected:

- Health response has `status = ok`.
- Runs response includes `g2a_smoke_run`.
- Run detail has `event_count > 0` and `snapshot_count > 0`.
- Public events response includes `perspective = public` and does not include private/internal/all/seer/witch events.
- God snapshot metadata response lists snapshots without absolute local paths.

- [ ] **Step 4: Record manual smoke status**

In review packet, record `MANUAL_OBSERVER_SMOKE = PASS` only if Steps 1-3 succeed. Otherwise record exact failing command and result.

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

Expected result: `OK`. Record exact test count.

- [ ] **Step 2: Run G1h regression tests touched by server launch path**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v
```

Expected result: `OK`.

- [ ] **Step 3: Run full unit suite**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Expected result: `OK`.

If a known pre-existing unrelated failure appears, include exact failing test name, proof it fails on `main` or was documented before this change, and focused G2a test pass summary.

- [ ] **Step 4: Compile Python files**

Run:

```powershell
python -m compileall src tests
```

Expected result: `0 failures` and exit code `0`.

- [ ] **Step 5: Run diff whitespace check**

Run:

```powershell
git diff --check main...HEAD
```

Expected result: no output.

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

Expected result: prints only allowed files and exits `0`.

- [ ] **Step 7: Run forbidden-scope check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; forbidden_prefixes=('clients/qt_observer/','docs/demo/','docs/generated-games/','docs/gold-game/','docs/adr/','.github/','.agents/skills/'); forbidden_exact={'README.md','docs/ROADMAP.md','docs/TASKS.md','docs/PRODUCT_ONE_PAGER.md','src/werewolf_eval/game_engine.py','src/werewolf_eval/provider_agent.py','src/werewolf_eval/run_g1h_fake_runtime.py','src/werewolf_eval/run_deepseek_consensus_game.py','src/werewolf_eval/scoring.py','src/werewolf_eval/score_game.py'}; changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p in forbidden_exact or p.startswith(forbidden_prefixes)]; print('\n'.join(bad)); assert not bad, 'forbidden scope changed: '+repr(bad)"
```

Expected result: no output.

- [ ] **Step 8: Run forbidden pattern scan on added source/test lines**

Run:

```powershell
git diff main...HEAD -- src tests | python -c "import sys; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; markers=['Authorization:', 'Bearer ', 'DEEPSEEK_API_KEY=', 'sk-']; hits=[line for line in added if any(marker in line for marker in markers)]; print('\n'.join(hits)); unsafe=[line for line in hits if 'secret' not in line.lower() and 'marker' not in line.lower() and 'scan' not in line.lower() and 'forbidden' not in line.lower()]; assert not unsafe, 'unsafe forbidden pattern hits: '+repr(unsafe)"
```

Expected result: no unsafe committed secret values. Safe literal markers inside secret-scan tests may print and must be listed in the review packet as safe test fixtures.

- [ ] **Step 9: Run dependency/import diff check**

Run:

```powershell
git diff --name-only main...HEAD -- package.json package-lock.json pyproject.toml requirements.txt poetry.lock pnpm-lock.yaml yarn.lock uv.lock CMakeLists.txt clients/qt_observer/CMakeLists.txt
```

Expected result: no output.

Also run:

```powershell
git diff main...HEAD -- src tests | python -c "import sys,re; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; risky=[line for line in added if re.search(r'^\+\s*(import|from)\s+(requests|httpx|aiohttp|websockets|fastapi|flask|starlette|uvicorn|openai|anthropic|PySide6|PyQt6|streamlit|gradio)\b', line)]; print('\n'.join(risky)); assert not risky, 'unexpected dependency/import addition'"
```

Expected result: no output.

- [ ] **Step 10: Verify no `.tmp` or `.runs` artifacts are staged**

Run:

```powershell
git diff --name-only --cached | python -c "import sys; bad=[p.strip() for p in sys.stdin if p.strip().startswith('.tmp/') or p.strip().startswith('.runs/')]; assert not bad, 'staged runtime artifacts: '+repr(bad); print('NO_STAGED_RUNTIME_ARTIFACTS')"
```

Expected result: `NO_STAGED_RUNTIME_ARTIFACTS`.

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

A5. `GET /api/runs/{run_id}/events` reads and validates `events.jsonl` through `read_events_jsonl()` and returns `perspective`, `events`, and `hidden_count`.

A6. `GET /api/runs/{run_id}/stream` emits SSE-formatted runtime events, emits run-status SSE events, and tails new events while a run is active.

A7. `POST /api/runs` accepts the minimum default launch contract, returns before run completion, and starts only the deterministic fake-provider 6-player runtime in a background thread.

A8. Default production launch wraps keyword-only `run_fake_runtime(game_id=..., out_dir=...)` correctly through `default_fake_launcher(run_id, run_dir)`.

A9. The launch contract rejects unknown templates, unknown modes, unsafe run IDs, and extra keys.

A10. G2a implements conservative visibility filtering for `god`, `public`, `role:p1`-`role:p6`, and `team:werewolf` perspectives.

A11. Non-god event perspectives do not receive `private`, `internal`, `all`, `seer`, `witch`, or unsafe unmapped event visibilities by default.

A12. Snapshot metadata and snapshot detail endpoints exist; non-god perspectives cannot read god snapshots, and role perspectives can read only their own role-projection snapshots.

A13. Artifact serving is restricted to the allowlisted G1h artifact names and rejects path traversal.

A14. Snapshot serving is restricted to safe `snapshots/*.json` names under the run directory and rejects path traversal.

A15. No API keys, bearer tokens, authorization headers, secret values, or local credential values are exposed in protocol responses, SSE events, or snapshot responses.

A16. G2a does not modify Qt scaffold, Web client, prompt/profile editor, scoring, providers, validators, generated fixtures, demo HTML, ROADMAP, TASKS, README, or PRODUCT_ONE_PAGER.

A17. G2a uses no new third-party dependencies and does not modify dependency manifests.

A18. Focused observer tests, G1h regression tests, full unit suite, compileall, allowlist check, forbidden-scope check, forbidden-pattern check, dependency/import check, and runtime-artifact staging check pass or are documented with exact pre-existing failure evidence.

A19. `.logs/review/latest/review-packet.md` exists, is compact, and contains the machine-generated evidence required below.

---

## Review Packet Requirements

After implementation, the implementer must create or update:

```text
.logs/review/latest/review-packet.md
```

The packet must be compact and must not rely on oral summaries. Keep the packet at or under 300 lines; if impossible, mark `PACKET_TOO_LARGE = YES` and provide B档 file ranges. It must include these sections in this order.

### 1. Metadata

Include:

```markdown
# Review Packet — G2a Local Observer Server / Protocol Control Plane

- Plan: `docs/harness/plans/2026-06-03--g2a-local-observer-server-protocol-control-plane-plan.md`
- Implementer: <name or agent id from local context>
- Date: <YYYY-MM-DD>
- Branch: <branch name>
- Base: `main`
- PR: <PR number or `not-opened`>
- Verdict target: G2a protocol/control-plane only
```

### 2. Changed Files

Include command and exact output:

```powershell
git diff --name-only main...HEAD
```

### 3. Diff Stat

Include command and exact output:

```powershell
git diff --stat main...HEAD
```

### 4. Diff Check

Include:

```powershell
git diff --check main...HEAD
```

For pass, record `DIFF_CHECK = PASS`.

### 5. Allowed Files Check

Include Task 6 Step 6 command and exact result. For pass, record `ALLOWLIST_CHECK = PASS`.

### 6. Forbidden Patterns Check

Include Task 6 Step 8 command and exact result. For pass, record `FORBIDDEN_PATTERN_CHECK = PASS`. If safe test fixture markers print, list them under `SAFE_TEST_MARKER_HITS`.

### 7. Dependency / Import Diff

Include both Task 6 Step 9 commands and exact result. For pass, record:

```text
DEPENDENCY_DIFF_CHECK = PASS
RISKY_IMPORT_CHECK = PASS
```

### 8. Test Summary

Include each command and exact observed summary:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol tests.test_observer_server -v
$env:PYTHONPATH='src'; python -m unittest tests.test_runtime_events tests.test_g1h_runtime_spine -v
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
```

For each, include `exit_code` and exact `Ran X tests ... OK` or failure summary.

### 9. Key Hunks

Include concise excerpts, not full diffs, for:

- endpoint dispatch in `observer_server.py`,
- `default_fake_launcher()` wrapper calling keyword-only `run_fake_runtime(game_id=..., out_dir=...)`,
- asynchronous `POST /api/runs` launcher and status transitions,
- live SSE tailing loop,
- path traversal defense,
- event visibility logic that hides `seer` and `witch` from non-god perspectives,
- snapshot visibility and detail loading,
- tests proving public/role perspectives hide private/internal/all/seer/witch events,
- tests proving snapshot detail rejects god snapshot for public perspective,
- tests proving live stream receives active-run events before completion,
- tests proving traversal rejection.

Each excerpt must include file path and line range after implementation.

### 10. Evidence Map

Include a Markdown table with exactly these columns:

```markdown
| Acceptance | Evidence | Status |
|------------|----------|--------|
| A1 | `observer_server.py:Lx-Ly`; `ObserverServerEndpointTests.test_health_endpoint_returns_ok` | PASS |
```

Every A1-A19 item must have one row. Evidence must point to a test name, command result, or key hunk line range.

### 11. Acceptance Checklist

Include checklist form for A1-A19. Each item must include an evidence pointer. Example:

```markdown
- [x] A8 default launcher wraps keyword-only fake runtime — `observer_server.py:Lx-Ly`; `ObserverServerEndpointTests.test_post_runs_launches_default_fake_match_asynchronously`
```

### 12. Implementer Risk Notes

Include:

```markdown
## Implementer Risk Notes

- Server uses Python stdlib HTTP only; no FastAPI/Flask/WebSocket dependency.
- SSE stream replays existing visible events and tails active-run `events.jsonl` until terminal status; it is local file polling, not a full hosted event bus.
- Live stream tests use 0.1s polling, >=0.5s launcher delay, and >=8s timeout to reduce CI flakiness.
- Minimum match/profile contract supports only `default_6p_fake`; full profile editor is G2d.
- `seer` and `witch` event visibility values are hidden from non-god perspectives in G2a until seat-role mapping exists.
- Snapshot detail access is conservative: god can read all, role views read only matching role projections, and public normally cannot read G1h god snapshots.
- Visibility filtering is conservative and protocol-level; full Phase E trust proof remains later hardening.
- Qt scaffold is untouched; G2b remains not completed.
```

### 13. Review Trigger Result

Include:

```text
PACKET_TOO_LARGE = YES|NO
POTENTIAL_CODEX_B_DEEP_REVIEW_TRIGGER = YES|NO
CHANGED_FILES_COUNT = N
CHANGED_LINES = +A/-D
B_DEEP_REVIEW_RANGES = <ranges or none>
```

Set `POTENTIAL_CODEX_B_DEEP_REVIEW_TRIGGER = YES` if any trigger below occurs.

---

## Potential Codex B档 Deep Review Triggers

The implementation may trigger B档 deeper review if any of these happen:

- `git diff --stat main...HEAD` exceeds 8 changed files or 500 changed lines.
- `observer_server.py` grows beyond 400 lines.
- Any source file combines protocol helpers, HTTP routing, CLI, and tests in one file instead of the planned separation.
- Any change touches forbidden scope such as Qt scaffold, ROADMAP/TASKS, runtime engine, provider adapter, scoring, validators, generated fixtures, demo HTML, or dependency manifests.
- Any import introduces third-party server/client dependencies.
- Any endpoint serves arbitrary paths or absolute paths.
- Any snapshot endpoint serves god-view snapshot content to non-god perspectives.
- Any non-god event perspective returns private/internal/all/seer/witch/unmapped event data.
- Any test starts a long-running server process without guaranteed shutdown.
- Full suite fails without proof that the failure is pre-existing and unrelated.
- Review packet lacks Metadata, Evidence Map, Review Trigger Result, key hunk excerpts, or acceptance evidence pointers.

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
- Exposes G1h run bundles through client-agnostic REST endpoints and SSE event replay/tailing.
- Adds asynchronous default fake-match launch for `default_6p_fake` with observable run status transitions.
- Adds controlled snapshot metadata/detail endpoints with conservative perspective checks.
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

`.logs/review/latest/review-packet.md` contains Metadata, machine-generated evidence, key hunk excerpts, Evidence Map, acceptance checklist pointers, implementer risk notes, and Review Trigger Result.
```

---

## Execution Handoff

Implementation should proceed task-by-task in order:

1. Observer protocol helpers and unit tests.
2. Local HTTP observer server with live run state, endpoint tests, live stream tests, and snapshot tests.
3. CLI and CLI help test.
4. Security/provenance/snapshot/no-secret tests.
5. Manual observer smoke evidence.
6. Full validation and review packet.

Do not jump directly into Qt/QML. Do not build a Web UI. Do not broaden the launch contract beyond `default_6p_fake` in this milestone. Do not accept completed-run replay alone as proof of G2a success. Do not expose `seer` or `witch` events to role views until G2 owns authoritative seat-role mapping.
