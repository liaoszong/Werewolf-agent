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

class ObserverApiError implements Exception {
  const ObserverApiError(this.operation, this.statusCode, this.code);

  final String operation;
  final int statusCode;
  final String code;

  @override
  String toString() => '$operation failed: $statusCode $code';
}

class ProviderSpecSummary {
  const ProviderSpecSummary({
    required this.id,
    required this.label,
    required this.defaultBaseUrl,
    required this.requiresBaseUrl,
    required this.defaultModels,
  });

  final String id;
  final String label;
  final String defaultBaseUrl;
  final bool requiresBaseUrl;
  final List<String> defaultModels;

  factory ProviderSpecSummary.fromJson(Map<String, dynamic> json) {
    return ProviderSpecSummary(
      id: json['id'] as String,
      label: json['label'] as String? ?? json['id'] as String,
      defaultBaseUrl: json['default_base_url'] as String? ?? '',
      requiresBaseUrl: json['requires_base_url'] as bool? ?? false,
      defaultModels: (json['default_models'] as List? ?? const [])
          .whereType<String>()
          .toList(growable: false),
    );
  }
}

class ObserverApiClient {
  ObserverApiClient({
    required this.baseUri,
    http.Client? httpClient,
    this.ownerToken,
  }) : _http = httpClient ?? http.Client();

  final Uri baseUri;
  final http.Client _http;
  String? ownerToken;

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

  Future<List<ProviderSpecSummary>> listProviderSpecs() async {
    final response = await _http.get(baseUri.resolve('/api/profiles/schema'));
    final decoded = _decodeObject(response);
    if (response.statusCode >= 400) {
      throw _error('listProviderSpecs', response.statusCode, decoded);
    }
    final specs = decoded['provider_specs'];
    if (specs is! List) return const [];
    return specs
        .whereType<Map<String, dynamic>>()
        .map(ProviderSpecSummary.fromJson)
        .toList(growable: false);
  }

  Future<String> createParticipantRun({required String seatId}) async {
    final response = await _http.post(
      baseUri.resolve('/api/runs'),
      headers: _headers(contentTypeJson: true),
      body: jsonEncode({
        'participant': {'seat_id': seatId},
      }),
    );
    final decoded = _decodeObject(response);
    if (response.statusCode >= 400) {
      throw _error('createParticipantRun', response.statusCode, decoded);
    }
    final runId = decoded['run_id'];
    if (runId is String && runId.isNotEmpty) return runId;
    throw const ObserverApiError('createParticipantRun', 500, 'missing_run_id');
  }

  Future<void> saveProviderCredential({
    required String provider,
    required String apiKey,
    String baseUrl = '',
  }) async {
    final body = <String, Object>{
      'provider': provider,
      'api_key': apiKey,
      if (baseUrl.trim().isNotEmpty) 'base_url': baseUrl.trim(),
    };
    final response = await _http.post(
      baseUri.resolve('/api/credentials'),
      headers: _headers(contentTypeJson: true),
      body: jsonEncode(body),
    );
    final decoded = _decodeObject(response);
    if (response.statusCode >= 400) {
      throw _error('saveProviderCredential', response.statusCode, decoded);
    }
  }

  Future<void> clearProviderCredential(String provider) async {
    final encoded = Uri.encodeComponent(provider);
    final response = await _http.delete(
      baseUri.resolve('/api/credentials/$encoded'),
      headers: _headers(),
    );
    final decoded = _decodeObject(response);
    if (response.statusCode >= 400) {
      throw _error('clearProviderCredential', response.statusCode, decoded);
    }
  }

  Future<List<String>> fetchProviderModels(String provider) async {
    final encoded = Uri.encodeComponent(provider);
    final response = await _http.get(
      baseUri.resolve('/api/providers/$encoded/models'),
      headers: _headers(),
    );
    final decoded = _decodeObject(response);
    if (response.statusCode >= 400) {
      throw _error('fetchProviderModels', response.statusCode, decoded);
    }
    return (decoded['models'] as List? ?? const []).whereType<String>().toList(
      growable: false,
    );
  }

  Map<String, dynamic> _decodeObject(http.Response response) {
    Object? decoded;
    try {
      decoded = jsonDecode(response.body);
    } on FormatException {
      return <String, dynamic>{};
    }
    return decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
  }

  ObserverApiError _error(
    String operation,
    int statusCode,
    Map<String, dynamic> body,
  ) {
    final code =
        body['error_code'] as String? ??
        body['error'] as String? ??
        body['code'] as String? ??
        'http_$statusCode';
    return ObserverApiError(operation, statusCode, code);
  }

  Map<String, String> _headers({bool contentTypeJson = false}) {
    final headers = <String, String>{};
    if (contentTypeJson) {
      headers['Content-Type'] = 'application/json';
    }
    final token = ownerToken?.trim();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }
}
