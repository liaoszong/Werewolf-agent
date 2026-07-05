"""PromptRenderer registry sentinels + byte-equivalence vs the underlying
version functions. The REGISTRY is the single seam: these tests pin (a) the
registry/version-tuple cannot drift, (b) each adapter is byte-identical to the
functions it packages, (c) the v3 injection suffixes reproduce the engine's
historical f-string composition exactly."""
import unittest

from werewolf_eval.prompt_renderers import REGISTRY, get_renderer
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS
from werewolf_eval.prompt_v1 import build_speech_system_prompt, render_observation_text
from werewolf_eval.prompt_v2 import (
    build_board_rules_card,
    build_speech_system_prompt_v2,
    render_observation_text_v2,
)
from werewolf_eval.prompt_v3 import (
    build_speech_system_prompt_v3,
    render_claim_digest,
    render_vote_scaffold,
)
from werewolf_eval.prompt_v4 import WITCH_COORD_GUIDANCE
from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.provider_contract import ProviderRequest

_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
          "p4": "witch", "p5": "villager", "p6": "villager"}
_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}
_EVENTS = {
    "e1": {"event_id": "e1", "sequence": 1, "round": 1, "phase": "night",
           "type": "werewolf_kill", "actor": "p1", "target": "p5",
           "visibility": "werewolf_team", "data": {"summary": "Wolf team kills p5."}},
    "e2": {"event_id": "e2", "sequence": 2, "round": 1, "phase": "day",
           "type": "day_announcement", "actor": "system", "target": "none",
           "visibility": "public", "data": {"summary": "Night fell: p5 died."}},
}
_CLAIMS = [{"round": 1, "claimant": "p3", "claim_type": "check_report",
            "target": "p1", "result": "werewolf", "refutes": None, "source": 1,
            "source_quote": "昨晚验了p1,他是狼人", "uncertain": False}]


def _obs(player_id="p1", role="werewolf", team="werewolf", phase="night"):
    return AgentObservation(
        game_id="t", player_id=player_id, role=role, team=team, phase=phase,
        round=1, alive_players=["p1", "p2", "p3", "p4", "p5", "p6"],
        public_event_ids=["e2"], private_event_ids=["e1"],
        known_roles={"p1": "werewolf", "p2": "werewolf"},
    )


def _req(kind="speech"):
    return ProviderRequest(
        request_id="t", game_id="t", actor="p5", phase="day", round=1,
        observation={}, allowed_actions=[], allowed_targets=[], response_kind=kind,
    )


class RegistrySentinelTest(unittest.TestCase):
    def test_registry_matches_known_versions_in_order(self):
        self.assertEqual(tuple(REGISTRY), KNOWN_PROMPT_VERSIONS)

    def test_adapter_version_matches_its_key(self):
        for key, renderer in REGISTRY.items():
            self.assertEqual(renderer.version, key)

    def test_unknown_version_fails_loud(self):
        with self.assertRaises(ValueError) as ctx:
            get_renderer("prompt_v99")
        self.assertIn("unknown prompt_version", str(ctx.exception))

    def test_requires_scaffold_flags(self):
        self.assertFalse(REGISTRY["prompt_v1"].requires_scaffold)
        self.assertFalse(REGISTRY["prompt_v2"].requires_scaffold)
        self.assertTrue(REGISTRY["prompt_v3"].requires_scaffold)
        self.assertTrue(REGISTRY["prompt_v4"].requires_scaffold)
        self.assertTrue(REGISTRY["prompt_v5"].requires_scaffold)


