import unittest
import json

from werewolf_eval.agent_assets import (
    AgentAssetValidationError,
    build_legacy_agent_asset_artifacts,
    require_runtime_team_state_authorized,
    validate_agent_preset,
    validate_execution_contract,
    validate_provider_profile,
    validate_role_policy,
    validate_runtime_seat_state,
    validate_runtime_team_state,
    validate_seat_character_card,
)
from werewolf_eval.profile_config import build_default_profile


class AgentAssetSchemaTests(unittest.TestCase):
    def test_accepts_minimal_p3a1_asset_layers(self):
        validate_seat_character_card(
            {
                "schema_version": "p3a.seat_character_card.v1",
                "card_id": "calm_logician",
                "version": "1.0.0",
                "display_name": "Calm Logician",
                "summary": "Careful, evidence-driven, reluctant to overclaim.",
                "role_scope": "role_agnostic",
                "asset_certification": {
                    "status": "built_in_vetted",
                    "attribution_eligible": True,
                },
            }
        )
        validate_role_policy(
            {
                "schema_version": "p3a.role_policy.v1",
                "policy_id": "standard_werewolf_balanced",
                "version": "1.0.0",
                "role": "werewolf",
                "applicability": {
                    "ruleset_id": "rules_v1_2",
                    "seat_count": [6],
                    "required_roles": ["werewolf", "seer", "witch", "villager"],
                    "phase_protocol_version": "phase_protocol_v2",
                },
                "fallback_policy": "reject",
                "goals": ["protect werewolf team identity"],
            }
        )
        validate_runtime_seat_state(
            {
                "schema_version": "p3a.runtime_seat_state.v1",
                "run_id": "run_123",
                "seat_id": "p2",
                "initialized_from": {
                    "seat_character_card_id": "calm_logician",
                    "role_policy_id": "standard_werewolf_balanced",
                    "provider_profile_id": "deepseek_flash_default",
                },
                "status": "active",
            }
        )
        validate_runtime_team_state(
            {
                "schema_version": "p3a.runtime_team_state.v1",
                "run_id": "run_123",
                "team_id": "werewolf",
                "visibility_scope": "faction_private",
                "authorized_seat_ids": ["p1", "p2"],
            }
        )
        validate_provider_profile(
            {
                "schema_version": "p3a.provider_profile.v1",
                "provider_profile_id": "deepseek_flash_default",
                "provider": "deepseek",
                "model": "deepseek-chat",
                "temperature": 0.8,
                "max_tokens": 256,
                "credential_slot": "deepseek",
            }
        )
        validate_execution_contract(
            {
                "schema_version": "p3a.execution_contract.v1",
                "execution_contract_id": "baseline_prompt_v1_action_runtime_v1_2",
                "prompt_template_version": "prompt_v1",
                "prompt_renderer_version": "prompt_renderer_v1",
                "action_schema_version": "g1d-action-v1",
                "tool_capability_manifest_version": "none",
                "context_selector_version": "legacy_visible_events_v1",
                "response_parser_version": "provider_agent_json_v1",
                "visibility_oracle_version": "i4b_v1",
            }
        )
        validate_agent_preset(
            {
                "schema_version": "p3a.agent_preset.v1",
                "preset_id": "reserved_deduction_player",
                "display_name": "Reserved Deduction Player",
                "seat_character_card_ref": "calm_logician@1.0.0",
                "role_policy_pack_refs": {
                    "werewolf": "standard_werewolf_balanced@1.0.0",
                },
                "provider_profile_ref": "deepseek_flash_default",
            }
        )


