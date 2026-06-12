import json
import unittest
from pathlib import Path

from werewolf_eval.failure_audit import (
    FailureAuditValidationError,
    parse_failure_audit,
)
from werewolf_eval.game_log import load_game_log

ROOT = Path(__file__).resolve().parents[1]


def _game():
    return load_game_log(ROOT / "docs/generated-games/g1c-wolf-consensus-game-log.json")


def _valid_raw():
    return json.loads(
        Path(ROOT / "docs/generated-games/g1c-wolf-consensus-failure-audit.json").read_text(
            encoding="utf-8"
        )
    )


class FailureAuditTests(unittest.TestCase):
    def test_accepts_empty_valid_audit(self):
        audit = parse_failure_audit(_valid_raw(), _game())

        self.assertEqual(audit.game_id, "g1c_wolf_consensus")
        self.assertEqual(audit.source_label, "[deterministic mock agent output]")
        self.assertEqual(audit.failures, [])

    def test_rejects_missing_kind(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p1",
                "target": "p99",
                "reason": "invalid target",
                "repaired_to_valid_action": False,
            }
        ]

        with self.assertRaisesRegex(FailureAuditValidationError, "failure missing fields"):
            parse_failure_audit(raw, _game())

    def test_accepts_structured_provider_failure_kinds(self):
        # B34-10 / B12-02/03: provider transport/respond exceptions are now
        # classified into structured kinds that flow into the failure audit via
        # ProviderFailure.kind. The whitelist must accept them.
        for kind in ("budget_exhausted", "transport_error", "auth_failed", "provider_error"):
            with self.subTest(kind=kind):
                raw = _valid_raw()
                raw["failures"] = [
                    {
                        "game_id": "g1c_wolf_consensus",
                        "round": 1,
                        "phase": "night",
                        "actor": "p1",
                        "kind": kind,
                        "target": None,
                        "reason": f"provider error classified as {kind}",
                        "repaired_to_valid_action": False,
                    }
                ]
                audit = parse_failure_audit(raw, _game())
                self.assertEqual(audit.failures[0].kind, kind)

    def test_rejects_repaired_to_valid_action_true(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p1",
                "kind": "invalid_action",
                "target": "p99",
                "reason": "invalid target",
                "repaired_to_valid_action": True,
            }
        ]

        with self.assertRaisesRegex(FailureAuditValidationError, "must be false"):
            parse_failure_audit(raw, _game())

    def test_rejects_unknown_failure_actor(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p99",
                "kind": "timeout",
                "target": None,
                "reason": "unknown actor timed out",
                "repaired_to_valid_action": False,
            }
        ]

        with self.assertRaisesRegex(FailureAuditValidationError, "unknown actor"):
            parse_failure_audit(raw, _game())

    def test_rejects_unknown_valid_target_for_invalid_action(self):
        raw = _valid_raw()
        raw["failures"] = [
            {
                "game_id": "g1c_wolf_consensus",
                "round": 1,
                "phase": "night",
                "actor": "p1",
                "kind": "invalid_action",
                "target": "p99",
                "reason": "invalid target",
                "repaired_to_valid_action": False,
            }
        ]

        audit = parse_failure_audit(raw, _game())
        self.assertEqual(audit.failures[0].target, "p99")


if __name__ == "__main__":
    unittest.main()
