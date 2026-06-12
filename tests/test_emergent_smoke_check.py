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
OPENAI_LABEL = "[OpenAI API output]"
ANTHROPIC_LABEL = "[Anthropic API output]"
FAKE_LABEL = "[deterministic fake provider output]"


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
            _write_run(tmp, turns=[_live_turn(actor=f"p{i}") for i in range(8)])  # < 12 floor
            strict = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertFalse(strict["checks"]["live_success_floor_ok"])
            waived = evaluate_emergent_smoke(tmp, expected_model=MODEL, allow_short_game=True)
            self.assertTrue(waived["checks"]["live_success_floor_ok"])

    def test_floor_twelve_passes_a_realistic_short_terminal(self) -> None:
        # Both real 2026-06-05 games (19 and 13 live successes) must pass the floor.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _write_run(tmp, turns=[_live_turn(actor=f"p{i}") for i in range(13)])  # werewolf-win run
            v = evaluate_emergent_smoke(tmp, expected_model=MODEL)
            self.assertTrue(v["checks"]["live_success_floor_ok"])
            self.assertTrue(v["passed"], v["checks"])


def _live_turn_labeled(actor, label, tokens=19, model=MODEL):
    t = _live_turn(actor=actor, label=label, tokens=tokens)
    t["model"] = model
    return t


def _write_mixed_run(tmp: Path, *, turns, agents):
    """Mixed-provider run: per-seat agents carry their own model/provider."""
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
        "requests": [{"request_id": "r", "observation_text": "可读文本"}], "responses": [],
    }), encoding="utf-8")
    (tmp / "prompt-manifest.json").write_text(json.dumps({"agents": agents}), encoding="utf-8")
    (tmp / "game-log.json").write_text(json.dumps({"result": {"winner": "villager"}}), encoding="utf-8")


class ProviderAgnosticHonestyTests(unittest.TestCase):
    """B34-07: the honesty gate accepts any real live-provider label and supports a
    per-seat expected provider/model plan, without any live API call."""

    def test_non_deepseek_single_provider_passes(self) -> None:
        # A single non-DeepSeek live provider (OpenAI) is honest -> passes.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = [_live_turn(actor=f"p{i}", label=OPENAI_LABEL) for i in range(13)]
            _write_run(tmp, turns=turns, model="gpt-x")
            v = evaluate_emergent_smoke(tmp, expected_model="gpt-x")
            self.assertTrue(v["passed"], v["checks"])
            self.assertTrue(v["checks"]["per_turn_honesty_ok"])

    def test_fake_label_on_live_turn_fails_honesty(self) -> None:
        # A live_success turn carrying a FAKE label is not a real live turn.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = [_live_turn(actor=f"p{i}", label=OPENAI_LABEL) for i in range(13)]
            turns.append(_live_turn(actor="fake", label=FAKE_LABEL))  # fake masquerading as live_success
            _write_run(tmp, turns=turns, model="gpt-x")
            v = evaluate_emergent_smoke(tmp, expected_model="gpt-x")
            self.assertFalse(v["checks"]["per_turn_honesty_ok"])

    def test_expected_source_label_pin_rejects_other_live_label(self) -> None:
        # Pinning DeepSeek but receiving OpenAI live output -> honesty fails.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = [_live_turn(actor=f"p{i}", label=OPENAI_LABEL) for i in range(13)]
            _write_run(tmp, turns=turns, model="gpt-x")
            v = evaluate_emergent_smoke(tmp, expected_model="gpt-x",
                                        expected_source_label=DEEPSEEK_SOURCE_LABEL)
            self.assertFalse(v["checks"]["per_turn_honesty_ok"])

    def test_mixed_provider_per_seat_passes(self) -> None:
        # p1-p3 on OpenAI, p4-p6 on Anthropic; per-seat manifest plan matches.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = (
                [_live_turn_labeled(f"p{i}", OPENAI_LABEL, model="gpt-x") for i in (1, 2, 3)] * 3
                + [_live_turn_labeled(f"p{i}", ANTHROPIC_LABEL, model="claude-y") for i in (4, 5, 6)] * 2
            )
            agents = (
                [{"player_id": f"p{i}", "model": "gpt-x", "provider": "openai"} for i in (1, 2, 3)]
                + [{"player_id": f"p{i}", "model": "claude-y", "provider": "anthropic"} for i in (4, 5, 6)]
            )
            expected = {
                **{f"p{i}": {"model": "gpt-x", "provider": "openai"} for i in (1, 2, 3)},
                **{f"p{i}": {"model": "claude-y", "provider": "anthropic"} for i in (4, 5, 6)},
            }
            _write_mixed_run(tmp, turns=turns, agents=agents)
            v = evaluate_emergent_smoke(tmp, expected_models_by_seat=expected)
            self.assertTrue(v["passed"], v["checks"])

    def test_empty_per_seat_plan_fails_closed(self) -> None:
        # An empty per-seat plan must NOT vacuously pass the manifest gate.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = [_live_turn_labeled(f"p{i}", OPENAI_LABEL, model="gpt-x") for i in (1, 2, 3)] * 5
            agents = [{"player_id": f"p{i}", "model": "gpt-x"} for i in (1, 2, 3)]
            _write_mixed_run(tmp, turns=turns, agents=agents)
            v = evaluate_emergent_smoke(tmp, expected_models_by_seat={})
            self.assertFalse(v["checks"]["manifest_model_honest"])

    def test_per_seat_wrong_model_fails(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            turns = [_live_turn_labeled(f"p{i}", OPENAI_LABEL, model="gpt-x") for i in (1, 2, 3)] * 5
            agents = [{"player_id": f"p{i}", "model": "gpt-x", "provider": "openai"} for i in (1, 2, 3)]
            expected = {f"p{i}": {"model": "WRONG"} for i in (1, 2, 3)}
            _write_mixed_run(tmp, turns=turns, agents=agents)
            v = evaluate_emergent_smoke(tmp, expected_models_by_seat=expected)
            self.assertFalse(v["checks"]["manifest_model_honest"])


if __name__ == "__main__":
    unittest.main()
