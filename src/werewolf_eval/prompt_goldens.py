"""Canonical golden-prompt sample set (spec 2026-06-10-prompt-versioning §5).

The ONE definition of which rendered prompts are byte-locked. Imported by
tests/test_prompt_versioning.py (the lock) and tools/generate_golden_prompts.py
(the generator) so the two can never drift.

Fixtures are hand-frozen literals — they must NEVER depend on RNG, time, or
engine state, or the lock becomes nondeterministic.
"""
from __future__ import annotations

from dataclasses import replace

from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.emergent_engine import (
    HUNTER_SHOT_OBSERVATION_SUFFIX,
    augment_witch_observation,
)
from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.llm_providers import (
    build_action_system_prompt,
    build_scribe_system_prompt,
    compose_system,
)
from werewolf_eval.prompt_v1 import build_speech_system_prompt, render_observation_text
from werewolf_eval.prompt_v2 import (
    build_board_rules_card,
    build_speech_system_prompt_v2,
    render_observation_text_v2,
)
from werewolf_eval.prompt_v3 import (
    build_speech_system_prompt_v3,
    render_claim_digest,
    render_scribe_input,
    render_vote_scaffold,
)
from werewolf_eval.prompt_v4 import render_witch_coord_suffix
from werewolf_eval.prompt_v5 import render_roleplay_context_suffix
from werewolf_eval.provider_contract import ProviderRequest
from werewolf_eval.agent_context_packet import AGENT_CONTEXT_PACKET_SCHEMA_VERSION
from werewolf_eval.role_policy_registry import build_default_role_policy_registry
from werewolf_eval.roleplay_shadow_arm import build_starter_seat_character_cards

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


_STD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
              "p4": "witch", "p5": "villager", "p6": "villager"}
_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}

_EVENTS_V2 = {
    "e1": {"event_id": "e1", "sequence": 1, "round": 1, "phase": "night", "type": "werewolf_kill",
           "actor": "p1", "target": "p5", "visibility": "werewolf_team",
           "data": {"summary": "Wolf team kills p5."}},
    "e2": {"event_id": "e2", "sequence": 2, "round": 1, "phase": "night", "type": "seer_check",
           "actor": "p3", "target": "p1", "visibility": "seer",
           "data": {"summary": "Seer p3 checks p1, result: werewolf."}},
    "e3": {"event_id": "e3", "sequence": 3, "round": 1, "phase": "day", "type": "day_announcement",
           "actor": "system", "target": "none", "visibility": "public",
           "data": {"summary": "Night fell: p5 died."}},
    "e4": {"event_id": "e4", "sequence": 4, "round": 1, "phase": "day", "type": "player_speech",
           "actor": "p3", "target": "none", "visibility": "public",
           "data": {"summary": "我验了p1,他是狼。"}},
    "e5": {"event_id": "e5", "sequence": 5, "round": 1, "phase": "day", "type": "player_speech",
           "actor": "p1", "target": "none", "visibility": "public",
           "data": {"summary": "p3在说谎,我是好人。"}},
    "e6": {"event_id": "e6", "sequence": 6, "round": 1, "phase": "day", "type": "player_vote",
           "actor": "p3", "target": "p1", "visibility": "public",
           "data": {"summary": "p3 votes p1."}},
    "e7": {"event_id": "e7", "sequence": 7, "round": 1, "phase": "day", "type": "player_vote",
           "actor": "p1", "target": "p3", "visibility": "public",
           "data": {"summary": "p1 votes p3."}},
}
_PUB_V2 = ["e3", "e4", "e5", "e6", "e7"]


def _obs_v2(player_id: str, role: str, team: str, phase: str,
            known: dict[str, str], private: list[str]) -> AgentObservation:
    return AgentObservation(
        game_id="golden_fixture", player_id=player_id, role=role, team=team,
        phase=phase, round=2, alive_players=["p1", "p2", "p3", "p4", "p6"],
        public_event_ids=list(_PUB_V2), private_event_ids=list(private),
        known_roles=known,
    )


