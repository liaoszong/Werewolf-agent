import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/update/update_models.dart';
import 'package:werewolf_app/src/update/update_repository.dart';
import 'package:werewolf_app/src/update/update_service.dart';

void main() {
  group('AppUpdateManifest', () {
    test('parses schema v1 manifest fields', () {
      final manifest = _manifest(versionCode: 2);

      expect(manifest.schemaVersion, 1);
      expect(manifest.channel, 'production');
      expect(manifest.applicationId, 'io.werewolfagent.werewolf_app');
      expect(manifest.versionName, '0.2.0');
      expect(manifest.versionCode, 2);
      expect(manifest.releaseTag, 'v0.2.0+2');
      expect(manifest.releaseNotes, 'Android release');
    });

    test('rejects non-https APK URL', () {
      final json = _manifestJson(versionCode: 2)
        ..['apkUrl'] =
            'http://github.com/liaoszong/Werewolf-agent/releases/download/v0.2.0+2/werewolf-agent.apk';

      expect(
        () => AppUpdateManifest.fromJson(json),
        throwsA(isA<FormatException>()),
      );
    });
  });

  group('UpdateService', () {
    test('reports update available when manifest versionCode is newer', () async {
      final metadataClient = _FakeMetadataClient(_metadata(versionCode: 2));
      final service = _service(
        manifest: _manifest(versionCode: 2),
        metadataClient: metadataClient,
      );

      final result = await service.checkForUpdate(
        manifestUri: Uri.parse(
          'https://liaoszong.github.io/Werewolf-agent/updates/stable.json',
        ),
        runtimeConfig: _runtimeConfig(currentVersionCode: 1),
      );

      expect(result.status, UpdateCheckStatus.updateAvailable);
      expect(metadataClient.requestedUris, [
        Uri.parse(
          'https://github.com/liaoszong/Werewolf-agent/releases/download/v0.2.0+2/build-metadata.json',
        ),
      ]);
    });

    test('rejects manifest with mismatched channel', () async {
      final service = _service(
        manifest: _manifest(versionCode: 2, channel: 'internal'),
        metadata: _metadata(versionCode: 2, channel: 'internal'),
      );

      expect(
        () => service.checkForUpdate(
          manifestUri: Uri.parse(
            'https://liaoszong.github.io/Werewolf-agent/updates/stable.json',
          ),
          runtimeConfig: _runtimeConfig(currentVersionCode: 1),
        ),
        throwsA(
          isA<UpdateException>().having(
            (error) => error.code,
            'code',
            'manifest_channel_mismatch',
          ),
        ),
      );
    });

    test(
      'downloads, verifies sha256, validates archive, then opens installer',
      () async {
        final tempDir = await Directory.systemTemp.createTemp(
          'werewolf_update_',
        );
        addTearDown(() async => tempDir.delete(recursive: true));
        final installer = _RecordingInstaller();
        final archiveValidator = _FakeArchiveValidator.forManifest(
          _manifest(versionCode: 2),
        );
        final service = _service(
          manifest: _manifest(versionCode: 2),
          archiveValidator: archiveValidator,
          installer: installer,
        );
        final progress = <double>[];

        final verifiedApk = await service.downloadAndVerify(
          manifest: _manifest(versionCode: 2),
          targetDirectory: tempDir,
          onProgress: (event) => progress.add(event.fraction),
        );
        await service.installVerifiedApk(verifiedApk);

        expect(progress, contains(1.0));
        expect(verifiedApk.file.existsSync(), isTrue);
        expect(archiveValidator.inspectedPaths, [verifiedApk.file.path]);
        expect(installer.installedPaths, [verifiedApk.file.path]);
      },
    );
  });

  group('UpdateRepository', () {
    test('tries fallback manifest source when primary source fails', () async {
      final manifestClient = _FailThenSucceedManifestClient(
        manifest: _manifest(versionCode: 2),
      );
      final repository = UpdateRepository(
        service: _service(
          manifestClient: manifestClient,
          manifest: _manifest(versionCode: 2),
        ),
        manifestUri: Uri.parse('https://github.com/latest.json'),
        manifestFallbackUris: [
          Uri.parse('https://mirror.example.com/latest.json'),
        ],
        runtimeConfig: _runtimeConfig(currentVersionCode: 1),
      );

      await repository.checkNow();

      expect(repository.state.status, UpdateStatus.updateAvailable);
      expect(manifestClient.requestedUris, [
        Uri.parse('https://github.com/latest.json'),
        Uri.parse('https://mirror.example.com/latest.json'),
      ]);
    });
  });
}

Map<String, Object?> _manifestJson({
  required int versionCode,
  String channel = 'production',
  String applicationId = 'io.werewolfagent.werewolf_app',
}) {
  return {
    'schemaVersion': 1,
    'channel': channel,
    'applicationId': applicationId,
    'versionName': '0.2.0',
    'versionCode': versionCode,
    'releaseTag': 'v0.2.0+2',
    'gitCommit': 'abcdef1',
    'signingCertificateSha256':
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
    'apkUrl':
        'https://github.com/liaoszong/Werewolf-agent/releases/download/v0.2.0+2/werewolf-agent-production-arm64.apk',
    'sha256':
        '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
    'sizeBytes': 5,
    'releaseNotes': 'Android release',
    'publishedAt': '2026-07-04T12:00:00Z',
  };
}

