"""R-06 guard — the two visibility implementations must not drift into a leak.

Two filters decide who sees an event:
  * `observer_protocol.event_visible_to_perspective`  — used by /events and /stream
    (the highest-traffic live surfaces).
  * `observer_visibility.event_visible_in_projection` — used by /projection.

They are intentionally NOT identical (the projection path additionally unlocks
role-private events for a *trusted* seat), so a naive equality test is wrong. The
security-meaningful invariant is a SUBSET relation: the protocol filter must never
expose MORE than the untrusted projection baseline. If a future edit widens the
protocol path (e.g. lets role:pN see seer/witch on /events), this fails — exactly
the "one change flips it to a leak" risk R-06 flagged. Plus a constant-drift guard
on the duplicated visibility frozensets.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.observer_protocol import (
    PUBLIC_EVENT_VISIBILITIES,
    WEREWOLF_TEAM_EVENT_VISIBILITIES,
    event_visible_to_perspective,
)
from werewolf_eval.observer_visibility import (
    PUBLIC_LIKE_EVENT_VISIBILITIES,
    event_visible_in_projection,
)
from werewolf_eval.observer_visibility import (
    WEREWOLF_TEAM_EVENT_VISIBILITIES as VIS_WEREWOLF_TEAM_EVENT_VISIBILITIES,
)

_VISIBILITIES = [
    "public",
    "all",
    "seer",
    "witch",
    "werewolf_team",
    "internal",
    "some_future_role",  # an unknown visibility must stay hidden on both paths
]
_PERSPECTIVES = ["god", "public", "team:werewolf", "role:p1", "role:p3", "role:p6"]


class VisibilityParityTests(unittest.TestCase):
    def test_protocol_never_shares_more_than_untrusted_projection(self):
        # Empty seat_index => the projection authority's UNTRUSTED baseline (no role is
        # trusted, so role:pN sees only public/all). The protocol filter must be a
        # subset of that: protocol-visible implies projection-visible.
        for visibility in _VISIBILITIES:
            event = {"visibility": visibility, "event_id": "e1"}
            for perspective in _PERSPECTIVES:
                proto = event_visible_to_perspective(event, perspective)
                proj = event_visible_in_projection(event, perspective, {})[0]
                if proto:
                    self.assertTrue(
                        proj,
                        f"/events filter exposes visibility={visibility!r} to "
                        f"{perspective!r} that the untrusted projection baseline hides "
                        f"— a divergence-into-leak (R-06).",
                    )

    def test_role_perspective_is_public_only_on_protocol_path(self):
        # Lock the current (safe) protocol behaviour: a role:pN seat on /events/stream
        # sees public/all only — never seer/witch/werewolf_team.
        for visibility in ["seer", "witch", "werewolf_team"]:
            event = {"visibility": visibility, "event_id": "e1"}
            self.assertFalse(event_visible_to_perspective(event, "role:p3"))

    def test_visibility_frozensets_do_not_drift(self):
        # The two modules keep duplicate frozensets; if they drift, the two filters
        # silently disagree on public/werewolf_team. Pin them equal.
        self.assertEqual(
            set(PUBLIC_EVENT_VISIBILITIES), set(PUBLIC_LIKE_EVENT_VISIBILITIES)
        )
        self.assertEqual(
            set(WEREWOLF_TEAM_EVENT_VISIBILITIES),
            set(VIS_WEREWOLF_TEAM_EVENT_VISIBILITIES),
        )


if __name__ == "__main__":
    unittest.main()
