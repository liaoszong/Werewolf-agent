import unittest
from werewolf_eval.invariants import check_run
from werewolf_eval.invariants.fuzz import SEED_BANK, well_formed_game, known_bad_games


class TestFuzz(unittest.TestCase):
    def test_every_well_formed_seed_passes_all_invariants(self):
        for seed in SEED_BANK:
            arts = well_formed_game(seed)
            violations = [v for v in check_run(arts) if v.severity == "error"]
            self.assertEqual(violations, [], f"seed {seed} produced {violations}")

    def test_each_known_bad_fails_its_target(self):
        for label, arts, expected_id in known_bad_games(seed=0):
            ids = {v.id for v in check_run(arts)}
            self.assertIn(expected_id, ids, f"{label} should fail {expected_id}; got {ids}")


if __name__ == "__main__":
    unittest.main()
