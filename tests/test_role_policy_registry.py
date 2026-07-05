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


if __name__ == "__main__":
    unittest.main()
