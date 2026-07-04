import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'participant_models.dart';

class ParticipantSseEvent {
  const ParticipantSseEvent({required this.name, required this.data});

  final String name;
  final Map<String, dynamic> data;
}

class ParticipantApiClient {
  ParticipantApiClient({
    required this.baseUri,
    http.Client? httpClient,
  }) : _http = httpClient ?? http.Client();

  final Uri baseUri;
  final http.Client _http;

  Future<ParticipantSession> join({
    required String runId,
    required String seatId,
    required String joinCode,
  }) async {
    final response = await _http.post(
      _uri('/api/runs/$runId/participants/join'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'seat_id': seatId, 'join_code': joinCode}),
    );
    final body = _decode(response);
    if (response.statusCode >= 400) {
      throw ParticipantApiError.fromJson(response.statusCode, body);
    }
    return ParticipantSession.fromJson(body);
  }

  Future<ParticipantState> state({
    required String runId,
    required String token,
  }) async {
    final response = await _http.get(
      _uri('/api/runs/$runId/participant/state'),
      headers: _authHeaders(token),
    );
    final body = _decode(response);
    if (response.statusCode >= 400) {
      throw ParticipantApiError.fromJson(response.statusCode, body);
    }
    return ParticipantState.fromJson(body);
  }

  Future<ParticipantActionResult> submitAction({
    required String runId,
    required String token,
    required Map<String, dynamic> payload,
  }) async {
    final response = await _http.post(
      _uri('/api/runs/$runId/participant/actions'),
      headers: {'Content-Type': 'application/json', ..._authHeaders(token)},
      body: jsonEncode(payload),
    );
    final body = _decode(response);
    if (response.statusCode >= 400) {
      throw ParticipantApiError.fromJson(response.statusCode, body);
    }
    return ParticipantActionResult.fromJson(body);
  }

  Stream<ParticipantSseEvent> events({
    required String runId,
    required String token,
    required String cursor,
  }) async* {
    final request = http.Request(
      'GET',
      _uri('/api/runs/$runId/participant/events?cursor=$cursor'),
    );
    request.headers.addAll(_authHeaders(token));
    final response = await _http.send(request);
    if (response.statusCode >= 400) {
      final text = await response.stream.bytesToString();
      throw ParticipantApiError.fromJson(
        response.statusCode,
        jsonDecode(text) as Map<String, dynamic>,
      );
    }

    String? eventName;
    final dataLines = <String>[];
    await for (final line in response.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())) {
      if (line.isEmpty) {
        if (eventName != null && dataLines.isNotEmpty) {
          yield ParticipantSseEvent(
            name: eventName,
            data: jsonDecode(dataLines.join('\n')) as Map<String, dynamic>,
          );
        }
        eventName = null;
        dataLines.clear();
      } else if (line.startsWith('event: ')) {
        eventName = line.substring('event: '.length);
      } else if (line.startsWith('data: ')) {
        dataLines.add(line.substring('data: '.length));
      }
    }
  }

  Uri _uri(String pathAndQuery) => baseUri.resolve(pathAndQuery);

  Map<String, String> _authHeaders(String token) {
    return {'Authorization': 'Bearer $token'};
  }

  Map<String, dynamic> _decode(http.Response response) {
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
