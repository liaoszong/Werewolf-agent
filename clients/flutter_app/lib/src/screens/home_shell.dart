import 'package:flutter/material.dart';

import '../app/app_settings.dart';
import '../app/app_strings.dart';
import '../app/build_info.dart';
import '../app/session_controller.dart';
import '../protocol/observer_api_client.dart';
import '../ui/app_theme.dart';
import '../update/update_models.dart';
import '../update/update_repository.dart';
import 'live_room_screen.dart';

typedef ObserverClientFactory = ObserverApiClient Function(Uri baseUri);
typedef SessionControllerFactory = SessionController Function(Uri baseUri);

enum _HomeFlow { dashboard, matchPicker, liveRoom }

class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.settingsController,
    required this.updateRepository,
    required this.observerClientFactory,
    required this.sessionControllerFactory,
  });

  final AppSettingsController settingsController;
  final UpdateRepository updateRepository;
  final ObserverClientFactory observerClientFactory;
  final SessionControllerFactory sessionControllerFactory;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _selectedIndex = 0;
  _HomeFlow _homeFlow = _HomeFlow.dashboard;
  Uri? _loadedBaseUri;
  bool _loadingRuns = false;
  bool _joining = false;
  bool _needsIdentityConfirm = false;
  String? _runsError;
  String? _joinError;
  List<RunSummary> _runs = const [];
  SessionController? _sessionController;

  AppSettingsController get _settings => widget.settingsController;

  @override
  void initState() {
    super.initState();
    _settings.addListener(_handleSettingsChanged);
    _loadRuns();
  }

  @override
  void dispose() {
    _settings.removeListener(_handleSettingsChanged);
    _sessionController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final showBottomNav =
        _selectedIndex != 0 || _homeFlow == _HomeFlow.dashboard;
    return Scaffold(
      body: SafeArea(
        child: IndexedStack(
          index: _selectedIndex,
          children: [
            _buildHomeFlow(),
            const _RolesPage(),
            _HistoryPage(
              runs: _runs,
              loadingRuns: _loadingRuns,
              error: _runsError,
              onRefresh: _loadRuns,
            ),
            _SettingsPage(
              settingsController: _settings,
              updateRepository: widget.updateRepository,
            ),
          ],
        ),
      ),
      bottomNavigationBar: showBottomNav
          ? _FloatingTabBar(
              selectedIndex: _selectedIndex,
              onSelected: _selectTab,
              items: [
                _TabBarItem(
                  icon: Icons.home_outlined,
                  selectedIcon: Icons.home_rounded,
                  label: strings.home,
                ),
                _TabBarItem(
                  icon: Icons.theater_comedy_outlined,
                  selectedIcon: Icons.theater_comedy_rounded,
                  label: strings.roles,
                ),
                _TabBarItem(
                  icon: Icons.history_outlined,
                  selectedIcon: Icons.history_rounded,
                  label: strings.history,
                ),
                _TabBarItem(
                  icon: Icons.settings_outlined,
                  selectedIcon: Icons.settings_rounded,
                  label: strings.settings,
                ),
              ],
            )
          : null,
    );
  }

  void _selectTab(int index) {
    setState(() {
      _selectedIndex = index;
      if (index == 0) {
        _homeFlow = _HomeFlow.dashboard;
      }
    });
  }

  Widget _buildHomeFlow() {
    return switch (_homeFlow) {
      _HomeFlow.dashboard => _HomePage(
        runs: _runs,
        loadingRuns: _loadingRuns,
        runsError: _runsError,
        onChooseMatch: () => setState(() => _homeFlow = _HomeFlow.matchPicker),
        onRefresh: _loadRuns,
      ),
      _HomeFlow.matchPicker => _MatchesPage(
        runs: _runs,
        loadingRuns: _loadingRuns,
        joining: _joining,
        error: _runsError ?? _joinError,
        onBack: () => setState(() => _homeFlow = _HomeFlow.dashboard),
        onRefresh: _loadRuns,
        onJoin: _joinRun,
      ),
      _HomeFlow.liveRoom => _RoomPage(
        controller: _sessionController,
        needsIdentityConfirm: _needsIdentityConfirm,
        onBackToMatches: () =>
            setState(() => _homeFlow = _HomeFlow.matchPicker),
        onEnterRoom: () {
          setState(() => _needsIdentityConfirm = false);
        },
      ),
    };
  }

  Future<void> _loadRuns() async {
    setState(() {
      _loadingRuns = true;
      _runsError = null;
      _loadedBaseUri = _settings.baseUri;
    });
    try {
      final observer = widget.observerClientFactory(_settings.baseUri);
      final runs = await observer.listRuns();
      if (!mounted) return;
      setState(() {
        _runs = runs;
        _loadingRuns = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _runsError = error.toString();
        _loadingRuns = false;
      });
    }
  }

  Future<void> _joinRun(String runId) async {
    setState(() {
      _joining = true;
      _joinError = null;
    });
    final controller = widget.sessionControllerFactory(_settings.baseUri);
    await controller.joinAndLoad(
      runId: runId,
      seatId: _settings.seatId,
      joinCode: _settings.joinCode,
    );
    if (!mounted) return;
    if (controller.connectionStatus == ConnectionStatus.connected) {
      _sessionController?.dispose();
      setState(() {
        _sessionController = controller;
        _joining = false;
        _needsIdentityConfirm = true;
        _selectedIndex = 0;
        _homeFlow = _HomeFlow.liveRoom;
      });
      return;
    }
    controller.dispose();
    setState(() {
      _joining = false;
      _joinError = controller.lastError ?? 'join failed';
    });
  }

  void _handleSettingsChanged() {
    if (_loadedBaseUri != _settings.baseUri) {
      _loadRuns();
      return;
    }
    setState(() {});
  }
}

