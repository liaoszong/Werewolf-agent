import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../protocol/participant_api_client.dart';
import '../protocol/participant_models.dart';

enum ConnectionStatus {
  idle,
  connecting,
  connected,
  reconnecting,
  sessionExpired,
  failed,
}

class SessionController extends ChangeNotifier {
  SessionController({required ParticipantApiClient participantApi})
    : _participantApi = participantApi;

  final ParticipantApiClient _participantApi;
  final Random _random = Random();
  StreamSubscription<ParticipantSseEvent>? _eventSubscription;

  ParticipantSession? session;
  ParticipantState? state;
  ConnectionStatus connectionStatus = ConnectionStatus.idle;
  String? lastError;
  bool isSubmittingAction = false;

  Future<void> joinAndLoad({
    required String runId,
    required String seatId,
    required String joinCode,
  }) async {
    connectionStatus = ConnectionStatus.connecting;
    lastError = null;
    notifyListeners();
    try {
      session = await _participantApi.join(
        runId: runId,
        seatId: seatId,
        joinCode: joinCode,
      );
      await refreshState();
      connectionStatus = ConnectionStatus.connected;
      _startEventStream();
    } on ParticipantApiError catch (error) {
      connectionStatus = error.errorCode == 'missing_or_invalid_session'
          ? ConnectionStatus.sessionExpired
          : ConnectionStatus.failed;
      lastError = error.message;
    } catch (error) {
      connectionStatus = ConnectionStatus.failed;
      lastError = error.toString();
    }
    notifyListeners();
  }

  Future<void> refreshState() async {
    final active = session;
    if (active == null) return;
    state = await _participantApi.state(
      runId: active.runId,
      token: active.token,
    );
    notifyListeners();
  }

  Future<void> recoverAfterDisconnect({bool clearLastError = true}) async {
    connectionStatus = ConnectionStatus.reconnecting;
    notifyListeners();
    try {
      await refreshState();
      connectionStatus = ConnectionStatus.connected;
      if (clearLastError) lastError = null;
      _startEventStream();
    } on ParticipantApiError catch (error) {
      connectionStatus = error.errorCode == 'missing_or_invalid_session'
          ? ConnectionStatus.sessionExpired
          : ConnectionStatus.failed;
      lastError = error.message;
    }
    notifyListeners();
  }

  Future<void> submitSpeech(String text) {
    final actions = state?.openActionWindow?.allowedActions ?? const [];
    return _submitCurrentWindow(_textActionType(actions), {'text': text});
  }

  String _textActionType(List<String> actions) {
    if (actions.contains('speech')) return 'speech';
    if (actions.contains('response')) return 'response';
    if (actions.contains('final_words')) return 'final_words';
    return 'speech';
  }

  Future<void> submitStructuredAction({
    required String actionType,
    required Map<String, dynamic> payload,
  }) {
    return _submitCurrentWindow(actionType, payload);
  }

  Future<void> _submitCurrentWindow(
    String actionType,
    Map<String, dynamic> payload,
  ) async {
    final active = session;
    final window = state?.openActionWindow;
    if (active == null || window == null || isSubmittingAction) return;
    isSubmittingAction = true;
    lastError = null;
    notifyListeners();
    try {
      await _participantApi.submitAction(
        runId: active.runId,
        token: active.token,
        payload: {
          'action_window_id': window.id,
          'game_revision': window.gameRevision,
          'idempotency_key': _newIdempotencyKey(),
          'action_type': actionType,
          'payload': payload,
        },
      );
      lastError = null;
      await refreshState();
    } on ParticipantApiError catch (error) {
      lastError = error.message;
      if (error.errorCode == 'missing_or_invalid_session') {
        connectionStatus = ConnectionStatus.sessionExpired;
      } else if (error.reconnectCursor != null) {
        await recoverAfterDisconnect(clearLastError: false);
        lastError = error.message;
      }
      notifyListeners();
    } finally {
      isSubmittingAction = false;
      notifyListeners();
    }
  }

  String _newIdempotencyKey() {
    final micros = DateTime.now().microsecondsSinceEpoch;
    final suffix = _random.nextInt(1 << 32).toRadixString(16);
    return 'flutter-$micros-$suffix';
  }

  void _startEventStream() {
    final active = session;
    if (active == null) return;
    unawaited(_eventSubscription?.cancel());
    final cursor = state?.reconnectCursor ?? active.reconnectCursor;
    _eventSubscription = _participantApi
        .events(runId: active.runId, token: active.token, cursor: cursor)
        .listen(
          (event) async {
            _applyEventSideEffects(event);
            if (_shouldRefreshForEvent(event.name)) {
              await refreshState();
            }
          },
          onError: (Object error) {
            connectionStatus = ConnectionStatus.reconnecting;
            lastError = error.toString();
            notifyListeners();
            unawaited(recoverAfterDisconnect());
          },
        );
  }

  void _applyEventSideEffects(ParticipantSseEvent event) {
    if (event.name == 'action_rejected') {
      final message = event.data['message'];
      if (message is String && message.isNotEmpty) {
        lastError = message;
        notifyListeners();
      }
    } else if (event.name == 'action_accepted' && lastError != null) {
      lastError = null;
      notifyListeners();
    }
  }

  bool _shouldRefreshForEvent(String eventName) {
    return eventName == 'run_status' ||
        eventName == 'participant_projection_updated' ||
        eventName == 'action_window_opened' ||
        eventName == 'action_window_updated' ||
        eventName == 'action_window_closed' ||
        eventName == 'action_window_timed_out' ||
        eventName == 'action_accepted' ||
        eventName == 'action_rejected' ||
        eventName == 'runtime_event';
  }

  @override
  void dispose() {
    unawaited(_eventSubscription?.cancel());
    super.dispose();
  }
}
