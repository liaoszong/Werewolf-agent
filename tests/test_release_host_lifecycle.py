import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


class ReleaseHostLifecycleTests(unittest.TestCase):
    def test_observer_server_exe_prefers_pyinstaller_onedir_layout(self):
        from werewolf_eval.release_host.lifecycle import _observer_server_exe

        with tempfile.TemporaryDirectory() as tmp:
            dist_root = Path(tmp)
            nested = dist_root / "runtime" / "observer-server" / "observer-server.exe"
            flat = dist_root / "runtime" / "observer-server.exe"
            nested.parent.mkdir(parents=True)
            nested.write_text("", encoding="utf-8")
            flat.write_text("", encoding="utf-8")

            self.assertEqual(_observer_server_exe(dist_root), nested)

    def test_observer_server_exe_keeps_flat_runtime_fallback(self):
        from werewolf_eval.release_host.lifecycle import _observer_server_exe

        with tempfile.TemporaryDirectory() as tmp:
            dist_root = Path(tmp)
            expected = dist_root / "runtime" / "observer-server.exe"

            self.assertEqual(_observer_server_exe(dist_root), expected)

    def test_hidden_test_update_source_requires_explicit_build_flag(self):
        from werewolf_eval.release_host.lifecycle import _test_update_source_allowed

        self.assertFalse(_test_update_source_allowed({}))
        self.assertFalse(_test_update_source_allowed({"WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE": "0"}))
        self.assertTrue(_test_update_source_allowed({"WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE": "1"}))

    def test_velopack_app_run_disables_startup_auto_apply(self):
        from werewolf_eval.release_host import velopack_runtime

        calls: list[tuple[str, object]] = []

        class FakeApp:
            def set_auto_apply_on_startup(self, apply):
                calls.append(("set_auto_apply_on_startup", apply))
                return self

            def run(self):
                calls.append(("run", None))

        with mock.patch.object(
            velopack_runtime,
            "_APP_RUN_CALLED",
            False,
        ), mock.patch.dict(
            "sys.modules",
            {"velopack": SimpleNamespace(App=FakeApp)},
        ):
            velopack_runtime.run_velopack_app_once()

        self.assertEqual(calls, [("set_auto_apply_on_startup", False), ("run", None)])


if __name__ == "__main__":
    unittest.main()
