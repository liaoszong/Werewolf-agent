import json
import copy
import tempfile
import unittest
from pathlib import Path

from werewolf_eval.agent_assets import validate_role_policy
from werewolf_eval.role_policy_registry import (
    RolePolicyRegistry,
    RolePolicyRegistryError,
    build_default_role_policy_registry,
)


class RolePolicyRegistryTests(unittest.TestCase):
    def test_default_registry_exposes_six_player_balanced_pack(self):
        registry = build_default_role_policy_registry()

        pack = registry.get_pack("standard_six_player_balanced")

        self.assertEqual(pack["schema_version"], "p3a.role_policy_pack.v1")
        self.assertEqual(pack["pack_id"], "standard_six_player_balanced")
        self.assertEqual(pack["version"], "1.0.0")
        self.assertEqual(
            set(pack["role_policy_refs"]),
            {"werewolf", "seer", "witch", "villager", "guard", "hunter"},
        )
        for role, ref in pack["role_policy_refs"].items():
            policy = registry.resolve_policy_ref(ref)
            self.assertEqual(policy["role"], role)
            validate_role_policy(policy)

    def test_create_draft_does_not_change_published_pack(self):
        registry = build_default_role_policy_registry()
        before_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["werewolf"]

        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="werewolf",
            changes={"goals": ["hide team identity", "push wrong votes"]},
        )

        after_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["werewolf"]
        self.assertEqual(after_ref, before_ref)
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(draft["role"], "werewolf")
        self.assertEqual(draft["policy"]["goals"], ["hide team identity", "push wrong votes"])
        validate_role_policy(draft["policy"])

    def test_publish_unreferenced_draft_updates_pack_ref_in_place(self):
        registry = build_default_role_policy_registry()
        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"policy_id": "local_seer_information_lead"},
        )

        published = registry.publish_draft(
            draft["draft_id"],
            referenced_policy_refs=set(),
        )

        pack = registry.get_pack("standard_six_player_balanced")
        self.assertEqual(
            pack["role_policy_refs"]["seer"],
            "local_seer_information_lead@1.0.0",
        )
        self.assertEqual(published["policy_id"], "local_seer_information_lead")
        self.assertEqual(published["version"], "1.0.0")

    def test_publish_referenced_policy_creates_new_version(self):
        registry = build_default_role_policy_registry()
        old_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["witch"]
        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="witch",
            changes={"goals": ["preserve potion value", "act on high-confidence evidence"]},
        )

        published = registry.publish_draft(
            draft["draft_id"],
            referenced_policy_refs={old_ref},
        )

        new_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["witch"]
        self.assertNotEqual(new_ref, old_ref)
        self.assertTrue(new_ref.endswith("@1.0.1"))
        self.assertEqual(published["version"], "1.0.1")
        self.assertEqual(registry.resolve_policy_ref(old_ref)["version"], "1.0.0")

    def test_rejects_forbidden_ownership_fields(self):
        registry = build_default_role_policy_registry()

        forbidden_fields = [
            "seat_character_card_ref",
            "provider_profile_ref",
            "execution_contract_ref",
            "runtime_state_ref",
            "team_plan",
            "extra_call_budget",
            "visibility_entitlement",
            "legal_action_window",
        ]
        for field in forbidden_fields:
            with self.subTest(field=field):
                with self.assertRaises(RolePolicyRegistryError):
                    registry.create_draft(
                        pack_id="standard_six_player_balanced",
                        role="villager",
                        changes={field: "forbidden"},
                    )

    def test_rejects_nested_forbidden_ownership_fields(self):
        registry = build_default_role_policy_registry()

        nested_payloads = [
            {"team_policy": {"team_plan_ref": "runtime_team_state_1"}},
            {"ability_use_policy": {"legal_action_window": "night:any"}},
            {"claim_policy": {"visibility_entitlement": "god_view"}},
            {"ability_use_policy": {"model_call_budget": 2}},
            {"ability_use_policy": {"tool_rounds": 2}},
            {"team_policy": {"timeout_budget_seconds": 90}},
            {"claim_policy": {"provider_profile_id": "deepseek_default"}},
            {"team_policy": {"Team_Plan": "runtime_team_state_1"}},
            {"team_policy": {"TEAM_PLAN_REF": "runtime_team_state_1"}},
            {"claim_policy": {"providerProfileId": "deepseek_default"}},
            {"ability_use_policy": {"modelCallBudget": 2}},
            {"ability_use_policy": {"toolRounds": 2}},
            {"team_policy": {"timeoutBudgetSeconds": 90}},
            {"ability_use_policy": {"legalActionWindow": "night:any"}},
            {"claim_policy": {"visibilityEntitlement": "god_view"}},
            {"ability_use_policy": {"runtime_agent_state_ref": "state_1"}},
            {"ability_use_policy": {"runtimeAgentStateRef": "state_1"}},
            {"team_policy": {"runtime_team_state_ref": "team_state_1"}},
            {"team_policy": {"teamStatePermissions": "wolf_private"}},
            {"ability_use_policy": {"action_window": "night:any"}},
            {"claim_policy": {"engine_entitlement": "god_view"}},
        ]
        for changes in nested_payloads:
            with self.subTest(changes=changes):
                with self.assertRaises(RolePolicyRegistryError):
                    registry.create_draft(
                        pack_id="standard_six_player_balanced",
                        role="werewolf",
                        changes=changes,
                    )

    def test_rejects_structured_values_in_strategy_lists(self):
        registry = build_default_role_policy_registry()

        payloads = [
            {"information_priorities": [{"engine_entitlement": "god_view"}]},
            {"playbook_refs": [{"action_window": "night:any"}]},
            {"forbidden_behavior": [{"teamStatePermissions": "wolf_private"}]},
        ]
        for changes in payloads:
            with self.subTest(changes=changes):
                with self.assertRaises(RolePolicyRegistryError):
                    registry.create_draft(
                        pack_id="standard_six_player_balanced",
                        role="seer",
                        changes=changes,
                    )

    def test_accepts_supported_policy_section_fields(self):
        registry = build_default_role_policy_registry()

        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={
                "ability_use_policy": {
                    "seer_check": "prioritize high-impact low-trust claims"
                },
                "claim_policy": {
                    "identity_claims": "reveal only after a useful check chain"
                },
                "deception_policy": {
                    "allowed": False,
                    "style": "avoid false claims",
                },
            },
        )

        self.assertEqual(
            draft["policy"]["ability_use_policy"]["seer_check"],
            "prioritize high-impact low-trust claims",
        )
        self.assertFalse(draft["policy"]["deception_policy"]["allowed"])

    def test_rejects_secret_like_values(self):
        registry = build_default_role_policy_registry()

        with self.assertRaises(RolePolicyRegistryError):
            registry.create_draft(
                pack_id="standard_six_player_balanced",
                role="villager",
                changes={"goals": ["use sk-test-secret"]},
            )

    def test_round_trips_to_file(self):
        registry = build_default_role_policy_registry()
        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="guard",
            changes={"goals": ["protect high-value public targets"]},
        )
        registry.publish_draft(draft["draft_id"], referenced_policy_refs=set())

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "role-policy-registry.json"
            registry.save(path)

            loaded = RolePolicyRegistry.load(path)

        self.assertEqual(
            loaded.get_pack("standard_six_player_balanced")["role_policy_refs"],
            registry.get_pack("standard_six_player_balanced")["role_policy_refs"],
        )
        self.assertEqual(loaded.export(), registry.export())

    def test_parallel_referenced_drafts_do_not_overwrite_versions(self):
        registry = build_default_role_policy_registry()
        old_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["seer"]
        first = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["publish first branch"]},
        )
        second = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["publish second branch"]},
        )

        first_policy = registry.publish_draft(
            first["draft_id"],
            referenced_policy_refs={old_ref},
        )
        self.assertEqual(first_policy["version"], "1.0.1")
        first_ref = f"{first_policy['policy_id']}@{first_policy['version']}"
        with self.assertRaises(RolePolicyRegistryError):
            registry.publish_draft(
                second["draft_id"],
                referenced_policy_refs={old_ref, first_ref},
            )
        self.assertEqual(
            registry.resolve_policy_ref(first_ref)["goals"],
            ["publish first branch"],
        )
        self.assertEqual(
            registry.get_pack("standard_six_player_balanced")["role_policy_refs"][
                "seer"
            ],
            first_ref,
        )

    def test_publish_rejects_existing_policy_ref_collision(self):
        registry = build_default_role_policy_registry()
        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"policy_id": "standard_werewolf_balanced"},
        )

        with self.assertRaises(RolePolicyRegistryError):
            registry.publish_draft(
                draft["draft_id"],
                referenced_policy_refs=set(),
            )

    def test_publish_rejects_stale_draft_without_current_ref(self):
        registry = build_default_role_policy_registry()
        old_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["seer"]
        first = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"policy_id": "local_seer_first"},
        )
        second = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["stale branch"]},
        )
        first_policy = registry.publish_draft(
            first["draft_id"],
            referenced_policy_refs=set(),
        )
        self.assertNotEqual(
            registry.get_pack("standard_six_player_balanced")["role_policy_refs"][
                "seer"
            ],
            old_ref,
        )

        with self.assertRaises(RolePolicyRegistryError):
            registry.publish_draft(
                second["draft_id"],
                referenced_policy_refs={old_ref},
            )
        self.assertEqual(
            registry.get_pack("standard_six_player_balanced")["role_policy_refs"][
                "seer"
            ],
            f"{first_policy['policy_id']}@{first_policy['version']}",
        )

    def test_publish_rejects_stale_draft_even_when_current_ref_is_referenced(self):
        registry = build_default_role_policy_registry()
        first = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"policy_id": "local_seer_first"},
        )
        second = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["stale branch"]},
        )
        first_policy = registry.publish_draft(
            first["draft_id"],
            referenced_policy_refs=set(),
        )
        current_ref = f"{first_policy['policy_id']}@{first_policy['version']}"

        with self.assertRaises(RolePolicyRegistryError):
            registry.publish_draft(
                second["draft_id"],
                referenced_policy_refs={current_ref},
            )
        self.assertEqual(
            registry.get_pack("standard_six_player_balanced")["role_policy_refs"][
                "seer"
            ],
            current_ref,
        )

    def test_publish_rejects_parallel_in_place_draft_without_current_ref(self):
        registry = build_default_role_policy_registry()
        old_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["seer"]
        first = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["first branch"]},
        )
        second = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["second branch"]},
        )
        first_policy = registry.publish_draft(
            first["draft_id"],
            referenced_policy_refs=set(),
        )

        with self.assertRaises(RolePolicyRegistryError):
            registry.publish_draft(
                second["draft_id"],
                referenced_policy_refs=set(),
            )
        first_ref = f"{first_policy['policy_id']}@{first_policy['version']}"
        self.assertNotEqual(first_ref, old_ref)
        self.assertEqual(
            registry.resolve_policy_ref(first_ref)["goals"],
            ["first branch"],
        )

    def test_publish_shared_pack_ref_creates_new_version(self):
        registry = build_default_role_policy_registry()
        data = registry.export()
        data["packs"]["experimental_pack"] = copy.deepcopy(
            data["packs"]["standard_six_player_balanced"]
        )
        data["packs"]["experimental_pack"]["pack_id"] = "experimental_pack"
        registry = RolePolicyRegistry(
            packs=data["packs"],
            policies=data["policies"],
            drafts=data["drafts"],
        )
        old_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["seer"]
        old_goals = registry.resolve_policy_ref(old_ref)["goals"]
        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["local pack seer branch"]},
        )

        published = registry.publish_draft(
            draft["draft_id"],
            referenced_policy_refs=set(),
        )

        new_ref = registry.get_pack("standard_six_player_balanced")[
            "role_policy_refs"
        ]["seer"]
        self.assertNotEqual(new_ref, old_ref)
        self.assertEqual(new_ref, f"{published['policy_id']}@1.0.1")
        self.assertEqual(
            registry.get_pack("experimental_pack")["role_policy_refs"]["seer"],
            old_ref,
        )
        self.assertEqual(registry.resolve_policy_ref(old_ref)["goals"], old_goals)
        self.assertEqual(
            registry.resolve_policy_ref(new_ref)["goals"],
            ["local pack seer branch"],
        )

    def test_load_rejects_pack_role_ref_mismatch(self):
        registry = build_default_role_policy_registry()
        data = registry.export()
        data["packs"]["standard_six_player_balanced"]["role_policy_refs"][
            "seer"
        ] = data["packs"]["standard_six_player_balanced"]["role_policy_refs"][
            "werewolf"
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad-role-policy-registry.json"
            path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaises(RolePolicyRegistryError):
                RolePolicyRegistry.load(path)

    def test_load_rejects_draft_role_policy_mismatch(self):
        registry = build_default_role_policy_registry()
        draft = registry.create_draft(
            pack_id="standard_six_player_balanced",
            role="seer",
            changes={"goals": ["seer draft"]},
        )
        data = registry.export()
        data["drafts"][draft["draft_id"]]["policy"] = registry.resolve_policy_ref(
            data["packs"]["standard_six_player_balanced"]["role_policy_refs"][
                "werewolf"
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad-draft-role-policy-registry.json"
            path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaises(RolePolicyRegistryError):
                RolePolicyRegistry.load(path)


if __name__ == "__main__":
    unittest.main()
