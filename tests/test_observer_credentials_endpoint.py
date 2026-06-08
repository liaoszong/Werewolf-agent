import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.observer_server import ObserverServerState, _build_capabilities_payload


def _state(tmp, *, live_enabled, env_key_available, has_client_key):
    cs = CredentialStore()
    if has_client_key:
        cs.set("deepseek", "sk-test-fake-client-key")
    return ObserverServerState(
        runs_dir=Path(tmp), launcher=lambda r, d: 0,
        live_enabled=live_enabled,
        credential_store=cs,
        live_launcher_factory=(lambda api_key: (lambda r, d: 0)),
        env_key_available=env_key_available,
    )


class CapabilityCredentialTests(unittest.TestCase):
    def test_available_with_client_key_no_env(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=True, env_key_available=False, has_client_key=True))
            self.assertTrue(cap["live_api"]["providers"]["deepseek"]["available"])

    def test_available_with_env_no_client_key(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=True, env_key_available=True, has_client_key=False))
            self.assertTrue(cap["live_api"]["providers"]["deepseek"]["available"])

    def test_unavailable_with_neither(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=True, env_key_available=False, has_client_key=False))
            dp = cap["live_api"]["providers"]["deepseek"]
            self.assertFalse(dp["available"])
            self.assertEqual(dp["reason_code"], "missing_api_key")

    def test_unavailable_when_live_disabled(self) -> None:
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(_state(t, live_enabled=False, env_key_available=True, has_client_key=True))
            self.assertFalse(cap["live_api"]["enabled"])

    def test_per_provider_availability_is_independent(self) -> None:
        # P2-B per-provider: configuring ONLY openai makes openai available while
        # deepseek (and the others) stay unavailable — the bug being fixed is the
        # old any-provider result masquerading as deepseek.
        with TemporaryDirectory() as t:
            cs = CredentialStore()
            cs.set("openai", "sk-test-fake-openai-key")
            st = ObserverServerState(
                runs_dir=Path(t), launcher=lambda r, d: 0,
                live_enabled=True, credential_store=cs,
                env_key_available=False,
            )
            providers = _build_capabilities_payload(st)["live_api"]["providers"]
            self.assertTrue(providers["openai"]["available"])
            self.assertFalse(providers["deepseek"]["available"])
            self.assertEqual(providers["deepseek"]["reason_code"], "missing_api_key")
            self.assertFalse(providers["anthropic"]["available"])
            # every registry provider is reported (not just deepseek)
            self.assertIn("openai_compatible", providers)

    def test_deepseek_env_backcompat_does_not_leak_to_other_providers(self) -> None:
        # The legacy env key counts ONLY for deepseek; openai/anthropic must still
        # report unavailable when no client credential exists for them.
        with TemporaryDirectory() as t:
            cap = _build_capabilities_payload(
                _state(t, live_enabled=True, env_key_available=True, has_client_key=False)
            )
            providers = cap["live_api"]["providers"]
            self.assertTrue(providers["deepseek"]["available"])
            self.assertFalse(providers["openai"]["available"])
            self.assertFalse(providers["anthropic"]["available"])


from werewolf_eval.observer_server import (
    _credentials_post_result,
    _credentials_delete_result,
)