AppUpdateManifest _manifest({
  required int versionCode,
  String channel = 'production',
  String applicationId = 'io.werewolfagent.werewolf_app',
}) {
  return AppUpdateManifest.fromJson(
    _manifestJson(
      versionCode: versionCode,
      channel: channel,
      applicationId: applicationId,
    ),
  );
}

UpdateBuildMetadata _metadata({
  int versionCode = 2,
  String channel = 'production',
  String applicationId = 'io.werewolfagent.werewolf_app',
}) {
  return UpdateBuildMetadata(
    schemaVersion: 1,
    channel: channel,
    applicationId: applicationId,
    versionName: '0.2.0',
    versionCode: versionCode,
    releaseTag: 'v0.2.0+2',
    gitCommit: 'abcdef1',
    signingCertificateSha256:
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
    apkSha256:
        '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
    apkSizeBytes: 5,
    apkAssetName: 'werewolf-agent-production-arm64.apk',
    builtAt: DateTime.parse('2026-07-04T12:00:00Z'),
  );
}

UpdateRuntimeConfig _runtimeConfig({required int currentVersionCode}) {
  return UpdateRuntimeConfig(
    channel: 'production',
    applicationId: 'io.werewolfagent.werewolf_app',
    currentVersionCode: currentVersionCode,
  );
}

UpdateService _service({
  required AppUpdateManifest manifest,
  UpdateManifestClient? manifestClient,
  UpdateBuildMetadata? metadata,
  UpdateMetadataClient? metadataClient,
  UpdateApkDownloader? downloader,
  UpdateApkArchiveValidator? archiveValidator,
  UpdateApkInstaller? installer,
}) {
  return UpdateService(
    manifestClient: manifestClient ?? _FakeManifestClient(manifest),
    metadataClient:
        metadataClient ??
        _FakeMetadataClient(
          metadata ??
              _metadata(
                versionCode: manifest.versionCode,
                channel: manifest.channel,
                applicationId: manifest.applicationId,
              ),
        ),
    downloader: downloader ?? _FakeDownloader(utf8.encode('hello')),
    archiveValidator:
        archiveValidator ?? _FakeArchiveValidator.forManifest(manifest),
    installer: installer ?? _RecordingInstaller(),
  );
}

final class _FakeManifestClient implements UpdateManifestClient {
  final AppUpdateManifest manifest;

  const _FakeManifestClient(this.manifest);

  @override
  Future<AppUpdateManifest> fetchManifest(Uri manifestUri) async => manifest;
}

final class _FakeMetadataClient implements UpdateMetadataClient {
  final UpdateBuildMetadata metadata;
  final requestedUris = <Uri>[];

  _FakeMetadataClient(this.metadata);

  @override
  Future<UpdateBuildMetadata> fetchMetadata(Uri metadataUri) async {
    requestedUris.add(metadataUri);
    return metadata;
  }
}

final class _FailThenSucceedManifestClient implements UpdateManifestClient {
  final AppUpdateManifest manifest;
  final requestedUris = <Uri>[];

  _FailThenSucceedManifestClient({required this.manifest});

  @override
  Future<AppUpdateManifest> fetchManifest(Uri manifestUri) async {
    requestedUris.add(manifestUri);
    if (requestedUris.length == 1) {
      throw const UpdateException('manifest_fetch_failed', '检查更新失败：网络不可用');
    }
    return manifest;
  }
}

final class _FakeDownloader implements UpdateApkDownloader {
  final List<int> bytes;

  const _FakeDownloader(this.bytes);

  @override
  Stream<UpdateDownloadProgress> download({
    required Uri apkUrl,
    required File destination,
    required int expectedSizeBytes,
  }) async* {
    await destination.parent.create(recursive: true);
    await destination.writeAsBytes(bytes);
    yield UpdateDownloadProgress(
      downloadedBytes: bytes.length,
      totalBytes: expectedSizeBytes,
    );
  }
}

final class _FakeArchiveValidator implements UpdateApkArchiveValidator {
  final ApkArchiveValidationResult result;
  final inspectedPaths = <String>[];

  _FakeArchiveValidator(this.result);

  factory _FakeArchiveValidator.forManifest(AppUpdateManifest manifest) {
    return _FakeArchiveValidator(
      ApkArchiveValidationResult(
        packageName: manifest.applicationId,
        versionCode: manifest.versionCode,
        signingCertificateSha256: manifest.signingCertificateSha256,
        isSignatureCompatible: true,
      ),
    );
  }

  @override
  Future<ApkArchiveValidationResult> inspect(File apkFile) async {
    inspectedPaths.add(apkFile.path);
    return result;
  }
}

final class _RecordingInstaller implements UpdateApkInstaller {
  final installedPaths = <String>[];

  @override
  Future<void> install(File apkFile) async {
    installedPaths.add(apkFile.path);
  }
}
