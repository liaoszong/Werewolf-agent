import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/app/werewolf_app.dart';
import 'package:werewolf_app/src/protocol/observer_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/providers/provider_credential_store.dart';

class FakeObserverApiClient extends ObserverApiClient {
  FakeObserverApiClient() : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

  @override
  Future<List<RunSummary>> listRuns() async => const [];

  @override
  Future<List<ProviderSpecSummary>> listProviderSpecs() async => const [
    ProviderSpecSummary(
      id: 'deepseek',
      label: 'DeepSeek',
      defaultBaseUrl: 'https://api.deepseek.com',
      requiresBaseUrl: false,
      defaultModels: ['deepseek-chat'],
    ),
  ];
}

class FakeParticipantApiClient extends ParticipantApiClient {
  FakeParticipantApiClient()
    : super(baseUri: Uri.parse('http://127.0.0.1:8765'));
}

void main() {
  testWidgets('app starts at the localized home shell', (tester) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pump();

    expect(find.text('狼人杀观察席'), findsOneWidget);
    expect(find.text('首页'), findsOneWidget);
  });
}
