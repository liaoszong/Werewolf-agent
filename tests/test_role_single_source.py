"""SYS-A2 role single-source sentinels (ADR 2026-06-11-role-facts-single-source).

known_role_teams() is THE source of role->team facts. The three former verbatim
copies (profile_config.ROLE_TEAMS / observer_visibility._KNOWN_ROLE_TEAMS /
runtime_events._KNOWN_ROLE_TEAMS) derive from it via observer_protocol, so a
role added to a ruleset can never be missing from a projection table again
(a wolf-side role missing from those tables would default to team "villager"
and LEAK its role string to villager observers instead of "unknown")."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import (  # noqa: E402
    all_rulesets,
    known_role_teams,
    rules_v1_1,
)


class KnownRoleTeamsTest(unittest.TestCase):
    def test_union_over_all_rulesets_in_declaration_order(self) -> None:
        self.assertEqual(
            known_role_teams(),
            {
                "werewolf": "werewolf",
                "seer": "villager",
                "witch": "villager",
                "villager": "villager",
                "hunter": "villager",
            },
        )
        # Insertion order is load-bearing: profile_config.ROLE_TEAMS derives
        # from this and is serialized into the capabilities payload
        # (profile_config.py:480), where dict order = byte order.
        self.assertEqual(
            list(known_role_teams()),
            ["werewolf", "seer", "witch", "villager", "hunter"],
        )

    def test_all_rulesets_is_append_only(self) -> None:
        # Observers must recognize roles from logs of ANY shipped rules version.
        self.assertEqual(
            [rs.rules_version for rs in all_rulesets()],
            ["rules_v1", "rules_v1_1"],
        )


class ProtocolReExportTest(unittest.TestCase):
    def test_protocol_table_is_the_ruleset_projection(self) -> None:
        from werewolf_eval import observer_protocol

        self.assertEqual(observer_protocol.KNOWN_ROLE_TEAMS, known_role_teams())


class DerivedCopiesTest(unittest.TestCase):
    def test_observer_visibility_table_is_the_protocol_object(self) -> None:
        from werewolf_eval import observer_protocol, observer_visibility

        self.assertIs(
            observer_visibility._KNOWN_ROLE_TEAMS,
            observer_protocol.KNOWN_ROLE_TEAMS,
        )


if __name__ == "__main__":
    unittest.main()
