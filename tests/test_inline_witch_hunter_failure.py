from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test-module reuse

from werewolf_eval.emergent_engine import (
    EmergentGameEngine,
    build_emergent_config,
    build_emergent_hunter_config,
)
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_hunter_night_kill_script,
)
from werewolf_eval.provider_agent import ProviderAgent

# milk-pierce board carries a witch (p4); reuse it as a complete witch-board script.
from test_guard_sentinels import SEATS_WITH_WITCH, build_milk_pierce_script


def _no_action_json(target: str) -> str:
    """Well-formed JSON object, valid in every field EXCEPT the mandatory `action`
    key — the exact shape B12-01 says was silently treated as a pass."""
    return json.dumps(
        {"target": target, "reason_summary": "x", "decision_type": "default", "confidence": 1.0},
        ensure_ascii=False,
    )


class _RaisingProvider:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def respond(self, request):  # noqa: ANN001 - test stub
        raise self._exc


def _witch_night1_turn(outcome):
    return next(t for t in outcome.provider_turns
               if t["actor"] == "p4" and t["request_id"].endswith("_witch") and t["round"] == 1)


def _hunter_shot_turn(outcome):
    return next(t for t in outcome.provider_turns if t["request_id"].endswith("_shot"))


def _failures(outcome):
    return outcome.failure_audit["failures"]


class WitchMissingActionTest(unittest.TestCase):
    """B12-01: a JSON-valid witch response missing the `action` key must NOT be
    silently counted as a live success pass — it is a parse_failure + downgrade,
    matching ProviderAgent's mandatory-field contract."""

    def test_missing_action_is_parse_failure_not_live_success(self) -> None:
        script = build_milk_pierce_script()
        script[("p4", "night", 1)] = _no_action_json("p6")
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="witch_no_action", seat_roles=SEATS_WITH_WITCH),
            agents=build_emergent_fake_agents(script), seed=0,
        )
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        turn = _witch_night1_turn(outcome)
        self.assertEqual(turn["kind"], "invalid_then_fallback")
        self.assertIsNone(turn["token_usage"])
        self.assertTrue(any(f["actor"] == "p4" and f["kind"] == "parse_failure" and f["round"] == 1
                            for f in _failures(outcome)))


class WitchTransportErrorTest(unittest.TestCase):
    """B12-02/03: a witch provider transport exception must classify as
    transport_error (NOT parse_failure — that conflates 'model bad' with
    'network bad')."""

    def test_transport_exception_classified_as_transport_error(self) -> None:
        agents = build_emergent_fake_agents(build_milk_pierce_script())
        agents["p4"] = ProviderAgent(
            "p4", _RaisingProvider(RuntimeError("[DeepSeek API output] transport error: ConnectionError")),
        )
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="witch_transport", seat_roles=SEATS_WITH_WITCH),
            agents=agents, seed=0,
        )
        outcome = engine.run()
        # The witch raising every night never terminates the scripted board, so the
        # run may fail-close on the round cap — irrelevant to *failure classification*,
        # which is recorded on the round-1 witch turn regardless of final status.
        turn = _witch_night1_turn(outcome)
        self.assertEqual(turn["kind"], "timeout_then_fallback")
        kinds = [f["kind"] for f in _failures(outcome) if f["actor"] == "p4"]
        self.assertIn("transport_error", kinds)
        self.assertNotIn("parse_failure", kinds)


class HunterMissingActionTest(unittest.TestCase):
    """B12-01 parity for the hunter inline path."""

    def test_missing_action_is_parse_failure_not_live_success(self) -> None:
        script = build_hunter_night_kill_script()
        script[("p6", "hunter_shot", 1)] = _no_action_json("p1")
        engine = EmergentGameEngine(
            config=build_emergent_hunter_config(),
            agents=build_emergent_fake_agents(script), seed=0,
        )
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        turn = _hunter_shot_turn(outcome)
        self.assertEqual(turn["kind"], "invalid_then_fallback")
        self.assertTrue(any(f["actor"] == "p6" and f["kind"] == "parse_failure"
                            for f in _failures(outcome)))


class HunterTransportErrorTest(unittest.TestCase):
    """B12-02/03 parity for the hunter inline path."""

    def test_transport_exception_classified_as_transport_error(self) -> None:
        agents = build_emergent_fake_agents(build_hunter_night_kill_script())
        agents["p6"] = ProviderAgent(
            "p6", _RaisingProvider(RuntimeError("[DeepSeek API output] transport error: ConnectionError")),
        )
        engine = EmergentGameEngine(
            config=build_emergent_hunter_config(),
            agents=agents, seed=0,
        )
        outcome = engine.run()
        # final status irrelevant to failure classification (see witch transport test)
        turn = _hunter_shot_turn(outcome)
        self.assertEqual(turn["kind"], "timeout_then_fallback")
        kinds = [f["kind"] for f in _failures(outcome) if f["actor"] == "p6"]
        self.assertIn("transport_error", kinds)
        self.assertNotIn("parse_failure", kinds)


if __name__ == "__main__":
    unittest.main()
