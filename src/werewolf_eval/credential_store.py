"""In-memory, process-lifetime credential store for BYO-key live runs (P2-B-1).

Holds {provider: {key, base_url}} ONLY in process memory: never persisted, never
logged, never serialized into any artifact or HTTP response. The plaintext-returning
methods (`get`, `get_base_url`) are called by the launch wiring, the capability check,
and the dynamic-model endpoint. `__repr__`/`__str__` are redacted so a failing test or
debug log can never print a key (or a private base_url). Lock-guarded because the
observer runs on a ThreadingHTTPServer.

P2-B-1 r2: per-provider ``base_url`` was added (custom OpenAI-compatible endpoints
require one). ``set(provider, api_key)`` stays 2-arg back-compatible; ``get`` still
returns the key string."""

from __future__ import annotations

import threading


class CredentialStore:
    def __init__(self) -> None:
        self._creds: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()

    def set(self, provider: str, api_key: str, base_url: str = "") -> None:
        if not isinstance(provider, str):
            raise TypeError("provider must be a str")
        if not api_key:
            raise ValueError("api_key must be non-empty")
        with self._lock:
            self._creds[provider] = {"key": api_key, "base_url": base_url or ""}

    def get(self, provider: str) -> str | None:
        if not isinstance(provider, str):
            raise TypeError("provider must be a str")
        with self._lock:
            entry = self._creds.get(provider)
            return entry["key"] if entry is not None else None

    def get_base_url(self, provider: str) -> str | None:
        """The provider's stored base_url ("" if none was supplied), or None when
        no credential exists for the provider."""
        if not isinstance(provider, str):
            raise TypeError("provider must be a str")
        with self._lock:
            entry = self._creds.get(provider)
            return entry["base_url"] if entry is not None else None

    def has(self, provider: str) -> bool:
        if not isinstance(provider, str):
            raise TypeError("provider must be a str")
        with self._lock:
            return provider in self._creds

    def clear(self, provider: str) -> bool:
        """Remove the provider's key. Returns True if one existed (idempotent)."""
        if not isinstance(provider, str):
            raise TypeError("provider must be a str")
        with self._lock:
            return self._creds.pop(provider, None) is not None

    def __repr__(self) -> str:
        with self._lock:
            return f"CredentialStore(providers={sorted(self._creds)})"

    __str__ = __repr__
