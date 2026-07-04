import 'package:flutter/material.dart';

import '../screens/connect_screen.dart';
import '../ui/app_theme.dart';

class WerewolfApp extends StatelessWidget {
  const WerewolfApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Werewolf Agent',
      debugShowCheckedModeBanner: false,
      theme: WerewolfAppTheme.darkTheme(),
      home: const ConnectScreen(),
    );
  }
}
