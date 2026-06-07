"""P2-D Task 2: offline route logic for GET /api/runs/{id}/settlement.

`build_settlement_response(run_dir, run_status, run_id)` is filesystem-only (no
socket), so the route branches (completed gate / no-game-log / decision-log
status / lazy cache) are tested here directly. The real HTTP route is a 2-line
wrapper over this; localhost HTTP server-route tests are env-blocked.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from werewolf_eval.settlement_bundle import build_settlement_response

_GOLD = Path(__file__).resolve().parent.parent / "docs" / "gold-game"
_GAME_JSON = (_GOLD / "g001-game-log.json").read_text(encoding="utf-8")
_DECISION_JSON = (_GOLD / "g001-decision-log.json").read_text(encoding="utf-8")


class TestBuildSettlementResponse(unittest.TestCase):
    def _run_dir(self, td, *, game=True, decision="valid"):
        d = Path(td)
        if game:
            (d / "game-log.json").write_text(_GAME_JSON, encoding="utf-8")
        if decision == "valid":
            (d / "decision-log.json").write_text(_DECISION_JSON, encoding="utf-8")
        elif decision == "broken":
            (d / "decision-log.json").write_text("{ not json", encoding="utf-8")
        # decision == "absent": no file
        return d

    def test_not_completed(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td), run_status="running", run_id="r1"
            )
            self.assertEqual(r, {"available": False, "reason": "not_completed"})

    def test_no_game_log(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td, game=False), run_status="completed", run_id="r1"
            )
            self.assertEqual(r["available"], False)
            self.assertEqual(r["reason"], "no_game_log")

    def test_failed_run_no_settlement(self):
        # failed run with game-log still does not settle (gate is on status).
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td), run_status="failed", run_id="r1"
            )
            self.assertEqual(r, {"available": False, "reason": "not_completed"})

    def test_completed_full_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td), run_status="completed", run_id="r1"
            )
            self.assertTrue(r["available"])
            self.assertEqual(r["bundle"]["run_id"], "r1")
            self.assertFalse(r["bundle"]["degraded"])

    def test_absent_decision_log_partial(self):
        # Product decision B: missing decision-log => partial (report available),
        # not full degrade.
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td, decision="absent"),
                run_status="completed",
                run_id="r1",
            )
            self.assertFalse(r["bundle"]["degraded"])
            self.assertFalse(r["bundle"]["decision_quality_available"])
            self.assertEqual(
                r["bundle"]["decision_quality_reason"], "missing_decision_log"
            )
            self.assertIn("game_length", r["bundle"]["core_metrics"])

    def test_invalid_decision_log_partial(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td, decision="broken"),
                run_status="completed",
                run_id="r1",
            )
            self.assertFalse(r["bundle"]["degraded"])
            self.assertFalse(r["bundle"]["decision_quality_available"])
            self.assertEqual(
                r["bundle"]["decision_quality_reason"], "invalid_decision_log"
            )

    def test_cache_write_then_read(self):
        with tempfile.TemporaryDirectory() as td:
            d = self._run_dir(td)
            build_settlement_response(d, run_status="completed", run_id="r1")
            self.assertTrue((d / "settlement-bundle.json").exists())  # cached
            # second call reads cache: mutate the cache, confirm the response
            # reflects it (proves no recompute).
            (d / "settlement-bundle.json").write_text(
                '{"bundle_version":"cached_marker"}', encoding="utf-8"
            )
            r2 = build_settlement_response(d, run_status="completed", run_id="r1")
            self.assertEqual(r2["bundle"]["bundle_version"], "cached_marker")

    def test_partial_bundle_is_not_cached_and_recovers(self):
        # An INCOMPLETE bundle (partial: no decision-log yet) must NOT be persisted, so
        # once the decision-log lands a later request recomputes the COMPLETE bundle
        # instead of serving the frozen partial one forever.
        with tempfile.TemporaryDirectory() as td:
            d = self._run_dir(td, decision="absent")
            r1 = build_settlement_response(d, run_status="completed", run_id="r1")
            self.assertFalse(r1["bundle"]["degraded"])                  # partial, not full degrade
            self.assertFalse(r1["bundle"]["decision_quality_available"])
            self.assertFalse((d / "settlement-bundle.json").exists())   # not cached
            # decision-log now appears -> recompute, complete bundle, then cached.
            (d / "decision-log.json").write_text(_DECISION_JSON, encoding="utf-8")
            r2 = build_settlement_response(d, run_status="completed", run_id="r1")
            self.assertTrue(r2["bundle"]["decision_quality_available"])
            self.assertTrue((d / "settlement-bundle.json").exists())

    def test_corrupt_cache_self_heals(self):
        # A truncated/partial cache file must not crash the route — it recomputes.
        with tempfile.TemporaryDirectory() as td:
            d = self._run_dir(td)
            (d / "settlement-bundle.json").write_text("{ truncated", encoding="utf-8")
            r = build_settlement_response(d, run_status="completed", run_id="r1")
            self.assertTrue(r["available"])
            self.assertEqual(r["bundle"]["run_id"], "r1")
            self.assertFalse(r["bundle"]["degraded"])

    def test_invalid_game_log_returns_reason(self):
        # A malformed game-log degrades to an available:False reason, not an exception.
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "game-log.json").write_text("{ not a game log", encoding="utf-8")
            r = build_settlement_response(d, run_status="completed", run_id="r1")
            self.assertEqual(r["available"], False)
            self.assertEqual(r["reason"], "invalid_game_log")


if __name__ == "__main__":
    unittest.main()
