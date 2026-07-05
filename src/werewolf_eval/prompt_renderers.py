"""PromptRenderer registry (SYS-B1 seam): ONE version->adapter mapping replaces
the v1/v2/v3 if/else scattered across the engine, provider layer, launcher and
ablation harness. Each adapter packages a version's full model-visible surface:
board card, observation renderer, speech contract, and the v3 injection
suffixes. Adding prompt_v4 = one adapter class + one REGISTRY entry + goldens
(KNOWN_PROMPT_VERSIONS stays a literal in prompt_version.py; the sentinel test
in tests/test_prompt_renderers.py pins registry/tuple equality).

Byte discipline: adapters CALL the version modules' locked functions verbatim —
no string is composed here except the historical engine f-string joins
("\\n" + scaffold/digest), which tests pin byte-exactly."""
from __future__ import annotations

from typing import Any

from werewolf_eval.prompt_v1 import (
    RenderedObservation,
    build_speech_system_prompt,
    render_observation_text,
)
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
from werewolf_eval.prompt_v4 import render_witch_coord_suffix
from werewolf_eval.prompt_v5 import render_roleplay_context_suffix
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS


class PromptRendererV1:
    """Baseline chain (legacy bytes): plain observation text, v1 speech
    contract, no board card, no injections, no scribe."""

    version = "prompt_v1"
    requires_scaffold = False

    def board_card(self, ruleset: Any, seat_roles: dict[str, str]) -> str:
        return ""

    def render_observation(self, obs: Any, events_by_id: dict[str, dict[str, Any]]) -> RenderedObservation:
        return render_observation_text(obs, events_by_id)

    def speech_contract(self, request: Any) -> str:
        return build_speech_system_prompt(request)

    def action_obs_suffix(self, phase: str, claim_ledger: list[dict[str, Any]]) -> str:
        return ""

    def speech_obs_suffix(self, claim_ledger: list[dict[str, Any]]) -> str:
        return ""

    def witch_obs_suffix(self, board_card: str | None, victim: str | None, save_used: bool) -> str:
        return ""

    def roleplay_context_suffix(
        self,
        *,
        role_policy: dict[str, Any] | None,
        agent_context_packet: dict[str, Any] | None,
        seat_character_card: dict[str, Any] | None = None,
        seat_id: str,
        team_ids: set[str] | None = None,
        max_context_records: int | None = 6,
    ) -> dict[str, Any]:
        return {"text": "", "blocks": []}


class PromptRendererV2(PromptRendererV1):
    """SYS-B1 context repair: board rules card + structured observation +
    discrimination speech contract."""

    version = "prompt_v2"

    def board_card(self, ruleset: Any, seat_roles: dict[str, str]) -> str:
        return build_board_rules_card(ruleset, seat_roles)

    def render_observation(self, obs: Any, events_by_id: dict[str, dict[str, Any]]) -> RenderedObservation:
        text, ids = render_observation_text_v2(obs, events_by_id)
        return RenderedObservation(text=text, source_event_ids=ids)

    def speech_contract(self, request: Any) -> str:
        return build_speech_system_prompt_v2(request)


class PromptRendererV3(PromptRendererV2):
    """SYS-B4 claim ledger + vote scaffold: v2 observation/board card, restrained
    speech, scribe-backed injections (digest for speech, full scaffold for the
    day vote — graded guidance, spec §4)."""

    version = "prompt_v3"
    requires_scaffold = True

    def speech_contract(self, request: Any) -> str:
        return build_speech_system_prompt_v3(request)

    def action_obs_suffix(self, phase: str, claim_ledger: list[dict[str, Any]]) -> str:
        if phase == "day":
            return "\n" + render_vote_scaffold(claim_ledger)
        return ""

    def speech_obs_suffix(self, claim_ledger: list[dict[str, Any]]) -> str:
        if claim_ledger:
            return "\n" + render_claim_digest(claim_ledger)
        return ""


class PromptRendererV4(PromptRendererV3):
    """l4_guard_witch_coord arm: the full v3 chain + witch antidote-coordination
    guidance injected ONLY into the witch's night action observation
    (3-condition gate in prompt_v4.render_witch_coord_suffix; spec 2026-06-12 §3)."""

    version = "prompt_v4"

    def witch_obs_suffix(self, board_card: str | None, victim: str | None, save_used: bool) -> str:
        return render_witch_coord_suffix(board_card, victim, save_used)


class PromptRendererV5(PromptRendererV4):
    """P3-A-2c roleplay arm: v4 chain plus a single, fixed-order
    RolePolicy/AgentContextPacket observation-side context path."""

    version = "prompt_v5"

    def roleplay_context_suffix(
        self,
        *,
        role_policy: dict[str, Any] | None,
        agent_context_packet: dict[str, Any] | None,
        seat_character_card: dict[str, Any] | None = None,
        seat_id: str,
        team_ids: set[str] | None = None,
        max_context_records: int | None = 6,
    ) -> dict[str, Any]:
        return render_roleplay_context_suffix(
            seat_character_card=seat_character_card,
            role_policy=role_policy,
            agent_context_packet=agent_context_packet,
            seat_id=seat_id,
            team_ids=team_ids,
            max_context_records=max_context_records,
        )


REGISTRY: dict[str, PromptRendererV1] = {
    r.version: r for r in (
        PromptRendererV1(),
        PromptRendererV2(),
        PromptRendererV3(),
        PromptRendererV4(),
        PromptRendererV5(),
    )
}


def get_renderer(version: str) -> PromptRendererV1:
    try:
        return REGISTRY[version]
    except KeyError:
        raise ValueError(
            f"unknown prompt_version {version!r}; known: {KNOWN_PROMPT_VERSIONS}"
        ) from None
