import json
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


class FakeUpdateBackend:
    def __init__(self):
        self.checked = 0
        self.downloaded = 0
        self.applied = 0

    def check_for_update(self):
        self.checked += 1
        return {
            "available": True,
            "current_version": "0.2.0",
            "target_version": "0.2.1",
            "release_notes": "Release notes",
        }

    def download_update(self, progress):
        self.downloaded += 1
        progress(10)
        progress(100)
        return {
            "downloaded": True,
            "target_version": "0.2.1",
        }

    def apply_downloaded_update(self):
        self.applied += 1
        return {"applying": True, "restart": True}


class FakeFailingDownloadBackend(FakeUpdateBackend):
    def download_update(self, progress):
        self.downloaded += 1
        progress(12)
        raise RuntimeError("download source unavailable")


def _post(port, session_id, token, action):
    data = json.dumps({
        "schema_version": 1,
        "session_id": session_id,
        "session_token": token,
        "action": action,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/update/{action}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get_status(port, session_id, token):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/update/status"
        f"?session_id={session_id}&session_token={token}",
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class ReleaseUpdateControlTests(unittest.TestCase):
    def test_update_source_factory_defaults_to_public_github_stable_source(self):
        from werewolf_eval.release_host.update_control import (
            DEFAULT_UPDATE_REPO_URL,
            create_update_source_factory,
        )

        calls = []

        class FakeGithubSource:
            def __init__(self, repo_url, access_token=None, prerelease=False):
                calls.append((repo_url, access_token, prerelease))

        fake_velopack = SimpleNamespace(GithubSource=FakeGithubSource)
        with mock.patch.dict(sys.modules, {"velopack": fake_velopack}):
            source = create_update_source_factory().create()

        self.assertIsInstance(source, FakeGithubSource)
        self.assertEqual(calls, [(DEFAULT_UPDATE_REPO_URL, None, False)])

    def test_update_source_factory_accepts_explicit_local_test_directory(self):
        from tempfile import TemporaryDirectory

        from werewolf_eval.release_host.update_control import create_update_source_factory

        with TemporaryDirectory() as tmp:
            Path(tmp, "releases.win.json").write_text("{}", encoding="utf-8")
            factory = create_update_source_factory(test_update_source=tmp)
            self.assertEqual(factory.kind, "local")
            self.assertEqual(factory.create(), str(Path(tmp).resolve()))

    def test_release_notes_mapping_uses_markdown_not_html(self):
        from werewolf_eval.release_host.update_control import _asset_notes_markdown

        class FakeAsset:
            NotesMarkdown = "# Markdown notes"
            NotesHtml = "<h1>HTML notes</h1>"

        self.assertEqual(_asset_notes_markdown(FakeAsset()), "# Markdown notes")

    def test_check_download_apply_flow_uses_host_owned_backend(self):
        from werewolf_eval.release_host.update_control import UpdateControlServer

        backend = FakeUpdateBackend()
        with UpdateControlServer(
            backend=backend,
            active_run_checker=lambda: False,
            session_id="session-a",
            session_token="token-a",
        ) as server:
            status, payload = _post(server.port, "session-a", "token-a", "check_for_update")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"]["phase"], "available")
            self.assertEqual(payload["status"]["target_version"], "0.2.1")
            self.assertEqual(payload["status"]["release_notes"], "Release notes")

            status, payload = _post(server.port, "session-a", "token-a", "download_update")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"]["phase"], "downloaded")
            self.assertEqual(payload["status"]["progress"], 100)

            status, payload = _post(server.port, "session-a", "token-a", "apply_downloaded_update")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"]["phase"], "applying")
            self.assertTrue(server.apply_requested)

        self.assertEqual(backend.checked, 1)
        self.assertEqual(backend.downloaded, 1)
        self.assertEqual(backend.applied, 1)

    def test_apply_is_refused_when_active_run_exists_without_mutating_update(self):
        from werewolf_eval.release_host.update_control import UpdateControlServer

        backend = FakeUpdateBackend()
        with UpdateControlServer(
            backend=backend,
            active_run_checker=lambda: True,
            session_id="session-b",
            session_token="token-b",
        ) as server:
            _post(server.port, "session-b", "token-b", "check_for_update")
            _post(server.port, "session-b", "token-b", "download_update")
            with self.assertRaises(urllib.error.HTTPError) as raised:
                _post(server.port, "session-b", "token-b", "apply_downloaded_update")
            self.assertEqual(raised.exception.code, 409)

            status, payload = _get_status(server.port, "session-b", "token-b")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"]["phase"], "blocked_active_run")
            self.assertFalse(server.apply_requested)

        self.assertEqual(backend.applied, 0)

    def test_apply_is_refused_before_download(self):
        from werewolf_eval.release_host.update_control import UpdateControlServer

        backend = FakeUpdateBackend()
        with UpdateControlServer(
            backend=backend,
            active_run_checker=lambda: False,
            session_id="session-pre-download",
            session_token="token-pre-download",
        ) as server:
            _post(server.port, "session-pre-download", "token-pre-download", "check_for_update")
            with self.assertRaises(urllib.error.HTTPError) as raised:
                _post(server.port, "session-pre-download", "token-pre-download", "apply_downloaded_update")
            self.assertEqual(raised.exception.code, 409)

            status, payload = _get_status(server.port, "session-pre-download", "token-pre-download")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"]["phase"], "apply_blocked")
            self.assertEqual(payload["status"]["error"], "update_not_downloaded")
            self.assertFalse(server.apply_requested)

        self.assertEqual(backend.applied, 0)

    def test_update_session_token_is_not_the_host_control_token(self):
        from werewolf_eval.release_host.update_control import UpdateControlServer

        backend = FakeUpdateBackend()
        with UpdateControlServer(
            backend=backend,
            active_run_checker=lambda: False,
            session_id="session-c",
            session_token="update-token",
        ) as server:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                _post(server.port, "session-c", "host-control-token", "check_for_update")
            self.assertEqual(raised.exception.code, 403)
            time.sleep(0.05)
            self.assertEqual(backend.checked, 0)

    def test_download_failure_stays_in_error_state_without_apply_request(self):
        from werewolf_eval.release_host.update_control import UpdateControlServer

        backend = FakeFailingDownloadBackend()
        with UpdateControlServer(
            backend=backend,
            active_run_checker=lambda: False,
            session_id="session-d",
            session_token="token-d",
        ) as server:
            _post(server.port, "session-d", "token-d", "check_for_update")
            with self.assertRaises(urllib.error.HTTPError) as raised:
                _post(server.port, "session-d", "token-d", "download_update")
            self.assertEqual(raised.exception.code, 500)

            status, payload = _get_status(server.port, "session-d", "token-d")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"]["phase"], "error")
            self.assertEqual(payload["status"]["error"], "download_failed")
            self.assertEqual(payload["status"]["error_detail"], "RuntimeError")
            self.assertFalse(server.apply_requested)


if __name__ == "__main__":
    unittest.main()
