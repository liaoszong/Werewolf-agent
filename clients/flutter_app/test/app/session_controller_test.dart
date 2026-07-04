import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';

class FakeParticipantApiClient extends ParticipantApiClient {
  FakeParticipantApiClient({this.allowedActions = const ['speech']})
      : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

  final List<String> allowedActions;
  int stateCalls = 0;
  Map<String, dynamic>? lastSubmit;
  final sseController = StreamController<ParticipantSseEvent>.broadcast();

  @override
  Future<ParticipantSession> join({
    required String runId,
    required String seatId,
    required String joinCode,
  }) async {
    return const ParticipantSession(
      runId: 'run_1',
      seatId: 'p3',
      perspective: 'role:p3',
      token: 'token',
      reconnectCursor: 'event:0',
    );
  }

  @override
  Future<ParticipantState> state({
    required String runId,
    required String token,
  }) async {
    stateCalls += 1;
    return ParticipantState.fromJson({
      'schema_version': 'p3c.participant_state.v1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'run_status': 'running',
      'projection': {'events': []},
      'open_action_window': {
        'schema_version': 'p3c.action_window.v1',
        'action_window_id': 'aw_1',
        'run_id': 'run_1',
        'seat_id': 'p3',
        'phase': 'day',
        'round': 1,
        'game_revision': 7,
        'opened_at_event_id': 'evt_1',
        'deadline_at': '2026-07-04T00:00:00Z',
        'allowed_actions': allowedActions,
        'required': true,
        'default_on_timeout': 'pass',
        'status': 'open',
        'reconnect_cursor': 'event:4',
      },
      'reconnect_cursor': 'event:4',
    });
  }

  @override
  Future<ParticipantActionResult> submitAction({
    required String runId,
    required String token,
    required Map<String, dynamic> payload,
  }) async {
    lastSubmit = payload;
    return const ParticipantActionResult(
      status: 'accepted',
      actionWindowId: 'aw_1',
      reconnectCursor: 'event:5',
      acceptedEventId: 'evt_5',
      gameRevision: 8,
    );
  }

  @override
  Stream<ParticipantSseEvent> events({
    required String runId,
    required String token,
    required String cursor,
  }) {
    return sseController.stream;
  }
}

void main() {
  test('join loads role-safe participant state', () async {
    final api = FakeParticipantApiClient();
    final controller = SessionController(participantApi: api);

    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    expect(controller.connectionStatus, ConnectionStatus.connected);
    expect(controller.session?.seatId, 'p3');
    expect(controller.state?.openActionWindow?.id, 'aw_1');
  });

  test('submitSpeech uses current window identity and refreshes state', () async {
    final api = FakeParticipantApiClient();
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    await controller.submitSpeech('I want to hear from P2.');

    expect(api.lastSubmit?['action_window_id'], 'aw_1');
    expect(api.lastSubmit?['game_revision'], 7);
    expect(api.lastSubmit?['action_type'], 'speech');
    expect(api.lastSubmit?['payload'], {'text': 'I want to hear from P2.'});
    expect(api.lastSubmit?['idempotency_key'], isA<String>());
    expect(api.stateCalls, 2);
  });

  test('submitSpeech uses final_words when that is the text window', () async {
    final api = FakeParticipantApiClient(allowedActions: const ['final_words']);
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    await controller.submitSpeech('最后说一句。');

    expect(api.lastSubmit?['action_type'], 'final_words');
    expect(api.lastSubmit?['payload'], {'text': '最后说一句。'});
  });

  test('recoverAfterDisconnect reloads participant state', () async {
    final api = FakeParticipantApiClient();
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    await controller.recoverAfterDisconnect();

    expect(controller.connectionStatus, ConnectionStatus.connected);
    expect(api.stateCalls, 2);
  });

  test('join starts participant SSE and refreshes state on room events',
      () async {
    final api = FakeParticipantApiClient();
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    api.sseController.add(const ParticipantSseEvent(
      name: 'action_window_opened',
      data: {'action_window_id': 'aw_2'},
    ));
    await Future<void>.delayed(Duration.zero);

    expect(api.stateCalls, 2);
    await api.sseController.close();
  });
}
