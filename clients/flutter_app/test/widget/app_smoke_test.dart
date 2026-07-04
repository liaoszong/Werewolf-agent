import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/werewolf_app.dart';

void main() {
  testWidgets('app starts at the connection screen', (tester) async {
    await tester.pumpWidget(const WerewolfApp());

    expect(find.text('Werewolf Agent'), findsOneWidget);
  });
}
