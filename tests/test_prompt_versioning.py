from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.prompt_goldens import canonical_prompt_samples

EXPECTED_SAMPLE_NAMES = {
    "action_werewolf_night",
    "action_seer_night",
    "action_witch_night",
    "action_villager_day_vote",
    "action_hunter_day_vote",
    "action_hunter_shot",
    "speech_villager_day1",
    "speech_werewolf_day1",
    "compose_persona_action",
    "obs_villager_day",
    "obs_werewolf_night",
    "obs_witch_night_victim",
    "obs_witch_night_no_victim",
    "obs_hunter_shot",
}


class CanonicalSampleTests(unittest.TestCase):
    def test_sample_set_complete_unique_nonempty(self) -> None:
        samples = canonical_prompt_samples()
        names = [name for name, _ in samples]
        self.assertEqual(sorted(names), sorted(set(names)), "duplicate sample names")
        self.assertEqual(set(names), EXPECTED_SAMPLE_NAMES)
        for name, text in samples:
            self.assertIsInstance(text, str)
            self.assertTrue(text, f"empty rendered sample: {name}")

    def test_samples_are_deterministic(self) -> None:
        a = dict(canonical_prompt_samples())
        b = dict(canonical_prompt_samples())
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
