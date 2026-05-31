from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class GameEngineContractTests(unittest.TestCase):
    def test_private_observation_hides_non_visible_roles(self) -> None:
        from werewolf_eval.game_engine import build_default_config, GameEngine

        engine = GameEngine.from_config(build_default_config(game_id="g1b_mock_001"))

        seer_observation = engine.observation_for("p3")
        self.assertEqual(seer_observation.player_id, "p3")
        self.assertEqual(seer_observation.role, "seer")
        self.assertEqual(seer_observation.team, "villager")
        self.assertEqual(seer_observation.known_roles, {"p3": "seer"})
        self.assertNotIn("p1", seer_observation.known_roles)
        self.assertNotIn("p2", seer_observation.known_roles)

        wolf_observation = engine.observation_for("p1")
        self.assertEqual(wolf_observation.role, "werewolf")
        self.assertEqual(wolf_observation.team, "werewolf")
        self.assertEqual(
            wolf_observation.known_roles,
            {"p1": "werewolf", "p2": "werewolf"},
        )

    def test_mock_agent_returns_structured_action(self) -> None:
        from werewolf_eval.game_engine import AgentAction, MockAgent

        agent = MockAgent(player_id="p3")
        action = agent.decide(
            observation={
                "game_id": "g1b_mock_001",
                "player_id": "p3",
                "role": "seer",
                "team": "villager",
                "phase": "night",
                "round": 1,
                "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
                "public_event_ids": [],
                "private_event_ids": [],
                "known_roles": {"p3": "seer"},
            }
        )

        self.assertIsInstance(action, AgentAction)
        self.assertEqual(action.actor, "p3")
        self.assertEqual(action.action, "seer_check")
        self.assertEqual(action.target, "p1")
        self.assertEqual(action.decision_type, "inference_based")
        self.assertEqual(action.source_label, "[deterministic mock agent output]")


if __name__ == "__main__":
    unittest.main()
