"""P3-C-1a human villager seat integration tests."""

from __future__ import annotations

import json
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from werewolf_eval.emergent_engine import EmergentBudget, EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.observer_server import create_observer_server
from werewolf_eval.participant_controller import InMemoryParticipantActionController


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
        with urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _start_server(runs_dir: Path):
    server = create_observer_server("127.0.0.1", 0, runs_dir)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def _submit_for_window(
    submit,
    *,
    run_id: str,
    seat_id: str,
    window: dict[str, object],
    idempotency_key: str,
) -> None:
    actions = set(window["allowed_actions"])
    if "speech" in actions:
        action_type = "speech"
        payload: dict[str, object] = {"text": f"human speech from {seat_id} r{window['round']}"}
    elif "vote" in actions:
        action_type = "vote"
        payload = {"target": "p1"}
    else:
        raise AssertionError(f"unexpected window actions: {actions}")
    submit(
        run_id=run_id,
        seat_id=seat_id,
        payload={
            "action_window_id": window["action_window_id"],
            "game_revision": window["game_revision"],
            "idempotency_key": idempotency_key,
            "action_type": action_type,
            "payload": payload,
        },
    )


class ParticipantGameLoopTests(unittest.TestCase):
    def test_engine_uses_participant_speech_and_vote_without_provider_turns(self) -> None:
        run_id = "p3c1_engine"
        controller = InMemoryParticipantActionController()
        controller.configure_human_seat(run_id, "p5")
        outcome_box: dict[str, object] = {}

        def run_engine() -> None:
            engine = EmergentGameEngine(
                config=build_emergent_config(game_id=run_id),
                agents=build_emergent_fake_agents(build_villager_win_script()),
                budget=EmergentBudget(max_requests=80, max_day_rounds=3),
                participant_controller=controller,
                human_seat_ids={"p5"},
                participant_action_timeout_seconds=5,
            )
            outcome_box["outcome"] = engine.run()

        thread = threading.Thread(target=run_engine, daemon=True)
        thread.start()
        seen: set[str] = set()
        deadline = time.monotonic() + 10
        while thread.is_alive() and time.monotonic() < deadline:
            window = controller.wait_for_open_window(run_id, "p5", timeout=0.2)
            if window is None or window.action_window_id in seen:
                continue
            seen.add(window.action_window_id)
            _submit_for_window(
                lambda **kw: controller.submit_action(**kw),
                run_id=run_id,
                seat_id="p5",
                window=window.to_payload(),
                idempotency_key=f"idem-{len(seen)}",
            )
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive(), "engine did not finish after participant submissions")
        outcome = outcome_box["outcome"]
        self.assertEqual(outcome.status, "completed")
        p5_speeches = [
            e for e in outcome.game_log["events"]
            if e["type"] == "player_speech" and e["actor"] == "p5"
        ]
        self.assertTrue(any("human speech from p5" in e["data"]["summary"] for e in p5_speeches))
        p5_votes = [
            e for e in outcome.game_log["events"]
            if e["type"] == "player_vote" and e["actor"] == "p5"
        ]
        self.assertEqual([e["target"] for e in p5_votes], ["p1"])
        p5_turns = [t for t in outcome.provider_turns if t["actor"] == "p5"]
        self.assertTrue(p5_turns)
        self.assertTrue(all(t["kind"] == "human_action" for t in p5_turns))
        self.assertTrue(all(not t["live_requested"] for t in p5_turns))

    def test_observer_participant_routes_drive_human_enabled_run(self) -> None:
        with TemporaryDirectory() as tmp:
            runs = Path(tmp)
            server, base_url = _start_server(runs)
            try:
                status, launch = _request_json(
                    base_url,
                    "/api/runs",
                    method="POST",
                    payload={
                        "run_id": "p3c1_http",
                        "template": "default_6p_fake",
                        "participant": {"seat_id": "p5"},
                    },
                )
                self.assertEqual(status, 202)
                self.assertEqual(launch["participant"]["seat_id"], "p5")

                status, bad_join = _request_json(
                    base_url,
                    "/api/runs/p3c1_http/participants/join",
                    method="POST",
                    payload={"seat_id": "p6", "join_code": "local-dev-code"},
                )
                self.assertEqual(status, 403)
                self.assertEqual(bad_join["error_code"], "seat_not_controlled_by_session")
                self.assertNotIn("participant_session_token", bad_join)

                status, join = _request_json(
                    base_url,
                    "/api/runs/p3c1_http/participants/join",
                    method="POST",
                    payload={"seat_id": "p5", "join_code": "local-dev-code"},
                )
                self.assertEqual(status, 200)
                token = str(join["participant_session_token"])
                auth = {"Authorization": f"Bearer {token}"}

                seen: set[str] = set()
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    status_now = server.state.run_status.get("p3c1_http")  # type: ignore[attr-defined]
                    if status_now == "completed":
                        break
                    status, state = _request_json(
                        base_url, "/api/runs/p3c1_http/participant/state", headers=auth
                    )
                    self.assertEqual(status, 200)
                    window = state.get("open_action_window")
                    if isinstance(window, dict) and window["action_window_id"] not in seen:
                        seen.add(str(window["action_window_id"]))

                        def post_action(**kw):
                            return _request_json(
                                base_url,
                                "/api/runs/p3c1_http/participant/actions",
                                method="POST",
                                payload=kw["payload"],
                                headers=auth,
                            )

                        _submit_for_window(
                            post_action,
                            run_id="p3c1_http",
                            seat_id="p5",
                            window=window,
                            idempotency_key=f"http-{len(seen)}",
                        )
                    time.sleep(0.05)
                self.assertEqual(server.state.run_status.get("p3c1_http"), "completed")  # type: ignore[attr-defined]
                game = json.loads((runs / "p3c1_http" / "game-log.json").read_text(encoding="utf-8"))
                self.assertTrue(
                    any(
                        e["type"] == "player_speech"
                        and e["actor"] == "p5"
                        and "human speech from p5" in e["data"]["summary"]
                        for e in game["events"]
                    )
                )
                events_text = (runs / "p3c1_http" / "events.jsonl").read_text(encoding="utf-8")
                self.assertIn("action_window_opened", events_text)
                self.assertIn("action_accepted", events_text)
                self.assertNotIn(token, events_text)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
