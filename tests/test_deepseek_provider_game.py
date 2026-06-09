from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from werewolf_eval.deepseek_provider import DeepSeekProviderConfig
from werewolf_eval.game_log import load_game_log, validate_game_log
from werewolf_eval.decision_log import load_decision_log, validate_decision_log
from werewolf_eval.run_deepseek_provider_game import (
    run_deepseek_game_with_provider_factory,
)


class _FakeDeepSeekProvider:
    """Deterministic fake DeepSeek provider that returns valid JSON."""

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
        target = request.allowed_targets[0] if request.allowed_targets else request.actor

        raw = json.dumps({
            "action": action,
            "target": target,
            "reason_summary": "auto",
            "decision_type": "inference_based",
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


class DeepSeekProviderGameCliTests(unittest.TestCase):
    def test_cli_without_allow_live_api_exits_nonzero_and_writes_nothing(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "werewolf_eval.run_deepseek_provider_game"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live_api=disabled", result.stdout)
        self.assertIn("game_log=not_written", result.stdout)
        self.assertIn("decision_log=not_written", result.stdout)

    def test_cli_with_allow_live_but_missing_key_exits_nonzero_and_writes_nothing(
        self,
    ) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.run_deepseek_provider_game",
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

    def test_helper_with_fake_provider_factory_writes_valid_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            exit_code = run_deepseek_game_with_provider_factory(
                game_id="g1e_test",
                out_dir=out_dir,
                provider_factory=_fake_provider_factory,
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue((out_dir / "game-log.json").exists())
            self.assertTrue((out_dir / "decision-log.json").exists())
            self.assertTrue((out_dir / "provider-trace.json").exists())
            self.assertTrue((out_dir / "failure-audit.json").exists())

            game_log = json.loads((out_dir / "game-log.json").read_text(encoding="utf-8"))
            self.assertIn("game_id", game_log)
            self.assertEqual(game_log["game_id"], "g1e_test")

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

            failure_audit = json.loads(
                (out_dir / "failure-audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(failure_audit["failures"], [])

    def test_helper_failure_writes_failure_audit_but_no_valid_logs(self) -> None:
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            exit_code = run_deepseek_game_with_provider_factory(
                game_id="g1e_test_fail",
                out_dir=out_dir,
                provider_factory=_failing_provider_factory,
            )
            self.assertEqual(exit_code, 2)
            self.assertFalse((out_dir / "game-log.json").exists())
            self.assertFalse((out_dir / "decision-log.json").exists())
            self.assertTrue((out_dir / "provider-trace.json").exists())
            self.assertTrue((out_dir / "failure-audit.json").exists())

            failure_audit = json.loads(
                (out_dir / "failure-audit.json").read_text(encoding="utf-8")
            )
            self.assertGreater(len(failure_audit["failures"]), 0)


class _SecretEchoingProvider(_FakeDeepSeekProvider):
    """Returns a valid action but echoes a secret-looking token in an EXTRA
    raw_content field the action parser ignores. The token therefore lands only
    in ProviderResponse.raw_content (the provider trace), not in the parsed
    decision-log — isolating the provider-trace redaction behaviour."""

    SECRET = "Authorization: Bearer sk-LEAKED-INTO-RAW-CONTENT-0123456789"

    def respond(self, request: Any) -> Any:
        from werewolf_eval.provider_contract import ProviderResponse

        self.requests.append(request)
        action = request.allowed_actions[0] if request.allowed_actions else "player_vote"
        target = request.allowed_targets[0] if request.allowed_targets else request.actor
        raw = json.dumps({
            "action": action,
            "target": target,
            "reason_summary": "auto",
            "decision_type": "inference_based",
            "confidence": 1.0,
            "debug_echo": self.SECRET,
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


def _secret_provider_factory(player_id: str) -> Any:
    from werewolf_eval.provider_agent import ProviderAgent

    return ProviderAgent(player_id, _SecretEchoingProvider())


class ProviderTraceRedactionTests(unittest.TestCase):
    def test_provider_trace_is_redacted_before_write(self) -> None:
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            code = run_deepseek_game_with_provider_factory(
                game_id="g1e_redact",
                out_dir=out_dir,
                provider_factory=_secret_provider_factory,
            )
            self.assertEqual(code, 0)
            trace_text = (out_dir / "provider-trace.json").read_text(encoding="utf-8")
            # The secret must not survive into the on-disk trace; redaction replaces it.
            self.assertNotIn("sk-LEAKED-INTO-RAW-CONTENT", trace_text)
            self.assertNotIn("Bearer sk-", trace_text)
            self.assertIn("<REDACTED>", trace_text)


if __name__ == "__main__":
    unittest.main()
