from __future__ import annotations

import unittest

from werewolf_eval.fake_provider import (
    DeterministicFakeProvider,
    build_default_fake_provider_agent,
    build_default_fake_provider_script,
)
from werewolf_eval.game_engine import AgentObservation, GameConfig, EnginePlayer
from werewolf_eval.provider_agent import ProviderActionError, ProviderAgent
from werewolf_eval.provider_contract import (
    FAKE_PROVIDER_SOURCE_LABEL,
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
)


class FakeProviderAdapterTests(unittest.TestCase):
    @staticmethod
    def _default_config() -> GameConfig:
        return GameConfig(
            game_id="g1d_test",
            players=[
                EnginePlayer("p1", "werewolf", "werewolf"),
                EnginePlayer("p2", "werewolf", "werewolf"),
                EnginePlayer("p3", "seer", "villager"),
                EnginePlayer("p4", "witch", "villager"),
                EnginePlayer("p5", "villager", "villager"),
                EnginePlayer("p6", "villager", "villager"),
            ],
        )

    @staticmethod
    def _p3_night_obs() -> AgentObservation:
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

    # --- 1. DeterministicFakeProvider returns same ProviderResponse for same ProviderRequest ---
    def test_deterministic_response_for_same_request(self) -> None:
        script = {
            ("p3", "night", 1): '{"action":"seer_check","target":"p1","reason_summary":"p3 checks p1","decision_type":"inference_based","confidence":1.0}',
        }
        provider = DeterministicFakeProvider(script)
        request = ProviderRequest(
            request_id="r1", game_id="g", actor="p3", phase="night", round=1,
            observation={}, allowed_actions=["seer_check"], allowed_targets=["p1", "p2"],
        )
        r1 = provider.respond(request)
        r2 = provider.respond(request)
        self.assertEqual(r1.raw_content, r2.raw_content)
        self.assertEqual(r1.source_label, FAKE_PROVIDER_SOURCE_LABEL)

    # --- 2. ProviderAgent converts valid provider JSON into AgentAction ---
    def test_valid_response_becomes_agent_action(self) -> None:
        agent = build_default_fake_provider_agent("p3")
        obs = self._p3_night_obs()
        action = agent.decide(obs)
        self.assertEqual(action.actor, "p3")
        self.assertEqual(action.action, "seer_check")
        self.assertEqual(action.target, "p1")
        self.assertEqual(action.source_label, FAKE_PROVIDER_SOURCE_LABEL)

    # --- 3. Invalid target is rejected before AgentAction is returned ---
    def test_invalid_target_raises_provider_action_error_without_repair(self) -> None:
        agent = build_default_fake_provider_agent(
            "p3",
            override_raw_content='{"action":"seer_check","target":"p99","reason_summary":"bad target","decision_type":"inference_based","confidence":1.0}',
        )
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "invalid_action")
        self.assertEqual(failure.target, "p99")
        self.assertFalse(failure.repaired_to_valid_action)

    # --- 4. Non-JSON raw_content → ProviderFailure(kind="parse_failure") ---
    def test_non_json_response_becomes_parse_failure(self) -> None:
        agent = build_default_fake_provider_agent(
            "p3", override_raw_content="not valid json {{{",
        )
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "parse_failure")
        self.assertFalse(failure.repaired_to_valid_action)

    # --- 5. Simulated timeout → ProviderFailure(kind="timeout") ---
    def test_timeout_becomes_provider_failure(self) -> None:
        agent = build_default_fake_provider_agent("p3", failure_mode="timeout")
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "timeout")
        self.assertFalse(failure.repaired_to_valid_action)

    # --- 6. Output contains no network URL, env, API key, or SDK reference ---
    def test_provider_output_contains_no_secrets_or_urls(self) -> None:
        script = {
            ("p3", "night", 1): '{"action":"seer_check","target":"p1","reason_summary":"check","decision_type":"inference_based","confidence":1.0}',
        }
        provider = DeterministicFakeProvider(script)
        request = ProviderRequest(
            request_id="r1", game_id="g", actor="p3", phase="night", round=1,
            observation={}, allowed_actions=["seer_check"], allowed_targets=["p1"],
        )
        resp = provider.respond(request)
        encoded = resp.raw_content.lower()
        self.assertNotIn("api_key", encoded)
        self.assertNotIn("authorization", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)
        self.assertNotIn("bearer", encoded)

    # --- 7. Missing action key in response is treated as parse failure ---
    def test_missing_action_key_raises_parse_failure(self) -> None:
        agent = build_default_fake_provider_agent(
            "p3", override_raw_content='{"target":"p1"}',
        )
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        self.assertEqual(ctx.exception.failure.kind, "parse_failure")

    # --- 8. build_default_fake_provider_script covers all mock agent keys ---
    def test_default_script_contains_known_actions(self) -> None:
        script = build_default_fake_provider_script()
        self.assertIn(("p3", "night", 1), script)
        self.assertIn(("p4", "night", 1), script)
        self.assertIn(("p3", "day", 1), script)
        self.assertIn(("p4", "day", 1), script)
        self.assertIn(("p5", "day", 1), script)
        self.assertIn(("p6", "day", 1), script)
        self.assertIn(("p4", "day", 2), script)
        self.assertIn(("p5", "day", 2), script)
        self.assertIn(("p6", "day", 2), script)
        self.assertIn(("wolf_team", "night", 1), script)
        self.assertIn(("wolf_team", "night", 2), script)

    # --- 9. ProviderAgent with wolf_team actor returns valid action ---
    def test_wolf_team_agent_returns_valid_action(self) -> None:
        agent = build_default_fake_provider_agent("wolf_team")
        obs = AgentObservation(
            game_id="g1d_test", player_id="wolf_team", role="werewolf", team="werewolf",
            phase="night", round=1, alive_players=["p1", "p2", "p3", "p4", "p5", "p6"],
            public_event_ids=[], private_event_ids=[],
            known_roles={"p1": "werewolf", "p2": "werewolf"},
        )
        action = agent.decide(obs)
        self.assertEqual(action.actor, "wolf_team")
        self.assertEqual(action.action, "werewolf_kill")
        self.assertEqual(action.source_label, FAKE_PROVIDER_SOURCE_LABEL)