class _HomePage extends StatelessWidget {
  const _HomePage({
    required this.runs,
    required this.loadingRuns,
    required this.runsError,
    required this.onChooseMatch,
    required this.onRefresh,
  });

  final List<RunSummary> runs;
  final bool loadingRuns;
  final String? runsError;
  final VoidCallback onChooseMatch;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final activeRuns = runs
        .where((run) => run.status == 'running' || run.status == 'queued')
        .toList(growable: false);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    strings.appTitle,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: palette.textPrimary,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    strings.appKicker,
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(color: palette.accent),
                  ),
                ],
              ),
            ),
            const _AppearanceQuickToggle(),
          ],
        ),
        const SizedBox(height: 18),
        Text(
          strings.appIntro,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: palette.textMuted),
        ),
        const SizedBox(height: 22),
        _ServerCard(
          loadingRuns: loadingRuns,
          runsError: runsError,
          onRefresh: onRefresh,
        ),
        const SizedBox(height: 18),
        _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.activeMatch,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 10),
              if (activeRuns.isEmpty)
                Text(
                  strings.noActiveRuns,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: palette.textMuted),
                )
              else
                for (final run in activeRuns.take(3))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _RunSummaryRow(run: run),
                  ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: FilledButton.icon(
                  onPressed: onChooseMatch,
                  icon: const Icon(Icons.arrow_forward_rounded),
                  label: Text(
                    activeRuns.isEmpty
                        ? strings.chooseMatch
                        : strings.continueObserving,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MatchesPage extends StatelessWidget {
  const _MatchesPage({
    required this.runs,
    required this.loadingRuns,
    required this.joining,
    required this.error,
    required this.onBack,
    required this.onRefresh,
    required this.onJoin,
  });

  final List<RunSummary> runs;
  final bool loadingRuns;
  final bool joining;
  final String? error;
  final VoidCallback onBack;
  final Future<void> Function() onRefresh;
  final ValueChanged<String> onJoin;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
      children: [
        Row(
          children: [
            _FloatingBackButton(onPressed: onBack),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                strings.chooseMatch,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: palette.textPrimary,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            IconButton(
              tooltip: strings.refresh,
              onPressed: loadingRuns ? null : onRefresh,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(strings.runListHint, style: Theme.of(context).textTheme.bodySmall),
        if (error != null) ...[
          const SizedBox(height: 12),
          Text(error!, style: TextStyle(color: palette.danger)),
        ],
        const SizedBox(height: 16),
        if (loadingRuns)
          const Center(child: CircularProgressIndicator())
        else if (runs.isEmpty)
          _Panel(
            child: Text(
              strings.noActiveRuns,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          )
        else
          for (final run in runs)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _RunCard(
                run: run,
                joining: joining,
                onJoin: () => onJoin(run.runId),
              ),
            ),
      ],
    );
  }
}

class _RolesPage extends StatelessWidget {
  const _RolesPage();

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 22, 18, 24),
      children: [
        Text(
          strings.roleLibraryTitle,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: palette.textPrimary,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          strings.roleLibraryIntro,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: palette.textMuted),
        ),
        const SizedBox(height: 16),
        for (final role in _roleTemplates)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: _RoleCard(role: role),
          ),
      ],
    );
  }
}

