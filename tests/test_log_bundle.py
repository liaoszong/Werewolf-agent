import json
import unittest
from pathlib import Path

from werewolf_eval.consensus_log import load_consensus_log
from werewolf_eval.decision_log import parse_decision_log
from werewolf_eval.failure_audit import load_failure_audit, parse_failure_audit
from werewolf_eval.game_log import load_game_log
from werewolf_eval.log_bundle import LogBundleValidationError, validate_log_bundle

ROOT = Path(__file__).resolve().parents[1]

GAME_PATH = ROOT / "docs/generated-games/g1c-wolf-consensus-game-log.json"
DECISION_PATH = ROOT / "docs/generated-games/g1c-wolf-consensus-decision-log.json"
CONSENSUS_PATH = ROOT / "docs/generated-games/g1c-wolf-consensus-consensus-log.json"
FAILURE_AUDIT_PATH = ROOT / "docs/generated-games/g1c-wolf-consensus-failure-audit.json"


def _raw(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class LogBundleTests(unittest.TestCase):
    def test_valid_g1c_bundle_passes(self):
        game = load_game_log(GAME_PATH)
        decision_log = parse_decision_log(_raw(DECISION_PATH), game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)
        failure_audit = load_failure_audit(FAILURE_AUDIT_PATH, game)

        result = validate_log_bundle(
            game,
            decision_log=decision_log,
            consensus_log=consensus_log,
            failure_audit=failure_audit,
        )

        self.assertEqual(result.team_consensus_links, 2)

    def test_team_decision_requires_consensus_id_when_consensus_log_is_supplied(self):
        game = load_game_log(GAME_PATH)
        raw_decision = _raw(DECISION_PATH)
        raw_decision["decisions"][0]["consensus_id"] = None
        decision_log = parse_decision_log(raw_decision, game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)

        with self.assertRaisesRegex(LogBundleValidationError, "missing consensus_id"):
            validate_log_bundle(game, decision_log=decision_log, consensus_log=consensus_log)

    def test_team_decision_rejects_unknown_consensus_id(self):
        game = load_game_log(GAME_PATH)
        raw_decision = _raw(DECISION_PATH)
        raw_decision["decisions"][0]["consensus_id"] = "missing_consensus"
        decision_log = parse_decision_log(raw_decision, game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)

        with self.assertRaisesRegex(LogBundleValidationError, "unknown consensus_id"):
            validate_log_bundle(game, decision_log=decision_log, consensus_log=consensus_log)

    def test_team_decision_rejects_consensus_target_mismatch(self):
        game = load_game_log(GAME_PATH)
        raw_decision = _raw(DECISION_PATH)
        raw_decision["decisions"][0]["target"] = "p6"
        decision_log = parse_decision_log(raw_decision, game)
        consensus_log = load_consensus_log(CONSENSUS_PATH, game)

        with self.assertRaisesRegex(LogBundleValidationError, "target mismatch"):
            validate_log_bundle(game, decision_log=decision_log, consensus_log=consensus_log)

    def test_failure_audit_source_label_must_match_game_source_label(self):
        game = load_game_log(GAME_PATH)
        raw_audit = _raw(FAILURE_AUDIT_PATH)
        raw_audit["source_label"] = "[scripted deterministic output]"

        with self.assertRaisesRegex(LogBundleValidationError, "source_label mismatch"):
            validate_log_bundle(
                game,
                failure_audit=parse_failure_audit(raw_audit, game),
            )


if __name__ == "__main__":
    unittest.main()
