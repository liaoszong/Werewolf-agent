import 'dart:async';

import 'package:flutter/material.dart';

import '../app/app_strings.dart';
import '../app/session_controller.dart';
import '../protocol/participant_models.dart';
import '../ui/app_theme.dart';
import '../ui/composer_rail.dart';
import '../ui/role_safe_status_bar.dart';
import '../ui/speech_feed.dart';

class LiveRoomScreen extends StatefulWidget {
  const LiveRoomScreen({super.key, required this.controller, this.onBack});

  final SessionController controller;
  final VoidCallback? onBack;

  @override
  State<LiveRoomScreen> createState() => _LiveRoomScreenState();
}

class _LiveRoomScreenState extends State<LiveRoomScreen> {
  String? _shownRoleNoticeKey;
  bool _roleNoticeScheduled = false;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        _scheduleRoleNotice(context, widget.controller.state);
        return Scaffold(
          body: SafeArea(
            child: Column(
              children: [
                if (widget.onBack != null)
                  _LiveRoomHeader(
                    connectionStatus: widget.controller.connectionStatus,
                    state: widget.controller.state,
                    onBack: widget.onBack!,
                  )
                else
                  RoleSafeStatusBar(
                    connectionStatus: widget.controller.connectionStatus,
                    state: widget.controller.state,
                  ),
                if (widget.controller.state case final state?)
                  _RoomInfoPanels(state: state),
                Expanded(
                  child: SpeechFeed(
                    events: widget.controller.state?.visibleEvents ?? const [],
                    currentSeatId: widget.controller.state?.seatId,
                  ),
                ),
                ComposerRail(
                  window: widget.controller.state?.openActionWindow,
                  targetCandidateSeatIds:
                      widget.controller.state?.targetCandidateSeatIds ??
                      const [],
                  errorMessage: widget.controller.lastError,
                  isSubmitting: widget.controller.isSubmittingAction,
                  onSubmitSpeech: widget.controller.submitSpeech,
                  onSubmitStructuredAction: (actionType, payload) {
                    return widget.controller.submitStructuredAction(
                      actionType: actionType,
                      payload: payload,
                    );
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _scheduleRoleNotice(BuildContext context, ParticipantState? state) {
    if (state == null || _roleNoticeScheduled) return;
    final noticeKey = '${state.runId}:${state.seatId}';
    if (_shownRoleNoticeKey == noticeKey) return;
    _roleNoticeScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        _roleNoticeScheduled = false;
        return;
      }
      final latest = widget.controller.state;
      if (latest == null) {
        _roleNoticeScheduled = false;
        return;
      }
      final latestKey = '${latest.runId}:${latest.seatId}';
      if (_shownRoleNoticeKey == latestKey) {
        _roleNoticeScheduled = false;
        return;
      }
      setState(() {
        _shownRoleNoticeKey = latestKey;
        _roleNoticeScheduled = false;
      });
      unawaited(
        showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (context) => _RoleNoticeDialog(state: latest),
        ),
      );
    });
  }
}

class _RoleNoticeDialog extends StatelessWidget {
  const _RoleNoticeDialog({required this.state});

  final ParticipantState state;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final projection = state.projectionEnvelope;
    final role = projection.selfRole;
    final team = projection.selfTeam;
    final teammates = projection.visibleWerewolfTeammates;
    return Dialog(
      key: const Key('role-notice-dialog'),
      backgroundColor: palette.surface,
      insetPadding: const EdgeInsets.symmetric(horizontal: 22, vertical: 24),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.badge_outlined, color: _roleColor(role, palette)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    strings.roleNoticeTitle,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              strings.roleNoticeBody,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _InfoChip(
                  label: strings.yourRole,
                  value: strings.roleLabel(role),
                  color: _roleColor(role, palette),
                ),
                _InfoChip(
                  label: strings.yourTeam,
                  value: strings.teamLabel(team),
                  color: _teamColor(team, palette),
                ),
              ],
            ),
            if (role == 'werewolf' || team == 'werewolf') ...[
              const SizedBox(height: 14),
              Text(
                strings.werewolfTeammates,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              if (teammates.isEmpty)
                Text(
                  strings.noVisibleWerewolfTeammates,
                  style: Theme.of(context).textTheme.bodySmall,
                )
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final teammate in teammates)
                      _InfoChip(
                        label: teammate.playerId.toUpperCase(),
                        value: strings.aliveLabel(teammate.alive),
                        color: palette.danger,
                      ),
                  ],
                ),
            ],
            const SizedBox(height: 14),
            Text(
              strings.roleSkill,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontSize: 14,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              strings.roleSkillIntro(role),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 46,
              child: FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text(strings.enterRoom),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RoomInfoPanels extends StatelessWidget {
  const _RoomInfoPanels({required this.state});

  final ParticipantState state;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 6, 14, 4),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final top = constraints.maxWidth >= 680
              ? Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _PhaseStatusPanel(state: state)),
                    const SizedBox(width: 10),
                    Expanded(child: _PrivateInfoPanel(state: state)),
                  ],
                )
              : Column(
                  children: [
                    _PhaseStatusPanel(state: state),
                    const SizedBox(height: 8),
                    _PrivateInfoPanel(state: state),
                  ],
                );
          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              top,
              const SizedBox(height: 8),
              _SeatStrip(state: state),
            ],
          );
        },
      ),
    );
  }
}

class _PhaseStatusPanel extends StatelessWidget {
  const _PhaseStatusPanel({required this.state});

