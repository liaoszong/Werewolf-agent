"""Unit tests for the RunManager seam (SYS-C2 split).

Function-level coverage for the run state machine that previously lived as
handler methods and was only reachable through HTTP integration tests or
in-process handler harnesses. The HTTP behavior stays pinned by
``test_observer_server.py``.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from werewolf_eval.observer.run_manager import RunManager
from werewolf_eval.observer.state import ObserverServerState
from werewolf_eval.observer_protocol import read_run_status


def _noop_launcher(run_id: str, run_dir: Path) -> int:
    return 0


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runs = Path(self._tmp.name)

    def _state(self) -> ObserverServerState:
        return ObserverServerState(runs_dir=self.runs, launcher=_noop_launcher)

    def _manager(self, state: ObserverServerState | None = None) -> RunManager:
        return RunManager(state or self._state())


class StatusDualWriteTests(_Fixture):
    def test_set_status_writes_memory_and_disk(self) -> None:
        state = self._state()
        rm = RunManager(state)
        run_dir = self.runs / "r1"
        run_dir.mkdir()
        rm.set_status("r1", "running")
        self.assertEqual(state.run_status["r1"], "running")
        self.assertEqual(read_run_status(run_dir), "running")

    def test_get_status_prefers_memory_over_disk(self) -> None:
        state = self._state()
        rm = RunManager(state)
        run_dir = self.runs / "r2"
        run_dir.mkdir()
        rm.set_status("r2", "completed")  # disk now says completed
        state.run_status["r2"] = "running"  # memory says running
        self.assertEqual(rm.get_status("r2", run_dir), "running")

    def test_get_status_falls_back_to_disk_after_restart(self) -> None:
        run_dir = self.runs / "r3"
        run_dir.mkdir()
        RunManager(self._state()).set_status("r3", "completed")
        # Fresh state simulates a server restart: memory is empty.
        fresh = RunManager(self._state())
        self.assertEqual(fresh.get_status("r3", run_dir), "completed")

    def test_error_roundtrip(self) -> None:
        rm = self._manager()
        self.assertIsNone(rm.get_error("rx"))
        rm.set_error("rx", "provider_failure")
        self.assertEqual(rm.get_error("rx"), "provider_failure")


class ExecuteRunTests(_Fixture):
    def _execute(self, run_id: str, launcher) -> RunManager:
        run_dir = self.runs / run_id
        run_dir.mkdir()
        rm = self._manager()
        rm.execute_run(run_id, run_dir, launcher)
        return rm

    def test_exit_zero_completes_without_reason(self) -> None:
        rm = self._execute("ok", lambda rid, rd: 0)
        self.assertEqual(rm.get_status("ok", self.runs / "ok"), "completed")
        self.assertIsNone(rm.get_error("ok"))

    def test_exit_three_records_budget_exhausted(self) -> None:
        rm = self._execute("b", lambda rid, rd: 3)
        self.assertEqual(rm.get_status("b", self.runs / "b"), "failed")
        self.assertEqual(rm.get_error("b"), "budget_exhausted")

    def test_other_exit_records_provider_failure(self) -> None:
        rm = self._execute("p", lambda rid, rd: 2)
        self.assertEqual(rm.get_error("p"), "provider_failure")

    def test_generic_exception_records_provider_failure(self) -> None:
        def _boom(rid: str, rd: Path) -> int:
            raise RuntimeError("kaboom")

        rm = self._execute("x", _boom)
        self.assertEqual(rm.get_status("x", self.runs / "x"), "failed")
        self.assertEqual(rm.get_error("x"), "provider_failure")

    def test_auth_exception_records_provider_auth_failed(self) -> None:
        def _denied(rid: str, rd: Path) -> int:
            raise RuntimeError("401 Unauthorized")

        rm = self._execute("a", _denied)
        self.assertEqual(rm.get_error("a"), "provider_auth_failed")

    def test_exit_zero_records_low_live_success_rate(self) -> None:
        def _simulate_run(rid: str, rd: Path) -> int:
            (rd / "provider-turns.json").write_text(json.dumps({
                "live_success_rate": 0.79,
                "live_requested_actions": 100,
                "live_success_actions": 79,
            }), encoding="utf-8")
            return 0
        rm = self._execute("low", _simulate_run)
        run_dir = self.runs / "low"
        self.assertEqual(rm.get_status("low", run_dir), "failed")
        self.assertEqual(rm.get_error("low"), "low_live_success_rate")
        
        status_data = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status_data["reason"], "low_live_success_rate")
        self.assertEqual(status_data["live_success_rate"], 0.79)


class DeleteRunTests(_Fixture):
    def test_active_run_is_never_deleted(self) -> None:
        state = self._state()
        rm = RunManager(state)
        run_dir = self.runs / "live"
        run_dir.mkdir()
        state.run_status["live"] = "running"
        code, payload = rm.delete_run("live", run_dir)
        self.assertEqual(code, 409)
        self.assertEqual(payload, {"error": "run_active"})
        self.assertTrue(run_dir.is_dir())

    def test_missing_dir_is_404(self) -> None:
        code, payload = self._manager().delete_run("ghost", self.runs / "ghost")
        self.assertEqual(code, 404)
        self.assertEqual(payload, {"error": "not_found"})

    def test_delete_evicts_in_memory_entries(self) -> None:
        state = self._state()
        rm = RunManager(state)
        run_dir = self.runs / "done"
        run_dir.mkdir()
        state.run_status["done"] = "completed"
        state.run_errors["done"] = "provider_failure"
        code, payload = rm.delete_run("done", run_dir)
        self.assertEqual(code, 200)
        self.assertEqual(payload, {"deleted": "done"})
        self.assertFalse(run_dir.exists())
        self.assertNotIn("done", state.run_status)
        self.assertNotIn("done", state.run_errors)


class RunDetailTests(_Fixture):
    def test_reason_and_execution_mode_attached(self) -> None:
        rm = self._manager()
        run_dir = self.runs / "d1"
        run_dir.mkdir()
        (run_dir / "resolved-profile.json").write_text(
            json.dumps({"execution_mode": "live"}), encoding="utf-8"
        )
        rm.set_status("d1", "failed")
        rm.set_error("d1", "budget_exhausted")
        detail = rm.run_detail_with_reason("d1", run_dir)
        self.assertEqual(detail["status"], "failed")
        self.assertEqual(detail["reason"], "budget_exhausted")
        self.assertEqual(detail["execution_mode"], "live")

    def test_no_reason_and_no_mode_when_absent(self) -> None:
        rm = self._manager()
        run_dir = self.runs / "d2"
        run_dir.mkdir()
        rm.set_status("d2", "completed")
        detail = rm.run_detail_with_reason("d2", run_dir)
        self.assertNotIn("reason", detail)
        self.assertNotIn("execution_mode", detail)


if __name__ == "__main__":
    unittest.main()
