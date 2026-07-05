# Project Memory

Purpose: this is the cross-session truth entry for Werewolf-agent. Future
agents should read it after `AGENTS.md` when starting or resuming non-trivial
work, then follow the canonical docs/code it points to.

This file keeps durable, human-readable facts, not secrets, logs, or large
transcripts. It does not replace route authorities such as
`docs/PROJECT_MAP.md`; it records what changed, why it matters, and where to
verify current state.

## Update Rule

Update this file after important tasks, especially when any of these happen:

- a phase/task is completed or materially re-scoped;
- a release, APK, installer, or public artifact is built;
- protocol or UI boundary decisions are settled;
- large local cleanup changes where future agents need to know what was kept;
- follow-up work is intentionally deferred.

Each entry should include:

- date;
- concise outcome;
- important commits or artifact paths;
- verification evidence;
- remaining caveats or follow-ups.

Do not store provider keys, join tokens, bearer tokens, private logs, or local
machine secrets here.

## Entries

### 2026-07-05 - P3-A-2b RolePolicy Asset Registry

- Completed P3-A-2b as a backend asset-registry slice with no runtime
  consumption.
- Scope delivered:
  - Added `src/werewolf_eval/role_policy_registry.py`.
  - Added built-in `standard_six_player_balanced` RolePolicyPack covering
    Werewolf, Seer, Witch, Villager, Guard, and Hunter.
  - Added draft creation, publish, referenced-policy version bumping, and JSON
    save/load helpers.
  - Publishing a draft now creates a fresh version when the base policy ref is
    shared by another pack, so local pack edits do not mutate sibling packs.
  - Publishing a draft never mutates an existing `policy_id@version` with new
    content; same-ref edits branch to a fresh patch version before updating the
    pack ref.
  - Stale drafts are rejected whenever the current pack ref has moved away from
    the draft base ref, even if the current ref is externally referenced.
  - Strategy sub-blocks are registry-allowlisted so RolePolicy cannot smuggle
    runtime/team state refs, engine entitlement, action windows, or permission
    fields through `ability_use_policy`, `claim_policy`, `deception_policy`, or
    `team_policy`.
  - Strategy list fields are registry-checked as `list[str]` to prevent
    structured authority payloads inside otherwise allowed RolePolicy fields.
  - `RolePolicy.applicability` is registry-allowlisted and type-checked so it
    cannot carry engine entitlement, action windows, runtime state refs, or
    team-state permission fields.
  - Registry rejects RolePolicy payloads that try to persist
    `seat_character_card_ref`, provider/execution/runtime refs, team plans,
    extra-call budgets, visibility entitlement, or legal action windows.
  - Registry rejects secret-like keys/values and delegates policy schema checks
    through `validate_role_policy()`.
- Verification:
  - `$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_role_policy_registry tests.test_agent_assets -v` passed 24 tests.
  - `$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest discover -s tests -p "test_*.py"` passed 1455 tests, skipped 2.
- Boundary: no runtime, provider, prompt byte, observer/participant protocol,
  validator, generated fixture, Flutter UI, or workflow behavior was changed.
  P3-A-2c remains the first runtime-consumption slice and must follow prompt
  byte/version rules if model-visible text changes.

### 2026-07-05 - P3-A-2a Flutter Local RolePolicy Draft Editor

- Completed P3-A-2a as a Flutter-only local draft UI slice.
- Scope delivered:
  - Replaced the mobile Roles page documentation list with a RolePolicyPack
    scoped role strategy entry page.
  - Added a two-column role policy grid for Werewolf, Seer, Witch, Villager,
    Guard, and Hunter.
  - Added full-screen role detail pages with read-only role boundary, strategy
    overview, decision tendencies, role-specific action strategy,
    evidence/context preferences, and runtime composition preview.
  - Added local-only preset and setting draft state with "local draft" /
    "draft not saved" wording.
  - Removed the old prompt/harness/memory documentation sheet from the mobile
    role path; the UI does not expose raw prompt editing.
- Verification:
  - `flutter test test/widget/home_shell_test.dart` passed 8 tests.
  - `flutter analyze` passed with no issues.
  - `flutter test` passed 65 tests.
- Boundary: no backend persistence, observer/participant protocol, runtime,
  provider, prompt byte, validator, generated fixture, or workflow behavior was
  changed. Real save/version/frozen/reference semantics remain P3-A-2b.

### 2026-07-05 - P3-A-1 Agent Asset Ownership Schema Bridge

