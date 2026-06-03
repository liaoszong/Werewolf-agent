"""Integration tests for the local observer HTTP server (G2a)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from werewolf_eval.observer_protocol import (
    ALLOWED_ARTIFACTS,
    ALLOWED_PERSPECTIVES,
)
from werewolf_eval.observer_server import (
    ObserverServerState,
    create_observer_server,
    default_fake_launcher,
)
from werewolf_eval.runtime_events import RuntimeEventWriter


def _event(kind: str = "test", visibility: str = "public", seq: int = 0) -> dict[str, object]:
    return {
        "event_id": f"evt_{seq}_{kind}",
        "seq": seq,
        "kind": kind,
        "round": 0,
        "phase": "lobby",
        "actor": "system",
        "visibility": visibility,
        "ts": "2026-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _start_server(
    runs_dir: Path,
    launcher: object = None,
) -> tuple[object, str]:
    """Start an observer server on a random port.  Returns (server, base_url)."""
    server = create_observer_server(
        "127.0.0.1", 0, runs_dir, launcher=launcher
    )
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, base_url


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> object:
    """Make an HTTP request and parse the JSON response."""
    url = f"{base_url}{path}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None
    req_headers: dict[str, str] = {}
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
    req = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise


def _request_text(base_url: str, path: str, headers: dict[str, str] | None = None) -> str:
    """Make an HTTP GET request and return the response as text."""
    url = f"{base_url}{path}"
    req_headers: dict[str, str] = {}
    if headers:
        req_headers.update(headers)
    req = Request(url, headers=req_headers)
    try:
        with urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except HTTPError as exc:
        return exc.read().decode("utf-8", errors="replace")


def _wait_for_status(
    base_url: str, run_id: str, expected: str, timeout_s: float = 8.0
) -> dict[str, object]:
    """Poll /api/runs/{run_id} until status matches *expected* or timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        detail = _request_json(base_url, f"/api/runs/{run_id}")
        if isinstance(detail, dict) and detail.get("status") == expected:
            return detail  # type: ignore[return-value]
        time.sleep(0.1)
    raise TimeoutError(
        f"Run {run_id} did not reach status {expected} within {timeout_s}s"
    )


# ---------------------------------------------------------------------------
# ObserverServerEndpointTests
# ---------------------------------------------------------------------------


class ObserverServerEndpointTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls._tmp_path = Path(cls._tmp.name)
        cls._server, cls._base_url = _start_server(cls._tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def test_health_endpoint_returns_ok(self) -> None:
        result = _request_json(self._base_url, "/health")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("status"), "ok")  # type: ignore[union-attr]

    def test_list_runs_and_run_detail_for_existing_fake_runtime(self) -> None:
        run_dir = self._tmp_path / "my_run"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )

        runs_list = _request_json(self._base_url, "/api/runs")
        self.assertIsInstance(runs_list, dict)
        runs = runs_list.get("runs", [])  # type: ignore[union-attr]
        run_ids = [r.get("run_id") for r in runs if isinstance(r, dict)]
        self.assertIn("my_run", run_ids)

        detail = _request_json(self._base_url, "/api/runs/my_run")
        self.assertIsInstance(detail, dict)
        self.assertEqual(detail.get("run_id"), "my_run")  # type: ignore[union-attr]
        self.assertEqual(detail.get("event_count"), 1)  # type: ignore[union-attr]

    def test_events_endpoint_filters_public_perspective(self) -> None:
        run_dir = self._tmp_path / "events_run"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n"
            + json.dumps(_event("provider_request", "private", 1)) + "\n",
            encoding="utf-8",
        )

        result = _request_json(
            self._base_url, "/api/runs/events_run/events?perspective=public"
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("hidden_count"), 1)  # type: ignore[union-attr]
        events = result.get("events", [])  # type: ignore[union-attr]
        self.assertEqual(len(events), 1)

    def test_stream_endpoint_replays_sse_events_for_completed_run(self) -> None:
        run_dir = self._tmp_path / "stream_run"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )
        # Mark as completed
        status_path = run_dir / "status.json"
        status_path.write_text(
            json.dumps({"status": "completed"}), encoding="utf-8"
        )

        text = _request_text(
            self._base_url,
            "/api/runs/stream_run/stream?perspective=god",
            headers={"Accept": "text/event-stream"},
        )
        self.assertIn("event: run_status", text)
        self.assertIn("event: runtime_event", text)
        self.assertIn("game_started", text)

    def test_artifact_endpoint_rejects_unknown_artifact(self) -> None:
        run_dir = self._tmp_path / "art_run"
        run_dir.mkdir()

        result = _request_json(
            self._base_url, "/api/runs/art_run/artifacts/bad.txt"
        )
        self.assertIsInstance(result, dict)
        code = result.get("code")  # type: ignore[union-attr]
        self.assertIn(code, ("invalid_request", "not_found"))

    def test_snapshot_detail_rejects_god_snapshot_for_public(self) -> None:
        run_dir = self._tmp_path / "snap_run"
        snap_dir = run_dir / "snapshots"
        snap_dir.mkdir(parents=True)
        (snap_dir / "s1.json").write_text(
            json.dumps({"snapshot_type": "god", "round": 1, "phase": "night"}),
            encoding="utf-8",
        )

        result = _request_json(
            self._base_url, "/api/runs/snap_run/snapshots/s1.json?perspective=public"
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("code"), "snapshot_hidden")  # type: ignore[union-attr]

    def test_snapshot_detail_allows_role_projection_for_matching_role(self) -> None:
        run_dir = self._tmp_path / "snap_run2"
        snap_dir = run_dir / "snapshots"
        snap_dir.mkdir(parents=True)
        (snap_dir / "s1.json").write_text(
            json.dumps({
                "snapshot_type": "role_projection",
                "player_id": "p1",
                "team": "villager",
                "round": 1,
                "phase": "day",
            }),
            encoding="utf-8",
        )

        result = _request_json(
            self._base_url, "/api/runs/snap_run2/snapshots/s1.json?perspective=role:p1"
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("player_id"), "p1")  # type: ignore[union-attr]

    def test_post_runs_rejects_unknown_template(self) -> None:
        result = _request_json(
            self._base_url,
            "/api/runs",
            method="POST",
            payload={"template": "nonexistent_template"},
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("code"), "invalid_request")  # type: ignore[union-attr]

    def test_post_404_on_unknown_endpoint(self) -> None:
        result = _request_json(self._base_url, "/api/unknown")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("code"), "not_found")  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# ObserverServerLiveTailTests
# ---------------------------------------------------------------------------


class ObserverServerLiveTailTests(TestCase):
    def _slow_launcher(self, run_id: str, run_dir: Path) -> int:
        """Launcher that writes events with delays for live tail testing."""
        writer = RuntimeEventWriter(run_id=run_id, out_dir=run_dir)
        writer.emit(
            "game_started", round=0, phase="lobby",
            actor="system", visibility="public",
            payload={"message": "game started"},
        )
        time.sleep(0.5)
        writer.emit(
            "round_started", round=1, phase="day",
            actor="system", visibility="public",
            payload={"message": "round 1 started"},
        )
        time.sleep(0.5)
        writer.emit(
            "game_ended", round=1, phase="ended",
            actor="system", visibility="public",
            payload={"message": "game ended"},
        )
        return 0

    def test_post_runs_launches_default_fake_match_asynchronously(self) -> None:
        with TemporaryDirectory() as tmp:
            runs_dir = Path(tmp)
            server, base_url = _start_server(runs_dir)

            try:
                result = _request_json(
                    base_url, "/api/runs", method="POST", payload={}
                )
                self.assertIsInstance(result, dict)
                self.assertEqual(result.get("status"), "queued")  # type: ignore[union-attr]
                run_id = result.get("run_id")  # type: ignore[union-attr]
                self.assertIsInstance(run_id, str)

                detail = _wait_for_status(base_url, run_id, "completed", timeout_s=12.0)
                self.assertEqual(detail.get("status"), "completed")
                self.assertGreater(
                    detail.get("event_count", 0), 0  # type: ignore[operator]
                )
            finally:
                server.shutdown()

    def test_stream_endpoint_tails_events_while_run_is_active(self) -> None:
        with TemporaryDirectory() as tmp:
            runs_dir = Path(tmp)
            server, base_url = _start_server(
                runs_dir, launcher=self._slow_launcher
            )

            try:
                launch = _request_json(
                    base_url, "/api/runs", method="POST", payload={}
                )
                run_id = launch.get("run_id")  # type: ignore[union-attr]
                self.assertEqual(launch.get("status"), "queued")  # type: ignore[union-attr]

                sse_text = _request_text(
                    base_url,
                    f"/api/runs/{run_id}/stream?perspective=god",
                    headers={"Accept": "text/event-stream"},
                )

                self.assertIn("event: run_status", sse_text)
                self.assertIn("event: runtime_event", sse_text)
                self.assertIn("game_started", sse_text)
                self.assertIn("round_started", sse_text)
                self.assertIn("game_ended", sse_text)
            finally:
                server.shutdown()


