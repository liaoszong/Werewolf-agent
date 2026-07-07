import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:werewolf_app/src/app/session_controller.dart';
import 'package:werewolf_app/src/app/werewolf_app.dart';
import 'package:werewolf_app/src/protocol/observer_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_api_client.dart';
import 'package:werewolf_app/src/protocol/participant_models.dart';
import 'package:werewolf_app/src/providers/provider_credential_store.dart';

class FakeObserverApiClient extends ObserverApiClient {
  FakeObserverApiClient({
    this.runs = const [],
    this.providerSpecs = _defaultProviderSpecs,
    this.providerModels = const ['deepseek-chat', 'deepseek-v4-flash'],
    this.providerSaveError,
  }) : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

  final List<RunSummary> runs;
  final List<ProviderSpecSummary> providerSpecs;
  final List<String> providerModels;
  final ObserverApiError? providerSaveError;
  String? savedProvider;
  String? savedApiKey;
  String? savedBaseUrl;
  String? clearedProvider;

  static const _defaultProviderSpecs = [
    ProviderSpecSummary(
      id: 'deepseek',
      label: 'DeepSeek',
      defaultBaseUrl: 'https://api.deepseek.com',
      requiresBaseUrl: false,
      defaultModels: ['deepseek-chat'],
    ),
    ProviderSpecSummary(
      id: 'openai_compatible',
      label: 'OpenAI Compatible',
      defaultBaseUrl: '',
      requiresBaseUrl: true,
      defaultModels: [],
    ),
  ];

  @override
  Future<List<RunSummary>> listRuns() async => runs;

  @override
  Future<List<ProviderSpecSummary>> listProviderSpecs() async => providerSpecs;

  @override
  Future<void> saveProviderCredential({
    required String provider,
    required String apiKey,
    String baseUrl = '',
  }) async {
    final error = providerSaveError;
    if (error != null) throw error;
    savedProvider = provider;
    savedApiKey = apiKey;
    savedBaseUrl = baseUrl;
  }

  @override
  Future<List<String>> fetchProviderModels(String provider) async {
    return providerModels;
  }

  @override
  Future<void> clearProviderCredential(String provider) async {
    clearedProvider = provider;
  }
}

class FakeParticipantApiClient extends ParticipantApiClient {
  FakeParticipantApiClient({this.joinGate})
    : super(baseUri: Uri.parse('http://127.0.0.1:8765'));

  final Completer<void>? joinGate;
  String? joinedRunId;
  final sseController = StreamController<ParticipantSseEvent>.broadcast();