class LegacyAgentAssetProjectionTests(unittest.TestCase):
    def test_legacy_profile_projection_splits_public_and_private_audiences(self):
        artifacts = build_legacy_agent_asset_artifacts(
            build_default_profile(),
            run_id="run_p3a1",
        )

        public = artifacts["public_run_manifest"]
        public_blob = json.dumps(public, ensure_ascii=False)
        self.assertEqual(public["schema_version"], "p3a.public_run_manifest.v1")
        self.assertEqual(public["visibility_scope"], "public")
        self.assertNotIn("true_role", public_blob)
        self.assertNotIn("role_policy", public_blob)
        self.assertNotIn("runtime_seat_state_ref", public_blob)
        self.assertNotIn("runtime_team_state_ref", public_blob)
        for hidden_word in ("werewolf", "seer", "witch", "villager"):
            self.assertNotIn(hidden_word, public_blob)

        seat_private = artifacts["seat_private_asset_snapshots"]
        self.assertEqual(len(seat_private), 6)
        wolf_private = next(
            seat for seat in seat_private if seat["true_role"] == "werewolf"
        )
        self.assertEqual(wolf_private["visibility_scope"], "seat_private")
        self.assertEqual(wolf_private["team"], "werewolf")
        self.assertIn("role_policy_ref", wolf_private)
        self.assertIn("runtime_seat_state_ref", wolf_private)

        faction_private = artifacts["faction_private_asset_snapshots"]
        self.assertEqual(len(faction_private), 1)
        self.assertEqual(faction_private[0]["team_id"], "werewolf")
        self.assertEqual(faction_private[0]["visibility_scope"], "faction_private")
        self.assertEqual(sorted(faction_private[0]["authorized_seat_ids"]), ["p1", "p2"])

    def test_human_seat_has_no_player_provider_profile_ref(self):
        profile = build_default_profile()
        profile["seat_overrides"] = {
            "p3": {"provider": "human", "model": "none", "strategy": "default"}
        }

        artifacts = build_legacy_agent_asset_artifacts(profile, run_id="run_human")

        p3_public = next(
            seat
            for seat in artifacts["public_run_manifest"]["seats"]
            if seat["seat_id"] == "p3"
        )
        self.assertEqual(p3_public["controller"], "human")
        self.assertNotIn("provider_profile_summary", p3_public)
        p3_private = next(
            seat
            for seat in artifacts["seat_private_asset_snapshots"]
            if seat["seat_id"] == "p3"
        )
        self.assertEqual(p3_private["controller"], "human")
        self.assertNotIn("provider_profile_ref", p3_private)

    def test_seat_override_prompt_becomes_legacy_overlay_not_role_policy(self):
        profile = build_default_profile()
        profile["role_defaults"]["werewolf"]["prompt"] = "ROLE_DEFAULT_WOLF"
        profile["seat_overrides"] = {"p1": {"prompt": "SEAT_OVERRIDE_PROMPT"}}

        artifacts = build_legacy_agent_asset_artifacts(profile, run_id="run_overlay")

        p1_private = next(
            seat
            for seat in artifacts["seat_private_asset_snapshots"]
            if seat["seat_id"] == "p1"
        )
        self.assertTrue(p1_private["legacy_bridge"]["used_legacy_prompt_overlay"])
        self.assertEqual(
            p1_private["role_policy_ref"]["policy_selection_reason"],
            "legacy_role_defaults_prompt",
        )
        self.assertEqual(
            p1_private["legacy_prompt_overlay"]["origin_path"],
            "seat_overrides.p1.prompt",
        )
        self.assertEqual(
            p1_private["legacy_prompt_overlay"]["classification"],
            "legacy_opaque",
        )


class RuntimeTeamStateAuthorizationTests(unittest.TestCase):
    def test_team_state_requires_authorized_seat(self):
        state = {
            "schema_version": "p3a.runtime_team_state.v1",
            "run_id": "run_123",
            "team_id": "werewolf",
            "visibility_scope": "faction_private",
            "authorized_seat_ids": ["p1", "p2"],
        }

        self.assertIs(require_runtime_team_state_authorized(state, "p1"), state)
        with self.assertRaises(AgentAssetValidationError):
            require_runtime_team_state_authorized(state, "p3")
