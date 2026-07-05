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
    required this.deadlineAt,
    required this.allowedActions,
    required this.required,
    required this.defaultOnTimeout,
    required this.status,
    required this.reconnectCursor,
  });

  final String id;
  final String runId;
  final String seatId;
  final String phase;
  final int round;
  final int gameRevision;
  final DateTime? deadlineAt;
  final List<String> allowedActions;
  final bool required;
  final String? defaultOnTimeout;
  final String status;
  final String reconnectCursor;

  bool get allowsTextInput {
    return allowedActions.contains('speech') ||
        allowedActions.contains('response') ||
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
      deadlineAt: _jsonDateTime(json['deadline_at']),
      allowedActions: (json['allowed_actions'] as List<dynamic>).cast<String>(),
      required: json['required'] as bool,
      defaultOnTimeout: _jsonString(json['default_on_timeout']),
      status: json['status'] as String,
      reconnectCursor: json['reconnect_cursor'] as String,
    );
  }
}

const _defaultSeatIds = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'];

Map<String, dynamic>? _jsonMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, item) => MapEntry(key.toString(), item));
}

List<Map<String, dynamic>> _jsonMapList(Object? value) {
  if (value is! List) return const [];
  final result = <Map<String, dynamic>>[];
  for (final item in value) {
    final map = _jsonMap(item);
    if (map != null) result.add(map);
  }
  return result;
}

String? _jsonString(Object? value) {
  if (value is String && value.isNotEmpty) return value;
  return null;
}

int? _jsonInt(Object? value) {
  if (value is int && !value.isNegative) return value;
  return null;
}

bool? _jsonBool(Object? value) {
  return value is bool ? value : null;
}

DateTime? _jsonDateTime(Object? value) {
  final text = _jsonString(value);
  if (text == null) return null;
  return DateTime.tryParse(text)?.toUtc();
}

String _firstString(Iterable<Object?> values, String fallback) {
  for (final value in values) {
    final text = _jsonString(value);
    if (text != null) return text;
  }
  return fallback;
}

class ProjectionPlayer {
  const ProjectionPlayer({
    required this.playerId,
    required this.displayRole,
    required this.displayTeam,
    required this.alive,
    required this.visibility,
    required this.source,
  });

  final String playerId;
  final String displayRole;
  final String displayTeam;
  final bool? alive;
  final String visibility;
  final String source;

  bool get isVisibleRole => displayRole != 'unknown';

  factory ProjectionPlayer.fromJson(Map<String, dynamic> json) {
    return ProjectionPlayer(
      playerId: _jsonString(json['player_id']) ?? 'unknown',
      displayRole: _jsonString(json['display_role']) ?? 'unknown',
      displayTeam: _jsonString(json['display_team']) ?? 'unknown',
      alive: _jsonBool(json['alive']),
      visibility: _jsonString(json['visibility']) ?? 'hidden',
      source: _jsonString(json['source']) ?? 'unknown',
    );
  }
}

class ProjectionSnapshot {
  const ProjectionSnapshot({
    required this.name,
    required this.type,
    required this.visible,
    required this.hidden,
    required this.round,
    required this.phase,
    required this.playerId,
    required this.team,
  });

  final String name;
  final String type;
  final bool visible;
  final bool hidden;
  final int? round;
  final String? phase;
  final String? playerId;
  final String? team;

  factory ProjectionSnapshot.fromJson(Map<String, dynamic> json) {
    return ProjectionSnapshot(
      name: _jsonString(json['snapshot_name']) ?? 'snapshot',
      type: _jsonString(json['snapshot_type']) ?? 'unknown',
      visible: _jsonBool(json['visible']) ?? false,
      hidden: _jsonBool(json['hidden']) ?? false,
      round: _jsonInt(json['round']),
      phase: _jsonString(json['phase']),
      playerId: _jsonString(json['player_id']),
      team: _jsonString(json['team']),
    );
  }
}

class ProjectionProof {
  const ProjectionProof({
    required this.source,
    required this.selfPlayerId,
    required this.selfRole,
    required this.selfTeam,
    required this.team,
  });

  final String source;
  final String? selfPlayerId;
  final String? selfRole;
  final String? selfTeam;
  final String? team;

  factory ProjectionProof.fromJson(Map<String, dynamic>? json) {
    return ProjectionProof(
      source: _jsonString(json?['source']) ?? 'unknown',
      selfPlayerId: _jsonString(json?['self_player_id']),
      selfRole: _jsonString(json?['self_role']),
      selfTeam: _jsonString(json?['self_team']),
      team: _jsonString(json?['team']),
    );
  }
}

class ProjectedEvent {
  const ProjectedEvent({
    required this.raw,
    required this.kind,
    required this.displayKind,
    required this.actor,
    required this.phase,
    required this.round,
    required this.text,
    required this.target,
  });

  final Map<String, dynamic> raw;
  final String kind;
  final String displayKind;
  final String actor;
  final String? phase;
  final int? round;
  final String text;
  final String? target;

