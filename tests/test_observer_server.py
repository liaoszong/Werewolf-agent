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
    RUNTIME_CAPABILITIES_SCHEMA_VERSION,
)
from werewolf_eval.observer_server import (
    ObserverRequestHandler,
    ObserverServerState,
    _build_capabilities_payload,
    _check_live_capability,
    _check_live_profile_shape,
    _map_launcher_exit_reason,
    _schema_payload,
    _seed_default_profile,
    create_observer_server,
    default_fake_launcher,
)
from werewolf_eval.profile_config import build_default_profile, list_profiles
from werewolf_eval.runtime_events import RuntimeEventWriter


class SeedDefaultProfileTests(TestCase):
    """P2-B: a fresh server seeds a baseline default profile so the setup page is
    never an empty 'no profiles' state — idempotent and non-destructive."""

    def test_seeds_default_when_dir_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "profiles"
            pdir.mkdir()
            _seed_default_profile(pdir)
            entries = list_profiles(pdir)
            self.assertEqual(len(entries), 1)
            self.assertTrue(entries[0]["valid"])
            self.assertEqual(entries[0]["name"], "default_6p")

    def test_skips_when_a_valid_profile_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "profiles"
            pdir.mkdir()
            (pdir / "mine.json").write_text(
                json.dumps(build_default_profile("mine")), encoding="utf-8"
            )
            _seed_default_profile(pdir)
            self.assertEqual(sorted(p.stem for p in pdir.glob("*.json")), ["mine"])

    def test_never_overwrites_existing_default_file(self) -> None:
        with TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "profiles"
            pdir.mkdir()
            # A user-broken default_6p.json must not be clobbered.
            (pdir / "default_6p.json").write_text("{}", encoding="utf-8")
            _seed_default_profile(pdir)
            self.assertEqual((pdir / "default_6p.json").read_text(encoding="utf-8"), "{}")

    def test_factory_seeds_only_when_opted_in(self) -> None:
        with TemporaryDirectory() as tmp:
            runs_on = Path(tmp) / "on" / "runs"
            srv = create_observer_server("127.0.0.1", 0, runs_on, seed_default_profile=True)
            srv.server_close()
            self.assertTrue(any(e["valid"] for e in list_profiles(runs_on.parent / "profiles")))

            runs_off = Path(tmp) / "off" / "runs"
            srv2 = create_observer_server("127.0.0.1", 0, runs_off)
            srv2.server_close()
            self.assertEqual(list_profiles(runs_off.parent / "profiles"), [])


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


# ---------------------------------------------------------------------------
# G3-1 live-mode gate matrix — validated OFFLINE (localhost HTTP is blocked in
# this env).  The two pure helpers cover the decision logic; the in-process
# handler harness covers dispatch (run_dir-not-created, launcher selection,
# capability-before-validate-before-shape ordering) with no socket.
# ---------------------------------------------------------------------------


def _deepseek_profile(name: str = "dsprofile", model: str = "deepseek-chat") -> dict:
    rd = {
        role: {"provider": "deepseek", "model": model, "prompt": "", "strategy": "default"}
        for role in ("werewolf", "seer", "witch", "villager")
    }
    return {
        "schema_version": "g2d.profile.v1",
        "name": name,
        "template": "default_6p_fake",
        "role_defaults": rd,
    }


def _mixed_model_deepseek_profile(name: str = "mixedmodel") -> dict:
    p = _deepseek_profile(name)
    p["seat_overrides"] = {
        "p3": {"provider": "deepseek", "model": "deepseek-reasoner", "prompt": "", "strategy": "default"}
    }
    return p


def _human_seat_profile(name: str = "humanseat", seat_id: str = "p3") -> dict:
    p = _deepseek_profile(name)
    p["seat_overrides"] = {
        seat_id: {"provider": "human", "model": "none", "prompt": "", "strategy": "default"}
    }
    return p


def _resolved_seats(provider: str, model: str) -> list[dict]:
    return [{"player_id": f"p{i}", "provider": provider, "model": model} for i in range(1, 7)]


