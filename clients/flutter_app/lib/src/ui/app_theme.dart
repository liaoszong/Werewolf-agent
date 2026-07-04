import 'package:flutter/material.dart';

class WerewolfAppTheme {
  static const background = Color(0xFF0D1118);
  static const surface = Color(0xFF151B24);
  static const surfaceElevated = Color(0xFF1C2530);
  static const textPrimary = Color(0xFFE8EDF3);
  static const textMuted = Color(0xFF96A2AF);
  static const accent = Color(0xFFF0C76A);
  static const danger = Color(0xFFE35757);
  static const seer = Color(0xFF6EA8FF);
  static const witch = Color(0xFF6FD6A6);
  static const villager = Color(0xFFBBC4CE);

  static ThemeData darkTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        surface: surface,
        primary: accent,
        error: danger,
      ),
      textTheme: const TextTheme(
        bodyMedium: TextStyle(color: textPrimary, height: 1.35),
        bodySmall: TextStyle(color: textMuted, height: 1.25),
        titleMedium: TextStyle(
          color: textPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
