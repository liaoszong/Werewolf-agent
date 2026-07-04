class ParticipantSession {
  const ParticipantSession({
    required this.runId,
    required this.seatId,
    required this.perspective,
    required this.token,
    required this.reconnectCursor,
  });

  final String runId;
  final String seatId;
  final String perspective;
  final String token;
  final String reconnectCursor;

  factory ParticipantSession.fromJson(Map<String, dynamic> json) {
    return ParticipantSession(
      runId: json['run_id'] as String,
      seatId: json['seat_id'] as String,
      perspective: json['perspective'] as String,
      token: json['participant_session_token'] as String,
      reconnectCursor: json['reconnect_cursor'] as String,
    );
  }
}

class ActionWindow {
  const ActionWindow({
    required this.id,
    required this.runId,
    required this.seatId,
    required this.phase,
    required this.round,
    required this.gameRevision,
    required this.allowedActions,
    required this.required,
    required this.status,
    required this.reconnectCursor,
  });

  final String id;
  final String runId;
  final String seatId;
  final String phase;
  final int round;
  final int gameRevision;
  final List<String> allowedActions;
  final bool required;
  final String status;
  final String reconnectCursor;

  bool get allowsTextInput {
    return allowedActions.contains('speech') ||
        allowedActions.contains('final_words');
  }

  bool get allowsStructuredChoice {
    return allowedActions.any((action) {
      return action == 'vote' ||
          action == 'werewolf_kill' ||
          action == 'seer_check' ||
          action == 'witch_save' ||
          action == 'witch_poison' ||
          action == 'guard_protect' ||
          action == 'hunter_shoot';
    });
  }

  factory ActionWindow.fromJson(Map<String, dynamic> json) {
    return ActionWindow(
      id: json['action_window_id'] as String,
      runId: json['run_id'] as String,
      seatId: json['seat_id'] as String,
      phase: json['phase'] as String,
      round: json['round'] as int,
      gameRevision: json['game_revision'] as int,
      allowedActions:
          (json['allowed_actions'] as List<dynamic>).cast<String>(),
      required: json['required'] as bool,
      status: json['status'] as String,
      reconnectCursor: json['reconnect_cursor'] as String,
    );
  }
}

class ParticipantState {
  const ParticipantState({
    required this.runId,
    required this.seatId,
    required this.perspective,
    required this.runStatus,
    required this.projection,
    required this.openActionWindow,
    required this.reconnectCursor,
  });

  final String runId;
  final String seatId;
  final String perspective;
  final String runStatus;
  final Map<String, dynamic> projection;
  final ActionWindow? openActionWindow;
  final String reconnectCursor;

  List<Map<String, dynamic>> get visibleEvents {
    final events = projection['events'];
    if (events is! List) return const [];
    return events
        .whereType<Map<String, dynamic>>()
        .toList(growable: false);
  }

  factory ParticipantState.fromJson(Map<String, dynamic> json) {
    final window = json['open_action_window'];
    return ParticipantState(
      runId: json['run_id'] as String,
      seatId: json['seat_id'] as String,
      perspective: json['perspective'] as String,
      runStatus: json['run_status'] as String,
      projection: (json['projection'] as Map<String, dynamic>?) ?? const {},
      openActionWindow: window is Map<String, dynamic>
          ? ActionWindow.fromJson(window)
          : null,
      reconnectCursor: json['reconnect_cursor'] as String,
    );
  }
}

class ParticipantActionResult {
  const ParticipantActionResult({
    required this.status,
    required this.actionWindowId,
    required this.reconnectCursor,
    this.acceptedEventId,
    this.gameRevision,
  });

  final String status;
  final String actionWindowId;
  final String reconnectCursor;
  final String? acceptedEventId;
  final int? gameRevision;

  factory ParticipantActionResult.fromJson(Map<String, dynamic> json) {
    return ParticipantActionResult(
      status: json['status'] as String,
      actionWindowId: json['action_window_id'] as String,
      reconnectCursor: json['reconnect_cursor'] as String,
      acceptedEventId: json['accepted_event_id'] as String?,
      gameRevision: json['game_revision'] as int?,
    );
  }
}

class ParticipantApiError implements Exception {
  ParticipantApiError({
    required this.statusCode,
    required this.errorCode,
    required this.message,
    this.reconnectCursor,
  });

  final int statusCode;
  final String errorCode;
  final String message;
  final String? reconnectCursor;

  factory ParticipantApiError.fromJson(
    int statusCode,
    Map<String, dynamic> json,
  ) {
    return ParticipantApiError(
      statusCode: statusCode,
      errorCode: json['error_code'] as String? ?? 'unknown_error',
      message: json['message'] as String? ?? 'Participant request failed',
      reconnectCursor: json['reconnect_cursor'] as String?,
    );
  }

  @override
  String toString() => '$errorCode: $message';
}