# --- 10. Missing reason_summary → ProviderActionError ---
    def test_missing_reason_summary_raises_provider_action_error(self) -> None:
        agent = build_default_fake_provider_agent(
            "p3",
            override_raw_content='{"action":"seer_check","target":"p1","decision_type":"inference_based","confidence":1.0}',
        )
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "parse_failure")
        self.assertIn("reason_summary", failure.reason)
        self.assertFalse(failure.repaired_to_valid_action)

    # --- 11. Missing decision_type → ProviderActionError ---
    def test_missing_decision_type_raises_provider_action_error(self) -> None:
        agent = build_default_fake_provider_agent(
            "p3",
            override_raw_content='{"action":"seer_check","target":"p1","reason_summary":"check","confidence":1.0}',
        )
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "parse_failure")
        self.assertIn("decision_type", failure.reason)
        self.assertFalse(failure.repaired_to_valid_action)

    # --- 12. Missing confidence → ProviderActionError ---
    def test_missing_confidence_raises_provider_action_error(self) -> None:
        agent = build_default_fake_provider_agent(
            "p3",
            override_raw_content='{"action":"seer_check","target":"p1","reason_summary":"check","decision_type":"inference_based"}',
        )
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "parse_failure")
        self.assertIn("confidence", failure.reason)
        self.assertFalse(failure.repaired_to_valid_action)

    # --- 13. Invalid confidence type → ProviderActionError ---
    def test_invalid_confidence_type_raises_provider_action_error(self) -> None:
        agent = build_default_fake_provider_agent(
            "p3",
            override_raw_content='{"action":"seer_check","target":"p1","reason_summary":"check","decision_type":"inference_based","confidence":"high"}',
        )
        with self.assertRaises(ProviderActionError) as ctx:
            agent.decide(self._p3_night_obs())
        failure = ctx.exception.failure
        self.assertEqual(failure.kind, "parse_failure")
        self.assertIn("confidence", failure.reason)
        self.assertFalse(failure.repaired_to_valid_action)


if __name__ == "__main__":
    unittest.main()
