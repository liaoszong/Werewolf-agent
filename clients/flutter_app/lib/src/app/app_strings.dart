import 'package:flutter/widgets.dart';

import 'app_settings.dart';

class AppLanguageScope extends InheritedNotifier<AppSettingsController> {
  const AppLanguageScope({
    super.key,
    required AppSettingsController controller,
    required super.child,
  }) : super(notifier: controller);

  static AppSettingsController? maybeControllerOf(BuildContext context) {
    return context
        .dependOnInheritedWidgetOfExactType<AppLanguageScope>()
        ?.notifier;
  }

  static AppStrings of(BuildContext context) {
    final controller = maybeControllerOf(context);
    return AppStrings.forLanguage(controller?.language ?? AppLanguage.zh);
  }
}

class AppStrings {
  const AppStrings._(this.appLanguage);

  final AppLanguage appLanguage;

  static AppStrings forLanguage(AppLanguage language) => AppStrings._(language);

  String get appTitle => _t('狼人杀观察席', 'Werewolf Observer');
  String get appKicker =>
      _t('AI 对局 · 真人席位 · 本地协议', 'AI matches · Human seat · Local protocol');
  String get appIntro => _t(
    '连接本地 observer server，选择一局进行中的对局，以合法参与者视角加入。',
    'Connect to the local observer server, choose a live match, and join through the participant perspective.',
  );
  String get home => _t('首页', 'Home');
  String get matches => _t('对局', 'Matches');
  String get room => _t('房间', 'Room');
  String get roles => _t('角色', 'Roles');
  String get history => _t('历史对局', 'History');
  String get settings => _t('设置', 'Settings');
  String get appearance => _t('外观', 'Appearance');
  String get dayStyle => _t('白天', 'Day');
  String get nightStyle => _t('夜晚', 'Night');
  String get switchToDayStyle => _t('切换到白天风格', 'Switch to day style');
  String get switchToNightStyle => _t('切换到夜晚风格', 'Switch to night style');
  String get server => _t('服务器', 'Server');
  String get connected => _t('已连接', 'Connected');
  String get offline => _t('离线', 'Offline');
  String get loading => _t('同步中', 'Syncing');
  String get activeMatch => _t('今夜对局', "Tonight's Match");
  String get noActiveRuns => _t('暂无进行中对局', 'No active runs');
  String get continueObserving => _t('继续进入', 'Continue');
  String get chooseMatch => _t('选择对局', 'Choose Match');
  String get refresh => _t('刷新', 'Refresh');
  String get joinRun => _t('加入此局', 'Join');
  String get joining => _t('加入中...', 'Joining...');
  String get running => _t('进行中', 'Running');
  String get queued => _t('排队中', 'Queued');
  String get completed => _t('已完成', 'Completed');
  String get failed => _t('失败', 'Failed');
  String get interrupted => _t('中断', 'Interrupted');
  String get unknown => _t('未知', 'Unknown');
  String get runListHint => _t(
    '从 observer server 读取对局列表；可使用 PaleInk 云服务器或本机开发服务。',
    'Runs are loaded from the observer server. Use PaleInk Cloud or a local dev server.',
  );
  String get roleLibraryTitle => _t('全部角色', 'All Roles');
  String get roleLibraryIntro => _t(
    '这里展示移动端可见的角色 Agent 设计说明。当前先只读预览允许编辑范围，不改后端协议。',
    'This shows the mobile-visible role agent design. This slice previews allowed edits without changing the backend protocol.',
  );
  String get agentHarness => _t('Agent harness', 'Agent harness');
  String get memory => _t('记忆', 'Memory');
  String get prompt => _t('提示词', 'Prompt');
  String get editable => _t('可编辑', 'Editable');
  String get locked => _t('锁定', 'Locked');
  String get historyIntro => _t(
    '按 observer server 返回状态分组；已完成、进行中、中断的详情页后续会继续拆。',
    'Grouped by observer server status. Completed, running, and interrupted details will be split in a later slice.',
  );
  String get emptyRoomTitle => _t('尚未加入席位', 'No seat joined');
  String get emptyRoomBody => _t(
    '先在首页选择一局，再进入你的参与者视角。',
    'Choose a match first, then enter your participant room.',
  );
  String get participantPerspective =>
      _t('参与者视角，不是上帝视角', 'Participant perspective, not god view');
  String get legalInfoOnly => _t(
    '你只会看到当前席位合法可见的信息。夜间他人行动会显示为等待状态。',
    'You only see information legal for this seat. Hidden night actions stay as waiting state.',
  );
  String get enterRoom => _t('进入房间', 'Enter Room');
  String get languageLabel => _t('语言', 'Language');
  String get connection => _t('连接', 'Connection');
  String get baseUrl => _t('Observer Base URL', 'Observer Base URL');
  String get quickServer => _t('快捷服务器', 'Quick Server');
  String get seatId => _t('席位 ID', 'Seat ID');
  String get joinCode => _t('加入码', 'Join code');
  String get saveConnection => _t('保存连接设置', 'Save Connection');
  String get invalidBaseUrl =>
      _t('请输入有效的 observer base URL', 'Enter a valid observer base URL');
  String get updates => _t('应用更新', 'App Updates');
  String get currentVersion => _t('当前版本', 'Current version');
  String get availableVersion => _t('可用版本', 'Available version');
  String get checkUpdates => _t('检查更新', 'Check Updates');
  String get downloadInstall => _t('下载并安装', 'Download & Install');
  String get providerSettings => _t('供应商', 'Providers');
  String get providerSettingsBody => _t(
    '后续迁移桌面客户端的 BYO-key、Base URL、模型和启用状态。当前移动端先不保存密钥。',
    'Next we will migrate the desktop client provider settings: BYO key, base URL, model, and enabled state. The mobile app does not store secrets yet.',
  );
  String get providerSettingsPending => _t('待接入', 'Pending');
  String get phoneLanHint => _t(
    '默认连接 PaleInk 云服务器；本机开发时，Android 真机不能使用 127.0.0.1，需要电脑局域网地址。',
    'Defaults to PaleInk Cloud. For local development on Android, use the computer LAN address instead of 127.0.0.1.',
  );
  String get visibleEventsWaiting =>
      _t('等待可见房间事件...', 'Waiting for visible room events...');
  String get waitingForYou => _t('等待你操作', 'Waiting for you');
  String get nightInProgress => _t('夜间行动中', 'Night actions');
  String get voting => _t('投票中', 'Voting');
  String get discussion => _t('公开讨论', 'Discussion');
  String get gameOver => _t('游戏结束', 'Game over');
  String get roomSyncing => _t('房间同步中', 'Room syncing');
  String get currentRound => _t('当前轮次', 'Current round');
  String get requiredAction => _t('必须操作', 'Required');
  String get optionalAction => _t('可选操作', 'Optional');
  String get actionWindowOpen => _t('行动窗口已开启', 'Action window open');
  String get publicEvent => _t('公开事件', 'Public event');
  String get systemEvent => _t('系统事件', 'System event');
  String get playerSpeech => _t('玩家发言', 'Player speech');
  String get reconnecting => _t('正在重连', 'Reconnecting');
  String get connecting => _t('连接中', 'Connecting');
  String get sessionExpired => _t('会话失效', 'Session expired');
  String get connectionFailed => _t('连接异常', 'Connection issue');
  String get idle => _t('未连接', 'Not connected');
  String get yourPerspective => _t('你的视角', 'Your view');
  String get collapseComposer => _t('收起行动框', 'Collapse action composer');
  String get expandComposer => _t('展开行动框', 'Expand action composer');
  String get noAction => _t('暂无行动', 'No action');
  String get send => _t('发送', 'Send');
  String get speech => _t('发言', 'Speak');
  String get finalWords => _t('留下遗言', 'Final words');
  String get pass => _t('跳过', 'Pass');
  String get confirm => _t('确认', 'Confirm');
  String get candidateTargets =>
      _t('候选目标，服务器会确认是否合法', 'Candidate targets; server confirms legality');
  String get vote => _t('投票', 'Vote');
  String get chooseAction => _t('选择行动', 'Choose action');

