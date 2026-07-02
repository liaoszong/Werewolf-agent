# R0 Windows Distribution Baseline

**Status:** Completed implementation target after Velopack local installed E2E.

**Owner decision:** Werewolf-agent ships as a normal Windows desktop client. The public first-install and update source is the main repository's GitHub Releases. Updates are discovered, downloaded, and applied from inside the Qt client.

---

## Product Behavior

1. A Windows user downloads one versioned setup executable such as `Werewolf-agent-0.2.0-Setup.exe` from the main repository GitHub Releases page.
2. Setup installs the app under `%LOCALAPPDATA%\WerewolfAgent\current\`.
3. The user launches Werewolf-agent from the desktop or Start menu.
4. Later, Settings -> About & Updates checks for a new stable release.
5. The Qt UI shows target version, release notes, download progress, and readable failure state.
6. If any run is `queued` or `running`, apply/restart is blocked without interrupting the run.
7. If there is no active run, the user clicks Download and Restart.
8. The release host calls the background updater before it exits, Qt closes normally, the owned observer server shuts down, the app tree is replaced, and the app restarts into the new version.

No separate maintenance UI, component selection, repository page, or second installer wizard is part of the product experience.

---

## Directory Contract

Program files:

```text
%LOCALAPPDATA%\WerewolfAgent\current\
```

User data:

```text
%LOCALAPPDATA%\Werewolf-agent\
  runs\
  profiles\
  configs\
  logs\
  runtime-state\
```

`runs`, `profiles`, `configs`, `logs`, and `runtime-state` never live under the replaceable `current` app directory.

Credential Manager entries and Qt settings are outside the replaceable app tree and must survive app updates.

---

## Version Contract

`VERSION` remains the single source for the application version. Release scripts copy it into:

- PyInstaller bootstrapper onedir staging.
- Frozen observer server staging.
- Velopack packDir.
- Velopack package metadata.
- Runtime `--version` output.

The release manifest/app version fields are derived from the same value.

---

## Runtime Architecture

### Main executable

`Werewolf-agent.exe` is the only Velopack main executable.

Startup order:

1. `werewolf_eval.release_host.__main__` runs first.
2. It calls `velopack.App().set_auto_apply_on_startup(False).run()` exactly once through `run_velopack_app_once()`.
3. Only after that returns does it enter `release_host_main()`.

The Qt client and frozen observer server never call `velopack.App().run()`.

Startup auto-apply is disabled deliberately: a downloaded package must not be
applied on the next launch unless the host update RPC has passed the active-run
gate and explicitly called `wait_exit_then_apply_updates(...)`.

### Process ownership

The release host owns:

- single-instance host control;
- dynamic loopback observer server startup;
- owned server shutdown;
- update source selection;
- update check/download/apply;
- short-lived update control endpoint.

The Qt client owns:

- Settings -> About & Updates presentation;
- display of version, release notes, progress, and failure state;
- client-side active-run apply gate;
- sending minimal update RPC calls to the host.

The observer server owns game/runtime APIs. It does not gain new business runtime dependencies for release infrastructure.

---

## Update Source

Production source is stable-only:

```python
GithubSource("https://github.com/liaoszong/Werewolf-agent", access_token=None, prerelease=False)
```

There is one source factory. The update control server receives an already-selected factory and does not branch on provider type.

A hidden developer test hook can point the host to a local update directory for installed E2E. It is disabled unless an explicit release-test environment flag is set, is never persisted, and is not exposed in Qt UI, QSettings, runtime-state, release notes, or user documentation.

GitHub Releases transport is intentionally deferred until a real future value release after v0.2.0. The absence of a public v0.2.1 during R0 is not a blocker for the core installed update experience.

---

## Host Update RPC

The release host starts a per-Qt-session update control endpoint and passes:

- update session id;
- update session token;
- update control port.

The token is separate from single-instance host control. No GitHub token, provider key, run content, host-control token, or source configuration is sent to Qt, logs, runtime-state, or UI payloads.

Endpoints:

- `check_for_update`
- `get_update_status`
- `download_update`
- `apply_downloaded_update`

Allowed behavior:

- `check_for_update`: allowed even when active runs exist.
- `download_update`: allowed in R0; never auto-applies.
- `apply_downloaded_update`: blocked by Qt and host if any run is `queued` or `running`.

Blocked apply never interrupts, kills, or edits run artifacts.

---

## Apply Sequence

Correct Download and Restart sequence:

1. Host completes download.
2. Host again confirms no `queued` or `running` run exists.
3. Host calls `wait_exit_then_apply_updates(update, silent=True, restart=True)` while still alive.
4. Qt client exits normally.
5. Host gracefully stops the owned observer server.
6. Host exits.
7. Background updater replaces `current`.
8. Main executable restarts into the target version.

The host must not defer the apply call until after it has already exited.

---

## Release Notes

`scripts/release/release-notes.md` is the single release-notes input.

It feeds:

- `vpk pack --releaseNotes`;
- future GitHub Release body creation.

Qt consumes only markdown notes returned by the Python binding and displays them as plain text or a restricted Markdown subset. The client must not render arbitrary rich HTML from update metadata.

---

## Packaging Outputs

Release staging keeps the existing build topology:

```text
.tmp/release/
  Werewolf-agent/
    Werewolf-agent.exe
    _internal/
    VERSION
  app/
    appqt_observer.exe
    Qt runtime deployment
  runtime/
    observer-server/
      observer-server.exe
      _internal/
      VERSION
```

Velopack packDir:

```text
.tmp/velopack-release/packdir-<version>/
  Werewolf-agent.exe
  _internal/
  app/
  runtime/observer-server/
  VERSION
```

Velopack output:

```text
.tmp/velopack-release/Releases/
  Werewolf-agent-<version>-Setup.exe
  WerewolfAgent-<version>-full.nupkg
  WerewolfAgent-<version>-delta.nupkg   # after a prior package exists
  releases.win.json
```

---

## Acceptance

R0 acceptance requires:

- clean Windows user environment without Python or Qt can install from `Werewolf-agent-<version>-Setup.exe`;
- installed app files are under `%LOCALAPPDATA%\WerewolfAgent\current\`;
- user data remains under `%LOCALAPPDATA%\Werewolf-agent\`;
- installed v0.2.0 can discover a test-only local v0.2.1 source, show target version and release notes, download, apply, and restart into v0.2.1;
- active-run apply is blocked by both Qt and host;
- completed/interrupted runs, profiles, configs, Credential Manager, and Qt settings survive update;
- release staging, packDir, unpacked full package, UI text, app logs, this spec, and the implementation plan contain no superseded release-chain tokens;
- full unittest failure set is unchanged from the pre-migration baseline.

Git history is out of scope for residual-token scanning.

---

## Current Evidence

The first Velopack installed E2E passed with:

- installed v0.2.0;
- test-only local update source for v0.2.1;
- real `UpdateInfo` field mapping for target version and markdown notes;
- download progress surfaced through host update RPC;
- apply/restart into v0.2.1;
- data preservation across update.

The remaining GitHub Releases transport proof will happen naturally when a real post-v0.2.0 release exists.
