class BuildInfo {
  const BuildInfo._();

  static const String defaultAppVersion = '1.0.0+1';
  static const String defaultUpdateChannel = 'production';
  static const String defaultUpdateApplicationId =
      'io.werewolfagent.werewolf_app';
  static const String defaultUpdateManifestUrl = '';
  static const String defaultUpdateManifestFallbackUrls = '';

  static const String gitCommit = String.fromEnvironment(
    'GIT_COMMIT',
    defaultValue: 'unknown',
  );

  static const String buildTime = String.fromEnvironment(
    'BUILD_TIME',
    defaultValue: 'unknown',
  );

  static const String appVersion = String.fromEnvironment(
    'APP_VERSION',
    defaultValue: defaultAppVersion,
  );

  static const String updateChannel = String.fromEnvironment(
    'UPDATE_CHANNEL',
    defaultValue: defaultUpdateChannel,
  );

  static const String updateApplicationId = String.fromEnvironment(
    'UPDATE_APPLICATION_ID',
    defaultValue: defaultUpdateApplicationId,
  );

  static const String updateManifestUrl = String.fromEnvironment(
    'UPDATE_MANIFEST_URL',
    defaultValue: defaultUpdateManifestUrl,
  );

  static const String updateManifestFallbackUrls = String.fromEnvironment(
    'UPDATE_MANIFEST_FALLBACK_URLS',
    defaultValue: defaultUpdateManifestFallbackUrls,
  );

  static Uri? get updateManifestUri {
    if (updateManifestUrl.trim().isEmpty) {
      return null;
    }
    return Uri.tryParse(updateManifestUrl);
  }

  static List<Uri> get updateManifestFallbackUris {
    return parseUpdateManifestUris(updateManifestFallbackUrls);
  }

  static int get appVersionCode {
    final parts = appVersion.split('+');
    if (parts.length < 2) {
      return 1;
    }
    return int.tryParse(parts.last) ?? 1;
  }

  static bool get isConfigured => gitCommit != 'unknown';
}

List<Uri> parseUpdateManifestUris(String value) {
  return value
      .split(RegExp(r'[,;\n\r]+'))
      .map((part) => part.trim())
      .where((part) => part.isNotEmpty)
      .map(Uri.tryParse)
      .whereType<Uri>()
      .where((uri) => uri.hasScheme && uri.host.isNotEmpty)
      .toList(growable: false);
}