# ---------------------------------------------------------------------------
# ObserverServerCliTests
# ---------------------------------------------------------------------------


class ObserverServerCliTests(TestCase):
    def test_cli_help_lists_runs_dir_host_and_port(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "werewolf_eval.run_observer_server", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--runs-dir", result.stdout)
        self.assertIn("--host", result.stdout)
        self.assertIn("--port", result.stdout)


# ---------------------------------------------------------------------------
# ObserverServerTraversalTests
# ---------------------------------------------------------------------------


class ObserverServerTraversalTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls._tmp_path = Path(cls._tmp.name)
        cls._server, cls._base_url = _start_server(cls._tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def test_url_encoded_traversal_in_artifact_returns_error(self) -> None:
        result = _request_json(
            self._base_url,
            "/api/runs/security_run/artifacts/..%2F..%2FREADME.md",
        )
        self.assertIsInstance(result, dict)
        code = result.get("code")  # type: ignore[union-attr]
        self.assertIn(code, ("not_found", "invalid_request"))

    def test_url_encoded_traversal_in_snapshot_returns_error(self) -> None:
        result = _request_json(
            self._base_url,
            "/api/runs/security_run/snapshots/..%2F..%2FREADME.md",
        )
        self.assertIsInstance(result, dict)
        code = result.get("code")  # type: ignore[union-attr]
        self.assertIn(code, ("not_found", "invalid_request"))


# ---------------------------------------------------------------------------
# ObserverServerSecretScanTests
# ---------------------------------------------------------------------------


class ObserverServerSecretScanTests(TestCase):
    _UNSAFE_MARKERS = ("Authorization:", "Bearer ", "DEEPSEEK_API_KEY=", "sk-")

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls._tmp_path = Path(cls._tmp.name)
        cls._server, cls._base_url = _start_server(cls._tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def _assert_no_secrets(self, text: str, endpoint: str) -> None:
        for marker in self._UNSAFE_MARKERS:
            if marker in text:
                self.fail(
                    f"Unsafe marker {marker!r} found in {endpoint} response. "
                    "Test contains forbidden-pattern markers that must be marked in the review packet."
                )

    def test_public_endpoints_do_not_expose_secret_markers(self) -> None:
        run_dir = self._tmp_path / "sec_run"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )

        endpoints = [
            "/api/runs",
            "/api/runs/sec_run",
            "/api/runs/sec_run/events?perspective=god",
            "/api/runs/sec_run/snapshots?perspective=god",
            "/api/runs/sec_run/snapshots/s1.json?perspective=god",
            "/api/runs/sec_run/manifest",
            "/api/runs/sec_run/provider-trace",
            "/api/runs/sec_run/failure-audit",
        ]

        for ep in endpoints:
            raw = _request_text(self._base_url, ep)
            self._assert_no_secrets(raw, ep)


# ---------------------------------------------------------------------------
# ObserverServerLiveObservationTests
# ---------------------------------------------------------------------------


class ObserverServerLiveObservationTests(TestCase):
    def _slow_launcher(self, run_id: str, run_dir: Path) -> int:
        writer = RuntimeEventWriter(run_id=run_id, out_dir=run_dir)
        writer.emit(
            "game_started", round=0, phase="lobby",
            actor="system", visibility="public",
            payload={"message": "start"},
        )
        time.sleep(0.5)
        writer.emit(
            "round_started", round=1, phase="day",
            actor="system", visibility="public",
            payload={"message": "round 1"},
        )
        return 0

    def test_status_changes_and_stream_events_are_visible_before_completion(self) -> None:
        """Prove async launch + live SSE: POST returns before completion,
        intermediate status is observable, and stream receives runtime events."""
        with TemporaryDirectory() as tmp:
            runs_dir = Path(tmp)
            server, base_url = _start_server(
                runs_dir, launcher=self._slow_launcher
            )

            try:
                launch = _request_json(
                    base_url, "/api/runs", method="POST", payload={}
                )
                run_id = launch.get("run_id")  # type: ignore[union-attr]

                self.assertEqual(launch.get("status"), "queued")  # type: ignore[union-attr]

                status_seen: set[str] = set()
                deadline = time.time() + 5.0
                while time.time() < deadline:
                    detail = _request_json(base_url, f"/api/runs/{run_id}")
                    s = detail.get("status")  # type: ignore[union-attr]
                    status_seen.add(s)  # type: ignore[arg-type]
                    if s == "completed":
                        break
                    time.sleep(0.05)

                self.assertIn("completed", status_seen)
                self.assertTrue(
                    status_seen & {"queued", "running"},
                    f"Must observe queued/running before completed, saw: {status_seen}",
                )

                launch2 = _request_json(
                    base_url, "/api/runs", method="POST", payload={}
                )
                run_id2 = launch2.get("run_id")  # type: ignore[union-attr]

                sse_text = _request_text(
                    base_url,
                    f"/api/runs/{run_id2}/stream?perspective=god",
                    headers={"Accept": "text/event-stream"},
                )
                self.assertIn("event: runtime_event", sse_text)
                self.assertIn("game_started", sse_text)
            finally:
                server.shutdown()
# ---------------------------------------------------------------------------


class ObserverServerArtifactTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls._tmp_path = Path(cls._tmp.name)
        cls._server, cls._base_url = _start_server(cls._tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def test_artifacts_endpoint_lists_allowed_artifacts(self) -> None:
        run_dir = self._tmp_path / "art_test"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )
        result = _request_json(
            self._base_url, "/api/runs/art_test/artifacts"
        )
        self.assertIsInstance(result, dict)
        artifacts = result.get("artifacts")  # type: ignore[union-attr]
        self.assertIsInstance(artifacts, dict)
        self.assertIn("events.jsonl", artifacts)

    def test_artifacts_name_endpoint_serves_file(self) -> None:
        run_dir = self._tmp_path / "art_file"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )
        text = _request_text(
            self._base_url, "/api/runs/art_file/artifacts/events.jsonl"
        )
        self.assertIn("evt_0_game_started", text)

    def test_manifest_endpoint_serves_prompt_manifest(self) -> None:
        run_dir = self._tmp_path / "mani_run"
        run_dir.mkdir()
        (run_dir / "prompt-manifest.json").write_text('{"hello":"world"}', encoding="utf-8")
        text = _request_text(
            self._base_url, "/api/runs/mani_run/manifest"
        )
        self.assertIn("hello", text)

    def test_provider_trace_endpoint_serves_file(self) -> None:
        run_dir = self._tmp_path / "trace_run"
        run_dir.mkdir()
        (run_dir / "provider-trace.json").write_text('{"trace":"yes"}', encoding="utf-8")
        text = _request_text(
            self._base_url, "/api/runs/trace_run/provider-trace"
        )
        self.assertIn("trace", text)

    def test_failure_audit_endpoint_serves_file(self) -> None:
        run_dir = self._tmp_path / "fa_run"
        run_dir.mkdir()
        (run_dir / "failure-audit.json").write_text('{"audit":"yes"}', encoding="utf-8")
        text = _request_text(
            self._base_url, "/api/runs/fa_run/failure-audit"
        )
        self.assertIn("audit", text)
