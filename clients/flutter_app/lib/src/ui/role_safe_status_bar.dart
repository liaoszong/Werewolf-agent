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
    final activity = _activityLabel(strings, state);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: palette.border),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            Expanded(
              child: Text(
                '$activity · 你的视角 $seat',
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Text(
              _connectionLabel(strings, connectionStatus),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  String _activityLabel(AppStrings strings, ParticipantState? state) {
    if (state?.openActionWindow != null) {
      return strings.waitingForYou;
    }
    final phase =
        state?.projection['phase'] as String? ??
        state?.openActionWindow?.phase ??
        state?.runStatus;
    return switch (phase) {
      'night' => strings.nightInProgress,
      'vote' => strings.voting,
      'day' => strings.discussion,
      'completed' => strings.gameOver,
      'finished' => strings.gameOver,
      'running' => strings.roomSyncing,
      _ => strings.roomSyncing,
    };
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
