import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';
import 'package:werewolf_app/src/screens/connect_screen.dart';

class ImmediateApiClient extends ParticipantApiClient {
  ImmediateApiClient() : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

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
    return ParticipantState.fromJson(const {
      'schema_version': 'p3c.participant_state.v1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'perspective': 'role:p3',
      'run_status': 'running',
      'projection': {'events': []},
      'open_action_window': null,
      'reconnect_cursor': 'event:1',
    });
  }
}

void main() {
  testWidgets('join shows identity confirmation before live room',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: ConnectScreen(
        controllerFactory: (_) => SessionController(
          participantApi: ImmediateApiClient(),
        ),
      ),
    ));

    await tester.enterText(
      find.byKey(const Key('base-url-input')),
      'http://127.0.0.1:8765',
    );
    await tester.enterText(find.byKey(const Key('run-id-input')), 'run_1');
    await tester.enterText(find.byKey(const Key('seat-id-input')), 'p3');
    await tester.enterText(
      find.byKey(const Key('join-code-input')),
      'local-dev-code',
    );
    await tester.tap(find.text('加入席位'));
    await tester.pumpAndSettle();

    expect(find.text('你的席位是 P3'), findsOneWidget);
    expect(find.text('参与者视角，不是上帝视角'), findsOneWidget);
  });
}
