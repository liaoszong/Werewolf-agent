"""Gated wrapper for the manual DeepSeek live smoke (G3-1).

By default the live test SKIPS — the skip gate reads ONLY
``RUN_DEEPSEEK_LIVE_SMOKE`` (evaluated at discovery); ``DEEPSEEK_API_KEY`` is
read only INSIDE the test body after the gate opens.  The default suite never
reads the key and never hits the network.
"""

from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_SMOKE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "dev" / "run_deepseek_live_smoke.py"
)


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("run_deepseek_live_smoke", _SMOKE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DeepSeekLiveSmokeGateClosedTests(unittest.TestCase):
    """Default-suite-safe: with the gate closed, main() is a key-free no-op."""

    def test_gate_closed_is_noop_and_reads_no_key(self) -> None:
        import io
        import sys
        from contextlib import redirect_stdout

        mod = _load_smoke_module()
        saved_argv = sys.argv
        saved_gate = os.environ.pop("RUN_DEEPSEEK_LIVE_SMOKE", None)
        try:
            sys.argv = ["run_deepseek_live_smoke.py"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = mod.main()
            self.assertEqual(code, 0)
            self.assertIn("smoke=skipped", buf.getvalue())
        finally:
            sys.argv = saved_argv
            if saved_gate is not None:
                os.environ["RUN_DEEPSEEK_LIVE_SMOKE"] = saved_gate


class SmokeManifestModelHelperTests(unittest.TestCase):
    """Offline (un-gated): the smoke's manifest-model honesty check (G3-3) — no
    key, no network.  Pins that the real smoke fails if the manifest records the
    legacy ``"unknown"`` instead of the configured model."""

    @staticmethod
    def _write_manifest(run_dir: Path, models: list[str]) -> None:
        (run_dir / "prompt-manifest.json").write_text(
            json.dumps({"agents": [
                {"player_id": f"p{i}", "provider": "deepseek", "model": m}
                for i, m in enumerate(models, start=1)
            ]}),
            encoding="utf-8",
        )

    def test_true_when_all_agents_match(self) -> None:
        mod = _load_smoke_module()
        with TemporaryDirectory() as tmp:
            rd = Path(tmp)
            self._write_manifest(rd, ["deepseek-chat"] * 6)
            self.assertTrue(mod._manifest_model_honest(rd, "deepseek-chat"))

    def test_false_when_any_agent_is_unknown(self) -> None:
        mod = _load_smoke_module()
        with TemporaryDirectory() as tmp:
            rd = Path(tmp)
            self._write_manifest(rd, ["deepseek-chat"] * 5 + ["unknown"])
            self.assertFalse(mod._manifest_model_honest(rd, "deepseek-chat"))

    def test_false_when_manifest_missing(self) -> None:
        mod = _load_smoke_module()
        with TemporaryDirectory() as tmp:
            self.assertFalse(mod._manifest_model_honest(Path(tmp), "deepseek-chat"))


@unittest.skipUnless(
    os.environ.get("RUN_DEEPSEEK_LIVE_SMOKE") == "1", "live smoke disabled"
)
class DeepSeekLiveSmokeTests(unittest.TestCase):
    def test_live_smoke_structural_success(self) -> None:
        # Reached only when the gate is open; the key is read HERE, never at
        # discovery.  Asserts structural success only — no model text.
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            self.skipTest("no DEEPSEEK_API_KEY")
        mod = _load_smoke_module()
        result = mod.run_live_smoke(api_key=api_key)
        self.assertTrue(result["passed"], result.get("checks"))
        self.assertGreaterEqual(result["real_response_count"], 1)


if __name__ == "__main__":
    unittest.main()
