"""Pure-logic tests for DELETE /api/runs/{run_id} (no HTTP — mirrors
tests/test_observer_credentials_endpoint.py's pattern for the same reason:
localhost HTTP is blocked in the agent environment)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.observer_server import _run_delete_result


class RunDeleteResultTests(unittest.TestCase):
    def _mk_run(self, root: Path, run_id: str) -> Path:
        d = root / run_id
        (d / "snapshots").mkdir(parents=True)
        (d / "game-log.json").write_text("{}", encoding="utf-8")
        return d

    def test_completed_run_is_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            status, payload = _run_delete_result(d, "r1", "completed")
            self.assertEqual((status, payload), (200, {"deleted": "r1"}))
            self.assertFalse(d.exists())

    def test_failed_run_is_deletable(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            self.assertEqual(_run_delete_result(d, "r1", "failed")[0], 200)

    def test_running_run_is_refused_409(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            status, payload = _run_delete_result(d, "r1", "running")
            self.assertEqual(status, 409)
            self.assertEqual(payload["error"], "run_active")
            self.assertTrue(d.exists())          # nothing deleted

    def test_queued_run_is_refused_409(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            self.assertEqual(_run_delete_result(d, "r1", "queued")[0], 409)

    def test_missing_dir_is_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = _run_delete_result(Path(tmp) / "ghost", "ghost", "unknown")
            self.assertEqual(status, 404)
            self.assertEqual(payload["error"], "not_found")

    @unittest.skipUnless(sys.platform == "win32", "Windows lock semantics")
    def test_rmtree_failure_is_500_not_fake_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._mk_run(Path(tmp), "r1")
            # Hold a file open WITHOUT delete-sharing so rmtree fails on Windows.
            f = open(d / "game-log.json", "r", encoding="utf-8")  # noqa: SIM115
            try:
                status, payload = _run_delete_result(d, "r1", "completed")
                self.assertEqual(status, 500)
                self.assertEqual(payload["error"], "delete_failed")
            finally:
                f.close()


if __name__ == "__main__":
    unittest.main()