class _RoleCard extends StatelessWidget {
  const _RoleCard({required this.role});

  final _AgentRoleTemplate role;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final language = strings.appLanguage;
    final palette = WerewolfAppTheme.colors(context);
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () => _showRoleDetail(context, role),
      child: _Panel(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: role.color.withValues(alpha: 0.16),
              foregroundColor: role.color,
              child: Icon(role.icon),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          role.name(language),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                      _RoleBadge(
                        label: role.editable
                            ? strings.editable
                            : strings.locked,
                        color: role.editable
                            ? palette.witch
                            : palette.textMuted,
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    role.summary(language),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(Icons.chevron_right_rounded),
          ],
        ),
      ),
    );
  }
}

void _showRoleDetail(BuildContext context, _AgentRoleTemplate role) {
  final palette = WerewolfAppTheme.colors(context);
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: palette.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (context) => _RoleDetailSheet(role: role),
  );
}

class _RoleDetailSheet extends StatelessWidget {
  const _RoleDetailSheet({required this.role});

  final _AgentRoleTemplate role;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final language = strings.appLanguage;
    final palette = WerewolfAppTheme.colors(context);
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          16,
          20,
          20 + MediaQuery.of(context).viewInsets.bottom,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: palette.textMuted.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: const SizedBox(width: 42, height: 4),
                ),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: role.color.withValues(alpha: 0.16),
                    foregroundColor: role.color,
                    child: Icon(role.icon),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      role.name(language),
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                  ),
                  _RoleBadge(
                    label: role.editable ? strings.editable : strings.locked,
                    color: role.editable ? palette.witch : palette.textMuted,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              _RoleDetailSection(
                title: strings.agentHarness,
                body: role.harness(language),
              ),
              _RoleDetailSection(
                title: strings.memory,
                body: role.memory(language),
              ),
              _RoleDetailSection(
                title: strings.prompt,
                body: role.prompt(language),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RoleDetailSection extends StatelessWidget {
  const _RoleDetailSection({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(body, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _RoleBadge extends StatelessWidget {
  const _RoleBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _HistoryPage extends StatelessWidget {
  const _HistoryPage({
    required this.runs,
    required this.loadingRuns,
    required this.error,
    required this.onRefresh,
  });

  final List<RunSummary> runs;
  final bool loadingRuns;
  final String? error;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 22, 18, 24),
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                strings.history,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: palette.textPrimary,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            IconButton(
              tooltip: strings.refresh,
              onPressed: loadingRuns ? null : onRefresh,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          strings.historyIntro,
          style: Theme.of(context).textTheme.bodySmall,
        ),
        if (error != null) ...[
          const SizedBox(height: 12),
          Text(error!, style: TextStyle(color: palette.danger)),
        ],
        const SizedBox(height: 16),
        if (loadingRuns)
          const Center(child: CircularProgressIndicator())
        else if (runs.isEmpty)
          _Panel(
            child: Text(
              strings.noActiveRuns,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          )
        else
          for (final group in _historyGroups(strings))
            _HistoryRunGroup(
              title: group.title,
              runs: runs
                  .where((run) => group.statuses.contains(run.status))
                  .toList(growable: false),
            ),
      ],
    );
  }
}

class _HistoryRunGroup extends StatelessWidget {
  const _HistoryRunGroup({required this.title, required this.runs});

  final String title;
  final List<RunSummary> runs;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    if (runs.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(color: palette.accent),
            ),
            const SizedBox(height: 10),
            for (final run in runs)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _RunSummaryRow(run: run),
              ),
          ],
        ),
      ),
    );
  }
}

class _HistoryGroupSpec {
  const _HistoryGroupSpec({required this.title, required this.statuses});

  final String title;
  final Set<String> statuses;
}

