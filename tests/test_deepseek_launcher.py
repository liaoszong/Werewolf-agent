"""Offline unit tests for the G3-1 deepseek live launcher.

Every test injects a fake ``provider_factory`` (no real transport, no key read,
no socket).  The launcher delegates to the spine consensus runner verbatim and
classifies the run-failure exit code from the ``failure-audit.json`` it caused.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from werewolf_eval.deepseek_launcher import (
    DEFAULT_MAX_LIVE_REQUESTS,
    _audit_is_budget_exhausted,
    _classify_failure,
    build_deepseek_launcher,
    build_deepseek_provider_config,
)


class _FakeDeepSeekProvider:
    """Deterministic fake that drives a real consensus game to completion, or
    raises a chosen error to exercise the failure-classification path."""

    def __init__(self, raise_message: str | None = None) -> None:
        self._raise_message = raise_message
        self.requests: list = []
        self.responses: list = []

    def respond(self, request: Any) -> Any:
        from werewolf_eval.provider_contract import ProviderResponse

        self.requests.append(request)
        if self._raise_message is not None:
            raise RuntimeError(self._raise_message)

        action = request.allowed_actions[0] if request.allowed_actions else "player_vote"
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


def _ok_factory(player_id: str) -> Any:
    from werewolf_eval.provider_agent import ProviderAgent

    return ProviderAgent(player_id, _FakeDeepSeekProvider())


def _raising_factory(message: str):
    def factory(player_id: str) -> Any:
        from werewolf_eval.provider_agent import ProviderAgent

        return ProviderAgent(player_id, _FakeDeepSeekProvider(raise_message=message))

    return factory


_BUDGET_FACTORY = _raising_factory("request budget exceeded: 32")
_GENERIC_FACTORY = _raising_factory("simulated provider failure")

_SECRET_MARKERS = ["Authorization", "Bearer ", "api_key", "DEEPSEEK_API_KEY", "sk-"]


class DeepSeekLauncherConfigTests(unittest.TestCase):
    def test_default_budget_is_32(self) -> None:
        self.assertEqual(DEFAULT_MAX_LIVE_REQUESTS, 32)
        cfg = build_deepseek_provider_config(
            api_key="sk-test-fake", base_url="https://api.deepseek.com",
            model="deepseek-chat", max_tokens=256,
        )
        self.assertEqual(cfg.max_requests, 32)

    def test_explicit_budget_overrides_default(self) -> None:
        cfg = build_deepseek_provider_config(
            api_key="sk-test-fake", base_url="https://api.deepseek.com",
            model="deepseek-chat", max_tokens=256, max_requests=48,
        )
        self.assertEqual(cfg.max_requests, 48)


class DeepSeekLauncherTests(unittest.TestCase):
    def _build(self, provider_factory) -> Any:
        return build_deepseek_launcher(
            api_key="sk-test-fake-key",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            timeout_seconds=30,
            max_tokens=256,
            max_requests=32,
            provider_factory=provider_factory,
        )

    def test_launcher_writes_spine_and_bundle(self) -> None:
        launcher = self._build(_ok_factory)
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            code = launcher("g3_live_ok", out_dir)
            self.assertEqual(code, 0)
            # runtime spine
            self.assertTrue((out_dir / "events.jsonl").exists())
            self.assertTrue((out_dir / "prompt-manifest.json").exists())
            self.assertTrue((out_dir / "snapshots").is_dir())
            self.assertGreater(len(list((out_dir / "snapshots").glob("*.json"))), 0)
            # bundle
            for name in (
                "game-log.json", "decision-log.json", "consensus-log.json",
                "provider-trace.json", "failure-audit.json",
            ):
                self.assertTrue((out_dir / name).exists(), name)
            # resolved-profile.json is the server wrapper's artifact, NOT the launcher's
            self.assertFalse((out_dir / "resolved-profile.json").exists())

    def test_launcher_records_real_model_in_manifest(self) -> None:
        # G3-3 end-to-end: a live launch records the model the launcher was
        # configured with ("deepseek-chat"), not the legacy hard-coded "unknown".
        launcher = self._build(_ok_factory)
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            self.assertEqual(launcher("g3_live_model", out_dir), 0)
            manifest = json.loads(
                (out_dir / "prompt-manifest.json").read_text(encoding="utf-8")
            )
            models = {a.get("model") for a in manifest["agents"]}
            self.assertEqual(models, {"deepseek-chat"})
            self.assertNotIn("unknown", models)

    def test_budget_exhaustion_classified_exit_3(self) -> None:
        launcher = self._build(_BUDGET_FACTORY)
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            code = launcher("g3_live_budget", out_dir)
            self.assertEqual(code, 3)
            self.assertTrue((out_dir / "provider-trace.json").exists())
            self.assertTrue((out_dir / "failure-audit.json").exists())
            self.assertFalse((out_dir / "game-log.json").exists())
            audit = json.loads((out_dir / "failure-audit.json").read_text(encoding="utf-8"))
            self.assertTrue(any("budget exceeded" in str(f.get("reason", "")) for f in audit["failures"]))

    def test_generic_provider_failure_classified_exit_2(self) -> None:
        launcher = self._build(_GENERIC_FACTORY)
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            code = launcher("g3_live_fail", out_dir)
            self.assertEqual(code, 2)
            self.assertTrue((out_dir / "failure-audit.json").exists())
            self.assertFalse((out_dir / "game-log.json").exists())

    def test_config_key_absent_from_raised_errors(self) -> None:
        # Regression: a fake key passed to DeepSeekProviderConfig must never
        # surface in a raised error string (offline; reuses provider patterns).
        from werewolf_eval.deepseek_provider import DeepSeekProvider, DeepSeekProviderConfig
        from werewolf_eval.provider_contract import ProviderRequest

        def _boom(url, headers, payload, timeout_seconds):  # type: ignore[no-untyped-def]
            raise RuntimeError("HTTP 500 upstream error")

        provider = DeepSeekProvider(
            DeepSeekProviderConfig(api_key="sk-test-fake-key"), transport=_boom
        )
        req = ProviderRequest(
            request_id="g3_r01_p3", game_id="g3", actor="p3", phase="night", round=1,
            observation={"role": "seer", "alive": ["p1", "p2", "p3"]},
            allowed_actions=["seer_check"], allowed_targets=["p1", "p2", "p3"],
        )
        with self.assertRaises(RuntimeError) as ctx:
            provider.respond(req)
        self.assertNotIn("sk-test-fake-key", str(ctx.exception))
        self.assertNotIn("sk-test", str(ctx.exception))

    def test_key_never_in_artifacts(self) -> None:
        launcher = self._build(_ok_factory)
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            launcher("g3_live_nokey", out_dir)
            for path in out_dir.rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn("sk-test-fake-key", text, path.name)
                for marker in _SECRET_MARKERS:
                    self.assertNotIn(marker, text, f"{marker!r} in {path.name}")


class BudgetClassifierConsistencyTests(unittest.TestCase):
    """The two budget-failure detectors (_classify_failure substring vs
    _audit_is_budget_exhausted structured kind) must agree. The substring-only
    detector silently missed the emergent engine's "budget exhausted" wording
    (vs the legacy "budget exceeded"), so reusing it on an emergent audit would
    misclassify a budget-exhausted run as a generic failure (exit 2 not 3)."""

    @staticmethod
    def _audit_dir(tmp: str, failures: list[dict]) -> Path:
        rdir = Path(tmp)
        (rdir / "failure-audit.json").write_text(
            json.dumps({"game_id": "g", "source_label": "x", "failures": failures}),
            encoding="utf-8",
        )
        return rdir

    def test_classify_failure_detects_structured_budget_kind(self) -> None:
        # emergent: kind="budget_exhausted", reason uses "exhausted" not "exceeded".
        with TemporaryDirectory() as tmp:
            rdir = self._audit_dir(tmp, [{"kind": "budget_exhausted", "reason": "budget exhausted: 30/30 requests"}])
            self.assertEqual(_classify_failure(rdir), 3)

    def test_classify_failure_detects_exhausted_wording_without_kind(self) -> None:
        with TemporaryDirectory() as tmp:
            rdir = self._audit_dir(tmp, [{"kind": "timeout", "reason": "provider error: budget exhausted: 30/30 requests"}])
            self.assertEqual(_classify_failure(rdir), 3)

    def test_classify_failure_still_detects_legacy_exceeded_wording(self) -> None:
        # regression: legacy llm_providers raises "request budget exceeded" (kind timeout).
        with TemporaryDirectory() as tmp:
            rdir = self._audit_dir(tmp, [{"kind": "timeout", "reason": "provider error: request budget exceeded: 32"}])
            self.assertEqual(_classify_failure(rdir), 3)

    def test_classify_failure_generic_stays_exit_2(self) -> None:
        with TemporaryDirectory() as tmp:
            rdir = self._audit_dir(tmp, [{"kind": "timeout", "reason": "provider error: simulated provider failure"}])
            self.assertEqual(_classify_failure(rdir), 2)

    def test_audit_detector_also_accepts_exhausted_wording(self) -> None:
        # symmetry: the structured detector should agree with _classify_failure even
        # if a path emits the wording without the structured kind.
        with TemporaryDirectory() as tmp:
            rdir = self._audit_dir(tmp, [{"kind": "timeout", "reason": "budget exhausted: 30/30 requests"}])
            self.assertTrue(_audit_is_budget_exhausted(rdir / "failure-audit.json"))

    def test_audit_detector_still_accepts_structured_kind(self) -> None:
        with TemporaryDirectory() as tmp:
            rdir = self._audit_dir(tmp, [{"kind": "budget_exhausted", "reason": "budget exhausted: 30/30"}])
            self.assertTrue(_audit_is_budget_exhausted(rdir / "failure-audit.json"))

    def test_audit_detector_rejects_generic_failure(self) -> None:
        with TemporaryDirectory() as tmp:
            rdir = self._audit_dir(tmp, [{"kind": "timeout", "reason": "provider error: simulated"}])
            self.assertFalse(_audit_is_budget_exhausted(rdir / "failure-audit.json"))


if __name__ == "__main__":
    unittest.main()
