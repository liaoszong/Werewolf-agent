"""Tests for G1h runtime event spine instrumentation.

Covers :class:`werewolf_eval.provider_agent.ProviderAgent` lifecycle events
and later :class:`werewolf_eval.game_engine.EngineOutputs` runtime events.

Only fake / deterministic providers are used — no network calls.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from werewolf_eval.game_engine import (
    AgentObservation,
    GameEngine,
    build_default_config,
)
from werewolf_eval.provider_agent import ProviderActionError, ProviderAgent
from werewolf_eval.provider_contract import ProviderRequest, ProviderResponse
from werewolf_eval.runtime_events import RuntimeEventWriter, read_events_jsonl
from werewolf_eval.game_log import load_game_log, validate_game_log
from werewolf_eval.decision_log import load_decision_log, validate_decision_log
from werewolf_eval.consensus_log import load_consensus_log, validate_consensus_log


class _FakeProvider:
    """A minimal fake provider that returns configurable responses."""

    def __init__(
        self,
        *,
        raw_content: str | None = None,
        provider_name: str = "test_fake_provider",
        source_label: str = "[deterministic fake provider output]",
        raise_on_respond: Exception | None = None,
    ) -> None:
        self._raw_content = raw_content
        self._provider_name = provider_name
        self._source_label = source_label
        self._raise_on_respond = raise_on_respond

    def respond(self, request: ProviderRequest) -> ProviderResponse:
        if self._raise_on_respond is not None:
            raise self._raise_on_respond
        return ProviderResponse(
            request_id=request.request_id,
            provider_name=self._provider_name,
            source_label=self._source_label,
            raw_content=self._raw_content or "{}",
            latency_ms=0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )


def _observation(
    player_id: str = "p1",
    game_id: str = "test_g1h",
    role: str = "seer",
    team: str = "villager",
    phase: str = "night",
    round_num: int = 1,
) -> AgentObservation:
    return AgentObservation(
        game_id=game_id,
        player_id=player_id,
        role=role,
        team=team,
        phase=phase,
        round=round_num,
        alive_players=["p1", "p2", "p3", "p4"],
        public_event_ids=[],
        private_event_ids=[],
        known_roles={},
    )


def _valid_action_json(action: str = "seer_check", target: str = "p2") -> str:
    return json.dumps(
        {
            "action": action,
            "target": target,
            "reason_summary": "testing",
            "decision_type": "inference_based",
            "confidence": 1.0,
        },
        ensure_ascii=False,
    )


class ProviderLifecycleEventTests(TestCase):
    """Tests for ProviderAgent lifecycle event emissions."""

    def test_successful_provider_decision_emits_request_response_parse_success(
        self,
    ) -> None:
        """A successful decide() cycle must emit request_prepared,
        response_received, and parse_succeeded events."""
        with TemporaryDirectory() as tmp:
            writer = RuntimeEventWriter("test", Path(tmp), clock=lambda: "T")
            provider = _FakeProvider(raw_content=_valid_action_json())
            agent = ProviderAgent("p1", provider, runtime_events=writer)

            result = agent.decide(_observation())
            self.assertEqual(result.action, "seer_check")

            events = writer.events_path.read_text(encoding="utf-8").splitlines()
            event_kinds = [json.loads(line)["kind"] for line in events]

            self.assertIn("provider_request_prepared", event_kinds)
            self.assertIn("provider_response_received", event_kinds)
            self.assertIn("provider_parse_succeeded", event_kinds)
            self.assertEqual(len(event_kinds), 3)

    def test_parse_failure_emits_parse_failed_event(self) -> None:
        """Invalid JSON response must emit provider_parse_failed."""
        with TemporaryDirectory() as tmp:
            writer = RuntimeEventWriter("test", Path(tmp), clock=lambda: "T")
            provider = _FakeProvider(raw_content="not valid json")
            agent = ProviderAgent("p1", provider, runtime_events=writer)

            with self.assertRaises(ProviderActionError):
                agent.decide(_observation())

            events = writer.events_path.read_text(encoding="utf-8").splitlines()
            event_kinds = [json.loads(line)["kind"] for line in events]
            self.assertIn("provider_parse_failed", event_kinds)
            # request_prepared and response_received should still be present.
            self.assertIn("provider_request_prepared", event_kinds)
            self.assertIn("provider_response_received", event_kinds)

    def test_invalid_action_emits_invalid_action_event(self) -> None:
        """An action not in allowed_actions must emit provider_action_invalid."""
        with TemporaryDirectory() as tmp:
            writer = RuntimeEventWriter("test", Path(tmp), clock=lambda: "T")
            # A seer cannot "witch_poison" (a real witch action, illegal for the seer role).
            provider = _FakeProvider(raw_content=_valid_action_json(action="witch_poison"))
            agent = ProviderAgent("p1", provider, runtime_events=writer)

            with self.assertRaises(ProviderActionError):
                agent.decide(_observation())

            events = writer.events_path.read_text(encoding="utf-8").splitlines()
            event_kinds = [json.loads(line)["kind"] for line in events]
            self.assertIn("provider_action_invalid", event_kinds)
            # Confirm parse_succeeded is NOT present.
            self.assertNotIn("provider_parse_succeeded", event_kinds)

    def test_timeout_emits_timeout_event(self) -> None:
        """failure_mode='timeout' must emit provider_timeout."""
        with TemporaryDirectory() as tmp:
            writer = RuntimeEventWriter("test", Path(tmp), clock=lambda: "T")
            agent = ProviderAgent("p1", _FakeProvider(), failure_mode="timeout", runtime_events=writer)

            with self.assertRaises(ProviderActionError):
                agent.decide(_observation())

            events = writer.events_path.read_text(encoding="utf-8").splitlines()
            event_kinds = [json.loads(line)["kind"] for line in events]
            self.assertIn("provider_timeout", event_kinds)
            self.assertEqual(len(event_kinds), 1)

    def test_provider_exception_emits_provider_failed_event(self) -> None:
        """A provider that raises an exception must emit provider_failed."""
        with TemporaryDirectory() as tmp:
            writer = RuntimeEventWriter("test", Path(tmp), clock=lambda: "T")
            provider = _FakeProvider(raise_on_respond=RuntimeError("connection refused"))
            agent = ProviderAgent("p1", provider, runtime_events=writer)

            with self.assertRaises(ProviderActionError):
                agent.decide(_observation())

            events = writer.events_path.read_text(encoding="utf-8").splitlines()
            event_kinds = [json.loads(line)["kind"] for line in events]
            self.assertIn("provider_failed", event_kinds)
            # request_prepared should be present (emitted before the call),
            # but response_received and parse_succeeded should not.
            self.assertIn("provider_request_prepared", event_kinds)
            self.assertNotIn("provider_response_received", event_kinds)
            self.assertNotIn("provider_parse_succeeded", event_kinds)
            self.assertEqual(len(event_kinds), 2)

    def test_event_free_when_no_writer_passed(self) -> None:
        """Without runtime_events, decide() must work as before."""
        provider = _FakeProvider(raw_content=_valid_action_json())
        agent = ProviderAgent("p1", provider)

        result = agent.decide(_observation())
        self.assertEqual(result.action, "seer_check")


class G1hFakeRuntimeCliTests(TestCase):
    """Integration tests for the fake G1h runtime CLI."""

    def test_fake_runtime_cli_writes_all_artifacts(self) -> None:
        """The CLI must exit 0, write all artifacts, and pass validation."""
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "g1h-fake-runtime"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_g1h_fake_runtime",
                    "--game-id",
                    "g1h_fake_runtime_test",
                    "--out-dir",
                    str(out_dir),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")

            stdout = result.stdout
            self.assertIn("g1h_fake_runtime_game_id=g1h_fake_runtime_test", stdout)
            self.assertIn("events_jsonl=written", stdout)
            self.assertIn("snapshots=written", stdout)
            self.assertIn("prompt_manifest=written", stdout)
            self.assertIn("game_log=written", stdout)
            self.assertIn("decision_log=written", stdout)
            self.assertIn("consensus_log=written", stdout)
            self.assertIn("provider_trace=written", stdout)
            self.assertIn("failure_audit=written", stdout)
            self.assertIn("live_api=not_used", stdout)

            events_path = out_dir / "events.jsonl"
            prompt_manifest_path = out_dir / "prompt-manifest.json"
            game_log_path = out_dir / "game-log.json"
            decision_log_path = out_dir / "decision-log.json"
            consensus_log_path = out_dir / "consensus-log.json"
            provider_trace_path = out_dir / "provider-trace.json"
            failure_audit_path = out_dir / "failure-audit.json"

            self.assertTrue(events_path.is_file())
            self.assertTrue(prompt_manifest_path.is_file())
            self.assertTrue(game_log_path.is_file())
            self.assertTrue(decision_log_path.is_file())
            self.assertTrue(consensus_log_path.is_file())
            self.assertTrue(provider_trace_path.is_file())
            self.assertTrue(failure_audit_path.is_file())

            events = read_events_jsonl(events_path)
            self.assertGreater(len(events), 0)

            seqs = [int(e["seq"]) for e in events]
            self.assertEqual(seqs, sorted(seqs))
            self.assertEqual(len(seqs), len(set(seqs)))

            has_game_event_id = any(
                "event_id" in e.get("payload", {}) or "event_id" in e.get("refs", {})
                for e in events
            )
            self.assertTrue(has_game_event_id, "No event references a game_event_id")

            has_provider_request = any(
                e["kind"] in ("provider_request_prepared", "provider_response_received")
                for e in events
            )
            self.assertTrue(has_provider_request, "No event references a provider_request_id")

            has_consensus = any(
                e["kind"] in ("consensus_started", "consensus_resolved")
                for e in events
            )
            self.assertTrue(has_consensus, "No event references a consensus_id")

            has_snapshot = any(
                e["kind"] == "snapshot_written"
                for e in events
            )
            self.assertTrue(has_snapshot, "No event references a snapshot_id")

            manifest = json.loads(prompt_manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest.get("secrets_redacted"))

            secret_patterns = ["Authorization", "Bearer ", "api_key", "DEEPSEEK_API_KEY", "sk-"]
            for artifact_path in [
                events_path,
                prompt_manifest_path,
                game_log_path,
                decision_log_path,
                consensus_log_path,
                provider_trace_path,
                failure_audit_path,
            ]:
                content = artifact_path.read_text(encoding="utf-8")
                for pattern in secret_patterns:
                    self.assertNotIn(
                        pattern,
                        content,
                        f"Secret pattern '{pattern}' found in {artifact_path.name}",
                    )


class G1hRuntimeBundleCompatibilityTests(TestCase):
    """Tests for final log compatibility and event refs integrity."""

    def test_final_logs_validate_through_existing_validators(self) -> None:
        """Final logs from fake runtime must validate through existing validators."""
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "g1h-fake-runtime"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_g1h_fake_runtime",
                    "--game-id",
                    "g1h_validate_test",
                    "--out-dir",
                    str(out_dir),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")

            game_log = load_game_log(out_dir / "game-log.json")
            validate_game_log(game_log)

            decision_log = load_decision_log(out_dir / "decision-log.json", game_log)
            validate_decision_log(decision_log, game_log)

            consensus_log = load_consensus_log(out_dir / "consensus-log.json", game_log)
            validate_consensus_log(consensus_log, game_log)

            failure_audit = json.loads(
                (out_dir / "failure-audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(failure_audit["failures"], [])

            provider_trace = json.loads(
                (out_dir / "provider-trace.json").read_text(encoding="utf-8")
            )
            self.assertGreater(len(provider_trace["requests"]), 0)
            self.assertGreater(len(provider_trace["responses"]), 0)


class G1hSecretScanTests(TestCase):
    """Tests for secret leak prevention in runtime artifacts."""

    def test_fake_runtime_artifacts_contain_no_secrets(self) -> None:
        """All fake runtime output files must not contain secret patterns."""
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "g1h-secret-scan"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_g1h_fake_runtime",
                    "--game-id",
                    "g1h_artifact_scan",
                    "--out-dir",
                    str(out_dir),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")

            case_insensitive_patterns = [
                "authorization",
                "deepseek_api_key",
                "api_key",
                "secret",
                "credential",
                "sk-",
            ]
            case_sensitive_patterns = ["Bearer "]
            allowed_literals = {"redacted", "secrets_redacted", "<REDACTED>"}

            for file_path in out_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                content = file_path.read_text(encoding="utf-8")
                lower_content = content.lower()

                for pattern in case_insensitive_patterns:
                    if pattern.lower() in lower_content:
                        for allowed in allowed_literals:
                            if allowed.lower() in lower_content:
                                break
                        else:
                            self.fail(
                                f"Secret pattern '{pattern}' found in {file_path.name}"
                            )

                for pattern in case_sensitive_patterns:
                    if pattern in content:
                        self.fail(
                            f"Secret pattern '{pattern}' found in {file_path.name}"
                        )
