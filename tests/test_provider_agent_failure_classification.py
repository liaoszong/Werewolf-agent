from __future__ import annotations

import unittest

from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.provider_agent import ProviderActionError, ProviderAgent


class _RaisingProvider:
    """Minimal provider whose respond() always raises a chosen exception, so we
    can assert how ProviderAgent classifies transport/respond failures (B34-10)."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def respond(self, request):  # noqa: ANN001 - test stub
        raise self._exc


def _night_obs() -> AgentObservation:
    return AgentObservation(
        game_id="g1d_test",
        player_id="p3",
        role="seer",
        team="villager",
        phase="night",
        round=1,
        alive_players=["p1", "p2", "p3", "p4", "p5", "p6"],
        public_event_ids=[],
        private_event_ids=[],
        known_roles={"p3": "seer"},
    )


class ProviderAgentFailureClassificationTests(unittest.TestCase):
    """B34-10: a provider exception must no longer be flattened to kind='timeout'.
    It is classified into a structured kind, while the original message survives
    in `reason` (substring back-compat for budget detectors)."""

    def _decide_and_capture(self, exc: Exception) -> ProviderActionError:
        agent = ProviderAgent(player_id="p3", provider=_RaisingProvider(exc))
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(_night_obs())
        return ctx.exception

    def test_budget_exception_classified_as_budget_exhausted(self) -> None:
        err = self._decide_and_capture(RuntimeError("request budget exceeded: 32"))
        self.assertEqual(err.failure.kind, "budget_exhausted")
        self.assertIn("budget exceeded", err.failure.reason)  # substring back-compat

    def test_transport_exception_classified_as_transport_error(self) -> None:
        err = self._decide_and_capture(RuntimeError("[DeepSeek API output] transport error: ConnectionError"))
        self.assertEqual(err.failure.kind, "transport_error")

    def test_auth_exception_classified_as_auth_failed(self) -> None:
        err = self._decide_and_capture(RuntimeError("DeepSeek API key is not configured"))
        self.assertEqual(err.failure.kind, "auth_failed")

    def test_unknown_exception_classified_as_provider_error(self) -> None:
        err = self._decide_and_capture(RuntimeError("DeepSeek returned empty content"))
        self.assertEqual(err.failure.kind, "provider_error")


if __name__ == "__main__":
    unittest.main()
