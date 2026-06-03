from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from werewolf_eval.game_log import load_game_log, validate_game_log
from werewolf_eval.decision_log import load_decision_log, validate_decision_log
from werewolf_eval.run_deepseek_consensus_game import (
    run_deepseek_consensus_game_with_provider_factory,
)
from werewolf_eval.runtime_events import read_events_jsonl


class _FakeDeepSeekProvider:
    """Deterministic fake DeepSeek provider for consensus smoke tests."""

    def __init__(self, fail: bool = False) -> None:
        self._fail = fail
        self.requests: list = []
        self.responses: list = []

    def respond(self, request: Any) -> Any:
        from werewolf_eval.provider_contract import ProviderResponse

        self.requests.append(request)

        if self._fail:
            raise RuntimeError("simulated provider failure")

        action = request.allowed_actions[0] if request.allowed_actions else "player_vote"

        # Choose a target: prefer the first non-werewolf alive player for
        # werewolf kill actions so the engine validation accepts it.
        obs = request.observation
        role = obs.get("role", "")
        phase = obs.get("phase", "")
        if role == "werewolf" and phase == "night":
            target = "p5" if 1 in (request.round,) else "p3"
        else:
            target = request.allowed_targets[0] if request.allowed_targets else request.actor

        raw = json.dumps({
            "action": action,
            "target": target,
            "reason_summary": "auto",
            "decision_type": "team_coordinated" if role == "werewolf" and phase == "night" else "inference_based",
            "confidence": 1.0,
        })

        response = ProviderResponse(
            request_id=request.request_id,
            provider_name="deepseek",
            source_label="[DeepSeek API output]",
            raw_content=raw,
            latency_ms=100,
            token_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        self.responses.append(response)
        return response


def _fake_provider_factory(player_id: str) -> Any:
    from werewolf_eval.provider_agent import ProviderAgent

    provider = _FakeDeepSeekProvider()
    return ProviderAgent(player_id, provider)


def _failing_provider_factory(player_id: str) -> Any:
    from werewolf_eval.provider_agent import ProviderAgent

    provider = _FakeDeepSeekProvider(fail=True)
    return ProviderAgent(player_id, provider)


class DeepSeekConsensusGameCliTests(unittest.TestCase):
    def test_cli_without_allow_live_api_exits_nonzero_and_writes_nothing(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "werewolf_eval.run_deepseek_consensus_game"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live_api=disabled", result.stdout)
        self.assertIn("game_log=not_written", result.stdout)
        self.assertIn("decision_log=not_written", result.stdout)
        self.assertIn("consensus_log=not_written", result.stdout)

    def test_cli_with_allow_live_but_missing_key_exits_nonzero_and_writes_nothing(
        self,
    ) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.run_deepseek_consensus_game",
                "--allow-live-api",
                "--api-key-env",
                "DOES_NOT_EXIST_XXXX",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DOES_NOT_EXIST_XXXX", result.stderr)
        self.assertIn("game_log=not_written", result.stdout)
        self.assertIn("decision_log=not_written", result.stdout)
        self.assertIn("consensus_log=not_written", result.stdout)

    def test_helper_with_fake_provider_factory_writes_consensus_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            exit_code = run_deepseek_consensus_game_with_provider_factory(
                game_id="g1f_test",
                out_dir=out_dir,
                provider_factory=_fake_provider_factory,
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue((out_dir / "game-log.json").exists())
            self.assertTrue((out_dir / "decision-log.json").exists())
            self.assertTrue((out_dir / "consensus-log.json").exists())
            self.assertTrue((out_dir / "provider-trace.json").exists())
            self.assertTrue((out_dir / "failure-audit.json").exists())

            game_log = json.loads((out_dir / "game-log.json").read_text(encoding="utf-8"))
            self.assertIn("game_id", game_log)
            self.assertEqual(game_log["game_id"], "g1f_test")

            parsed_game = load_game_log(out_dir / "game-log.json")
            validate_game_log(parsed_game)

            decision_log = json.loads(
                (out_dir / "decision-log.json").read_text(encoding="utf-8")
            )
            self.assertIn("decisions", decision_log)

            parsed_decision = load_decision_log(
                out_dir / "decision-log.json", parsed_game
            )
            validate_decision_log(parsed_decision, parsed_game)

            consensus_log = json.loads(
                (out_dir / "consensus-log.json").read_text(encoding="utf-8")
            )
            self.assertIn("consensuses", consensus_log)
            self.assertGreater(len(consensus_log["consensuses"]), 0)
            first = consensus_log["consensuses"][0]
            self.assertEqual(first["participants"], ["p1", "p2"])
            self.assertEqual(first["final_decision"]["target"], "p5")

            failure_audit = json.loads(
                (out_dir / "failure-audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(failure_audit["failures"], [])

    def test_helper_provider_failure_writes_trace_and_failure_audit_but_no_valid_logs(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            exit_code = run_deepseek_consensus_game_with_provider_factory(
                game_id="g1f_test_fail",
                out_dir=out_dir,
                provider_factory=_failing_provider_factory,
            )
            self.assertEqual(exit_code, 2)
            self.assertFalse((out_dir / "game-log.json").exists())
            self.assertFalse((out_dir / "decision-log.json").exists())
            self.assertFalse((out_dir / "consensus-log.json").exists())
            self.assertTrue((out_dir / "provider-trace.json").exists())
            self.assertTrue((out_dir / "failure-audit.json").exists())

            failure_audit = json.loads(
                (out_dir / "failure-audit.json").read_text(encoding="utf-8")
            )
            self.assertGreater(len(failure_audit["failures"]), 0)

    def test_helper_with_runtime_spine_writes_events_and_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            exit_code = run_deepseek_consensus_game_with_provider_factory(
                game_id="g1h_test_spine",
                out_dir=out_dir,
                provider_factory=_fake_provider_factory,
                write_runtime_spine=True,
            )
            self.assertEqual(exit_code, 0)

            self.assertTrue((out_dir / "events.jsonl").exists())
            self.assertTrue((out_dir / "prompt-manifest.json").exists())
            self.assertTrue((out_dir / "snapshots").is_dir())
            snapshot_files = list((out_dir / "snapshots").glob("*.json"))
            self.assertGreater(len(snapshot_files), 0)

            events = read_events_jsonl(out_dir / "events.jsonl")
            self.assertGreater(len(events), 0)
            seqs = [int(e["seq"]) for e in events]
            self.assertEqual(seqs, sorted(seqs))

            manifest = json.loads(
                (out_dir / "prompt-manifest.json").read_text(encoding="utf-8")
            )
            self.assertTrue(manifest.get("secrets_redacted"))

            self.assertTrue((out_dir / "game-log.json").exists())
            self.assertTrue((out_dir / "decision-log.json").exists())
            self.assertTrue((out_dir / "consensus-log.json").exists())
            self.assertTrue((out_dir / "provider-trace.json").exists())
            self.assertTrue((out_dir / "failure-audit.json").exists())

            parsed_game = load_game_log(out_dir / "game-log.json")
            validate_game_log(parsed_game)

    def test_cli_write_runtime_spine_without_allow_live_api_exits_nonzero(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.run_deepseek_consensus_game",
                "--write-runtime-spine",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live_api=disabled", result.stdout)
        self.assertIn("game_log=not_written", result.stdout)
        self.assertIn("decision_log=not_written", result.stdout)
        self.assertIn("consensus_log=not_written", result.stdout)


if __name__ == "__main__":
    unittest.main()
