# Review Packet — G2d-2 Qt Profile Setup UI

## Metadata
- **Branch:** `feat/g2d-2-qt-setup-ui`
- **Base:** `main`
- **Plan:** `docs/harness/plans/2026-06-04--g2d-2-qt-setup-ui-plan.md`
- **Spec:** `docs/superpowers/specs/2026-06-04-g2d-2-qt-setup-ui-design.md`
- **Implementation commits (this slice):**
  - `0a310cf` feat(g2d-2): add read-only GET /api/profiles/schema
  - `189a3b2` feat(g2d-2): add profile fetch/validate/launch to ObserverApiClient
  - `c5642ff` feat(g2d-2): add SeatEditorPanel.qml (per-seat provider/model/strategy/prompt)
  - `562b3c7` feat(g2d-2): profile-driven master-detail MatchSetupView with 202-gated launch
  - (+ `816a0c1` pre-existing on branch: Deterministic Mock execution banner; `0e973fe`/`fdf93de` docs)

## Changed Files (code)
| File | Status | Allowlisted |
|---|---|---|
| src/werewolf_eval/profile_config.py | M (+17) | yes |
| src/werewolf_eval/observer_server.py | M (+11) | yes |
| clients/qt_observer/src/ObserverApiClient.h | M (+30) | yes |
| clients/qt_observer/src/ObserverApiClient.cpp | M (+111) | yes |
| clients/qt_observer/qml/components/SeatEditorPanel.qml | A (+148) | yes |
| clients/qt_observer/qml/MatchSetupView.qml | M (rewrite) | yes |
| clients/qt_observer/CMakeLists.txt | M (+1) | yes |
| clients/qt_observer/README.md | M (+1/-1) | yes |
| tests/test_profile_config.py | M (+20) | yes |
| tests/test_observer_server.py | M (+6) | yes |
| tests/test_qt_observer_static_contract.py | M (+57) | yes |

Docs already on branch (allowlisted): the plan + spec under `docs/`.

## Diff Stat (`git diff --stat main...HEAD -- src clients tests`)
```
 clients/qt_observer/CMakeLists.txt                     |   1 +
 clients/qt_observer/README.md                          |   2 +-
 clients/qt_observer/qml/MatchSetupView.qml             | 312 +++++++++--------
 clients/qt_observer/qml/components/SeatEditorPanel.qml | 148 ++++++++
 clients/qt_observer/src/ObserverApiClient.cpp          | 111 ++++++
 clients/qt_observer/src/ObserverApiClient.h            |  30 ++
 src/werewolf_eval/observer_server.py                   |  11 +-
 src/werewolf_eval/profile_config.py                    |  17 ++
 tests/test_observer_server.py                          |   6 +
 tests/test_profile_config.py                           |  20 ++
 tests/test_qt_observer_static_contract.py              |  57 +++-
 11 files changed, 595 insertions(+), 120 deletions(-)
```

## Diff Check
- `git diff --check main...HEAD` → no whitespace/conflict errors.
- All changed paths within the plan Allowlist; no forbidden-scope files (no AGENTS.md, ROADMAP/TASKS, root README, adr/, .github/, generated fixtures).

## Allowlist Conformance
All 11 code files + 2 docs match the plan Allowlist. No new server **write** endpoint (only read-only `/api/profiles/schema`). No client local file I/O, no live providers, no new third-party deps, no engine/route-product-doc changes.

## Forbidden / Secret Scan
- **Real-forbidden scan** (HTTP client libs as imports/usage, `QFile`/`QDir`/`file://`, `sk-…` secrets, `Authorization:`/`Bearer …`) over added lines → **CLEAN** (0 hits).
- Broad substring scan flagged **1 benign match**: the test method name `test_profile_requests_use_latest_wins_guards` contains the English substring "requests" (NOT the `requests` HTTP library). No actual library import or usage.
- Static-contract `QtObserverSecretBoundaryTests` / `QtObserverBoundaryTests` pass over all new `.cpp/.h/.qml` (no `api_key`, `sk-`, `events.jsonl`, `snapshots/`, `QProcess`, `file://`).

## Test Summary
| Check | Result |
|---|---|
| `tests.test_profile_config` (incl. `ProfileSchemaTests.test_schema_shape`) | **OK** (23) |
| `tests.test_observer_protocol` | **OK** (focused run with profile_config: 71 OK) |
| `tests.test_qt_observer_static_contract` (new profile-client + setup + objectNames + README tests) | **OK** (36) |
| Qt build (F: toolchain) `--target appqt_observer` | **exit 0** — qmlcachegen AOT-compiled all QML incl. SeatEditorPanel + rewritten MatchSetupView |
| `ctest --test-dir .tmp/qt-observer-build` | **100%** (1/1 observer_sse_parser) |
| `qmllint` MatchSetupView + SeatEditorPanel | **exit 0**, 0 `Error:` lines (only `[unqualified]`/`[missing-property]` on C++-registered `ObserverClient`/`Theme` singletons — expected, same as existing views) |
| Full suite `unittest discover` | 431 tests; **47 errors + 1 failure**, all accounted for (below) |
| `compileall src tests` | **exit 0** |
| Visual `.tmp/g2d2_setup.png` | seeded master-detail render confirmed (seat grid + seat editor + banner + disabled Launch); temp harness edits reverted; tree clean |

**Accounted failures (not regressions):**
- 47 errors are **all** `test_observer_server.*` failing with `RemoteDisconnected` / `ConnectionResetError` — the documented localhost-HTTP env block (server starts but loopback connect is severed). Includes the newly-authored `ObserverServerProfileTests.test_schema_endpoint` (env-blocked like its siblings).
- 1 failure: `test_context_budget.ContextBudgetGateDocsTests.test_agents_documents_context_budget_gate` — pre-existing on `main` (asserts a string in `AGENTS.md`, which is untouched and out of allowlist).
- Confirmed: **0** non-`test_observer_server` errors and **0** non-`test_context_budget` failures.

