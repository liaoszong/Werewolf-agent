"""Unit tests for Adapter A — the fake-deterministic emergent runtime launcher.

Pure offline (no socket, no key). Asserts: a completed game writes the full
observer spine + four logs + provider trace + redacted manifest and returns 0;
a fail-closed (budget) outcome writes ONLY the failure audit and returns 2; the
manifest never carries a real model/secret; and the default launcher conforms to
the observer's RunLauncher signature.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.consensus_log import parse_consensus_log
from werewolf_eval.decision_log import parse_decision_log
from werewolf_eval.game_log import parse_game_log
from werewolf_eval.provider_contract import FAKE_PROVIDER_SOURCE_LABEL
from werewolf_eval.run_emergent_fake_runtime import (
    default_emergent_fake_launcher,
    run_emergent_fake_runtime,
)

_SECRET_MARKERS = ["sk-", "authorization", "bearer", "api_key", "http://", "https://"]


class EmergentFakeRuntimeTests(unittest.TestCase):
    def test_completed_writes_full_spine_and_logs_that_validate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rc = run_emergent_fake_runtime(game_id="bf_ok", out_dir=out)
            self.assertEqual(rc, 0)
            for name in (
                "events.jsonl",
                "game-log.json",
                "decision-log.json",
                "consensus-log.json",
                "failure-audit.json",
                "provider-trace.json",
                "prompt-manifest.json",
            ):
                self.assertTrue((out / name).exists(), name)
            self.assertTrue(
                (out / "snapshots").is_dir() and any((out / "snapshots").glob("*.json")),
                "snapshots empty",
            )
            # logs validate against the parsers P3 scoring will use
            game = parse_game_log(json.loads((out / "game-log.json").read_text(encoding="utf-8")))
            parse_decision_log(json.loads((out / "decision-log.json").read_text(encoding="utf-8")), game)
            parse_consensus_log(json.loads((out / "consensus-log.json").read_text(encoding="utf-8")), game)

    def test_manifest_redacted_and_no_real_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_emergent_fake_runtime(game_id="bf_manifest", out_dir=out)
            manifest = json.loads((out / "prompt-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["secrets_redacted"])
            self.assertEqual(manifest["source_label"], FAKE_PROVIDER_SOURCE_LABEL)
            self.assertEqual({a["model"] for a in manifest["agents"]}, {"none"})
            # roles carried through for the settlement per-seat rollup
            self.assertEqual(len(manifest["agents"]), 6)

    def test_fail_closed_writes_only_failure_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rc = run_emergent_fake_runtime(game_id="bf_fc", out_dir=out, max_requests=3)
            self.assertEqual(rc, 2)
            self.assertTrue((out / "failure-audit.json").exists())
            self.assertFalse((out / "game-log.json").exists())
            self.assertFalse((out / "decision-log.json").exists())
            self.assertFalse((out / "consensus-log.json").exists())
            # the streamed spine stays as evidence
            self.assertTrue((out / "events.jsonl").exists())
            audit = json.loads((out / "failure-audit.json").read_text(encoding="utf-8"))
            self.assertTrue(any(f.get("kind") == "budget_exhausted" for f in audit["failures"]))

    def test_no_secrets_or_urls_in_any_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_emergent_fake_runtime(game_id="bf_secrets", out_dir=out)
            for path in out.rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace").lower()
                for marker in _SECRET_MARKERS:
                    self.assertNotIn(marker, text, f"{marker!r} in {path.name}")

    def test_default_launcher_conforms_to_runlauncher(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rc = default_emergent_fake_launcher("bf_dl", out)
            self.assertEqual(rc, 0)
            self.assertTrue((out / "events.jsonl").exists())
            self.assertTrue((out / "game-log.json").exists())

    def test_werewolf_win_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rc = run_emergent_fake_runtime(game_id="bf_ww", out_dir=out, script="werewolf_win")
            self.assertEqual(rc, 0)
            game = json.loads((out / "game-log.json").read_text(encoding="utf-8"))
            self.assertEqual(game["result"]["winner"], "werewolf")


if __name__ == "__main__":
    unittest.main()
