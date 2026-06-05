"""P2-A-2 offline units: text-enrichment visibility safety, speech path, and
provider_turns live-success accounting. No network — DeepSeekProvider is driven
by an injected fake transport."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.deepseek_provider import DeepSeekProvider, DeepSeekProviderConfig
from werewolf_eval.emergent_engine import (
    ACTION_MAX_OUTPUT_TOKENS,
    INVALID_FALLBACK,
    LIVE_SUCCESS,
    SPEECH_MAX_OUTPUT_TOKENS,
    TIMEOUT_FALLBACK,
    EmergentGameEngine,
    build_emergent_config,
    render_observation_text,
)
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.provider_contract import DEEPSEEK_PROVIDER_SOURCE_LABEL, ProviderRequest


# ---- fake DeepSeek transports (no network) ----------------------------------

def _action_transport(content: str):
    def t(url, headers, payload, timeout):
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
        }
    return t


def _speech_transport(text: str):
    def t(url, headers, payload, timeout):
        return {
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 40, "total_tokens": 70},
        }
    return t


def _raise_transport(exc: Exception):
    def t(url, headers, payload, timeout):
        raise exc
    return t


def _deepseek_agent(pid: str, transport) -> ProviderAgent:
    cfg = DeepSeekProviderConfig(api_key="test-key", model="deepseek-v4-flash", max_requests=64)
    return ProviderAgent(pid, DeepSeekProvider(cfg, transport=transport))


# ---- gate ①: visibility-safe text-enrichment --------------------------------

class ObservationTextVisibilityTests(unittest.TestCase):
    def _engine_with_events(self):
        eng = EmergentGameEngine(
            build_emergent_config("vis"), build_emergent_fake_agents(build_villager_win_script()), seed=0
        )
        # public + role-private events
        eng._emit("setup", 0, "role_assignment", "system", "none", "public", "Roles assigned.")
        eng._emit("night", 1, "werewolf_kill", "p1", "p5", "werewolf_team", "Wolf team kills p5.")
        eng._emit("night", 1, "seer_check", "p3", "p1", "seer", "Seer p3 checks p1, result: werewolf.")
        eng._emit("night", 1, "witch_save", "p4", "p5", "witch", "Witch p4 saves p5.")
        return eng

    def test_source_event_ids_subset_of_visible(self) -> None:
        eng = self._engine_with_events()
        for pid in ("p1", "p2", "p3", "p4", "p5", "p6"):
            obs = eng._build_obs(pid, "day", 1)
            rendered = render_observation_text(obs, eng._events_by_id())
            visible = set(obs.public_event_ids) | set(obs.private_event_ids)
            self.assertTrue(set(rendered.source_event_ids) <= visible, f"{pid} leaked refs")

    def test_villager_text_excludes_wolf_kill_and_seer_result(self) -> None:
        eng = self._engine_with_events()
        obs = eng._build_obs("p6", "day", 1)  # p6 is a villager
        text = render_observation_text(obs, eng._events_by_id()).text
        self.assertNotIn("Wolf team kills", text)         # werewolf_team-private
        self.assertNotIn("result: werewolf", text)        # seer-private
        self.assertNotIn("Witch p4 saves", text)          # witch-private
        self.assertIn("Roles assigned", text)             # public is fine

    def test_wolf_sees_own_team_kill_but_not_seer_result(self) -> None:
        eng = self._engine_with_events()
        obs = eng._build_obs("p1", "day", 1)  # p1 is a wolf
        text = render_observation_text(obs, eng._events_by_id()).text
        self.assertIn("Wolf team kills", text)            # wolf sees team-private
        self.assertNotIn("result: werewolf", text)        # but not seer-private

    def test_known_roles_canary_not_leaked(self) -> None:
        # A villager's observation knows only itself; a hidden role planted in a
        # GLOBAL map must never appear (proves render reads obs, not a god map).
        obs = AgentObservation(
            game_id="g", player_id="p6", role="villager", team="villager",
            phase="day", round=1, alive_players=["p1", "p6"],
            public_event_ids=[], private_event_ids=[], known_roles={"p6": "villager"},
        )
        canary = "CANARY_SECRET_ROLE_p1_is_werewolf"
        events_by_id = {"x": {"round": 1, "phase": "night", "data": {"summary": canary}}}
        text = render_observation_text(obs, events_by_id).text
        self.assertNotIn(canary, text)  # x not in obs refs -> never rendered
        self.assertNotIn("werewolf", text)


# ---- gate ①: observation_text is non-empty on every emergent live request ----

class _RecordingProvider:
    """Wraps record of requests; returns a fixed valid action JSON."""
    def __init__(self):
        self.requests = []
        self.responses = []
    model = "rec"
    def respond(self, request):
        self.requests.append(request)
        from werewolf_eval.provider_contract import ProviderResponse
        r = ProviderResponse(request.request_id, "rec", "[rec]", '{"action":"player_vote","target":"p1","reason_summary":"x","decision_type":"inference_based","confidence":1.0}', 0, {"prompt_tokens":1,"completion_tokens":1,"total_tokens":2})
        self.responses.append(r)
        return r


class ObservationTextNonEmptyTests(unittest.TestCase):
    def test_every_emergent_request_carries_nonempty_observation_text(self) -> None:
        # Use fake agents but spy on requests via the provider each agent holds.
        agents = build_emergent_fake_agents(build_villager_win_script())
        eng = EmergentGameEngine(build_emergent_config("ot"), agents, seed=0)
        eng.run()
        seen_any = False
        for agent in agents.values():
            for req in agent.provider.requests:
                seen_any = True
                self.assertTrue(req.observation_text.strip(), f"empty observation_text on {req.request_id}")
                # and it must not be the raw observation-id dump
                import json
                self.assertNotEqual(req.observation_text, json.dumps(req.observation))
        self.assertTrue(seen_any, "no provider requests captured")


# ---- prereq (i): speech path does not IndexError + uses observation_text -----

class SpeechProviderTests(unittest.TestCase):
    def _speech_request(self):
        return ProviderRequest(
            request_id="r", game_id="g", actor="p3", phase="day_speech", round=1,
            observation={"x": 1}, allowed_actions=[], allowed_targets=[],
            observation_text="你能看到的事件: ...", response_kind="speech",
            max_output_tokens=SPEECH_MAX_OUTPUT_TOKENS,
        )

    def test_speech_with_empty_allowed_actions_does_not_indexerror(self) -> None:
        prov = DeepSeekProvider(DeepSeekProviderConfig(api_key="k", model="m"), transport=_speech_transport("我怀疑 p2，今天投 p2。"))
        resp = prov.respond(self._speech_request())  # would IndexError pre-fix
        self.assertEqual(resp.raw_content, "我怀疑 p2，今天投 p2。")
        self.assertEqual(resp.source_label, DEEPSEEK_PROVIDER_SOURCE_LABEL)

    def test_speech_payload_is_freetext_not_json_and_uses_token_cap(self) -> None:
        captured = {}
        def transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 5}}
        prov = DeepSeekProvider(DeepSeekProviderConfig(api_key="k", model="m"), transport=transport)
        prov.respond(self._speech_request())
        self.assertNotIn("response_format", captured)  # speech is NOT json_object
        self.assertEqual(captured["max_tokens"], SPEECH_MAX_OUTPUT_TOKENS)
        # user content is the readable observation_text, not an id dump
        self.assertEqual(captured["messages"][1]["content"], "你能看到的事件: ...")

    def test_action_payload_uses_observation_text_and_per_request_tokens(self) -> None:
        captured = {}
        def transport(url, headers, payload, timeout):
            captured.update(payload)
            return {"choices": [{"message": {"content": '{"action":"player_vote","target":"p1","reason_summary":"x","decision_type":"inference_based","confidence":1.0}'}}], "usage": {"total_tokens": 5}}
        prov = DeepSeekProvider(DeepSeekProviderConfig(api_key="k", model="m"), transport=transport)
        req = ProviderRequest(
            request_id="r", game_id="g", actor="p3", phase="day", round=1,
            observation={"x": 1}, allowed_actions=["player_vote"], allowed_targets=["p1"],
            observation_text="可读文本", response_kind="action", max_output_tokens=ACTION_MAX_OUTPUT_TOKENS,
        )
        prov.respond(req)
        self.assertEqual(captured["messages"][1]["content"], "可读文本")
        self.assertEqual(captured["max_tokens"], ACTION_MAX_OUTPUT_TOKENS)
        self.assertEqual(captured["response_format"], {"type": "json_object"})


# ---- integration: engine speech turn via ProviderAgent -> DeepSeekProvider ---

class SpeechIntegrationTests(unittest.TestCase):
    def test_engine_speech_turn_records_live_text_without_json_failure(self) -> None:
        agents = build_emergent_fake_agents(build_villager_win_script())
        # swap p3's agent for a DeepSeek-backed one that returns speech text
        agents["p3"] = _deepseek_agent("p3", _speech_transport("我是预言家，昨晚验了 p1 是狼，请投 p1。"))
        eng = EmergentGameEngine(build_emergent_config("spk"), agents, seed=0)
        eng._emit("setup", 0, "role_assignment", "system", "none", "public", "Roles assigned.")
        eng._resolve_speech("p3", 1)
        speeches = [e for e in eng._events if e["type"] == "player_speech" and e["actor"] == "p3"]
        self.assertEqual(len(speeches), 1)
        self.assertIn("预言家", speeches[0]["data"]["summary"])
        turn = [t for t in eng._provider_turns if t["actor"] == "p3" and t["response_kind"] == "speech"][0]
        self.assertEqual(turn["kind"], LIVE_SUCCESS)
        self.assertEqual(turn["source_label"], DEEPSEEK_PROVIDER_SOURCE_LABEL)
        self.assertGreater(turn["token_usage"]["total_tokens"], 0)


# ---- gate ②: provider_turns taxonomy + live_success_rate --------------------

class ProviderTurnTaxonomyTests(unittest.TestCase):
    def test_timeout_then_fallback_classified_and_excluded_from_success(self) -> None:
        agents = build_emergent_fake_agents(build_villager_win_script())
        # p5/p6 votes time out on day 1 -> timeout_then_fallback, game still completes
        agents["p5"] = _deepseek_agent("p5", _raise_transport(TimeoutError("slow")))
        agents["p6"] = _deepseek_agent("p6", _raise_transport(TimeoutError("slow")))
        outcome = EmergentGameEngine(build_emergent_config("tax"), agents, seed=0).run()
        self.assertEqual(outcome.status, "completed")
        kinds = [t["kind"] for t in outcome.provider_turns if t["actor"] in ("p5", "p6")]
        self.assertIn(TIMEOUT_FALLBACK, kinds)
        # fallback turns must NOT carry a DeepSeek source_label
        for t in outcome.provider_turns:
            if t["kind"] != LIVE_SUCCESS:
                self.assertIsNone(t["source_label"])
        # rate excludes the fallbacks
        self.assertLess(outcome.live_success_rate, 1.0)
        self.assertEqual(
            outcome.live_success_rate,
            outcome.live_success_actions / outcome.live_requested_actions,
        )

    def test_invalid_live_action_downgraded_not_counted_success(self) -> None:
        agents = build_emergent_fake_agents(build_villager_win_script())
        # p6 returns a vote for a non-existent target -> ProviderAgent raises invalid_action
        agents["p6"] = _deepseek_agent("p6", _action_transport('{"action":"player_vote","target":"p99","reason_summary":"x","decision_type":"inference_based","confidence":1.0}'))
        outcome = EmergentGameEngine(build_emergent_config("inv"), agents, seed=0).run()
        self.assertEqual(outcome.status, "completed")
        p6_vote_turns = [t for t in outcome.provider_turns if t["actor"] == "p6" and t["response_kind"] == "action" and t["phase"] == "day"]
        self.assertTrue(p6_vote_turns)
        self.assertEqual(p6_vote_turns[0]["kind"], INVALID_FALLBACK)
        self.assertIsNone(p6_vote_turns[0]["source_label"])


if __name__ == "__main__":
    unittest.main()
