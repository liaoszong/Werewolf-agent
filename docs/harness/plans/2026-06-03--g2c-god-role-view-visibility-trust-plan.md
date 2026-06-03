# G2c God View / Role View Visibility Trust Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add the G2c visibility trust layer so God/Public/Role/Team views are explicit, auditable, and enforced end-to-end across the G2a observer protocol and G2b Qt cockpit.

**Architecture:** Implement a focused server-side visibility projection layer that builds a run-local seat/role/team index from existing G1h/G2a artifacts, returns projection envelopes through a new G2a protocol endpoint, and adds proof metadata explaining what each perspective can and cannot see. Update the Qt cockpit to consume the projection endpoint, render perspective-aware player cards, hidden-count badges, and proof panels without reading local files or implementing independent hidden-information filtering.

**Tech Stack:** Python standard library, existing G2a stdlib HTTP server, Python `unittest`, Qt 6.8+ / Qt Quick / Qt Network / Qt Test, CMake, C++17, QML. No new third-party dependencies, no provider API calls, no prompt/profile editor.

---

## Plan Review Fixes Incorporated

This revision incorporates the G2c plan review findings before implementation:

- **Seat-index trust fixed:** `build_seat_role_index()` may read god snapshots for server-side god projection and diagnostics, but non-god projections must trust only `role_projection_snapshot` data for self/team visibility and `projected_known_roles`. A field filled only from `god_snapshot` must not be exposed to Public/Role/Team perspectives.
- **Snapshot metadata fixed:** `project_snapshots()` now has a required minimum metadata shape with `snapshot_name`, `snapshot_type`, `perspective`, `visible`, `hidden`, `round`, `phase`, `detail_endpoint`, and `hidden_reason`; `player_id` / `team` appear only when safe for the requesting perspective.
- **Qt projection request race fixed:** `ObserverApiClient` must implement latest-wins projection requests using a monotonically increasing request id plus run/perspective checks before applying a response.
- **`all` visibility semantics fixed:** `visibility == "all"` means public-like visibility for all observer perspectives. It is not god-only. Therefore Public, Role, and Team projections may see `all` events.
- **Player-count assumption fixed:** helpers infer player IDs from artifacts and fall back to the current default six-player template `p1`-`p6`; they do not hard-code six players as a future protocol limit.
- **ObjectName style retained:** new QML object names use the existing G2b camelCase style.
- **Headless smoke clarified:** when desktop GUI launch is unavailable, the implementer must run an offscreen Qt startup smoke and record the exact result.
- **Review packet line budget clarified:** the project gate remains `review-packet.md <= 300 lines`; use line-range references and compact hunk excerpts rather than relaxing the limit.

---

## Context Basis

Current route facts:

- `README.md` says G1a-G1h, G2a Local Observer Server / Protocol Control Plane, and G2b Qt Observer Cockpit MVP are completed, and the next candidate is G2c God View / Role View.
- `docs/ROADMAP.md` marks G2a and G2b as `completed`, and defines G2c as separating god-view state from role-view projections so hidden information remains auditable.
- `docs/TASKS.md` marks G2b completed with Qt Network protocol adapter, QML cockpit views, SSE parser, QtTest, and static contract tests.
- `src/werewolf_eval/observer_protocol.py` already has conservative event/snapshot visibility helpers, perspective strings, and snapshot detail loading.
- `src/werewolf_eval/observer_server.py` already exposes G2a REST/SSE endpoints for runs, events, snapshots, artifacts, and async fake-run launch.
- `clients/qt_observer` already consumes G2a REST/SSE through `ObserverApiClient` and displays a first cockpit MVP.

Recommended next development point:

```text
G2c God View / Role View Visibility Trust Layer
```

Reason:

```text
G2a provides protocol access and G2b provides a cockpit, but the product still needs an explicit trust contract proving that God/Public/Role/Team views are not merely UI toggles. G2c makes perspective projection a server-side protocol artifact and makes the Qt client visibly consume that artifact.
```

---

## Scope Summary

G2c includes:

- A focused `observer_visibility.py` helper module for seat/role/team indexing, player-card projection, event/snapshot projection envelopes, hidden counts, and trust-proof metadata.
- A new G2a endpoint: `GET /api/runs/{run_id}/projection?perspective=...`.
- Server tests proving that God/Public/Role/Team projections differ and that non-god projections do not expose hidden roles or god snapshots.
- Qt client support for projection envelopes: player cards, hidden event/snapshot counts, visibility contract version, proof metadata, and latest-wins projection refresh.
- Qt cockpit UI components for view boundary badge and projection proof panel.
- Static tests proving the Qt client uses `/projection?perspective=...`, does not infer hidden roles from raw files, and does not render all roles in non-god views.
- Review packet evidence compatible with Codex A档 packet-first review.

G2c does not include:

- Prompt/profile editor, seat-level prompt/model configuration, human-vs-AI UI, Web observer client, multi-run experiment orchestration, multi-provider arena, leaderboard, or score formula changes.
- Runtime gameplay behavior changes, provider adapter changes, generated fixtures, demo HTML, or route-doc updates.
- Client-side hidden-information filtering from raw artifacts.

---

## Visibility Contract For G2c

### Perspectives

G2c uses the existing G2a perspective strings:

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

### `all` Event Visibility Semantics

`visibility == "all"` means public-like visibility for every observer perspective. It is visible to `public`, `role:pN`, and `team:werewolf`. It is not god-only. God still sees it because God sees every event.

### Projection Envelope

The new endpoint must return a JSON object shaped like:

```json
{
  "contract_version": "g2c.visibility.v1",
  "run_id": "example_run",
  "perspective": "role:p3",
  "view_kind": "role",
  "players": [
    {"player_id":"p1","display_role":"unknown","display_team":"unknown","alive":true,"visibility":"hidden","source":"masked"},
    {"player_id":"p3","display_role":"seer","display_team":"villager","alive":true,"visibility":"self","source":"role_projection_snapshot"}
  ],
  "events": [],
  "hidden_event_count": 12,
  "snapshots": [],
  "hidden_snapshot_count": 4,
  "proof": {
    "source": "snapshots",
    "rules": ["role:p3 sees public/all events and own role-projection snapshot"],
    "self_player_id": "p3",
    "self_role": "seer",
    "self_team": "villager"
  }
}
```

Rules:

- `god` sees complete known role/team labels and all server-side visible events/snapshot metadata.
- `public` sees player seats and alive status when available, but hidden roles and teams are `unknown`.
- `role:pN` sees its own role/team only when backed by a `role_projection_snapshot` for `pN`; other hidden roles are `unknown` unless `pN`'s own role projection safely exposes them through `projected_known_roles`.
- `team:werewolf` sees werewolf teammates only when backed by role-projection data proving the player is on the werewolf team; non-wolves are `unknown`.
- If a seat-role index cannot be built from trusted role-projection snapshots, non-god projections degrade safely: role/team labels become `unknown`, role-specific event visibility is not expanded, and `proof.source = "insufficient_artifacts"`.
- Qt must not reconstruct hidden roles from raw events, snapshots, local files, static role arrays, or setup cards.

