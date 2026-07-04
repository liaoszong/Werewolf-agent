import 'package:flutter/material.dart';

import '../app/app_strings.dart';
import 'app_theme.dart';

class SpeechFeed extends StatelessWidget {
  const SpeechFeed({super.key, required this.events});

  final List<Map<String, dynamic>> events;

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) {
      return Center(child: Text(AppLanguageScope.of(context).visibleEventsWaiting));
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 96),
      itemCount: events.length,
      separatorBuilder: (context, index) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final event = events[index];
        final kind =
            event['kind'] as String? ?? event['type'] as String? ?? 'event';
        final actor = event['actor'] as String? ?? 'system';
        final text = _extractText(event, kind);
        if (_isPublicRuleEvent(kind)) {
          return _RuleEventPill(label: text);
        }
        return _SpeechBubble(actor: actor.toUpperCase(), text: text);
      },
    );
  }

  static String _extractText(Map<String, dynamic> event, String fallback) {
    final payload = event['payload'] ?? event['data'];
    if (payload is Map<String, dynamic>) {
      final message = payload['message'] ?? payload['summary'] ?? payload['text'];
      if (message is String && message.isNotEmpty) return message;
    }
    return fallback;
  }

  static bool _isPublicRuleEvent(String kind) {
    return kind == 'phase_changed' ||
        kind == 'vote_started' ||
        kind == 'vote_ended' ||
        kind == 'player_eliminated' ||
        kind == 'player_died' ||
        kind == 'game_completed' ||
        kind == 'game_over';
  }
}

class _SpeechBubble extends StatelessWidget {
  const _SpeechBubble({required this.actor, required this.text});

  final String actor;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 340),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: WerewolfAppTheme.surfaceElevated,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(actor, style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 6),
                RichText(text: highlightSpeechText(text)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RuleEventPill extends StatelessWidget {
  const _RuleEventPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: WerewolfAppTheme.surface,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: const Color(0xFF2D3744)),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          child: Text(label, style: Theme.of(context).textTheme.bodySmall),
        ),
      ),
    );
  }
}

InlineSpan highlightSpeechText(String text) {
  final pattern = RegExp(
    r'(P[1-6]|狼人|预言家|女巫|猎人|守卫|村民)',
    caseSensitive: false,
  );
  final spans = <TextSpan>[];
  var cursor = 0;
  for (final match in pattern.allMatches(text)) {
    if (match.start > cursor) {
      spans.add(TextSpan(text: text.substring(cursor, match.start)));
    }
    final token = match.group(0)!;
    spans.add(TextSpan(
      text: token,
      style: TextStyle(
        color: _highlightColor(token),
        fontWeight: FontWeight.w800,
      ),
    ));
    cursor = match.end;
  }
  if (cursor < text.length) {
    spans.add(TextSpan(text: text.substring(cursor)));
  }
  return TextSpan(
    style: const TextStyle(color: WerewolfAppTheme.textPrimary, height: 1.38),
    children: spans,
  );
}

Color _highlightColor(String token) {
  return switch (token.toUpperCase()) {
    '狼人' => WerewolfAppTheme.danger,
    '预言家' => WerewolfAppTheme.seer,
    '女巫' => WerewolfAppTheme.witch,
    '猎人' => WerewolfAppTheme.accent,
    '守卫' => const Color(0xFF8CC8FF),
    '村民' => WerewolfAppTheme.villager,
    _ => Colors.white,
  };
}
