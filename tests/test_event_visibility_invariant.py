"""R-17 guard — engine-emitted private event types must carry the right visibility.

The whole leak model rests on each `_emit(...)` passing the correct visibility string;
nothing binds an event TYPE to its required visibility, so a copy-pasted "public" on a
private type (the visibility version of the witch_kill/witch_poison vocab class) would
silently expose seer/witch/wolf events. This guard runs both engine arcs and asserts
every emitted role-private event type carries exactly its required visibility, so such
a drift fails CI instead of leaking.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_engine import (
    EmergentGameEngine,
    build_emergent_config,
)
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
    build_werewolf_win_script,
)
from werewolf_eval.game_log import parse_game_log

# Canonical type -> required visibility for ROLE-PRIVATE event types. Public/narrative
# types (player_speech, player_vote, role_assignment, player_died, ...) are not listed:
# they are public and not part of the leak surface.
EVENT_TYPE_REQUIRED_VISIBILITY = {
    "seer_check": "seer",
    "witch_save": "witch",
    "witch_poison": "witch",
    "witch_pass": "witch",
    "guard_protect": "guard",
    "werewolf_kill": "werewolf_team",
}


class EventVisibilityInvariantTests(unittest.TestCase):
    def _all_events(self):
        events = []
        for make in (build_villager_win_script, build_werewolf_win_script):
            engine = EmergentGameEngine(
                config=build_emergent_config(game_id="vis_inv"),
                agents=build_emergent_fake_agents(make()),
                seed=0,
            )
            events.extend(parse_game_log(engine.run().game_log).events)
        return events

    def test_private_event_types_carry_required_visibility(self):
        events = self._all_events()
        offenders = [
            (e.event_id, e.type, e.visibility)
            for e in events
            if e.type in EVENT_TYPE_REQUIRED_VISIBILITY
            and e.visibility != EVENT_TYPE_REQUIRED_VISIBILITY[e.type]
        ]
        self.assertEqual(offenders, [], f"private event type emitted with wrong visibility: {offenders}")

    def test_invariant_actually_observes_private_events(self):
        # Guard the guard: ensure the run really produced some of these private types,
        # so the invariant isn't vacuously passing on an empty set.
        seen = {e.type for e in self._all_events()} & set(EVENT_TYPE_REQUIRED_VISIBILITY)
        self.assertTrue(seen, "expected the engine to emit role-private event types")


if __name__ == "__main__":
    unittest.main()
