"""P2-D Task 1: build_settlement_bundle pure-unit gate.

Spec §5/§6.1: curtain layer (run_id/game_id/result/players-reveal/board_timeline)
always comes from the game-log; battle-report layer comes from
score_game+summarize_metrics+attribute_game; degrade with a bare reason CODE
(never raw exception text/path/stack). All three degrade codes are produced
explicitly — missing/invalid via the decision_log_status pre-check, scoring_failed
via the except branch.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

from werewolf_eval.game_log import load_game_log, parse_game_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.settlement_bundle import build_settlement_bundle

_GOLD = Path(__file__).resolve().parent.parent / "docs" / "gold-game"
_GAME_LOG_PATH = _GOLD / "g001-game-log.json"
_DECISION_LOG_PATH = _GOLD / "g001-decision-log.json"


class TestBuildSettlementBundle(unittest.TestCase):
    """P2-D §5/§6.1."""

    def _game(self):
        # g001 villager-win arc: night kills + day vote/elim across 2 rounds → game_end.
        return load_game_log(_GAME_LOG_PATH)

    def _decision_log(self):
        return load_decision_log(_DECISION_LOG_PATH, self._game())

    def _broken_for_scoring_game(self):
        # A real, parseable game; the scoring chain is forced to raise via a
        # monkeypatch in the relevant tests (the scorer is lenient and does not
        # naturally raise on the witch-vocabulary mismatch). We still return a
        # real GameLog so the curtain layer is genuine.
        raw = json.loads(_GAME_LOG_PATH.read_text(encoding="utf-8"))
        return parse_game_log(raw)

    def test_full_bundle_shape(self):
        bundle = build_settlement_bundle(self._game(), self._decision_log(), run_id="r1")
        self.assertEqual(bundle["bundle_version"], "p2d.settlement.v1")
        self.assertEqual(bundle["run_id"], "r1")
        self.assertEqual(bundle["game_id"], self._game().game_id)
        self.assertFalse(bundle["degraded"])
        self.assertIsNone(bundle["degraded_reason"])
        # curtain layer
        self.assertEqual(bundle["result"]["winner"], "villager")
        self.assertEqual(
            {p["player_id"] for p in bundle["players"]},
            {"p1", "p2", "p3", "p4", "p5", "p6"},
        )
        self.assertTrue(all("role" in p and "alive" in p for p in bundle["players"]))
        # board_timeline covers every (round,phase) group, monotonic cursor_index
        bt = bundle["board_timeline"]
        self.assertEqual([n["cursor_index"] for n in bt], list(range(len(bt))))
        self.assertTrue(all("alive_player_ids" in n for n in bt))
        # battle-report layer
        self.assertEqual(
            bundle["core_metrics"]["mvp_player_id"],
            max(bundle["players"], key=lambda p: p["outcome_score"])["player_id"],
        )
        self.assertIsNotNone(bundle["top_attribution"])
        self.assertIn("description", bundle["top_attribution"])
        for tp in bundle["turning_points"]:
            self.assertIn("cursor_index", tp)
            self.assertTrue(0 <= tp["cursor_index"] < len(bt))

    def test_board_timeline_only_needs_game_log(self):
        bundle = build_settlement_bundle(self._game(), decision_log=None)
        self.assertTrue(len(bundle["board_timeline"]) >= 1)
        self.assertEqual(bundle["board_timeline"][-1]["phase"], "game_end")
        self.assertEqual(
            set(bundle["board_timeline"][-1]["alive_player_ids"]),
            set(self._game().result.survivors),
        )

    def test_degrade_missing_decision_log_is_curtain_only(self):
        bundle = build_settlement_bundle(
            self._game(), None, run_id="r1", decision_log_status="absent"
        )
        self.assertTrue(bundle["degraded"])
        self.assertEqual(bundle["degraded_reason"], "missing_decision_log")
        self.assertEqual(bundle["turning_points"], [])
        self.assertEqual(bundle["result"]["winner"], "villager")
        self.assertTrue(len(bundle["board_timeline"]) >= 1)

    def test_degrade_invalid_decision_log(self):
        bundle = build_settlement_bundle(
            self._game(), None, run_id="r1", decision_log_status="invalid"
        )
        self.assertTrue(bundle["degraded"])
        self.assertEqual(bundle["degraded_reason"], "invalid_decision_log")
        self.assertEqual(bundle["turning_points"], [])

    def test_degrade_on_scoring_error_keeps_curtain(self):
        with mock.patch(
            "werewolf_eval.settlement_bundle.score_game",
            side_effect=RuntimeError("/abs/path/scoring.py boom\nTraceback"),
        ):
            bundle = build_settlement_bundle(
                self._broken_for_scoring_game(),
                self._decision_log(),
                run_id="r1",
                decision_log_status="present",
            )
        self.assertTrue(bundle["degraded"])
        self.assertEqual(bundle["degraded_reason"], "scoring_failed")
        self.assertEqual(bundle["turning_points"], [])
        self.assertIsNone(bundle["top_attribution"])
        self.assertEqual(bundle["core_metrics"], {})
        self.assertEqual(bundle["result"]["winner"], "villager")
        self.assertTrue(len(bundle["board_timeline"]) >= 1)

    def test_degraded_reason_is_code_not_raw_exception(self):
        with mock.patch(
            "werewolf_eval.settlement_bundle.score_game",
            side_effect=RuntimeError("C:\\secret\\scoring.py boom Traceback /src/"),
        ):
            bundle = build_settlement_bundle(
                self._broken_for_scoring_game(),
                self._decision_log(),
                run_id="r1",
                decision_log_status="present",
            )
        self.assertIn(
            bundle["degraded_reason"],
            {"missing_decision_log", "invalid_decision_log", "scoring_failed"},
        )
        reason = str(bundle["degraded_reason"] or "")
        for forbidden in ["Traceback", ".py", "/", "\\", " "]:
            self.assertNotIn(forbidden, reason)

    def test_secret_free(self):
        blob = json.dumps(
            build_settlement_bundle(self._game(), self._decision_log()),
            ensure_ascii=False,
        )
        for forbidden in ["reason_summary", "prompt", "api_key", "Bearer", "sk-", "C:\\", "/src/"]:
            self.assertNotIn(forbidden, blob)

    def test_deterministic(self):
        a = build_settlement_bundle(self._game(), self._decision_log())
        b = build_settlement_bundle(self._game(), self._decision_log())
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
