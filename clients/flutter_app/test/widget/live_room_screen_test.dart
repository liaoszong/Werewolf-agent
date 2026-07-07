import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';
import 'package:werewolf_app/src/screens/live_room_screen.dart';

class NeverCalledApi extends ParticipantApiClient {
  NeverCalledApi() : super(baseUri: Uri.parse('http://127.0.0.1:8765'));
}

void main() {
  testWidgets('live room shows role-safe status and speech feed', (
    tester,
  ) async {
    final controller = SessionController(participantApi: NeverCalledApi());
    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );

    expect(find.textContaining('你的视角'), findsOneWidget);
    expect(find.textContaining('等待可见房间事件'), findsOneWidget);
  });

  testWidgets('live room shows seat structure and private seat info', (
    tester,
  ) async {
    final controller = SessionController(participantApi: NeverCalledApi())
      ..connectionStatus = ConnectionStatus.connected
      ..state = ParticipantState.fromJson(const {
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
              'actor': 'p1',
              'phase': 'day',
              'round': 2,
              'payload': {'event_id': 'g_e01', 'type': 'player_speech'},
              'data': {'summary': 'P1 发言。'},
            },
          ],
          'hidden_event_count': 2,
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

    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );

    expect(find.byKey(const Key('seat-strip')), findsOneWidget);
    expect(find.byKey(const Key('private-info-panel')), findsOneWidget);
    expect(find.byKey(const Key('phase-status-panel')), findsOneWidget);
    expect(find.textContaining('预言家'), findsWidgets);
    expect(find.textContaining('第 2 轮'), findsWidgets);
    expect(find.text('P5'), findsOneWidget);
  });

  testWidgets('waiting status is compact and does not spell connection label', (
    tester,
  ) async {
    final controller = SessionController(participantApi: NeverCalledApi())
      ..connectionStatus = ConnectionStatus.connected
      ..state = ParticipantState.fromJson(const {
        'schema_version': 'p3c.participant_state.v1',
        'run_id': 'run_1',
        'seat_id': 'p3',
        'perspective': 'role:p3',
        'run_status': 'running',
        'projection': {
          'players': [
            {
              'player_id': 'p3',
              'display_role': 'seer',
              'display_team': 'villager',
              'alive': true,
              'visibility': 'self',
            },
          ],
          'proof': {
            'source': 'snapshots',
            'self_player_id': 'p3',
            'self_role': 'seer',
            'self_team': 'villager',
          },
          'events': [],
        },
        'open_action_window': {
          'schema_version': 'p3c.action_window.v1',
          'action_window_id': 'aw_1',
          'run_id': 'run_1',
          'seat_id': 'p3',
          'phase': 'day_speech',
          'round': 2,
          'game_revision': 7,
          'opened_at_event_id': 'evt_1',
          'deadline_at': '2026-07-04T00:00:00Z',
          'allowed_actions': ['speech', 'pass'],
          'required': true,
          'default_on_timeout': 'pass',
          'status': 'open',
          'reconnect_cursor': 'event:4',
        },
        'reconnect_cursor': 'event:4',
      });

    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );

    expect(find.byKey(const Key('room-status-island')), findsOneWidget);
    expect(find.byKey(const Key('connection-status-dot')), findsOneWidget);
    expect(find.text('等待你操作'), findsOneWidget);
    expect(find.text('已连接'), findsNothing);

    final screenCenterX = tester.getSize(find.byType(LiveRoomScreen)).width / 2;
    final islandCenterX = tester
        .getCenter(find.byKey(const Key('room-status-island')))
        .dx;
    expect((islandCenterX - screenCenterX).abs(), lessThanOrEqualTo(2));
  });

  testWidgets('stub action window without role projection is not actionable', (
    tester,
  ) async {
    final controller = SessionController(participantApi: NeverCalledApi())
      ..connectionStatus = ConnectionStatus.connected
      ..state = ParticipantState.fromJson(const {
        'schema_version': 'p3c.participant_state.v1',
        'run_id': 'run_1',
        'seat_id': 'p3',
        'perspective': 'role:p3',
        'run_status': 'running',
        'projection': {
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
              'display_role': 'unknown',
              'display_team': 'unknown',
              'alive': true,
              'visibility': 'hidden',
            },
          ],
          'events': [],
        },
        'open_action_window': {
          'schema_version': 'p3c.action_window.v1',
          'action_window_id': 'aw_stub',
          'run_id': 'run_1',
          'seat_id': 'p3',
          'phase': 'day_speech',
          'round': 1,
          'game_revision': 0,
          'opened_at_event_id': 'event:0',
          'deadline_at': '2026-07-04T00:00:00Z',
          'allowed_actions': ['speech', 'pass'],
          'required': true,
          'default_on_timeout': 'pass',
          'status': 'open',
          'reconnect_cursor': 'event:0',
        },
        'reconnect_cursor': 'event:0',
      });

    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );

    expect(find.text('房间尚未准备好'), findsOneWidget);
    expect(find.text('等待你操作'), findsNothing);
    expect(find.byKey(const Key('composer-text-input')), findsNothing);
    expect(find.byKey(const Key('composer-collapsed-handle')), findsOneWidget);
  });

  testWidgets('empty feed placeholder hides while keyboard is open', (
    tester,
  ) async {
    tester.view.viewInsets = const FakeViewPadding(bottom: 320);
    addTearDown(tester.view.resetViewInsets);
    final controller = SessionController(participantApi: NeverCalledApi())
      ..connectionStatus = ConnectionStatus.connected
      ..state = ParticipantState.fromJson(const {
        'schema_version': 'p3c.participant_state.v1',
        'run_id': 'run_1',
        'seat_id': 'p3',
        'perspective': 'role:p3',
        'run_status': 'running',
        'projection': {
          'players': [
            {
              'player_id': 'p3',
              'display_role': 'seer',
              'display_team': 'villager',
              'alive': true,
              'visibility': 'self',
            },
          ],
          'proof': {
            'source': 'snapshots',
            'self_player_id': 'p3',
            'self_role': 'seer',
            'self_team': 'villager',
          },
          'events': [],
        },
        'open_action_window': {
          'schema_version': 'p3c.action_window.v1',
          'action_window_id': 'aw_1',
          'run_id': 'run_1',
          'seat_id': 'p3',
          'phase': 'day_speech',
          'round': 1,
          'game_revision': 1,
          'opened_at_event_id': 'evt_1',
          'deadline_at': '2026-07-04T00:00:00Z',
          'allowed_actions': ['speech', 'pass'],
          'required': true,
          'default_on_timeout': 'pass',
          'status': 'open',
          'reconnect_cursor': 'event:1',
        },
        'reconnect_cursor': 'event:1',
      });

    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );

    expect(find.byKey(const Key('composer-text-input')), findsOneWidget);
    expect(find.textContaining('等待可见房间事件'), findsNothing);
  });

  testWidgets('live room disables stale action window when session expired', (
    tester,
  ) async {
    final controller = SessionController(participantApi: NeverCalledApi())
      ..connectionStatus = ConnectionStatus.sessionExpired
      ..lastError = 'Missing or invalid participant session'
      ..state = ParticipantState.fromJson(const {
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
          'phase': 'day_speech',
          'round': 2,
          'game_revision': 7,
          'opened_at_event_id': 'evt_1',
          'deadline_at': '2026-07-04T00:00:00Z',
          'allowed_actions': ['speech', 'pass'],
          'required': true,
          'default_on_timeout': 'pass',
          'status': 'open',
          'reconnect_cursor': 'event:4',
        },
        'reconnect_cursor': 'event:4',
      });

    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );

    expect(find.byKey(const Key('composer-text-input')), findsNothing);
    expect(find.byKey(const Key('composer-collapsed-handle')), findsOneWidget);
    expect(find.text('Missing or invalid participant session'), findsOneWidget);
    expect(find.text('等待你操作'), findsNothing);
  });

  testWidgets('live room opens role notice dialog with werewolf teammates', (
    tester,
  ) async {
    final controller = SessionController(participantApi: NeverCalledApi())
      ..connectionStatus = ConnectionStatus.connected
      ..state = ParticipantState.fromJson(const {
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
              'player_id': 'p3',
              'display_role': 'werewolf',
              'display_team': 'werewolf',
              'alive': true,
              'visibility': 'self',
            },
            {
              'player_id': 'p6',
              'display_role': 'unknown',
              'display_team': 'unknown',
              'alive': true,
              'visibility': 'hidden',
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

    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('role-notice-dialog')), findsOneWidget);
    expect(find.textContaining('你的身份'), findsWidgets);
    expect(find.text('狼人'), findsWidgets);
    expect(find.text('狼人同伴'), findsOneWidget);
    expect(find.text('P1'), findsOneWidget);

    await tester.tap(find.text('进入房间'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('role-notice-dialog')), findsNothing);
    expect(find.byKey(const Key('room-status-island')), findsOneWidget);
  });
}

class TestApp extends StatelessWidget {
  const TestApp({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => MaterialApp(home: child);
}
