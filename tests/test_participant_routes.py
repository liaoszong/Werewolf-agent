"""HTTP tests for the P3-C participant route skeleton."""

from __future__ import annotations

import json
import threading
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from werewolf_eval.observer_server import create_observer_server


def _event(kind: str, visibility: str, seq: int) -> dict[str, object]:
    return {
        "event_id": f"evt_{seq}_{kind}",
        "seq": seq,
        "kind": kind,
        "round": 0,
        "phase": "p3c_stub",
        "actor": "system",
        "visibility": visibility,
        "ts": "2026-07-03T00:00:00Z",
        "payload": {"event_id": f"g_{seq}_{kind}", "message": kind},
    }


def _make_run(root: Path, run_id: str, *, status: str = "running") -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "status.json").write_text(json.dumps({"status": status}), encoding="utf-8")
    (run_dir / "events.jsonl").write_text(
        json.dumps(_event("game_started", "public", 0)) + "\n"
        + json.dumps(_event("observation_delivered", "internal", 1)) + "\n",
        encoding="utf-8",
    )
    return run_dir


def _start_server(runs_dir: Path):
    server = create_observer_server("127.0.0.1", 0, runs_dir)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req_headers: dict[str, str] = {}
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
    req = Request(f"{base_url}{path}", data=data, headers=req_headers, method=method)
    try:
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _request_text(
    base_url: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    req = Request(f"{base_url}{path}", headers=headers or {})
    try:
        with urlopen(req) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read().decode("utf-8")


class ParticipantRouteTests(TestCase):
    def test_join_state_submit_duplicate_and_sse_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp)
            _make_run(runs, "run_participant")
            server, base_url = _start_server(runs)
            server.state.run_status["run_participant"] = "running"  # type: ignore[attr-defined]
            try:
                status, missing = _request_json(
                    base_url, "/api/runs/run_participant/participant/state"
                )
                self.assertEqual(status, 401)
                self.assertEqual(missing["schema_version"], "p3c.error.v1")
                self.assertEqual(missing["error_code"], "missing_or_invalid_session")
                self.assertNotIn("run_id", missing)
                self.assertNotIn("seat_id", missing)

                status, join_override = _request_json(
                    base_url,
                    "/api/runs/run_participant/participants/join?perspective=god",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                self.assertEqual(status, 403)
                self.assertEqual(join_override["error_code"], "visibility_forbidden")

                status, join = _request_json(
                    base_url,
                    "/api/runs/run_participant/participants/join",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                self.assertEqual(status, 200)
                self.assertEqual(join["schema_version"], "p3c.participant_session.v1")
                self.assertEqual(join["run_id"], "run_participant")
                self.assertEqual(join["seat_id"], "p3")
                self.assertEqual(join["perspective"], "role:p3")
                self.assertEqual(join["reconnect_cursor"], "event:0")
                self.assertIn("participant_session_token", join)
                self.assertNotIn("last_seen_cursor", join)
                self.assertNotIn("join_code", json.dumps(join))
                token = str(join["participant_session_token"])
                auth = {"Authorization": f"Bearer {token}"}

                status, rejected = _request_json(
                    base_url,
                    "/api/runs/run_participant/participant/state?perspective=god",
                    headers=auth,
                )
                self.assertEqual(status, 403)
                self.assertEqual(rejected["error_code"], "visibility_forbidden")

                status, state = _request_json(
                    base_url, "/api/runs/run_participant/participant/state", headers=auth
                )
                self.assertEqual(status, 200)
                self.assertEqual(state["schema_version"], "p3c.participant_state.v1")
                self.assertEqual(state["perspective"], "role:p3")
                self.assertNotIn("artifacts", state)
                projection = state["projection"]
                self.assertIsInstance(projection, dict)
                self.assertEqual(projection["perspective"], "role:p3")
                self.assertEqual(len(projection["events"]), 1)
                self.assertEqual(projection["hidden_event_count"], 1)
                window = state["open_action_window"]
                self.assertIsInstance(window, dict)
                self.assertEqual(window["status"], "open")
                self.assertEqual(window["allowed_actions"], ["speech", "pass"])

                status, content_type, stream = _request_text(
                    base_url,
                    "/api/runs/run_participant/participant/events?cursor=event:0",
                    headers=auth,
                )
                self.assertEqual(status, 200)
                self.assertIn("text/event-stream", content_type)
                self.assertIn("event: run_status", stream)
                self.assertIn("event: action_window_opened", stream)
                self.assertNotIn(token, stream)

                submission = {
                    "action_window_id": window["action_window_id"],
                    "game_revision": window["game_revision"],
                    "idempotency_key": "idem-1",
                    "action_type": "speech",
                    "payload": {"text": "I want to hear from p5."},
                }
                status, accepted = _request_json(
                    base_url,
                    "/api/runs/run_participant/participant/actions",
                    method="POST",
                    payload=submission,
                    headers=auth,
                )
                self.assertEqual(status, 200)
                self.assertEqual(accepted["status"], "accepted")
                self.assertEqual(accepted["game_revision"], 1)
                self.assertEqual(accepted["reconnect_cursor"], "event:1")

                status, duplicate = _request_json(
                    base_url,
                    "/api/runs/run_participant/participant/actions",
                    method="POST",
                    payload=submission,
                    headers=auth,
                )
                self.assertEqual(status, 200)
                self.assertEqual(duplicate["status"], "duplicate")
                self.assertEqual(duplicate["accepted_event_id"], accepted["accepted_event_id"])

                conflict_submission = dict(submission)
                conflict_submission["payload"] = {"text": "changed"}
                status, conflict = _request_json(
                    base_url,
                    "/api/runs/run_participant/participant/actions",
                    method="POST",
                    payload=conflict_submission,
                    headers=auth,
                )
                self.assertEqual(status, 409)
                self.assertEqual(conflict["error_code"], "idempotency_conflict")

                status, after = _request_json(
                    base_url, "/api/runs/run_participant/participant/state", headers=auth
                )
                self.assertEqual(status, 200)
                self.assertIsNone(after["open_action_window"])
                self.assertEqual(after["reconnect_cursor"], accepted["reconnect_cursor"])
            finally:
                server.shutdown()
                server.server_close()

    def test_token_cannot_control_another_run(self) -> None:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp)
            _make_run(runs, "run_one")
            _make_run(runs, "run_two")
            server, base_url = _start_server(runs)
            try:
                _, join = _request_json(
                    base_url,
                    "/api/runs/run_one/participants/join",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                token = str(join["participant_session_token"])
                status, body = _request_json(
                    base_url,
                    "/api/runs/run_two/participant/state",
                    headers={"Authorization": f"Bearer {token}"},
                )
                self.assertEqual(status, 403)
                self.assertEqual(body["error_code"], "seat_not_controlled_by_session")
                self.assertEqual(body["run_id"], "run_one")
                self.assertEqual(body["seat_id"], "p3")
                self.assertNotIn(token, json.dumps(body))
            finally:
                server.shutdown()
                server.server_close()

    def test_participant_sse_rejects_invalid_cursor(self) -> None:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp)
            _make_run(runs, "run_cursor")
            server, base_url = _start_server(runs)
            try:
                _, join = _request_json(
                    base_url,
                    "/api/runs/run_cursor/participants/join",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                token = str(join["participant_session_token"])
                status, body = _request_json(
                    base_url,
                    "/api/runs/run_cursor/participant/events?cursor=bad-cursor",
                    headers={"Authorization": f"Bearer {token}"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body["schema_version"], "p3c.error.v1")
                self.assertEqual(body["error_code"], "invalid_payload")
                self.assertNotIn(token, json.dumps(body))
            finally:
                server.shutdown()
                server.server_close()

    def test_revoked_or_expired_session_requires_rejoin(self) -> None:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp)
            _make_run(runs, "run_session")
            server, base_url = _start_server(runs)
            try:
                _, join = _request_json(
                    base_url,
                    "/api/runs/run_session/participants/join",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                token = str(join["participant_session_token"])
                auth = {"Authorization": f"Bearer {token}"}
                with server.state.lock:  # type: ignore[attr-defined]
                    session = server.state.participant_sessions[token]  # type: ignore[attr-defined]
                    server.state.participant_sessions[token] = replace(  # type: ignore[attr-defined]
                        session,
                        revoked_at="2026-07-03T00:00:00Z",
                    )
                status, revoked = _request_json(
                    base_url, "/api/runs/run_session/participant/state", headers=auth
                )
                self.assertEqual(status, 401)
                self.assertEqual(revoked["error_code"], "missing_or_invalid_session")
                self.assertNotIn(token, json.dumps(revoked))

                _, rejoin = _request_json(
                    base_url,
                    "/api/runs/run_session/participants/join",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                expired_token = str(rejoin["participant_session_token"])
                expired_auth = {"Authorization": f"Bearer {expired_token}"}
                expired_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
                with server.state.lock:  # type: ignore[attr-defined]
                    session = server.state.participant_sessions[expired_token]  # type: ignore[attr-defined]
                    server.state.participant_sessions[expired_token] = replace(  # type: ignore[attr-defined]
                        session,
                        expires_at=expired_at,
                    )
                status, expired = _request_json(
                    base_url, "/api/runs/run_session/participant/state", headers=expired_auth
                )
                self.assertEqual(status, 401)
                self.assertEqual(expired["error_code"], "missing_or_invalid_session")
                self.assertNotIn(expired_token, json.dumps(expired))
            finally:
                server.shutdown()
                server.server_close()

    def test_state_reconnect_cursor_advances_after_window_timeout(self) -> None:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp)
            _make_run(runs, "run_timeout")
            server, base_url = _start_server(runs)
            server.state.run_status["run_timeout"] = "running"  # type: ignore[attr-defined]
            try:
                _, join = _request_json(
                    base_url,
                    "/api/runs/run_timeout/participants/join",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                token = str(join["participant_session_token"])
                auth = {"Authorization": f"Bearer {token}"}
                _, state = _request_json(
                    base_url, "/api/runs/run_timeout/participant/state", headers=auth
                )
                window = state["open_action_window"]
                self.assertIsInstance(window, dict)

                self.assertIsNone(
                    server.state.participant_controller.wait_for_action(  # type: ignore[attr-defined]
                        str(window["action_window_id"]),
                        timeout=0.01,
                    )
                )

                status, after_timeout = _request_json(
                    base_url, "/api/runs/run_timeout/participant/state", headers=auth
                )
                self.assertEqual(status, 200)
                self.assertIsNone(after_timeout["open_action_window"])
                self.assertEqual(after_timeout["reconnect_cursor"], "event:1")
            finally:
                server.shutdown()
                server.server_close()

    def test_submit_rejects_run_not_accepting_actions(self) -> None:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp)
            _make_run(runs, "run_done", status="completed")
            server, base_url = _start_server(runs)
            try:
                _, join = _request_json(
                    base_url,
                    "/api/runs/run_done/participants/join",
                    method="POST",
                    payload={"seat_id": "p3", "join_code": "local-dev-code"},
                )
                token = str(join["participant_session_token"])
                _, state = _request_json(
                    base_url,
                    "/api/runs/run_done/participant/state",
                    headers={"Authorization": f"Bearer {token}"},
                )
                window = state["open_action_window"]
                status, body = _request_json(
                    base_url,
                    "/api/runs/run_done/participant/actions",
                    method="POST",
                    payload={
                        "action_window_id": window["action_window_id"],
                        "game_revision": window["game_revision"],
                        "idempotency_key": "idem-1",
                        "action_type": "pass",
                        "payload": {},
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                self.assertEqual(status, 423)
                self.assertEqual(body["error_code"], "run_not_accepting_actions")
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
