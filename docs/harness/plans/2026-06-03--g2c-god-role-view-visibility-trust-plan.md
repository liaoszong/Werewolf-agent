# G2c God View / Role View Visibility Trust Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add the G2c visibility trust layer so God/Public/Role/Team views are explicit, auditable, and enforced end-to-end across the G2a observer protocol and G2b Qt cockpit.

**Architecture:** Implement a focused server-side visibility projection layer that builds a run-local seat/role/team index from existing G1h/G2a artifacts, returns projection envelopes through a new G2a protocol endpoint, and adds proof metadata explaining what each perspective can and cannot see. Update the Qt cockpit to consume the projection endpoint, render perspective-aware player cards, hidden-count badges, and proof panels without reading local files or implementing independent hidden-information filtering.

**Tech Stack:** Python standard library, existing G2a stdlib HTTP server, Python `unittest`, Qt 6.8+ / Qt Quick / Qt Network / Qt Test, CMake, C++17, QML. No new third-party dependencies, no provider API calls, no prompt/profile editor.

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
G2a provides protocol access and G2b provides a cockpit, but the product still needs an explicit trust contract proving that God/Public/Role/Team views are not merely UI toggles. G2c should make perspective projection a server-side protocol artifact and make the Qt client visibly consume that artifact.
```

## Scope Summary

G2c includes:

- A focused `observer_visibility.py` helper module for seat/role/team indexing, player-card projection, event/snapshot projection envelopes, and trust-proof metadata.
- A new G2a endpoint: `GET /api/runs/{run_id}/projection?perspective=...`.
- Server tests proving that God/Public/Role/Team projections differ and that non-god projections do not expose hidden roles or god snapshots.
- Qt client support for projection envelopes: player cards, hidden event/snapshot counts, visibility contract version, and trust proof notes.
- Qt cockpit UI components for view boundary badge and projection proof panel.
- Static tests proving the Qt client uses `/projection?perspective=...`, does not infer hidden roles from raw files, and does not render all roles in non-god views.
- Review packet evidence compatible with Codex A档 packet-first review.

G2c does not include:

- Prompt/profile editor.
- Seat-level prompt/model configuration.
- Human-vs-AI UI.
- Web observer client.
- Multi-run experiment orchestration.
- Multi-provider arena.
- Leaderboard or score formula changes.
- Runtime gameplay behavior changes.
- Provider adapter changes.
- New generated fixtures or demo HTML.
- Client-side hidden-information filtering from raw artifacts.

---

## Visibility Contract For G2c

### Perspectives

G2c must use the existing G2a perspective strings:

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

### Projection Envelope

The new endpoint must return a JSON object shaped like:

```json
{
  "contract_version": "g2c.visibility.v1",
  "run_id": "example_run",
  "perspective": "role:p3",
  "view_kind": "role",
  "players": [
    {"player_id":"p1","display_role":"unknown","display_team":"unknown","alive":true,"visibility":"hidden"},
    {"player_id":"p3","display_role":"seer","display_team":"villager","alive":true,"visibility":"self"}
  ],
  "events": [],
  "hidden_event_count": 12,
  "snapshots": [],
  "hidden_snapshot_count": 4,
  "proof": {
    "source": "snapshots",
    "rules": ["role:p3 sees public events and own role-projection snapshots"],
    "self_player_id": "p3",
    "self_role": "seer",
    "self_team": "villager"
  }
}
```

Rules:

- `god` sees complete player role/team labels and all visible server-side events/snapshots.
- `public` sees player seats and alive status when available, but hidden roles and teams are displayed as `unknown`.
- `role:pN` sees its own role/team, public-like event data, and own role-projection snapshots. Other players' hidden roles are `unknown` unless the role projection explicitly exposes them through `projected_known_roles`.
- `team:werewolf` sees werewolf teammates as werewolves, sees non-wolf roles as `unknown`, and sees werewolf-team events/snapshots allowed by G2a.
- Projection must be server-side. Qt must not reconstruct hidden roles from raw events, snapshots, or local files.
- If a seat-role index cannot be built from run artifacts, non-god projections must degrade safely: role/team labels become `unknown`, role-specific event visibility is not expanded, and `proof.source = "insufficient_artifacts"`.

### Event Visibility Decision

G2c must keep conservative event filtering:

- `god`: all events.
- `public`: public-like events only.
- `role:pN`: public-like events and safe role-specific events only when the server can prove the role from the seat-role index.
- `team:werewolf`: public-like events and werewolf-team events.
- Unknown or unmapped event visibilities are hidden from non-god perspectives.

Implementation detail:

```text
G2c may preserve existing G2a /events behavior for compatibility, but /projection must be the canonical trusted endpoint for cockpit role/god view rendering.
```

---

## File Plan

### Create

- `src/werewolf_eval/observer_visibility.py`
  - Owns G2c projection helpers: seat index, player-card projection, projection envelope, hidden counts, and proof metadata.
  - Pure helper module: no network server lifecycle, no Qt, no provider calls.

- `tests/test_observer_visibility.py`
  - Unit tests for projection rules, safe degradation, role/team views, hidden role masking, and proof metadata.

- `clients/qt_observer/qml/components/ViewBoundaryBadge.qml`
  - Displays current perspective, contract version, and warning/ready state.

- `clients/qt_observer/qml/components/ProjectionProofPanel.qml`
  - Displays server-provided proof source, rules, hidden counts, and self role/team when allowed.

### Modify

- `src/werewolf_eval/observer_protocol.py`
  - Import or delegate event/snapshot projection where needed without moving existing public constants.
  - Keep backward-compatible perspective strings.

- `src/werewolf_eval/observer_server.py`
  - Add `GET /api/runs/{run_id}/projection?perspective=...` endpoint.
  - Serve projection envelopes from `observer_visibility.py`.

- `tests/test_observer_protocol.py`
  - Add or adjust focused tests only if protocol helper behavior changes.

- `tests/test_observer_server.py`
  - Add endpoint integration tests for `/projection`.

- `clients/qt_observer/CMakeLists.txt`
  - Register `ViewBoundaryBadge.qml` and `ProjectionProofPanel.qml` in `qt_add_qml_module(... QML_FILES ...)`.

- `clients/qt_observer/src/ObserverApiClient.h`
  - Add QML properties for projection data.

- `clients/qt_observer/src/ObserverApiClient.cpp`
  - Add projection fetch and perspective-change refresh behavior.

- `clients/qt_observer/qml/LiveCockpitView.qml`
  - Render projection-backed player cards, view boundary badge, and proof panel.

- `clients/qt_observer/qml/components/RoleCard.qml`
  - Render `display_role`, `display_team`, and hidden-role status instead of always showing static setup roles inside cockpit.

- `clients/qt_observer/qml/components/PerspectiveSwitcher.qml`
  - Ensure perspective changes trigger projection refresh through `ObserverClient`.

- `clients/qt_observer/qml/components/AuditLinksPanel.qml`
  - Link to projection endpoint as a copyable protocol artifact.

- `tests/test_qt_observer_static_contract.py`
  - Add static tests for projection endpoint use, no raw role leakage, and new QML components.

- `.logs/review/latest/review-packet.md`
  - Implementation evidence only.

- `.oh-my-harness/tree.md`
  - Refresh only via `node .codex/hooks/tree.mjs --force` because new files are created.

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
- Add prompt/profile editor UI.
- Add Web UI, Electron, React/Vue, PySide/PyQt, QML WebEngine, or browser automation.
- Read local run files directly from Qt.
- Implement Qt-side hidden-information filtering from raw artifacts.
- Claim G2d, G3, or G4 completion.

---

## Task 1: Add server-side visibility projection helper

**Files:**

- Create: `src/werewolf_eval/observer_visibility.py`
- Test: `tests/test_observer_visibility.py`

- [ ] **Step 1: Add core data helpers**

Create `observer_visibility.py` with these public names:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "g2c.visibility.v1"
ROLE_PERSPECTIVE_PREFIX = "role:"
PUBLIC_LIKE_EVENT_VISIBILITIES = frozenset({"public", "all"})
WEREWOLF_TEAM_EVENT_VISIBILITIES = frozenset({"public", "all", "werewolf_team"})
ROLE_SPECIFIC_EVENT_VISIBILITIES = frozenset({"seer", "witch"})

class VisibilityProjectionError(ValueError):
    """Raised when a visibility projection cannot be built safely."""
```

