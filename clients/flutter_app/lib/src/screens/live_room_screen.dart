import 'package:flutter/material.dart';

import '../app/session_controller.dart';
import '../ui/composer_rail.dart';
import '../ui/role_safe_status_bar.dart';
import '../ui/speech_feed.dart';

class LiveRoomScreen extends StatelessWidget {
  const LiveRoomScreen({super.key, required this.controller});

  final SessionController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return Scaffold(
          body: SafeArea(
            child: Column(
              children: [
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
