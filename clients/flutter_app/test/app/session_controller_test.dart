import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';

class FakeParticipantApiClient extends ParticipantApiClient {
  FakeParticipantApiClient({
    this.allowedActions = const ['speech'],
    this.submitGate,
    this.submitError,
  }) : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

  final List<String> allowedActions;
  final Completer<void>? submitGate;
  final ParticipantApiError? submitError;
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
    await submitGate?.future;
    final error = submitError;
    if (error != null) throw error;
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

  test(
    'submitSpeech uses current window identity and refreshes state',
    () async {
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
    },
  );

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

  test('submitSpeech uses response when that is the text window', () async {
    final api = FakeParticipantApiClient(allowedActions: const ['response']);
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    await controller.submitSpeech('我回应 P2。');

    expect(api.lastSubmit?['action_type'], 'response');
    expect(api.lastSubmit?['payload'], {'text': '我回应 P2。'});
  });

  test('submitSpeech exposes in-flight action state', () async {
    final gate = Completer<void>();
    final api = FakeParticipantApiClient(submitGate: gate);
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    final submit = controller.submitSpeech('我先说。');
    await Future<void>.delayed(Duration.zero);

    expect(controller.isSubmittingAction, isTrue);

    gate.complete();
    await submit;

    expect(controller.isSubmittingAction, isFalse);
  });

  test('submit rejection refreshes state and preserves server message', () async {
    final api = FakeParticipantApiClient(
      submitError: ParticipantApiError(
        statusCode: 422,
        errorCode: 'illegal_action',
        message: 'Target is not legal for this action window.',
        reconnectCursor: 'event:9',
      ),
    );
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    await controller.submitStructuredAction(
      actionType: 'vote',
      payload: const {'target': 'p1'},
    );

    expect(api.stateCalls, 2);
    expect(controller.connectionStatus, ConnectionStatus.connected);
    expect(controller.lastError, 'Target is not legal for this action window.');
  });

  test('submit missing session marks session expired', () async {
    final api = FakeParticipantApiClient(
      submitError: ParticipantApiError(
        statusCode: 401,
        errorCode: 'missing_or_invalid_session',
        message: 'Missing or invalid participant session',
      ),
    );
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    await controller.submitSpeech('still here?');

    expect(controller.connectionStatus, ConnectionStatus.sessionExpired);
    expect(controller.lastError, 'Missing or invalid participant session');
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

  test(
    'join starts participant SSE and refreshes state on room events',
    () async {
      final api = FakeParticipantApiClient();
      final controller = SessionController(participantApi: api);
      await controller.joinAndLoad(
        runId: 'run_1',
        seatId: 'p3',
        joinCode: 'local-dev-code',
      );

      api.sseController.add(
        const ParticipantSseEvent(
          name: 'action_window_opened',
          data: {'action_window_id': 'aw_2'},
        ),
      );
      await Future<void>.delayed(Duration.zero);

      expect(api.stateCalls, 2);
      await api.sseController.close();
    },
  );

  test(
    'participant SSE state-change events refresh current state',
    () async {
      final api = FakeParticipantApiClient();
      final controller = SessionController(participantApi: api);
      await controller.joinAndLoad(
        runId: 'run_1',
        seatId: 'p3',
        joinCode: 'local-dev-code',
      );

      const eventNames = [
        'participant_projection_updated',
        'action_accepted',
        'action_rejected',
        'action_window_timed_out',
      ];
      for (final name in eventNames) {
        api.sseController.add(ParticipantSseEvent(name: name, data: const {}));
        await Future<void>.delayed(Duration.zero);
      }

      expect(api.stateCalls, 1 + eventNames.length);
      await api.sseController.close();
    },
  );

  test('participant SSE action rejection exposes server message', () async {
    final api = FakeParticipantApiClient();
    final controller = SessionController(participantApi: api);
    await controller.joinAndLoad(
      runId: 'run_1',
      seatId: 'p3',
      joinCode: 'local-dev-code',
    );

    api.sseController.add(
      const ParticipantSseEvent(
        name: 'action_rejected',
        data: {'message': 'Server rejected this target.'},
      ),
    );
    await Future<void>.delayed(Duration.zero);

    expect(api.stateCalls, 2);
    expect(controller.lastError, 'Server rejected this target.');
    await api.sseController.close();
  });
}
