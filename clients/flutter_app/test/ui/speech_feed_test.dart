import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/ui/speech_feed.dart';

void main() {
  testWidgets('highlights seat and role words without coaching blocks', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SpeechFeed(
            events: [
              {
                'kind': 'player_speech',
                'actor': 'p5',
                'payload': {'message': 'P2 sounds like 狼人 to me.'},
              },
            ],
          ),
        ),
      ),
    );

    expect(find.textContaining('P2', findRichText: true), findsOneWidget);
    expect(find.textContaining('狼人', findRichText: true), findsOneWidget);
    expect(find.textContaining('投票意向', findRichText: true), findsNothing);
    expect(find.textContaining('重点', findRichText: true), findsNothing);
  });

  testWidgets('separates public events and own speech', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SpeechFeed(
            currentSeatId: 'p3',
            events: [
              {
                'kind': 'phase_changed',
                'actor': 'system',
                'payload': {'summary': '进入白天讨论。'},
              },
              {
                'kind': 'player_speech',
                'actor': 'p3',
                'round': 2,
                'phase': 'day',
                'payload': {'message': '我认为 P1 有狼人面。'},
              },
            ],
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('speech-system-pill')), findsOneWidget);
    expect(find.byKey(const Key('speech-event-bubble')), findsOneWidget);
    expect(find.textContaining('阶段变化'), findsOneWidget);
    expect(find.textContaining('第 2 轮'), findsOneWidget);
    expect(find.textContaining('P1', findRichText: true), findsOneWidget);
  });
}