- Completed P3-A-1 as a schema-first, runtime-neutral bridge.
- Scope delivered:
  - Added `src/werewolf_eval/agent_assets.py` with pure validators for
    `SeatCharacterCard`, `RolePolicy`, `RuntimeSeatState`,
    `RuntimeTeamState`, `ProviderProfile`, `ExecutionContract`, and
    `AgentPreset`.
  - Added legacy profile projection into audience-scoped artifacts:
    `PublicRunManifest`, `SeatPrivateAssetSnapshot`,
    `FactionPrivateAssetSnapshot`, and `PostgameAuditAssetSnapshot`.
  - Public manifest intentionally excludes true roles, teams, RolePolicy refs,
    runtime state refs, faction refs, and role words for hidden seats.
  - Human seats do not receive provider profile refs for player model calls.
  - `seat_overrides[seat].prompt` is represented as `LegacyPromptOverlay`, not
    silently migrated into RolePolicy.
  - Added RuntimeTeamState authorization helper for faction-private state.
- Route/docs updated:
  - `docs/PROJECT_MAP.md` reconciles P3-A numbering: P3-A-2 is now Mobile
    RolePolicy editor; Agent memory packet moved to P3-A-3.
  - `docs/TASKS.md` records P3-A-1 completed outputs.
- Verification:
  - `$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_agent_assets tests.test_profile_config -v` passed 84 tests.
- Boundary: no runtime, provider, prompt, validator, generated fixture, client,
  or workflow behavior was changed.

### 2026-07-05 - P3-E-3 Human Seat Client Slice Closeout

- Completed P3-E-3 as a Flutter-only human-seat client hardening slice.
- Scope delivered:
  - `SessionController` now refreshes participant state for P3-C state-changing
    SSE events: `participant_projection_updated`, `action_accepted`,
    `action_rejected`, `action_window_timed_out`, plus existing window/status
    events.
  - `action_rejected` SSE and submit rejections preserve the server message for
    user feedback; submit `missing_or_invalid_session` moves the room into
    `sessionExpired`.
  - `response` action windows are treated as text input and submit
    `action_type=response`; `speech` and `final_words` behavior is preserved.
  - Live room no longer exposes a stale local action window while reconnecting,
    failed, or session-expired; it waits for server state before allowing new
    submissions.
  - Candidate targets remain Flutter-only visible/alive candidates derived from
    `projection.players`; no `target_options` / `legal_targets` protocol fields
    were added.
- Verification:
  - `flutter analyze` passed.
  - `flutter test` passed 65 tests.
  - `flutter build apk --debug --flavor internal` built
    `clients/flutter_app/build/app/outputs/flutter-apk/app-internal-debug.apk`.
  - `$env:NO_PROXY='*'; $env:PYTHONPATH='src'; python -m unittest tests.test_participant_protocol tests.test_participant_routes tests.test_participant_game_loop tests.test_observer_routes -v` passed 39 tests.
- Boundary: no backend protocol, runtime, provider, validator, generated
  fixture, or workflow behavior was changed.

### 2026-07-05 - P3-E-2 Mobile-first Live Room Closeout

- Completed P3-E-2 as a Flutter-only mobile live-room slice.
- Scope delivered:
  - Mobile Home-owned match flow, consistent floating back affordance, day/night
    appearance styles, role library shell, history grouping shell, Settings
    provider/update/server controls.
  - Real participant projection parsing for `game_event_emitted`,
    `data.summary`, projected players/proof/snapshots, event-derived phase and
    round, and visible alive candidate seats.
  - Live room information structure: centered status island, connection dot,
    phase/private/seat panels, role-safe speech feed, and in-room identity
    reminder dialog with visible werewolf teammates derived only from
    `projection.players`.
  - Composer Rail supports multiple structured actions, visible candidate
    target selection, pass, deadline/default-timeout display, submitting state,
    and server rejection feedback.
- Removed the separate Flutter identity-confirm page from the current flow;
  `ConnectScreen` and Home match join now go straight to `LiveRoomScreen`, where
  the role reminder appears after participant state arrives.
- Android Studio / Flutter run note: use `--flavor internal`; running without a
  flavor can produce flavored APKs while Flutter looks for `app-debug.apk`.
- Verification:
  - `flutter analyze` passed.
  - `flutter test` passed 58 tests.
  - `flutter build apk --debug --flavor internal` built
    `clients/flutter_app/build/app/outputs/flutter-apk/app-internal-debug.apk`.