  final ParticipantState state;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final phase = state.currentPhase;
    final round = state.currentRound;
    final window = state.openActionWindow;
    return DecoratedBox(
      key: const Key('phase-status-panel'),
      decoration: _panelDecoration(palette),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
        child: Row(
          children: [
            Icon(
              _phaseIcon(phase),
              color: window == null ? palette.textMuted : palette.accent,
              size: 20,
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    strings.phaseStatus,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${strings.phaseLabel(phase)} · ${strings.roundLabel(round)}',
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(
                      context,
                    ).textTheme.titleMedium?.copyWith(fontSize: 14),
                  ),
                ],
              ),
            ),
            _MiniMetric(
              label: strings.hiddenEvents,
              value: '${state.projectionEnvelope.hiddenEventCount}',
            ),
          ],
        ),
      ),
    );
  }
}

class _PrivateInfoPanel extends StatelessWidget {
  const _PrivateInfoPanel({required this.state});

  final ParticipantState state;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final projection = state.projectionEnvelope;
    final self = projection.selfPlayer;
    final role = projection.proof.selfRole ?? self?.displayRole;
    final team = projection.proof.selfTeam ?? self?.displayTeam;
    final visibleSnapshots = projection.visibleSnapshots.length;
    return DecoratedBox(
      key: const Key('private-info-panel'),
      decoration: _panelDecoration(palette),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(
                  Icons.lock_outline_rounded,
                  size: 18,
                  color: palette.accent,
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    strings.privateInfo,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: [
                _InfoChip(
                  label: strings.yourRole,
                  value: strings.roleLabel(role),
                  color: _roleColor(role, palette),
                ),
                _InfoChip(
                  label: strings.yourTeam,
                  value: strings.teamLabel(team),
                  color: _teamColor(team, palette),
                ),
                _InfoChip(
                  label: strings.visibleSnapshot,
                  value: '$visibleSnapshots',
                  color: palette.textMuted,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SeatStrip extends StatelessWidget {
  const _SeatStrip({required this.state});

  final ParticipantState state;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final players = state.projectionEnvelope.players;
    if (players.isEmpty) return const SizedBox.shrink();
    return DecoratedBox(
      key: const Key('seat-strip'),
      decoration: _panelDecoration(palette),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 10, 10, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(strings.seats, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final player in players) ...[
                    _SeatPill(
                      player: player,
                      isSelf:
                          player.playerId == state.seatId ||
                          player.visibility == 'self',
                    ),
                    const SizedBox(width: 8),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SeatPill extends StatelessWidget {
  const _SeatPill({required this.player, required this.isSelf});

  final ProjectionPlayer player;
  final bool isSelf;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final roleColor = _roleColor(player.displayRole, palette);
    return ConstrainedBox(
      constraints: const BoxConstraints(minWidth: 76, maxWidth: 96),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: isSelf
              ? palette.accent.withValues(alpha: palette.isDay ? 0.16 : 0.14)
              : palette.control,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelf
                ? palette.accent.withValues(alpha: 0.50)
                : palette.border,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      player.playerId.toUpperCase(),
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(
                        context,
                      ).textTheme.titleMedium?.copyWith(fontSize: 13),
                    ),
                  ),
                  if (isSelf)
                    Text(
                      strings.you,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: palette.accent,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 5),
              Text(
                strings.roleLabel(player.displayRole),
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: roleColor,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                strings.aliveLabel(player.alive),
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: palette.isDay ? 0.10 : 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
        child: Text(
          '$label · $value',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: palette.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _MiniMetric extends StatelessWidget {
  const _MiniMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: palette.control,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.border),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              value,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontSize: 13),
            ),
            Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(fontSize: 10),
            ),
          ],
        ),
      ),
    );
  }
}

BoxDecoration _panelDecoration(WerewolfPalette palette) {
  return BoxDecoration(
    color: palette.surface.withValues(alpha: palette.isDay ? 0.92 : 0.82),
    borderRadius: BorderRadius.circular(18),
    border: Border.all(color: palette.border),
  );
}

IconData _phaseIcon(String? phase) {
  return switch (phase) {
    'night' || 'night_werewolf' || 'night_witch' => Icons.nights_stay_rounded,
    'day' || 'day_speech' => Icons.forum_rounded,
    'vote' || 'voting' || 'day_vote' => Icons.how_to_vote_rounded,
    'completed' || 'finished' || 'game_over' => Icons.flag_rounded,
    _ => Icons.sync_rounded,
  };
}

Color _roleColor(String? role, WerewolfPalette palette) {
  return switch (role) {
    'werewolf' => palette.danger,
    'seer' => palette.seer,
    'witch' => palette.witch,
    'hunter' => palette.accent,
    'guard' => const Color(0xFF8CC8FF),
    'villager' => palette.villager,
    _ => palette.textMuted,
  };
}

Color _teamColor(String? team, WerewolfPalette palette) {
  return switch (team) {
    'werewolf' => palette.danger,
    'villager' => palette.witch,
    _ => palette.textMuted,
  };
}

class _LiveRoomHeader extends StatelessWidget {
  const _LiveRoomHeader({
    required this.connectionStatus,
    required this.state,
    required this.onBack,
  });

  final ConnectionStatus connectionStatus;
  final ParticipantState? state;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
      child: SizedBox(
        height: 44,
        child: Stack(
          children: [
            Positioned.fill(
              child: RoleSafeStatusBar(
                connectionStatus: connectionStatus,
                state: state,
              ),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: SizedBox(
                key: const Key('flow-back-button'),
                width: 44,
                height: 44,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: palette.surface.withValues(
                      alpha: palette.isDay ? 0.92 : 0.78,
                    ),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: palette.border.withValues(alpha: 0.7),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: palette.shadow,
                        blurRadius: 18,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: IconButton(
                    tooltip: MaterialLocalizations.of(
                      context,
                    ).backButtonTooltip,
                    onPressed: onBack,
                    icon: Icon(
                      Icons.chevron_left_rounded,
                      size: 26,
                      color: palette.textPrimary,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
