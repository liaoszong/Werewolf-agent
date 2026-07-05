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
    expect(window.deadlineAt, DateTime.utc(2026, 7, 4));
    expect(window.defaultOnTimeout, 'pass');
  });

  test('parses participant state with null action window', () {
    final state = ParticipantState.fromJson(const {
      'schema_version': 'p3c.participant_state.v1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'run_status': 'running',
      'projection': {'events': []},
      'open_action_window': null,
      'reconnect_cursor': 'event:2',
    });

    expect(state.openActionWindow, isNull);
    expect(state.visibleEvents, isEmpty);
  });

  test('parses role-safe projection players proof snapshots and phase', () {
    final state = ParticipantState.fromJson(const {
      'schema_version': 'p3c.participant_state.v1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'run_status': 'running',
      'projection': {
        'contract_version': 'g2c.visibility.v1',
        'run_id': 'run_1',
        'perspective': 'role:p3',
        'view_kind': 'role',
        'players': [
          {
            'player_id': 'p1',
            'display_role': 'unknown',
            'display_team': 'unknown',
            'alive': true,
            'visibility': 'hidden',
          },
          {
            'player_id': 'p3',
            'display_role': 'seer',
            'display_team': 'villager',
            'alive': true,
            'visibility': 'self',
          },
          {
            'player_id': 'p5',
            'display_role': 'unknown',
            'display_team': 'unknown',
            'alive': false,
            'visibility': 'hidden',
          },
        ],
        'events': [
          {
            'event_id': 'rt1',
            'kind': 'game_event_emitted',
            'actor': 'p2',
            'phase': 'day',
            'round': 2,
            'payload': {'event_id': 'g_e1', 'type': 'player_speech'},
            'data': {'summary': 'P2 says P1 is suspicious.'},
          },
        ],
        'hidden_event_count': 4,
        'snapshots': [
          {
            'snapshot_name': 'role-p3-r2.json',
            'snapshot_type': 'role_projection',
            'visible': true,
            'round': 2,
            'phase': 'day',
            'player_id': 'p3',
          },
        ],
        'hidden_snapshot_count': 3,
        'proof': {
          'source': 'snapshots',
          'self_player_id': 'p3',
          'self_role': 'seer',
          'self_team': 'villager',
        },
      },
      'open_action_window': null,
      'reconnect_cursor': 'event:2',
    });

    expect(state.projectionEnvelope.players, hasLength(3));
    expect(state.projectionEnvelope.selfPlayer?.displayRole, 'seer');
    expect(state.projectionEnvelope.proof.selfRole, 'seer');
    expect(state.projectionEnvelope.visibleSnapshots.single.playerId, 'p3');
    expect(state.currentPhase, 'day');
    expect(state.currentRound, 2);
    expect(state.targetCandidateSeatIds, ['p1', 'p3']);
    expect(state.projectedEvents.single.displayKind, 'player_speech');
    expect(state.projectedEvents.single.text, 'P2 says P1 is suspicious.');
  });

  test('derives visible werewolf teammates from projection only', () {
    final state = ParticipantState.fromJson(const {
      'schema_version': 'p3c.participant_state.v1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'run_status': 'running',
      'projection': {
        'players': [
          {
            'player_id': 'p1',
            'display_role': 'werewolf',
            'display_team': 'werewolf',
            'alive': true,
            'visibility': 'team',
          },
          {
            'player_id': 'p2',
            'display_role': 'unknown',
            'display_team': 'unknown',
            'alive': true,
            'visibility': 'hidden',
          },
          {
            'player_id': 'p3',
            'display_role': 'werewolf',
            'display_team': 'werewolf',
            'alive': true,
            'visibility': 'self',
          },
        ],
        'proof': {
          'source': 'snapshots',
          'self_player_id': 'p3',
          'self_role': 'werewolf',
          'self_team': 'werewolf',
        },
      },
      'open_action_window': null,
      'reconnect_cursor': 'event:2',
    });

    final projection = state.projectionEnvelope;
    expect(projection.selfRole, 'werewolf');
    expect(projection.selfTeam, 'werewolf');
    expect(
      projection.visibleWerewolfTeammates.map((player) => player.playerId),
      ['p1'],
    );
  });
}