- Boundary: no backend protocol, runtime, provider, validator, generated
  fixture, or workflow behavior was changed.

### 2026-07-05 - CI Stability + Live Room Usability Slice

- Fixed the ordinary GitHub `tests.yml` red workflow on `main`:
  - Removed the unintended `pytest` import dependency from unittest-discovered
    test modules.
  - Restored the root `AGENTS.md` Context Budget Gate text expected by the
    context-budget guard.
  - Updated the settlement cache-hit test to include the current
    `evaluation_bucket` validity requirement.
- Pushed commit `74461c8` and verified GitHub run `28727974868` was fully green:
  `unittest`, `windows-gate`, and `flutter-client` all passed.
- Continued P3-E-2 live room usability:
  - `RoleSafeStatusBar` now shows phase, round, seat perspective, and connection
    state with a stronger waiting-for-you state.
  - `SpeechFeed` now separates system timeline events from speech bubbles,
    highlights the current human seat, and has a role-safe empty state.
  - `ComposerRail` structured action windows now use a floating action panel with
    phase/round/required chips and clearer target selection.
- Verification:
  - `flutter analyze` passed.
  - `flutter test` passed 48 tests.
  - Focused Flutter UI tests for speech feed, composer rail, and live room passed
    10 tests.
  - `$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest discover -s tests -p "test_*.py"` passed 1431 tests, skipped 2.
- Pushed commit `33e4061` to `main`; GitHub `tests.yml` run `28728197715`
  passed.
- Published Android Internal release `v0.2.1-internal.5+215`:
  - Workflow run:
    `https://github.com/liaoszong/Werewolf-agent/actions/runs/28728233220`
  - Release:
    `https://github.com/liaoszong/Werewolf-agent/releases/tag/v0.2.1-internal.5%2B215`
  - Manifest:
    `https://liaoszong.github.io/Werewolf-agent/updates/internal.json`
  - Signed APK asset: `werewolf-agent-internal-arm64.apk`
  - Size: `19386642`
  - SHA256:
    `44800db2665e3d0c1c7c12cf14857a60d4b280b5942f2d5f69e21334563f9853`
- Boundary: no protocol, runtime, provider, validator, generated fixture, or
  backend route behavior was changed.

### 2026-07-05 - Flutter Mobile Navigation + Appearance Shell

- Reworked the Flutter home shell so the bottom navigation is top-level only:
  Home, Roles, History, Settings. Match picking and live room entry are now a
  Home-owned flow, not duplicate bottom tabs.
- Replaced Material `NavigationBar` with a custom floating rounded tab bar to
  avoid the default blue ripple/indicator animation. Match picker and live room
  flows hide bottom navigation and use an iOS-style floating back button.
- Added two appearance styles: Night (Werewolf-themed dark palette) and Day
  (Claude-like warm light palette). Home now has a compact day/night toggle in
  the upper-right; language switching remains in Settings only.
- Added a mobile role library with role cards for Werewolf, Seer, Witch,
  Hunter, Villager, and Guard. Role detail sheets expose agent harness, memory,
  prompt, and editable/locked scope. This is a read-only UI slice and does not
  change prompt protocol or backend role policy.
- Added a History page shell that groups observer runs by running/completed/
  interrupted/failed status. Detailed completed/running/interrupted replay UX
  remains a later discussion.
- Kept Settings connection/update controls and added a Providers section that
  explicitly marks BYO-key/base URL/model migration as pending. The mobile app
  still does not store provider secrets.
- Tightened the live-room composer into a ChatGPT/Claude-like rounded input bar
  with larger vertically centered text and compact icon buttons.
- Verification:
  - `flutter test test/widget/home_shell_test.dart test/ui/composer_rail_test.dart` passed 14 tests.
  - `flutter analyze` passed.
  - `flutter test` passed 47 tests.
  - `git diff --check` had only checkout CRLF warnings and no whitespace errors.
- Local APK artifact built:
  - `clients/flutter_app/build/app/outputs/flutter-apk/app-internal-release.apk`
  - version: `0.2.1-internal.4+214`
  - size: `19056082`
  - SHA256:
    `7a807da7fead347091c497033f7afad9105bd161f531a03eb9cc485757590177`
