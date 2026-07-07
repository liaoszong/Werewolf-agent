import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ProviderLocalCredential {
  const ProviderLocalCredential({
    required this.provider,
    required this.hasApiKey,
    required this.baseUrl,
    required this.selectedModel,
  });

  final String provider;
  final bool hasApiKey;
  final String baseUrl;
  final String selectedModel;
}

abstract interface class ProviderCredentialStore {
  Future<ProviderLocalCredential> read(String provider);

  Future<String> readActiveProvider({String fallback = 'deepseek'});

  Future<void> writeActiveProvider(String provider);

  Future<String?> readApiKey(String provider);

  Future<void> writeApiKey(String provider, String apiKey);

  Future<void> deleteApiKey(String provider);

  Future<void> writeBaseUrl(String provider, String baseUrl);

  Future<void> writeSelectedModel(String provider, String model);

  Future<String?> readOwnerToken(String observerBaseUri);

  Future<void> writeOwnerToken(String observerBaseUri, String ownerToken);
}

class SecureProviderCredentialStore implements ProviderCredentialStore {
  SecureProviderCredentialStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<ProviderLocalCredential> read(String provider) async {
    final key = await readApiKey(provider);
    return ProviderLocalCredential(
      provider: provider,
      hasApiKey: key != null && key.isNotEmpty,
      baseUrl: await _storage.read(key: _baseUrlKey(provider)) ?? '',
      selectedModel: await _storage.read(key: _modelKey(provider)) ?? '',
    );
  }

  @override
  Future<String> readActiveProvider({String fallback = 'deepseek'}) async {
    final provider = await _storage.read(key: _activeProviderKey);
    return provider == null || provider.isEmpty ? fallback : provider;
  }

  @override
  Future<void> writeActiveProvider(String provider) {
    return _storage.write(key: _activeProviderKey, value: provider);
  }

  @override
  Future<String?> readApiKey(String provider) {
    return _storage.read(key: _apiKeyKey(provider));
  }

  @override
  Future<void> writeApiKey(String provider, String apiKey) {
    return _storage.write(key: _apiKeyKey(provider), value: apiKey);
  }

  @override
  Future<void> deleteApiKey(String provider) {
    return _storage.delete(key: _apiKeyKey(provider));
  }

  @override
  Future<void> writeBaseUrl(String provider, String baseUrl) async {
    final key = _baseUrlKey(provider);
    if (baseUrl.trim().isEmpty) {
      await _storage.delete(key: key);
      return;
    }
    await _storage.write(key: key, value: baseUrl.trim());
  }

  @override
  Future<void> writeSelectedModel(String provider, String model) async {
    final key = _modelKey(provider);
    if (model.trim().isEmpty) {
      await _storage.delete(key: key);
      return;
    }
    await _storage.write(key: key, value: model.trim());
  }

  @override
  Future<String?> readOwnerToken(String observerBaseUri) {
    return _storage.read(key: _ownerTokenKey(observerBaseUri));
  }

  @override
  Future<void> writeOwnerToken(
    String observerBaseUri,
    String ownerToken,
  ) async {
    final key = _ownerTokenKey(observerBaseUri);
    if (ownerToken.trim().isEmpty) {
      await _storage.delete(key: key);
      return;
    }
    await _storage.write(key: key, value: ownerToken.trim());
  }

  static const _activeProviderKey = 'werewolf.provider.active';

  static String _apiKeyKey(String provider) =>
      'werewolf.provider.$provider.key';

  static String _baseUrlKey(String provider) =>
      'werewolf.provider.$provider.base_url';

  static String _modelKey(String provider) =>
      'werewolf.provider.$provider.model';

  static String _ownerTokenKey(String observerBaseUri) =>
      'werewolf.observer.${_storageSafe(observerBaseUri)}.owner_token';

  static String _storageSafe(String value) =>
      base64Url.encode(utf8.encode(value)).replaceAll('=', '');
}

class MemoryProviderCredentialStore implements ProviderCredentialStore {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<ProviderLocalCredential> read(String provider) async {
    final key = await readApiKey(provider);
    return ProviderLocalCredential(
      provider: provider,
      hasApiKey: key != null && key.isNotEmpty,
      baseUrl: _values[_baseUrlKey(provider)] ?? '',
      selectedModel: _values[_modelKey(provider)] ?? '',
    );
  }

  @override
  Future<String> readActiveProvider({String fallback = 'deepseek'}) async {
    final provider = _values[_activeProviderKey];
    return provider == null || provider.isEmpty ? fallback : provider;
  }

  @override
  Future<void> writeActiveProvider(String provider) async {
    _values[_activeProviderKey] = provider;
  }

  @override
  Future<String?> readApiKey(String provider) async {
    return _values[_apiKeyKey(provider)];
  }

  @override
  Future<void> writeApiKey(String provider, String apiKey) async {
    _values[_apiKeyKey(provider)] = apiKey;
  }

  @override
  Future<void> deleteApiKey(String provider) async {
    _values.remove(_apiKeyKey(provider));
  }

  @override
  Future<void> writeBaseUrl(String provider, String baseUrl) async {
    final key = _baseUrlKey(provider);
    if (baseUrl.trim().isEmpty) {
      _values.remove(key);
      return;
    }
    _values[key] = baseUrl.trim();
  }

  @override
  Future<void> writeSelectedModel(String provider, String model) async {
    final key = _modelKey(provider);
    if (model.trim().isEmpty) {
      _values.remove(key);
      return;
    }
    _values[key] = model.trim();
  }

  @override
  Future<String?> readOwnerToken(String observerBaseUri) async {
    return _values[_ownerTokenKey(observerBaseUri)];
  }

  @override
  Future<void> writeOwnerToken(
    String observerBaseUri,
    String ownerToken,
  ) async {
    final key = _ownerTokenKey(observerBaseUri);
    if (ownerToken.trim().isEmpty) {
      _values.remove(key);
      return;
    }
    _values[key] = ownerToken.trim();
  }

  static const _activeProviderKey = 'werewolf.provider.active';

  static String _apiKeyKey(String provider) =>
      'werewolf.provider.$provider.key';

  static String _baseUrlKey(String provider) =>
      'werewolf.provider.$provider.base_url';

  static String _modelKey(String provider) =>
      'werewolf.provider.$provider.model';

  static String _ownerTokenKey(String observerBaseUri) =>
      'werewolf.observer.${_storageSafe(observerBaseUri)}.owner_token';

  static String _storageSafe(String value) =>
      base64Url.encode(utf8.encode(value)).replaceAll('=', '');
}