class LiveGateHelperTests(TestCase):
    """Pure-helper unit tests for the live-mode gate matrix (no socket).

    B5 closeout: the env-key fallback (live_launcher, env_key_available) has been
    retired. Live capability now depends on credential_store having at least one
    provider key."""

    def _state(self, *, live_enabled: bool, has_credential: bool = False) -> ObserverServerState:
        from werewolf_eval.credential_store import CredentialStore
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            cs = CredentialStore()
            if has_credential:
                cs.set("deepseek", "sk-test-fake-key")
            return ObserverServerState(
                runs_dir=runs,
                launcher=default_fake_launcher,
                live_enabled=live_enabled,
                credential_store=cs,
            )

    # -- capability (BEFORE load/validate) --------------------------------

    def test_capability_fake_mode_always_proceeds(self) -> None:
        st = self._state(live_enabled=False)
        self.assertIsNone(_check_live_capability(st, "fake"))

    def test_capability_live_not_enabled_is_403_disabled(self) -> None:
        st = self._state(live_enabled=False)
        result = _check_live_capability(st, "live")
        self.assertEqual(result, (403, "live_api_disabled", result[2]))  # type: ignore[index]

    def test_capability_live_enabled_no_credential_is_403_missing_key(self) -> None:
        # B5 closeout: without a client credential, capability returns missing_api_key.
        st = self._state(live_enabled=True, has_credential=False)
        result = _check_live_capability(st, "live")
        self.assertEqual(result[0], 403)  # type: ignore[index]
        self.assertEqual(result[1], "missing_api_key")  # type: ignore[index]

    def test_capability_live_enabled_with_credential_proceeds(self) -> None:
        # B5 closeout: with a client credential, capability proceeds.
        st = self._state(live_enabled=True, has_credential=True)
        self.assertIsNone(_check_live_capability(st, "live"))

    # -- shape (AFTER validate) -------------------------------------------

    def test_shape_all_deepseek_single_model_proceeds(self) -> None:
        self.assertIsNone(_check_live_profile_shape(_resolved_seats("deepseek", "deepseek-chat")))

    def test_shape_non_deepseek_is_400_unsupported(self) -> None:
        result = _check_live_profile_shape(_resolved_seats("fake_deterministic", "none"))
        self.assertEqual(result[0], 400)  # type: ignore[index]
        self.assertEqual(result[1], "unsupported_live_provider")  # type: ignore[index]

    def test_shape_mixed_models_now_allowed(self) -> None:
        # P2-B-3: mixed models (and mixed providers) are the feature, no longer a
        # shape rejection. The per-seat credential check happens at launch.
        seats = _resolved_seats("deepseek", "deepseek-chat")
        seats[2]["model"] = "deepseek-reasoner"
        self.assertIsNone(_check_live_profile_shape(seats))

    def test_shape_mixed_providers_now_allowed(self) -> None:
        seats = _resolved_seats("deepseek", "deepseek-chat")
        seats[0]["provider"] = "anthropic"
        seats[0]["model"] = "claude-haiku-4-5"
        self.assertIsNone(_check_live_profile_shape(seats))

    def test_shape_rejects_unsupported_provider_among_supported(self) -> None:
        # An unsupported provider (fake) on any seat still fails the shape gate.
        seats = _resolved_seats("deepseek", "deepseek-chat")
        seats[0]["provider"] = "fake_deterministic"
        seats[0]["model"] = "none"
        result = _check_live_profile_shape(seats)
        self.assertEqual(result[1], "unsupported_live_provider")  # type: ignore[index]

    def test_shape_allows_single_human_seat_with_live_providers(self) -> None:
        seats = _resolved_seats("deepseek", "deepseek-chat")
        seats[2]["provider"] = "human"
        seats[2]["model"] = "none"

        self.assertIsNone(_check_live_profile_shape(seats))

    # -- exit-code → reason map -------------------------------------------

    def test_exit_code_3_maps_to_budget_exhausted(self) -> None:
        self.assertEqual(_map_launcher_exit_reason(3), "budget_exhausted")

    def test_exit_code_2_maps_to_provider_failure(self) -> None:
        self.assertEqual(_map_launcher_exit_reason(2), "provider_failure")

    def test_other_nonzero_maps_to_provider_failure(self) -> None:
        self.assertEqual(_map_launcher_exit_reason(1), "provider_failure")


class RuntimeCapabilitiesEndpointTests(TestCase):
    """Offline derivation tests for GET /api/runtime/capabilities (G3-2).

    Localhost HTTP is blocked in this env, so the read-only endpoint is proven
    by feeding a real ``ObserverServerState`` through the pure derivation helper
    (``_build_capabilities_payload``) — exactly as the G3-1 gate matrix is proven
    via ``_check_live_capability``.  The live-socket variant (a real GET
    round-trip) is env-blocked (RemoteDisconnected) and intentionally not
    exercised here; document, don't 'fix'.

    B5 closeout: the env-key fallback (live_launcher, env_key_available) has been
    retired. Live capability now depends on credential_store having at least one
    provider key."""

    def _state(self, *, live_enabled: bool, has_credential: bool = False) -> ObserverServerState:
        from werewolf_eval.credential_store import CredentialStore
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            cs = CredentialStore()
            if has_credential:
                cs.set("deepseek", "sk-test-fake-key")
            return ObserverServerState(
                runs_dir=runs,
                launcher=default_fake_launcher,
                live_enabled=live_enabled,
                credential_store=cs,
            )

    def test_available_posture_proceeds_with_no_reason(self) -> None:
        # B5 closeout: with a client credential, deepseek is available.
        st = self._state(live_enabled=True, has_credential=True)
        payload = _build_capabilities_payload(st)
        self.assertEqual(payload["schema_version"], RUNTIME_CAPABILITIES_SCHEMA_VERSION)
        self.assertEqual(payload["default_mode"], "fake")
        live = payload["live_api"]
        self.assertTrue(live["enabled"])
        ds = live["providers"]["deepseek"]
        self.assertTrue(ds["available"])
        self.assertNotIn("reason_code", ds)
        self.assertNotIn("message", ds)
        # available <=> the launch-time capability gate proceeds
        self.assertIsNone(_check_live_capability(st, "live"))

    def test_disabled_posture_reason_matches_launch_403(self) -> None:
        st = self._state(live_enabled=False)
        payload = _build_capabilities_payload(st)
        live = payload["live_api"]
        self.assertFalse(live["enabled"])
        ds = live["providers"]["deepseek"]
        self.assertFalse(ds["available"])
        self.assertEqual(ds["reason_code"], "live_api_disabled")
        self.assertTrue(ds["message"])
        # the capabilities reason_code is IDENTICAL to the launch-time 403 code
        self.assertEqual(ds["reason_code"], _check_live_capability(st, "live")[1])  # type: ignore[index]

    def test_flag_on_no_key_posture_reason_matches_launch_403(self) -> None:
        # B5 closeout: without a client credential, deepseek is unavailable.
        st = self._state(live_enabled=True, has_credential=False)
        payload = _build_capabilities_payload(st)
        live = payload["live_api"]
        self.assertTrue(live["enabled"])
        ds = live["providers"]["deepseek"]
        self.assertFalse(ds["available"])
        self.assertEqual(ds["reason_code"], "missing_api_key")
        self.assertEqual(ds["reason_code"], _check_live_capability(st, "live")[1])  # type: ignore[index]

    def test_payload_carries_no_secret_in_any_posture(self) -> None:
        # Real-secret markers only — the canonical key-free reason code
        # ``missing_api_key`` legitimately appears, mirroring the server response
        # secret scan (which also excludes the ``api_key`` substring).
        markers = ("Authorization", "Bearer ", "DEEPSEEK_API_KEY", "sk-")
        for st in (
            self._state(live_enabled=False),
            self._state(live_enabled=True, has_credential=False),
            self._state(live_enabled=True, has_credential=True),
        ):
            text = json.dumps(_build_capabilities_payload(st), ensure_ascii=False, sort_keys=True)
            for marker in markers:
                self.assertNotIn(marker, text, f"{marker!r} leaked in capabilities payload")