- Published Android Internal release `v0.2.1-internal.4+214` from GitHub
  Actions using the internal signing secret:
  - Workflow run:
    `https://github.com/liaoszong/Werewolf-agent/actions/runs/28727243033`
  - Release:
    `https://github.com/liaoszong/Werewolf-agent/releases/tag/v0.2.1-internal.4%2B214`
  - Manifest:
    `https://liaoszong.github.io/Werewolf-agent/updates/internal.json`
  - Signed APK asset: `werewolf-agent-internal-arm64.apk`
  - Size: `19319730`
  - SHA256:
    `93ff694a8644980f0adc297131e9147ae655767463017cd3766500e36c7941ff`

### 2026-07-04 - Public Observer Endpoint + Flutter Server Preset

- Bound `api.paleink.cc` to Tencent Cloud server `43.159.168.39` and verified
  public health over `http://api.paleink.cc:8765/health`.
- Added Docker deployment files for the observer server:
  - `Dockerfile`
  - `.dockerignore`
  - `deploy/docker-compose.yml`
  - `deploy/README.md`
- Docker deploy contract: expose TCP `8765`, persist runs in Docker volume
  `werewolf_runs:/data/runs`, and start
  `werewolf_eval.run_observer_server --host 0.0.0.0 --port 8765 --runs-dir /data/runs --allow-live-api`.
- Flutter app now defaults to `http://api.paleink.cc:8765` and the Settings
  page exposes quick presets for PaleInk Cloud and Local Dev. This keeps the
  observer/participant protocol boundary unchanged.
- Updated docs:
  - `README.md`
  - `README.zh-CN.md`
  - `clients/flutter_app/README.md`
  - `docs/release/android-update-channels.md`
  - `docs/PROJECT_MAP.md`
  - `docs/TASKS.md`
- Added regression coverage:
  - `clients/flutter_app/test/widget/home_shell_test.dart` covers the server
    preset UI.
  - `tests/test_deploy_contract.py` covers Dockerfile/compose/deploy README
    static contract.
- Verification:
  - `flutter analyze` passed.
  - `flutter test` passed 43 tests.
  - `$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_deploy_contract -v` passed 3 tests.
  - `git diff --check` passed.
  - Public health checks for both `api.paleink.cc:8765` and `43.159.168.39:8765`
    returned `{"service":"werewolf-observer","status":"ok"}`.
  - Local Docker build was not run because Docker CLI is not installed on the
    Windows workstation.
- Pushed commit `fa81c8c` to `main` and published Android Internal release
  `v0.2.1-internal.2+212`:
  - Workflow run:
    `https://github.com/liaoszong/Werewolf-agent/actions/runs/28709022366`
  - Release:
    `https://github.com/liaoszong/Werewolf-agent/releases/tag/v0.2.1-internal.2%2B212`
  - Manifest:
    `https://liaoszong.github.io/Werewolf-agent/updates/internal.json`
  - APK: `werewolf-agent-internal-arm64.apk`
  - Size: `19187346`
  - SHA256:
    `d38443d97caac3eeb1cf64bb28fc6d1aafb55c722579fd7205663ea948b61aa9`
- Post-push CI for commit `fa81c8c`: `flutter-client` and `windows-gate`
  passed; `unittest` failed with the existing missing-`pytest` import errors
  in CI plus the two local historical failures
  (`ContextBudgetGateDocsTests` and settlement cache).
- APK artifact built with `flutter build apk`:
  - `clients/flutter_app/build/app/outputs/flutter-apk/app-release.apk`
  - size at build time: 48,346,266 bytes
- Caveat: the Tencent server is currently running the earlier one-off Docker
  container. To migrate it to the repo compose deploy, pull these changes on
  the server and run `sudo docker compose up -d --build` from `deploy/`.

### 2026-07-04 - Flutter Android Remote Update Channels

- Added BatteryCtrl-style lightweight Android remote update support to the
  Flutter client.
- Landed Flutter baseline commit `d98fbea` first, then update-channel commit
  `2b3f9fd` on `main`.
- Channels:
  - Internal: `io.werewolfagent.werewolf_app.internal`,
    `updates/internal.json`, prerelease workflow.
  - Production: `io.werewolfagent.werewolf_app`,
    `updates/stable.json`, candidate + promote workflow.
- Update client behavior: checks schema v1 manifest, validates matching
  `build-metadata.json`, downloads APK, checks size and SHA256, inspects APK
  package/version/signing certificate via Android MethodChannel, then opens the
  Android system installer. It does not do silent install or hot update.
- Added Android flavor/signing split, FileProvider cache root
  `werewolf_updates/`, and Settings-page update controls.
