"""Tests for observer_enrichment: cross-round join, ambiguity marking, and legacy fallback.

C12-06/A45-7: Ensures (round, phase, actor, action, target) composite key join,
fail-soft ambiguity marking on duplicate keys, and graceful legacy fallback
for decision logs without round.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from werewolf_eval.observer_enrichment import _load_decision_reasons


def _write_run_dir(game_log: dict, decision_log: dict) -> Path:
    """Write game-log.json and decision-log.json to a temp dir and return the path."""
    d = tempfile.mkdtemp()
    dp = Path(d)
    (dp / "game-log.json").write_text(json.dumps(game_log), encoding="utf-8")
    (dp / "decision-log.json").write_text(json.dumps(decision_log), encoding="utf-8")
    return dp


class CrossRoundEnrichmentTests(unittest.TestCase):
    """C12-06/A45-7: round-aware composite key join disambiguates repeated
    (actor, action, target) across rounds."""

    def _base_game_log(self, events: list[dict]) -> dict:
        return {
            "game_log_id": "test_gl",
            "game_id": "test_game",
            "source_label": "[test]",
            "events": events,
        }

    def _base_decision_log(self, decisions: list[dict]) -> dict:
        return {
            "decision_log_id": "test_dl",
            "game_id": "test_game",
            "source_label": "[test]",
            "decisions": decisions,
        }

    def test_cross_round_same_actor_action_target_matched_correctly(self):
        """Guard protects p3 in round 1 and round 2 — enrichment maps each
        reason to the correct round's event, not cross-round."""
        run_dir = _write_run_dir(
            self._base_game_log([
                {"event_id": "e_g1", "round": 1, "phase": "night", "actor": "p3", "type": "guard_protect", "target": "p3", "data": {"summary": "Guard protects p3 r1"}},
                {"event_id": "e_g2", "round": 2, "phase": "night", "actor": "p3", "type": "guard_protect", "target": "p3", "data": {"summary": "Guard protects p3 r2"}},
            ]),
            self._base_decision_log([
                {"decision_id": "d1", "actor": "p3", "decision_scope": "single", "phase": "night", "round": 1, "action": "guard_protect", "target": "p3", "reason_summary": "r1 reason", "decision_type": "inference_based", "visible_info_refs": [], "request_id": "r01_p3"},
                {"decision_id": "d2", "actor": "p3", "decision_scope": "single", "phase": "night", "round": 2, "action": "guard_protect", "target": "p3", "reason_summary": "r2 reason", "decision_type": "inference_based", "visible_info_refs": [], "request_id": "r02_p3"},
            ]),
        )
        result = _load_decision_reasons(run_dir)
        # Round 1 event gets round 1 reason
        self.assertEqual(result["e_g1"]["reason_summary"], "r1 reason")
        self.assertEqual(result["e_g1"]["reason_source"], "matched")
        self.assertEqual(result["e_g1"]["decision_id"], "d1")
        self.assertEqual(result["e_g1"]["request_id"], "r01_p3")
        # Round 2 event gets round 2 reason (NOT round 1)
        self.assertEqual(result["e_g2"]["reason_summary"], "r2 reason")
        self.assertEqual(result["e_g2"]["reason_source"], "matched")
        self.assertEqual(result["e_g2"]["decision_id"], "d2")
        self.assertEqual(result["e_g2"]["request_id"], "r02_p3")

    def test_round_bearing_event_without_same_round_decision_not_mislabeled(self):
        """A45-7 regression: a round-2 event whose round-2 decision is MISSING must
        NOT inherit a different round's reason. The pre-fix greedy last-resort
        fallback grabbed the round-1 decision and stamped it on the round-2 event
        (reproduced). Correct behavior: leave the event unmatched rather than
        attach the wrong round's reasoning."""
        run_dir = _write_run_dir(
            self._base_game_log([
                {"event_id": "e_g2", "round": 2, "phase": "night", "actor": "p3", "type": "guard_protect", "target": "p3", "data": {"summary": "Guard protects p3 r2"}},
            ]),
            self._base_decision_log([
                {"decision_id": "d1", "actor": "p3", "decision_scope": "single", "phase": "night", "round": 1, "action": "guard_protect", "target": "p3", "reason_summary": "r1 reason", "decision_type": "inference_based", "visible_info_refs": [], "request_id": "r01_p3"},
            ]),
        )
        result = _load_decision_reasons(run_dir)
        # The round-2 event must NOT be labeled with the round-1 decision at all.
        self.assertNotIn(
            "e_g2", result,
            "round-bearing event with no same-round decision must stay unmatched, "
            "not inherit another round's reason",
        )

    def test_ambiguous_duplicate_key_marked_not_silently_resolved(self):
        """When two decisions share the same (round, phase, actor, action, target),
        enrichment marks ambiguity instead of silently picking one."""
        run_dir = _write_run_dir(
            self._base_game_log([
                {"event_id": "e1", "round": 1, "phase": "night", "actor": "p1", "type": "werewolf_kill", "target": "p5", "data": {}},
            ]),
            self._base_decision_log([
                {"decision_id": "d1", "actor": "p1", "decision_scope": "team", "phase": "night", "round": 1, "action": "werewolf_kill", "target": "p5", "reason_summary": "wolf consensus kill", "decision_type": "team_coordinated", "visible_info_refs": []},
                {"decision_id": "d2", "actor": "p1", "decision_scope": "team", "phase": "night", "round": 1, "action": "werewolf_kill", "target": "p5", "reason_summary": "duplicate kill entry", "decision_type": "team_coordinated", "visible_info_refs": []},
            ]),
        )
        result = _load_decision_reasons(run_dir)
        self.assertIn("e1", result)
        self.assertEqual(result["e1"]["reason_source"], "ambiguous")
        self.assertIn("2 decisions match", result["e1"].get("reason_detail", ""))
        # decision_id and request_id should be empty for ambiguous entries
        self.assertEqual(result["e1"]["decision_id"], "")

    def test_legacy_decision_without_round_uses_greedy_fallback(self):
        """Decision log entries without round field fall back to greedy
        (actor, action, target) matching with legacy_no_round annotation."""
        run_dir = _write_run_dir(
            self._base_game_log([
                {"event_id": "e1", "round": 1, "phase": "night", "actor": "p1", "type": "werewolf_kill", "target": "p5", "data": {}},
            ]),
            self._base_decision_log([
                {"decision_id": "d1", "actor": "p1", "decision_scope": "team", "phase": "night", "action": "werewolf_kill", "target": "p5", "reason_summary": "wolf kill", "decision_type": "team_coordinated", "visible_info_refs": []},
                # No round field — legacy format
            ]),
        )
        result = _load_decision_reasons(run_dir)
        self.assertIn("e1", result)
        self.assertEqual(result["e1"]["reason_summary"], "wolf kill")
        self.assertEqual(result["e1"]["reason_source"], "legacy_no_round")

    def test_null_request_id_handled(self):
        """Wolf consensus decisions have request_id=None, which should appear as empty string."""
        run_dir = _write_run_dir(
            self._base_game_log([
                {"event_id": "e1", "round": 1, "phase": "night", "actor": "p1", "type": "werewolf_kill", "target": "p5", "data": {}},
            ]),
            self._base_decision_log([
                {"decision_id": "d1", "actor": "p1", "decision_scope": "team", "phase": "night", "round": 1, "action": "werewolf_kill", "target": "p5", "reason_summary": "wolf kill", "decision_type": "team_coordinated", "visible_info_refs": [], "request_id": None},
            ]),
        )
        result = _load_decision_reasons(run_dir)
        self.assertEqual(result["e1"]["request_id"], "")
        self.assertEqual(result["e1"]["reason_source"], "matched")

    def test_no_decision_log_returns_empty(self):
        """Missing decision-log.json should return empty dict, not raise."""
        d = tempfile.mkdtemp()
        dp = Path(d)
        (dp / "game-log.json").write_text(json.dumps(self._base_game_log([])), encoding="utf-8")
        # No decision-log.json
        result = _load_decision_reasons(dp)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()