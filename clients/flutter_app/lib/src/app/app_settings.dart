import 'package:flutter/foundation.dart';

enum AppLanguage { zh, en }

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
    Uri? baseUri,
    String seatId = 'p3',
    String joinCode = 'local-dev-code',
  }) : _language = language,
       _baseUri = baseUri ?? ObserverServerPreset.paleInkCloud.baseUri,
       _seatId = seatId,
       _joinCode = joinCode;

  AppLanguage _language;
  Uri _baseUri;
  String _seatId;
  String _joinCode;

  AppLanguage get language => _language;
  Uri get baseUri => _baseUri;
  String get seatId => _seatId;
  String get joinCode => _joinCode;

  void setLanguage(AppLanguage value) {
    if (_language == value) return;
    _language = value;
    notifyListeners();
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