Implement helpers:

```python
def perspective_kind(perspective: str) -> str: ...
def is_werewolf_role(role: str) -> bool: ...
def unknown_player(player_id: str, alive: bool | None = None) -> dict[str, object]: ...
```

Expected behavior:

- `perspective_kind("god") == "god"`.
- `perspective_kind("public") == "public"`.
- `perspective_kind("role:p3") == "role"`.
- `perspective_kind("team:werewolf") == "team"`.
- Unknown perspectives raise `VisibilityProjectionError`.

- [ ] **Step 2: Add seat/role index builder**

Implement:

```python
def build_seat_role_index(run_dir: Path) -> dict[str, dict[str, object]]: ...
```

Source order:

1. Prefer role-projection snapshots under `run_dir / "snapshots"`.
2. Fill missing fields from god snapshots only inside server-side helper logic.
3. Do not expose god snapshot content to non-god callers.
4. If no role data is available, return an empty dict.

Each index entry shape:

```python
{
    "player_id": "p3",
    "role": "seer",
    "team": "villager",
    "alive": True,
    "source": "role_projection_snapshot" | "god_snapshot" | "unknown",
}
```

Required behavior:

- It must never raise for missing snapshots; missing artifacts produce an empty or partial index.
- It must ignore malformed snapshot files.
- It must not return prompt text or secret-like fields.

