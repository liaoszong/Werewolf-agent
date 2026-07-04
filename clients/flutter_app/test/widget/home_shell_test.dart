import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/app/werewolf_app.dart';
import 'package:werewolf_app/src/protocol/observer_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';

class FakeObserverApiClient extends ObserverApiClient {
  FakeObserverApiClient({this.runs = const []})
    : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

  final List<RunSummary> runs;

  @override
  Future<List<RunSummary>> listRuns() async => runs;
}

class FakeParticipantApiClient extends ParticipantApiClient {
  FakeParticipantApiClient()
    : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

  String? joinedRunId;
  final sseController = StreamController<ParticipantSseEvent>.broadcast();

  @override
  Future<ParticipantSession> join({
    required String runId,
    required String seatId,
    required String joinCode,
  }) async {
    joinedRunId = runId;
    return ParticipantSession(
      runId: runId,
      seatId: seatId,
      perspective: 'role:$seatId',
      token: 'token',
      reconnectCursor: 'event:0',
    );
  }

  @override
  Future<ParticipantState> state({
    required String runId,
    required String token,
  }) async {
    return ParticipantState.fromJson({
      'schema_version': 'p3c.participant_state.v1',
      'run_id': runId,
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'run_status': 'running',
      'projection': {'events': []},
      'open_action_window': null,
      'reconnect_cursor': 'event:1',
    });
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
  testWidgets('home defaults to Chinese and exposes bottom navigation', (
    tester,
  ) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('狼人杀观察席'), findsOneWidget);
    expect(find.text('首页'), findsOneWidget);
    expect(find.text('对局'), findsOneWidget);
    expect(find.text('房间'), findsOneWidget);
    expect(find.text('设置'), findsOneWidget);
    expect(find.text('Werewolf Agent'), findsNothing);
  });

  testWidgets('language toggle switches primary shell copy to English', (
    tester,
  ) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('EN'));
    await tester.pumpAndSettle();

    expect(find.text('Werewolf Observer'), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Matches'), findsOneWidget);
    expect(find.text('Room'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
  });

  testWidgets('settings exposes cloud and local observer presets', (
    tester,
  ) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('设置'));
    await tester.pumpAndSettle();

    expect(find.text('http://api.paleink.cc:8765'), findsOneWidget);
    expect(find.text('PaleInk 云服务器'), findsOneWidget);
    expect(find.text('本机开发'), findsOneWidget);

    await tester.tap(find.text('本机开发'));
    await tester.pumpAndSettle();

    expect(find.text('http://127.0.0.1:8765'), findsOneWidget);
  });

  testWidgets('matches tab lists observer runs and can join one', (
    tester,
  ) async {
    final participant = FakeParticipantApiClient();
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(
          runs: const [RunSummary(runId: 'run_1', status: 'running')],
        ),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: participant),
      ),
    );
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('对局'));
    await tester.pump();

    expect(find.text('run_1'), findsOneWidget);
    expect(find.text('进行中'), findsOneWidget);

    await tester.tap(find.text('加入此局'));
    await tester.pump();
    await tester.pump();

    expect(participant.joinedRunId, 'run_1');
    expect(find.text('你的席位是 P3'), findsOneWidget);

    await participant.sseController.close();
  });
}
