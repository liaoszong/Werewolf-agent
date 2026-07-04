import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import 'update_models.dart';

abstract interface class UpdateManifestClient {
  Future<AppUpdateManifest> fetchManifest(Uri manifestUri);
}

abstract interface class UpdateMetadataClient {
  Future<UpdateBuildMetadata> fetchMetadata(Uri metadataUri);
}

abstract interface class UpdateApkDownloader {
  Stream<UpdateDownloadProgress> download({
    required Uri apkUrl,
    required File destination,
    required int expectedSizeBytes,
  });
}

abstract interface class UpdateApkArchiveValidator {
  Future<ApkArchiveValidationResult> inspect(File apkFile);
}

abstract interface class UpdateApkInstaller {
  Future<void> install(File apkFile);
}

final class HttpUpdateBuildMetadataClient implements UpdateMetadataClient {
  final HttpClient _httpClient;
  final Duration timeout;

  HttpUpdateBuildMetadataClient({
    HttpClient? httpClient,
    this.timeout = const Duration(seconds: 12),
  }) : _httpClient = httpClient ?? HttpClient();

  @override
  Future<UpdateBuildMetadata> fetchMetadata(Uri metadataUri) async {
    try {
      final request = await _httpClient.getUrl(metadataUri).timeout(timeout);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final response = await request.close().timeout(timeout);
      if (response.statusCode != HttpStatus.ok) {
        throw UpdateException(
          'metadata_http_status',
          '检查更新失败：metadata HTTP ${response.statusCode}',
        );
      }
      final body = await response.transform(utf8.decoder).join();
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, Object?>) {
        throw const FormatException('metadata root must be a JSON object.');
      }
      return UpdateBuildMetadata.fromJson(decoded);
    } on UpdateException {
      rethrow;
    } on Object catch (error) {
      throw UpdateException('metadata_fetch_failed', '检查更新失败：$error', error);
    }
  }
}

final class HttpUpdateManifestClient implements UpdateManifestClient {
  final HttpClient _httpClient;
  final Duration timeout;

  HttpUpdateManifestClient({
    HttpClient? httpClient,
    this.timeout = const Duration(seconds: 12),
  }) : _httpClient = httpClient ?? HttpClient();

  @override
  Future<AppUpdateManifest> fetchManifest(Uri manifestUri) async {
    try {
      final request = await _httpClient.getUrl(manifestUri).timeout(timeout);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final response = await request.close().timeout(timeout);
      if (response.statusCode != HttpStatus.ok) {
        throw UpdateException(
          'manifest_http_status',
          '检查更新失败：manifest HTTP ${response.statusCode}',
        );
      }
      final body = await response.transform(utf8.decoder).join();
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, Object?>) {
        throw const FormatException('manifest root must be a JSON object.');
      }
      return AppUpdateManifest.fromJson(decoded);
    } on UpdateException {
      rethrow;
    } on Object catch (error) {
      throw UpdateException('manifest_fetch_failed', '检查更新失败：$error', error);
    }
  }
}

final class HttpUpdateApkDownloader implements UpdateApkDownloader {
  final HttpClient _httpClient;
  final Duration connectionTimeout;
  final Duration chunkIdleTimeout;

  HttpUpdateApkDownloader({
    HttpClient? httpClient,
    Duration? timeout,
    Duration connectionTimeout = const Duration(seconds: 20),
    Duration chunkIdleTimeout = const Duration(minutes: 2),
  }) : _httpClient = httpClient ?? HttpClient(),
       connectionTimeout = timeout ?? connectionTimeout,
       chunkIdleTimeout = timeout ?? chunkIdleTimeout;

