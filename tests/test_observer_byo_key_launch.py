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


class NoOrphanRunDirOnLiveRejectTests(unittest.TestCase):
    """Regression: run_dir must NOT be created when the live launcher can't be
    resolved (missing credential).  Before the fix, mkdir ran before the
    resolver, leaving an orphan directory that caused any retry to 409."""

    def _make_state(self, tmp: str) -> "ObserverServerState":
        from werewolf_eval.observer_server import ObserverServerState
        from werewolf_eval.credential_store import CredentialStore
        cs = CredentialStore()  # empty — no key stored
        return ObserverServerState(
            runs_dir=Path(tmp),
            launcher=lambda r, d: 0,
            live_enabled=True,
            credential_store=cs,
            live_launcher_factory=None,  # no factory
            env_key_available=False,     # no env key
            live_launcher=None,          # no prebuilt launcher
        )

    def test_no_run_dir_created_on_missing_api_key_reject(self):
        """_handle_profile_launch with live mode and no credential must send a
        403 missing_api_key AND must leave runs_dir empty (no orphan subdir)."""
        from werewolf_eval.observer_server import (
            ObserverRequestHandler,
            ObserverServerState,
        )

        # Capture what _send_error_json and _send_json receive.
        captured_errors: list[tuple[int, str, str]] = []
        captured_ok: list[tuple[int, object]] = []

        class _FakeHandler(ObserverRequestHandler):
            def __init__(self):  # noqa: D107
                pass  # skip BaseHTTPRequestHandler init

            def _send_error_json(self, status, code, message):
                captured_errors.append((status, code, message))

            def _send_json(self, status, payload):
                captured_ok.append((status, payload))

            def _get_state(self_h):
                return self._state_obj  # type: ignore[attr-defined]

            def _read_json_body(self):
                return self._body  # type: ignore[attr-defined]

        with TemporaryDirectory() as tmp:
            state = self._make_state(tmp)
            self._state_obj = state  # bind for the closure above

            # Build a valid live profile body.
            profile = _live_profile()
            body = {"profile": profile, "mode": "live"}

            handler = _FakeHandler()
            handler._state_obj = state
            handler._body = body
            handler._handle_profile_launch(body)

            # (a) A 403 missing_api_key error must have been sent.
            self.assertTrue(
                captured_errors,
                "expected _send_error_json to be called but it was not",
            )
            status, code, _msg = captured_errors[0]
            self.assertEqual(status, 403, f"expected 403, got {status}")
            self.assertEqual(code, "missing_api_key", f"expected missing_api_key, got {code!r}")

            # (b) No 202 success response must have been sent.
            self.assertFalse(
                captured_ok,
                f"_send_json should not have been called but got: {captured_ok}",
            )

            # (c) The runs_dir must be empty — no orphan run subdir.
            subdirs = list(Path(tmp).iterdir())
            self.assertEqual(
                subdirs,
                [],
                f"orphan dirs found in runs_dir: {subdirs}",
            )


from werewolf_eval.observer_server import _sanitize_launcher_error


class SanitizeLauncherErrorTests(unittest.TestCase):
    def test_auth_error_maps_to_provider_auth_failed_without_key(self):
        msg = "401 Unauthorized: Authorization: Bearer sk-test-fake-LEAK url=https://api.deepseek.com"
        code = _sanitize_launcher_error(RuntimeError(msg))
        self.assertEqual(code, "provider_auth_failed")
        self.assertNotIn("sk-", code)
        self.assertNotIn("Bearer", code)

    def test_generic_error_maps_to_provider_failure(self):
        self.assertEqual(_sanitize_launcher_error(RuntimeError("connection reset")), "provider_failure")
