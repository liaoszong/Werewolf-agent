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

    def test_absent_decision_log_degrades(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td, decision="absent"),
                run_status="completed",
                run_id="r1",
            )
            self.assertEqual(r["bundle"]["degraded_reason"], "missing_decision_log")

    def test_invalid_decision_log_degrades(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_settlement_response(
                self._run_dir(td, decision="broken"),
                run_status="completed",
                run_id="r1",
            )
            self.assertEqual(r["bundle"]["degraded_reason"], "invalid_decision_log")

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


if __name__ == "__main__":
    unittest.main()
