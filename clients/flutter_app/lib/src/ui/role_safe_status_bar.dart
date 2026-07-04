import 'package:flutter/material.dart';

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
    final seat = state?.seatId.toUpperCase() ?? '--';
    final activity = _activityLabel(state);
    return DecoratedBox(
      decoration: const BoxDecoration(color: WerewolfAppTheme.surface),
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
              _connectionLabel(connectionStatus),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  String _activityLabel(ParticipantState? state) {
    if (state?.openActionWindow != null) {
      return '等待你操作';
    }
    final phase = state?.projection['phase'] as String? ??
        state?.openActionWindow?.phase ??
        state?.runStatus;
    return switch (phase) {
      'night' => '夜间行动中',
      'vote' => '投票中',
      'day' => '公开讨论',
      'completed' => '游戏结束',
      'finished' => '游戏结束',
      'running' => '房间同步中',
      _ => '房间同步中',
    };
  }

  String _connectionLabel(ConnectionStatus status) {
    return switch (status) {
      ConnectionStatus.reconnecting => '正在重连',
      ConnectionStatus.connected => '已连接',
      ConnectionStatus.connecting => '连接中',
      ConnectionStatus.sessionExpired => '会话失效',
      ConnectionStatus.failed => '连接异常',
      ConnectionStatus.idle => '未连接',
    };
  }
}
