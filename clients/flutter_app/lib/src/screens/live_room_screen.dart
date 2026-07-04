import 'package:flutter/material.dart';

import '../app/session_controller.dart';

class LiveRoomScreen extends StatelessWidget {
  const LiveRoomScreen({super.key, required this.controller});

  final SessionController controller;

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: SafeArea(
        child: Center(child: Text('Live room')),
      ),
    );
  }
}