- [ ] **Step 3: Add player projection builder**

Implement:

```python
def build_player_projection(
    seat_index: dict[str, dict[str, object]],
    perspective: str,
) -> list[dict[str, object]]: ...
```

Rules:

- Always return six seats `p1` through `p6` sorted by player id.
- For `god`, expose `display_role` and `display_team` for every known seat.
- For `public`, set hidden roles and teams to `unknown`.
- For `role:pN`, expose only pN's own role/team; other players are `unknown` unless the pN role-projection snapshot's `projected_known_roles` safely exposes a non-wolf known role.
- For `team:werewolf`, expose werewolf teammates as `werewolf` / `werewolf`; non-wolves are `unknown`.
- Every player item includes `player_id`, `display_role`, `display_team`, `alive`, and `visibility` where `visibility` is one of `full`, `self`, `team`, `public`, `hidden`, or `unknown`.

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
- `public`: only `public` and `all`, reason `public_event`.
- `role:pN`: public-like events; also `seer` only if pN role is `seer`; `witch` only if pN role is `witch`; `werewolf_team` only if pN team is `werewolf`.
- `team:werewolf`: public-like and `werewolf_team`.
- Unknown/unmapped visibility is hidden from non-god perspectives.
- Visible event copies receive `_visibility_reason` but must not mutate the original event object.

Return shape:

```python
{
    "events": visible_events,
    "hidden_event_count": hidden_count,
    "event_visibility_reasons": {"public_event": 4, "hidden": 8}
}
```

- [ ] **Step 5: Add snapshot projection helper**

Implement:

```python
def project_snapshots(
    run_dir: Path,
    perspective: str,
) -> dict[str, object]: ...
```

Rules:

- Use existing `build_snapshot_registry(run_dir, perspective)` semantics when possible.
- Return metadata only, not snapshot detail content.
- Count hidden snapshots.
- No absolute paths.

Return shape:

```python
{
    "snapshots": snapshot_metadata,
    "hidden_snapshot_count": hidden_count,
}
```

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

- `proof.source` is `snapshots` if at least one seat role is known.
- `proof.source` is `insufficient_artifacts` if the seat index is empty.
- `proof.rules` is a list of human-readable rule strings.
- `role:pN` proof may include `self_player_id`, `self_role`, and `self_team` only for pN.
- `team:werewolf` proof may include `team = "werewolf"` but must not list non-wolf roles.

- [ ] **Step 7: Add projection unit tests**

Create `tests/test_observer_visibility.py` with these classes:

```python
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from werewolf_eval.observer_visibility import (
    CONTRACT_VERSION,
    build_projection_envelope,
    build_seat_role_index,
    build_player_projection,
    event_visible_in_projection,
    project_events,
)

class VisibilitySeatIndexTests(unittest.TestCase):
    def test_build_seat_role_index_reads_role_projection_snapshots(self) -> None: ...
    def test_build_seat_role_index_degrades_to_empty_on_missing_snapshots(self) -> None: ...

class VisibilityPlayerProjectionTests(unittest.TestCase):
    def test_god_projection_exposes_all_roles(self) -> None: ...
    def test_public_projection_hides_all_roles(self) -> None: ...
    def test_role_projection_exposes_only_self_role(self) -> None: ...
    def test_werewolf_team_projection_exposes_only_wolves(self) -> None: ...

class VisibilityEventProjectionTests(unittest.TestCase):
    def test_seer_event_visible_only_to_seer_role(self) -> None: ...
    def test_witch_event_visible_only_to_witch_role(self) -> None: ...
    def test_werewolf_team_event_visible_to_wolves_and_team_view(self) -> None: ...
    def test_unknown_visibility_hidden_from_non_god(self) -> None: ...

class VisibilityEnvelopeTests(unittest.TestCase):
    def test_projection_envelope_contains_contract_version_and_proof(self) -> None: ...
    def test_projection_envelope_uses_insufficient_artifacts_source_when_no_index(self) -> None: ...
```

