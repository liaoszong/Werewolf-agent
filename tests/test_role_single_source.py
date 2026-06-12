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
    rules_v1_2,
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
                "guard": "villager",
            },
        )
        # Insertion order is load-bearing: profile_config.ROLE_TEAMS derives
        # from this and is serialized into the capabilities payload
        # (profile_config.py:480), where dict order = byte order.
        self.assertEqual(
            list(known_role_teams()),
            ["werewolf", "seer", "witch", "villager", "hunter", "guard"],
        )

    def test_all_rulesets_is_append_only(self) -> None:
        # Observers must recognize roles from logs of ANY shipped rules version.
        self.assertEqual(
            [rs.rules_version for rs in all_rulesets()],
            ["rules_v1", "rules_v1_1", "rules_v1_2"],
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
                "guard": "villager",
            },
        )
        # Pinned insertion order: serialized into the capabilities payload
        # (profile_config.py:480) — dict order is byte order there. guard lands
        # LAST (ruleset declaration order: rules_v1_2 appends it after hunter,
        # which the gate excludes).
        self.assertEqual(
            list(profile_config.ROLE_TEAMS),
            ["werewolf", "seer", "witch", "villager", "guard"],
        )
        # The projection never invents a role outside the product gate.
        self.assertEqual(
            set(profile_config.ROLE_TEAMS), set(profile_config.ALLOWED_ROLES)
        )


class GateAndOrderSentinelTest(unittest.TestCase):
    def test_product_gate_is_subset_of_ruleset_roles(self) -> None:
        # ALLOWED_ROLES is a deliberate explicit allowlist (new roles do NOT
        # auto-appear in the launch UI) — but it may never invent a role the
        # ruleset doesn't have.
        from werewolf_eval import profile_config

        self.assertLessEqual(
            set(profile_config.ALLOWED_ROLES), set(known_role_teams())
        )

    def test_night_dispatch_order_is_subset_of_ruleset_night_abilities(self) -> None:
        # NIGHT_DISPATCH_ORDER stays engine data until NightPlan (SYS-A1);
        # this sentinel only forbids it referencing an ability the ruleset
        # doesn't declare as phase:night.
        from werewolf_eval.emergent_engine import NIGHT_DISPATCH_ORDER

        night_ids = {
            a.action_id
            for a in rules_v1_2().abilities
            if a.trigger == "phase:night"
        }
        self.assertLessEqual(set(NIGHT_DISPATCH_ORDER), night_ids)


class ObserverProjectionCoverageSentinelTest(unittest.TestCase):
    def test_role_specific_visibility_constant_drives_projection(self) -> None:
        from werewolf_eval import observer_projection

        original = observer_projection.ROLE_SPECIFIC_EVENT_VISIBILITIES
        try:
            observer_projection.ROLE_SPECIFIC_EVENT_VISIBILITIES = frozenset(
                set(original) | {"sentinel_private_role"}
            )
            visible, reason = observer_projection.event_visible_in_projection(
                {"event_id": "e_sentinel", "visibility": "sentinel_private_role"},
                "role:p1",
                {
                    "p1": {
                        "role": "sentinel_private_role",
                        "team": "villager",
                        "role_source": "role_projection_snapshot",
                        "team_source": "role_projection_snapshot",
                    }
                },
            )
        finally:
            observer_projection.ROLE_SPECIFIC_EVENT_VISIBILITIES = original

        self.assertTrue(visible)
        self.assertEqual(reason, "sentinel_private_role_event")

    def test_ruleset_role_private_visibilities_are_projection_covered(self) -> None:
        from werewolf_eval import observer_projection, observer_protocol

        role_specific_visibilities = {
            ability.visibility
            for rs in all_rulesets()
            for ability in rs.abilities
            if ability.visibility not in observer_protocol.PUBLIC_EVENT_VISIBILITIES
            and ability.visibility not in observer_protocol.WEREWOLF_TEAM_EVENT_VISIBILITIES
        }
        self.assertLessEqual(
            role_specific_visibilities,
            set(observer_projection.ROLE_SPECIFIC_EVENT_VISIBILITIES),
        )
        for visibility in role_specific_visibilities:
            visible, reason = observer_projection.event_visible_in_projection(
                {"event_id": f"e_{visibility}", "visibility": visibility},
                "role:p1",
                {
                    "p1": {
                        "role": visibility,
                        "team": known_role_teams()[visibility],
                        "role_source": "role_projection_snapshot",
                        "team_source": "role_projection_snapshot",
                    }
                },
            )
            self.assertTrue(visible, visibility)
            self.assertEqual(reason, f"{visibility}_event")


