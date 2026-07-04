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
  String get settings => _t('设置', 'Settings');
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
  String get emptyRoomTitle => _t('尚未加入席位', 'No seat joined');
  String get emptyRoomBody => _t(
    '先在「对局」里选择一局，再进入你的参与者视角。',
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

  String serverPresetLabel(ObserverServerPreset preset) {
    return switch (preset) {
      ObserverServerPreset.paleInkCloud => _t('PaleInk 云服务器', 'PaleInk Cloud'),
      ObserverServerPreset.localDev => _t('本机开发', 'Local Dev'),
    };
  }

  String _t(String zh, String en) => appLanguage == AppLanguage.zh ? zh : en;
}
