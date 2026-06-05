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
    profiles_dir: Path | None = None,
) -> tuple[object, str]:
    """Start an observer server on a random port.  Returns (server, base_url)."""
    server = create_observer_server(
        "127.0.0.1", 0, runs_dir, launcher=launcher, profiles_dir=profiles_dir
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


# ---------------------------------------------------------------------------
# ObserverServerProjectionEndpointTests (G2c)
# ---------------------------------------------------------------------------


class ObserverServerProjectionEndpointTests(TestCase):
    """Test the /api/runs/{run_id}/projection endpoint."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls._tmp_path = Path(cls._tmp.name)
        cls._server, cls._base_url = _start_server(cls._tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def _make_fixture_run(self, run_id: str) -> Path:
        """Create a run directory with events.jsonl and role-projection snapshots."""
        run_dir = self._tmp_path / run_id
        run_dir.mkdir()
        # Write events.jsonl with various visibilities
        events = [
            _event("game_started", "public", 0),
            _event("provider_request", "private", 1),
            _event("observation_delivered", "all", 2),
            _event("action_executed", "seer", 3),
            _event("consensus_started", "werewolf_team", 4),
            _event("vote_cast", "witch", 5),
            _event("internal_event", "internal", 6),
        ]
        lines = "\n".join(json.dumps(e) for e in events) + "\n"
        (run_dir / "events.jsonl").write_text(lines, encoding="utf-8")

        # Write role_projection snapshots
        snap_dir = run_dir / "snapshots"
        snap_dir.mkdir()
        (snap_dir / "role-p1-r1.json").write_text(json.dumps({
            "snapshot_type": "role_projection",
            "player_id": "p1",
            "role": "seer",
            "team": "villager",
            "round": 1,
            "phase": "night",
            "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "projected_known_roles": {"p1": "seer", "p2": "villager", "p3": "unknown"},
        }), encoding="utf-8")
        (snap_dir / "role-p3-r1.json").write_text(json.dumps({
            "snapshot_type": "role_projection",
            "player_id": "p3",
            "role": "werewolf",
            "team": "werewolf",
            "round": 1,
            "phase": "night",
            "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "projected_known_roles": {"p1": "unknown", "p3": "werewolf"},
        }), encoding="utf-8")
        (snap_dir / "role-p5-r1.json").write_text(json.dumps({
            "snapshot_type": "role_projection",
            "player_id": "p5",
            "role": "villager",
            "team": "villager",
            "round": 1,
            "phase": "night",
            "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "projected_known_roles": {},
        }), encoding="utf-8")
        return run_dir

    def test_projection_endpoint_returns_contract_version(self) -> None:
        self._make_fixture_run("proj_contract")
        result = _request_json(
            self._base_url, "/api/runs/proj_contract/projection"
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("contract_version"), "g2c.visibility.v1")  # type: ignore[union-attr]

    def test_god_projection_exposes_roles(self) -> None:
        self._make_fixture_run("proj_god")
        result = _request_json(
            self._base_url, "/api/runs/proj_god/projection?perspective=god"
        )
        self.assertIsInstance(result, dict)
        players = result.get("players", [])  # type: ignore[union-attr]
        # Fixture provides 3 role-projection snapshots → 3 players in index
        self.assertGreaterEqual(len(players), 3)
        roles = {p["player_id"]: p["display_role"] for p in players}
        self.assertEqual(roles.get("p1"), "seer")
        self.assertEqual(roles.get("p3"), "werewolf")

    def test_public_projection_hides_roles(self) -> None:
        self._make_fixture_run("proj_public")
        result = _request_json(
            self._base_url, "/api/runs/proj_public/projection?perspective=public"
        )
        self.assertIsInstance(result, dict)
        players = result.get("players", [])  # type: ignore[union-attr]
        for p in players:
            self.assertEqual(p["display_role"], "unknown")
            self.assertEqual(p["display_team"], "unknown")

    def test_role_projection_exposes_self_role_only(self) -> None:
        self._make_fixture_run("proj_role")
        result = _request_json(
            self._base_url, "/api/runs/proj_role/projection?perspective=role:p1"
        )
        self.assertIsInstance(result, dict)
        players = result.get("players", [])  # type: ignore[union-attr]
        # p1 should see its own role
        p1 = [p for p in players if p["player_id"] == "p1"][0]
        self.assertEqual(p1["display_role"], "seer")
        # p3 (werewolf) should be hidden
        p3 = [p for p in players if p["player_id"] == "p3"][0]
        self.assertEqual(p3["display_role"], "unknown")

    def test_werewolf_team_projection_hides_non_wolf_roles(self) -> None:
        self._make_fixture_run("proj_team")
        result = _request_json(
            self._base_url, "/api/runs/proj_team/projection?perspective=team:werewolf"
        )
        self.assertIsInstance(result, dict)
        players = result.get("players", [])  # type: ignore[union-attr]
        wolf_visible = [p for p in players if p["display_role"] != "unknown"]
        self.assertGreater(len(wolf_visible), 0)
        # Non-wolf players should be hidden
        for p in players:
            if p["display_role"] != "unknown":
                self.assertEqual(p["display_team"], "werewolf")

    def test_projection_rejects_unknown_perspective(self) -> None:
        self._make_fixture_run("proj_bad")
        result = _request_json(
            self._base_url, "/api/runs/proj_bad/projection?perspective=invalid"
        )
        self.assertIsInstance(result, dict)
        self.assertIn(result.get("code"), ("invalid_request", "invalid_perspective"))  # type: ignore[union-attr]

    def test_projection_contains_proof(self) -> None:
        self._make_fixture_run("proj_proof")
        result = _request_json(
            self._base_url, "/api/runs/proj_proof/projection"
        )
        self.assertIsInstance(result, dict)
        proof = result.get("proof")  # type: ignore[union-attr]
        self.assertIsInstance(proof, dict)
        self.assertIn("source", proof)

    def test_projection_all_keys_present(self) -> None:
        self._make_fixture_run("proj_keys")
        result = _request_json(
            self._base_url, "/api/runs/proj_keys/projection"
        )
        self.assertIsInstance(result, dict)
        for key in ("contract_version", "run_id", "perspective", "view_kind",
                     "players", "events", "hidden_event_count", "snapshots",
                     "hidden_snapshot_count", "proof"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# ObserverServerVisibilityNonLeakTests (G2c Task 5)
# ---------------------------------------------------------------------------


class ObserverServerVisibilityNonLeakTests(TestCase):
    """Test that projection endpoints do not leak role information."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls._tmp_path = Path(cls._tmp.name)
        cls._server, cls._base_url = _start_server(cls._tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def _make_nonleak_fixture(self, run_id: str) -> None:
        """Create a run with werewolf (p3, p4) and seer (p1) players."""
        run_dir = self._tmp_path / run_id
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )
        snap_dir = run_dir / "snapshots"
        snap_dir.mkdir()
        (snap_dir / "role-p1-r1.json").write_text(json.dumps({
            "snapshot_type": "role_projection",
            "player_id": "p1", "role": "seer", "team": "villager",
            "round": 1, "phase": "night",
            "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "projected_known_roles": {"p1": "seer", "p3": "unknown", "p4": "unknown"},
        }), encoding="utf-8")
        (snap_dir / "role-p3-r1.json").write_text(json.dumps({
            "snapshot_type": "role_projection",
            "player_id": "p3", "role": "werewolf", "team": "werewolf",
            "round": 1, "phase": "night",
            "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "projected_known_roles": {"p1": "unknown", "p3": "werewolf", "p4": "werewolf"},
        }), encoding="utf-8")
        (snap_dir / "role-p4-r1.json").write_text(json.dumps({
            "snapshot_type": "role_projection",
            "player_id": "p4", "role": "werewolf", "team": "werewolf",
            "round": 1, "phase": "night",
            "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "projected_known_roles": {"p1": "unknown", "p3": "werewolf", "p4": "werewolf"},
        }), encoding="utf-8")

    def test_public_projection_response_does_not_contain_werewolf_role_labels(self) -> None:
        self._make_nonleak_fixture("leak_public")
        text = _request_text(
            self._base_url, "/api/runs/leak_public/projection?perspective=public"
        )
        self.assertNotIn('"display_role":"werewolf"', text)
        self.assertNotIn('"display_team":"werewolf"', text)

    def test_role_projection_response_does_not_contain_other_hidden_roles(self) -> None:
        self._make_nonleak_fixture("leak_role")
        result = _request_json(
            self._base_url, "/api/runs/leak_role/projection?perspective=role:p1"
        )
        self.assertIsInstance(result, dict)
        players = result.get("players", [])  # type: ignore[union-attr]
        # p1 is seer, should NOT expose werewolf roles for p3/p4
        for p in players:
            if p.get("player_id") != "p1":
                self.assertNotEqual(p.get("display_role"), "werewolf",
                                    f"Leaked werewolf role for {p.get('player_id')}")

    def test_team_werewolf_projection_response_does_not_contain_non_wolf_roles(self) -> None:
        self._make_nonleak_fixture("leak_team")
        result = _request_json(
            self._base_url, "/api/runs/leak_team/projection?perspective=team:werewolf"
        )
        self.assertIsInstance(result, dict)
        players = result.get("players", [])  # type: ignore[union-attr]
        for p in players:
            if p.get("display_role") != "unknown":
                # If role is exposed, it must be werewolf team
                self.assertIn(p.get("display_role"), ("werewolf",),
                              f"Non-wolf role exposed in team view: {p.get('display_role')}")

    def test_projection_response_contains_no_absolute_paths(self) -> None:
        self._make_nonleak_fixture("leak_paths")
        text = _request_text(
            self._base_url, "/api/runs/leak_paths/projection"
        )
        # Should not contain the temp directory absolute path
        self.assertNotIn(self._tmp_path.as_posix(), text)
        # Should not contain Windows-style absolute paths
        self.assertNotIn(":\\", text)


# ---------------------------------------------------------------------------
# ObserverServerProjectionDegradationTests (G2c B档 gap fix)
# ---------------------------------------------------------------------------


class ObserverServerProjectionDegradationTests(TestCase):
    """Test projection endpoint degrades safely when artifacts are missing."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls._tmp_path = Path(cls._tmp.name)
        cls._server, cls._base_url = _start_server(cls._tmp_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def test_projection_degrades_when_no_snapshots_exist(self) -> None:
        """Run dir exists with events but no snapshots dir → insufficient_artifacts."""
        run_dir = self._tmp_path / "degrade_no_snaps"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )
        result = _request_json(
            self._base_url, "/api/runs/degrade_no_snaps/projection?perspective=god"
        )
        self.assertIsInstance(result, dict)
        proof = result.get("proof")  # type: ignore[union-attr]
        self.assertIsInstance(proof, dict)
        self.assertEqual(proof.get("source"), "insufficient_artifacts")

    def test_projection_degrades_all_roles_unknown_without_snapshots(self) -> None:
        """Without snapshots, non-god perspectives must show all roles as unknown."""
        run_dir = self._tmp_path / "degrade_roles"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text(
            json.dumps(_event("game_started", "public", 0)) + "\n",
            encoding="utf-8",
        )
        result = _request_json(
            self._base_url, "/api/runs/degrade_roles/projection?perspective=public"
        )
        self.assertIsInstance(result, dict)
        players = result.get("players", [])  # type: ignore[union-attr]
        for p in players:
            self.assertEqual(p["display_role"], "unknown")
            self.assertEqual(p["display_team"], "unknown")

    def test_projection_degrades_empty_events_jsonl(self) -> None:
        """Run dir with empty events.jsonl and no snapshots → valid envelope with empty events."""
        run_dir = self._tmp_path / "degrade_empty_events"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text("", encoding="utf-8")
        result = _request_json(
            self._base_url, "/api/runs/degrade_empty_events/projection"
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("contract_version"), "g2c.visibility.v1")  # type: ignore[union-attr]
        self.assertEqual(result.get("events"), [])  # type: ignore[union-attr]
        self.assertEqual(result.get("hidden_event_count"), 0)  # type: ignore[union-attr]

    def test_projection_degrades_no_events_file(self) -> None:
        """Run dir without events.jsonl at all → valid envelope with empty events."""
        run_dir = self._tmp_path / "degrade_no_events"
        run_dir.mkdir()
        result = _request_json(
            self._base_url, "/api/runs/degrade_no_events/projection?perspective=role:p1"
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("contract_version"), "g2c.visibility.v1")  # type: ignore[union-attr]
        self.assertEqual(result.get("events"), [])  # type: ignore[union-attr]


def _valid_profile_payload(name: str = "demo", seat_overrides: dict | None = None) -> dict:
    payload: dict = {
        "schema_version": "g2d.profile.v1",
        "name": name,
        "template": "default_6p_fake",
        "role_defaults": {
            "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
        },
    }
    if seat_overrides:
        payload["seat_overrides"] = seat_overrides
    return payload

class ObserverServerProfileTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls._runs = root / "runs"
        cls._profiles = root / "profiles"
        cls._runs.mkdir(parents=True)
        cls._profiles.mkdir(parents=True)
        (cls._profiles / "demo.json").write_text(
            json.dumps(_valid_profile_payload("demo")), encoding="utf-8"
        )
        cls._server, cls._base_url = _start_server(cls._runs, profiles_dir=cls._profiles)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmp.cleanup()

    def test_list_profiles(self) -> None:
        result = _request_json(self._base_url, "/api/profiles")
        names = {p["name"] for p in result["profiles"]}
        self.assertIn("demo", names)

    def test_get_profile(self) -> None:
        result = _request_json(self._base_url, "/api/profiles/demo")
        self.assertEqual(result["name"], "demo")

    def test_get_unknown_profile_404(self) -> None:
        result = _request_json(self._base_url, "/api/profiles/nope")
        self.assertEqual(result.get("code"), "not_found")

    def test_schema_endpoint(self) -> None:
        s = _request_json(self._base_url, "/api/profiles/schema")
        self.assertEqual(s["seat_roles"]["p1"], "werewolf")
        self.assertIn("deepseek", s["providers"])
        self.assertNotIn("templates", s)

    def test_validate_inline_profile(self) -> None:
        result = _request_json(
            self._base_url, "/api/profiles/validate", method="POST",
            payload=_valid_profile_payload("inline"),
        )
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["resolved_seats"]), 6)

    def test_validate_reports_invalid(self) -> None:
        bad = _valid_profile_payload("bad")
        bad["seat_overrides"] = {"p3": {"model": "deepseek-chat"}}
        result = _request_json(self._base_url, "/api/profiles/validate", method="POST", payload=bad)
        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_launch_from_named_profile_writes_resolved_artifact(self) -> None:
        resp = _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile_name": "demo", "run_id": "g2d_named_run"},
        )
        self.assertEqual(resp["status"], "queued")
        _wait_for_status(self._base_url, "g2d_named_run", "completed")
        art = _request_json(self._base_url, "/api/runs/g2d_named_run/artifacts/resolved-profile.json")
        self.assertEqual(art["execution_mode"], "fake")
        self.assertEqual(art["live_api"], "not_used")
        self.assertEqual(len(art["seats"]), 6)

    def test_launch_from_inline_profile(self) -> None:
        resp = _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile": _valid_profile_payload("inlinerun"), "run_id": "g2d_inline_run"},
        )
        self.assertEqual(resp["status"], "queued")
        _wait_for_status(self._base_url, "g2d_inline_run", "completed")

    def test_launch_rejects_invalid_profile(self) -> None:
        bad = _valid_profile_payload("badrun")
        bad["template"] = "nope"
        result = _request_json(self._base_url, "/api/runs", method="POST", payload={"profile": bad})
        self.assertEqual(result.get("code"), "invalid_profile")

    def test_launch_rejects_mixed_template_and_profile(self) -> None:
        result = _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile_name": "demo", "template": "default_6p_fake"},
        )
        self.assertEqual(result.get("code"), "invalid_request")

    def test_responses_have_no_absolute_paths_or_secret_markers(self) -> None:
        # malformed-profile errors (listing + get-by-name) must not leak the
        # absolute profiles dir
        broken = self._profiles / "broken.json"
        broken.write_text("{ not json", encoding="utf-8")
        try:
            listing = _request_json(self._base_url, "/api/profiles")
            self.assertNotIn(str(self._profiles), json.dumps(listing))
            get_broken = _request_json(self._base_url, "/api/profiles/broken")
            self.assertNotIn(str(self._profiles), json.dumps(get_broken))
        finally:
            broken.unlink()
        # a launched run's resolved-profile artifact must not leak paths/secrets
        _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile_name": "demo", "run_id": "g2d_leak_run"},
        )
        _wait_for_status(self._base_url, "g2d_leak_run", "completed")
        art_text = _request_text(
            self._base_url, "/api/runs/g2d_leak_run/artifacts/resolved-profile.json"
        )
        self.assertNotIn(str(self._runs), art_text)
        for marker in ("sk-", "Bearer ", "DEEPSEEK_API_KEY", "api_key"):
            self.assertNotIn(marker, art_text)
