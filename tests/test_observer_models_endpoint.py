from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.observer_server import _provider_models_result


def _ok_models_transport(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
    _ok_models_transport.seen = {"url": url, "headers": dict(headers)}  # type: ignore[attr-defined]
    return {"object": "list", "data": [{"id": "deepseek-v4-flash"}, {"id": "deepseek-v4-pro"}]}


class ProviderModelsEndpointTests(unittest.TestCase):
    def test_unsupported_provider_400(self) -> None:
        cs = CredentialStore()
        status, payload = _provider_models_result(cs, "gemini", transport=_ok_models_transport)
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "unsupported_provider")

    def test_missing_key_403(self) -> None:
        cs = CredentialStore()
        status, payload = _provider_models_result(cs, "deepseek", transport=_ok_models_transport)
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "missing_api_key")

    def test_returns_model_ids_for_configured_provider(self) -> None:
        cs = CredentialStore()
        cs.set("deepseek", "sk-fake")
        status, payload = _provider_models_result(cs, "deepseek", transport=_ok_models_transport)
        self.assertEqual(status, 200)
        self.assertEqual(payload["provider"], "deepseek")
        self.assertEqual(payload["models"], ["deepseek-v4-flash", "deepseek-v4-pro"])

    def test_uses_stored_base_url_and_auth_without_echoing_key(self) -> None:
        cs = CredentialStore()
        cs.set("openai_compatible", "sk-secret-models", "https://my.proxy/v1")
        status, payload = _provider_models_result(
            cs, "openai_compatible", transport=_ok_models_transport
        )
        self.assertEqual(status, 200)
        seen = _ok_models_transport.seen  # type: ignore[attr-defined]
        self.assertEqual(seen["url"], "https://my.proxy/v1/models")
        # the key never appears in the returned payload
        self.assertNotIn("sk-secret-models", str(payload))

    def test_upstream_error_collapses_to_502_without_leaking_key(self) -> None:
        def boom(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
            raise RuntimeError(f"HTTP 401 {headers.get('Authorization', '')}")

        cs = CredentialStore()
        cs.set("deepseek", "sk-secret-key")
        status, payload = _provider_models_result(cs, "deepseek", transport=boom)
        self.assertEqual(status, 502)
        self.assertEqual(payload["error"], "provider_unavailable")
        self.assertNotIn("sk-secret-key", str(payload))


if __name__ == "__main__":
    unittest.main()
