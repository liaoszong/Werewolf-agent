# Flutter Human Seat Client

Mobile-first Flutter client for P3-E human-seat participation.

## Scope

- Connects to the existing Python observer server.
- Joins/resumes one profile-bound human seat.
- Renders participant state only, including role-safe visible events and the
  server-owned open action window.
- Submits actions through server-owned action windows.
- Does not read local run artifacts, request god projection, call model
  providers, or handle provider keys.

## Local Verification

From this directory:

```powershell
flutter analyze
flutter test
```

Focused backend participant regression from repository root:

```powershell
$env:NO_PROXY='*'
$env:PYTHONPATH='src'
python -m unittest tests.test_participant_protocol tests.test_participant_routes tests.test_participant_game_loop tests.test_observer_routes -v
```

## Local Run

Start the observer server from repository root:

```powershell
$env:PYTHONPATH='src'
python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .runs --allow-live-api
```

Then run the Flutter app:

```powershell
Set-Location clients/flutter_app
flutter run
```

Default local fields:

- Observer base URL: `http://127.0.0.1:8765`
- Seat ID: `p3`
- Join code: `local-dev-code`

The client joins the profile-bound human seat selected by the backend profile.
Future multi-human seat picking should be inserted before identity confirmation,
without weakening the participant protocol boundary.

## Android APK

Build a local release APK from this directory:

```powershell
flutter build apk
```

Default output:

```text
clients/flutter_app/build/app/outputs/flutter-apk/app-release.apk
```

The generated APK is a build artifact and is not tracked by git. If you need to
keep the APK, do not run `flutter clean` until the file has been copied or
otherwise preserved.

## Local Cleanup

Repository-local temporary output can be large. It is safe to clear old
repository-local `.tmp/` contents and clean, merged worktrees under
`.worktrees/` when they are no longer needed. Keep dirty worktrees until their
changes are reviewed or intentionally discarded.

Flutter build output under `clients/flutter_app/build/` can be removed with
`flutter clean`, but that also removes the generated APK path above.