  factory ProjectedEvent.fromJson(Map<String, dynamic> json) {
    final payload = _jsonMap(json['payload']);
    final data = _jsonMap(json['data']);
    final kind =
        _jsonString(json['kind']) ?? _jsonString(json['type']) ?? 'event';
    final payloadType = _jsonString(payload?['type']);
    final dataType = _jsonString(data?['type']);
    final displayKind = payloadType ?? dataType ?? kind;
    return ProjectedEvent(
      raw: json,
      kind: kind,
      displayKind: displayKind,
      actor: _jsonString(json['actor']) ?? 'system',
      phase: _jsonString(json['phase']),
      round: _jsonInt(json['round']),
      text: _firstString([
        data?['summary'],
        data?['message'],
        data?['text'],
        payload?['message'],
        payload?['summary'],
        payload?['text'],
        json['summary'],
        json['message'],
      ], displayKind),
      target: _jsonString(json['target']) ?? _jsonString(payload?['target']),
    );
  }
}

class ParticipantProjection {
  const ParticipantProjection({
    required this.contractVersion,
    required this.runId,
    required this.perspective,
    required this.viewKind,
    required this.players,
    required this.events,
    required this.hiddenEventCount,
    required this.snapshots,
    required this.hiddenSnapshotCount,
    required this.proof,
    required this.selfSeatId,
  });

  final String contractVersion;
  final String runId;
  final String perspective;
  final String viewKind;
  final List<ProjectionPlayer> players;
  final List<ProjectedEvent> events;
  final int hiddenEventCount;
  final List<ProjectionSnapshot> snapshots;
  final int hiddenSnapshotCount;
  final ProjectionProof proof;
  final String selfSeatId;

  List<ProjectionSnapshot> get visibleSnapshots {
    return snapshots.where((snapshot) => snapshot.visible).toList();
  }

  ProjectionPlayer? get selfPlayer {
    final proofSeat = proof.selfPlayerId;
    for (final player in players) {
      if (proofSeat != null && player.playerId == proofSeat) return player;
    }
    for (final player in players) {
      if (player.playerId == selfSeatId || player.visibility == 'self') {
        return player;
      }
    }
    return null;
  }

  String get selfRole {
    return proof.selfRole ?? selfPlayer?.displayRole ?? 'unknown';
  }

  String get selfTeam {
    return proof.selfTeam ?? selfPlayer?.displayTeam ?? proof.team ?? 'unknown';
  }

  List<ProjectionPlayer> get visibleWerewolfTeammates {
    if (selfRole != 'werewolf' && selfTeam != 'werewolf') return const [];
    final selfId = proof.selfPlayerId ?? selfPlayer?.playerId ?? selfSeatId;
    return players
        .where((player) {
          if (player.playerId == selfId) return false;
          return player.displayRole == 'werewolf' ||
              player.displayTeam == 'werewolf';
        })
        .toList(growable: false);
  }

  String? get currentPhase {
    for (final event in events.reversed) {
      if (event.phase != null) return event.phase;
    }
    for (final snapshot in snapshots.reversed) {
      if (snapshot.visible && snapshot.phase != null) return snapshot.phase;
    }
    return null;
  }

  int? get currentRound {
    for (final event in events.reversed) {
      if (event.round != null) return event.round;
    }
    for (final snapshot in snapshots.reversed) {
      if (snapshot.visible && snapshot.round != null) return snapshot.round;
    }
    return null;
  }

  factory ParticipantProjection.fromJson(
    Map<String, dynamic> json, {
    required String fallbackRunId,
    required String fallbackPerspective,
    required String selfSeatId,
  }) {
    return ParticipantProjection(
      contractVersion: _jsonString(json['contract_version']) ?? 'unknown',
      runId: _jsonString(json['run_id']) ?? fallbackRunId,
      perspective: _jsonString(json['perspective']) ?? fallbackPerspective,
      viewKind: _jsonString(json['view_kind']) ?? 'role',
      players: _jsonMapList(
        json['players'],
      ).map(ProjectionPlayer.fromJson).toList(growable: false),
      events: _jsonMapList(
        json['events'],
      ).map(ProjectedEvent.fromJson).toList(growable: false),
      hiddenEventCount: _jsonInt(json['hidden_event_count']) ?? 0,
      snapshots: _jsonMapList(
        json['snapshots'],
      ).map(ProjectionSnapshot.fromJson).toList(growable: false),
      hiddenSnapshotCount: _jsonInt(json['hidden_snapshot_count']) ?? 0,
      proof: ProjectionProof.fromJson(_jsonMap(json['proof'])),
      selfSeatId: selfSeatId,
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

  ParticipantProjection get projectionEnvelope {
    return ParticipantProjection.fromJson(
      projection,
      fallbackRunId: runId,
      fallbackPerspective: perspective,
      selfSeatId: seatId,
    );
  }

  List<ProjectedEvent> get projectedEvents => projectionEnvelope.events;

  List<Map<String, dynamic>> get visibleEvents {
    return _jsonMapList(projection['events']);
  }

  String? get currentPhase {
    return openActionWindow?.phase ??
        projectionEnvelope.currentPhase ??
        runStatus;
  }

  int? get currentRound {
    return openActionWindow?.round ?? projectionEnvelope.currentRound;
  }

  List<String> get targetCandidateSeatIds {
    final playerSeats = projectionEnvelope.players
        .where((player) => player.alive != false)
        .map((player) => player.playerId)
        .where((seat) => seat != 'unknown')
        .toList(growable: false);
    if (playerSeats.isNotEmpty) return playerSeats;
    return _defaultSeatIds;
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
