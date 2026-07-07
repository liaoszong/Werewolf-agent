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

  test(
    'provider endpoints send owner token without leaking provider key',
    () async {
      final seen = <String, String>{};
      final client = ObserverApiClient(
        baseUri: Uri.parse('http://127.0.0.1:8765'),
        ownerToken: 'owner-secret',
        httpClient: MockClient((request) async {
          seen['${request.method} ${request.url.path}'] =
              request.headers['Authorization'] ?? '';
          return http.Response(
            request.url.path.endsWith('/models')
                ? jsonEncode({'provider': 'deepseek', 'models': <String>[]})
                : jsonEncode({'ok': true}),
            200,
          );
        }),
      );

      await client.saveProviderCredential(
        provider: 'deepseek',
        apiKey: 'sk-test-secret',
      );
      await client.fetchProviderModels('deepseek');
      await client.clearProviderCredential('deepseek');

      expect(seen['POST /api/credentials'], 'Bearer owner-secret');
      expect(seen['GET /api/providers/deepseek/models'], 'Bearer owner-secret');
      expect(seen['DELETE /api/credentials/deepseek'], 'Bearer owner-secret');
      expect(seen.toString(), isNot(contains('sk-test-secret')));
    },
  );

  test('createParticipantRun posts human seat with owner token', () async {
    late http.Request captured;
    final client = ObserverApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      ownerToken: 'owner-secret',
      httpClient: MockClient((request) async {
        captured = request;
        return http.Response(
          jsonEncode({
            'run_id': 'fake_run_123',
            'participant': {'seat_id': 'p3'},
          }),
          202,
        );
      }),
    );

    final runId = await client.createParticipantRun(seatId: 'p3');

    expect(runId, 'fake_run_123');
    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/runs');
    expect(captured.headers['Authorization'], 'Bearer owner-secret');
    expect(jsonDecode(captured.body), {
      'participant': {'seat_id': 'p3'},
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
