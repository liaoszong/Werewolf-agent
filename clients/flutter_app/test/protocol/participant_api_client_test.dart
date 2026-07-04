import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';

void main() {
  test('join posts seat and join code', () async {
    late http.Request captured;
    final client = ParticipantApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient((request) async {
        captured = request;
        return http.Response(jsonEncode({
          'schema_version': 'p3c.participant_session.v1',
          'run_id': 'run_1',
          'seat_id': 'p3',
          'perspective': 'role:p3',
          'participant_session_token': 'token',
          'reconnect_cursor': 'event:0',
        }), 200);
      }),
    );

    final session = await client.join(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/runs/run_1/participants/join');
    expect(jsonDecode(captured.body), {
      'seat_id': 'p3',
      'join_code': 'local-dev-code',
    });
    expect(session.token, 'token');
  });

  test('state sends bearer token', () async {
    late String? auth;
    final client = ParticipantApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient((request) async {
        auth = request.headers['Authorization'];
        return http.Response(jsonEncode({
          'schema_version': 'p3c.participant_state.v1',
          'run_id': 'run_1',
          'seat_id': 'p3',
          'perspective': 'role:p3',
          'run_status': 'running',
          'projection': {'events': []},
          'open_action_window': null,
          'reconnect_cursor': 'event:1',
        }), 200);
      }),
    );

    final state = await client.state(runId: 'run_1', token: 'token');

    expect(auth, 'Bearer token');
    expect(state.perspective, 'role:p3');
  });

  test('submit throws participant api error envelope', () async {
    final client = ParticipantApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient((request) async {
        return http.Response(jsonEncode({
          'schema_version': 'p3c.error.v1',
          'error_code': 'stale_game_revision',
          'message': 'Submitted game_revision is not current',
          'reconnect_cursor': 'event:9',
        }), 409);
      }),
    );

    await expectLater(
      client.submitAction(
        runId: 'run_1',
        token: 'token',
        payload: const {'action_type': 'speech'},
      ),
      throwsA(isA<ParticipantApiError>()
          .having((e) => e.errorCode, 'errorCode', 'stale_game_revision')
          .having((e) => e.reconnectCursor, 'reconnectCursor', 'event:9')),
    );
  });

  test('events parses named SSE frames', () async {
    final stream = Stream<List<int>>.fromIterable([
      utf8.encode('event: run_status\n'),
      utf8.encode('data: {"run_id":"run_1","status":"running"}\n\n'),
      utf8.encode('event: action_window_opened\n'),
      utf8.encode('data: {"action_window_id":"aw_1"}\n\n'),
    ]);
    final client = ParticipantApiClient(
      baseUri: Uri.parse('http://127.0.0.1:8765'),
      httpClient: MockClient.streaming((request, bodyStream) async {
        return http.StreamedResponse(stream, 200);
      }),
    );

    final events = await client
        .events(runId: 'run_1', token: 'token', cursor: 'event:0')
        .toList();

    expect(events.map((e) => e.name), ['run_status', 'action_window_opened']);
  });
}
