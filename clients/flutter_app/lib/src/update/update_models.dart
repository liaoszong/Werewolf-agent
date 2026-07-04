import 'dart:io';

final class AppUpdateManifest {
  final int schemaVersion;
  final String channel;
  final String applicationId;
  final String versionName;
  final int versionCode;
  final String releaseTag;
  final String gitCommit;
  final String signingCertificateSha256;
  final Uri apkUrl;
  final String sha256;
  final int sizeBytes;
  final String releaseNotes;
  final DateTime publishedAt;

  const AppUpdateManifest({
    required this.schemaVersion,
    required this.channel,
    required this.applicationId,
    required this.versionName,
    required this.versionCode,
    required this.releaseTag,
    required this.gitCommit,
    required this.signingCertificateSha256,
    required this.apkUrl,
    required this.sha256,
    required this.sizeBytes,
    required this.releaseNotes,
    required this.publishedAt,
  });

  factory AppUpdateManifest.fromJson(Map<String, Object?> json) {
    final schemaVersion = _requiredInt(json, 'schemaVersion');
    final channel = _requiredString(json, 'channel');
    final applicationId = _requiredString(json, 'applicationId');
    final versionName = _requiredString(json, 'versionName');
    final versionCode = _requiredInt(json, 'versionCode');
    final releaseTag = _requiredString(json, 'releaseTag');
    final gitCommit = _requiredString(json, 'gitCommit');
    final signingCertificateSha256 = _requiredString(
      json,
      'signingCertificateSha256',
    ).trim().toLowerCase();
    final apkUrl = Uri.parse(_requiredString(json, 'apkUrl'));
    final sha256 = _requiredString(json, 'sha256').trim().toLowerCase();
    final sizeBytes = _requiredInt(json, 'sizeBytes');
    final releaseNotes = _requiredString(json, 'releaseNotes');
    final publishedAt = DateTime.parse(_requiredString(json, 'publishedAt'));

    _validateManifestFields(
      schemaVersion: schemaVersion,
      channel: channel,
      applicationId: applicationId,
      versionName: versionName,
      versionCode: versionCode,
      releaseTag: releaseTag,
      gitCommit: gitCommit,
      signingCertificateSha256: signingCertificateSha256,
      apkUrl: apkUrl,
      sha256: sha256,
      sizeBytes: sizeBytes,
    );

    return AppUpdateManifest(
      schemaVersion: schemaVersion,
      channel: channel,
      applicationId: applicationId,
      versionName: versionName,
      versionCode: versionCode,
      releaseTag: releaseTag,
      gitCommit: gitCommit,
      signingCertificateSha256: signingCertificateSha256,
      apkUrl: apkUrl,
      sha256: sha256,
      sizeBytes: sizeBytes,
      releaseNotes: releaseNotes,
      publishedAt: publishedAt,
    );
  }
}

final class UpdateRuntimeConfig {
  final String channel;
  final String applicationId;
  final int currentVersionCode;

  const UpdateRuntimeConfig({
    required this.channel,
    required this.applicationId,
    required this.currentVersionCode,
  });
}

final class UpdateBuildMetadata {
  final int schemaVersion;
  final String channel;
  final String applicationId;
  final String versionName;
  final int versionCode;
  final String releaseTag;
  final String gitCommit;
  final String signingCertificateSha256;
  final String apkSha256;
  final int apkSizeBytes;
  final String apkAssetName;
  final DateTime builtAt;

  const UpdateBuildMetadata({
    required this.schemaVersion,
    required this.channel,
    required this.applicationId,
    required this.versionName,
    required this.versionCode,
    required this.releaseTag,
    required this.gitCommit,
    required this.signingCertificateSha256,
    required this.apkSha256,
    required this.apkSizeBytes,
    required this.apkAssetName,
    required this.builtAt,
  });

