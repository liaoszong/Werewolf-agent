import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/ui/speech_feed.dart';

void main() {
  testWidgets('highlights seat and role words without coaching blocks',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: SpeechFeed(events: [
          {
            'kind': 'player_speech',
            'actor': 'p5',
            'payload': {'message': 'P2 sounds like 狼人 to me.'},
          },
        ]),
      ),
    ));

    expect(find.textContaining('P2', findRichText: true), findsOneWidget);
    expect(find.textContaining('狼人', findRichText: true), findsOneWidget);
    expect(find.textContaining('投票意向', findRichText: true), findsNothing);
    expect(find.textContaining('重点', findRichText: true), findsNothing);
  });
}