- Added workflows:
  - `.github/workflows/build-android-internal.yml`
  - `.github/workflows/build-android-production-candidate.yml`
  - `.github/workflows/promote-android-production.yml`
- Added release operation doc:
  `docs/release/android-update-channels.md`.
- Verification:
  - `flutter analyze`
  - `flutter test` passing 42 tests
  - `flutter build apk --debug --flavor internal --target-platform android-arm64`
  - `flutter build apk --debug --flavor production --target-platform android-arm64`
  - `flutter build apk --release --flavor internal --target-platform android-arm64 ...`
  - `.github/scripts/android-update/common.ps1` artifact generation smoke
    passed when `ANDROID_HOME` / `ANDROID_SDK_ROOT` pointed at `G:\Android\Sdk`.
- GitHub publication completed:
  - GitHub Pages enabled from `gh-pages` branch root:
    `https://liaoszong.github.io/Werewolf-agent/`.
  - Internal run `28708039101` published prerelease
    `v0.2.1-internal.1+211`; `updates/internal.json` returned 200 and points
    at `werewolf-agent-internal-arm64.apk`, size `19187346`, SHA256
    `eadd9c1f414be42d78e7b691b7f5eb19a778d99132e3dcc555dd86a061a3131a`.
  - Production candidate run `28708187657` published prerelease
    `v0.2.1+211`; promote run `28708345316` reused the candidate manifest,
    wrote `updates/stable.json`, and marked the release latest/non-prerelease.
  - `updates/stable.json` returned 200 and points at
    `werewolf-agent-production-arm64.apk`, size `19187330`, SHA256
    `f6b420d4013a1effb8c6ab6796e927e520bcd2a88d334dec26637ddb7abce9dc`.
- Android signing secrets were configured in GitHub Actions. A local backup of
  generated signing material exists outside the repo under
  `G:\Werewolf-agent-signing\android\20260704-214032`; do not commit or print
  secret contents.
- Caveat: full Python unittest still had two unrelated historical failures
  after this work (`ContextBudgetGateDocsTests` root docs expectation and a
  settlement cache test). Flutter analyze/tests/builds and all Android release
  workflows passed.
- Post-push CI for docs commit `53cb365` matched the prior `2b3f9fd` tests run:
  `flutter-client` and `windows-gate` passed; `unittest` stayed red with
  three missing-`pytest` import errors plus the two historical failures above.

### 2026-07-04 - P3-E-1 Flutter Human Seat Client

- Completed and merged P3-E-1 on `main` at `70d8ba3`.
- Added Flutter client under `clients/flutter_app/`.
- Scope: profile-bound single human seat join, identity confirmation,
  participant REST/SSE DTO/client, role-safe live room, semantic speech
  highlighting, collapsible bottom Composer Rail, speech/final_words,
  pass, vote, and role-target structured actions.
- Boundary: client uses observer/participant REST+SSE only; it does not read
  local run artifacts, request god projection, call model providers, or handle
  provider keys.
- Verification:
  - `flutter analyze`
  - `flutter test` passing 20 tests after pass-action regression coverage
  - `$env:NO_PROXY='*'; $env:PYTHONPATH='src'; python -m unittest tests.test_participant_protocol tests.test_participant_routes tests.test_participant_game_loop tests.test_observer_routes -v` passing 39 tests
  - 393x852 portrait visual check for live room and Composer Rail
- APK artifact built with `flutter build apk`:
  - `clients/flutter_app/build/app/outputs/flutter-apk/app-release.apk`
  - size at build time: 47,918,450 bytes
- Keep the APK before running `flutter clean`; `flutter clean` removes the
  `clients/flutter_app/build/` output tree.

### 2026-07-04 - Local Cleanup After APK Build

- Cleared repository-local `.tmp/` contents.
- Removed clean, merged worktrees:
  - `.worktrees/active-runs-navigation-lifecycle`
  - `.worktrees/p2b-config-save-import-export`
  - `.worktrees/ui-tech-debt-burn-down`
  - `.worktrees/p3c0b-route-skeleton`
  - `.worktrees/p3c1-human-villager-seat`
  - `.worktrees/p3e-flutter-human-seat-client`
- Kept `.worktrees/active-runs-live-follow-fix` because it had uncommitted
  changes.
- The `p3e-flutter-human-seat-client` worktree record was removed; a locked
  empty directory shell may remain under `.worktrees/` until the process holding
  it exits. It contains no file payload.
- APK was intentionally preserved.
