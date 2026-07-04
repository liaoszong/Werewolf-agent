import 'package:flutter/material.dart';

import '../protocol/observer_api_client.dart';
import '../protocol/participant_api_client.dart';
import '../screens/home_shell.dart';
import '../ui/app_theme.dart';
import 'app_settings.dart';
import 'app_strings.dart';
import 'session_controller.dart';

class WerewolfApp extends StatefulWidget {
  const WerewolfApp({
    super.key,
    this.settingsController,
    this.observerClientFactory,
    this.sessionControllerFactory,
  });

  final AppSettingsController? settingsController;
  final ObserverClientFactory? observerClientFactory;
  final SessionControllerFactory? sessionControllerFactory;

  @override
  State<WerewolfApp> createState() => _WerewolfAppState();
}

class _WerewolfAppState extends State<WerewolfApp> {
  late final AppSettingsController _settingsController;

  @override
  void initState() {
    super.initState();
    _settingsController = widget.settingsController ?? AppSettingsController();
  }

  @override
  void dispose() {
    if (widget.settingsController == null) {
      _settingsController.dispose();
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
            theme: WerewolfAppTheme.darkTheme(),
            home: HomeShell(
              settingsController: _settingsController,
              observerClientFactory:
                  widget.observerClientFactory ?? _defaultObserverClientFactory,
              sessionControllerFactory:
                  widget.sessionControllerFactory ?? _defaultSessionControllerFactory,
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
}
