import json
import unittest
from unittest.mock import patch

from tests.fake_scribe import _FakeScribeProvider

from werewolf_eval.ablation.arms import Arm, layout_for
from werewolf_eval.ablation.harness import run_arm
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
)
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.roleplay_shadow_arm import ROLEPLAY_SHADOW_ARM_ID


def _fake_factory(arm, api_key):
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


def _fake_scribe_factory(arm, api_key):
    return lambda: ProviderAgent("scribe", _FakeScribeProvider())


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_public_manifest_has_no_hidden_identity(testcase, public_manifest):
    blob = json.dumps(public_manifest, ensure_ascii=False)
    forbidden = (
        "true_role",
        "role_policy",
        "runtime_seat_state",
        "runtime_team_state",
        "werewolf",
        "seer",
        "witch",
        "villager",
        "standard_werewolf",
        "standard_seer",
        "standard_witch",
        "standard_villager",
    )
    for marker in forbidden:
        testcase.assertNotIn(marker, blob)


class RoleplayShadowArmTests(unittest.TestCase):
    def test_run_arm_launches_six_player_roleplay_shadow_fake_game(self):
        with patch(
            "werewolf_eval.ablation.harness._check_run",
            return_value=[],
        ):
            arm = Arm(
                label="roleplay_shadow",
                prompt_version="prompt_v5",
                n_games=1,
                seed_base=7,
                roleplay_arm=ROLEPLAY_SHADOW_ARM_ID,
            )
            result = run_arm(
                arm,
                out_root=self.tmp_path,
                factory_builder=_fake_factory,
                scaffold_factory_builder=_fake_scribe_factory,
            )

        self.assertEqual(result["arm"], "roleplay_shadow")
        self.assertEqual(result["prompt_version"], "prompt_v5")
        self.assertEqual(result["roleplay_arm"], ROLEPLAY_SHADOW_ARM_ID)
        self.assertEqual(result["metrics"]["n_total"], 1)

        game_dir = self.tmp_path / "roleplay_shadow" / "roleplay_shadow_000"
        manifest = _json(game_dir / "prompt-manifest.json")
        self.assertEqual(manifest["evaluation_bucket"]["prompt_version"], "prompt_v5")
        public_manifest = manifest["roleplay_public_manifest"]
        self.assertEqual(public_manifest["roleplay_arm"], ROLEPLAY_SHADOW_ARM_ID)
        self.assertEqual(len(public_manifest["seats"]), 6)
        summaries = {
            seat["public_card"]["summary"] for seat in public_manifest["seats"]
        }
        self.assertGreaterEqual(len(summaries), 3)
        _assert_public_manifest_has_no_hidden_identity(self, public_manifest)

    def test_roleplay_shadow_artifacts_are_auditable_without_public_leaks(self):
        arm = Arm(
            label="roleplay_artifacts",
            prompt_version="prompt_v5",
            n_games=1,
            seed_base=7,
            roleplay_arm=ROLEPLAY_SHADOW_ARM_ID,
        )
        with patch(
            "werewolf_eval.ablation.harness._check_run",
            return_value=[],
        ):
            run_arm(
                arm,
                out_root=self.tmp_path,
                factory_builder=_fake_factory,
                scaffold_factory_builder=_fake_scribe_factory,
            )

        game_dir = self.tmp_path / "roleplay_artifacts" / "roleplay_artifacts_000"
        audit = _json(game_dir / "roleplay-audit.json")
        self.assertEqual(audit["roleplay_arm"], ROLEPLAY_SHADOW_ARM_ID)
        self.assertEqual(audit["visibility_scope"], "postgame_only")
        self.assertEqual(len(audit["seat_private_asset_snapshots"]), 6)

        seat_roles = layout_for(arm, 0)
        wolf_seats = sorted(
            seat_id for seat_id, role in seat_roles.items() if role == "werewolf"
        )
        faction_private = audit["faction_private_asset_snapshots"]
        self.assertEqual(len(faction_private), 1)
        self.assertEqual(faction_private[0]["visibility_scope"], "faction_private")
        self.assertEqual(faction_private[0]["team_id"], "werewolf")
        self.assertEqual(faction_private[0]["authorized_seat_ids"], wolf_seats)

        manifest = _json(game_dir / "prompt-manifest.json")
        _assert_public_manifest_has_no_hidden_identity(
            self,
            manifest["roleplay_public_manifest"],
        )

    def test_roleplay_shadow_context_and_call_accounting_are_scoped(self):
        arm = Arm(
            label="roleplay_context",
            prompt_version="prompt_v5",
            n_games=1,
            seed_base=7,
            roleplay_arm=ROLEPLAY_SHADOW_ARM_ID,
        )
        with patch(
            "werewolf_eval.ablation.harness._check_run",
            return_value=[],
        ):
            run_arm(
                arm,
                out_root=self.tmp_path,
                factory_builder=_fake_factory,
                scaffold_factory_builder=_fake_scribe_factory,
            )

        game_dir = self.tmp_path / "roleplay_context" / "roleplay_context_000"
        turns_doc = _json(game_dir / "provider-turns.json")
        roleplay_turns = [
            turn for turn in turns_doc["turns"] if turn.get("prompt_context_blocks")
        ]
        self.assertTrue(roleplay_turns)
        first_blocks = roleplay_turns[0]["prompt_context_blocks"]
        self.assertEqual(
            [block["block_name"] for block in first_blocks[:2]],
            ["seat_character_card", "role_policy"],
        )
        block_blob = json.dumps(first_blocks, ensure_ascii=False)
        self.assertNotIn("policy_id", block_blob)
        self.assertNotIn("true_role", block_blob)
        self.assertNotIn('"team":', block_blob)

        accounting = turns_doc["call_accounting"]
        self.assertEqual(len(accounting), len(turns_doc["turns"]))
        for row in accounting:
            self.assertIn("owner", row)
            self.assertIn("visibility_scope", row)
            self.assertIn("token_usage", row)
            self.assertIn("latency_ms", row)
            self.assertIn("context_block_hashes", row)
            self.assertIn("fallback_result", row)
        self.assertTrue(
            any(row["context_block_hashes"] for row in accounting),
            "roleplay arm must expose context block hashes for audit",
        )
        self.assertTrue(
            any(row["owner"].startswith("seat:") for row in accounting),
            "player model calls must be owned by seats",
        )
        self.assertTrue(
            any(row["owner"] == "scaffold:scribe" for row in accounting),
            "scribe calls must be accounted separately from seats",
        )

        trace = _json(game_dir / "provider-trace.json")
        seat_roles = layout_for(arm, 0)
        wolf_seats = {
            seat_id for seat_id, role in seat_roles.items() if role == "werewolf"
        }
        wolf_text = "\n".join(
            req["observation_text"]
            for req in trace["requests"]
            if req["actor"] in wolf_seats
        )
        non_wolf_text = "\n".join(
            req["observation_text"]
            for req in trace["requests"]
            if req["actor"] not in wolf_seats and req["actor"] != "scribe"
        )
        self.assertIn("【座位表现】", wolf_text)
        self.assertIn("TeamPlanRecord", wolf_text)
        self.assertNotIn("TeamPlanRecord", non_wolf_text)
        self.assertIn("this is not engine truth", wolf_text + non_wolf_text)

    def test_baseline_arm_runs_without_roleplay_assets(self):
        arm = Arm(
            label="baseline_no_roleplay",
            prompt_version="prompt_v1",
            n_games=1,
            seed_base=7,
        )
        with patch(
            "werewolf_eval.ablation.harness._check_run",
            return_value=[],
        ):
            result = run_arm(
                arm,
                out_root=self.tmp_path,
                factory_builder=_fake_factory,
            )

        self.assertNotIn("roleplay_arm", result)
        game_dir = self.tmp_path / "baseline_no_roleplay" / "baseline_no_roleplay_000"
        manifest = _json(game_dir / "prompt-manifest.json")
        self.assertNotIn("roleplay_public_manifest", manifest)
        turns_doc = _json(game_dir / "provider-turns.json")
        self.assertFalse(
            any(turn.get("prompt_context_blocks") for turn in turns_doc["turns"])
        )

    def setUp(self):
        import tempfile
        from pathlib import Path

        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
