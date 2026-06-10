"""Canonical golden-prompt sample set (spec 2026-06-10-prompt-versioning §5).

The ONE definition of which rendered prompts are byte-locked. Imported by
tests/test_prompt_versioning.py (the lock) and tools/generate_golden_prompts.py
(the generator) so the two can never drift.

Fixtures are hand-frozen literals — they must NEVER depend on RNG, time, or
engine state, or the lock becomes nondeterministic.
"""
from __future__ import annotations

from werewolf_eval.emergent_engine import (
    HUNTER_SHOT_OBSERVATION_SUFFIX,
    augment_witch_observation,
    render_observation_text,
)
from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.llm_providers import (
    build_action_system_prompt,
    build_speech_system_prompt,
    compose_system,
)
from werewolf_eval.provider_contract import ProviderRequest

_ALIVE = ["p1", "p2", "p3", "p4", "p5", "p6"]

# Event payloads are arbitrary narrative fillers for byte-locking the renderer —
# they are NOT engine-consistent state (e.g. "p2 死亡" while p2 stays in _ALIVE).
_EVENTS = {
    "e1": {"round": 1, "phase": "night", "data": {"summary": "夜晚开始。"}},
    "e2": {"round": 1, "phase": "day", "data": {"summary": "p2 死亡。"}},
}


def _req(
    actor: str,
    phase: str,
    allowed_actions: list[str],
    allowed_targets: list[str],
    response_kind: str = "action",
) -> ProviderRequest:
    return ProviderRequest(
        request_id="golden_fixture",
        game_id="golden_fixture",
        actor=actor,
        phase=phase,
        round=1,
        observation={},
        allowed_actions=allowed_actions,
        allowed_targets=allowed_targets,
        response_kind=response_kind,
    )


def _obs(player_id: str, role: str, team: str, phase: str, known: dict[str, str]) -> AgentObservation:
    return AgentObservation(
        game_id="golden_fixture",
        player_id=player_id,
        role=role,
        team=team,
        phase=phase,
        round=1,
        alive_players=list(_ALIVE),
        public_event_ids=["e1", "e2"],
        private_event_ids=[],
        known_roles=known,
    )


def canonical_prompt_samples() -> list[tuple[str, str]]:
    villager_vote = _req("p5", "day", ["player_vote"], _ALIVE)
    witch_obs = render_observation_text(
        _obs("p4", "witch", "villager", "night", {"p4": "witch"}), _EVENTS
    ).text
    return [
        ("action_werewolf_night",
         build_action_system_prompt(_req("p1", "night", ["werewolf_kill"], _ALIVE))),
        ("action_seer_night",
         build_action_system_prompt(_req("p3", "night", ["seer_check"], _ALIVE))),
        ("action_witch_night",
         build_action_system_prompt(
             _req("p4", "night", ["witch_save", "witch_poison", "witch_pass"], _ALIVE))),
        ("action_villager_day_vote", build_action_system_prompt(villager_vote)),
        ("action_hunter_day_vote",
         build_action_system_prompt(_req("p6", "day", ["player_vote"], _ALIVE))),
        ("action_hunter_shot",
         build_action_system_prompt(
             _req("p6", "hunter_shot", ["hunter_shoot", "hunter_pass"], _ALIVE))),
        ("speech_villager_day1",
         build_speech_system_prompt(_req("p5", "day", [], [], response_kind="speech"))),
        ("speech_werewolf_day1",
         build_speech_system_prompt(_req("p1", "day", [], [], response_kind="speech"))),
        ("compose_persona_action",
         compose_system("你是谨慎的分析型玩家。", build_action_system_prompt(villager_vote))),
        ("obs_villager_day",
         render_observation_text(
             _obs("p5", "villager", "villager", "day", {"p5": "villager"}), _EVENTS).text),
        ("obs_werewolf_night",
         render_observation_text(
             _obs("p1", "werewolf", "werewolf", "night",
                  {"p1": "werewolf", "p2": "werewolf"}), _EVENTS).text),
        ("obs_witch_night_victim", augment_witch_observation(witch_obs, "p5")),
        ("obs_witch_night_no_victim", augment_witch_observation(witch_obs, None)),
        ("obs_hunter_shot",
         render_observation_text(
             _obs("p6", "hunter", "villager", "hunter_shot", {"p6": "hunter"}), _EVENTS
         ).text + HUNTER_SHOT_OBSERVATION_SUFFIX),
    ]
