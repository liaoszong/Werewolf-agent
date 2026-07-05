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
        onBackToMatches: () =>
            setState(() => _homeFlow = _HomeFlow.matchPicker),
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
    final controller = widget.sessionControllerFactory(_settings.baseUri);
    _sessionController?.dispose();
    setState(() {
      _sessionController = controller;
      _joining = true;
      _joinError = null;
      _selectedIndex = 0;
      _homeFlow = _HomeFlow.liveRoom;
    });
    await controller.joinAndLoad(
      runId: runId,
      seatId: _settings.seatId,
      joinCode: _settings.joinCode,
    );
    if (!mounted) return;
    if (controller.connectionStatus == ConnectionStatus.connected) {
      setState(() {
        _joining = false;
      });
      return;
    }
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
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 24),
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _FloatingBackButton(onPressed: onBack),
            const SizedBox(width: 12),
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

class _RolesPage extends StatefulWidget {
  const _RolesPage();

  @override
  State<_RolesPage> createState() => _RolesPageState();
}

class _RolesPageState extends State<_RolesPage> {
  late final Map<String, String> _selectedPresetByRole = {
    for (final role in _roleTemplates) role.roleId: role.defaultPresetId,
  };
  final Map<String, Map<String, _LocalizedText>> _settingSelectionsByRole = {};

  String _selectedPresetId(_AgentRoleTemplate role) {
    return _selectedPresetByRole[role.roleId] ?? role.defaultPresetId;
  }

  bool _isDirty(_AgentRoleTemplate role) {
    return _selectedPresetId(role) != role.defaultPresetId ||
        (_settingSelectionsByRole[role.roleId]?.isNotEmpty ?? false);
  }

  void _selectPreset(_AgentRoleTemplate role, String presetId) {
    setState(() {
      _selectedPresetByRole[role.roleId] = presetId;
    });
  }

  void _selectSetting(
    _AgentRoleTemplate role,
    String settingId,
    _LocalizedText value,
  ) {
    setState(() {
      final settings = _settingSelectionsByRole.putIfAbsent(
        role.roleId,
        () => {},
      );
      settings[settingId] = value;
    });
  }

  void _openRole(BuildContext context, _AgentRoleTemplate role) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => _RolePolicyDetailPage(
          role: role,
          selectedPresetId: _selectedPresetId(role),
          selectedSettings: Map.unmodifiable(
            _settingSelectionsByRole[role.roleId] ??
                const <String, _LocalizedText>{},
          ),
          onPresetChanged: (presetId) => _selectPreset(role, presetId),
          onSettingChanged: (settingId, value) =>
              _selectSetting(role, settingId, value),
        ),
      ),
    );
  }

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
        _Panel(
          child: Row(
            children: [
              Icon(Icons.rule_folder_rounded, color: palette.accent),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      strings.rolePolicyPackLabel,
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      strings.rolePolicyPackDraft,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ],
                ),
              ),
              _RoleBadge(label: strings.localDraftBadge, color: palette.accent),
            ],
          ),
        ),
        const SizedBox(height: 14),
        GridView.builder(
          key: const Key('role-policy-grid'),
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 0.88,
          ),
          itemCount: _roleTemplates.length,
          itemBuilder: (context, index) {
            final role = _roleTemplates[index];
            return _RolePolicyCard(
              role: role,
              preset: role.presetById(_selectedPresetId(role)),
              dirty: _isDirty(role),
              onTap: () => _openRole(context, role),
            );
          },
        ),
      ],
    );
  }
}

class _RolePolicyCard extends StatelessWidget {
  const _RolePolicyCard({
    required this.role,
    required this.preset,
    required this.dirty,
    required this.onTap,
  });

