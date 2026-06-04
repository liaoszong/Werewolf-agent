# G2d-2 Qt Profile Setup UI — Design Spec

- **Date:** 2026-06-04
- **Status:** Approved design — pending implementation plan
- **Roadmap item:** G2d Prompt Configuration MVP (charter Phase F) — UI half
- **Slice:** G2d-2 (Qt setup UI). Builds on the merged G2d-1 backend (PR #39).
- **Base:** `main` (contains G2d-1: `profile_config.py`, `/api/profiles*`, `resolved-profile.json`).

---

## 1. Goal

Make G2d profile configuration **user-facing**: turn the Qt cockpit's `MatchSetupView` into a profile-driven setup editor that loads an existing server-side profile from the G2d-1 endpoints, lets the user edit per-seat provider/model/strategy/prompt, validates it server-side, and launches a fake run from it — all through the G2a protocol, with no local file I/O.

This completes the G2d milestone end-to-end (G2d-1 = backend; G2d-2 = UI). It is the work the existing `MatchSetupView.qml` placeholder already announces ("提示词/档案编辑计划于 G2d 实现 / Prompt/profile editing is planned for G2d").

## 2. Locked decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Editor depth | **Full per-seat** — provider/model/strategy/prompt | Exercises the whole `g2d.profile.v1` schema the backend already validates. |
| D2 | Save/import | **Defer save** — load → edit → validate → launch | The Qt client is forbidden local file I/O (contract test bans `QFile`/`QDir`/`file://`), and G2d-1 deliberately exposes no server write endpoint. "Import" = picking an existing server-side profile. Save lands in a later slice that adds a server write endpoint. |
| D3 | Layout | **Master-detail** — seat grid (left) + editor panel (right) | The split `MatchSetupView.qml` already anticipates; fits the wizard page + bottom action bar. |
| D4 | Dropdown allowlists | **Read-only `GET /api/profiles/schema`** | The UI must not hardcode provider/model/strategy lists (drift + violates the "don't bake backend truth into QML" contract philosophy). One read-only endpoint = single source of truth. No write surface. |

## 3. Context anchors (current code)

- `clients/qt_observer/qml/MatchSetupView.qml` (170 lines) — wizard page: left-aligned title, hardcoded `roles` array (p1–p6), `SectionHeader` + `Grid` of `RoleCard`s (objectName `setupRoleCards`), bottom action bar (Back ghost left, `setupContinueButton` primary right → `navigatePreflight()`). Contains the "G2d planned" note (lines 93–99) and a "no editor" stance.
- `clients/qt_observer/src/ObserverApiClient.h/.cpp` — singleton with `get(path)`/`post(path, body)` helpers, `startDefaultMatch()` (POST `/api/runs`), `refreshProjection()` (latest-wins serial guard, a model for new fetches), Q_PROPERTY/NOTIFY pattern.
- `clients/qt_observer/CMakeLists.txt` — `qt_add_qml_module(... QML_FILES ...)` lists views/components; `Theme`/`I18n` are `QT_QML_SINGLETON_TYPE`.
- Design system (`Theme.qml`, `I18n.qml`): tokens `Theme.color/space/radius/font/size/weight`, layout `Theme.layout.pageMargin=40`/`contentMax=1040`/`actionBarHeight=72`; components `AppButton` (primary/secondary/ghost/danger), `AppCard`, `SectionHeader`, `EmptyState`, `RoleCard` (faction tints/stripe, omitted for `unknown`). `I18n.t(zh, en)` — **English is always the 2nd arg** (keeps contract-test substrings in files). Default language zh.
- `tests/test_qt_observer_static_contract.py` — required QML files + objectNames (MatchSetupView → `matchSetupView`, `setupRoleCards`, `setupContinueButton`), forbidden-pattern scan (`events.jsonl`, `snapshots/`, `QFile`, `QDir`, `file://`), `test_setup_contains_default_six_player_roles` (asserts p1–p6 + role names in MatchSetupView), and `QtObserverReadmeTests` asserting `clients/qt_observer/README.md` contains `"no full prompt/profile editor"`.
- G2d-1 backend (merged): `profile_config.py` constants (`ALLOWED_PROVIDERS`, `ALLOWED_MODELS`, `ALLOWED_STRATEGIES`, `DEFAULT_6P_SEAT_ROLES`, `ROLE_TEAMS`, `PROMPT_MAX_LEN`), endpoints `GET /api/profiles`, `GET /api/profiles/{name}`, `POST /api/profiles/validate`, `POST /api/runs {profile|profile_name}`.

**Build feasibility:** Qt 6.10 mingw toolchain on `F:` with a configured `.tmp/qt-observer-build`; build, static-contract test, `ctest`, `qmllint`, and **visual** verification (`grabToImage` → PNG → Read) all run in this environment. No environment blocker (contrast G2d-1 server tests).

## 4. Architecture

```
GET /api/profiles ───────► profile picker (names)
GET /api/profiles/schema ─► dropdown options (providers/models/strategies) + seat→role layout
GET /api/profiles/{name} ─► loadedProfile ──► seat grid (left) + SeatEditorPanel (right)
                                   │ edit seat → seat_overrides[pN]
                                   ▼
POST /api/profiles/validate ◄──── Validate button ──► verdict + errors (inline)
POST /api/runs {profile} ◄─────── Launch button ───► currentRunId → Preflight/Cockpit
```

The backend gains one read-only endpoint. The Qt client gains profile fetch/validate/launch methods. `MatchSetupView` becomes master-detail; a new `SeatEditorPanel` component holds the per-seat editor. No new runtime behavior; execution stays the fake-deterministic G2d-1 path (`resolved-profile.json` written server-side).

## 5. Components

### 5.1 `src/werewolf_eval/profile_config.py` (MODIFY — add one pure function)

- `build_profile_schema() -> dict` — returns UI metadata from the existing constants:
  ```json
  {
    "schema_version": "g2d.profile.v1",
    "providers": ["deepseek", "fake_deterministic"],
    "models": {"deepseek": ["deepseek-chat", "deepseek-reasoner"], "fake_deterministic": ["none"]},
    "strategies": ["aggressive", "cautious", "default"],
    "roles": ["seer", "villager", "werewolf", "witch"],
    "role_teams": {"werewolf": "werewolf", "seer": "villager", "witch": "villager", "villager": "villager"},
    "seat_roles": {"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager", "p6": "villager"},
    "seat_ids": ["p1", "p2", "p3", "p4", "p5", "p6"],
    "prompt_max_len": 8000
  }
  ```
  Lists are sorted for determinism. No secrets, no paths. **No `templates` / profile-name list here** — the schema is dropdown/option metadata only; the set of available profiles comes solely from `GET /api/profiles`, so the UI never learns "which profiles exist" from two diverging sources.

### 5.2 `src/werewolf_eval/observer_server.py` + `observer_protocol.py` (MODIFY — one read endpoint)

- `GET /api/profiles/schema` → `build_profile_schema()` (200). Placed alongside the existing `/api/profiles` routes; no perspective, no params. Read-only.

### 5.3 `clients/qt_observer/src/ObserverApiClient.h/.cpp` (MODIFY)

- Properties (Q_PROPERTY + NOTIFY): `QVariantList profileItems`, `QVariantMap profileSchema`, `QVariantMap loadedProfile`, `QVariantMap profileValidation`.
- Invokables:
  - `refreshProfiles()` → GET `/api/profiles` → `profileItems`.
  - `refreshProfileSchema()` → GET `/api/profiles/schema` → `profileSchema`.
  - `fetchProfile(QString name)` → GET `/api/profiles/{name}` → `loadedProfile`.
  - `validateProfile(QVariantMap profile)` → POST `/api/profiles/validate` → `profileValidation` (`{valid, errors, resolved_seats}`).
  - `launchFromProfile(QVariantMap profile)` → POST `/api/runs` with `{profile}`. **Only on HTTP `202`** does it set `currentRunId`/status and emit `launchSucceeded()`; on any non-202 / network error it sets `lastError`, emits `launchFailed()`, and does **not** set `currentRunId` (mirrors `startDefaultMatch`'s success path but never advances optimistically).
- Each GET/validate uses a monotonically increasing serial + run/name guard (the `refreshProjection` latest-wins pattern) so stale responses don't overwrite newer UI state.
- JSON assembly via `QJsonDocument`/`QJsonObject` from the `QVariantMap` (no string building).

### 5.4 `clients/qt_observer/qml/components/SeatEditorPanel.qml` (NEW)

- Properties: `seat` (`{player_id, role, team}`), `config` (`{provider, model, strategy, prompt}`), `schema` (from `ObserverClient.profileSchema`).
- Controls (Quick Controls + design tokens): provider `ComboBox` (from `schema.providers`) → model `ComboBox` (from `schema.models[provider]`, resets when provider changes) → strategy `ComboBox` (from `schema.strategies`) → prompt `TextArea` with a live `len / prompt_max_len` counter that turns `Theme.color.danger` past the limit.
- ObjectNames (camelCase, per G2b style): `seatEditorPanel`, `seatEditorProvider`, `seatEditorModel`, `seatEditorStrategy`, `seatEditorPrompt`.
- Emits `edited(string field, var value)` (or writes into a bound override map) so `MatchSetupView` records a `seat_overrides[player_id]` entry. Pure presentation; no network, no file I/O.

### 5.5 `clients/qt_observer/qml/MatchSetupView.qml` (MODIFY — master-detail)

- On entry: `ObserverClient.refreshProfiles()` + `refreshProfileSchema()`; **default-select the first item of `profileItems`** → `fetchProfile(name)`. If `profileItems` is empty, show an `EmptyState` ("no profiles — drop a JSON into the server's profiles/ dir") and disable Launch.
- Header: profile picker `ComboBox` (`objectName: setupProfilePicker`) bound to `ObserverClient.profileItems`; selecting → `fetchProfile(name)`.
- Master (left): seat `Grid` of `RoleCard`s (keeps `setupRoleCards`) driven by the resolved seats of `loadedProfile` (+ local edits); clicking a seat selects it (highlight) and opens the detail.
- Detail (right): `SeatEditorPanel` bound to the selected seat's resolved config; edits update a local `editedProfile` (clone of `loadedProfile` with `seat_overrides[pN]` applied).
- Validate affordance (`objectName: setupValidateButton`): `ObserverClient.validateProfile(editedProfile)`; render `profileValidation.valid` / `errors[]` inline (a `SectionHeader` caption or a small status row).
- Action bar: Back (ghost left) → `navigateHome()`; **Launch** (primary right, keep objectName `setupContinueButton` so the existing contract assertion holds, label → "启动 / Launch") → `ObserverClient.launchFromProfile(editedProfile)`. **The view advances to Preflight only after the launch request returns `202` and `currentRunId` is updated** (wire to `launchSucceeded()` / `onCurrentRunChanged`). On `launchFailed()` it stays on `MatchSetupView` and surfaces `lastError` (and any `profileValidation` error). No optimistic navigation.
- Launch is enabled only when `profileValidation.valid` holds for the current edit (see §7) — so the user validates before launching.
- Removes the static `roles` array and the "G2d planned / no editor" note.

### 5.6 `clients/qt_observer/CMakeLists.txt` (MODIFY)

- Register `qml/components/SeatEditorPanel.qml` in `qt_add_qml_module(... QML_FILES ...)`.

### 5.7 `clients/qt_observer/README.md` (MODIFY)

- Update the non-goals: remove `no full prompt/profile editor`; state that G2d-2 adds a profile setup editor consuming `/api/profiles*` (still no Web client, no Python binding, no local artifact reads, no provider secrets).

### 5.8 Tests

- `tests/test_profile_config.py` (MODIFY) — `build_profile_schema` shape: providers/models/strategies match the allowlists, `seat_roles` == canonical, `prompt_max_len` == 8000, sorted, no secrets/paths.
- `tests/test_observer_protocol.py` / `tests/test_observer_server.py` (MODIFY) — `/api/profiles/schema` returns the schema (server test env-blocked like other server tests; authored + documented).
- `tests/test_qt_observer_static_contract.py` (MODIFY) — see §9.

## 6. Editing model & data flow

1. `loadedProfile` (from `/api/profiles/{name}`) has `role_defaults` (+ maybe partial `seat_overrides`). The UI resolves seats client-side for **display only**; role/team come from `schema.seat_roles` + `schema.role_teams`, and each config field is merged **field-by-field**:
   ```
   effective[field] = seat_overrides[player_id][field]  if that field is present,
                      otherwise role_defaults[role][field]
   for field in {provider, model, strategy, prompt}
   ```
   This tolerates existing profiles whose `seat_overrides[pN]` carry only some fields. The UI display logic is kept distinct from the server resolver — the server remains authoritative.
2. Editing seat `pN` **materializes a full coherent fragment** `editedProfile.seat_overrides[pN] = {provider, model, strategy, prompt}` — seeded from the current *effective* values, with the edited field changed; changing `provider` resets `model` to that provider's first allowed model (so the materialized fragment always satisfies G2d-1's resolved-seat coherence rule).
3. **Validate** posts `editedProfile` to `/api/profiles/validate` → inline verdict; the server is the single source of validity truth (UI does no independent validation beyond coherence-friendly dropdowns).
4. **Launch** posts `{profile: editedProfile}` to `/api/runs`; on `202` the client tracks the run and the wizard advances to Preflight → Cockpit (where the existing G2c projection UI shows the run).

## 7. Error / validation UX

- **Validation is bound to the current edit via a local `profileRevision` counter.** Any edit (seat-override change or profile reload) increments `profileRevision` and clears `profileValidation`. The Validate handler remembers which revision it validated; **Launch is enabled only when `profileValidation.valid` is true for the current `profileRevision`** — so editing after a passing Validate re-disables Launch until re-validated. No stale "valid" state can leak into a launch.
- Invalid profile on Validate → show `profileValidation.errors[0]` (single-error mode from G2d-1) in a `Theme.color.danger` caption.
- Network/`lastError` surfaces in the existing error affordance.
- Prompt over `prompt_max_len` → counter turns danger; Validate also rejects server-side.

## 8. Design-system adherence

- All strings `I18n.t(zh, en)` (English 2nd arg). Default zh.
- Tokens only (no literal colors/sizes); charcoal/silver palette; `AppButton` variants; `AppCard`/`SectionHeader`; 1px borders, no glows.
- Wizard layout: left-aligned at `pageMargin`, bottom action bar Back-left / primary-right; view root `Item` must not `anchors.fill: parent` (StackView sizes it).
- `RoleCard` faction tints stay (this is god-view setup, roles are intentionally shown — distinct from the live-cockpit visibility boundary).

## 9. Verification strategy

The Qt-side gates — build, static-contract, ctest, qmllint, visual — are **runnable in this environment**. The new `/api/profiles/schema` server endpoint test is **authored and documented but not canonically runnable here** (same `RemoteDisconnected` localhost limit as the other G2a/G2d server tests); the underlying `build_profile_schema()` is covered by a pure `test_profile_config` unit test that **does** run.

- **Build:** `cmake --build .tmp/qt-observer-build --target appqt_observer` exit 0 (qmlcachegen AOT-compiles QML → syntactic validity gate). PATH via `/f/...` mount form.
- **Static contract** (`tests/test_qt_observer_static_contract.py`) — **update + extend**:
  - register `SeatEditorPanel.qml`; new objectNames (`setupProfilePicker`, `setupValidateButton`, `seatEditorPanel`/`seatEditorProvider`/`seatEditorModel`/`seatEditorStrategy`/`seatEditorPrompt`);
  - assert MatchSetupView references `ObserverClient.profileItems` / `loadedProfile` / `launchFromProfile` / `validateProfile`;
  - assert it does **not** hardcode provider/model lists (options come from `profileSchema`);
  - replace `test_setup_contains_default_six_player_roles` so seats/roles are driven by profile/schema, not a static `roles` array;
  - update `QtObserverReadmeTests` ("no full prompt/profile editor" assertion removed / replaced);
  - keep forbidden-pattern scan green (`QFile`/`QDir`/`file://`/`events.jsonl`/`snapshots/`).
- **ctest** (`.tmp/qt-observer-build`) — SSE parser test stays green.
- **qmllint** — only `Error:` lines matter.
- **Visual:** temp `Timer` in AppShell navigating to MatchSetup with a profile loaded + a seat selected → `grabToImage` → PNG under `.tmp/` → Read the image to confirm master-detail layout, dropdowns, prompt area, action bar. Remove the harness after.

## 10. Boundaries — non-goals this slice

- No profile **save** to the server (load+edit+launch only); no client local file I/O.
- No new server **write** surface beyond the existing G2d-1 endpoints; the only backend addition is the read-only `/api/profiles/schema`.
- No live providers / API keys / secrets; execution stays fake-deterministic.
- No Web client, no Python runtime binding, no changes to game engine / fake runtime / scoring / route-product docs.
- No multi-profile experiment orchestration (that is G3).

## 11. Allowlist (files this slice may touch)

```
src/werewolf_eval/profile_config.py            (add build_profile_schema)
src/werewolf_eval/observer_protocol.py          (schema route constant if needed)
src/werewolf_eval/observer_server.py            (GET /api/profiles/schema)
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/components/SeatEditorPanel.qml   (new)
clients/qt_observer/qml/MatchSetupView.qml
clients/qt_observer/CMakeLists.txt
clients/qt_observer/README.md
tests/test_profile_config.py
tests/test_observer_protocol.py
tests/test_observer_server.py
tests/test_qt_observer_static_contract.py
docs/superpowers/specs/2026-06-04-g2d-2-qt-setup-ui-design.md
docs/harness/plans/2026-06-04--g2d-2-qt-setup-ui-plan.md
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

## 12. Acceptance criteria (expanded in the plan)

- A1. `GET /api/profiles/schema` returns providers/models/strategies/seat_roles/prompt_max_len from the constants (read-only, no secrets/paths).
- A2. `ObserverApiClient` exposes `profileItems`, `profileSchema`, `loadedProfile`, `profileValidation` + `refreshProfiles`/`refreshProfileSchema`/`fetchProfile`/`validateProfile`/`launchFromProfile`, with latest-wins guards.
- A3. `SeatEditorPanel.qml` edits provider/model(dependent)/strategy/prompt(with counter), registered in CMake, with the required objectNames.
- A4. `MatchSetupView.qml` is profile-driven master-detail: picker + seat grid + editor + validate + launch; no static role array; consumes `profileSchema` (no hardcoded option lists).
- A5. Launch sends the edited profile to `/api/runs` and **advances to Preflight only after `202` + `currentRunId` is set** (otherwise stays on MatchSetupView and shows the error); the run is observable via the existing cockpit.
- A6. Static-contract test updated + green (new objectNames/components, README non-goal updated, forbidden patterns absent); Qt build exit 0; ctest green.
- A7. Visual capture confirms the master-detail editor renders per the design system.
- A8. No save endpoint, no local file I/O, no live providers, no new deps, no engine/route-doc changes.

## 13. Future (out of scope)

- Server-side profile **save** endpoint + UI save/import-from-file (needs a write surface + path-safety, like G2d-1 `save_profile`).
- Role-defaults editing mode (vs per-seat overrides), profile diffing, multi-template support.
- G3 experiment orchestration over batches of profiles.

### Deferred UX enhancements (from a frontend design review)

This slice keeps the **master-detail + explicit-Validate** design. A reviewed-but-deferred richer iteration (a "G2d-3" UX pass) would, in priority order:

1. **Global "Deterministic Mock" execution banner** + a dropdown caption — surfaces the declared-vs-executed (`execution_mode=fake`) distinction so users never think a real LLM is called. (Cheap; strong fit with the auditability ethos — a good first fast-follow.)
2. **Prompt focus-mode modal** — replace the inline `TextArea` with a read-only preview + `[↗ Edit Prompt]` opening a large centered modal (mono `Consolas`, big counter). An 8000-char prompt is cramped inline.
3. **Accordion / all-seats-visible list** instead of master-detail — better for at-a-glance auditing of all 6 seats' configs.
4. **Expose the two-tier model** — a Role Defaults section + per-seat "inherited → [Override]" toggles (the data model auditors care about), instead of always materializing full per-seat overrides. (Must respect G2d-1's resolved-seat coherence: overriding `provider` must also set a valid `model`.)
5. **Live debounced validation** instead of an explicit Validate button — gated on enhancing the validate endpoint to **collect-all** errors (G2d-1 ships single-error mode) for per-field highlighting.
