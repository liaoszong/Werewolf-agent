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
