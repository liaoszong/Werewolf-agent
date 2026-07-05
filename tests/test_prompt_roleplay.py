import json
import unittest

from werewolf_eval.agent_context_packet import AGENT_CONTEXT_PACKET_SCHEMA_VERSION
from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
)
from werewolf_eval.prompt_renderers import get_renderer
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.role_policy_registry import build_default_role_policy_registry
from tests.fake_scribe import _FakeScribeProvider


def _record(record_id, *, kind, summary, visibility_scope="public", audience_scope=None):
    render_mode = "quoted_evidence" if kind == "ClaimRecord" else "state_summary"
    return {
        "record_id": record_id,
        "kind": kind,
        "section": "public_timeline" if kind == "ClaimRecord" else "episodic_notes",
        "writer": "public_event" if kind == "ClaimRecord" else "seat_agent",
        "visibility_scope": visibility_scope,
        "audience_scope": audience_scope or {"seat_ids": []},
        "trust_class": "run_derived",
        "render_mode": render_mode,
        "source_provenance": {
            "source_event_ids": ["evt_1"],
            "generated_by": "test_runtime",
        },
        "status": "active",
        "summary": summary,
    }


def _packet(records):
    return {
        "schema_version": AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
        "run_id": "run_1",
        "seat_id": "p1",
        "decision_id": "day1_speech_p1",
        "records": records,
        "context_budget": {
            "included_blocks": [],
            "compacted_blocks": [],
            "dropped_blocks": [],
        },
    }


class PromptRoleplayRendererTest(unittest.TestCase):
    def test_v5_renders_role_policy_and_context_blocks_without_hidden_refs(self):
        registry = build_default_role_policy_registry()
        pack = registry.get_pack("standard_six_player_balanced")
        policy = registry.resolve_policy_ref(pack["role_policy_refs"]["werewolf"])
        packet = _packet(
            [
                _record("claim_1", kind="ClaimRecord", summary="p3 claimed seer"),
                _record(
                    "belief_1",
                    kind="BeliefRecord",
                    summary="p1 suspects p3 based on vote pressure",
                    visibility_scope="seat_private",
                    audience_scope={"seat_ids": ["p1"]},
                ),
            ]
        )

        rendered = get_renderer("prompt_v5").roleplay_context_suffix(
            role_policy=policy,
            agent_context_packet=packet,
            seat_id="p1",
            team_ids={"werewolf"},
        )

        self.assertTrue(rendered["text"].startswith("\n【角色策略】"))
        self.assertLess(
            rendered["text"].index("【角色策略】"),
            rendered["text"].index("【上下文记忆】"),
        )
        self.assertIn("hide team identity", rendered["text"])
        self.assertIn("Claim: a seat claimed p3 claimed seer", rendered["text"])
        self.assertIn("Belief: this agent currently believes", rendered["text"])
        self.assertEqual(
            [block["block_name"] for block in rendered["blocks"]],
            ["role_policy", "agent_context"],
        )
        for block in rendered["blocks"]:
            self.assertIn("trust_class", block)
            self.assertIn("render_mode", block)
            self.assertIn("visibility_scope", block)
            self.assertIn("source_provenance", block)
            self.assertRegex(block["content_hash"], r"^sha256:[0-9a-f]{64}$")

        blob = json.dumps(rendered, ensure_ascii=False)
        self.assertNotIn(policy["policy_id"], blob)
        self.assertNotIn(policy["version"], blob)
        self.assertNotIn("standard_werewolf_balanced@1.0.0", blob)
        self.assertNotIn('"role": "werewolf"', blob)
        self.assertNotIn('"team": "werewolf"', blob)

    def test_v5_context_respects_faction_private_authorization(self):
        team_plan = {
            "record_id": "wolf_plan_1",
            "kind": "TeamPlanRecord",
            "section": "team_memory",
            "writer": "team_scaffold",
            "visibility_scope": "faction_private",
            "audience_scope": {
                "team_ids": ["werewolf"],
                "authorized_seat_ids": ["p1", "p2"],
            },
            "trust_class": "run_derived",
            "render_mode": "state_summary",
            "source_provenance": {
                "source_event_ids": ["evt_wolf_1"],
                "generated_by": "team_scaffold",
            },
            "status": "active",
            "summary": "pressure p3 without exposing both wolves",
        }
        packet = _packet([team_plan])

        wolf_view = get_renderer("prompt_v5").roleplay_context_suffix(
            role_policy=None,
            agent_context_packet=packet,
            seat_id="p1",
            team_ids={"werewolf"},
        )
        villager_view = get_renderer("prompt_v5").roleplay_context_suffix(
            role_policy=None,
            agent_context_packet=packet,
            seat_id="p3",
            team_ids={"villager"},
        )

        self.assertIn("pressure p3", wolf_view["text"])
        self.assertNotIn("pressure p3", villager_view["text"])
        self.assertEqual(villager_view["blocks"], [])


