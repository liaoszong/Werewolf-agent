"""Offline tests for the P2-A-2 smoke JUDGE: synthesize artifact dirs and assert
each hard gate passes/fails as designed (no network, no key)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_smoke_check import DEEPSEEK_SOURCE_LABEL, evaluate_emergent_smoke

MODEL = "deepseek-v4-flash"


def _live_turn(actor="p1", kind="live_success", label=DEEPSEEK_SOURCE_LABEL, tokens=19):
    return {
        "request_id": f"r_{actor}", "round": 1, "phase": "day", "actor": actor,
        "response_kind": "action", "live_requested": True, "kind": kind,
        "fallback_reason": None, "source_label": label, "model": MODEL,
        "token_usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": tokens},
        "observation_source_event_ids": ["e1"],
    }


def _write_run(tmp: Path, *, turns, completed=True, model=MODEL, obs_text="可读文本", secret=False):
    live_req = sum(1 for t in turns if t.get("live_requested"))
    live_succ = sum(1 for t in turns if t.get("kind") == "live_success")
    (tmp / "provider-turns.json").write_text(json.dumps({
        "live_requested_actions": live_req,
        "live_success_actions": live_succ,
        "live_success_rate": (live_succ / live_req) if live_req else 1.0,
        "by_provider_result_kind": {},
        "turns": turns,
    }), encoding="utf-8")
    (tmp / "provider-trace.json").write_text(json.dumps({
        "requests": [{"request_id": "r", "observation_text": obs_text}],
        "responses": [],
    }), encoding="utf-8")
    (tmp / "prompt-manifest.json").write_text(json.dumps({
        "agents": [{"player_id": f"p{i}", "model": model} for i in range(1, 7)],
    }), encoding="utf-8")
    if completed:
        (tmp / "game-log.json").write_text(json.dumps({"result": {"winner": "villager"}}), encoding="utf-8")
    if secret:
        (tmp / "leak.json").write_text(json.dumps({"k": "sk-leaked"}), encoding="utf-8")


class EmergentSmokeJudgeTests(unittest.TestCase):
    def _good_turns(self):
        return [_live_turn(actor=f"p{i%6}") for i in range(22)]

    def test_passing_run(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _write_run(tmp, turns=self._good_turns())
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertTrue(v["passed"], v["checks"])

    def test_low_live_rate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = [_live_turn(actor=f"p{i}") for i in range(10)] + [
                _live_turn(actor=f"q{i}", kind="timeout_then_fallback", label=None) for i in range(12)
            ]
            _write_run(tmp, turns=turns)
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(v["passed"])
            self.assertFalse(v["checks"]["live_success_rate_ok"])

    def test_fallback_masquerading_as_deepseek_fails_honesty(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = self._good_turns() + [_live_turn(actor="x", kind="timeout_then_fallback", label=DEEPSEEK_SOURCE_LABEL)]
            _write_run(tmp, turns=turns)
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(v["checks"]["per_turn_honesty_ok"])

    def test_live_success_zero_tokens_fails_honesty(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = self._good_turns() + [_live_turn(actor="z", tokens=0)]
            _write_run(tmp, turns=turns)
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(v["checks"]["per_turn_honesty_ok"])

    def test_wrong_manifest_model_fails(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _write_run(tmp, turns=self._good_turns(), model="unknown")
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(v["checks"]["manifest_model_honest"])

    def test_empty_observation_text_fails_gate1(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _write_run(tmp, turns=self._good_turns(), obs_text="  ")
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(v["checks"]["observation_text_present"])

    def test_budget_failclosed_no_gamelog_fails(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _write_run(tmp, turns=self._good_turns(), completed=False)
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(v["checks"]["budget_not_exhausted"])

    def test_secret_marker_anywhere_fails(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _write_run(tmp, turns=self._good_turns(), secret=True)
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(v["checks"]["no_secret_markers"])

    def test_short_game_floor_waived_with_flag(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _write_run(tmp, turns=[_live_turn(actor=f"p{i}") for i in range(12)])  # < 20
            strict = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(strict["checks"]["live_success_floor_ok"])
            waived = evaluate_emergent_smoke(tmp, expected_model=MODEL, allow_short_game=True)
            self.assertTrue(waived["checks"]["live_success_floor_ok"])


if __name__ == "__main__":
    unittest.main()