class _FakeServer:
    def __init__(self, state: ObserverServerState) -> None:
        self.state = state


class _InProcessHandler(ObserverRequestHandler):
    """Drive ``_handle_profile_launch`` with no socket.  Overrides only the
    response sink and the async-launch hook; the chosen launcher runs
    synchronously so run_dir artifacts are deterministic."""

    def __init__(self, state: ObserverServerState) -> None:  # noqa: D107 - skips socket init intentionally
        self.server = _FakeServer(state)  # type: ignore[assignment]
        self.responses: list[tuple[int, dict]] = []
        self.launched: list[tuple[str, Path]] = []
        self.last_code: int | None = None

    def _send_json(self, status: int, payload: object) -> None:  # type: ignore[override]
        self.responses.append((status, payload))  # type: ignore[arg-type]

    def _launch_run_async(self, run_id: str, run_dir: Path, launcher: object) -> None:  # type: ignore[override]
        self.launched.append((run_id, run_dir))
        self.last_code = launcher(run_id, run_dir)  # type: ignore[operator]


class LiveDispatchTests(TestCase):
    """In-process dispatch tests for the live gate matrix (no socket).

    B5 closeout: the env-key fallback (live_launcher, env_key_available) has been
    retired. Live launches now require client-supplied credentials via
    credential_store + multi_provider_launcher_factory."""

    def _live_launcher(self, run_id: str, run_dir: Path) -> int:
        (run_dir / "live.sentinel").write_text("live", encoding="utf-8")
        return 0

    def _fake_launcher(self, run_id: str, run_dir: Path) -> int:
        (run_dir / "fake.sentinel").write_text("fake", encoding="utf-8")
        return 0

    def _dispatch(
        self,
        body: dict,
        *,
        live_enabled: bool = False,
        credential_store: object | None = None,
        multi_factory: object | None = None,
        tmp: Path | None = None,
    ) -> tuple[_InProcessHandler, Path]:
        runs = (tmp or Path(self._tmp.name)) / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        profiles = (tmp or Path(self._tmp.name)) / "profiles"
        profiles.mkdir(parents=True, exist_ok=True)
        kwargs = {}
        if credential_store is not None:
            kwargs["credential_store"] = credential_store
        if multi_factory is not None:
            kwargs["multi_provider_launcher_factory"] = multi_factory
        state = ObserverServerState(
            runs_dir=runs,
            launcher=self._fake_launcher,
            profiles_dir=profiles,
            live_enabled=live_enabled,
            **kwargs,
        )
        handler = _InProcessHandler(state)
        handler._handle_profile_launch(body)
        return handler, runs

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _run_dir(self, runs: Path, run_id: str) -> Path:
        return runs / run_id

    def _make_cs_and_factory(self):
        """Helper: create a credential_store with deepseek key and a multi_factory
        that returns the live launcher."""
        from werewolf_eval.credential_store import CredentialStore
        cs = CredentialStore()
        cs.set("deepseek", "sk-test-fake-key")

        def multi_factory(resolved_seats, credentials):
            return self._live_launcher

        return cs, multi_factory

    # 1. mode omitted + deepseek profile → fake launcher ran (no live sentinel)
    def test_mode_omitted_runs_fake_launcher(self) -> None:
        body = {"profile": _deepseek_profile(), "run_id": "r_omit"}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 202)
        self.assertEqual(h.responses[-1][1]["mode"], "fake")
        rd = self._run_dir(runs, "r_omit")
        self.assertTrue((rd / "fake.sentinel").exists())
        self.assertFalse((rd / "live.sentinel").exists())

    # 2. mode=fake → fake launcher ran
    def test_mode_fake_runs_fake_launcher(self) -> None:
        body = {"profile": _deepseek_profile(), "run_id": "r_fake", "mode": "fake"}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        rd = self._run_dir(runs, "r_fake")
        self.assertTrue((rd / "fake.sentinel").exists())
        self.assertFalse((rd / "live.sentinel").exists())

    def test_mode_fake_with_human_seat_configures_participant(self) -> None:
        body = {"profile": _human_seat_profile(seat_id="p4"), "run_id": "r_human_fake", "mode": "fake"}
        h, runs = self._dispatch(body, live_enabled=False)
        rd = self._run_dir(runs, "r_human_fake")

        self.assertEqual(h.responses[-1][0], 202)
        self.assertEqual(h.responses[-1][1]["participant"], {"seat_id": "p4"})
        self.assertTrue((rd / "fake.sentinel").exists())
        self.assertTrue(h.server.state.participant_controller.is_human_seat("r_human_fake", "p4"))

    # 2b. fake + role_shuffle.enabled → 400 (artifact/engine alignment; spec §1.1)
    def test_fake_mode_with_role_shuffle_is_400(self) -> None:
        prof = _deepseek_profile()
        prof["role_shuffle"] = {"enabled": True}
        body = {"profile": prof, "run_id": "r_fs", "mode": "fake"}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 400)
        self.assertEqual(h.responses[-1][1].get("code"), "shuffle_requires_live")
        self.assertFalse((self._run_dir(runs, "r_fs") / "fake.sentinel").exists())

    def test_mode_omitted_with_role_shuffle_is_400(self) -> None:
        prof = _deepseek_profile()
        prof["role_shuffle"] = {"enabled": True}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch({"profile": prof, "run_id": "r_om"}, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 400)
        self.assertEqual(h.responses[-1][1].get("code"), "shuffle_requires_live")

    # 3. mode=live, server NOT live-enabled → 403 live_api_disabled, no run_dir
    def test_live_not_enabled_403_disabled_no_run_dir(self) -> None:
        body = {"profile": _deepseek_profile(), "run_id": "r_dis", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=False)
        self.assertEqual(h.responses[-1][0], 403)
        self.assertEqual(h.responses[-1][1]["code"], "live_api_disabled")
        self.assertFalse(self._run_dir(runs, "r_dis").exists())

    # 4. mode=live, enabled but no credential → 403 missing_api_key
    def test_live_enabled_no_key_403_missing_no_run_dir(self) -> None:
        body = {"profile": _deepseek_profile(), "run_id": "r_key", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=True)
        self.assertEqual(h.responses[-1][0], 403)
        self.assertEqual(h.responses[-1][1]["code"], "missing_api_key")
        self.assertFalse(self._run_dir(runs, "r_key").exists())

    # 5. mode=live + non-deepseek provider → 400 unsupported_live_provider
    def test_live_non_deepseek_400_unsupported_no_run_dir(self) -> None:
        body = {"profile": _valid_profile_payload("fakeonly"), "run_id": "r_unsup", "mode": "live"}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 400)
        self.assertEqual(h.responses[-1][1]["code"], "unsupported_live_provider")
        self.assertFalse(self._run_dir(runs, "r_unsup").exists())

    # 6. mode=live + >1 distinct deepseek model → ALLOWED (P2-B-3) and runs via
    #    the per-seat MULTI launcher.
    def test_live_mixed_models_runs_via_multi(self) -> None:
        from werewolf_eval.credential_store import CredentialStore
        cs = CredentialStore()
        cs.set("deepseek", "sk-ds")
        captured: dict = {}

        def multi_factory(resolved_seats, credentials):
            captured["models"] = {s["model"] for s in resolved_seats}
            def _run(rid, rdir):
                (rdir / "multi.sentinel").write_text("multi", encoding="utf-8")
                return 0
            return _run

        body = {"profile": _mixed_model_deepseek_profile(), "run_id": "r_mix", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 202)
        self.assertEqual(h.responses[-1][1]["mode"], "live")
        self.assertTrue((self._run_dir(runs, "r_mix") / "multi.sentinel").exists())
        self.assertEqual(captured["models"], {"deepseek-chat", "deepseek-reasoner"})

    def test_live_mixed_models_without_credential_403(self) -> None:
        # B5 closeout: without a client credential, mixed-model profile → 403.
        body = {"profile": _mixed_model_deepseek_profile(), "run_id": "r_mix2", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=True)
        self.assertEqual(h.responses[-1][0], 403)
        self.assertEqual(h.responses[-1][1]["code"], "missing_api_key")
        self.assertFalse(self._run_dir(runs, "r_mix2").exists())

    # 7. mode=live + single-model deepseek + credential → live launcher ran
    def test_live_valid_runs_live_launcher(self) -> None:
        body = {"profile": _deepseek_profile(), "run_id": "r_live", "mode": "live"}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 202)
        self.assertEqual(h.responses[-1][1]["mode"], "live")
        rd = self._run_dir(runs, "r_live")
        self.assertTrue((rd / "live.sentinel").exists())
        self.assertFalse((rd / "fake.sentinel").exists())

    def test_live_human_seat_skips_human_credential_and_configures_participant(self) -> None:
        from werewolf_eval.credential_store import CredentialStore
        cs = CredentialStore()
        cs.set("deepseek", "sk-ds")
        captured: dict = {}

        def multi_factory(resolved_seats, credentials, **kwargs):
            captured["providers"] = {s["provider"] for s in resolved_seats}
            captured["creds"] = set(credentials)
            captured["participant_controller"] = kwargs.get("participant_controller")
            captured["human_seat_ids"] = set(kwargs.get("human_seat_ids", ()))

            def _run(rid, rdir):
                (rdir / "human-live.sentinel").write_text("human-live", encoding="utf-8")
                return 0

            return _run

        body = {"profile": _human_seat_profile(seat_id="p3"), "run_id": "r_human_live", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)

        self.assertEqual(h.responses[-1][0], 202)
        self.assertEqual(h.responses[-1][1]["participant"], {"seat_id": "p3"})
        self.assertTrue((self._run_dir(runs, "r_human_live") / "human-live.sentinel").exists())
        self.assertEqual(captured["providers"], {"deepseek", "human"})
        self.assertEqual(captured["creds"], {"deepseek"})
        self.assertEqual(captured["human_seat_ids"], {"p3"})
        self.assertIs(captured["participant_controller"], h.server.state.participant_controller)
        self.assertTrue(h.server.state.participant_controller.is_human_seat("r_human_live", "p3"))

    def test_live_human_seat_still_requires_ai_provider_credential(self) -> None:
        body = {"profile": _human_seat_profile(seat_id="p3"), "run_id": "r_human_no_cred", "mode": "live"}

        h, runs = self._dispatch(body, live_enabled=True)

        self.assertEqual(h.responses[-1][0], 403)
        self.assertEqual(h.responses[-1][1]["code"], "missing_api_key")
        self.assertFalse(self._run_dir(runs, "r_human_no_cred").exists())

    # P2-B-4: mixed-provider profile + per-seat client creds → multi launcher ran.
    def _mixed_provider_profile(self):
        p = _deepseek_profile("mixedprov")
        p["seat_overrides"] = {
            "p3": {"provider": "anthropic", "model": "claude-haiku-4-5", "prompt": "", "strategy": "default"},
        }
        return p

    def test_live_multi_provider_runs_with_per_seat_creds(self) -> None:
        from werewolf_eval.credential_store import CredentialStore
        cs = CredentialStore()
        cs.set("deepseek", "sk-ds")
        cs.set("anthropic", "sk-ant")
        captured: dict = {}

        def multi_factory(resolved_seats, credentials):
            captured["providers"] = {s["provider"] for s in resolved_seats}
            captured["creds"] = set(credentials)
            def _run(rid, rdir):
                (rdir / "multi.sentinel").write_text("multi", encoding="utf-8")
                return 0
            return _run

        body = {"profile": self._mixed_provider_profile(), "run_id": "r_multi", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 202)
        self.assertEqual(h.responses[-1][1]["mode"], "live")
        self.assertTrue((self._run_dir(runs, "r_multi") / "multi.sentinel").exists())
        self.assertEqual(captured["providers"], {"deepseek", "anthropic"})
        self.assertEqual(captured["creds"], {"deepseek", "anthropic"})

    def test_live_missing_provider_credential_403_no_run_dir(self) -> None:
        from werewolf_eval.credential_store import CredentialStore
        cs = CredentialStore()
        cs.set("deepseek", "sk-ds")  # anthropic seat has NO credential

        def multi_factory(resolved_seats, credentials):
            return lambda rid, rdir: 0

        body = {"profile": self._mixed_provider_profile(), "run_id": "r_nocred", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        self.assertEqual(h.responses[-1][0], 403)
        self.assertEqual(h.responses[-1][1]["code"], "missing_provider_credential")
        self.assertFalse(self._run_dir(runs, "r_nocred").exists())

    # 8. capability precedes validity/shape: not-enabled + malformed profile
    def test_capability_precedes_validity_disabled_with_malformed(self) -> None:
        body = {"profile": {"name": "x"}, "run_id": "r_cap1", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=False)
        self.assertEqual(h.responses[-1][1]["code"], "live_api_disabled")
        self.assertFalse(self._run_dir(runs, "r_cap1").exists())

    # 8b. capability precedes validity/shape: not-enabled + non-deepseek profile
    def test_capability_precedes_shape_disabled_with_non_deepseek(self) -> None:
        body = {"profile": _valid_profile_payload("fakeonly"), "run_id": "r_cap2", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=False)
        self.assertEqual(h.responses[-1][1]["code"], "live_api_disabled")
        self.assertFalse(self._run_dir(runs, "r_cap2").exists())

    # 8c. flag-on + key-missing + malformed → missing_api_key (capability wins)
    def test_capability_missing_key_precedes_validity(self) -> None:
        body = {"profile": {"name": "x"}, "run_id": "r_cap3", "mode": "live"}
        h, runs = self._dispatch(body, live_enabled=True)
        self.assertEqual(h.responses[-1][1]["code"], "missing_api_key")
        self.assertFalse(self._run_dir(runs, "r_cap3").exists())

    # --- Task 4: honest execution markers on the wrapper's resolved-profile ---

    def _resolved_artifact(self, runs: Path, run_id: str) -> dict:
        return json.loads(
            (self._run_dir(runs, run_id) / "resolved-profile.json").read_text(encoding="utf-8")
        )

    def test_live_dispatch_stamps_live_markers(self) -> None:
        body = {"profile": _deepseek_profile(), "run_id": "r_live_mark", "mode": "live"}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        art = self._resolved_artifact(runs, "r_live_mark")
        self.assertEqual(art["execution_mode"], "live")
        self.assertEqual(art["live_api"], "used")
        self.assertTrue(art["secrets_redacted"])
        for seat in art["seats"]:
            self.assertEqual(seat["provider"], "deepseek")

    def test_fake_dispatch_stamps_fake_markers(self) -> None:
        body = {"profile": _deepseek_profile(), "run_id": "r_fake_mark", "mode": "fake"}
        cs, multi_factory = self._make_cs_and_factory()
        h, runs = self._dispatch(body, live_enabled=True, credential_store=cs, multi_factory=multi_factory)
        art = self._resolved_artifact(runs, "r_fake_mark")
        self.assertEqual(art["execution_mode"], "fake")
        self.assertEqual(art["live_api"], "not_used")


# ---------------------------------------------------------------------------
# G3-1 run_observer_server live opt-in — wired via the pure builder helper
# (localhost HTTP is blocked here, so the request-time effect is proven by
# feeding the resolved (live_enabled, live_launcher) into _check_live_capability
# rather than starting a real socket).
# ---------------------------------------------------------------------------


class ObserverServerLiveOptInTests(TestCase):
    def _args(self, argv: list[str]):
        from werewolf_eval.run_observer_server import build_arg_parser

        return build_arg_parser().parse_args(argv)

    def _resolve(self, argv: list[str], environ: dict):
        from werewolf_eval.run_observer_server import resolve_live_launcher

        return resolve_live_launcher(self._args(argv), environ)

    def _state(self, live_enabled: bool) -> ObserverServerState:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            return ObserverServerState(
                runs_dir=runs, launcher=default_fake_launcher,
                live_enabled=live_enabled,
            )

    def test_no_flag_yields_disabled(self) -> None:
        # B5 closeout: resolve_live_launcher returns live_enabled (bool); the
        # vestigial single-provider factory was removed. --api-key-env is ignored.
        live_enabled = self._resolve(
            ["--runs-dir", "x"], {"DEEPSEEK_API_KEY": "sk-test-fake-unused"}
        )
        self.assertFalse(live_enabled)
        # request-time effect: live → live_api_disabled
        st = self._state(live_enabled)
        self.assertEqual(_check_live_capability(st, "live")[1], "live_api_disabled")  # type: ignore[index]

    def test_flag_on_yields_enabled(self) -> None:
        # B5 closeout: --allow-live-api enables live. Live launches require a
        # client-supplied credential (no env-key factory). --api-key-env ignored.
        live_enabled = self._resolve(
            ["--allow-live-api", "--api-key-env", "DOES_NOT_EXIST_XXXX"], {}
        )
        self.assertTrue(live_enabled)
        # with empty credential store, capability returns missing_api_key
        st = self._state(live_enabled)
        self.assertEqual(_check_live_capability(st, "live")[1], "missing_api_key")  # type: ignore[index]

    def test_env_var_set_triggers_deprecation_warning(self) -> None:
        # B5 closeout: if the named env var is set, a deprecation warning is
        # printed to stderr; the env key is otherwise ignored.
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            live_enabled = self._resolve(
                ["--allow-live-api"], {"DEEPSEEK_API_KEY": "sk-test-fake-key"}
            )
        self.assertTrue(live_enabled)
        self.assertIn("deprecated", buf.getvalue())

    def test_help_lists_live_flags(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "werewolf_eval.run_observer_server", "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        for flag in ("--allow-live-api", "--api-key-env", "--max-live-requests",
                     "--deepseek-base-url", "--deepseek-model"):
            self.assertIn(flag, result.stdout)

    def test_help_output_never_contains_a_key(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "werewolf_eval.run_observer_server", "--help"],
            capture_output=True, text=True,
        )
        for marker in ("sk-", "Bearer ", "Authorization"):
            self.assertNotIn(marker, result.stdout)