### Event Visibility Decision

G2c event projection rules:

- `god`: all events.
- `public`: `public` and `all` events.
- `role:pN`: `public` and `all` events; `seer` only when `pN` has trusted role `seer`; `witch` only when `pN` has trusted role `witch`; `werewolf_team` only when `pN` has trusted team `werewolf`.
- `team:werewolf`: `public`, `all`, and `werewolf_team` events.
- Unknown or unmapped event visibilities are hidden from non-god perspectives.

Compatibility:

```text
G2c may preserve existing G2a /events behavior for compatibility, but /projection is the canonical trusted endpoint for cockpit role/god view rendering.
```

---

## File Plan

### Create

- `src/werewolf_eval/observer_visibility.py`
  - Pure projection helper module: no networking, no Qt, no provider calls.
- `tests/test_observer_visibility.py`
  - Unit tests for projection rules, safe degradation, role/team views, hidden role masking, snapshot metadata, and proof metadata.
- `clients/qt_observer/qml/components/ViewBoundaryBadge.qml`
  - Displays current perspective, contract version, and hidden counts.
- `clients/qt_observer/qml/components/ProjectionProofPanel.qml`
  - Displays proof source, rules, hidden counts, and allowed self role/team fields.

### Modify

- `src/werewolf_eval/observer_protocol.py`
  - Only if needed for compatibility imports/constants; do not rewrite existing path helpers.
- `src/werewolf_eval/observer_server.py`
  - Add `GET /api/runs/{run_id}/projection?perspective=...`.
- `tests/test_observer_protocol.py`
  - Only if protocol helper behavior changes.
- `tests/test_observer_server.py`
  - Add `/projection` endpoint integration and non-leak tests.
- `clients/qt_observer/CMakeLists.txt`
  - Register the two new QML components in `qt_add_qml_module(... QML_FILES ...)`.
- `clients/qt_observer/src/ObserverApiClient.h`
  - Add projection QML properties and request tracking fields.
- `clients/qt_observer/src/ObserverApiClient.cpp`
  - Add projection fetch, latest-wins response guard, and perspective/run refresh behavior.
- `clients/qt_observer/qml/LiveCockpitView.qml`
  - Render projection-backed player cards, view boundary badge, and proof panel.
- `clients/qt_observer/qml/components/RoleCard.qml`
  - Render `display_role`, `display_team`, and hidden-role status.
- `clients/qt_observer/qml/components/PerspectiveSwitcher.qml`
  - Ensure perspective changes trigger projection refresh through `ObserverClient`.
- `clients/qt_observer/qml/components/AuditLinksPanel.qml`
  - Add projection endpoint as a copyable protocol artifact.
- `tests/test_qt_observer_static_contract.py`
  - Add static tests for projection endpoint use, no raw role leakage, new QML components, and latest-wins request guard.
- `.logs/review/latest/review-packet.md`
  - Implementation evidence only.
- `.oh-my-harness/tree.md`
  - Refresh only via `node .codex/hooks/tree.mjs --force`.

### Do Not Modify

- Runtime game engine behavior.
- Provider adapters or live provider paths.
- Scoring and attribution.
- Validators unrelated to observer protocol.
- Prompt/profile configuration surfaces.
- Route docs such as root `README.md`, `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/PRODUCT_ONE_PAGER.md`.
- Demo HTML, generated games, gold-game fixtures, `.github/**`, `.agents/skills/**`.

---

## Allowlist

Implementation may change only these paths:

