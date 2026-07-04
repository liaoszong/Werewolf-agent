import 'dart:io';

import 'package:flutter/foundation.dart';

import 'update_models.dart';
import 'update_service.dart';

typedef UpdateCacheDirectoryProvider = Future<Directory> Function();

final class UpdateRepository extends ChangeNotifier {
  static const int maxLogEntries = 200;

  final UpdateService service;
  final Uri? manifestUri;
  final List<Uri> manifestFallbackUris;
  final UpdateRuntimeConfig runtimeConfig;
  final UpdateCacheDirectoryProvider cacheDirectoryProvider;
  final DateTime Function() clock;

  UpdateState _state = const UpdateState.initial();

  UpdateRepository({
    required this.service,
    required this.manifestUri,
    this.manifestFallbackUris = const [],
    required this.runtimeConfig,
    UpdateCacheDirectoryProvider? cacheDirectoryProvider,
    DateTime Function()? clock,
  }) : cacheDirectoryProvider =
           cacheDirectoryProvider ?? _defaultCacheDirectoryProvider,
       clock = clock ?? DateTime.now;

  UpdateState get state => _state;

  Future<UpdateCheckResult?> checkNow() async {
    final candidates = _manifestCandidates();
    if (candidates.isEmpty) {
      _fail('未配置更新 manifest 地址');
      return null;
    }

    _log('开始检查更新');
    _setState(
      status: UpdateStatus.checking,
      clearAvailableUpdate: true,
      clearProgress: true,
      message: '正在检查更新...',
      clearError: true,
    );

    Object? lastError;
    try {
      for (var index = 0; index < candidates.length; index += 1) {
        final candidate = candidates[index];
        try {
          final result = await service.checkForUpdate(
            manifestUri: candidate,
            runtimeConfig: runtimeConfig,
          );
          if (index > 0) {
            _log('已使用备用更新源：${_sourceLabel(candidate)}');
          }
          switch (result.status) {
            case UpdateCheckStatus.noUpdate:
              _log('已是最新版本');
              _setState(
                status: UpdateStatus.noUpdate,
                clearAvailableUpdate: true,
                clearProgress: true,
                message: '已是最新版本',
                clearError: true,
              );
            case UpdateCheckStatus.updateAvailable:
              final manifest = result.manifest!;
              _log('发现新版本 ${manifest.versionName} (${manifest.versionCode})');
              _setState(
                status: UpdateStatus.updateAvailable,
                availableUpdate: manifest,
                clearProgress: true,
                message: '发现新版本 ${manifest.versionName}',
                clearError: true,
              );
          }
          return result;
        } on Object catch (error) {
          lastError = error;
          if (index < candidates.length - 1) {
            _log(
              '更新源不可用，尝试备用源：${_sourceLabel(candidates[index + 1])}',
              level: UpdateLogLevel.warning,
            );
            continue;
          }
        }
      }
      _fail(_messageFromError(lastError ?? '检查更新失败'));
      return null;
    } on Object catch (error) {
      _fail(_messageFromError(error));
      return null;
    }
  }

  Future<void> downloadAndInstall() async {
    final manifest = _state.availableUpdate;
    if (manifest == null) {
      _fail('没有可下载的更新');
      return;
    }

    _log('开始下载 APK');
    _setState(
      status: UpdateStatus.downloading,
      progress: 0,
      downloadedBytes: 0,
      totalBytes: manifest.sizeBytes,
      message: '正在下载 APK...',
      clearError: true,
    );

    try {
      final targetDirectory = await cacheDirectoryProvider();
      final verifiedApk = await service.downloadAndVerify(
        manifest: manifest,
        targetDirectory: targetDirectory,
        onProgress: (event) {
          _setState(
            status: event.fraction >= 1
                ? UpdateStatus.verifying
                : UpdateStatus.downloading,
            progress: event.fraction,
            downloadedBytes: event.downloadedBytes,
            totalBytes: event.totalBytes,
            message: event.fraction >= 1 ? '正在校验 SHA256...' : '正在下载 APK...',
            clearError: true,
          );
        },
      );

      _log('SHA256 校验通过');
      await service.installVerifiedApk(verifiedApk);
      _log('系统安装器已打开');
      _setState(
        status: UpdateStatus.installerOpened,
        progress: 1,
        downloadedBytes: manifest.sizeBytes,
        totalBytes: manifest.sizeBytes,
        message: '系统安装器已打开',
        clearError: true,
      );
    } on Object catch (error) {
      _fail(_messageFromError(error));
    }
  }

  List<Uri> _manifestCandidates() {
    final candidates = <Uri>[];
    final primary = manifestUri;
    if (primary != null) {
      candidates.add(primary);
    }
    for (final fallback in manifestFallbackUris) {
      if (!candidates.contains(fallback)) {
        candidates.add(fallback);
      }
    }
    return candidates;
  }

  void _log(String message, {UpdateLogLevel level = UpdateLogLevel.info}) {
    final nextLogs = [
      UpdateLogEntry(timestamp: clock(), level: level, message: message),
      ..._state.logs,
    ].take(maxLogEntries).toList(growable: false);
    _state = UpdateState(
      status: _state.status,
      availableUpdate: _state.availableUpdate,
      progress: _state.progress,
      downloadedBytes: _state.downloadedBytes,
      totalBytes: _state.totalBytes,
      message: _state.message,
      errorMessage: _state.errorMessage,
      logs: nextLogs,
    );
    notifyListeners();
  }

  void _fail(String message) {
    _log(message, level: UpdateLogLevel.error);
    _setState(
      status: UpdateStatus.error,
      message: message,
      errorMessage: message,
      clearProgress: true,
    );
  }

  void _setState({
    UpdateStatus? status,
    AppUpdateManifest? availableUpdate,
    bool clearAvailableUpdate = false,
    double? progress,
    bool clearProgress = false,
    int? downloadedBytes,
    int? totalBytes,
    String? message,
    String? errorMessage,
    bool clearError = false,
  }) {
    _state = UpdateState(
      status: status ?? _state.status,
      availableUpdate: clearAvailableUpdate
          ? null
          : availableUpdate ?? _state.availableUpdate,
      progress: clearProgress ? null : progress ?? _state.progress,
      downloadedBytes: clearProgress
          ? null
          : downloadedBytes ?? _state.downloadedBytes,
      totalBytes: clearProgress ? null : totalBytes ?? _state.totalBytes,
      message: message ?? _state.message,
      errorMessage: clearError ? null : errorMessage ?? _state.errorMessage,
      logs: _state.logs,
    );
    notifyListeners();
  }
}

Future<Directory> _defaultCacheDirectoryProvider() async {
  final directory = Directory(
    '${Directory.systemTemp.path}${Platform.pathSeparator}werewolf_updates',
  );
  await directory.create(recursive: true);
  return directory;
}

String _messageFromError(Object error) {
  if (error is UpdateException) {
    return error.message;
  }
  return '更新失败：$error';
}

String _sourceLabel(Uri uri) {
  if (uri.host.isNotEmpty) {
    return uri.host;
  }
  return uri.toString();
}
