import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:werewolf_app/src/protocol/observer_api_client.dart';

void main() {
  test('listProviderSpecs parses provider specs from profile schema', () async {
    final client = ObserverApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient((request) async {
        expect(request.url.path, '/api/profiles/schema');
        return http.Response(
          jsonEncode({
            'provider_specs': [
              {
                'id': 'deepseek',
                'label': 'DeepSeek',
                'default_base_url': 'https://api.deepseek.com',
                'requires_base_url': false,
                'default_models': ['deepseek-chat'],
              },
            ],
          }),
          200,
        );
      }),
    );

    final specs = await client.listProviderSpecs();

    expect(specs, hasLength(1));
    expect(specs.single.id, 'deepseek');
    expect(specs.single.defaultModels, ['deepseek-chat']);
  });

  test('saveProviderCredential posts key in JSON body only', () async {
    late http.Request captured;
    final client = ObserverApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient((request) async {
        captured = request;
        return http.Response(
          jsonEncode({
            'stored': ['deepseek'],
          }),
          200,
        );
      }),
    );

    await client.saveProviderCredential(
      provider: 'deepseek',
      apiKey: 'sk-test-secret',
      baseUrl: 'https://api.deepseek.com',
    );

    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/credentials');
    expect(captured.url.toString(), isNot(contains('sk-test-secret')));
    expect(captured.headers.toString(), isNot(contains('sk-test-secret')));
    expect(jsonDecode(captured.body), {
      'provider': 'deepseek',
      'api_key': 'sk-test-secret',
      'base_url': 'https://api.deepseek.com',
    });
  });

  test('fetchProviderModels returns model ids', () async {
    final client = ObserverApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient((request) async {
        expect(request.url.path, '/api/providers/deepseek/models');
        return http.Response(
          jsonEncode({
            'provider': 'deepseek',
            'models': ['deepseek-chat', 'deepseek-v4-flash'],
          }),
          200,
        );
      }),
    );

    final models = await client.fetchProviderModels('deepseek');

    expect(models, ['deepseek-chat', 'deepseek-v4-flash']);
  });

  test(
    'provider endpoint errors do not include response body secrets',
    () async {
      final client = ObserverApiClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        httpClient: MockClient((request) async {
          return http.Response(
            jsonEncode({
              'error': 'provider_unavailable',
              'debug': 'Bearer sk-test-secret',
            }),
            502,
          );
        }),
      );

      await expectLater(
        client.fetchProviderModels('deepseek'),
        throwsA(
          isA<ObserverApiError>()
              .having((e) => e.code, 'code', 'provider_unavailable')
              .having(
                (e) => e.toString(),
                'safe string',
                isNot(contains('sk-test-secret')),
              ),
        ),
      );
    },
  );

  test('clearProviderCredential calls provider delete endpoint', () async {
    late http.Request captured;
    final client = ObserverApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient((request) async {
        captured = request;
        return http.Response(jsonEncode({'cleared': 'deepseek'}), 200);
      }),
    );

    await client.clearProviderCredential('deepseek');

    expect(captured.method, 'DELETE');
    expect(captured.url.path, '/api/credentials/deepseek');
  });
}
