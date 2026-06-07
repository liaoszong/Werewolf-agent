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


if __name__ == "__main__":
    unittest.main()