  @override
  Future<ParticipantSession> join({
    required String runId,
    required String seatId,
    required String joinCode,
  }) async {
    joinedRunId = runId;
    await joinGate?.future;
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
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('狼人杀观察席'), findsOneWidget);
    expect(find.text('首页'), findsOneWidget);
    expect(find.text('角色'), findsOneWidget);
    expect(find.text('历史对局'), findsOneWidget);
    expect(find.text('设置'), findsOneWidget);
    expect(find.text('房间'), findsNothing);
    expect(find.text('EN'), findsNothing);
    expect(find.byKey(const Key('appearance-quick-toggle')), findsOneWidget);
    expect(find.text('Werewolf Agent'), findsNothing);
  });

  testWidgets(
    'settings language toggle switches primary shell copy to English',
    (tester) async {
      await tester.pumpWidget(
        WerewolfApp(
          observerClientFactory: (_) => FakeObserverApiClient(),
          sessionControllerFactory: (_) =>
              SessionController(participantApi: FakeParticipantApiClient()),
          providerCredentialStore: MemoryProviderCredentialStore(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('设置'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('EN'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Home'));
      await tester.pumpAndSettle();

      expect(find.text('Werewolf Observer'), findsOneWidget);
      expect(find.text('Home'), findsOneWidget);
      expect(find.text('Roles'), findsOneWidget);
      expect(find.text('History'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
      expect(find.text('Room'), findsNothing);
    },
  );

  testWidgets('home quick appearance toggle switches day and night styles', (
    tester,
  ) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('appearance-quick-toggle')), findsOneWidget);
    expect(find.byIcon(Icons.dark_mode_rounded), findsOneWidget);

    await tester.tap(find.byKey(const Key('appearance-quick-toggle')));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.light_mode_rounded), findsOneWidget);
  });

  testWidgets('settings exposes cloud and local observer presets', (
    tester,
  ) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('设置'));
    await tester.pumpAndSettle();

    expect(find.text('外观'), findsOneWidget);
    expect(find.text('白天'), findsOneWidget);
    expect(find.text('夜晚'), findsOneWidget);
    expect(find.text('http://api.paleink.cc:8765'), findsOneWidget);
    expect(find.text('PaleInk 云服务器'), findsOneWidget);
    expect(find.text('本机开发'), findsOneWidget);

    await tester.tap(find.text('本机开发'));
    await tester.pumpAndSettle();

    expect(find.text('http://127.0.0.1:8765'), findsOneWidget);
  });

  testWidgets('provider settings save key, sync, and fetch models', (
    tester,
  ) async {
    final observer = FakeObserverApiClient();
    final store = MemoryProviderCredentialStore();
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => observer,
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: store,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('设置'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('provider-api-key-field')),
      500,
      scrollable: find.byWidgetPredicate(
        (widget) =>
            widget is Scrollable && widget.axisDirection == AxisDirection.down,
      ),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.byKey(const Key('provider-select-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('provider-select-button')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('provider-picker-sheet')), findsOneWidget);
    await tester.tap(
      find.byKey(const Key('provider-option-openai_compatible')),
    );
    await tester.pumpAndSettle();
    expect(await store.readActiveProvider(), 'openai_compatible');

    await tester.tap(find.byKey(const Key('provider-select-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('provider-option-deepseek')));
    await tester.pumpAndSettle();
    expect(await store.readActiveProvider(), 'deepseek');

    await tester.enterText(
      find.byKey(const Key('provider-api-key-field')),
      'sk-mobile-secret',
    );
    EditableText apiKeyEditableText() {
      return tester.widget<EditableText>(
        find.descendant(
          of: find.byKey(const Key('provider-api-key-field')),
          matching: find.byType(EditableText),
        ),
      );
    }

    expect(apiKeyEditableText().obscureText, isTrue);
    await tester.tap(
      find.byKey(const Key('provider-api-key-visibility-button')),
    );
    await tester.pumpAndSettle();
    expect(apiKeyEditableText().obscureText, isFalse);
    await tester.tap(
      find.byKey(const Key('provider-api-key-visibility-button')),
    );
    await tester.pumpAndSettle();
    expect(apiKeyEditableText().obscureText, isTrue);
    await tester.ensureVisible(
      find.byKey(const Key('provider-owner-token-field')),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('provider-owner-token-field')),
      'owner-secret',
    );
    await tester.ensureVisible(find.byKey(const Key('provider-sync-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('provider-sync-button')));
    await tester.pumpAndSettle();

    expect(observer.savedProvider, 'deepseek');
    expect(observer.savedApiKey, 'sk-mobile-secret');
    expect(observer.ownerToken, 'owner-secret');
    expect(await store.readApiKey('deepseek'), 'sk-mobile-secret');
    expect(
      await store.readOwnerToken('http://api.paleink.cc:8765'),
      'owner-secret',
    );
    expect(find.text('sk-mobile-secret'), findsNothing);
    expect(find.text('owner-secret'), findsNothing);
    expect(find.text('已同步到当前 observer server'), findsOneWidget);

    await tester.tap(find.byKey(const Key('provider-models-button')));
    await tester.pumpAndSettle();

    expect(find.text('已拉取 2 个模型'), findsOneWidget);
    await tester.tap(find.byKey(const Key('provider-model-select-button')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const Key('provider-model-picker-sheet')),
      findsOneWidget,
    );
    await tester.tap(
      find.byKey(const Key('provider-model-option-deepseek-v4-flash')),
    );
    await tester.pumpAndSettle();
    expect((await store.read('deepseek')).selectedModel, 'deepseek-v4-flash');

    await tester.tap(find.byKey(const Key('provider-clear-button')));
    await tester.pumpAndSettle();

    expect(observer.clearedProvider, 'deepseek');
    expect(await store.readApiKey('deepseek'), isNull);
    expect(find.text('已清除本机 key'), findsOneWidget);
  });

  testWidgets('provider settings explains forbidden remote credential sync', (
    tester,
  ) async {
    final observer = FakeObserverApiClient(
      providerSaveError: const ObserverApiError(
        'saveProviderCredential',
        403,
        'owner_token_required',
      ),
    );
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => observer,
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('设置'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('provider-api-key-field')),
      500,
      scrollable: find.byWidgetPredicate(
        (widget) =>
            widget is Scrollable && widget.axisDirection == AxisDirection.down,
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('provider-api-key-field')),
      'sk-mobile-secret',
    );
    await tester.ensureVisible(find.byKey(const Key('provider-sync-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('provider-sync-button')));
    await tester.pumpAndSettle();

    expect(find.textContaining('请输入当前 observer 的 owner token'), findsOneWidget);
    expect(find.text('供应商操作失败：owner_token_required'), findsNothing);
  });

  testWidgets('home choose match flow lists observer runs and can join one', (
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
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('对局'), findsNothing);

    await tester.tap(find.text('继续进入'));
    await tester.pump();

    expect(find.text('选择对局'), findsOneWidget);
    expect(find.text('首页'), findsNothing);
    expect(find.byKey(const Key('flow-back-button')), findsOneWidget);
    expect(find.text('run_1'), findsOneWidget);
    expect(find.text('进行中'), findsOneWidget);
    final matchBackTopLeft = tester.getTopLeft(
      find.byKey(const Key('flow-back-button')),
    );
    final matchBackRight = tester
        .getTopRight(find.byKey(const Key('flow-back-button')))
        .dx;
    final matchTitleLeft = tester.getTopLeft(find.text('选择对局')).dx;
    expect(matchTitleLeft - matchBackRight, greaterThanOrEqualTo(12));

    await tester.tap(find.text('加入此局'));
    await tester.pump();
    await tester.pump();

    expect(participant.joinedRunId, 'run_1');
    expect(find.byKey(const Key('role-notice-dialog')), findsOneWidget);
    expect(find.textContaining('你的身份'), findsWidgets);
    expect(find.text('预言家'), findsWidgets);
    expect(find.text('首页'), findsNothing);
    expect(find.byKey(const Key('flow-back-button')), findsOneWidget);
    expect(
      tester.getTopLeft(find.byKey(const Key('flow-back-button'))),
      matchBackTopLeft,
    );

    await tester.tap(find.text('进入房间'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('flow-back-button')), findsOneWidget);
    expect(
      tester.getTopLeft(find.byKey(const Key('flow-back-button'))),
      matchBackTopLeft,
    );
    await participant.sseController.close();
  });

  testWidgets('join enters room before participant API completes', (
    tester,
  ) async {
    final joinGate = Completer<void>();
    final participant = FakeParticipantApiClient(joinGate: joinGate);
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(
          runs: const [RunSummary(runId: 'run_1', status: 'running')],
        ),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: participant),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('继续进入'));
    await tester.pump();
    await tester.tap(find.text('加入此局'));
    await tester.pump();

    expect(participant.joinedRunId, 'run_1');
    expect(find.byKey(const Key('room-status-island')), findsOneWidget);
    expect(find.byKey(const Key('role-notice-dialog')), findsNothing);
    expect(find.text('加入中...'), findsNothing);

    joinGate.complete();
    await tester.pump();
    await tester.pump();

    expect(find.byKey(const Key('role-notice-dialog')), findsOneWidget);
    expect(find.text('预言家'), findsWidgets);
    await participant.sseController.close();
  });

  testWidgets('roles tab exposes local role policy editor draft', (
    tester,
  ) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('角色'));
    await tester.pumpAndSettle();

    expect(find.text('角色策略'), findsOneWidget);
    expect(find.text('标准六人局 · 本地草稿'), findsOneWidget);
    expect(find.byKey(const Key('role-policy-grid')), findsOneWidget);
    for (final roleName in ['狼人', '预言家', '女巫', '村民', '守卫', '猎人']) {
      expect(find.text(roleName), findsOneWidget);
    }

    await tester.tap(find.text('预言家'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('role-policy-detail-page')), findsOneWidget);
    expect(find.text('身份边界'), findsOneWidget);
    expect(find.text('策略总览'), findsOneWidget);
    expect(find.text('决策倾向'), findsOneWidget);
    expect(find.text('行动策略'), findsOneWidget);
    expect(find.text('证据与上下文'), findsOneWidget);
    expect(find.text('运行时组合'), findsOneWidget);
    expect(find.text('提示词'), findsNothing);

    await tester.tap(find.text('强势带队'));
    await tester.pumpAndSettle();

    expect(find.text('草稿未保存'), findsOneWidget);
    expect(find.text('当前策略：强势带队'), findsOneWidget);
    expect(find.text('已保存'), findsNothing);
    expect(find.text('本局已冻结'), findsNothing);
    expect(find.text('v1.3'), findsNothing);
    expect(find.textContaining('历史对局引用'), findsNothing);
  });

  testWidgets('role policy setting-only edits persist in local draft', (
    tester,
  ) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('角色'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('女巫'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('女巫'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('药品风险姿态'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, '主动'));
    await tester.pumpAndSettle();

    expect(find.text('草稿未保存'), findsOneWidget);
    expect(find.text('主动'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('role-policy-grid')), findsOneWidget);
    expect(find.text('本地草稿'), findsAtLeastNWidgets(1));

    await tester.ensureVisible(find.text('女巫'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('女巫'));
    await tester.pumpAndSettle();

    expect(find.text('草稿未保存'), findsOneWidget);
    expect(find.text('主动'), findsOneWidget);
  });

  testWidgets('history tab groups previous runs by status', (tester) async {
    await tester.pumpWidget(
      WerewolfApp(
        observerClientFactory: (_) => FakeObserverApiClient(
          runs: const [
            RunSummary(runId: 'run_live', status: 'running'),
            RunSummary(runId: 'run_done', status: 'completed'),
            RunSummary(runId: 'run_stop', status: 'interrupted'),
          ],
        ),
        sessionControllerFactory: (_) =>
            SessionController(participantApi: FakeParticipantApiClient()),
        providerCredentialStore: MemoryProviderCredentialStore(),
      ),
    );
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('历史对局'));
    await tester.pumpAndSettle();

    expect(find.text('进行中'), findsWidgets);
    expect(find.text('已完成'), findsWidgets);
    expect(find.text('中断'), findsWidgets);
    expect(find.text('run_live'), findsOneWidget);
    expect(find.text('run_done'), findsOneWidget);
    expect(find.text('run_stop'), findsOneWidget);
  });
}
