import 'package:flutter/foundation.dart';

enum AppLanguage { zh, en }

enum AppAppearance { night, day }

const hostedObserverBaseUriString = 'http://api.paleink.cc:8765';
const localObserverBaseUriString = 'http://127.0.0.1:8765';

enum ObserverServerPreset { paleInkCloud, localDev }

extension ObserverServerPresetData on ObserverServerPreset {
  Uri get baseUri {
    return switch (this) {
      ObserverServerPreset.paleInkCloud => Uri.parse(
        hostedObserverBaseUriString,
      ),
      ObserverServerPreset.localDev => Uri.parse(localObserverBaseUriString),
    };
  }
}

class AppSettingsController extends ChangeNotifier {
  AppSettingsController({
    AppLanguage language = AppLanguage.zh,
    AppAppearance appearance = AppAppearance.night,
    Uri? baseUri,
    String seatId = 'p3',
    String joinCode = 'local-dev-code',
  }) : _language = language,
       _appearance = appearance,
       _baseUri = baseUri ?? ObserverServerPreset.paleInkCloud.baseUri,
       _seatId = seatId,
       _joinCode = joinCode;

  AppLanguage _language;
  AppAppearance _appearance;
  Uri _baseUri;
  String _seatId;
  String _joinCode;

  AppLanguage get language => _language;
  AppAppearance get appearance => _appearance;
  Uri get baseUri => _baseUri;
  String get seatId => _seatId;
  String get joinCode => _joinCode;

  void setLanguage(AppLanguage value) {
    if (_language == value) return;
    _language = value;
    notifyListeners();
  }

  void setAppearance(AppAppearance value) {
    if (_appearance == value) return;
    _appearance = value;
    notifyListeners();
  }

  void toggleAppearance() {
    setAppearance(
      _appearance == AppAppearance.night
          ? AppAppearance.day
          : AppAppearance.night,
    );
  }

  void setBaseUri(Uri value) {
    if (_baseUri == value) return;
    _baseUri = value;
    notifyListeners();
  }

  void setSeatId(String value) {
    final normalized = value.trim().toLowerCase();
    if (normalized.isEmpty || _seatId == normalized) return;
    _seatId = normalized;
    notifyListeners();
  }

  void setJoinCode(String value) {
    final normalized = value.trim();
    if (normalized.isEmpty || _joinCode == normalized) return;
    _joinCode = normalized;
    notifyListeners();
  }
}
