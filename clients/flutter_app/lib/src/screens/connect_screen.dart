import 'package:flutter/material.dart';

import '../app/session_controller.dart';
import '../protocol/participant_api_client.dart';
import '../ui/app_theme.dart';
import 'identity_confirm_screen.dart';

typedef SessionControllerFactory = SessionController Function(Uri baseUri);

class ConnectScreen extends StatefulWidget {
  const ConnectScreen({
    super.key,
    this.controllerFactory,
  });

  final SessionControllerFactory? controllerFactory;

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final _baseUrl = TextEditingController(text: 'http://127.0.0.1:8765');
  final _runId = TextEditingController();
  final _seatId = TextEditingController(text: 'p3');
  final _joinCode = TextEditingController(text: 'local-dev-code');
  bool _joining = false;
  String? _error;

  @override
  void dispose() {
    _baseUrl.dispose();
    _runId.dispose();
    _seatId.dispose();
    _joinCode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
          children: [
            const SizedBox(height: 24),
            Text(
              'Werewolf Agent',
              style: textTheme.headlineSmall?.copyWith(
                color: WerewolfAppTheme.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '加入你绑定的真人席位。客户端只连接 observer/participant 协议。',
              style: textTheme.bodyMedium?.copyWith(
                color: WerewolfAppTheme.textMuted,
              ),
            ),
            const SizedBox(height: 28),
            _ConnectField(
              key: const Key('base-url-input'),
              controller: _baseUrl,
              label: 'Observer base URL',
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 12),
            _ConnectField(
              key: const Key('run-id-input'),
              controller: _runId,
              label: 'Run ID',
            ),
            const SizedBox(height: 12),
            _ConnectField(
              key: const Key('seat-id-input'),
              controller: _seatId,
              label: 'Seat ID',
              textCapitalization: TextCapitalization.characters,
            ),
            const SizedBox(height: 12),
            _ConnectField(
              key: const Key('join-code-input'),
              controller: _joinCode,
              label: 'Join code',
            ),
            if (_error != null) ...[
              const SizedBox(height: 14),
              Text(
                _error!,
                style: textTheme.bodySmall?.copyWith(
                  color: WerewolfAppTheme.danger,
                ),
              ),
            ],
            const SizedBox(height: 24),
            SizedBox(
              height: 52,
              child: FilledButton(
                onPressed: _joining ? null : _join,
                child: Text(_joining ? '加入中...' : '加入席位'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _join() async {
    final baseUri = Uri.tryParse(_baseUrl.text.trim());
    if (baseUri == null || !baseUri.hasScheme) {
      setState(() => _error = '请输入有效的 observer base URL');
      return;
    }
    setState(() {
      _joining = true;
      _error = null;
    });

    final controller = (widget.controllerFactory ?? _defaultControllerFactory)
        .call(baseUri);
    await controller.joinAndLoad(
      runId: _runId.text.trim(),
      seatId: _seatId.text.trim().toLowerCase(),
      joinCode: _joinCode.text.trim(),
    );
    if (!mounted) return;
    if (controller.connectionStatus == ConnectionStatus.connected) {
      await Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => IdentityConfirmScreen(controller: controller),
      ));
      if (mounted) {
        setState(() => _joining = false);
      }
    } else {
      setState(() {
        _joining = false;
        _error = controller.lastError ?? '加入席位失败';
      });
    }
  }

  SessionController _defaultControllerFactory(Uri baseUri) {
    return SessionController(
      participantApi: ParticipantApiClient(baseUri: baseUri),
    );
  }
}

class _ConnectField extends StatelessWidget {
  const _ConnectField({
    super.key,
    required this.controller,
    required this.label,
    this.keyboardType,
    this.textCapitalization = TextCapitalization.none,
  });

  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  final TextCapitalization textCapitalization;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      textCapitalization: textCapitalization,
      decoration: InputDecoration(
        labelText: label,
        filled: true,
        fillColor: WerewolfAppTheme.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}
