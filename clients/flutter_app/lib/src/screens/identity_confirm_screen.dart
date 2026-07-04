import 'package:flutter/material.dart';

import '../app/session_controller.dart';
import '../ui/app_theme.dart';
import 'live_room_screen.dart';

class IdentityConfirmScreen extends StatelessWidget {
  const IdentityConfirmScreen({
    super.key,
    required this.controller,
    this.onEnterRoom,
  });

  final SessionController controller;
  final VoidCallback? onEnterRoom;

  @override
  Widget build(BuildContext context) {
    final session = controller.session;
    final seat = session?.seatId.toUpperCase() ?? 'UNKNOWN';
    final perspective = session?.perspective ?? 'role-safe';

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              Text(
                '你的席位是 $seat',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: WerewolfAppTheme.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 12),
              const Text('参与者视角，不是上帝视角'),
              const SizedBox(height: 8),
              Text(
                'Perspective: $perspective',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: WerewolfAppTheme.textMuted,
                    ),
              ),
              const SizedBox(height: 18),
              const DecoratedBox(
                decoration: BoxDecoration(
                  color: WerewolfAppTheme.surface,
                  borderRadius: BorderRadius.all(Radius.circular(14)),
                ),
                child: Padding(
                  padding: EdgeInsets.all(14),
                  child: Text('你只会看到当前席位合法可见的信息。夜间他人行动会显示为等待状态。'),
                ),
              ),
              const Spacer(),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: FilledButton(
                  onPressed: onEnterRoom ??
                      () {
                        Navigator.of(context).pushReplacement(
                          MaterialPageRoute<void>(
                            builder: (_) =>
                                LiveRoomScreen(controller: controller),
                          ),
                        );
                      },
                  child: const Text('进入房间'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
