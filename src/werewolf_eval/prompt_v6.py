"""prompt_v6 (P3-A-3 continuity context).

This is a coexisting, explicit prompt version for the
``p3a_continuity_shadow`` arm. It adds continuity context blocks while leaving
``prompt_v1`` as the default and ``prompt_v5`` byte-frozen.
"""

from __future__ import annotations

from typing import Any

from werewolf_eval.continuity_context import (
    CONTINUITY_CONTEXT_SCHEMA_VERSION,
    select_continuity_context,
)


def render_continuity_context_suffix(
    *,
    role_policy: dict[str, Any] | None,
    agent_context_packet: dict[str, Any] | None,
    seat_character_card: dict[str, Any] | None = None,
    seat_id: str,
    team_ids: set[str] | None = None,
    max_context_records: int | None = 8,
    action_contract: dict[str, Any] | None = None,
    public_timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rendered = select_continuity_context(
        seat_id=seat_id,
        team_ids=team_ids or set(),
        role_policy=role_policy,
        agent_context_packet=agent_context_packet,
        seat_character_card=seat_character_card,
        action_contract=action_contract,
        public_timeline=public_timeline,
        max_context_records=max_context_records,
    )
    return {
        "schema_version": CONTINUITY_CONTEXT_SCHEMA_VERSION,
        "selector_version": rendered["selector_version"],
        "text": rendered["text"],
        "blocks": rendered["blocks"],
        "dropped_blocks": rendered["dropped_blocks"],
    }