  String seatIdentity(String seat) {
    return appLanguage == AppLanguage.zh ? '你的席位是 $seat' : 'Your seat is $seat';
  }

  String statusLabel(String status) {
    return switch (status) {
      'running' => running,
      'queued' => queued,
      'completed' || 'finished' => completed,
      'failed' => failed,
      'interrupted' => interrupted,
      _ => unknown,
    };
  }

  String actionLabel(String actionType) {
    return switch (actionType) {
      'vote' => vote,
      'werewolf_kill' => _t('选择击杀目标', 'Choose kill target'),
      'seer_check' => _t('选择查验目标', 'Choose check target'),
      'witch_save' => _t('选择解药目标', 'Choose save target'),
      'witch_poison' => _t('选择毒药目标', 'Choose poison target'),
      'guard_protect' => _t('选择守护目标', 'Choose guard target'),
      'hunter_shoot' => _t('选择开枪目标', 'Choose shot target'),
      'pass' => pass,
      _ => chooseAction,
    };
  }

  String phaseLabel(String? phase) {
    return switch (phase) {
      'night' => nightInProgress,
      'day' => discussion,
      'vote' || 'voting' => voting,
      'completed' || 'finished' || 'game_over' => gameOver,
      'running' => roomSyncing,
      _ => roomSyncing,
    };
  }

  String roundLabel(int? round) {
    if (round == null || round <= 0) return currentRound;
    return appLanguage == AppLanguage.zh ? '第 $round 轮' : 'Round $round';
  }

  String eventKindLabel(String kind) {
    return switch (kind) {
      'player_speech' || 'speech' => playerSpeech,
      'final_words' => finalWords,
      'player_vote' || 'vote' => vote,
      'phase_changed' => _t('阶段变化', 'Phase change'),
      'vote_started' => _t('投票开始', 'Vote started'),
      'vote_ended' => _t('投票结束', 'Vote ended'),
      'player_eliminated' => _t('放逐结果', 'Elimination'),
      'player_died' => _t('死亡通告', 'Death notice'),
      'game_completed' || 'game_over' => gameOver,
      _ => systemEvent,
    };
  }

  String serverPresetLabel(ObserverServerPreset preset) {
    return switch (preset) {
      ObserverServerPreset.paleInkCloud => _t('PaleInk 云服务器', 'PaleInk Cloud'),
      ObserverServerPreset.localDev => _t('本机开发', 'Local Dev'),
    };
  }

  String _t(String zh, String en) => appLanguage == AppLanguage.zh ? zh : en;
}
