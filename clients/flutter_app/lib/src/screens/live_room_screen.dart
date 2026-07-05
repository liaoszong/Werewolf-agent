import 'package:flutter/material.dart';

import '../app/session_controller.dart';
import '../protocol/participant_models.dart';
import '../ui/app_theme.dart';
import '../ui/composer_rail.dart';
import '../ui/role_safe_status_bar.dart';
import '../ui/speech_feed.dart';

class LiveRoomScreen extends StatelessWidget {
  const LiveRoomScreen({super.key, required this.controller, this.onBack});

  final SessionController controller;
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return Scaffold(
          body: SafeArea(
            child: Column(
              children: [
                if (onBack != null)
                  _LiveRoomHeader(
                    connectionStatus: controller.connectionStatus,
                    state: controller.state,
                    onBack: onBack!,
                  )
                else
                  RoleSafeStatusBar(
                    connectionStatus: controller.connectionStatus,
                    state: controller.state,
                  ),
                Expanded(
                  child: SpeechFeed(
                    events: controller.state?.visibleEvents ?? const [],
                  ),
                ),
                ComposerRail(
                  window: controller.state?.openActionWindow,
                  errorMessage: controller.lastError,
                  onSubmitSpeech: controller.submitSpeech,
                  onSubmitStructuredAction: (actionType, payload) {
                    return controller.submitStructuredAction(
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
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
      child: Row(
        children: [
          SizedBox(
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
                key: const Key('flow-back-button'),
                tooltip: MaterialLocalizations.of(context).backButtonTooltip,
                onPressed: onBack,
                icon: Icon(
                  Icons.chevron_left_rounded,
                  size: 26,
                  color: palette.textPrimary,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: RoleSafeStatusBar(
              connectionStatus: connectionStatus,
              state: state,
            ),
          ),
        ],
      ),
    );
  }
}