class CredentialsEndpointLogicTests(unittest.TestCase):
    def _cs(self):
        return CredentialStore()

    def test_post_stores_deepseek_and_does_not_echo_key(self):
        cs = self._cs()
        status, payload = _credentials_post_result(
            cs, "application/json", {"provider": "deepseek", "api_key": "sk-test-fake-xyz"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"stored": ["deepseek"]})
        self.assertNotIn("sk-test-fake-xyz", str(payload))
        self.assertTrue(cs.has("deepseek"))

    def test_post_rejects_non_json_content_type(self):
        cs = self._cs()
        status, payload = _credentials_post_result(cs, "text/plain", {"provider": "deepseek", "api_key": "k"})
        self.assertEqual(status, 415)
        self.assertFalse(cs.has("deepseek"))

    def test_post_accepts_charset_suffix(self):
        cs = self._cs()
        status, _ = _credentials_post_result(
            cs, "application/json; charset=utf-8", {"provider": "deepseek", "api_key": "sk-ok"}
        )
        self.assertEqual(status, 200)

    def test_post_rejects_empty_or_missing(self):
        cs = self._cs()
        for body in ({}, {"provider": "deepseek"}, {"provider": "deepseek", "api_key": ""}, {"api_key": "k"}):
            status, _ = _credentials_post_result(cs, "application/json", body)
            self.assertEqual(status, 400, body)
        self.assertFalse(cs.has("deepseek"))

    def test_post_rejects_non_allowlisted_provider(self):
        # P2-B-1 r2: registry providers are now allowlisted; only non-registry
        # ids (and the fake provider, which has no key) are rejected.
        cs = self._cs()
        for prov in ("fake_deterministic", "weird", "gemini"):
            status, _ = _credentials_post_result(cs, "application/json", {"provider": prov, "api_key": "k"})
            self.assertEqual(status, 400, prov)

    def test_post_accepts_deepseek_openai_anthropic(self):
        cs = self._cs()
        for prov in ("deepseek", "openai", "anthropic"):
            status, payload = _credentials_post_result(
                cs, "application/json", {"provider": prov, "api_key": "sk-fake"}
            )
            self.assertEqual(status, 200, prov)
            self.assertEqual(payload, {"stored": [prov]})
            self.assertTrue(cs.has(prov))

    def test_post_custom_requires_base_url(self):
        cs = self._cs()
        # openai_compatible requires a base_url (registry.requires_base_url)
        status, _ = _credentials_post_result(
            cs, "application/json", {"provider": "openai_compatible", "api_key": "k"}
        )
        self.assertEqual(status, 400)
        self.assertFalse(cs.has("openai_compatible"))
        status, payload = _credentials_post_result(
            cs,
            "application/json",
            {"provider": "openai_compatible", "api_key": "k", "base_url": "https://my.proxy/v1"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(cs.get_base_url("openai_compatible"), "https://my.proxy/v1")

    def test_post_rejects_non_http_base_url(self):
        cs = self._cs()
        for bad in ("ftp://x", "file:///etc/passwd", "api.openai.com", "gopher://x"):
            status, payload = _credentials_post_result(
                cs, "application/json",
                {"provider": "openai_compatible", "api_key": "k", "base_url": bad},
            )
            self.assertEqual(status, 400, bad)
            self.assertEqual(payload["error"], "invalid_base_url", bad)
        self.assertFalse(cs.has("openai_compatible"))

    def test_post_allows_localhost_http_base_url_for_local_models(self):
        # local model servers (Ollama / LM Studio) are a first-class use case.
        cs = self._cs()
        status, _ = _credentials_post_result(
            cs, "application/json",
            {"provider": "openai_compatible", "api_key": "k", "base_url": "http://localhost:11434/v1"},
        )
        self.assertEqual(status, 200)

    def test_post_stores_base_url_and_does_not_echo_secret(self):
        cs = self._cs()
        status, payload = _credentials_post_result(
            cs,
            "application/json",
            {"provider": "deepseek", "api_key": "sk-secret", "base_url": "https://api.deepseek.com"},
        )
        self.assertEqual(status, 200)
        self.assertNotIn("sk-secret", str(payload))
        self.assertEqual(cs.get_base_url("deepseek"), "https://api.deepseek.com")

    def test_delete_clears_and_is_idempotent(self):
        cs = self._cs()
        cs.set("deepseek", "sk-x")
        self.assertEqual(_credentials_delete_result(cs, "deepseek"), (200, {"cleared": "deepseek"}))
        self.assertFalse(cs.has("deepseek"))
        self.assertEqual(_credentials_delete_result(cs, "deepseek")[0], 200)   # idempotent
        self.assertEqual(_credentials_delete_result(cs, "openai")[0], 200)     # now allowlisted
        self.assertEqual(_credentials_delete_result(cs, "weird")[0], 400)      # still rejected

    def test_post_non_dict_json_body_is_rejected(self):
        """A parsed non-dict JSON value (array, string, number) must yield
        invalid_json — not be silently coerced to {} (fix 3)."""
        import io
        import json as _json
        import socket
        from unittest.mock import MagicMock, patch
        from werewolf_eval.observer_server import ObserverRequestHandler, ObserverServerState

        captured: list[tuple[int, str]] = []

        class _FakeHandler(ObserverRequestHandler):
            def __init__(self):  # noqa: D107
                pass  # skip BaseHTTPRequestHandler init

            def _send_error_json(self, status, code, message):
                captured.append((status, code))

            def _send_json(self, status, payload):
                captured.append((status, "ok"))

            def _is_loopback(self):
                return True

            def _get_state(self):
                cs = CredentialStore()
                return ObserverServerState(runs_dir=Path("/tmp"), launcher=lambda r, d: 0, credential_store=cs)

            @property
            def path(self):
                return "/api/credentials"

            @property
            def headers(self):
                h = MagicMock()
                h.get = lambda k, d="": {"Content-Type": "application/json", "Content-Length": str(len(self._raw))}.get(k, d)
                return h

            @property
            def rfile(self):
                return io.BytesIO(self._raw)

        for non_dict in (b"[]", b'["a","b"]', b'"hello"', b"42", b"true"):
            captured.clear()
            h = _FakeHandler()
            h._raw = non_dict
            h.do_POST()
            self.assertTrue(captured, f"no response captured for body {non_dict}")
            status, code = captured[0]
            self.assertEqual(status, 400, f"expected 400 for body {non_dict}, got {status}")
            self.assertEqual(code, "invalid_json", f"expected invalid_json for body {non_dict}, got {code}")


if __name__ == "__main__":
    unittest.main()