List<_HistoryGroupSpec> _historyGroups(AppStrings strings) {
  return [
    _HistoryGroupSpec(title: strings.running, statuses: {'running', 'queued'}),
    _HistoryGroupSpec(
      title: strings.completed,
      statuses: {'completed', 'finished'},
    ),
    _HistoryGroupSpec(title: strings.interrupted, statuses: {'interrupted'}),
    _HistoryGroupSpec(title: strings.failed, statuses: {'failed'}),
  ];
}

class _AgentRoleTemplate {
  const _AgentRoleTemplate({
    required this.zhName,
    required this.enName,
    required this.zhSummary,
    required this.enSummary,
    required this.zhHarness,
    required this.enHarness,
    required this.zhMemory,
    required this.enMemory,
    required this.zhPrompt,
    required this.enPrompt,
    required this.icon,
    required this.color,
    required this.editable,
  });

  final String zhName;
  final String enName;
  final String zhSummary;
  final String enSummary;
  final String zhHarness;
  final String enHarness;
  final String zhMemory;
  final String enMemory;
  final String zhPrompt;
  final String enPrompt;
  final IconData icon;
  final Color color;
  final bool editable;

  String name(AppLanguage language) =>
      language == AppLanguage.zh ? zhName : enName;

  String summary(AppLanguage language) =>
      language == AppLanguage.zh ? zhSummary : enSummary;

  String harness(AppLanguage language) =>
      language == AppLanguage.zh ? zhHarness : enHarness;

  String memory(AppLanguage language) =>
      language == AppLanguage.zh ? zhMemory : enMemory;

  String prompt(AppLanguage language) =>
      language == AppLanguage.zh ? zhPrompt : enPrompt;
}