class ScoringCoverageSentinelTest(unittest.TestCase):
    def test_key_villager_roles_cover_ruleset_special_villagers(self) -> None:
        from werewolf_eval.scoring_types import KEY_VILLAGER_ROLES

        special_villagers = {
            role_def.role
            for rs in all_rulesets()
            for role_def in rs.roles
            if role_def.team == "villager"
            and role_def.ability_ids != ("player_vote",)
        }
        self.assertLessEqual(special_villagers, KEY_VILLAGER_ROLES)


class InvariantCoverageSentinelTest(unittest.TestCase):
    def test_invariant_event_type_tables_cover_ruleset_abilities_by_family(self) -> None:
        from werewolf_eval.invariants import checker

        ability_ids = {
            ability.action_id
            for rs in all_rulesets()
            for ability in rs.abilities
        }
        death_like = {
            action_id
            for action_id in ability_ids
            if action_id.endswith(("_kill", "_poison", "_shoot"))
        }
        consume_like = {
            action_id
            for action_id in ability_ids
            if action_id.endswith(("_save", "_poison", "_shoot"))
        }
        self.assertLessEqual(set(checker.CONSUME_TYPES), ability_ids)
        self.assertLessEqual(set(checker.DEATH_CAUSE_TYPES), ability_ids)
        self.assertLessEqual(death_like, set(checker.DEATH_CAUSE_TYPES))
        self.assertLessEqual(consume_like, set(checker.CONSUME_TYPES))


class AblationCoverageSentinelTest(unittest.TestCase):
    def test_classify_event_handles_every_ruleset_ability_event_type(self) -> None:
        from werewolf_eval.ablation.metrics import classify_event

        for rs in all_rulesets():
            for ability in rs.abilities:
                kind = classify_event(
                    {
                        "type": ability.action_id,
                        "phase": "night",
                        "actor": "p1",
                        "target": "p2",
                        "data": {"summary": ""},
                    }
                )[0]
                self.assertNotEqual(kind, "other", ability.action_id)


class VocabCompletenessSentinelTest(unittest.TestCase):
    """Coverage-only sentinels. The prompt and display vocabularies are
    deliberately different wordings and must never be merged (prompt bytes are
    golden-locked); these tests only guarantee no role/team/ability that a
    ruleset can put on a board is missing a word in either vocabulary.

    Known coupling: the TYPE_LABELS check assumes an ability's emitted event
    type == its action_id (true for every ability today, e.g. hunter_shoot at
    emergent_engine.py:1080). A future ability emitting under a different name
    would force a label entry no renderer looks up — relax this check then."""

    def test_prompt_tables_cover_all_rulesets(self) -> None:
        from werewolf_eval import prompt_v2

        for rs in all_rulesets():
            for role_def in rs.roles:
                self.assertIn(role_def.role, prompt_v2.ROLE_NAMES_ZH)
                self.assertIn(role_def.team, prompt_v2.TEAM_NAMES_ZH)
            for ability in rs.abilities:
                self.assertIn(ability.action_id, prompt_v2.ABILITY_DESCRIPTIONS)

    def test_display_tables_cover_all_rulesets(self) -> None:
        from werewolf_eval import display_labels

        for rs in all_rulesets():
            for role_def in rs.roles:
                self.assertIn(role_def.role, display_labels.ROLE_LABELS)
                self.assertIn(role_def.team, display_labels.TEAM_LABELS)
            for ability in rs.abilities:
                self.assertIn(ability.action_id, display_labels.TYPE_LABELS)


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
