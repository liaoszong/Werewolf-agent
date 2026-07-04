import 'package:flutter/material.dart';

import '../app/app_strings.dart';
import '../protocol/participant_models.dart';
import 'app_theme.dart';

typedef SpeechSubmit = Future<void> Function(String text);
typedef StructuredSubmit = Future<void> Function(
  String actionType,
  Map<String, dynamic> payload,
);

class ComposerRail extends StatefulWidget {
  const ComposerRail({
    super.key,
    required this.window,
    this.errorMessage,
    required this.onSubmitSpeech,
    required this.onSubmitStructuredAction,
  });

  final ActionWindow? window;
  final String? errorMessage;
  final SpeechSubmit onSubmitSpeech;
  final StructuredSubmit onSubmitStructuredAction;

  @override
  State<ComposerRail> createState() => _ComposerRailState();
}

class _ComposerRailState extends State<ComposerRail> {
  final _text = TextEditingController();
  String? _selectedTarget;
  bool _collapsed = false;

  @override
  void didUpdateWidget(covariant ComposerRail oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.window?.id != widget.window?.id) {
      _collapsed = false;
      _selectedTarget = null;
      _text.clear();
    }
  }

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final window = widget.window;
    if (window == null || _collapsed) {
      return _CollapsedHandle(
        enabled: window != null,
        errorMessage: widget.errorMessage,
        onTap: () => setState(() => _collapsed = false),
      );
    }
    if (window.allowsTextInput) {
      return _TextComposer(
        controller: _text,
        label: _textActionLabel(window),
        errorMessage: widget.errorMessage,
        onCollapse: () => setState(() => _collapsed = true),
        onSend: () async {
          final text = _text.text.trim();
          if (text.isEmpty) return;
          await widget.onSubmitSpeech(text);
          _text.clear();
        },
      );
    }
    return _StructuredComposer(
      window: window,
      actionType: _primaryStructuredAction(window.allowedActions),
      selectedTarget: _selectedTarget,
      errorMessage: widget.errorMessage,
      onTargetSelected: (target) => setState(() => _selectedTarget = target),
      onPass: () {
        widget.onSubmitStructuredAction('pass', const {});
      },
      onCollapse: () => setState(() => _collapsed = true),
      onConfirm: () async {
        final action = _primaryStructuredAction(window.allowedActions);
        if (action == 'pass') {
          await widget.onSubmitStructuredAction('pass', const {});
          return;
        }
        final target = _selectedTarget;
        if (target == null) return;
        await widget.onSubmitStructuredAction(action, {'target': target});
      },
    );
  }

  String _primaryStructuredAction(List<String> actions) {
    for (final action in actions) {
      if (action != 'pass') return action;
    }
    return 'pass';
  }

  String _textActionLabel(ActionWindow window) {
    final strings = AppLanguageScope.of(context);
    if (window.allowedActions.contains('final_words') &&
        !window.allowedActions.contains('speech')) {
      return strings.finalWords;
    }
    return strings.speech;
  }
}

class _CollapsedHandle extends StatelessWidget {
  const _CollapsedHandle({
    required this.enabled,
    required this.errorMessage,
    required this.onTap,
  });

  final bool enabled;
  final String? errorMessage;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(0, 2, 0, 6),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (errorMessage != null) _ComposerError(message: errorMessage!),
            Center(
              child: IconButton(
                key: const Key('composer-collapsed-handle'),
                tooltip: enabled ? strings.expandComposer : strings.noAction,
                onPressed: enabled ? onTap : null,
                icon: Icon(
                  Icons.keyboard_arrow_up_rounded,
                  color: enabled
                      ? WerewolfAppTheme.accent
                      : WerewolfAppTheme.textMuted,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TextComposer extends StatelessWidget {
  const _TextComposer({
    required this.controller,
    required this.label,
    required this.errorMessage,
    required this.onCollapse,
    required this.onSend,
  });

  final TextEditingController controller;
  final String label;
  final String? errorMessage;
  final VoidCallback onCollapse;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (errorMessage != null) _ComposerError(message: errorMessage!),
            DecoratedBox(
              decoration: BoxDecoration(
                color: WerewolfAppTheme.surface,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: const Color(0xFF2D3744)),
              ),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(4, 4, 6, 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    IconButton(
                      key: const Key('composer-collapse-button'),
                      tooltip: strings.collapseComposer,
                      onPressed: onCollapse,
                      icon: const Icon(Icons.keyboard_arrow_down_rounded),
                    ),
                    Expanded(
                      child: TextField(
                        key: const Key('composer-text-input'),
                        controller: controller,
                        minLines: 1,
                        maxLines: 4,
                        textInputAction: TextInputAction.newline,
                        decoration: InputDecoration(
                          hintText: '$label...',
                          border: InputBorder.none,
                          isDense: true,
                        ),
                      ),
                    ),
                    IconButton.filled(
                      key: const Key('composer-send-button'),
                      tooltip: strings.send,
                      onPressed: onSend,
                      icon: const Icon(Icons.arrow_upward_rounded),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StructuredComposer extends StatelessWidget {
  const _StructuredComposer({
    required this.window,
    required this.actionType,
    required this.selectedTarget,
    required this.errorMessage,
    required this.onTargetSelected,
    required this.onPass,
    required this.onCollapse,
    required this.onConfirm,
  });

  final ActionWindow window;
  final String actionType;
  final String? selectedTarget;
  final String? errorMessage;
  final ValueChanged<String> onTargetSelected;
  final VoidCallback onPass;
  final VoidCallback onCollapse;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
    final strings = AppLanguageScope.of(context);
    final canPass = window.allowedActions.contains('pass');
    final needsTarget = actionType != 'pass';
    return SafeArea(
      top: false,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          color: WerewolfAppTheme.surface,
          border: Border(top: BorderSide(color: Color(0xFF2D3744))),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (errorMessage != null) _ComposerError(message: errorMessage!),
              Row(
                children: [
                  IconButton(
                    key: const Key('composer-collapse-button'),
                    tooltip: strings.collapseComposer,
                    onPressed: onCollapse,
                    icon: const Icon(Icons.keyboard_arrow_down_rounded),
                  ),
                  Expanded(
                    child: Text(
                      strings.actionLabel(actionType),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  if (canPass)
                    TextButton(
                      onPressed: onPass,
                      child: Text(strings.pass),
                    ),
                ],
              ),
              if (needsTarget) ...[
                const SizedBox(height: 4),
                Text(
                  strings.candidateTargets,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final seat in const [
                      'p1',
                      'p2',
                      'p3',
                      'p4',
                      'p5',
                      'p6',
                    ])
                      ChoiceChip(
                        label: Text(seat.toUpperCase()),
                        selected: selectedTarget == seat,
                        onSelected: (_) => onTargetSelected(seat),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton(
                  key: const Key('composer-confirm-button'),
                  onPressed:
                      actionType == 'pass' || selectedTarget != null
                          ? onConfirm
                          : null,
                  child: Text(strings.confirm),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

}

class _ComposerError extends StatelessWidget {
  const _ComposerError({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(6, 0, 6, 8),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: WerewolfAppTheme.danger.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: WerewolfAppTheme.danger.withValues(alpha: 0.35)),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          child: Row(
            children: [
              const Icon(Icons.error_outline_rounded, size: 18, color: WerewolfAppTheme.danger),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  message,
                  style: const TextStyle(color: WerewolfAppTheme.textPrimary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
