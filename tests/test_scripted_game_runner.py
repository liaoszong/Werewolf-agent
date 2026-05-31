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


class ScriptedGameRunnerTests(unittest.TestCase):
    def test_runner_emits_valid_log_dicts(self) -> None:
        from werewolf_eval.consensus_log import parse_consensus_log
        from werewolf_eval.decision_log import parse_decision_log
        from werewolf_eval.game_log import parse_game_log
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        outputs = run_scripted_game(script)

        game = parse_game_log(outputs.game_log)
        decision_log = parse_decision_log(outputs.decision_log, game)
        consensus_log = parse_consensus_log(outputs.consensus_log, game)

        self.assertEqual(game.game_id, "g1_scripted_001")
        self.assertEqual(outputs.game_log["source_label"], "[scripted deterministic output]")
        self.assertEqual(decision_log.source_label, "[scripted deterministic output]")
        self.assertEqual(consensus_log.source_label, "[scripted deterministic output]")
        self.assertEqual(len(game.events), 15)
        self.assertEqual(len(decision_log.decisions), 7)
        self.assertEqual(len(consensus_log.consensuses), 2)

    def test_runner_is_deterministic(self) -> None:
        from werewolf_eval.scripted_game import load_scripted_game, run_scripted_game

        script = load_scripted_game(ROOT / "docs/game-scripts/g1-scripted-game.json")
        first = run_scripted_game(script)
        second = run_scripted_game(script)

        self.assertEqual(first.game_log, second.game_log)
        self.assertEqual(first.decision_log, second.decision_log)
        self.assertEqual(first.consensus_log, second.consensus_log)


if __name__ == "__main__":
    unittest.main()