const _roleTemplates = [
  _AgentRoleTemplate(
    zhName: '狼人',
    enName: 'Werewolf',
    zhSummary: '夜间协同击杀，白天伪装成好人并推动错误票型。',
    enSummary:
        'Coordinates the night kill and blends into town discussion during the day.',
    zhHarness: '读取同伴、夜间行动窗口、公开发言和票型；隐藏信息只暴露给合法狼人视角。',
    enHarness:
        'Reads packmates, night action windows, public speech, and votes; hidden data stays role-scoped.',
    zhMemory: '保留同伴身份、已暴露嫌疑、白天发言策略和关键投票线索。',
    enMemory:
        'Stores packmates, suspicion pressure, day-speech strategy, and key voting clues.',
    zhPrompt: '强调伪装、协作和风险控制；不得泄漏系统或非法夜间信息。',
    enPrompt:
        'Prioritizes deception, coordination, and risk control without leaking illegal hidden information.',
    icon: Icons.dark_mode_rounded,
    color: WerewolfAppTheme.danger,
    editable: true,
  ),
  _AgentRoleTemplate(
    zhName: '预言家',
    enName: 'Seer',
    zhSummary: '夜间查验阵营，白天管理信息释放和警徽流。',
    enSummary:
        'Checks alignment at night and manages claim timing during the day.',
    zhHarness: '接收查验窗口、查验结果、公开讨论和投票上下文；查验结果只给当前席位。',
    enHarness:
        'Receives check windows, check results, public discussion, and voting context; results are seat-private.',
    zhMemory: '保存查验目标、查验结果、警徽流意图和发言可信度判断。',
    enMemory:
        'Stores checked targets, results, claim plan, and credibility judgments.',
    zhPrompt: '强调信息价值最大化、避免过早暴露，并在必要时给出明确归票。',
    enPrompt:
        'Maximizes information value, avoids premature exposure, and gives clear voting guidance when needed.',
    icon: Icons.visibility_rounded,
    color: WerewolfAppTheme.seer,
    editable: true,
  ),
  _AgentRoleTemplate(
    zhName: '女巫',
    enName: 'Witch',
    zhSummary: '管理解药和毒药，依据死亡信息与公开讨论决定收益。',
    enSummary:
        'Manages save and poison decisions using death information and table talk.',
    zhHarness: '读取夜间救/毒行动窗口、死亡提示、公开讨论和历史票型。',
    enHarness:
        'Reads save/poison action windows, death notices, public talk, and vote history.',
    zhMemory: '保存药品状态、救人/毒人理由、疑似强神和狼坑列表。',
    enMemory:
        'Stores potion state, action rationale, suspected power roles, and wolf candidates.',
    zhPrompt: '强调药品稀缺性和可解释决策；非法目标交由服务器拒绝。',
    enPrompt:
        'Treats potions as scarce and decisions as explainable; illegal targets are rejected by the server.',
    icon: Icons.science_rounded,
    color: WerewolfAppTheme.witch,
    editable: true,
  ),
  _AgentRoleTemplate(
    zhName: '猎人',
    enName: 'Hunter',
    zhSummary: '死亡时可能开枪，白天用威慑力参与归票。',
    enSummary: 'May shoot on death and uses that pressure to shape day voting.',
    zhHarness: '读取开枪窗口、死亡状态、公开讨论和个人嫌疑排序。',
    enHarness:
        'Reads shot windows, death state, public discussion, and personal suspicion ranking.',
    zhMemory: '保存可开枪状态、目标排序、被攻击原因和遗言策略。',
    enMemory:
        'Stores shot availability, target ranking, pressure reasons, and final-word strategy.',
    zhPrompt: '强调克制、明确理由和防止被狼队诱导带走好人。',
    enPrompt:
        'Emphasizes restraint, explicit reasoning, and avoiding baited shots on town.',
    icon: Icons.gps_fixed_rounded,
    color: WerewolfAppTheme.accent,
    editable: false,
  ),
  _AgentRoleTemplate(
    zhName: '村民',
    enName: 'Villager',
    zhSummary: '没有夜间能力，依赖发言、票型和逻辑寻找狼人。',
    enSummary:
        'Has no night power and relies on speech, votes, and logic to find wolves.',
    zhHarness: '仅读取公开讨论、投票、死亡公告和自己的行动窗口。',
    enHarness:
        'Reads only public discussion, votes, death notices, and the seat action window.',
    zhMemory: '保存发言矛盾、投票变化、可信玩家和重点怀疑对象。',
    enMemory:
        'Stores contradictions, vote changes, trusted players, and main suspects.',
    zhPrompt: '强调公开推理、主动发言和不使用任何隐藏信息。',
    enPrompt:
        'Prioritizes public reasoning, active speech, and never using hidden information.',
    icon: Icons.groups_rounded,
    color: WerewolfAppTheme.villager,
    editable: false,
  ),
  _AgentRoleTemplate(
    zhName: '守卫',
    enName: 'Guard',
    zhSummary: '夜间守护玩家，通过轮次节奏保护关键身份。',
    enSummary:
        'Protects one player at night and times guards around important roles.',
    zhHarness: '读取守护窗口、公开身份压力、死亡节奏和上一轮守护约束。',
    enHarness:
        'Reads guard windows, public role pressure, death rhythm, and previous guard constraints.',
    zhMemory: '保存守护历史、疑似强神、狼刀倾向和不能连续守护的约束。',
    enMemory:
        'Stores guard history, suspected power roles, kill tendencies, and repeat-guard constraints.',
    zhPrompt: '强调轮次收益、避免机械守人，并解释守护选择。',
    enPrompt:
        'Optimizes round value, avoids mechanical protection, and explains guard choices.',
    icon: Icons.shield_rounded,
    color: Color(0xFF8BD3DD),
    editable: false,
  ),
];

class _RoomPage extends StatelessWidget {
  const _RoomPage({
    required this.controller,
    required this.needsIdentityConfirm,
    required this.onBackToMatches,
    required this.onEnterRoom,
  });

  final SessionController? controller;
  final bool needsIdentityConfirm;
  final VoidCallback onBackToMatches;
  final VoidCallback onEnterRoom;

  @override
  Widget build(BuildContext context) {
    final active = controller;
    if (active == null) {
      final strings = AppLanguageScope.of(context);
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.event_seat_outlined, size: 42),
              const SizedBox(height: 14),
              Text(
                strings.emptyRoomTitle,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(
                strings.emptyRoomBody,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      );
    }
    if (needsIdentityConfirm) {
      return _IdentityConfirmPane(
        controller: active,
        onBackToMatches: onBackToMatches,
        onEnterRoom: onEnterRoom,
      );
    }
    return LiveRoomScreen(controller: active, onBack: onBackToMatches);
  }
}

