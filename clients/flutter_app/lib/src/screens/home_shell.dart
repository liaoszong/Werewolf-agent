import 'package:flutter/material.dart';

import '../app/app_settings.dart';
import '../app/app_strings.dart';
import '../app/session_controller.dart';
import '../protocol/observer_api_client.dart';
import '../ui/app_theme.dart';
import 'live_room_screen.dart';

typedef ObserverClientFactory = ObserverApiClient Function(Uri baseUri);
typedef SessionControllerFactory = SessionController Function(Uri baseUri);

class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.settingsController,
    required this.observerClientFactory,
    required this.sessionControllerFactory,
  });

  final AppSettingsController settingsController;
  final ObserverClientFactory observerClientFactory;
  final SessionControllerFactory sessionControllerFactory;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _selectedIndex = 0;
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
    return Scaffold(
      body: SafeArea(
        child: IndexedStack(
          index: _selectedIndex,
          children: [
            _HomePage(
              runs: _runs,
              loadingRuns: _loadingRuns,
              runsError: _runsError,
              onChooseMatch: () => setState(() => _selectedIndex = 1),
              onRefresh: _loadRuns,
            ),
            _MatchesPage(
              runs: _runs,
              loadingRuns: _loadingRuns,
              joining: _joining,
              error: _runsError ?? _joinError,
              onRefresh: _loadRuns,
              onJoin: _joinRun,
            ),
            _RoomPage(
              controller: _sessionController,
              needsIdentityConfirm: _needsIdentityConfirm,
              onEnterRoom: () {
                setState(() => _needsIdentityConfirm = false);
              },
            ),
            _SettingsPage(settingsController: _settings),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.home_outlined),
            selectedIcon: const Icon(Icons.home_rounded),
            label: strings.home,
          ),
          NavigationDestination(
            icon: const Icon(Icons.forum_outlined),
            selectedIcon: const Icon(Icons.forum_rounded),
            label: strings.matches,
          ),
          NavigationDestination(
            icon: const Icon(Icons.nightlight_outlined),
            selectedIcon: const Icon(Icons.nightlight_round),
            label: strings.room,
          ),
          NavigationDestination(
            icon: const Icon(Icons.settings_outlined),
            selectedIcon: const Icon(Icons.settings_rounded),
            label: strings.settings,
          ),
        ],
      ),
    );
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
        _selectedIndex = 2;
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
                          color: WerewolfAppTheme.textPrimary,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    strings.appKicker,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: WerewolfAppTheme.accent,
                        ),
                  ),
                ],
              ),
            ),
            const _LanguageToggle(),
          ],
        ),
        const SizedBox(height: 18),
        Text(
          strings.appIntro,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: WerewolfAppTheme.textMuted,
              ),
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
              Text(strings.activeMatch, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 10),
              if (activeRuns.isEmpty)
                Text(
                  strings.noActiveRuns,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: WerewolfAppTheme.textMuted,
                      ),
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
                    activeRuns.isEmpty ? strings.chooseMatch : strings.continueObserving,
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
    required this.onRefresh,
    required this.onJoin,
  });

  final List<RunSummary> runs;
  final bool loadingRuns;
  final bool joining;
  final String? error;
  final Future<void> Function() onRefresh;
  final ValueChanged<String> onJoin;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                strings.matches,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: WerewolfAppTheme.textPrimary,
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
          strings.runListHint,
          style: Theme.of(context).textTheme.bodySmall,
        ),
        if (error != null) ...[
          const SizedBox(height: 12),
          Text(error!, style: const TextStyle(color: WerewolfAppTheme.danger)),
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

class _RoomPage extends StatelessWidget {
  const _RoomPage({
    required this.controller,
    required this.needsIdentityConfirm,
    required this.onEnterRoom,
  });

  final SessionController? controller;
  final bool needsIdentityConfirm;
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
              Text(strings.emptyRoomTitle, style: Theme.of(context).textTheme.titleMedium),
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
      return _IdentityConfirmPane(controller: active, onEnterRoom: onEnterRoom);
    }
    return LiveRoomScreen(controller: active);
  }
}

class _IdentityConfirmPane extends StatelessWidget {
  const _IdentityConfirmPane({
    required this.controller,
    required this.onEnterRoom,
  });

  final SessionController controller;
  final VoidCallback onEnterRoom;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final session = controller.session;
    final seat = session?.seatId.toUpperCase() ?? 'UNKNOWN';
    final perspective = session?.perspective ?? 'role-safe';
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Spacer(),
          Text(
            strings.seatIdentity(seat),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: WerewolfAppTheme.textPrimary,
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
  const _SettingsPage({required this.settingsController});

  final AppSettingsController settingsController;

  @override
  State<_SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<_SettingsPage> {
  late final TextEditingController _baseUrl;
  late final TextEditingController _seatId;
  late final TextEditingController _joinCode;
  String? _error;

  AppSettingsController get _settings => widget.settingsController;

  @override
  void initState() {
    super.initState();
    _baseUrl = TextEditingController(text: _settings.baseUri.toString());
    _seatId = TextEditingController(text: _settings.seatId);
    _joinCode = TextEditingController(text: _settings.joinCode);
  }

  @override
  void dispose() {
    _baseUrl.dispose();
    _seatId.dispose();
    _joinCode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 24),
      children: [
        Text(
          strings.settings,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: WerewolfAppTheme.textPrimary,
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: 18),
        _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(strings.languageLabel, style: Theme.of(context).textTheme.titleMedium),
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
              Text(strings.connection, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              TextField(
                controller: _baseUrl,
                keyboardType: TextInputType.url,
                decoration: InputDecoration(labelText: strings.baseUrl),
              ),
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
                Text(_error!, style: const TextStyle(color: WerewolfAppTheme.danger)),
              ],
              const SizedBox(height: 12),
              Text(strings.phoneLanHint, style: Theme.of(context).textTheme.bodySmall),
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
    final status = loadingRuns
        ? strings.loading
        : (runsError == null ? strings.connected : strings.offline);
    return _Panel(
      child: Row(
        children: [
          Icon(
            runsError == null ? Icons.cloud_done_outlined : Icons.cloud_off_outlined,
            color: runsError == null ? WerewolfAppTheme.witch : WerewolfAppTheme.danger,
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
    return DecoratedBox(
      decoration: BoxDecoration(
        color: WerewolfAppTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF2D3744)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: child,
      ),
    );
  }
}