  final _AgentRoleTemplate role;
  final _RolePolicyPreset preset;
  final bool dirty;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final language = strings.appLanguage;
    final palette = WerewolfAppTheme.colors(context);
    final status = dirty ? strings.localDraftBadge : strings.defaultDraftBadge;
    return Semantics(
      button: true,
      label: '${role.name(language)} ${strings.strategyOverview}',
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 20,
                    backgroundColor: role.color.withValues(alpha: 0.16),
                    foregroundColor: role.color,
                    child: Icon(role.icon, size: 22),
                  ),
                  const Spacer(),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: palette.textMuted,
                    size: 22,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                role.name(language),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(
                preset.summary.text(language),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const Spacer(),
              Text(
                status,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall,
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: _RoleBadge(
                  label: preset.tendency.text(language),
                  color: dirty ? palette.accent : role.color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RolePolicyDetailPage extends StatefulWidget {
  const _RolePolicyDetailPage({
    required this.role,
    required this.selectedPresetId,
    required this.selectedSettings,
    required this.onPresetChanged,
    required this.onSettingChanged,
  });

  final _AgentRoleTemplate role;
  final String selectedPresetId;
  final Map<String, _LocalizedText> selectedSettings;
  final ValueChanged<String> onPresetChanged;
  final void Function(String settingId, _LocalizedText value) onSettingChanged;

  @override
  State<_RolePolicyDetailPage> createState() => _RolePolicyDetailPageState();
}

class _RolePolicyDetailPageState extends State<_RolePolicyDetailPage> {
  late String _selectedPresetId = widget.selectedPresetId;
  late final Map<String, _LocalizedText> _settingSelections = Map.of(
    widget.selectedSettings,
  );

  _AgentRoleTemplate get role => widget.role;

  bool get _dirty {
    return _selectedPresetId != role.defaultPresetId ||
        _settingSelections.isNotEmpty;
  }

  _RolePolicyPreset get _selectedPreset => role.presetById(_selectedPresetId);

  void _selectPreset(String presetId) {
    setState(() {
      _selectedPresetId = presetId;
    });
    widget.onPresetChanged(presetId);
  }

  _LocalizedText _settingValue(_PolicySetting setting) {
    return _settingSelections[setting.id] ?? setting.value;
  }

  void _selectSetting(_PolicySetting setting, _LocalizedText choice) {
    setState(() {
      _settingSelections[setting.id] = choice;
    });
    widget.onSettingChanged(setting.id, choice);
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final language = strings.appLanguage;
    final palette = WerewolfAppTheme.colors(context);
    return Scaffold(
      key: const Key('role-policy-detail-page'),
      appBar: AppBar(
        backgroundColor: palette.background,
        foregroundColor: palette.textPrimary,
        elevation: 0,
        title: Text(role.name(language)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: _RoleBadge(
                label: _dirty
                    ? strings.localDraftBadge
                    : strings.defaultDraftBadge,
                color: _dirty ? palette.accent : palette.textMuted,
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 96),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    radius: 28,
                    backgroundColor: role.color.withValues(alpha: 0.16),
                    foregroundColor: role.color,
                    child: Icon(role.icon, size: 30),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          strings.rolePolicyPackDraft,
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          role.summary(language),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '当前策略：${_selectedPreset.name.text(language)}',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        if (_dirty) ...[
                          const SizedBox(height: 6),
                          Text(
                            strings.unsavedDraft,
                            style: Theme.of(context).textTheme.labelSmall
                                ?.copyWith(color: palette.accent),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              _RoleDetailSection(
                title: strings.roleBoundary,
                child: _RoleParagraphs([
                  role.boundary(language),
                  strings.engineAuthority,
                ]),
              ),
              _RoleDetailSection(
                title: strings.strategyOverview,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _selectedPreset.description.text(language),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final preset in role.presets)
                          ChoiceChip(
                            label: Text(preset.name.text(language)),
                            selected: preset.id == _selectedPresetId,
                            onSelected: (_) => _selectPreset(preset.id),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              _RoleDetailSection(
                title: strings.decisionTendencies,
                child: Column(
                  children: [
                    for (final setting in role.decisionTendencies)
                      _SettingRow(
                        setting: setting,
                        value: _settingValue(setting),
                        onTap: () => _showSettingSheet(context, setting),
                      ),
                  ],
                ),
              ),
              _RoleDetailSection(
                title: strings.actionStrategy,
                child: Column(
                  children: [
                    for (final setting in role.actionStrategies)
                      _SettingRow(
                        setting: setting,
                        value: _settingValue(setting),
                        onTap: () => _showSettingSheet(context, setting),
                      ),
                  ],
                ),
              ),
              _RoleDetailSection(
                title: strings.evidenceContext,
                child: Column(
                  children: [
                    for (final setting in role.evidencePreferences)
                      _SettingRow(
                        setting: setting,
                        value: _settingValue(setting),
                        onTap: () => _showSettingSheet(context, setting),
                      ),
                  ],
                ),
              ),
              _RoleDetailSection(
                title: strings.runtimeComposition,
                child: _RoleParagraphs([
                  role.runtimeComposition(language),
                  strings.localPreviewOnly,
                ]),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: null,
                  icon: const Icon(Icons.visibility_rounded),
                  label: Text(strings.localPreviewAction),
                  style: FilledButton.styleFrom(
                    disabledBackgroundColor: palette.control,
                    disabledForegroundColor: palette.textMuted,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _showSettingSheet(
    BuildContext context,
    _PolicySetting setting,
  ) async {
    final strings = AppLanguageScope.of(context);
    final language = strings.appLanguage;
    final palette = WerewolfAppTheme.colors(context);
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: palette.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  setting.title.text(language),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                for (final choice in setting.choices)
                  ListTile(
                    leading: Icon(
                      _settingValue(setting) == choice
                          ? Icons.radio_button_checked_rounded
                          : Icons.radio_button_unchecked_rounded,
                      color: _settingValue(setting) == choice
                          ? palette.accent
                          : palette.textMuted,
                    ),
                    title: Text(choice.text(language)),
                    onTap: () {
                      _selectSetting(setting, choice);
                      Navigator.of(context).pop();
                    },
                  ),
                const SizedBox(height: 8),
                Text(
                  setting.explanation.text(language),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                Text(
                  strings.engineAuthority,
                  style: Theme.of(context).textTheme.labelSmall,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _RoleDetailSection extends StatelessWidget {
  const _RoleDetailSection({required this.title, required this.child});

  final String title;
  final Widget child;

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
            child,
          ],
        ),
      ),
    );
  }
}

class _RoleParagraphs extends StatelessWidget {
  const _RoleParagraphs(this.paragraphs);

  final List<String> paragraphs;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final paragraph in paragraphs)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              paragraph,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
      ],
    );
  }
}

class _SettingRow extends StatelessWidget {
  const _SettingRow({
    required this.setting,
    required this.value,
    required this.onTap,
  });

  final _PolicySetting setting;
  final _LocalizedText value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final language = AppLanguageScope.of(context).appLanguage;
    final palette = WerewolfAppTheme.colors(context);
    return Semantics(
      button: true,
      label: setting.title.text(language),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      setting.title.text(language),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      value.text(language),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.keyboard_arrow_right_rounded,
                color: palette.textMuted,
              ),
            ],
          ),
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

class _LocalizedText {
  const _LocalizedText(this.zh, this.en);

  final String zh;
  final String en;

  String text(AppLanguage language) => language == AppLanguage.zh ? zh : en;

  @override
  bool operator ==(Object other) {
    return other is _LocalizedText && other.zh == zh && other.en == en;
  }

  @override
  int get hashCode => Object.hash(zh, en);
}

class _RolePolicyPreset {
  const _RolePolicyPreset({
    required this.id,
    required this.name,
    required this.summary,
    required this.tendency,
    required this.description,
  });

  final String id;
  final _LocalizedText name;
  final _LocalizedText summary;
  final _LocalizedText tendency;
  final _LocalizedText description;
}

class _PolicySetting {
  const _PolicySetting({
    required this.id,
    required this.title,
    required this.value,
    required this.choices,
    required this.explanation,
  });

  final String id;
  final _LocalizedText title;
  final _LocalizedText value;
  final List<_LocalizedText> choices;
  final _LocalizedText explanation;
}

class _AgentRoleTemplate {
  const _AgentRoleTemplate({
    required this.roleId,
    required this.localizedName,
    required this.localizedSummary,
    required this.boundaryDescription,
    required this.runtimeCompositionDescription,
    required this.defaultPresetId,
    required this.presets,
    required this.decisionTendencies,
    required this.actionStrategies,
    required this.evidencePreferences,
    required this.icon,
    required this.color,
  });

  final String roleId;
  final _LocalizedText localizedName;
  final _LocalizedText localizedSummary;
  final _LocalizedText boundaryDescription;
  final _LocalizedText runtimeCompositionDescription;
  final String defaultPresetId;
  final List<_RolePolicyPreset> presets;
  final List<_PolicySetting> decisionTendencies;
  final List<_PolicySetting> actionStrategies;
  final List<_PolicySetting> evidencePreferences;
  final IconData icon;
  final Color color;

  String nameText(AppLanguage language) => localizedName.text(language);

  String summaryText(AppLanguage language) => localizedSummary.text(language);

  String boundaryText(AppLanguage language) =>
      boundaryDescription.text(language);

  String runtimeCompositionText(AppLanguage language) =>
      runtimeCompositionDescription.text(language);

  String name(AppLanguage language) => nameText(language);

  String summary(AppLanguage language) => summaryText(language);

  String boundary(AppLanguage language) => boundaryText(language);

  String runtimeComposition(AppLanguage language) =>
      runtimeCompositionText(language);

  _RolePolicyPreset presetById(String presetId) {
    return presets.firstWhere(
      (preset) => preset.id == presetId,
      orElse: () => presets.firstWhere(
        (preset) => preset.id == defaultPresetId,
        orElse: () => presets.first,
      ),
    );
  }
}

const _low = _LocalizedText('低', 'Low');
const _medium = _LocalizedText('中', 'Medium');
const _high = _LocalizedText('高', 'High');
const _recentOnly = _LocalizedText('优先近期', 'Recent first');
const _recentPlusTargeted = _LocalizedText(
  '近期 + 关键历史',
  'Recent plus targeted history',
);
const _evidenceDense = _LocalizedText(
  '票型与身份声明优先',
  'Vote and claim evidence first',
);
const _playerOnly = _LocalizedText('只标玩家', 'Player only');
const _playerAndRound = _LocalizedText('玩家和轮次', 'Player and round');
const _playerRoundEvidence = _LocalizedText(
  '玩家、轮次和证据类型',
  'Player, round, and evidence type',
);
const _conservative = _LocalizedText('保守', 'Conservative');
const _balanced = _LocalizedText('平衡', 'Balanced');
const _assertive = _LocalizedText('主动', 'Assertive');
const _gentlePressure = _LocalizedText('温和施压', 'Gentle pressure');
const _leadDiscussion = _LocalizedText('主动带讨论', 'Lead discussion');
const _explainEvidence = _LocalizedText('解释证据', 'Explain evidence');
const _claimUnderPressure = _LocalizedText('压力下再声明', 'Claim under pressure');
const _proactiveClaim = _LocalizedText('主动声明', 'Proactive claim');
const _avoidClaim = _LocalizedText('避免声明', 'Avoid claim');

const _roleTemplates = [
  _AgentRoleTemplate(
    roleId: 'werewolf',
    localizedName: _LocalizedText('狼人', 'Werewolf'),
    localizedSummary: _LocalizedText(
      '隐藏团队身份，推动白天票型向有利方向发展。',
      'Hide team identity and steer daytime votes.',
    ),
    boundaryDescription: _LocalizedText(
      '夜间可参与狼人击杀，白天只能通过公开发言和投票影响局势。狼队信息只属于合法狼人视角。',
      'Can join the night kill and influence the day only through public speech and votes. Wolf-team information is wolf-entitled only.',
    ),
    runtimeCompositionDescription: _LocalizedText(
      '本策略只描述狼人身份打法。开局后会与座位人格、运行配置和本局状态组合，但不会把这些对象写进 RolePolicy。',
      'This policy describes werewolf play only. At launch it combines with seat personality, runtime config, and run state without storing those objects in RolePolicy.',
    ),
    defaultPresetId: 'balanced_control',
    presets: [
      _RolePolicyPreset(
        id: 'quiet_cover',
        name: _LocalizedText('保守潜伏', 'Quiet cover'),
        summary: _LocalizedText('保守潜伏策略', 'Quiet-cover policy'),
        tendency: _conservative,
        description: _LocalizedText(
          '降低存在感，优先自保，只在票型关键处轻推方向。',
          'Stay low-profile, preserve self, and nudge only key vote moments.',
        ),
      ),
      _RolePolicyPreset(
        id: 'balanced_control',
        name: _LocalizedText('平衡控场', 'Balanced control'),
        summary: _LocalizedText('平衡控场策略', 'Balanced-control policy'),
        tendency: _balanced,
        description: _LocalizedText(
          '在不暴露狼队的前提下，围绕公开矛盾和票型温和控场。',
          'Control the table through public contradictions and votes without exposing the team.',
        ),
      ),
      _RolePolicyPreset(
        id: 'aggressive_pressure',
        name: _LocalizedText('激进带节奏', 'Aggressive pressure'),
        summary: _LocalizedText('激进带节奏策略', 'Aggressive pressure policy'),
        tendency: _LocalizedText('激进', 'Aggressive'),
        description: _LocalizedText(
          '主动制造压力和转移焦点，接受更高暴露风险。',
          'Create pressure and redirect focus while accepting higher exposure risk.',
        ),
      ),
    ],
    decisionTendencies: [
      _PolicySetting(
        id: 'wolf_teamwork',
        title: _LocalizedText('队友协作', 'Teammate coordination'),
        value: _LocalizedText(
          '有限保护，必要时切割',
          'Limited protection with distancing',
        ),
        choices: [
          _LocalizedText('尽量保护队友', 'Protect teammates'),
          _LocalizedText('有条件保护', 'Conditionally protect'),
          _LocalizedText('有限保护，必要时切割', 'Limited protection with distancing'),
          _LocalizedText('优先隐藏自己', 'Prioritize self-cover'),
        ],
        explanation: _LocalizedText(
          '只影响个人发言和投票倾向，实际狼队计划属于运行期队伍状态。',
          'Affects personal speech and vote posture only; actual team plans belong to runtime team state.',
        ),
      ),
      _PolicySetting(
        id: 'wolf_claim',
        title: _LocalizedText('身份声明', 'Claim posture'),
        value: _claimUnderPressure,
        choices: [_avoidClaim, _claimUnderPressure, _proactiveClaim],
        explanation: _LocalizedText(
          '策略可以建议是否声明身份，但不能创造新的合法身份能力。',
          'Policy may guide claim timing, but cannot create legal role abilities.',
        ),
      ),
    ],
    actionStrategies: [
      _PolicySetting(
        id: 'wolf_kill_target',
        title: _LocalizedText('夜间目标优先级', 'Night target priority'),
        value: _LocalizedText('高威胁非狼优先', 'High-threat non-wolves first'),
        choices: [
          _LocalizedText('高威胁非狼优先', 'High-threat non-wolves first'),
          _LocalizedText('保护伪装路线', 'Protect cover story'),
          _LocalizedText('扰乱公开推理', 'Disrupt public reasoning'),
        ],
        explanation: _LocalizedText(
          '只影响击杀提案；最终合法目标和结算由服务器控制。',
          'Guides kill proposals only; legal targets and adjudication remain server-controlled.',
        ),
      ),
      _PolicySetting(
        id: 'wolf_vote_steering',
        title: _LocalizedText('白天归票方式', 'Day vote steering'),
        value: _gentlePressure,
        choices: [_explainEvidence, _gentlePressure, _leadDiscussion],
        explanation: _LocalizedText(
          '通过公开理由影响票型，不可读取非授权私有状态。',
          'Influences votes through public reasons without reading unauthorized private state.',
        ),
      ),
    ],
    evidencePreferences: [
      _PolicySetting(
        id: 'wolf_teammate_risk',
        title: _LocalizedText('队友风险关注', 'Teammate risk attention'),
        value: _high,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '仅狼人授权视角可使用；普通观察者和非狼玩家不可见。',
          'Wolf-entitled only; public observers and non-wolf players cannot see it.',
        ),
      ),
      _PolicySetting(
        id: 'wolf_history',
        title: _LocalizedText('发言历史读取', 'History preference'),
        value: _recentPlusTargeted,
        choices: [_recentOnly, _recentPlusTargeted, _evidenceDense],
        explanation: _LocalizedText(
          '只是 ContextSelector 偏好，预算和工具权限仍由运行契约决定。',
          'A ContextSelector preference only; budget and tool permission stay in runtime contracts.',
        ),
      ),
    ],
    icon: Icons.dark_mode_rounded,
    color: WerewolfAppTheme.danger,
  ),
  _AgentRoleTemplate(
    roleId: 'seer',
    localizedName: _LocalizedText('预言家', 'Seer'),
    localizedSummary: _LocalizedText(
      '查验阵营并决定何时公开信息带队。',
      'Checks alignment and chooses when to lead with information.',
    ),
    boundaryDescription: _LocalizedText(
      '夜间拥有查验窗口，查验结果只属于本席位；白天公开信息仍要通过发言和投票表达。',
      'Has night check windows and seat-private results; public influence still happens through speech and votes.',
    ),
    runtimeCompositionDescription: _LocalizedText(
      '本策略只描述预言家信息节奏。它不会绑定具体人格、模型、提示模板或本局记忆。',
      'This policy describes seer information cadence only. It does not bind personality, model, prompt template, or run memory.',
    ),
    defaultPresetId: 'steady_checks',
    presets: [
      _RolePolicyPreset(
        id: 'steady_checks',
        name: _LocalizedText('稳健验人', 'Steady checks'),
        summary: _LocalizedText('稳健验人策略', 'Steady-check policy'),
        tendency: _LocalizedText('稳健', 'Steady'),
        description: _LocalizedText(
          '优先查高影响、低可信玩家，证据链不足时避免过早跳出。',
          'Check high-impact low-trust players and avoid early exposure without enough evidence.',
        ),
      ),
      _RolePolicyPreset(
        id: 'forceful_lead',
        name: _LocalizedText('强势带队', 'Forceful lead'),
        summary: _LocalizedText('强势带队策略', 'Forceful-lead policy'),
        tendency: _assertive,
        description: _LocalizedText(
          '查验信息形成连续证据后主动归票，承受更高对跳压力。',
          'Lead votes once checks form a chain, accepting higher counterclaim pressure.',
        ),
      ),
      _RolePolicyPreset(
        id: 'hidden_role',
        name: _LocalizedText('隐藏身份', 'Hidden role'),
        summary: _LocalizedText('隐藏身份策略', 'Hidden-role policy'),
        tendency: _conservative,
        description: _LocalizedText(
          '先积累查验结果，除非局势危险否则不主动暴露身份。',
          'Accumulate check results and avoid exposing the role unless the table is in danger.',
        ),
      ),
    ],
    decisionTendencies: [
      _PolicySetting(
        id: 'seer_release',
        title: _LocalizedText('信息公开策略', 'Information release'),
        value: _LocalizedText('连续证据后主动带队', 'Lead after a check chain'),
        choices: [
          _LocalizedText('保留结果，等待压力', 'Hold results until pressured'),
          _LocalizedText('连续证据后主动带队', 'Lead after a check chain'),
          _LocalizedText('尽早建立可信度', 'Build credibility early'),
        ],
        explanation: _LocalizedText(
          '只影响公开节奏；查验结果的可见性仍由服务器决定。',
          'Guides public cadence only; result visibility remains server-owned.',
        ),
      ),
      _PolicySetting(
        id: 'seer_challenge',
        title: _LocalizedText('被质疑时应对', 'When challenged'),
        value: _LocalizedText('解释验人链', 'Explain check chain'),
        choices: [
          _LocalizedText('解释验人链', 'Explain check chain'),
          _LocalizedText('反问质疑来源', 'Question the challenger'),
          _LocalizedText('先稳住票型', 'Stabilize votes first'),
        ],
        explanation: _LocalizedText(
          '应对方式不能把 Belief 当成裁判事实。',
          'Response style cannot treat beliefs as adjudicated facts.',
        ),
      ),
    ],
    actionStrategies: [
      _PolicySetting(
        id: 'seer_check_target',
        title: _LocalizedText('验人对象', 'Check target'),
        value: _LocalizedText('高影响低可信', 'High impact and low trust'),
        choices: [
          _LocalizedText('高影响低可信', 'High impact and low trust'),
          _LocalizedText('票型摇摆位', 'Vote swing players'),
          _LocalizedText('公开对跳相关', 'Claim-conflict related'),
        ],
        explanation: _LocalizedText(
          '只指导目标提案；合法目标由行动窗口决定。',
          'Guides target proposals only; legal targets come from the action window.',
        ),
      ),
      _PolicySetting(
        id: 'seer_vote_threshold',
        title: _LocalizedText('归票置信度', 'Vote guidance confidence'),
        value: _medium,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '置信度是策略偏好，不是事实真值。',
          'Confidence is a policy preference, not engine truth.',
        ),
      ),
    ],
    evidencePreferences: [
      _PolicySetting(
        id: 'seer_claim_conflict',
        title: _LocalizedText('身份冲突优先级', 'Claim conflict priority'),
        value: _high,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '帮助选择可见证据，不授予额外隐藏信息。',
          'Helps select visible evidence without granting hidden information.',
        ),
      ),
      _PolicySetting(
        id: 'seer_citation',
        title: _LocalizedText('证据引用方式', 'Citation style'),
        value: _playerAndRound,
        choices: [_playerOnly, _playerAndRound, _playerRoundEvidence],
        explanation: _LocalizedText(
          '影响发言中引用证据的粒度，不改变日志或审计事实。',
          'Affects how evidence is cited in speech, not logs or audit truth.',
        ),
      ),
    ],
    icon: Icons.visibility_rounded,
    color: WerewolfAppTheme.seer,
  ),
  _AgentRoleTemplate(
    roleId: 'witch',
    localizedName: _LocalizedText('女巫', 'Witch'),
    localizedSummary: _LocalizedText(
      '管理解药和毒药，在关键轮次决定资源价值。',
      'Manages save and poison resources at pivotal moments.',
    ),
    boundaryDescription: _LocalizedText(
      '夜间按服务器窗口使用药品；药品剩余、死亡提示和可选目标由本席位合法视角提供。',
      'Uses potions through server night windows; potion state, death notice, and targets come from the entitled seat view.',
    ),
    runtimeCompositionDescription: _LocalizedText(
      '本策略只表达药品时机和证据偏好，不改变女巫是否有药或能否行动。',
      'This policy expresses potion timing and evidence preferences without changing potion availability or action rights.',
    ),
    defaultPresetId: 'resource_timing',
    presets: [
      _RolePolicyPreset(
        id: 'save_potions',
        name: _LocalizedText('保守保药', 'Conserve potions'),
        summary: _LocalizedText('保守保药策略', 'Potion-conservation policy'),
        tendency: _conservative,
        description: _LocalizedText(
          '避免过早消耗药品，除非收益明确。',
          'Avoid early potion use unless value is clear.',
        ),
      ),
      _RolePolicyPreset(
        id: 'info_first',
        name: _LocalizedText('信息优先', 'Information first'),
        summary: _LocalizedText('信息优先策略', 'Information-first policy'),
        tendency: _balanced,
        description: _LocalizedText(
          '围绕死亡节奏和公开讨论判断药品收益。',
          'Use death rhythm and public discussion to judge potion value.',
        ),
      ),
      _RolePolicyPreset(
        id: 'resource_timing',
        name: _LocalizedText('关键轮次强干预', 'Pivotal intervention'),
        summary: _LocalizedText('资源时机策略', 'Resource-timing policy'),
        tendency: _assertive,
        description: _LocalizedText(
          '在胜负手附近果断救或毒，并保留可解释理由。',
          'Act decisively near pivotal turns while preserving explainable reasons.',
        ),
      ),
    ],
    decisionTendencies: [
      _PolicySetting(
        id: 'witch_risk',
        title: _LocalizedText('药品风险姿态', 'Potion risk posture'),
        value: _balanced,
        choices: [_conservative, _balanced, _assertive],
        explanation: _LocalizedText(
          '风险姿态不会改变药品次数或目标合法性。',
          'Risk posture does not change potion charges or legal targets.',
        ),
      ),
      _PolicySetting(
        id: 'witch_review',
        title: _LocalizedText('行动前复核', 'Pre-action review'),
        value: _LocalizedText('高风险时偏好复核', 'Prefer review when high risk'),
        choices: [
          _LocalizedText('不额外复核', 'No extra review preference'),
          _LocalizedText('高风险时偏好复核', 'Prefer review when high risk'),
          _LocalizedText(
            '关键轮次强复核',
            'Strong review preference on pivotal turns',
          ),
        ],
        explanation: _LocalizedText(
          '复核只是偏好，是否额外调用由 ExecutionContract 和预算决定。',
          'Review is only a preference; ExecutionContract and budget decide extra work.',
        ),
      ),
    ],
    actionStrategies: [
      _PolicySetting(
        id: 'witch_save',
        title: _LocalizedText('解药使用倾向', 'Save potion tendency'),
        value: _LocalizedText('关键目标优先', 'Prioritize key targets'),
        choices: [
          _LocalizedText('尽量保药', 'Conserve save potion'),
          _LocalizedText('关键目标优先', 'Prioritize key targets'),
          _LocalizedText('早期保护信息位', 'Protect information roles early'),
        ],
        explanation: _LocalizedText(
          '只影响解药提案，不改变死亡信息管道。',
          'Guides save proposals only; death information flow is unchanged.',
        ),
      ),
      _PolicySetting(
        id: 'witch_poison',
        title: _LocalizedText('毒药使用倾向', 'Poison tendency'),
        value: _LocalizedText('高置信目标优先', 'High-confidence targets first'),
        choices: [
          _LocalizedText('保守不用毒', 'Conservative no-poison'),
          _LocalizedText('高置信目标优先', 'High-confidence targets first'),
          _LocalizedText('关键轮次接受风险', 'Accept risk on pivotal turns'),
        ],
        explanation: _LocalizedText(
          '毒药策略不得把公开怀疑升级成裁判事实。',
          'Poison policy must not upgrade public suspicion into adjudicated truth.',
        ),
      ),
    ],
    evidencePreferences: [
      _PolicySetting(
        id: 'witch_poison_evidence',
        title: _LocalizedText('毒前证据优先', 'Evidence before poison'),
        value: _LocalizedText('身份冲突 · 票型异常', 'Claim conflict and vote anomaly'),
        choices: [
          _LocalizedText('身份冲突 · 票型异常', 'Claim conflict and vote anomaly'),
          _LocalizedText('带队风险', 'Leader risk'),
          _LocalizedText('自我压力变化', 'Pressure on self'),
        ],
        explanation: _LocalizedText(
          '证据偏好只选取已授权可见材料。',
          'Evidence preference only selects authorized visible material.',
        ),
      ),
      _PolicySetting(
        id: 'witch_history',
        title: _LocalizedText('历史信息使用', 'History use'),
        value: _recentPlusTargeted,
        choices: [_recentOnly, _recentPlusTargeted, _evidenceDense],
        explanation: _LocalizedText(
          '不允许读取他人私有记忆或上帝状态。',
          'Cannot read another seat private memory or god state.',
        ),
      ),
    ],
    icon: Icons.science_rounded,
    color: WerewolfAppTheme.witch,
  ),
  _AgentRoleTemplate(
    roleId: 'villager',
    localizedName: _LocalizedText('村民', 'Villager'),
    localizedSummary: _LocalizedText(
      '依赖公开发言、票型和逻辑寻找狼人。',
      'Uses public speech, votes, and logic to find wolves.',
    ),
    boundaryDescription: _LocalizedText(
      '没有夜间能力，只能读取公开事件和自己的行动窗口；不能看到任何隐藏身份或私有记忆。',
      'Has no night ability and reads only public events plus own action windows; no hidden roles or private memory.',
    ),
    runtimeCompositionDescription: _LocalizedText(
      '本策略只塑造村民公开推理方式，不绑定座位人格或模型配置。',
      'This policy shapes public villager reasoning without binding seat personality or model config.',
    ),
    defaultPresetId: 'claim_review',
    presets: [
      _RolePolicyPreset(
        id: 'vote_tracking',
        name: _LocalizedText('跟踪票型', 'Track votes'),
        summary: _LocalizedText('票型追踪策略', 'Vote-tracking policy'),
        tendency: _LocalizedText('谨慎', 'Careful'),
        description: _LocalizedText(
          '重点比较发言和投票是否一致。',
          'Compare speech and vote consistency.',
        ),
      ),
      _RolePolicyPreset(
        id: 'claim_review',
        name: _LocalizedText('发言矛盾优先', 'Contradictions first'),
        summary: _LocalizedText('证据推理策略', 'Evidence-reasoning policy'),
        tendency: _balanced,
        description: _LocalizedText(
          '优先抓公开矛盾、身份声明和承诺变化。',
          'Prioritize public contradictions, claims, and commitment changes.',
        ),
      ),
      _RolePolicyPreset(
        id: 'active_discussion',
        name: _LocalizedText('主动带讨论', 'Lead discussion'),
        summary: _LocalizedText('主动讨论策略', 'Active-discussion policy'),
        tendency: _assertive,
        description: _LocalizedText(
          '主动发问和整理焦点，但不假装拥有私有信息。',
          'Ask questions and organize focus without pretending to have private info.',
        ),
      ),
    ],
    decisionTendencies: [
      _PolicySetting(
        id: 'villager_stance',
        title: _LocalizedText('公开站边阈值', 'Public stance threshold'),
        value: _medium,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '阈值影响表达强度，不改变可见事实。',
          'Threshold affects expression strength, not visible facts.',
        ),
      ),
      _PolicySetting(
        id: 'villager_vote',
        title: _LocalizedText('跟票倾向', 'Follow-vote tendency'),
        value: _low,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '跟票倾向不能绕过投票窗口。',
          'Follow-vote posture cannot bypass vote windows.',
        ),
      ),
    ],
    actionStrategies: [
      _PolicySetting(
        id: 'villager_questions',
        title: _LocalizedText('压力提问方式', 'Pressure-question style'),
        value: _gentlePressure,
        choices: [_explainEvidence, _gentlePressure, _leadDiscussion],
        explanation: _LocalizedText(
          '发问只产生公开发言，不改变其他玩家行动。',
          'Questions are public speech only and do not alter other players actions.',
        ),
      ),
      _PolicySetting(
        id: 'villager_commitments',
        title: _LocalizedText('承诺追踪', 'Commitment follow-through'),
        value: _high,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '追踪的是公开承诺，不是运行期私有状态编辑器。',
          'Tracks public commitments; it is not a runtime private-state editor.',
        ),
      ),
    ],
    evidencePreferences: [
      _PolicySetting(
        id: 'villager_contradiction',
        title: _LocalizedText('发言矛盾优先级', 'Contradiction priority'),
        value: _high,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '只从公开发言和可见投票中选择证据。',
          'Selects evidence only from public speech and visible votes.',
        ),
      ),
      _PolicySetting(
        id: 'villager_citation',
        title: _LocalizedText('证据引用方式', 'Citation style'),
        value: _playerAndRound,
        choices: [_playerOnly, _playerAndRound, _playerRoundEvidence],
        explanation: _LocalizedText(
          '引用方式帮助发言清晰，不改变日志内容。',
          'Citation style improves speech clarity without changing logs.',
        ),
      ),
    ],
    icon: Icons.groups_rounded,
    color: WerewolfAppTheme.villager,
  ),
  _AgentRoleTemplate(
    roleId: 'guard',
    localizedName: _LocalizedText('守卫', 'Guard'),
    localizedSummary: _LocalizedText(
      '夜间守护玩家，通过轮次节奏保护关键身份。',
      'Protects players at night around round tempo.',
    ),
    boundaryDescription: _LocalizedText(
      '守护窗口和连续守护限制由规则决定；策略只能建议守护目标优先级。',
      'Guard windows and repeat constraints are rule-owned; policy only guides target priority.',
    ),
    runtimeCompositionDescription: _LocalizedText(
      '本策略只表达守护博弈倾向，不改变规则集是否启用守卫。',
      'This policy expresses guard-risk posture without changing whether the ruleset includes guard.',
    ),
    defaultPresetId: 'safe_guard',
    presets: [
      _RolePolicyPreset(
        id: 'safe_guard',
        name: _LocalizedText('保守守护', 'Safe guard'),
        summary: _LocalizedText('保护优先策略', 'Protection-first policy'),
        tendency: _conservative,
        description: _LocalizedText(
          '优先保护公开高价值目标，降低失败风险。',
          'Prefer publicly high-value targets and reduce failure risk.',
        ),
      ),
      _RolePolicyPreset(
        id: 'counter_logic',
        name: _LocalizedText('反逻辑守护', 'Counter-logic guard'),
        summary: _LocalizedText('反逻辑守护策略', 'Counter-logic guard policy'),
        tendency: _balanced,
        description: _LocalizedText(
          '在狼队可能预判常规守护时改变目标。',
          'Change target when wolves may predict obvious guards.',
        ),
      ),
      _RolePolicyPreset(
        id: 'risk_gamble',
        name: _LocalizedText('风险博弈', 'Risk gamble'),
        summary: _LocalizedText('风险博弈策略', 'Risk-gamble policy'),
        tendency: _LocalizedText('冒险', 'Risky'),
        description: _LocalizedText(
          '接受更高失误风险换取关键轮次收益。',
          'Accept higher miss risk for pivotal-turn value.',
        ),
      ),
    ],
    decisionTendencies: [
      _PolicySetting(
        id: 'guard_risk',
        title: _LocalizedText('守护风险姿态', 'Guard risk posture'),
        value: _balanced,
        choices: [_conservative, _balanced, _assertive],
        explanation: _LocalizedText(
          '风险偏好不会改变守护限制。',
          'Risk preference does not change guard constraints.',
        ),
      ),
      _PolicySetting(
        id: 'guard_claimed_roles',
        title: _LocalizedText('公开身份保护', 'Protect claimed roles'),
        value: _medium,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '公开身份声明仍只是 Claim，不等于真实身份。',
          'Public role claims are claims, not true roles.',
        ),
      ),
    ],
    actionStrategies: [
      _PolicySetting(
        id: 'guard_target',
        title: _LocalizedText('守护目标优先级', 'Guard target priority'),
        value: _LocalizedText('高价值公开目标', 'High-value public target'),
        choices: [
          _LocalizedText('高价值公开目标', 'High-value public target'),
          _LocalizedText('被低估目标', 'Underestimated target'),
          _LocalizedText('反常规目标', 'Counter-obvious target'),
        ],
        explanation: _LocalizedText(
          '只建议目标，不改变夜间行动窗口。',
          'Suggests targets only and does not change night windows.',
        ),
      ),
      _PolicySetting(
        id: 'guard_review',
        title: _LocalizedText('守前复核', 'Pre-guard review'),
        value: _LocalizedText('高风险时偏好复核', 'Prefer review when high risk'),
        choices: [
          _LocalizedText('不额外复核', 'No extra review preference'),
          _LocalizedText('高风险时偏好复核', 'Prefer review when high risk'),
          _LocalizedText(
            '关键轮次强复核',
            'Strong review preference on pivotal turns',
          ),
        ],
        explanation: _LocalizedText(
          '是否可复核取决于运行契约和预算。',
          'Review availability depends on runtime contract and budget.',
        ),
      ),
    ],
    evidencePreferences: [
      _PolicySetting(
        id: 'guard_death_rhythm',
        title: _LocalizedText('死亡节奏优先级', 'Death rhythm priority'),
        value: _medium,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '死亡节奏只来自可见结算事件。',
          'Death rhythm comes only from visible resolution events.',
        ),
      ),
      _PolicySetting(
        id: 'guard_history',
        title: _LocalizedText('历史信息使用', 'History use'),
        value: _recentPlusTargeted,
        choices: [_recentOnly, _recentPlusTargeted, _evidenceDense],
        explanation: _LocalizedText(
          '不读取他人私有行动理由。',
          'Does not read another seat private action rationale.',
        ),
      ),
    ],
    icon: Icons.shield_rounded,
    color: Color(0xFF8BD3DD),
  ),
  _AgentRoleTemplate(
    roleId: 'hunter',
    localizedName: _LocalizedText('猎人', 'Hunter'),
    localizedSummary: _LocalizedText(
      '用死亡开枪威慑参与归票和遗言反制。',
      'Uses shot threat and final words to shape votes.',
    ),
    boundaryDescription: _LocalizedText(
      '是否能开枪由死亡状态、规则和行动窗口决定；策略不能强行触发能力。',
      'Shot availability is decided by death state, rules, and action windows; policy cannot trigger abilities.',
    ),
    runtimeCompositionDescription: _LocalizedText(
      '本策略只表达猎人威慑和开枪克制，不绑定模型、人格或本局运行状态。',
      'This policy expresses hunter threat and restraint without binding model, personality, or run state.',
    ),
    defaultPresetId: 'quiet_survive',
    presets: [
      _RolePolicyPreset(
        id: 'quiet_survive',
        name: _LocalizedText('低调存活', 'Quiet survival'),
        summary: _LocalizedText('低调存活策略', 'Quiet-survival policy'),
        tendency: _conservative,
        description: _LocalizedText(
          '降低被刀和被抗推风险，保留开枪威慑。',
          'Reduce kill/execution risk while preserving shot threat.',
        ),
      ),
      _RolePolicyPreset(
        id: 'threat_control',
        name: _LocalizedText('威慑控场', 'Threat control'),
        summary: _LocalizedText('威慑控场策略', 'Threat-control policy'),
        tendency: _balanced,
        description: _LocalizedText(
          '用可解释威慑约束狼队和错误归票。',
          'Use explainable threat to constrain wolves and bad votes.',
        ),
      ),
      _RolePolicyPreset(
        id: 'counterstrike',
        name: _LocalizedText('关键反制', 'Counterstrike'),
        summary: _LocalizedText('关键反制策略', 'Counterstrike policy'),
        tendency: _assertive,
        description: _LocalizedText(
          '在强证据或临死窗口果断反制。',
          'Counter decisively with strong evidence or a death window.',
        ),
      ),
    ],
    decisionTendencies: [
      _PolicySetting(
        id: 'hunter_signal',
        title: _LocalizedText('威慑表达', 'Threat signaling'),
        value: _medium,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '威慑表达是公开发言策略，不透露隐藏系统事实。',
          'Threat signaling is public speech strategy and reveals no hidden system facts.',
        ),
      ),
      _PolicySetting(
        id: 'hunter_bait',
        title: _LocalizedText('防诱导规则', 'Anti-bait posture'),
        value: _high,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '防诱导只影响判断，不改变开枪合法性。',
          'Anti-bait posture affects judgment, not legal shot availability.',
        ),
      ),
    ],
    actionStrategies: [
      _PolicySetting(
        id: 'hunter_shot_restraint',
        title: _LocalizedText('开枪克制', 'Shot restraint'),
        value: _high,
        choices: [_low, _medium, _high],
        explanation: _LocalizedText(
          '克制程度不会跳过服务器行动窗口。',
          'Restraint cannot bypass server action windows.',
        ),
      ),
      _PolicySetting(
        id: 'hunter_target_basis',
        title: _LocalizedText('目标排序依据', 'Target ranking basis'),
        value: _LocalizedText('票型与发言矛盾', 'Votes and speech contradictions'),
        choices: [
          _LocalizedText('票型与发言矛盾', 'Votes and speech contradictions'),
          _LocalizedText('身份冲突', 'Claim conflicts'),
          _LocalizedText('临死前压力来源', 'Pressure source before death'),
        ],
        explanation: _LocalizedText(
          '目标排序只从已授权证据中产生。',
          'Target ranking uses authorized evidence only.',
        ),
      ),
    ],
    evidencePreferences: [
      _PolicySetting(
        id: 'hunter_final_words',
        title: _LocalizedText('遗言证据密度', 'Final-word evidence density'),
        value: _playerRoundEvidence,
        choices: [_playerOnly, _playerAndRound, _playerRoundEvidence],
        explanation: _LocalizedText(
          '遗言引用公开证据，不公开隐藏身份。',
          'Final words cite public evidence and do not reveal hidden roles.',
        ),
      ),
      _PolicySetting(
        id: 'hunter_history',
        title: _LocalizedText('历史信息使用', 'History use'),
        value: _recentPlusTargeted,
        choices: [_recentOnly, _recentPlusTargeted, _evidenceDense],
        explanation: _LocalizedText(
          '仅选择可见历史，不读裁判私有状态。',
          'Selects visible history only, not private judge state.',
        ),
      ),
    ],
    icon: Icons.gps_fixed_rounded,
    color: WerewolfAppTheme.accent,
  ),
];

class _RoomPage extends StatelessWidget {
  const _RoomPage({required this.controller, required this.onBackToMatches});

  final SessionController? controller;
  final VoidCallback onBackToMatches;

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
    return LiveRoomScreen(controller: active, onBack: onBackToMatches);
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
      key: const Key('flow-back-button'),
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
