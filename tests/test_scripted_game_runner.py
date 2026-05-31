from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ScriptedGameFixtureTests(unittest.TestCase):
    def test_script_fixture_exists_and_has_contract_shape(self) -> None:
        path = ROOT / "docs/game-scripts/g1-scripted-game.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["script_id"], "g1_scripted_001")
        self.assertEqual(payload["game_id"], "g1_scripted_001")
        self.assertEqual(payload["source_label"], "[scripted deterministic output]")
        self.assertEqual(len(payload["players"]), 6)
        self.assertEqual(len(payload["steps"]), 15)
        self.assertEqual(payload["result"]["winner"], "villager")

        decision_steps = [step for step in payload["steps"] if "decision_actor" in step]
        self.assertEqual(len(decision_steps), 7)
        self.assertTrue(
            all(
                step["decision_source_label"] == "[scripted deterministic output]"
                for step in decision_steps
            )
        )

        wolf_kills = [step for step in payload["steps"] if step["type"] == "werewolf_kill"]
        self.assertEqual(len(wolf_kills), 2)
        self.assertTrue(
            all(
                step["consensus_source_label"] == "[scripted deterministic output]"
                for step in wolf_kills
            )
        )


if __name__ == "__main__":
    unittest.main()
