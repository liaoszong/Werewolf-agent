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
