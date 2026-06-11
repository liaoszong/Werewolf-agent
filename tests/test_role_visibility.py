"""B-2: unit tests for the shared engine-side visibility rule + witness sentinel.

The rule itself is security-bearing (P2-A-2 no-feed-leak gate renders prompts from
these id sets); the sentinel locks the SYS-A4/I4b witness boundary (observer +
invariants oracle must stay independent implementations)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.role_visibility import private_refs_for_role, public_refs


def _e(eid: str, vis: str) -> dict:
    return {"event_id": eid, "visibility": vis}


EVENTS = [
    _e("e1", "public"),
    _e("e2", "all"),
    _e("e3", "seer"),
    _e("e4", "witch"),
    _e("e5", "werewolf_team"),
    _e("e6", "internal"),
    _e("e7", "guard"),
    _e("e8", "some_future_visibility"),
]


class PublicRefsTest(unittest.TestCase):
    def test_public_and_all_only_in_event_order(self):
        self.assertEqual(public_refs(EVENTS), ["e1", "e2"])

    def test_empty(self):
        self.assertEqual(public_refs([]), [])


class PrivateRefsForRoleTest(unittest.TestCase):
    def test_seer(self):
        self.assertEqual(private_refs_for_role(EVENTS, "seer"), ["e2", "e3"])

    def test_witch(self):
        self.assertEqual(private_refs_for_role(EVENTS, "witch"), ["e2", "e4"])

    def test_werewolf_gets_team_channel(self):
        self.assertEqual(private_refs_for_role(EVENTS, "werewolf"), ["e2", "e5"])

    def test_guard_role_match_is_generic(self):
        self.assertEqual(private_refs_for_role(EVENTS, "guard"), ["e2", "e7"])

    def test_villager_sees_all_only(self):
        self.assertEqual(private_refs_for_role(EVENTS, "villager"), ["e2"])

    def test_internal_and_unknown_visibilities_stay_hidden_from_everyone(self):
        for role in ("villager", "seer", "witch", "werewolf", "guard", "hunter"):
            refs = private_refs_for_role(EVENTS, role)
            self.assertNotIn("e6", refs)
            self.assertNotIn("e8", refs)
        self.assertNotIn("e6", public_refs(EVENTS))
        self.assertNotIn("e8", public_refs(EVENTS))


class WitnessBoundarySentinelTest(unittest.TestCase):
    """SYS-A4 dual-witness / I4b anti-circularity: the observer-side filters and the
    invariants oracle must stay INDEPENDENT implementations of the visibility rule.
    If one of them starts importing role_visibility, the leak net would check the
    engine against itself."""

    def test_observer_and_oracle_do_not_reference_role_visibility(self):
        src = ROOT / "src" / "werewolf_eval"
        witnesses = [
            src / "observer_visibility.py",
            src / "observer_protocol.py",
            *sorted((src / "invariants").glob("*.py")),
        ]
        offenders = [
            p.name
            for p in witnesses
            if "role_visibility" in p.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])
