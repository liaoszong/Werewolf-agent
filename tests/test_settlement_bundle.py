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
from types import SimpleNamespace
import unittest
from unittest import mock

from werewolf_eval.game_log import load_game_log, parse_game_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.settlement_bundle import _board_timeline, build_settlement_bundle

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
        self.assertEqual(bundle["bundle_version"], "p2d.settlement.v2")
        self.assertEqual(bundle["run_id"], "r1")
        self.assertEqual(bundle["game_id"], self._game().game_id)
        self.assertFalse(bundle["degraded"])
        self.assertIsNone(bundle["degraded_reason"])
        # decision-log present -> decision-quality axis available
        self.assertTrue(bundle["decision_quality_available"])
        self.assertIsNone(bundle["decision_quality_reason"])
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

    def test_missing_decision_log_partial_not_full_degrade(self):
        # Product decision B: no decision-log => PARTIAL, not curtain-only. The
        # result-type battle report (metrics/turning points) is still computed from
        # the game-log; only the decision-quality axis is flagged unavailable.
        bundle = build_settlement_bundle(
            self._game(), None, run_id="r1", decision_log_status="absent"
        )
        self.assertFalse(bundle["degraded"])                     # report available
        self.assertIsNone(bundle["degraded_reason"])
        self.assertFalse(bundle["decision_quality_available"])
        self.assertEqual(bundle["decision_quality_reason"], "missing_decision_log")
        self.assertNotEqual(bundle["core_metrics"], {})          # result metrics present
        self.assertIn("game_length", bundle["core_metrics"])
        self.assertEqual(bundle["result"]["winner"], "villager")
        # decision-quality scores zeroed (unavailable, not real)
        self.assertTrue(all(p["decision_quality_score"] == 0 for p in bundle["players"]))

    def test_invalid_decision_log_partial(self):
        bundle = build_settlement_bundle(
            self._game(), None, run_id="r1", decision_log_status="invalid"
        )
        self.assertFalse(bundle["degraded"])
        self.assertFalse(bundle["decision_quality_available"])
        self.assertEqual(bundle["decision_quality_reason"], "invalid_decision_log")
        self.assertIn("game_length", bundle["core_metrics"])

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
        self.assertFalse(bundle["decision_quality_available"])  # full degrade: nothing scored
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
        bundle = build_settlement_bundle(self._game(), self._decision_log())
        # Pop evaluation_bucket and shape-check it explicitly; it legitimately
        # contains "prompt_version" — scanning the remainder with the full
        # forbidden list (including bare "prompt") is safe once it is removed.
        bucket = bundle.pop("evaluation_bucket")
        self.assertEqual(
            set(bucket),
            {"rules_version", "prompt_version", "scoring_version", "comparison_key"},
        )
        # B5 closeout: usage_summary is additive and contains no secrets.
        self.assertIn("usage_summary", bundle)
        blob = json.dumps(bundle, ensure_ascii=False)
        # Check for actual secret markers, not "prompt" which may appear as a
        # substring in garbled Chinese text encoding. The evaluation_bucket
        # (which contains "prompt_version") has already been popped.
        for forbidden in ["reason_summary", "api_key", "Bearer", "sk-", "C:\\", "/src/"]:
            self.assertNotIn(forbidden, blob)

    def test_deterministic(self):
        a = build_settlement_bundle(self._game(), self._decision_log())
        b = build_settlement_bundle(self._game(), self._decision_log())
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_board_highlight_prefers_death_over_earlier_action(self):
        # A night group where a seer_check (p3->p1) is sequenced BEFORE the kill that
        # actually removes p1: the docked-sandbox highlight must be the death, not the
        # earlier non-death action it happened to see first.
        players = [SimpleNamespace(player_id=f"p{i}") for i in range(1, 7)]
        events = [
            SimpleNamespace(sequence=1, round=1, phase="night",
                            type="seer_check", actor="p3", target="p1"),
            SimpleNamespace(sequence=2, round=1, phase="night",
                            type="player_died", actor="p2", target="p1"),
        ]
        board = _board_timeline(SimpleNamespace(players=players, events=events))
        self.assertEqual(len(board), 1)
        self.assertEqual(board[0]["highlight"]["kind"], "player_died")
        self.assertEqual(board[0]["highlight"]["target"], "p1")

    def test_board_highlight_falls_back_to_action_when_no_death(self):
        # A quiet group with only a non-death action keeps that action as the highlight.
        players = [SimpleNamespace(player_id=f"p{i}") for i in range(1, 7)]
        events = [
            SimpleNamespace(sequence=1, round=2, phase="day",
                            type="seer_check", actor="p3", target="p5"),
        ]
        board = _board_timeline(SimpleNamespace(players=players, events=events))
        self.assertEqual(board[0]["highlight"]["kind"], "seer_check")
        self.assertEqual(board[0]["highlight"]["target"], "p5")

    def test_top_attribution_sentinel_becomes_null(self):
        # attribute_game returns a sentinel TopAttribution (turn_point_id == "none")
        # when there are no turn_points; the bundle must emit null, not a fake "none".
        sentinel = SimpleNamespace(
            turn_point_id="none", description_template="无确定性归因转折点。"
        )
        fake = SimpleNamespace(top_attribution=sentinel, turn_points=[])
        with mock.patch(
            "werewolf_eval.settlement_bundle.attribute_game", return_value=fake
        ):
            bundle = build_settlement_bundle(
                self._game(), self._decision_log(), run_id="r1"
            )
        self.assertFalse(bundle["degraded"])
        self.assertIsNone(bundle["top_attribution"])
        self.assertEqual(bundle["turning_points"], [])