class PromptRoleplayEngineConsumptionTest(unittest.TestCase):
    def test_prompt_v5_engine_injects_roleplay_context_and_records_block_metadata(self):
        agents = build_emergent_fake_agents(build_villager_win_script())
        registry = build_default_role_policy_registry()
        packet = _packet(
            [
                _record("claim_1", kind="ClaimRecord", summary="p3 claimed seer"),
                _record(
                    "belief_1",
                    kind="BeliefRecord",
                    summary="p1 suspects p3 based on vote pressure",
                    visibility_scope="seat_private",
                    audience_scope={"seat_ids": ["p1"]},
                ),
            ]
        )
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="v5_roleplay"),
            agents=agents,
            seed=7,
            prompt_version="prompt_v5",
            scaffold_agent=ProviderAgent("scribe", _FakeScribeProvider()),
            role_policy_registry=registry,
            agent_context_packets={"p1": packet},
        )

        engine._emit("setup", 0, "role_assignment", "system", "none", "public", "setup")
        engine._resolve_speech("p1", 1)

        request = agents["p1"].provider.requests[-1]
        self.assertIn("【角色策略】", request.observation_text)
        self.assertIn("hide team identity", request.observation_text)
        self.assertIn("【上下文记忆】", request.observation_text)
        self.assertIn("p3 claimed seer", request.observation_text)

        turn = [
            turn for turn in engine._provider_turns
            if turn["actor"] == "p1" and turn["response_kind"] == "speech"
        ][0]
        self.assertEqual(
            [block["block_name"] for block in turn["prompt_context_blocks"]],
            ["role_policy", "agent_context"],
        )
        for block in turn["prompt_context_blocks"]:
            self.assertRegex(block["content_hash"], r"^sha256:[0-9a-f]{64}$")
            self.assertIn("source_provenance", block)

    def test_legacy_prompt_versions_ignore_roleplay_assets_byte_safely(self):
        agents = build_emergent_fake_agents(build_villager_win_script())
        registry = build_default_role_policy_registry()
        packet = _packet(
            [
                _record(
                    "belief_1",
                    kind="BeliefRecord",
                    summary="p1 suspects p3 based on vote pressure",
                    visibility_scope="seat_private",
                    audience_scope={"seat_ids": ["p1"]},
                ),
            ]
        )
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="v1_no_roleplay"),
            agents=agents,
            seed=7,
            prompt_version="prompt_v1",
            role_policy_registry=registry,
            agent_context_packets={"p1": packet},
        )

        engine._emit("setup", 0, "role_assignment", "system", "none", "public", "setup")
        engine._resolve_speech("p1", 1)

        request = agents["p1"].provider.requests[-1]
        self.assertNotIn("【角色策略】", request.observation_text)
        self.assertNotIn("【上下文记忆】", request.observation_text)
        turn = [
            turn for turn in engine._provider_turns
            if turn["actor"] == "p1" and turn["response_kind"] == "speech"
        ][0]
        self.assertNotIn("prompt_context_blocks", turn)

    def test_prompt_v5_selects_policy_from_engine_true_role(self):
        agents = build_emergent_fake_agents(build_villager_win_script())
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="v5_true_role"),
            agents=agents,
            seed=7,
            prompt_version="prompt_v5",
            scaffold_agent=ProviderAgent("scribe", _FakeScribeProvider()),
            role_policy_registry=build_default_role_policy_registry(),
        )

        engine._emit("setup", 0, "role_assignment", "system", "none", "public", "setup")
        engine._resolve_speech("p3", 1)

        request = agents["p3"].provider.requests[-1]
        self.assertIn("maximize check information", request.observation_text)
        self.assertNotIn("hide team identity", request.observation_text)
        self.assertNotIn("misdirect daytime votes", request.observation_text)


if __name__ == "__main__":
    unittest.main()