# ---------------------------------------------------------------------------
# G3-1 secret-scan + artifact-contract regression (offline, in-process)
# ---------------------------------------------------------------------------


class _ConsensusFakeProvider:
    """Deterministic fake that drives a real consensus game to completion."""

    def __init__(self) -> None:
        self.requests: list = []
        self.responses: list = []

    def respond(self, request: object) -> object:
        from werewolf_eval.provider_contract import ProviderResponse

        self.requests.append(request)
        action = request.allowed_actions[0] if request.allowed_actions else "player_vote"  # type: ignore[attr-defined]
        obs = request.observation  # type: ignore[attr-defined]
        role = obs.get("role", "")
        phase = obs.get("phase", "")
        if role == "werewolf" and phase == "night":
            target = "p5" if 1 in (request.round,) else "p3"  # type: ignore[attr-defined]
        else:
            target = request.allowed_targets[0] if request.allowed_targets else request.actor  # type: ignore[attr-defined]
        raw = json.dumps({
            "action": action, "target": target, "reason_summary": "auto",
            "decision_type": "team_coordinated" if role == "werewolf" and phase == "night" else "inference_based",
            "confidence": 1.0,
        })
        resp = ProviderResponse(
            request_id=request.request_id,  # type: ignore[attr-defined]
            provider_name="deepseek", source_label="[DeepSeek API output]",
            raw_content=raw, latency_ms=1,
            token_usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )
        self.responses.append(resp)
        return resp