  @override
  Stream<UpdateDownloadProgress> download({
    required Uri apkUrl,
    required File destination,
    required int expectedSizeBytes,
  }) async* {
    final tempFile = File('${destination.path}.part');
    IOSink? sink;
    try {
      await destination.parent.create(recursive: true);
      if (tempFile.existsSync()) {
        await tempFile.delete();
      }

      final request = await _httpClient
          .getUrl(apkUrl)
          .timeout(connectionTimeout);
      final response = await request.close().timeout(connectionTimeout);
      if (response.statusCode != HttpStatus.ok) {
        throw UpdateException(
          'apk_http_status',
          'APK 下载失败：HTTP ${response.statusCode}',
        );
      }

      final totalBytes = expectedSizeBytes > 0
          ? expectedSizeBytes
          : response.contentLength;
      var downloadedBytes = 0;
      sink = tempFile.openWrite();
      await for (final chunk in response.timeout(chunkIdleTimeout)) {
        sink.add(chunk);
        downloadedBytes += chunk.length;
        yield UpdateDownloadProgress(
          downloadedBytes: downloadedBytes,
          totalBytes: totalBytes,
        );
      }
      await sink.close();
      sink = null;

      if (expectedSizeBytes > 0 && downloadedBytes != expectedSizeBytes) {
        throw UpdateException(
          'apk_size_mismatch',
          'APK 大小不一致：期望 $expectedSizeBytes bytes，实际 $downloadedBytes bytes',
        );
      }
      if (destination.existsSync()) {
        await destination.delete();
      }
      await tempFile.rename(destination.path);
    } on UpdateException {
      rethrow;
    } on Object catch (error) {
      throw UpdateException('apk_download_failed', 'APK 下载失败：$error', error);
    } finally {
      await sink?.close();
      if (tempFile.existsSync()) {
        await tempFile.delete();
      }
    }
  }
}

final class UpdateService {
  final UpdateManifestClient manifestClient;
  final UpdateMetadataClient metadataClient;
  final UpdateApkDownloader downloader;
  final UpdateApkArchiveValidator archiveValidator;
  final UpdateApkInstaller installer;

  const UpdateService({
    required this.manifestClient,
    required this.metadataClient,
    required this.downloader,
    required this.archiveValidator,
    required this.installer,
  });

  Future<UpdateCheckResult> checkForUpdate({
    required Uri manifestUri,
    required UpdateRuntimeConfig runtimeConfig,
  }) async {
    final manifest = await manifestClient.fetchManifest(manifestUri);
    _validateManifestForRuntime(manifest, runtimeConfig);
    final metadata = await metadataClient.fetchMetadata(
      _metadataUrlFor(manifest.apkUrl),
    );
    _validateMetadata(manifest, metadata);
    if (manifest.versionCode > runtimeConfig.currentVersionCode) {
      return UpdateCheckResult.updateAvailable(manifest);
    }
    return const UpdateCheckResult.noUpdate();
  }

  Future<VerifiedApk> downloadAndVerify({
    required AppUpdateManifest manifest,
    required Directory targetDirectory,
    void Function(UpdateDownloadProgress event)? onProgress,
  }) async {
    final apkFile = File(
      '${targetDirectory.path}${Platform.pathSeparator}${_apkFileName(manifest)}',
    );
    await for (final event in downloader.download(
      apkUrl: manifest.apkUrl,
      destination: apkFile,
      expectedSizeBytes: manifest.sizeBytes,
    )) {
      onProgress?.call(event);
    }

    final actualSha256 = await _sha256OfFile(apkFile);
    if (actualSha256 != manifest.sha256) {
      throw UpdateException(
        'apk_sha256_mismatch',
        'SHA256 校验失败：期望 ${_shortHash(manifest.sha256)}，实际 ${_shortHash(actualSha256)}',
      );
    }

    final archive = await archiveValidator.inspect(apkFile);
    _validateApkArchive(manifest, archive);

    return VerifiedApk(file: apkFile, manifest: manifest, sha256: actualSha256);
  }

  Future<void> installVerifiedApk(VerifiedApk verifiedApk) {
    return installer.install(verifiedApk.file);
  }
}

