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

  Future<void> recoverAfterDisconnect() async {
    connectionStatus = ConnectionStatus.reconnecting;
    notifyListeners();
    try {
      await refreshState();
      connectionStatus = ConnectionStatus.connected;
      lastError = null;
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
    final actionType =
        actions.contains('final_words') && !actions.contains('speech')
        ? 'final_words'
        : 'speech';
    return _submitCurrentWindow(actionType, {'text': text});
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
      if (error.reconnectCursor != null) {
        await recoverAfterDisconnect();
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

  bool _shouldRefreshForEvent(String eventName) {
    return eventName == 'run_status' ||
        eventName == 'action_window_opened' ||
        eventName == 'action_window_updated' ||
        eventName == 'action_window_closed' ||
        eventName == 'action_window_timed_out' ||
        eventName == 'runtime_event';
  }

  @override
  void dispose() {
    unawaited(_eventSubscription?.cancel());
    super.dispose();
  }
}
