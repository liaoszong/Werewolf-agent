import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';
import 'package:werewolf_app/src/ui/composer_rail.dart';

ActionWindow _window(List<String> actions) => ActionWindow.fromJson({
      'schema_version': 'p3c.action_window.v1',
      'action_window_id': 'aw_1',
      'run_id': 'run_1',
      'seat_id': 'p3',
      'phase': 'day',
      'round': 1,
      'game_revision': 1,
      'opened_at_event_id': 'evt_1',
      'deadline_at': null,
      'allowed_actions': actions,
      'required': true,
      'default_on_timeout': 'pass',
      'status': 'open',
      'reconnect_cursor': 'event:1',
    });

void main() {
  testWidgets('speech window submits text', (tester) async {
    String? submitted;
    await tester.pumpWidget(TestHarness(
      child: ComposerRail(
        window: _window(['speech']),
        onSubmitSpeech: (text) async => submitted = text,
        onSubmitStructuredAction: (actionType, payload) async {},
      ),
    ));

    await tester.enterText(
      find.byKey(const Key('composer-text-input')),
      '我先听 P2 怎么说',
    );
    await tester.tap(find.byKey(const Key('composer-send-button')));
    await tester.pump();

    expect(submitted, '我先听 P2 怎么说');
  });

  testWidgets('vote window submits selected target', (tester) async {
    String? action;
    Map<String, dynamic>? payload;
    await tester.pumpWidget(TestHarness(
      child: ComposerRail(
        window: _window(['vote']),
        onSubmitSpeech: (_) async {},
        onSubmitStructuredAction: (type, body) async {
          action = type;
          payload = body;
        },
      ),
    ));

    await tester.tap(find.text('P2'));
    await tester.pump();
    await tester.tap(find.byKey(const Key('composer-confirm-button')));
    await tester.pump();

    expect(action, 'vote');
    expect(payload, {'target': 'p2'});
  });

  testWidgets('active composer can collapse to bottom handle', (tester) async {
    await tester.pumpWidget(TestHarness(
      child: ComposerRail(
        window: _window(['speech']),
        onSubmitSpeech: (_) async {},
        onSubmitStructuredAction: (actionType, payload) async {},
      ),
    ));

    await tester.tap(find.byKey(const Key('composer-collapse-button')));
    await tester.pump();

    expect(find.byKey(const Key('composer-collapsed-handle')), findsOneWidget);
    expect(find.byKey(const Key('composer-text-input')), findsNothing);
  });

  testWidgets('null window shows collapsed handle only', (tester) async {
    await tester.pumpWidget(TestHarness(
      child: ComposerRail(
        window: null,
        onSubmitSpeech: (_) async {},
        onSubmitStructuredAction: (actionType, payload) async {},
      ),
    ));

    expect(find.byKey(const Key('composer-collapsed-handle')), findsOneWidget);
    expect(find.byKey(const Key('composer-text-input')), findsNothing);
  });
}

class TestHarness extends StatelessWidget {
  const TestHarness({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => MaterialApp(home: Scaffold(body: child));
}
