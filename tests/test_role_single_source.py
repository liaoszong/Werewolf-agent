"""SYS-A2 role single-source sentinels (ADR 2026-06-11-role-facts-single-source).

known_role_teams() is THE source of role->team facts. The three former verbatim
copies (profile_config.ROLE_TEAMS / observer_visibility._KNOWN_ROLE_TEAMS /
runtime_events._KNOWN_ROLE_TEAMS) derive from it via observer_protocol, so a
role added to a ruleset can never be missing from a projection table again
(a wolf-side role missing from those tables would default to team "villager"
and LEAK its role string to villager observers instead of "unknown")."""
from __future__ import annotations

import os
import subprocess
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

    def test_runtime_events_table_is_the_protocol_object(self) -> None:
        # runtime_events resolves the table lazily (import-cycle constraint:
        # action_runtime.__init__ -> turn -> game_engine -> runtime_events),
        # but the object it returns must BE the protocol table, not a copy.
        from werewolf_eval import observer_protocol, runtime_events

        self.assertIs(
            runtime_events._known_role_teams(),
            observer_protocol.KNOWN_ROLE_TEAMS,
        )


class ProfileRoleTeamsTest(unittest.TestCase):
    def test_role_teams_is_gated_projection_with_pinned_order(self) -> None:
        from werewolf_eval import profile_config

        self.assertEqual(
            profile_config.ROLE_TEAMS,
            {
                "werewolf": "werewolf",
                "seer": "villager",
                "witch": "villager",
                "villager": "villager",
            },
        )
        # Pinned insertion order: serialized into the capabilities payload
        # (profile_config.py:480) — dict order is byte order there.
        self.assertEqual(
            list(profile_config.ROLE_TEAMS),
            ["werewolf", "seer", "witch", "villager"],
        )
        # The projection never invents a role outside the product gate.
        self.assertEqual(
            set(profile_config.ROLE_TEAMS), set(profile_config.ALLOWED_ROLES)
        )


class ColdImportTest(unittest.TestCase):
    """Each entry module must import cleanly as the FIRST import of a fresh
    interpreter. Same-process smoke tests are order-dependent and miss cycles:
    the runtime_events -> observer_protocol -> action_runtime edge is only
    circular when runtime_events loads first (via game_engine), which a warm
    sys.modules hides."""

    def test_cold_import_each_entry_module(self) -> None:
        src = str(Path(__file__).resolve().parents[1] / "src")
        env = dict(os.environ, PYTHONPATH=src)
        for module in (
            "werewolf_eval.game_engine",
            "werewolf_eval.runtime_events",
            "werewolf_eval.observer_protocol",
            "werewolf_eval.observer_visibility",
            "werewolf_eval.profile_config",
            "werewolf_eval.emergent_engine",
            "werewolf_eval.observer_server",
        ):
            proc = subprocess.run(
                [sys.executable, "-c", f"import {module}"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                proc.returncode, 0, f"cold import of {module} failed:\n{proc.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