def _v2_text(player_id: str, role: str, team: str, phase: str,
             known: dict[str, str], private: list[str]) -> str:
    return render_observation_text_v2(_obs_v2(player_id, role, team, phase, known, private), _EVENTS_V2)[0]


def canonical_prompt_samples_v2() -> list[tuple[str, str]]:
    """prompt_v2 golden sample set — locks the SYS-B1 chain (rules card +
    structured observation + speech v2 + full system composition).

    CAVEAT (same precedent as v1's compose_persona_action): compose_full_v2_speech
    locks a HAND-REPLICATED assembly f"{card}\\n\\n" + compose_system(...) — not the
    real _system_for path; if the assembly order ever changes, this golden won't
    catch it by itself. The end-to-end guard is
    tests/test_prompt_v2.py::test_system_for_selects_by_prompt_version_and_prepends_card."""
    card = build_board_rules_card(rules_v1_1(), _STD_SEATS)
    speech_v2 = build_speech_system_prompt_v2(
        _req("p5", "day", [], [], response_kind="speech"))
    witch_text = _v2_text("p4", "witch", "villager", "night", {"p4": "witch"}, [])
    return [
        ("board_card_standard_6p", card),
        ("speech_villager_v2", speech_v2),
        ("speech_werewolf_v2", build_speech_system_prompt_v2(
            _req("p1", "day", [], [], response_kind="speech"))),
        ("obs_v2_seer_day",
         _v2_text("p3", "seer", "villager", "day", {"p3": "seer"}, ["e2"])),
        ("obs_v2_werewolf_night",
         _v2_text("p1", "werewolf", "werewolf", "night",
                  {"p1": "werewolf", "p2": "werewolf"}, ["e1"])),
        ("obs_v2_villager_day",
         _v2_text("p6", "villager", "villager", "day", {"p6": "villager"}, [])),
        ("obs_v2_witch_victim", augment_witch_observation(witch_text, "p5")),
        ("obs_v2_witch_no_victim", augment_witch_observation(witch_text, None)),
        ("obs_v2_hunter_shot",
         _v2_text("p6", "hunter", "villager", "hunter_shot", {"p6": "hunter"}, [])
         + HUNTER_SHOT_OBSERVATION_SUFFIX),
        ("compose_full_v2_speech",
         f"{card}\n\n" + compose_system("你是谨慎的分析型玩家。", speech_v2)),
    ]


_CLAIMS_V3 = [
    {"round": 1, "claimant": "p3", "claim_type": "check_report", "target": "p1",
     "result": "werewolf", "refutes": None, "source": 1,
     "source_quote": "昨晚验了p1,他是狼人", "uncertain": False},
    {"round": 1, "claimant": "p1", "claim_type": "refutation", "target": None,
     "result": None, "refutes": "p3", "source": 2,
     "source_quote": "p3在悍跳", "uncertain": True},
]


def canonical_prompt_samples_v3() -> list[tuple[str, str]]:
    """prompt_v3 golden set — the three spec §8.6 classes: ① scribe prompt+schema,
    ② claim digest injection text, ③ vote scaffold full text; plus the restrained
    speech contract and the scribe input rendering."""
    scaffold_req = _req("scribe", "day", [], [], response_kind="scaffold")
    return [
        ("scribe_system_prompt", build_scribe_system_prompt(scaffold_req)),
        ("scribe_input_round1", render_scribe_input(1, [("p3", "我验了p1,他是狼。"), ("p1", "p3在悍跳。")])),
        ("claim_digest_two_claims", render_claim_digest(_CLAIMS_V3)),
        ("vote_scaffold_with_claims", render_vote_scaffold(_CLAIMS_V3)),
        ("vote_scaffold_empty_ledger", render_vote_scaffold([])),
        ("speech_villager_v3", build_speech_system_prompt_v3(_req("p5", "day", [], [], response_kind="speech"))),
        # ---- L4 guard-board additions (spec §6: new samples only; old hashes frozen) ----
        ("board_card_guard_6p", build_board_rules_card(rules_v1_2(), _GUARD_SEATS)),
        ("speech_villager_v3_guard_board", build_speech_system_prompt_v3(
            replace(_req("p6", "day", [], [], response_kind="speech"),
                    board_card=build_board_rules_card(rules_v1_2(), _GUARD_SEATS)))),
        ("action_guard_night",
         build_action_system_prompt(_req("p5", "night", ["guard_protect"], _ALIVE))),
        ("obs_v2_guard_night",
         _v2_text("p5", "guard", "villager", "night", {"p5": "guard"}, [])),
    ]