Use handcrafted snapshot fixtures; do not read repository run artifacts.

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

In `ObserverRequestHandler.do_GET()`, add a branch under `/api/runs/{run_id}`:

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
- Returns `400` for unknown perspectives through existing `normalize_perspective()`/helper validation.
- Returns no absolute paths.
- Does not change `/events`, `/snapshots`, `/stream`, or artifact alias behavior in this task.

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
- Write controlled `events.jsonl` with public, seer, witch, werewolf_team, private, and internal events.
- Write controlled role-projection snapshot JSON files under `snapshots/`.
- Do not call live providers.

Expected assertions:

- God response includes `contract_version = g2c.visibility.v1`.
- God players include visible role labels.
- Public players contain `display_role = unknown` for hidden roles.
- `role:p3` sees p3 role but does not see p1/p2 werewolf roles.
- `team:werewolf` sees p1/p2 as werewolves and hides non-wolf roles.
- Unknown perspective returns HTTP 400.

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

- [ ] **Step 1: Add projection properties to `ObserverApiClient.h`**

Add Q_PROPERTY declarations:

```cpp
Q_PROPERTY(QVariantList playerItems READ playerItems NOTIFY playerItemsChanged)
Q_PROPERTY(QVariantMap projectionProof READ projectionProof NOTIFY projectionProofChanged)
Q_PROPERTY(int hiddenEventCount READ hiddenEventCount NOTIFY projectionChanged)
Q_PROPERTY(int hiddenSnapshotCount READ hiddenSnapshotCount NOTIFY projectionChanged)
Q_PROPERTY(QString visibilityContractVersion READ visibilityContractVersion NOTIFY projectionChanged)
```

Add getters:

```cpp
QVariantList playerItems() const;
QVariantMap projectionProof() const;
int hiddenEventCount() const;
int hiddenSnapshotCount() const;
QString visibilityContractVersion() const;
```

Add invokable:

```cpp
Q_INVOKABLE void refreshProjection();
```

Add signals:

```cpp
void playerItemsChanged();
void projectionProofChanged();
void projectionChanged();
```

Add private fields:

```cpp
QVariantList m_playerItems;
QVariantMap m_projectionProof;
int m_hiddenEventCount = 0;
int m_hiddenSnapshotCount = 0;
QString m_visibilityContractVersion;
```

- [ ] **Step 2: Implement projection fetch in `ObserverApiClient.cpp`**

Add method:

```cpp
void ObserverApiClient::refreshProjection()
{
    if (m_currentRunId.isEmpty())
        return;

    QUrl url(m_baseUrl + QStringLiteral("/api/runs/") + m_currentRunId + QStringLiteral("/projection"));
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("perspective"), m_currentPerspective);
    url.setQuery(query);
    QNetworkRequest req(url);
    req.setRawHeader("Accept", "application/json");
    QNetworkReply *reply = m_network->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
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
- `connectStream()` does not replace projection fetching; it remains event streaming only.
- `refreshAuditLinks()` adds copyable path `/projection?perspective=<currentPerspective>`.

- [ ] **Step 3: Add static endpoint tests**

Extend `tests/test_qt_observer_static_contract.py`:

```python
class QtObserverProjectionClientTests(unittest.TestCase):
    def test_observer_client_uses_projection_endpoint(self) -> None: ...
    def test_observer_client_exposes_projection_properties(self) -> None: ...
    def test_projection_refresh_happens_on_perspective_change(self) -> None: ...
