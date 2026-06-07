import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.observer_server import _resolve_live_launcher_for_launch

_CLIENT = "sk-test-fake-client-AAAA"
_ENV = "sk-test-fake-env-BBBB"


class ResolveLiveLauncherTests(unittest.TestCase):
    def _state(self, *, client, env):
        cs = CredentialStore()
        if client:
            cs.set("deepseek", _CLIENT)
        captured = {}

        def factory(api_key):
            captured["key"] = api_key
            return lambda r, d: 0

        from werewolf_eval.observer_server import ObserverServerState
        st = ObserverServerState(
            runs_dir=Path("."), launcher=lambda r, d: 0,
            live_enabled=True, credential_store=cs,
            live_launcher_factory=factory,
            env_key_available=bool(env),
            live_launcher=(lambda r, d: 0) if env else None,
        )
        return st, captured

    def test_client_key_preferred_over_env(self):
        st, captured = self._state(client=True, env=True)
        launcher, err = _resolve_live_launcher_for_launch(st)
        self.assertIsNone(err)
        self.assertIsNotNone(launcher)
        self.assertEqual(captured["key"], _CLIENT)   # client beats env

    def test_env_fallback_when_no_client_key(self):
        st, captured = self._state(client=False, env=True)
        launcher, err = _resolve_live_launcher_for_launch(st)
        self.assertIsNone(err)
        self.assertIs(launcher, st.live_launcher)    # uses the prebuilt env launcher

    def test_error_when_neither(self):
        st, _ = self._state(client=False, env=False)
        st.live_launcher = None
        st.env_key_available = False
        launcher, err = _resolve_live_launcher_for_launch(st)
        self.assertIsNone(launcher)
        self.assertEqual(err[1], "missing_api_key")


def _live_profile():
    """Minimal valid profile with deepseek seats (matches canonical 6P shape)."""
    from werewolf_eval.profile_config import PROFILE_SCHEMA_VERSION
    rd = {
        role: {"provider": "deepseek", "model": "deepseek-chat", "prompt": "p", "strategy": "default"}
        for role in ("werewolf", "seer", "witch", "villager")
    }
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "name": "test-live",
        "template": "default_6p_fake",
        "role_defaults": rd,
    }


class ResolvedProfileNoKeyTests(unittest.TestCase):
    def test_resolved_profile_artifact_has_no_credential(self):
        from werewolf_eval.profile_config import build_resolved_profile_artifact
        profile = _live_profile()
        art = build_resolved_profile_artifact(profile, "r1", execution_mode="live", live_api="used")
        blob = json.dumps(art)
        for marker in ("sk-", "api_key", "authorization", "bearer"):
            self.assertNotIn(marker, blob.lower())
