import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';

void main() {
  test('parses participant session', () {
    final session = ParticipantSession.fromJson(const {
      'schema_version': 'p3c.participant_session.v1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'participant_session_token': 'secret-token',
      'reconnect_cursor': 'event:4',
    });

    expect(session.runId, 'run_1');
    expect(session.seatId, 'p3');
    expect(session.token, 'secret-token');
    expect(session.reconnectCursor, 'event:4');
  });

  test('parses action window and detects text action', () {
    final window = ActionWindow.fromJson(const {
      'schema_version': 'p3c.action_window.v1',
      'action_window_id': 'aw_1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'phase': 'day',
      'round': 1,
      'game_revision': 7,
      'opened_at_event_id': 'evt_1',
      'deadline_at': '2026-07-04T00:00:00Z',
      'allowed_actions': ['speech', 'pass'],
      'required': false,
      'default_on_timeout': 'pass',
      'status': 'open',
      'reconnect_cursor': 'event:9',
    });

    expect(window.id, 'aw_1');
    expect(window.gameRevision, 7);
    expect(window.allowedActions, contains('speech'));
    expect(window.allowsTextInput, isTrue);
    expect(window.allowsStructuredChoice, isFalse);
  });

  test('parses participant state with null action window', () {
    final state = ParticipantState.fromJson(const {
      'schema_version': 'p3c.participant_state.v1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'run_status': 'running',
      'projection': {
        'events': [],
      },
      'open_action_window': null,
      'reconnect_cursor': 'event:2',
    });

    expect(state.openActionWindow, isNull);
    expect(state.visibleEvents, isEmpty);
  });
}