```

Expected assertions:

- `ObserverApiClient.cpp` contains `/projection` and `perspective` query construction.
- `ObserverApiClient.h` contains `playerItems`, `projectionProof`, `hiddenEventCount`, `hiddenSnapshotCount`, and `visibilityContractVersion`.
- `setCurrentPerspective()` calls `refreshProjection()`.

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

Required object names:

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
- Calls `ObserverClient.refreshProjection()` when entering cockpit or after perspective change.
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
- Role response for a villager/interesting role must not expose other hidden werewolf roles.
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

- [ ] **Step 1: Generate or launch a local default run through G2a**

Run:

```powershell
Remove-Item -Recurse -Force .tmp/g2c-visibility-smoke -ErrorAction SilentlyContinue
$env:PYTHONPATH='src'; python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .tmp/g2c-visibility-smoke/runs
```

In a second terminal:

```powershell
Invoke-RestMethod -Method Post -ContentType 'application/json' -Body '{"template":"default_6p_fake","mode":"fake"}' http://127.0.0.1:8765/api/runs
```

Expected:

- POST returns `202` with `run_id`.
- Run status eventually becomes `completed` from `GET /api/runs/{run_id}`.

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
- Role response exposes only its own role/team and hides other hidden roles.
- Werewolf team response exposes wolf teammates and hides non-wolf roles.

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

Record:

```text
MANUAL_G2C_VISIBILITY_SMOKE = PASS
```

only if the flow succeeds. If GUI cannot launch due to headless environment, record exact environment limitation and include server projection/manual REST evidence plus Qt build/CTest/static evidence.

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

Expected result:

```text
OK
```

Record exact test count.

- [ ] **Step 2: Run Qt static tests**

Run:

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

Expected result:

```text
OK
```

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

Expected result:

```text
100% tests passed
```

- [ ] **Step 5: Run full unit suite**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Expected result:

```text
OK
```

If a known unrelated pre-existing failure appears, include exact failing test name, proof it fails on `main` or was documented before this change, and focused G2c test pass summary.

- [ ] **Step 6: Compile Python files**

Run:

```powershell
python -m compileall src tests
```

Expected result:

```text
0 failures
```

- [ ] **Step 7: Run diff whitespace check**

Run:

```powershell
git diff --check main...HEAD
```

Expected result:

```text
(no output)
```

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

Expected:

- Prints only allowed files.
- Exits `0`.

- [ ] **Step 9: Run forbidden-scope check**

Run:

```powershell
git diff --name-only main...HEAD | python -c "import sys; forbidden_prefixes=('docs/demo/','docs/generated-games/','docs/gold-game/','docs/adr/','.github/','.agents/skills/'); forbidden_exact={'README.md','docs/ROADMAP.md','docs/TASKS.md','docs/PRODUCT_ONE_PAGER.md','src/werewolf_eval/game_engine.py','src/werewolf_eval/provider_agent.py','src/werewolf_eval/run_g1h_fake_runtime.py','src/werewolf_eval/run_deepseek_consensus_game.py','src/werewolf_eval/scoring.py','src/werewolf_eval/score_game.py','src/werewolf_eval/attribution.py'}; changed=[line.strip() for line in sys.stdin if line.strip()]; bad=[p for p in changed if p in forbidden_exact or p.startswith(forbidden_prefixes)]; print('\n'.join(bad)); assert not bad, 'forbidden scope changed: '+repr(bad)"
```

Expected:

```text
(no output)
```

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

Expected:

```text
(no output)
```

- [ ] **Step 12: Verify no build/runtime artifacts are staged**

Run:

```powershell
git diff --name-only --cached | python -c "import sys; bad=[p.strip() for p in sys.stdin if p.strip().startswith('.tmp/') or p.strip().startswith('.runs/') or '/build/' in p.strip() or p.strip().endswith('.user')]; assert not bad, 'staged build/runtime artifacts: '+repr(bad); print('NO_STAGED_BUILD_OR_RUNTIME_ARTIFACTS')"
```

Expected result:

```text
NO_STAGED_BUILD_OR_RUNTIME_ARTIFACTS
```

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

A6. Role projection exposes only the selected player's own role/team and does not expose other hidden roles.

A7. Werewolf team projection exposes werewolf teammates and hides non-wolf roles.

A8. Role-specific seer/witch events are visible only to the matching role perspective when the server can prove that role from the seat index.

A9. Unknown or unmapped event visibility is hidden from non-god projections.

A10. Projection envelopes include proof metadata explaining source and rules without leaking non-self hidden roles.

A11. Projection responses contain no absolute local paths and no raw secret markers.

A12. Qt `ObserverApiClient` fetches `/projection?perspective=...`, exposes player/proof/hidden-count properties, and refreshes projection when perspective or run changes.

A13. Qt Live Cockpit uses `ObserverClient.playerItems` for cockpit player cards instead of hardcoded god-view role labels.

A14. Qt UI includes `ViewBoundaryBadge` and `ProjectionProofPanel` and displays contract version plus hidden event/snapshot counts.

A15. Qt client continues to consume only G2a protocol endpoints and does not read local `events.jsonl`, `snapshots/`, or use `QProcess`.

A16. G2c does not modify runtime gameplay, provider adapters, scoring, validators unrelated to observer protocol, route docs, demo/generated/gold artifacts, or dependency manifests outside Qt CMake.

A17. Focused visibility tests, observer server/protocol tests, Qt static tests, Qt build/CTest, full unit suite, compileall, diff check, allowlist check, forbidden-scope check, forbidden-pattern check, dependency/import check, and build-artifact staging check pass or are documented with exact environment/pre-existing failure evidence.

A18. `.logs/review/latest/review-packet.md` exists, is compact, and contains the machine-generated evidence required below.

---

## Review Packet Requirements

After implementation, create or update:

```text
.logs/review/latest/review-packet.md
```

The packet must be compact and must not rely on oral summaries. Keep the packet at or under 300 lines; if impossible, mark `PACKET_TOO_LARGE = YES` and provide B档 file ranges. It must include these sections in this order.

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

For each, include `exit_code` and exact pass/fail summary. If Qt GUI manual smoke cannot run due to headless environment, state the exact limitation and include build/CTest/static/server evidence.

### 9. Key Hunks

Include concise excerpts, not full diffs, for:

- `observer_visibility.py` seat-role index builder,
- `observer_visibility.py` player projection rules,
- `observer_visibility.py` event projection rules,
- `observer_visibility.py` projection envelope builder,
- `observer_server.py` `/projection` endpoint dispatch,
- server tests proving Public/Role/Team non-leak behavior,
- `ObserverApiClient` projection properties and `/projection` endpoint call,
- `LiveCockpitView.qml` projection-backed player cards,
- `ViewBoundaryBadge.qml` and `ProjectionProofPanel.qml`,
- static tests proving no cockpit hardcoded role leakage.

Each excerpt must include file path and line range after implementation.

### 10. Evidence Map

Include a Markdown table with exactly these columns:

```markdown
| Acceptance | Evidence | Status |
|------------|----------|--------|
| A1 | `observer_visibility.py:Lx-Ly`; `VisibilityEnvelopeTests.test_projection_envelope_contains_contract_version_and_proof` | PASS |
```

Every A1-A18 item must have one row. Evidence must point to a test name, command result, manual smoke result, or key hunk line range.

### 11. Acceptance Checklist

Include checklist form for A1-A18. Each item must include an evidence pointer.

Example:

```markdown
- [x] A6 role projection exposes only self role — `VisibilityPlayerProjectionTests.test_role_projection_exposes_only_self_role`; `ObserverServerVisibilityNonLeakTests.test_role_projection_response_does_not_contain_other_hidden_roles`
```

### 12. Implementer Risk Notes

Include:

```markdown
## Implementer Risk Notes

