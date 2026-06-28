# R0 Implementation Plan - Windows Desktop Distribution

**Status:** Completed target plan for the Velopack migration.

**Goal:** Ship a normal Windows desktop app flow: first install from GitHub Releases, then in-client check/download/restart updates.

**Non-goal:** Create a public test release just to validate transport. The first real public release is v0.2.0; the next valuable release validates GitHub transport from installed v0.2.0.

---

## Build Inputs

- Root `VERSION` remains the version source.
- `scripts/release/release-notes.md` is the only release-notes source.
- Python release venv provides PyInstaller and Velopack Python binding.
- Qt Release build plus deployment tree remains the client payload.
- Frozen observer server remains a separate runtime payload.

---

## Task 1 - Release Environment

Script:

```bash
bash scripts/release/setup-release-venv.sh
```

Expected:

- `.venv-release` contains PyInstaller and Velopack Python package.
- No release dependency is added to observer server business runtime.

---

## Task 2 - Frozen Runtime Staging

Build artifacts:

```bash
bash scripts/release/build-bootstrapper-release.sh
bash scripts/release/build-server-frozen.sh
bash scripts/release/build-qt-release.sh
```

Expected staging:

```text
.tmp/release/Werewolf-agent/Werewolf-agent.exe
.tmp/release/Werewolf-agent/_internal/
.tmp/release/app/appqt_observer.exe
.tmp/release/runtime/observer-server/observer-server.exe
```

---

## Task 3 - Velopack Packaging

Script:

```bash
bash scripts/release/build-velopack-release.sh
```

Important defaults:

- pack id: `WerewolfAgent`
- title: `Werewolf-agent`
- main executable: `Werewolf-agent.exe`
- release notes: `scripts/release/release-notes.md`
- output: `.tmp/velopack-release/Releases/`

Outputs:

```text
Werewolf-agent-Setup.exe
WerewolfAgent-<version>-full.nupkg
WerewolfAgent-<version>-delta.nupkg
releases.win.json
```

Delta packages appear after an earlier compatible package is present in the same release output.

---

## Task 4 - GitHub Upload

Script:

```bash
GITHUB_TOKEN=... PUBLISH=false bash scripts/release/upload-github-release.sh
```

Behavior:

- uploads Velopack output to the main repository GitHub Releases;
- uses stable releases only;
- keeps the release unpublished unless `PUBLISH=true`;
- applies the same `release-notes.md` as the GitHub Release body when `gh` is available.

Do not run this task during local migration validation unless owner explicitly approves release creation.

---

## Task 5 - Runtime Update Flow

Main executable:

- `Werewolf-agent.exe` calls `run_velopack_app_once()` before `release_host_main()`.
- `run_velopack_app_once()` calls `set_auto_apply_on_startup(False)` before `run()` so downloaded packages cannot bypass the active-run gate on the next launch.
- Qt client and frozen observer server never call Velopack app hooks.

Host update source:

- production factory creates `GithubSource("https://github.com/liaoszong/Werewolf-agent", access_token=None, prerelease=False)`;
- hidden local-source test hook is gated by `WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE=1`;
- the test hook is not persisted and is not visible to Qt.

Host update RPC:

- per Qt session id/token/port;
- separate from host-control;
- no provider key, GitHub token, run content, or host-control token in UI payloads or runtime-state.

Apply order:

1. download completes;
2. host checks active runs again;
3. host calls `wait_exit_then_apply_updates(update, silent=True, restart=True)`;
4. Qt exits normally;
5. owned observer server stops;
6. host exits;
7. updater replaces `current`;
8. app restarts.

---

## Task 6 - Installed Local E2E

Purpose: validate the core installed update experience without creating artificial public stable releases.

Command entry:

```bash
RUN_INSTALLED_E2E=1 bash scripts/release/smoke-test.sh
```

The smoke script calls:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass \
  -File scripts/release/run-installed-local-e2e.ps1 \
  -UpdateSource .tmp/velopack-release/Releases
```

Required result:

- installed v0.2.0 is launched from `%LOCALAPPDATA%\WerewolfAgent\current\`;
- local test source exposes v0.2.1 packages and index;
- host update RPC reports available update, target version, markdown release notes;
- download reaches `downloaded` with progress `100`;
- apply enters `applying`;
- Qt and host exit normally;
- updater restarts into v0.2.1;
- data markers under `%LOCALAPPDATA%\Werewolf-agent\`, Credential Manager, and Qt settings remain present.

---

## Task 7 - Active-Run Gate

Validation layers:

- Qt C++ invokable `applyDownloadedUpdate()` checks `hasActiveRun()` and sets `blocked_active_run`.
- Qt About UI checks before starting download-and-restart and again after download.
- Host `UpdateControlServer` checks active runs immediately before apply.
- Unit tests assert host refusal does not call backend apply.

Blocked apply must not interrupt, kill, or mutate run artifacts.

---

## Task 8 - Hygiene Scan

Run after staging and package generation:

```bash
bash scripts/release/smoke-test.sh
```

Scan scope:

- current worktree;
- release staging;
- Velopack packDir;
- unpacked full package;
- Qt UI text;
- runtime logs produced by installed E2E;
- R0 spec and plan.

Git history is intentionally excluded.

---

## Task 9 - Full Test Baseline

Run:

```powershell
$env:NO_PROXY='*'
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py"
```

Expected migration result:

- no new failure names;
- the two pre-existing failures remain the only full-suite failures;
- failure names, assertion summaries, and stack roots are recorded in the closeout report.

---

## Final Closeout Checklist

- `scripts/release/build-velopack-release.sh` is the package builder.
- `scripts/release/upload-github-release.sh` is the GitHub Release uploader.
- `scripts/release/release-notes.md` is the single notes input.
- `scripts/release/smoke-test.sh` validates Velopack staging/package hygiene.
- `scripts/release/run-installed-local-e2e.ps1` validates installed local update E2E for test builds.
- No double release chain remains in the current worktree.
- Do not publish a GitHub Release as part of the migration commit.