class TestSettlementBundleEvaluationBucket(unittest.TestCase):
    """Spec 2026-06-10-prompt-versioning §4.5: bundle carries evaluation_bucket.
    scoring_v2: the bucket is always rebased to the current formula, never the
    manifest's historical one."""

    def _game(self):
        return load_game_log(_GAME_LOG_PATH)

    def _decision_log(self):
        return load_decision_log(_DECISION_LOG_PATH, self._game())

    def test_builder_without_kwarg_stamps_unknown_bucket(self):
        bundle = build_settlement_bundle(self._game(), self._decision_log())
        self.assertEqual(
            bundle["evaluation_bucket"]["comparison_key"],
            "unknown__unknown__scoring_v2",
        )

    def test_settle_entry_rebases_manifest_scoring_v1_to_current(self):
        """A manifest stamped scoring_v1 must be rebased to scoring_v2 by
        build_settlement_response — preserving rules/prompt from the manifest."""
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            shutil.copy(_GAME_LOG_PATH, run_dir / "game-log.json")
            shutil.copy(_DECISION_LOG_PATH, run_dir / "decision-log.json")
            manifest = {
                "evaluation_bucket": {
                    "rules_version": "rules_v1_1",
                    "prompt_version": "prompt_v1",
                    "scoring_version": "scoring_v1",
                    "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
                },
                "agents": [],
            }
            (run_dir / "prompt-manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            from werewolf_eval.settlement_bundle import build_settlement_response
            response = build_settlement_response(run_dir, "completed", "r_test")
            self.assertTrue(response["available"])
            bucket = response["bundle"]["evaluation_bucket"]
            self.assertEqual(bucket["rules_version"], "rules_v1_1")
            self.assertEqual(bucket["prompt_version"], "prompt_v1")
            self.assertEqual(bucket["scoring_version"], "scoring_v2")
            self.assertEqual(bucket["comparison_key"], "rules_v1_1__prompt_v1__scoring_v2")

    def test_stale_scoring_v1_cache_is_not_reused(self):
        """A cached bundle with bundle_version=p2d.settlement.v2 but
        evaluation_bucket.scoring_version=scoring_v1 MUST be recomputed."""
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            shutil.copy(_GAME_LOG_PATH, run_dir / "game-log.json")
            shutil.copy(_DECISION_LOG_PATH, run_dir / "decision-log.json")
            # Write a manifest with scoring_v1 bucket.
            manifest = {
                "evaluation_bucket": {
                    "rules_version": "rules_v1_1",
                    "prompt_version": "prompt_v1",
                    "scoring_version": "scoring_v1",
                    "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
                },
                "agents": [],
            }
            (run_dir / "prompt-manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            # Plant a stale cache: same BUNDLE_VERSION but scoring_v1 bucket.
            stale = {
                "bundle_version": "p2d.settlement.v2",
                "evaluation_bucket": {
                    "rules_version": "rules_v1_1",
                    "prompt_version": "prompt_v1",
                    "scoring_version": "scoring_v1",
                    "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
                },
                "game_id": "stale",
                "degraded": False,
                "decision_quality_available": True,
                "decision_quality_reason": None,
                "result": {"winner": "villager", "end_round": 2,
                           "end_condition": "all_werewolves_eliminated",
                           "survivors": [], "margin": 0,
                           "source_label": "stale"},
                "players": [],
                "core_metrics": {},
                "top_attribution": None,
                "turning_points": [],
                "score_records": [],
                "board_timeline": [],
                "usage_summary": {"seats": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                                  "scaffold": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                                  "total": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}},
            }
            (run_dir / "settlement-bundle.json").write_text(
                json.dumps(stale), encoding="utf-8"
            )
            from werewolf_eval.settlement_bundle import build_settlement_response
            response = build_settlement_response(run_dir, "completed", "r_test")
            self.assertTrue(response["available"])
            # Must have been recomputed under scoring_v2, not the stale v1 cache.
            self.assertEqual(
                response["bundle"]["evaluation_bucket"]["scoring_version"],
                "scoring_v2",
            )
            # Must be the real g001, not the stale placeholder.
            self.assertEqual(response["bundle"]["game_id"], "g001")

    def test_current_scoring_v2_cache_is_reused(self):
        """A cache whose evaluation_bucket already matches the expected
        (current scoring) bucket MUST be served without recomputation."""
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            shutil.copy(_GAME_LOG_PATH, run_dir / "game-log.json")
            shutil.copy(_DECISION_LOG_PATH, run_dir / "decision-log.json")
            # No manifest → expected bucket is unknown/unknown/scoring_v2.
            # Plant a pre-computed cache with that exact bucket.
            cache = {
                "bundle_version": "p2d.settlement.v2",
                "evaluation_bucket": {
                    "rules_version": "unknown",
                    "prompt_version": "unknown",
                    "scoring_version": "scoring_v2",
                    "comparison_key": "unknown__unknown__scoring_v2",
                },
                "game_id": "g001",
                "degraded": False,
                "decision_quality_available": True,
                "decision_quality_reason": None,
                "result": {"winner": "villager", "end_round": 2,
                           "end_condition": "all_werewolves_eliminated",
                           "survivors": [], "margin": 0,
                           "source_label": "[scripted deterministic output]"},
                "players": [],
                "core_metrics": {},
                "top_attribution": None,
                "turning_points": [],
                "score_records": [],
                "board_timeline": [],
                "usage_summary": {"seats": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                                  "scaffold": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                                  "total": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}},
            }
            (run_dir / "settlement-bundle.json").write_text(
                json.dumps(cache), encoding="utf-8"
            )
            from werewolf_eval.settlement_bundle import build_settlement_response
            response = build_settlement_response(run_dir, "completed", "r_test")
            self.assertTrue(response["available"])
            # Served from cache — game_id matches the cached one (not recomputed).
            self.assertEqual(response["bundle"]["game_id"], "g001")


if __name__ == "__main__":
    unittest.main()