## Key Hunks
1. **`GET /api/profiles/schema` (read-only)** — `profile_config.build_profile_schema()` derives providers/models/strategies/roles/role_teams/seat_roles/seat_ids/prompt_max_len from validation constants (sorted, no `templates`, no secrets/paths). `observer_server.do_GET` adds the 3-segment exact-match route **before** the list/name branches and guards the name branch with `segments[2] != "schema"`.
2. **`ObserverApiClient` profile methods** — `profileItems/profileSchema/loadedProfile/profileValidation` properties; `refreshProfiles/refreshProfileSchema/fetchProfile/validateProfile/launchFromProfile` invokables; `launchSucceeded/launchFailed` signals. `fetchProfile` + `validateProfile` use independent latest-wins serials (`m_profileRequestSerial`/`m_profileValidateSerial`). `launchFromProfile` advances **only** on HTTP `202` + non-empty `run_id` (via `HttpStatusCodeAttribute`); network-error and non-202 paths emit `launchFailed` and surface `{message}`.
3. **`SeatEditorPanel.qml`** — provider/model(provider-dependent)/strategy dropdowns + prompt TextArea with live `len / prompt_max` counter; typed `signal edited(string field, string value)`; `_ready` guard. Lays content out with explicit inset margins (AppCard is a plain Rectangle with no `padding` property — see Deviations).
4. **`MatchSetupView.qml`** — profile-driven master (RoleCard grid bound to `seatIds`/`effective()`) + detail (SeatEditorPanel); dropdown options come from `profileSchema`; `Validate` pins `_validatedRevision = profileRevision`; `Launch` `enabled` only when validation passed for the current revision; navigation to Preflight happens **only** in `onLaunchSucceeded`. Global `setupExecutionBanner` (low-opacity `Theme.color.warning`) states Deterministic-Mock once.

## Deviations from Plan (intentional, verified — surfaced by a pre-implementation context-verification pass)
- **AppCard has no `padding` property** (it is a `Rectangle`, not a Control). The plan's `padding: Theme.space.lg` on SeatEditorPanel's root would fail qmlcachegen AOT. Replaced with an inset content `Column` (`x/y = Theme.space.lg`, `width = parent.width - 2*lg`). Verified by build + visual capture. AppCard.qml is out of allowlist, so it was not modified.
- **Typed signal** `edited(string field, string value)` instead of the plan's untyped `edited(field, value)` (no existing QML uses parameterized untyped signals; typed is AOT-safe). All emitted values are strings.
- **Contract assertion** `assertIn("onLaunchSucceeded", …)` instead of `assertIn("launchSucceeded", …)`: idiomatic QML only ever contains the handler name `onLaunchSucceeded` (the lowercase signal name cannot appear in valid QML), and the handler is exactly what proves 202-gated (non-optimistic) navigation.
- **SeatEditorPanel counter row** uses an anchored `Item` (label left / counter right) instead of the plan's `Row`+spacer (whose `parent.width - 2*implicitWidth` math collapsed to full width). Renders correctly in the capture.

## Evidence Map
- **A1** schema endpoint shape (no templates/secrets/paths) → `ProfileSchemaTests.test_schema_shape` OK; `test_schema_endpoint` authored (env-blocked).
- **A2** client properties/invokables/signals + latest-wins + 202 gate → `QtObserverProfileClientTests` (3 tests) OK; Qt build exit 0.
- **A3** SeatEditorPanel edits + CMake registration + objectNames → static contract OK; build AOT-compiles `SeatEditorPanel_qml`.
- **A4** profile-driven master-detail, options from schema, no static role array, revision-bound Launch → `test_setup_is_profile_driven` OK; visual capture.
- **A5** 202-gated navigation via `onLaunchSucceeded`; failure stays + error → cpp `launchFromProfile` 202 gate; QML `onLaunchSucceeded`; `test_client_launch_is_202_gated`.
- **A6** static contract green, README non-goal updated, forbidden patterns absent, build exit 0, ctest green, qmllint clean → all above.
- **A7** visual capture renders master-detail per design system → `.tmp/g2d2_setup.png` (seat grid + editor + counter + banner + disabled Launch).
- **A8** no save endpoint / no client file I/O / no live providers / no new deps / no engine or route-doc changes → allowlist + forbidden scan.
- **A9** global Deterministic-Mock banner (`setupExecutionBanner`, low-opacity warning), no per-seat spam → `test_setup_is_profile_driven` asserts "Deterministic Mock"; visual.

## Acceptance Checklist
- [x] A1 read-only schema endpoint
- [x] A2 client profile methods (latest-wins, 202 gate)
- [x] A3 SeatEditorPanel registered + objectNames
- [x] A4 profile-driven master-detail
- [x] A5 202-gated launch → Preflight
- [x] A6 contract/build/ctest/qmllint green
- [x] A7 visual capture
- [x] A8 scope boundaries held
- [x] A9 execution banner

## Review Trigger Result
- Visual harness edits (`AppShell.qml` + temp seed in `MatchSetupView.qml`) used for `.tmp/g2d2_setup.png` were **fully reverted**; `git status` clean; `git diff --quiet` on both files passes; no `TEMP VISUAL ONLY` markers remain; `AppShell.qml` never staged/committed.
- Suggested reviewer focus: server route ordering (`/api/profiles/schema` vs name branch); client 202 gate + dual latest-wins serials; QML reactivity of `effective()`/`profileRevision` Validate→Launch gating.