class AdapterByteEquivalenceTest(unittest.TestCase):
    def test_v1_observation_identical(self):
        obs = _obs()
        self.assertEqual(
            get_renderer("prompt_v1").render_observation(obs, _EVENTS),
            render_observation_text(obs, _EVENTS),
        )

    def test_v2_v3_observation_identical(self):
        obs = _obs()
        text, ids = render_observation_text_v2(obs, _EVENTS)
        for v in ("prompt_v2", "prompt_v3"):
            rendered = get_renderer(v).render_observation(obs, _EVENTS)
            self.assertEqual(rendered.text, text)
            self.assertEqual(rendered.source_event_ids, ids)

    def test_board_card_dispatch(self):
        rs = rules_v1_1()
        self.assertEqual(get_renderer("prompt_v1").board_card(rs, _SEATS), "")
        expected = build_board_rules_card(rs, _SEATS)
        self.assertEqual(get_renderer("prompt_v2").board_card(rs, _SEATS), expected)
        self.assertEqual(get_renderer("prompt_v3").board_card(rs, _SEATS), expected)

    def test_speech_contract_dispatch(self):
        req = _req()
        self.assertEqual(get_renderer("prompt_v1").speech_contract(req),
                         build_speech_system_prompt(req))
        self.assertEqual(get_renderer("prompt_v2").speech_contract(req),
                         build_speech_system_prompt_v2(req))
        self.assertEqual(get_renderer("prompt_v3").speech_contract(req),
                         build_speech_system_prompt_v3(req))

    def test_v4_inherits_v3_surfaces(self):
        req = _req()
        r4 = get_renderer("prompt_v4")
        self.assertEqual(r4.speech_contract(req), build_speech_system_prompt_v3(req))
        self.assertEqual(r4.action_obs_suffix("day", _CLAIMS), "\n" + render_vote_scaffold(_CLAIMS))
        self.assertEqual(r4.speech_obs_suffix(_CLAIMS), "\n" + render_claim_digest(_CLAIMS))
        rs = rules_v1_1()
        self.assertEqual(r4.board_card(rs, _SEATS),
                         get_renderer("prompt_v3").board_card(rs, _SEATS))


class WitchObsSuffixDispatchTest(unittest.TestCase):
    """v4 注入 hook:v1/v2/v3 恒返 ""(既有版本字节零影响);v4 走 3 条件门。"""

    def setUp(self):
        # build_board_rules_card is already module-level imported in this file
        self.guard_card = build_board_rules_card(rules_v1_2(), _GUARD_SEATS)

    def test_v1_v2_v3_always_empty(self):
        for v in ("prompt_v1", "prompt_v2", "prompt_v3"):
            self.assertEqual(get_renderer(v).witch_obs_suffix(self.guard_card, "p5", False), "")

    def test_v4_injects_only_on_full_conjunction(self):
        r4 = get_renderer("prompt_v4")
        self.assertEqual(r4.witch_obs_suffix(self.guard_card, "p5", False),
                         "\n" + WITCH_COORD_GUIDANCE)
        self.assertEqual(r4.witch_obs_suffix(self.guard_card, None, False), "")
        self.assertEqual(r4.witch_obs_suffix(self.guard_card, "p5", True), "")
        std_card = get_renderer("prompt_v2").board_card(rules_v1_1(), _SEATS)
        self.assertEqual(r4.witch_obs_suffix(std_card, "p5", False), "")


class InjectionSuffixTest(unittest.TestCase):
    """钉死引擎历史拼接字节:f"{obs_text}\\n{render_vote_scaffold(...)}" 与
    f"{obs_text}\\n{render_claim_digest(...)}"(仅 ledger 非空)。"""

    def test_v1_v2_suffixes_empty(self):
        for v in ("prompt_v1", "prompt_v2"):
            r = get_renderer(v)
            self.assertEqual(r.action_obs_suffix("day", _CLAIMS), "")
            self.assertEqual(r.speech_obs_suffix(_CLAIMS), "")

    def test_v3_action_suffix_day_only(self):
        r = get_renderer("prompt_v3")
        self.assertEqual(r.action_obs_suffix("day", _CLAIMS),
                         "\n" + render_vote_scaffold(_CLAIMS))
        # 空账本时 vote scaffold 仍非空(「没有可记录的身份声称」+ 程序),与引擎旧行为一致
        self.assertEqual(r.action_obs_suffix("day", []),
                         "\n" + render_vote_scaffold([]))
        self.assertEqual(r.action_obs_suffix("night", _CLAIMS), "")

    def test_v3_speech_suffix_gated_on_nonempty_ledger(self):
        r = get_renderer("prompt_v3")
        self.assertEqual(r.speech_obs_suffix(_CLAIMS),
                         "\n" + render_claim_digest(_CLAIMS))
        self.assertEqual(r.speech_obs_suffix([]), "")


if __name__ == "__main__":
    unittest.main()
