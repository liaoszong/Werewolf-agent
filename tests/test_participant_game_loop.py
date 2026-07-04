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
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
    build_werewolf_win_script,
)
from werewolf_eval.observer_server import create_observer_server
from werewolf_eval.participant_controller import InMemoryParticipantActionController

_HUMAN_TURN_KINDS = {"human_action", "human_timeout", "invalid_then_fallback"}


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
    elif "final_words" in actions:
        action_type = "final_words"
        payload = {"text": f"human final words from {seat_id} r{window['round']}"}
    elif "werewolf_kill" in actions:
        action_type = "werewolf_kill"
        payload = {"target": "p5"}
    elif "seer_check" in actions:
        action_type = "seer_check"
        payload = {"target": "p1"}
    elif "witch_save" in actions or "witch_poison" in actions:
        action_type = "pass"
        payload = {}
    elif "guard_protect" in actions:
        action_type = "guard_protect"
        payload = {"target": "p6"}
    elif "hunter_shoot" in actions:
        action_type = "pass"
        payload = {}
    else:
        raise AssertionError(f"unexpected window actions: {actions}")
    result = submit(
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
    if isinstance(result, tuple):
        status, body = result
        if status != 200:
            raise AssertionError(f"participant submit failed: {status} {body}")


class ParticipantGameLoopTests(unittest.TestCase):
    def _run_engine_with_human_seat(
        self,
        seat_id: str,
        *,
        script_builder=build_villager_win_script,
        timeout_seconds: float = 5,
        skip_action_windows: set[str] | None = None,
    ):
        run_id = f"p3c1b_{seat_id}"
        controller = InMemoryParticipantActionController()
        controller.configure_human_seat(run_id, seat_id)
        outcome_box: dict[str, object] = {}
        skip_action_windows = skip_action_windows or set()

        def run_engine() -> None:
            try:
                agents = build_emergent_fake_agents(script_builder())
                agents.pop(seat_id, None)
                engine = EmergentGameEngine(
                    config=build_emergent_config(game_id=run_id),
                    agents=agents,
                    budget=EmergentBudget(max_requests=80, max_day_rounds=3),
                    participant_controller=controller,
                    human_seat_ids={seat_id},
                    participant_action_timeout_seconds=timeout_seconds,
                )
                outcome_box["outcome"] = engine.run()
            except BaseException as exc:  # noqa: BLE001 - thread test must surface failures
                outcome_box["error"] = exc

        thread = threading.Thread(target=run_engine, daemon=True)
        thread.start()
        seen: set[str] = set()
        deadline = time.monotonic() + 15
        while thread.is_alive() and time.monotonic() < deadline:
            window = controller.wait_for_open_window(run_id, seat_id, timeout=0.2)
            if window is None or window.action_window_id in seen:
                continue
            seen.add(window.action_window_id)
            if set(window.allowed_actions) & skip_action_windows:
                continue
            _submit_for_window(
                lambda **kw: controller.submit_action(**kw),
                run_id=run_id,
                seat_id=seat_id,
                window=window.to_payload(),
                idempotency_key=f"idem-{len(seen)}",
            )
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive(), f"engine did not finish for {seat_id}")
        if "error" in outcome_box:
            raise outcome_box["error"]  # type: ignore[misc]
        outcome = outcome_box["outcome"]
        self.assertEqual(outcome.status, "completed")
        return outcome

    def test_engine_uses_human_final_words_when_seat_dies_without_provider_agent(self) -> None:
        outcome = self._run_engine_with_human_seat(
            "p5",
            script_builder=build_werewolf_win_script,
        )

        final_words = [
            event for event in outcome.game_log["events"]
            if event["type"] == "final_words" and event["actor"] == "p5"
        ]
        self.assertTrue(final_words)
        self.assertIn("human final words from p5", final_words[0]["data"]["summary"])
        p5_turns = [turn for turn in outcome.provider_turns if turn["actor"] == "p5"]
        self.assertTrue(p5_turns)
        self.assertTrue(all(turn["kind"] in _HUMAN_TURN_KINDS for turn in p5_turns))
        self.assertTrue(all(not turn["live_requested"] for turn in p5_turns))

    def test_human_final_words_timeout_does_not_block_game(self) -> None:
        outcome = self._run_engine_with_human_seat(
            "p5",
            script_builder=build_werewolf_win_script,
            timeout_seconds=0.05,
            skip_action_windows={"final_words"},
        )

        final_words = [
            event for event in outcome.game_log["events"]
            if event["type"] == "final_words" and event["actor"] == "p5"
        ]
        self.assertEqual(final_words, [])
        p5_timeouts = [
            turn for turn in outcome.provider_turns
            if turn["actor"] == "p5" and turn["kind"] == "human_timeout"
        ]
        self.assertTrue(p5_timeouts)

    def test_engine_uses_human_seer_night_action_without_provider_agent(self) -> None:
        outcome = self._run_engine_with_human_seat("p3")

        seer_checks = [
            event for event in outcome.game_log["events"]
            if event["type"] == "seer_check" and event["actor"] == "p3"
        ]
        self.assertTrue(seer_checks)
        self.assertEqual(seer_checks[0]["target"], "p1")
        p3_turns = [turn for turn in outcome.provider_turns if turn["actor"] == "p3"]
        self.assertTrue(p3_turns)
        self.assertTrue(all(turn["kind"] in _HUMAN_TURN_KINDS for turn in p3_turns))
        self.assertTrue(all(not turn["live_requested"] for turn in p3_turns))

    def test_engine_uses_human_witch_action_without_provider_agent(self) -> None:
        outcome = self._run_engine_with_human_seat("p4")

        witch_passes = [
            event for event in outcome.game_log["events"]
            if event["type"] == "witch_pass" and event["actor"] == "p4"
        ]
        self.assertTrue(witch_passes)
        p4_turns = [turn for turn in outcome.provider_turns if turn["actor"] == "p4"]
        self.assertTrue(p4_turns)
        self.assertTrue(all(turn["kind"] in _HUMAN_TURN_KINDS for turn in p4_turns))
        self.assertTrue(all(not turn["live_requested"] for turn in p4_turns))

    def test_engine_uses_human_werewolf_action_without_provider_agent(self) -> None:
        outcome = self._run_engine_with_human_seat("p1")

        wolf_kills = [
            event for event in outcome.game_log["events"]
            if event["type"] == "werewolf_kill" and event["actor"] == "p1"
        ]
        self.assertTrue(wolf_kills)
        self.assertEqual(wolf_kills[0]["target"], "p5")
        p1_turns = [turn for turn in outcome.provider_turns if turn["actor"] == "p1"]
        self.assertTrue(p1_turns)
        self.assertTrue(all(turn["kind"] in _HUMAN_TURN_KINDS for turn in p1_turns))
        self.assertTrue(all(not turn["live_requested"] for turn in p1_turns))

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
                self.assertEqual(
                    server.state.run_status.get("p3c1_http"),  # type: ignore[attr-defined]
                    "completed",
                    server.state.run_errors,  # type: ignore[attr-defined]
                )
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
