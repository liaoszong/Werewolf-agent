import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.credential_store import CredentialStore

_KEY = "sk-test-fake-credential-store-1234"


class CredentialStoreTests(unittest.TestCase):
    def test_set_get_has_clear(self) -> None:
        s = CredentialStore()
        self.assertFalse(s.has("deepseek"))
        self.assertIsNone(s.get("deepseek"))
        s.set("deepseek", _KEY)
        self.assertTrue(s.has("deepseek"))
        self.assertEqual(s.get("deepseek"), _KEY)
        self.assertTrue(s.clear("deepseek"))      # existed -> True
        self.assertFalse(s.has("deepseek"))
        self.assertFalse(s.clear("deepseek"))     # idempotent -> False

    def test_repr_and_str_never_contain_key(self) -> None:
        s = CredentialStore()
        s.set("deepseek", _KEY)
        self.assertNotIn(_KEY, repr(s))
        self.assertNotIn(_KEY, str(s))
        self.assertNotIn("sk-", repr(s))

    def test_thread_safe_set_get(self) -> None:
        s = CredentialStore()
        errors: list = []

        def worker(i: int) -> None:
            try:
                for _ in range(200):
                    s.set("deepseek", f"sk-{i}")
                    s.get("deepseek")
                    s.has("deepseek")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertTrue(s.has("deepseek"))

    def test_thread_safe_set_clear(self) -> None:
        """set and clear interleaved across 8 threads must never raise."""
        s = CredentialStore()
        errors: list = []

        def worker(i: int) -> None:
            try:
                for _ in range(200):
                    s.set("deepseek", f"sk-{i}")
                    s.has("deepseek")
                    s.clear("deepseek")
                    s.get("deepseek")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_non_string_provider_rejected(self) -> None:
        s = CredentialStore()
        with self.assertRaises(TypeError):
            s.set(42, "sk-valid-key")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            s.has(42)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            s.get(42)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            s.clear(42)  # type: ignore[arg-type]

    def test_empty_key_rejected(self) -> None:
        s = CredentialStore()
        with self.assertRaises(ValueError):
            s.set("deepseek", "")

    # P2-B-1 r2: per-provider base_url (custom OpenAI-compatible endpoints).
    def test_set_with_base_url_is_retrievable(self) -> None:
        s = CredentialStore()
        s.set("openai_compatible", _KEY, "https://my.proxy/v1")
        self.assertEqual(s.get("openai_compatible"), _KEY)
        self.assertEqual(s.get_base_url("openai_compatible"), "https://my.proxy/v1")

    def test_base_url_defaults_empty_when_set_without_one(self) -> None:
        s = CredentialStore()
        s.set("deepseek", _KEY)  # 2-arg back-compat
        self.assertEqual(s.get_base_url("deepseek"), "")

    def test_base_url_none_for_absent_provider(self) -> None:
        s = CredentialStore()
        self.assertIsNone(s.get_base_url("openai"))

    def test_repr_never_contains_base_url_or_key(self) -> None:
        s = CredentialStore()
        s.set("openai_compatible", _KEY, "https://secret.host/internal")
        self.assertNotIn("secret.host", repr(s))
        self.assertNotIn(_KEY, repr(s))


if __name__ == "__main__":
    unittest.main()
