import 'dart:convert';

import 'package:http/http.dart' as http;

class RunSummary {
  const RunSummary({required this.runId, required this.status});

  final String runId;
  final String status;

  factory RunSummary.fromJson(Map<String, dynamic> json) {
    return RunSummary(
      runId: (json['run_id'] ?? json['id']) as String,
      status: json['status'] as String? ?? 'unknown',
    );
  }
}

class ObserverApiClient {
  ObserverApiClient({required this.baseUri, http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  final Uri baseUri;
  final http.Client _http;

  Future<List<RunSummary>> listRuns() async {
    final response = await _http.get(baseUri.resolve('/api/runs'));
    final decoded = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      throw StateError('listRuns failed: ${response.statusCode}');
    }
    final runs = decoded is Map<String, dynamic> ? decoded['runs'] : decoded;
    if (runs is! List) return const [];
    return runs
        .whereType<Map<String, dynamic>>()
        .map(RunSummary.fromJson)
        .toList(growable: false);
  }
}
