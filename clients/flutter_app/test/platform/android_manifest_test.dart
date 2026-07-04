import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('release Android manifest allows local observer network access', () {
    final manifest = File('android/app/src/main/AndroidManifest.xml')
        .readAsStringSync();

    expect(
      manifest,
      contains('android.permission.INTERNET'),
      reason: 'Release APK must be able to call the observer server.',
    );
    expect(
      manifest,
      contains('android:usesCleartextTraffic="true"'),
      reason: 'P3-E local-network slice uses http:// LAN observer URLs.',
    );
  });
}
