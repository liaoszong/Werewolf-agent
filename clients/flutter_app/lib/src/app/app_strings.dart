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
  String get startTestMatch => _t('新建测试局', 'New Test Match');
  String get startingTestMatch => _t('创建中...', 'Creating...');
  String get startTestMatchHint => _t(
    '创建一局假 AI + 真人席位的测试对局，用来验证手机房间流程；不会调用真实模型。',
    'Create a fake-AI match with your human seat to test the mobile room flow. This does not call a live model.',
  );
  String launchRunFailed(String code) {
    if (code == 'owner_token_required') {
      return _t(
        '请输入当前 observer 的 owner token 后再新建测试局。',
        'Enter this observer owner token before creating a test match.',
      );
    }
    if (code == 'missing_run_id') {
      return _t(
        'observer 创建了响应但没有返回 run id。',
        'The observer response did not include a run id.',
      );
    }
    return _t('新建测试局失败：$code', 'Failed to create test match: $code');
  }

  String get roleLibraryTitle => _t('角色策略', 'Role Policies');
  String get roleLibraryIntro => _t(
    '按身份调整本地 RolePolicy 草稿；当前不保存到后端，也不改变对局规则、提示词或模型调用。',
    'Tune local RolePolicy drafts by identity. This does not persist to the backend or change rules, prompts, or model calls.',
  );
  String get rolePolicyPackLabel => _t('当前策略包', 'Current policy pack');
  String get rolePolicyPackDraft =>
      _t('标准六人局 · 本地草稿', 'Standard six-player · Local draft');
  String get localDraftBadge => _t('本地草稿', 'Local draft');
  String get defaultDraftBadge => _t('默认草稿', 'Default draft');
  String get unsavedDraft => _t('草稿未保存', 'Draft not saved');
  String get roleBoundary => _t('身份边界', 'Role boundary');
  String get strategyOverview => _t('策略总览', 'Strategy overview');
  String get decisionTendencies => _t('决策倾向', 'Decision tendencies');
  String get actionStrategy => _t('行动策略', 'Action strategy');
  String get evidenceContext => _t('证据与上下文', 'Evidence and context');
  String get runtimeComposition => _t('运行时组合', 'Runtime composition');
  String get localPreviewOnly => _t(
    '本页只是本地预览。真正保存和历史绑定要等资产仓库切片。',
    'This page is local preview only. Persistence and run history require the asset registry slice.',
  );
  String get localPreviewAction => _t('仅本地预览', 'Local preview only');
  String get engineAuthority => _t(
    '引擎决定行动窗口、合法动作、信息权限、状态转移和胜负；策略只影响发言、判断和行动提案。',
    'The engine owns decision windows, legal actions, information entitlement, state transitions, and victory. Policy only guides speech, judgment, and action proposals.',
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
  String get confirmingSeat => _t('正在确认席位...', 'Confirming seat...');
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
    'API key 保存在本机安全存储，只同步到当前 observer server。',
    'API keys stay in secure local storage and sync only to the current observer server.',
  );
  String get providerSettingsStored => _t('已本地保存', 'Stored');
  String get providerSettingsNotStored => _t('未保存', 'Not stored');
  String get provider => _t('供应商', 'Provider');
  String get providerBaseUrl => _t('Provider Base URL', 'Provider Base URL');
  String get providerApiKey => _t('API key', 'API key');
  String get providerShowApiKey => _t('显示 API key', 'Show API key');
  String get providerHideApiKey => _t('隐藏 API key', 'Hide API key');
  String get providerApiKeyStored =>
      _t('已保存；留空会继续使用本机已保存 key', 'Saved; leave blank to reuse the local key');
  String get providerOwnerToken =>
      _t('Observer owner token', 'Observer owner token');
  String get providerOwnerTokenStored => _t(
    '已保存；留空继续使用当前服务器 token',
    'Saved; leave blank to reuse this server token',
  );
  String get providerShowOwnerToken => _t('显示 owner token', 'Show owner token');
  String get providerHideOwnerToken => _t('隐藏 owner token', 'Hide owner token');
  String get providerModel => _t('模型', 'Model');
  String get syncProviderCredential => _t('保存并同步', 'Save & Sync');
  String get fetchProviderModels => _t('拉取模型', 'Fetch Models');
  String get clearProviderCredential => _t('清除本机 key', 'Clear local key');
  String get providerMissingApiKey => _t('请输入 API key', 'Enter an API key');
  String get providerMissingBaseUrl =>
      _t('这个供应商需要 Base URL', 'This provider requires a Base URL');
  String get providerCredentialSynced =>
      _t('已同步到当前 observer server', 'Synced to the current observer server');
  String get providerCredentialCleared => _t('已清除本机 key', 'Local key cleared');
  String get phoneLanHint => _t(
    '默认连接 PaleInk 云服务器；本机开发时，Android 真机不能使用 127.0.0.1，需要电脑局域网地址。',
    'Defaults to PaleInk Cloud. For local development on Android, use the computer LAN address instead of 127.0.0.1.',
  );
  String get visibleEventsWaiting =>
      _t('等待可见房间事件...', 'Waiting for visible room events...');
  String get roomNotReadyTitle => _t('房间尚未准备好', 'Room is not ready');
  String get roomNotReadyBody => _t(
    '当前席位还没有拿到角色投影。请等待服务器启动对局，或返回新建一局测试局。',
    'This seat has not received a role projection yet. Wait for the server to start the match, or go back and create a test match.',
  );
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
  String get response => _t('回应', 'Respond');
  String get finalWords => _t('留下遗言', 'Final words');
  String get pass => _t('跳过', 'Pass');
  String get confirm => _t('确认', 'Confirm');
  String get submittingAction => _t('提交中', 'Submitting');
  String get actionExpired => _t('已超时', 'Expired');
  String get timeoutDefault => _t('超时默认', 'Timeout default');
  String get candidateTargets =>
      _t('候选目标，服务器会确认是否合法', 'Candidate targets; server confirms legality');
  String get roleNoticeTitle => _t('身份提醒', 'Role reminder');
  String get roleNoticeBody => _t(
    '进入房间前再次确认你的当前席位信息。这里仍只展示服务器投影允许你看到的内容。',
    'Confirm your current seat before entering the room. This only shows information allowed by the server projection.',
  );
  String get werewolfTeammates => _t('狼人同伴', 'Werewolf teammates');
  String get noVisibleWerewolfTeammates =>
      _t('当前视野没有显示其他狼人', 'No other werewolves are visible in this view');
  String get roleSkill => _t('技能提示', 'Skill tip');
  String get vote => _t('投票', 'Vote');
  String get chooseAction => _t('选择行动', 'Choose action');
  String get seats => _t('座位区', 'Seats');
  String get phaseStatus => _t('阶段状态', 'Phase status');
  String get privateInfo => _t('当前席位私有信息', 'Private seat info');
  String get yourRole => _t('你的身份', 'Your role');
  String get yourTeam => _t('你的阵营', 'Your team');
  String get visibilityProof => _t('视野证明', 'Visibility proof');
  String get hiddenEvents => _t('隐藏事件', 'Hidden events');
  String get hiddenSnapshots => _t('隐藏快照', 'Hidden snapshots');
  String get visibleSnapshot => _t('可见快照', 'Visible snapshot');
  String get you => _t('你', 'You');
  String get alive => _t('存活', 'Alive');
  String get dead => _t('出局', 'Out');
  String get statusUnknown => _t('状态未知', 'Unknown state');

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
      'response' => response,
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
      'night' ||
      'night_werewolf' ||
      'night_witch' ||
      'night_seer' ||
      'night_guard' => nightInProgress,
      'day' || 'day_speech' => discussion,
      'vote' || 'voting' || 'day_vote' => voting,
      'completed' || 'finished' || 'game_over' => gameOver,
      'running' => roomSyncing,
      _ => roomSyncing,
    };
  }

  String roleLabel(String? role) {
    return switch (role) {
      'werewolf' => _t('狼人', 'Werewolf'),
      'seer' => _t('预言家', 'Seer'),
      'witch' => _t('女巫', 'Witch'),
      'hunter' => _t('猎人', 'Hunter'),
      'guard' => _t('守卫', 'Guard'),
      'villager' => _t('村民', 'Villager'),
      'unknown' || null => unknown,
      _ => role,
    };
  }

  String teamLabel(String? team) {
    return switch (team) {
      'werewolf' => _t('狼人阵营', 'Werewolf team'),
      'villager' => _t('好人阵营', 'Village team'),
      'unknown' || null => unknown,
      _ => team,
    };
  }

  String roleSkillIntro(String? role) {
    return switch (role) {
      'werewolf' => _t(
        '夜晚与狼人同伴选择击杀目标；白天需要隐藏阵营并影响投票。',
        'At night, choose a kill target with your teammates. By day, hide your team and influence the vote.',
      ),
      'seer' => _t(
        '夜晚可查验一名玩家的阵营；白天用发言引导好人阵营。',
        'At night, check one player. By day, guide the village through speech.',
      ),
      'witch' => _t(
        '拥有解药和毒药；具体可用行动以后端行动窗口为准。',
        'You have save and poison powers. Available actions still follow the server action window.',
      ),
      'hunter' => _t(
        '出局时通常可以开枪带走一名玩家；是否可用以后端行动窗口为准。',
        'When eliminated, you may be able to shoot one player. Availability follows the server action window.',
      ),
      'guard' => _t(
        '夜晚可守护一名玩家；具体目标以后端行动窗口确认为准。',
        'At night, protect one player. The server action window confirms the available target.',
      ),
      'villager' => _t(
        '没有夜间技能，依靠发言、投票和推理找出狼人。',
        'No night power. Use speech, voting, and logic to find werewolves.',
      ),
      _ => _t(
        '技能会在后续行动窗口中按服务器开放。',
        'Your actions will appear later through server-owned action windows.',
      ),
    };
  }

  String aliveLabel(bool? isAlive) {
    return switch (isAlive) {
      true => alive,
      false => dead,
      null => statusUnknown,
    };
  }

  String roundLabel(int? round) {
    if (round == null || round <= 0) return currentRound;
    return appLanguage == AppLanguage.zh ? '第 $round 轮' : 'Round $round';
  }

  String timeRemainingLabel(Duration remaining) {
    if (remaining.isNegative || remaining.inSeconds <= 0) return actionExpired;
    final minutes = remaining.inMinutes;
    final seconds = remaining.inSeconds
        .remainder(60)
        .toString()
        .padLeft(2, '0');
    return appLanguage == AppLanguage.zh
        ? '剩余 $minutes:$seconds'
        : '$minutes:$seconds left';
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

  String providerModelsLoaded(int count) {
    return appLanguage == AppLanguage.zh
        ? '已拉取 $count 个模型'
        : 'Fetched $count models';
  }

  String providerOperationFailed(String code) {
    if (code == 'owner_token_required') {
      return _t(
        '请输入当前 observer 的 owner token 后再同步。',
        'Enter this observer owner token before syncing.',
      );
    }
    if (code == 'forbidden') {
      return _t(
        '当前 observer 未启用远程 owner-token 凭据同步；请更新服务器并配置 owner token。',
        'This observer has not enabled remote owner-token credential sync. Update the server and configure an owner token.',
      );
    }
    return appLanguage == AppLanguage.zh
        ? '供应商操作失败：$code'
        : 'Provider operation failed: $code';
  }

  String _t(String zh, String en) => appLanguage == AppLanguage.zh ? zh : en;
}