- G2c is cross-cutting: server projection helpers, observer endpoint, and Qt cockpit display all change together.
- Projection is server-side; Qt consumes `/projection?perspective=...` and does not read local run artifacts.
- Seat/role index is built from existing snapshots and degrades safely when artifacts are insufficient.
- Role-specific seer/witch event visibility is enabled only when the server can prove the role from the seat index.
- Public and non-matching role/team perspectives hide hidden roles as `unknown`.
- Full prompt/profile editor remains G2d; G2c does not add prompt or model configuration UI.
- Manual GUI smoke may depend on local Qt desktop availability; build/CTest/static/server evidence remains required.
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

`.logs/review/latest/review-packet.md` contains Metadata, machine-generated evidence, key hunk excerpts, Evidence Map, acceptance checklist pointers, implementer risk notes, and Review Trigger Result.
```

---

## Execution Handoff

Implementation should proceed task-by-task in order:

1. Server-side visibility projection helper and unit tests.
2. `/projection` observer endpoint and server integration tests.
3. Qt protocol adapter projection properties and endpoint calls.
4. Qt boundary/proof UI components and cockpit integration.
5. End-to-end non-leak regression tests.
6. Manual G2c smoke evidence.
7. Full validation and review packet.

Do not modify prompt/profile configuration. Do not expand into G2d. Do not read local artifacts from Qt. Do not claim G3/G4 evaluation capabilities.
