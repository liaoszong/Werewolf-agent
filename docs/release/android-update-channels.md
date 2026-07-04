# Android update channels

Werewolf-agent Flutter Android uses the same lightweight update shape as
BatteryCtrl:

- the app checks a JSON manifest, not the GitHub API;
- the APK is downloaded in-app, size-checked, SHA256-checked, archive-checked,
  then handed to the Android system package installer;
- Internal and Production are separate Android flavors, application IDs, signing
  keys, GitHub Release assets, and GitHub Pages manifests.

## Channels

| Channel | Android applicationId | Manifest |
| --- | --- | --- |
| Internal | `io.werewolfagent.werewolf_app.internal` | `https://liaoszong.github.io/Werewolf-agent/updates/internal.json` |
| Production | `io.werewolfagent.werewolf_app` | `https://liaoszong.github.io/Werewolf-agent/updates/stable.json` |

Internal releases are prereleases and update `updates/internal.json` directly.
Production first builds a prerelease candidate. Promotion reuses that exact APK
and only publishes `updates/stable.json`; it must not rebuild.

## Observer endpoint defaults

The Android app's participant client talks to the observer/participant protocol,
not to GitHub. Early mobile builds default to:

```text
http://api.paleink.cc:8765
```

The Settings page exposes quick server presets for PaleInk Cloud and Local Dev.
For local development on a physical Android device, use the computer LAN address
instead of `127.0.0.1`. The public HTTP endpoint is for smoke testing; put it
behind HTTPS and access control before using real provider credentials.

## GitHub setup

Enable GitHub Pages from the `gh-pages` branch root.

Required repository secrets:

- `INTERNAL_ANDROID_KEYSTORE_BASE64`
- `INTERNAL_ANDROID_KEY_PROPERTIES`
- `PRODUCTION_ANDROID_KEYSTORE_BASE64`
- `PRODUCTION_ANDROID_KEY_PROPERTIES`

The properties secret must include:

```properties
storeFile=internal-upload-keystore.jks
storePassword=...
keyAlias=...
keyPassword=...
```

Use `production-upload-keystore.jks` in the Production properties secret.

Optional repository variables:

- `INTERNAL_UPDATE_MANIFEST_FALLBACK_URLS`
- `PRODUCTION_UPDATE_MANIFEST_FALLBACK_URLS`

Multiple fallback URLs may be separated by comma, semicolon, or newline.

## Workflows

1. `Build Android Internal`
   - Input tag example: `v0.2.1-internal.1+211`
   - Builds `werewolf-agent-internal-arm64.apk`
   - Uploads APK, `latest.json`, and `build-metadata.json` to a prerelease
   - Publishes `updates/internal.json` to GitHub Pages

2. `Build Android Production Candidate`
   - Input tag example: `v0.2.1+211`
   - Builds `werewolf-agent-production-arm64.apk`
   - Uploads APK, `latest.json`, and `build-metadata.json` to a prerelease
   - Does not update `updates/stable.json`

3. `Promote Android Production`
   - Input tag must be an existing production candidate tag
   - Downloads candidate `latest.json` and `build-metadata.json`
   - Validates schema/channel/identity/hash/size consistency
   - Publishes `updates/stable.json`
   - Marks the GitHub Release as latest and not prerelease

## Published 2026-07-04

GitHub Pages is enabled from the `gh-pages` branch root:
`https://liaoszong.github.io/Werewolf-agent/`.

Internal:

- Workflow run:
  `https://github.com/liaoszong/Werewolf-agent/actions/runs/28708039101`
- Release:
  `https://github.com/liaoszong/Werewolf-agent/releases/tag/v0.2.1-internal.1%2B211`
- Manifest:
  `https://liaoszong.github.io/Werewolf-agent/updates/internal.json`
- APK: `werewolf-agent-internal-arm64.apk`
- Size: `19187346`
- SHA256:
  `eadd9c1f414be42d78e7b691b7f5eb19a778d99132e3dcc555dd86a061a3131a`

Production:

- Candidate workflow run:
  `https://github.com/liaoszong/Werewolf-agent/actions/runs/28708187657`
- Promote workflow run:
  `https://github.com/liaoszong/Werewolf-agent/actions/runs/28708345316`
- Release:
  `https://github.com/liaoszong/Werewolf-agent/releases/tag/v0.2.1%2B211`
- Manifest:
  `https://liaoszong.github.io/Werewolf-agent/updates/stable.json`
- APK: `werewolf-agent-production-arm64.apk`
- Size: `19187330`
- SHA256:
  `f6b420d4013a1effb8c6ab6796e927e520bcd2a88d334dec26637ddb7abce9dc`

## Local checks

```powershell
cd clients/flutter_app
flutter analyze
flutter test
flutter build apk --debug --flavor internal --target-platform android-arm64
flutter build apk --debug --flavor production --target-platform android-arm64
```

Release artifact generation needs `apksigner`. If the SDK is not on PATH, set:

```powershell
$env:ANDROID_HOME='G:\Android\Sdk'
$env:ANDROID_SDK_ROOT='G:\Android\Sdk'
```
