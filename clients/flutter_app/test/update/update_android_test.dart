import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/update/update_android.dart';
import 'package:werewolf_app/src/update/update_models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const channel = MethodChannel('werewolf_app/apk_installer');

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
  });

  test(
    'MethodChannelApkArchiveValidator maps native archive inspection',
    () async {
      final calls = <MethodCall>[];
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async {
            calls.add(call);
            return {
              'packageName': 'io.werewolfagent.werewolf_app',
              'versionCode': 7,
              'signingCertificateSha256':
                  '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
              'isSignatureCompatible': true,
            };
          });

      final result = await const MethodChannelApkArchiveValidator().inspect(
        File('werewolf.apk'),
      );

      expect(calls.single.method, 'inspectApkArchive');
      expect(calls.single.arguments, {'path': 'werewolf.apk'});
      expect(result.packageName, 'io.werewolfagent.werewolf_app');
      expect(result.versionCode, 7);
      expect(result.isSignatureCompatible, isTrue);
    },
  );

  test('ApkArchiveValidationResult rejects incomplete native payloads', () {
    expect(
      () => ApkArchiveValidationResult.fromJson({
        'packageName': 'io.werewolfagent.werewolf_app',
        'versionCode': 7,
        'signingCertificateSha256':
            '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
      }),
      throwsA(isA<FormatException>()),
    );
  });
}
