import 'package:flutter/material.dart';

import '../app/session_controller.dart';
import '../app/app_strings.dart';
import '../protocol/participant_models.dart';
import 'app_theme.dart';

class RoleSafeStatusBar extends StatelessWidget {
  const RoleSafeStatusBar({
    super.key,
    required this.connectionStatus,
    required this.state,
  });

  final ConnectionStatus connectionStatus;
  final ParticipantState? state;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final seat = state?.seatId.toUpperCase() ?? '--';
    final phase = _phase(state);
    final round = _round(state);
    final activity = _activityLabel(strings, state, phase);
    final waiting = state?.openActionWindow != null;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: palette.surface.withValues(alpha: palette.isDay ? 0.94 : 0.86),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: waiting
              ? palette.accent.withValues(alpha: 0.54)
              : palette.border,
        ),
        boxShadow: [
          BoxShadow(
            color: palette.shadow.withValues(
              alpha: palette.isDay ? 0.10 : 0.18,
            ),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 11, 12, 11),
        child: Row(
          children: [
            _PhaseChip(phase: phase, active: waiting),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    activity,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(
                      context,
                    ).textTheme.titleMedium?.copyWith(fontSize: 15),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${strings.roundLabel(round)} · ${strings.yourPerspective} $seat',
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            _ConnectionPill(
              label: _connectionLabel(strings, connectionStatus),
              status: connectionStatus,
            ),
          ],
        ),
      ),
    );
  }

  String _activityLabel(
    AppStrings strings,
    ParticipantState? state,
    String? phase,
  ) {
    if (state?.openActionWindow != null) {
      return strings.waitingForYou;
    }
    return strings.phaseLabel(phase);
  }

  String? _phase(ParticipantState? state) {
    final projectionPhase = state?.projection['phase'];
    return state?.openActionWindow?.phase ??
        (projectionPhase is String ? projectionPhase : null) ??
        state?.runStatus;
  }

  int? _round(ParticipantState? state) {
    final projectionRound = state?.projection['round'];
    if (projectionRound is int) return projectionRound;
    return state?.openActionWindow?.round;
  }

  String _connectionLabel(AppStrings strings, ConnectionStatus status) {
    return switch (status) {
      ConnectionStatus.reconnecting => strings.reconnecting,
      ConnectionStatus.connected => strings.connected,
      ConnectionStatus.connecting => strings.connecting,
      ConnectionStatus.sessionExpired => strings.sessionExpired,
      ConnectionStatus.failed => strings.connectionFailed,
      ConnectionStatus.idle => strings.idle,
    };
  }
}

class _PhaseChip extends StatelessWidget {
  const _PhaseChip({required this.phase, required this.active});

  final String? phase;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    final icon = switch (phase) {
      'night' => Icons.nights_stay_rounded,
      'day' => Icons.wb_sunny_rounded,
      'vote' || 'voting' => Icons.how_to_vote_rounded,
      'completed' || 'finished' || 'game_over' => Icons.flag_rounded,
      _ => Icons.sync_rounded,
    };
    return DecoratedBox(
      key: const Key('room-phase-chip'),
      decoration: BoxDecoration(
        color: active
            ? palette.accent.withValues(alpha: palette.isDay ? 0.22 : 0.18)
            : palette.control,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: active
              ? palette.accent.withValues(alpha: 0.48)
              : palette.border,
        ),
      ),
      child: SizedBox(
        width: 42,
        height: 42,
        child: Icon(
          icon,
          size: 20,
          color: active ? palette.accent : palette.textPrimary,
        ),
      ),
    );
  }
}

class _ConnectionPill extends StatelessWidget {
  const _ConnectionPill({required this.label, required this.status});

  final String label;
  final ConnectionStatus status;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    final color = switch (status) {
      ConnectionStatus.connected => palette.witch,
      ConnectionStatus.connecting ||
      ConnectionStatus.reconnecting => palette.accent,
      ConnectionStatus.idle => palette.textMuted,
      ConnectionStatus.sessionExpired ||
      ConnectionStatus.failed => palette.danger,
    };
    return DecoratedBox(
      key: const Key('room-connection-pill'),
      decoration: BoxDecoration(
        color: color.withValues(alpha: palette.isDay ? 0.12 : 0.16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            DecoratedBox(
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              child: const SizedBox(width: 7, height: 7),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: palette.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
