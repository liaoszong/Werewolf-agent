import 'package:flutter/material.dart';

import '../app/app_strings.dart';
import '../app/session_controller.dart';
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
    final waiting = state?.openActionWindow != null;
    final statusText = waiting
        ? strings.waitingForYou
        : '${strings.phaseLabel(phase)} · ${strings.yourPerspective} $seat';
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 286),
        child: DecoratedBox(
          key: const Key('room-status-island'),
          decoration: BoxDecoration(
            color: palette.surface.withValues(
              alpha: palette.isDay ? 0.96 : 0.88,
            ),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: waiting
                  ? palette.accent.withValues(alpha: 0.58)
                  : palette.border.withValues(alpha: 0.82),
            ),
            boxShadow: [
              BoxShadow(
                color: palette.shadow.withValues(
                  alpha: palette.isDay ? 0.10 : 0.20,
                ),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 9, 14, 9),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 220),
                  child: Text(
                    statusText,
                    textAlign: TextAlign.center,
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: palette.textPrimary,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 9),
                _ConnectionDot(
                  label: _connectionLabel(strings, connectionStatus),
                  status: connectionStatus,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String? _phase(ParticipantState? state) {
    return state?.currentPhase;
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

class _ConnectionDot extends StatelessWidget {
  const _ConnectionDot({required this.label, required this.status});

  final String label;
  final ConnectionStatus status;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    final color = status == ConnectionStatus.connected
        ? palette.witch
        : palette.danger;
    return Tooltip(
      message: label,
      child: Semantics(
        label: label,
        child: DecoratedBox(
          key: const Key('connection-status-dot'),
          decoration: BoxDecoration(
            color: color.withValues(alpha: palette.isDay ? 0.14 : 0.18),
            shape: BoxShape.circle,
            border: Border.all(color: color.withValues(alpha: 0.45)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: DecoratedBox(
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              child: const SizedBox(width: 8, height: 8),
            ),
          ),
        ),
      ),
    );
  }
}
