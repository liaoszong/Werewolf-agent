import 'package:flutter/material.dart';

import '../app/app_strings.dart';
import 'app_theme.dart';

class SpeechFeed extends StatelessWidget {
  const SpeechFeed({super.key, required this.events, this.currentSeatId});

  final List<Map<String, dynamic>> events;
  final String? currentSeatId;

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) return const _EmptyFeedState();
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 104),
      itemCount: events.length,
      separatorBuilder: (context, index) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final event = events[index];
        final kind =
            event['kind'] as String? ?? event['type'] as String? ?? 'event';
        final actor = event['actor'] as String? ?? 'system';
        final text = _extractText(event, kind);
        if (_isPublicRuleEvent(kind)) {
          return _RuleEventPill(kind: kind, label: text);
        }
        if (_isSpeechEvent(kind)) {
          return _SpeechBubble(
            actor: actor.toUpperCase(),
            text: text,
            kind: kind,
            phase: event['phase'] as String?,
            round: event['round'] as int?,
            isMine: actor.toLowerCase() == currentSeatId?.toLowerCase(),
          );
        }
        return _TimelineNotice(kind: kind, label: text);
      },
    );
  }

  static String _extractText(Map<String, dynamic> event, String fallback) {
    final payload = event['payload'] ?? event['data'];
    if (payload is Map<String, dynamic>) {
      final message =
          payload['message'] ?? payload['summary'] ?? payload['text'];
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

  static bool _isSpeechEvent(String kind) {
    return kind == 'player_speech' || kind == 'speech' || kind == 'final_words';
  }
}

class _EmptyFeedState extends StatelessWidget {
  const _EmptyFeedState();

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 28),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: palette.surface.withValues(
              alpha: palette.isDay ? 0.78 : 0.62,
            ),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: palette.border),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.visibility_off_outlined,
                  color: palette.textMuted,
                  size: 26,
                ),
                const SizedBox(height: 10),
                Text(
                  strings.visibleEventsWaiting,
                  textAlign: TextAlign.center,
                  style: Theme.of(
                    context,
                  ).textTheme.titleMedium?.copyWith(fontSize: 16),
                ),
                const SizedBox(height: 6),
                Text(
                  strings.legalInfoOnly,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SpeechBubble extends StatelessWidget {
  const _SpeechBubble({
    required this.actor,
    required this.text,
    required this.kind,
    required this.phase,
    required this.round,
    required this.isMine,
  });

  final String actor;
  final String text;
  final String kind;
  final String? phase;
  final int? round;
  final bool isMine;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    final width = MediaQuery.sizeOf(context).width;
    final maxWidth = (width - 54).clamp(250.0, 430.0).toDouble();
    final accentColor = isMine ? palette.accent : palette.border;
    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: DecoratedBox(
          key: const Key('speech-event-bubble'),
          decoration: BoxDecoration(
            color: isMine
                ? palette.accent.withValues(alpha: palette.isDay ? 0.13 : 0.16)
                : palette.surfaceElevated,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(20),
              topRight: const Radius.circular(20),
              bottomLeft: Radius.circular(isMine ? 20 : 8),
              bottomRight: Radius.circular(isMine ? 8 : 20),
            ),
            border: Border.all(color: accentColor.withValues(alpha: 0.44)),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(13, 11, 13, 12),
            child: Column(
              crossAxisAlignment: isMine
                  ? CrossAxisAlignment.end
                  : CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 7,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      actor,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: palette.textPrimary,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    _MetaChip(label: strings.eventKindLabel(kind)),
                    _MetaChip(label: strings.roundLabel(round)),
                    if (phase != null)
                      _MetaChip(label: strings.phaseLabel(phase)),
                  ],
                ),
                const SizedBox(height: 8),
                RichText(
                  textAlign: isMine ? TextAlign.right : TextAlign.left,
                  text: highlightSpeechText(context, text),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RuleEventPill extends StatelessWidget {
  const _RuleEventPill({required this.kind, required this.label});

  final String kind;
  final String label;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: DecoratedBox(
          key: const Key('speech-system-pill'),
          decoration: BoxDecoration(
            color: palette.surface,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: palette.border),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.circle_notifications_outlined,
                  size: 16,
                  color: palette.textMuted,
                ),
                const SizedBox(width: 7),
                Flexible(
                  child: Text(
                    '${strings.eventKindLabel(kind)} · $label',
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TimelineNotice extends StatelessWidget {
  const _TimelineNotice({required this.kind, required this.label});

  final String kind;
  final String label;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final palette = WerewolfAppTheme.colors(context);
    return DecoratedBox(
      key: const Key('speech-timeline-notice'),
      decoration: BoxDecoration(
        color: palette.control.withValues(alpha: palette.isDay ? 0.68 : 0.54),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: palette.border.withValues(alpha: 0.7)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            Icon(
              Icons.info_outline_rounded,
              size: 17,
              color: palette.textMuted,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '${strings.eventKindLabel(kind)} · $label',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: palette.textPrimary),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: palette.control,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            fontSize: 10,
            color: palette.textMuted,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

InlineSpan highlightSpeechText(BuildContext context, String text) {
  final palette = WerewolfAppTheme.colors(context);
  final pattern = RegExp(r'(P[1-6]|狼人|预言家|女巫|猎人|守卫|村民)', caseSensitive: false);
  final spans = <TextSpan>[];
  var cursor = 0;
  for (final match in pattern.allMatches(text)) {
    if (match.start > cursor) {
      spans.add(TextSpan(text: text.substring(cursor, match.start)));
    }
    final token = match.group(0)!;
    spans.add(
      TextSpan(
        text: token,
        style: TextStyle(
          color: _highlightColor(token, palette),
          fontWeight: FontWeight.w800,
        ),
      ),
    );
    cursor = match.end;
  }
  if (cursor < text.length) {
    spans.add(TextSpan(text: text.substring(cursor)));
  }
  return TextSpan(
    style: TextStyle(color: palette.textPrimary, height: 1.42, fontSize: 15),
    children: spans,
  );
}

Color _highlightColor(String token, WerewolfPalette palette) {
  return switch (token.toUpperCase()) {
    '狼人' => palette.danger,
    '预言家' => palette.seer,
    '女巫' => palette.witch,
    '猎人' => palette.accent,
    '守卫' => const Color(0xFF8CC8FF),
    '村民' => palette.villager,
    _ => palette.textPrimary,
  };
}
