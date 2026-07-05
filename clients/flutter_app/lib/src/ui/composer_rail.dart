import 'package:flutter/material.dart';

import '../app/app_strings.dart';
import '../protocol/participant_models.dart';
import 'app_theme.dart';

typedef SpeechSubmit = Future<void> Function(String text);
typedef StructuredSubmit =
    Future<void> Function(String actionType, Map<String, dynamic> payload);

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
    final palette = WerewolfAppTheme.colors(context);
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
                  color: enabled ? palette.accent : palette.textMuted,
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
    final palette = WerewolfAppTheme.colors(context);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (errorMessage != null) _ComposerError(message: errorMessage!),
            ConstrainedBox(
              key: const Key('composer-input-shell'),
              constraints: const BoxConstraints(minHeight: 54, maxHeight: 64),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: palette.surface,
                  borderRadius: BorderRadius.circular(28),
                  border: Border.all(color: palette.border),
                  boxShadow: [
                    BoxShadow(
                      color: palette.shadow,
                      blurRadius: 22,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(4, 3, 5, 3),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 44,
                        height: 44,
                        child: IconButton(
                          key: const Key('composer-collapse-button'),
                          tooltip: strings.collapseComposer,
                          onPressed: onCollapse,
                          icon: Icon(
                            Icons.keyboard_arrow_down_rounded,
                            color: palette.textPrimary,
                          ),
                        ),
                      ),
                      Expanded(
                        child: TextField(
                          key: const Key('composer-text-input'),
                          controller: controller,
                          minLines: 1,
                          maxLines: 3,
                          textAlignVertical: TextAlignVertical.center,
                          textInputAction: TextInputAction.newline,
                          style: TextStyle(
                            color: palette.textPrimary,
                            fontSize: 18,
                            height: 1.2,
                          ),
                          decoration: InputDecoration(
                            hintText: '$label...',
                            hintStyle: TextStyle(
                              color: palette.textMuted,
                              fontSize: 18,
                            ),
                            border: InputBorder.none,
                            enabledBorder: InputBorder.none,
                            focusedBorder: InputBorder.none,
                            filled: false,
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(
                              vertical: 12,
                              horizontal: 2,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      SizedBox(
                        width: 44,
                        height: 44,
                        child: IconButton.filled(
                          key: const Key('composer-send-button'),
                          tooltip: strings.send,
                          onPressed: onSend,
                          style: IconButton.styleFrom(
                            backgroundColor: palette.textPrimary,
                            foregroundColor: palette.background,
                          ),
                          icon: const Icon(Icons.arrow_upward_rounded),
                        ),
                      ),
                    ],
                  ),
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
    final palette = WerewolfAppTheme.colors(context);
    final canPass = window.allowedActions.contains('pass');
    final needsTarget = actionType != 'pass';
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (errorMessage != null) _ComposerError(message: errorMessage!),
            DecoratedBox(
              key: const Key('structured-composer-shell'),
              decoration: BoxDecoration(
                color: palette.surface,
                borderRadius: BorderRadius.circular(26),
                border: Border.all(
                  color: palette.accent.withValues(alpha: 0.36),
                ),
                boxShadow: [
                  BoxShadow(
                    color: palette.shadow,
                    blurRadius: 24,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 10, 12),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        IconButton(
                          key: const Key('composer-collapse-button'),
                          tooltip: strings.collapseComposer,
                          onPressed: onCollapse,
                          icon: Icon(
                            Icons.keyboard_arrow_down_rounded,
                            color: palette.textPrimary,
                          ),
                        ),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                strings.actionLabel(actionType),
                                style: Theme.of(
                                  context,
                                ).textTheme.titleMedium?.copyWith(fontSize: 16),
                              ),
                              const SizedBox(height: 3),
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: [
                                  _ActionWindowChip(
                                    label: strings.actionWindowOpen,
                                    icon: Icons.bolt_rounded,
                                  ),
                                  _ActionWindowChip(
                                    label: strings.roundLabel(window.round),
                                    icon: Icons.track_changes_rounded,
                                  ),
                                  _ActionWindowChip(
                                    label: strings.phaseLabel(window.phase),
                                    icon: Icons.timelapse_rounded,
                                  ),
                                  _ActionWindowChip(
                                    label: window.required
                                        ? strings.requiredAction
                                        : strings.optionalAction,
                                    icon: window.required
                                        ? Icons.priority_high_rounded
                                        : Icons.check_circle_outline_rounded,
                                  ),
                                ],
                              ),
                            ],
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
                      const SizedBox(height: 10),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        child: Text(
                          strings.candidateTargets,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        child: Wrap(
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
                                selectedColor: palette.accent.withValues(
                                  alpha: palette.isDay ? 0.24 : 0.20,
                                ),
                                backgroundColor: palette.control,
                                side: BorderSide(
                                  color: selectedTarget == seat
                                      ? palette.accent.withValues(alpha: 0.64)
                                      : palette.border,
                                ),
                                labelStyle: TextStyle(
                                  color: palette.textPrimary,
                                  fontWeight: FontWeight.w800,
                                ),
                                showCheckmark: false,
                                onSelected: (_) => onTargetSelected(seat),
                              ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 12),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          key: const Key('composer-confirm-button'),
                          onPressed:
                              actionType == 'pass' || selectedTarget != null
                              ? onConfirm
                              : null,
                          icon: const Icon(Icons.arrow_upward_rounded),
                          label: Text(strings.confirm),
                        ),
                      ),
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

class _ActionWindowChip extends StatelessWidget {
  const _ActionWindowChip({required this.label, required this.icon});

  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final palette = WerewolfAppTheme.colors(context);
    return DecoratedBox(
      key: const Key('action-window-chip'),
      decoration: BoxDecoration(
        color: palette.control,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: palette.border.withValues(alpha: 0.78)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 13, color: palette.textMuted),
            const SizedBox(width: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: palette.textMuted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
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
    final palette = WerewolfAppTheme.colors(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(6, 0, 6, 8),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: palette.danger.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: palette.danger.withValues(alpha: 0.35)),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          child: Row(
            children: [
              Icon(
                Icons.error_outline_rounded,
                size: 18,
                color: palette.danger,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  message,
                  style: TextStyle(color: palette.textPrimary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
