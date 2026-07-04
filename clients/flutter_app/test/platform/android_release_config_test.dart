import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Android Gradle defines internal and production flavors', () {
    final source = _repoFile(
      'clients/flutter_app/android/app/build.gradle.kts',
    ).readAsStringSync();

    expect(source, contains('flavorDimensions += "channel"'));
    expect(source, contains('create("internal")'));
    expect(source, contains('create("production")'));
    expect(
      source,
      contains('applicationId = "io.werewolfagent.werewolf_app.internal"'),
    );
    expect(source, contains('applicationId = "io.werewolfagent.werewolf_app"'));
    expect(source, contains('"Werewolf Agent Internal"'));
    expect(source, contains('"Werewolf Agent"'));
    expect(source, contains('isMinifyEnabled = false'));
    expect(source, contains('isShrinkResources = false'));
  });

  test('Android manifest exposes APK installer provider', () {
    final manifest = _repoFile(
      'clients/flutter_app/android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();

    expect(manifest, contains('android.permission.REQUEST_INSTALL_PACKAGES'));
    expect(manifest, contains('android:label="@string/app_name"'));
    expect(
      manifest,
      contains(r'android:authorities="${applicationId}.apk_provider"'),
    );
  });

  test('apk installer cache directory matches FileProvider path', () {
    final providerPaths = _repoFile(
      'clients/flutter_app/android/app/src/main/res/xml/apk_provider_paths.xml',
    ).readAsStringSync();
    final mainActivity = _repoFile(
      'clients/flutter_app/android/app/src/main/kotlin/io/werewolfagent/werewolf_app/MainActivity.kt',
    ).readAsStringSync();

    expect(providerPaths, contains('werewolf_updates/'));
    expect(mainActivity, contains('getUpdateCacheDirectory'));
    expect(mainActivity, contains('File(cacheDir, "werewolf_updates")'));
    expect(mainActivity, contains('inspectApkArchive'));
    expect(mainActivity, contains('getPackageArchiveInfo'));
    expect(mainActivity, contains('isSignatureCompatible'));
  });

  test('android update workflows are split by channel and promotion', () {
    expect(
      _repoFile('.github/workflows/build-android-internal.yml').existsSync(),
      isTrue,
    );
    expect(
      _repoFile(
        '.github/workflows/build-android-production-candidate.yml',
      ).existsSync(),
      isTrue,
    );
    expect(
      _repoFile(
        '.github/workflows/promote-android-production.yml',
      ).existsSync(),
      isTrue,
    );
    expect(
      _repoFile('.github/scripts/android-update/common.ps1').existsSync(),
      isTrue,
    );
  });

  test('production promotion updates stable manifest without rebuilding', () {
    final content = _repoFile(
      '.github/workflows/promote-android-production.yml',
    ).readAsStringSync();

    expect(content, contains('gh release download'));
    expect(content, contains('updates/stable.json'));
    expect(content, contains('latest.json'));
    expect(content, contains('build-metadata.json'));
    expect(content, isNot(contains('flutter build')));
    expect(content, isNot(contains('assemble')));
  });

  test('shared script emits schema v1 identity and metadata fields', () {
    final content = _repoFile(
      '.github/scripts/android-update/common.ps1',
    ).readAsStringSync();

    expect(content, contains('schemaVersion'));
    expect(content, contains('channel'));
    expect(content, contains('applicationId'));
    expect(content, contains('signingCertificateSha256'));
    expect(content, contains('apkSha256'));
    expect(content, contains('apkSizeBytes'));
    expect(content, contains('releaseTag'));
    expect(content, contains('gitCommit'));
    expect(content, contains('apksigner'));
  });
}

File _repoFile(String relativePath) {
  final root = _repoRoot();
  return File('${root.path}/$relativePath');
}

Directory _repoRoot() {
  var directory = Directory.current;
  while (true) {
    final hasProjectMemory = File('${directory.path}/MEMORY.md').existsSync();
    final hasGitHubWorkflowDir = Directory(
      '${directory.path}/.github',
    ).existsSync();
    if (hasProjectMemory && hasGitHubWorkflowDir) {
      return directory;
    }
    final parent = directory.parent;
    if (parent.path == directory.path) {
      return Directory.current;
    }
    directory = parent;
  }
}
