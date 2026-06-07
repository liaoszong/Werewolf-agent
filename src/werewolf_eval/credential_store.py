"""In-memory, process-lifetime credential store for BYO-key live runs (P2-B-1).

Holds {provider: api_key} ONLY in process memory: never persisted, never logged,
never serialized into any artifact or HTTP response. The single plaintext-returning
method is `get`, called only by the launch wiring. `__repr__`/`__str__` are redacted
so a failing test or debug log can never print a key. Lock-guarded because the
observer runs on a ThreadingHTTPServer."""

from __future__ import annotations

import threading


class CredentialStore:
    def __init__(self) -> None:
        self._creds: dict[str, str] = {}
        self._lock = threading.Lock()

    def set(self, provider: str, api_key: str) -> None:
        if not api_key:
            raise ValueError("api_key must be non-empty")
        with self._lock:
            self._creds[provider] = api_key

    def get(self, provider: str) -> str | None:
        with self._lock:
            return self._creds.get(provider)

    def has(self, provider: str) -> bool:
        with self._lock:
            return provider in self._creds

    def clear(self, provider: str) -> bool:
        """Remove the provider's key. Returns True if one existed (idempotent)."""
        with self._lock:
            return self._creds.pop(provider, None) is not None

    def __repr__(self) -> str:
        with self._lock:
            return f"CredentialStore(providers={sorted(self._creds)})"

    __str__ = __repr__