  factory UpdateBuildMetadata.fromJson(Map<String, Object?> json) {
    final schemaVersion = _requiredInt(json, 'schemaVersion');
    final channel = _requiredString(json, 'channel');
    final applicationId = _requiredString(json, 'applicationId');
    final versionName = _requiredString(json, 'versionName');
    final versionCode = _requiredInt(json, 'versionCode');
    final releaseTag = _requiredString(json, 'releaseTag');
    final gitCommit = _requiredString(json, 'gitCommit');
    final signingCertificateSha256 = _requiredString(
      json,
      'signingCertificateSha256',
    ).trim().toLowerCase();
    final apkSha256 = _requiredString(json, 'apkSha256').trim().toLowerCase();
    final apkSizeBytes = _requiredInt(json, 'apkSizeBytes');
    final apkAssetName = _requiredString(json, 'apkAssetName');
    final builtAt = DateTime.parse(_requiredString(json, 'builtAt'));

    _validateManifestFields(
      schemaVersion: schemaVersion,
      channel: channel,
      applicationId: applicationId,
      versionName: versionName,
      versionCode: versionCode,
      releaseTag: releaseTag,
      gitCommit: gitCommit,
      signingCertificateSha256: signingCertificateSha256,
      apkUrl: Uri.https(
        'github.com',
        '/metadata/releases/download/$releaseTag/$apkAssetName',
      ),
      sha256: apkSha256,
      sizeBytes: apkSizeBytes,
    );
    if (apkAssetName.trim().isEmpty) {
      throw const FormatException('apkAssetName must not be empty.');
    }

    return UpdateBuildMetadata(
      schemaVersion: schemaVersion,
      channel: channel,
      applicationId: applicationId,
      versionName: versionName,
      versionCode: versionCode,
      releaseTag: releaseTag,
      gitCommit: gitCommit,
      signingCertificateSha256: signingCertificateSha256,
      apkSha256: apkSha256,
      apkSizeBytes: apkSizeBytes,
      apkAssetName: apkAssetName,
      builtAt: builtAt,
    );
  }
}

final class ApkArchiveValidationResult {
  final String packageName;
  final int versionCode;
  final String signingCertificateSha256;
  final bool isSignatureCompatible;

  const ApkArchiveValidationResult({
    required this.packageName,
    required this.versionCode,
    required this.signingCertificateSha256,
    required this.isSignatureCompatible,
  });

  factory ApkArchiveValidationResult.fromJson(Map<Object?, Object?> json) {
    final packageName = _requiredObjectString(json, 'packageName');
    final versionCode = _requiredObjectInt(json, 'versionCode');
    final signingCertificateSha256 = _requiredObjectString(
      json,
      'signingCertificateSha256',
    ).trim().toLowerCase();
    final isSignatureCompatible = _requiredObjectBool(
      json,
      'isSignatureCompatible',
    );

    if (packageName.trim().isEmpty) {
      throw const FormatException('packageName must not be empty.');
    }
    if (versionCode <= 0) {
      throw const FormatException('versionCode must be greater than 0.');
    }
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(signingCertificateSha256)) {
      throw const FormatException(
        'signingCertificateSha256 must be 64 lowercase hex chars.',
      );
    }

    return ApkArchiveValidationResult(
      packageName: packageName,
      versionCode: versionCode,
      signingCertificateSha256: signingCertificateSha256,
      isSignatureCompatible: isSignatureCompatible,
    );
  }
}

enum UpdateCheckStatus { noUpdate, updateAvailable }

final class UpdateCheckResult {
  final UpdateCheckStatus status;
  final AppUpdateManifest? manifest;

  const UpdateCheckResult._({required this.status, this.manifest});

  const UpdateCheckResult.noUpdate()
    : this._(status: UpdateCheckStatus.noUpdate);

  const UpdateCheckResult.updateAvailable(AppUpdateManifest manifest)
    : this._(status: UpdateCheckStatus.updateAvailable, manifest: manifest);
}

final class UpdateDownloadProgress {
  final int downloadedBytes;
  final int totalBytes;

  const UpdateDownloadProgress({
    required this.downloadedBytes,
    required this.totalBytes,
  });

  double get fraction {
    if (totalBytes <= 0) {
      return 0;
    }
    final value = downloadedBytes / totalBytes;
    return value.clamp(0.0, 1.0).toDouble();
  }
}

final class VerifiedApk {
  final File file;
  final AppUpdateManifest manifest;
  final String sha256;

  const VerifiedApk({
    required this.file,
    required this.manifest,
    required this.sha256,
  });
}

enum UpdateStatus {
  idle,
  checking,
  noUpdate,
  updateAvailable,
  downloading,
  verifying,
  installerOpened,
  error,
}

