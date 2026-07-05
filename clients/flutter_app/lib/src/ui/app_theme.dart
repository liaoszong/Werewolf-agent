import 'package:flutter/material.dart';

import '../app/app_settings.dart';

class WerewolfPalette extends ThemeExtension<WerewolfPalette> {
  const WerewolfPalette({
    required this.background,
    required this.surface,
    required this.surfaceElevated,
    required this.control,
    required this.controlSelected,
    required this.textPrimary,
    required this.textMuted,
    required this.border,
    required this.shadow,
    required this.accent,
    required this.danger,
    required this.seer,
    required this.witch,
    required this.villager,
    required this.isDay,
  });

  final Color background;
  final Color surface;
  final Color surfaceElevated;
  final Color control;
  final Color controlSelected;
  final Color textPrimary;
  final Color textMuted;
  final Color border;
  final Color shadow;
  final Color accent;
  final Color danger;
  final Color seer;
  final Color witch;
  final Color villager;
  final bool isDay;

  @override
  WerewolfPalette copyWith({
    Color? background,
    Color? surface,
    Color? surfaceElevated,
    Color? control,
    Color? controlSelected,
    Color? textPrimary,
    Color? textMuted,
    Color? border,
    Color? shadow,
    Color? accent,
    Color? danger,
    Color? seer,
    Color? witch,
    Color? villager,
    bool? isDay,
  }) {
    return WerewolfPalette(
      background: background ?? this.background,
      surface: surface ?? this.surface,
      surfaceElevated: surfaceElevated ?? this.surfaceElevated,
      control: control ?? this.control,
      controlSelected: controlSelected ?? this.controlSelected,
      textPrimary: textPrimary ?? this.textPrimary,
      textMuted: textMuted ?? this.textMuted,
      border: border ?? this.border,
      shadow: shadow ?? this.shadow,
      accent: accent ?? this.accent,
      danger: danger ?? this.danger,
      seer: seer ?? this.seer,
      witch: witch ?? this.witch,
      villager: villager ?? this.villager,
      isDay: isDay ?? this.isDay,
    );
  }

  @override
  WerewolfPalette lerp(ThemeExtension<WerewolfPalette>? other, double t) {
    if (other is! WerewolfPalette) return this;
    return WerewolfPalette(
      background: Color.lerp(background, other.background, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceElevated: Color.lerp(surfaceElevated, other.surfaceElevated, t)!,
      control: Color.lerp(control, other.control, t)!,
      controlSelected: Color.lerp(controlSelected, other.controlSelected, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textMuted: Color.lerp(textMuted, other.textMuted, t)!,
      border: Color.lerp(border, other.border, t)!,
      shadow: Color.lerp(shadow, other.shadow, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      seer: Color.lerp(seer, other.seer, t)!,
      witch: Color.lerp(witch, other.witch, t)!,
      villager: Color.lerp(villager, other.villager, t)!,
      isDay: t < 0.5 ? isDay : other.isDay,
    );
  }
}

class WerewolfAppTheme {
  static const night = WerewolfPalette(
    background: Color(0xFF0D1118),
    surface: Color(0xFF151B24),
    surfaceElevated: Color(0xFF1C2530),
    control: Color(0xFF222B36),
    controlSelected: Color(0xFF332B1C),
    textPrimary: Color(0xFFE8EDF3),
    textMuted: Color(0xFF96A2AF),
    border: Color(0xFF2D3744),
    shadow: Color(0xAA000000),
    accent: Color(0xFFF0C76A),
    danger: Color(0xFFE35757),
    seer: Color(0xFF6EA8FF),
    witch: Color(0xFF6FD6A6),
    villager: Color(0xFFBBC4CE),
    isDay: false,
  );

  static const day = WerewolfPalette(
    background: Color(0xFFF8F7F3),
    surface: Color(0xFFFFFFFF),
    surfaceElevated: Color(0xFFF0EEE9),
    control: Color(0xFFEDEBE6),
    controlSelected: Color(0xFFE4DED2),
    textPrimary: Color(0xFF151515),
    textMuted: Color(0xFF686661),
    border: Color(0xFFE7E3DB),
    shadow: Color(0x26000000),
    accent: Color(0xFF80623B),
    danger: Color(0xFFB6433C),
    seer: Color(0xFF3667A8),
    witch: Color(0xFF3E7F55),
    villager: Color(0xFF6D716F),
    isDay: true,
  );

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

  static WerewolfPalette colors(BuildContext context) {
    return Theme.of(context).extension<WerewolfPalette>() ?? night;
  }

  static ThemeData themeFor(AppAppearance appearance) {
    final palette = appearance == AppAppearance.day ? day : night;
    final brightness = appearance == AppAppearance.day
        ? Brightness.light
        : Brightness.dark;
    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      scaffoldBackgroundColor: palette.background,
      splashFactory: NoSplash.splashFactory,
      splashColor: Colors.transparent,
      highlightColor: Colors.transparent,
      hoverColor: Colors.transparent,
      colorScheme: ColorScheme.fromSeed(
        seedColor: palette.accent,
        brightness: brightness,
        primary: palette.accent,
        surface: palette.surface,
        error: palette.danger,
      ),
      extensions: [palette],
      textTheme: TextTheme(
        bodyMedium: TextStyle(color: palette.textPrimary, height: 1.35),
        bodySmall: TextStyle(color: palette.textMuted, height: 1.25),
        titleMedium: TextStyle(
          color: palette.textPrimary,
          fontWeight: FontWeight.w700,
        ),
        labelSmall: TextStyle(color: palette.textMuted, height: 1.2),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: palette.control,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: palette.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: palette.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: palette.accent, width: 1.2),
        ),
      ),
    );
  }

  static ThemeData darkTheme() => themeFor(AppAppearance.night);
}