def _consensus_ok_factory(player_id: str) -> object:
    from werewolf_eval.provider_agent import ProviderAgent

    return ProviderAgent(player_id, _ConsensusFakeProvider())


_LIVE_SECRET_MARKERS = ("Authorization", "Bearer ", "api_key", "DEEPSEEK_API_KEY", "sk-")


class LiveArtifactContractTests(TestCase):
    """A faked live launch yields the same top-level artifact set as a fake
    launch — only the execution markers differ — and leaks no secret."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._root = Path(self._tmp.name)

    def _dispatch_real(self, run_id: str, mode: str) -> Path:
        from werewolf_eval.deepseek_launcher import build_deepseek_launcher
        from werewolf_eval.credential_store import CredentialStore

        runs = self._root / mode / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        live_launcher = build_deepseek_launcher(
            api_key="sk-test-fake-key", base_url="https://api.deepseek.com",
            model="deepseek-chat", max_tokens=64, max_requests=32,
            provider_factory=_consensus_ok_factory,
        )
        # B5 closeout: live_launcher field removed from state. Use
        # multi_provider_launcher_factory to inject the fake launcher for testing.
        cs = CredentialStore()
        cs.set("deepseek", "sk-test-fake-key")

        def multi_factory(resolved_seats, credentials):
            return live_launcher

        state = ObserverServerState(
            runs_dir=runs, launcher=default_fake_launcher,
            profiles_dir=self._root / "profiles",
            live_enabled=True,
            credential_store=cs,
            multi_provider_launcher_factory=multi_factory,
        )
        handler = _InProcessHandler(state)
        handler._handle_profile_launch(
            {"profile": _deepseek_profile(), "run_id": run_id, "mode": mode}
        )
        self.assertEqual(handler.responses[-1][0], 202)
        return runs / run_id

    @staticmethod
    def _top_level_files(run_dir: Path) -> list[str]:
        return sorted(p.name for p in run_dir.iterdir() if p.is_file())

    def test_live_and_fake_produce_same_top_level_artifact_set(self) -> None:
        fake_dir = self._dispatch_real("contract_fake", "fake")
        live_dir = self._dispatch_real("contract_live", "live")
        self.assertEqual(self._top_level_files(fake_dir), self._top_level_files(live_dir))
        # both have non-empty snapshots dirs
        self.assertTrue(any((fake_dir / "snapshots").glob("*.json")))
        self.assertTrue(any((live_dir / "snapshots").glob("*.json")))

    def test_only_execution_markers_differ(self) -> None:
        fake_dir = self._dispatch_real("contract_fake2", "fake")
        live_dir = self._dispatch_real("contract_live2", "live")
        fake_art = json.loads((fake_dir / "resolved-profile.json").read_text(encoding="utf-8"))
        live_art = json.loads((live_dir / "resolved-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(fake_art["execution_mode"], "fake")
        self.assertEqual(live_art["execution_mode"], "live")
        self.assertEqual(fake_art["live_api"], "not_used")
        self.assertEqual(live_art["live_api"], "used")
        # everything else (seats/profile_name/template/run_id-aside) identical
        fake_rest = {k: v for k, v in fake_art.items()
                     if k not in ("execution_mode", "live_api", "run_id")}
        live_rest = {k: v for k, v in live_art.items()
                     if k not in ("execution_mode", "live_api", "run_id")}
        self.assertEqual(fake_rest, live_rest)

    def test_faked_live_artifacts_contain_no_secret_markers(self) -> None:
        live_dir = self._dispatch_real("contract_scan", "live")
        for path in live_dir.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("sk-test-fake-key", text, path.name)
            for marker in _LIVE_SECRET_MARKERS:
                self.assertNotIn(marker, text, f"{marker!r} in {path.name}")

    def test_secrets_redacted_true_in_manifest_and_resolved_profile(self) -> None:
        live_dir = self._dispatch_real("contract_redacted", "live")
        manifest = json.loads((live_dir / "prompt-manifest.json").read_text(encoding="utf-8"))
        resolved = json.loads((live_dir / "resolved-profile.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest.get("secrets_redacted"))
        self.assertTrue(resolved.get("secrets_redacted"))


# ---------------------------------------------------------------------------
# G3-1 run-status reason exposure (A7) — the key-free reason recorded for a
# failed live run must surface in run detail / list / SSE, not just internally.
# Validated offline via the in-process handler harness (no socket).
# ---------------------------------------------------------------------------


class LiveRunStatusReasonTests(TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._runs = Path(self._tmp.name)

    def _handler(self) -> "_InProcessHandler":
        state = ObserverServerState(runs_dir=self._runs, launcher=default_fake_launcher)
        return _InProcessHandler(state)

    def _run(self, run_id: str, code: int) -> "_InProcessHandler":
        run_dir = self._runs / run_id
        run_dir.mkdir()
        h = self._handler()
        h._execute_run(run_id, run_dir, lambda rid, rd, c=code: c)
        return h

    def test_exit_3_exposes_budget_exhausted_in_detail(self) -> None:
        h = self._run("rr3", 3)
        run_dir = self._runs / "rr3"
        self.assertEqual(h._get_status("rr3", run_dir), "failed")
        self.assertEqual(h._get_error("rr3"), "budget_exhausted")
        detail = h._run_detail_with_reason("rr3", run_dir)
        self.assertEqual(detail["status"], "failed")
        self.assertEqual(detail["reason"], "budget_exhausted")

    def test_exit_2_exposes_provider_failure_in_detail(self) -> None:
        h = self._run("rr2", 2)
        run_dir = self._runs / "rr2"
        detail = h._run_detail_with_reason("rr2", run_dir)
        self.assertEqual(detail["status"], "failed")
        self.assertEqual(detail["reason"], "provider_failure")

    def test_exit_0_completed_has_no_reason(self) -> None:
        h = self._run("rr0", 0)
        run_dir = self._runs / "rr0"
        self.assertEqual(h._get_status("rr0", run_dir), "completed")
        detail = h._run_detail_with_reason("rr0", run_dir)
        self.assertNotIn("reason", detail)

    def test_launcher_exception_records_provider_failure_reason(self) -> None:
        run_dir = self._runs / "rrx"
        run_dir.mkdir()
        h = self._handler()

        def _boom(rid: str, rd: Path) -> int:
            raise RuntimeError("kaboom")

        h._execute_run("rrx", run_dir, _boom)
        self.assertEqual(h._get_status("rrx", run_dir), "failed")
        # an exception (not an exit code) still records a key-free reason
        detail = h._run_detail_with_reason("rrx", run_dir)
        self.assertEqual(detail["status"], "failed")
        self.assertEqual(detail["reason"], "provider_failure")

    def test_restart_stale_running_run_becomes_interrupted(self) -> None:
        from werewolf_eval.observer_protocol import read_run_status, write_run_status

        run_dir = self._runs / "rr_stale"
        run_dir.mkdir()
        write_run_status(run_dir, "running")

        h = self._handler()
        self.assertEqual(h._get_status("rr_stale", run_dir), "interrupted")
        self.assertEqual(read_run_status(run_dir), "interrupted")
        payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["interrupted_source"], "server_restart_stale")
        self.assertEqual(payload["status_reason"], "server_restart_stale")
        self.assertIn("interrupted_at", payload)

    def test_interrupt_wins_over_launcher_return(self) -> None:
        from werewolf_eval.observer_protocol import read_run_status

        run_dir = self._runs / "rr_interrupt"
        run_dir.mkdir()
        h = self._handler()

        def _interrupt_then_finish(rid: str, rd: Path) -> int:
            code, payload = h._run_manager().interrupt_run(
                rid, rd, source="user", reason="user_interrupted"
            )
            self.assertEqual((code, payload), (200, {"interrupted": rid}))
            return 0

        h._execute_run("rr_interrupt", run_dir, _interrupt_then_finish)
        self.assertEqual(h._get_status("rr_interrupt", run_dir), "interrupted")
        self.assertEqual(read_run_status(run_dir), "interrupted")
        payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["interrupted_source"], "user")
        self.assertEqual(payload["status_reason"], "user_interrupted")


# ---------------------------------------------------------------------------
# G3-2 run-detail execution_mode — the server reads its OWN resolved-profile.json
# and surfaces execution_mode as a JSON field so the Qt HUD chip can show
# executed truth with ZERO client file I/O.  Validated offline (no socket).
# ---------------------------------------------------------------------------


class RunDetailExecutionModeTests(TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._runs = Path(self._tmp.name)

    def _handler(self) -> "_InProcessHandler":
        state = ObserverServerState(runs_dir=self._runs, launcher=default_fake_launcher)
        return _InProcessHandler(state)

    _OMIT = object()

    def _run_dir(self, run_id: str, *, execution_mode: object = _OMIT) -> Path:
        run_dir = self._runs / run_id
        run_dir.mkdir()
        if execution_mode is not self._OMIT:
            artifact: dict[str, object] = {"schema_version": "g2d.profile.v1", "run_id": run_id}
            if execution_mode is not None:
                artifact["execution_mode"] = execution_mode
            (run_dir / "resolved-profile.json").write_text(
                json.dumps(artifact), encoding="utf-8"
            )
        return run_dir

    def test_live_execution_mode_surfaced(self) -> None:
        run_dir = self._run_dir("rd_live", execution_mode="live")
        detail = self._handler()._run_detail_with_reason("rd_live", run_dir)
        self.assertEqual(detail["execution_mode"], "live")

    def test_fake_execution_mode_surfaced(self) -> None:
        run_dir = self._run_dir("rd_fake", execution_mode="fake")
        detail = self._handler()._run_detail_with_reason("rd_fake", run_dir)
        self.assertEqual(detail["execution_mode"], "fake")

    def test_no_artifact_omits_execution_mode(self) -> None:
        run_dir = self._run_dir("rd_none")  # no resolved-profile.json
        detail = self._handler()._run_detail_with_reason("rd_none", run_dir)
        self.assertNotIn("execution_mode", detail)

    def test_non_string_execution_mode_is_omitted(self) -> None:
        # A malformed artifact (non-string execution_mode) must NOT surface a
        # truthy field — the chip then conservatively falls back to SIMULATION.
        run_dir = self._run_dir("rd_bad", execution_mode=123)
        detail = self._handler()._run_detail_with_reason("rd_bad", run_dir)
        self.assertNotIn("execution_mode", detail)

    def test_corrupt_artifact_is_tolerated(self) -> None:
        run_dir = self._runs / "rd_corrupt"
        run_dir.mkdir()
        (run_dir / "resolved-profile.json").write_text("{ not json", encoding="utf-8")
        detail = self._handler()._run_detail_with_reason("rd_corrupt", run_dir)
        self.assertNotIn("execution_mode", detail)
        self.assertIn("status", detail)  # detail still builds

    def test_execution_mode_coexists_with_reason(self) -> None:
        run_dir = self._run_dir("rd_both", execution_mode="live")
        h = self._handler()
        h._set_error("rd_both", "provider_failure")
        detail = h._run_detail_with_reason("rd_both", run_dir)
        self.assertEqual(detail["execution_mode"], "live")
        self.assertEqual(detail["reason"], "provider_failure")


class ProviderSpecsInSchemaTests(TestCase):
    def test_schema_payload_includes_provider_specs(self) -> None:
        payload = _schema_payload()
        self.assertIn("provider_specs", payload)
        ids = {row["id"] for row in payload["provider_specs"]}
        self.assertIn("qwen", ids)
        self.assertIn("deepseek", ids)
        # the base profile-schema fields are still present
        self.assertIn("providers", payload)
        self.assertIn("roles", payload)
