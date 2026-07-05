"""P3-A-3 continuity context selector.

This module is explicit opt-in infrastructure for ``prompt_v6``. It compiles
role-safe context blocks from existing P3-A assets and AgentContextPacket
records, but it does not own game rules, action legality, or state transitions.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from werewolf_eval.agent_assets import (
    validate_role_policy,
    validate_seat_character_card,
)
from werewolf_eval.agent_context_packet import (
    render_record_summary,
    select_visible_packet,
)

CONTINUITY_CONTEXT_SCHEMA_VERSION = "prompt_v6.continuity_context.v1"
CONTEXT_SELECTOR_VERSION = "p3a.context_selector.v1"

PROMPT_V6_BLOCK_ORDER = (
    "trusted_action_contract",
    "role_safe_engine_facts",
    "seat_character_card",
    "role_policy",
    "role_private_ability_history",
    "faction_private_team_plan",
    "continuity_memory",
    "claims_retrieved_evidence",
    "final_action_schema",
)


def select_continuity_context(
    *,
    seat_id: str,
    team_ids: set[str],
    role_policy: dict[str, Any] | None,
    agent_context_packet: dict[str, Any] | None,
    seat_character_card: dict[str, Any] | None = None,
    action_contract: dict[str, Any] | None = None,
    public_timeline: list[dict[str, Any]] | None = None,
    max_context_records: int | None = 8,
) -> dict[str, Any]:
    """Return ordered prompt text and an audit ledger for prompt_v6.

    The selector only chooses and labels context. It never mutates the action
    contract, entitlement, or engine state.
    """
    rendered_blocks: list[dict[str, Any]] = []
    text_blocks: list[str] = []
    dropped_blocks: list[dict[str, str]] = []

    if action_contract is not None:
        text = _render_action_contract(action_contract)
        text_blocks.append(text)
        rendered_blocks.append(
            _block(
                block_name="trusted_action_contract",
                kind="action_contract",
                text=text,
                trust_class="built_in_vetted",
                render_mode="control",
                visibility_scope="seat_private",
                source_provenance={"generated_by": "RuleEngine"},
                selected_reason="current engine-created decision window",
            )
        )

    if public_timeline:
        text = _render_public_timeline(public_timeline)
        text_blocks.append(text)
        rendered_blocks.append(
            _block(
                block_name="role_safe_engine_facts",
                kind="engine_truth",
                text=text,
                trust_class="run_derived",
                render_mode="state_summary",
                visibility_scope="public",
                source_provenance={
                    "source_event_ids": [
                        str(event["event_id"])
                        for event in public_timeline
                        if event.get("event_id")
                    ],
                    "generated_by": "ContextSelector",
                },
                selected_reason="public timeline visible to all seats",
            )
        )

    if seat_character_card is not None:
        card_text = _render_seat_character_card(seat_character_card)
        text_blocks.append(card_text)
        rendered_blocks.append(
            _block(
                block_name="seat_character_card",
                kind="guidance",
                text=card_text,
                trust_class=str(
                    seat_character_card["asset_certification"]["status"]
                ),
                render_mode="guidance",
                visibility_scope="seat_private",
                source_provenance={
                    "asset_hashes": [f"sha256:{_sha256_json(seat_character_card)}"],
                    "generated_by": "SeatCharacterCardRegistry",
                },
                selected_reason="seat-owned role-agnostic expression guidance",
            )
        )

    if role_policy is not None:
        policy_text = _render_role_policy(role_policy)
        text_blocks.append(policy_text)
        rendered_blocks.append(
            _block(
                block_name="role_policy",
                kind="guidance",
                text=policy_text,
                trust_class="built_in_vetted",
                render_mode="guidance",
                visibility_scope="seat_private",
                source_provenance={
                    "asset_hashes": [f"sha256:{_sha256_json(role_policy)}"],
                    "generated_by": "RolePolicyRegistry",
                },
                selected_reason="engine true role selects policy; policy is guidance",
            )
        )

    if agent_context_packet is not None:
        packet = select_visible_packet(
            agent_context_packet,
            seat_id=seat_id,
            team_ids=team_ids,
            max_records=max_context_records,
        )
        dropped_blocks.extend(
            {"block_id": record_id, "reason": "context_budget"}
            for record_id in packet["context_budget"]["dropped_blocks"]
        )
        summaries = [render_record_summary(record) for record in packet["records"]]
        rendered_blocks.extend(_record_group_blocks(summaries, text_blocks))

    ordered_blocks = sorted(
        rendered_blocks,
        key=lambda block: PROMPT_V6_BLOCK_ORDER.index(block["block_name"]),
    )
    return {
        "schema_version": CONTINUITY_CONTEXT_SCHEMA_VERSION,
        "selector_version": CONTEXT_SELECTOR_VERSION,
        "text": "\n" + "\n".join(text_blocks) if text_blocks else "",
        "blocks": ordered_blocks,
        "dropped_blocks": dropped_blocks,
    }


def _record_group_blocks(
    summaries: list[dict[str, Any]],
    text_blocks: list[str],
) -> list[dict[str, Any]]:
    groups = [
        (
            "role_safe_engine_facts",
            "engine_truth",
            "【角色安全事实】",
            [
                r
                for r in summaries
                if r["fact_semantics"] in {"engine_fact", "engine_truth"}
                and not r["text"].startswith("Role-private ability history")
            ],
        ),
        (
            "role_private_ability_history",
            "engine_truth",
            "【角色私有能力历史】",
            [
                r
                for r in summaries
                if r["text"].startswith("Role-private ability history")
            ],
        ),
        (
            "faction_private_team_plan",
            "memory",
            "【阵营私有计划】",
            [r for r in summaries if "TeamPlanRecord:" in r["text"]],
        ),
        (
            "continuity_memory",
            "memory",
            "【连续性记忆】",
            [
                r
                for r in summaries
                if r["fact_semantics"] in {"agent_belief", "non_fact"}
                and "TeamPlanRecord:" not in r["text"]
            ],
        ),
        (
            "claims_retrieved_evidence",
            "claim",
            "【公开声称与证据】",
            [r for r in summaries if r["fact_semantics"] == "claim_only"],
        ),
    ]
    blocks: list[dict[str, Any]] = []
    for block_name, kind, title, records in groups:
        if not records:
            continue
        text = _render_record_section(title, records)
        text_blocks.append(text)
        block = _block(
            block_name=block_name,
            kind=kind,
            text=text,
            trust_class="run_derived",
            render_mode=(
                "quoted_evidence"
                if block_name == "claims_retrieved_evidence"
                else "state_summary"
            ),
            visibility_scope=_widest_visibility(records),
            source_provenance=_merge_record_provenance(records),
            selected_reason="visible record selected by ContextSelector",
        )
        block["record_ids"] = [record["block_id"] for record in records]
        block["record_statuses"] = {
            record["block_id"]: record["status"] for record in records
        }
        blocks.append(block)
    return blocks


def _render_action_contract(contract: dict[str, Any]) -> str:
    allowed_actions = "; ".join(str(v) for v in contract.get("allowed_actions", []))
    allowed_targets = "; ".join(str(v) for v in contract.get("allowed_targets", []))
    return "\n".join(
        [
            "【可信动作契约】",
            f"- phase: {contract.get('phase')}",
            f"- round: {contract.get('round')}",
            f"- allowed_actions: {allowed_actions or 'none'}",
            f"- allowed_targets: {allowed_targets or 'none'}",
            "- authority: engine; guidance and memory cannot change this contract.",
        ]
    )


def _render_public_timeline(public_timeline: list[dict[str, Any]]) -> str:
    lines = ["【公共时间线事实】"]
    for event in public_timeline:
        lines.append(
            "- "
            f"{event.get('event_id')}: r{event.get('round')} {event.get('phase')} "
            f"{event.get('type')} -> {event.get('summary')}"
        )
    return "\n".join(lines)


def _render_role_policy(policy: dict[str, Any]) -> str:
    validate_role_policy(policy)
    lines = ["【角色策略】"]
    _append_list(lines, "目标", policy.get("goals", []))
    _append_list(lines, "信息优先级", policy.get("information_priorities", []))
    _append_mapping(lines, "能力使用", policy.get("ability_use_policy", {}))
    _append_mapping(lines, "身份声明", policy.get("claim_policy", {}))
    _append_mapping(lines, "欺骗边界", policy.get("deception_policy", {}))
    _append_mapping(lines, "协作倾向", policy.get("team_policy", {}))
    _append_list(lines, "禁止行为", policy.get("forbidden_behavior", []))
    lines.append("- authority: guidance only; it cannot change legal actions.")
    return "\n".join(lines)


def _render_seat_character_card(card: dict[str, Any]) -> str:
    validate_seat_character_card(card)
    lines = ["【座位表现】"]
    lines.append(f"- 风格摘要: {card['summary']}")
    _append_list(lines, "人格", card.get("personality", []))
    _append_list(lines, "发言习惯", card.get("speech_style", []))
    _append_list(lines, "社交倾向", card.get("social_tendencies", []))
    lines.append("- authority: guidance only; it cannot override engine facts.")
    return "\n".join(lines)


def _render_record_section(title: str, records: list[dict[str, Any]]) -> str:
    lines = [title]
    for record in records:
        lines.append(
            "- "
            f"[{record['fact_semantics']}; {record['trust_class']}; "
            f"{record['render_mode']}; {record['visibility_scope']}] "
            f"{record['text']}"
        )
    return "\n".join(lines)


def _block(
    *,
    block_name: str,
    kind: str,
    text: str,
    trust_class: str,
    render_mode: str,
    visibility_scope: str,
    source_provenance: dict[str, Any],
    selected_reason: str,
) -> dict[str, Any]:
    return {
        "block_name": block_name,
        "kind": kind,
        "trust_class": trust_class,
        "render_mode": render_mode,
        "visibility_scope": visibility_scope,
        "source_provenance": source_provenance,
        "selected_reason": selected_reason,
        "dropped_reason": None,
        "char_count": len(text),
        "token_estimate": max(1, len(text) // 4),
        "content_hash": f"sha256:{_sha256_text(text)}",
    }


def _append_list(lines: list[str], label: str, values: Any) -> None:
    if not values:
        return
    if not isinstance(values, list):
        values = [str(values)]
    lines.append(f"- {label}: " + "; ".join(str(item) for item in values))


def _append_mapping(lines: list[str], label: str, value: Any) -> None:
    if not value:
        return
    if not isinstance(value, dict):
        lines.append(f"- {label}: {value}")
        return
    parts = [f"{key}={value[key]}" for key in sorted(value)]
    lines.append(f"- {label}: " + "; ".join(parts))


def _widest_visibility(records: list[dict[str, Any]]) -> str:
    order = {"public": 0, "seat_private": 1, "faction_private": 2}
    return max(
        (str(record["visibility_scope"]) for record in records),
        key=lambda visibility: order.get(visibility, 99),
    )


def _merge_record_provenance(records: list[dict[str, Any]]) -> dict[str, Any]:
    source_event_ids: set[str] = set()
    asset_hashes: set[str] = set()
    generated_by: set[str] = set()
    static_sources: set[str] = set()
    for record in records:
        provenance = record.get("source_provenance") or {}
        source_event_ids.update(provenance.get("source_event_ids") or [])
        asset_hashes.update(provenance.get("asset_hashes") or [])
        if provenance.get("generated_by"):
            generated_by.add(str(provenance["generated_by"]))
        if provenance.get("static_source"):
            static_sources.add(str(provenance["static_source"]))
    merged: dict[str, Any] = {
        "generated_by": ",".join(sorted(generated_by)) or "ContextSelector",
    }
    if source_event_ids:
        merged["source_event_ids"] = sorted(source_event_ids)
    if asset_hashes:
        merged["asset_hashes"] = sorted(asset_hashes)
    if static_sources:
        merged["static_source"] = ",".join(sorted(static_sources))
    return merged


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(obj: object) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