class _IdentityConfirmPane extends StatelessWidget {
  const _IdentityConfirmPane({
    required this.controller,
    required this.onBackToMatches,
    required this.onEnterRoom,
  });

  final SessionController controller;
  final VoidCallback onBackToMatches;
  final VoidCallback onEnterRoom;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final session = controller.session;
    final seat = session?.seatId.toUpperCase() ?? 'UNKNOWN';
    final perspective = session?.perspective ?? 'role-safe';
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: _FloatingBackButton(onPressed: onBackToMatches),
          ),
          const Spacer(),
          Text(
            strings.seatIdentity(seat),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: palette.textPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 12),
          Text(strings.participantPerspective),
          const SizedBox(height: 8),
          Text(
            'Perspective: $perspective',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 18),
          _Panel(child: Text(strings.legalInfoOnly)),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: FilledButton(
              onPressed: onEnterRoom,
              child: Text(strings.enterRoom),
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsPage extends StatefulWidget {
  const _SettingsPage({
    required this.settingsController,
    required this.updateRepository,
  });

  final AppSettingsController settingsController;
  final UpdateRepository updateRepository;

  @override
  State<_SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<_SettingsPage> {
  late final TextEditingController _baseUrl;
  late final TextEditingController _seatId;
  late final TextEditingController _joinCode;
  String? _error;

  AppSettingsController get _settings => widget.settingsController;
  UpdateRepository get _updates => widget.updateRepository;

  @override
  void initState() {
    super.initState();
    _baseUrl = TextEditingController(text: _settings.baseUri.toString());
    _seatId = TextEditingController(text: _settings.seatId);
    _joinCode = TextEditingController(text: _settings.joinCode);
    _updates.addListener(_handleUpdateChanged);
  }

  @override
  void dispose() {
    _updates.removeListener(_handleUpdateChanged);
    _baseUrl.dispose();
    _seatId.dispose();
    _joinCode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 24),
      children: [
        Text(
          strings.settings,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: palette.textPrimary,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 18),
        _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.languageLabel,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 10),
              const _LanguageToggle(),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.appearance,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 10),
              const _AppearanceSelector(),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.connection,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _baseUrl,
                keyboardType: TextInputType.url,
                decoration: InputDecoration(labelText: strings.baseUrl),
              ),
              const SizedBox(height: 10),
              Text(
                strings.quickServer,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              _buildServerPresetChips(strings),
              const SizedBox(height: 10),
              TextField(
                controller: _seatId,
                textCapitalization: TextCapitalization.characters,
                decoration: InputDecoration(labelText: strings.seatId),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _joinCode,
                decoration: InputDecoration(labelText: strings.joinCode),
              ),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(_error!, style: TextStyle(color: palette.danger)),
              ],
              const SizedBox(height: 12),
              Text(
                strings.phoneLanHint,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _save,
                  child: Text(strings.saveConnection),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _Panel(child: _buildUpdatePanel(context, strings)),
        const SizedBox(height: 14),
        _Panel(child: _buildProviderPanel(context, strings)),
      ],
    );
  }

  Widget _buildUpdatePanel(BuildContext context, AppStrings strings) {
    final palette = WerewolfAppTheme.colors(context);
    final state = _updates.state;
    final manifest = state.availableUpdate;
    final progress = state.progress;
    final latestLogs = state.logs.take(4).toList(growable: false);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(strings.updates, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(
          '${strings.currentVersion}: ${BuildInfo.appVersion} · ${BuildInfo.updateChannel}',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        if (state.message != null) ...[
          const SizedBox(height: 10),
          Text(
            state.message!,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: state.status == UpdateStatus.error
                  ? palette.danger
                  : palette.textPrimary,
            ),
          ),
        ],
        if (state.errorMessage != null &&
            state.errorMessage != state.message) ...[
          const SizedBox(height: 8),
          Text(state.errorMessage!, style: TextStyle(color: palette.danger)),
        ],
        if (manifest != null) ...[
          const SizedBox(height: 12),
          Text(
            '${strings.availableVersion}: ${manifest.versionName} (${manifest.versionCode})',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          Text(
            manifest.releaseNotes,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
        if (progress != null) ...[
          const SizedBox(height: 12),
          LinearProgressIndicator(value: progress.clamp(0.0, 1.0)),
        ],
        if (latestLogs.isNotEmpty) ...[
          const SizedBox(height: 12),
          for (final log in latestLogs)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                log.message,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: log.level == UpdateLogLevel.error
                      ? palette.danger
                      : palette.textMuted,
                ),
              ),
            ),
        ],
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: state.isBusy ? null : _updates.checkNow,
                icon: const Icon(Icons.system_update_alt_rounded),
                label: Text(strings.checkUpdates),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton.icon(
                onPressed: state.isBusy || manifest == null
                    ? null
                    : _updates.downloadAndInstall,
                icon: const Icon(Icons.download_rounded),
                label: Text(strings.downloadInstall),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildProviderPanel(BuildContext context, AppStrings strings) {
    final palette = WerewolfAppTheme.colors(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.hub_outlined, color: palette.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                strings.providerSettings,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            _RoleBadge(
              label: strings.providerSettingsPending,
              color: palette.textMuted,
            ),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          strings.providerSettingsBody,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  void _save() {
    final strings = AppLanguageScope.of(context);
    final baseUri = Uri.tryParse(_baseUrl.text.trim());
    if (baseUri == null || !baseUri.hasScheme) {
      setState(() => _error = strings.invalidBaseUrl);
      return;
    }
    _settings
      ..setBaseUri(baseUri)
      ..setSeatId(_seatId.text)
      ..setJoinCode(_joinCode.text);
    setState(() => _error = null);
  }

  Widget _buildServerPresetChips(AppStrings strings) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final preset in ObserverServerPreset.values)
          ChoiceChip(
            label: Text(strings.serverPresetLabel(preset)),
            selected: _baseUrl.text.trim() == preset.baseUri.toString(),
            onSelected: (_) => _applyServerPreset(preset),
          ),
      ],
    );
  }

  void _applyServerPreset(ObserverServerPreset preset) {
    final baseUri = preset.baseUri;
    setState(() {
      _baseUrl.text = baseUri.toString();
      _error = null;
    });
    _settings.setBaseUri(baseUri);
  }

  void _handleUpdateChanged() {
    if (!mounted) return;
    setState(() {});
  }
}

