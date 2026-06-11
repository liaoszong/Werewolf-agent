"""Pure endpoint logic for credentials CRUD + provider model discovery
(SYS-C2 split). Already function-level testable; the HTTP handler translates
these ``(status, payload)`` results into responses. NEVER returns or logs a key.
"""

from __future__ import annotations

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.llm_providers import ChatProviderConfig
from werewolf_eval.provider_registry import PROVIDER_REGISTRY, list_models

# P2-B-1 r2: credential writes now accept every registry provider (the single
# source of truth). Custom OpenAI-compatible endpoints additionally require a
# base_url. (The live-launch GATE that requires a credential per seat is P2-B-4.)
_CREDENTIAL_PROVIDERS: frozenset[str] = frozenset(PROVIDER_REGISTRY)


def _credentials_post_result(
    store: "CredentialStore", content_type: str, body: dict[str, object]
) -> tuple[int, dict[str, object]]:
    """Pure logic for POST /api/credentials. NEVER returns or logs the key."""
    if str(content_type or "").split(";")[0].strip() != "application/json":
        return (415, {"error": "unsupported_media_type"})
    provider = body.get("provider")
    api_key = body.get("api_key")
    base_url = body.get("base_url", "")
    if not isinstance(provider, str) or provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    if not isinstance(api_key, str) or not api_key:
        return (400, {"error": "missing_api_key"})
    if not isinstance(base_url, str):
        return (400, {"error": "invalid_base_url"})
    # Only http(s) endpoints are fetchable; reject file://, gopher://, schemeless,
    # etc. (localhost/private hosts are intentionally allowed — local model servers
    # like Ollama/LM Studio are a first-class BYO-key use case).
    if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
        return (400, {"error": "invalid_base_url"})
    if PROVIDER_REGISTRY[provider].requires_base_url and not base_url:
        return (400, {"error": "missing_base_url"})
    store.set(provider, api_key, base_url)
    return (200, {"stored": [provider]})


def _credentials_delete_result(
    store: "CredentialStore", provider: str
) -> tuple[int, dict[str, object]]:
    """Pure logic for DELETE /api/credentials/{provider}. Idempotent."""
    if provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    store.clear(provider)
    return (200, {"cleared": provider})


def _provider_models_result(
    store: "CredentialStore", provider: str, transport=None
) -> tuple[int, dict[str, object]]:
    """Pure logic for GET /api/providers/{provider}/models. Fetches the live model
    list from the provider using the session credential. NEVER returns or logs the
    key; upstream failures collapse to a sanitized code."""
    if provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    key = store.get(provider)
    if not key:
        return (403, {"error": "missing_api_key"})
    base_url = store.get_base_url(provider) or ""
    config = ChatProviderConfig(api_key=key, base_url=base_url)
    try:
        models = list_models(provider, config, transport=transport)
    except Exception:
        # Never surface the upstream message (could carry url/auth); fail closed.
        return (502, {"error": "provider_unavailable"})
    return (200, {"provider": provider, "models": models})
