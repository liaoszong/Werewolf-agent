import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/screens/live_room_screen.dart';

class NeverCalledApi extends ParticipantApiClient {
  NeverCalledApi() : super(baseUri: Uri.parse('http://127.0.0.1:8765'));
}

void main() {
  testWidgets('live room shows role-safe status and speech feed',
      (tester) async {
    final controller = SessionController(participantApi: NeverCalledApi());
    await tester.pumpWidget(
      TestApp(child: LiveRoomScreen(controller: controller)),
    );

    expect(find.textContaining('你的视角'), findsOneWidget);
    expect(find.textContaining('等待可见房间事件'), findsOneWidget);
  });
}

class TestApp extends StatelessWidget {
  const TestApp({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => MaterialApp(home: child);
}