Uri _metadataUrlFor(Uri apkUrl) {
  final segments = apkUrl.pathSegments.toList(growable: true);
  if (segments.isEmpty) {
    throw const UpdateException('metadata_url_invalid', '构建元数据地址不可用');
  }
  if (segments.first == 'apk') {
    segments[0] = 'metadata';
  }
  segments[segments.length - 1] = 'build-metadata.json';
  return apkUrl.replace(pathSegments: segments);
}

void _validateManifestForRuntime(
  AppUpdateManifest manifest,
  UpdateRuntimeConfig runtimeConfig,
) {
  if (manifest.channel != runtimeConfig.channel) {
    throw UpdateException(
      'manifest_channel_mismatch',
      '更新通道不匹配：当前 ${runtimeConfig.channel}，manifest ${manifest.channel}',
    );
  }
  if (manifest.applicationId != runtimeConfig.applicationId) {
    throw UpdateException(
      'manifest_application_id_mismatch',
      '应用包名不匹配：当前 ${runtimeConfig.applicationId}，manifest ${manifest.applicationId}',
    );
  }
}

void _validateMetadata(
  AppUpdateManifest manifest,
  UpdateBuildMetadata metadata,
) {
  final mismatches = <String>[];
  void compare(String field, Object manifestValue, Object metadataValue) {
    if (manifestValue != metadataValue) {
      mismatches.add(field);
    }
  }

  compare('schemaVersion', manifest.schemaVersion, metadata.schemaVersion);
  compare('channel', manifest.channel, metadata.channel);
  compare('applicationId', manifest.applicationId, metadata.applicationId);
  compare('versionName', manifest.versionName, metadata.versionName);
  compare('versionCode', manifest.versionCode, metadata.versionCode);
  compare('releaseTag', manifest.releaseTag, metadata.releaseTag);
  compare('gitCommit', manifest.gitCommit, metadata.gitCommit);
  compare(
    'signingCertificateSha256',
    manifest.signingCertificateSha256,
    metadata.signingCertificateSha256,
  );
  compare('sha256', manifest.sha256, metadata.apkSha256);
  compare('sizeBytes', manifest.sizeBytes, metadata.apkSizeBytes);

  if (mismatches.isNotEmpty) {
    throw UpdateException(
      'release_metadata_mismatch',
      'Release 构建元数据不匹配：${mismatches.join(", ")}',
    );
  }
}

void _validateApkArchive(
  AppUpdateManifest manifest,
  ApkArchiveValidationResult archive,
) {
  if (archive.packageName != manifest.applicationId) {
    throw UpdateException(
      'apk_package_mismatch',
      'APK 包名不匹配：期望 ${manifest.applicationId}，实际 ${archive.packageName}',
    );
  }
  if (archive.versionCode != manifest.versionCode) {
    throw UpdateException(
      'apk_version_code_mismatch',
      'APK versionCode 不匹配：期望 ${manifest.versionCode}，实际 ${archive.versionCode}',
    );
  }
  if (archive.signingCertificateSha256 != manifest.signingCertificateSha256) {
    throw UpdateException(
      'apk_signing_certificate_mismatch',
      'APK 签名证书 SHA256 不匹配：期望 ${_shortHash(manifest.signingCertificateSha256)}，实际 ${_shortHash(archive.signingCertificateSha256)}',
    );
  }
  if (!archive.isSignatureCompatible) {
    throw const UpdateException(
      'apk_signature_incompatible',
      'APK 签名与当前已安装应用不兼容',
    );
  }
}

String _apkFileName(AppUpdateManifest manifest) {
  final safeVersion = manifest.versionName.replaceAll(
    RegExp(r'[^0-9A-Za-z._-]'),
    '_',
  );
  return 'werewolf-agent-$safeVersion-${manifest.versionCode}-arm64.apk';
}

Future<String> _sha256OfFile(File file) async {
  final digest = await sha256.bind(file.openRead()).first;
  return digest.toString();
}

String _shortHash(String value) {
  if (value.length <= 12) {
    return value;
  }
  return '${value.substring(0, 12)}...';
}
