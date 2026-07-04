import 'dart:io';

import 'package:flutter/services.dart';

import 'update_models.dart';
import 'update_service.dart';

final class MethodChannelUpdateApkInstaller implements UpdateApkInstaller {
  static const MethodChannel _channel = MethodChannel(
    'werewolf_app/apk_installer',
  );

  Future<Directory> updateCacheDirectory() async {
    if (!Platform.isAndroid) {
      final directory = Directory(
        '${Directory.systemTemp.path}${Platform.pathSeparator}werewolf_updates',
      );
      await directory.create(recursive: true);
      return directory;
    }
    final path = await _channel.invokeMethod<String>('getUpdateCacheDirectory');
    if (path == null || path.trim().isEmpty) {
      throw const UpdateException('apk_cache_directory_missing', '更新缓存目录不可用');
    }
    final directory = Directory(path);
    await directory.create(recursive: true);
    return directory;
  }

  @override
  Future<void> install(File apkFile) async {
    if (!Platform.isAndroid) {
      throw const UpdateException('unsupported_platform', '当前平台不支持 APK 安装');
    }
    await _channel.invokeMethod<void>('installApk', {'path': apkFile.path});
  }
}

final class MethodChannelApkArchiveValidator
    implements UpdateApkArchiveValidator {
  static const MethodChannel _channel = MethodChannel(
    'werewolf_app/apk_installer',
  );

  const MethodChannelApkArchiveValidator();

  @override
  Future<ApkArchiveValidationResult> inspect(File apkFile) async {
    try {
      final payload = await _channel.invokeMapMethod<Object?, Object?>(
        'inspectApkArchive',
        {'path': apkFile.path},
      );
      if (payload == null) {
        throw const UpdateException(
          'apk_archive_inspection_empty',
          'APK 预检结果为空',
        );
      }
      return ApkArchiveValidationResult.fromJson(payload);
    } on UpdateException {
      rethrow;
    } on Object catch (error) {
      throw UpdateException(
        'apk_archive_inspection_failed',
        'APK 预检失败：$error',
        error,
      );
    }
  }
}