```text
src/werewolf_eval/observer_visibility.py
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
tests/test_observer_visibility.py
tests/test_observer_protocol.py
tests/test_observer_server.py
clients/qt_observer/CMakeLists.txt
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/LiveCockpitView.qml
clients/qt_observer/qml/components/RoleCard.qml
clients/qt_observer/qml/components/PerspectiveSwitcher.qml
clients/qt_observer/qml/components/AuditLinksPanel.qml
clients/qt_observer/qml/components/ViewBoundaryBadge.qml
clients/qt_observer/qml/components/ProjectionProofPanel.qml
tests/test_qt_observer_static_contract.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

`.oh-my-harness/tree.md` is allowed only if refreshed by:

```powershell
node .codex/hooks/tree.mjs --force
```

`.logs/review/latest/review-packet.md` is allowed only for compact implementation evidence.

## Forbidden Scope

Implementation must not:

- Modify `src/werewolf_eval/game_engine.py`, `provider_agent.py`, `run_g1h_fake_runtime.py`, `run_deepseek_consensus_game.py`, `scoring.py`, `score_game.py`, or `attribution.py`.
- Modify root `README.md`, `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/PRODUCT_ONE_PAGER.md`, or `docs/adr/**`.
- Modify `docs/demo/**`, `docs/generated-games/**`, `docs/gold-game/**`, historical reviews/plans except this active plan, `.github/**`, or `.agents/skills/**`.
- Modify dependency manifests such as `pyproject.toml`, `requirements.txt`, package lockfiles, or Qt dependency files outside `clients/qt_observer/CMakeLists.txt`.
- Add live provider API calls, API key handling, provider credentials, or environment-secret handling.
- Add prompt/profile editor UI, Web UI, Electron, React/Vue, PySide/PyQt, QML WebEngine, or browser automation.
- Read local run files directly from Qt.
- Implement Qt-side hidden-information filtering from raw artifacts.
- Claim G2d, G3, or G4 completion.

---

## Task 1: Add server-side visibility projection helper

**Files:**

- Create: `src/werewolf_eval/observer_visibility.py`
- Test: `tests/test_observer_visibility.py`

- [ ] **Step 1: Add core constants and perspective helpers**

Create `observer_visibility.py` with these public names:

```python
from __future__ import annotations

import json
from pathlib import Path

CONTRACT_VERSION = "g2c.visibility.v1"
ROLE_PERSPECTIVE_PREFIX = "role:"
DEFAULT_PLAYER_IDS = tuple(f"p{i}" for i in range(1, 7))
PUBLIC_LIKE_EVENT_VISIBILITIES = frozenset({"public", "all"})
WEREWOLF_TEAM_EVENT_VISIBILITIES = frozenset({"public", "all", "werewolf_team"})
ROLE_SPECIFIC_EVENT_VISIBILITIES = frozenset({"seer", "witch"})

class VisibilityProjectionError(ValueError):
    """Raised when a visibility projection cannot be built safely."""
```

Implement:

```python
def perspective_kind(perspective: str) -> str: ...
def is_werewolf_role(role: str) -> bool: ...
def infer_player_ids(seat_index: dict[str, dict[str, object]]) -> list[str]: ...
def unknown_player(player_id: str, alive: bool | None = None) -> dict[str, object]: ...
```

Expected behavior:

- `perspective_kind("god") == "god"`, `perspective_kind("public") == "public"`, `perspective_kind("role:p3") == "role"`, and `perspective_kind("team:werewolf") == "team"`.
- Unknown perspectives raise `VisibilityProjectionError`.
- `infer_player_ids()` returns sorted IDs from the index when available and falls back to `p1`-`p6` for the current default match template.

- [ ] **Step 2: Add seat/role index builder with source trust**

Implement:

```python
def build_seat_role_index(run_dir: Path) -> dict[str, dict[str, object]]: ...
```

Each index entry shape:

```python
{
    "player_id": "p3",
    "role": "seer",
    "team": "villager",
    "alive": True,
    "role_source": "role_projection_snapshot" | "god_snapshot" | "unknown",
    "team_source": "role_projection_snapshot" | "god_snapshot" | "unknown",
    "alive_source": "role_projection_snapshot" | "god_snapshot" | "unknown",
    "projected_known_roles": {"p1": "unknown", "p3": "seer"},
}
```

Source rules:

1. Prefer each player's own `role_projection_snapshot` for that player's `role`, `team`, `alive`, and `projected_known_roles`.
2. God snapshot data may fill missing fields only for server-side god projection and diagnostics.
3. Non-god projections must not expose `role` or `team` when the corresponding source is only `god_snapshot`.
4. `projected_known_roles` is trusted only from the requesting role player's own `role_projection_snapshot`.
5. Missing or malformed snapshots produce an empty or partial index; the helper must not raise.
6. Do not return prompt text, provider secrets, local absolute paths, or secret-like fields.

- [ ] **Step 3: Add player projection builder**

Implement:

```python
def build_player_projection(
    seat_index: dict[str, dict[str, object]],
    perspective: str,
) -> list[dict[str, object]]: ...
```

Rules:

- Use `infer_player_ids(seat_index)`; fallback is `p1`-`p6` for the current default template.
- `god` exposes complete known role/team labels, including fields sourced from god snapshot.
- `public` sets hidden roles and teams to `unknown`.
- `role:pN` exposes pN's own role/team only if pN's entry has `role_source == "role_projection_snapshot"` and `team_source == "role_projection_snapshot"`.
- `role:pN` may expose non-wolf known roles only if pN's own `projected_known_roles` says so; never use another player's god-snapshot role to expose a non-god view.
- `team:werewolf` exposes only entries whose role/team are backed by `role_projection_snapshot` and prove werewolf team membership; non-wolves are `unknown`.
- Every player item includes `player_id`, `display_role`, `display_team`, `alive`, `visibility`, and `source`.

- [ ] **Step 4: Add event projection helper**

Implement:

```python
def event_visible_in_projection(
    event: dict[str, object],
    perspective: str,
    seat_index: dict[str, dict[str, object]],
) -> tuple[bool, str]: ...

def project_events(
    events: list[dict[str, object]],
    perspective: str,
    seat_index: dict[str, dict[str, object]],
) -> dict[str, object]: ...
```

Rules:

- `god`: all events, reason `god_view`.
- `public`: `public` and `all`, reason `public_event`.
- `role:pN`: `public` and `all`; `seer` only if trusted role for pN is `seer`; `witch` only if trusted role for pN is `witch`; `werewolf_team` only if trusted team for pN is `werewolf`.
- `team:werewolf`: `public`, `all`, and `werewolf_team`.
- Unknown/unmapped visibility is hidden from non-god perspectives.
- Visible event copies receive `_visibility_reason`; the original event object is not mutated.

Return shape:

```python
{
    "events": visible_events,
    "hidden_event_count": hidden_count,
    "event_visibility_reasons": {"public_event": 4, "hidden": 8}
}
```

- [ ] **Step 5: Add snapshot projection helper with exact metadata shape**

Implement:

```python
def project_snapshots(run_dir: Path, perspective: str) -> dict[str, object]: ...
```

Each snapshot metadata item must include:

```python
{
    "snapshot_name": "role-p3-round1.json",
    "snapshot_type": "role_projection" | "god" | "public" | "unknown",
    "perspective": "role:p3",
    "visible": True,
    "hidden": False,
    "round": 1,
    "phase": "night",
    "detail_endpoint": "/api/runs/{run_id}/snapshots/{snapshot_name}?perspective=role:p3",
    "hidden_reason": "none" | "not_visible_to_perspective" | "malformed_snapshot",
}
```

Optional safe fields:

- `player_id` only when visible for the perspective or when it is the requesting self player.
- `team` only when visible for the perspective.
- `timestamp` or `ts` only if present in the snapshot artifact.

Rules:

- Return metadata only, not snapshot detail content.
- Count hidden snapshots.
- Do not include absolute paths.

- [ ] **Step 6: Add projection envelope builder**

Implement:

```python
def build_projection_envelope(
    *,
    run_dir: Path,
    run_id: str,
    perspective: str,
    events: list[dict[str, object]],
) -> dict[str, object]: ...
```

Required output keys:

```text
contract_version
run_id
perspective
view_kind
players
events
hidden_event_count
snapshots
hidden_snapshot_count
proof
```

Proof rules:

- `proof.source = "snapshots"` if at least one role-projection snapshot is trusted.
- `proof.source = "insufficient_artifacts"` if no trusted role-projection data exists for non-god views.
- `proof.rules` is a list of human-readable rule strings.
- `role:pN` proof may include `self_player_id`, `self_role`, and `self_team` only if sourced from pN's own role projection.
- `team:werewolf` proof may include `team = "werewolf"` but must not list non-wolf roles.

- [ ] **Step 7: Add projection unit tests**

Create `tests/test_observer_visibility.py` with:

```python
class VisibilitySeatIndexTests(unittest.TestCase):
    def test_build_seat_role_index_reads_role_projection_snapshots(self) -> None: ...
    def test_god_snapshot_fields_are_not_trusted_for_non_god_projection(self) -> None: ...
    def test_build_seat_role_index_degrades_to_empty_on_missing_snapshots(self) -> None: ...

class VisibilityPlayerProjectionTests(unittest.TestCase):
    def test_god_projection_exposes_all_roles(self) -> None: ...
    def test_public_projection_hides_all_roles(self) -> None: ...
    def test_role_projection_exposes_only_self_role(self) -> None: ...
    def test_role_projection_uses_only_self_projected_known_roles(self) -> None: ...
    def test_werewolf_team_projection_exposes_only_trusted_wolves(self) -> None: ...

class VisibilityEventProjectionTests(unittest.TestCase):
    def test_all_visibility_is_public_like_for_all_perspectives(self) -> None: ...
    def test_seer_event_visible_only_to_trusted_seer_role(self) -> None: ...
    def test_witch_event_visible_only_to_trusted_witch_role(self) -> None: ...
    def test_werewolf_team_event_visible_to_trusted_wolves_and_team_view(self) -> None: ...
    def test_unknown_visibility_hidden_from_non_god(self) -> None: ...

class VisibilitySnapshotProjectionTests(unittest.TestCase):
    def test_snapshot_metadata_shape_has_required_fields(self) -> None: ...
    def test_hidden_snapshot_metadata_omits_unsafe_player_and_team(self) -> None: ...
    def test_snapshot_metadata_contains_no_absolute_paths(self) -> None: ...

class VisibilityEnvelopeTests(unittest.TestCase):
    def test_projection_envelope_contains_contract_version_and_proof(self) -> None: ...
    def test_projection_envelope_uses_insufficient_artifacts_source_when_no_trusted_index(self) -> None: ...
```

Use handcrafted snapshot fixtures under `TemporaryDirectory()`; do not read repository run artifacts.

- [ ] **Step 8: Run visibility focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_visibility -v
```

Expected result:

```text
OK
```

Record exact test count in the review packet.

---

## Task 2: Add G2c projection endpoint to observer server

**Files:**

- Modify: `src/werewolf_eval/observer_server.py`
- Modify: `src/werewolf_eval/observer_protocol.py` only if imports/constants need minor compatibility changes
- Test: `tests/test_observer_server.py`
- Test: `tests/test_observer_protocol.py` only if protocol behavior changes

- [ ] **Step 1: Add server import**

In `observer_server.py`, import:

```python
from werewolf_eval.observer_visibility import build_projection_envelope
```

- [ ] **Step 2: Add `/projection` dispatch**

In `ObserverRequestHandler.do_GET()`, add this branch under `/api/runs/{run_id}` before artifact aliases:

```python
if sub_path == ["projection"]:
    events_path = run_dir / "events.jsonl"
    events = _read_events_jsonl_safe(events_path)
    envelope = build_projection_envelope(
        run_dir=run_dir,
        run_id=run_id,
        perspective=perspective,
        events=events,
    )
    self._send_json(200, envelope)
    return
```

Required behavior:

- Uses the same `perspective` query parsing as `/events` and `/snapshots`.
- Returns `400` for unknown perspectives.
- Returns no absolute paths.
- Does not change `/events`, `/snapshots`, `/stream`, or artifact alias behavior.

- [ ] **Step 3: Add server integration tests**

Extend `tests/test_observer_server.py` with:

```python
class ObserverServerProjectionEndpointTests(unittest.TestCase):
    def test_projection_endpoint_returns_contract_version(self) -> None: ...
    def test_god_projection_exposes_roles(self) -> None: ...
    def test_public_projection_hides_roles(self) -> None: ...
    def test_role_projection_exposes_self_role_only(self) -> None: ...
    def test_werewolf_team_projection_hides_non_wolf_roles(self) -> None: ...
    def test_projection_rejects_unknown_perspective(self) -> None: ...
```

Fixture strategy:

- Use `TemporaryDirectory()`.
- Write controlled `events.jsonl` with `public`, `all`, `seer`, `witch`, `werewolf_team`, `private`, and `internal` events.
- Write controlled role-projection snapshot JSON files under `snapshots/`.
- Do not call live providers.

Expected assertions:

- God response includes `contract_version = g2c.visibility.v1`.
- God players include visible role labels.
- Public players contain `display_role = unknown` for hidden roles.
- `role:p3` sees p3 role but does not see p1/p2 werewolf roles.
- `team:werewolf` sees trusted wolves and hides non-wolf roles.
- Unknown perspective returns HTTP `400`.

- [ ] **Step 4: Run server projection tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_visibility tests.test_observer_server -v
```

Expected result:

```text
OK
```

---

## Task 3: Update Qt protocol adapter for projection envelopes

**Files:**

- Modify: `clients/qt_observer/src/ObserverApiClient.h`
- Modify: `clients/qt_observer/src/ObserverApiClient.cpp`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Add projection properties and request guard fields**

Add Q_PROPERTY declarations:

```cpp
Q_PROPERTY(QVariantList playerItems READ playerItems NOTIFY playerItemsChanged)
Q_PROPERTY(QVariantMap projectionProof READ projectionProof NOTIFY projectionProofChanged)
Q_PROPERTY(int hiddenEventCount READ hiddenEventCount NOTIFY projectionChanged)
Q_PROPERTY(int hiddenSnapshotCount READ hiddenSnapshotCount NOTIFY projectionChanged)
Q_PROPERTY(QString visibilityContractVersion READ visibilityContractVersion NOTIFY projectionChanged)
```

Add getters, invokable, signals, and fields:

```cpp
QVariantList playerItems() const;
QVariantMap projectionProof() const;
int hiddenEventCount() const;
int hiddenSnapshotCount() const;
QString visibilityContractVersion() const;
Q_INVOKABLE void refreshProjection();
void playerItemsChanged();
void projectionProofChanged();
void projectionChanged();

QVariantList m_playerItems;
QVariantMap m_projectionProof;
int m_hiddenEventCount = 0;
int m_hiddenSnapshotCount = 0;
QString m_visibilityContractVersion;
quint64 m_projectionRequestSerial = 0;
```

- [ ] **Step 2: Implement latest-wins projection fetch**

Implement `refreshProjection()` in `ObserverApiClient.cpp`:

```cpp
void ObserverApiClient::refreshProjection()
{
    if (m_currentRunId.isEmpty())
        return;

    const quint64 requestSerial = ++m_projectionRequestSerial;
    const QString requestedRunId = m_currentRunId;
    const QString requestedPerspective = m_currentPerspective;

    QUrl url(m_baseUrl + QStringLiteral("/api/runs/") + requestedRunId + QStringLiteral("/projection"));
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("perspective"), requestedPerspective);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setRawHeader("Accept", "application/json");
    QNetworkReply *reply = m_network->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, requestSerial, requestedRunId, requestedPerspective]() {
        reply->deleteLater();
        if (requestSerial != m_projectionRequestSerial || requestedRunId != m_currentRunId || requestedPerspective != m_currentPerspective)
            return;
        if (reply->error() != QNetworkReply::NoError) {
            setError(reply->errorString());
            return;
        }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) {
            setError(QStringLiteral("Invalid projection response"));
            return;
        }
        QJsonObject obj = doc.object();
        m_visibilityContractVersion = obj.value(QStringLiteral("contract_version")).toString();
        m_hiddenEventCount = obj.value(QStringLiteral("hidden_event_count")).toInt();
        m_hiddenSnapshotCount = obj.value(QStringLiteral("hidden_snapshot_count")).toInt();

        QVariantList players;
        for (const QJsonValue &v : obj.value(QStringLiteral("players")).toArray())
            players.append(v.toObject().toVariantMap());
        m_playerItems = players;
        m_projectionProof = obj.value(QStringLiteral("proof")).toObject().toVariantMap();

        emit playerItemsChanged();
        emit projectionProofChanged();
        emit projectionChanged();
    });
}
```

Required integration points:

- `setCurrentPerspective()` calls `refreshProjection()` after changing perspective.
- `startDefaultMatch()` calls `refreshProjection()` after setting `currentRunId`.
- `openRun()` calls `refreshProjection()` after setting `currentRunId`.
- `refreshAuditLinks()` adds copyable path `/projection?perspective=<currentPerspective>`.
- Stale projection responses must be ignored and must not overwrite the current UI state.

- [ ] **Step 3: Add Qt static endpoint and race-guard tests**

Extend `tests/test_qt_observer_static_contract.py`:

```python
class QtObserverProjectionClientTests(unittest.TestCase):
    def test_observer_client_uses_projection_endpoint(self) -> None: ...
    def test_observer_client_exposes_projection_properties(self) -> None: ...
    def test_projection_refresh_happens_on_perspective_change(self) -> None: ...
    def test_projection_request_uses_latest_wins_guard(self) -> None: ...
```

Expected assertions:

- `ObserverApiClient.cpp` contains `/projection` and `perspective` query construction.
- `ObserverApiClient.h` contains `playerItems`, `projectionProof`, `hiddenEventCount`, `hiddenSnapshotCount`, and `visibilityContractVersion`.
- `setCurrentPerspective()` calls `refreshProjection()`.
- Source contains `m_projectionRequestSerial`, `requestSerial`, `requestedRunId`, and `requestedPerspective` stale-response checks.

- [ ] **Step 4: Run Qt static projection tests**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected result:

```text
OK
```

---

## Task 4: Add Qt visibility trust UI components

**Files:**

- Modify: `clients/qt_observer/CMakeLists.txt`
- Create: `clients/qt_observer/qml/components/ViewBoundaryBadge.qml`
- Create: `clients/qt_observer/qml/components/ProjectionProofPanel.qml`
- Modify: `clients/qt_observer/qml/components/RoleCard.qml`
- Modify: `clients/qt_observer/qml/LiveCockpitView.qml`
- Modify: `clients/qt_observer/qml/components/PerspectiveSwitcher.qml`
- Modify: `clients/qt_observer/qml/components/AuditLinksPanel.qml`
- Test: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Register new QML files in CMake**

Add to the existing `qt_add_qml_module(... QML_FILES ...)` list:

```cmake
qml/components/ViewBoundaryBadge.qml
qml/components/ProjectionProofPanel.qml
```

- [ ] **Step 2: Implement `ViewBoundaryBadge.qml`**

Required properties:

```qml
property string perspective
property string contractVersion
property int hiddenEventCount
property int hiddenSnapshotCount
```

Required object names use existing G2b camelCase style:

```text
viewBoundaryBadge
viewBoundaryPerspective
viewBoundaryHiddenCounts
```

Required display text:

```text
God View
Public View
Role View
Werewolf Team View
g2c.visibility.v1
hidden events
hidden snapshots
```

- [ ] **Step 3: Implement `ProjectionProofPanel.qml`**

Required properties:

```qml
property var proof
property int hiddenEventCount
property int hiddenSnapshotCount
```

Required object names:

```text
projectionProofPanel
projectionProofSource
projectionProofRules
projectionProofHiddenCounts
```

Required behavior:

- Displays `proof.source`.
- Displays proof rules as text/list.
- Displays self role/team only when present in proof.
- Does not display non-self hidden role table.

- [ ] **Step 4: Update `RoleCard.qml` for projection data**

Add properties:

```qml
property string displayRole
property string displayTeam
property string visibilityLabel
```

Required behavior:

- If `displayRole == "unknown"`, render role as `Unknown` or `Hidden`.
- Render `visibilityLabel` as a status tag.
- Do not assume setup-time role names inside live cockpit role cards.

- [ ] **Step 5: Update `LiveCockpitView.qml`**

Required behavior:

- Imports `components`.
- Displays `ViewBoundaryBadge` bound to `ObserverClient.currentPerspective`, `ObserverClient.visibilityContractVersion`, `ObserverClient.hiddenEventCount`, and `ObserverClient.hiddenSnapshotCount`.
- Displays `ProjectionProofPanel` bound to `ObserverClient.projectionProof`.
- Uses `ObserverClient.playerItems` for cockpit player cards.
- Calls `ObserverClient.refreshProjection()` when entering cockpit.
- Maintains existing event timeline and audit links.
- Does not use hardcoded static role labels for cockpit display.

- [ ] **Step 6: Update `PerspectiveSwitcher.qml` and `AuditLinksPanel.qml`**

Required behavior:

- `PerspectiveSwitcher` calls `ObserverClient.currentPerspective = selectedPerspective` and relies on `ObserverApiClient` to refresh projection.
- `AuditLinksPanel` includes a copyable projection endpoint path:

```text
/api/runs/{run_id}/projection?perspective={perspective}
```

- [ ] **Step 7: Extend static UI tests**

Add:

```python
class QtObserverVisibilityUiTests(unittest.TestCase):
    def test_visibility_components_are_registered_in_cmake(self) -> None: ...
    def test_live_cockpit_uses_projection_player_items(self) -> None: ...
    def test_live_cockpit_contains_boundary_badge_and_proof_panel(self) -> None: ...
    def test_role_card_supports_hidden_role_rendering(self) -> None: ...
    def test_cockpit_does_not_hardcode_god_roles_as_live_player_source(self) -> None: ...
```

Expected assertions:

- CMake contains both new component filenames.
- `LiveCockpitView.qml` contains `ObserverClient.playerItems`, `ViewBoundaryBadge`, and `ProjectionProofPanel`.
- `RoleCard.qml` contains `displayRole`, `displayTeam`, and `Unknown` or `Hidden`.
- Cockpit player model is not a hardcoded `p1 Werewolf` / `p2 Werewolf` role list.

- [ ] **Step 8: Run Qt static tests and build**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
ctest --test-dir .tmp/qt-observer-build --output-on-failure
```

Expected:

- Python static tests: `OK`.
- CMake configure exits `0`.
- Build exits `0`.
- CTest: `100% tests passed`.

---

## Task 5: Add end-to-end trust regression tests

**Files:**

- Modify: `tests/test_observer_visibility.py`
- Modify: `tests/test_observer_server.py`
- Modify: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Add server non-leak regression tests**

Add to `tests/test_observer_server.py`:

```python
class ObserverServerVisibilityNonLeakTests(unittest.TestCase):
    def test_public_projection_response_does_not_contain_werewolf_role_labels(self) -> None: ...
    def test_role_projection_response_does_not_contain_other_hidden_roles(self) -> None: ...
    def test_team_werewolf_projection_response_does_not_contain_non_wolf_roles(self) -> None: ...
    def test_projection_response_contains_no_absolute_paths(self) -> None: ...
```

Required checks:

- Public JSON response must not contain `"display_role":"werewolf"`.
- Role response for a non-wolf player must not expose other hidden werewolf roles.
- Team werewolf response must not expose `seer` or `witch` as non-wolf roles.
- Response text must not contain the temporary directory absolute path.

- [ ] **Step 2: Add Qt no hidden-role hardcoding tests**

Add to `tests/test_qt_observer_static_contract.py`:

```python
class QtObserverHiddenInfoBoundaryTests(unittest.TestCase):
    def test_live_cockpit_does_not_embed_static_role_assignments(self) -> None: ...
    def test_qml_boundary_copy_mentions_server_projection(self) -> None: ...
    def test_qt_client_does_not_use_local_snapshot_or_event_paths(self) -> None: ...
```

Required checks:

- `LiveCockpitView.qml` does not use fixed role arrays like `Werewolf`, `Seer`, `Witch`, `Villager` as the live player model.
- Boundary/proof UI mentions server projection or G2c visibility contract.
- Qt client source/QML does not contain `events.jsonl`, `snapshots/`, `QFile`, or `QDir` for runtime artifacts.

- [ ] **Step 3: Run trust regression tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_visibility tests.test_observer_server -v
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected:

```text
OK
OK
```

Record exact test counts in review packet.

---

## Task 6: Manual G2c smoke evidence

**Files:**

- Modify: none
- Test: manual smoke evidence only

- [ ] **Step 1: Launch local G2a server and start a default run**

Run in terminal 1:

```powershell
Remove-Item -Recurse -Force .tmp/g2c-visibility-smoke -ErrorAction SilentlyContinue
$env:PYTHONPATH='src'; python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .tmp/g2c-visibility-smoke/runs
```

Run in terminal 2:

```powershell
Invoke-RestMethod -Method Post -ContentType 'application/json' -Body '{"template":"default_6p_fake","mode":"fake"}' http://127.0.0.1:8765/api/runs
```

Expected:

- POST returns `202` with `run_id`.
- `GET /api/runs/{run_id}` eventually reports `completed`.

- [ ] **Step 2: Query projection endpoints manually**

Replace `<run_id>` with the returned ID:

```powershell
Invoke-RestMethod "http://127.0.0.1:8765/api/runs/<run_id>/projection?perspective=god"
Invoke-RestMethod "http://127.0.0.1:8765/api/runs/<run_id>/projection?perspective=public"
Invoke-RestMethod "http://127.0.0.1:8765/api/runs/<run_id>/projection?perspective=role:p3"
Invoke-RestMethod "http://127.0.0.1:8765/api/runs/<run_id>/projection?perspective=team:werewolf"
```

Expected:

- Every response has `contract_version = g2c.visibility.v1`.
- God response exposes roles.
- Public response hides roles as `unknown`.
- Role response exposes only its own trusted role/team and hides other hidden roles.
- Werewolf team response exposes trusted wolf teammates and hides non-wolf roles.

- [ ] **Step 3: Launch Qt app and switch perspectives**

Run:

```powershell
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
& .tmp/qt-observer-build/appqt_observer.exe --observer-base-url http://127.0.0.1:8765
```

Expected manual UI result:

```text
Live Cockpit perspective switcher changes player-card role visibility; ViewBoundaryBadge and ProjectionProofPanel show contract/proof information; raw JSON is not the primary UI.
```

- [ ] **Step 4: Headless fallback smoke when desktop GUI is unavailable**

If desktop GUI cannot launch, run an offscreen startup smoke and record the result:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$p = Start-Process -FilePath .tmp/qt-observer-build/appqt_observer.exe -ArgumentList '--observer-base-url','http://127.0.0.1:8765' -PassThru
Start-Sleep -Seconds 5
if ($p.HasExited) { throw "Qt app exited during offscreen startup smoke with code $($p.ExitCode)" }
Stop-Process -Id $p.Id
$env:QT_QPA_PLATFORM=$null
```

Expected:

- App stays alive for 5 seconds and is then stopped by the script.
- Record `MANUAL_G2C_VISIBILITY_SMOKE = HEADLESS_OFFSCREEN_PASS` if REST projection smoke also passed.

Record `MANUAL_G2C_VISIBILITY_SMOKE = PASS` only if desktop UI flow succeeds. If only headless smoke is possible, record the headless result and the exact environment limitation.

---

## Task 7: Full validation commands

**Files:**

- Modify: `.logs/review/latest/review-packet.md`
- Modify: `.oh-my-harness/tree.md` through tree hook if needed

- [ ] **Step 1: Run focused G2c server tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_visibility tests.test_observer_server tests.test_observer_protocol -v
```

Expected result: `OK`. Record exact test count.

- [ ] **Step 2: Run Qt static tests**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected result: `OK`.

- [ ] **Step 3: Configure and build Qt client**

Run:

```powershell
Remove-Item -Recurse -Force .tmp/qt-observer-build -ErrorAction SilentlyContinue
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
```

Expected:

- Configure exits `0`.
- Build exits `0`.

- [ ] **Step 4: Run Qt CTest tests**

Run:

```powershell
ctest --test-dir .tmp/qt-observer-build --output-on-failure
```

Expected result: `100% tests passed`.

- [ ] **Step 5: Run full unit suite**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Expected result: `OK`.

If a known unrelated pre-existing failure appears, include exact failing test name, proof it fails on `main` or was documented before this change, and focused G2c test pass summary.

- [ ] **Step 6: Compile Python files**

Run:

```powershell
python -m compileall src tests
```

Expected result: `0 failures`.

- [ ] **Step 7: Run diff whitespace check**

Run:

```powershell
git diff --check main...HEAD
```

Expected result: no output.

- [ ] **Step 8: Run changed files allowlist check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; allowed=set('''src/werewolf_eval/observer_visibility.py
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
tests/test_observer_visibility.py
tests/test_observer_protocol.py
tests/test_observer_server.py
clients/qt_observer/CMakeLists.txt
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/LiveCockpitView.qml
clients/qt_observer/qml/components/RoleCard.qml
clients/qt_observer/qml/components/PerspectiveSwitcher.qml
clients/qt_observer/qml/components/AuditLinksPanel.qml
clients/qt_observer/qml/components/ViewBoundaryBadge.qml
clients/qt_observer/qml/components/ProjectionProofPanel.qml
tests/test_qt_observer_static_contract.py
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md'''.splitlines()); changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p not in allowed]; print('\n'.join(changed)); assert not bad, 'outside allowlist: '+repr(bad)"
```

Expected: prints only allowed files and exits `0`.

- [ ] **Step 9: Run forbidden-scope check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; forbidden_prefixes=('docs/demo/','docs/generated-games/','docs/gold-game/','docs/adr/','.github/','.agents/skills/'); forbidden_exact={'README.md','docs/ROADMAP.md','docs/TASKS.md','docs/PRODUCT_ONE_PAGER.md','src/werewolf_eval/game_engine.py','src/werewolf_eval/provider_agent.py','src/werewolf_eval/run_g1h_fake_runtime.py','src/werewolf_eval/run_deepseek_consensus_game.py','src/werewolf_eval/scoring.py','src/werewolf_eval/score_game.py','src/werewolf_eval/attribution.py'}; changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p in forbidden_exact or p.startswith(forbidden_prefixes)]; print('\n'.join(bad)); assert not bad, 'forbidden scope changed: '+repr(bad)"
```

Expected: no output.

- [ ] **Step 10: Run forbidden pattern scan**

Run:

```powershell
git diff main...HEAD -- src tests clients/qt_observer | python -c "import sys; data=sys.stdin.read(); added=[line for line in data.splitlines() if line.startswith('+') and not line.startswith('+++')]; markers=['Authorization:', 'Bearer ', 'DEEPSEEK_API_KEY=', 'sk-', 'api_key', 'api-key']; hits=[line for line in added if any(marker in line for marker in markers)]; print('\n'.join(hits)); unsafe=[line for line in hits if 'secret' not in line.lower() and 'marker' not in line.lower() and 'scan' not in line.lower() and 'forbidden' not in line.lower()]; assert not unsafe, 'unsafe forbidden pattern hits: '+repr(unsafe)"
```

Expected:

- No unsafe committed secret values.
- Safe literal markers inside secret-scan tests may print and must be listed in the review packet as safe test fixtures.

- [ ] **Step 11: Run dependency/import diff check**

Run:

```powershell
git diff --name-only main...HEAD -- package.json package-lock.json pyproject.toml requirements.txt poetry.lock pnpm-lock.yaml yarn.lock uv.lock CMakeLists.txt clients/qt_observer/CMakeLists.txt
```

Expected:

- Only `clients/qt_observer/CMakeLists.txt` may appear.
- No root dependency manifests may appear.

Also run:

```powershell
git diff main...HEAD -- src tests clients/qt_observer | python -c "import sys,re; data=sys.stdin.read(); risky=[line for line in data.splitlines() if line.startswith('+') and re.search(r'(requests|httpx|aiohttp|websockets|fastapi|flask|starlette|uvicorn|openai|anthropic|PySide6|PyQt6|QProcess|file://)', line)]; print('\n'.join(risky)); unsafe=[line for line in risky if 'forbidden' not in line.lower() and 'scan' not in line.lower() and 'marker' not in line.lower()]; assert not unsafe, 'unexpected dependency/import/runtime-binding addition: '+repr(unsafe)"
```

Expected: no output.

- [ ] **Step 12: Verify no build/runtime artifacts are staged**

Run:

```powershell
git diff --name-only --cached | python -c "import sys; bad=[p.strip() for p in sys.stdin if p.strip().startswith('.tmp/') or p.strip().startswith('.runs/') or '/build/' in p.strip() or p.strip().endswith('.user')]; assert not bad, 'staged build/runtime artifacts: '+repr(bad); print('NO_STAGED_BUILD_OR_RUNTIME_ARTIFACTS')"
```

Expected result: `NO_STAGED_BUILD_OR_RUNTIME_ARTIFACTS`.

- [ ] **Step 13: Refresh tree for new files**

Run:

```powershell
node .codex/hooks/tree.mjs --force
```

Expected:

- `.oh-my-harness/tree.md` includes `observer_visibility.py`, `test_observer_visibility.py`, `ViewBoundaryBadge.qml`, and `ProjectionProofPanel.qml` by filename.
- It must not include `.tmp/`, `.runs/`, build directories, or Qt Creator `.user` files.

---

## Acceptance Criteria

A1. G2c adds a server-side visibility projection helper module with contract version `g2c.visibility.v1`.

A2. The server exposes `GET /api/runs/{run_id}/projection?perspective=...`.

A3. Projection responses include `contract_version`, `run_id`, `perspective`, `view_kind`, `players`, `events`, `hidden_event_count`, `snapshots`, `hidden_snapshot_count`, and `proof`.

A4. God projection exposes complete known role/team labels.

A5. Public projection hides hidden roles and teams as `unknown`.

A6. Role projection exposes only the selected player's own trusted role/team and does not expose other hidden roles from god snapshots.

A7. Werewolf team projection exposes only trusted wolf teammates and hides non-wolf roles.

A8. Role-specific seer/witch events are visible only to the matching trusted role perspective.

A9. `all` visibility is public-like and visible to Public/Role/Team projections.

A10. Unknown or unmapped event visibility is hidden from non-god projections.

A11. Snapshot metadata uses the required minimal field shape and contains no detail content or absolute local paths.

A12. Projection envelopes include proof metadata explaining source and rules without leaking non-self hidden roles.

A13. Projection responses contain no absolute local paths and no raw secret markers.

A14. Qt `ObserverApiClient` fetches `/projection?perspective=...`, exposes player/proof/hidden-count properties, refreshes projection when perspective or run changes, and ignores stale projection responses.

A15. Qt Live Cockpit uses `ObserverClient.playerItems` for cockpit player cards instead of hardcoded god-view role labels.

A16. Qt UI includes `ViewBoundaryBadge` and `ProjectionProofPanel` and displays contract version plus hidden event/snapshot counts.

A17. Qt client continues to consume only G2a protocol endpoints and does not read local `events.jsonl`, `snapshots/`, or use `QProcess`.

A18. G2c does not modify runtime gameplay, provider adapters, scoring, validators unrelated to observer protocol, route docs, demo/generated/gold artifacts, or dependency manifests outside Qt CMake.

A19. Focused visibility tests, observer server/protocol tests, Qt static tests, Qt build/CTest, full unit suite, compileall, diff check, allowlist check, forbidden-scope check, forbidden-pattern check, dependency/import check, and build-artifact staging check pass or are documented with exact environment/pre-existing failure evidence.

A20. `.logs/review/latest/review-packet.md` exists, is compact, and contains the machine-generated evidence required below.

---

## Review Packet Requirements

After implementation, create or update:

```text
.logs/review/latest/review-packet.md
```

The packet must be compact and must not rely on oral summaries. The project gate is `review-packet.md <= 300 lines`; do not relax this to 400 lines. Use line-range references for most key hunks, and include only short excerpts for the highest-risk changes. If the limit cannot be met, mark `PACKET_TOO_LARGE = YES` and provide B档 file ranges.

The packet must include these sections in this order.

### 1. Metadata

Include:

```markdown
# Review Packet — G2c God View / Role View Visibility Trust

- Plan: `docs/harness/plans/2026-06-03--g2c-god-role-view-visibility-trust-plan.md`
- Implementer: <name or agent id from local context>
- Date: <YYYY-MM-DD>
- Branch: <branch name>
- Base: `main`
- PR: <PR number or `not-opened`>
- Verdict target: G2c visibility trust layer only
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

Include command and exact result:

```powershell
git diff --check main...HEAD
```

For pass, record `DIFF_CHECK = PASS`.

### 5. Allowed Files Check

Include Task 7 Step 8 command and exact result. For pass, record `ALLOWLIST_CHECK = PASS`.

### 6. Forbidden Patterns Check

Include Task 7 Step 10 command and exact result. For pass, record `FORBIDDEN_PATTERN_CHECK = PASS`. If safe test fixture markers print, list them under `SAFE_TEST_MARKER_HITS`.

### 7. Dependency / Import Diff

Include both Task 7 Step 11 commands and exact result. For pass, record:

```text
DEPENDENCY_DIFF_CHECK = PASS
RISKY_IMPORT_CHECK = PASS
```

### 8. Test Summary

Include each command and exact observed summary:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_visibility tests.test_observer_server tests.test_observer_protocol -v
python -m unittest tests.test_qt_observer_static_contract -v
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug
ctest --test-dir .tmp/qt-observer-build --output-on-failure
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
```

For each, include `exit_code` and exact pass/fail summary. If Qt GUI manual smoke cannot run due to headless environment, state the exact limitation and include offscreen smoke/server evidence.

### 9. Key Hunks

Use compact line-range references with very short excerpts. Include references for:

- `observer_visibility.py` seat-role index source-trust rules,
- `observer_visibility.py` player projection rules,
- `observer_visibility.py` event projection rules including `all` semantics,
- `observer_visibility.py` snapshot metadata shape,
- `observer_visibility.py` projection envelope builder,
- `observer_server.py` `/projection` endpoint dispatch,
- server tests proving Public/Role/Team non-leak behavior,
- `ObserverApiClient` projection properties, `/projection` endpoint call, and latest-wins guard,
- `LiveCockpitView.qml` projection-backed player cards,
- `ViewBoundaryBadge.qml` and `ProjectionProofPanel.qml`,
- static tests proving no cockpit hardcoded role leakage.

Each entry must include file path and line range after implementation.

### 10. Evidence Map

Include a Markdown table with exactly these columns:

```markdown
| Acceptance | Evidence | Status |
|------------|----------|--------|
| A1 | `observer_visibility.py:Lx-Ly`; `VisibilityEnvelopeTests.test_projection_envelope_contains_contract_version_and_proof` | PASS |
```

Every A1-A20 item must have one row. Evidence must point to a test name, command result, manual/offscreen smoke result, or key hunk line range.

### 11. Acceptance Checklist

Include checklist form for A1-A20. Each item must include an evidence pointer.

### 12. Implementer Risk Notes

Include:

```markdown
## Implementer Risk Notes

- G2c is cross-cutting: server projection helpers, observer endpoint, and Qt cockpit display all change together.
- Projection is server-side; Qt consumes `/projection?perspective=...` and does not read local run artifacts.
- God snapshot data must not be used to expose non-god role/team labels; non-god projections trust only role-projection snapshot data and the requesting role's own `projected_known_roles`.
- `all` visibility is public-like and visible to Public/Role/Team perspectives.
- Projection requests in Qt use latest-wins request guards to avoid stale perspective responses overwriting current UI state.
- Snapshot projection returns metadata only; snapshot detail remains controlled by G2a snapshot endpoints.
- Full prompt/profile editor remains G2d; G2c does not add prompt or model configuration UI.
- Manual GUI smoke may depend on local Qt desktop availability; offscreen smoke plus build/CTest/static/server evidence is acceptable when documented.
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

Because G2c is cross-cutting and the allowlist contains more than 8 possible files, the implementer must expect `POTENTIAL_CODEX_B_DEEP_REVIEW_TRIGGER = YES` if changed files exceed the review-packet-gate threshold. If triggered, provide focused B档 ranges for:

```text
src/werewolf_eval/observer_visibility.py
src/werewolf_eval/observer_server.py
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/LiveCockpitView.qml
tests/test_observer_visibility.py
tests/test_observer_server.py
tests/test_qt_observer_static_contract.py
```

---

## Potential Codex B档 Deep Review Triggers

The implementation may trigger B档 deeper review if any of these happen:

- Changed file count exceeds 8.
- Diff stat indicates more than 500 changed lines.
- `observer_visibility.py` exceeds 350 lines.
- `observer_server.py` projection change touches unrelated endpoint behavior.
- `ObserverApiClient.cpp` exceeds 500 lines.
- Any change touches forbidden scope such as runtime engine, provider adapter, scoring, route docs, generated fixtures, demo HTML, or dependency manifests outside Qt CMake.
- Any non-god projection returns hidden werewolf/seer/witch role labels that are not allowed by the current perspective.
- Any Qt source reads local files, references `events.jsonl`, uses `QProcess`, or bypasses G2a protocol.
- Any endpoint response contains absolute local paths or secret markers.
- Qt build or CTest fails without exact environment limitation and passing static/server tests.
- Review packet lacks Metadata, Evidence Map, Review Trigger Result, key hunk excerpts, or acceptance evidence pointers.

If triggered, the review packet must name explicit files and line ranges for B档 review.

---

## Implementation PR Description Draft

Title:

```text
feat: add G2c god/role visibility trust layer
```

Body:

```markdown
## Summary

- Adds a server-side G2c visibility projection layer with `g2c.visibility.v1` projection envelopes.
- Adds `/api/runs/{run_id}/projection?perspective=...` to the observer protocol.
- Makes God/Public/Role/Team player-card visibility explicit and auditable.
- Updates the Qt cockpit to render projection-backed player cards, hidden counts, boundary badge, and proof panel.
- Adds server, visibility, Qt static, and no-leak tests.

## Scope

- G2c visibility trust layer only.
- No prompt/profile editor, no Web UI, no human-vs-AI UI, no arena, no leaderboard.
- No runtime gameplay, provider adapter, scoring, route-doc, generated fixture, or demo HTML changes.

## Validation

- `$env:PYTHONPATH='src'; python -m unittest tests.test_observer_visibility tests.test_observer_server tests.test_observer_protocol -v`
- `python -m unittest tests.test_qt_observer_static_contract -v`
- `cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug`
- `cmake --build .tmp/qt-observer-build --config Debug`
- `ctest --test-dir .tmp/qt-observer-build --output-on-failure`
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"`
- `python -m compileall src tests`
- `git diff --check main...HEAD`
- allowlist / forbidden-scope / forbidden-pattern / dependency/import checks recorded in `.logs/review/latest/review-packet.md`

## Review Packet

`.logs/review/latest/review-packet.md` contains Metadata, machine-generated evidence, key hunk line ranges, Evidence Map, acceptance checklist pointers, implementer risk notes, and Review Trigger Result.
```

---

## Execution Handoff

Implementation should proceed task-by-task in order:

1. Server-side visibility projection helper and unit tests.
2. `/projection` observer endpoint and server integration tests.
3. Qt protocol adapter projection properties, latest-wins guard, and endpoint calls.
4. Qt boundary/proof UI components and cockpit integration.
5. End-to-end non-leak regression tests.
6. Manual or headless G2c smoke evidence.
7. Full validation and review packet.

Do not modify prompt/profile configuration. Do not expand into G2d. Do not read local artifacts from Qt. Do not claim G3/G4 evaluation capabilities.
