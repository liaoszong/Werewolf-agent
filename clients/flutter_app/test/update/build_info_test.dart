import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/build_info.dart';

void main() {
  test('uses local defaults without a hardcoded personal update source', () {
    expect(BuildInfo.appVersion, '1.0.0+1');
    expect(BuildInfo.appVersionCode, 1);
    expect(BuildInfo.updateChannel, 'production');
    expect(BuildInfo.updateApplicationId, 'io.werewolfagent.werewolf_app');
    expect(BuildInfo.updateManifestUri, isNull);
    expect(BuildInfo.updateManifestFallbackUris, isEmpty);
  });

  test('parses fallback manifest URLs from common separators', () {
    expect(
      parseUpdateManifestUris(
        ' https://mirror.example.com/latest.json ; invalid ;\n'
        'https://cdn.example.com/latest.json,',
      ),
      [
        Uri.parse('https://mirror.example.com/latest.json'),
        Uri.parse('https://cdn.example.com/latest.json'),
      ],
    );
  });
}
