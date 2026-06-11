"""T-2/D-5: first behavior tests for the six validate_* CLIs.

Locks (a) exit 0 + summary line on good fixtures, (b) the uniform error
contract `invalid <label>: <exc>` + exit 1 on bad input (was: 5 of 6 CLIs
dumped a raw traceback)."""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval import (
    validate_consensus_log,
    validate_decision_log,
    validate_failure_audit,
    validate_game_log,
    validate_log_bundle,
    validate_semantic_labels,
)

GOLD = ROOT / "docs" / "gold-game"
GEN = ROOT / "docs" / "generated-games"
GAME = str(GOLD / "g001-game-log.json")
DECISION = str(GOLD / "g001-decision-log.json")
CONSENSUS = str(GOLD / "g001-consensus-log.json")
LABELS = str(GOLD / "s5-semantic-label-output.example.json")
G1C_GAME = str(GEN / "g1c-wolf-consensus-game-log.json")
G1C_AUDIT = str(GEN / "g1c-wolf-consensus-failure-audit.json")


def _run(main, argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class ValidateCliSuccessTest(unittest.TestCase):
    def test_game_log(self):
        code, out = _run(validate_game_log.main, [GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated game_id=", out)

    def test_decision_log(self):
        code, out = _run(validate_decision_log.main, [DECISION, GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated decision_log_id=", out)

    def test_consensus_log(self):
        code, out = _run(validate_consensus_log.main, [CONSENSUS, GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated consensus_log_id=", out)

    def test_failure_audit(self):
        code, out = _run(validate_failure_audit.main, [G1C_AUDIT, G1C_GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated failure_audit game_id=", out)

    def test_log_bundle(self):
        code, out = _run(validate_log_bundle.main, [GAME, "--decision-log", DECISION])
        self.assertEqual(code, 0)
        self.assertIn("validated log_bundle game_id=", out)

    def test_semantic_labels(self):
        code, out = _run(validate_semantic_labels.main, [GAME, DECISION, LABELS])
        self.assertEqual(code, 0)
        self.assertIn("validated semantic_label_log_id=", out)


class ValidateCliInvalidInputTest(unittest.TestCase):
    """Uniform error contract: bad input -> `invalid <label>: ...` + exit 1,
    never an uncaught traceback."""

    def test_bad_input_exits_1_with_uniform_message(self):
        cases = [
            (validate_game_log.main, ["missing.json"], "invalid game log:"),
            (validate_decision_log.main, ["missing.json", GAME], "invalid decision log:"),
            (validate_consensus_log.main, ["missing.json", GAME], "invalid consensus log:"),
            (validate_failure_audit.main, ["missing.json", G1C_GAME], "invalid failure audit:"),
            (validate_log_bundle.main, ["missing.json"], "invalid log bundle:"),
            (validate_semantic_labels.main, [GAME, DECISION, "missing.json"], "invalid semantic label log:"),
        ]
        for main, argv, label in cases:
            with self.subTest(label=label):
                code, out = _run(main, argv)
                self.assertEqual(code, 1)
                self.assertIn(label, out)


if __name__ == "__main__":
    unittest.main()
