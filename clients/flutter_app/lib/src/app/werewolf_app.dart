import 'package:flutter/material.dart';

import '../protocol/observer_api_client.dart';
import '../protocol/participant_api_client.dart';
import '../screens/home_shell.dart';
import '../ui/app_theme.dart';
import '../update/update_android.dart';
import '../update/update_models.dart';
import '../update/update_repository.dart';
import '../update/update_service.dart';
import 'app_settings.dart';
import 'app_strings.dart';
import 'build_info.dart';
import 'session_controller.dart';

class WerewolfApp extends StatefulWidget {
  const WerewolfApp({
    super.key,
    this.settingsController,
    this.updateRepository,
    this.observerClientFactory,
    this.sessionControllerFactory,
  });

  final AppSettingsController? settingsController;
  final UpdateRepository? updateRepository;
  final ObserverClientFactory? observerClientFactory;
  final SessionControllerFactory? sessionControllerFactory;

  @override
  State<WerewolfApp> createState() => _WerewolfAppState();
}

class _WerewolfAppState extends State<WerewolfApp> {
  late final AppSettingsController _settingsController;
  late final UpdateRepository _updateRepository;

  @override
  void initState() {
    super.initState();
    _settingsController = widget.settingsController ?? AppSettingsController();
    _updateRepository = widget.updateRepository ?? _defaultUpdateRepository();
  }

  @override
  void dispose() {
    if (widget.settingsController == null) {
      _settingsController.dispose();
    }
    if (widget.updateRepository == null) {
      _updateRepository.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _settingsController,
      builder: (context, _) {
        final strings = AppStrings.forLanguage(_settingsController.language);
        return AppLanguageScope(
          controller: _settingsController,
          child: MaterialApp(
            title: strings.appTitle,
            debugShowCheckedModeBanner: false,
            theme: WerewolfAppTheme.themeFor(_settingsController.appearance),
            home: HomeShell(
              settingsController: _settingsController,
              updateRepository: _updateRepository,
              observerClientFactory:
                  widget.observerClientFactory ?? _defaultObserverClientFactory,
              sessionControllerFactory:
                  widget.sessionControllerFactory ??
                  _defaultSessionControllerFactory,
            ),
          ),
        );
      },
    );
  }

  ObserverApiClient _defaultObserverClientFactory(Uri baseUri) {
    return ObserverApiClient(baseUri: baseUri);
  }

  SessionController _defaultSessionControllerFactory(Uri baseUri) {
    return SessionController(
      participantApi: ParticipantApiClient(baseUri: baseUri),
    );
  }

  UpdateRepository _defaultUpdateRepository() {
    final apkInstaller = MethodChannelUpdateApkInstaller();
    return UpdateRepository(
      service: UpdateService(
        manifestClient: HttpUpdateManifestClient(),
        metadataClient: HttpUpdateBuildMetadataClient(),
        downloader: HttpUpdateApkDownloader(),
        archiveValidator: const MethodChannelApkArchiveValidator(),
        installer: apkInstaller,
      ),
      manifestUri: BuildInfo.updateManifestUri,
      manifestFallbackUris: BuildInfo.updateManifestFallbackUris,
      runtimeConfig: UpdateRuntimeConfig(
        channel: BuildInfo.updateChannel,
        applicationId: BuildInfo.updateApplicationId,
        currentVersionCode: BuildInfo.appVersionCode,
      ),
      cacheDirectoryProvider: apkInstaller.updateCacheDirectory,
    );
  }
}