def canonical_prompt_samples_v4() -> list[tuple[str, str]]:
    """prompt_v4 golden set — only the NEW surface (spec §5/§9): the injected
    suffix, the fully composed injected witch observation, and the no-victim
    identity state (whose bytes ARE prompt_v3's — locking that v4 adds nothing
    there). The "" states can't be golden files; they are pinned by the canary
    unit tests (tests/test_prompt_v4*.py)."""
    guard_card = build_board_rules_card(rules_v1_2(), _GUARD_SEATS)
    witch_text = _v2_text("p4", "witch", "villager", "night", {"p4": "witch"}, [])
    return [
        ("witch_coord_suffix_injected",
         render_witch_coord_suffix(guard_card, "p5", False)),
        ("obs_witch_guard_board_victim_coord",
         augment_witch_observation(witch_text, "p5")
         + render_witch_coord_suffix(guard_card, "p5", False)),
        ("obs_witch_guard_board_no_victim_identity",
         augment_witch_observation(witch_text, None)
         + render_witch_coord_suffix(guard_card, None, False)),
    ]


def _roleplay_packet() -> dict:
    return {
        "schema_version": AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
        "run_id": "golden_fixture",
        "seat_id": "p1",
        "decision_id": "golden_day1_speech_p1",
        "records": [
            {
                "record_id": "claim_1",
                "kind": "ClaimRecord",
                "section": "public_timeline",
                "writer": "public_event",
                "visibility_scope": "public",
                "audience_scope": {"seat_ids": []},
                "trust_class": "run_derived",
                "render_mode": "quoted_evidence",
                "source_provenance": {
                    "source_event_ids": ["evt_claim_1"],
                    "generated_by": "golden_fixture",
                },
                "status": "active",
                "summary": "p3 claimed seer",
            },
            {
                "record_id": "belief_1",
                "kind": "BeliefRecord",
                "section": "episodic_notes",
                "writer": "seat_agent",
                "visibility_scope": "seat_private",
                "audience_scope": {"seat_ids": ["p1"]},
                "trust_class": "run_derived",
                "render_mode": "state_summary",
                "source_provenance": {
                    "source_event_ids": ["evt_vote_1"],
                    "generated_by": "golden_fixture",
                },
                "status": "active",
                "summary": "p1 suspects p3 based on vote pressure",
            },
        ],
        "context_budget": {
            "included_blocks": [],
            "compacted_blocks": [],
            "dropped_blocks": [],
        },
    }


def canonical_prompt_samples_v5() -> list[tuple[str, str]]:
    """prompt_v5 golden set — the new P3-A roleplay-context surface only.

    Existing v1-v4 samples stay owned by their prior versions; this locks the
    model-visible RolePolicy + AgentContextPacket suffix introduced by P3-A-2c.
    """
    registry = build_default_role_policy_registry()
    pack = registry.get_pack("standard_six_player_balanced")
    policy = registry.resolve_policy_ref(pack["role_policy_refs"]["werewolf"])
    rendered = render_roleplay_context_suffix(
        role_policy=policy,
        agent_context_packet=_roleplay_packet(),
        seat_id="p1",
        team_ids={"werewolf"},
    )
    card_rendered = render_roleplay_context_suffix(
        role_policy=policy,
        agent_context_packet=_roleplay_packet(),
        seat_character_card=build_starter_seat_character_cards()["calm_logician"],
        seat_id="p1",
        team_ids={"werewolf"},
    )
    return [
        ("roleplay_context_werewolf_with_packet", rendered["text"]),
        ("roleplay_context_card_policy_packet", card_rendered["text"]),
    ]


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