class _AppearanceQuickToggle extends StatelessWidget {
  const _AppearanceQuickToggle();

  @override
  Widget build(BuildContext context) {
    final settings = AppLanguageScope.maybeControllerOf(context);
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final appearance = settings?.appearance ?? AppAppearance.night;
    final isNight = appearance == AppAppearance.night;
    return SizedBox(
      width: 44,
      height: 44,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: palette.control.withValues(alpha: palette.isDay ? 0.88 : 0.72),
          borderRadius: BorderRadius.circular(999),
          boxShadow: [
            BoxShadow(
              color: palette.shadow,
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: IconButton(
          key: const Key('appearance-quick-toggle'),
          tooltip: isNight
              ? strings.switchToDayStyle
              : strings.switchToNightStyle,
          onPressed: settings?.toggleAppearance,
          icon: Icon(
            isNight ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
            size: 21,
            color: palette.textPrimary,
          ),
        ),
      ),
    );
  }
}

class _FloatingBackButton extends StatelessWidget {
  const _FloatingBackButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return SizedBox(
      width: 44,
      height: 44,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: palette.surface.withValues(alpha: palette.isDay ? 0.92 : 0.78),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: palette.border.withValues(alpha: 0.7)),
          boxShadow: [
            BoxShadow(
              color: palette.shadow,
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: IconButton(
          key: const Key('flow-back-button'),
          tooltip: MaterialLocalizations.of(context).backButtonTooltip,
          onPressed: onPressed,
          icon: Icon(
            Icons.chevron_left_rounded,
            size: 26,
            color: palette.textPrimary,
          ),
        ),
      ),
    );
  }
}

