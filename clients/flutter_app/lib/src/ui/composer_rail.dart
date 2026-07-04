import 'package:flutter/material.dart';

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
    required this.onSubmitSpeech,
    required this.onSubmitStructuredAction,
  });

  final ActionWindow? window;
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
        onTap: () => setState(() => _collapsed = false),
      );
    }
    if (window.allowsTextInput) {
      return _TextComposer(
        controller: _text,
        label: _textActionLabel(window),
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
    if (window.allowedActions.contains('final_words') &&
        !window.allowedActions.contains('speech')) {
      return '留下遗言';
    }
    return '发言';
  }
}

class _CollapsedHandle extends StatelessWidget {
  const _CollapsedHandle({
    required this.enabled,
    required this.onTap,
  });

  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(0, 2, 0, 6),
        child: Center(
          child: IconButton(
            key: const Key('composer-collapsed-handle'),
            tooltip: enabled ? '展开行动框' : '暂无行动',
            onPressed: enabled ? onTap : null,
            icon: Icon(
              Icons.keyboard_arrow_up_rounded,
              color: enabled
                  ? WerewolfAppTheme.accent
                  : WerewolfAppTheme.textMuted,
            ),
          ),
        ),
      ),
    );
  }
}

class _TextComposer extends StatelessWidget {
  const _TextComposer({
    required this.controller,
    required this.label,
    required this.onCollapse,
    required this.onSend,
  });

  final TextEditingController controller;
  final String label;
  final VoidCallback onCollapse;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
        child: DecoratedBox(
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
                  tooltip: '收起行动框',
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
                  tooltip: '发送',
                  onPressed: onSend,
                  icon: const Icon(Icons.arrow_upward_rounded),
                ),
              ],
            ),
          ),
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
    required this.onTargetSelected,
    required this.onPass,
    required this.onCollapse,
    required this.onConfirm,
  });

  final ActionWindow window;
  final String actionType;
  final String? selectedTarget;
  final ValueChanged<String> onTargetSelected;
  final VoidCallback onPass;
  final VoidCallback onCollapse;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
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
              Row(
                children: [
                  IconButton(
                    key: const Key('composer-collapse-button'),
                    tooltip: '收起行动框',
                    onPressed: onCollapse,
                    icon: const Icon(Icons.keyboard_arrow_down_rounded),
                  ),
                  Expanded(
                    child: Text(
                      _actionLabel(actionType),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  if (canPass)
                    TextButton(
                      onPressed: onPass,
                      child: const Text('跳过'),
                    ),
                ],
              ),
              if (needsTarget) ...[
                const SizedBox(height: 4),
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
                  child: const Text('确认'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _actionLabel(String actionType) {
    return switch (actionType) {
      'vote' => '投票',
      'werewolf_kill' => '选择击杀目标',
      'seer_check' => '选择查验目标',
      'witch_save' => '选择解药目标',
      'witch_poison' => '选择毒药目标',
      'guard_protect' => '选择守护目标',
      'hunter_shoot' => '选择开枪目标',
      'pass' => '跳过行动',
      _ => '选择行动',
    };
  }
}