enum UpdateLogLevel { info, warning, error }

final class UpdateLogEntry {
  final DateTime timestamp;
  final UpdateLogLevel level;
  final String message;

  const UpdateLogEntry({
    required this.timestamp,
    required this.level,
    required this.message,
  });
}

final class UpdateState {
  final UpdateStatus status;
  final AppUpdateManifest? availableUpdate;
  final double? progress;
  final int? downloadedBytes;
  final int? totalBytes;
  final String? message;
  final String? errorMessage;
  final List<UpdateLogEntry> logs;

  const UpdateState({
    required this.status,
    this.availableUpdate,
    this.progress,
    this.downloadedBytes,
    this.totalBytes,
    this.message,
    this.errorMessage,
    this.logs = const [],
  });

  const UpdateState.initial() : this(status: UpdateStatus.idle);

  bool get isBusy =>
      status == UpdateStatus.checking ||
      status == UpdateStatus.downloading ||
      status == UpdateStatus.verifying;
}

final class UpdateException implements Exception {
  final String code;
  final String message;
  final Object? cause;

  const UpdateException(this.code, this.message, [this.cause]);

  @override
  String toString() => 'UpdateException($code): $message';
}

void _validateManifestFields({
  required int schemaVersion,
  required String channel,
  required String applicationId,
  required String versionName,
  required int versionCode,
  required String releaseTag,
  required String gitCommit,
  required String signingCertificateSha256,
  required Uri apkUrl,
  required String sha256,
  required int sizeBytes,
}) {
  if (schemaVersion != 1) {
    throw const FormatException('schemaVersion must be 1.');
  }
  if (channel != 'internal' && channel != 'production') {
    throw const FormatException('channel must be internal or production.');
  }
  if (applicationId.trim().isEmpty) {
    throw const FormatException('applicationId must not be empty.');
  }
  if (versionName.trim().isEmpty) {
    throw const FormatException('versionName must not be empty.');
  }
  if (versionCode <= 0) {
    throw const FormatException('versionCode must be greater than 0.');
  }
  if (!RegExp(r'^v.+\+[1-9][0-9]*$').hasMatch(releaseTag)) {
    throw const FormatException('releaseTag must be a versioned release tag.');
  }
  if (!RegExp(r'^[0-9a-fA-F]{7,40}$').hasMatch(gitCommit)) {
    throw const FormatException('gitCommit must be a git SHA.');
  }
  if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(signingCertificateSha256)) {
    throw const FormatException(
      'signingCertificateSha256 must be 64 lowercase hex chars.',
    );
  }
  if (apkUrl.scheme != 'https') {
    throw const FormatException('apkUrl must use https.');
  }
  if (!apkUrl.hasScheme || apkUrl.host.isEmpty) {
    throw const FormatException('apkUrl must be an absolute URL.');
  }
  final releaseTagPathSegment = apkUrl.pathSegments.any(
    (segment) => Uri.decodeComponent(segment) == releaseTag,
  );
  if (!releaseTagPathSegment) {
    throw const FormatException(
      'apkUrl must point to the manifest releaseTag.',
    );
  }
  if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256)) {
    throw const FormatException('sha256 must be 64 lowercase hex chars.');
  }
  if (sizeBytes <= 0) {
    throw const FormatException('sizeBytes must be greater than 0.');
  }
}

String _requiredString(Map<String, Object?> json, String key) {
  final value = json[key];
  if (value is! String) {
    throw FormatException('$key must be a string.');
  }
  return value;
}

int _requiredInt(Map<String, Object?> json, String key) {
  final value = json[key];
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  throw FormatException('$key must be an integer.');
}

String _requiredObjectString(Map<Object?, Object?> json, String key) {
  final value = json[key];
  if (value is! String) {
    throw FormatException('$key must be a string.');
  }
  return value;
}

int _requiredObjectInt(Map<Object?, Object?> json, String key) {
  final value = json[key];
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  throw FormatException('$key must be an integer.');
}

bool _requiredObjectBool(Map<Object?, Object?> json, String key) {
  final value = json[key];
  if (value is! bool) {
    throw FormatException('$key must be a boolean.');
  }
  return value;
}