class _FloatingTabBar extends StatelessWidget {
  const _FloatingTabBar({
    required this.selectedIndex,
    required this.onSelected,
    required this.items,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final List<_TabBarItem> items;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 4, 18, 12),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: palette.surface.withValues(
              alpha: palette.isDay ? 0.96 : 0.9,
            ),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: palette.border.withValues(alpha: 0.72)),
            boxShadow: [
              BoxShadow(
                color: palette.shadow,
                blurRadius: 24,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(6),
            child: Row(
              children: [
                for (var index = 0; index < items.length; index++)
                  Expanded(
                    child: _FloatingTabButton(
                      item: items[index],
                      selected: selectedIndex == index,
                      onTap: () => onSelected(index),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _FloatingTabButton extends StatelessWidget {
  const _FloatingTabButton({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final _TabBarItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    final color = selected ? palette.textPrimary : palette.textMuted;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        curve: Curves.easeOutCubic,
        height: 54,
        decoration: BoxDecoration(
          color: selected ? palette.controlSelected : Colors.transparent,
          borderRadius: BorderRadius.circular(22),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              selected ? item.selectedIcon : item.icon,
              size: 21,
              color: color,
            ),
            const SizedBox(height: 3),
            Text(
              item.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: color,
                fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                letterSpacing: 0,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TabBarItem {
  const _TabBarItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });

  final IconData icon;
  final IconData selectedIcon;
  final String label;
}

class _AppearanceSelector extends StatelessWidget {
  const _AppearanceSelector();

  @override
  Widget build(BuildContext context) {
    final controller = AppLanguageScope.maybeControllerOf(context);
    final appearance = controller?.appearance ?? AppAppearance.night;
    final strings = AppLanguageScope.of(context);
    return SegmentedButton<AppAppearance>(
      showSelectedIcon: false,
      segments: [
        ButtonSegment(
          value: AppAppearance.day,
          icon: const Icon(Icons.light_mode_rounded),
          label: Text(strings.dayStyle),
        ),
        ButtonSegment(
          value: AppAppearance.night,
          icon: const Icon(Icons.dark_mode_rounded),
          label: Text(strings.nightStyle),
        ),
      ],
      selected: {appearance},
      onSelectionChanged: (selection) {
        controller?.setAppearance(selection.first);
      },
    );
  }
}

class _LanguageToggle extends StatelessWidget {
  const _LanguageToggle();

  @override
  Widget build(BuildContext context) {
    final controller = AppLanguageScope.maybeControllerOf(context);
    final language = controller?.language ?? AppLanguage.zh;
    return SegmentedButton<AppLanguage>(
      showSelectedIcon: false,
      segments: const [
        ButtonSegment(value: AppLanguage.zh, label: Text('中文')),
        ButtonSegment(value: AppLanguage.en, label: Text('EN')),
      ],
      selected: {language},
      onSelectionChanged: (selection) {
        controller?.setLanguage(selection.first);
      },
    );
  }
}

class _ServerCard extends StatelessWidget {
  const _ServerCard({
    required this.loadingRuns,
    required this.runsError,
    required this.onRefresh,
  });

  final bool loadingRuns;
  final String? runsError;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final settings = AppLanguageScope.maybeControllerOf(context);
    final palette = WerewolfAppTheme.colors(context);
    final status = loadingRuns
        ? strings.loading
        : (runsError == null ? strings.connected : strings.offline);
    return _Panel(
      child: Row(
        children: [
          Icon(
            runsError == null
                ? Icons.cloud_done_outlined
                : Icons.cloud_off_outlined,
            color: runsError == null ? palette.witch : palette.danger,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${strings.server} · $status'),
                const SizedBox(height: 4),
                Text(
                  settings?.baseUri.toString() ?? '',
                  style: Theme.of(context).textTheme.bodySmall,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: strings.refresh,
            onPressed: loadingRuns ? null : onRefresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
    );
  }
}

class _RunCard extends StatelessWidget {
  const _RunCard({
    required this.run,
    required this.joining,
    required this.onJoin,
  });

  final RunSummary run;
  final bool joining;
  final VoidCallback onJoin;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _RunSummaryRow(run: run),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 44,
            child: FilledButton(
              onPressed: joining ? null : onJoin,
              child: Text(joining ? strings.joining : strings.joinRun),
            ),
          ),
        ],
      ),
    );
  }
}

class _RunSummaryRow extends StatelessWidget {
  const _RunSummaryRow({required this.run});

  final RunSummary run;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    return Row(
      children: [
        const Icon(Icons.radio_button_checked_rounded, size: 16),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            run.runId,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          strings.statusLabel(run.status),
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: palette.border),
      ),
      child: Padding(padding: const EdgeInsets.all(16), child: child),
    );
  }
}
